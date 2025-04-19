"""add carts and cart_items tables

Revision ID: 2e134c7201ac
Revises: 0276bda88d22
Create Date: 2025-04-18 18:04:57.114782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e134c7201ac'
down_revision: Union[str, None] = '0276bda88d22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "carts",
        sa.Column("cart_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "cart_items",
        sa.Column("cart_item_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("cart_id", sa.Integer, sa.ForeignKey("carts.cart_id", ondelete="CASCADE"), nullable=False),
        sa.Column("potion_sku", sa.String(), sa.ForeignKey("potions.sku", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cart_items")
    op.drop_table("carts")

