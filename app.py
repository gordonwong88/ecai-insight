# EC-AI Insight — Retail Sales MVP (Founder-first)
# Reconstructed v7 from recovered base
# Notes:
# - Safe Executive Dashboard for demo dataset
# - 3 Executive Insight Cards
# - Charts + commentary
# - Ask AI with suggested questions
# - PDF / PPT export
# - Demo dataset included

import io
import os
import re
import math
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

# Optional: PPT export
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.dml.color import RGBColor
    PPT_AVAILABLE = True
except Exception:
    PPT_AVAILABLE = False

# Optional: PDF export
try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.enums import TA_LEFT
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False


# =========================================================
# Page config
# =========================================================
st.set_page_config(page_title="EC-AI Insight", layout="wide")


# =========================================================
# Global styling
# =========================================================
st.markdown(
    """
<style>
html, body, [class*="css"]  { font-size: 16px; }
p, li { font-size: 16px; line-height: 1.55; }
small, .stCaption { font-size: 14px; }

h1 { font-size: 40px !important; margin-bottom: 0.25rem; }
h2 { font-size: 26px !important; margin-top: 1.2rem; }
h3 { font-size: 20px !important; margin-top: 1.0rem; }
h4 { font-size: 18px !important; margin-top: 0.9rem; }

.ec-space { margin-top: 10px; margin-bottom: 10px; }
.ec-tight { margin-top: 2px; margin-bottom: 2px; }
.ec-note { color: #555; font-size: 15px; }
.ec-kicker { color: #555; font-size: 18px; }
.ec-subtle { color: #666; font-size: 15px; }

.ec-card {
  border: 1px solid rgba(17,24,39,0.08);
  border-radius: 16px;
  padding: 16px 16px 12px 16px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(17,24,39,0.04);
  min-height: 150px;
}
.ec-card-title {
  font-size: 13px;
  font-weight: 800;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 8px;
}
.ec-card-value {
  font-size: 28px;
  font-weight: 900;
  color: #111827;
  line-height: 1.1;
  margin-bottom: 8px;
}
.ec-card-note {
  font-size: 14px;
  color: #374151;
  line-height: 1.45;
}

.ec-note-box {
  border: 1px solid rgba(17,24,39,0.10);
  border-radius: 16px;
  padding: 16px 18px;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(17,24,39,0.05);
  font-size: 13px;
  color: #374151;
  line-height: 1.45;
}

.ec-insight-card {
  border: 1px solid rgba(17,24,39,0.10);
  border-radius: 16px;
  padding: 16px 18px;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(17,24,39,0.05);
  min-height: 100%;
  margin-top: 18px;
}
.ec-insight-section {
  margin-bottom: 12px;
}
.ec-insight-section:last-child {
  margin-bottom: 0;
}
.ec-insight-heading {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 6px;
}
.ec-insight-list {
  margin: 0;
  padding-left: 18px;
}
.ec-insight-list li {
  margin: 0 0 6px 0;
  color: #374151;
}

.ec-ai-answer {
  border: 1px solid rgba(17,24,39,0.08);
  border-radius: 14px;
  padding: 14px 16px;
  background: #ffffff;
  margin-bottom: 10px;
}

.ec-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: #F3F4F6;
  color: #374151;
  font-size: 12px;
  margin: 0 6px 8px 0;
}

.ec-section-title {
  margin: 6px 0 10px 0;
  font-weight: 900;
  font-size: 18px;
  color:#111827;
}

.ec-dashboard-note {
  margin-top: 6px;
  font-size: 12px;
  color:#374151;
  line-height: 1.35;
}

div[data-testid="stExpander"] > details { padding: 0.25rem 0.25rem 0.5rem 0.25rem; }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# Palette
# =========================================================
TABLEAU10 = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"
]

CONSULTING_PALETTE = [
    "#0B1F3B",  # deep navy
    "#2A6F97",  # blue
    "#2F855A",  # green
    "#B7791F",  # amber
    "#9B2C2C",  # red
    "#4A5568",  # slate
    "#718096",  # gray
    "#A0AEC0",  # light gray
]


# =========================================================
# Basic helpers
# =========================================================
def clean_display_text(s: str) -> str:
    if not s:
        return s

    raw = str(s).strip()
    low = raw.lower()

    if "persale" in low or "deepdiscount" in low:
        return ""

    s = raw
    s = s.replace("**", "").replace("*", "")
    s = s.replace("`", "").replace("```", "")
    s = s.replace("_", "")
    s = re.sub(r"\\\((.*?)\\\)", "", s)
    s = re.sub(r"\$[^\$]*\$", "", s)
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"[\[\]{}<>]", "", s)
    s = re.sub(r"[\.]{2,}", ".", s)

    letters = sum(ch.isalpha() for ch in s)
    if letters < 4:
        return ""

    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def emphasize_exec_keywords_html(text: str) -> str:
    if not text:
        return text or ""

    text = re.sub(r"(\$[0-9,.]+[KMB]?)", r"<b>\1</b>", text)
    text = re.sub(r"(\d+\.?\d*%)", r"<b>\1</b>", text)
    text = re.sub(r"(#\d+|top \d+)", r"<b>\1</b>", text, flags=re.I)
    text = re.sub(r"((HK|SG|JP|CN)-[A-Za-z0-9]+)", r"<b>\1</b>", text)
    text = re.sub(r"^(Takeaway:)", r"<b>\1</b>", text)
    text = re.sub(r"^(Next focus:)", r"<b>\1</b>", text)
    return text


def clean_col(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())


def fmt_currency(x: float) -> str:
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


def _fmt_money(x: float) -> str:
    return fmt_currency(x)


def _fmt_pct(x: float) -> str:
    try:
        return f"{float(x)*100:.1f}%"
    except Exception:
        return "N/A"


def _safe_div(a: float, b: float) -> float:
    try:
        a = float(a)
        b = float(b)
        return a / b if b not in (0, 0.0) else float("nan")
    except Exception:
        return float("nan")


def md_to_plain(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = s.replace("**", "")
    return s


def md_to_plain_lines(s: str) -> List[str]:
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


# =========================================================
# Column detection
# =========================================================
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
            for n, orig in norm.items():
                if n == cand_norm or cand_norm in n:
                    out[key] = orig
                    break
            if out[key] is not None:
                break

    if out["revenue"] is None:
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            out["revenue"] = num_cols[0]

    return out


# =========================================================
# Data model
# =========================================================
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

    if cols["date"] is None:
        raise ValueError("Could not detect a Date column. Please ensure your file includes a date field (e.g., Date, OrderDate).")
    if cols["revenue"] is None:
        raise ValueError("Could not detect a Revenue/Sales column. Please ensure your file includes a numeric revenue field (e.g., Revenue, Sales, Amount).")

    col_date = cols["date"]
    col_store = cols["store"] or "__store__"
    col_revenue = cols["revenue"]

    if cols["store"] is None:
        df[col_store] = "All Stores"

    df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
    df = df.dropna(subset=[col_date])

    df[col_revenue] = pd.to_numeric(df[col_revenue], errors="coerce")
    df = df.dropna(subset=[col_revenue])

    col_qty = cols["qty"]
    if col_qty is not None:
        df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce")

    col_discount = cols["discount"]
    if col_discount is not None:
        df[col_discount] = pd.to_numeric(df[col_discount], errors="coerce")
        s = df[col_discount].dropna()
        if len(s) > 0 and s.quantile(0.95) > 1.5:
            df[col_discount] = df[col_discount] / 100.0
        df[col_discount] = df[col_discount].clip(lower=0, upper=1)

    for k in ["store", "category", "channel", "payment"]:
        c = cols.get(k)
        if c is not None:
            df[c] = df[c].astype(str).str.strip()

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


# =========================================================
# Demo dataset
# =========================================================
def build_demo_dataset(n: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(42)

    dates = pd.date_range("2025-01-01", periods=120, freq="D")
    stores = ["HK-CWB", "HK-MK", "HK-TST", "HK-KLN", "SG-MBS", "SG-ORC"]
    categories = ["Electronics", "Fashion", "Beauty", "Home", "Sports", "Kids"]
    channels = ["Store", "Online", "Marketplace"]
    payments = ["Visa", "Cash", "Mastercard", "FPS", "AlipayHK"]

    df = pd.DataFrame({
        "Date": rng.choice(dates, size=n),
        "Store": rng.choice(stores, size=n, p=[0.22, 0.18, 0.17, 0.15, 0.15, 0.13]),
        "Category": rng.choice(categories, size=n, p=[0.23, 0.21, 0.16, 0.14, 0.14, 0.12]),
        "Channel": rng.choice(channels, size=n, p=[0.58, 0.28, 0.14]),
        "Payment": rng.choice(payments, size=n),
        "Units": rng.integers(1, 6, size=n),
        "Discount": rng.choice([0, 0.02, 0.05, 0.10, 0.15, 0.25], size=n, p=[0.16, 0.20, 0.24, 0.20, 0.14, 0.06]),
    })

    base_price = {
        "Electronics": 820,
        "Fashion": 330,
        "Beauty": 180,
        "Home": 260,
        "Sports": 290,
        "Kids": 150,
    }

    store_factor = {
        "HK-CWB": 1.22,
        "HK-MK": 1.08,
        "HK-TST": 1.14,
        "HK-KLN": 0.96,
        "SG-MBS": 1.18,
        "SG-ORC": 1.04,
    }

    channel_factor = {
        "Store": 1.00,
        "Online": 0.93,
        "Marketplace": 0.88,
    }

    revenue = []
    cost = []

    for _, row in df.iterrows():
        cat = row["Category"]
        store = row["Store"]
        channel = row["Channel"]
        units = row["Units"]
        disc = row["Discount"]

        raw = base_price[cat] * store_factor[store] * channel_factor[channel]
        demand_noise = rng.normal(1.0, 0.12)
        rev = raw * units * (1 - disc) * demand_noise
        cst = rev * rng.uniform(0.50, 0.72)

        revenue.append(max(rev, 20))
        cost.append(max(cst, 10))

    df["Revenue"] = np.round(revenue, 2)
    df["Cost"] = np.round(cost, 2)
    df["Product"] = df["Category"] + " Item"

    return df.sort_values("Date").reset_index(drop=True)


# =========================================================
# Plot helpers
# =========================================================
def _build_unavailable_figure(
    title: str = "Chart unavailable",
    message: str = "This chart needs columns that are not present in the current dataset.",
    *,
    height: int = 320,
) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="center",
        font=dict(size=13, color="#6B7280"),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=24, r=24, t=56, b=24),
        paper_bgcolor="white",
        plot_bgcolor="white",
        title=dict(text=title, x=0.0, xanchor="left", font=dict(size=18, color="#111827")),
        font=dict(family="Inter, Arial, sans-serif", size=13, color="#111827"),
    )
    return fig


def apply_consulting_theme(
    fig: Optional[go.Figure],
    *,
    title: str | None = None,
    height: int | None = None,
    y_is_currency: bool = False,
    y_is_pct: bool = False,
) -> go.Figure:
    if fig is None:
        return _build_unavailable_figure(
            title=title or "Chart unavailable",
            message="This chart is unavailable for the current dataset.",
            height=height or 320,
        )

    if title is not None:
        fig.update_layout(title=dict(text=title, x=0.0, xanchor="left"))

    fig.update_layout(
        template="plotly_white",
        height=height or fig.layout.height or 380,
        margin=dict(l=48, r=26, t=62, b=52),
        font=dict(family="Inter, Arial, sans-serif", size=13, color="#111827"),
        title=dict(font=dict(size=18, color="#111827")),
        paper_bgcolor="white",
        plot_bgcolor="white",
        colorway=CONSULTING_PALETTE,
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
        showline=True,
        linewidth=1,
        linecolor="#374151",
        ticks="outside",
        tickfont=dict(size=12, color="#374151"),
        gridcolor="rgba(17,24,39,0.07)",
    )
    fig.update_yaxes(
        title=None,
        showline=True,
        linewidth=1,
        linecolor="#374151",
        ticks="outside",
        tickfont=dict(
            family="Inter SemiBold, Inter, Arial, sans-serif",
            size=12,
            color="#374151",
        ),
        gridcolor="rgba(17,24,39,0.07)",
    )

    if y_is_currency:
        fig.update_yaxes(tickprefix="$", tickformat=",.2s")
    elif y_is_pct:
        fig.update_yaxes(tickformat=".0%")

    fig.update_traces(hoverlabel=dict(font_size=12), hovertemplate=None)
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
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>",
        )
    )
    fig = apply_consulting_theme(fig, title=title, height=360, y_is_currency=True)
    fig.update_xaxes(showgrid=False, tickformat="%b %d")
    return fig


def _wrap_axis_label(label: str, width: int = 12) -> str:
    parts = textwrap.wrap(str(label), width=width, break_long_words=False, break_on_hyphens=True)
    return "<br>".join(parts) if parts else str(label)


def bar_categorical(
    x_labels: List[str],
    y_values: List[float],
    title: str,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    colors: Optional[List[str]] = None,
    text_fmt: str = ",.0f",
    y_is_currency: bool = True,
    label_wrap_width: int = 14,
    tick_angle: int = 0,
) -> go.Figure:
    base_x = [str(v) for v in x_labels]
    wrapped = [_wrap_axis_label(v, width=label_wrap_width) for v in base_x]
    y = [float(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else 0.0 for v in y_values]
    ranked = [f"{i+1}.<br>{lbl}" for i, lbl in enumerate(wrapped)]

    if colors is None:
        leader = CONSULTING_PALETTE[0]
        muted = "#D1D5DB"
        colors = [leader] + [muted] * max(0, len(ranked) - 1)
    else:
        colors = colors[: len(ranked)]

    ymax = max(y) if y else 0.0
    ypad = ymax * 0.16 if ymax > 0 else 1.0

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=ranked,
            y=y,
            customdata=base_x,
            marker=dict(color=colors),
            width=0.22,
            text=y,
            texttemplate=f"%{{text:{text_fmt}}}",
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color="#111827", size=12),
            hovertemplate="%{customdata}<br>%{y:,.2f}<extra></extra>",
        )
    )

    fig = apply_consulting_theme(fig, title=title, height=400, y_is_currency=y_is_currency)
    fig.update_layout(bargap=0.78, margin=dict(l=48, r=26, t=62, b=86))

    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=ranked,
        title_text=x_title,
        showgrid=False,
        tickangle=tick_angle,
        automargin=True,
        tickfont=dict(family="Inter SemiBold, Inter, Arial, sans-serif", size=11, color="#111827"),
    )
    fig.update_yaxes(
        title_text=y_title,
        range=[0, ymax + ypad],
        autorange=False,
        rangemode="tozero",
        tickfont=dict(family="Inter SemiBold, Inter, Arial, sans-serif", size=12, color="#111827"),
    )
    return fig


def top5_stores_bar(m: RetailModel) -> Tuple[go.Figure, pd.DataFrame]:
    s = m.df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False).head(5)
    dfp = s.reset_index()
    dfp.columns = ["Store", "Revenue"]
    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Store"].tolist(),
        y_values=dfp["Revenue"].tolist(),
        title="Top Revenue-Generating Stores (Top 5)",
        y_title="Revenue",
        colors=colors,
        text_fmt=",.0f",
        label_wrap_width=12,
        tick_angle=0,
    )
    fig.update_layout(height=400)
    return fig, dfp


def store_small_multiples(m: RetailModel) -> Tuple[List[go.Figure], List[str]]:
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
                hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>",
            )
        )
        fig = apply_consulting_theme(fig, title=f"Store Trend — {store}", height=260, y_is_currency=True)
        fig.update_layout(showlegend=False)
        fig.update_xaxes(showgrid=False, tickformat="%b %d")

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
    agg = df.groupby("Discount Band", observed=False)[m.col_revenue].mean().reindex(labels)

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

    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
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

    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
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

    daily = m.df.groupby([m.col_channel, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    agg = daily.groupby(m.col_channel)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    agg["Volatility"] = agg["std"] / agg["mean"]
    agg = agg.sort_values("Volatility", ascending=False).dropna(subset=["Volatility"])

    if len(agg) == 0:
        return None

    dfp = agg[["Volatility"]].head(8).reset_index()
    dfp.columns = ["Channel", "Volatility (relative)"]

    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Channel"].tolist(),
        y_values=dfp["Volatility (relative)"].tolist(),
        title="Channel Stability — Which Channels Swing the Most",
        y_title="Relative Volatility",
        colors=colors,
        text_fmt=",.2f",
        y_is_currency=False,
    )
    return fig, dfp


# =========================================================
# Insights / summaries
# =========================================================
def build_business_summary_points(m: RetailModel) -> List[str]:
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

    df_sorted = df.sort_values(m.col_date)
    mid = df_sorted[m.col_date].min() + pd.Timedelta(days=days / 2)
    rev_first = float(df_sorted.loc[df_sorted[m.col_date] <= mid, m.col_revenue].sum())
    rev_second = float(df_sorted.loc[df_sorted[m.col_date] > mid, m.col_revenue].sum())
    growth = (rev_second - rev_first) / rev_first if rev_first > 0 else np.nan

    daily = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol = daily.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol["ratio"] = vol["std"] / vol["mean"]
    most_volatile_store = str(vol["ratio"].sort_values(ascending=False).index[0]) if len(vol) else None
    most_volatile_score = float(vol.loc[most_volatile_store, "ratio"]) if most_volatile_store in vol.index else np.nan

    best_band = worst_band = None
    best_avg = worst_avg = np.nan
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 20:
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            agg = tmp.groupby("disc_band", observed=False)[m.col_revenue].mean()
            if agg.notna().sum() >= 2:
                best_band = str(agg.sort_values(ascending=False).index[0])
                best_avg = float(agg.loc[best_band])
                worst_band = str(agg.sort_values(ascending=True).index[0])
                worst_avg = float(agg.loc[worst_band])

    points: List[str] = []
    points.append(f"You have **{days} days** of data with **{len(df):,} transactions** (total revenue **{fmt_currency(total_rev)}**).")

    if not np.isnan(top_store_share):
        points.append(f"Revenue is concentrated: **{top_store}** contributes **{fmt_currency(top_store_rev)}** (about **{fmt_pct(top_store_share, 0)}** of total).")

    if not np.isnan(top2_share):
        points.append(f"The **top 2 stores** together generate **{fmt_currency(top2_rev)}** (about **{fmt_pct(top2_share, 0)}**). Small wins in these locations move the whole business.")

    if top_cat is not None and not np.isnan(top_cat_share):
        points.append(f"By category, **{top_cat}** is your largest driver: **{fmt_currency(top_cat_rev)}** (about **{fmt_pct(top_cat_share, 0)}**).")

    if not np.isnan(growth):
        if growth > 0.03:
            points.append(f"Momentum is positive: the second half of the period delivered about **{fmt_pct(growth, 0)}** more revenue than the first half.")
        elif growth < -0.03:
            points.append(f"Momentum is softer: the second half of the period delivered about **{fmt_pct(growth, 0)}** less revenue than the first half.")
        else:
            points.append("Overall revenue looks broadly stable across the period (no major shift between first vs second half).")

    if most_volatile_store is not None and not np.isnan(most_volatile_score):
        points.append(f"Day-to-day sales are not equally predictable. **{most_volatile_store}** shows the biggest swings (variability score ≈ **{most_volatile_score:.2f}**).")

    if best_band is not None and worst_band is not None:
        points.append(f"Discounting: **{best_band}** performs best on average (**{fmt_currency(best_avg)}** per sale). Deep discount **{worst_band}** underperforms (**{fmt_currency(worst_avg)}**).")
        points.append("Takeaway: moderate discounts tend to work better than aggressive ones — bigger discounts do not automatically lead to better results.")

    points.append("Next focus: protect and improve the top stores first (availability, staffing, promotion discipline), then scale what works.")
    return points[:12]


def build_business_insights_sections(m: RetailModel) -> Dict[str, List[str]]:
    df = m.df
    total_rev = float(df[m.col_revenue].sum())

    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)
    top_store = str(store_rev.index[0]) if len(store_rev) else "—"
    top_store_rev = float(store_rev.iloc[0]) if len(store_rev) else np.nan

    top2 = store_rev.head(2)
    top2_share = float(top2.sum() / total_rev) if total_rev > 0 and len(top2) else np.nan

    cat_rev = df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False) if m.col_category else pd.Series(dtype=float)
    top_cat = str(cat_rev.index[0]) if len(cat_rev) else None
    top_cat_rev = float(cat_rev.iloc[0]) if len(cat_rev) else np.nan

    channel_rev = df.groupby(m.col_channel)[m.col_revenue].sum().sort_values(ascending=False) if m.col_channel else pd.Series(dtype=float)
    top_channel = str(channel_rev.index[0]) if len(channel_rev) else None
    top_channel_rev = float(channel_rev.iloc[0]) if len(channel_rev) else np.nan

    daily_store = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol_store = daily_store.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol_store["cv"] = vol_store["std"] / vol_store["mean"]
    vol_store = vol_store.dropna(subset=["cv"]).sort_values("cv", ascending=False)
    most_volatile_store = str(vol_store.index[0]) if len(vol_store) else None
    most_volatile_cv = float(vol_store.iloc[0]["cv"]) if len(vol_store) else np.nan

    most_volatile_chan = None
    most_volatile_chan_cv = np.nan
    if m.col_channel:
        daily_chan = df.groupby([m.col_channel, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
        vol_chan = daily_chan.groupby(m.col_channel)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
        vol_chan["cv"] = vol_chan["std"] / vol_chan["mean"]
        vol_chan = vol_chan.dropna(subset=["cv"]).sort_values("cv", ascending=False)
        most_volatile_chan = str(vol_chan.index[0]) if len(vol_chan) else None
        most_volatile_chan_cv = float(vol_chan.iloc[0]["cv"]) if len(vol_chan) else np.nan

    best_band = worst_band = None
    best_avg = worst_avg = np.nan
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 20:
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            agg = tmp.groupby("disc_band", observed=False)[m.col_revenue].mean()
            if agg.notna().sum() >= 2:
                best_band = str(agg.sort_values(ascending=False).index[0])
                best_avg = float(agg.loc[best_band])
                worst_band = str(agg.sort_values(ascending=True).index[0])
                worst_avg = float(agg.loc[worst_band])

    sections: Dict[str, List[str]] = {}

    money_bullets = []
    money_bullets.append(f"Revenue is driven by a small number of key stores — **{top_store}** is #1 with **{fmt_currency(top_store_rev)}**.")
    if not np.isnan(top2_share):
        money_bullets.append(f"The **top 2 stores** contribute about **{fmt_pct(top2_share, 0)}** of total revenue. Improvements here have the biggest impact.")
    if top_cat is not None:
        money_bullets.append(f"Top category: **{top_cat}** contributes **{fmt_currency(top_cat_rev)}**.")
    if top_channel is not None:
        money_bullets.append(f"Top channel: **{top_channel}** contributes **{fmt_currency(top_channel_rev)}**.")
    sections["Where the money is made"] = money_bullets

    risk_bullets = []
    if most_volatile_store is not None:
        risk_bullets.append(f"Predictability risk: **{most_volatile_store}** has the most uneven day-to-day sales (variability score ≈ **{most_volatile_cv:.2f}**).")
    if most_volatile_chan is not None:
        risk_bullets.append(f"Channel stability matters too — **{most_volatile_chan}** is the most volatile channel (variability score ≈ **{most_volatile_chan_cv:.2f}**).")
    risk_bullets.append("Concentration risk: when most revenue comes from a few stores, execution slips in those locations hit the whole business.")
    sections["Where risk exists"] = risk_bullets

    improve_bullets = []
    if best_band is not None and worst_band is not None:
        improve_bullets.append(f"Discount discipline: **{best_band}** delivers the best average revenue per sale (**{fmt_currency(best_avg)}**). Deep discount **{worst_band}** underperforms (**{fmt_currency(worst_avg)}**).")
        improve_bullets.append("Takeaway: moderate discounts tend to perform better than aggressive ones — bigger discounts do not automatically lead to better results.")
    else:
        improve_bullets.append("Discounting works best when treated as an experiment (clear target + measure the lift), not a default habit.")
    improve_bullets.append("In top stores, focus on fundamentals first: inventory, staffing, and promotion discipline.")
    sections["What can be improved"] = improve_bullets

    next_bullets = []
    next_bullets.append(f"Run a simple playbook on the top stores (starting with **{top_store}**) and scale what works.")
    next_bullets.append("Fix volatility before chasing growth — stability usually comes from operations, not more campaigns.")
    sections["What to focus on next"] = next_bullets

    return sections


# =========================================================
# Executive cards
# =========================================================
def build_exec_cards(m: RetailModel) -> List[Dict[str, str]]:
    df = m.df
    total_rev = float(df[m.col_revenue].sum())
    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)

    top_store = str(store_rev.index[0]) if len(store_rev) else "—"
    top_store_rev = float(store_rev.iloc[0]) if len(store_rev) else np.nan
    top_store_share = (top_store_rev / total_rev) if total_rev > 0 and len(store_rev) else np.nan

    df_sorted = df.sort_values(m.col_date)
    dmin, dmax = df_sorted[m.col_date].min(), df_sorted[m.col_date].max()
    days = max((dmax - dmin).days + 1, 1)
    mid = df_sorted[m.col_date].min() + pd.Timedelta(days=days / 2)
    rev_first = float(df_sorted.loc[df_sorted[m.col_date] <= mid, m.col_revenue].sum())
    rev_second = float(df_sorted.loc[df_sorted[m.col_date] > mid, m.col_revenue].sum())
    growth = (rev_second - rev_first) / rev_first if rev_first > 0 else np.nan

    best_band = None
    best_avg = np.nan
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 20:
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            agg = tmp.groupby("disc_band", observed=False)[m.col_revenue].mean()
            if agg.notna().sum() > 0:
                best_band = str(agg.sort_values(ascending=False).index[0])
                best_avg = float(agg.loc[best_band])

    growth_label = "Stable"
    if not np.isnan(growth):
        if growth > 0.03:
            growth_label = "Positive"
        elif growth < -0.03:
            growth_label = "Softer"

    cards = [
        {
            "title": "Revenue Concentration",
            "value": fmt_currency(top_store_rev) if not np.isnan(top_store_rev) else "—",
            "note": f"{top_store} is the leading store at about {fmt_pct(top_store_share, 0)} of total revenue." if not np.isnan(top_store_share) else "Top store concentration unavailable.",
        },
        {
            "title": "Momentum",
            "value": growth_label,
            "note": f"Second half vs first half: {fmt_pct(growth, 0)}." if not np.isnan(growth) else "Not enough information to assess momentum.",
        },
        {
            "title": "Pricing Signal",
            "value": best_band if best_band is not None else "N/A",
            "note": f"Best average revenue per sale: {fmt_currency(best_avg)}." if not np.isnan(best_avg) else "Discount signal unavailable for this dataset.",
        },
    ]
    return cards


def render_parallel_insight_cards(cards: List[Dict[str, str]]) -> None:
    cols = st.columns(3, gap="small")
    for i, card in enumerate(cards[:3]):
        with cols[i]:
            st.markdown(
                f"""
<div class="ec-card">
  <div class="ec-card-title">{card.get("title","")}</div>
  <div class="ec-card-value">{card.get("value","")}</div>
  <div class="ec-card-note">{card.get("note","")}</div>
</div>
""",
                unsafe_allow_html=True,
            )


# =========================================================
# Commentary block
# =========================================================
def _html_bullets(items) -> str:
    rows = []
    for item in (items or []):
        _t = clean_display_text(item)
        if _t:
            rows.append(f"<li>{emphasize_exec_keywords_html(_t)}</li>")
    return "".join(rows)


def render_insight_card(what_points=None, why_points=None, todo_points=None) -> None:
    what_html = _html_bullets(what_points)
    why_html = _html_bullets(why_points)
    todo_html = _html_bullets(todo_points)

    st.markdown(
        f"""
<div class='ec-insight-card'>
  <div class='ec-insight-section'>
    <div class='ec-insight-heading'>What this shows</div>
    <ul class='ec-insight-list'>{what_html}</ul>
  </div>
  <div class='ec-insight-section'>
    <div class='ec-insight-heading'>Why it matters</div>
    <ul class='ec-insight-list'>{why_html}</ul>
  </div>
  <div class='ec-insight-section'>
    <div class='ec-insight-heading'>What to do</div>
    <ul class='ec-insight-list'>{todo_html}</ul>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def insight_block(what_points=None, why_points=None, todo_points=None) -> None:
    render_insight_card(what_points=what_points, why_points=why_points, todo_points=todo_points)


def render_chart_with_commentary(
    fig: go.Figure,
    *,
    what_points=None,
    why_points=None,
    todo_points=None,
    boxed_commentary: bool = True,
    left_ratio: int = 2,
    right_ratio: int = 1,
    height: Optional[int] = None,
):
    what_points = what_points or []
    why_points = why_points or []
    todo_points = todo_points or []

    col_l, col_r = st.columns([left_ratio, right_ratio], gap="large")
    with col_l:
        try:
            if height is not None:
                fig.update_layout(height=height)
        except Exception:
            pass
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_r:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        render_insight_card(what_points=what_points, why_points=why_points, todo_points=todo_points)


# =========================================================
# Ask AI
# =========================================================
def _get_openai_api_key() -> str | None:
    try:
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY")


def get_api_key() -> str | None:
    return _get_openai_api_key()


def _build_ai_context(df: pd.DataFrame, m: RetailModel) -> str:
    if df is None or df.empty:
        return "No dataset loaded."

    col_date = m.col_date
    col_rev = m.col_revenue
    col_store = m.col_store
    col_cat = m.col_category
    col_channel = m.col_channel
    col_disc = m.col_discount

    overview_lines = []
    n_rows = len(df)

    d = pd.to_datetime(df[col_date], errors="coerce")
    date_min = d.min()
    date_max = d.max()
    n_days = int((date_max - date_min).days) + 1 if pd.notna(date_min) and pd.notna(date_max) else None

    total_rev = float(pd.to_numeric(df[col_rev], errors="coerce").fillna(0).sum())

    overview_lines.append(f"Rows: {n_rows}")
    overview_lines.append(f"Date range: {date_min.date()} to {date_max.date()} ({n_days} days)" if n_days is not None else "Date range: N/A")
    overview_lines.append(f"Total revenue: {_fmt_money(total_rev)}")

    def top_contrib(col_name: Optional[str], top_n: int = 5):
        if not (col_name and col_name in df.columns and col_rev in df.columns):
            return None
        tmp = df[[col_name, col_rev]].copy()
        tmp[col_rev] = pd.to_numeric(tmp[col_rev], errors="coerce").fillna(0)
        g = tmp.groupby(col_name, dropna=False)[col_rev].sum().sort_values(ascending=False)
        g = g[g.index.notna()]
        top = g.head(top_n)
        if top.empty:
            return None
        tot = float(g.sum())
        out = []
        for i, (k, v) in enumerate(top.items(), start=1):
            out.append({"rank": i, "name": str(k), "revenue": float(v), "share": float(_safe_div(v, tot)) if tot else float("nan")})
        return {"total": tot, "top": out}

    top_stores = top_contrib(col_store, 5)
    top_cats = top_contrib(col_cat, 5)
    top_channels = top_contrib(col_channel, 5)

    momentum_lines = []
    tmp = df[[col_date, col_rev]].copy()
    tmp[col_date] = pd.to_datetime(tmp[col_date], errors="coerce")
    tmp[col_rev] = pd.to_numeric(tmp[col_rev], errors="coerce").fillna(0)
    tmp = tmp.dropna(subset=[col_date])

    daily = tmp.groupby(col_date, as_index=False)[col_rev].sum().sort_values(col_date)
    if len(daily) >= 10:
        mid = len(daily) // 2
        first = float(daily.iloc[:mid][col_rev].sum())
        second = float(daily.iloc[mid:][col_rev].sum())
        delta = second - first
        momentum_lines.append(f"First half revenue: {_fmt_money(first)}")
        momentum_lines.append(f"Second half revenue: {_fmt_money(second)} (Δ {_fmt_money(delta)})")
        if len(daily) >= 28:
            last14 = float(daily.iloc[-14:][col_rev].sum())
            prev14 = float(daily.iloc[-28:-14][col_rev].sum())
            mom14 = last14 - prev14
            momentum_lines.append(f"Last 14 days: {_fmt_money(last14)} vs prior 14: {_fmt_money(prev14)} (Δ {_fmt_money(mom14)})")
        peak_row = daily.loc[daily[col_rev].idxmax()]
        trough_row = daily.loc[daily[col_rev].idxmin()]
        momentum_lines.append(f"Peak day: {pd.to_datetime(peak_row[col_date]).date()} at {_fmt_money(peak_row[col_rev])}")
        momentum_lines.append(f"Lowest day: {pd.to_datetime(trough_row[col_date]).date()} at {_fmt_money(trough_row[col_rev])}")

    discount_lines = []
    if col_disc and col_disc in df.columns:
        tmp2 = df[[col_disc, col_rev]].copy()
        tmp2[col_rev] = pd.to_numeric(tmp2[col_rev], errors="coerce").fillna(0)
        disc_num = pd.to_numeric(tmp2[col_disc], errors="coerce")
        bins = [-float("inf"), 0.02, 0.05, 0.10, 0.20, float("inf")]
        labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
        tmp2["discount_band"] = pd.cut(disc_num, bins=bins, labels=labels)
        g = tmp2.groupby("discount_band", observed=False)[col_rev].agg(["mean", "count"]).reset_index()
        g = g.dropna(subset=["discount_band"]).sort_values("mean", ascending=False)
        if not g.empty:
            for _, r in g.head(5).iterrows():
                discount_lines.append(f"{r['discount_band']}: avg {_fmt_money(r['mean'])} (n={int(r['count'])})")

    def format_top(title: str, obj):
        if not obj:
            return f"{title}: N/A"
        lines = [f"{title} (by revenue):"]
        for it in obj["top"]:
            lines.append(f"- {it['rank']}. {it['name']}: {_fmt_money(it['revenue'])} ({_fmt_pct(it['share'])})")
        if len(obj["top"]) >= 2 and obj["total"]:
            top1 = obj["top"][0]["revenue"]
            top2 = obj["top"][1]["revenue"]
            lines.append(f"Concentration: Top1 {_fmt_pct(_safe_div(top1, obj['total']))}, Top2 {_fmt_pct(_safe_div(top1+top2, obj['total']))}")
        return "\n".join(lines)

    context = f"""You are EC-AI Insight. Answer strictly using the dataset facts below.
Rules:
- ALWAYS reference actual numbers from this context (use $ amounts, dates, % shares).
- Do NOT invent metrics or give generic advice.
- If something is not in context, say 'Not available in this dataset/context' and specify what column/metric would be needed.

DATASET FACTS
{chr(10).join(overview_lines)}

{format_top('Top Stores', top_stores)}

{format_top('Top Categories', top_cats)}

{format_top('Top Channels', top_channels)}

Trend / Momentum:
{chr(10).join('- ' + s for s in momentum_lines)}

Discount effectiveness (avg revenue per sale, best bands first):
{chr(10).join('- ' + s for s in discount_lines)}

Available columns: {', '.join(map(str, df.columns))}
"""
    return context


def answer_question_with_openai(question: str, context: str) -> str:
    api_key = get_api_key()
    if not api_key:
        return "OpenAI API key not configured. Add OPENAI_API_KEY in Streamlit secrets."
    if OpenAI is None:
        return "OpenAI SDK not installed. Add 'openai' to requirements.txt."

    q = (question or "").strip()
    if not q:
        return "Please enter a question."

    try:
        client = OpenAI(api_key=api_key)
        user = f"""Question:
{q}

Instructions:
- Answer using ONLY the dataset facts in the system context.
- Always cite numbers ($, %, dates) from the context when relevant.
- Use the following structure:
  1. Key Insight
  2. Business Meaning
  3. Recommended Action
- If the context lacks required info, say what is missing."""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=420,
            messages=[
                {"role": "system", "content": context.strip()},
                {"role": "user", "content": user},
            ],
        )
        response_text = (resp.choices[0].message.content or "").strip()
        return response_text or "No response."
    except Exception as e:
        return f"Ask AI error: {e}"


