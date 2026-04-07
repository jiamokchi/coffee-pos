"""
app/services/bom_service.py
BOM 庫存自動扣減服務。

規格書邏輯：
  觸發點：訂單狀態變更為 COMPLETED
  流程：product_bom → current_stock - (qty * qty_required)
  同時：寫入 StockTransaction 稽核記錄
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Ingredient, Order, OrderItem, ProductBOM, StockTransaction

logger = logging.getLogger(__name__)


# ── 自定義例外 ────────────────────────────────────────────────────────────────

class InsufficientStockError(Exception):
    """原料庫存不足，無法完成 BOM 扣減"""
    def __init__(self, ingredient_name: str, required: Decimal, available: Decimal):
        self.ingredient_name = ingredient_name
        self.required = required
        self.available = available
        super().__init__(
            f"原料「{ingredient_name}」庫存不足："
            f"需要 {required}，現有 {available}"
        )


class OrderAlreadyCompletedError(Exception):
    """訂單已完成，避免重複扣減"""
    pass


# ── 回傳資料結構 ──────────────────────────────────────────────────────────────

@dataclass
class DeductionResult:
    """BOM 扣減結果摘要"""
    order_id: int
    success: bool
    deducted_items: list[dict]   # [{ingredient_name, qty_deducted}]
    warnings: list[str]          # 低庫存警告（扣減後低於 min_stock_level）


# ══════════════════════════════════════════════════════════════
# 核心服務函式
# ══════════════════════════════════════════════════════════════

def deduct_stock_by_bom(db: Session, order_id: int) -> DeductionResult:
    """
    訂單完成時，根據 BOM 自動扣減原料庫存。

    流程：
    1. 驗證訂單存在且狀態為 COMPLETED
    2. 彙整本次訂單所有商品 × 數量的原料需求
    3. 預檢全部原料是否充足（all-or-nothing）
    4. 批次更新 current_stock
    5. 寫入 StockTransaction 稽核記錄
    6. 回傳扣減結果（含低庫存警告）

    Args:
        db:       SQLAlchemy Session（由路由層透過 Depends 注入）
        order_id: 目標訂單 ID

    Returns:
        DeductionResult

    Raises:
        ValueError:              訂單不存在或狀態不符
        OrderAlreadyCompletedError: 重複觸發保護
        InsufficientStockError:  任一原料庫存不足
    """
    # ── Step 1：取得訂單 ────────────────────────────────────────
    order: Order | None = db.get(Order, order_id)
    if order is None:
        raise ValueError(f"訂單 {order_id} 不存在")

    if order.status != "COMPLETED":
        raise ValueError(
            f"訂單 {order_id} 狀態為 {order.status}，"
            "只有 COMPLETED 訂單才能觸發 BOM 扣減"
        )

    # 防止重複扣減（若已存在 OUT_BOM 記錄）
    existing = (
        db.query(StockTransaction)
        .filter(
            StockTransaction.order_id == order_id,
            StockTransaction.transaction_type == "OUT_BOM",
        )
        .first()
    )
    if existing:
        raise OrderAlreadyCompletedError(
            f"訂單 {order_id} 已執行過 BOM 扣減，禁止重複操作"
        )

    # ── Step 2：彙整原料需求 ────────────────────────────────────
    # { ingredient_id: total_qty_needed }
    ingredient_demand: dict[int, Decimal] = {}

    items: list[OrderItem] = order.items
    if not items:
        logger.warning(f"訂單 {order_id} 沒有任何明細，跳過 BOM 扣減")
        return DeductionResult(
            order_id=order_id,
            success=True,
            deducted_items=[],
            warnings=["訂單無商品明細"],
        )

    for item in items:
        bom_list: list[ProductBOM] = (
            db.query(ProductBOM)
            .filter(ProductBOM.product_id == item.product_id)
            .all()
        )
        for bom in bom_list:
            needed = bom.qty_required * Decimal(str(item.quantity))
            ingredient_demand[bom.ingredient_id] = (
                ingredient_demand.get(bom.ingredient_id, Decimal("0")) + needed
            )

    if not ingredient_demand:
        logger.info(f"訂單 {order_id} 所有商品均無 BOM 配方，無需扣減庫存")
        return DeductionResult(
            order_id=order_id,
            success=True,
            deducted_items=[],
            warnings=[],
        )

    # ── Step 3：預檢庫存（all-or-nothing，避免部分扣減） ─────────
    ingredients: dict[int, Ingredient] = {
        ing.id: ing
        for ing in db.query(Ingredient)
        .filter(Ingredient.id.in_(ingredient_demand.keys()))
        .with_for_update()  # 加鎖，防止並發超賣
        .all()
    }

    for ingredient_id, needed_qty in ingredient_demand.items():
        ing = ingredients.get(ingredient_id)
        if ing is None:
            raise ValueError(f"原料 ID {ingredient_id} 不存在於資料庫")
        if ing.current_stock < needed_qty:
            raise InsufficientStockError(
                ingredient_name=ing.name,
                required=needed_qty,
                available=ing.current_stock,
            )

    # ── Step 4 & 5：執行扣減 + 寫稽核記錄 ──────────────────────
    deducted_items = []
    warnings = []
    now = datetime.now(tz=timezone.utc)

    for ingredient_id, deduct_qty in ingredient_demand.items():
        ing = ingredients[ingredient_id]
        ing.current_stock -= deduct_qty
        ing.last_updated = now

        # 稽核記錄
        tx = StockTransaction(
            ingredient_id=ingredient_id,
            transaction_type="OUT_BOM",
            quantity_change=-deduct_qty,   # 負值代表扣減
            order_id=order_id,
            note=f"訂單 #{order_id} BOM 自動扣減",
        )
        db.add(tx)

        deducted_items.append({
            "ingredient_id": ingredient_id,
            "ingredient_name": ing.name,
            "unit": ing.unit,
            "qty_deducted": float(deduct_qty),
            "remaining_stock": float(ing.current_stock),
        })

        # 低庫存警告
        if ing.current_stock < ing.min_stock_level:
            msg = (
                f"⚠️ 原料「{ing.name}」庫存 {ing.current_stock}{ing.unit} "
                f"已低於安全庫存 {ing.min_stock_level}{ing.unit}"
            )
            warnings.append(msg)
            logger.warning(msg)

    # db.commit() 由呼叫端（路由層的 get_db）負責，這裡只 flush 讓 ID 生效
    db.flush()

    logger.info(
        f"✅ 訂單 {order_id} BOM 扣減完成，"
        f"共異動 {len(deducted_items)} 種原料"
    )

    return DeductionResult(
        order_id=order_id,
        success=True,
        deducted_items=deducted_items,
        warnings=warnings,
    )
