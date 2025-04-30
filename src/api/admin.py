from fastapi import APIRouter, Depends, status
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """

    with db.engine.begin() as connection:
        # Reset capacity in global_inventory only
        connection.execute(
            sqlalchemy.text("""
                UPDATE global_inventory
                SET potion_capacity = 1, ml_capacity = 1
            """)
        )

        # Clear potions
        connection.execute(sqlalchemy.text("UPDATE potions SET amount = 0"))

        # Clear carts
        connection.execute(sqlalchemy.text("DELETE FROM cart_items"))
        connection.execute(sqlalchemy.text("DELETE FROM carts"))

        # Clear ledger + add baseline transaction
        connection.execute(sqlalchemy.text("DELETE FROM entries"))
        connection.execute(sqlalchemy.text("DELETE FROM transactions"))

        tx_id = connection.execute(sqlalchemy.text("""
            INSERT INTO transactions (type, description)
            VALUES ('reset', 'Reset game state')
            RETURNING id
        """)).scalar_one()

        base_entries = [
            ("gold", 100),
            ("red_ml", 0),
            ("green_ml", 0),
            ("blue_ml", 0),
            ("dark_ml", 0),
        ]

        for resource, amount in base_entries:
            connection.execute(sqlalchemy.text("""
                INSERT INTO entries (transaction_id, resource, amount)
                VALUES (:tx_id, :resource, :amount)
            """), {"tx_id": tx_id, "resource": resource, "amount": amount})

    return


