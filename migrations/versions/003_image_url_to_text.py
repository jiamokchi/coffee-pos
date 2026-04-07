"""change image_url to text

Revision ID: 003_image_url_to_text
Revises: 002_add_image_url
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "003_image_url_to_text"
down_revision = "002_add_image_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres uses TEXT which is better for Base64 strings.
    op.alter_column('ingredients', 'image_url', type_=sa.Text())
    op.alter_column('products',    'image_url', type_=sa.Text())


def downgrade() -> None:
    op.alter_column('ingredients', 'image_url', type_=sa.String(500))
    op.alter_column('products',    'image_url', type_=sa.String(500))
