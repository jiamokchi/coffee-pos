"""
app/api/orders.py
訂單相關 API 路由，包含訂單完成觸發 BOM 扣減。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order
from app.services.bom_service import (
    DeductionResult,
    InsufficientStockError,
    OrderAlreadyCompletedError,
    deduct_stock_by_bom,
)

router = APIRouter(prefix="/orders", tags=["Orders"])
from app.schemas import OrderCreate, OrderOut
from app.models import OrderItem


# ── Pydantic Schemas (簡化版，完整版請放 schemas/order.py) ────────────────────

class OrderStatusUpdate(BaseModel):
    status: str   # PENDING / COMPLETED / CANCELLED / REFUNDED


class CompleteOrderResponse(BaseModel):
    order_id: int
    status: str
    bom_deduction: dict


# ══════════════════════════════════════════════════════════════
# POST /orders
# 建立新訂單
# ══════════════════════════════════════════════════════════════

@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    """
    建立新訂單（初始狀態為 PENDING）。
    """
    order = Order(
        status="PENDING",
        total_amount=payload.total_amount,
        tax_amount=payload.tax_amount,
        payment_method=payload.payment_method,
        note=payload.note,
    )
    db.add(order)
    db.flush()

    for item in payload.items:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
        ))

    db.flush()
    db.refresh(order)
    return order


# ══════════════════════════════════════════════════════════════
# PATCH /orders/{order_id}/status
# 訂單狀態更新 → 若變更為 COMPLETED，自動觸發 BOM 扣減
# ══════════════════════════════════════════════════════════════

@router.patch("/{order_id}/status", response_model=CompleteOrderResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    更新訂單狀態。
    - 當 status = COMPLETED 時，自動執行 BOM 庫存扣減。
    - 所有操作在同一個 DB transaction 中完成（原子性）。
    """
    order: Order | None = db.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"訂單 {order_id} 不存在",
        )

    allowed_transitions = {
        "PENDING":   {"COMPLETED", "CANCELLED"},
        "COMPLETED": {"REFUNDED"},
        "CANCELLED": set(),
        "REFUNDED":  set(),
    }
    if payload.status not in allowed_transitions.get(order.status, set()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不允許從 {order.status} 變更為 {payload.status}",
        )

    order.status = payload.status
    bom_result: DeductionResult | None = None

    # ── 觸發 BOM 扣減 ──────────────────────────────────────────
    if payload.status == "COMPLETED":
        try:
            bom_result = deduct_stock_by_bom(db=db, order_id=order_id)
        except OrderAlreadyCompletedError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        except InsufficientStockError as e:
            # 庫存不足 → 整個 transaction rollback（由 get_db 處理）
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "原料庫存不足，訂單無法完成",
                    "ingredient": e.ingredient_name,
                    "required": float(e.required),
                    "available": float(e.available),
                },
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    return CompleteOrderResponse(
        order_id=order_id,
        status=order.status,
        bom_deduction=(
            {
                "success": bom_result.success,
                "deducted_items": bom_result.deducted_items,
                "warnings": bom_result.warnings,
            }
            if bom_result
            else {}
        ),
    )


# ══════════════════════════════════════════════════════════════
# POST /orders/{order_id}/complete  (語意化捷徑)
# ══════════════════════════════════════════════════════════════

@router.post("/{order_id}/complete", response_model=CompleteOrderResponse)
def complete_order(
    order_id: int,
    db: Session = Depends(get_db),
):
    """
    將訂單標記為完成並執行 BOM 庫存扣減的捷徑端點。
    等同於 PATCH /orders/{order_id}/status { "status": "COMPLETED" }
    """
    order: Order | None = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"訂單 {order_id} 不存在")
    if order.status != "PENDING":
        raise HTTPException(
            status_code=422,
            detail=f"訂單目前狀態為 {order.status}，無法完成",
        )

    order.status = "COMPLETED"

    try:
        bom_result = deduct_stock_by_bom(db=db, order_id=order_id)
    except InsufficientStockError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "原料庫存不足",
                "ingredient": e.ingredient_name,
                "required": float(e.required),
                "available": float(e.available),
            },
        )

    return CompleteOrderResponse(
        order_id=order_id,
        status="COMPLETED",
        bom_deduction={
            "success": bom_result.success,
            "deducted_items": bom_result.deducted_items,
            "warnings": bom_result.warnings,
        },
    )