def render_structured_ai_answer(answer: str) -> None:
    st.markdown("<div class='ec-ai-answer'>", unsafe_allow_html=True)
    cleaned = answer.strip()

    if "1." in cleaned or "Key Insight" in cleaned:
        st.markdown(cleaned)
    else:
        st.markdown("**Key Insight**")
        st.markdown(cleaned)

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# Exports
# =========================================================
def fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> bytes:
    return fig.to_image(format="png", scale=scale)


def build_pdf_exec_brief(
    title: str,
    subtitle: str,
    summary_points: List[str],
    chart_items: List[Tuple[str, go.Figure, str]],
) -> bytes:
    if not PDF_AVAILABLE:
        raise RuntimeError("ReportLab is not installed. Add reportlab to requirements.txt.")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ECBody", parent=styles["BodyText"], fontSize=11, leading=15))
    styles.add(ParagraphStyle(name="ECTitle", parent=styles["Title"], fontSize=20, leading=24, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="ECSub", parent=styles["BodyText"], fontSize=12, leading=16, textColor="#555555"))

    story = []
    story.append(Paragraph(title, styles["ECTitle"]))
    story.append(Paragraph(subtitle, styles["ECSub"]))
    story.append(Spacer(1, 0.18 * inch))

    story.append(Paragraph("<b>Executive Summary</b>", styles["ECBody"]))
    for p in summary_points[:12]:
        _t = md_to_plain(p)
        _t = clean_display_text(_t)
        if _t:
            story.append(Paragraph(f"• {_t}", styles["ECBody"]))
    story.append(Spacer(1, 0.20 * inch))

    story.append(Paragraph("<b>Key Charts & Commentary</b>", styles["ECBody"]))
    story.append(Spacer(1, 0.12 * inch))

    for (ctitle, fig, commentary) in chart_items:
        story.append(Paragraph(f"<b>{ctitle}</b>", styles["ECBody"]))
        if commentary:
            for line in md_to_plain_lines(commentary):
                story.append(Paragraph(f"• {line}", styles["ECBody"]))
        story.append(Spacer(1, 0.10 * inch))
        png = fig_to_png_bytes(fig, scale=2)
        img_buf = io.BytesIO(png)
        img = RLImage(img_buf, width=6.7 * inch, height=3.2 * inch)
        story.append(img)
        story.append(Spacer(1, 0.22 * inch))

    doc.build(story)
    return buf.getvalue()


