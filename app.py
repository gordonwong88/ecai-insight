# EC-AI Insight — Executive Brief v1 (Streamlit)
# Author: Gordon Wong (EC-AI)
# Notes:
# - Executive-first UI (no advanced toggles)
# - Consultancy-grade charts (clean, readable, no zoom/modebar)
# - Business Summary + Business Insights include concrete examples (stores/categories/channels)
# - Optional "Ask EC-AI" Q&A (OpenAI if key provided; otherwise falls back to rules-based answers)
# - PDF/PPT exports include charts via Plotly->Kaleido (when available)

import io
import os
import json
import math
import textwrap
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

# Optional deps (exports / AI)
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except Exception:
    canvas = None

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
except Exception:
    Presentation = None

# OpenAI (optional)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# -----------------------------
# App config
# -----------------------------
st.set_page_config(
    page_title="EC-AI Insight",
    layout="wide",
    page_icon="📈",
)

# Plotly theme: clean & business-like
pio.templates.default = "plotly_white"

# Streamlit-wide CSS (executive feel)
st.markdown(
    """
<style>
:root{
  --ec-primary:#0f2a45;
  --ec-muted:#5b6b7a;
  --ec-border:#e6eaf0;
  --ec-bg:#f6f8fb;
  --ec-card:#ffffff;
}
.block-container { padding-top: 2.0rem; padding-bottom: 2.5rem; }
h1,h2,h3 { color: var(--ec-primary); }
p,li,span,div { color: #1f2d3d; }
.ec-hero {
  padding: 18px 20px; border:1px solid var(--ec-border); border-radius:16px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  box-shadow: 0 1px 0 rgba(12, 27, 54, 0.03);
}
.ec-subtle { color: var(--ec-muted); font-size: 0.95rem; }
.ec-pill {
  display:inline-block; padding:4px 10px; border-radius:999px;
  border:1px solid var(--ec-border); background: #fff;
  color: var(--ec-muted); font-size: 0.85rem; margin-right:6px;
}
.ec-card {
  border:1px solid var(--ec-border); border-radius:16px;
  background: var(--ec-card);
  padding: 14px 16px;
  box-shadow: 0 1px 0 rgba(12, 27, 54, 0.03);
}
.ec-section { margin-top: 8px; }
.ec-h3 { margin: 0 0 6px 0; font-size: 1.05rem; color: var(--ec-primary); }
.ec-bullets li { margin: 0.25rem 0; }
small { color: var(--ec-muted); }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Helpers
# -----------------------------
PALETTE = ["#5B7FFF", "#FF8A3D", "#E85D5D", "#39BFA6", "#A06AFB", "#F2C14E", "#2EA3F2"]

PLOTLY_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": "reset",
    "showTips": False,
    "responsive": True,
}


def _safe_float(x) -> Optional[float]:
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def fmt_money(x: float, currency: str = "$") -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    x = float(x)
    absx = abs(x)
    if absx >= 1_000_000:
        return f"{currency}{x/1_000_000:,.2f}M"
    if absx >= 1_000:
        return f"{currency}{x/1_000:,.1f}K"
    return f"{currency}{x:,.0f}"


def fmt_pct(x: float, digits: int = 0) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    return f"{x*100:.{digits}f}%"


def guess_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    # fuzzy contains
    for cand in candidates:
        for c in df.columns:
            if cand.lower() in str(c).lower():
                return c
    return None


def to_datetime_series(s: pd.Series) -> Optional[pd.Series]:
    try:
        out = pd.to_datetime(s, errors="coerce", utc=False)
        if out.notna().sum() >= max(3, int(0.6 * len(s))):
            return out
        return None
    except Exception:
        return None


def ensure_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")


def top_n_table(df: pd.DataFrame, group_col: str, value_col: str, n: int = 5) -> pd.DataFrame:
    t = df.groupby(group_col, dropna=False)[value_col].sum().sort_values(ascending=False).head(n).reset_index()
    t.columns = [group_col, value_col]
    return t


def compute_volatility(df: pd.DataFrame, date_col: str, group_col: str, value_col: str) -> pd.DataFrame:
    # volatility = std / mean of daily totals per group (CV)
    tmp = df[[date_col, group_col, value_col]].dropna()
    if tmp.empty:
        return pd.DataFrame(columns=[group_col, "cv", "mean_daily", "std_daily"])
    tmp = tmp.copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col]).dt.date
    daily = tmp.groupby([date_col, group_col])[value_col].sum().reset_index()
    agg = daily.groupby(group_col)[value_col].agg(["mean", "std"]).reset_index()
    agg["cv"] = agg["std"] / agg["mean"].replace({0: np.nan})
    agg.rename(columns={"mean": "mean_daily", "std": "std_daily"}, inplace=True)
    return agg.sort_values("cv", ascending=False)


def local_business_qa(question: str, context: Dict) -> str:
    q = (question or "").lower().strip()
    if not q:
        return "Ask a specific question (e.g., “Which store should I prioritize?”)."

    # simple heuristics using context
    top_store = context.get("top_store_name")
    top_store_rev = context.get("top_store_rev")
    top_cat = context.get("top_cat_name")
    top_cat_rev = context.get("top_cat_rev")

    if "which store" in q or "prioritize" in q:
        if top_store:
            return f"Prioritize {top_store} first — it is your #1 revenue driver ({fmt_money(top_store_rev)}). Protect staffing and inventory here before trying new growth experiments."
        return "I can’t identify a top store from this file — please ensure you have a Store column and a Revenue column."
    if "discount" in q or "promotion" in q:
        best_band = context.get("best_discount_band")
        best_band_val = context.get("best_discount_val")
        if best_band:
            return f"Your data suggests {best_band} discounts perform best on average (≈ {fmt_money(best_band_val)} revenue per sale). Treat deeper discounts as controlled tests with clear targets."
        return "I didn’t detect a discount column — if you have Discount_Rate, include it and I’ll assess pricing effectiveness."
    if "category" in q:
        if top_cat:
            return f"Your top category is {top_cat} ({fmt_money(top_cat_rev)}). Start by improving availability and merchandising for this category in your top stores."
        return "I can’t identify categories from this file — please include a Category column."
    if "risk" in q or "volatile" in q or "stability" in q:
        most_volatile = context.get("most_volatile_name")
        most_volatile_cv = context.get("most_volatile_cv")
        if most_volatile:
            return f"Watch {most_volatile}: it shows the biggest day-to-day swings (volatility score ≈ {most_volatile_cv:.2f}). Volatility usually points to operational inconsistency (stock, staffing, execution)."
        return "I can’t compute volatility without Date + Store/Channel + Revenue."
    return "I can answer questions about stores, categories, channels, discounts, trends, and where to focus next. Try: “What should I focus on next week?”"


def openai_answer(question: str, context: Dict, api_key: str) -> str:
    if OpenAI is None:
        return local_business_qa(question, context)
    try:
        client = OpenAI(api_key=api_key)
        # Keep prompt short & CEO-grade
        prompt = {
            "role": "system",
            "content": (
                "You are EC-AI, a concise business analyst. "
                "Answer in a CEO-grade style: short, direct, concrete numbers, actionable next steps. "
                "No technical jargon, no equations, no markdown."
            ),
        }
        user = {
            "role": "user",
            "content": f"Question: {question}\n\nContext (facts): {json.dumps(context, ensure_ascii=False)}\n\nAnswer:",
        }
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[prompt, user],
            temperature=0.2,
            max_tokens=220,
        )
        return (resp.choices[0].message.content or "").strip() or local_business_qa(question, context)
    except Exception:
        return local_business_qa(question, context)


def fig_bar_single_trace(
    x: List[str],
    y: List[float],
    title: str,
    y_title: str,
    x_title: str = "",
    colors: Optional[List[str]] = None,
    height: int = 360,
    text_fmt: str = "money",
) -> go.Figure:
    colors = colors or PALETTE
    bar_colors = [colors[i % len(colors)] for i in range(len(x))]

    if text_fmt == "money":
        text = [fmt_money(v) for v in y]
    elif text_fmt == "pct":
        text = [fmt_pct(v, 0) for v in y]
    else:
        text = [f"{v:,.2f}" for v in y]

    fig = go.Figure(
        data=[
            go.Bar(
                x=x,
                y=y,
                marker=dict(color=bar_colors),
                text=text,
                textposition="outside",
                cliponaxis=False,
                hovertemplate=f"{x_title or 'Item'}=%{{x}}<br>{y_title}=%{{y:,.2f}}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=18)),
        height=height,
        margin=dict(l=50, r=30, t=60, b=55),
        bargap=0.45,
        yaxis=dict(title=y_title, gridcolor="rgba(16,24,40,0.08)", zeroline=False),
        xaxis=dict(
            title=x_title,
            type="category",
            tickmode="array",
            tickvals=x,
            ticktext=x,
            tickfont=dict(size=12),
            automargin=True,
        ),
        font=dict(size=13, color="#1f2d3d"),
    )
    # ensure labels not cut off
    fig.update_yaxes(range=[0, max(y) * 1.18 if len(y) else 1])
    return fig


def fig_line_trend(df: pd.DataFrame, date_col: str, value_col: str, title: str, height: int = 330) -> go.Figure:
    tmp = df[[date_col, value_col]].dropna().copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col])
    daily = tmp.groupby(pd.Grouper(key=date_col, freq="D"))[value_col].sum().reset_index()
    daily = daily.sort_values(date_col)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily[date_col],
            y=daily[value_col],
            mode="lines+markers",
            line=dict(width=3, color="#39BFA6"),
            marker=dict(size=6, color="#39BFA6"),
            hovertemplate="%{x|%Y-%m-%d}<br>Revenue=%{y:,.0f}<extra></extra>",
        )
    )

    # label top 2 peaks (CEO-friendly)
    if len(daily) >= 5:
        peaks = daily.nlargest(2, value_col)
        for _, row in peaks.iterrows():
            fig.add_annotation(
                x=row[date_col],
                y=row[value_col],
                text=fmt_money(row[value_col]),
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-28,
                font=dict(size=12, color="#0f2a45"),
            )

    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=18)),
        height=height,
        margin=dict(l=50, r=30, t=60, b=55),
        yaxis=dict(title="Revenue", gridcolor="rgba(16,24,40,0.08)", zeroline=False),
        xaxis=dict(title="", gridcolor="rgba(16,24,40,0.04)", automargin=True),
        font=dict(size=13, color="#1f2d3d"),
    )
    return fig


# -----------------------------
# Data schema (robust, no dataclasses)
# -----------------------------
class Schema:
    def __init__(self, **kwargs):
        # core
        self.col_date = kwargs.get("col_date")
        self.col_store = kwargs.get("col_store")
        self.col_category = kwargs.get("col_category")
        self.col_channel = kwargs.get("col_channel")
        self.col_revenue = kwargs.get("col_revenue")
        # optional
        self.col_discount = kwargs.get("col_discount")  # 0-1 or 0-100
        self.col_qty = kwargs.get("col_qty")
        self.currency = kwargs.get("currency", "$")


def infer_schema(df: pd.DataFrame) -> Schema:
    col_date = guess_column(df, ["date", "order_date", "transaction_date", "day"])
    col_store = guess_column(df, ["store", "branch", "location", "shop"])
    col_category = guess_column(df, ["category", "product_category", "segment"])
    col_channel = guess_column(df, ["channel", "payment", "payment_method", "source"])
    col_revenue = guess_column(df, ["revenue", "sales", "amount", "total", "net_sales"])
    col_discount = guess_column(df, ["discount_rate", "discount", "promo", "promotion"])
    col_qty = guess_column(df, ["qty", "quantity", "units", "unit"])

    # Try to auto-detect date column if not found
    if col_date is None:
        for c in df.columns:
            ds = to_datetime_series(df[c])
            if ds is not None:
                col_date = c
                break

    return Schema(
        col_date=col_date,
        col_store=col_store,
        col_category=col_category,
        col_channel=col_channel,
        col_revenue=col_revenue,
        col_discount=col_discount,
        col_qty=col_qty,
        currency="$",
    )


def validate_minimum(schema: Schema) -> Tuple[bool, str]:
    missing = []
    if not schema.col_revenue:
        missing.append("Revenue")
    if not schema.col_date:
        missing.append("Date")
    if not schema.col_store:
        missing.append("Store")
    if missing:
        return False, "Missing required fields: " + ", ".join(missing) + ". Please include these columns (any naming is OK)."
    return True, ""


# -----------------------------
# Executive brief computation
# -----------------------------
def compute_context(df: pd.DataFrame, schema: Schema) -> Dict:
    df = df.copy()

    # parse & coerce
    df[schema.col_revenue] = ensure_numeric(df, schema.col_revenue).fillna(0)
    df[schema.col_date] = pd.to_datetime(df[schema.col_date], errors="coerce")
    df = df.dropna(subset=[schema.col_date])

    total_rev = float(df[schema.col_revenue].sum())
    n_rows = int(len(df))
    n_days = int(df[schema.col_date].dt.date.nunique())

    # top stores
    top_store_tbl = top_n_table(df, schema.col_store, schema.col_revenue, n=5) if schema.col_store else pd.DataFrame()
    top_store_name = top_store_tbl.iloc[0][schema.col_store] if len(top_store_tbl) else None
    top_store_rev = float(top_store_tbl.iloc[0][schema.col_revenue]) if len(top_store_tbl) else None
    top2_rev = float(top_store_tbl.head(2)[schema.col_revenue].sum()) if len(top_store_tbl) >= 2 else None
    top2_share = (top2_rev / total_rev) if (top2_rev is not None and total_rev > 0) else None
    top_store_share = (top_store_rev / total_rev) if (top_store_rev is not None and total_rev > 0) else None

    # categories
    top_cat_tbl = top_n_table(df, schema.col_category, schema.col_revenue, n=5) if schema.col_category else pd.DataFrame()
    top_cat_name = top_cat_tbl.iloc[0][schema.col_category] if len(top_cat_tbl) else None
    top_cat_rev = float(top_cat_tbl.iloc[0][schema.col_revenue]) if len(top_cat_tbl) else None
    top_cat_share = (top_cat_rev / total_rev) if (top_cat_rev is not None and total_rev > 0) else None

    # channels
    top_ch_tbl = top_n_table(df, schema.col_channel, schema.col_revenue, n=5) if schema.col_channel else pd.DataFrame()
    top_ch_name = top_ch_tbl.iloc[0][schema.col_channel] if len(top_ch_tbl) else None
    top_ch_rev = float(top_ch_tbl.iloc[0][schema.col_revenue]) if len(top_ch_tbl) else None
    top_ch_share = (top_ch_rev / total_rev) if (top_ch_rev is not None and total_rev > 0) else None

    # trend momentum
    daily = df.groupby(pd.Grouper(key=schema.col_date, freq="D"))[schema.col_revenue].sum().reset_index()
    daily = daily.sort_values(schema.col_date)
    half = max(1, len(daily) // 2)
    first_half = float(daily.head(half)[schema.col_revenue].sum())
    second_half = float(daily.tail(len(daily) - half)[schema.col_revenue].sum())
    momentum = (second_half / first_half - 1.0) if first_half > 0 else None

    # volatility
    vol_tbl = compute_volatility(df, schema.col_date, schema.col_store, schema.col_revenue) if schema.col_store else pd.DataFrame()
    most_volatile_name = vol_tbl.iloc[0][schema.col_store] if len(vol_tbl) else None
    most_volatile_cv = float(vol_tbl.iloc[0]["cv"]) if len(vol_tbl) and pd.notna(vol_tbl.iloc[0]["cv"]) else None

    # discount effectiveness: avg revenue per transaction by discount band
    best_discount_band = None
    best_discount_val = None
    discount_band_tbl = None
    if schema.col_discount:
        disc = pd.to_numeric(df[schema.col_discount], errors="coerce")
        disc = disc.fillna(0.0)
        # normalize 0-1 vs 0-100
        if disc.max() > 1.5:
            disc = disc / 100.0
        disc = disc.clip(lower=0, upper=1)
        df["_disc_norm"] = disc
        bins = [0, 0.02, 0.05, 0.10, 0.15, 0.20, 1.0]
        labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
        df["_disc_band"] = pd.cut(df["_disc_norm"], bins=bins, labels=labels, include_lowest=True, right=True)
        band = df.groupby("_disc_band")[schema.col_revenue].mean().reset_index()
        band.columns = ["band", "avg_rev"]
        band = band.dropna(subset=["band"])
        discount_band_tbl = band
        if len(band):
            best = band.sort_values("avg_rev", ascending=False).iloc[0]
            best_discount_band = str(best["band"])
            best_discount_val = float(best["avg_rev"])

    # Build context dict for AI and for insights (no markdown, clean)
    ctx = {
        "days_of_data": n_days,
        "transactions": n_rows,
        "total_revenue": round(total_rev, 2),
        "top_store_name": top_store_name,
        "top_store_rev": round(top_store_rev, 2) if top_store_rev is not None else None,
        "top_store_share": round(top_store_share, 4) if top_store_share is not None else None,
        "top2_rev": round(top2_rev, 2) if top2_rev is not None else None,
        "top2_share": round(top2_share, 4) if top2_share is not None else None,
        "top_cat_name": top_cat_name,
        "top_cat_rev": round(top_cat_rev, 2) if top_cat_rev is not None else None,
        "top_cat_share": round(top_cat_share, 4) if top_cat_share is not None else None,
        "top_channel_name": top_ch_name,
        "top_channel_rev": round(top_ch_rev, 2) if top_ch_rev is not None else None,
        "top_channel_share": round(top_ch_share, 4) if top_ch_share is not None else None,
        "momentum_second_half_vs_first": round(momentum, 4) if momentum is not None else None,
        "most_volatile_name": most_volatile_name,
        "most_volatile_cv": round(most_volatile_cv, 3) if most_volatile_cv is not None else None,
        "best_discount_band": best_discount_band,
        "best_discount_val": round(best_discount_val, 2) if best_discount_val is not None else None,
    }
    return ctx, top_store_tbl, top_cat_tbl, top_ch_tbl, vol_tbl, discount_band_tbl, daily


def build_business_summary(ctx: Dict) -> List[str]:
    # 10 CEO-grade bullets with concrete examples
    bullets = []

    bullets.append(f"You have {ctx.get('days_of_data', '—')} days of sales data across {ctx.get('transactions', '—')} transactions (total revenue {fmt_money(ctx.get('total_revenue'))}).")

    if ctx.get("top_store_name"):
        bullets.append(
            f"Revenue is concentrated: {ctx['top_store_name']} is your #1 store at {fmt_money(ctx.get('top_store_rev'))} ({fmt_pct(ctx.get('top_store_share'), 0)} of total)."
        )
    if ctx.get("top2_rev") is not None:
        bullets.append(
            f"The top 2 stores generate {fmt_money(ctx.get('top2_rev'))} (about {fmt_pct(ctx.get('top2_share'), 0)}). Small improvements here move the whole business."
        )

    if ctx.get("top_cat_name"):
        bullets.append(
            f"By category, {ctx['top_cat_name']} is your largest driver at {fmt_money(ctx.get('top_cat_rev'))} ({fmt_pct(ctx.get('top_cat_share'), 0)} of total)."
        )

    if ctx.get("top_channel_name"):
        bullets.append(
            f"By channel/payment, {ctx['top_channel_name']} contributes {fmt_money(ctx.get('top_channel_rev'))} ({fmt_pct(ctx.get('top_channel_share'), 0)})."
        )

    mom = ctx.get("momentum_second_half_vs_first")
    if mom is not None:
        direction = "more" if mom >= 0 else "less"
        bullets.append(f"Momentum: the second half of the period delivered about {fmt_pct(abs(mom), 0)} {direction} revenue than the first half.")

    if ctx.get("most_volatile_name") and ctx.get("most_volatile_cv") is not None:
        bullets.append(
            f"Stability: {ctx['most_volatile_name']} shows the biggest day-to-day swings (volatility score ≈ {ctx['most_volatile_cv']}). This usually signals operational inconsistency (stock, staffing, execution)."
        )

    if ctx.get("best_discount_band"):
        bullets.append(
            f"Discounting: {ctx['best_discount_band']} performs best on average (≈ {fmt_money(ctx.get('best_discount_val'))} revenue per sale). Bigger discounts do not automatically lead to better results."
        )

    bullets.append("Action focus: protect and improve the top stores first (availability, staffing, promotion discipline), then scale what works.")
    bullets.append("Next step: pick 1–2 levers to test for 2 weeks (pricing/discount guardrails, inventory availability, staffing coverage) and measure the uplift in revenue per sale.")

    # Ensure max 10–11 bullets (keep it executive)
    return bullets[:10]


def build_business_insights(ctx: Dict) -> Dict[str, List[str]]:
    # Concrete examples per bullet; no markdown
    s = []

    # Where money is made
    money = []
    if ctx.get("top_store_name"):
        money.append(f"Top store: {ctx['top_store_name']} contributes {fmt_money(ctx.get('top_store_rev'))} ({fmt_pct(ctx.get('top_store_share'), 0)}). This is your biggest lever — protect staffing and inventory here first.")
    if ctx.get("top2_rev") is not None:
        money.append(f"Concentration: your top 2 stores contribute about {fmt_pct(ctx.get('top2_share'), 0)} of total revenue. Prioritize execution in these locations before expanding campaigns elsewhere.")
    if ctx.get("top_cat_name"):
        money.append(f"Top category: {ctx['top_cat_name']} drives {fmt_money(ctx.get('top_cat_rev'))}. If you improve availability and merchandising here in top stores, it will move total revenue fastest.")
    if ctx.get("top_channel_name"):
        money.append(f"Top channel: {ctx['top_channel_name']} contributes {fmt_money(ctx.get('top_channel_rev'))}. Use this to decide where to invest your marketing and operational attention.")

    # Risk
    risk = []
    if ctx.get("most_volatile_name") and ctx.get("most_volatile_cv") is not None:
        risk.append(f"Volatility risk: {ctx['most_volatile_name']} has the highest variability (≈ {ctx['most_volatile_cv']}). This makes forecasting harder and can hide operational problems.")
    risk.append("Concentration risk: when revenue is dominated by a few stores, any execution slip (stock-outs, staffing gaps) materially impacts total results.")

    # Improve
    improve = []
    if ctx.get("best_discount_band"):
        improve.append(f"Pricing discipline: {ctx['best_discount_band']} performs best on average. Treat deep discounts as experiments — set a target and stop if revenue per sale does not improve.")
    improve.append("Execution beats campaigns: consistency (availability, staffing, service) usually delivers higher ROI than adding more promotions.")

    # Focus next
    next_ = []
    next_.append("Week 1: lock down top stores — confirm staffing coverage, shelf availability, and promotion quality.")
    next_.append("Week 2: test one pricing guardrail — cap discounts, compare revenue per sale between discount bands, and keep only what works.")

    return {
        "Where the money is made": money[:4],
        "Where risk exists": risk[:3],
        "What can be improved": improve[:3],
        "What to focus on next": next_[:3],
    }


# -----------------------------
# Exports (PDF / PPT)
# -----------------------------
def fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> Optional[bytes]:
    try:
        # Needs kaleido
        return fig.to_image(format="png", scale=scale)
    except Exception:
        return None


def make_executive_pdf(title: str, summary_bullets: List[str], insights: Dict[str, List[str]], chart_blocks: List[Tuple[str, Optional[bytes]]]) -> Optional[bytes]:
    if canvas is None:
        return None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    def draw_title(text, y):
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, y, text)

    def draw_section_header(text, y):
        c.setFont("Helvetica-Bold", 12.5)
        c.drawString(50, y, text)

    def draw_bullets(bullets, y, max_lines=999):
        c.setFont("Helvetica", 10.5)
        line_h = 14
        lines_used = 0
        for b in bullets:
            if lines_used >= max_lines:
                break
            wrapped = textwrap.wrap(str(b), width=95)
            for i, w in enumerate(wrapped):
                prefix = "• " if i == 0 else "  "
                c.drawString(55, y, prefix + w)
                y -= line_h
                lines_used += 1
                if y < 70:
                    c.showPage()
                    y = height - 60
                    c.setFont("Helvetica", 10.5)
        return y

    y = height - 55
    draw_title(title, y)
    y -= 28
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.35, 0.42, 0.48)
    c.drawString(50, y, f"Generated by EC-AI • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.setFillColorRGB(0, 0, 0)
    y -= 20

    draw_section_header("Business Summary", y)
    y -= 16
    y = draw_bullets(summary_bullets, y, max_lines=80)
    y -= 10

    draw_section_header("Business Insights", y)
    y -= 16
    for sec, bullets in insights.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, sec)
        y -= 14
        y = draw_bullets(bullets, y, max_lines=50)
        y -= 6
        if y < 140:
            c.showPage()
            y = height - 60

    # Charts
    draw_section_header("Key Charts", y)
    y -= 16
    for chart_title, png in chart_blocks:
        if y < 180:
            c.showPage()
            y = height - 60
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, chart_title)
        y -= 10
        if png:
            # roughly fit width
            img_w = 510
            img_h = 250
            c.drawInlineImage(io.BytesIO(png), 50, y - img_h, width=img_w, height=img_h)
            y -= (img_h + 18)
        else:
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.55, 0.55, 0.55)
            c.drawString(50, y, "(Chart image export unavailable in this environment.)")
            c.setFillColorRGB(0, 0, 0)
            y -= 22

    c.save()
    buf.seek(0)
    return buf.getvalue()


def make_ppt(title: str, slides: List[Tuple[str, str, Optional[bytes]]]) -> Optional[bytes]:
    if Presentation is None:
        return None

    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9
    prs.slide_height = Inches(7.5)

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # blank
    tx = slide.shapes.add_textbox(Inches(0.7), Inches(0.9), Inches(12), Inches(1.2)).text_frame
    p = tx.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = RGBColor(15, 42, 69)

    subtitle = slide.shapes.add_textbox(Inches(0.7), Inches(2.0), Inches(12), Inches(0.7)).text_frame
    p2 = subtitle.paragraphs[0]
    p2.text = "Executive insights pack"
    p2.font.size = Pt(16)
    p2.font.color.rgb = RGBColor(91, 107, 122)

    # Insight slides
    for s_title, s_body, png in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[5])  # blank
        # Header
        box = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(12), Inches(0.8)).text_frame
        p = box.paragraphs[0]
        p.text = s_title
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = RGBColor(15, 42, 69)

        # Chart
        if png:
            img_stream = io.BytesIO(png)
            slide.shapes.add_picture(img_stream, Inches(0.8), Inches(1.3), width=Inches(7.6))
        # Commentary
        body = slide.shapes.add_textbox(Inches(8.6), Inches(1.25), Inches(4.4), Inches(5.7)).text_frame
        body.word_wrap = True
        body.margin_left = 0
        body.margin_right = 0
        body.clear()
        bp = body.paragraphs[0]
        bp.text = s_body
        bp.font.size = Pt(14)
        bp.font.color.rgb = RGBColor(31, 45, 61)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.getvalue()


# -----------------------------
# UI
# -----------------------------
st.markdown(
    """
<div class="ec-hero">
  <div style="font-size:42px; font-weight:800; letter-spacing:-0.5px; color:#0f2a45;">EC-AI Insight</div>
  <div class="ec-subtle" style="margin-top:6px;">Sales performance, explained clearly.</div>
  <div class="ec-subtle" style="margin-top:2px;">Upload your sales data and get a short business briefing — what’s working, what’s risky, and where to focus next.</div>
  <div style="margin-top:10px;">
    <span class="ec-pill">Executive brief</span>
    <span class="ec-pill">Charts + commentary</span>
    <span class="ec-pill">PDF & PPT export</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")

# Sidebar: upload + AI key
with st.sidebar:
    st.markdown("### Upload data")
    uploaded = st.file_uploader("CSV or Excel", type=["csv", "xlsx", "xls"])
    st.markdown("---")
    st.markdown("### Ask EC-AI")
    st.caption("Optional: add an OpenAI key for deeper Q&A. If not provided, EC-AI uses rule-based answers.")
    api_key = st.text_input("OpenAI API key (optional)", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    st.caption("Using an API key may incur token costs from your OpenAI account.")
    st.markdown("---")
    st.markdown("### Report sections")
    # simple section toggles (Alice “I may only want to see what I care about”)
    default_sections = ["Business Summary", "Business Insights", "Key Charts", "Ask EC-AI"]
    if "sections" not in st.session_state:
        st.session_state["sections"] = default_sections.copy()
    sections = st.multiselect(
        "Choose what to show (saved for this session)",
        ["Business Summary", "Business Insights", "Key Charts", "Further Analysis", "Ask EC-AI"],
        default=st.session_state["sections"],
    )
    st.session_state["sections"] = sections

    # Save “fields” meaning: remember user selections
    st.download_button(
        "Download my view settings",
        data=json.dumps({"sections": sections}, indent=2).encode("utf-8"),
        file_name="ecai_view_settings.json",
        mime="application/json",
        help="Lets users save what they like to see and load it next time.",
    )

# Load settings
if uploaded is None:
    st.info("Upload a CSV/Excel file to begin.")
    st.stop()

# Read file
try:
    if uploaded.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

if df is None or df.empty:
    st.error("This file is empty.")
    st.stop()

schema = infer_schema(df)
ok, msg = validate_minimum(schema)
if not ok:
    st.error(msg)
    st.write("Detected columns:", list(df.columns))
    st.stop()

# Compute facts
ctx, top_store_tbl, top_cat_tbl, top_ch_tbl, vol_tbl, discount_band_tbl, daily = compute_context(df, schema)
summary_bullets = build_business_summary(ctx)
insights = build_business_insights(ctx)

# Create charts (freeze which charts stay in v1)
# 1) Revenue trend
fig_trend = fig_line_trend(df, schema.col_date, schema.col_revenue, "Revenue trend (daily)")

# 2) Top 5 stores
store_x = top_store_tbl[schema.col_store].astype(str).tolist()
store_y = top_store_tbl[schema.col_revenue].astype(float).tolist()
fig_top_stores = fig_bar_single_trace(
    x=store_x,
    y=store_y,
    title="Top stores by revenue (Top 5)",
    y_title="Revenue",
    x_title="Store",
    colors=PALETTE,
    height=380,
    text_fmt="money",
)

# 3) Discount effectiveness
fig_discount = None
discount_comment = ""
if discount_band_tbl is not None and len(discount_band_tbl):
    band_x = discount_band_tbl["band"].astype(str).tolist()
    band_y = discount_band_tbl["avg_rev"].astype(float).tolist()
    fig_discount = fig_bar_single_trace(
        x=band_x,
        y=band_y,
        title="Pricing effectiveness (average revenue per sale by discount band)",
        y_title="Avg revenue per sale",
        x_title="Discount band",
        colors=PALETTE,
        height=360,
        text_fmt="money",
    )
    discount_comment = f"Best-performing band: {ctx.get('best_discount_band')} (≈ {fmt_money(ctx.get('best_discount_val'))} per sale)."

# 4) Volatility by channel (if present)
fig_vol_channel = None
if schema.col_channel:
    # compute CV by channel using daily totals
    vch = compute_volatility(df, schema.col_date, schema.col_channel, schema.col_revenue)
    vch = vch.dropna(subset=["cv"])
    if len(vch):
        x = vch[schema.col_channel].astype(str).tolist()
        y = vch["cv"].astype(float).tolist()
        fig_vol_channel = fig_bar_single_trace(
            x=x,
            y=y,
            title="Volatility by channel (higher = less stable)",
            y_title="Volatility score (CV)",
            x_title="Channel",
            colors=PALETTE,
            height=340,
            text_fmt="num",
        )

# -----------------------------
# Main content
# -----------------------------
if "Business Summary" in sections:
    st.markdown("## Business Summary")
    st.markdown('<div class="ec-card"><ul class="ec-bullets">' + "".join([f"<li>{b}</li>" for b in summary_bullets]) + "</ul></div>", unsafe_allow_html=True)

if "Business Insights" in sections:
    st.markdown("## Business Insights")
    # add spacing between subheaders (your request)
    blocks = []
    for sec, bullets in insights.items():
        blocks.append(f"<div class='ec-section'><div class='ec-h3'>{sec}</div><ul class='ec-bullets'>" +
                      "".join([f"<li>{b}</li>" for b in bullets]) + "</ul></div>")
    st.markdown('<div class="ec-card">' + "".join(blocks) + "</div>", unsafe_allow_html=True)

if "Key Charts" in sections:
    st.markdown("## Key Charts")
    # 1) Trend
    st.plotly_chart(fig_trend, use_container_width=True, config=PLOTLY_CONFIG)
    st.caption("Use this to spot promotion spikes, slowdowns, and whether momentum is improving.")

    # 2) Top stores
    st.plotly_chart(fig_top_stores, use_container_width=True, config=PLOTLY_CONFIG)
    if ctx.get("top_store_name"):
        st.caption(f"Your #1 store is {ctx['top_store_name']} at {fmt_money(ctx.get('top_store_rev'))}. Protect inventory and staffing here first — it is your biggest lever.")

    # 3) Discount
    if fig_discount is not None:
        st.plotly_chart(fig_discount, use_container_width=True, config=PLOTLY_CONFIG)
        if discount_comment:
            st.caption(discount_comment)

    # 4) Volatility
    if fig_vol_channel is not None:
        st.plotly_chart(fig_vol_channel, use_container_width=True, config=PLOTLY_CONFIG)
        st.caption("High volatility often indicates inconsistent execution or supply issues. Stabilize first, then push growth.")

if "Further Analysis" in sections:
    st.markdown("## Further Analysis (optional)")
    # Simple tables (high-signal, CEO-friendly)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Top stores**")
        st.dataframe(top_store_tbl.rename(columns={schema.col_revenue: "Revenue"}), use_container_width=True)
    with c2:
        if schema.col_category and len(top_cat_tbl):
            st.markdown("**Top categories**")
            st.dataframe(top_cat_tbl.rename(columns={schema.col_revenue: "Revenue"}), use_container_width=True)
        else:
            st.info("No Category column detected.")
    with c3:
        if schema.col_channel and len(top_ch_tbl):
            st.markdown("**Top channels**")
            st.dataframe(top_ch_tbl.rename(columns={schema.col_revenue: "Revenue"}), use_container_width=True)
        else:
            st.info("No Channel/Payment column detected.")

if "Ask EC-AI" in sections:
    st.markdown("## Ask EC-AI")
    st.caption("Ask a business question like: “Which store should I prioritize?” or “What should I do next week?”")
    q = st.text_input("Your question", placeholder="e.g., Which store should I prioritize first?")
    if st.button("Ask"):
        if q.strip():
            if api_key:
                ans = openai_answer(q, ctx, api_key)
            else:
                ans = local_business_qa(q, ctx)
            st.markdown('<div class="ec-card">' + ans + "</div>", unsafe_allow_html=True)
        else:
            st.warning("Type a question first.")

# -----------------------------
# Exports (PDF & PPT)
# -----------------------------
st.markdown("## Export EC-AI Executive Brief")
st.caption("Includes Business Summary + Business Insights + selected charts. Charts require Kaleido for best results.")

chart_pngs = [
    ("Revenue trend (daily)", fig_to_png_bytes(fig_trend)),
    ("Top stores by revenue (Top 5)", fig_to_png_bytes(fig_top_stores)),
]
if fig_discount is not None:
    chart_pngs.append(("Pricing effectiveness (discount bands)", fig_to_png_bytes(fig_discount)))
if fig_vol_channel is not None:
    chart_pngs.append(("Volatility by channel", fig_to_png_bytes(fig_vol_channel)))

colA, colB = st.columns([1, 1])
with colA:
    if st.button("Generate PDF Executive Brief"):
        pdf_bytes = make_executive_pdf("EC-AI Executive Brief", summary_bullets, insights, chart_pngs)
        if pdf_bytes:
            st.download_button("Download PDF", data=pdf_bytes, file_name="ecai_executive_brief.pdf", mime="application/pdf")
        else:
            st.error("PDF export is unavailable (reportlab missing) or failed in this environment.")
with colB:
    if st.button("Generate PPT Insights Pack"):
        # Build a few insight slides with concrete commentary
        slides = []
        slides.append(("Revenue trend", "Spot spikes and slowdowns; if the last 2–3 weeks are trending up, scale what worked and repeat.", fig_to_png_bytes(fig_trend, scale=2)))
        if ctx.get("top_store_name"):
            slides.append(("Top stores", f"Your #1 store is {ctx['top_store_name']} at {fmt_money(ctx.get('top_store_rev'))}. Protect inventory and staffing here first — it moves total performance most.", fig_to_png_bytes(fig_top_stores, scale=2)))
        if fig_discount is not None and ctx.get("best_discount_band"):
            slides.append(("Pricing effectiveness", f"{ctx.get('best_discount_band')} performs best on average (≈ {fmt_money(ctx.get('best_discount_val'))} per sale). Bigger discounts do not automatically improve results — treat deep discount as controlled tests.", fig_to_png_bytes(fig_discount, scale=2)))
        if fig_vol_channel is not None:
            slides.append(("Channel volatility", "Stabilize the most volatile channel first. Volatility often means inconsistent execution or demand — fix operations before pushing growth.", fig_to_png_bytes(fig_vol_channel, scale=2)))

        ppt_bytes = make_ppt("EC-AI Insights Pack", slides)
        if ppt_bytes:
            st.download_button("Download PPT", data=ppt_bytes, file_name="ecai_insights_pack.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
        else:
            st.error("PPT export is unavailable (python-pptx missing) or failed in this environment.")
