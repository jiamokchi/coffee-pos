"""add is_active to ingredients

Revision ID: 004_add_ingredient_active
Revises: 003_image_url_to_text
Create Date: 2026-03-28
"""
from alembic import op
import sqlalchemy as sa

revision = "004_add_ingredient_active"
down_revision = "003_image_url_to_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_active column to ingredients
    op.add_column('ingredients', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('ingredients', 'is_active')
