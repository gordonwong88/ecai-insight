# EC-AI Insight — Retail Sales MVP (Founder-first)

def clean_display_text(s: str) -> str:
    """Clean model/AI text for on-screen executive readability.

    Goal: remove markdown/math artifacts and drop any corrupted fragments.
    """
    if not s:
        return s

    raw = s.strip()
    low = raw.lower()

    # Drop known corrupted fragments (example: '(1.7K **persale).Deepdiscount **10-201.1K).')
    if "persale" in low or "deepdiscount" in low:
        return ""

    # Remove common markdown / code artifacts
    s = raw
    s = s.replace("**", "").replace("*", "")
    s = s.replace("`", "").replace("```", "")
    s = s.replace("_", "")

    # Remove LaTeX-ish inline math: \( ... \) or $...$
    s = re.sub(r"\\\((.*?)\\\)", "", s)
    s = re.sub(r"\$[^\$]*\$", "", s)

    # Remove unmatched parentheses/brackets leftovers and repeated punctuation
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"[\[\]{}<>]", "", s)
    s = re.sub(r"[\.]{2,}", ".", s)

    # If the line is mostly symbols/numbers after cleaning, drop it
    letters = sum(ch.isalpha() for ch in s)
    if letters < 4:
        return ""

    # Normalize whitespace
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

import io
import os
import re
import textwrap
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

import plotly.graph_objects as go
import plotly.express as px

# Optional: Ask AI chat
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# -----------------------------
# Ask AI helpers (minimal, stable)
# -----------------------------
def _get_openai_api_key() -> str | None:
    try:
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY")


def answer_question_with_openai(question: str, context: str) -> str:
    """CEO-level Q&A based on provided context only."""
    api_key = _get_openai_api_key()
    if OpenAI is None or not api_key:
        return "Ask AI is not configured yet. Please add `OPENAI_API_KEY` in Streamlit Secrets."

    client = OpenAI(api_key=api_key)

    system = (
        "You are EC-AI, an executive analytics consultant. "
        "Respond in a CEO-ready style: Insight → Evidence → Action. "
        "Be concise, practical, and avoid jargon. "
        "Only use the provided context; if the answer isn't supported, say what's missing."
    )

    user = f"CONTEXT (from dashboard summary):\n{context}\n\nQUESTION:\n{question}"

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return f"Ask AI failed: {e}"


# Export deps (optional at runtime)
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.enums import TA_LEFT


# -----------------------------
# Page config + global styling
# -----------------------------
st.set_page_config(page_title="EC-AI Insight", layout="wide")

# Slightly larger, more executive typography.
st.markdown(
    """
<style>
/* Base */
html, body, [class*="css"]  { font-size: 16px; }
p, li { font-size: 16px; line-height: 1.55; }
small, .stCaption { font-size: 14px; }

/* Titles */
h1 { font-size: 40px !important; margin-bottom: 0.25rem; }
h2 { font-size: 26px !important; margin-top: 1.2rem; }
h3 { font-size: 20px !important; margin-top: 1.0rem; }
h4 { font-size: 18px !important; margin-top: 0.9rem; }

/* Extra spacing between subheaders + paragraphs */
.ec-space { margin-top: 10px; margin-bottom: 10px; }
.ec-tight { margin-top: 2px; margin-bottom: 2px; }
.ec-note { color: #555; font-size: 15px; }
.ec-kicker { color: #555; font-size: 18px; }
.ec-subtle { color: #666; font-size: 15px; }

/* Make expanders less cramped */
div[data-testid="stExpander"] > details { padding: 0.25rem 0.25rem 0.5rem 0.25rem; }
</style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Palette (Tableau-like)
# -----------------------------
TABLEAU10 = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"
]


# -----------------------------
# Consultancy-grade Plotly theme (applies to all charts)
# -----------------------------
def apply_consulting_theme(
    fig: go.Figure,
    *,
    title: str | None = None,
    height: int | None = None,
    y_is_currency: bool = False,
    y_is_pct: bool = False,
) -> go.Figure:
    """Make charts look like a clean executive deck (stable, consistent)."""
    if title is not None:
        fig.update_layout(title=dict(text=title, x=0.0, xanchor="left"))

    fig.update_layout(
        template="plotly_white",
        height=height or fig.layout.height or 380,
        margin=dict(l=48, r=26, t=62, b=52),
        font=dict(family="Inter, Arial, sans-serif", size=14, color="#111827"),
        title=dict(font=dict(size=18, color="#111827")),
        paper_bgcolor="white",
        plot_bgcolor="white",
        colorway=TABLEAU10,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12, color="#374151"),
        ),
    )

    fig.update_xaxes(
        title=None,
        showline=False,
        ticks="outside",
        tickfont=dict(size=12, color="#374151"),
        gridcolor="rgba(17,24,39,0.06)",
        zeroline=False,
    )
    fig.update_yaxes(
        title=None,
        showline=False,
        ticks="outside",
        tickfont=dict(size=12, color="#374151"),
        gridcolor="rgba(17,24,39,0.08)",
        zeroline=False,
    )

    if y_is_currency:
        # $1.2M style ticks
        fig.update_yaxes(tickprefix="$", tickformat=",.2s")
    elif y_is_pct:
        fig.update_yaxes(tickformat=".0%")

    # Cleaner hover
    fig.update_traces(hoverlabel=dict(font_size=12), hovertemplate=None)

    return fig


def safe_money(x: float) -> str:
    """Friendly money formatting without 'machine noise'."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    x = float(x)
    ax = abs(x)
    if ax >= 1_000_000_000:
        return f"${x/1_000_000_000:.2f}B"
    if ax >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    if ax >= 1_000:
        return f"${x/1_000:.1f}K"
    return f"${x:,.0f}"

def safe_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x*100:.0f}%"

