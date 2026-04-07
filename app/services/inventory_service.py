"""
app/services/inventory_service.py
進貨入庫服務：加權平均成本 (WAC) 計算 + 自烘豆失重補償。

WAC 公式：
  新平均成本 = (現有庫存量 × 舊平均成本 + 進貨量 × 進貨單價)
               ÷ (現有庫存量 + 進貨量)
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models import Ingredient, StockTransaction

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal("0.01")


# ── 回傳資料結構 ──────────────────────────────────────────────

@dataclass
class StockInResult:
    ingredient_id: int
    ingredient_name: str
    qty_received: Decimal        # 實際入庫量（熟豆已換算）
    new_stock: Decimal
    old_avg_cost: Decimal
    new_avg_cost: Decimal        # WAC 更新後的平均成本


# ══════════════════════════════════════════════════════════════
# 標準進貨入庫
# ══════════════════════════════════════════════════════════════

def stock_in(
    db: Session,
    ingredient_id: int,
    qty: Decimal,
    unit_cost: Decimal,
    note: str = "",
) -> StockInResult:
    """
    一般原料進貨入庫，更新 WAC 與庫存量。

    Args:
        db:            SQLAlchemy Session
        ingredient_id: 原料 ID
        qty:           進貨數量
        unit_cost:     本次進貨單價
        note:          備註（例如發票號碼）
    """
    ing: Ingredient | None = (
        db.query(Ingredient)
        .filter(Ingredient.id == ingredient_id)
        .with_for_update()
        .first()
    )
    if ing is None:
        raise ValueError(f"原料 ID {ingredient_id} 不存在")
    if qty <= 0:
        raise ValueError("進貨數量必須大於 0")
    if unit_cost < 0:
        raise ValueError("進貨單價不能為負數")

    old_avg_cost = ing.avg_unit_cost
    new_avg_cost = _calc_wac(
        current_stock=ing.current_stock,
        current_avg_cost=ing.avg_unit_cost,
        incoming_qty=qty,
        incoming_unit_cost=unit_cost,
    )

    ing.current_stock += qty
    ing.avg_unit_cost = new_avg_cost
    ing.last_updated = datetime.now(tz=timezone.utc)

    tx = StockTransaction(
        ingredient_id=ingredient_id,
        transaction_type="IN",
        quantity_change=qty,
        unit_cost=unit_cost,
        note=note or f"進貨入庫 {qty}{ing.unit} @ {unit_cost}",
    )
    db.add(tx)
    db.flush()

    logger.info(
        f"進貨完成：{ing.name} +{qty}{ing.unit}，"
        f"WAC {old_avg_cost} → {new_avg_cost}"
    )

    return StockInResult(
        ingredient_id=ingredient_id,
        ingredient_name=ing.name,
        qty_received=qty,
        new_stock=ing.current_stock,
        old_avg_cost=old_avg_cost,
        new_avg_cost=new_avg_cost,
    )


# ══════════════════════════════════════════════════════════════
# 自烘豆失重補償入庫
# ══════════════════════════════════════════════════════════════

def stock_in_roasted_bean(
    db: Session,
    green_bean_ingredient_id: int,   # 生豆原料 ID（扣減）
    roasted_bean_ingredient_id: int, # 熟豆原料 ID（增加）
    green_qty: Decimal,              # 生豆進貨量 (g)
    loss_rate: Decimal,              # 失重率，例如 0.18 代表 18%
    unit_cost_per_green: Decimal,    # 生豆進貨單價 (元/g)
    note: str = "",
) -> tuple[StockInResult, StockInResult]:
    """
    自烘豆工作流程：
      1. 生豆進貨（增加生豆庫存）
      2. 烘焙完成：生豆 → 熟豆，依失重率換算熟豆重量
      3. 熟豆成本 = 生豆總成本 ÷ 熟豆重量

    Args:
        loss_rate: 0.0 ~ 1.0 之間，例如失重 18% 填 0.18

    Returns:
        (生豆入庫結果, 熟豆入庫結果)
    """
    if not (0 < loss_rate < 1):
        raise ValueError("失重率必須介於 0 到 1 之間（例如 0.18 代表 18%）")

    roasted_qty = green_qty * (Decimal("1") - loss_rate)
    roasted_qty = roasted_qty.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    # 熟豆成本 = 生豆總成本 / 熟豆重量
    total_green_cost = green_qty * unit_cost_per_green
    roasted_unit_cost = (total_green_cost / roasted_qty).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )

    note_prefix = note or f"自烘豆入庫（失重率 {loss_rate*100:.1f}%）"

    # 生豆入庫
    green_result = stock_in(
        db=db,
        ingredient_id=green_bean_ingredient_id,
        qty=green_qty,
        unit_cost=unit_cost_per_green,
        note=f"{note_prefix} - 生豆",
    )

    # 熟豆入庫（成本已換算）
    roasted_result = stock_in(
        db=db,
        ingredient_id=roasted_bean_ingredient_id,
        qty=roasted_qty,
        unit_cost=roasted_unit_cost,
        note=f"{note_prefix} - 熟豆（從 {green_qty}g 生豆烘製）",
    )

    logger.info(
        f"自烘豆：生豆 {green_qty}g → 熟豆 {roasted_qty}g"
        f"（實際失重 {(1 - roasted_qty/green_qty)*100:.1f}%），"
        f"熟豆單價 {roasted_unit_cost} 元/g"
    )

    return green_result, roasted_result


# ══════════════════════════════════════════════════════════════
# 手動庫存調整（盤點）
# ══════════════════════════════════════════════════════════════

def adjust_stock(
    db: Session,
    ingredient_id: int,
    actual_qty: Decimal,    # 盤點後的實際庫存量
    note: str = "盤點調整",
) -> dict:
    """
    手動盤點調整：將庫存直接設為實際數量，記錄差異。
    不影響 WAC（成本不因盤損/盤盈改變）。
    """
    ing: Ingredient | None = (
        db.query(Ingredient)
        .filter(Ingredient.id == ingredient_id)
        .with_for_update()
        .first()
    )
    if ing is None:
        raise ValueError(f"原料 ID {ingredient_id} 不存在")

    diff = actual_qty - ing.current_stock
    ing.current_stock = actual_qty
    ing.last_updated = datetime.now(tz=timezone.utc)

    tx = StockTransaction(
        ingredient_id=ingredient_id,
        transaction_type="ADJUST",
        quantity_change=diff,
        note=f"{note}（系統:{ing.current_stock + diff} → 實際:{actual_qty}）",
    )
    db.add(tx)
    db.flush()

    return {
        "ingredient_id": ingredient_id,
        "ingredient_name": ing.name,
        "before": float(ing.current_stock - diff),  # 調整前
        "after": float(actual_qty),
        "difference": float(diff),
    }


# ══════════════════════════════════════════════════════════════
# 內部工具
# ══════════════════════════════════════════════════════════════

def _calc_wac(
    current_stock: Decimal,
    current_avg_cost: Decimal,
    incoming_qty: Decimal,
    incoming_unit_cost: Decimal,
) -> Decimal:
    """
    加權平均成本計算。
    若現有庫存為 0（或負），直接以本次進貨價作為新平均成本。
    """
    total_qty = current_stock + incoming_qty
    if total_qty == 0:
        return Decimal("0")

    if current_stock <= 0:
        # 庫存歸零後首次進貨，重置為本次單價
        return incoming_unit_cost.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    wac = (
        current_stock * current_avg_cost + incoming_qty * incoming_unit_cost
    ) / total_qty

    return wac.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
