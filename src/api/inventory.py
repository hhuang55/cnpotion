from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)


class InventoryAudit(BaseModel):
    number_of_potions: int
    ml_in_barrels: int
    gold: int


class CapacityPlan(BaseModel):
    potion_capacity: int = Field(
        ge=0, le=10, description="Potion capacity units, max 10"
    )
    ml_capacity: int = Field(ge=0, le=10, description="ML capacity units, max 10")


@router.get("/audit", response_model=InventoryAudit)
def get_inventory():
    """
    Returns an audit of the current inventory. Any discrepancies between
    what is reported here and my source of truth will be posted
    as errors on potion exchange.
    """
    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    gi.red_ml,
                    gi.green_ml,
                    gi.blue_ml,
                    gi.dark_ml,
                    gi.gold,
                    (SELECT SUM(p.amount) FROM potions p) AS totalpot
                FROM global_inventory gi
                LIMIT 1
                """
            )
        ).one()

        total_ml = row.red_ml + row.green_ml + row.blue_ml + row.dark_ml
        total_potions = row.totalpot

    return InventoryAudit(
        number_of_potions=total_potions,
        ml_in_barrels=total_ml,
        gold=row.gold
    )


@router.post("/plan", response_model=CapacityPlan)
def get_capacity_plan():
    """
    Provides a daily capacity purchase plan.

    - Start with 1 capacity for 50 potions and 1 capacity for 10,000 ml of potion.
    - Each additional capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT gold, potion_capacity, ml_capacity
                FROM global_inventory
                LIMIT 1
                """
            )
        ).first()

        gold = row.gold
        potion_capacity = row.potion_capacity
        ml_capacity = row.ml_capacity

        #have at least 1k gold
        usable_gold = max(gold - (1000 * ml_capacity), 0)
        max_units = usable_gold // 1000

        #how many can be bought
        potion_slots_left = max(10 - potion_capacity, 0)
        ml_slots_left = max(10 - ml_capacity, 0)

        #split it evenly
        potions_to_buy = min(potion_slots_left, max_units // 2)
        ml_to_buy = min(ml_slots_left, max_units - potions_to_buy)

        return CapacityPlan(potion_capacity=potions_to_buy, ml_capacity=ml_to_buy)


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def deliver_capacity_plan(capacity_purchase: CapacityPlan, order_id: int):
    """
    Processes the delivery of the planned capacity purchase. order_id is a
    unique value representing a single delivery; the call is idempotent.

    - Start with 1 capacity for 50 potions and 1 capacity for 10,000 ml of potion.
    - Each additional capacity unit costs 1000 gold.
    """
    print(f"capacity delivered: {capacity_purchase} order_id: {order_id}")
    total_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000

    with db.engine.begin() as connection:
        # Optional: check current capacities to avoid exceeding max
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT potion_capacity, ml_capacity, gold
                FROM global_inventory
                LIMIT 1
                """
            )
        ).first()

        current_potion_capacity = row.potion_capacity
        current_ml_capacity = row.ml_capacity
        current_gold = row.gold

        #check limit
        if current_potion_capacity + capacity_purchase.potion_capacity > 10 or \
           current_ml_capacity + capacity_purchase.ml_capacity > 10:
            raise HTTPException(status_code=400, detail="past the limit 10")

        #check gold
        if current_gold < total_cost:
            raise HTTPException(status_code=400, detail="not enough gold")

        #update db
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory
                SET 
                    potion_capacity = potion_capacity + :potions,
                    ml_capacity = ml_capacity + :ml,
                    gold = gold - :cost
                """
            ),
            {
                "potions": capacity_purchase.potion_capacity,
                "ml": capacity_purchase.ml_capacity,
                "cost": total_cost
            }
        )
