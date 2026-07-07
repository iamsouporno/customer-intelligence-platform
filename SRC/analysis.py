"""
analysis.py
-----------
Business-metric calculations on top of the feature-engineered tables from
feature_engineering.py. Every function here returns data (DataFrames,
dicts, Series) -- charting lives in visualization.py, not here, so these
functions are independently testable and reusable outside a notebook.
"""

import pandas as pd


def calculate_kpis(order_df):
    """
    Calculate the headline Executive KPI Dashboard metrics from the
    order-level analytical base table.

    Returns
    -------
    dict
        Flat dict of KPI name -> value, suitable for direct display or
        for a visualization.plot_kpi_dashboard() call.
    """
    total_revenue = order_df["order_total_value"].sum()
    total_orders = order_df["order_id"].nunique()
    total_customers = order_df["customer_unique_id"].nunique()
    aov = order_df["order_total_value"].mean()

    repeat_customers = order_df.groupby("customer_unique_id")["order_id"].nunique()
    repeat_rate = (repeat_customers > 1).mean() * 100

    avg_delivery_days = order_df["delivery_days"].mean()
    avg_review_score = order_df["review_score"].mean()

    monthly_revenue = order_df.groupby("order_purchase_month")["order_total_value"].sum().sort_index()
    # Trim partial first/last calendar months so growth isn't measured
    # against a near-empty month.
    full_months = monthly_revenue.iloc[1:-1] if len(monthly_revenue) > 2 else monthly_revenue
    mom_growth = full_months.pct_change().iloc[-1] * 100 if len(full_months) > 1 else float("nan")

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "average_order_value": aov,
        "repeat_purchase_rate_pct": repeat_rate,
        "average_delivery_days": avg_delivery_days,
        "average_review_score": avg_review_score,
        "latest_month_revenue_growth_pct": mom_growth,
    }


def calculate_top_category(item_df):
    """Return (category_name, revenue) for the single highest-revenue product category."""
    cat_revenue = item_df.groupby("product_category_name_english")["price"].sum()
    top_cat = cat_revenue.idxmax()
    return top_cat, cat_revenue.max()


def calculate_top_seller(item_df):
    """Return (seller_id, revenue) for the single highest-revenue seller."""
    seller_revenue = item_df.groupby("seller_id")["price"].sum()
    top_seller = seller_revenue.idxmax()
    return top_seller, seller_revenue.max()


def analyze_monthly_revenue(order_df, trim_partial_months=True):
    """
    Return monthly revenue as a Series indexed by Period('M'), optionally
    trimming the first/last calendar month (usually partial).
    """
    monthly = order_df.groupby("order_purchase_month")["order_total_value"].sum().sort_index()
    if trim_partial_months and len(monthly) > 2:
        monthly = monthly.iloc[1:-1]
    return monthly


def analyze_customer_value(customer_df):
    """
    Segment customers into simple value tiers based on order_count, used
    by the Customer Analytics section (distinct from the more granular
    RFM segmentation in `calculate_rfm`).
    """
    df = customer_df.copy()
    n_customers = len(df)
    repeat_customers = int(df["is_repeat_customer"].sum())
    repeat_rate = repeat_customers / n_customers * 100

    order_count_dist = df["order_count"].value_counts().sort_index()

    return {
        "n_customers": n_customers,
        "repeat_customers": repeat_customers,
        "repeat_rate_pct": repeat_rate,
        "order_count_distribution": order_count_dist,
    }


def analyze_category_performance(item_df, top_n=10):
    """
    Return the top N product categories by revenue, with order count and
    average item price, used to answer "which categories generate the
    highest revenue?"
    """
    summary = item_df.groupby("product_category_name_english").agg(
        revenue=("price", "sum"),
        orders=("order_id", "nunique"),
        avg_item_price=("price", "mean"),
    ).sort_values("revenue", ascending=False)
    summary["revenue_share_pct"] = summary["revenue"] / summary["revenue"].sum() * 100
    return summary.head(top_n)


def analyze_seller_performance(item_df, order_df, review_df):
    """
    Return a seller-level performance table: revenue, order count,
    average delivery delay, and average review score, used to identify
    both top performers and consistent underperformers.

    Parameters
    ----------
    item_df : DataFrame with seller_id, order_id, price (from get_product_catalog)
    order_df : feature-engineered order-level table (has is_late, delivery_delay_days)
    review_df : order-level table with review_score (order_df itself works)
    """
    seller_revenue = item_df.groupby("seller_id").agg(
        revenue=("price", "sum"),
        orders=("order_id", "nunique"),
    ).sort_values("revenue", ascending=False)

    order_seller = item_df[["order_id", "seller_id"]].drop_duplicates()
    order_seller = order_seller.merge(
        order_df[["order_id", "is_late", "review_score"]], on="order_id", how="left"
    )
    seller_quality = order_seller.groupby("seller_id").agg(
        late_rate_pct=("is_late", lambda s: s.mean() * 100),
        avg_review_score=("review_score", "mean"),
    )

    seller_summary = seller_revenue.join(seller_quality, how="left")
    seller_summary["revenue_share_pct"] = (
        seller_summary["revenue"] / seller_summary["revenue"].sum() * 100
    )
    return seller_summary


