"""
feature_engineering.py
-----------------------
Business features built on top of the cleaned order-level table produced
by `cleaning.clean_data()`. Each feature maps directly to a business
question used later in analysis.py / visualization.py -- nothing here is
speculative.
"""

import pandas as pd


def add_delivery_features(df):
    """
    Add delivery-time and delivery-delay features.

    - delivery_days: purchase -> customer delivery, in days.
    - delivery_delay_days: actual delivery date minus the *estimated*
      delivery date. Positive means late.
    - is_late: boolean flag, used throughout satisfaction analysis.

    Business value: delivery reliability is (Section: Delivery
    Performance) the clearest measurable driver of review score in this
    dataset, so these features feed both operational and satisfaction
    analysis.
    """
    df = df.copy()
    df["delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days
    df["delivery_delay_days"] = (
        df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]
    ).dt.days
    df["is_late"] = df["delivery_delay_days"] > 0
    return df


def add_time_features(df):
    """
    Add calendar features used for seasonality and revenue-trend analysis:
    purchase month (as a Period, for clean monthly grouping), day of week,
    and hour of day.
    """
    df = df.copy()
    df["order_purchase_month"] = df["order_purchase_timestamp"].dt.to_period("M")
    df["order_purchase_dow"] = df["order_purchase_timestamp"].dt.day_name()
    df["order_purchase_hour"] = df["order_purchase_timestamp"].dt.hour
    return df


def add_repeat_customer_features(df):
    """
    Add customer-level repeat-purchase features:

    - customer_order_rank: 1st, 2nd, 3rd... order for this customer
      (uses customer_unique_id, since Olist assigns a new customer_id
      to every order -- see Data Dictionary).
    - is_repeat_customer: True if this customer has ever placed more
      than one order (computed at the customer level, then joined back
      so every row for that customer carries the same flag).

    Business value: distinguishing one-time buyers from repeat buyers is
    the foundation of the retention analysis in Customer Analytics and
    RFM Segmentation.
    """
    df = df.copy()
    df = df.sort_values("order_purchase_timestamp")
    df["customer_order_rank"] = df.groupby("customer_unique_id").cumcount() + 1

    orders_per_customer = df.groupby("customer_unique_id")["order_id"].transform("nunique")
    df["is_repeat_customer"] = orders_per_customer > 1
    return df


def add_review_category(df):
    """
    Bucket the numeric review_score into a 3-level business-readable
    category: Detractor (1-2), Passive (3), Promoter (4-5).

    Business value: a 3-bucket view is easier to report to executives
    than a raw 1-5 average, and mirrors NPS-style customer-experience
    reporting that a Product/Growth team would recognize.
    """
    df = df.copy()

    def _bucket(score):
        if pd.isna(score):
            return "No Review"
        if score <= 2:
            return "Detractor"
        if score == 3:
            return "Passive"
        return "Promoter"

    df["review_category"] = df["review_score"].apply(_bucket)
    return df


def add_customer_tenure(df):
    """
    Add customer_tenure_days: days between a customer's first and most
    recent order. Zero for one-time buyers by definition.

    Business value: tenure is a precondition for any lifetime-value
    conversation -- a customer can't have a "long relationship" without
    tenure, regardless of how much they spent in one order.
    """
    df = df.copy()
    first_last = df.groupby("customer_unique_id")["order_purchase_timestamp"].agg(["min", "max"])
    tenure = (first_last["max"] - first_last["min"]).dt.days
    df["customer_tenure_days"] = df["customer_unique_id"].map(tenure)
    return df


def create_features(df):
    """
    Run the full feature-engineering pipeline on the cleaned order-level
    table from cleaning.clean_data(), in one call.

    This is the single entry point the notebook uses -- individual
    add_* functions above stay available for unit testing or reuse.
    """
    df = add_delivery_features(df)
    df = add_time_features(df)
    df = add_repeat_customer_features(df)
    df = add_review_category(df)
    df = add_customer_tenure(df)
    return df


def build_customer_level_table(df):
    """
    Collapse the order-level table to one row per customer, with the
    aggregate features needed for CLV approximation, RFM, and segment
    analysis:

    - order_count: purchase frequency (lifetime).
    - total_spend: CLV approximation (sum of order_total_value to date --
      an approximation because it has no forward-looking projection, only
      realized spend; stated explicitly rather than implied).
    - avg_order_value: total_spend / order_count.
    - customer_tenure_days, is_repeat_customer: carried from order level.
    - avg_review_score: mean review score across the customer's orders.
    """
    customer_df = df.groupby("customer_unique_id").agg(
        order_count=("order_id", "nunique"),
        total_spend=("order_total_value", "sum"),
        customer_tenure_days=("customer_tenure_days", "first"),
        is_repeat_customer=("is_repeat_customer", "first"),
        avg_review_score=("review_score", "mean"),
        last_purchase_date=("order_purchase_timestamp", "max"),
        customer_state=("customer_state", "first"),
    ).reset_index()

    customer_df["avg_order_value"] = customer_df["total_spend"] / customer_df["order_count"]
    return customer_df
