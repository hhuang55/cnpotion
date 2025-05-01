from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field
import sqlalchemy
from src.api import auth
from src import database as db
import json

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
        total_potions = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM potions")
        ).scalar_one()

        total_ml = connection.execute(
            sqlalchemy.text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM entries
                WHERE resource IN ('red_ml', 'green_ml', 'blue_ml', 'dark_ml')
            """),
        ).scalar_one()

        gold = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'gold'")
        ).scalar_one()

    return InventoryAudit(
        number_of_potions=total_potions,
        ml_in_barrels=total_ml,
        gold=gold
    )


@router.post("/plan", response_model=CapacityPlan)
def get_capacity_plan():

    """
    Provides a daily capacity purchase plan.

    - Start with 1 capacity for 50 potions and 1 capacity for 10,000 ml of potion.
    - Each additional capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:
        gold = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'gold'")
        ).scalar_one()

        caps = connection.execute(
            sqlalchemy.text("SELECT potion_capacity, ml_capacity FROM global_inventory")
        ).first()

        potion_capacity = caps.potion_capacity
        ml_capacity = caps.ml_capacity

        usable_gold = max(gold - 1000, 0)
        units_available = usable_gold // 1000

        max_potions = 10 - potion_capacity
        max_ml = 10 - ml_capacity

        potions_to_buy = 0
        ml_to_buy = 0

        while units_available > 0 and (max_potions > 0 or max_ml > 0):
            if potion_capacity + potions_to_buy < ml_capacity + ml_to_buy and max_potions > 0:
                potions_to_buy += 1
                max_potions -= 1
            elif ml_capacity + ml_to_buy < potion_capacity + potions_to_buy and max_ml > 0:
                ml_to_buy += 1
                max_ml -= 1
            else:
                if max_potions > 0:
                    potions_to_buy += 1
                    max_potions -= 1
                elif max_ml > 0:
                    ml_to_buy += 1
                    max_ml -= 1
            units_available -= 1

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
        source = "inventory"
        existing = connection.execute(
            sqlalchemy.text("SELECT response FROM requests WHERE order_id = :order_id AND source = :source"),
            {"order_id": str(order_id), "source": source}
        ).fetchone()


        if existing:
            return json.loads(existing.response)

        gold = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'gold'")
        ).scalar_one()

        caps = connection.execute(
            sqlalchemy.text("SELECT potion_capacity, ml_capacity FROM global_inventory")
        ).first()

        if caps.potion_capacity + capacity_purchase.potion_capacity > 10 or \
           caps.ml_capacity + capacity_purchase.ml_capacity > 10:
            raise HTTPException(status_code=400, detail="past the limit 10")

        if gold < total_cost:
            raise HTTPException(status_code=400, detail="not enough gold")

        tx_id = connection.execute(
            sqlalchemy.text("""
                INSERT INTO transactions (type, description)
                VALUES ('capacity', 'Purchased capacity')
                RETURNING id
            """),
        ).scalar_one()

        connection.execute(
            sqlalchemy.text("""
                INSERT INTO entries (transaction_id, resource, amount)
                VALUES (:tx_id, 'gold', :amount)
            """),
            {"tx_id": tx_id, "amount": -total_cost}
        )

        connection.execute(
            sqlalchemy.text("""
                UPDATE global_inventory
                SET 
                    potion_capacity = potion_capacity + :potions,
                    ml_capacity = ml_capacity + :ml
            """),
            {
                "potions": capacity_purchase.potion_capacity,
                "ml": capacity_purchase.ml_capacity
            }
        )

        connection.execute(
            sqlalchemy.text("""
                INSERT INTO requests (order_id, source, response)
                VALUES (:order_id, :source, :response)
            """),
            {"order_id": str(order_id), "source": source, "response": json.dumps({"status": "ok"})}
        )

    return {"status": "ok"}