def identify_underperforming_sellers(seller_summary, min_orders=10,
                                      late_rate_threshold=15.0, review_threshold=3.5):
    """
    Flag sellers that clear a minimum order volume (so a single bad
    order doesn't distort the picture) but have a late-delivery rate
    above `late_rate_threshold` OR an average review score below
    `review_threshold`.

    This directly answers "which sellers consistently underperform?" --
    consistency is enforced via the min_orders floor.
    """
    eligible = seller_summary[seller_summary["orders"] >= min_orders].copy()
    underperformers = eligible[
        (eligible["late_rate_pct"] > late_rate_threshold)
        | (eligible["avg_review_score"] < review_threshold)
    ].sort_values("late_rate_pct", ascending=False)
    return underperformers


def analyze_delivery_performance(order_df):
    """
    Return delivery-performance summary stats: average delivery time,
    late-delivery rate, average delay when late, and late rate by state.
    """
    late_rate = order_df["is_late"].mean() * 100
    avg_days = order_df["delivery_days"].mean()
    avg_delay_when_late = order_df.loc[order_df["is_late"], "delivery_delay_days"].mean()

    state_late_rate = (
        order_df.groupby("customer_state")["is_late"].mean().mul(100).sort_values(ascending=False)
    )

    return {
        "late_rate_pct": late_rate,
        "avg_delivery_days": avg_days,
        "avg_delay_when_late_days": avg_delay_when_late,
        "late_rate_by_state_pct": state_late_rate,
    }


def analyze_delivery_satisfaction_link(order_df):
    """Return average review score split by on-time vs. late delivery."""
    return order_df.groupby("is_late")["review_score"].mean()


def analyze_payment_behavior(payments_df, order_df):
    """
    Return payment-method mix (share of orders), average order value by
    method, and average installments by method.
    """
    primary_payment = (
        payments_df.sort_values("payment_value", ascending=False)
        .drop_duplicates(subset="order_id")[["order_id", "payment_type"]]
    )
    order_pay = order_df.merge(primary_payment, on="order_id", how="left")

    payment_mix = order_pay["payment_type"].value_counts(normalize=True) * 100
    aov_by_payment = order_pay.groupby("payment_type")["order_total_value"].mean().sort_values(ascending=False)
    installments_by_type = payments_df.groupby("payment_type")["payment_installments"].mean()

    return {
        "payment_mix_pct": payment_mix,
        "aov_by_payment_type": aov_by_payment,
        "avg_installments_by_type": installments_by_type,
    }


def analyze_geographic_performance(order_df, top_n=10):
    """Return revenue and order count by customer state, ranked descending."""
    state_summary = order_df.groupby("customer_state").agg(
        revenue=("order_total_value", "sum"),
        orders=("order_id", "nunique"),
    ).sort_values("revenue", ascending=False)
    state_summary["revenue_share_pct"] = state_summary["revenue"] / state_summary["revenue"].sum() * 100
    return state_summary.head(top_n)


def calculate_rfm(order_df, snapshot_date=None):
    """
    Calculate Recency, Frequency, Monetary values per customer, plus a
    business-tiered `segment` label.

    Design note: this dataset has a 97% one-time-purchase rate (see
    Customer Analytics), which makes a mechanical 5x5x5 RFM quintile
    score misleading -- most customers tie on Frequency. Instead of
    forcing that textbook score, segments here are built primarily on
    Recency and Monetary value, with Frequency used only to carve out
    genuine repeat buyers as their own top tier. This is a more honest
    read of this specific dataset than a standard RFM score would be.

    Returns
    -------
    pd.DataFrame with columns: customer_unique_id, recency, frequency,
    monetary, segment
    """
    if snapshot_date is None:
        snapshot_date = order_df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)

    rfm = order_df.groupby("customer_unique_id").agg(
        recency=("order_purchase_timestamp", lambda x: (snapshot_date - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("order_total_value", "sum"),
    ).reset_index()

    monetary_p75 = rfm["monetary"].quantile(0.75)
    recency_median = rfm["recency"].median()

    def _segment(row):
        if row["frequency"] > 1:
            return "Repeat Buyer"
        if row["monetary"] >= monetary_p75 and row["recency"] <= recency_median:
            return "Recent High-Value (one-time)"
        if row["monetary"] >= monetary_p75 and row["recency"] > recency_median:
            return "At-Risk High-Value (one-time)"
        return "Standard"

    rfm["segment"] = rfm.apply(_segment, axis=1)
    return rfm


def summarize_rfm_segments(rfm_df):
    """Return revenue and customer-count summary by RFM segment, ranked by revenue."""
    summary = rfm_df.groupby("segment").agg(
        customers=("customer_unique_id", "count"),
        avg_monetary=("monetary", "mean"),
        total_monetary=("monetary", "sum"),
    ).sort_values("total_monetary", ascending=False)
    summary["revenue_share_pct"] = summary["total_monetary"] / summary["total_monetary"].sum() * 100
    return summary


def predict_repeat_likelihood_factors(customer_df):
    """
    Return a simple, transparent comparison of first-order characteristics
    between customers who did and did not go on to place a second order --
    a lightweight, descriptive stand-in for "which customers are likely to
    become repeat buyers?" that is defensible without a full predictive
    model (see Conclusion for why a formal model is out of scope here).
    """
    comparison = customer_df.groupby("is_repeat_customer").agg(
        avg_first_order_value=("avg_order_value", "mean"),
        avg_review_score=("avg_review_score", "mean"),
        n_customers=("customer_unique_id", "count"),
    )
    return comparison
