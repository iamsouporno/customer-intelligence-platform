"""
Customer Intelligence Platform -- analytics package.

Modules:
    cleaning.py             Raw data loading and cleaning into an analytical base table.
    feature_engineering.py  Business feature construction (delivery delay, tenure, RFM inputs, etc.).
    analysis.py              KPI, segmentation, and business-metric calculations.
    visualization.py         All chart construction (matplotlib figures).
    utils.py                 Shared formatting and validation helpers.

The notebook in notebooks/ is a thin presentation layer that imports from
this package -- it does not contain reusable logic itself.
"""
