
# app.py
# EC-AI Insight — Sales / Retail Transactions MVP (Founder-first)
# - Business Summary (human) + Business Insights
# - Core visuals (clean, Tableau-like colors)
# - Further Analysis (3 extra charts)
# - Advanced (collapsed): Preview data + Data profile + Correlation
# - Exports: PDF Executive Brief + PPT Talking Deck (16:9) with charts + commentary

import io
import math
import textwrap
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Optional deps for export (keep imports inside functions where possible)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


# ----------------------------
# Styling
# ----------------------------
TABLEAU10 = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"
]

PLOTLY_TEMPLATE = "plotly_white"

st.set_page_config(page_title="EC-AI Insight", layout="wide")

BASE_CSS = """<style>
html, body, [class*="css"]  { font-size: 17px; }
h1 { margin-bottom: 0.2rem; }
h2, h3 { margin-top: 0.6rem; }
.ec-subtitle { font-size: 18px; color: #666; margin-top: -0.25rem; }
.ec-hint { font-size: 14px; color: #666; }
.ec-card { background: #ffffff; border: 1px solid #e9ecef; border-radius: 14px; padding: 16px 18px; margin: 10px 0 6px 0; }
.ec-card h3 { margin: 0 0 8px 0; font-size: 18px; }
.ec-card ul { margin: 0.2rem 0 0 1.1rem; }
.ec-space { height: 6px; }
</style>"""
st.markdown(BASE_CSS, unsafe_allow_html=True)


# ----------------------------
# Utilities
# ----------------------------
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

def find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    norm_map = {_norm(c): c for c in df.columns}
    for cand in candidates:
        n = _norm(cand)
        if n in norm_map:
            return norm_map[n]
    # fuzzy contains
    for col in df.columns:
        nc = _norm(col)
        for cand in candidates:
            if _norm(cand) in nc or nc in _norm(cand):
                return col
    return None

def to_number(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce")

def fmt_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    ax = abs(float(x))
    if ax >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if ax >= 1_000:
        return f"${x/1_000:.1f}K"
    return f"${x:,.0f}"

def fmt_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x*100:.1f}%"

def safe_div(a: float, b: float) -> float:
    if b is None or b == 0 or (isinstance(b, float) and np.isnan(b)):
        return np.nan
    return a / b

def wrap_title(s: str, width: int = 48) -> str:
    # For PDF/PPT titles (avoid truncation)
    return "\n".join(textwrap.wrap(s, width=width)) if len(s) > width else s


# ----------------------------
# Chart helpers (alignment + colors)
# ----------------------------
def make_bar_categorical(
    title: str,
    x_labels: List[str],
    y_values: List[float],
    y_title: str,
    colors: Optional[List[str]] = None,
    height: int = 360,
) -> go.Figure:
    x_labels = [str(x) for x in x_labels]
    colors = (colors or TABLEAU10)[: len(x_labels)]
    fig = go.Figure(
        data=[
            go.Bar(
                x=x_labels,
                y=y_values,
                marker_color=colors,
                text=[fmt_money(v) if y_title.lower().startswith("revenue") else (f"{v:.2f}" if isinstance(v, (float, int)) else str(v)) for v in y_values],
                textposition="outside",
                cliponaxis=False,
            )
        ]
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        title=None,  # titles handled by Streamlit/PDF/PPT text to avoid cropping
        margin=dict(l=50, r=30, t=20, b=60),
        bargap=0.35,
    )
    fig.update_yaxes(title=y_title, rangemode="tozero")
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=x_labels,
        tickmode="array",
        tickvals=x_labels,
        ticktext=x_labels,
        tickangle=0,
        title=None,
    )
    return fig

def make_line_trend(
    title: str,
    x: pd.Series,
    y: pd.Series,
    line_color: str,
    height: int = 260,
) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Scatter(
                x=x,
                y=y,
                mode="lines+markers",
                line=dict(color=line_color, width=3),
                marker=dict(size=5, color=line_color),
            )
        ]
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        title=dict(text=title, x=0, xanchor="left"),
        margin=dict(l=45, r=20, t=60, b=55),
    )
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, rangemode="tozero")
    return fig

def fig_to_png_bytes(fig: go.Figure, width: int = 1200, height: int = 650) -> bytes:
    # Requires kaleido installed in runtime
    # Remove internal titles to avoid cropping inside export images
    fig2 = fig.full_figure_for_development(warn=False)
    fig2.update_layout(title=None, margin=dict(l=60, r=40, t=30, b=70))
    return fig2.to_image(format="png", width=width, height=height, scale=2)


