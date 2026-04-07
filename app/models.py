"""
app/models.py
SQLAlchemy ORM 模型，對應規格書 DDL。
涵蓋：原料、商品、BOM、訂單、發票。
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ══════════════════════════════════════════════════════════════
# 1. 原料 (Ingredients)
# ══════════════════════════════════════════════════════════════
class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)   # g / ml / 個 / 包…
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0"), nullable=False
    )
    min_stock_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0"), nullable=False
    )
    avg_unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False,
        comment="加權平均單價 (WAC)"
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 關聯
    bom_items: Mapped[list["ProductBOM"]] = relationship(
        "ProductBOM", back_populates="ingredient"
    )
    stock_transactions: Mapped[list["StockTransaction"]] = relationship(
        "StockTransaction", back_populates="ingredient"
    )

    def __repr__(self) -> str:
        return f"<Ingredient id={self.id} name={self.name} stock={self.current_stock}{self.unit}>"


# ══════════════════════════════════════════════════════════════
# 2. 商品 (Products)
# ══════════════════════════════════════════════════════════════
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=True)   # 咖啡 / 茶 / 餐點…
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_type: Mapped[str] = mapped_column(
        String(10), default="TAX",
        comment="TAX=應稅 / ZERO=零稅率 / EXEMPT=免稅"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 關聯
    bom_items: Mapped[list["ProductBOM"]] = relationship(
        "ProductBOM", back_populates="product", cascade="all, delete-orphan"
    )
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="product"
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} price={self.price}>"


# ══════════════════════════════════════════════════════════════
# 3. 商品配方 BOM (Bill of Materials)
# ══════════════════════════════════════════════════════════════
class ProductBOM(Base):
    __tablename__ = "product_bom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    qty_required: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False,
        comment="製作 1 份商品所需原料用量"
    )

    # 關聯
    product: Mapped["Product"] = relationship("Product", back_populates="bom_items")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="bom_items")

    def __repr__(self) -> str:
        return (
            f"<ProductBOM product_id={self.product_id} "
            f"ingredient_id={self.ingredient_id} qty={self.qty_required}>"
        )


# ══════════════════════════════════════════════════════════════
# 4. 訂單 (Orders)
# ══════════════════════════════════════════════════════════════
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING",
        comment="PENDING / COMPLETED / CANCELLED / REFUNDED"
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    payment_method: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="CASH / CARD / LINEPAY / JKOPAY"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 關聯
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    invoice: Mapped["Invoice | None"] = relationship(
        "Invoice", back_populates="order", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.status} total={self.total_amount}>"


# ══════════════════════════════════════════════════════════════
# 5. 訂單明細 (Order Items)
# ══════════════════════════════════════════════════════════════
class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="下單當下的售價快照，避免商品改價影響歷史訂單"
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # 關聯
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")

    def __repr__(self) -> str:
        return (
            f"<OrderItem order_id={self.order_id} "
            f"product_id={self.product_id} qty={self.quantity}>"
        )


# ══════════════════════════════════════════════════════════════
# 6. 台灣電子發票 (Invoices) - MIG 4.0
# ══════════════════════════════════════════════════════════════
class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="RESTRICT"),
        unique=True, nullable=False
    )
    inv_no: Mapped[str | None] = mapped_column(
        String(10), unique=True, nullable=True,
        comment="電子發票號碼，例如 AB12345678"
    )
    random_no: Mapped[str | None] = mapped_column(
        String(4), nullable=True,
        comment="隨機碼 (4位數)"
    )
    buyer_ubn: Mapped[str | None] = mapped_column(
        String(8), nullable=True,
        comment="買方統一編號（公司戶）"
    )
    carrier_type: Mapped[str | None] = mapped_column(
        String(10), nullable=True,
        comment="載具類型：3J0002=手機條碼 / CQ0001=自然人憑證"
    )
    carrier_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="載具識別碼"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="OPEN",
        comment="OPEN / CANCELLED / DONATED"
    )
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 關聯
    order: Mapped["Order"] = relationship("Order", back_populates="invoice")

    def __repr__(self) -> str:
        return f"<Invoice id={self.id} inv_no={self.inv_no} status={self.status}>"


# ══════════════════════════════════════════════════════════════
# 7. 庫存異動記錄 (Stock Transactions) — 稽核軌跡
# ══════════════════════════════════════════════════════════════
class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="IN=進貨 / OUT_BOM=BOM扣減 / ADJUST=手動調整 / WASTE=耗損"
    )
    quantity_change: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False,
        comment="正值=增加，負值=扣減"
    )
    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True,
        comment="進貨時的單位成本，用於 WAC 計算"
    )
    order_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="BOM扣減時關聯的訂單"
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 關聯
    ingredient: Mapped["Ingredient"] = relationship(
        "Ingredient", back_populates="stock_transactions"
    )

    def __repr__(self) -> str:
        return (
            f"<StockTransaction ingredient_id={self.ingredient_id} "
            f"type={self.transaction_type} change={self.quantity_change}>"
        )
