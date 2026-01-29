
# app.py
# EC-AI Insight — Sales / Retail Transactions MVP (Founder-first)
# Default: Business Summary → Business Insights → Core Visuals → Further Analysis → Advanced (collapsed) → Exports
#
# IMPORTANT (exports):
# - To include charts in PDF/PPT exports, add `kaleido` to requirements.txt (Plotly image renderer).

import io
from datetime import datetime
from typing import Optional, List, Tuple, Dict

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


# -----------------------------
# UI / Theme
# -----------------------------
BASE_FONT_PX = 19  # +1 size (executive readable)
TITLE_FONT_PX = 40
SUBTITLE_FONT_PX = 18

TABLEAU_COLORS = px.colors.qualitative.T10  # Tableau-like palette
PLOT_TEMPLATE = "plotly_white"

st.set_page_config(page_title="EC-AI Insight", layout="wide")

st.markdown(
    f"""
<style>
  html, body, [class*="css"] {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    font-size: {BASE_FONT_PX}px;
  }}
  .ec-subtitle {{
    font-size: {SUBTITLE_FONT_PX}px;
    color: #5a5a5a;
    margin-top: -6px;
    margin-bottom: 10px;
  }}
  .ec-hint {{
    font-size: {BASE_FONT_PX - 1}px;
    color: #6d6d6d;
  }}
  .ec-card {{
    background: #ffffff;
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    margin-top: 4px;
    margin-bottom: 8px;
  }}
  .ec-card h3 {{
    font-size: {BASE_FONT_PX + 6}px;
    margin: 0 0 8px 0;
  }}
  .ec-card p {{
    font-size: {BASE_FONT_PX + 1}px;
    line-height: 1.55;
    margin: 6px 0;
  }}
  .ec-sec {{
    font-size: {BASE_FONT_PX + 2}px;
    margin-top: 10px;
    margin-bottom: 6px;
  }}
  .ec-micro {{
    font-size: {BASE_FONT_PX}px;
    color: #666;
  }}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# Helpers
# -----------------------------
def kaleido_ok() -> bool:
    """Return True if Plotly image export is available."""
    try:
        import kaleido  # noqa: F401
        return True
    except Exception:
        return False


def style_fig(fig: go.Figure, *, height: Optional[int] = None, showlegend: Optional[bool] = None) -> go.Figure:
    """Apply a consistent Tableau-like theme."""
    fig.update_layout(
        template=PLOT_TEMPLATE,
        colorway=TABLEAU_COLORS,
        font=dict(size=BASE_FONT_PX + 1),
        margin=dict(l=20, r=20, t=45, b=30),
    )
    if height is not None:
        fig.update_layout(height=height)
    if showlegend is not None:
        fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="left", x=0))
        fig.update_layout(showlegend=showlegend)
    fig.update_xaxes(title_font=dict(size=BASE_FONT_PX + 1), tickfont=dict(size=BASE_FONT_PX))
    fig.update_yaxes(title_font=dict(size=BASE_FONT_PX + 1), tickfont=dict(size=BASE_FONT_PX))
    return fig


def human_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    x = float(x)
    absx = abs(x)
    if absx >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if absx >= 1_000:
        return f"${x/1_000:.1f}K"
    return f"${x:,.0f}"


def discount_band(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    # assume user may provide 0-1 or 0-100
    if s.max(skipna=True) is not None and s.max(skipna=True) > 1.5:
        s = s / 100.0
    bins = [-np.inf, 0.02, 0.05, 0.10, 0.15, 0.20, np.inf]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    return pd.cut(s, bins=bins, labels=labels)


def detect_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    # fuzzy contains
    lower_cols = [c.lower() for c in df.columns]
    for cand in candidates:
        for i, c in enumerate(lower_cols):
            if cand.lower() in c:
                return df.columns[i]
    return None


def fig_to_png_bytes(fig: go.Figure) -> Optional[bytes]:
    try:
        return fig.to_image(format="png", scale=2)  # requires kaleido
    except Exception:
        return None


def read_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded)
    raise ValueError("Unsupported file type. Please upload CSV or Excel.")


# -----------------------------
# Header
# -----------------------------
st.markdown(f"<div style='font-size:{TITLE_FONT_PX}px; font-weight:800;'>EC-AI Insight</div>", unsafe_allow_html=True)
st.markdown("<div class='ec-subtitle'>Sales performance, explained clearly.</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='ec-hint'>Upload your sales data and get a short business briefing — what’s working, what’s risky, and where to focus next.</div>",
    unsafe_allow_html=True,
)

st.divider()

uploaded = st.file_uploader("Upload a dataset (CSV / Excel)", type=["csv", "xlsx", "xls"])

if not uploaded:
    st.info("Upload a retail sales / transaction dataset to begin (Date, Store, Revenue).")
    st.stop()

try:
    df = read_file(uploaded)
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

# Basic cleanup
df = df.copy()
df.columns = [str(c).strip() for c in df.columns]

# Detect key columns (retail-first)
date_col = detect_col(df, ["date", "transaction_date", "order_date", "day"])
store_col = detect_col(df, ["store", "branch", "location", "shop"])
revenue_col = detect_col(df, ["revenue", "sales", "amount", "net_sales", "total"])
cogs_col = detect_col(df, ["cogs", "cost", "cost_of_goods", "costs"])
discount_col = detect_col(df, ["discount", "discount_rate", "disc", "markdown"])
category_col = detect_col(df, ["category", "product_category", "dept", "department"])
product_col = detect_col(df, ["product", "sku", "item", "product_name"])
channel_col = detect_col(df, ["channel", "sales_channel"])
payment_col = detect_col(df, ["payment", "payment_method", "tender"])

# Hard gate: retail-sales MVP needs Revenue + Date
if revenue_col is None:
    st.error("Could not find a Revenue/Sales column. Please include a column named like 'Revenue' or 'Sales'.")
    st.stop()

df[revenue_col] = pd.to_numeric(df[revenue_col], errors="coerce")

if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
else:
    st.warning("No Date column detected. Trend charts will be limited.")

# Basic derived metrics
if cogs_col:
    df[cogs_col] = pd.to_numeric(df[cogs_col], errors="coerce")
    df["_gross_profit"] = df[revenue_col] - df[cogs_col]
    df["_gross_margin"] = np.where(df[revenue_col].fillna(0) != 0, df["_gross_profit"] / df[revenue_col], np.nan)

# -----------------------------
# Business Summary (data-backed, founder language)
# -----------------------------
total_rev = float(df[revenue_col].sum(skipna=True))
n_rows = int(len(df))
period_txt = ""
if date_col and df[date_col].notna().any():
    dmin = df[date_col].min()
    dmax = df[date_col].max()
    if pd.notna(dmin) and pd.notna(dmax):
        period_txt = f"{dmin.date()} to {dmax.date()}"

top_store_name = None
top2_share = None
store_rank = None
if store_col:
    store_rank = df.groupby(store_col)[revenue_col].sum().sort_values(ascending=False)
    if len(store_rank) >= 1:
        top_store_name = str(store_rank.index[0])
    if len(store_rank) >= 2 and store_rank.sum() != 0:
        top2_share = float((store_rank.iloc[0] + store_rank.iloc[1]) / store_rank.sum())

# Growth trend (first vs last day)
growth_txt = None
if date_col and df[date_col].notna().any():
    daily = df.dropna(subset=[date_col]).groupby(pd.Grouper(key=date_col, freq="D"))[revenue_col].sum().dropna()
    if len(daily) >= 2:
        start_v = float(daily.iloc[0])
        end_v = float(daily.iloc[-1])
        if start_v != 0:
            pct = (end_v - start_v) / abs(start_v) * 100
            growth_txt = f"Overall sales increased from {human_money(start_v)} to {human_money(end_v)} (approx. {pct:.1f}%)."

# Volatility by store
vol_txt = None
most_volatile_store = None
if date_col and store_col and df[date_col].notna().any():
    daily_store = df.dropna(subset=[date_col]).groupby([pd.Grouper(key=date_col, freq="D"), store_col])[revenue_col].sum().reset_index()
    tmp = daily_store.groupby(store_col)[revenue_col].agg(["mean", "std"]).reset_index()
    tmp["cv"] = tmp["std"] / tmp["mean"].replace(0, np.nan)
    tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["cv"])
    if not tmp.empty:
        row = tmp.sort_values("cv", ascending=False).iloc[0]
        most_volatile_store = str(row[store_col])
        vol_txt = f"Some stores are highly volatile (e.g., **{most_volatile_store}** shows large day‑to‑day swings; volatility score ≈ {row['cv']:.2f})."

# Discount effectiveness cue
disc_txt = None
best_band = None
worst_band = None
if discount_col:
    bands = discount_band(df[discount_col])
    tmp = df.copy()
    tmp["_disc_band"] = bands
    agg = tmp.groupby("_disc_band")[revenue_col].mean().dropna()
    if len(agg) >= 2:
        best_band = str(agg.sort_values(ascending=False).index[0])
        worst_band = str(agg.sort_values(ascending=True).index[0])
        disc_txt = f"Discounts around **{best_band}** align with higher average revenue per sale, while deeper discounts (e.g., **{worst_band}**) appear less efficient."

# Summary bullets
summary_lines: List[str] = []
if top_store_name and top2_share is not None:
    summary_lines.append(
        f"Revenue is concentrated in a small number of stores, led by **{store_rank.index[0]}** and **{store_rank.index[1]}** (top two contribute ~{top2_share*100:.0f}% of total)."
    )
elif top_store_name:
    summary_lines.append(f"Your top store by revenue is **{top_store_name}**.")

if growth_txt:
    summary_lines.append(growth_txt)
if vol_txt:
    summary_lines.append(vol_txt)
if disc_txt:
    summary_lines.append(disc_txt)

summary_lines.append("The biggest opportunity is to **stabilise and scale what already works** in top-performing stores before expanding promotions.")

summary_html = "<div class='ec-card'><h3>Business Summary</h3>" + "".join([f"<p>• {x}</p>" for x in summary_lines]) + \
    "<p class='ec-hint'>Start here. This section explains the story before you look at any charts.</p></div>"
st.markdown(summary_html, unsafe_allow_html=True)

# -----------------------------
# Business Insights (actionable)
# -----------------------------
st.divider()

# Build a few data-backed insight lines
ins_money: List[str] = []
ins_risk: List[str] = []
ins_improve: List[str] = []
ins_focus: List[str] = []

if store_rank is not None and len(store_rank) >= 1:
    ins_money.append(f"**{store_rank.index[0]}** is the largest contributor ({human_money(store_rank.iloc[0])}).")
    if len(store_rank) >= 5:
        ins_money.append("A small group of stores accounts for a disproportionate share of revenue (winner‑takes‑more pattern).")

if category_col:
    cat_rank = df.groupby(category_col)[revenue_col].sum().sort_values(ascending=False)
    if len(cat_rank) >= 1:
        ins_money.append(f"Top category by revenue is **{cat_rank.index[0]}** ({human_money(cat_rank.iloc[0])}).")

if most_volatile_store:
    ins_risk.append(f"Performance is uneven — **{most_volatile_store}** shows the largest variability, which makes forecasting harder.")

if top2_share is not None and top2_share >= 0.45:
    ins_risk.append("Revenue concentration is high — losing performance in the top stores materially impacts total results.")

if best_band and worst_band:
    ins_improve.append(f"Discounting beyond **{worst_band}** may reduce revenue efficiency; treat deep discounts as experiments with clear targets.")
    ins_improve.append(f"Use **revenue per sale** as a guardrail metric when testing promotions (not only volume).")

if cogs_col and df["_gross_margin"].notna().any():
    gm = float(df["_gross_margin"].mean(skipna=True))
    ins_improve.append(f"Average gross margin is approximately **{gm*100:.1f}%** (directional). Consider reviewing margin by store/category.")

ins_focus.extend([
    "Strengthen execution in top stores (inventory availability, staffing, promotion discipline).",
    "Reduce volatility first — inconsistent performance is often operational.",
    "Test promotions with clear targets; stop what doesn’t improve revenue per sale."
])

ins_html = "<div class='ec-card'><h3>Business Insights</h3>"
ins_html += "<p class='ec-sec'><b>Where the money is made</b></p>" + "".join([f"<p>• {x}</p>" for x in (ins_money[:3] or ["Identify your top stores/categories and protect them."])])
ins_html += "<p class='ec-sec'><b>Where risk exists</b></p>" + "".join([f"<p>• {x}</p>" for x in (ins_risk[:2] or ["Results vary materially across stores; investigate execution differences."])])
ins_html += "<p class='ec-sec'><b>What can be improved</b></p>" + "".join([f"<p>• {x}</p>" for x in (ins_improve[:3] or ["Review discount strategy and ensure promotions improve revenue per sale."])])
ins_html += "<p class='ec-sec'><b>What to focus on next</b></p>" + "".join([f"<p>• {x}</p>" for x in ins_focus[:3]])
ins_html += "</div>"
st.markdown(ins_html, unsafe_allow_html=True)

# -----------------------------
# Core visuals (DEFAULT)
# -----------------------------
st.divider()
st.subheader("Revenue Overview")

charts_for_export: List[Tuple[str, Optional[bytes]]] = []

# Revenue trend
trend_fig = None
if date_col and df[date_col].notna().any():
    daily = df.dropna(subset=[date_col]).groupby(pd.Grouper(key=date_col, freq="D"))[revenue_col].sum(min_count=1).dropna().reset_index()
    trend_fig = px.line(daily, x=date_col, y=revenue_col, markers=True, title="")
    trend_fig.update_traces(line=dict(width=3))
    trend_fig.update_yaxes(tickprefix="$", separatethousands=True)
    trend_fig.update_layout(xaxis_title="Date", yaxis_title="Revenue")
    style_fig(trend_fig, height=380, showlegend=False)
    st.plotly_chart(trend_fig, use_container_width=True)
    charts_for_export.append(("Revenue Trend", fig_to_png_bytes(trend_fig)))
else:
    st.info("Revenue trend requires a Date column.")

# Top stores by revenue
st.subheader("Top Revenue-Generating Stores")
top_store_fig = None
if store_col:
    by_store = df.groupby(store_col)[revenue_col].sum().sort_values(ascending=True).tail(10)
    plot_df = by_store.reset_index()
    plot_df["Label"] = plot_df[revenue_col].apply(human_money)
    top_store_fig = px.bar(
        plot_df,
        x=revenue_col,
        y=store_col,
        orientation="h",
        text="Label",
        color=store_col,
        color_discrete_sequence=TABLEAU_COLORS,
        title="",
    )
    top_store_fig.update_traces(textposition="outside", cliponaxis=False)
    top_store_fig.update_layout(xaxis_title="Revenue", yaxis_title="Store")
    style_fig(top_store_fig, height=420, showlegend=False)
    st.plotly_chart(top_store_fig, use_container_width=True)
    charts_for_export.append(("Top Stores by Revenue", fig_to_png_bytes(top_store_fig)))
else:
    st.info("Top stores view requires a Store column.")

# Store stability small multiples
st.subheader("Store Stability (Top 5)")
if date_col and store_col and df[date_col].notna().any():
    daily_store = df.dropna(subset=[date_col]).groupby([pd.Grouper(key=date_col, freq="D"), store_col])[revenue_col].sum(min_count=1).reset_index()
    top_stores = []
    if store_rank is not None:
        top_stores = [str(x) for x in store_rank.index[:5]]
    cols = st.columns(2)
    mini = []
    for i, sname in enumerate(top_stores):
        d = daily_store[daily_store[store_col] == sname]
        fig = px.line(d, x=date_col, y=revenue_col, markers=True, title=str(sname))
        fig.update_traces(line=dict(width=3))
        fig.update_yaxes(tickprefix="$", separatethousands=True)
        fig.update_layout(xaxis_title="", yaxis_title="")
        style_fig(fig, height=260, showlegend=False)
        with cols[i % 2]:
            st.plotly_chart(fig, use_container_width=True)
        mini.append((f"Store Trend — {sname}", fig_to_png_bytes(fig)))
    # keep 2 representative store charts in PDF
    charts_for_export.extend(mini[:2])
else:
    st.info("Store stability view requires both Date and Store columns.")

# Pricing effectiveness
st.subheader("Pricing Effectiveness")
disc_fig = None
if discount_col:
    tmp = df.copy()
    tmp["_disc_band"] = discount_band(tmp[discount_col])
    band = tmp.groupby("_disc_band")[revenue_col].mean().reset_index().dropna(subset=["_disc_band", revenue_col])
    if not band.empty:
        band["Label"] = band[revenue_col].apply(human_money)
        disc_fig = px.bar(
            band,
            x="_disc_band",
            y=revenue_col,
            text="Label",
            color="_disc_band",
            color_discrete_sequence=TABLEAU_COLORS,
            title="",
        )
        disc_fig.update_traces(textposition="outside", cliponaxis=False)
        disc_fig.update_layout(xaxis_title="Discount band", yaxis_title="Average revenue per sale")
        style_fig(disc_fig, height=380, showlegend=False)
        st.plotly_chart(disc_fig, use_container_width=True)
        charts_for_export.append(("Average Revenue per Sale by Discount Band", fig_to_png_bytes(disc_fig)))
else:
    st.info("Discount chart requires a Discount / Discount_Rate column.")

# -----------------------------
# Further analysis (bring back 3 extra charts)
# -----------------------------
st.divider()
with st.expander("Further Analysis (recommended)", expanded=True):
    st.markdown("<div class='ec-micro'>Extra cuts that many owners find useful (optional, but easy to read).</div>", unsafe_allow_html=True)

    # 1) Revenue mix by Category
    if category_col:
        cat = df.groupby(category_col)[revenue_col].sum().sort_values(ascending=False).head(8).reset_index()
        cat["Label"] = cat[revenue_col].apply(human_money)
        fig1 = px.bar(cat, x=revenue_col, y=category_col, orientation="h", text="Label", color=category_col, color_discrete_sequence=TABLEAU_COLORS)
        fig1.update_traces(textposition="outside", cliponaxis=False)
        fig1.update_layout(xaxis_title="Revenue", yaxis_title="Category", title="Revenue by Category (Top)")
        style_fig(fig1, height=420, showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Add a Category column to see revenue mix by category.")

    # 2) Revenue mix by Payment Method
    if payment_col:
        pay = df.groupby(payment_col)[revenue_col].sum().sort_values(ascending=False).head(8).reset_index()
        pay["Label"] = pay[revenue_col].apply(human_money)
        fig2 = px.bar(pay, x=revenue_col, y=payment_col, orientation="h", text="Label", color=payment_col, color_discrete_sequence=TABLEAU_COLORS)
        fig2.update_traces(textposition="outside", cliponaxis=False)
        fig2.update_layout(xaxis_title="Revenue", yaxis_title="Payment method", title="Revenue by Payment Method (Top)")
        style_fig(fig2, height=420, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Add a Payment_Method column to see revenue mix by payment method.")

    # 3) Volatility by Channel
    if date_col and channel_col and df[date_col].notna().any():
        daily_channel = df.dropna(subset=[date_col]).groupby([pd.Grouper(key=date_col, freq="D"), channel_col])[revenue_col].sum(min_count=1).reset_index()
        tmp = daily_channel.groupby(channel_col)[revenue_col].agg(["mean", "std"]).reset_index()
        tmp["cv"] = tmp["std"] / tmp["mean"].replace(0, np.nan)
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["cv"]).sort_values("cv", ascending=False)
        if not tmp.empty:
            tmp["Label"] = tmp["cv"].apply(lambda v: f"{v:.2f}")
            fig3 = px.bar(tmp, x=channel_col, y="cv", text="Label", color=channel_col, color_discrete_sequence=TABLEAU_COLORS, title="Volatility by Channel (higher = less stable)")
            fig3.update_traces(textposition="outside", cliponaxis=False)
            fig3.update_layout(xaxis_title="Channel", yaxis_title="Volatility score (CV)")
            style_fig(fig3, height=380, showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Not enough signal to compute channel volatility.")
    else:
        st.info("Add Channel + Date columns to compute volatility by channel.")

# -----------------------------
# Advanced analysis (collapsed)
# -----------------------------
st.divider()
with st.expander("Advanced analysis (optional)", expanded=False):
    st.markdown("### Raw data preview")
    st.dataframe(df.head(50), use_container_width=True)

    st.markdown("### Data quality & assumptions")
    miss = df.isna().mean().sort_values(ascending=False)
    prof = pd.DataFrame({"missing_%": (miss * 100).round(1)})
    st.dataframe(prof, use_container_width=True)

    if date_col and df[date_col].notna().any():
        st.markdown("### Correlation (numeric fields)")
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(num_cols) >= 2:
            corr = df[num_cols].corr(numeric_only=True)
            heat = px.imshow(corr, text_auto=".2f", aspect="auto", title="Correlation heatmap")
            style_fig(heat, height=520, showlegend=False)
            st.plotly_chart(heat, use_container_width=True)
        else:
            st.info("Not enough numeric columns for correlation.")

# -----------------------------
# Exports (Executive Brief only)
# -----------------------------
st.divider()
st.subheader("Export Executive Brief")

if not kaleido_ok():
    st.warning("Chart export is not enabled (kaleido is missing). Add **kaleido** to requirements.txt to include charts in PDF/PPT exports.")

def build_pdf(title: str, summary: List[str], insights: Dict[str, List[str]], charts: List[Tuple[str, Optional[bytes]]]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    def draw_title():
        c.setFont("Helvetica-Bold", 18)
        c.drawString(0.8 * inch, h - 0.8 * inch, title)
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawString(0.8 * inch, h - 1.05 * inch, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.setFillColorRGB(0, 0, 0)

    draw_title()
    y = h - 1.4 * inch

    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.8 * inch, y, "Business Summary")
    y -= 0.25 * inch
    c.setFont("Helvetica", 11)
    for line in summary[:6]:
        c.drawString(0.95 * inch, y, f"• {line.replace('**','')}")
        y -= 0.22 * inch
        if y < 1.2 * inch:
            c.showPage()
            draw_title()
            y = h - 1.4 * inch

    y -= 0.15 * inch
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.8 * inch, y, "Business Insights")
    y -= 0.25 * inch
    c.setFont("Helvetica", 11)

    for sec, lines in insights.items():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.95 * inch, y, sec)
        y -= 0.20 * inch
        c.setFont("Helvetica", 11)
        for ln in lines[:3]:
            c.drawString(1.10 * inch, y, f"• {ln.replace('**','')}")
            y -= 0.20 * inch
            if y < 1.2 * inch:
                c.showPage()
                draw_title()
                y = h - 1.4 * inch
        y -= 0.08 * inch

    # Charts (selected)
    for chart_title, png in charts:
        if png is None:
            continue
        c.showPage()
        draw_title()
        c.setFont("Helvetica-Bold", 13)
        c.drawString(0.8 * inch, h - 1.4 * inch, chart_title)
        img = ImageReader(io.BytesIO(png))
        c.drawImage(img, 0.8 * inch, 1.2 * inch, width=w - 1.6 * inch, height=h - 2.8 * inch, preserveAspectRatio=True, anchor="c")

    c.save()
    buf.seek(0)
    return buf.read()


def build_ppt(title: str, summary: List[str], insights: Dict[str, List[str]], charts: List[Tuple[str, Optional[bytes]]]) -> bytes:
    prs = Presentation()

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = "Sales performance briefing (executive-ready)"

    # Summary slide
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Business Summary"
    tf = slide.shapes.placeholders[1].text_frame
    tf.clear()
    for i, line in enumerate(summary[:6]):
        p = tf.add_paragraph() if i else tf.paragraphs[0]
        p.text = line.replace("**", "")
        p.level = 0

    # Insights slide
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Business Insights"
    tf = slide.shapes.placeholders[1].text_frame
    tf.clear()
    for sec, lines in insights.items():
        p = tf.add_paragraph() if len(tf.paragraphs) else tf.paragraphs[0]
        p.text = sec
        p.level = 0
        for ln in lines[:2]:
            p2 = tf.add_paragraph()
            p2.text = ln.replace("**", "")
            p2.level = 1

    # Chart slides
    for chart_title, png in charts:
        if png is None:
            continue
        slide = prs.slides.add_slide(prs.slide_layouts[5])  # blank
        tx = slide.shapes.add_textbox(Inches(0.6), Inches(0.3), Inches(12.2), Inches(0.6))
        run = tx.text_frame.paragraphs[0].add_run()
        run.text = chart_title
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = RGBColor(20, 20, 20)

        img_stream = io.BytesIO(png)
        slide.shapes.add_picture(img_stream, Inches(0.6), Inches(1.1), width=Inches(12.2))

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()


insights_dict = {
    "Where the money is made": ins_money[:3] or ["Protect and replicate what works in your top stores/categories."],
    "Where risk exists": ins_risk[:2] or ["Investigate inconsistent performance drivers across stores/channels."],
    "What can be improved": ins_improve[:3] or ["Review discount strategy and margin guardrails."],
    "What to focus on next": ins_focus[:3],
}

colA, colB = st.columns(2)

with colA:
    if st.button("Generate PDF Executive Brief"):
        pdf_bytes = build_pdf(
            "EC-AI Executive Brief",
            summary_lines,
            insights_dict,
            charts_for_export,
        )
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name="ecai_executive_brief.pdf",
            mime="application/pdf",
        )

with colB:
    if st.button("Generate PPT Talking Deck"):
        ppt_bytes = build_ppt(
            "EC-AI Executive Brief",
            summary_lines,
            insights_dict,
            charts_for_export,
        )
        st.download_button(
            "Download PPTX",
            data=ppt_bytes,
            file_name="ecai_talking_deck.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
