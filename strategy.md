
Step 1: Strategy

Idea 1: Sell the Potions That Make the Most Gold and Have Good Ratings
I want to focus on potions that make the most profit and also score high in the competition.

The ratings are based on value (how cheap it is compared to other students), quality (how close the color is to what the customer wanted), and reliability (how often it sells).

If a potion is both profitable and rated well, that’s a sign it’s working , so I’ll brew more of those.

Idea 2: Brew What People Actually Buy
Even though potions don’t expire, brewing the wrong ones is a waste of time and ingredients.

If I can tell what’s selling the most, I can stop guessing and just focus on making those.

That way I’m not filling the shop with stuff nobody wants.

Idea 3: Match Potions to the Time of Day
Some potions seem to sell better at certain times ,like dark potions selling more at night.

I want to track which potions sell during which hours and show those more in the shop at those times.

This way I’m giving customers what they’re likely to buy when they come and visit my shop.






Step 2: Tests

Idea 1: Sell the Best Potions
I’ll track potion costs, how much gold they bring in, and their ratings.

I’ll combine that into a single score using profit × (average rating / 5).

Then I’ll brew more of the top scoring potions and compare gold and ratings before and after.

Idea 2: Brew the Right Potions
I’ll track how many of each potion I brew and how many are sold.

If a potion sells slowly, I’ll brew less of it.

If one sells fast, I’ll start making more of that one.

Idea 3: Sell Based on the Time of Day
I’ll track potion sales by hour and see what sells best at different times.

If certain potions sell better at night or in the morning, I’ll adjust the catalog to match that.

I’ll compare sales before and after changing the display.






Step 3: What I’ll Track

Gold earned from each potion.

Value, quality, and reliability ratings.

How many of each potion is brewed and how many are sold.

What time of day potions are sold.

When customers are most active and what they’re buying at those times.






Step 4: SQL Queries to Help


Potions That Make the Most Gold and Score Well


SELECT
    p.name,
    AVG(i.price_per_ml * p.ml_used) AS cost,
    s.selling_price,
    (s.selling_price - AVG(i.price_per_ml * p.ml_used)) AS profit,
    r.value + r.quality + r.reliability + r.recognition AS rating_score,
    (s.selling_price - AVG(i.price_per_ml * p.ml_used)) * 
        ((r.value + r.quality + r.reliability + r.recognition) / 20.0) AS adjusted_score
FROM
    sales s
JOIN potions p ON s.potion_sku = p.sku
JOIN ingredients i ON p.ingredient_id = i.id
JOIN ratings r ON p.sku = r.potion_sku
GROUP BY p.name, s.selling_price, r.value, r.quality, r.reliability, r.recognition
ORDER BY adjusted_score DESC;


Brewing vs. Sales Ratio

SELECT
    p.sku,
    COUNT(*) FILTER (WHERE e.type = 'brewed') AS brewed,
    COUNT(*) FILTER (WHERE e.type = 'sold') AS sold,
    ROUND(
        COUNT(*) FILTER (WHERE e.type = 'sold')::decimal / 
        NULLIF(COUNT(*) FILTER (WHERE e.type = 'brewed'), 0), 2
    ) AS brew_to_sale_ratio
FROM
    entries e
JOIN potions p ON e.potion_sku = p.sku
GROUP BY p.sku
ORDER BY brew_to_sale_ratio DESC;




Potion Sales by Hour

SELECT
    EXTRACT(HOUR FROM s.timestamp) AS hour,
    COUNT(*) AS potions_sold,
    SUM(s.gold_earned) AS revenue
FROM
    sales s
GROUP BY hour
ORDER BY hour;



What Potions Sell Best at What Time

SELECT
    s.potion_sku,
    EXTRACT(HOUR FROM s.timestamp) AS hour,
    COUNT(DISTINCT s.customer_id) AS buyers
FROM
    sales s
GROUP BY s.potion_sku, hour
ORDER BY buyers DESC;
