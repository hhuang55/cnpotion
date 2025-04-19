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
        # Reset global inventory
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory SET 
                gold = 100,
                red_ml = 0,
                green_ml = 0,
                blue_ml = 0,
                dark_ml = 0
                """
            )
        )
    
        # clear potion inventory
        connection.execute(sqlalchemy.text("UPDATE potions SET amount = 0"))

        # clear cart data
        connection.execute(sqlalchemy.text("DELETE FROM cart_items"))
        connection.execute(sqlalchemy.text("DELETE FROM carts"))


    return

