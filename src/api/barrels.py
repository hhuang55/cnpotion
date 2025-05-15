from dataclasses import dataclass
from fastapi import HTTPException
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List

import sqlalchemy
from src.api import auth
from src import database as db
import random

from uuid import UUID

import json




router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)


class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int = Field(gt=0, description="Must be greater than 0")
    potion_type: List[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Must contain exactly 4 elements: [r, g, b, d] that sum to 1.0",
    )
    price: int = Field(ge=0, description="Price must be non-negative")
    quantity: int = Field(ge=0, description="Quantity must be non-negative")

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[float]) -> List[float]:
        if len(potion_type) != 4:
            raise ValueError("potion_type must have exactly 4 elements: [r, g, b, d]")
        if not abs(sum(potion_type) - 1.0) < 1e-6:
            raise ValueError("Sum of potion_type values must be exactly 1.0")
        return potion_type


class BarrelOrder(BaseModel):
    sku: str
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


@dataclass
class BarrelSummary:
    gold_paid: int


def calculate_barrel_summary(barrels: List[Barrel]) -> BarrelSummary:
    return BarrelSummary(gold_paid=sum(b.price * b.quantity for b in barrels))


@router.post("/deliver/{order_id}", status_code=status.HTTP_200_OK)
def post_deliver_barrels(barrels_delivered: List[Barrel], order_id: int):
    delivery = calculate_barrel_summary(barrels_delivered)
    source = "barrels"
    red_ml = green_ml = blue_ml = dark_ml = 0

    for barrel in barrels_delivered:
        ml_added = barrel.ml_per_barrel * barrel.quantity
        red_ml += barrel.potion_type[0] * ml_added
        green_ml += barrel.potion_type[1] * ml_added
        blue_ml += barrel.potion_type[2] * ml_added
        dark_ml += barrel.potion_type[3] * ml_added

    response_data = {
        "status": "ok",
        "gold_paid": delivery.gold_paid,
        "ml_added": {
            "red": red_ml,
            "green": green_ml,
            "blue": blue_ml,
            "dark": dark_ml
        }
    }

    with db.engine.begin() as connection:
        existing = connection.execute(
            sqlalchemy.text("SELECT response FROM requests WHERE order_id = :order_id AND source = :source"),
            {"order_id": order_id, "source": source}
        ).fetchone()

        if existing:
            return json.loads(existing.response)

        current_gold = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'gold'")
        ).scalar_one()

        if current_gold < delivery.gold_paid:
            raise HTTPException(status_code=400, detail="Not enough gold to pay for barrels")

        tx_id = connection.execute(
            sqlalchemy.text("""
                INSERT INTO transactions (type, description)
                VALUES ('delivery', 'Barrel delivery')
                RETURNING id
            """)
        ).scalar_one()

        for resource, amount in [
            ("gold", -delivery.gold_paid),
            ("red_ml", int(red_ml)),
            ("green_ml", int(green_ml)),
            ("blue_ml", int(blue_ml)),
            ("dark_ml", int(dark_ml)),
        ]:
            if amount != 0:
                connection.execute(
                    sqlalchemy.text("""
                        INSERT INTO entries (transaction_id, resource, amount)
                        VALUES (:tx_id, :resource, :amount)
                    """),
                    {"tx_id": tx_id, "resource": resource, "amount": amount}
                )

        connection.execute(
            sqlalchemy.text("""
                INSERT INTO requests (order_id, source, response)
                VALUES (:order_id, :source, :response)
            """),
            {
                "order_id": order_id,
                "source": source,
                "response": json.dumps(response_data)
            }
        )


    return response_data