# ----------------------------
# Export helpers
# ----------------------------
def build_pdf_executive_brief(
    filepath: str,
    business_summary: List[str],
    business_insights: Dict[str, List[str]],
    chart_items: List[Tuple[str, go.Figure, str]],
) -> None:
    # chart_items: (title, fig, commentary)
    c = canvas.Canvas(filepath, pagesize=LETTER)
    W, H = LETTER

    def draw_paragraph(text: str, x: float, y: float, max_width: float, font="Helvetica", size=11, leading=14) -> float:
        c.setFont(font, size)
        lines = []
        for para in text.split("\n"):
            lines.extend(textwrap.wrap(para, width=max(20, int(max_width / 6.2))) or [""])
        for ln in lines:
            c.drawString(x, y, ln)
            y -= leading
        return y

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(0.8 * inch, H - 0.9 * inch, "EC-AI Insight — Executive Brief")
    c.setFont("Helvetica", 10)
    c.drawString(0.8 * inch, H - 1.15 * inch, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y = H - 1.55 * inch

    # Business Summary
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.8 * inch, y, "Business Summary")
    y -= 0.25 * inch

    c.setFont("Helvetica", 11)
    for b in business_summary:
        y = draw_paragraph(f"• {b}", 0.9 * inch, y, W - 1.6 * inch, size=11)
        y -= 3
        if y < 1.2 * inch:
            c.showPage()
            y = H - 0.9 * inch

    y -= 0.15 * inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.8 * inch, y, "Business Insights")
    y -= 0.25 * inch

    for section, bullets in business_insights.items():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0.9 * inch, y, section)
        y -= 0.18 * inch
        c.setFont("Helvetica", 11)
        for b in bullets:
            y = draw_paragraph(f"• {b}", 1.05 * inch, y, W - 1.8 * inch, size=11)
            y -= 2
            if y < 1.2 * inch:
                c.showPage()
                y = H - 0.9 * inch
        y -= 0.1 * inch

    # Charts + commentary
    for (title, fig, comm) in chart_items:
        if y < 3.8 * inch:
            c.showPage()
            y = H - 0.9 * inch

        c.setFont("Helvetica-Bold", 13)
        title_wrapped = wrap_title(title, 56)
        y = draw_paragraph(title_wrapped, 0.8 * inch, y, W - 1.6 * inch, font="Helvetica-Bold", size=13, leading=15)
        y -= 0.08 * inch

        # commentary
        if comm:
            y = draw_paragraph(comm, 0.9 * inch, y, W - 1.8 * inch, size=11, leading=14)
            y -= 0.1 * inch

        try:
            img_bytes = fig_to_png_bytes(fig)
            img = ImageReader(io.BytesIO(img_bytes))
            img_w = W - 1.6 * inch
            img_h = 3.1 * inch
            c.drawImage(img, 0.8 * inch, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, anchor="n")
            y -= (img_h + 0.25 * inch)
        except Exception as e:
            c.setFont("Helvetica", 10)
            y = draw_paragraph(f"[Chart export failed: {e}]", 0.9 * inch, y, W - 1.8 * inch, size=10)
            y -= 0.2 * inch

    c.save()


def build_ppt_talking_deck(
    filepath: str,
    slides: List[Tuple[str, str, Optional[go.Figure]]],
) -> None:
    # slides: (title, commentary, fig)
    prs = Presentation()
    # Set 16:9
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank = prs.slide_layouts[6]

    def add_title(slide, title: str):
        tx = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.2), Inches(0.8))
        tf = tx.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.name = "Calibri"
        p.alignment = PP_ALIGN.LEFT

    def add_body(slide, body: str):
        tx = slide.shapes.add_textbox(Inches(0.6), Inches(6.35), Inches(12.2), Inches(1.0))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.clear()
        p = tf.paragraphs[0]
        p.text = body
        p.font.size = Pt(16)
        p.font.name = "Calibri"
        p.alignment = PP_ALIGN.LEFT

    for title, comm, fig in slides:
        slide = prs.slides.add_slide(blank)
        add_title(slide, wrap_title(title, 60))

        if fig is not None:
            try:
                img_bytes = fig_to_png_bytes(fig, width=1400, height=760)
                image_stream = io.BytesIO(img_bytes)
                # Fit chart nicely between title and body
                slide.shapes.add_picture(image_stream, Inches(0.8), Inches(1.25), width=Inches(11.7), height=Inches(4.9))
            except Exception as e:
                comm = (comm + f"\n\n[Chart export failed: {e}]").strip()

        add_body(slide, comm)

    prs.save(filepath)


