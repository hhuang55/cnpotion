"""change uuid into int

Revision ID: 0f7f89d743ec
Revises: 305192c653ad
Create Date: 2025-04-30 16:02:15.777866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f7f89d743ec'
down_revision: Union[str, None] = '305192c653ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_table("requests")
    op.create_table(
        "requests",
        sa.Column("order_id", sa.Integer(), primary_key=True),
        sa.Column("response", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
