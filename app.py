# app.py
# EC-AI Insight (MVP) — Upload CSV/XLSX → Executive Dashboard + profile + auto charts + R² + consultant-grade suggestions + exports
# Fixes included:
# 1) StreamlitDuplicateElementId when clicking "Run all 3 analyses" (unique keys for charts)
# 2) Key Insights duplicated sentences (dedupe + better filler logic)
# 3) Tableau-like colorful tones (global palette + per-category mapping)
# 4) Executive Dashboard (top) with 2 rows; 2nd row has 3 charts (no wasted space)
# 5) Reduce label overlap / improve spacing
# 6) Store trend: multi-line, one color per store

import io
import math
import re
import html
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Optional (export)
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# Optional (AI)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="EC-AI Insight (MVP)",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
      :root {
        --ec-font-base: 18px;
        --ec-font-small: 16px;
        --ec-font-h1: 38px;
        --ec-font-h2: 28px;
        --ec-font-h3: 22px;
      }

      html, body, [data-testid="stAppViewContainer"] {
        font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
        font-size: var(--ec-font-base);
        line-height: 1.5;
      }

      .block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; }

      /* Markdown text */
      [data-testid="stMarkdownContainer"] p,
      [data-testid="stMarkdownContainer"] li {
        font-size: var(--ec-font-base);
        line-height: 1.55;
      }

      /* Headings */
      h1 { font-size: var(--ec-font-h1) !important; letter-spacing: -0.3px; }
      h2 { font-size: var(--ec-font-h2) !important; letter-spacing: -0.2px; }
      h3 { font-size: var(--ec-font-h3) !important; letter-spacing: -0.1px; }

      /* Captions */
      .stCaption, [data-testid="stCaptionContainer"] {
        font-size: var(--ec-font-small) !important;
        opacity: 0.9;
      }

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

      /* Executive summary card */
      .ec-summary {
        background: #ffffff;
        border: 1px solid rgba(49,51,63,0.10);
        border-radius: 16px;
        padding: 14px 16px;
        box-shadow: 0 1px 10px rgba(0,0,0,0.05);
        margin: 10px 0 14px 0;
      }
      .ec-summary-title {
        font-size: 22px;
        font-weight: 700;
        margin: 0 0 6px 0;
      }
      .ec-summary-body {
        font-size: calc(var(--ec-font-base) + 2px);
        margin: 0;
      }
      .ec-pill {
        display: inline-block;
        font-size: 12px;
        padding: 4px 10px;
        border-radius: 999px;
        border: 1px solid rgba(49,51,63,0.18);
        margin-right: 8px;
        margin-bottom: 8px;
      }
    
      /* Headings */
      h1, [data-testid="stMarkdownContainer"] h1 { font-size: var(--ec-font-h1) !important; }
      h2, [data-testid="stMarkdownContainer"] h2 { font-size: var(--ec-font-h2) !important; }
      h3, [data-testid="stMarkdownContainer"] h3 { font-size: var(--ec-font-h3) !important; }

      /* Subtitle / caption under title */
      [data-testid="stCaptionContainer"] p {
        font-size: 16px !important;
        color: rgba(49,51,63,0.70) !important;
        margin-top: -6px;
      }

      /* AI report card */
      .ec-report {
        background: #ffffff;
        border: 1px solid rgba(49,51,63,0.10);
        border-radius: 16px;
        padding: 14px 16px;
        box-shadow: 0 1px 10px rgba(0,0,0,0.05);
        font-size: calc(var(--ec-font-base) + 2px);
        line-height: 1.55;
        white-space: pre-wrap;
      }

      /* Make expanders + info text more readable */
      [data-testid="stExpander"] p,
      [data-testid="stExpander"] li {
        font-size: calc(var(--ec-font-base) + 1px) !important;
      }

    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Global Plotly defaults (Tableau-like colorful tones)
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
        return f"{sign}{currency}{x/1e9:.1f}B"
    if x >= 1e6:
        return f"{sign}{currency}{x/1e6:.1f}M"
    if x >= 1e3:
        return f"{sign}{currency}{x/1e3:.1f}K"
    return f"{sign}{currency}{x:.1f}"