def _ppt_add_textbox(slide, left, top, width, height, text, font_size=18, bold=False, color=(17,24,39)):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = RGBColor(*color)
    return box


def _ppt_add_filled_box(slide, left, top, width, height, fill_rgb, line_rgb=(229,231,235), radius=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(*fill_rgb)
    shape.line.color.rgb = RGBColor(*line_rgb)
    return shape


def build_ppt_talking_deck(
    deck_title: str,
    chart_items: List[Tuple[str, go.Figure, str]],
    summary_points: Optional[List[str]] = None,
    exec_cards: Optional[List[Dict[str, str]]] = None,
) -> bytes:
    if not PPT_AVAILABLE:
        raise RuntimeError("python-pptx is not installed. Add python-pptx to requirements.txt.")

    summary_points = summary_points or []
    exec_cards = exec_cards or []

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _ppt_add_filled_box(slide, 0, 0, 13.333, 7.5, (245,247,250), line_rgb=(245,247,250))
    _ppt_add_filled_box(slide, 0.0, 0.0, 13.333, 0.45, (11,31,59), line_rgb=(11,31,59))
    _ppt_add_textbox(slide, 0.8, 1.0, 11.5, 0.8, deck_title, font_size=28, bold=True, color=(11,31,59))
    _ppt_add_textbox(slide, 0.8, 1.9, 10.5, 0.5, "Executive storyline deck", font_size=16, color=(75,85,99))
    _ppt_add_textbox(slide, 0.8, 2.8, 11.0, 1.1, "This pack highlights where revenue is made, where performance is fragile, and what management should do next.", font_size=18, color=(31,41,55))

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _ppt_add_textbox(slide, 0.6, 0.35, 12.0, 0.5, "Executive Summary", font_size=24, bold=True, color=(17,24,39))
    _ppt_add_textbox(slide, 0.6, 0.8, 12.0, 0.3, "Headline messages management can act on immediately", font_size=12, color=(107,114,128))

    card_lefts = [0.6, 4.45, 8.3]
    for i, card in enumerate(exec_cards[:3]):
        _ppt_add_filled_box(slide, card_lefts[i], 1.25, 3.35, 1.65, (255,255,255), line_rgb=(229,231,235), radius=True)
        _ppt_add_textbox(slide, card_lefts[i]+0.18, 1.42, 3.0, 0.25, str(card.get("title","")), font_size=10, bold=True, color=(107,114,128))
        _ppt_add_textbox(slide, card_lefts[i]+0.18, 1.72, 3.0, 0.45, str(card.get("value","")), font_size=21, bold=True, color=(17,24,39))
        _ppt_add_textbox(slide, card_lefts[i]+0.18, 2.18, 3.0, 0.55, str(card.get("note","")), font_size=11, color=(55,65,81))

    _ppt_add_filled_box(slide, 0.6, 3.2, 12.1, 3.6, (255,255,255), line_rgb=(229,231,235), radius=True)
    _ppt_add_textbox(slide, 0.85, 3.42, 4.0, 0.3, "What management should know", font_size=13, bold=True, color=(17,24,39))
    y = 3.78
    for point in summary_points[:6]:
        txt = md_to_plain(clean_display_text(point))
        if txt:
            _ppt_add_textbox(slide, 0.95, y, 11.2, 0.38, u"• " + txt, font_size=13, color=(31,41,55))
            y += 0.48

    for idx, (ctitle, fig, bullets) in enumerate(chart_items, start=1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _ppt_add_textbox(slide, 0.55, 0.28, 11.5, 0.45, ctitle, font_size=22, bold=True, color=(17,24,39))
        bullet_lines = [md_to_plain(l).strip("-• ").strip() for l in str(bullets).split("\n") if str(l).strip()]
        takeaway = bullet_lines[0] if bullet_lines else "Key takeaway"
        _ppt_add_filled_box(slide, 0.55, 0.82, 12.0, 0.55, (243,244,246), line_rgb=(229,231,235), radius=True)
        _ppt_add_textbox(slide, 0.75, 0.98, 11.5, 0.2, f"Takeaway: {takeaway}", font_size=12, bold=True, color=(17,24,39))

        png = fig_to_png_bytes(fig, scale=2)
        img_stream = io.BytesIO(png)
        slide.shapes.add_picture(img_stream, Inches(0.55), Inches(1.55), width=Inches(7.35), height=Inches(4.45))

        _ppt_add_filled_box(slide, 8.2, 1.55, 4.55, 4.45, (255,255,255), line_rgb=(229,231,235), radius=True)
        _ppt_add_textbox(slide, 8.45, 1.8, 3.8, 0.22, "Why it matters", font_size=12, bold=True, color=(17,24,39))
        y = 2.1
        for line in bullet_lines[:3]:
            _ppt_add_textbox(slide, 8.48, y, 3.95, 0.5, u"• " + line, font_size=12, color=(55,65,81))
            y += 0.56

        _ppt_add_filled_box(slide, 8.35, 4.75, 4.25, 0.95, (248,250,252), line_rgb=(229,231,235), radius=True)
        action_text = bullet_lines[1] if len(bullet_lines) > 1 else takeaway
        _ppt_add_textbox(slide, 8.58, 4.98, 3.8, 0.22, "Recommended action", font_size=12, bold=True, color=(17,24,39))
        _ppt_add_textbox(slide, 8.58, 5.22, 3.7, 0.38, action_text, font_size=11, color=(55,65,81))

        _ppt_add_textbox(slide, 0.58, 6.3, 12.0, 0.24, f"Slide {idx + 2} | EC-AI Insight", font_size=9, color=(107,114,128))

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


# =========================================================
# Executive dashboard
# =========================================================
def _dash_note(md: str) -> None:
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md)
    st.markdown(f"<div class='ec-dashboard-note'>{html}</div>", unsafe_allow_html=True)


def render_onepager_dashboard(m: RetailModel, df: pd.DataFrame) -> dict:
    st.markdown("<div class='ec-section-title'>Executive Dashboard</div>", unsafe_allow_html=True)

    def _as_fig(obj):
        return obj[0] if isinstance(obj, tuple) and len(obj) else obj

    def _note_for_chart(fig, normal_note: str, fallback_note: str) -> str:
        return fallback_note if fig is None else normal_note

    fig_trend_raw = line_trend(df, m.col_date, m.col_revenue, "Revenue Trend (Daily)")
    fig_trend = apply_consulting_theme(fig_trend_raw, title="Revenue Trend (Daily)", height=320, y_is_currency=True)

    fig_topstores_raw, df_top = top5_stores_bar(m)
    fig_topstores = apply_consulting_theme(fig_topstores_raw, title="Top Stores (Top 5)", height=320, y_is_currency=True)
    top_store = df_top.iloc[0]["Store"] if len(df_top) else "Top store"

    fig_cat_raw = _as_fig(revenue_by_category(m, topn=5))
    fig_cat = apply_consulting_theme(fig_cat_raw, title="Revenue by Category (Top 5)", height=320, y_is_currency=True)

    fig_price_raw = _as_fig(pricing_effectiveness(m))
    fig_price = apply_consulting_theme(fig_price_raw, title="Pricing Effectiveness", height=320, y_is_currency=True)

    fig_channel_raw = _as_fig(revenue_by_channel(m, topn=3))
    fig_channel = apply_consulting_theme(fig_channel_raw, title="Revenue by Channel (Top 3)", height=320, y_is_currency=True)

    fig_vol_raw = _as_fig(volatility_by_channel(m))
    fig_vol = apply_consulting_theme(fig_vol_raw, title="Volatility by Channel", height=320, y_is_currency=False)

    r1 = st.columns(3, gap="small")
    with r1[0]:
        with st.container(border=True):
            st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
            _dash_note("Protect **momentum**; investigate spikes and dips.")
    with r1[1]:
        with st.container(border=True):
            st.plotly_chart(fig_topstores, use_container_width=True, config={"displayModeBar": False})
            _dash_note(f"Revenue is concentrated — prioritise **{top_store}** and top drivers.")
    with r1[2]:
        with st.container(border=True):
            st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})
            _dash_note(_note_for_chart(
                fig_cat_raw,
                "Double down on **top categories**; fix weak lines.",
                "Category insight unavailable — this dataset may not include a usable category field.",
            ))

    r2 = st.columns(3, gap="small")
    with r2[0]:
        with st.container(border=True):
            st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})
            _dash_note(_note_for_chart(
                fig_price_raw,
                "Use **pricing discipline**; moderate discounts can outperform aggressive ones.",
                "Pricing insight unavailable — this dataset does not include a usable discount column.",
            ))
    with r2[1]:
        with st.container(border=True):
            st.plotly_chart(fig_channel, use_container_width=True, config={"displayModeBar": False})
            _dash_note(_note_for_chart(
                fig_channel_raw,
                "Reallocate effort to channels that **convert**; fix weakest channel.",
                "Channel insight unavailable — this dataset does not include a usable channel column.",
            ))
    with r2[2]:
        with st.container(border=True):
            st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})
            _dash_note(_note_for_chart(
                fig_vol_raw,
                "Reduce volatility: stabilise operations where swings are highest.",
                "Volatility-by-channel unavailable — this dataset does not include a usable channel column.",
            ))

    return {
        "Revenue Trend (Daily)": fig_trend,
        "Top Stores (Top 5)": fig_topstores,
        "Revenue by Category (Top 5)": fig_cat,
        "Pricing Effectiveness": fig_price,
        "Revenue by Channel (Top 3)": fig_channel,
        "Volatility by Channel": fig_vol,
    }