def clean_col(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

# -----------------------------
# Column detection
# -----------------------------
CANDIDATES = {
    "date": ["date", "orderdate", "transactiondate", "salesdate", "invoice_date", "day"],
    "store": ["store", "store_name", "shop", "branch", "location", "outlet"],
    "revenue": ["revenue", "sales", "amount", "net_sales", "total", "total_sales", "gmv"],
    "category": ["category", "product_category", "dept", "department", "cat"],
    "channel": ["channel", "sales_channel", "platform", "source"],
    "payment": ["payment", "payment_method", "tender", "paymethod"],
    "discount": ["discount", "discount_rate", "disc", "discount_pct", "promo_discount"],
    "qty": ["qty", "quantity", "units", "unit_sold", "items"]
}

def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols = list(df.columns)
    norm = {clean_col(c): c for c in cols}
    out: Dict[str, Optional[str]] = {k: None for k in CANDIDATES.keys()}
    for key, cands in CANDIDATES.items():
        for cand in cands:
            cand_norm = clean_col(cand)
            # exact or substring
            for n, orig in norm.items():
                if n == cand_norm or cand_norm in n:
                    out[key] = orig
                    break
            if out[key] is not None:
                break
    # Fallback for revenue: choose first numeric col if none found
    if out["revenue"] is None:
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            out["revenue"] = num_cols[0]
    return out

# -----------------------------
# Data prep
# -----------------------------


# -----------------------------
# Formatting helpers
# -----------------------------
def fmt_currency(x: float) -> str:
    """Short currency format: $1.50M / $86.4K / $950."""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        x = float(x)
    except Exception:
        return "—"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000_000:
        return f"{sign}${x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:.1f}K"
    return f"{sign}${x:.0f}"

def fmt_pct(x: float, digits: int = 0) -> str:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        return f"{x*100:.{digits}f}%"
    except Exception:
        return "—"


def md_to_plain(s: str) -> str:
    """Remove simple Markdown markers for clean exports (PDF/PPT)."""
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    # Leave single * alone unless it's paired (avoid nuking multiplication signs in data)
    s = s.replace("**", "")
    return s

def md_to_plain_lines(s: str) -> List[str]:
    """Split into lines and clean markdown per-line, keeping newlines."""
    if s is None:
        return []
    lines = str(s).split("\n")
    out = []
    for line in lines:
        line = md_to_plain(line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            out.append(line)
    return out

@dataclass
class RetailModel:
    df: pd.DataFrame
    col_date: str
    col_store: str
    col_revenue: str
    col_category: Optional[str] = None
    col_channel: Optional[str] = None
    col_payment: Optional[str] = None
    col_discount: Optional[str] = None
    col_qty: Optional[str] = None

def prep_retail(df_raw: pd.DataFrame) -> RetailModel:
    df = df_raw.copy()

    cols = detect_columns(df)
    # Minimal requirements
    if cols["date"] is None:
        # try parse index as date?
        raise ValueError("Could not detect a Date column. Please ensure your file includes a date field (e.g., Date, OrderDate).")
    if cols["revenue"] is None:
        raise ValueError("Could not detect a Revenue/Sales column. Please ensure your file includes a numeric revenue field (e.g., Revenue, Sales, Amount).")

    col_date = cols["date"]
    col_store = cols["store"] or "__store__"
    col_revenue = cols["revenue"]

    # Create a default store if missing
    if cols["store"] is None:
        df[col_store] = "All Stores"

    # Parse dates
    df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
    df = df.dropna(subset=[col_date])

    # Revenue numeric
    df[col_revenue] = pd.to_numeric(df[col_revenue], errors="coerce")
    df = df.dropna(subset=[col_revenue])

    # Optional numeric
    col_qty = cols["qty"]
    if col_qty is not None:
        df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce")

    # Discount normalize: accept 0-1 or 0-100
    col_discount = cols["discount"]
    if col_discount is not None:
        df[col_discount] = pd.to_numeric(df[col_discount], errors="coerce")
        # If looks like percent 0-100
        s = df[col_discount].dropna()
        if len(s) > 0 and s.quantile(0.95) > 1.5:
            df[col_discount] = df[col_discount] / 100.0
        df[col_discount] = df[col_discount].clip(lower=0, upper=1)

    # Trim string columns
    for k in ["store", "category", "channel", "payment"]:
        c = cols.get(k)
        if c is not None:
            df[c] = df[c].astype(str).str.strip()

    # Keep only useful columns
    return RetailModel(
        df=df,
        col_date=col_date,
        col_store=col_store,
        col_revenue=col_revenue,
        col_category=cols["category"],
        col_channel=cols["channel"],
        col_payment=cols["payment"],
        col_discount=col_discount,
        col_qty=col_qty,
    )

# -----------------------------
# Insight helpers (human tone)
# -----------------------------
def build_business_summary_points(m: RetailModel) -> List[str]:
    """Founder-facing summary: concrete, human, and includes examples."""
    df = m.df
    dmin, dmax = df[m.col_date].min(), df[m.col_date].max()
    days = max((dmax - dmin).days + 1, 1)

    total_rev = float(df[m.col_revenue].sum())
    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)
    cat_rev = df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False) if m.col_category else pd.Series(dtype=float)

    top_store = str(store_rev.index[0]) if len(store_rev) else "—"
    top_store_rev = float(store_rev.iloc[0]) if len(store_rev) else np.nan
    top_store_share = (top_store_rev / total_rev) if total_rev > 0 and len(store_rev) else np.nan

    top2_rev = float(store_rev.iloc[:2].sum()) if len(store_rev) >= 2 else np.nan
    top2_share = (top2_rev / total_rev) if total_rev > 0 and len(store_rev) >= 2 else np.nan

    top_cat = str(cat_rev.index[0]) if len(cat_rev) else None
    top_cat_rev = float(cat_rev.iloc[0]) if len(cat_rev) else np.nan
    top_cat_share = (top_cat_rev / total_rev) if total_rev > 0 and len(cat_rev) else np.nan

    # Trend: first half vs second half
    df_sorted = df.sort_values(m.col_date)
    mid = df_sorted[m.col_date].min() + pd.Timedelta(days=days / 2)
    rev_first = float(df_sorted.loc[df_sorted[m.col_date] <= mid, m.col_revenue].sum())
    rev_second = float(df_sorted.loc[df_sorted[m.col_date] > mid, m.col_revenue].sum())
    growth = (rev_second - rev_first) / rev_first if rev_first > 0 else np.nan

    # Volatility proxy: daily revenue std / mean by store
    daily = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol = daily.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol["ratio"] = vol["std"] / vol["mean"]
    most_volatile_store = str(vol["ratio"].sort_values(ascending=False).index[0]) if len(vol) else None
    most_volatile_score = float(vol.loc[most_volatile_store, "ratio"]) if most_volatile_store in vol.index else np.nan

    # Discount effectiveness
    best_band = worst_band = None
    best_avg = worst_avg = np.nan
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 20:
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            agg = tmp.groupby("disc_band")[m.col_revenue].mean()
            if agg.notna().sum() >= 2:
                best_band = str(agg.sort_values(ascending=False).index[0])
                best_avg = float(agg.loc[best_band])
                worst_band = str(agg.sort_values(ascending=True).index[0])
                worst_avg = float(agg.loc[worst_band])

    points: List[str] = []

    # 1) Big picture
    points.append(f"You have **{days} days** of data with **{len(df):,} transactions** (total revenue **{fmt_currency(total_rev)}**).")

    # 2) Concentration
    if not np.isnan(top_store_share):
        points.append(f"Revenue is concentrated: **{top_store}** contributes **{fmt_currency(top_store_rev)}** (about **{fmt_pct(top_store_share, 0)}** of total).")

    if not np.isnan(top2_share):
        points.append(f"The **top 2 stores** together generate **{fmt_currency(top2_rev)}** (about **{fmt_pct(top2_share, 0)}**). Small wins in these locations move the whole business.")

    # 3) Category mix
    if top_cat is not None and not np.isnan(top_cat_share):
        points.append(f"By category, **{top_cat}** is your largest driver: **{fmt_currency(top_cat_rev)}** (about **{fmt_pct(top_cat_share, 0)}**).")

    # 4) Momentum
    if not np.isnan(growth):
        if growth > 0.03:
            points.append(f"Momentum is positive: the second half of the period delivered about **{fmt_pct(growth, 0)}** more revenue than the first half.")
        elif growth < -0.03:
            points.append(f"Momentum is softer: the second half of the period delivered about **{fmt_pct(growth, 0)}** less revenue than the first half.")
        else:
            points.append("Overall revenue looks broadly stable across the period (no major shift between first vs second half).")

    # 5) Stability / predictability
    if most_volatile_store is not None and not np.isnan(most_volatile_score):
        points.append(f"Day-to-day sales are not equally predictable. **{most_volatile_store}** shows the biggest swings (variability score ≈ **{most_volatile_score:.2f}**).")

    # 6) Discount discipline
    if best_band is not None and worst_band is not None:
        points.append(f"Discounting: **{best_band}** performs best on average (**{fmt_currency(best_avg)}** per sale). Deep discount **{worst_band}** underperforms (**{fmt_currency(worst_avg)}**).")
        points.append("Takeaway: moderate discounts tend to work better than aggressive ones — bigger discounts do not automatically lead to better results.")

    # 7) Next focus
    points.append("Next focus: protect and improve the top stores first (availability, staffing, promotion discipline), then scale what works.")

    # Keep it tight
    return points[:12]