def human_num(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    x = float(x)
    if abs(x) >= 1e9:
        return f"{x/1e9:.1f}B"
    if abs(x) >= 1e6:
        return f"{x/1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"{x/1e3:.1f}K"
    return f"{x:.2f}"


def safe_to_datetime(s: pd.Series) -> Optional[pd.Series]:
    try:
        dt = pd.to_datetime(s, errors="coerce", utc=False)
        if dt.notna().mean() >= 0.6:
            return dt
    except Exception:
        pass
    return None


def guess_date_col(df: pd.DataFrame) -> Optional[str]:
    candidates = [c for c in df.columns if re.search(r"(date|dt|time|month|day)", str(c), re.I)]
    for c in candidates:
        dt = safe_to_datetime(df[c])
        if dt is not None:
            return c
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
        r"\brevenue\b", r"\bsales\b", r"\bturnover\b", r"\bincome\b", r"\bgmv\b",
        r"\bnet[_ ]?sales\b", r"\bamount\b"
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


def top_categories(df: pd.DataFrame, dim: str, metric: str, top_n: int = 5) -> List[str]:
    g = df.groupby(dim, dropna=False)[metric].sum(numeric_only=True).sort_values(ascending=False)
    return [str(x) for x in g.head(top_n).index.tolist()]


def calc_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        missing = df[c].isna().mean() * 100
        rows.append({
            "column": c,
            "dtype": str(df[c].dtype),
            "missing_%": round(missing, 1),
            "unique_values": int(df[c].nunique(dropna=True)),
        })
    return pd.DataFrame(rows).sort_values(["missing_%", "unique_values"], ascending=[False, False])


def coverage_indicator(df: pd.DataFrame) -> float:
    total = df.shape[0] * df.shape[1]
    if total == 0:
        return 0.0
    non_missing = int(df.notna().sum().sum())
    return non_missing / total


def avg_missing_indicator(df: pd.DataFrame) -> float:
    if df.shape[1] == 0:
        return 100.0
    return float((df.isna().mean() * 100).mean())


def confidence_indicator(df: pd.DataFrame, numeric_cols: List[str]) -> Tuple[int, str]:
    cov = coverage_indicator(df)  # 0-1
    avg_miss = avg_missing_indicator(df)  # 0-100
    rows = df.shape[0]
    cols = df.shape[1]
    num_count = len(numeric_cols)

    score = 0
    score += min(55, cov * 55)
    score += max(0, 20 - (avg_miss / 100) * 20)
    score += min(15, (num_count / max(1, cols)) * 15)
    score += min(10, math.log10(max(10, rows)) * 2.5)

    score = int(round(min(100, max(0, score))))
    label = "High" if score >= 80 else ("Medium" if score >= 55 else "Low")
    return score, label


def pearson_r_and_r2(df: pd.DataFrame, numeric_cols: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    num = df[numeric_cols].copy()
    corr = num.corr(method="pearson")
    r2 = corr ** 2
    return corr, r2


def r_strength_label(r: float) -> str:
    a = abs(r)
    if a < 0.2:
        return "Weak"
    if a < 0.5:
        return "Moderate"
    if a < 0.8:
        return "Strong"
    return "Very strong"


def r2_strength_label(r2: float) -> str:
    if r2 < 0.04:
        return "Weak"
    if r2 < 0.25:
        return "Moderate"
    if r2 < 0.64:
        return "Strong"
    return "Very strong"


def chart_commentary_bar(top_name: str, top_val: float, metric_name: str) -> str:
    return f"Top segment is **{top_name}** with **{human_money(top_val)}**."


def chart_commentary_trend(metric: str, series: pd.Series) -> str:
    y = series.dropna()
    if len(y) < 2:
        return f"Not enough data points to infer a trend for **{metric}**."
    first, last = float(y.iloc[0]), float(y.iloc[-1])
    if first == 0:
        return f"Trend view for **{metric}** across time."
    change = (last - first) / abs(first)
    direction = "increased" if change > 0 else ("decreased" if change < 0 else "remained stable")
    return f"Overall, **{metric}** {direction} from **{human_num(first)}** to **{human_num(last)}** (approx. {change*100:.1f}%)."


def add_max_point_annotation(fig: go.Figure, x_vals, y_vals, label_prefix="Peak") -> go.Figure:
    try:
        y = np.array(y_vals, dtype=float)
        if len(y) == 0 or np.all(np.isnan(y)):
            return fig
        idx = int(np.nanargmax(y))
        fig.add_annotation(
            x=x_vals[idx],
            y=y_vals[idx],
            text=f"{label_prefix}: {human_money(y_vals[idx])}",
            showarrow=True,
            arrowhead=2,
            yshift=10,
        )
    except Exception:
        pass
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


# ---------- Color & style helpers ----------
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


def unique_bullets(bullets: List[str], max_items: int = 10) -> List[str]:
    seen = set()
    out = []
    for b in bullets:
        key = re.sub(r"\s+", " ", str(b).strip())
        if not key:
            continue
        if key.lower() in seen:
            continue
        seen.add(key.lower())
        out.append(b)
        if len(out) >= max_items:
            break
    return out


# -----------------------------
# AI
# -----------------------------
def get_openai_client() -> Optional["OpenAI"]:
    key = None
    try:
        key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        key = None

    if not key:
        import os
        key = os.getenv("OPENAI_API_KEY")

    if not key or OpenAI is None:
        return None
    return OpenAI(api_key=key)


def build_facts_pack(df: pd.DataFrame, date_col: Optional[str], revenue_col: Optional[str], dims: Dict[str, Optional[str]]) -> Dict:
    facts = {}
    facts["rows"] = int(df.shape[0])
    facts["cols"] = int(df.shape[1])
    facts["coverage_pct"] = round(coverage_indicator(df) * 100, 1)
    facts["avg_missing_pct"] = round(avg_missing_indicator(df), 1)
    facts["date_col"] = date_col
    facts["revenue_col"] = revenue_col
    facts["dims_detected"] = {k: v for k, v in dims.items() if v is not None}

    if date_col:
        dt = safe_to_datetime(df[date_col])
        if dt is not None:
            facts["date_min"] = str(dt.min().date()) if pd.notna(dt.min()) else None
            facts["date_max"] = str(dt.max().date()) if pd.notna(dt.max()) else None

    if revenue_col:
        s = pd.to_numeric(df[revenue_col], errors="coerce")
        facts["revenue_sum"] = float(s.sum(skipna=True))
        facts["revenue_avg"] = float(s.mean(skipna=True))
        facts["revenue_min"] = float(s.min(skipna=True))
        facts["revenue_max"] = float(s.max(skipna=True))

    return facts


def ai_generate_suggestions(facts: Dict) -> List[Dict]:
    fallback = [
        {
            "title": "Revenue and Profit Trends by Core Segments",
            "business_context": "Pinpoint where value is created (and lost) by comparing revenue (and profit if available) across the most important segments.",
            "what_to_do": "Rank segments by total revenue, then examine margin/profit distribution if present. Validate whether outperformance is driven by price, volume, or mix.",
            "expected_insight": "Clear identification of top growth engines vs. underperformers, and whether performance is structural or driven by a few spikes/outliers.",
            "outputs": "Segment leaderboard + trend chart for the top segments.",
            "risks": "Mix effects (product/store/channel) can mask true drivers; confirm with controlled cuts.",
        },
        {
            "title": "Time Trend & Seasonality Scan",
            "business_context": "Understand whether performance is stable, improving, or volatile over time to support planning and promotion timing.",
            "what_to_do": "Aggregate the primary metric by day/week/month. Identify peaks/troughs and relate them to segments (store/channel/category).",
            "expected_insight": "Baseline vs. spikes, plus which segments amplify volatility and which are stable.",
            "outputs": "Total trend + trend by top segments; volatility flags for unusual periods.",
            "risks": "Short time windows can overfit; avoid over-interpreting 1–2 spikes as seasonality.",
        },
        {
            "title": "Discount Effectiveness & Price/Mix Sanity Check",
            "business_context": "Validate whether discounts increase total value (revenue/profit) or erode margin.",
            "what_to_do": "Create discount bands and compare average revenue/profit. Break down by category or channel to control for mix.",
            "expected_insight": "A directional “sweet spot” for discounting and where discounting is likely harmful.",
            "outputs": "Discount-band bar chart with sample sizes + segment breakdown.",
            "risks": "Confounding from campaign timing or product mix; treat as directional until confirmed.",
        },
    ]

    client = get_openai_client()
    if client is None:
        return fallback

    prompt = f"""
You are a top-tier analytics consultant.
Generate EXACTLY 3 "Suggested Next Analyses" for this dataset.
They MUST be data-specific, actionable, and consistent quality.

Rules:
- Use the facts pack as ground truth.
- Avoid generic fluff.
- Each suggestion must have:
  1) title
  2) business_context
  3) what_to_do
  4) expected_insight
  5) outputs
  6) risks
- Keep each field concise but meaningful.
- Return valid JSON list of 3 objects.

Facts pack:
{facts}
"""
    try:
        import json
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Return strictly valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
        )
        txt = resp.choices[0].message.content.strip()
        data = json.loads(txt)

        needed = {"title", "business_context", "what_to_do", "expected_insight", "outputs", "risks"}
        if isinstance(data, list) and len(data) == 3 and all(isinstance(d, dict) and needed.issubset(d.keys()) for d in data):
            return data
        return fallback
    except Exception:
        return fallback


def ai_generate_report(exec_bullets: List[str], insights_bullets: List[str], suggestions: List[Dict]) -> str:
    client = get_openai_client()

    base = []
    base.append("AI Insights Report\n")
    base.append("1) Executive Summary\n" + "\n".join([f"- {b}" for b in exec_bullets]) + "\n")
    base.append("2) Key Insights\n" + "\n".join([f"- {b}" for b in insights_bullets]) + "\n")
    base.append("3) Suggested Next Analyses\n")
    for i, s in enumerate(suggestions, 1):
        base.append(
            f"{i}. {s['title']}\n"
            f"- Business Context: {s['business_context']}\n"
            f"- What to Do: {s['what_to_do']}\n"
            f"- Expected Insight: {s['expected_insight']}\n"
            f"- Outputs: {s['outputs']}\n"
            f"- Risks: {s['risks']}\n"
        )
    fallback_text = "\n".join(base)

    if client is None:
        return fallback_text

    prompt = f"""
Write a concise "AI Insights Report" using the provided bullets and suggested analyses.
- Do NOT add new analyses outside the provided list.
- Tone: consultant-grade, crisp, professional.
- Output as plain text with numbered sections.

Executive Summary bullets:
{exec_bullets}

Key Insights bullets:
{insights_bullets}

Suggested Next Analyses (3 items):
{suggestions}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Write clean plain text. No markdown tables."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return fallback_text


# -----------------------------
# “Run all 3 analyses”
# -----------------------------
@dataclass
class AnalysisOutput:
    title: str
    figure: Optional[go.Figure]
    bullets: List[str]


def run_analysis_1_driver(df: pd.DataFrame, revenue_col: str, dim_a: Optional[str], dim_b: Optional[str]) -> AnalysisOutput:
    title = "1) Revenue driver & segment performance"
    bullets: List[str] = []

    dims = [d for d in [dim_a, dim_b] if d is not None]
    if not dims:
        bullets.append("No segment columns detected; add a categorical field (e.g., Store/Channel/Category) for driver analysis.")
        return AnalysisOutput(title=title, figure=None, bullets=bullets)

    dim = dims[0]
    g = df.groupby(dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(12)

    top_name = str(g.index[0])
    top_val = float(g.iloc[0])

    bullets.append(f"Top segment: **{top_name}** contributes **{human_money(top_val)}** total {revenue_col}.")
    if len(g) >= 2:
        bullets.append(f"Second segment is **{g.index[1]}** at **{human_money(float(g.iloc[1]))}**.")
    bullets.append("Use this to confirm what really drives revenue (and whether performance is concentrated).")

    df_plot = g.reset_index()
    df_plot["Label"] = df_plot[revenue_col].apply(lambda v: human_money(float(v)))
    color_map = stable_color_map([str(x) for x in df_plot[dim].tolist()])

    fig = px.bar(
        df_plot,
        x=dim,
        y=revenue_col,
        color=dim,
        text="Label",
        color_discrete_map=color_map,
        title=f"{revenue_col} by {dim}",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_traces(hovertemplate=f"{dim}: %{{x}}<br>{revenue_col}: %{{y:.2f}}<extra></extra>")
    fig = apply_chart_style(fig, height=420, showlegend=False)
    fig = fix_label_overlap_for_bar(fig)

    return AnalysisOutput(title=title, figure=fig, bullets=bullets)


def run_analysis_2_variability(df: pd.DataFrame, revenue_col: str, dim: Optional[str]) -> AnalysisOutput:
    title = "2) Variability by best cut"
    bullets: List[str] = []
    if dim is None:
        bullets.append("No suitable segment column detected for variability analysis.")
        return AnalysisOutput(title=title, figure=None, bullets=bullets)

    g = df.groupby(dim)[revenue_col].agg(["mean", "std", "count"])
    g["CV"] = g["std"] / g["mean"].replace(0, np.nan)
    g = g.sort_values("CV", ascending=False).head(12)

    top = str(g.index[0])
    top_cv = float(g.iloc[0]["CV"])

    bullets.append(f"Most volatile segment: **{top}** (CV={top_cv:.2f}).")
    bullets.append("Higher CV means revenue is less predictable relative to its average size.")
    bullets.append("Use this to find segments that need deeper diagnosis (mix, pricing, promotions, stockouts).")

    df_plot = g.reset_index().rename(columns={"CV": "CV (Coefficient of Variation)"})
    df_plot["Label"] = df_plot["CV (Coefficient of Variation)"].apply(lambda v: f"{float(v):.2f}" if pd.notna(v) else "-")

    color_map = stable_color_map([str(x) for x in df_plot[dim].tolist()])
    fig = px.bar(
        df_plot,
        x=dim,
        y="CV (Coefficient of Variation)",
        color=dim,
        text="Label",
        color_discrete_map=color_map,
        title=f"Revenue volatility (CV) by {dim}",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig = apply_chart_style(fig, height=420, showlegend=False)
    fig = fix_label_overlap_for_bar(fig)

    return AnalysisOutput(title=title, figure=fig, bullets=bullets)


def run_analysis_3_discount_simple(df: pd.DataFrame, revenue_col: str, discount_col: Optional[str]) -> AnalysisOutput:
    title = "3) Discount effectiveness (simple)"
    bullets: List[str] = []
    if discount_col is None:
        bullets.append("No discount-like numeric column detected (e.g., Discount, Discount_Rate).")
        return AnalysisOutput(title=title, figure=None, bullets=bullets)

    s = pd.to_numeric(df[discount_col], errors="coerce")
    if s.notna().sum() < 10:
        bullets.append("Discount column has too few numeric values to analyze.")
        return AnalysisOutput(title=title, figure=None, bullets=bullets)

    disc = s.copy()
    if disc.max(skipna=True) > 2:  # likely 0-100
        disc = disc / 100.0

    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    bins = [-np.inf, 0.02, 0.05, 0.10, 0.15, 0.20, np.inf]
    band = pd.cut(disc, bins=bins, labels=labels)

    tmp = df[[revenue_col]].copy()
    tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
    tmp["Discount_Band"] = band.astype(str)

    g = tmp.groupby("Discount_Band")[revenue_col].agg(["mean", "count"]).reset_index()
    g["Discount_Band"] = pd.Categorical(g["Discount_Band"], categories=labels, ordered=True)
    g = g.sort_values("Discount_Band")

    # keep only bands with enough samples
    g = g[g["count"] >= 5].copy()
    if g.empty:
        bullets.append("Not enough samples per discount band to draw a directional view (need >=5 records per band).")
        return AnalysisOutput(title=title, figure=None, bullets=bullets)

    best = g.loc[g["mean"].idxmax()]
    worst = g.loc[g["mean"].idxmin()]

    bullets.append(f"Shows **average {revenue_col} per record** by discount band (directional).")
    bullets.append(f"Best band: **{best['Discount_Band']}** (avg {human_money(float(best['mean']))}, n={int(best['count'])}).")
    bullets.append(f"Weakest band: **{worst['Discount_Band']}** (avg {human_money(float(worst['mean']))}, n={int(worst['count'])}).")
    bullets.append("If this matters, confirm by controlling for Store/Channel/Category (to avoid mix effects).")

    df_plot = g.rename(columns={"mean": "AvgRevenue"})
    df_plot["Label"] = df_plot["AvgRevenue"].apply(lambda v: human_money(float(v)))

    band_colors = stable_color_map([str(x) for x in df_plot["Discount_Band"].tolist()])
    fig = px.bar(
        df_plot,
        x="Discount_Band",
        y="AvgRevenue",
        color="Discount_Band",
        text="Label",
        color_discrete_map=band_colors,
        title=f"Average {revenue_col} per record by Discount Band",
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        customdata=df_plot["count"].values,
        hovertemplate="Band: %{x}<br>Avg: %{y:.2f}<br>n=%{customdata}<extra></extra>",
    )
    fig = apply_chart_style(fig, height=420, showlegend=False)
    fig = fix_label_overlap_for_bar(fig)

    return AnalysisOutput(title=title, figure=fig, bullets=bullets)


def build_pdf(exec_bullets: List[str], insights_bullets: List[str], suggestions: List[Dict],
              charts: List[Tuple[str, Optional[bytes]]], analyses: List[AnalysisOutput], include_analyses: bool) -> bytes:
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

    def write_bullets(bullets, y, font_size=11, max_lines=36):
        c.setFont("Helvetica", font_size)
        lines = 0
        for b in bullets:
            wrapped = wrap_text(f"• {b}", 95)
            for w in wrapped:
                if lines >= max_lines:
                    return y, True
                c.drawString(0.85 * inch, y, w)
                y -= 0.22 * inch
                lines += 1
        return y, False

    y = H - 0.9 * inch
    y = write_title("EC-AI Executive Brief", y)

    c.setFont("Helvetica", 11)
    c.drawString(0.8 * inch, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 0.35 * inch

    y = write_title("Executive Summary", y)
    y, overflow = write_bullets(exec_bullets, y)
    if overflow:
        c.showPage()
        y = H - 0.9 * inch

    y -= 0.2 * inch
    y = write_title("Key Insights", y)
    y, overflow = write_bullets(insights_bullets, y)
    if overflow:
        c.showPage()
        y = H - 0.9 * inch

    y -= 0.2 * inch
    y = write_title("Suggested Next Analyses", y)
    sug_lines = []
    for i, s in enumerate(suggestions, 1):
        sug_lines.append(f"{i}. {s['title']}")
        sug_lines.append(f"Business Context: {s['business_context']}")
        sug_lines.append(f"What to Do: {s['what_to_do']}")
        sug_lines.append(f"Expected Insight: {s['expected_insight']}")
        sug_lines.append(f"Outputs: {s['outputs']}")
        sug_lines.append(f"Risks: {s['risks']}")
    y, overflow = write_bullets(sug_lines, y, font_size=10, max_lines=40)
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

    if include_analyses and analyses:
        for a in analyses:
            c.showPage()
            y = H - 0.9 * inch
            y = write_title(a.title, y)
            y, _ = write_bullets(a.bullets, y, font_size=10, max_lines=30)
            if a.figure is not None:
                img = fig_to_png_bytes(a.figure)
                if img:
                    from reportlab.lib.utils import ImageReader
                    ir = ImageReader(io.BytesIO(img))
                    img_w = W - 1.6 * inch
                    c.drawImage(ir, 0.8 * inch, 1.2 * inch, width=img_w, height=4.8 * inch, preserveAspectRatio=True, anchor="n")

    c.save()
    buff.seek(0)
    return buff.getvalue()


def build_pptx(exec_bullets: List[str], insights_bullets: List[str], suggestions: List[Dict],
               charts: List[Tuple[str, Optional[bytes]]], analyses: List[AnalysisOutput], include_analyses: bool) -> bytes:
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
    add_bullets_to_slide(slide, "Executive Summary", exec_bullets)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bullets_to_slide(slide, "Key Insights", insights_bullets)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sug_bullets = []
    for i, s in enumerate(suggestions, 1):
        sug_bullets.append(f"{i}. {s['title']}")
        sug_bullets.append(f"Context: {s['business_context']}")
        sug_bullets.append(f"What to do: {s['what_to_do']}")
        sug_bullets.append(f"Expected: {s['expected_insight']}")
        sug_bullets.append(f"Outputs: {s['outputs']}")
        sug_bullets.append(f"Risks: {s['risks']}")
        sug_bullets.append("")
    add_bullets_to_slide(slide, "Suggested Next Analyses", sug_bullets[:35])

    for title, img in charts:
        if img:
            add_image_slide(prs, title, img)

    if include_analyses and analyses:
        for a in analyses:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            add_bullets_to_slide(slide, a.title, a.bullets[:12])
            if a.figure is not None:
                img = fig_to_png_bytes(a.figure)
                if img:
                    add_image_slide(prs, f"{a.title} — chart", img)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.getvalue()


# -----------------------------
# UI
# -----------------------------
st.title("EC-AI Insight (MVP)")
st.caption("Turning Data Into Intelligence — upload CSV or Excel to get instant profiling, Tableau-like charts, R² relationships, and insights.")


# -----------------------------
# Product Executive Summary (Owner-first)
# -----------------------------
st.markdown(
    """
    <div class="ec-summary">
      <div class="ec-summary-title">Executive Summary</div>
      <div class="ec-summary-body">
        EC-AI Insight turns <b>retail sales / transaction data</b> into clear, decision-ready insights in minutes.
        Upload your dataset and instantly see (1) the revenue trend, (2) what truly drives sales (top stores/products/channels),
        and (3) where revenue is concentrated — so you can act without building dashboards.
      </div>
      <div style="margin-top:10px;">
        <span class="ec-pill">Scope: Sales / Transactions only</span>
        <span class="ec-pill">Audience: Owners & Sales Leaders</span>
        <span class="ec-pill">Goal: Answers → Decisions</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.info("MVP scope for testing: **Retail sales / transaction data only** (e.g., Date, Store, Product/Category, Channel, Revenue).", icon="✅")

uploaded = st.file_uploader("Upload a dataset", type=["csv", "xlsx", "xls"])
if uploaded is None:
    st.info("Upload a CSV/XLSX to begin.")
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

date_col = guess_date_col(df)
if date_col:
    dt = safe_to_datetime(df[date_col])
    if dt is not None:
        df[date_col] = dt.dt.tz_localize(None)

numeric_cols = [c for c in df.columns if is_numeric_series(df[c])]
cat_cols = [c for c in df.columns if is_categorical_series(df[c]) and c != date_col]

revenue_col = pick_revenue_like(df) or (numeric_cols[0] if numeric_cols else None)
cost_col = pick_cost_like(df)

# -----------------------------
# Sales-only guardrails (MVP testing scope)
# -----------------------------
if revenue_col is None:
    st.error("This MVP is for **sales/transaction** datasets. Please include a Revenue/Sales column (e.g., 'Revenue', 'Sales', 'Amount').")
    st.stop()
if date_col is None:
    st.error("This MVP is for **sales/transaction** datasets with a Date column (e.g., 'Date', 'Order Date', 'Transaction Date').")
    st.stop()

dims = {
    "country": pick_dim_like(df, ["country", "region", "market", "geo"]),
    "store": pick_dim_like(df, ["store", "branch", "location", "outlet"]),
    "channel": pick_dim_like(df, ["channel", "source"]),
    "category": pick_dim_like(df, ["category", "product", "sku", "segment", "industry"]),
    "payment": pick_dim_like(df, ["payment", "pay", "method", "card"]),
    "team": pick_dim_like(df, ["team", "sales_rep", "owner", "rm", "relationship", "agent"]),
}

discount_col = None
for c in df.columns:
    if re.search(r"discount|promo|rebate", str(c), re.I) and is_numeric_series(df[c]):
        discount_col = c
        break

cov = coverage_indicator(df)
avg_miss = avg_missing_indicator(df)
conf_score, conf_label = confidence_indicator(df, numeric_cols)

facts = build_facts_pack(df, date_col, revenue_col, dims)

# -----------------------------
# Executive Dashboard (Top) — sexy Tableau-ish layout
# -----------------------------
st.markdown("## Executive Dashboard")

charts_for_export: List[Tuple[str, Optional[bytes]]] = []

if revenue_col:
    srev = pd.to_numeric(df[revenue_col], errors="coerce")
    total_rev = float(srev.sum(skipna=True))
    avg_rev = float(srev.mean(skipna=True))
    med_rev = float(srev.median(skipna=True))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Revenue", human_money(total_rev))
    k2.metric("Avg / Record", human_money(avg_rev))
    k3.metric("Median / Record", human_money(med_rev))
    k4.metric("Rows", f"{df.shape[0]:,}")

    r1c1, r1c2 = st.columns([1.3, 1.0])

    with r1c1:
        if date_col:
            tmp = df[[date_col, revenue_col]].copy()
            tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
            ts_total = tmp.groupby(date_col)[revenue_col].sum().sort_index()

            fig_total = px.line(
                ts_total.reset_index(),
                x=date_col,
                y=revenue_col,
                markers=True,
                title=f"{revenue_col} trend (Total)",
            )
            fig_total = add_max_point_annotation(fig_total, ts_total.index, ts_total.values, label_prefix="Peak")
            fig_total = apply_chart_style(fig_total, height=340, showlegend=False)
            fig_total.update_xaxes(automargin=True)
            fig_total.update_yaxes(automargin=True)
            st.plotly_chart(fig_total, use_container_width=True, key="exec_total_trend")
            charts_for_export.append((f"{revenue_col} trend (Total)", fig_to_png_bytes(fig_total)))

    with r1c2:
        store_dim = dims.get("store")
        if store_dim and store_dim in df.columns:
            g = df.groupby(store_dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(5)
            color_map = stable_color_map([str(x) for x in g.index.tolist()])

            fig_store_bar = px.bar(
                g.reset_index(),
                x=store_dim,
                y=revenue_col,
                color=store_dim,
                color_discrete_map=color_map,
                title=f"{revenue_col} by Store (Top 5)",
            )
            fig_store_bar.update_traces(text=[human_money(v) for v in g.values])
            fig_store_bar = apply_chart_style(fig_store_bar, height=340, showlegend=False)
            fig_store_bar = fix_label_overlap_for_bar(fig_store_bar)
            st.plotly_chart(fig_store_bar, use_container_width=True, key="exec_store_bar")
            charts_for_export.append((f"{revenue_col} by Store (Top 5)", fig_to_png_bytes(fig_store_bar)))

    # Row 2: three charts
    r2c1, r2c2, r2c3 = st.columns(3)

    with r2c1:
        ch_dim = dims.get("channel")
        if ch_dim and ch_dim in df.columns:
            g = df.groupby(ch_dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(8)
            colors = stable_color_map([str(x) for x in g.index.tolist()])
            fig_donut = px.pie(
                g.reset_index(),
                names=ch_dim,
                values=revenue_col,
                hole=0.58,
                color=ch_dim,
                color_discrete_map=colors,
                title="Revenue Mix (Channel)",
            )
            fig_donut = apply_chart_style(fig_donut, height=380, showlegend=True)
            fig_donut.update_layout(
                legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="left", x=0, title=None),
                margin=dict(l=10, r=10, t=60, b=110),
            )
            st.plotly_chart(fig_donut, use_container_width=True, key="exec_donut_channel")
            charts_for_export.append(("Revenue Mix (Channel)", fig_to_png_bytes(fig_donut)))

    with r2c2:
        cat_dim = dims.get("category")
        if cat_dim and cat_dim in df.columns:
            g = df.groupby(cat_dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(8)
            colors = stable_color_map([str(x) for x in g.index.tolist()])
            fig_donut2 = px.pie(
                g.reset_index(),
                names=cat_dim,
                values=revenue_col,
                hole=0.58,
                color=cat_dim,
                color_discrete_map=colors,
                title="Revenue Mix (Category)",
            )
            fig_donut2 = apply_chart_style(fig_donut2, height=380, showlegend=True)
            fig_donut2.update_layout(
                legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="left", x=0, title=None),
                margin=dict(l=10, r=10, t=60, b=110),
            )
            st.plotly_chart(fig_donut2, use_container_width=True, key="exec_donut_category")
            charts_for_export.append(("Revenue Mix (Category)", fig_to_png_bytes(fig_donut2)))

    with r2c3:
        dim3 = dims.get("payment") or dims.get("country")
        if dim3 and dim3 in df.columns:
            g = df.groupby(dim3)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(8)
            colors = stable_color_map([str(x) for x in g.index.tolist()])
            fig_donut3 = px.pie(
                g.reset_index(),
                names=dim3,
                values=revenue_col,
                hole=0.58,
                color=dim3,
                color_discrete_map=colors,
                title=f"Revenue Mix ({dim3})",
            )
            fig_donut3 = apply_chart_style(fig_donut3, height=380, showlegend=True)
            fig_donut3.update_layout(
                legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="left", x=0, title=None),
                margin=dict(l=10, r=10, t=60, b=110),
            )
            st.plotly_chart(fig_donut3, use_container_width=True, key="exec_donut_third")
            charts_for_export.append((f"Revenue Mix ({dim3})", fig_to_png_bytes(fig_donut3)))

st.divider()

# -----------------------------
# Executive Summary + Key Insights
# -----------------------------
st.subheader("Executive Summary")

exec_bullets: List[str] = []
exec_bullets.append(f"Dataset has **{df.shape[0]} rows** and **{df.shape[1]} columns**; coverage is **{cov*100:.1f}%** with average missing **{avg_miss:.1f}%**.")
if date_col:
    exec_bullets.append(f"Time field detected: **{date_col}** (useful for trend analysis).")
if revenue_col:
    s = pd.to_numeric(df[revenue_col], errors="coerce")
    exec_bullets.append(f"Primary metric detected: **{revenue_col}** — total **{human_money(s.sum())}**, average **{human_money(s.mean())}**.")
if len(numeric_cols) >= 2:
    corr0, r20 = pearson_r_and_r2(df, numeric_cols)
    r2u = r20.where(~np.eye(r20.shape[0], dtype=bool))
    max_pair = r2u.stack().sort_values(ascending=False).head(1)
    if len(max_pair) == 1:
        (a, b), v = max_pair.index[0], float(max_pair.iloc[0])
        r_val = float(corr0.loc[a, b])
        exec_bullets.append(f"Strongest numeric relationship: **{a} ↔ {b}** with **R²={v:.2f}** (R={r_val:.2f}, {r_strength_label(r_val)}).")
exec_bullets.append(f"Confidence indicator is **{conf_score} ({conf_label})** based on coverage, missingness, and numeric signal availability.")
exec_bullets.append("Next: review key business cuts + trends, then use the suggested analyses for deeper dives.")

for b in exec_bullets:
    st.write("• " + b)

st.divider()

st.subheader("Key Insights")

insights_bullets: List[str] = []
if revenue_col:
    best_dim = None
    best_gap = 0
    best_top = None
    for k in ["store", "channel", "category", "country", "payment", "team"]:
        d = dims.get(k)
        if d and d in df.columns:
            g = df.groupby(d)[revenue_col].sum(numeric_only=True).sort_values(ascending=False)
            if len(g) >= 2:
                gap = float(g.iloc[0] - g.iloc[1])
            elif len(g) == 1:
                gap = float(g.iloc[0])
            else:
                continue
            if gap > best_gap:
                best_gap = gap
                best_dim = d
                best_top = (str(g.index[0]), float(g.iloc[0]))
    if best_dim and best_top:
        insights_bullets.append(f"Top segment by {revenue_col}: **{best_top[0]}** (by **{best_dim}**) at **{human_money(best_top[1])}** total.")

    if date_col:
        tmp = df[[date_col, revenue_col]].copy()
        tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
        ts = tmp.groupby(date_col)[revenue_col].sum().sort_index()
        insights_bullets.append(chart_commentary_trend(revenue_col, ts))
        if len(ts) >= 3 and ts.notna().sum() >= 3:
            peak_date = ts.idxmax()
            insights_bullets.append(f"Peak {revenue_col} occurs on **{peak_date.date()}** at **{human_money(float(ts.max()))}**.")

    if cost_col:
        tmp = df[[revenue_col, cost_col]].copy()
        tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
        tmp[cost_col] = pd.to_numeric(tmp[cost_col], errors="coerce")
        m = (tmp[revenue_col] - tmp[cost_col]).mean(skipna=True)
        insights_bullets.append(f"Estimated average (Revenue − Cost) using **{revenue_col}** and **{cost_col}** is **{human_money(m)}** per record (directional).")

# Filler bullets: take unique numeric cols (no repeats), skip revenue col
filler = []
if numeric_cols:
    for c in numeric_cols:
        if c == revenue_col:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().sum() < 5:
            continue
        filler.append(f"**{c}** ranges from **{human_num(s.min())}** to **{human_num(s.max())}** (n={int(s.notna().sum())}).")
    insights_bullets.extend(filler)

insights_bullets = unique_bullets(insights_bullets, max_items=10)
for b in insights_bullets:
    st.write("• " + b)

with st.expander("How correlation (R) and R² are interpreted (in this app)"):
    st.markdown(
        """
**What the chart shows**
- **R (Pearson correlation)** ranges from **-1 to +1** and keeps direction (positive/negative).
- **R² (R square)** is **R squared**, ranges from **0 to 1**, and shows **strength only** (direction removed).

**Why we use R² by default**
- It is easier for business users: “how much of the variation is explained.”

**Strength labels (heuristic)**
- **R² < 0.04** → Weak ( <4% )
- **0.04–0.25** → Moderate (4–25%)
- **0.25–0.64** → Strong (25–64%)
- **≥0.64** → Very strong (≥64%)
"""
    )

# -----------------------------
# Preview + profile
# -----------------------------
st.divider()

with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(50), use_container_width=True)