# ----------------------------
# App
# ----------------------------
st.title("EC-AI Insight")
st.markdown('<div class="ec-subtitle">Sales performance, explained clearly.</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ec-hint">Upload your sales data and get a short business briefing — what’s working, what’s risky, and where to focus next.</div>',
    unsafe_allow_html=True
)

st.divider()

uploaded = st.file_uploader("Upload retail sales / transaction data (CSV)", type=["csv"])

if not uploaded:
    st.info("Upload a retail sales CSV to begin. (Tip: include Date, Store, Revenue/Sales; optional: COGS, Discount, Channel, Category, Payment Method.)")
    st.stop()

df = pd.read_csv(uploaded)
df.columns = [c.strip() for c in df.columns]

# Detect columns
date_col = find_col(df, ["date", "transactiondate", "orderdate"])
store_col = find_col(df, ["store", "branch", "location"])
rev_col = find_col(df, ["revenue", "sales", "amount", "net_sales", "total"])
cogs_col = find_col(df, ["cogs", "cost", "cost_of_goods", "costofgoods"])
disc_col = find_col(df, ["discount", "discount_rate", "discountrate", "discount_pct", "discountpercent"])
cat_col = find_col(df, ["category", "product_category", "dept", "department"])
channel_col = find_col(df, ["channel", "sales_channel", "platform"])
pay_col = find_col(df, ["payment_method", "payment", "paymethod", "tender"])

if rev_col is None:
    st.error("I couldn't find a Revenue/Sales column. Please include a column like 'Revenue' or 'Sales'.")
    st.stop()

df["_Revenue"] = to_number(df[rev_col]).fillna(0.0)

if date_col:
    df["_Date"] = pd.to_datetime(df[date_col], errors="coerce")
else:
    df["_Date"] = pd.NaT

if store_col:
    df["_Store"] = df[store_col].astype(str)
else:
    df["_Store"] = "All Stores"

if disc_col:
    df["_Discount"] = to_number(df[disc_col])
else:
    df["_Discount"] = np.nan