# =========================================================
# Main app
# =========================================================
st.title("EC-AI Insight")
st.markdown("<div class='ec-kicker'>Sales performance, explained clearly.</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='ec-subtle'>Upload your sales data and get a short business briefing — what’s working, what’s risky, and where to focus next.</div>",
    unsafe_allow_html=True
)
st.divider()

with st.sidebar:
    st.header("Data Source")
    source_mode = st.radio("Choose data source", ["Upload CSV", "Try Demo Dataset"], index=0)

    up = None
    if source_mode == "Upload CSV":
        up = st.file_uploader("Upload CSV", type=["csv"])
        st.caption("Tip: first load on Streamlit Cloud may take 30–60 seconds if the app was asleep.")
    else:
        st.caption("Using built-in demo retail dataset.")

    st.header("Exports")
    export_scale = st.slider("Export image scale", min_value=1, max_value=3, value=2, help="Higher = clearer charts, but slower exports.")

    st.header("Diagnostics")
    try:
        import plotly
        import importlib.util
        st.write("Plotly:", plotly.__version__)
        st.write("Kaleido installed:", importlib.util.find_spec("kaleido") is not None)
        st.write("OpenAI installed:", OpenAI is not None)
        st.write("PPT export:", PPT_AVAILABLE)
        st.write("PDF export:", PDF_AVAILABLE)
    except Exception as e:
        st.write("Diagnostics unavailable:", e)

