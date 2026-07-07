-- ============================================================================
-- customer_analysis.sql
-- Business question: Who are the highest-value customers, and how much of
-- the business comes from repeat vs. one-time buyers?
--
-- Reproduces: notebook Section 10 (Customer Analytics) and Section 18
-- (RFM Customer Segmentation) -- see src/analysis.py calculate_rfm() for
-- the Python equivalent and the rationale for the simplified segmentation.
-- Dialect: PostgreSQL (uses DISTINCT ON and PERCENTILE_CONT; for
-- Redshift/Snowflake, replace DISTINCT ON with a ROW_NUMBER() window
-- function filter -- see the comment above the customer_state join below).
-- ============================================================================

-- Note: olist_orders assigns a new customer_id to every order. All
-- customer-level analysis must join through olist_customers to
-- customer_unique_id, the true customer key.

WITH delivered_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_purchase_timestamp
    FROM olist_orders_dataset o
    WHERE o.order_status = 'delivered'
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
        c.customer_unique_id,
        c.customer_state,
        d.order_purchase_timestamp,
        p.order_total_value
    FROM delivered_orders d
    JOIN olist_customers_dataset c ON c.customer_id = d.customer_id
    JOIN order_payments p ON p.order_id = d.order_id
),

-- Recency, Frequency, Monetary per customer.
customer_rfm AS (
    SELECT
        customer_unique_id,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(order_total_value) AS monetary,
        EXTRACT(DAY FROM (
            (SELECT MAX(order_purchase_timestamp) FROM order_base)
            - MAX(order_purchase_timestamp)
        )) AS recency
    FROM order_base
    GROUP BY customer_unique_id
),

-- Quartile cut points computed once, reused for every customer via CROSS JOIN
-- rather than recomputed per row.
thresholds AS (
    SELECT
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY monetary) AS monetary_p75,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY recency)  AS recency_median
    FROM customer_rfm
),

customer_segments AS (
    SELECT
        r.customer_unique_id,
        r.frequency,
        r.monetary,
        r.recency,
        -- Ranking window function: highest-spend customers, ranked overall
        -- and within their own state (useful for regional account management).
        RANK() OVER (ORDER BY r.monetary DESC) AS spend_rank_overall,
        RANK() OVER (PARTITION BY ob.customer_state ORDER BY r.monetary DESC) AS spend_rank_in_state,
        CASE
            WHEN r.frequency > 1 THEN 'Repeat Buyer'
            WHEN r.monetary >= t.monetary_p75 AND r.recency <= t.recency_median
                THEN 'Recent High-Value (one-time)'
            WHEN r.monetary >= t.monetary_p75 AND r.recency > t.recency_median
                THEN 'At-Risk High-Value (one-time)'
            ELSE 'Standard'
        END AS segment
    FROM customer_rfm r
    CROSS JOIN thresholds t
    -- one representative state per customer, for the partitioned rank above
    JOIN (
        SELECT DISTINCT ON (customer_unique_id) customer_unique_id, customer_state
        FROM order_base
    ) ob ON ob.customer_unique_id = r.customer_unique_id
)

-- Final output: highest-value customers overall (business question #1)
SELECT
    customer_unique_id,
    segment,
    frequency,
    monetary,
    recency,
    spend_rank_overall,
    spend_rank_in_state
FROM customer_segments
ORDER BY monetary DESC
LIMIT 100;


-- ----------------------------------------------------------------------------
-- Segment-level rollup (mirrors src/analysis.py summarize_rfm_segments()):
-- how many customers and how much revenue sits in each segment.
-- ----------------------------------------------------------------------------
--
-- SELECT
--     segment,
--     COUNT(*)                                   AS customers,
--     ROUND(AVG(monetary), 2)                    AS avg_monetary,
--     ROUND(SUM(monetary), 2)                    AS total_monetary,
--     ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS revenue_share_pct
-- FROM customer_segments
-- GROUP BY segment
-- HAVING COUNT(*) > 0
-- ORDER BY total_monetary DESC;
