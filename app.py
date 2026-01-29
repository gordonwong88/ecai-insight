# app.py
# EC-AI Insight — Sales / Retail Transactions MVP
# Founder-first: Business Summary → Business Implications → 4 core visuals → Advanced (collapsed) → Exports
#
# NOTE: To export charts into PDF/PPT, add `kaleido` to requirements.txt.
#       Plotly uses Kaleido for fig.to_image().

import io
from datetime import datetime
from typing import List, Optional, Tuple, Dict

import numpy as np
import pandas as pd
import streamlit as st

import plotly.graph_objects as go
import plotly.express as px

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


# -----------------------------
# UI: Global styling
# -----------------------------
BASE_FONT_PX = 18  # bumped for readability (executive-friendly)

st.set_page_config(page_title="EC-AI Insight", layout="wide")

st.markdown(
    f"""
<style>
  html, body, [class*="css"]  {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    font-size: {BASE_FONT_PX}px;
  }}
  .ec-muted {{
    color: rgba(49,51,63,0.72);
    font-size: {BASE_FONT_PX}px;
  }}
  .ec-caption {{
    color: rgba(49,51,63,0.72);
    font-size: {BASE_FONT_PX}px;
    line-height: 1.5;
  }}
  .ec-card {{
    background: #ffffff;
    border: 1px solid rgba(49,51,63,0.10);
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 1px 10px rgba(0,0,0,0.04);
  }}
  .ec-card h3 {{
    margin: 0 0 8px 0;
    font-size: {BASE_FONT_PX + 6}px;
  }}
  .ec-card p {{
    margin: 0.35rem 0;
    line-height: 1.55;
    font-size: {BASE_FONT_PX}px;
  }}
  .ec-hint {{
    font-size: {BASE_FONT_PX}px;
    color: rgba(49,51,63,0.70);
  }}
  /* Make Streamlit captions readable */
  .stCaption, div[data-testid="stCaptionContainer"] {{
    font-size: {BASE_FONT_PX}px !important;
    color: rgba(49,51,63,0.72) !important;
  }}
  /* Tighten header spacing */
  h1 {{
    font-size: {BASE_FONT_PX + 18}px !important;
    margin-bottom: 0.2rem !important;
  }}
  h2 {{
    font-size: {BASE_FONT_PX + 10}px !important;
    margin-top: 0.8rem !important;
  }}
  h3 {{
    font-size: {BASE_FONT_PX + 6}px !important;
    margin-top: 0.6rem !important;
  }}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Helpers
# -----------------------------
def human_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    x = float(x)
    s = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000_000:
        return f"{s}${x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"{s}${x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{s}${x/1_000:.1f}K"
    return f"{s}${x:,.0f}"

def human_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"{x*100:.1f}%"

def try_parse_dates(s: pd.Series) -> Optional[pd.Series]:
    try:
        dt = pd.to_datetime(s, errors="coerce", utc=False)
        if dt.notna().mean() >= 0.60:
            return dt
    except Exception:
        pass
    return None

def pick_col(cols: List[str], candidates: List[str]) -> Optional[str]:
    cols_l = {c.lower(): c for c in cols}
    for k in candidates:
        for c in cols:
            if c.lower() == k.lower():
                return c
        # contains match
        for c in cols:
            if k.lower() in c.lower():
                return c
    return None

def fig_to_png_bytes(fig: go.Figure) -> Optional[bytes]:
    try:
        return fig.to_image(format="png", scale=2)  # requires kaleido
    except Exception:
        return None

def safe_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")

def discount_band(discount: pd.Series) -> pd.Series:
    # Expect discount as 0-1 or 0-100. Normalize to 0-1.
    d = pd.to_numeric(discount, errors="coerce")
    if d.dropna().empty:
        return pd.Series([np.nan] * len(discount))
    if d.dropna().quantile(0.95) > 1.0:  # likely 0-100
        d = d / 100.0
    bins = [-1, 0.0000001, 0.02, 0.05, 0.10, 0.15, 0.20, 1.0]
    labels = ["0%", "0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    return pd.cut(d, bins=bins, labels=labels)

# -----------------------------
# Export builders
# -----------------------------
def build_pdf(business_summary: List[str], business_implications: List[str],
              charts: List[Tuple[str, Optional[bytes]]]) -> bytes:
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=letter)
    W, H = letter

    def title(text: str, y: float) -> float:
        c.setFont("Helvetica-Bold", 18)
        c.drawString(0.8 * inch, y, text)
        return y - 0.35 * inch

    def bullets(lines: List[str], y: float, width_chars: int = 95) -> float:
        c.setFont("Helvetica", 12)
        for line in lines:
            # simple wrap
            words = line.split()
            cur = ""
            wrapped = []
            for w in words:
                if len(cur) + len(w) + 1 <= width_chars:
                    cur = (cur + " " + w).strip()
                else:
                    wrapped.append(cur)
                    cur = w
            if cur:
                wrapped.append(cur)

            for i, seg in enumerate(wrapped):
                prefix = "• " if i == 0 else "  "
                c.drawString(0.9 * inch, y, prefix + seg)
                y -= 0.22 * inch
                if y < 1.2 * inch:
                    c.showPage()
                    y = H - 0.9 * inch
                    c.setFont("Helvetica", 12)
        return y

    # Cover page
    c.setFont("Helvetica-Bold", 22)
    c.drawString(0.8 * inch, H - 0.9 * inch, "EC-AI Executive Brief")
    c.setFont("Helvetica", 12)
    c.drawString(0.8 * inch, H - 1.25 * inch, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y = H - 1.75 * inch

    y = title("Business Summary", y)
    y = bullets(business_summary, y)

    y -= 0.15 * inch
    y = title("Business Implications", y)
    y = bullets(business_implications, y)

    # Charts pages
    for chart_title, img in charts:
        c.showPage()
        y = H - 0.9 * inch
        y = title(chart_title, y)
        if img is None:
            c.setFont("Helvetica", 12)
            c.drawString(0.9 * inch, y, "Chart image could not be rendered. (Install kaleido to enable exports.)")
            continue
        ir = ImageReader(io.BytesIO(img))
        img_w = W - 1.6 * inch
        img_h = 5.0 * inch
        c.drawImage(ir, 0.8 * inch, 1.4 * inch, width=img_w, height=img_h, preserveAspectRatio=True, anchor="n")

    c.save()
    buff.seek(0)
    return buff.getvalue()

def _add_title(slide, title: str, subtitle: Optional[str] = None):
    tx = slide.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12.0), Inches(0.8))
    tf = tx.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = title
    p.font.bold = True
    p.font.size = Pt(34)
    p.font.color.rgb = RGBColor(20, 20, 20)
    if subtitle:
        tx2 = slide.shapes.add_textbox(Inches(0.7), Inches(1.1), Inches(12.0), Inches(0.6))
        tf2 = tx2.text_frame
        tf2.clear()
        p2 = tf2.paragraphs[0]
        p2.text = subtitle
        p2.font.size = Pt(18)
        p2.font.color.rgb = RGBColor(90, 90, 90)

def _add_bullets(slide, heading: str, lines: List[str]):
    box = slide.shapes.add_textbox(Inches(0.7), Inches(1.6), Inches(12.0), Inches(5.5))
    tf = box.text_frame
    tf.word_wrap = True
    tf.clear()
    p0 = tf.paragraphs[0]
    p0.text = heading
    p0.font.bold = True
    p0.font.size = Pt(24)
    p0.font.color.rgb = RGBColor(20, 20, 20)
    for line in lines:
        p = tf.add_paragraph()
        p.text = line
        p.level = 0
        p.font.size = Pt(18)
        p.font.color.rgb = RGBColor(40, 40, 40)

def _add_image_slide(prs: Presentation, title: str, img_bytes: bytes):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, title)
    img_stream = io.BytesIO(img_bytes)
    slide.shapes.add_picture(img_stream, Inches(0.8), Inches(1.4), width=Inches(11.8))

def build_pptx(business_summary: List[str], business_implications: List[str],
               charts: List[Tuple[str, Optional[bytes]]]) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, "EC-AI Executive Brief", "Sales performance, explained clearly.")

    # Summary slide
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, "Business Summary")
    _add_bullets(slide, "Key points", business_summary)

    # Implications slide
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, "Business Implications")
    _add_bullets(slide, "What to do next", business_implications)

    # Chart slides
    for chart_title, img in charts:
        if img is None:
            continue
        _add_image_slide(prs, chart_title, img)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.getvalue()


# -----------------------------
# Main UI
# -----------------------------
st.title("EC-AI Insight")
st.markdown("<div class='ec-muted'>Sales performance, explained clearly.</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='ec-caption'>Upload your sales data and get a short business briefing — "
    "what’s working, what’s risky, and where to focus next.</div>",
    unsafe_allow_html=True,
)

st.divider()

uploaded = st.file_uploader("Upload retail sales / transaction data (CSV or Excel)", type=["csv", "xlsx", "xls"])

if not uploaded:
    st.info("Tip: start with retail sales / transaction data. Columns like Date, Store, Revenue, Discount will give the best demo.")
    st.stop()

# Load
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

if df_raw.empty:
    st.error("File loaded but contains no rows.")
    st.stop()

df = df_raw.copy()

# Detect key columns
date_col = pick_col(df.columns.tolist(), ["date", "transaction_date", "order_date", "invoice_date"])
store_col = pick_col(df.columns.tolist(), ["store", "branch", "location", "outlet"])
revenue_col = pick_col(df.columns.tolist(), ["revenue", "sales", "amount", "net_sales", "total"])
discount_col = pick_col(df.columns.tolist(), ["discount", "discount_rate", "discount_pct", "disc"])
cogs_col = pick_col(df.columns.tolist(), ["cogs", "cost", "cost_of_goods"])
units_col = pick_col(df.columns.tolist(), ["units", "qty", "quantity", "volume"])

if revenue_col is None:
    st.error("I couldn't find a Revenue/Sales column. For this MVP, please include a column like 'Revenue' or 'Sales'.")
    st.stop()

df[revenue_col] = safe_numeric(df, revenue_col)

if date_col:
    dt = try_parse_dates(df[date_col])
    if dt is not None:
        df[date_col] = dt
    else:
        date_col = None

# -----------------------------
# BUSINESS SUMMARY + IMPLICATIONS (data-driven, founder tone)
# -----------------------------
total_rev = float(df[revenue_col].sum(skipna=True))
avg_rev = float(df[revenue_col].mean(skipna=True)) if df[revenue_col].notna().any() else np.nan

top_store_name = None
second_store_name = None
top_store_rev = None
second_store_rev = None
share_top2 = None

if store_col:
    by_store = df.groupby(store_col)[revenue_col].sum(min_count=1).sort_values(ascending=False)
    if len(by_store) >= 1:
        top_store_name = str(by_store.index[0])
        top_store_rev = float(by_store.iloc[0])
    if len(by_store) >= 2:
        second_store_name = str(by_store.index[1])
        second_store_rev = float(by_store.iloc[1])
    if len(by_store) >= 2 and float(by_store.sum()) != 0:
        share_top2 = float((by_store.iloc[0] + by_store.iloc[1]) / by_store.sum())

# Growth estimate
growth_txt = None
if date_col:
    daily = df.dropna(subset=[date_col]).groupby(pd.Grouper(key=date_col, freq="D"))[revenue_col].sum(min_count=1).dropna()
    if len(daily) >= 2:
        start_v = float(daily.iloc[0])
        end_v = float(daily.iloc[-1])
        if start_v != 0:
            growth = (end_v - start_v) / abs(start_v)
            growth_txt = f"Overall sales increased from {human_money(start_v)} to {human_money(end_v)} (approx. {human_pct(growth)})."

# Volatility cue (store-level CV)
volatility_txt = None
if store_col:
    store_stats = df.groupby(store_col)[revenue_col].agg(["mean", "std", "count"])
    store_stats["cv"] = store_stats["std"] / store_stats["mean"].replace(0, np.nan)
    store_stats = store_stats.replace([np.inf, -np.inf], np.nan).dropna(subset=["cv"])
    if not store_stats.empty:
        worst = store_stats.sort_values("cv", ascending=False).head(1)
        w_name = str(worst.index[0])
        w_cv = float(worst["cv"].iloc[0])
        volatility_txt = f"Some stores are highly volatile (e.g., **{w_name}** shows high day‑to‑day swings; CV≈{w_cv:.2f})."

# Discount effectiveness cue
disc_txt = None
if discount_col:
    bands = discount_band(df[discount_col])
    tmp = df.copy()
    tmp["_disc_band"] = bands
    agg = tmp.groupby("_disc_band")[revenue_col].mean().dropna()
    if len(agg) >= 2:
        best_band = agg.sort_values(ascending=False).index[0]
        worst_band = agg.sort_values(ascending=True).index[0]
        disc_txt = f"Moderate discounts (around **{best_band}**) are associated with higher average revenue per sale, while deeper discounts (e.g., **{worst_band}**) appear less efficient."

business_summary = []
if top_store_name and second_store_name and share_top2 is not None:
    business_summary.append(
        f"Revenue is concentrated in a small number of stores, led by **{top_store_name}** and **{second_store_name}** (top two contribute ~{share_top2*100:.0f}% of total)."
    )
elif store_col and top_store_name:
    business_summary.append(f"Top store by revenue is **{top_store_name}** ({human_money(top_store_rev)}).")

if growth_txt:
    business_summary.append(growth_txt)
else:
    business_summary.append(f"Total revenue is **{human_money(total_rev)}** (average per record {human_money(avg_rev)}).")

if volatility_txt:
    business_summary.append(volatility_txt)
else:
    business_summary.append("Performance varies by store/day; focus on consistency in your top performers.")

if disc_txt:
    business_summary.append(disc_txt)
else:
    business_summary.append("Pricing/discount patterns can materially affect revenue efficiency — review discount strategy by store and product mix.")

business_summary.append("The biggest opportunity is to **stabilise and scale what already works** in top-performing stores before expanding promotions.")

business_implications = [
    "Double down on execution in top stores (staffing, inventory availability, consistent promotion rules).",
    "Reduce volatility first — inconsistent performance is often operational (mix, stockouts, local promotion discipline).",
    "Be cautious with deep discounts; test promotions with clear targets and measure revenue per sale (not just volume).",
]

# Render Business Summary card (safe HTML string)
summary_html = "<div class='ec-card'><h3>Business Summary</h3>" + "".join(
    [f"<p>• {line}</p>" for line in business_summary]
) + "<p class='ec-hint'>Start here. This section explains the story before you look at any charts.</p></div>"

st.markdown(summary_html, unsafe_allow_html=True)

st.divider()

implications_html = "<div class='ec-card'><h3>What This Means for the Business</h3><p><b>What to focus on next</b></p>" + "".join(
    [f"<p>• {line}</p>" for line in business_implications]
) + "</div>"

st.markdown(implications_html, unsafe_allow_html=True)

st.divider()

# -----------------------------
# Core visuals (DEFAULT)
# -----------------------------
st.subheader("Revenue Overview")

charts_for_export: List[Tuple[str, Optional[bytes]]] = []

# 1) Revenue trend
trend_fig = None
if date_col:
    ts = df.dropna(subset=[date_col]).groupby(pd.Grouper(key=date_col, freq="D"))[revenue_col].sum(min_count=1).reset_index()
    if not ts.empty:
        trend_fig = px.line(ts, x=date_col, y=revenue_col, markers=False)
        trend_fig.update_layout(
            height=360,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_title="Date",
            yaxis_title="Revenue",
            legend_title_text="",
            font=dict(size=BASE_FONT_PX + 2),
        )
        trend_fig.update_yaxes(tickprefix="$", separatethousands=True)
        st.plotly_chart(trend_fig, use_container_width=True)
        charts_for_export.append(("Revenue Trend", fig_to_png_bytes(trend_fig)))
else:
    st.info("No usable Date column detected, so the revenue trend chart is hidden.")

st.subheader("Top Revenue-Generating Stores")
top_store_fig = None
if store_col:
    top5 = df.groupby(store_col)[revenue_col].sum(min_count=1).sort_values(ascending=False).head(5).reset_index()
    top5["Label"] = top5[revenue_col].apply(lambda v: human_money(v))
    top_store_fig = px.bar(top5, x=revenue_col, y=store_col, orientation="h", text="Label")
    top_store_fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Revenue",
        yaxis_title="Store",
        font=dict(size=BASE_FONT_PX + 2),
    )
    top_store_fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(top_store_fig, use_container_width=True)
    charts_for_export.append(("Top Stores by Revenue", fig_to_png_bytes(top_store_fig)))
else:
    st.info("No Store column detected — store breakdown is hidden.")

st.subheader("Store Stability (Top 5)")
if store_col and date_col:
    top_stores = df.groupby(store_col)[revenue_col].sum(min_count=1).sort_values(ascending=False).head(5).index.tolist()
    sub = df[df[store_col].isin(top_stores)].dropna(subset=[date_col])
    if not sub.empty:
        # daily per store
        daily_store = sub.groupby([pd.Grouper(key=date_col, freq="D"), store_col])[revenue_col].sum(min_count=1).reset_index()
        cols = st.columns(2, gap="large")
        mini_figs = []
        for i, sname in enumerate(top_stores):
            d = daily_store[daily_store[store_col] == sname]
            fig = px.line(d, x=date_col, y=revenue_col)
            fig.update_layout(
                height=260,
                margin=dict(l=10, r=10, t=35, b=10),
                xaxis_title="",
                yaxis_title="",
                title=dict(text=str(sname), x=0.02, xanchor="left"),
                font=dict(size=BASE_FONT_PX + 1),
            )
            fig.update_yaxes(tickprefix="$", separatethousands=True)
            with cols[i % 2]:
                st.plotly_chart(fig, use_container_width=True)
            mini_figs.append((f"Store Trend — {sname}", fig_to_png_bytes(fig)))
        # Export: include only 2 representative mini charts to keep brief short
        charts_for_export.extend(mini_figs[:2])
else:
    st.info("Store stability view requires both Date and Store columns.")

st.subheader("Pricing Effectiveness")
disc_fig = None
if discount_col:
    tmp = df.copy()
    tmp["_disc_band"] = discount_band(tmp[discount_col])
    band = tmp.groupby("_disc_band")[revenue_col].mean().reset_index()
    band = band.dropna(subset=["_disc_band", revenue_col])
    if not band.empty:
        band["Label"] = band[revenue_col].apply(lambda v: human_money(v))
        disc_fig = px.bar(band, x="_disc_band", y=revenue_col, text="Label")
        disc_fig.update_layout(
            height=360,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_title="Discount band",
            yaxis_title="Average revenue per sale",
            font=dict(size=BASE_FONT_PX + 2),
        )
        disc_fig.update_traces(textposition="outside", cliponaxis=False)
        disc_fig.update_yaxes(tickprefix="$", separatethousands=True)
        st.plotly_chart(disc_fig, use_container_width=True)
        charts_for_export.append(("Discount Effectiveness", fig_to_png_bytes(disc_fig)))
else:
    st.info("No Discount column detected — discount effectiveness is hidden.")

st.divider()

# -----------------------------
# Advanced analysis (collapsed)
# -----------------------------
with st.expander("Advanced analysis (optional)"):
    st.markdown("### View raw data (optional)")
    st.dataframe(df.head(50), use_container_width=True)

    st.markdown("### Data quality & assumptions (advanced)")
    miss = df.isna().mean().sort_values(ascending=False)
    prof = pd.DataFrame({
        "Column": df.columns,
        "Missing %": (df.isna().mean() * 100).round(1).values,
        "Distinct": [df[c].nunique(dropna=True) for c in df.columns],
        "Type": [str(df[c].dtype) for c in df.columns],
    })
    st.dataframe(prof, use_container_width=True, height=260)

    st.markdown("### Correlation (advanced)")
    num = df.select_dtypes(include=[np.number]).copy()
    if num.shape[1] >= 2:
        corr = num.corr(numeric_only=True)
        heat = px.imshow(corr, text_auto=".2f", aspect="auto")
        heat.update_layout(height=520, margin=dict(l=20, r=20, t=30, b=20), font=dict(size=BASE_FONT_PX))
        st.plotly_chart(heat, use_container_width=True)
    else:
        st.caption("Not enough numeric columns to compute correlation.")

st.divider()

# -----------------------------
# Exports (Executive Brief only)
# -----------------------------
st.subheader("Export Executive Brief")
st.markdown(
    "<div class='ec-caption'>Download a short executive-ready summary for sharing or review.<br>"
    "• PDF Executive Brief — selected insights only<br>"
    "• PPT Talking Deck — one insight per slide</div>",
    unsafe_allow_html=True,
)

# Pre-render chart bytes and warn if missing
missing_imgs = [t for t, b in charts_for_export if b is None]
if missing_imgs:
    st.warning(
        "Some charts could not be rendered for export (likely missing `kaleido`). "
        "Exports will work best after adding `kaleido` to requirements.txt. "
        f"Missing images: {', '.join(missing_imgs[:4])}{'...' if len(missing_imgs) > 4 else ''}"
    )

c1, c2 = st.columns(2)
with c1:
    if st.button("Build PDF Executive Brief"):
        pdf_bytes = build_pdf(business_summary, business_implications, charts_for_export[:4])
        st.download_button("Download PDF", data=pdf_bytes, file_name="ecai_executive_brief.pdf", mime="application/pdf")
with c2:
    if st.button("Build PPT Talking Deck"):
        ppt_bytes = build_pptx(business_summary, business_implications, charts_for_export[:4])
        st.download_button(
            "Download PPTX",
            data=ppt_bytes,
            file_name="ecai_talking_deck.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