# Load data
df_raw = None
if source_mode == "Try Demo Dataset":
    df_raw = build_demo_dataset()
else:
    if up is not None:
        try:
            df_raw = pd.read_csv(up)
        except Exception:
            up.seek(0)
            df_raw = pd.read_csv(up, encoding="latin-1")

if df_raw is None:
    st.info("Upload a CSV or choose Try Demo Dataset to begin.")
    st.stop()

# Prep
try:
    m = prep_retail(df_raw)
except Exception as e:
    st.error(f"Data load error: {e}")
    st.stop()

df = m.df

# Summary / cards / insights
summary_points = build_business_summary_points(m)
exec_cards = build_exec_cards(m)
ins_sections = build_business_insights_sections(m)

# Executive Dashboard
try:
    export_figures = render_onepager_dashboard(m, df)
except Exception as e:
    st.warning(f"Executive Dashboard unavailable: {e}")
    export_figures = {}

st.divider()

# Executive Summary + 3 insight cards
st.subheader("Executive Summary")
render_parallel_insight_cards(exec_cards)
st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)

for p in summary_points[:8]:
    _t = clean_display_text(p)
    if _t:
        st.markdown(f"• {emphasize_exec_keywords_html(_t)}", unsafe_allow_html=True)

st.divider()

# Charts & Insights
st.subheader("Charts & Insights")

