"""
visualization.py
-----------------
All charting logic lives here. Every function takes data returned by
analysis.py / feature_engineering.py and returns a matplotlib Figure --
the notebook only calls these functions and displays/saves the result,
it never builds a chart inline.
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

from src.utils import PALETTE, apply_house_style, currency_formatter, currency_fmt

apply_house_style()


def plot_kpi_dashboard(kpis, top_category, top_seller_revenue):
    """
    Render the Executive KPI Dashboard as a grid of KPI cards.

    Parameters
    ----------
    kpis : dict from analysis.calculate_kpis()
    top_category : str, the top category name from analysis.calculate_top_category()
    top_seller_revenue : float, revenue of the top seller
    """
    cards = [
        ("Total Revenue", currency_fmt(kpis["total_revenue"])),
        ("Total Orders", f"{kpis['total_orders']:,}"),
        ("Total Customers", f"{kpis['total_customers']:,}"),
        ("Average Order Value", f"R${kpis['average_order_value']:,.2f}"),
        ("Repeat Purchase Rate", f"{kpis['repeat_purchase_rate_pct']:.1f}%"),
        ("Avg. Delivery Time", f"{kpis['average_delivery_days']:.1f} days"),
        ("Avg. Review Score", f"{kpis['average_review_score']:.2f} / 5"),
        ("Top Category", top_category.replace("_", " ").title()),
    ]

    fig, axes = plt.subplots(2, 4, figsize=(16, 5))
    for ax, (label, value) in zip(axes.flat, cards):
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes,
                                    facecolor="#F4F6F8", edgecolor="#D5DBE0", linewidth=1))
        ax.text(0.5, 0.62, str(value), ha="center", va="center", fontsize=17,
                fontweight="bold", color=PALETTE["primary"], transform=ax.transAxes)
        ax.text(0.5, 0.25, label, ha="center", va="center", fontsize=10.5,
                color="#444444", transform=ax.transAxes)

    fig.suptitle("Executive KPI Dashboard", fontsize=16, fontweight="bold", y=1.03)
    plt.tight_layout()
    return fig


def plot_monthly_sales(monthly_revenue, rolling_window=3):
    """
    Plot the monthly revenue trend with a rolling average overlay.

    Parameters
    ----------
    monthly_revenue : pd.Series indexed by Period('M'), from
        analysis.analyze_monthly_revenue()
    """
    rolling = monthly_revenue.rolling(rolling_window).mean()

    fig, ax = plt.subplots(figsize=(12, 5))
    monthly_revenue.plot(ax=ax, marker="o", markersize=4, color=PALETTE["muted"],
                          linewidth=1.2, label="Monthly revenue")
    rolling.plot(ax=ax, color=PALETTE["primary"], linewidth=2.5,
                 label=f"{rolling_window}-month rolling average")
    ax.set_title("Monthly Revenue Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue")
    ax.yaxis.set_major_formatter(currency_formatter())
    ax.legend(frameon=False)
    sns.despine(ax=ax)
    plt.tight_layout()
    return fig


def plot_customer_segments(order_count_distribution, max_bucket=5):
    """
    Plot a bar chart of customers by number of lifetime orders, from
    analysis.analyze_customer_value()['order_count_distribution'].
    """
    dist = order_count_distribution[order_count_distribution.index <= max_bucket]
    overflow = order_count_distribution[order_count_distribution.index > max_bucket].sum()

    labels = [str(i) for i in dist.index[:-1]] + [f"{max_bucket}+"]
    values = list(dist.values[:-1]) + [dist.values[-1] + overflow]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, values, color=PALETTE["primary"])
    bars[0].set_color(PALETTE["accent"])
    for bar, val in zip(bars, values):
        ax.annotate(f"{val:,}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom", fontsize=9)
    ax.set_title("Customers by Number of Orders Placed")
    ax.set_xlabel("Orders placed (lifetime)")
    ax.set_ylabel("Number of customers")
    ax.set_yscale("log")
    sns.despine(ax=ax)
    plt.tight_layout()
    return fig


def plot_category_revenue(category_summary, top_n=10):
    """
    Horizontal ranked bar chart of top product categories by revenue,
    from analysis.analyze_category_performance().
    """
    top = category_summary.head(top_n).sort_values("revenue")

    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(top.index.str.replace("_", " ").str.title(), top["revenue"], color=PALETTE["primary"])
    bars[-1].set_color(PALETTE["accent"])
    ax.set_title(f"Top {top_n} Product Categories by Revenue")
    ax.set_xlabel("Revenue")
    ax.xaxis.set_major_formatter(currency_formatter())
    for bar, val in zip(bars, top["revenue"]):
        ax.annotate(currency_fmt(val), (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    ha="left", va="center", fontsize=9, xytext=(4, 0), textcoords="offset points")
    sns.despine(ax=ax)
    plt.tight_layout()
    return fig


def plot_seller_concentration(seller_summary):
    """
    Plot a Pareto-style cumulative revenue concentration curve across
    sellers, alongside a horizontal bar of the top 10 sellers by revenue.
    """
    ranked = seller_summary.sort_values("revenue", ascending=False).reset_index()
    ranked["cum_revenue_pct"] = ranked["revenue"].cumsum() / ranked["revenue"].sum() * 100
    ranked["seller_rank_pct"] = (ranked.index + 1) / len(ranked) * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(ranked["seller_rank_pct"], ranked["cum_revenue_pct"], color=PALETTE["primary"], linewidth=2.5)
    axes[0].axhline(80, color=PALETTE["muted"], linestyle="--", linewidth=1)
    axes[0].set_title("Revenue Concentration Across Sellers")
    axes[0].set_xlabel("% of sellers (ranked by revenue)")
    axes[0].set_ylabel("Cumulative % of revenue")
    axes[0].set_xlim(0, 100)
    axes[0].set_ylim(0, 100)
    sns.despine(ax=axes[0])

    top10 = ranked.head(10).sort_values("revenue")
    axes[1].barh([f"Seller {i+1}" for i in range(10)][::-1], top10["revenue"], color=PALETTE["primary"])
    axes[1].set_title("Top 10 Sellers by Revenue")
    axes[1].set_xlabel("Revenue")
    axes[1].xaxis.set_major_formatter(currency_formatter())
    sns.despine(ax=axes[1])

    plt.tight_layout()
    return fig


def plot_delivery_analysis(order_df, state_late_rate, avg_delivery_days, top_n_states=10):
    """
    Plot delivery-time distribution and late-delivery rate by state
    (top N states by order volume), from analysis.analyze_delivery_performance().
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    sns.histplot(order_df["delivery_days"].clip(upper=60), bins=40, color=PALETTE["primary"], ax=axes[0])
    axes[0].axvline(avg_delivery_days, color=PALETTE["accent"], linestyle="--", linewidth=2,
                     label=f"Mean = {avg_delivery_days:.1f} days")
    axes[0].set_title("Distribution of Delivery Time\n(clipped at 60 days for readability)")
    axes[0].set_xlabel("Days from purchase to delivery")
    axes[0].legend(frameon=False)
    sns.despine(ax=axes[0])

    top_states = order_df["customer_state"].value_counts().head(top_n_states).index
    subset = state_late_rate.reindex(top_states).sort_values(ascending=False)
    bars = axes[1].bar(subset.index, subset.values, color=PALETTE["primary"])
    bars[subset.values.argmax()].set_color(PALETTE["bad"])
    axes[1].set_title(f"Late Delivery Rate by State\n(top {top_n_states} states by order volume)")
    axes[1].set_xlabel("Customer state")
    axes[1].set_ylabel("% of orders delivered late")
    sns.despine(ax=axes[1])

    plt.tight_layout()
    return fig