def create_barrel_plan(
    gold: int,
    max_barrel_capacity: int,
    current_red_ml: int,
    current_green_ml: int,
    current_blue_ml: int,
    current_dark_ml: int,
    wholesale_catalog: List[Barrel],
) -> List[BarrelOrder]:
    import math
    from collections import defaultdict

    plan: List[BarrelOrder] = []
    remaining_gold = gold

    target_per_color = max_barrel_capacity // 4
    current_ml = [current_red_ml, current_green_ml, current_blue_ml, current_dark_ml]

    while True:
        # compute how much is needed per color
        needed_ml = [max(0, target_per_color - amt) for amt in current_ml]

        # stop if nothing is needed
        if all(n == 0 for n in needed_ml):
            break

        def useful_ml(barrel: Barrel) -> float:
            return sum(
                barrel.potion_type[i] * barrel.ml_per_barrel if needed_ml[i] > 0 else 0
                for i in range(4)
            )

        # only barrels with > 3 ml/g and needs refill
        useful_barrels = []
        for b in wholesale_catalog:
            if b.price <= 0 or b.quantity <= 0 or b.price > remaining_gold:
                continue

            u_ml = useful_ml(b)
            if u_ml <= 0 or (u_ml / b.price) < 3:
                continue

            ml_per_color = [b.potion_type[i] * b.ml_per_barrel for i in range(4)]

            # filter out if it would overflow
            would_overflow = False
            for i in range(4):
                if ml_per_color[i] > 0 and current_ml[i] + ml_per_color[i] > target_per_color:
                    would_overflow = True
                    break

            if not would_overflow:
                useful_barrels.append(b)

        if not useful_barrels:
            break

        # find which color is most lacking
        most_needed_index = needed_ml.index(max(needed_ml))

        # prioritize barrels that help that color
        prioritized_barrels = [b for b in useful_barrels if b.potion_type[most_needed_index] > 0]
        if not prioritized_barrels:
            prioritized_barrels = useful_barrels

        # sort by how useful per price
        prioritized_barrels.sort(key=lambda b: b.price / useful_ml(b))
        best_ratio = prioritized_barrels[0].price / useful_ml(prioritized_barrels[0])

        # find all best
        equally_best = [b for b in prioritized_barrels if abs((b.price / useful_ml(b)) - best_ratio) < 1e-6]

        bought = False
        for barrel in equally_best:
            if barrel.price > remaining_gold or barrel.quantity <= 0:
                continue

            ml_per_color = [barrel.potion_type[i] * barrel.ml_per_barrel for i in range(4)]

            # buy 1
            plan.append(BarrelOrder(sku=barrel.sku, quantity=1))
            remaining_gold -= barrel.price
            barrel.quantity -= 1
            for i in range(4):
                current_ml[i] += ml_per_color[i]
            bought = True

        if not bought:
            break

    # compress repeated SKUs into 1
    compressed = defaultdict(int)
    for order in plan:
        compressed[order.sku] += order.quantity
    return [BarrelOrder(sku=sku, quantity=qty) for sku, qty in compressed.items()]





@router.post("/plan", response_model=List[BarrelOrder])
def get_wholesale_purchase_plan(wholesale_catalog: List[Barrel]):
    """
    Gets the plan for purchasing wholesale barrels. The call passes in a catalog of available barrels
    and the shop returns back which barrels they'd like to purchase and how many.
    """
    print(f"barrel catalog: {wholesale_catalog}")


    with db.engine.begin() as connection:
        gold = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'gold'")
        ).scalar_one()

        red_ml = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'red_ml'")
        ).scalar_one()

        green_ml = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'green_ml'")
        ).scalar_one()

        blue_ml = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'blue_ml'")
        ).scalar_one()

        dark_ml = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(amount), 0) FROM entries WHERE resource = 'dark_ml'")
        ).scalar_one()

        ml_capacity = connection.execute(
            sqlalchemy.text("SELECT ml_capacity FROM global_inventory")
        ).scalar_one()

    return create_barrel_plan(
        gold=gold,
        max_barrel_capacity=10000 * ml_capacity,
        current_red_ml=red_ml,
        current_green_ml=green_ml,
        current_blue_ml=blue_ml,
        current_dark_ml=dark_ml,
        wholesale_catalog=wholesale_catalog,
    )