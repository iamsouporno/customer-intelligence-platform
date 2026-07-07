"""
utils.py
--------
Shared, low-level helpers used across the analytics package: currency and
percentage formatting for chart axes, and small validation utilities used
by cleaning.py and analysis.py.

Keeping these in one place avoids every module reinventing its own
formatting logic (and getting slightly different rounding / label
conventions in different charts).
"""

import matplotlib.ticker as mticker
import pandas as pd


def currency_fmt(value, _pos=None):
    """
    Format a numeric value as a compact Brazilian Real string for chart
    axes and annotations, e.g. 1_250_000 -> 'R$1.3M', 45_000 -> 'R$45K'.

    Accepts a `_pos` argument so it can be dropped directly into
    matplotlib.ticker.FuncFormatter without a wrapper lambda.
    """
    if abs(value) >= 1_000_000:
        return f"R${value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"R${value / 1_000:,.0f}K"
    return f"R${value:,.0f}"


def currency_formatter():
    """Return a ready-to-use matplotlib formatter for currency axes."""
    return mticker.FuncFormatter(currency_fmt)


def pct_fmt(value, _pos=None):
    """Format a numeric value (already on a 0-100 scale) as '12.3%'."""
    return f"{value:,.1f}%"


def pct_formatter():
    """Return a ready-to-use matplotlib formatter for percentage axes."""
    return mticker.FuncFormatter(pct_fmt)


def safe_divide(numerator, denominator, default=0.0):
    """Divide two numbers (or Series) without raising on a zero denominator."""
    if isinstance(denominator, (pd.Series, pd.DataFrame)):
        return numerator.div(denominator).fillna(default)
    return numerator / denominator if denominator else default


def assert_no_nulls(df, columns, context=""):
    """
    Raise a clear error if any of `columns` contain nulls after a cleaning
    step that was supposed to remove them. Used as a lightweight
    post-condition check rather than silently trusting the cleaning code.
    """
    null_counts = df[columns].isna().sum()
    offending = null_counts[null_counts > 0]
    if not offending.empty:
        raise ValueError(
            f"Unexpected nulls remain{' in ' + context if context else ''}: "
            f"{offending.to_dict()}"
        )


def assert_no_duplicates(df, subset, context=""):
    """Raise a clear error if duplicate rows remain on a key that should be unique."""
    dup_count = df.duplicated(subset=subset).sum()
    if dup_count > 0:
        raise ValueError(
            f"Unexpected duplicates{' in ' + context if context else ''} "
            f"on subset={subset}: {dup_count} rows"
        )


def apply_house_style():
    """
    Apply the consistent visual theme used by every chart in visualization.py.
    Centralizing this means every chart in the notebook shares fonts,
    color palette, and grid style without repeating the setup per chart.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid", font_scale=1.05)
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#444444",
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "font.family": "DejaVu Sans",
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    })


# Shared color palette, imported by visualization.py so every chart uses
# the same brand-consistent colors instead of matplotlib defaults.
PALETTE = {
    "primary": "#2E5EAA",
    "accent": "#E8703A",
    "muted": "#8A9BA8",
    "good": "#3C9F6E",
    "bad": "#C0392B",
}
