"""Add unique constraint on cart_id and potion_sku

Revision ID: ec3e784a989b
Revises: ad1c19e80a2f
Create Date: 2025-04-18 18:35:12.820034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec3e784a989b'
down_revision: Union[str, None] = 'ad1c19e80a2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uix_cart_potion",  
        "cart_items",       
        ["cart_id", "potion_sku"]  
    )


def downgrade() -> None:
    op.drop_constraint(
        "uix_cart_potion",
        "cart_items",
        type_="unique"
    )
