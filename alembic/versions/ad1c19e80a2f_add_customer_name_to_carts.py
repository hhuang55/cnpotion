"""Add customer_name to carts

Revision ID: ad1c19e80a2f
Revises: 2e134c7201ac
Create Date: 2025-04-18 18:27:59.722791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad1c19e80a2f'
down_revision: Union[str, None] = '2e134c7201ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import String
    op.add_column("carts", sa.Column("customer_name", sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column("carts", "customer_name")