st.divider()

st.subheader("Data profile")
profile = calc_profile(df)
st.dataframe(profile, use_container_width=True)

st.subheader("Indicators")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Coverage", f"{cov*100:.0f}%")
c2.metric("Avg Missing", f"{avg_miss:.1f}%")
c3.metric("Confidence", f"{conf_score} ({conf_label})")
strong_pairs = 0
if len(numeric_cols) >= 2:
    _, r2x = pearson_r_and_r2(df, numeric_cols)
    r2u = r2x.where(~np.eye(r2x.shape[0], dtype=bool))
    strong_pairs = int((r2u.stack() >= 0.64).sum())
c4.metric("Strong R² pairs", f"{strong_pairs}")

st.caption(
    "Logic: Coverage = non-missing cells / total cells. Avg Missing = average missing% across columns. "
    "Confidence is a heuristic score combining coverage, missingness, dataset size, and numeric signal."
)

# -----------------------------
# Quick Exploration
# -----------------------------
st.divider()

st.subheader("Trends")

if date_col is None or revenue_col is None:
    st.info("Trend charts require a Date-like field and a primary metric (e.g., Revenue/Sales).")
else:
    tmp = df[[date_col, revenue_col]].copy()
    tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
    ts_total = tmp.groupby(date_col)[revenue_col].sum().sort_index()

    fig_total2 = px.line(ts_total.reset_index(), x=date_col, y=revenue_col, markers=True, title=f"{revenue_col} trend (total)")
    fig_total2 = add_max_point_annotation(fig_total2, ts_total.index, ts_total.values, label_prefix="Peak")
    fig_total2 = apply_chart_style(fig_total2, height=420, showlegend=False)
    fig_total2.update_xaxes(automargin=True)
    fig_total2.update_yaxes(automargin=True)
    st.caption("Commentary: " + chart_commentary_trend(revenue_col, ts_total))
    st.plotly_chart(fig_total2, use_container_width=True, key="trend_total_main")
    charts_for_export.append((f"{revenue_col} trend (total)", fig_to_png_bytes(fig_total2)))

    # Trend by Store: multi-line, one color per store (top 5)
    store_dim = dims.get("store")
    if store_dim and store_dim in df.columns:
        tmp2 = df[[date_col, store_dim, revenue_col]].copy()
        tmp2[revenue_col] = pd.to_numeric(tmp2[revenue_col], errors="coerce")
        tmp2[store_dim] = tmp2[store_dim].astype(str)

        top_stores = (
            tmp2.groupby(store_dim)[revenue_col].sum()
            .sort_values(ascending=False)
            .head(5)
            .index.tolist()
        )
        tmp2 = tmp2[tmp2[store_dim].isin(top_stores)]
        ts_store = tmp2.groupby([date_col, store_dim])[revenue_col].sum().reset_index().sort_values(date_col)
        store_colors = stable_color_map(top_stores)

        # Small multiples: one store per chart (cleaner than a multi-line chart)
        st.markdown(f"**{revenue_col} trend by Store (Top 5)**")
        cols = st.columns(2)
        for i, store in enumerate(top_stores):
            dff = ts_store[ts_store[store_dim] == store]
            fig_s = px.line(
                dff,
                x=date_col,
                y=revenue_col,
                markers=False,
                title=str(store),
            )
            fig_s = apply_chart_style(fig_s, height=260, showlegend=False)
            fig_s.update_layout(margin=dict(l=10, r=10, t=50, b=10))
            with cols[i % 2]:
                st.plotly_chart(fig_s, use_container_width=True, key=f"trend_store_{i}_{store}")
            charts_for_export.append((f"{revenue_col} trend — {store}", fig_to_png_bytes(fig_s)))

