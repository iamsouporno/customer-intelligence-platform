-- ============================================================================
-- payment_analysis.sql
-- Business question: Which payment methods are most common, and does
-- payment method relate to order size?
--
-- Reproduces: notebook Section 14 (Payment Analysis) -- see
-- src/analysis.py analyze_payment_behavior() for the Python equivalent.
-- Dialect: PostgreSQL.
-- ============================================================================

WITH delivered_orders AS (
    SELECT order_id
    FROM olist_orders_dataset
    WHERE order_status = 'delivered'
),

order_payment_totals AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_total_value
    FROM olist_order_payments_dataset
    GROUP BY order_id
),

-- A single order can have more than one payment row (e.g. voucher +
-- credit card). The "primary" payment method is the one with the
-- largest payment_value on that order -- mirrors the
-- sort_values(...).drop_duplicates() logic in analyze_payment_behavior().
primary_payment_method AS (
    SELECT DISTINCT ON (order_id)
        order_id,
        payment_type,
        payment_installments
    FROM olist_order_payments_dataset
    ORDER BY order_id, payment_value DESC
),

order_base AS (
    SELECT
        d.order_id,
        t.order_total_value,
        p.payment_type,
        p.payment_installments
    FROM delivered_orders d
    JOIN order_payment_totals t ON t.order_id = d.order_id
    JOIN primary_payment_method p ON p.order_id = d.order_id
)

-- 1. Payment method mix and average order value by method
SELECT
    payment_type,
    COUNT(*)                                                  AS orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)        AS pct_of_orders,
    ROUND(AVG(order_total_value), 2)                          AS avg_order_value,
    ROUND(AVG(payment_installments), 2)                       AS avg_installments
FROM order_base
GROUP BY payment_type
ORDER BY orders DESC;


-- ----------------------------------------------------------------------------
-- 2. Installment behavior for credit-card orders specifically, bucketed --
-- useful to see whether high-installment orders skew toward higher AOV
-- (referenced in the notebook's Payment Analysis recommendation).
-- ----------------------------------------------------------------------------
--
-- SELECT
--     CASE
--         WHEN payment_installments = 1 THEN '1 (no financing)'
--         WHEN payment_installments BETWEEN 2 AND 4 THEN '2-4'
--         WHEN payment_installments BETWEEN 5 AND 8 THEN '5-8'
--         ELSE '9+'
--     END AS installment_bucket,
--     COUNT(*)                        AS orders,
--     ROUND(AVG(order_total_value), 2) AS avg_order_value
-- FROM order_base
-- WHERE payment_type = 'credit_card'
-- GROUP BY 1
-- ORDER BY MIN(payment_installments);