def build_business_insights_sections(m: RetailModel) -> Dict[str, List[str]]:
    """Business Insights with concrete examples (names + numbers)."""
    df = m.df
    total_rev = float(df[m.col_revenue].sum())

    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)
    top_store = str(store_rev.index[0]) if len(store_rev) else "—"
    top_store_rev = float(store_rev.iloc[0]) if len(store_rev) else np.nan

    top2 = store_rev.head(2)
    top2_share = float(top2.sum() / total_rev) if total_rev > 0 and len(top2) else np.nan

    # Category / channel drivers
    cat_rev = df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False) if m.col_category else pd.Series(dtype=float)
    top_cat = str(cat_rev.index[0]) if len(cat_rev) else None
    top_cat_rev = float(cat_rev.iloc[0]) if len(cat_rev) else np.nan

    channel_rev = df.groupby(m.col_channel)[m.col_revenue].sum().sort_values(ascending=False) if m.col_channel else pd.Series(dtype=float)
    top_channel = str(channel_rev.index[0]) if len(channel_rev) else None
    top_channel_rev = float(channel_rev.iloc[0]) if len(channel_rev) else np.nan

    # Stability: daily CV per store + per channel
    daily_store = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol_store = daily_store.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol_store["cv"] = vol_store["std"] / vol_store["mean"]
    vol_store = vol_store.dropna(subset=["cv"]).sort_values("cv", ascending=False)
    most_volatile_store = str(vol_store.index[0]) if len(vol_store) else None
    most_volatile_cv = float(vol_store.iloc[0]["cv"]) if len(vol_store) else np.nan

    daily_chan = None
    most_volatile_chan = None
    most_volatile_chan_cv = np.nan
    if m.col_channel:
        daily_chan = df.groupby([m.col_channel, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
        vol_chan = daily_chan.groupby(m.col_channel)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
        vol_chan["cv"] = vol_chan["std"] / vol_chan["mean"]
        vol_chan = vol_chan.dropna(subset=["cv"]).sort_values("cv", ascending=False)
        most_volatile_chan = str(vol_chan.index[0]) if len(vol_chan) else None
        most_volatile_chan_cv = float(vol_chan.iloc[0]["cv"]) if len(vol_chan) else np.nan

    # Pricing: best discount band
    best_band = worst_band = None
    best_avg = worst_avg = np.nan
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 20:
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            agg = tmp.groupby("disc_band")[m.col_revenue].mean()
            if agg.notna().sum() >= 2:
                best_band = str(agg.sort_values(ascending=False).index[0])
                best_avg = float(agg.loc[best_band])
                worst_band = str(agg.sort_values(ascending=True).index[0])
                worst_avg = float(agg.loc[worst_band])

    sections: Dict[str, List[str]] = {}

    # Where money is made
    money_bullets = []
    money_bullets.append(
        f"Revenue is driven by a small number of key stores — **{top_store}** is #1 with **{fmt_currency(top_store_rev)}**."
    )
    if not np.isnan(top2_share):
        money_bullets.append(
            f"The **top 2 stores** contribute about **{fmt_pct(top2_share, 0)}** of total revenue. Improvements here have the biggest impact."
        )
    if top_cat is not None:
        money_bullets.append(
            f"Top category: **{top_cat}** contributes **{fmt_currency(top_cat_rev)}**."
        )
    if top_channel is not None:
        money_bullets.append(
            f"Top channel: **{top_channel}** contributes **{fmt_currency(top_channel_rev)}**."
        )
    sections["Where the money is made"] = money_bullets

    # Where risk exists
    risk_bullets = []
    if most_volatile_store is not None:
        risk_bullets.append(
            f"Predictability risk: **{most_volatile_store}** has the most uneven day-to-day sales (variability score ≈ **{most_volatile_cv:.2f}**)."
        )
    if most_volatile_chan is not None:
        risk_bullets.append(
            f"Channel stability matters too — **{most_volatile_chan}** is the most volatile channel (variability score ≈ **{most_volatile_chan_cv:.2f}**)."
        )
    risk_bullets.append(
        "Concentration risk: when most revenue comes from a few stores, execution slips in those locations hit the whole business."
    )
    sections["Where risk exists"] = risk_bullets

    # What can be improved
    improve_bullets = []
    if best_band is not None and worst_band is not None:
        improve_bullets.append(
            f"Discount discipline: **{best_band}** delivers the best average revenue per sale (**{fmt_currency(best_avg)}**). Deep discount **{worst_band}** underperforms (**{fmt_currency(worst_avg)}**)."
        )
        improve_bullets.append(
            "Takeaway: moderate discounts tend to perform better than aggressive ones — bigger discounts do not automatically lead to better results."
        )
    else:
        improve_bullets.append("Discounting works best when treated as an experiment (clear target + measure the lift), not a default habit.")
    improve_bullets.append("In top stores, focus on fundamentals first: inventory, staffing, and promotion discipline.")
    sections["What can be improved"] = improve_bullets

    # What to focus on next
    next_bullets = []
    next_bullets.append(f"Run a simple playbook on the top stores (starting with **{top_store}**) and scale what works.")
    next_bullets.append("Fix volatility before chasing growth — stability usually comes from operations, not more campaigns.")
    sections["What to focus on next"] = next_bullets

    return sections
# -----------------------------
# Chart builders (strict categorical alignment)
# -----------------------------
def fig_style_common(fig: go.Figure, title: str) -> go.Figure:
    # Executive-grade defaults for all charts
    fig = apply_consulting_theme(fig, title=title, height=380, y_is_currency=True)
    # Slightly tighter for small multiples will be overridden where needed
    return fig

def bar_categorical(
    x_labels: List[str],
    y_values: List[float],
    title: str,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    colors: Optional[List[str]] = None,
    text_fmt: str = ",.0f",
) -> go.Figure:
    # Strict categorical axis: tickvals == categoryarray == x
    x = [str(v) for v in x_labels]
    y = [float(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else 0.0 for v in y_values]
    if colors is None:
        colors = [TABLEAU10[i % len(TABLEAU10)] for i in range(len(x))]
    else:
        colors = colors[: len(x)]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x,
            y=y,
            marker_color=colors,
            text=[format(v, text_fmt) for v in y],
            textposition="auto",
            cliponaxis=True,
            textfont=dict(size=12, color="#111827"),
            
            hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
        )
    )
    fig = fig_style_common(fig, title)
    fig.update_layout(bargap=0.35)
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=x,
        tickmode="array",
        tickvals=x,
        ticktext=x,
        title_text=x_title,
    )
    fig.update_yaxes(title_text=y_title)
    return fig

