-- ============================================================================
-- seller_analysis.sql
-- Business questions: Which sellers drive the most revenue, and which
-- sellers consistently underperform on delivery reliability or customer
-- satisfaction?
--
-- Reproduces: notebook Section 12 (Seller Analytics) -- see
-- src/analysis.py analyze_seller_performance() and
-- identify_underperforming_sellers() for the Python equivalent.
-- Dialect: PostgreSQL.
-- ============================================================================

WITH delivered_orders AS (
    SELECT order_id, order_delivered_customer_date, order_estimated_delivery_date
    FROM olist_orders_dataset
    WHERE order_status = 'delivered'
),

order_reviews AS (
    -- De-duplicate review_id and collapse multiple review cycles per
    -- order to a single average score (mirrors cleaning.get_clean_reviews()).
    SELECT
        order_id,
        AVG(review_score) AS review_score
    FROM (
        SELECT DISTINCT ON (review_id) review_id, order_id, review_score
        FROM olist_order_reviews_dataset
    ) deduped
    GROUP BY order_id
),

order_delivery AS (
    SELECT
        order_id,
        (order_delivered_customer_date > order_estimated_delivery_date) AS is_late
    FROM delivered_orders
    WHERE order_delivered_customer_date IS NOT NULL
),

seller_items AS (
    SELECT
        oi.seller_id,
        oi.order_id,
        oi.price
    FROM olist_order_items_dataset oi
    JOIN delivered_orders d ON d.order_id = oi.order_id
),

seller_revenue AS (
    SELECT
        seller_id,
        SUM(price)                   AS revenue,
        COUNT(DISTINCT order_id)     AS orders
    FROM seller_items
    GROUP BY seller_id
),

seller_quality AS (
    SELECT
        si.seller_id,
        ROUND(100.0 * AVG(CASE WHEN dd.is_late THEN 1 ELSE 0 END), 2) AS late_rate_pct,
        ROUND(AVG(orr.review_score), 2)                               AS avg_review_score
    FROM (SELECT DISTINCT seller_id, order_id FROM seller_items) si
    LEFT JOIN order_delivery dd ON dd.order_id = si.order_id
    LEFT JOIN order_reviews orr ON orr.order_id = si.order_id
    GROUP BY si.seller_id
),

seller_summary AS (
    SELECT
        r.seller_id,
        r.revenue,
        r.orders,
        q.late_rate_pct,
        q.avg_review_score,
        ROUND(100.0 * r.revenue / SUM(r.revenue) OVER (), 2) AS revenue_share_pct,
        RANK() OVER (ORDER BY r.revenue DESC)                AS revenue_rank
    FROM seller_revenue r
    JOIN seller_quality q ON q.seller_id = r.seller_id
)

-- Top 20 sellers by revenue (business question: top-performer view)
SELECT *
FROM seller_summary
ORDER BY revenue DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- Underperforming sellers: at least 10 orders (so a single bad order
-- doesn't distort the picture), with either a late-delivery rate above
-- 15% or an average review score below 3.5. Mirrors
-- identify_underperforming_sellers() in src/analysis.py.
-- ----------------------------------------------------------------------------
--
-- SELECT *
-- FROM seller_summary
-- WHERE orders >= 10
--   AND (late_rate_pct > 15.0 OR avg_review_score < 3.5)
-- ORDER BY late_rate_pct DESC;
