"""add image_url to ingredients and products

Revision ID: 002_add_image_url
Revises: 001_initial
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "002_add_image_url"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingredients", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("products",    sa.Column("image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("ingredients", "image_url")
    op.drop_column("products",    "image_url")