# 1) Overall trend
fig_trend = line_trend(df, m.col_date, m.col_revenue, "Revenue Trend (Daily)")
render_chart_with_commentary(
    fig_trend,
    what_points=["Overall revenue direction over time (daily total)."],
    why_points=["Sets the context: growth vs stability.", "Helps spot spikes that may come from promotions or one-off events."],
    todo_points=["If the trend is flat, focus on execution and mix. If it’s rising, protect top drivers and scale carefully."],
    boxed_commentary=True,
)

# 2) Top 5 stores
fig_topstores, df_topstores = top5_stores_bar(m)
top_store_name = df_topstores.iloc[0]["Store"] if len(df_topstores) else "Top store"
render_chart_with_commentary(
    fig_topstores,
    what_points=[f"Revenue is concentrated in a small number of stores, led by **{top_store_name}**."],
    why_points=["Top stores disproportionately drive outcomes.", "Operational issues in one key store can move the whole month."],
    todo_points=["Prioritise stock availability, staffing, and execution in the top stores before expanding elsewhere."],
    boxed_commentary=True,
)

# 3) Store stability
st.markdown("### Store Stability (Top 5)")
figs, store_names = store_small_multiples(m)
cols = st.columns(2)
for i, fig in enumerate(figs):
    with cols[i % 2]:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