def plot_review_distribution_and_delay_link(order_df, delay_review_link):
    """
    Plot the review-score distribution alongside average review score
    split by on-time vs. late delivery.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    review_counts = order_df["review_score"].value_counts().sort_index()
    bars = axes[0].bar(review_counts.index.astype(int), review_counts.values, color=PALETTE["primary"])
    bars[-1].set_color(PALETTE["good"])
    bars[0].set_color(PALETTE["bad"])
    axes[0].set_title("Review Score Distribution")
    axes[0].set_xlabel("Review score (1-5)")
    axes[0].set_ylabel("Number of orders")
    sns.despine(ax=axes[0])

    labels = ["On-time", "Late"]
    vals = [delay_review_link.loc[False], delay_review_link.loc[True]]
    bars2 = axes[1].bar(labels, vals, color=[PALETTE["good"], PALETTE["bad"]])
    for bar, val in zip(bars2, vals):
        axes[1].annotate(f"{val:.2f}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                          ha="center", va="bottom", fontsize=11, fontweight="bold")
    axes[1].set_title("Average Review Score:\nOn-Time vs. Late Delivery")
    axes[1].set_ylabel("Average review score")
    axes[1].set_ylim(0, 5.5)
    sns.despine(ax=axes[1])

    plt.tight_layout()
    return fig


def plot_geographic_revenue(state_summary, top_n=10):
    """Horizontal ranked bar chart of top states by revenue."""
    top = state_summary.head(top_n).sort_values("revenue")

    fig, ax = plt.subplots(figsize=(9, 6))
    bars = ax.barh(top.index, top["revenue"], color=PALETTE["primary"])
    bars[-1].set_color(PALETTE["accent"])
    ax.set_title(f"Top {top_n} States by Revenue")
    ax.set_xlabel("Revenue")
    ax.xaxis.set_major_formatter(currency_formatter())
    for bar, val in zip(bars, top["revenue"]):
        ax.annotate(currency_fmt(val), (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    ha="left", va="center", fontsize=9, xytext=(4, 0), textcoords="offset points")
    sns.despine(ax=ax)
    plt.tight_layout()
    return fig


def plot_seasonality_heatmap(order_df):
    """Heatmap of order volume by day of week and hour of day."""
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap_data = (
        order_df.groupby(["order_purchase_dow", "order_purchase_hour"])["order_id"]
        .count().unstack(fill_value=0).reindex(dow_order)
    )

    fig, ax = plt.subplots(figsize=(13, 5))
    sns.heatmap(heatmap_data, cmap="Blues", ax=ax, cbar_kws={"label": "Orders"})
    ax.set_title("Order Volume by Day of Week and Hour of Day")
    ax.set_xlabel("Hour of day (24h)")
    ax.set_ylabel("")
    plt.tight_layout()
    return fig


def plot_payment_behavior(payment_mix_pct, aov_by_payment_type):
    """Plot payment method mix and average order value by payment method."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    order = payment_mix_pct.sort_values(ascending=False).index
    axes[0].bar(order, payment_mix_pct.loc[order], color=PALETTE["primary"])
    axes[0].set_title("Payment Method Mix")
    axes[0].set_ylabel("% of orders")
    sns.despine(ax=axes[0])

    axes[1].bar(aov_by_payment_type.index, aov_by_payment_type.values, color=PALETTE["primary"])
    axes[1].set_title("Average Order Value by Payment Method")
    axes[1].set_ylabel("Average order value")
    axes[1].yaxis.set_major_formatter(currency_formatter())
    sns.despine(ax=axes[1])

    plt.tight_layout()
    return fig


