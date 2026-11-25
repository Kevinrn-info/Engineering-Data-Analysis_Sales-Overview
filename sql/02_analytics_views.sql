-- =============================================================================
-- 02_analytics_views.sql
-- Analytics layer: star schema consumed by Power BI.
--
--   dim_date ─┐
--   dim_customer ─┼── fact_orders        (grain: one order)
--   dim_product ──┼── fact_order_items   (grain: one order line)
--                 └── fact_returns       (grain: one returned order line)
--
-- Business definitions (documented once, reused everywhere):
--   * Cancelled order : status = 'cancelled'  -> never counts as revenue.
--   * Returned order  : status = 'returned'   -> payment fully refunded.
--   * Completed sale  : status IN ('processing','shipped','delivered')
--                       -> the payment is captured; this is NET revenue.
--   * Discounts are allocated to order lines proportionally to line_total.
-- =============================================================================

CREATE SCHEMA analytics;

-- -----------------------------------------------------------------------------
-- dim_date: contiguous calendar covering every date used by the facts
-- -----------------------------------------------------------------------------
CREATE VIEW analytics.dim_date AS
WITH bounds AS (
    SELECT
        LEAST(
            (SELECT MIN(order_ts)::date FROM staging.orders),
            (SELECT MIN(signup_date)  FROM staging.customers)
        ) AS start_date,
        GREATEST(
            (SELECT MAX(order_ts)::date   FROM staging.orders),
            (SELECT MAX(delivered_date)   FROM staging.shipments),
            (SELECT MAX(requested_date)   FROM staging.returns)
        ) AS end_date
)
SELECT
    d::date                                   AS date,
    EXTRACT(YEAR    FROM d)::int              AS year,
    EXTRACT(QUARTER FROM d)::int              AS quarter,
    'Q' || EXTRACT(QUARTER FROM d)::int       AS quarter_label,
    EXTRACT(MONTH   FROM d)::int              AS month_number,
    TO_CHAR(d, 'FMMonth')                     AS month_name,
    TO_CHAR(d, 'Mon')                         AS month_short,
    TO_CHAR(d, 'YYYY-MM')                     AS year_month,
    EXTRACT(ISODOW  FROM d)::int              AS day_of_week,       -- 1 = Monday
    TO_CHAR(d, 'FMDay')                       AS day_name,
    EXTRACT(WEEK    FROM d)::int              AS iso_week,
    EXTRACT(ISODOW  FROM d) IN (6, 7)         AS is_weekend
FROM bounds,
     generate_series(DATE_TRUNC('year', start_date),
                     DATE_TRUNC('year', end_date) + INTERVAL '1 year - 1 day',
                     INTERVAL '1 day') AS d;

