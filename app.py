# EC-AI Insight — Retail Sales MVP (Founder-first)
# -------------------------------------------------
# This Streamlit app is intentionally opinionated:
# Meaning first, charts second. Advanced analytics are optional.
#
# Requirements (recommended pins for Streamlit Cloud):
#   streamlit
#   pandas
#   numpy
#   plotly==5.22.0
#   kaleido==0.2.1
#   python-pptx
#   reportlab

from __future__ import annotations

import io
import re
import textwrap
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

import plotly.graph_objects as go
import plotly.express as px

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
@dataclass
class RetailModel:
    df: pd.DataFrame
    col_date: str
    col_store: str
    col_revenue: str
    col_category: Optional[str]
    col_channel: Optional[str]
    col_payment: Optional[str]
    col_discount: Optional[str]
    col_qty: Optional[str]

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
    """12 bullets, human founder language. Avoid tech terms and avoid noisy number formatting."""
    df = m.df
    dmin, dmax = df[m.col_date].min(), df[m.col_date].max()
    days = max((dmax - dmin).days + 1, 1)

    total_rev = df[m.col_revenue].sum()
    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)
    top_store = store_rev.index[0] if len(store_rev) else "—"
    top_store_share = (store_rev.iloc[0] / total_rev) if total_rev > 0 and len(store_rev) else np.nan
    top2_share = (store_rev.iloc[:2].sum() / total_rev) if total_rev > 0 and len(store_rev) >= 2 else np.nan
    top5_share = (store_rev.iloc[:5].sum() / total_rev) if total_rev > 0 and len(store_rev) >= 5 else np.nan

    # Growth: compare first half vs second half
    df_sorted = df.sort_values(m.col_date)
    mid = df_sorted[m.col_date].min() + pd.Timedelta(days=days/2)
    rev_first = df_sorted.loc[df_sorted[m.col_date] <= mid, m.col_revenue].sum()
    rev_second = df_sorted.loc[df_sorted[m.col_date] > mid, m.col_revenue].sum()
    growth = (rev_second - rev_first) / rev_first if rev_first > 0 else np.nan

    # Uneven across stores: use store growth dispersion if possible
    # compute store revenue in first vs second
    g_store = None
    try:
        a = df_sorted.loc[df_sorted[m.col_date] <= mid].groupby(m.col_store)[m.col_revenue].sum()
        b = df_sorted.loc[df_sorted[m.col_date] > mid].groupby(m.col_store)[m.col_revenue].sum()
        common = a.index.union(b.index)
        a = a.reindex(common).fillna(0)
        b = b.reindex(common).fillna(0)
        store_growth = (b - a) / a.replace(0, np.nan)
        g_store = float(np.nanstd(store_growth.values))
    except Exception:
        g_store = None

    # Volatility proxy: per-store daily revenue std / mean (but describe as "ups and downs", not CV)
    daily = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol = daily.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol["ratio"] = vol["std"] / vol["mean"]
    most_volatile_store = vol["ratio"].sort_values(ascending=False).index[0] if len(vol) else None
    most_stable_store = vol["ratio"].sort_values().index[0] if len(vol) else None

    # Discount effectiveness: avg revenue per sale by discount bands
    discount_note = None
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 20:
            # define bands
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            # use revenue per transaction row
            agg = tmp.groupby("disc_band")[m.col_revenue].mean()
            if agg.notna().sum() >= 2:
                best_band = agg.sort_values(ascending=False).index[0]
                worst_band = agg.sort_values(ascending=True).index[0]
                discount_note = (str(best_band), str(worst_band))

    points: List[str] = []

    # Where money comes from
    points.append(f"Revenue is concentrated in a small number of stores, with **{top_store}** as a key driver of overall performance.")
    if not np.isnan(top2_share):
        points.append(f"The top two stores together account for about **{safe_pct(top2_share)}** of total revenue — store execution matters more than you think.")
    if not np.isnan(top5_share):
        points.append(f"The top five stores contribute roughly **{safe_pct(top5_share)}** of revenue, so improving these locations delivers the fastest ROI.")

    # Growth context
    if not np.isnan(growth):
        if growth > 0.05:
            points.append(f"Sales are growing over the period (about **{safe_pct(growth)}** higher in the second half), but the growth is not evenly shared.")
        elif growth < -0.05:
            points.append(f"Sales softened over the period (about **{safe_pct(abs(growth))}** lower in the second half), so protecting strong stores becomes more important.")
        else:
            points.append("Overall sales are relatively steady across the period — performance differences are mainly store-to-store, not market-wide.")
    else:
        points.append("Overall sales direction is visible in the trend chart; the bigger story is which stores are driving (or dragging) results.")

    if g_store is not None and not np.isnan(g_store):
        points.append("Growth is uneven across stores, suggesting execution differences rather than broad demand changes.")

    # Fragility / stability
    if most_stable_store is not None and most_volatile_store is not None:
        points.append(f"Some stores are stable and predictable (e.g., **{most_stable_store}**), while others swing sharply day-to-day (e.g., **{most_volatile_store}**).")
        points.append("These ups and downs are usually operational (stock, staffing, local promotion timing) more than customer demand.")
    else:
        points.append("Some stores appear stable while others swing day-to-day — consistency is a major lever for improving performance.")

    # Pricing effectiveness
    if discount_note is not None:
        best_band, worst_band = discount_note
        points.append(f"Moderate discounting tends to work best (**{best_band}** performs stronger than deeper discounts). Bigger discounts do not automatically lead to better results.")
        points.append(f"Deep discounting (e.g., **{worst_band}**) risks reducing revenue quality without building sustainable growth.")
    else:
        points.append("Moderate discounts often perform better than aggressive discounting. Treat large discounts as controlled experiments, not default strategy.")

    # Action focus
    points.append("The biggest opportunity is to strengthen and standardize what already works in top-performing stores before expanding promotions or assortment.")
    points.append("Improving consistency will likely deliver more value than launching more campaigns — fix volatility first, then scale.")
    points.append("Use this dashboard as a weekly business review: focus on top stores, pricing discipline, and operational stability.")

    # Ensure 10+ points
    if len(points) < 10:
        points.extend([
            "If you can improve execution in just one top store, it can move the entire business outcome.",
            "Prefer simple, repeatable wins (availability, in-store execution) over complex analytics.",
        ])

    return points[:12]