def line_trend(df: pd.DataFrame, date_col: str, value_col: str, title: str) -> go.Figure:
    daily = df.groupby(pd.Grouper(key=date_col, freq="D"))[value_col].sum().reset_index()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily[date_col],
            y=daily[value_col],
            mode="lines",
            line=dict(width=3),
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2s}<extra></extra>",
        )
    )
    fig = apply_consulting_theme(fig, title=title, height=360, y_is_currency=True)
    fig.update_xaxes(showgrid=False, tickformat="%b %d")
    return fig

def top5_stores_bar(m: RetailModel) -> Tuple[go.Figure, pd.DataFrame]:
    s = m.df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False).head(5)
    dfp = s.reset_index()
    dfp.columns = ["Store", "Revenue"]
    colors = [TABLEAU10[i % len(TABLEAU10)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Store"].tolist(),
        y_values=dfp["Revenue"].tolist(),
        title="Top Revenue-Generating Stores (Top 5)",
        y_title="Revenue",
        colors=colors,
        text_fmt=",.0f",
    )
    fig.update_layout(height=380)
    return fig, dfp

def store_small_multiples(m: RetailModel) -> Tuple[List[go.Figure], List[str]]:
    # top 5 stores
    top = m.df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False).head(5).index.tolist()
    figs = []
    names = []
    for i, store in enumerate(top):
        sub = m.df[m.df[m.col_store] == store]
        daily = sub.groupby(pd.Grouper(key=m.col_date, freq="D"))[m.col_revenue].sum().reset_index()
        fig = go.Figure()
        color = TABLEAU10[i % len(TABLEAU10)]
        fig.add_trace(
            go.Scatter(
                x=daily[m.col_date],
                y=daily[m.col_revenue],
                mode="lines+markers",
                line=dict(width=3, color=color),
                marker=dict(size=5, color=color),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.0f}<extra></extra>",
            )
        )
        fig = apply_consulting_theme(fig, title=f"Store Trend — {store}", height=260, y_is_currency=True)
        fig.update_layout(showlegend=False)
        fig.update_xaxes(showgrid=False)
        fig.update_xaxes(tickformat="%b %d")
        figs.append(fig)
        names.append(store)
    return figs, names

