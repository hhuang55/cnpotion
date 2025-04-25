"""add class table to carts

Revision ID: 23965ee5a14a
Revises: 3eafe8a1692b
Create Date: 2025-04-25 12:52:12.658896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23965ee5a14a'
down_revision: Union[str, None] = '3eafe8a1692b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import String
    op.add_column("carts", sa.Column("customer_class", sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column("carts", "customer_class")