# EC-AI Insight — Streamlit App (CEO-grade Executive Brief v1)
# Author: Gordon (EC-AI) + Jarvis
# Notes:
# - Executive-first UI: clear business summary + concrete insights + curated charts.
# - Advanced section is optional (expand / toggle).
# - Exports: Executive Brief PDF (with charts) + EC-AI Insights Pack PPT (16:9).
# - No dataclasses (avoids Python 3.13 dataclass edge cases on Streamlit Cloud).

import io
import math
import textwrap
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


# -----------------------------
# UI + Styling
# -----------------------------
APP_TITLE = "EC-AI Insight"
APP_TAGLINE = "Sales performance, explained clearly."
APP_SUBTITLE = "Upload your sales data and get a CEO-grade briefing — what’s working, what’s risky, and where to focus next."

# Executive visual system (clean + corporate)
PLOTLY_TEMPLATE = "plotly_white"
pio.templates.default = PLOTLY_TEMPLATE

COLORWAY = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"
]

# Remove zoom + modebar (Executive)
EXEC_PLOTLY_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": "reset",
    "showTips": False,
    "responsive": True,
}

# Advanced allows modebar (still no scroll zoom)
ADV_PLOTLY_CONFIG = {
    "displayModeBar": True,
    "scrollZoom": False,
    "doubleClick": "reset",
    "showTips": True,
    "responsive": True,
}