# -----------------------------
# Correlation (R² default)
# -----------------------------

st.subheader("Key business cuts")

if revenue_col is None:
    st.warning("No revenue/sales-like numeric metric detected — key business cuts will be limited.")
else:
    candidates = [dims.get("store"), dims.get("channel"), dims.get("category"), dims.get("country"), dims.get("payment"), dims.get("team")]
    candidates = [c for c in candidates if c is not None and c in df.columns]
    cols2 = st.columns(2)

    for idx, d in enumerate(candidates[:2]):
        g = df.groupby(d)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(12)
        top_name = str(g.index[0])
        top_val = float(g.iloc[0])

        color_map = stable_color_map([str(x) for x in g.index.tolist()])
        fig = px.bar(
            g.reset_index(),
            x=d,
            y=revenue_col,
            color=d,
            color_discrete_map=color_map,
            title=f"{revenue_col} by {d}",
        )
        fig.update_traces(
            text=[human_money(v) for v in g.values],
            hovertemplate=f"{d}: %{{x}}<br>{revenue_col}: %{{y:.2f}}<extra></extra>",
        )
        fig = apply_chart_style(fig, height=420, showlegend=False)
        fig = fix_label_overlap_for_bar(fig)

        with cols2[idx % 2]:
            st.caption(f"Commentary: {chart_commentary_bar(top_name, top_val, revenue_col)}")
            st.plotly_chart(fig, use_container_width=True, key=f"keycut_{idx}_{d}")

        charts_for_export.append((f"{revenue_col} by {d}", fig_to_png_bytes(fig)))