# Discount bands (as strings)
def discount_band(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "No discount"
    # treat as rate if <=1 else percent
    r = x if x <= 1 else x / 100.0
    if r < 0.0001:
        return "No discount"
    if r <= 0.02:
        return "0–2%"
    if r <= 0.05:
        return "2–5%"
    if r <= 0.10:
        return "5–10%"
    if r <= 0.15:
        return "10–15%"
    return "15–20%"

df["_DiscountBand"] = df["_Discount"].apply(discount_band)

# Basic metrics
total_rev = float(df["_Revenue"].sum())
n_rows = int(len(df))

# Date range & growth
rev_by_date = None
date_range_txt = None
growth_pct = np.nan
peak_day_txt = None
if date_col and df["_Date"].notna().any():
    rev_by_date = df.dropna(subset=["_Date"]).groupby(df["_Date"].dt.date)["_Revenue"].sum().sort_index()
    if len(rev_by_date) >= 2:
        first = float(rev_by_date.iloc[0])
        last = float(rev_by_date.iloc[-1])
        growth_pct = safe_div((last - first), max(first, 1e-9))
    date_range_txt = f"{rev_by_date.index.min()} to {rev_by_date.index.max()}"
    peak_day_txt = str(rev_by_date.idxmax())
else:
    rev_by_date = pd.Series([], dtype=float)

# Top stores
store_rev = df.groupby("_Store")["_Revenue"].sum().sort_values(ascending=False)
top5_stores = store_rev.head(5)
top_store = top5_stores.index[0] if len(top5_stores) > 0 else "—"
second_store = top5_stores.index[1] if len(top5_stores) > 1 else None
top_share = safe_div(float(top5_stores.sum()), total_rev) if total_rev > 0 else np.nan

# Volatility (store daily std/mean)
store_vol = pd.Series([], dtype=float)
if date_col and df["_Date"].notna().any() and store_col:
    tmp = df.dropna(subset=["_Date"]).copy()
    tmp["__d"] = tmp["_Date"].dt.date
    daily = tmp.groupby(["_Store", "__d"])["_Revenue"].sum()
    vol = daily.groupby(level=0).agg(["mean", "std"])
    vol["cv"] = vol["std"] / vol["mean"].replace(0, np.nan)
    store_vol = vol["cv"].sort_values(ascending=False)

# Discount effectiveness (avg revenue per record by band)
band_order = ["No discount", "0–2%", "2–5%", "5–10%", "10–15%", "15–20%"]
band_stats = df.groupby("_DiscountBand")["_Revenue"].agg(["mean", "count"]).reindex(band_order)
band_stats = band_stats.dropna(subset=["mean"])
present_bands = [b for b in band_order if b in band_stats.index]

best_band = None
if len(band_stats) > 0:
    best_band = band_stats["mean"].idxmax()

# ----------------------------
# Business Summary (10 bullets, human)
# ----------------------------
bullets: List[str] = []
bullets.append(f"Total revenue in this file is {fmt_money(total_rev)} across {n_rows:,} transactions/rows.")
if date_range_txt:
    bullets.append(f"This data covers {date_range_txt}. Think of it as a snapshot for spotting patterns, not a full-year view.")
if not (isinstance(growth_pct, float) and np.isnan(growth_pct)):
    if growth_pct > 0:
        bullets.append(f"Sales ended higher than they started over the period (roughly {fmt_pct(growth_pct)} growth from start to end)." )
    else:
        bullets.append(f"Sales ended lower than they started over the period (roughly {fmt_pct(abs(growth_pct))} decline from start to end)." )
if peak_day_txt:
    bullets.append(f"The strongest sales day in the period was {peak_day_txt}.")

if len(top5_stores) > 0:
    bullets.append(f"Revenue is concentrated: the top 5 stores contribute about {fmt_pct(top_share)} of total sales.")
    bullets.append(f"Your top store is **{top_store}** at {fmt_money(float(top5_stores.iloc[0]))}.")

if second_store:
    bullets.append(f"Second is **{second_store}** at {fmt_money(float(top5_stores.loc[second_store]))} — these two deserve extra attention.")

if len(store_vol) > 0:
    # phrase as inconsistency rather than 'volatile is ridiculous'
    most_inconsistent = store_vol.index[0]
    bullets.append(f"Some stores are more inconsistent day-to-day than others (for example **{most_inconsistent}** swings more). This is usually promotions, stockouts, staffing, or local execution.")

if best_band is not None:
    bullets.append(f"Discounting: in this snapshot, **{best_band}** shows the highest average revenue per sale. Use this as a starting point — verify by store/channel.")

bullets.append("If you want quick wins: focus on stabilising top stores first, then tune discounts and promotions based on what actually lifts revenue.")
bullets.append("Next: review the 4 core visuals below, then open ‘Further Analysis’ for simple breakdowns by category/channel/payment.")
# ensure at least 10
while len(bullets) < 10:
    bullets.append("Keep the story simple: what’s working, what’s risky, and one action to try next week.")

# ----------------------------
# Business Insights (renamed)
# ----------------------------
insights = {
    "Where the money is made": [
        f"Top store: {top_store} ({fmt_money(float(top5_stores.iloc[0]))})" if len(top5_stores) else "Top store: —",
        f"Top 5 stores contribute ~{fmt_pct(top_share)} of revenue" if not (isinstance(top_share, float) and np.isnan(top_share)) else "Revenue concentration: —",
    ],
    "Where risk exists": [
        "High concentration means performance depends heavily on a few locations — great when stable, risky when not.",
        "If daily performance swings a lot, it often points to operational inconsistency (stock, staffing, promotions) rather than demand.",
    ],
    "What can be improved": [
        "Avoid ‘automatic discounting’. Use discounts only where they clearly lift revenue, not where they simply reduce price.",
        "Treat the store trends as an execution dashboard: stabilise the winners before expanding campaigns.",
    ],
    "What to focus on next": [
        "Confirm what drives revenue in top stores (assortment, staffing, inventory availability).",
        "Review discount levels and stop the ones that reduce revenue efficiency.",
        "Use Further Analysis to identify which categories/channels/payment methods are associated with higher sales.",
    ],
}

# ----------------------------
# UI Rendering
# ----------------------------
def render_card(title: str, bullet_list: List[str]):
    html = f'<div class="ec-card"><h3>{title}</h3><ul>'
    for b in bullet_list:
        html += f"<li>{b}</li>"
    html += "</ul></div>"
    st.markdown(html, unsafe_allow_html=True)

render_card("Business Summary", bullets)

st.divider()
st.subheader("Business Insights")

# spacing between subsections
for section, blts in insights.items():
    st.markdown(f"### {section}")
    st.markdown("\n".join([f"• {x}" for x in blts]))
    st.markdown('<div class="ec-space"></div>', unsafe_allow_html=True)

st.divider()
st.subheader("Key Performance Visuals")

charts_for_export: List[Tuple[str, go.Figure, str]] = []

# 1) Revenue Trend
st.markdown("#### Revenue Trend")
if len(rev_by_date) > 0:
    fig_trend = make_line_trend(
        "Revenue Trend",
        x=pd.to_datetime(rev_by_date.index),
        y=rev_by_date.values,
        line_color=TABLEAU10[0],
        height=340,
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    charts_for_export.append(("Revenue Trend", fig_trend, "Overall revenue trend across the period." ))
else:
    st.info("No Date column detected (or dates are missing). Add a Date column to enable trend analysis.")

st.divider()

# 2) Top 5 Stores bar (5 colors)
st.markdown("#### Top Revenue-Generating Stores (Top 5)")
if len(top5_stores) > 0:
    fig_top5 = make_bar_categorical(
        "Top Stores",
        x_labels=list(top5_stores.index),
        y_values=[float(v) for v in top5_stores.values],
        y_title="Revenue",
        colors=TABLEAU10[: len(top5_stores)],
        height=380,
    )
    st.plotly_chart(fig_top5, use_container_width=True)
    charts_for_export.append(("Top 5 Stores by Revenue", fig_top5, "Where most revenue is generated (Top 5 stores)." ))
else:
    st.info("Store column not detected. Add a Store/Branch column for store-level insights.")

st.divider()

# 3) Store stability (small multiples, 5 colors)
st.markdown("#### Store Stability (Top 5) — one store per chart")
if date_col and df["_Date"].notna().any() and len(top5_stores) > 0:
    tmp = df.dropna(subset=["_Date"]).copy()
    tmp["__d"] = tmp["_Date"].dt.date
    daily_store = tmp.groupby(["_Store", "__d"])["_Revenue"].sum().reset_index()
    cols = st.columns(2)
    figs_sm: List[Tuple[str, go.Figure]] = []
    for i, store in enumerate(list(top5_stores.index)):
        sub = daily_store[daily_store["_Store"] == store].sort_values("__d")
        fig = make_line_trend(
            store,
            x=pd.to_datetime(sub["__d"]),
            y=sub["_Revenue"],
            line_color=TABLEAU10[i % len(TABLEAU10)],
            height=260,
        )
        figs_sm.append((store, fig))
        with cols[i % 2]:
            st.markdown(f"**{store}**")
            st.plotly_chart(fig, use_container_width=True)
    # For export, include one combined representative chart (top store)
    charts_for_export.append(("Store Stability — Top Store", figs_sm[0][1], "Daily revenue pattern for the top store." ))
else:
    st.info("Need Date + Store to show store stability. Add both columns to your dataset.")

st.divider()

# 4) Pricing effectiveness (aligned categorical)
st.markdown("#### Pricing Effectiveness — average revenue per sale by discount band")
pricing_present = band_stats.dropna(subset=["mean"])
if len(pricing_present) > 0:
    x = [str(i) for i in pricing_present.index.tolist()]
    y = [float(v) for v in pricing_present["mean"].values]
    fig_price = make_bar_categorical(
        "Average Revenue per Sale by Discount Band",
        x_labels=x,
        y_values=y,
        y_title="Average revenue per sale",
        colors=TABLEAU10[: len(x)],
        height=360,
    )
    st.plotly_chart(fig_price, use_container_width=True)
    charts_for_export.append(("Pricing Effectiveness", fig_price, "Directional view of discount bands vs average revenue per sale." ))
else:
    st.info("No discount information detected. Add a Discount column (rate or %) for pricing analysis.")

# ----------------------------
# Further analysis (3 extra charts, shown by default)
# ----------------------------
st.divider()
st.subheader("Further Analysis (recommended)")

# Revenue by Category (Top 8)
if cat_col:
    by_cat = df.groupby(cat_col)["_Revenue"].sum().sort_values(ascending=False).head(8)
    fig_cat = make_bar_categorical(
        "Revenue by Category (Top)",
        x_labels=[str(x) for x in by_cat.index.tolist()],
        y_values=[float(v) for v in by_cat.values],
        y_title="Revenue",
        colors=TABLEAU10[: len(by_cat)],
        height=360,
    )
    st.plotly_chart(fig_cat, use_container_width=True)
    charts_for_export.append(("Revenue by Category (Top)", fig_cat, "Which product categories contribute most revenue." ))

# Revenue by Payment Method (Top 8)
if pay_col:
    by_pay = df.groupby(pay_col)["_Revenue"].sum().sort_values(ascending=False).head(8)
    fig_pay = make_bar_categorical(
        "Revenue by Payment Method (Top)",
        x_labels=[str(x) for x in by_pay.index.tolist()],
        y_values=[float(v) for v in by_pay.values],
        y_title="Revenue",
        colors=TABLEAU10[: len(by_pay)],
        height=360,
    )
    st.plotly_chart(fig_pay, use_container_width=True)
    charts_for_export.append(("Revenue by Payment Method (Top)", fig_pay, "Payment methods associated with revenue volume." ))

# Volatility by Channel (CV)
if channel_col and date_col and df["_Date"].notna().any():
    tmp = df.dropna(subset=["_Date"]).copy()
    tmp["__d"] = tmp["_Date"].dt.date
    daily_ch = tmp.groupby([channel_col, "__d"])["_Revenue"].sum()
    agg = daily_ch.groupby(level=0).agg(["mean", "std"])
    agg["cv"] = agg["std"] / agg["mean"].replace(0, np.nan)
    agg = agg.dropna(subset=["cv"]).sort_values("cv", ascending=False)
    if len(agg) > 0:
        x = [str(x) for x in agg.index.tolist()]
        y = [float(v) for v in agg["cv"].values]
        fig_cv = make_bar_categorical(
            "Volatility by Channel (higher = less predictable)",
            x_labels=x,
            y_values=y,
            y_title="CV (std / mean)",
            colors=TABLEAU10[: len(x)],
            height=360,
        )
        st.plotly_chart(fig_cv, use_container_width=True)
        charts_for_export.append(("Volatility by Channel", fig_cv, "Higher CV means revenue is less predictable within that channel." ))

# ----------------------------
# Advanced section
# ----------------------------
st.divider()
with st.expander("Advanced (optional)"):
    st.markdown("### Preview data (optional)")
    st.dataframe(df.head(30), use_container_width=True)

    st.markdown("### Data profile (optional)")
    prof = pd.DataFrame({
        "Column": df.columns,
        "Missing %": (df.isna().mean() * 100).round(1).values,
        "Example": [str(df[c].dropna().iloc[0]) if df[c].dropna().shape[0] else "" for c in df.columns],
    })
    st.dataframe(prof, use_container_width=True)

    st.markdown("### Correlation (optional)")
    num = df.select_dtypes(include=["number"]).copy()
    if num.shape[1] >= 2:
        corr = num.corr(numeric_only=True)
        # simple heatmap via go
        heat = go.Figure(data=go.Heatmap(z=corr.values, x=corr.columns, y=corr.index, colorscale="RdBu", zmid=0))
        heat.update_layout(template=PLOTLY_TEMPLATE, height=420, margin=dict(l=50, r=30, t=20, b=50))
        st.plotly_chart(heat, use_container_width=True)
    else:
        st.info("Not enough numeric fields to compute correlation.")

# ----------------------------
# Exports
# ----------------------------
st.divider()
st.subheader("Export Executive Brief")

st.markdown("""Export a short, shareable brief with commentary and selected charts.
- **PDF Executive Brief** (3–5 pages)
- **PPT Talking Deck** (16:9)
""")

colA, colB = st.columns(2)

with colA:
    if st.button("Generate PDF Executive Brief"):
        out = "ecai_executive_brief.pdf"
        try:
            build_pdf_executive_brief(
                out,
                business_summary=bullets[:10],
                business_insights=insights,
                chart_items=charts_for_export[:6],  # keep brief
            )
            with open(out, "rb") as f:
                st.download_button("Download PDF", f, file_name=out, mime="application/pdf")
        except Exception as e:
            st.error(f"PDF export failed: {e}")

with colB:
    if st.button("Generate PPT Talking Deck"):
        out = "ecai_talking_deck.pptx"
        try:
            # slides: title, commentary, fig
            slides = []
            slides.append(("Business Summary", "\n".join([f"• {b}" for b in bullets[:10]]), None))
            slides.append(("Business Insights", "\n".join([f"{k}:" + "\n" + "\n".join(["• " + x for x in v]) for k, v in insights.items()]), None))
            for t, fig, comm in charts_for_export[:6]:
                slides.append((t, comm, fig))
            build_ppt_talking_deck(out, slides)
            with open(out, "rb") as f:
                st.download_button("Download PPT", f, file_name=out, mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
        except Exception as e:
            st.error(f"PPT export failed: {e}")
