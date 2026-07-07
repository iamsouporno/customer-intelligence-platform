"""
cleaning.py
-----------
Loading and cleaning logic for the Olist e-commerce dataset.

Design note: Olist ships nine separate CSVs (orders, items, payments,
reviews, customers, products, sellers, category translation). Rather than
have the notebook load and clean each one inline, `load_data()` returns a
single dict of raw DataFrames and `clean_data()` returns a single,
analysis-ready order-level table. This mirrors how a real pipeline would
separate "raw ingestion" from "cleaned analytical base".
"""

import pandas as pd

from src.utils import assert_no_nulls

# Columns that represent the order lifecycle and must be parsed as dates.
ORDER_DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def load_data(data_dir="data"):
    """
    Load all raw Olist CSVs into a dict of DataFrames, keyed by table name.

    Parameters
    ----------
    data_dir : str
        Directory containing the Olist CSV files.

    Returns
    -------
    dict[str, pd.DataFrame]
    """
    files = {
        "customers": "olist_customers_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "items": "olist_order_items_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
        "products": "olist_products_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "translation": "product_category_name_translation.csv",
    }
    return {name: pd.read_csv(f"{data_dir}/{filename}") for name, filename in files.items()}


def parse_order_dates(orders_df):
    """Convert all order lifecycle timestamp columns to datetime."""
    df = orders_df.copy()
    for col in ORDER_DATE_COLUMNS:
        df[col] = pd.to_datetime(df[col])
    return df


def get_delivered_orders(orders_df):
    """
    Return only orders that reached 'delivered' status.

    Why: canceled/unavailable orders never generated revenue, and
    shipped/processing/invoiced/created/approved orders are still
    mid-lifecycle. Including them would understate or bias revenue,
    delivery-time, and satisfaction metrics. This is the standard,
    defensible cut used for every downstream metric in this project.
    """
    return orders_df.loc[orders_df["order_status"] == "delivered"].copy()


def build_order_payment_totals(payments_df):
    """Collapse multi-installment / multi-method payments to one total per order."""
    return (
        payments_df.groupby("order_id", as_index=False)["payment_value"]
        .sum()
        .rename(columns={"payment_value": "order_payment_value"})
    )


def build_order_item_summary(items_df):
    """One row per order: item count, product revenue, freight cost."""
    return items_df.groupby("order_id", as_index=False).agg(
        items_count=("order_item_id", "count"),
        product_revenue=("price", "sum"),
        freight_cost=("freight_value", "sum"),
    )


def get_clean_reviews(reviews_df):
    """
    De-duplicate reviews and collapse multiple review cycles per order to
    a single score per order.

    Why: the raw table has 827 duplicate review_ids and 559 orders with
    more than one review cycle. Averaging (rather than taking the first
    or last) avoids arbitrarily privileging either the initial or the
    final review when a customer revised their score.
    """
    deduped = reviews_df.drop_duplicates(subset="review_id")
    return deduped.groupby("order_id", as_index=False)["review_score"].mean()


def remove_invalid_transactions(items_df, payments_df):
    """
    Drop line items or payments with non-positive values, which would
    represent a data error rather than a real transaction.

    In the current Olist export this is a no-op (zero rows match), but
    the check is kept as an explicit guardrail against a future data
    refresh silently introducing bad rows.
    """
    clean_items = items_df.loc[items_df["price"] > 0].copy()
    clean_payments = payments_df.loc[payments_df["payment_value"] >= 0].copy()
    return clean_items, clean_payments


def clean_data(raw_tables):
    """
    Run the full cleaning pipeline on the raw table dict from `load_data()`
    and return a single order-level analytical base table.

    Steps: parse dates -> filter to delivered orders -> deduplicate
    payments/items/reviews to one row per order -> join everything ->
    drop the small number of orders with no matching payment record.

    Returns
    -------
    pd.DataFrame
        One row per delivered order, joined with customer geography,
        payment total, item/freight summary, and review score.
    """
    orders = parse_order_dates(raw_tables["orders"])
    delivered_orders = get_delivered_orders(orders)

    clean_items, clean_payments = remove_invalid_transactions(
        raw_tables["items"], raw_tables["payments"]
    )
    order_payments = build_order_payment_totals(clean_payments)
    order_items_summary = build_order_item_summary(clean_items)
    clean_reviews = get_clean_reviews(raw_tables["reviews"])

    df = delivered_orders.merge(raw_tables["customers"], on="customer_id", how="left")
    df = df.merge(order_payments, on="order_id", how="left")
    df = df.merge(order_items_summary, on="order_id", how="left")
    df = df.merge(clean_reviews, on="order_id", how="left")

    # A handful of delivered orders have no matching payment record at all.
    # Revenue cannot be computed for them, so they are dropped here (not
    # imputed) with the count made explicit for auditability.
    n_before = len(df)
    df = df.dropna(subset=["order_payment_value"]).copy()
    n_dropped = n_before - len(df)
    if n_dropped:
        print(f"clean_data(): dropped {n_dropped} delivered order(s) with no payment record")

    df = df.rename(columns={"order_payment_value": "order_total_value"})

    assert_no_nulls(df, ["order_id", "customer_unique_id", "order_total_value"],
                     context="clean_data() output")

    return df


def get_product_catalog(raw_tables):
    """
    Build a single item-level table joining order items with product,
    category translation, and seller attributes. Used by product and
    seller analytics rather than re-joining these tables in every module.
    """
    item_full = (
        raw_tables["items"]
        .merge(raw_tables["products"], on="product_id", how="left")
        .merge(raw_tables["translation"], on="product_category_name", how="left")
        .merge(raw_tables["sellers"], on="seller_id", how="left")
    )
    return item_full