# -----------------------------
# Trends (auto)
# -----------------------------

st.subheader("Correlation")

if len(numeric_cols) < 2:
    st.info("Need at least 2 numeric columns to compute correlations.")
else:
    corr, r2 = pearson_r_and_r2(df, numeric_cols)

    x = list(r2.columns)
    y = list(r2.index)
    z = r2.values

    hover = []
    for yi in y:
        row = []
        for xi in x:
            r = float(corr.loc[yi, xi])
            rr2 = float(r2.loc[yi, xi])
            row.append(f"{yi} vs {xi}<br>R²={rr2:.2f} ({r2_strength_label(rr2)})<br>R={r:.2f} ({r_strength_label(r)})")
        hover.append(row)

    fig_corr = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=np.round(z, 2),
            texttemplate="%{text}",
            hoverinfo="text",
            hovertext=hover,
            colorbar=dict(title="R²"),
        )
    )
    fig_corr.update_layout(title="R² relationships (Pearson)", height=520, margin=dict(l=10, r=10, t=60, b=10))
    st.caption("Commentary: R² shows strength (0–1). Higher R² means stronger relationship; direction is not shown (see tooltip for R).")
    st.plotly_chart(fig_corr, use_container_width=True, key="corr_r2_heatmap")
    charts_for_export.append(("R² relationships (Pearson)", fig_to_png_bytes(fig_corr)))

    r2u = r2.where(~np.eye(r2.shape[0], dtype=bool))
    pairs = r2u.stack().sort_values(ascending=False).head(6)
    st.markdown("**Key R² relationships (top pairs)**")
    for (a, b), v in pairs.items():
        r = float(corr.loc[a, b])
        st.write(f"• **{a} ↔ {b}**: R²={v:.2f} ({r2_strength_label(v)}), R={r:.2f} ({r_strength_label(r)})")

