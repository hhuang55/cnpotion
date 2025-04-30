"""add ledger tables

Revision ID: 95dce7e380d9
Revises: 23965ee5a14a
Create Date: 2025-04-30 12:13:38.194896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95dce7e380d9'
down_revision: Union[str, None] = '23965ee5a14a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('type', sa.Text, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('description', sa.Text),
    )

    op.create_table(
        'entries',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('transaction_id', sa.Integer, sa.ForeignKey('transactions.id')),
        sa.Column('resource', sa.Text, nullable=False),
        sa.Column('amount', sa.Integer, nullable=False),
    )

    op.create_table(
        'requests',
        sa.Column('order_id', sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column('response', sa.JSON, nullable=False),
    )


def downgrade():
    op.drop_table('requests')
    op.drop_table('entries')
    op.drop_table('transactions')