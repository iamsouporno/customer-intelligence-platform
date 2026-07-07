-- ============================================================================
-- revenue_analysis.sql
-- Business question: What is the topline revenue trend, and is growth
-- accelerating, stalling, or seasonal?
--
-- Reproduces: notebook Section 17 (Revenue Analysis) -- see
-- src/analysis.py analyze_monthly_revenue() / calculate_kpis() for the
-- Python equivalent.
-- Dialect: PostgreSQL (DATE_TRUNC, window functions). For Redshift /
-- Snowflake the syntax below is portable as-is.
-- ============================================================================

WITH delivered_orders AS (
    SELECT
        order_id,
        customer_id,
        order_purchase_timestamp
    FROM olist_orders_dataset
    WHERE order_status = 'delivered'
),

order_payments AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_total_value
    FROM olist_order_payments_dataset
    GROUP BY order_id
),

order_base AS (
    SELECT
        d.order_id,
        d.order_purchase_timestamp,
        p.order_total_value
    FROM delivered_orders d
    JOIN order_payments p ON p.order_id = d.order_id
),

monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', order_purchase_timestamp) AS order_month,
        SUM(order_total_value)                        AS revenue,
        COUNT(DISTINCT order_id)                       AS orders,
        ROUND(AVG(order_total_value), 2)               AS avg_order_value
    FROM order_base
    GROUP BY 1
),

-- Month-over-month growth via window function (LAG), mirroring
-- monthly_revenue.pct_change() in analysis.calculate_kpis().
monthly_with_growth AS (
    SELECT
        order_month,
        revenue,
        orders,
        avg_order_value,
        LAG(revenue) OVER (ORDER BY order_month)            AS prior_month_revenue,
        ROUND(
            100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
            / NULLIF(LAG(revenue) OVER (ORDER BY order_month), 0),
        2) AS mom_growth_pct,
        -- 3-month rolling average revenue, mirroring the rolling(3).mean()
        -- overlay in visualization.plot_monthly_sales().
        ROUND(
            AVG(revenue) OVER (ORDER BY order_month
                                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),
        2) AS rolling_3month_avg_revenue
    FROM monthly_revenue
)

SELECT *
FROM monthly_with_growth
-- Excludes the first/last calendar month, which are partial in the
-- source data and would distort month-over-month growth (see
-- clean_data() / calculate_kpis() docstring for the same trimming logic).
WHERE order_month NOT IN (
    (SELECT MIN(order_month) FROM monthly_revenue),
    (SELECT MAX(order_month) FROM monthly_revenue)
)
ORDER BY order_month;


-- ----------------------------------------------------------------------------
-- Headline revenue KPIs (mirrors src/analysis.py calculate_kpis()):
-- total revenue, total orders, AOV, median order value.
-- ----------------------------------------------------------------------------
--
-- SELECT
--     SUM(order_total_value)                                       AS total_revenue,
--     COUNT(DISTINCT order_id)                                     AS total_orders,
--     ROUND(AVG(order_total_value), 2)                             AS avg_order_value,
--     ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_total_value), 2)
--                                                                   AS median_order_value
-- FROM order_base;