# -----------------------------
# Suggested Next Analyses + Run all 3 analyses
# -----------------------------

with st.expander("More charts (optional) — quick exploration", expanded=False):
    st.subheader("Quick exploration")

    if not numeric_cols:
        st.warning("No numeric columns found — quick exploration needs numeric measures.")
    else:
        default_numeric = revenue_col if revenue_col in numeric_cols else numeric_cols[0]
        default_cat = dims.get("store") or dims.get("channel") or dims.get("category") or (cat_cols[0] if cat_cols else None)

        left, right = st.columns(2)

        with left:
            num_col = st.selectbox("Numeric column", numeric_cols, index=numeric_cols.index(default_numeric))
            s = pd.to_numeric(df[num_col], errors="coerce")
            fig_hist = px.histogram(s.dropna(), nbins=12, title=f"Distribution of {num_col}")
            fig_hist = apply_chart_style(fig_hist, height=360, showlegend=False)  # fixes overlapping legend
            fig_hist.update_layout(margin=dict(l=10, r=10, t=60, b=10))
            med = float(s.median(skipna=True)) if s.notna().sum() else np.nan
            p90 = float(s.quantile(0.9)) if s.notna().sum() else np.nan
            st.caption(f"Commentary: median is **{human_num(med)}**; 90th percentile is **{human_num(p90)}** (skew check).")
            st.plotly_chart(fig_hist, use_container_width=True, key="quick_hist")

        with right:
            if default_cat is None:
                st.info("No categorical columns detected for a segment cut.")
            else:
                cat_choices = [c for c in cat_cols]
                if not cat_choices:
                    st.info("No categorical columns detected for a segment cut.")
                else:
                    cat_col = st.selectbox(
                        "Categorical column",
                        cat_choices,
                        index=cat_choices.index(default_cat) if default_cat in cat_choices else 0
                    )
                    g = df.groupby(cat_col)[num_col].count().sort_values(ascending=False).head(12)
                    color_map = stable_color_map([str(x) for x in g.index.tolist()])
                    fig_bar = px.bar(
                        g.reset_index(),
                        x=cat_col,
                        y=num_col,
                        color=cat_col,
                        color_discrete_map=color_map,
                        title=f"Record count by {cat_col}",
                    )
                    fig_bar.update_traces(text=g.values)
                    fig_bar = apply_chart_style(fig_bar, height=360, showlegend=False)
                    fig_bar = fix_label_overlap_for_bar(fig_bar)
                    st.caption(f"Commentary: top category by volume is **{g.index[0]}** with **{int(g.iloc[0])} records**.")
                    st.plotly_chart(fig_bar, use_container_width=True, key="quick_count_bar")

    # -----------------------------
    # Key business cuts (auto)
    # -----------------------------