def pricing_effectiveness(m: RetailModel) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_discount is None:
        return None
    df = m.df.dropna(subset=[m.col_discount]).copy()
    if len(df) < 20:
        return None
    bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
    labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
    df["Discount Band"] = pd.cut(df[m.col_discount], bins=bins, labels=labels)
    agg = df.groupby("Discount Band")[m.col_revenue].mean().reindex(labels)
    dfp = agg.reset_index()
    dfp.columns = ["Discount Band", "Avg Revenue per Sale"]
    fig = bar_categorical(
        x_labels=dfp["Discount Band"].astype(str).tolist(),
        y_values=dfp["Avg Revenue per Sale"].fillna(0).tolist(),
        title="Pricing Effectiveness — Avg Revenue per Sale by Discount Level",
        y_title="Avg Revenue per Sale",
        colors=[TABLEAU10[i % len(TABLEAU10)] for i in range(len(dfp))],
        text_fmt=",.0f",
    )
    return fig, dfp

def revenue_by_category(m: RetailModel, topn: int = 8) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_category is None:
        return None
    s = m.df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False).head(topn)
    dfp = s.reset_index()
    dfp.columns = ["Category", "Revenue"]
    colors = [TABLEAU10[i % len(TABLEAU10)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Category"].tolist(),
        y_values=dfp["Revenue"].tolist(),
        title=f"Revenue by Category (Top {len(dfp)})",
        y_title="Revenue",
        colors=colors,
        text_fmt=",.0f",
    )
    fig.update_layout(height=360)
    return fig, dfp

def revenue_by_channel(m: RetailModel, topn: int = 8) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_channel is None:
        return None
    s = m.df.groupby(m.col_channel)[m.col_revenue].sum().sort_values(ascending=False).head(topn)
    dfp = s.reset_index()
    dfp.columns = ["Channel", "Revenue"]
    colors = [TABLEAU10[i % len(TABLEAU10)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Channel"].tolist(),
        y_values=dfp["Revenue"].tolist(),
        title=f"Revenue by Channel (Top {len(dfp)})",
        y_title="Revenue",
        colors=colors,
        text_fmt=",.0f",
    )
    return fig, dfp

def volatility_by_channel(m: RetailModel) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_channel is None:
        return None
    # daily revenue per channel
    daily = m.df.groupby([m.col_channel, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    agg = daily.groupby(m.col_channel)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    agg["Volatility"] = agg["std"] / agg["mean"]
    agg = agg.sort_values("Volatility", ascending=False).dropna(subset=["Volatility"])
    if len(agg) == 0:
        return None
    dfp = agg[["Volatility"]].head(8).reset_index()
    dfp.columns = ["Channel", "Volatility (relative)"]
    colors = [TABLEAU10[i % len(TABLEAU10)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Channel"].tolist(),
        y_values=dfp["Volatility (relative)"].tolist(),
        title=f"Channel Stability — Which Channels Swing the Most",
        y_title="Relative Volatility",
        colors=colors,
        text_fmt=",.2f",
    )
    return fig, dfp

# -----------------------------
# Chart-specific insights (short, human)
# -----------------------------
def insight_block(title: str, what: List[str], why: List[str], action: List[str]) -> None:
    st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)
    st.markdown("**What this shows**")
    for w in what:
        st.markdown(f"- {clean_display_text(w)}")
    st.markdown("**Why it matters**")
    for w in why:
        st.markdown(f"- {clean_display_text(w)}")
    st.markdown("**What to do**")
    for a in action:
        st.markdown(f"- {clean_display_text(a)}")
    st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)

# -----------------------------
# Export helpers (PDF + PPT with charts + commentary)
# -----------------------------
def fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> bytes:
    # Requires kaleido
    return fig.to_image(format="png", scale=scale)

def build_pdf_exec_brief(
    title: str,
    subtitle: str,
    summary_points: List[str],
    chart_items: List[Tuple[str, go.Figure, str]],  # (chart_title, fig, commentary)
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=0.8*inch, rightMargin=0.8*inch, topMargin=0.7*inch, bottomMargin=0.7*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ECBody", parent=styles["BodyText"], fontSize=11, leading=15))
    styles.add(ParagraphStyle(name="ECTitle", parent=styles["Title"], fontSize=20, leading=24, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="ECSub", parent=styles["BodyText"], fontSize=12, leading=16, textColor="#555555"))

    story = []
    story.append(Paragraph(title, styles["ECTitle"]))
    story.append(Paragraph(subtitle, styles["ECSub"]))
    story.append(Spacer(1, 0.18*inch))

    story.append(Paragraph("<b>Executive Summary</b>", styles["ECBody"]))
    for p in summary_points[:12]:
        _t = md_to_plain(p)
        _t = clean_display_text(_t)
        if _t:
            story.append(Paragraph(f"• {_t}", styles["ECBody"]))
    story.append(Spacer(1, 0.20*inch))

    story.append(Paragraph("<b>Key Charts & Commentary</b>", styles["ECBody"]))
    story.append(Spacer(1, 0.12*inch))

    for (ctitle, fig, commentary) in chart_items:
        # Title
        story.append(Paragraph(f"<b>{ctitle}</b>", styles["ECBody"]))
        # Commentary
        if commentary:
            for line in md_to_plain_lines(commentary):
                story.append(Paragraph(f"• {line}", styles["ECBody"]))
        story.append(Spacer(1, 0.10*inch))
        # Image
        png = fig_to_png_bytes(fig, scale=2)
        img_buf = io.BytesIO(png)
        # Fit to page width
        img = RLImage(img_buf, width=6.7*inch, height=3.2*inch)
        story.append(img)
        story.append(Spacer(1, 0.22*inch))

    doc.build(story)
    return buf.getvalue()

def build_ppt_talking_deck(
    deck_title: str,
    chart_items: List[Tuple[str, go.Figure, str]],  # (title, fig, bullets)
) -> bytes:
    prs = Presentation()
    # 16:9
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Title slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = deck_title
    subtitle = slide.placeholders[1]
    subtitle.text = "Talking Deck — one insight per slide"

    # Content slides
    blank_layout = prs.slide_layouts[6]  # blank
    for (ctitle, fig, bullets) in chart_items:
        slide = prs.slides.add_slide(blank_layout)

        # Slide title (textbox so it never gets cut)
        tx = slide.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12.0), Inches(0.6))
        tf = tx.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = ctitle
        p.font.size = Pt(22)
        p.font.bold = True
        # Keep default color; don't assign None to RGB (that crashes).

        # Chart image
        png = fig_to_png_bytes(fig, scale=2)
        img_stream = io.BytesIO(png)
        slide.shapes.add_picture(img_stream, Inches(0.7), Inches(1.2), width=Inches(7.2))

        # Bullets
        bx = slide.shapes.add_textbox(Inches(8.2), Inches(1.2), Inches(4.8), Inches(5.8))
        btf = bx.text_frame
        btf.word_wrap = True
        btf.clear()
        if bullets:
            lines = [md_to_plain(l).strip("-• ").strip() for l in str(bullets).split("\n") if str(l).strip()]
            # Title for bullets
            p0 = btf.paragraphs[0]
            p0.text = "Commentary"
            p0.font.size = Pt(16)
            p0.font.bold = True
            # Bullets
            for line in lines[:8]:
                pp = btf.add_paragraph()
                pp.text = line
                pp.level = 0
                pp.font.size = Pt(14)
        else:
            p0 = btf.paragraphs[0]
            p0.text = "—"
            p0.font.size = Pt(14)

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()

# -----------------------------
# Sidebar: upload + diagnostics
# -----------------------------
st.title("EC-AI Insight")
st.markdown("<div class='ec-kicker'>Sales performance, explained clearly.</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='ec-subtle'>Upload your sales data and get a short business briefing — what’s working, what’s risky, and where to focus next.</div>",
    unsafe_allow_html=True
)

st.divider()

with st.sidebar:
    st.header("Data")
    up = st.file_uploader("Upload CSV", type=["csv"])
    st.caption("Tip: First load on Streamlit Cloud may take 30–60 seconds if the app was asleep.")

    st.header("Exports")
    export_scale = st.slider("Export image scale", min_value=1, max_value=3, value=2, help="Higher = clearer charts, but slower exports.")

    st.header("Diagnostics")
    try:
        import plotly
        import importlib.util
        st.write("Plotly:", plotly.__version__)
        st.write("Kaleido installed:", importlib.util.find_spec("kaleido") is not None)
    except Exception as e:
        st.write("Diagnostics unavailable:", e)

# Load data
df_raw = None
if up is not None:
    try:
        df_raw = pd.read_csv(up)
    except Exception:
        up.seek(0)
        df_raw = pd.read_csv(up, encoding="latin-1")
else:
    st.info("Upload a CSV to begin. (Retail sales / transaction data works best.)")

if df_raw is None:
    st.stop()

# Prep
try:
    m = prep_retail(df_raw)
except Exception as e:
    st.error(f"Data load error: {e}")
    st.stop()

df = m.df

# -----------------------------
# Executive Summary (DEFAULT)
# -----------------------------
summary_points = build_business_summary_points(m)

st.subheader("Executive Summary")
for p in summary_points[:12]:
    _t = clean_display_text(p)
    if _t:
        st.markdown(f"• {_t}")

st.divider()

# -----------------------------
# Business Insights (DEFAULT)
# -----------------------------
st.subheader("Business Insights")
st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)

ins_sections = build_business_insights_sections(m)
for i, (sec_title, bullets) in enumerate(ins_sections.items()):
    st.markdown(f"#### {sec_title}")
    for b in bullets:
        st.markdown(f"- {clean_display_text(b)}")
    if i < len(ins_sections) - 1:
        st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)

