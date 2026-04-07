"""
app/schemas/__init__.py  +  全部 schema 集中一檔方便匯入
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


# ══════════════════════════════════════════════════════════════
# Ingredient
# ══════════════════════════════════════════════════════════════
class IngredientBase(BaseModel):
    name: str = Field(..., max_length=100)
    unit: str = Field(..., max_length=20)
    min_stock_level: Decimal = Field(default=Decimal("0"), ge=0)
    image_url: Optional[str] = None


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    min_stock_level: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class IngredientOut(IngredientBase):
    id: int
    current_stock: Decimal
    avg_unit_cost: Decimal
    last_updated: datetime
    is_active: bool = True
    is_low_stock: bool = False
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════
# BOM
# ══════════════════════════════════════════════════════════════
class BOMItemIn(BaseModel):
    ingredient_id: int
    qty_required: Decimal = Field(..., gt=0)


class BOMItemOut(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str = ""
    unit: str = ""
    qty_required: Decimal

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════
# Product
# ══════════════════════════════════════════════════════════════
class ProductBase(BaseModel):
    name: str = Field(..., max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    price: Decimal = Field(..., gt=0)
    barcode: Optional[str] = Field(None, max_length=50)
    tax_type: str = Field(default="TAX", pattern="^(TAX|ZERO|EXEMPT)$")
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    bom: list[BOMItemIn] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    barcode: Optional[str] = None
    is_active: Optional[bool] = None
    tax_type: Optional[str] = Field(None, pattern="^(TAX|ZERO|EXEMPT)$")
    bom: Optional[list[BOMItemIn]] = None


class ProductOut(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    bom_items: list[BOMItemOut] = []

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════
# Order
# ══════════════════════════════════════════════════════════════
class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    subtotal: Decimal = Field(..., gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(..., min_length=1)
    total_amount: Decimal
    tax_amount: Decimal
    payment_method: Optional[str] = Field(None, pattern="^(CASH|CARD|LINEPAY|JKOPAY)$")
    note: Optional[str] = None


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    status: str
    total_amount: Decimal
    tax_amount: Decimal
    payment_method: Optional[str]
    note: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    items: list[OrderItemOut] = []

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════
# Invoice
# ══════════════════════════════════════════════════════════════
class InvoiceCreate(BaseModel):
    order_id: int
    carrier_type: Optional[str] = None
    carrier_id: Optional[str] = None
    buyer_ubn: Optional[str] = Field(None, pattern=r"^\d{8}$")

    @field_validator("carrier_id")
    @classmethod
    def validate_carrier_id(cls, v, info):
        if v is None:
            return v
        ct = info.data.get("carrier_type")
        if ct == "3J0002" and not re.match(r"^/[A-Z0-9+\-.]{7}$", v):
            raise ValueError("手機條碼格式錯誤，應為 /XXXXXXX")
        if ct == "CQ0001" and not re.match(r"^[A-Z]{2}\d{14}$", v):
            raise ValueError("自然人憑證格式錯誤")
        return v


class InvoiceOut(BaseModel):
    id: int
    order_id: int
    inv_no: Optional[str]
    random_no: Optional[str]
    buyer_ubn: Optional[str]
    carrier_type: Optional[str]
    status: str
    issued_at: Optional[datetime]

    model_config = {"from_attributes": True}