def plot_rfm_segments(segment_summary):
    """Horizontal bar chart of total revenue by RFM/value segment."""
    seg_sorted = segment_summary.sort_values("total_monetary")
    colors = [PALETTE["accent"] if s == "Repeat Buyer" else PALETTE["primary"] for s in seg_sorted.index]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(seg_sorted.index, seg_sorted["total_monetary"], color=colors)
    ax.set_title("Total Revenue by Customer Value Segment")
    ax.set_xlabel("Total revenue")
    ax.xaxis.set_major_formatter(currency_formatter())
    for bar, (n, pct) in zip(bars, zip(seg_sorted["customers"], seg_sorted["revenue_share_pct"])):
        ax.annotate(f"{n:,} customers - {pct:.0f}% of revenue",
                    (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    ha="left", va="center", fontsize=9, xytext=(4, 0), textcoords="offset points")
    sns.despine(ax=ax)
    plt.tight_layout()
    return fig


def plot_rfm_scatter(rfm_df):
    """
    Scatter plot of Recency vs. Monetary value, colored by segment --
    a visual complement to the bar chart that shows within-segment spread
    rather than just segment totals.
    """
    fig, ax = plt.subplots(figsize=(9, 6))
    segments = rfm_df["segment"].unique()
    colors = sns.color_palette("Set2", len(segments))
    for seg, color in zip(segments, colors):
        subset = rfm_df[rfm_df["segment"] == seg]
        ax.scatter(subset["recency"], subset["monetary"], s=14, alpha=0.5, label=seg, color=color)
    ax.set_title("Customer Value Segments: Recency vs. Monetary Value")
    ax.set_xlabel("Recency (days since last purchase)")
    ax.set_ylabel("Monetary value (total spend)")
    ax.yaxis.set_major_formatter(currency_formatter())
    ax.legend(frameon=False, markerscale=2)
    sns.despine(ax=ax)
    plt.tight_layout()
    return fig