st.divider()

# -----------------------------
# Key Performance Visuals (DEFAULT)
# -----------------------------
st.subheader("Charts & Insights")

# 1) Overall trend
fig_trend = line_trend(df, m.col_date, m.col_revenue, "Revenue Trend (Daily)")
st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
insight_block(
    "Revenue Trend",
    what=["Overall revenue direction over time (daily total)."],
    why=["Sets the context: growth vs stability.", "Helps spot spikes that may come from promotions or one-off events."],
    action=["If the trend is flat, focus on execution and mix. If it’s rising, protect top drivers and scale carefully."],
)

# 2) Top 5 stores
fig_topstores, df_topstores = top5_stores_bar(m)
st.plotly_chart(fig_topstores, use_container_width=True, config={"displayModeBar": False})
top_store_name = df_topstores.iloc[0]["Store"] if len(df_topstores) else "Top store"
insight_block(
    "Top Stores",
    what=[f"Revenue is concentrated in a small number of stores, led by **{top_store_name}**."],
    why=["Top stores disproportionately drive outcomes.", "Operational issues in one key store can move the whole month."],
    action=["Prioritise stock availability, staffing, and execution in the top stores before expanding elsewhere."],
)

# 3) Store stability (mini charts)
st.markdown("### Store Stability (Top 5)")
figs, store_names = store_small_multiples(m)
cols = st.columns(2)
for i, fig in enumerate(figs):
    with cols[i % 2]:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