# -----------------------------
# Chart builders (strict categorical alignment)
# -----------------------------
def fig_style_common(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title, x=0.0, xanchor="left", font=dict(size=18)),
        margin=dict(l=40, r=20, t=60, b=55),
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(title=None, tickfont=dict(size=12))
    fig.update_yaxes(title=None, tickfont=dict(size=12), gridcolor="rgba(0,0,0,0.08)")
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
            textposition="outside",
            cliponaxis=False,
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
            mode="lines+markers",
            line=dict(width=3, color=TABLEAU10[0]),
            marker=dict(size=5, color=TABLEAU10[0]),
            hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.0f}<extra></extra>",
        )
    )
    fig = fig_style_common(fig, title)
    fig.update_layout(height=340)
    fig.update_xaxes(tickformat="%b %d")
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
        fig = fig_style_common(fig, f"Store Trend — {store}")
        fig.update_layout(height=250, showlegend=False)
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
        st.markdown(f"- {w}")
    st.markdown("**Why it matters**")
    for w in why:
        st.markdown(f"- {w}")
    st.markdown("**What to do**")
    for a in action:
        st.markdown(f"- {a}")
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

    story.append(Paragraph("<b>Business Summary</b>", styles["ECBody"]))
    for p in summary_points[:12]:
        story.append(Paragraph(f"• {p}", styles["ECBody"]))
    story.append(Spacer(1, 0.20*inch))

    story.append(Paragraph("<b>Key Charts & Commentary</b>", styles["ECBody"]))
    story.append(Spacer(1, 0.12*inch))

    for (ctitle, fig, commentary) in chart_items:
        # Title
        story.append(Paragraph(f"<b>{ctitle}</b>", styles["ECBody"]))
        # Commentary
        if commentary:
            for line in commentary.split("\n"):
                line = line.strip()
                if line:
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
            lines = [l.strip("-• ").strip() for l in bullets.split("\n") if l.strip()]
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
# Business Summary (DEFAULT)
# -----------------------------
summary_points = build_business_summary_points(m)

st.subheader("Business Summary")
for p in summary_points[:12]:
    st.markdown(f"• {p}")

st.divider()

# -----------------------------
# Business Insights (DEFAULT)
# -----------------------------
st.subheader("Business Insights")

# Add a little spacing between mini-sections
st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)

st.markdown("#### Where the money is made")
st.markdown("- Revenue is driven by a small number of key stores and categories.")
st.markdown("- Small improvements in top stores typically move total performance the most.")

st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)
st.markdown("#### Where risk exists")
st.markdown("- Store and channel stability affects predictability and planning.")
st.markdown("- Concentration in a few stores increases downside risk when execution slips.")

st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)
st.markdown("#### What can be improved")
st.markdown("- Pricing discipline often beats aggressive discounting.")
st.markdown("- Consistency (stock, staffing, execution) tends to deliver higher ROI than new campaigns.")

st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)
st.markdown("#### What to focus on next")
st.markdown("- Strengthen top stores first, then scale.")
st.markdown("- Fix volatility before pushing growth through discounts or expansion.")

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
        fig_corr.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=50, b=40), height=420, title=dict(text="Numeric Correlation (Advanced)", x=0))
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Not enough numeric fields to compute correlation.")

    vol_ch = volatility_by_channel(m)
    if vol_ch is not None:
        fig_vol, _ = vol_ch
        st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})

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