render_insight_card(
    what_points=["Some stores are steady while others swing day-to-day."],
    why_points=["Volatility makes forecasting and inventory planning harder.", "Stability is often execution rather than market demand."],
    todo_points=["Fix volatility first (availability, staffing, promotion timing). Use stable stores as benchmarks for best practices."],
)

# 4) Pricing Effectiveness
pe = pricing_effectiveness(m)
if pe is not None:
    fig_price, df_price = pe
    render_chart_with_commentary(
        fig_price,
        what_points=["Moderate discounts often perform better than aggressive discounting."],
        why_points=["Large discounts can erode revenue quality without improving outcomes.", "Pricing discipline is a repeatable advantage."],
        todo_points=["Use small discounts as default. Treat deep discounts as experiments with clear goals and limits."],
        boxed_commentary=True,
    )
else:
    st.info("Pricing Effectiveness is unavailable (no usable discount column found).")

# 5) Revenue by Category
cat = revenue_by_category(m, topn=8)
if cat is not None:
    fig_cat, _ = cat
    render_chart_with_commentary(
        fig_cat,
        what_points=["A few categories typically drive most revenue."],
        why_points=["Category mix often matters more than SKU count.", "Weak categories can drag overall performance."],
        todo_points=["Double down on winner categories (stock depth, placement). Review whether weak categories need repositioning or removal."],
        boxed_commentary=True,
    )