insight_block(
    "Store Stability",
    what=["Some stores are steady while others swing day-to-day."],
    why=["Volatility makes forecasting and inventory planning harder.", "Stability is often execution (not market demand)."],
    action=["Fix volatility first (availability, staffing, promotion timing). Use stable stores as benchmarks for best practices."],
)

# 4) Pricing effectiveness
pe = pricing_effectiveness(m)
if pe is not None:
    fig_price, df_price = pe
    st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})
    insight_block(
        "Pricing Effectiveness",
        what=["Moderate discounts often perform better than aggressive discounting."],
        why=["Large discounts can erode revenue quality without improving outcomes.", "Pricing discipline is a repeatable advantage."],
        action=["Use small discounts as default. Treat deep discounts as experiments with clear goals and limits."],
    )
else:
    st.info("Pricing Effectiveness is unavailable (no usable discount column found).")

# 5) Revenue by Category
cat = revenue_by_category(m, topn=8)
if cat is not None:
    fig_cat, _ = cat
    st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})
    insight_block(
        "Category Mix",
        what=["A few categories typically drive most revenue."],
        why=["Category mix often matters more than SKU count.", "Weak categories can drag overall performance."],
        action=["Double down on winner categories (stock depth, placement). Review whether weak categories need repositioning or removal."],
    )

