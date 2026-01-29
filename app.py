# app.py
# EC-AI Insight — Sales / Retail Transactions MVP (Founder-first)
# Focus: clear business story + executive-ready exports (PDF/PPT with charts)
#
# Requirements (key):
# - streamlit, pandas, numpy, plotly, openpyxl
# - reportlab (PDF), python-pptx (PPT)
# - kaleido (Plotly image export for PDF/PPT charts)

import io
from datetime import datetime
from typing import Optional, List, Tuple, Dict

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN

# -----------------------------
# UI theme + helpers
# -----------------------------
BASE_FONT_PX = 17  # global readability (you asked +1)
TITLE_FONT_PX = BASE_FONT_PX + 14
SUBTITLE_FONT_PX = BASE_FONT_PX + 1
SECTION_FONT_PX = BASE_FONT_PX + 4

# Tableau 10 palette (Tableau-like)
TABLEAU10 = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"
]

def inject_css() -> None:
    st.markdown(
        f"""
        <style>
          html, body, [class*="css"]  {{
            font-size: {BASE_FONT_PX}px;
          }}
          .ec-subtitle {{
            color: #555;
            font-size: {SUBTITLE_FONT_PX}px;
            line-height: 1.5;
            margin-top: -6px;
            margin-bottom: 14px;
          }}
          .ec-card {{
            border: 1px solid #eee;
            border-radius: 14px;
            padding: 16px 18px;
            background: #fff;
            box-shadow: 0 1px 10px rgba(0,0,0,0.03);
            margin-bottom: 14px;
          }}
          .ec-card h3 {{
            font-size: {SECTION_FONT_PX}px;
            margin: 0 0 10px 0;
          }}
          .ec-h4 {{
            font-weight: 700;
            font-size: {BASE_FONT_PX + 1}px;
            margin: 18px 0 10px 0; /* more spacing between sub headers */
          }}
          .ec-bullets {{
            margin: 0 0 6px 0;
            padding-left: 18px;
          }}
          .ec-bullets li {{
            margin: 8px 0;           /* more spacing between bullets */
            line-height: 1.6;
          }}
          .ec-note {{
            color: #666;
            font-size: {BASE_FONT_PX}px;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def human_money(x: float) -> str:
    try:
        x = float(x)
    except Exception:
        return "—"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:.1f}K"
    return f"{sign}${x:,.0f}"

def safe_to_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")

def pick_col(cols: List[str], candidates: List[str]) -> Optional[str]:
    cl = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in cl:
            return cl[cand.lower()]
    # fuzzy contains
    for c in cols:
        lc = c.lower()
        for cand in candidates:
            if cand.lower() in lc:
                return c
    return None

def detect_date_col(df: pd.DataFrame) -> Optional[str]:
    # prefer explicit names
    c = pick_col(list(df.columns), ["date", "transaction_date", "order_date", "day"])
    if c:
        return c
    # try parse any object column with high parse success
    best = None
    best_rate = 0.0
    for col in df.columns:
        if df[col].dtype == "object" or "date" in str(df[col].dtype).lower():
            parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            rate = parsed.notna().mean()
            if rate > best_rate and rate >= 0.7:
                best_rate = rate
                best = col
    return best

def ensure_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col and col in df.columns:
        df = df.copy()
        df[col] = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
    return df

def discount_band_from_rate(rate: pd.Series) -> pd.Series:
    # rate: 0-1
    r = pd.to_numeric(rate, errors="coerce")
    bins = [-1e9, 0.02, 0.05, 0.10, 0.15, 0.20, 1e9]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    return pd.cut(r, bins=bins, labels=labels, include_lowest=True, right=True)

DISCOUNT_ORDER = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]

def fig_style(fig):
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20),
        font=dict(size=BASE_FONT_PX),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(title_font=dict(size=BASE_FONT_PX), tickfont=dict(size=BASE_FONT_PX-1))
    fig.update_yaxes(title_font=dict(size=BASE_FONT_PX), tickfont=dict(size=BASE_FONT_PX-1))
    return fig

def fig_to_png_bytes(fig) -> Optional[bytes]:
    if fig is None:
        return None
    try:
        # Higher scale for sharp PDF/PPT
        return fig.to_image(format="png", scale=2)
    except Exception as e:
        # surface the real error to user (not generic "install kaleido")
        st.warning(f"Chart export failed (Plotly→PNG). Details: {e}")
        return None

# -----------------------------
# Business computations
# -----------------------------
def compute_concentration(agg: pd.Series, top_n: int = 2) -> float:
    if agg is None or len(agg) == 0:
        return np.nan
    total = float(agg.sum())
    if total <= 0:
        return np.nan
    return float(agg.sort_values(ascending=False).head(top_n).sum() / total)

def coeff_var(s: pd.Series) -> float:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < 2:
        return np.nan
    m = float(s.mean())
    if m == 0:
        return np.nan
    return float(s.std(ddof=0) / m)

def build_insights(df: pd.DataFrame, date_col: Optional[str], revenue_col: str,
                   store_col: Optional[str], category_col: Optional[str],
                   channel_col: Optional[str], discount_col: Optional[str],
                   cogs_col: Optional[str]) -> Dict[str, List[str]]:
    bullets_summary: List[str] = []
    bullets_money: List[str] = []
    bullets_risk: List[str] = []
    bullets_improve: List[str] = []
    bullets_next: List[str] = []

    # totals
    rev = safe_to_numeric(df[revenue_col]).dropna()
    total_rev = float(rev.sum()) if len(rev) else np.nan

    # store concentration
    top_store_name = None
    top_store_rev = None
    conc2 = np.nan
    if store_col and store_col in df.columns:
        store_agg = df.groupby(store_col)[revenue_col].apply(lambda s: safe_to_numeric(s).sum(min_count=1)).sort_values(ascending=False)
        if len(store_agg):
            top_store_name = str(store_agg.index[0])
            top_store_rev = float(store_agg.iloc[0])
            conc2 = compute_concentration(store_agg, top_n=2)

            if not np.isnan(conc2):
                bullets_summary.append(
                    f"Revenue is concentrated in a small number of stores, led by **{top_store_name}** (top two contribute ~**{conc2*100:.0f}%** of total)."
                )
            else:
                bullets_summary.append(
                    f"Top store is **{top_store_name}** with total revenue **{human_money(top_store_rev)}**."
                )

            bullets_money.append(f"**{top_store_name}** is the largest contributor (**{human_money(top_store_rev)}**).")
            if not np.isnan(conc2):
                bullets_money.append("A small group of stores accounts for a disproportionate share of revenue (winner‑takes‑more pattern).")

    # trend
    if date_col:
        tmp = df[[date_col, revenue_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce", infer_datetime_format=True)
        tmp[revenue_col] = safe_to_numeric(tmp[revenue_col])
        ts = tmp.dropna(subset=[date_col]).groupby(pd.Grouper(key=date_col, freq="D"))[revenue_col].sum(min_count=1).dropna().sort_index()
        if len(ts) >= 5:
            first = float(ts.iloc[0])
            last = float(ts.iloc[-1])
            if first > 0:
                pct = (last / first - 1.0) * 100.0
                bullets_summary.append(f"Overall sales moved from **{human_money(first)}** to **{human_money(last)}** (approx. **{pct:.1f}%**).")

    # volatility: store-level CV on daily totals
    top_cv_store = None
    top_cv_val = None
    if store_col and date_col:
        tmp = df[[date_col, store_col, revenue_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce", infer_datetime_format=True)
        tmp[revenue_col] = safe_to_numeric(tmp[revenue_col])
        g = tmp.dropna(subset=[date_col]).groupby([store_col, pd.Grouper(key=date_col, freq="D")])[revenue_col].sum(min_count=1).reset_index()
        if len(g):
            cvs = g.groupby(store_col)[revenue_col].apply(coeff_var).sort_values(ascending=False)
            if len(cvs) and not np.isnan(float(cvs.iloc[0])):
                top_cv_store = str(cvs.index[0])
                top_cv_val = float(cvs.iloc[0])
                bullets_summary.append(f"Some stores are volatile (e.g., **{top_cv_store}** shows large day‑to‑day swings; volatility score ≈ **{top_cv_val:.2f}**).")
                bullets_risk.append(f"Performance is uneven — **{top_cv_store}** shows the largest variability, which makes forecasting harder.")
                bullets_risk.append("Revenue concentration is high — losing performance in the top stores materially impacts total results.")

    # discount effectiveness: revenue per sale by band
    if discount_col and discount_col in df.columns:
        tmp = df[[discount_col, revenue_col]].copy()
        tmp[discount_col] = safe_to_numeric(tmp[discount_col])
        tmp[revenue_col] = safe_to_numeric(tmp[revenue_col])
        tmp = tmp.dropna(subset=[discount_col, revenue_col])
        if len(tmp) >= 30:
            tmp["_band"] = discount_band_from_rate(tmp[discount_col])
            band_avg = tmp.groupby("_band")[revenue_col].mean().reindex(DISCOUNT_ORDER)
            if band_avg.notna().sum() >= 3:
                best_band = band_avg.idxmax()
                worst_band = band_avg.idxmin()
                bullets_summary.append(
                    f"Discounts around **{best_band}** align with higher average revenue per sale, while deeper discounts (e.g., **{worst_band}**) appear less efficient."
                )
                bullets_improve.append("Discounting beyond **15–20%** may reduce revenue efficiency; treat deep discounts as experiments with clear targets.")
                bullets_improve.append("Use **revenue per sale** as a guardrail metric when testing promotions (not only volume).")

    # category top
    if category_col and category_col in df.columns:
        cat_agg = df.groupby(category_col)[revenue_col].apply(lambda s: safe_to_numeric(s).sum(min_count=1)).sort_values(ascending=False)
        if len(cat_agg):
            top_cat = str(cat_agg.index[0])
            top_cat_rev = float(cat_agg.iloc[0])
            bullets_money.append(f"Top category by revenue is **{top_cat}** (**{human_money(top_cat_rev)}**).")

    # gross margin (directional)
    if cogs_col and cogs_col in df.columns:
        rev_s = safe_to_numeric(df[revenue_col])
        cogs_s = safe_to_numeric(df[cogs_col])
        valid = rev_s.notna() & cogs_s.notna() & (rev_s != 0)
        if valid.sum() >= 30:
            gm = (rev_s[valid] - cogs_s[valid]) / rev_s[valid]
            gm_avg = float(gm.mean())
            bullets_improve.append(f"Average gross margin is approximately **{gm_avg*100:.1f}%** (directional). Consider reviewing margin by store/category.")

    # next focus (always)
    bullets_next.append("Strengthen execution in top stores (inventory availability, staffing, promotion discipline).")
    bullets_next.append("Reduce volatility first — inconsistent performance is often operational.")
    bullets_next.append("Test promotions with clear targets; stop what doesn’t improve revenue per sale.")

    # If summary too short, add general fallback
    if len(bullets_summary) < 3 and not np.isnan(total_rev):
        bullets_summary.append(f"Total revenue in the dataset is **{human_money(total_rev)}** across **{len(df):,}** transactions/rows.")

    return {
        "summary": bullets_summary,
        "money": bullets_money,
        "risk": bullets_risk,
        "improve": bullets_improve,
        "next": bullets_next,
    }

# -----------------------------
# Exports
# -----------------------------
def make_executive_brief_pdf(
    title: str,
    insights: Dict[str, List[str]],
    charts: List[Tuple[str, Optional[bytes]]],
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    W, H = letter

    def draw_header():
        c.setFont("Helvetica-Bold", 18)
        c.drawString(40, H - 60, "EC-AI Executive Brief")
        c.setFont("Helvetica", 10)
        c.drawString(40, H - 78, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.setStrokeColorRGB(0.85, 0.85, 0.85)
        c.line(40, H - 90, W - 40, H - 90)

    def draw_bullets(x, y, bullets, font_size=11, leading=15, max_lines=999):
        c.setFont("Helvetica", font_size)
        used = 0
        for b in bullets:
            # wrap lines
            wrapped = textwrap.wrap(b.replace("**", ""), width=95)
            for j, wline in enumerate(wrapped):
                if used >= max_lines:
                    return y
                prefix = "• " if j == 0 else "  "
                c.drawString(x, y, prefix + wline)
                y -= leading
                used += 1
            y -= 2
        return y

    # Page 1: summary + business insights
    draw_header()
    y = H - 120

    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Business Summary")
    y -= 18
    y = draw_bullets(50, y, insights.get("summary", []), font_size=11, leading=15, max_lines=18)

    y -= 6
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, y, "Business Insights")
    y -= 18

    # more readable spacing between sub-sections
    sections = [
        ("Where the money is made", insights.get("money", [])),
        ("Where risk exists", insights.get("risk", [])),
        ("What can be improved", insights.get("improve", [])),
        ("What to focus on next", insights.get("next", [])),
    ]
    for sec, bl in sections:
        if not bl:
            continue
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, sec)
        y -= 16
        y = draw_bullets(60, y, bl, font_size=11, leading=15, max_lines=10)
        y -= 6

    c.showPage()

    # Chart pages: include chart + 2-3 commentary bullets
    for chart_title, png_bytes in charts:
        if not png_bytes:
            continue
        draw_header()
        y = H - 120
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, chart_title)
        y -= 18

        # chart image area (fit)
        img = ImageReader(io.BytesIO(png_bytes))
        img_w, img_h = img.getSize()

        # target box
        box_w = W - 80
        box_h = 360
        scale = min(box_w / img_w, box_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x0 = 40 + (box_w - draw_w) / 2
        y0 = y - draw_h - 6
        c.drawImage(img, x0, y0, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')

        # commentary (lightweight; reuse existing insight pools)
        y_text = y0 - 22
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y_text, "Commentary")
        y_text -= 16

        # pick 2-3 bullets depending on chart
        comm: List[str] = []
        lt = chart_title.lower()
        if "top store" in lt:
            comm = (insights.get("money", []) + insights.get("risk", []))[:3]
        elif "trend" in lt:
            comm = insights.get("summary", [])[:3]
        elif "discount" in lt or "pricing" in lt:
            comm = insights.get("improve", [])[:3]
        elif "volatility" in lt or "stability" in lt:
            comm = (insights.get("risk", []) + insights.get("next", []))[:3]
        else:
            comm = (insights.get("summary", []) + insights.get("next", []))[:3]

        y_text = draw_bullets(50, y_text, comm, font_size=10, leading=14, max_lines=10)
        c.showPage()

    c.save()
    return buf.getvalue()

def make_talking_deck_pptx(
    insights: Dict[str, List[str]],
    charts: List[Tuple[str, Optional[bytes]]],
) -> bytes:
    prs = Presentation()
    # 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    def add_title(slide, text):
        tx = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12.2), Inches(0.6))
        tf = tx.text_frame
        tf.clear()
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(28)
        p.font.bold = True

    def add_bullets(slide, bullets: List[str]):
        box = slide.shapes.add_textbox(Inches(0.7), Inches(1.15), Inches(5.2), Inches(5.9))
        tf = box.text_frame
        tf.word_wrap = True
        tf.clear()
        for i, b in enumerate(bullets[:6]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = b.replace("**", "")
            p.level = 0
            p.font.size = Pt(16)
            p.space_after = Pt(6)

    def add_image_fit(slide, img_bytes: bytes):
        # Fit into right side nicely
        left = Inches(6.1)
        top = Inches(1.2)
        max_w = Inches(6.9)
        max_h = Inches(5.8)
        pic = slide.shapes.add_picture(io.BytesIO(img_bytes), left, top)
        # scale to fit
        w = pic.width
        h = pic.height
        scale = min(max_w / w, max_h / h)
        pic.width = int(w * scale)
        pic.height = int(h * scale)
        # center in box
        pic.left = int(left + (max_w - pic.width) / 2)
        pic.top = int(top + (max_h - pic.height) / 2)

    # Slide 1: Business Summary
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    add_title(s, "EC-AI Talking Deck")
    sub = s.shapes.add_textbox(Inches(0.7), Inches(1.2), Inches(12.0), Inches(0.6))
    tf = sub.text_frame
    tf.text = "Sales performance briefing (executive-ready)"
    tf.paragraphs[0].font.size = Pt(18)
    tf.paragraphs[0].font.bold = False

    box = s.shapes.add_textbox(Inches(0.7), Inches(2.0), Inches(12.0), Inches(5.2))
    tf2 = box.text_frame
    tf2.word_wrap = True
    tf2.clear()
    p = tf2.paragraphs[0]
    p.text = "Business Summary"
    p.font.size = Pt(22); p.font.bold = True
    for b in insights.get("summary", [])[:6]:
        pp = tf2.add_paragraph()
        pp.text = "• " + b.replace("**", "")
        pp.font.size = Pt(16)
        pp.space_after = Pt(6)

    # Chart slides
    for title, png in charts:
        if not png:
            continue
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        add_title(slide, title)

        # commentary picks
        lt = title.lower()
        if "top store" in lt:
            comm = (insights.get("money", []) + insights.get("risk", []))[:4]
        elif "trend" in lt:
            comm = insights.get("summary", [])[:4]
        elif "discount" in lt or "pricing" in lt:
            comm = insights.get("improve", [])[:4]
        elif "volatility" in lt or "stability" in lt:
            comm = (insights.get("risk", []) + insights.get("next", []))[:4]
        else:
            comm = (insights.get("next", []) + insights.get("summary", []))[:4]

        add_bullets(slide, comm)
        add_image_fit(slide, png)

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()

# -----------------------------
# App
# -----------------------------
st.set_page_config(page_title="EC-AI Insight", layout="wide")
inject_css()

st.markdown(f"<div style='font-size:{TITLE_FONT_PX}px; font-weight:800;'>EC-AI Insight</div>", unsafe_allow_html=True)
st.markdown("<div class='ec-subtitle'>Sales performance, explained clearly. Upload your sales data and get a short briefing — what’s working, what’s risky, and where to focus next.</div>", unsafe_allow_html=True)

uploaded = st.file_uploader("Upload a dataset", type=["csv", "xlsx", "xls"])
if not uploaded:
    st.info("Upload a CSV or Excel file to begin.")
    st.stop()

# Load data
try:
    if uploaded.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

df.columns = [c.strip() for c in df.columns]

# Detect columns (retail/sales)
cols = list(df.columns)
revenue_col = pick_col(cols, ["revenue", "sales", "amount", "total", "net_sales"]) or cols[0]
store_col = pick_col(cols, ["store", "branch", "outlet", "shop"])
category_col = pick_col(cols, ["category", "product_category", "dept", "department"])
channel_col = pick_col(cols, ["channel", "sales_channel"])
discount_col = pick_col(cols, ["discount_rate", "discount", "disc_rate"])
cogs_col = pick_col(cols, ["cogs", "cost", "cost_of_goods", "cost_of_sales"])

date_col = detect_date_col(df)
if date_col:
    df = ensure_datetime(df, date_col)

# Ensure revenue numeric
df[revenue_col] = safe_to_numeric(df[revenue_col])

# -----------------------------
# Business Summary + Insights (DEFAULT)
# -----------------------------
insights = build_insights(df, date_col, revenue_col, store_col, category_col, channel_col, discount_col, cogs_col)

st.divider()

# Business Insights card with better spacing
def render_business_insights_card(ins: Dict[str, List[str]]):
    html = """
    <div class="ec-card">
      <h3>Business Insights</h3>

      <div class="ec-h4">Where the money is made</div>
      <ul class="ec-bullets">
    """
    for b in ins.get("money", [])[:4]:
        html += f"<li>{b}</li>"
    html += "</ul>"

    html += """
      <div class="ec-h4">Where risk exists</div>
      <ul class="ec-bullets">
    """
    for b in ins.get("risk", [])[:4]:
        html += f"<li>{b}</li>"
    html += "</ul>"

    html += """
      <div class="ec-h4">What can be improved</div>
      <ul class="ec-bullets">
    """
    for b in ins.get("improve", [])[:4]:
        html += f"<li>{b}</li>"
    html += "</ul>"

    html += """
      <div class="ec-h4">What to focus on next</div>
      <ul class="ec-bullets">
    """
    for b in ins.get("next", [])[:4]:
        html += f"<li>{b}</li>"
    html += "</ul></div>"
    st.markdown(html, unsafe_allow_html=True)

# Summary (short bullets)
st.subheader("Business Summary")
for b in insights.get("summary", [])[:6]:
    st.write("• " + b)

render_business_insights_card(insights)

# -----------------------------
# Core visuals (DEFAULT)
# -----------------------------
st.divider()
st.subheader("Revenue Overview")

charts_for_export: List[Tuple[str, Optional[bytes]]] = []

# Revenue trend
trend_fig = None
if date_col and df[date_col].notna().any():
    tmp = df[[date_col, revenue_col]].copy()
    tmp = tmp.dropna(subset=[date_col])
    tmp[revenue_col] = safe_to_numeric(tmp[revenue_col])
    daily = tmp.groupby(pd.Grouper(key=date_col, freq="D"))[revenue_col].sum(min_count=1).dropna().reset_index()
    trend_fig = px.line(daily, x=date_col, y=revenue_col, markers=True)
    trend_fig.update_traces(line=dict(width=3))
    trend_fig.update_yaxes(tickprefix="$", separatethousands=True)
    trend_fig.update_layout(xaxis_title="Date", yaxis_title="Revenue")
    fig_style(trend_fig)
    st.plotly_chart(trend_fig, use_container_width=True)
    charts_for_export.append(("Revenue Trend", fig_to_png_bytes(trend_fig)))
else:
    st.info("No Date column detected (add a Date column to show revenue trend).")

# Top stores
st.subheader("Top Stores by Revenue (Top 5)")
top_store_fig = None
if store_col:
    store_agg = df.groupby(store_col)[revenue_col].sum(min_count=1).sort_values(ascending=False).head(5).reset_index()
    # One store one color
    top_store_fig = px.bar(
        store_agg,
        y=store_col,
        x=revenue_col,
        color=store_col,
        orientation="h",
        text=revenue_col,
        color_discrete_sequence=TABLEAU10,
    )
    top_store_fig.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
    top_store_fig.update_layout(showlegend=False, xaxis_title="Revenue", yaxis_title="Store")
    top_store_fig.update_xaxes(tickprefix="$", separatethousands=True)
    fig_style(top_store_fig)
    top_store_fig.update_layout(height=320)
    st.plotly_chart(top_store_fig, use_container_width=True)
    charts_for_export.append(("Top Stores by Revenue", fig_to_png_bytes(top_store_fig)))
else:
    st.info("No Store column detected.")

# Store stability: small multiples
st.subheader("Store Stability (Top 5)")
if store_col and date_col:
    tmp = df[[date_col, store_col, revenue_col]].copy()
    tmp = tmp.dropna(subset=[date_col])
    tmp[revenue_col] = safe_to_numeric(tmp[revenue_col])
    daily_store = tmp.groupby([store_col, pd.Grouper(key=date_col, freq="D")])[revenue_col].sum(min_count=1).reset_index()
    top_stores = daily_store.groupby(store_col)[revenue_col].sum().sort_values(ascending=False).head(5).index.tolist()

    # layout 2 columns, last row single
    colsA, colsB = st.columns(2)
    for idx, sname in enumerate(top_stores):
        sub = daily_store[daily_store[store_col] == sname].sort_values(date_col)
        fig = px.line(sub, x=date_col, y=revenue_col, markers=False)
        fig.update_traces(line=dict(width=3))
        fig.update_layout(title=str(sname), xaxis_title="Date", yaxis_title="Revenue", showlegend=False)
        fig.update_yaxes(tickprefix="$", separatethousands=True)
        fig_style(fig)
        fig.update_layout(height=260)
        if idx % 2 == 0:
            colsA.plotly_chart(fig, use_container_width=True)
        else:
            colsB.plotly_chart(fig, use_container_width=True)
        charts_for_export.append((f"Store Trend — {sname}", fig_to_png_bytes(fig)))
else:
    st.info("Add Store + Date columns to show store stability.")

# Pricing Effectiveness (fix alignment)
st.subheader("Pricing Effectiveness")
disc_fig = None
if discount_col:
    tmp = df[[discount_col, revenue_col]].copy()
    tmp[discount_col] = safe_to_numeric(tmp[discount_col])
    tmp[revenue_col] = safe_to_numeric(tmp[revenue_col])
    tmp = tmp.dropna(subset=[discount_col, revenue_col])
    if len(tmp) >= 20:
        tmp["_band"] = discount_band_from_rate(tmp[discount_col]).astype(str)
        # ensure categorical order; drop "nan"
        tmp = tmp[tmp["_band"].isin(DISCOUNT_ORDER)]
        band_avg = tmp.groupby("_band")[revenue_col].mean().reindex(DISCOUNT_ORDER).dropna().reset_index()
        band_avg.columns = ["Discount band", "Average revenue per sale"]
        disc_fig = px.bar(
            band_avg,
            x="Discount band",
            y="Average revenue per sale",
            text="Average revenue per sale",
            color="Discount band",
            color_discrete_sequence=TABLEAU10,
            category_orders={"Discount band": DISCOUNT_ORDER},
        )
        disc_fig.update_traces(texttemplate="%{text:$,.0f}", textposition="outside", cliponaxis=False)
        disc_fig.update_layout(showlegend=False, xaxis_title="Discount band", yaxis_title="Average revenue per sale")
        disc_fig.update_yaxes(tickprefix="$", separatethousands=True)
        fig_style(disc_fig)
        disc_fig.update_layout(height=340)
        st.plotly_chart(disc_fig, use_container_width=True)
        charts_for_export.append(("Average Revenue per Sale by Discount Band", fig_to_png_bytes(disc_fig)))
    else:
        st.info("Not enough discount records to assess pricing effectiveness.")
else:
    st.info("No Discount column detected.")

# -----------------------------
# Further analysis (recommended)
# -----------------------------
st.divider()
st.subheader("Further Analysis (recommended)")

# 1) Revenue mix by Category (top)
if category_col:
    cat = df.groupby(category_col)[revenue_col].sum(min_count=1).sort_values(ascending=False).head(8).reset_index()
    fig = px.bar(cat, x=category_col, y=revenue_col, color=category_col, color_discrete_sequence=TABLEAU10)
    fig.update_layout(showlegend=False, title="Revenue by Category (Top)")
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    fig_style(fig)
    st.plotly_chart(fig, use_container_width=True)
    charts_for_export.append(("Revenue by Category (Top)", fig_to_png_bytes(fig)))
else:
    st.info("Add Category to see revenue mix by category.")

# 2) Revenue mix by Payment Method / Channel proxy
if channel_col:
    ch = df.groupby(channel_col)[revenue_col].sum(min_count=1).sort_values(ascending=False).head(8).reset_index()
    fig = px.bar(ch, x=channel_col, y=revenue_col, color=channel_col, color_discrete_sequence=TABLEAU10)
    fig.update_layout(showlegend=False, title="Revenue by Channel (Top)")
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    fig_style(fig)
    st.plotly_chart(fig, use_container_width=True)
    charts_for_export.append(("Revenue by Channel (Top)", fig_to_png_bytes(fig)))
else:
    st.info("Add Channel to see revenue mix by channel.")

# 3) Volatility by Channel (fix alignment)
if channel_col and date_col:
    tmp = df[[date_col, channel_col, revenue_col]].copy()
    tmp = tmp.dropna(subset=[date_col])
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce", infer_datetime_format=True)
    tmp[revenue_col] = safe_to_numeric(tmp[revenue_col])
    daily_ch = tmp.groupby([channel_col, pd.Grouper(key=date_col, freq="D")])[revenue_col].sum(min_count=1).reset_index()
    cvs = daily_ch.groupby(channel_col)[revenue_col].apply(coeff_var).dropna().sort_values(ascending=False).reset_index()
    cvs.columns = ["Channel", "Volatility score (CV)"]
    fig = px.bar(
        cvs,
        x="Channel",
        y="Volatility score (CV)",
        text="Volatility score (CV)",
        color="Channel",
        color_discrete_sequence=TABLEAU10,
        category_orders={"Channel": cvs["Channel"].tolist()},
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, title="Volatility by Channel (higher = less stable)")
    fig_style(fig)
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)
    charts_for_export.append(("Volatility by Channel", fig_to_png_bytes(fig)))
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

    st.markdown("### Correlation (numeric)")
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(num_cols) >= 3:
        corr = df[num_cols].corr(numeric_only=True)
        corr_fig = px.imshow(corr, text_auto=True, aspect="auto", title="Correlation heatmap (numeric)")
        corr_fig.update_layout(height=460)
        st.plotly_chart(corr_fig, use_container_width=True)
    else:
        st.info("Not enough numeric columns for correlation heatmap.")

# -----------------------------
# Exports
# -----------------------------
st.divider()
st.subheader("Export Executive Brief")

st.caption("PDF includes: Business Summary + Business Insights + selected key charts with short commentary. PPT is a talking deck (one insight per slide).")

col1, col2 = st.columns(2)

pdf_bytes = make_executive_brief_pdf("EC-AI Executive Brief", insights, charts_for_export)
ppt_bytes = make_talking_deck_pptx(insights, charts_for_export)

with col1:
    st.download_button(
        "Download PDF Executive Brief",
        data=pdf_bytes,
        file_name="ecai_executive_brief.pdf",
        mime="application/pdf",
        use_container_width=True
    )

with col2:
    st.download_button(
        "Download PPT Talking Deck (16:9)",
        data=ppt_bytes,
        file_name="ecai_talking_deck.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True
    )
