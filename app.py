# app.py
# EC-AI Insight — Sales / Retail Transactions MVP
# Founder-first layout: Business Summary -> Business Insights -> Key visuals -> Further analysis -> Advanced (collapsed) -> Exports

import io
import os
import math
import textwrap
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN


# -----------------------------
# Styling / Theme
# -----------------------------
TABLEAU10 = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
             "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"]

PLOTLY_TEMPLATE = "plotly_white"

st.set_page_config(page_title="EC-AI Insight", layout="wide")

BASE_CSS = """
<style>
/* Slightly larger default typography */
html, body, [class*="css"]  { font-size: 16px; }
h1 { margin-bottom: 0.2rem; }
.ec-subtitle { font-size: 17px; color: #666; margin-top: -0.3rem; }
.ec-hint { font-size: 13px; color: #777; }
.ec-block-title { font-size: 18px; font-weight: 700; margin: 0.2rem 0 0.6rem 0; }
.ec-section-gap { margin-top: 0.8rem; }
.ec-bullets p { margin: 0.45rem 0; }
.ec-bullets ul { margin-top: 0.25rem; }
.ec-bullets li { margin: 0.35rem 0; line-height: 1.45; }
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)


# -----------------------------
# Helpers
# -----------------------------
def fmt_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    sign = "-" if x < 0 else ""
    x = abs(float(x))
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:.1f}K"
    return f"{sign}${x:,.0f}"


def fmt_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x*100:.0f}%"


def to_datetime_safe(s: pd.Series) -> Optional[pd.Series]:
    try:
        out = pd.to_datetime(s, errors="coerce")
        if out.notna().sum() >= max(5, int(0.6 * len(out))):
            return out
    except Exception:
        return None
    return None


def pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    return None


def ensure_revenue(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """
    Returns df, revenue_col name. Tries to find an existing Revenue column; if not, derives from common retail fields.
    """
    revenue_col = pick_col(df, ["Revenue", "Sales", "Total_Sales", "TotalRevenue"])
    if revenue_col:
        return df, revenue_col

    # Derive: Unit_Price * Units * (1 - Discount_Rate)  (if those exist)
    unit_price = pick_col(df, ["Unit_Price", "UnitPrice", "Price", "unit_price"])
    units = pick_col(df, ["Units", "Quantity", "Qty", "units"])
    disc = pick_col(df, ["Discount_Rate", "DiscountRate", "Discount", "discount_rate"])

    if unit_price and units:
        d = df.copy()
        d["_unit_price"] = pd.to_numeric(d[unit_price], errors="coerce")
        d["_units"] = pd.to_numeric(d[units], errors="coerce")
        if disc:
            d["_disc"] = pd.to_numeric(d[disc], errors="coerce").fillna(0.0)
            d["Revenue"] = d["_unit_price"] * d["_units"] * (1.0 - d["_disc"].clip(0, 1))
        else:
            d["Revenue"] = d["_unit_price"] * d["_units"]
        return d, "Revenue"

    # Fallback: first numeric column as pseudo revenue (last resort)
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if num_cols:
        return df, num_cols[0]
    # If nothing numeric, create empty revenue
    d = df.copy()
    d["Revenue"] = np.nan
    return d, "Revenue"


def discount_band(rate: float) -> str:
    if rate is None or (isinstance(rate, float) and np.isnan(rate)):
        return "Unknown"
    r = float(rate)
    if r < 0:
        r = 0.0
    if r < 0.02:
        return "0–2%"
    if r < 0.05:
        return "2–5%"
    if r < 0.10:
        return "5–10%"
    if r < 0.15:
        return "10–15%"
    if r < 0.20:
        return "15–20%"
    return "20%+"

DISCOUNT_BANDS_ORDER = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]


def compute_cv(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 3:
        return np.nan
    m = s.mean()
    if m == 0:
        return np.nan
    return float(s.std(ddof=0) / m)


def fig_standard_layout(fig: go.Figure, title: Optional[str] = None, height: Optional[int] = None) -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        font=dict(size=14),
        margin=dict(l=40, r=20, t=45 if title else 20, b=50),
        height=height,
        showlegend=False
    )
    if title:
        fig.update_layout(title=dict(text=title, x=0.0, xanchor="left", font=dict(size=20)))
    fig.update_xaxes(title_font=dict(size=14), tickfont=dict(size=12))
    fig.update_yaxes(title_font=dict(size=14), tickfont=dict(size=12))
    return fig


def fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> bytes:
    """
    Requires kaleido in environment.
    """
    return fig.to_image(format="png", scale=scale)


# -----------------------------
# Data load
# -----------------------------
st.title("EC-AI Insight")
st.markdown('<div class="ec-subtitle">Sales performance, explained clearly.</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ec-subtitle">Upload your sales data and get a short business briefing — what’s working, what’s risky, and where to focus next.</div>',
    unsafe_allow_html=True
)

st.markdown('<div class="ec-section-gap"></div>', unsafe_allow_html=True)

uploaded = st.file_uploader("Upload a dataset", type=["csv", "xlsx", "xls"])
if not uploaded:
    st.info("Upload a CSV or Excel file to begin (retail sales / transaction data recommended).")
    st.stop()

# Read file
if uploaded.name.lower().endswith(".csv"):
    df_raw = pd.read_csv(uploaded)
else:
    df_raw = pd.read_excel(uploaded)

df_raw.columns = [str(c).strip() for c in df_raw.columns]

# Identify columns
date_col = pick_col(df_raw, ["Date", "Transaction_Date", "Txn_Date", "Order_Date"])
store_col = pick_col(df_raw, ["Store", "Location", "Branch"])
cat_col = pick_col(df_raw, ["Category", "Product_Category"])
channel_col = pick_col(df_raw, ["Channel", "Sales_Channel"])
pay_col = pick_col(df_raw, ["Payment_Method", "Payment", "Pay_Method"])
disc_col = pick_col(df_raw, ["Discount_Rate", "DiscountRate", "Discount", "discount_rate"])
cogs_col = pick_col(df_raw, ["COGS", "Cost", "Cost_of_Goods", "CostOfGoods"])

df, revenue_col = ensure_revenue(df_raw)

# Parse date
if date_col:
    dt = to_datetime_safe(df[date_col])
    if dt is not None:
        df["_Date"] = dt
    else:
        df["_Date"] = pd.NaT
else:
    df["_Date"] = pd.NaT

# Ensure numeric revenue
df["_Revenue"] = pd.to_numeric(df[revenue_col], errors="coerce")

# Discount band
if disc_col:
    df["_DiscountRate"] = pd.to_numeric(df[disc_col], errors="coerce").fillna(0.0)
else:
    df["_DiscountRate"] = np.nan
df["_DiscountBand"] = df["_DiscountRate"].apply(discount_band)

# Gross profit proxy
if cogs_col:
    df["_COGS"] = pd.to_numeric(df[cogs_col], errors="coerce")
    df["_GrossProfit"] = df["_Revenue"] - df["_COGS"]
else:
    df["_COGS"] = np.nan
    df["_GrossProfit"] = np.nan

# -----------------------------
# Build founder-language narrative
# -----------------------------
def build_business_summary(df: pd.DataFrame) -> List[str]:
    bullets: List[str] = []

    n = len(df)
    total_rev = df["_Revenue"].sum(skipna=True)
    bullets.append(f"Quick view: {fmt_money(total_rev)} revenue from {n:,} transactions.")

    # Top store & concentration
    if store_col:
        by_store = df.groupby(store_col, dropna=False)["_Revenue"].sum().sort_values(ascending=False)
        if len(by_store) >= 1:
            top_store = by_store.index[0]
            bullets.append(f"Your best-performing store is **{top_store}** ({fmt_money(by_store.iloc[0])}).")
        if len(by_store) >= 2 and total_rev and total_rev > 0:
            top2_share = float((by_store.iloc[0] + by_store.iloc[1]) / total_rev)
            bullets.append(f"Revenue is concentrated: the top two stores contribute roughly **{fmt_pct(top2_share)}** of sales (keep them strong).")
        if len(by_store) >= 3:
            # "long tail"
            tail_share = float(by_store.iloc[3:].sum() / total_rev) if total_rev else np.nan
            if not np.isnan(tail_share):
                bullets.append(f"There is a long tail: stores outside the top 3 contribute about **{fmt_pct(tail_share)}** — improve consistency before expanding aggressively.")

    # Trend
    if df["_Date"].notna().sum() >= 5:
        daily = df.dropna(subset=["_Date"]).groupby(df["_Date"].dt.date)["_Revenue"].sum().sort_index()
        if len(daily) >= 7:
            start = daily.iloc[:3].mean()
            end = daily.iloc[-3:].mean()
            if start and start > 0:
                change = (end - start) / start
                direction = "up" if change > 0 else "down"
                bullets.append(f"Sales are trending **{direction}**: daily revenue moved from about {fmt_money(start)} to {fmt_money(end)} (around {fmt_pct(abs(change))} change).")
        if len(daily) >= 1:
            best_day = daily.idxmax()
            bullets.append(f"Best day in the period was **{best_day}** with about {fmt_money(daily.max())} revenue.")

    # Category and channel/payment
    if cat_col:
        by_cat = df.groupby(cat_col)["_Revenue"].sum().sort_values(ascending=False)
        if len(by_cat) >= 1:
            bullets.append(f"Top category by revenue is **{by_cat.index[0]}** ({fmt_money(by_cat.iloc[0])}).")

    if channel_col:
        by_ch = df.groupby(channel_col)["_Revenue"].sum().sort_values(ascending=False)
        if len(by_ch) >= 1:
            bullets.append(f"Strongest channel is **{by_ch.index[0]}** ({fmt_money(by_ch.iloc[0])} revenue).")

    if pay_col:
        by_pay = df.groupby(pay_col)["_Revenue"].sum().sort_values(ascending=False)
        if len(by_pay) >= 1:
            bullets.append(f"Most-used payment method by revenue is **{by_pay.index[0]}** ({fmt_money(by_pay.iloc[0])}).")

    # Discount effectiveness: revenue per sale proxy
    # (Use average revenue per transaction by band)
    band = df.groupby("_DiscountBand")["_Revenue"].mean().reindex(DISCOUNT_BANDS_ORDER)
    if band.notna().sum() >= 3:
        best_band = band.idxmax()
        bullets.append(f"Discounts appear to work best around **{best_band}** in this dataset — treat deeper discounts as controlled experiments.")

    # Profit proxy
    if df["_GrossProfit"].notna().sum() >= 10:
        gp_mean = df["_GrossProfit"].mean(skipna=True)
        bullets.append(f"Average gross profit per sale (Revenue − COGS) is about {fmt_money(gp_mean)} (directional).")

    # Ensure ~10 bullets max (and minimum 10 if possible)
    bullets = bullets[:12]
    return bullets


def build_business_insights(df: pd.DataFrame) -> Dict[str, List[str]]:
    insights = {"money": [], "risk": [], "improve": [], "focus": []}

    total_rev = df["_Revenue"].sum(skipna=True)
    if store_col:
        by_store = df.groupby(store_col)["_Revenue"].sum().sort_values(ascending=False)
        if len(by_store) >= 1:
            insights["money"].append(f"Most revenue comes from **{by_store.index[0]}** — protect execution there (stock, staffing, service).")
        if len(by_store) >= 2 and total_rev and total_rev > 0:
            share = float((by_store.iloc[0] + by_store.iloc[1]) / total_rev)
            insights["money"].append(f"Revenue concentration is high (top 2 ≈ **{fmt_pct(share)}**). A dip in top stores will move the whole business.")

    if cat_col:
        by_cat = df.groupby(cat_col)["_Revenue"].sum().sort_values(ascending=False)
        if len(by_cat) >= 1:
            insights["money"].append(f"Category **{by_cat.index[0]}** is the biggest revenue driver — review availability and best-sellers first.")

    # Risk: volatility (but expressed in plain language)
    if store_col and df["_Date"].notna().sum() >= 10:
        daily_store = (
            df.dropna(subset=["_Date"])
              .groupby([df["_Date"].dt.date, store_col])["_Revenue"].sum()
              .reset_index()
        )
        if len(daily_store) > 0:
            cvs = daily_store.groupby(store_col)["_Revenue"].apply(compute_cv).sort_values(ascending=False)
            if cvs.notna().sum() >= 1:
                top_vol_store = cvs.index[0]
                insights["risk"].append(f"One location is noticeably more ‘spiky’: **{top_vol_store}** swings more day-to-day than others (often operational).")
                insights["risk"].append("If results feel ‘random’, it’s usually stock availability, staffing, or inconsistent promotion discipline.")

    # Improve: discount guidance
    band_mean = df.groupby("_DiscountBand")["_Revenue"].mean().reindex(DISCOUNT_BANDS_ORDER)
    if band_mean.notna().sum() >= 3:
        best_band = band_mean.idxmax()
        insights["improve"].append(f"Use **revenue per sale** as the guardrail metric when running promotions. In this data, **{best_band}** looks healthiest.")
        insights["improve"].append("Treat deep discounts as experiments with a clear goal (e.g., increase revenue per sale), and stop what doesn’t work.")

    if df["_GrossProfit"].notna().sum() >= 10:
        insights["improve"].append("Review margin by store/category — profitability can differ even when revenue looks similar.")

    # Focus next
    insights["focus"].append("Double down on top stores first: get the basics right where revenue is concentrated.")
    insights["focus"].append("Stabilise inconsistent locations before setting aggressive growth targets.")
    insights["focus"].append("Keep promotions simple and measurable: run fewer, clearer experiments rather than many overlapping discounts.")

    return insights


summary_bullets = build_business_summary(df)
insights = build_business_insights(df)

# If user wants 10 bullets minimum, pad with sensible founder bullets (non-numeric) if missing
PAD_BULLETS = [
    "Look for 1–2 repeatable plays (top store + top category) and scale them before adding new complexity.",
    "Use this report as a weekly rhythm: check top stores, trend, and promotion effectiveness.",
    "If you have stock-out logs or footfall, add them next — they usually explain volatility quickly.",
    "Make one owner-level KPI visible: weekly revenue per sale, by store."
]
while len(summary_bullets) < 10 and PAD_BULLETS:
    summary_bullets.append(PAD_BULLETS.pop(0))


# -----------------------------
# Charts
# -----------------------------
charts_for_export: List[Tuple[str, go.Figure]] = []

# Revenue trend
if df["_Date"].notna().sum() >= 5:
    daily = df.dropna(subset=["_Date"]).groupby(df["_Date"].dt.date)["_Revenue"].sum().reset_index()
    daily.columns = ["Date", "Revenue"]
    fig_trend = px.line(daily, x="Date", y="Revenue")
    fig_trend.update_traces(line=dict(width=3), mode="lines+markers")
    fig_trend = fig_standard_layout(fig_trend, title="Revenue Trend", height=380)
    fig_trend.update_yaxes(title="Revenue")
    charts_for_export.append(("Revenue Trend", fig_trend))
else:
    fig_trend = None

# Top stores by revenue (1 store = 1 color)
fig_topstores = None
if store_col:
    by_store = df.groupby(store_col)["_Revenue"].sum().sort_values(ascending=True).tail(5)
    top_df = by_store.reset_index()
    top_df.columns = ["Store", "Revenue"]
    # color mapping
    stores_order = list(top_df["Store"])
    color_map = {s: TABLEAU10[i % len(TABLEAU10)] for i, s in enumerate(stores_order)}
    fig_topstores = px.bar(
        top_df,
        x="Revenue",
        y="Store",
        orientation="h",
        color="Store",
        color_discrete_map=color_map,
        text="Revenue"
    )
    fig_topstores.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
    fig_topstores = fig_standard_layout(fig_topstores, title="Top Stores by Revenue", height=360)
    fig_topstores.update_layout(showlegend=False)
    charts_for_export.append(("Top Stores by Revenue", fig_topstores))

# Store stability small multiples (5 different colors)
store_small_figs: List[Tuple[str, go.Figure]] = []
if store_col and df["_Date"].notna().sum() >= 5:
    daily_store = (
        df.dropna(subset=["_Date"])
          .groupby([df["_Date"].dt.date, store_col])["_Revenue"].sum()
          .reset_index()
    )
    daily_store.columns = ["Date", "Store", "Revenue"]
    top5 = df.groupby(store_col)["_Revenue"].sum().sort_values(ascending=False).head(5).index.tolist()
    color_map = {s: TABLEAU10[i % len(TABLEAU10)] for i, s in enumerate(top5)}
    for s in top5:
        part = daily_store[daily_store["Store"] == s].sort_values("Date")
        f = px.line(part, x="Date", y="Revenue")
        f.update_traces(line=dict(width=3, color=color_map[s]), mode="lines+markers", marker=dict(size=5, color=color_map[s]))
        f = fig_standard_layout(f, title=s, height=240)
        f.update_layout(title=dict(font=dict(size=16)))
        f.update_yaxes(title=None)
        store_small_figs.append((s, f))
        charts_for_export.append((f"Store Trend — {s}", f))

# Pricing effectiveness (alignment fix)
fig_pricing = None
band_mean = df.groupby("_DiscountBand")["_Revenue"].mean().reindex(DISCOUNT_BANDS_ORDER).dropna()
if len(band_mean) >= 2:
    pricing_df = band_mean.reset_index()
    pricing_df.columns = ["Discount band", "Avg revenue per sale"]
    # Force categorical order
    pricing_df["Discount band"] = pd.Categorical(pricing_df["Discount band"], categories=DISCOUNT_BANDS_ORDER, ordered=True)
    pricing_df = pricing_df.sort_values("Discount band")

    fig_pricing = px.bar(
        pricing_df,
        x="Discount band",
        y="Avg revenue per sale",
        color="Discount band",
        color_discrete_sequence=TABLEAU10,
        text="Avg revenue per sale"
    )
    fig_pricing.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
    fig_pricing = fig_standard_layout(fig_pricing, title="Pricing Effectiveness", height=420)
    fig_pricing.update_layout(bargap=0.55, showlegend=False)
    fig_pricing.update_xaxes(type="category", categoryorder="array", categoryarray=DISCOUNT_BANDS_ORDER, title="Discount band")
    fig_pricing.update_yaxes(title="Average revenue per sale")
    charts_for_export.append(("Average Revenue per Sale by Discount Band", fig_pricing))

# Further analysis charts (aligned categorical)
fig_cat = None
if cat_col:
    by_cat = df.groupby(cat_col)["_Revenue"].sum().sort_values(ascending=False).head(8)
    cat_df = by_cat.reset_index()
    cat_df.columns = ["Category", "Revenue"]
    fig_cat = px.bar(cat_df, x="Category", y="Revenue", color="Category", color_discrete_sequence=TABLEAU10, text="Revenue")
    fig_cat.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
    fig_cat = fig_standard_layout(fig_cat, title="Revenue by Category (Top)", height=360)
    fig_cat.update_layout(showlegend=False, bargap=0.55)
    fig_cat.update_xaxes(type="category")
    charts_for_export.append(("Revenue by Category (Top)", fig_cat))

fig_ch = None
if channel_col:
    by_ch = df.groupby(channel_col)["_Revenue"].sum().sort_values(ascending=False).head(8)
    ch_df = by_ch.reset_index()
    ch_df.columns = ["Channel", "Revenue"]
    fig_ch = px.bar(ch_df, x="Channel", y="Revenue", color="Channel", color_discrete_sequence=TABLEAU10, text="Revenue")
    fig_ch.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
    fig_ch = fig_standard_layout(fig_ch, title="Revenue by Channel (Top)", height=340)
    fig_ch.update_layout(showlegend=False, bargap=0.55)
    fig_ch.update_xaxes(type="category")
    charts_for_export.append(("Revenue by Channel (Top)", fig_ch))

fig_cv_ch = None
if channel_col and df["_Date"].notna().sum() >= 10:
    daily_ch = (
        df.dropna(subset=["_Date"])
          .groupby([df["_Date"].dt.date, channel_col])["_Revenue"].sum()
          .reset_index()
    )
    daily_ch.columns = ["Date", "Channel", "Revenue"]
    cvs = daily_ch.groupby("Channel")["Revenue"].apply(compute_cv).sort_values(ascending=False).dropna()
    if len(cvs) >= 2:
        cv_df = cvs.reset_index()
        cv_df.columns = ["Channel", "Volatility (CV)"]
        fig_cv_ch = px.bar(cv_df, x="Channel", y="Volatility (CV)", color="Channel", color_discrete_sequence=TABLEAU10, text="Volatility (CV)")
        fig_cv_ch.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
        fig_cv_ch = fig_standard_layout(fig_cv_ch, title="Volatility by Channel (higher = less stable)", height=320)
        fig_cv_ch.update_layout(showlegend=False, bargap=0.55)
        fig_cv_ch.update_xaxes(type="category")
        charts_for_export.append(("Volatility by Channel", fig_cv_ch))


# -----------------------------
# UI
# -----------------------------
st.divider()
st.subheader("Business Summary")
st.markdown('<div class="ec-bullets">', unsafe_allow_html=True)
st.markdown("\n".join([f"- {b}" for b in summary_bullets]))
st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.subheader("Business Insights")

def spaced_section(title: str, items: List[str]):
    st.markdown(f"<div class='ec-block-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown('<div class="ec-bullets">', unsafe_allow_html=True)
    st.markdown("\n".join([f"- {x}" for x in items]))
    st.markdown("</div>", unsafe_allow_html=True)

spaced_section("Where the money is made", insights["money"])
spaced_section("Where risk exists", insights["risk"])
spaced_section("What can be improved", insights["improve"])
spaced_section("What to focus on next", insights["focus"])

st.divider()
st.subheader("Revenue Overview")
if fig_trend is not None:
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("No reliable date column detected — upload data with a Date field to see the revenue trend.")

if fig_topstores is not None:
    st.subheader("Top Stores by Revenue")
    st.plotly_chart(fig_topstores, use_container_width=True)

if store_small_figs:
    st.subheader("Store Stability (Top 5)")
    # grid: 2 columns
    cols = st.columns(2)
    for i, (s, f) in enumerate(store_small_figs):
        with cols[i % 2]:
            st.plotly_chart(f, use_container_width=True)

if fig_pricing is not None:
    st.subheader("Pricing Effectiveness")
    st.plotly_chart(fig_pricing, use_container_width=True)

# Further analysis (recommended)
st.divider()
st.subheader("Further Analysis (recommended)")
if fig_cat is not None:
    st.plotly_chart(fig_cat, use_container_width=True)
if fig_ch is not None:
    st.plotly_chart(fig_ch, use_container_width=True)
if fig_cv_ch is not None:
    st.plotly_chart(fig_cv_ch, use_container_width=True)

# Advanced (collapsed)
st.divider()
with st.expander("Advanced (optional): data preview • data profile • correlation"):
    st.markdown("### Data Preview")
    st.dataframe(df_raw.head(50), use_container_width=True)

    st.markdown("### Data Profile (quick)")
    profile = pd.DataFrame({
        "Column": df_raw.columns,
        "Type": [str(df_raw[c].dtype) for c in df_raw.columns],
        "Missing %": [float(df_raw[c].isna().mean() * 100) for c in df_raw.columns],
        "Unique": [int(df_raw[c].nunique(dropna=True)) for c in df_raw.columns],
    })
    st.dataframe(profile, use_container_width=True)

    # Correlation (numeric only)
    st.markdown("### Correlation (numeric)")
    num = df.select_dtypes(include=[np.number]).copy()
    if num.shape[1] >= 2:
        corr = num.corr(numeric_only=True)
        fig_corr = px.imshow(corr, text_auto=True, aspect="auto", color_continuous_scale="RdBu_r")
        fig_corr = fig_standard_layout(fig_corr, title="Correlation Heatmap", height=420)
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Not enough numeric columns for correlation.")


# -----------------------------
# Exports
# -----------------------------
def pdf_draw_title(c: canvas.Canvas, text: str, x: float, y: float, max_width_chars: int = 80):
    # Wrap long titles so they never get cut
    lines = textwrap.wrap(text, width=max_width_chars)
    c.setFont("Helvetica-Bold", 14)
    for line in lines[:2]:
        c.drawString(x, y, line)
        y -= 16


def pdf_draw_bullets(c: canvas.Canvas, bullets: List[str], x: float, y: float, font_size: int = 11, leading: int = 15, width_chars: int = 100):
    c.setFont("Helvetica", font_size)
    for b in bullets:
        if y < 2.2 * cm:
            c.showPage()
            y = A4[1] - 2.0 * cm
            c.setFont("Helvetica", font_size)
        wrapped = textwrap.wrap(str(b).replace("**", ""), width=width_chars)
        if not wrapped:
            continue
        c.drawString(x, y, f"• {wrapped[0]}")
        y -= leading
        for cont in wrapped[1:]:
            c.drawString(x + 14, y, cont)
            y -= leading
        y -= 2
    return y


def make_executive_brief_pdf(title: str, summary_bullets: List[str], insights: Dict[str, List[str]], figs: List[Tuple[str, go.Figure]]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Header
    pdf_draw_title(c, title, 2 * cm, h - 2.0 * cm)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawString(2 * cm, h - 2.6 * cm, f"Generated by EC-AI Insight • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.setFillColor(colors.black)

    y = h - 3.3 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Business Summary")
    y -= 0.6 * cm
    y = pdf_draw_bullets(c, summary_bullets[:10], 2 * cm, y, font_size=11, leading=14, width_chars=105)

    y -= 0.2 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Business Insights")
    y -= 0.6 * cm
    flat_insights = []
    for k in ["money", "risk", "improve", "focus"]:
        flat_insights.extend(insights.get(k, []))
    y = pdf_draw_bullets(c, flat_insights[:10], 2 * cm, y, font_size=11, leading=14, width_chars=105)

    # Charts (each on new page)
    for chart_title, fig in figs:
        c.showPage()
        pdf_draw_title(c, chart_title, 2 * cm, h - 2.0 * cm, max_width_chars=70)

        # chart image
        try:
            png = fig_to_png_bytes(fig, scale=2)
            img = io.BytesIO(png)
            # Fit inside page
            img_w = w - 4 * cm
            img_h = h - 6 * cm
            c.drawImage(img, 2 * cm, 2.5 * cm, width=img_w, height=img_h, preserveAspectRatio=True, anchor='c')
        except Exception as e:
            c.setFont("Helvetica", 11)
            c.setFillColor(colors.red)
            c.drawString(2 * cm, h - 3.0 * cm, "Chart export failed (check kaleido/plotly versions).")
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 10)
            c.drawString(2 * cm, h - 3.5 * cm, str(e)[:120])

    c.save()
    return buf.getvalue()


def make_talking_deck_pptx(title: str, summary_bullets: List[str], figs: List[Tuple[str, go.Figure]]) -> bytes:
    prs = Presentation()
    # 16:9
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    def add_title(slide, text):
        tx = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.2), Inches(0.6))
        tf = tx.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(26)
        p.font.bold = True

    def add_notes(slide, bullets):
        box = slide.shapes.add_textbox(Inches(0.6), Inches(1.15), Inches(5.6), Inches(5.9))
        tf = box.text_frame
        tf.word_wrap = True
        tf.clear()
        for i, b in enumerate(bullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = str(b).replace("**", "")
            p.level = 0
            p.font.size = Pt(16)
            p.space_after = Pt(6)

    def add_chart(slide, fig):
        png = fig_to_png_bytes(fig, scale=2)
        img = io.BytesIO(png)
        # Right side chart area
        slide.shapes.add_picture(img, Inches(6.5), Inches(1.15), width=Inches(6.6), height=Inches(5.9))

    # Cover slide
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    add_title(slide, title)
    sub = slide.shapes.add_textbox(Inches(0.6), Inches(1.1), Inches(12.0), Inches(0.8))
    tf = sub.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = "Sales performance briefing (executive-ready)"
    p.font.size = Pt(18)
    p.font.color.rgb = None

    add_notes(slide, summary_bullets[:6])

    # One insight per slide
    for chart_title, fig in figs:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        add_title(slide, chart_title)  # title is in textbox (won't be cut)
        # small commentary (2–3 bullets) based on chart type
        notes = []
        if "Revenue Trend" in chart_title:
            notes = summary_bullets[:4]
        elif "Top Stores" in chart_title:
            notes = [x for x in summary_bullets if "store" in x.lower() or "concentr" in x.lower()][:4]
        elif "Discount" in chart_title or "Pricing" in chart_title:
            notes = [x for x in summary_bullets if "discount" in x.lower() or "revenue per sale" in x.lower()][:4]
        elif "Category" in chart_title:
            notes = [x for x in summary_bullets if "category" in x.lower()][:3] + ["Double down on best-sellers before expanding the catalog."]
        else:
            notes = summary_bullets[:4]
        if not notes:
            notes = summary_bullets[:4]
        add_notes(slide, notes[:5])
        try:
            add_chart(slide, fig)
        except Exception as e:
            box = slide.shapes.add_textbox(Inches(6.6), Inches(2.2), Inches(6.3), Inches(1.5))
            tf = box.text_frame
            tf.text = f"Chart export failed: {str(e)[:80]}"

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


st.divider()
st.subheader("Export Executive Brief")
st.markdown('<div class="ec-hint">PDF includes: Business Summary + Business Insights + selected key charts with short commentary. PPT is a talking deck (one insight per slide).</div>', unsafe_allow_html=True)

# Choose a small, high-value set for export
export_set: List[Tuple[str, go.Figure]] = []
for name, fig in charts_for_export:
    if name in ["Revenue Trend", "Top Stores by Revenue", "Average Revenue per Sale by Discount Band", "Revenue by Category (Top)", "Revenue by Channel (Top)"]:
        export_set.append((name, fig))
# Fallback if missing
if not export_set and charts_for_export:
    export_set = charts_for_export[:4]

colA, colB = st.columns(2)
with colA:
    if st.button("Generate PDF Executive Brief"):
        try:
            pdf_bytes = make_executive_brief_pdf("EC-AI Executive Brief", summary_bullets, insights, export_set)
            st.download_button("Download PDF", data=pdf_bytes, file_name="ecai_executive_brief.pdf", mime="application/pdf")
        except Exception as e:
            st.error("PDF export failed.")
            st.code(str(e))

with colB:
    if st.button("Generate PPT Talking Deck"):
        try:
            ppt_bytes = make_talking_deck_pptx("EC-AI Talking Deck", summary_bullets, export_set)
            st.download_button("Download PPT", data=ppt_bytes, file_name="ecai_talking_deck.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
        except Exception as e:
            st.error("PPT export failed.")
            st.code(str(e))

# Sidebar diagnostic for export engine (helps debug Streamlit Cloud)
with st.sidebar:
    st.markdown("### Diagnostics")
    try:
        import plotly
        import importlib
        st.write("Plotly:", plotly.__version__)
        st.write("Kaleido installed:", importlib.util.find_spec("kaleido") is not None)
        # quick smoke test
        test_fig = go.Figure(go.Scatter(y=[1, 3, 2]))
        _ = test_fig.to_image(format="png")
        st.success("Chart export engine OK ✅")
    except Exception as e:
        st.error("Chart export engine failed ❌")
        st.code(str(e))