# 6) Revenue by Channel
chn = revenue_by_channel(m, topn=8)
if chn is not None:
    fig_chn, _ = chn
    st.plotly_chart(fig_chn, use_container_width=True, config={"displayModeBar": False})
    insight_block(
        "Channel Mix",
        what=["Channels contribute very differently to revenue."],
        why=["Scaling the right channel can be cheaper than opening new stores.", "Channel concentration adds risk if one channel weakens."],
        action=["Invest more in high-performing channels. Fix or rethink consistently weak channels."],
    )

st.divider()

# -----------------------------
# Advanced analysis (COLLAPSED)
# -----------------------------
with st.expander("Advanced analysis (optional)"):
    st.markdown("### Raw Data Preview")
    st.dataframe(df.head(50), use_container_width=True)

    st.markdown("### Data Quality & Assumptions")
    profile = pd.DataFrame({
        "Column": df.columns,
        "Type": [str(df[c].dtype) for c in df.columns],
        "Missing %": [float(df[c].isna().mean()) for c in df.columns],
        "Unique": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    st.dataframe(profile, use_container_width=True)

    st.markdown("### Correlation (numeric fields)")
    num = df.select_dtypes(include=[np.number])
    if num.shape[1] >= 2:
        corr = num.corr()
        fig_corr = px.imshow(corr, text_auto=True, aspect="auto", color_continuous_scale="Blues")
        fig_corr = apply_consulting_theme(fig_corr, title="Numeric Correlation (Advanced)", height=440)
        fig_corr.update_xaxes(side="bottom")
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Not enough numeric fields to compute correlation.")

    vol_ch = volatility_by_channel(m)
    if vol_ch is not None:
        fig_vol, _ = vol_ch
        st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})


# -----------------------------
# Ask AI (CEO-level Q&A)
# -----------------------------
st.subheader("Ask AI (CEO Q&A)")
st.caption("Ask questions about your data (e.g., 'Why did revenue drop?' 'Which store should I fix first?'). Answers are generated from your uploaded dataset summary.")

# Inline Q&A (input stays directly under this section)
q = st.text_input("Ask a question", placeholder="e.g., What should I focus on next week and why?")
ask_btn = st.button("Ask AI")

if ask_btn and q.strip():
    # Use the existing Executive Summary bullets as the context
    _ctx = ""
    try:
        _ctx = "\n".join([clean_display_text(x) for x in summary_points[:12] if clean_display_text(x)])
    except Exception:
        _ctx = ""
    answer = answer_question_with_openai(q.strip(), _ctx)
    st.markdown("**Answer**")
    st.write(answer)

st.divider()


# -----------------------------
# Exports
# -----------------------------
st.subheader("Export Executive Brief")
st.markdown(
    """
Download a short executive-ready summary for sharing or review.

- **PDF Executive Brief** — selected insights only  
- **PPT Talking Deck** — one insight per slide (16:9)
    """
)

# Prepare chart bundle for export (selected only)
export_items: List[Tuple[str, go.Figure, str]] = []

export_items.append(("Revenue Trend", fig_trend, "Overall direction of revenue over time.\nUse this to spot promotion spikes and slowdowns."))
export_items.append(("Top Revenue-Generating Stores (Top 5)", fig_topstores, "Revenue is concentrated in a small number of stores.\nProtect performance in the top stores first."))

# Add one representative store chart (best to keep brief)
if figs:
    export_items.append((f"Store Stability — {store_names[0]}", figs[0], "Stability matters for forecasting and inventory.\nFix volatility before scaling growth."))

if pe is not None:
    export_items.append(("Pricing Effectiveness", pe[0], "Moderate discounts often outperform aggressive discounting.\nUse deep discounts as controlled experiments."))

if cat is not None:
    export_items.append(("Category Mix", cat[0], "Category mix drives revenue structure.\nDouble down on winners; review weak categories."))

if chn is not None:
    export_items.append(("Channel Mix", chn[0], "Channel contribution is uneven.\nInvest in channels that consistently perform."))

colA, colB = st.columns([1, 1])

with colA:
    if st.button("Generate PDF Executive Brief", type="primary"):
        try:
            pdf_bytes = build_pdf_exec_brief(
                title="EC-AI Insight — Executive Brief",
                subtitle="Retail sales performance, explained clearly.",
                summary_points=summary_points,
                chart_items=export_items,
            )
            st.download_button("Download PDF", data=pdf_bytes, file_name="ecai_executive_brief.pdf", mime="application/pdf")
        except Exception as e:
            st.error("PDF export failed.")
            st.code(str(e))

with colB:
    if st.button("Generate PPT Talking Deck"):
        try:
            ppt_bytes = build_ppt_talking_deck(
                deck_title="EC-AI Insight — Talking Deck",
                chart_items=export_items,
            )
            st.download_button("Download PPT", data=ppt_bytes, file_name="ecai_talking_deck.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
        except Exception as e:
            st.error("PPT export failed.")
            st.code(str(e))
