-- ============================================================================
-- delivery_analysis.sql
-- Business question: How reliable is delivery, where does it break down
-- geographically, and how much does a late delivery affect review score?
--
-- Reproduces: notebook Section 13 (Delivery Performance) -- see
-- src/analysis.py analyze_delivery_performance() and
-- analyze_delivery_satisfaction_link() for the Python equivalent.
-- Dialect: PostgreSQL.
-- ============================================================================

WITH delivered_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_purchase_timestamp))
            AS delivery_days,
        EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))
            AS delivery_delay_days,
        (o.order_delivered_customer_date > o.order_estimated_delivery_date) AS is_late
    FROM olist_orders_dataset o
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
),

order_geo AS (
    SELECT
        d.*,
        c.customer_state
    FROM delivered_orders d
    JOIN olist_customers_dataset c ON c.customer_id = d.customer_id
),

order_reviews AS (
    SELECT
        order_id,
        AVG(review_score) AS review_score
    FROM (
        SELECT DISTINCT ON (review_id) review_id, order_id, review_score
        FROM olist_order_reviews_dataset
    ) deduped
    GROUP BY order_id
)

-- 1. Headline delivery KPIs
SELECT
    ROUND(AVG(delivery_days), 1)                                   AS avg_delivery_days,
    ROUND(100.0 * AVG(CASE WHEN is_late THEN 1 ELSE 0 END), 2)     AS late_rate_pct,
    ROUND(AVG(delivery_delay_days) FILTER (WHERE is_late), 1)      AS avg_delay_when_late_days
FROM order_geo;


-- ----------------------------------------------------------------------------
-- 2. Late-delivery rate by state, ranked descending (mirrors
-- analyze_delivery_performance()['late_rate_by_state_pct']).
-- ----------------------------------------------------------------------------
--
-- SELECT
--     customer_state,
--     COUNT(*)                                                   AS orders,
--     ROUND(100.0 * AVG(CASE WHEN is_late THEN 1 ELSE 0 END), 2) AS late_rate_pct
-- FROM order_geo
-- GROUP BY customer_state
-- HAVING COUNT(*) >= 30   -- drop states with too few orders to be reliable
-- ORDER BY late_rate_pct DESC;


-- ----------------------------------------------------------------------------
-- 3. The core satisfaction-driver finding: average review score, on-time
-- vs. late delivery (mirrors analyze_delivery_satisfaction_link()).
-- ----------------------------------------------------------------------------
--
-- SELECT
--     og.is_late,
--     COUNT(*)                          AS orders,
--     ROUND(AVG(orr.review_score), 2)   AS avg_review_score
-- FROM order_geo og
-- JOIN order_reviews orr ON orr.order_id = og.order_id
-- GROUP BY og.is_late;
