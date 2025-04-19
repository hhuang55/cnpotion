"""Add checked out

Revision ID: c7d8c6368cc9
Revises: ec3e784a989b
Create Date: 2025-04-18 18:42:14.524634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8c6368cc9'
down_revision: Union[str, None] = 'ec3e784a989b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("carts", sa.Column("checked_out", sa.Boolean(), nullable=False, server_default=sa.text("false")))



def downgrade() -> None:
    op.drop_column("carts", "checked_out")