st.divider()

st.subheader("Suggested Next Analyses")

# Keep AI suggestions for later (also used in the AI Insights report),
# but present a simpler, owner-first view here.
suggestions = ai_generate_suggestions(facts)

st.markdown("Pick one question below — each generates a chart + a short explanation (no jargon).")

cS1, cS2, cS3 = st.columns(3)
with cS1:
    st.markdown("#### 1) What drives my revenue?")
    st.write("• Compare revenue across **Store / Channel / Category**.")
    st.write("• See the **Top contributors** (focus areas).")
with cS2:
    st.markdown("#### 2) Where is performance unstable?")
    st.write("• Find segments with **high volatility** (less predictable).")
    st.write("• Prioritize what needs diagnosis.")
with cS3:
    st.markdown("#### 3) Are discounts helping or hurting?")
    st.write("• Compare **average revenue per order** by discount band.")
    st.write("• Identify a **best band** to validate further.")

st.markdown(
    "<div class='ec-flow'>"
    "Data → Charts → Decision"
    "</div>",
    unsafe_allow_html=True,
)

with st.expander("AI suggestions (advanced)"):
    for i, s in enumerate(suggestions, 1):
        st.markdown(f"**{i}. {s['title']}**")
        st.write(f"• {s['expected_insight']}")
        st.write(f"• Output: {s['outputs']}")
        st.write(f"• Notes: {s['risks']}")
        st.write("")

