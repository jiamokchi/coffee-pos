"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ingredients ───────────────────────────────────────────
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("current_stock", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("min_stock_level", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("avg_unit_cost", sa.Numeric(12, 2), nullable=False, server_default="0",
                  comment="加權平均單價 WAC"),
        sa.Column("last_updated", TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── products ──────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("barcode", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tax_type", sa.String(10), nullable=False, server_default="TAX",
                  comment="TAX/ZERO/EXEMPT"),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
    )

    # ── product_bom ───────────────────────────────────────────
    op.create_table(
        "product_bom",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("qty_required", sa.Numeric(12, 3), nullable=False,
                  comment="製作 1 份所需原料用量"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── orders ────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("payment_method", sa.String(20), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── order_items ───────────────────────────────────────────
    op.create_table(
        "order_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False,
                  comment="下單當下售價快照"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── invoices ──────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("inv_no", sa.String(10), nullable=True, comment="電子發票號碼"),
        sa.Column("random_no", sa.String(4), nullable=True),
        sa.Column("buyer_ubn", sa.String(8), nullable=True),
        sa.Column("carrier_type", sa.String(10), nullable=True),
        sa.Column("carrier_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("issued_at", TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
        sa.UniqueConstraint("inv_no"),
    )

    # ── stock_transactions ────────────────────────────────────
    op.create_table(
        "stock_transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False,
                  comment="IN/OUT_BOM/ADJUST/WASTE"),
        sa.Column("quantity_change", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("order_id", sa.BigInteger(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 效能索引 ───────────────────────────────────────────────
    op.create_index("ix_orders_status",          "orders",             ["status"])
    op.create_index("ix_orders_created_at",      "orders",             ["created_at"])
    op.create_index("ix_stock_tx_ingredient",    "stock_transactions", ["ingredient_id"])
    op.create_index("ix_stock_tx_type",          "stock_transactions", ["transaction_type"])
    op.create_index("ix_stock_tx_order",         "stock_transactions", ["order_id"])
    op.create_index("ix_order_items_order",      "order_items",        ["order_id"])
    op.create_index("ix_product_bom_product",    "product_bom",        ["product_id"])


def downgrade() -> None:
    # 反向刪除（注意外鍵相依順序）
    op.drop_table("stock_transactions")
    op.drop_table("invoices")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("product_bom")
    op.drop_table("products")
    op.drop_table("ingredients")
