"""
app/api/inventory.py
進貨入庫、盤點調整、庫存查詢 API。
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.inventory_service import adjust_stock, stock_in, stock_in_roasted_bean

router = APIRouter(prefix="/inventory", tags=["Inventory"])


class StockInRequest(BaseModel):
    ingredient_id: int
    qty: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)
    note: str = ""


class RoastedBeanRequest(BaseModel):
    green_bean_ingredient_id: int
    roasted_bean_ingredient_id: int
    green_qty: Decimal = Field(gt=0, description="生豆重量 (g)")
    loss_rate: Decimal = Field(gt=0, lt=1, description="失重率 0.0~1.0")
    unit_cost_per_green: Decimal = Field(ge=0, description="生豆單價 (元/g)")
    note: str = ""


class AdjustRequest(BaseModel):
    ingredient_id: int
    actual_qty: Decimal = Field(ge=0)
    note: str = "盤點調整"


@router.post("/stock-in")
def api_stock_in(payload: StockInRequest, db: Session = Depends(get_db)):
    """一般原料進貨入庫（更新 WAC）"""
    try:
        result = stock_in(db, **payload.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stock-in/roasted-bean")
def api_stock_in_roasted(payload: RoastedBeanRequest, db: Session = Depends(get_db)):
    """自烘豆入庫（含失重率換算）"""
    try:
        green_r, roasted_r = stock_in_roasted_bean(db, **payload.model_dump())
        return {"green_bean": green_r, "roasted_bean": roasted_r}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/adjust")
def api_adjust(payload: AdjustRequest, db: Session = Depends(get_db)):
    """手動盤點庫存調整"""
    try:
        return adjust_stock(db, **payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