st.subheader("Deeper dives (one click)")
analyses_outputs: List[AnalysisOutput] = st.session_state.get("analyses_outputs", [])
ran = st.session_state.get("ran_analyses", False)

colA, colB = st.columns([1, 2])
with colA:
    run_btn = st.button("Run all 3 analyses", type="primary")
with colB:
    st.caption("One click generates charts + brief commentary. (Unique chart keys prevent Streamlit duplicate element errors.)")

if run_btn:
    analyses_outputs = []
    if revenue_col:
        dim1 = dims.get("store") or dims.get("channel") or dims.get("category")
        dim2 = dims.get("channel") or dims.get("store") or dims.get("category")
        analyses_outputs.append(run_analysis_1_driver(df, revenue_col, dim1, dim2))
        analyses_outputs.append(run_analysis_2_variability(df, revenue_col, dim2))
        analyses_outputs.append(run_analysis_3_discount_simple(df, revenue_col, discount_col))
    else:
        analyses_outputs.append(AnalysisOutput("1) Revenue driver & segment performance", None, ["No revenue-like metric detected."]))
        analyses_outputs.append(AnalysisOutput("2) Variability by best cut", None, ["No revenue-like metric detected."]))
        analyses_outputs.append(AnalysisOutput("3) Discount effectiveness (simple)", None, ["No revenue-like metric detected."]))

    st.session_state["analyses_outputs"] = analyses_outputs
    st.session_state["ran_analyses"] = True
    ran = True

if ran and analyses_outputs:
    for i, a in enumerate(analyses_outputs):
        st.markdown(f"### {a.title}")
        for b in a.bullets:
            st.write("• " + b)
        if a.figure is not None:
            # CRITICAL FIX: unique keys prevent StreamlitDuplicateElementId
            st.plotly_chart(a.figure, use_container_width=True, key=f"analysis_chart_{i}_{a.title}")
            charts_for_export.append((a.title, fig_to_png_bytes(a.figure)))
        st.divider()

# -----------------------------
# AI Insights Report
# -----------------------------
st.subheader("AI Insights Report")
report_text = ai_generate_report(exec_bullets[:10], insights_bullets[:10], suggestions)
# Render as a readable executive brief (not monospace)
st.markdown(f'<div class="ec-report">{html.escape(report_text)}</div>', unsafe_allow_html=True)

# -----------------------------
# Export
# -----------------------------
st.subheader("Export")
st.caption("Note: This app is for demo/testing. Please avoid uploading confidential or regulated data.")

include_analyses = bool(st.session_state.get("ran_analyses", False))

cE1, cE2, cE3, cE4 = st.columns(4)

with cE1:
    if st.button("Build Executive Brief (PDF)"):
        pdf_bytes = build_pdf(exec_bullets[:10], insights_bullets[:10], suggestions, charts_for_export, analyses_outputs, include_analyses=False)
        st.download_button("Download Executive Brief (PDF)", data=pdf_bytes, file_name="ecai_executive_brief.pdf", mime="application/pdf")

with cE2:
    if st.button("Build Slides (PPTX)"):
        ppt_bytes = build_pptx(exec_bullets[:10], insights_bullets[:10], suggestions, charts_for_export, analyses_outputs, include_analyses=False)
        st.download_button("Download Slides (PPTX)", data=ppt_bytes, file_name="ecai_insight_slides.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

with cE3:
    if st.button("Build Full Pack (PDF)", disabled=not include_analyses):
        pdf_bytes = build_pdf(exec_bullets[:10], insights_bullets[:10], suggestions, charts_for_export, analyses_outputs, include_analyses=True)
        st.download_button("Download Full Pack (PDF)", data=pdf_bytes, file_name="ecai_full_pack.pdf", mime="application/pdf")

with cE4:
    if st.button("Build Full Pack (PPTX)", disabled=not include_analyses):
        ppt_bytes = build_pptx(exec_bullets[:10], insights_bullets[:10], suggestions, charts_for_export, analyses_outputs, include_analyses=True)
        st.download_button("Download Full Pack (PPTX)", data=ppt_bytes, file_name="ecai_full_pack.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

with st.expander("Dev notes / FAQ"):
    st.markdown(
        """
**Why the previous crash happened (StreamlitDuplicateElementId)**  
Streamlit can throw duplicate element errors when multiple charts are rendered without unique identifiers during reruns (especially inside loops / button triggers).  
This version assigns unique `key=` to every repeated `st.plotly_chart()` call.

**Dependencies for chart images in exports**  
To embed charts in PPT/PDF, add **kaleido** in requirements.

**Secrets**  
Store your OpenAI key as `OPENAI_API_KEY` in Streamlit Secrets or environment variable.
"""
    )