else:
    st.info("Category Mix is unavailable (no usable category column found).")

# 6) Revenue by Channel
ch = revenue_by_channel(m, topn=8)
if ch is not None:
    fig_ch, _ = ch
    render_chart_with_commentary(
        fig_ch,
        what_points=["Channels contribute very differently to revenue."],
        why_points=["Scaling the right channel can be cheaper than opening new stores.", "Channel concentration adds risk if one channel weakens."],
        todo_points=["Invest more in high-performing channels. Fix or rethink consistently weak channels."],
        boxed_commentary=True,
    )
else:
    st.info("Channels view is unavailable (no usable channel column found).")

st.divider()

# AI Insights
st.subheader("AI Insights")
for i, (sec_title, bullets) in enumerate(ins_sections.items()):
    st.markdown(f"#### {sec_title}")
    for b in bullets:
        t = clean_display_text(b)
        if t:
            st.markdown(f"- {emphasize_exec_keywords_html(t)}", unsafe_allow_html=True)
    if i < len(ins_sections) - 1:
        st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)


st.divider()

# Advanced analytics
with st.expander("Advanced analytics (optional)", expanded=False):
    st.caption("Optional deeper diagnostics for power users. Collapsed by default to keep the UI executive-clean.")
    try:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(num_cols) >= 2:
            corr = df[num_cols].corr(numeric_only=True)
            if m.col_revenue in corr.columns:
                top_corr = (
                    corr[m.col_revenue]
                    .drop(labels=[m.col_revenue], errors="ignore")
                    .sort_values(key=lambda s: s.abs(), ascending=False)
                    .head(10)
                    .reset_index()
                    .rename(columns={"index": "Metric", m.col_revenue: "Correlation"})
                )
                st.markdown("**Top correlations with Revenue (directional)**")
                st.dataframe(top_corr, use_container_width=True, hide_index=True)

            st.markdown("**Correlation heatmap (numeric metrics)**")
            fig_corr = px.imshow(
                corr.round(2),
                text_auto=".2f",
                aspect="auto",
                color_continuous_scale="Blues",
            )
            fig_corr.update_traces(textfont=dict(color="white", size=12))
            fig_corr.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=420)
            st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Not enough numeric columns to compute correlations.")
    except Exception as e:
        st.warning(f"Advanced analytics unavailable: {e}")

# Ask AI
st.subheader("Ask AI (CEO Q&A)")
st.caption("Ask questions about your data (for example: Why did revenue soften? Which store should I fix first?)")

_context_lines: List[str] = []
try:
    _context_lines.append(f"Dataset: {len(df)} rows, {df[m.col_date].nunique()} days.")
except Exception:
    pass

try:
    _context_lines += [f"- {clean_display_text(x)}" for x in summary_points if clean_display_text(x)]
except Exception:
    pass

try:
    for sec_title, bullets in ins_sections.items():
        _context_lines.append(f"{sec_title}:")
        _context_lines += [f"- {clean_display_text(x)}" for x in bullets if clean_display_text(x)]
except Exception:
    pass

dashboard_notes = "\n".join([x for x in _context_lines if x]).strip()
context_text = _build_ai_context(df, m)
if dashboard_notes:
    context_text = context_text + "\n\nDASHBOARD INSIGHTS (auto-generated):\n" + dashboard_notes

if "ask_ai_history" not in st.session_state:
    st.session_state.ask_ai_history = []
if "ask_ai_question" not in st.session_state:
    st.session_state.ask_ai_question = ""

st.markdown("**Suggested Questions**")
sq1, sq2, sq3 = st.columns(3)
with sq1:
    if st.button("Which store should I fix first?", use_container_width=True):
        st.session_state.ask_ai_question = "Which store should I fix first and why?"
with sq2:
    if st.button("Is discounting helping or hurting?", use_container_width=True):
        st.session_state.ask_ai_question = "Is discounting helping or hurting revenue quality?"
with sq3:
    if st.button("What should management do next?", use_container_width=True):
        st.session_state.ask_ai_question = "What should management focus on next based on this dataset?"

q_col, btn_col = st.columns([0.82, 0.18])
with q_col:
    user_q = st.text_input(
        "Ask EC-AI…",
        value=st.session_state.ask_ai_question,
        key="ask_ai_question_input",
        placeholder="E.g., What should I focus on next week?",
    )
with btn_col:
    ask_clicked = st.button("Ask", use_container_width=True)

if ask_clicked and user_q.strip():
    with st.spinner("Thinking…"):
        answer = answer_question_with_openai(user_q.strip(), context_text)
    st.session_state.ask_ai_history.insert(0, (user_q.strip(), answer))
    st.session_state.ask_ai_history = st.session_state.ask_ai_history[:6]

for q, a in st.session_state.ask_ai_history[:3]:
    st.markdown(f"**Q:** {q}")
    render_structured_ai_answer(a)

st.divider()

# Export pack
st.subheader("Export Executive Pack")
st.caption("Download a shareable executive-ready brief (PDF) or slide pack (PPTX).")

chart_items: List[Tuple[str, go.Figure, str]] = []

try:
    chart_items.append((
        "Revenue Trend (Daily)",
        fig_trend,
        "Trend line of daily revenue.\nUse this to spot spikes and dips and protect momentum."
    ))
except Exception:
    pass

try:
    chart_items.append((
        "Top Revenue-Generating Stores (Top 5)",
        fig_topstores,
        "Revenue concentration by store.\nPrioritise execution in the top stores first."
    ))
except Exception:
    pass

try:
    if pe is not None:
        chart_items.append((
            "Pricing Effectiveness — Avg Revenue per Sale by Discount Level",
            fig_price,
            "Compares average revenue per sale across discount levels.\nUse moderate discounts by default; treat deep discounts as controlled tests."
        ))
except Exception:
    pass

try:
    if cat is not None:
        chart_items.append((
            "Revenue by Category",
            fig_cat,
            "Shows which categories drive revenue.\nDouble down on winners; fix or trim weak categories."
        ))
except Exception:
    pass

try:
    if ch is not None:
        chart_items.append((
            "Revenue by Channel",
            fig_ch,
            "Channel contribution to revenue.\nReallocate effort to channels that consistently perform."
        ))
except Exception:
    pass

c1, c2 = st.columns(2)

with c1:
    if st.button("Generate PDF Executive Brief", use_container_width=True):
        try:
            pdf_bytes = build_pdf_exec_brief(
                title="EC-AI Insight — Executive Brief",
                subtitle="Sales performance, explained clearly.",
                summary_points=summary_points,
                chart_items=chart_items,
            )
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name="ecai_executive_brief.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

with c2:
    if st.button("Generate Executive Pack (PPTX)", use_container_width=True):
        try:
            pptx_bytes = build_ppt_talking_deck(
                deck_title="EC-AI Insight — Executive Pack",
                chart_items=chart_items,
                summary_points=summary_points,
                exec_cards=exec_cards,
            )
            st.download_button(
                "Download PPTX",
                data=pptx_bytes,
                file_name="ecai_executive_pack.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PPT generation failed: {e}")
