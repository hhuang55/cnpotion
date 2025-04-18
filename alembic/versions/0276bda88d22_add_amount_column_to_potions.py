"""Add amount column to potions

Revision ID: 0276bda88d22
Revises: 961e7d221450
Create Date: 2025-04-18 11:00:10.056130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0276bda88d22'
down_revision: Union[str, None] = '961e7d221450'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "potions",
        sa.Column("amount", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_check_constraint(
        "ck_potions_amount_non_negative", "potions", "amount >= 0"
    )

def downgrade() -> None:
    op.drop_constraint("ck_potions_amount_non_negative", "potions", type_="check")
    op.drop_column("potions", "amount")