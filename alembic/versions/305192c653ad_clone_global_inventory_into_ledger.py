"""clone global inventory into ledger

Revision ID: 305192c653ad
Revises: 95dce7e380d9
Create Date: 2025-04-30 12:35:20.745535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy import text







# revision identifiers, used by Alembic.
revision: str = '305192c653ad'
down_revision: Union[str, None] = '95dce7e380d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()
    result = conn.execute(text("""
        INSERT INTO transactions (type, description)
        VALUES ('init', 'Cloned from global_inventory')
        RETURNING id;
    """))
    tx_id = result.scalar_one()

    row = conn.execute(text("""
        SELECT gold, red_ml, green_ml, blue_ml, dark_ml FROM global_inventory
    """)).one()

    for resource, amount in [
        ("gold", row.gold),
        ("red_ml", row.red_ml),
        ("green_ml", row.green_ml),
        ("blue_ml", row.blue_ml),
        ("dark_ml", row.dark_ml),
    ]:
        conn.execute(text("""
            INSERT INTO entries (transaction_id, resource, amount)
            VALUES (:tx_id, :resource, :amount)
        """), {"tx_id": tx_id, "resource": resource, "amount": amount})

def downgrade() -> None:
    """Downgrade schema."""
    pass