st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 2rem; padding-bottom: 2.5rem; }
      h1, h2, h3 { letter-spacing: -0.02em; }
      .ec-subtle { color: rgba(17, 24, 39, 0.70); font-size: 0.95rem; }
      .ec-bullets li { margin: 0.55rem 0; line-height: 1.35; }
      .ec-h3gap { margin-top: 0.9rem; margin-bottom: 0.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Helpers: column detection
# -----------------------------
def _norm(s: str) -> str:
    return "".join(
        ch.lower() for ch in str(s).strip()
        if ch.isalnum() or ch in ["_", " "]
    ).replace(" ", "_")


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Detects common sales columns.
    Keys: date, store, category, channel, payment, qty, revenue, discount_rate
    """
    cols = list(df.columns)
    norm_map = {c: _norm(c) for c in cols}

    def pick(candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            for c, n in norm_map.items():
                if n == cand:
                    return c
        for cand in candidates:
            for c, n in norm_map.items():
                if cand in n:
                    return c
        return None

    return {
        "date": pick(["date", "order_date", "transaction_date", "tx_date", "day"]),
        "store": pick(["store", "branch", "location", "outlet", "shop"]),
        "category": pick(["category", "product_category", "dept", "department"]),
        "channel": pick(["channel", "sales_channel", "platform"]),
        "payment": pick(["payment", "payment_method", "tender", "pay_method"]),
        "qty": pick(["qty", "quantity", "units", "unit", "items"]),
        "revenue": pick(["revenue", "sales", "amount", "net_sales", "total_sales", "gross_sales"]),
        "discount_rate": pick(["discount_rate", "discount", "disc_rate", "promo_discount", "discount_pct", "discount_percent"]),
    }


def coerce_date(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce")
    except Exception:
        return pd.to_datetime(series.astype(str), errors="coerce")


def as_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def safe_div(a, b):
    return np.where((b == 0) | pd.isna(b), np.nan, a / b)


def strip_machine_marks(s: str) -> str:
    # Remove markdown ** and stray asterisks that look like "machine language"
    return str(s).replace("**", "").replace("*", "").strip()


# -----------------------------
# Business computations
# -----------------------------
def summarize_period(dates: pd.Series) -> Tuple[int, str, str]:
    d = dates.dropna()
    if d.empty:
        return 0, "-", "-"
    start = d.min().date().isoformat()
    end = d.max().date().isoformat()
    days = int((d.max().normalize() - d.min().normalize()).days) + 1
    return days, start, end


def top_n_share(series: pd.Series, n: int = 2) -> float:
    s = series.sort_values(ascending=False)
    total = float(s.sum()) if len(s) else 0.0
    if total <= 0:
        return 0.0
    return float(s.head(n).sum() / total)


def format_money(x: float) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "-"
    absx = abs(float(x))
    if absx >= 1_000_000:
        return f"${x/1_000_000:,.2f}M"
    if absx >= 1_000:
        return f"${x/1_000:,.1f}K"
    return f"${x:,.0f}"


def format_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "-"
    return f"{x*100:.0f}%"


def discount_band(discount_rate: pd.Series) -> pd.Series:
    dr = as_numeric(discount_rate)
    dr_norm = dr.copy()
    # if values look like 0-100, normalize to 0-1
    if dr_norm.dropna().gt(1.5).mean() > 0.5:
        dr_norm = dr_norm / 100.0

    bins = [-np.inf, 0.02, 0.05, 0.10, 0.15, 0.20, np.inf]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    out = pd.cut(dr_norm, bins=bins, labels=labels)
    return out.astype("category")


def compute_volatility_by_group(df: pd.DataFrame, group_col: str, date_col: str, revenue_col: str) -> pd.DataFrame:
    tmp = df[[group_col, date_col, revenue_col]].dropna()
    if tmp.empty:
        return pd.DataFrame(columns=[group_col, "volatility"])
    daily = tmp.groupby([group_col, tmp[date_col].dt.date])[revenue_col].sum().reset_index()
    stats = daily.groupby(group_col)[revenue_col].agg(["mean", "std"]).reset_index()
    stats["volatility"] = safe_div(stats["std"].values, stats["mean"].values)
    stats["volatility"] = np.nan_to_num(stats["volatility"], nan=0.0, posinf=0.0, neginf=0.0)
    return stats[[group_col, "volatility"]].sort_values("volatility", ascending=False)


def build_business_summary(df: pd.DataFrame, cols: Dict[str, str]) -> List[str]:
    bullets: List[str] = []

    col_date = cols.get("date")
    col_store = cols.get("store")
    col_category = cols.get("category")
    col_channel = cols.get("channel") or cols.get("payment")
    col_qty = cols.get("qty")
    col_rev = cols.get("revenue")
    col_disc = cols.get("discount_rate")

    total_rev = float(df[col_rev].sum()) if col_rev else 0.0
    n_tx = int(len(df))

    if col_date:
        days, start, end = summarize_period(df[col_date])
        bullets.append(
            f"You have {days} days of data ({start} to {end}) covering {n_tx:,} transactions with total revenue of {format_money(total_rev)}."
        )
    else:
        bullets.append(f"Dataset contains {n_tx:,} transactions with total revenue of {format_money(total_rev)}.")

    # Store concentration
    if col_store:
        store_rev = df.groupby(col_store)[col_rev].sum().sort_values(ascending=False)
        if len(store_rev) > 0:
            top_store, top_val = str(store_rev.index[0]), float(store_rev.iloc[0])
            top_share = top_val / total_rev if total_rev > 0 else 0
            bullets.append(f"Revenue is concentrated: {top_store} contributes {format_money(top_val)} (~{format_pct(top_share)} of total).")

        if len(store_rev) >= 2:
            top2_share = top_n_share(store_rev, 2)
            bullets.append(f"Top 2 stores together generate ~{format_pct(top2_share)} of total revenue — small wins here move the whole business most.")

    # Category drivers
    if col_category:
        cat_rev = df.groupby(col_category)[col_rev].sum().sort_values(ascending=False)
        if len(cat_rev) > 0:
            top_cat, top_cat_val = str(cat_rev.index[0]), float(cat_rev.iloc[0])
            top_cat_share = top_cat_val / total_rev if total_rev > 0 else 0
            bullets.append(f"By category, {top_cat} is the largest driver at {format_money(top_cat_val)} (~{format_pct(top_cat_share)}).")

    # Channel drivers
    if col_channel:
        ch_rev = df.groupby(col_channel)[col_rev].sum().sort_values(ascending=False)
        if len(ch_rev) > 0:
            top_ch, top_ch_val = str(ch_rev.index[0]), float(ch_rev.iloc[0])
            top_ch_share = top_ch_val / total_rev if total_rev > 0 else 0
            bullets.append(f"Top channel is {top_ch} at {format_money(top_ch_val)} (~{format_pct(top_ch_share)}).")

    # Momentum + peak day
    if col_date:
        daily_rev = df.groupby(df[col_date].dt.date)[col_rev].sum().sort_index()
        if len(daily_rev) >= 10:
            mid = len(daily_rev) // 2
            first_half = float(daily_rev.iloc[:mid].sum())
            second_half = float(daily_rev.iloc[mid:].sum())
            if first_half > 0:
                delta = (second_half / first_half) - 1
                direction = "more" if delta >= 0 else "less"
                bullets.append(f"Momentum check: the second half of the period delivered {abs(delta)*100:.0f}% {direction} revenue than the first half.")

        if len(daily_rev) >= 3:
            peak_day = daily_rev.idxmax()
            peak_val = float(daily_rev.max())
            bullets.append(f"Peak day was {peak_day} with {format_money(peak_val)} — likely linked to a promotion, event, or stock availability.")

    # Stability risk
    if col_store and col_date:
        vol_store = compute_volatility_by_group(df, col_store, col_date, col_rev)
        if len(vol_store) > 0:
            worst = vol_store.iloc[0]
            bullets.append(f"Stability risk: {worst[col_store]} shows the biggest day-to-day swings (volatility score {worst['volatility']:.2f}).")

    # Pricing effectiveness
    if col_disc:
        tmp = df.copy()
        tmp["_disc_band"] = discount_band(tmp[col_disc]).astype(str)
        tmp = tmp[tmp["_disc_band"].ne("nan")]
        if not tmp.empty:
            if col_qty:
                tmp["_rev_per_sale"] = safe_div(tmp[col_rev].values, as_numeric(tmp[col_qty]).values)
            else:
                tmp["_rev_per_sale"] = tmp[col_rev]
            by = tmp.groupby("_disc_band")["_rev_per_sale"].mean().dropna()
            if len(by) >= 2:
                best_band = by.idxmax()
                best_val = float(by.max())
                deep = tmp[tmp["_disc_band"].isin(["10–15%", "15–20%", "20%+"])]["_rev_per_sale"].mean()
                if pd.notna(deep):
                    bullets.append(
                        f"Discounting: {best_band} performs best (avg revenue per sale {format_money(best_val)}). Deep discounts (10%+) average {format_money(float(deep))} — bigger discounts do not automatically lead to better results."
                    )
                else:
                    bullets.append(f"Discounting: {best_band} performs best (avg revenue per sale {format_money(best_val)}).")

    # Action line
    bullets.append("Next focus: protect and improve the top stores first (inventory, staffing, promotion discipline), then scale what works.")

    # Pad to ~10 bullets
    while len(bullets) < 10:
        bullets.append("Use this brief weekly: review concentration, stability, and pricing effectiveness before making promotional decisions.")

    return [strip_machine_marks(b) for b in bullets[:12]]


def build_business_insights(df: pd.DataFrame, cols: Dict[str, str]) -> Dict[str, List[str]]:
    col_date = cols.get("date")
    col_store = cols.get("store")
    col_category = cols.get("category")
    col_channel = cols.get("channel") or cols.get("payment")
    col_qty = cols.get("qty")
    col_rev = cols.get("revenue")
    col_disc = cols.get("discount_rate")

    total_rev = float(df[col_rev].sum()) if col_rev else 0.0

    def top_k(group_col: str, k=3):
        s = df.groupby(group_col)[col_rev].sum().sort_values(ascending=False)
        out = []
        for i in range(min(k, len(s))):
            name = str(s.index[i])
            val = float(s.iloc[i])
            share = val / total_rev if total_rev > 0 else 0
            out.append((name, val, share))
        return out

    insights = {
        "Where the money is made": [],
        "Where risk exists": [],
        "What can be improved": [],
        "What to focus on next": [],
    }

    if col_store:
        top_stores = top_k(col_store, 3)
        if top_stores:
            insights["Where the money is made"].append(
                "Top stores: " + ", ".join([f"{n} {format_money(v)} ({format_pct(sh)})" for n, v, sh in top_stores])
            )
            insights["Where the money is made"].append(
                "Small improvements in the top stores usually move total performance the most (because they contribute a large share of revenue)."
            )

    if col_category:
        top_cats = top_k(col_category, 3)
        if top_cats:
            insights["Where the money is made"].append(
                "Top categories: " + ", ".join([f"{n} {format_money(v)} ({format_pct(sh)})" for n, v, sh in top_cats])
            )

    if col_channel:
        top_ch = top_k(col_channel, 3)
        if top_ch:
            insights["Where the money is made"].append(
                "Top channels: " + ", ".join([f"{n} {format_money(v)} ({format_pct(sh)})" for n, v, sh in top_ch])
            )

    if col_store and col_date:
        vol_store = compute_volatility_by_group(df, col_store, col_date, col_rev)
        if len(vol_store) > 0:
            worst = vol_store.iloc[0]
            best = vol_store.iloc[-1] if len(vol_store) > 1 else worst
            insights["Where risk exists"].append(
                f"Stability risk: {worst[col_store]} is the most volatile (score {worst['volatility']:.2f}). "
                f"More stable benchmark: {best[col_store]} (score {best['volatility']:.2f})."
            )
            store_rev = df.groupby(col_store)[col_rev].sum().sort_values(ascending=False)
            top2 = top_n_share(store_rev, 2)
            insights["Where risk exists"].append(
                f"Concentration risk: top 2 stores contribute ~{format_pct(top2)} of revenue — execution slip here has a material impact."
            )

    if col_channel and col_date:
        vol_ch = compute_volatility_by_group(df, col_channel, col_date, col_rev)
        if len(vol_ch) > 0:
            worst = vol_ch.iloc[0]
            insights["Where risk exists"].append(
                f"Channel predictability: {worst[col_channel]} is the least stable channel (volatility {worst['volatility']:.2f})."
            )

    if col_disc:
        tmp = df.copy()
        tmp["_disc_band"] = discount_band(tmp[col_disc]).astype(str)
        tmp = tmp[tmp["_disc_band"].ne("nan")]
        if not tmp.empty:
            if col_qty:
                tmp["_rev_per_sale"] = safe_div(tmp[col_rev].values, as_numeric(tmp[col_qty]).values)
            else:
                tmp["_rev_per_sale"] = tmp[col_rev]
            by = tmp.groupby("_disc_band")["_rev_per_sale"].mean().dropna()
            if len(by) >= 2:
                best_band = by.idxmax()
                best_val = float(by.max())
                deep = tmp[tmp["_disc_band"].isin(["10–15%", "15–20%", "20%+"])]["_rev_per_sale"].mean()
                if pd.notna(deep):
                    insights["What can be improved"].append(
                        f"Pricing discipline: {best_band} discounts deliver the best average revenue per sale ({format_money(best_val)}). "
                        f"Deep discounts (10%+) average {format_money(float(deep))} — treat deep discounting as controlled experiments with clear targets."
                    )
                else:
                    insights["What can be improved"].append(
                        f"Pricing discipline: {best_band} discounts deliver the best average revenue per sale ({format_money(best_val)})."
                    )

    if col_store:
        store_rev = df.groupby(col_store)[col_rev].sum().sort_values(ascending=False)
        if len(store_rev) > 0:
            top_store = str(store_rev.index[0])
            insights["What can be improved"].append(
                f"Execution leverage: review stock availability, staffing, and promotion compliance in {top_store} first — it is the biggest lever on total results."
            )

    insights["What to focus on next"].append("Weekly cadence: review Top Stores, Store Stability, and Pricing Effectiveness before launching new promotions.")
    insights["What to focus on next"].append("Stabilize first: volatility is often operational (stock/staffing/execution). Once stable, scale what’s repeatable.")
    insights["What to focus on next"].append("Use Ask EC-AI to explore: ‘why did revenue spike?’, ‘which store needs attention?’, ‘what discount band works best?’")

    # Strip machine marks
    for k in list(insights.keys()):
        insights[k] = [strip_machine_marks(x) for x in insights[k]]

    return insights


# -----------------------------
# Charts (consultancy-grade defaults)
# -----------------------------
def style_fig(fig: go.Figure, title: str, x_title: str = "", y_title: str = "", height: int = 380) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.0, "xanchor": "left", "font": {"size": 20}},
        margin=dict(l=30, r=20, t=60, b=45),
        height=height,
        font=dict(size=14),
        colorway=COLORWAY,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    fig.update_xaxes(title=x_title, tickfont=dict(size=12), titlefont=dict(size=13), type="category")
    fig.update_yaxes(title=y_title, tickfont=dict(size=12), titlefont=dict(size=13), gridcolor="rgba(15,23,42,0.08)")
    return fig


def fig_revenue_trend(df: pd.DataFrame, cols: Dict[str, str]) -> Optional[go.Figure]:
    col_date, col_rev = cols.get("date"), cols.get("revenue")
    if not col_date or not col_rev:
        return None
    daily = df.groupby(df[col_date].dt.date)[col_rev].sum().reset_index()
    daily.columns = ["Date", "Revenue"]
    fig = px.line(daily, x="Date", y="Revenue", markers=True)
    fig = style_fig(fig, "Revenue Trend", y_title="Revenue")
    if len(daily) >= 3:
        peak = daily.loc[daily["Revenue"].idxmax()]
        fig.add_annotation(
            x=peak["Date"], y=peak["Revenue"],
            text=f"Peak {format_money(float(peak['Revenue']))}",
            showarrow=True, arrowhead=2, ax=0, ay=-40
        )
    return fig


def fig_top_stores(df: pd.DataFrame, cols: Dict[str, str], top_n: int = 5) -> Optional[go.Figure]:
    col_store, col_rev = cols.get("store"), cols.get("revenue")
    if not col_store or not col_rev:
        return None
    s = df.groupby(col_store)[col_rev].sum().sort_values(ascending=False).head(top_n)
    if s.empty:
        return None
    data = pd.DataFrame({"Store": s.index.astype(str), "Revenue": s.values})
    fig = px.bar(data, x="Store", y="Revenue", text="Revenue", color="Store")
    fig.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
    fig = style_fig(fig, f"Top {top_n} Revenue-Generating Stores", y_title="Revenue")
    fig.update_layout(showlegend=False, bargap=0.35)
    fig.update_yaxes(range=[0, data["Revenue"].max() * 1.15])
    return fig


def fig_store_stability(df: pd.DataFrame, cols: Dict[str, str], top_n: int = 5) -> Optional[go.Figure]:
    col_store, col_date, col_rev = cols.get("store"), cols.get("date"), cols.get("revenue")
    if not col_store or not col_date or not col_rev:
        return None
    store_rev = df.groupby(col_store)[col_rev].sum().sort_values(ascending=False).head(top_n)
    stores = store_rev.index.tolist()
    if not stores:
        return None

    tmp = df[df[col_store].isin(stores)].copy()
    tmp["_date"] = tmp[col_date].dt.date
    daily = tmp.groupby([col_store, "_date"])[col_rev].sum().reset_index()
    daily.columns = ["Store", "Date", "Revenue"]
    daily["Store"] = daily["Store"].astype(str)

    fig = px.line(
        daily,
        x="Date",
        y="Revenue",
        facet_col="Store",
        facet_col_wrap=2,
        markers=True,
        color="Store",
        category_orders={"Store": [str(s) for s in stores]},
    )
    fig.update_layout(
        title={"text": f"Store Stability (Top {top_n})", "x": 0.0, "xanchor": "left", "font": {"size": 20}},
        height=720,
        margin=dict(l=30, r=20, t=70, b=30),
        showlegend=False,
        font=dict(size=13),
        colorway=COLORWAY,
    )
    fig.update_xaxes(title="", tickfont=dict(size=11))
    fig.update_yaxes(title="Revenue", tickfont=dict(size=11), gridcolor="rgba(15,23,42,0.08)")
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return fig


def fig_pricing_effectiveness(df: pd.DataFrame, cols: Dict[str, str]) -> Optional[go.Figure]:
    col_disc, col_rev = cols.get("discount_rate"), cols.get("revenue")
    if not col_disc or not col_rev:
        return None

    tmp = df.copy()
    tmp["Discount band"] = discount_band(tmp[col_disc]).astype(str)
    tmp = tmp[tmp["Discount band"].ne("nan")]
    if tmp.empty:
        return None

    col_qty = cols.get("qty")
    if col_qty:
        tmp["Revenue per sale"] = safe_div(tmp[col_rev].values, as_numeric(tmp[col_qty]).values)
    else:
        tmp["Revenue per sale"] = tmp[col_rev]

    by = tmp.groupby("Discount band")["Revenue per sale"].mean().reset_index()
    order = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    by["Discount band"] = pd.Categorical(by["Discount band"], categories=order, ordered=True)
    by = by.sort_values("Discount band")

    fig = px.bar(by, x="Discount band", y="Revenue per sale", text="Revenue per sale", color="Discount band")
    fig.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
    fig = style_fig(fig, "Pricing Effectiveness", x_title="Discount band", y_title="Average revenue per sale")
    fig.update_layout(showlegend=False, bargap=0.35)
    fig.update_yaxes(range=[0, by["Revenue per sale"].max() * 1.18])
    return fig


def fig_bar_top(df: pd.DataFrame, cols: Dict[str, str], key: str, title: str, top_n: int = 6) -> Optional[go.Figure]:
    col_group, col_rev = cols.get(key), cols.get("revenue")
    if not col_group or not col_rev:
        return None
    s = df.groupby(col_group)[col_rev].sum().sort_values(ascending=False).head(top_n)
    if s.empty:
        return None
    data = pd.DataFrame({key.title(): s.index.astype(str), "Revenue": s.values})
    fig = px.bar(data, x=key.title(), y="Revenue", text="Revenue", color=key.title())
    fig.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
    fig = style_fig(fig, title, y_title="Revenue")
    fig.update_layout(showlegend=False, bargap=0.35)
    fig.update_yaxes(range=[0, data["Revenue"].max() * 1.15])
    return fig


def fig_volatility_channel(df: pd.DataFrame, cols: Dict[str, str]) -> Optional[go.Figure]:
    col_channel = cols.get("channel") or cols.get("payment")
    col_date, col_rev = cols.get("date"), cols.get("revenue")
    if not col_channel or not col_date or not col_rev:
        return None
    vol = compute_volatility_by_group(df, col_channel, col_date, col_rev)
    if vol.empty:
        return None
    vol[col_channel] = vol[col_channel].astype(str)
    vol.rename(columns={col_channel: "Channel", "volatility": "Volatility (CV)"}, inplace=True)
    fig = px.bar(vol, x="Channel", y="Volatility (CV)", text="Volatility (CV)", color="Channel")
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
    fig = style_fig(fig, "Volatility by Channel (higher = less stable)", y_title="Volatility score (CV)")
    fig.update_layout(showlegend=False, bargap=0.45)
    fig.update_yaxes(range=[0, vol["Volatility (CV)"].max() * 1.20])
    return fig


# -----------------------------
# Export helpers (Plotly -> PNG)
# -----------------------------
def fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> Optional[bytes]:
    try:
        return fig.to_image(format="png", scale=scale, engine="kaleido")
    except Exception:
        try:
            return pio.to_image(fig, format="png", scale=scale)
        except Exception:
            return None


# -----------------------------
# PDF Export (Executive Brief)
# -----------------------------
def _draw_wrapped_bullets(
    c: canvas.Canvas,
    x: float,
    y: float,
    bullets: List[str],
    width_chars: int = 100,
    font_size: int = 11,
    leading: int = 15,
    max_lines: int = 999,
) -> float:
    c.setFont("Helvetica", font_size)
    lines_used = 0
    for b in bullets:
        b = strip_machine_marks(b)
        wrapped = textwrap.wrap(b, width=width_chars) or [""]
        for i, line in enumerate(wrapped):
            if lines_used >= max_lines:
                return y
            prefix = "• " if i == 0 else "  "
            c.drawString(x, y, prefix + line)
            y -= leading
            lines_used += 1
        y -= 3
    return y


def make_executive_brief_pdf(
    title: str,
    summary_bullets: List[str],
    insight_sections: Dict[str, List[str]],
    chart_items: List[Tuple[str, go.Figure, str]],
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    W, H = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(0.75 * inch, H - 0.9 * inch, title)
    c.setFont("Helvetica", 11)
    c.setFillGray(0.35)
    c.drawString(0.75 * inch, H - 1.15 * inch, "CEO-grade snapshot: summary, insights, and charts with commentary.")
    c.setFillGray(0)

    y = H - 1.5 * inch

    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.75 * inch, y, "Business Summary")
    y -= 18
    y = _draw_wrapped_bullets(c, 0.85 * inch, y, summary_bullets, max_lines=45)

    y -= 8

    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.75 * inch, y, "Business Insights")
    y -= 20

    for section, bullets in insight_sections.items():
        if y < 2.0 * inch:
            c.showPage()
            y = H - 0.9 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.85 * inch, y, strip_machine_marks(section))
        y -= 16
        y = _draw_wrapped_bullets(c, 0.95 * inch, y, bullets, max_lines=22)
        y -= 6

    if chart_items:
        c.showPage()
        y = H - 0.9 * inch
        c.setFont("Helvetica-Bold", 14)
        c.drawString(0.75 * inch, y, "Key Charts & Commentary")
        y -= 20

        for chart_title, fig, commentary in chart_items:
            if y < 3.0 * inch:
                c.showPage()
                y = H - 0.9 * inch

            c.setFont("Helvetica-Bold", 12)
            c.drawString(0.75 * inch, y, strip_machine_marks(chart_title))
            y -= 14

            c.setFont("Helvetica", 10.5)
            c.setFillGray(0.25)
            for line in textwrap.wrap(strip_machine_marks(commentary), width=110)[:3]:
                c.drawString(0.75 * inch, y, line)
                y -= 13
            c.setFillGray(0)

            png = fig_to_png_bytes(fig, scale=2)
            if png:
                img = ImageReader(io.BytesIO(png))
                img_w = 7.2 * inch
                img_h = 3.2 * inch
                c.drawImage(img, 0.75 * inch, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, anchor="sw")
                y -= (img_h + 18)
            else:
                c.setFont("Helvetica-Oblique", 10)
                c.setFillGray(0.4)
                c.drawString(0.75 * inch, y, "Chart export unavailable (Kaleido not working).")
                c.setFillGray(0)
                y -= 18

    c.save()
    buf.seek(0)
    return buf.read()


# -----------------------------
# PPT Export (EC-AI Insights Pack, 16:9)
# -----------------------------
def ppt_set_widescreen(prs: Presentation):
    prs.slide_width = Inches(13.333)   # 16:9
    prs.slide_height = Inches(7.5)


def add_title(prs: Presentation, title: str, subtitle: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = subtitle

    title_tf = slide.shapes.title.text_frame
    title_tf.paragraphs[0].font.size = Pt(40)
    title_tf.paragraphs[0].font.bold = True

    subtitle_tf = slide.placeholders[1].text_frame
    subtitle_tf.paragraphs[0].font.size = Pt(18)


def add_chart_slide(prs: Presentation, title: str, fig: go.Figure, bullets: List[str]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # title only
    slide.shapes.title.text = title

    t = slide.shapes.title.text_frame
    t.paragraphs[0].font.size = Pt(28)
    t.paragraphs[0].font.bold = True

    png = fig_to_png_bytes(fig, scale=2)
    if png:
        img_stream = io.BytesIO(png)
        slide.shapes.add_picture(img_stream, Inches(0.7), Inches(1.2), width=Inches(8.2))

    left, top, width, height = Inches(9.2), Inches(1.3), Inches(3.9), Inches(5.8)
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True

    cleaned = [strip_machine_marks(b) for b in bullets][:6]
    for i, b in enumerate(cleaned):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = b
        p.font.size = Pt(16)
        p.font.color.rgb = RGBColor(17, 24, 39)
        p.space_after = Pt(6)

    footer = slide.shapes.add_textbox(Inches(0.7), Inches(7.05), Inches(12.6), Inches(0.35))
    ftf = footer.text_frame
    fp = ftf.paragraphs[0]
    fp.text = "EC-AI Insight — CEO-grade brief (v1)"
    fp.font.size = Pt(10)
    fp.font.color.rgb = RGBColor(107, 114, 128)


def make_ppt_insights_pack(
    title: str,
    subtitle: str,
    summary_bullets: List[str],
    chart_items: List[Tuple[str, go.Figure, List[str]]],
) -> bytes:
    prs = Presentation()
    ppt_set_widescreen(prs)

    add_title(prs, title, subtitle)

    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Business Summary (CEO-grade)"
    t = slide.shapes.title.text_frame
    t.paragraphs[0].font.size = Pt(28)
    t.paragraphs[0].font.bold = True

    box = slide.shapes.add_textbox(Inches(0.9), Inches(1.4), Inches(12.0), Inches(5.8))
    tf = box.text_frame
    tf.word_wrap = True
    for i, b in enumerate([strip_machine_marks(x) for x in summary_bullets[:12]]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "• " + b
        p.font.size = Pt(18)
        p.font.color.rgb = RGBColor(17, 24, 39)
        p.space_after = Pt(6)

    for chart_title, fig, bullets in chart_items:
        add_chart_slide(prs, chart_title, fig, bullets)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()


# -----------------------------
# Interaction: Ask EC-AI
# -----------------------------
def render_ask_ecai(context_text: str):
    st.markdown("### Ask EC-AI (interactive)")
    st.markdown(
        "<div class='ec-subtle'>Ask a question about your data. Example: “Which stores should I focus on next week and why?”</div>",
        unsafe_allow_html=True,
    )

    q = st.text_input("Your question", placeholder="E.g. Where is revenue concentrated, and what should I do next?")
    use_ai = st.checkbox("Use AI (OpenAI key required)", value=False)

    if st.button("Answer"):
        if not q.strip():
            st.warning("Please enter a question.")
            return

        if not use_ai:
            st.success("Answer (rule-based)")
            ql = q.lower()
            if "store" in ql or "location" in ql:
                st.write("Focus on the top revenue stores first — they drive a disproportionate share of revenue. Protect inventory and staffing there, then fix volatility in the most unstable store.")
            elif "discount" in ql or "pricing" in ql or "promotion" in ql:
                st.write("Moderate discounts tend to perform better than aggressive ones. Use revenue per sale as the guardrail metric and treat deep discounts as controlled experiments.")
            elif "risk" in ql or "volatile" in ql:
                st.write("Reduce volatility before pushing growth — inconsistent performance is often operational (stock, staffing, execution). Stabilize first, then scale what’s repeatable.")
            else:
                st.write("Start with concentration, stability, and pricing effectiveness. Improve execution in the top stores, reduce volatility, then scale what works.")
            st.caption("Enable AI later when you add your API key in Streamlit Secrets.")
            return

        try:
            import os
            from openai import OpenAI

            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                try:
                    api_key = st.secrets.get("OPENAI_API_KEY", None)
                except Exception:
                    api_key = None

            if not api_key:
                st.error("No OPENAI_API_KEY found. Add it to Streamlit Secrets or environment variables.")
                return

            client = OpenAI(api_key=api_key)
            prompt = f"""
You are EC-AI Insight, a CEO-grade analytics assistant.
Answer using concrete examples, numbers, and action steps.
Avoid jargon and avoid machine formatting.
If data is missing, say what is missing and give the best next step.

Context:
{context_text}

User question:
{q}

Answer format:
- 3 bullet summary (what it means)
- 3 bullet actions (what to do next week)
- 1 risk note
"""
            with st.spinner("Thinking..."):
                resp = client.responses.create(
                    model="gpt-4.1-mini",
                    input=prompt
                )
            st.success("Answer (AI)")
            st.write(resp.output_text.strip())
        except Exception as e:
            st.error(f"AI answer failed: {e}")


# -----------------------------
# Main App
# -----------------------------
def main():
    st.title(APP_TITLE)
    st.markdown(f"<div class='ec-subtle'>{APP_TAGLINE}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='ec-subtle'>{APP_SUBTITLE}</div>", unsafe_allow_html=True)
    st.markdown("---")

    with st.sidebar:
        st.markdown("### Mode")
        mode = st.radio("View", ["Executive (default)", "Advanced"], index=0)
        executive = (mode == "Executive (default)")

        st.markdown("### What to show")
        sections = ["Business Summary", "Business Insights", "Key Charts", "Further Analysis", "Ask EC-AI", "Exports"]
        default_sections = ["Business Summary", "Business Insights", "Key Charts", "Exports"] if executive else sections
        show_sections = st.multiselect("Sections", sections, default=default_sections)

        st.markdown("### Data upload")
        file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

        st.markdown("---")
        st.markdown("### Why EC-AI (vs ChatGPT / Google Analytics)")
        st.caption("EC-AI gives you: (1) a CEO-grade brief instantly, (2) consistent structure every time, (3) charts + export packs, (4) optional Q&A trained on your uploaded data.")
        st.caption("ChatGPT is great, but it does not automatically compute your KPIs, build the charts, and generate a structured executive brief + slides you can share.")

    if not file:
        st.info("Upload a dataset to generate your CEO-grade brief.")
        return

    try:
        if file.name.lower().endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    if df.empty or df.shape[0] < 3:
        st.warning("Dataset is empty or too small.")
        return

    cols = detect_columns(df)

    if not cols.get("revenue"):
        st.error("Missing required column: Revenue (or Sales/Amount). Rename your sales column to include 'revenue' or 'sales' or 'amount'.")
        st.write("Detected columns:", cols)
        return

    if cols.get("date"):
        df[cols["date"]] = coerce_date(df[cols["date"]])
    df[cols["revenue"]] = as_numeric(df[cols["revenue"]])

    if cols.get("qty"):
        df[cols["qty"]] = as_numeric(df[cols["qty"]])
    if cols.get("discount_rate"):
        df[cols["discount_rate"]] = as_numeric(df[cols["discount_rate"]])

    summary_bullets = build_business_summary(df, cols)
    insight_sections = build_business_insights(df, cols)

    plot_cfg = EXEC_PLOTLY_CONFIG if executive else ADV_PLOTLY_CONFIG

    # Core charts
    charts: List[Tuple[str, go.Figure, str]] = []
    f_trend = fig_revenue_trend(df, cols)
    if f_trend:
        charts.append(("Revenue Trend", f_trend, "Shows direction and highlights peak days. Investigate whether peaks come from promotions, events, or stock availability."))

    f_top = fig_top_stores(df, cols, top_n=5)
    if f_top:
        if cols.get("store"):
            store_rev = df.groupby(cols["store"])[cols["revenue"]].sum().sort_values(ascending=False)
            if len(store_rev) > 0:
                top_store, top_val = str(store_rev.index[0]), float(store_rev.iloc[0])
                charts.append(("Top Stores by Revenue", f_top, f"Your #1 store is {top_store} at {format_money(top_val)}. Protect inventory and staffing here first — it is your biggest lever."))
            else:
                charts.append(("Top Stores by Revenue", f_top, "Identifies the few stores that drive a disproportionate share of revenue. Focus execution here first."))
        else:
            charts.append(("Top Stores by Revenue", f_top, "Identifies the few stores that drive a disproportionate share of revenue. Focus execution here first."))

    f_stab = fig_store_stability(df, cols, top_n=5)
    if f_stab:
        charts.append(("Store Stability (Top 5)", f_stab, "Helps you spot which stores are steady vs volatile. Fix volatility before pushing growth; volatility is often operational (stock/staffing/execution)."))

    f_price = fig_pricing_effectiveness(df, cols)
    if f_price:
        charts.append(("Pricing Effectiveness", f_price, "Compares average revenue per sale by discount band. Moderate discounts often outperform aggressive ones — use deep discounts as controlled experiments."))

    # Further analysis
    fig_cat = fig_bar_top(df, cols, "category", "Revenue by Category (Top)", top_n=6)
    fig_ch = fig_bar_top(df, cols, "channel", "Revenue by Channel (Top)", top_n=6) if cols.get("channel") else None
    fig_pay = fig_bar_top(df, cols, "payment", "Revenue by Payment Method (Top)", top_n=6) if (not fig_ch and cols.get("payment")) else None
    fig_vol = fig_volatility_channel(df, cols)

    # Render
    if "Business Summary" in show_sections:
        st.markdown("## Business Summary")
        st.markdown("<ul class='ec-bullets'>" + "".join([f"<li>{b}</li>" for b in summary_bullets]) + "</ul>", unsafe_allow_html=True)

    if "Business Insights" in show_sections:
        st.markdown("## Business Insights (with concrete examples)")
        for section, bullets in insight_sections.items():
            st.markdown(f"<h3 class='ec-h3gap'>{section}</h3>", unsafe_allow_html=True)
            st.markdown("<ul class='ec-bullets'>" + "".join([f"<li>{b}</li>" for b in bullets]) + "</ul>", unsafe_allow_html=True)

    if "Key Charts" in show_sections:
        st.markdown("## Key Charts (curated)")
        for chart_title, fig, commentary in charts[:4]:
            st.markdown(f"### {chart_title}")
            st.plotly_chart(fig, use_container_width=True, config=plot_cfg)
            st.caption(commentary)

    if "Further Analysis" in show_sections:
        st.markdown("## Further Analysis (recommended)")
        c1, c2 = st.columns(2)
        with c1:
            if fig_cat:
                st.plotly_chart(fig_cat, use_container_width=True, config=plot_cfg)
                st.caption("Category view: focus attention where revenue is concentrated, then test improvements there first.")
        with c2:
            if fig_ch:
                st.plotly_chart(fig_ch, use_container_width=True, config=plot_cfg)
                st.caption("Channel view: compare performance across channels to decide where to invest marketing and operations.")
            elif fig_pay:
                st.plotly_chart(fig_pay, use_container_width=True, config=plot_cfg)
                st.caption("Payment-method view: can help explain customer behavior patterns.")

        if fig_vol:
            st.plotly_chart(fig_vol, use_container_width=True, config=plot_cfg)
            st.caption("Higher volatility = less predictable results. Stabilize first (often operational), then scale what’s repeatable.")

    if "Ask EC-AI" in show_sections:
        context_text = "Business Summary:\n" + "\n".join(["- " + b for b in summary_bullets]) + "\n\nBusiness Insights:\n"
        for sec, bullets in insight_sections.items():
            context_text += f"{sec}:\n" + "\n".join(["- " + x for x in bullets]) + "\n"
        render_ask_ecai(context_text)

    if "Exports" in show_sections:
        st.markdown("## Export Packs")
        st.markdown("<div class='ec-subtle'>PDF includes Summary + Insights + key charts with commentary. PPT is a 16:9 EC-AI Insights Pack with concrete bullets per slide.</div>", unsafe_allow_html=True)

        pdf_charts = charts[:4]

        # Build PPT bullets with concrete examples
        ppt_items: List[Tuple[str, go.Figure, List[str]]] = []
        if cols.get("store"):
            store_rev = df.groupby(cols["store"])[cols["revenue"]].sum().sort_values(ascending=False)
            top_store = str(store_rev.index[0]) if len(store_rev) else "Top store"
            top_val = float(store_rev.iloc[0]) if len(store_rev) else 0.0
            top2_share = top_n_share(store_rev, 2) if len(store_rev) else 0.0
            top_store_bullets = [
                f"Top store is {top_store} at {format_money(top_val)}.",
                f"Top 2 stores contribute ~{format_pct(top2_share)} of revenue — protect execution here first.",
                "Resource focus: prioritize inventory and staffing in the top stores, then replicate what works.",
            ]
        else:
            top_store_bullets = [
                "Revenue is concentrated in a small number of top stores.",
                "Focus execution and resources there first.",
                "Then fix volatility before scaling growth."
            ]

        pricing_bullets = [
            "Moderate discounts tend to perform better than aggressive ones.",
            "Use revenue per sale as the guardrail metric (not only volume).",
            "Treat deep discounts as controlled experiments with targets and stop rules.",
        ]

        for (t, f, _c) in pdf_charts:
            if "Top Stores" in t:
                ppt_items.append(("Top Revenue Stores", f, top_store_bullets))
            elif "Pricing" in t:
                ppt_items.append(("Pricing Effectiveness", f, pricing_bullets))
            elif "Stability" in t:
                ppt_items.append(("Store Stability", f, [
                    "Stability matters for planning and forecasting.",
                    "Fix volatility before pushing growth.",
                    "Volatility is often operational (stock/staffing/execution)."
                ]))
            else:
                ppt_items.append(("Revenue Trend", f, [
                    "Use this to spot spikes and slowdowns.",
                    "Investigate peak days: promotions, events, stock availability.",
                    "Build a weekly cadence around this chart."
                ]))

        colA, colB = st.columns(2)

        with colA:
            if st.button("Generate Executive Brief (PDF)"):
                try:
                    pdf_bytes = make_executive_brief_pdf(
                        title="EC-AI Executive Brief",
                        summary_bullets=summary_bullets,
                        insight_sections=insight_sections,
                        chart_items=pdf_charts,
                    )
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name="ecai_executive_brief.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"PDF export failed: {e}")

        with colB:
            if st.button("Generate EC-AI Insights Pack (PPT)"):
                try:
                    ppt_bytes = make_ppt_insights_pack(
                        title="EC-AI Insights Pack",
                        subtitle="CEO-grade snapshot of what’s working, what’s risky, and where to focus next.",
                        summary_bullets=summary_bullets,
                        chart_items=ppt_items,
                    )
                    st.download_button(
                        "Download PPT",
                        data=ppt_bytes,
                        file_name="ecai_insights_pack.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    )
                except Exception as e:
                    st.error(f"PPT export failed: {e}")

        with st.expander("Troubleshooting (internal)"):
            st.write("If exports fail:")
            st.write("- Ensure `kaleido` is installed and `plotly` is recent.")
            st.write("- Streamlit Cloud sometimes needs a redeploy after requirements changes.")
            st.write("- AI Q&A requires OPENAI_API_KEY in Streamlit Secrets.")

if __name__ == "__main__":
    main()
