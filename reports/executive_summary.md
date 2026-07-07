# Executive Summary — Customer Intelligence Platform

**Dataset:** Olist Brazilian E-Commerce (Sep 2016 – Aug 2018) &nbsp;|&nbsp; **Base:** 96,477 delivered orders, 93,357 unique customers

---

## Headline

Olist's growth on this dataset has been driven almost entirely by new-customer acquisition, not retention — only **3.0%** of customers ever place a second order. At the same time, delivery reliability is a measurable driver of satisfaction: late orders score roughly **two points lower** on average than on-time orders (2.26/5 vs. 4.28/5). Revenue is also geographically and seller-concentrated, which is normal for a marketplace but worth actively managing.

![Executive KPI Dashboard](../images/executive_dashboard.png)

## Top 5 Findings

1. **Retention is the single biggest structural gap.** 90,556 of 93,357 customers (97%) never return after their first order. Marketing and CAC-payback math built on a higher assumed repeat rate will overstate blended unit economics.
2. **Delivery reliability drives satisfaction, not just operations.** 6.8% of orders arrive late; late orders average 2.26/5 vs. 4.28/5 on time — the clearest single lever on review score in the dataset.
3. **Revenue is concentrated in the Southeast.** São Paulo, Rio de Janeiro, and Minas Gerais together generate 62.5% of revenue, and late-delivery rates are measurably worse outside this corridor.
4. **The seller base is a healthy long tail.** The top 10 of 2,970 sellers generate only 13.3% of revenue — low single-seller concentration risk — but 137 sellers with ≥10 orders combine high late rates with low review scores and are flagged as consistent underperformers.
5. **A small, high-value one-time-buyer segment is the best retention-pilot target.** Customers who spent well above median in a single order but never returned are a smaller, higher-propensity audience than the full 90K-customer win-back problem.

## Prioritized Recommendations

| # | Action | Why |
|---|---|---|
| 1 | Pilot a win-back offer targeted at high-value, one-time buyers | Smallest, most defensible test of the retention opportunity |
| 2 | Make on-time delivery rate a headline KPI; add service recovery for late orders | Largest measurable driver of review score |
| 3 | Move to state-tiered estimated delivery dates | Directly reduces the *late rate* and the geography/satisfaction gap |
| 4 | Track average installments as a leading AOV indicator | Financing availability is structurally tied to order size |
| 5 | Invest in seller quality/logistics support in the long tail, especially outside the Southeast | Addresses delivery variance at its likely source |

## Scope Note

This summary intentionally stops short of a predictive churn or CLV model — the analysis supports directional segmentation and diagnosis; a model needs a proper train/holdout design and is scoped as future work rather than claimed here. Full methodology, data quality checks, and all supporting charts are in `notebooks/Customer_Intelligence_Platform.ipynb`.
