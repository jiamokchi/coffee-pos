"""
tests/test_bom_service.py
BOM 庫存扣減的單元測試（使用 SQLite in-memory 替代 PostgreSQL）。
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Ingredient, Order, OrderItem, Product, ProductBOM
from app.services.bom_service import (
    InsufficientStockError,
    OrderAlreadyCompletedError,
    deduct_stock_by_bom,
)

# ── 測試用 SQLite In-Memory DB ────────────────────────────────
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(TEST_ENGINE)
    yield
    Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


def _seed(db):
    """建立測試資料：拿鐵 = 牛奶 200ml + 濃縮咖啡 30ml"""
    milk = Ingredient(name="全脂牛奶", unit="ml", current_stock=Decimal("500"), min_stock_level=Decimal("100"), avg_unit_cost=Decimal("0.05"))
    espresso = Ingredient(name="濃縮咖啡液", unit="ml", current_stock=Decimal("200"), min_stock_level=Decimal("50"), avg_unit_cost=Decimal("0.3"))
    db.add_all([milk, espresso])
    db.flush()

    latte = Product(name="拿鐵", price=Decimal("120"), tax_type="TAX")
    db.add(latte)
    db.flush()

    db.add_all([
        ProductBOM(product_id=latte.id, ingredient_id=milk.id, qty_required=Decimal("200")),
        ProductBOM(product_id=latte.id, ingredient_id=espresso.id, qty_required=Decimal("30")),
    ])

    order = Order(status="COMPLETED")
    db.add(order)
    db.flush()

    db.add(OrderItem(order_id=order.id, product_id=latte.id, quantity=2, unit_price=Decimal("120"), subtotal=Decimal("240")))
    db.commit()

    return {"milk": milk, "espresso": espresso, "latte": latte, "order": order}


def test_bom_deduction_success(db):
    data = _seed(db)
    result = deduct_stock_by_bom(db, data["order"].id)
    db.commit()

    assert result.success is True
    assert len(result.deducted_items) == 2

    db.refresh(data["milk"])
    db.refresh(data["espresso"])
    # 2 杯拿鐵：牛奶 500 - 400 = 100，濃縮 200 - 60 = 140
    assert data["milk"].current_stock == Decimal("100")
    assert data["espresso"].current_stock == Decimal("140")


def test_insufficient_stock_raises(db):
    data = _seed(db)
    # 把牛奶庫存調到不夠
    data["milk"].current_stock = Decimal("100")
    db.commit()

    with pytest.raises(InsufficientStockError) as exc_info:
        deduct_stock_by_bom(db, data["order"].id)

    assert "全脂牛奶" in str(exc_info.value)


def test_duplicate_deduction_raises(db):
    data = _seed(db)
    deduct_stock_by_bom(db, data["order"].id)
    db.commit()

    with pytest.raises(OrderAlreadyCompletedError):
        deduct_stock_by_bom(db, data["order"].id)


def test_low_stock_warning(db):
    data = _seed(db)
    # 牛奶扣完後剛好等於安全庫存邊緣
    data["milk"].current_stock = Decimal("400")  # 扣 400 後剩 0 < min 100
    db.commit()

    result = deduct_stock_by_bom(db, data["order"].id)
    db.commit()

    assert any("全脂牛奶" in w for w in result.warnings)