-- -----------------------------------------------------------------------------
-- dim_customer: no direct PII (email / phone) is exposed to the BI layer
-- -----------------------------------------------------------------------------
CREATE VIEW analytics.dim_customer AS
WITH first_order AS (
    SELECT customer_id, MIN(order_ts)::date AS first_order_date
    FROM staging.orders
    WHERE status <> 'cancelled'
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.first_name || ' ' || c.last_name                    AS customer_name,
    c.country,
    c.city,
    c.signup_date,
    INITCAP(c.loyalty_tier)                               AS loyalty_tier,
    CASE c.loyalty_tier
        WHEN 'none' THEN 0 WHEN 'silver' THEN 1
        WHEN 'gold' THEN 2 WHEN 'platinum' THEN 3
    END                                                   AS loyalty_tier_rank,
    c.marketing_opt_in,
    (c.phone IS NOT NULL)                                 AS has_phone,
    f.first_order_date,
    TO_CHAR(f.first_order_date, 'YYYY-MM')                AS cohort_month
FROM staging.customers c
LEFT JOIN first_order f USING (customer_id);

-- -----------------------------------------------------------------------------
-- dim_product
-- -----------------------------------------------------------------------------
CREATE VIEW analytics.dim_product AS
SELECT
    p.product_id,
    p.sku,
    p.product_name,
    p.category,
    p.brand,
    p.unit_price                                              AS list_price,
    p.unit_cost,
    p.unit_price - p.unit_cost                                AS unit_margin,
    ROUND((p.unit_price - p.unit_cost) / p.unit_price, 4)     AS margin_pct,
    CASE
        WHEN p.unit_price <  50  THEN '1. < $50'
        WHEN p.unit_price < 150  THEN '2. $50 - $149'
        WHEN p.unit_price < 400  THEN '3. $150 - $399'
        ELSE                          '4. $400+'
    END                                                       AS price_band,
    p.weight_kg,
    p.weight_imputed,
    p.is_active,
    p.created_at
FROM staging.products p;

-- -----------------------------------------------------------------------------
-- fact_orders (grain: order) - order economics, payment and logistics
-- -----------------------------------------------------------------------------
CREATE VIEW analytics.fact_orders AS
WITH lines AS (
    SELECT order_id,
           COUNT(*)        AS line_count,
           SUM(quantity)   AS units
    FROM staging.order_items
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    o.order_ts::date                                          AS order_date,
    o.order_ts,
    EXTRACT(HOUR FROM o.order_ts)::int                        AS order_hour,
    INITCAP(o.status)                                         AS order_status,
    INITCAP(o.channel)                                        AS channel,
    o.subtotal,
    o.discount_amount,
    o.shipping_fee,
    o.tax_amount,
    o.total_amount,
    o.subtotal - o.discount_amount                            AS net_merchandise,
    (o.status = 'cancelled')                                  AS is_cancelled,
    (o.status = 'returned')                                   AS is_returned,
    (o.status IN ('processing', 'shipped', 'delivered'))      AS is_completed_sale,
    (o.discount_amount > 0)                                   AS has_discount,
    l.line_count,
    l.units,
    p.method                                                  AS payment_method,
    p.status                                                  AS payment_status,
    s.carrier,
    s.shipped_date,
    s.delivered_date,
    s.shipped_date   - o.order_ts::date                       AS days_to_ship,
    s.delivered_date - s.shipped_date                         AS days_in_transit,
    s.delivered_date - o.order_ts::date                       AS days_to_deliver
FROM staging.orders o
JOIN lines l              ON l.order_id = o.order_id
LEFT JOIN staging.payments  p ON p.order_id = o.order_id
LEFT JOIN staging.shipments s ON s.order_id = o.order_id;

-- -----------------------------------------------------------------------------
-- fact_order_items (grain: order line) - revenue, cost and margin by product
-- -----------------------------------------------------------------------------
CREATE VIEW analytics.fact_order_items AS
SELECT
    i.order_item_id,
    i.order_id,
    o.customer_id,
    i.product_id,
    o.order_ts::date                                          AS order_date,
    INITCAP(o.status)                                         AS order_status,
    INITCAP(o.channel)                                        AS channel,
    i.quantity,
    i.unit_price,
    i.line_total                                              AS gross_sales,
    ROUND(o.discount_amount * i.line_total / NULLIF(o.subtotal, 0), 2)
                                                              AS discount_allocated,
    i.line_total
      - ROUND(o.discount_amount * i.line_total / NULLIF(o.subtotal, 0), 2)
                                                              AS net_sales,
    i.quantity * p.unit_cost                                  AS cogs,
    i.line_total
      - ROUND(o.discount_amount * i.line_total / NULLIF(o.subtotal, 0), 2)
      - i.quantity * p.unit_cost                              AS gross_profit,
    (o.status IN ('processing', 'shipped', 'delivered'))      AS is_completed_sale,
    (r.return_id IS NOT NULL)                                 AS has_return_request
FROM staging.order_items i
JOIN staging.orders   o ON o.order_id   = i.order_id
JOIN staging.products p ON p.product_id = i.product_id
LEFT JOIN staging.returns r ON r.order_item_id = i.order_item_id;

-- -----------------------------------------------------------------------------
-- fact_returns (grain: returned order line)
-- -----------------------------------------------------------------------------
CREATE VIEW analytics.fact_returns AS
SELECT
    r.return_id,
    r.order_item_id,
    i.order_id,
    o.customer_id,
    i.product_id,
    r.requested_date,
    o.order_ts::date                                          AS order_date,
    r.requested_date - o.order_ts::date                       AS days_to_return,
    INITCAP(REPLACE(r.reason, '_', ' '))                      AS return_reason,
    INITCAP(r.status)                                         AS return_status,
    i.quantity,
    i.line_total                                              AS returned_sales,
    r.refund_amount
FROM staging.returns r
JOIN staging.order_items i ON i.order_item_id = r.order_item_id
JOIN staging.orders      o ON o.order_id      = i.order_id;
