# app.py
# EC-AI Insight (Sales-only MVP)
# Upload retail sales / transaction data (CSV/XLSX) → Executive Summary + owner-first charts + export (PDF/PPTX)
#
# Sales-only scope (for MVP):
# - Designed for retail sales / transaction datasets (Date, Store, Channel, Category, Revenue, etc.)
# - Charts are ordered for business owners: Revenue Trend → Top Drivers → Concentration → Simple Relationships
#
# Notes:
# - This version removes "feature soup" and focuses on a confident demo flow.
# - Optional OpenAI integration has been intentionally disabled by default (keeps GitHub deploy simple).
#
# Recommended requirements additions:
# - kaleido (for exporting Plotly charts to PNG inside PDF/PPTX)

import io
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Exports
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="EC-AI Insight (Sales-only MVP)",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.1rem; padding-bottom: 2.3rem; }
      h1, h2, h3 { letter-spacing: -0.3px; }
      .stDownloadButton button { border-radius: 10px; }
      .stAlert { border-radius: 12px; }

      /* KPI cards */
      div[data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid rgba(49,51,63,0.08);
        padding: 14px 14px 12px 14px;
        border-radius: 14px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.04);
      }

      /* Executive Summary box */
      .ecai-summary {
        background: #ffffff;
        border: 1px solid rgba(49,51,63,0.08);
        border-radius: 16px;
        padding: 14px 16px 14px 16px;
        box-shadow: 0 1px 8px rgba(0,0,0,0.04);
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
      }
      .ecai-summary p { margin: 0.15rem 0; line-height: 1.4; }
      .ecai-muted { color: rgba(49,51,63,0.7); font-size: 0.95rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Global Plotly defaults
# -----------------------------
TABLEAU_T10 = px.colors.qualitative.T10
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = TABLEAU_T10


# -----------------------------
# Helpers
# -----------------------------
def human_money(x: float, currency="$") -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    sign = "-" if x < 0 else ""
    x = abs(float(x))
    if x >= 1e9:
        return f"{sign}{currency}{x/1e9:.2f}B"
    if x >= 1e6:
        return f"{sign}{currency}{x/1e6:.2f}M"
    if x >= 1e3:
        return f"{sign}{currency}{x/1e3:.2f}K"
    return f"{sign}{currency}{x:.2f}"


def human_num(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    x = float(x)
    if abs(x) >= 1e9:
        return f"{x/1e9:.2f}B"
    if abs(x) >= 1e6:
        return f"{x/1e6:.2f}M"
    if abs(x) >= 1e3:
        return f"{x/1e3:.2f}K"
    return f"{x:.2f}"


def safe_to_datetime(s: pd.Series) -> Optional[pd.Series]:
    try:
        dt = pd.to_datetime(s, errors="coerce", utc=False)
        if dt.notna().mean() >= 0.6:
            return dt
    except Exception:
        return None
    return None


def guess_date_col(df: pd.DataFrame) -> Optional[str]:
    # Prefer columns named like Date / OrderDate / TransactionDate
    candidates = [c for c in df.columns if re.search(r"(date|dt|time|month|day)", str(c), re.I)]
    for c in candidates:
        dt = safe_to_datetime(df[c])
        if dt is not None:
            return c
    # fallback: try object cols
    for c in df.columns:
        if df[c].dtype == "object":
            dt = safe_to_datetime(df[c])
            if dt is not None:
                return c
    return None


def is_numeric_series(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s)


def is_categorical_series(s: pd.Series) -> bool:
    if pd.api.types.is_bool_dtype(s):
        return True
    if pd.api.types.is_object_dtype(s):
        return True
    if pd.api.types.is_categorical_dtype(s):
        return True
    return False


def pick_revenue_like(df: pd.DataFrame) -> Optional[str]:
    patterns = [
        r"\brevenue\b", r"\bsales\b", r"\bturnover\b", r"\bgmv\b",
        r"\bnet[_ ]?sales\b", r"\bamount\b", r"\bvalue\b"
    ]
    scored = []
    for c in df.columns:
        if not is_numeric_series(df[c]):
            continue
        name = str(c).lower()
        score = 0
        for p in patterns:
            if re.search(p, name):
                score += 3
        if score > 0:
            scored.append((score, c))
    if not scored:
        return None
    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[0][1]


def pick_cost_like(df: pd.DataFrame) -> Optional[str]:
    pats = [r"\bcogs\b", r"\bcost\b", r"\bexpense\b"]
    for c in df.columns:
        if is_numeric_series(df[c]) and any(re.search(p, str(c), re.I) for p in pats):
            return c
    return None


def pick_dim_like(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    for c in df.columns:
        if not is_categorical_series(df[c]):
            continue
        name = str(c).lower()
        if any(k in name for k in keywords):
            return c
    return None


def stable_color_map(categories: List[str], palette: List[str] = None) -> Dict[str, str]:
    palette = palette or TABLEAU_T10
    cats = [str(c) for c in categories]
    return {c: palette[i % len(palette)] for i, c in enumerate(cats)}


def apply_chart_style(fig: go.Figure, height: Optional[int] = None, showlegend: Optional[bool] = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        colorway=TABLEAU_T10,
        margin=dict(l=10, r=10, t=60, b=10),
        font=dict(size=12),
    )
    if height is not None:
        fig.update_layout(height=height)
    if showlegend is not None:
        fig.update_layout(showlegend=showlegend)
    return fig


def fix_label_overlap_for_bar(fig: go.Figure) -> go.Figure:
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="hide")
    fig.update_xaxes(tickangle=-20, automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def fig_to_png_bytes(fig: go.Figure) -> Optional[bytes]:
    try:
        return fig.to_image(format="png", scale=2)
    except Exception:
        return None


def fit_font_size(text: str, max_chars: int, base: int = 24, min_size: int = 12) -> int:
    if not text:
        return base
    ratio = len(text) / max(1, max_chars)
    if ratio <= 1:
        return base
    size = int(base / ratio)
    return max(min_size, min(base, size))


def add_bullets_to_slide(slide, title: str, bullets: List[str]):
    left = Inches(0.6)
    top = Inches(0.5)
    width = Inches(12.0)
    height = Inches(6.5)

    title_shape = slide.shapes.add_textbox(left, top, width, Inches(0.6))
    tf = title_shape.text_frame
    tf.text = title
    tf.paragraphs[0].font.size = Pt(32)
    tf.paragraphs[0].font.bold = True

    body = slide.shapes.add_textbox(left, Inches(1.2), width, height)
    tfb = body.text_frame
    tfb.word_wrap = True
    tfb.clear()

    joined = "\n".join(bullets)
    fs = fit_font_size(joined, max_chars=900, base=18, min_size=12)

    for i, b in enumerate(bullets):
        p = tfb.paragraphs[0] if i == 0 else tfb.add_paragraph()
        p.text = b
        p.level = 0
        p.font.size = Pt(fs)
        p.space_after = Pt(6)


def add_image_slide(prs, title: str, image_bytes: bytes, caption: Optional[str] = None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    tbox = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12.0), Inches(0.6))
    tf = tbox.text_frame
    tf.text = title
    tf.paragraphs[0].font.size = Pt(26)
    tf.paragraphs[0].font.bold = True

    stream = io.BytesIO(image_bytes)
    slide.shapes.add_picture(stream, Inches(0.6), Inches(1.2), width=Inches(12.0))

    if caption:
        cbox = slide.shapes.add_textbox(Inches(0.6), Inches(7.0), Inches(12.0), Inches(0.4))
        ctf = cbox.text_frame
        ctf.text = caption
        ctf.paragraphs[0].font.size = Pt(14)
        ctf.paragraphs[0].font.color.rgb = RGBColor(80, 80, 80)


# -----------------------------
# Exports
# -----------------------------
def build_pdf(exec_lines: List[str], insight_lines: List[str],
              charts: List[Tuple[str, Optional[bytes]]]) -> bytes:
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=letter)
    W, H = letter

    def wrap_text(text, width_chars):
        words = text.split()
        out, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 <= width_chars:
                cur = (cur + " " + w).strip()
            else:
                out.append(cur)
                cur = w
        if cur:
            out.append(cur)
        return out

    def write_title(text, y):
        c.setFont("Helvetica-Bold", 18)
        c.drawString(0.8 * inch, y, text)
        return y - 0.35 * inch

    def write_lines(lines, y, font_size=11, max_lines=38):
        c.setFont("Helvetica", font_size)
        lines_used = 0
        for b in lines:
            wrapped = wrap_text(f"• {b}", 95)
            for w in wrapped:
                if lines_used >= max_lines:
                    return y, True
                c.drawString(0.85 * inch, y, w)
                y -= 0.22 * inch
                lines_used += 1
        return y, False

    y = H - 0.9 * inch
    y = write_title("EC-AI Insight — Executive Brief (Sales-only MVP)", y)
    c.setFont("Helvetica", 11)
    c.drawString(0.8 * inch, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 0.35 * inch

    y = write_title("Executive Summary", y)
    y, overflow = write_lines(exec_lines, y)
    if overflow:
        c.showPage()
        y = H - 0.9 * inch

    y -= 0.2 * inch
    y = write_title("Key Insights", y)
    y, overflow = write_lines(insight_lines, y)
    if overflow:
        c.showPage()
        y = H - 0.9 * inch

    for title, img in charts:
        if img is None:
            continue
        c.showPage()
        y = H - 0.9 * inch
        y = write_title(title, y)
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(io.BytesIO(img))
        img_w = W - 1.6 * inch
        c.drawImage(ir, 0.8 * inch, 1.2 * inch, width=img_w, height=4.8 * inch, preserveAspectRatio=True, anchor="n")

    c.save()
    buff.seek(0)
    return buff.getvalue()


def build_pptx(exec_lines: List[str], insight_lines: List[str],
               charts: List[Tuple[str, Optional[bytes]]]) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    tbox = slide.shapes.add_textbox(Inches(0.8), Inches(1.0), Inches(12.0), Inches(1.2))
    tf = tbox.text_frame
    tf.text = "EC-AI Insight — Executive Brief"
    tf.paragraphs[0].font.size = Pt(42)
    tf.paragraphs[0].font.bold = True

    sbox = slide.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(12.0), Inches(0.8))
    stf = sbox.text_frame
    stf.text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    stf.paragraphs[0].font.size = Pt(18)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bullets_to_slide(slide, "Executive Summary", exec_lines)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bullets_to_slide(slide, "Key Insights", insight_lines)

    for title, img in charts:
        if img:
            add_image_slide(prs, title, img)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.getvalue()


# -----------------------------
# UI
# -----------------------------
st.title("EC-AI Insight (Sales-only MVP)")
st.caption("Upload retail sales / transaction data → get a CEO-friendly summary and a few high-impact charts. No feature soup.")

uploaded = st.file_uploader("Upload sales data (CSV / Excel)", type=["csv", "xlsx", "xls"])
if uploaded is None:
    st.info("Upload a CSV/XLSX to begin. (Tip: start with retail sales / transaction data.)")
    st.stop()


def load_data(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)


try:
    df_raw = load_data(uploaded)
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

if df_raw is None or df_raw.empty:
    st.warning("Dataset is empty.")
    st.stop()

df = df_raw.copy()
df.columns = [str(c).strip() for c in df.columns]

# Detect core fields for sales MVP
date_col = guess_date_col(df)
if date_col:
    dt = safe_to_datetime(df[date_col])
    if dt is not None:
        df[date_col] = dt.dt.tz_localize(None)

numeric_cols = [c for c in df.columns if is_numeric_series(df[c])]
revenue_col = pick_revenue_like(df) or (numeric_cols[0] if numeric_cols else None)
cost_col = pick_cost_like(df)

dims = {
    "store": pick_dim_like(df, ["store", "branch", "location", "outlet"]),
    "channel": pick_dim_like(df, ["channel", "source"]),
    "category": pick_dim_like(df, ["category", "product", "sku", "segment"]),
    "payment": pick_dim_like(df, ["payment", "pay", "method", "card"]),
}

# Fallback for common retail field names
for k, candidates in {
    "store": ["Store", "STORE", "Branch"],
    "channel": ["Channel", "CHANNEL"],
    "category": ["Category", "Product", "SKU"],
    "payment": ["Payment_Method", "PaymentMethod"],
}.items():
    if dims.get(k) is None:
        for c in candidates:
            if c in df.columns:
                dims[k] = c
                break

if revenue_col is None:
    st.error("No numeric 'Revenue/Sales' column detected. For the sales-only MVP, please include a Revenue/Sales field.")
    with st.expander("Show detected columns"):
        st.write(list(df.columns))
    st.stop()

# -----------------------------
# Executive Summary (Owner-first)
# -----------------------------
srev = pd.to_numeric(df[revenue_col], errors="coerce")
total_rev = float(srev.sum(skipna=True))
avg_rev = float(srev.mean(skipna=True))
med_rev = float(srev.median(skipna=True))
rows = int(df.shape[0])

date_min = date_max = None
if date_col:
    dts = pd.to_datetime(df[date_col], errors="coerce")
    if dts.notna().sum() > 0:
        date_min = dts.min().date()
        date_max = dts.max().date()

def top_driver(dim: Optional[str]) -> Optional[Tuple[str, float]]:
    if not dim or dim not in df.columns:
        return None
    g = df.groupby(dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False)
    if len(g) == 0:
        return None
    return str(g.index[0]), float(g.iloc[0])

top_store = top_driver(dims.get("store"))
top_cat = top_driver(dims.get("category"))
top_channel = top_driver(dims.get("channel"))

# KPI row
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", human_money(total_rev))
k2.metric("Avg / Record", human_money(avg_rev))
k3.metric("Median / Record", human_money(med_rev))
k4.metric("Rows", f"{rows:,}")

# Executive Summary box (short, readable)
summary_lines: List[str] = []
if date_min and date_max:
    summary_lines.append(f"This dataset covers **{date_min} → {date_max}** with **{rows:,}** transactions.")
else:
    summary_lines.append(f"This dataset contains **{rows:,}** transactions/records.")
summary_lines.append(f"Total **{revenue_col}** is **{human_money(total_rev)}** (avg **{human_money(avg_rev)}** per record).")

drivers = []
if top_store:
    drivers.append(f"Store: **{top_store[0]}** ({human_money(top_store[1])})")
if top_cat:
    drivers.append(f"Category: **{top_cat[0]}** ({human_money(top_cat[1])})")
if top_channel:
    drivers.append(f"Channel: **{top_channel[0]}** ({human_money(top_channel[1])})")
if drivers:
    summary_lines.append("Top drivers: " + " • ".join(drivers) + ".")
summary_lines.append("Below, the charts are ordered to answer owner questions: **Are we growing? What drives revenue? Are we over‑dependent on a few items? What factors appear linked to revenue?**")

st.markdown('<div class="ecai-summary">', unsafe_allow_html=True)
for i, line in enumerate(summary_lines):
    # Keep paragraphs short
    st.markdown(f"<p>{line}</p>", unsafe_allow_html=True)
st.markdown('<p class="ecai-muted">Sales-only MVP: keep it simple, credible, and demo-ready.</p>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Collect charts for export
charts_for_export: List[Tuple[str, Optional[bytes]]] = []

st.divider()

# -----------------------------
# Charts (Owner-first order)
# -----------------------------
st.header("Owner-first dashboard")

# 1) Revenue trend (Total)
if date_col:
    tmp = df[[date_col, revenue_col]].copy()
    tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
    ts_total = tmp.groupby(date_col)[revenue_col].sum().sort_index()

    fig_trend = px.line(
        ts_total.reset_index(),
        x=date_col,
        y=revenue_col,
        markers=True,
        title=f"1) Total {revenue_col} over time",
    )
    fig_trend = apply_chart_style(fig_trend, height=380, showlegend=False)
    fig_trend.update_xaxes(automargin=True)
    fig_trend.update_yaxes(automargin=True)
    st.plotly_chart(fig_trend, use_container_width=True, key="chart_trend_total")
    charts_for_export.append((f"Total {revenue_col} over time", fig_to_png_bytes(fig_trend)))
else:
    st.info("No date column detected — trend chart is skipped. (Include a Date field for the best demo.)")

# 2–4) Top drivers (Store / Category / Channel) — simple bars
c1, c2, c3 = st.columns(3)

def bar_top5(dim: Optional[str], title: str, key: str):
    if not dim or dim not in df.columns:
        return None
    g = df.groupby(dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(5)
    if len(g) == 0:
        return None
    color_map = stable_color_map([str(x) for x in g.index.tolist()])
    fig = px.bar(
        g.reset_index(),
        x=dim,
        y=revenue_col,
        color=dim,
        color_discrete_map=color_map,
        title=title,
    )
    fig.update_traces(text=[human_money(v) for v in g.values])
    fig = apply_chart_style(fig, height=340, showlegend=False)
    fig = fix_label_overlap_for_bar(fig)
    st.plotly_chart(fig, use_container_width=True, key=key)
    charts_for_export.append((title, fig_to_png_bytes(fig)))
    return fig

with c1:
    bar_top5(dims.get("store"), f"2) {revenue_col} by Store (Top 5)", "chart_store_top5")
with c2:
    bar_top5(dims.get("category"), f"3) {revenue_col} by Category (Top 5)", "chart_category_top5")
with c3:
    bar_top5(dims.get("channel"), f"4) {revenue_col} by Channel (Top 5)", "chart_channel_top5")

# 5) Concentration / Pareto (over-dependence check)
st.subheader("5) Revenue concentration (Pareto)")

pareto_dim = dims.get("category") or dims.get("store") or dims.get("channel")
if pareto_dim and pareto_dim in df.columns:
    g = df.groupby(pareto_dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False)
    g = g[g.notna()]
    if len(g) >= 3:
        top_n = min(15, len(g))
        top = g.head(top_n)
        cum = top.cumsum() / max(1e-9, float(g.sum()))
        x = [str(i) for i in top.index.tolist()]
        fig_p = go.Figure()
        fig_p.add_trace(go.Bar(x=x, y=top.values, name="Revenue"))
        fig_p.add_trace(go.Scatter(x=x, y=(cum.values * 100), name="Cumulative %", yaxis="y2", mode="lines+markers"))
        fig_p.update_layout(
            title=f"Top {top_n} {pareto_dim} by {revenue_col} + cumulative share",
            yaxis=dict(title=f"{revenue_col}"),
            yaxis2=dict(title="Cumulative %", overlaying="y", side="right", rangemode="tozero", range=[0, 100]),
        )
        fig_p = apply_chart_style(fig_p, height=420, showlegend=True)
        fig_p.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, title=None))
        st.plotly_chart(fig_p, use_container_width=True, key="chart_pareto")
        charts_for_export.append((f"Revenue concentration (Pareto) — {pareto_dim}", fig_to_png_bytes(fig_p)))

        # Owner-readable sentence
        share_top3 = float(g.head(3).sum() / max(1e-9, g.sum())) * 100
        st.caption(f"Quick read: top 3 {pareto_dim} contribute ~{share_top3:.1f}% of total {revenue_col}.")
    else:
        st.info(f"Not enough unique values in {pareto_dim} for a concentration view.")
else:
    st.info("No suitable Store/Category/Channel column detected for concentration view.")

# 6) Simple relationships (optional, non-academic)
st.subheader("6) Simple relationship (optional)")

# Try to pick sensible retail numeric fields
units_col = None
price_col = None
for c in df.columns:
    if units_col is None and re.search(r"\b(unit|qty|quantity|units)\b", str(c), re.I) and is_numeric_series(df[c]):
        units_col = c
    if price_col is None and re.search(r"\bprice\b|\bunit[_ ]?price\b", str(c), re.I) and is_numeric_series(df[c]):
        price_col = c

if units_col and price_col:
    tmp = df[[units_col, price_col, revenue_col]].copy()
    tmp[units_col] = pd.to_numeric(tmp[units_col], errors="coerce")
    tmp[price_col] = pd.to_numeric(tmp[price_col], errors="coerce")
    tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
    tmp = tmp.dropna()
    if len(tmp) >= 10:
        fig_sc = px.scatter(
            tmp.sample(min(2000, len(tmp)), random_state=7),
            x=price_col,
            y=units_col,
            size=tmp[revenue_col].clip(lower=0.0),
            title=f"Price vs Units (bubble size = {revenue_col})",
            labels={price_col: price_col, units_col: units_col},
        )
        fig_sc = apply_chart_style(fig_sc, height=420, showlegend=False)
        st.plotly_chart(fig_sc, use_container_width=True, key="chart_price_units")
        charts_for_export.append((f"Price vs Units (bubble = {revenue_col})", fig_to_png_bytes(fig_sc)))
        st.caption("Quick read: look for clusters (high price/low units vs low price/high units) and outliers driving revenue.")
    else:
        st.info("Not enough non-missing rows for the relationship view.")
else:
    st.info("No obvious Units + Price columns detected — relationship view is skipped.")

st.divider()

# -----------------------------
# Key Insights (CEO-level, short)
# -----------------------------
st.header("Key insights (short, CEO-level)")

insight_lines: List[str] = []
insight_lines.append(f"Total {revenue_col} is **{human_money(total_rev)}** across **{rows:,}** records.")
if date_min and date_max:
    insight_lines.append(f"Time window is **{date_min} → {date_max}**.")

if top_store:
    insight_lines.append(f"Top store is **{top_store[0]}** with **{human_money(top_store[1])}** total {revenue_col}.")
if top_cat:
    insight_lines.append(f"Top category is **{top_cat[0]}** with **{human_money(top_cat[1])}** total {revenue_col}.")
if top_channel:
    insight_lines.append(f"Top channel is **{top_channel[0]}** with **{human_money(top_channel[1])}** total {revenue_col}.")

if cost_col and cost_col in df.columns:
    sc = pd.to_numeric(df[cost_col], errors="coerce")
    gm = None
    if "margin" in revenue_col.lower() or "margin" in cost_col.lower():
        gm = None
    else:
        gm = float((srev - sc).sum(skipna=True))
    if gm is not None and not np.isnan(gm):
        insight_lines.append(f"Gross profit proxy (Revenue − {cost_col}) is **{human_money(gm)}** (directional).")

# Concentration read if possible
if pareto_dim and pareto_dim in df.columns:
    g = df.groupby(pareto_dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False)
    if len(g) >= 3 and float(g.sum()) != 0:
        share_top3 = float(g.head(3).sum() / g.sum()) * 100
        insight_lines.append(f"Concentration: top 3 {pareto_dim} contribute ~**{share_top3:.1f}%** of total {revenue_col}.")

for line in insight_lines[:8]:
    st.write("• " + re.sub(r"\*\*", "", line))  # keep UI clean; summary already has bold feel

st.caption("MVP principle: clarity > completeness. If any chart needs explanation, remove it.")

# -----------------------------
# Data preview (optional)
# -----------------------------
with st.expander("Data preview & diagnostics (optional)", expanded=False):
    st.dataframe(df.head(50), use_container_width=True)

    profile_rows = []
    for c in df.columns:
        missing = df[c].isna().mean() * 100
        profile_rows.append({
            "column": c,
            "dtype": str(df[c].dtype),
            "missing_%": round(float(missing), 1),
            "unique_values": int(df[c].nunique(dropna=True)),
        })
    profile = pd.DataFrame(profile_rows).sort_values(["missing_%", "unique_values"], ascending=[False, False])
    st.markdown("**Column profile**")
    st.dataframe(profile, use_container_width=True)

# -----------------------------
# Export
# -----------------------------
st.header("Export (demo)")
st.caption("Please avoid uploading confidential or regulated data. This MVP is for demo/testing.")

cE1, cE2 = st.columns(2)
with cE1:
    if st.button("Build Executive Brief (PDF)"):
        pdf_bytes = build_pdf(summary_lines[:10], insight_lines[:10], charts_for_export)
        st.download_button("Download PDF", data=pdf_bytes, file_name="ecai_sales_mvp_brief.pdf", mime="application/pdf")

with cE2:
    if st.button("Build Slides (PPTX)"):
        ppt_bytes = build_pptx(summary_lines[:10], insight_lines[:10], charts_for_export)
        st.download_button("Download PPTX", data=ppt_bytes, file_name="ecai_sales_mvp_brief.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

with st.expander("Dev notes"):
    st.markdown(
        """
- **Sales-only MVP scope** keeps the product sharp for owner demos.
- For chart images inside exports, add **kaleido** to requirements:
  - `pip install kaleido`
- If your dataset has a Date field, you get the strongest demo flow.
"""
    )
