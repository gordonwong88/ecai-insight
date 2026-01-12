# app.py
# EC-AI Insight (MVP) — Runnable "middle-start" version
# - Upload CSV/XLSX → profile + auto charts + R² + consultant-grade suggestions + exports (optional)
# - FIX: More colorful charts (custom Plotly colorway + multi-color bars + nicer heatmap)
# - FIX: Make heavy deps OPTIONAL so the app still runs even if you didn't install them
#   (reportlab / python-pptx / kaleido / openai are optional)

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

# -----------------------------
# Optional deps (keep app runnable even if missing)
# -----------------------------
REPORTLAB_OK = True
PPTX_OK = True
OPENAI_OK = True

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas as rl_canvas
except Exception:
    REPORTLAB_OK = False

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
except Exception:
    PPTX_OK = False

try:
    from openai import OpenAI
except Exception:
    OPENAI_OK = False
    OpenAI = None  # noqa


# -----------------------------
# Page config (start point you requested)
# -----------------------------
st.set_page_config(
    page_title="EC-AI Insight (MVP)",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2.5rem; }
      h1, h2, h3 { letter-spacing: -0.3px; }
      .stDownloadButton button { border-radius: 10px; }
      .stAlert { border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Plotly theme + COLORS (more colorful)
# -----------------------------
# A rich but professional palette
EC_COLORWAY = (
    px.colors.qualitative.Set3
    + px.colors.qualitative.Bold
    + px.colors.qualitative.Pastel
    + px.colors.qualitative.Safe
)

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = EC_COLORWAY


def apply_theme(fig: go.Figure, height: Optional[int] = None) -> go.Figure:
    """Apply consistent layout styling + colorful palette."""
    fig.update_layout(
        template="plotly_white",
        colorway=EC_COLORWAY,
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    if height:
        fig.update_layout(height=height)
    return fig


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
        r"\brevenue\b", r"\bsales\b", r"\bturnover\b", r"\bincome\b",
        r"\bgmv\b", r"\bamount\b", r"\bprofit\b", r"\bmargin\b", r"\bfees?\b",
    ]
    scored = []
    for c in df.columns:
        if not is_numeric_series(df[c]):
            continue
        name = str(c).lower()
        score = sum(3 for p in patterns if re.search(p, name))
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
    cov = coverage_indicator(df)
    avg_miss = avg_missing_indicator(df)
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


def add_max_point_annotation(fig: go.Figure, x_vals, y_vals, label_prefix="Top") -> go.Figure:
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
    """
    Requires kaleido. If unavailable, returns None.
    Add to requirements: kaleido==0.2.1
    """
    try:
        return fig.to_image(format="png", scale=2)
    except Exception:
        return None


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


# -----------------------------
# AI (optional) — suggestions + report
# -----------------------------
def get_openai_client() -> Optional["OpenAI"]:
    if not OPENAI_OK:
        return None
    key = None
    try:
        key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        key = None
    if not key:
        key = st.session_state.get("OPENAI_API_KEY", None)
    if not key:
        import os
        key = os.getenv("OPENAI_API_KEY")

    if not key:
        return None
    return OpenAI(api_key=key)


def ai_generate_suggestions(facts: Dict) -> List[Dict]:
    fallback = [
        {
            "title": "Revenue and Profit Trends by Core Segments",
            "business_context": "Pinpoint where value is created (and lost) by comparing revenue (and profit if available) across the most important segments.",
            "what_to_do": "Rank segments by total revenue, then examine margin/profit distribution if present. Validate whether outperformance is driven by price, volume, or mix.",
            "expected_insight": "Identification of top growth engines vs. underperformers, and whether performance is structural or driven by spikes/outliers.",
            "outputs": "Segment leaderboard + contribution view + trend chart for top segments.",
            "risks": "Mix effects can mask true drivers; confirm with controlled cuts.",
        },
        {
            "title": "Time Trend & Seasonality Scan",
            "business_context": "Understand stability vs. volatility over time for planning and resource allocation.",
            "what_to_do": "Aggregate the primary metric by week/month. Identify peaks/troughs and relate them to segments (store/channel/category).",
            "expected_insight": "Baseline vs. spikes and which segments drive volatility.",
            "outputs": "Total trend line + trend by top segments; anomaly flags.",
            "risks": "Short time windows can overfit; avoid over-interpreting a few spikes.",
        },
        {
            "title": "Discount Effectiveness & Price/Mix Sanity Check",
            "business_context": "Validate whether discounts increase total value or erode margin.",
            "what_to_do": "Create discount bands and compare average economics (revenue/profit/units) by band; break down by category/channel.",
            "expected_insight": "A discount “sweet spot” and where discounting is likely harmful.",
            "outputs": "Discount-band chart with sample sizes + segment breakdown.",
            "risks": "Confounding from campaign timing or product mix; treat as directional until tested.",
        },
    ]

    client = get_openai_client()
    if client is None:
        return fallback

    prompt = f"""
You are a top-tier analytics consultant.
Generate EXACTLY 3 "Suggested Next Analyses" for this dataset.

Rules:
- Use the facts pack as ground truth.
- Each suggestion must have:
  title, business_context, what_to_do, expected_insight, outputs, risks
- Return valid JSON list of 3 objects.

Facts pack:
{facts}
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Return strictly valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
        )
        import json
        data = json.loads(resp.choices[0].message.content.strip())
        if isinstance(data, list) and len(data) == 3:
            return data
        return fallback
    except Exception:
        return fallback


def ai_generate_report(exec_bullets: List[str], insights_bullets: List[str], suggestions: List[Dict]) -> str:
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

    client = get_openai_client()
    if client is None:
        return fallback_text

    prompt = f"""
Write a concise "AI Insights Report" using ONLY the provided bullets and suggested analyses.
Tone: consultant-grade, crisp, professional.
Output as plain text with numbered sections.

Executive Summary bullets:
{exec_bullets}

Key Insights bullets:
{insights_bullets}

Suggested Next Analyses:
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
        bullets.append("No segment columns detected; consider adding a categorical field (e.g., Store/Channel/Category).")
        return AnalysisOutput(title=title, figure=None, bullets=bullets)

    dim = dims[0]
    g = df.groupby(dim)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(12)
    top_name = str(g.index[0])
    top_val = float(g.iloc[0])

    bullets.append(f"Top segment: **{top_name}** contributes **{human_money(top_val)}** total {revenue_col}.")
    if len(g) >= 2:
        bullets.append(f"Second segment is **{g.index[1]}** at **{human_money(float(g.iloc[1]))}**.")
    bullets.append("Use this view to confirm concentration risk (one segment dominates the outcome).")

    # MULTI-COLOR bars: set color=dim, but hide legend for cleanliness
    fig = px.bar(
        g.reset_index(),
        x=dim,
        y=revenue_col,
        color=dim,
        title=f"{revenue_col} by {dim}",
    )
    fig.update_traces(
        text=[human_money(v) for v in g.values],
        textposition="inside",
        hovertemplate=f"{dim}: %{{x}}<br>{revenue_col}: %{{y:.2f}}<extra></extra>",
    )
    fig.update_layout(showlegend=False)
    fig = apply_theme(fig)

    return AnalysisOutput(title=title, figure=fig, bullets=bullets)


def run_analysis_2_variability(df: pd.DataFrame, revenue_col: str, dim: Optional[str]) -> AnalysisOutput:
    title = "2) Variability by best cut"
    bullets: List[str] = []
    if dim is None:
        bullets.append("No suitable segment column detected for variability analysis.")
        return AnalysisOutput(title=title, figure=None, bullets=bullets)

    g = df.groupby(dim)[revenue_col].agg(["mean", "std", "count"])
    g["CV (Coefficient of Variation)"] = g["std"] / g["mean"].replace(0, np.nan)
    g = g.sort_values("CV (Coefficient of Variation)", ascending=False).head(12)

    top = g.index[0]
    top_cv = float(g.iloc[0]["CV (Coefficient of Variation)"])

    bullets.append(f"Highest variability segment is **{top}** with **CV={top_cv:.2f}** (more volatile revenue).")
    bullets.append("CV compares volatility relative to average size; higher CV means less predictable performance.")
    bullets.append("Use CV to prioritize which segments need deeper diagnostics (mix, pricing, promotions, stockouts).")

    fig = px.bar(
        g.reset_index(),
        x=dim,
        y="CV (Coefficient of Variation)",
        color=dim,
        title=f"Revenue volatility (CV) by {dim}",
    )
    fig.update_traces(text=np.round(g["CV (Coefficient of Variation)"].values, 2), textposition="outside")
    fig.update_layout(showlegend=False)
    fig = apply_theme(fig)

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

    bins = [-np.inf, 0.02, 0.05, 0.10, 0.15, 0.20, np.inf]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    band = pd.cut(disc, bins=bins, labels=labels)
    tmp = df.copy()
    tmp["Discount_Band"] = band

    g = tmp.groupby("Discount_Band")[revenue_col].agg(["mean", "count"]).reset_index()
    g["mean"] = g["mean"].astype(float)

    best = g.loc[g["mean"].idxmax()]
    worst = g.loc[g["mean"].idxmin()]

    bullets.append(f"Chart shows **average {revenue_col} per record** by discount band.")
    bullets.append(f"Best band is **{best['Discount_Band']}** with avg **{human_money(best['mean'])}** (n={int(best['count'])}).")
    bullets.append(f"Weakest band is **{worst['Discount_Band']}** with avg **{human_money(worst['mean'])}** (n={int(worst['count'])}).")
    bullets.append("Treat this as directional; confirm by controlling for Store/Channel/Category to avoid mix effects.")

    fig = px.bar(
        g,
        x="Discount_Band",
        y="mean",
        color="Discount_Band",
        title=f"Average {revenue_col} per record by Discount Band",
    )
    fig.update_traces(
        text=[human_money(v) for v in g["mean"].values],
        textposition="inside",
        customdata=g["count"].values,
        hovertemplate="Band: %{x}<br>Avg: %{y:.2f}<br>n=%{customdata}<extra></extra>",
    )
    fig.update_layout(showlegend=False, yaxis_title=f"Avg {revenue_col} per record", xaxis_title="Discount Band")
    fig = apply_theme(fig)

    return AnalysisOutput(title=title, figure=fig, bullets=bullets)


# -----------------------------
# Exports (optional) — only enabled if deps installed
# -----------------------------
def build_pdf(exec_bullets, insights_bullets, suggestions, charts, analyses, include_analyses) -> bytes:
    if not REPORTLAB_OK:
        raise RuntimeError("reportlab not installed. Install reportlab to enable PDF export.")

    buff = io.BytesIO()
    c = rl_canvas.Canvas(buff, pagesize=letter)
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

    # Page 1
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
        sug_lines += [
            f"{i}. {s['title']}",
            f"Business Context: {s['business_context']}",
            f"What to Do: {s['what_to_do']}",
            f"Expected Insight: {s['expected_insight']}",
            f"Outputs: {s['outputs']}",
            f"Risks: {s['risks']}",
        ]
    y, overflow = write_bullets(sug_lines, y, font_size=10, max_lines=40)
    if overflow:
        c.showPage()

    # Charts
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


def build_pptx(exec_bullets, insights_bullets, suggestions, charts, analyses, include_analyses) -> bytes:
    if not PPTX_OK:
        raise RuntimeError("python-pptx not installed. Install python-pptx to enable PPTX export.")

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

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

        for i, b in enumerate(bullets):
            p = tfb.paragraphs[0] if i == 0 else tfb.add_paragraph()
            p.text = b
            p.font.size = Pt(16)

    def add_image_slide(prs, title: str, image_bytes: bytes, caption: Optional[str] = None):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
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

    # Slides
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
        sug_bullets += [
            f"{i}. {s['title']}",
            f"Context: {s['business_context']}",
            f"What to do: {s['what_to_do']}",
            f"Expected: {s['expected_insight']}",
            f"Outputs: {s['outputs']}",
            f"Risks: {s['risks']}",
            "",
        ]
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
st.caption("Turning Data Into Intelligence — upload CSV or Excel to get instant profiling, charts, R² relationships, and insights.")

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

# Detect columns
date_col = guess_date_col(df)
if date_col:
    dt = safe_to_datetime(df[date_col])
    if dt is not None:
        df[date_col] = dt.dt.tz_localize(None)

numeric_cols = [c for c in df.columns if is_numeric_series(df[c])]
cat_cols = [c for c in df.columns if is_categorical_series(df[c]) and c != date_col]

revenue_col = pick_revenue_like(df) or (numeric_cols[0] if numeric_cols else None)
cost_col = pick_cost_like(df)

dims = {
    "country": pick_dim_like(df, ["country", "region", "market", "geo"]),
    "store": pick_dim_like(df, ["store", "branch", "location", "outlet"]),
    "channel": pick_dim_like(df, ["channel", "source"]),
    "category": pick_dim_like(df, ["category", "product", "sku", "segment", "industry"]),
    "payment": pick_dim_like(df, ["payment", "pay", "method", "card"]),
    "team": pick_dim_like(df, ["team", "sales_rep", "owner", "rm", "relationship", "agent"]),
}

# discount numeric detection
discount_col = None
for c in df.columns:
    if re.search(r"discount|promo|rebate", str(c), re.I) and is_numeric_series(df[c]):
        discount_col = c
        break

# Indicators
cov = coverage_indicator(df)
avg_miss = avg_missing_indicator(df)
conf_score, conf_label = confidence_indicator(df, numeric_cols)
facts = build_facts_pack(df, date_col, revenue_col, dims)

# -----------------------------
# Executive Summary + Key Insights
# -----------------------------
st.subheader("Executive Summary")

exec_bullets: List[str] = []
exec_bullets.append(
    f"Dataset has **{df.shape[0]} rows** and **{df.shape[1]} columns**; coverage is **{cov*100:.1f}%** with average missing **{avg_miss:.1f}%**."
)
if date_col:
    exec_bullets.append(f"Time field detected: **{date_col}** (usable for trend analysis).")
if revenue_col:
    s = pd.to_numeric(df[revenue_col], errors="coerce")
    exec_bullets.append(f"Primary metric detected: **{revenue_col}** — total **{human_money(s.sum())}**, average **{human_money(s.mean())}**.")
if len(numeric_cols) >= 2:
    corr, r2 = pearson_r_and_r2(df, numeric_cols)
    r2u = r2.where(~np.eye(r2.shape[0], dtype=bool))
    max_pair = r2u.stack().sort_values(ascending=False).head(1)
    if len(max_pair) == 1:
        (a, b), v = max_pair.index[0], float(max_pair.iloc[0])
        r_val = float(corr.loc[a, b])
        exec_bullets.append(f"Strongest numeric relationship: **{a} ↔ {b}** with **R²={v:.2f}** (R={r_val:.2f}, {r_strength_label(r_val)}).")
exec_bullets.append(f"Confidence indicator is **{conf_score} ({conf_label})** based on coverage, missingness, and numeric signal availability.")
exec_bullets.append("Next: review key business cuts + trends, then use the suggested analyses for deeper dives.")

for b in exec_bullets:
    st.write("• " + b)

st.subheader("Key Insights")

insights_bullets: List[str] = []
if revenue_col:
    best_dim = None
    best_gap = 0
    best_top = None
    for k in ["country", "store", "channel", "category", "payment", "team"]:
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
        if len(ts) >= 3:
            peak_date = ts.idxmax()
            insights_bullets.append(f"Peak {revenue_col} occurs on **{peak_date.date()}** at **{human_money(float(ts.max()))}**.")

    if cost_col:
        tmp = df[[revenue_col, cost_col]].copy()
        tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
        tmp[cost_col] = pd.to_numeric(tmp[cost_col], errors="coerce")
        m = (tmp[revenue_col] - tmp[cost_col]).mean(skipna=True)
        insights_bullets.append(f"Estimated average (Revenue − Cost) using **{revenue_col}** and **{cost_col}** is **{human_money(m)}** per record (directional).")

while len(insights_bullets) < 10:
    if len(numeric_cols) > 0:
        c = numeric_cols[min(len(insights_bullets), len(numeric_cols) - 1)]
        s = pd.to_numeric(df[c], errors="coerce")
        insights_bullets.append(f"**{c}** ranges from **{human_num(s.min())}** to **{human_num(s.max())}** (n={int(s.notna().sum())}).")
    else:
        insights_bullets.append("Consider adding numeric measures (e.g., Revenue, Cost, Units) to unlock richer analytics.")
        break

for b in insights_bullets[:10]:
    st.write("• " + b)

with st.expander("How correlation (R) and R² are interpreted (in this app)"):
    st.markdown(
        """
- **R (Pearson correlation)** ranges **-1 to +1** and keeps direction (positive/negative).
- **R²** ranges **0 to 1** and shows **strength only** (direction removed).

**Strength labels (heuristic)**
- **R² < 0.04** → Weak
- **0.04–0.25** → Moderate
- **0.25–0.64** → Strong
- **≥0.64** → Very strong
"""
    )

# -----------------------------
# Preview + profile
# -----------------------------
with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(50), use_container_width=True)

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
    corr, r2 = pearson_r_and_r2(df, numeric_cols)
    r2u = r2.where(~np.eye(r2.shape[0], dtype=bool))
    strong_pairs = int((r2u.stack() >= 0.64).sum())
c4.metric("Strong R² pairs", f"{strong_pairs}")

# -----------------------------
# Quick Exploration (more colorful charts)
# -----------------------------
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

        fig_hist = px.histogram(
            s.dropna(),
            nbins=18,
            title=f"Distribution of {num_col}",
        )
        fig_hist = apply_theme(fig_hist)
        med = float(s.median(skipna=True)) if s.notna().sum() else np.nan
        p90 = float(s.quantile(0.9)) if s.notna().sum() else np.nan
        st.caption(f"Commentary: median is **{human_num(med)}**; 90th percentile is **{human_num(p90)}** (skew check).")
        st.plotly_chart(fig_hist, use_container_width=True)

    with right:
        if default_cat is None:
            st.info("No categorical columns detected for a segment cut.")
        else:
            cat_col = st.selectbox("Categorical column", [c for c in cat_cols], index=[c for c in cat_cols].index(default_cat))
            g = df.groupby(cat_col)[num_col].count().sort_values(ascending=False).head(12)

            fig_bar = px.bar(
                g.reset_index().rename(columns={num_col: "count"}),
                x=cat_col,
                y="count",
                color=cat_col,          # MULTI-COLOR
                title=f"Record count by {cat_col}",
            )
            fig_bar.update_traces(text=g.values, textposition="outside")
            fig_bar.update_layout(showlegend=False)
            fig_bar = apply_theme(fig_bar)

            st.caption(f"Commentary: top category by volume is **{g.index[0]}** with **{int(g.iloc[0])} records**.")
            st.plotly_chart(fig_bar, use_container_width=True)

# -----------------------------
# Key business cuts (multi-color bars)
# -----------------------------
st.subheader("Key business cuts")
charts_for_export: List[Tuple[str, Optional[bytes]]] = []

if revenue_col is None:
    st.warning("No revenue/sales-like numeric metric detected — key business cuts will be limited.")
else:
    candidates = [dims.get("store"), dims.get("channel"), dims.get("category"), dims.get("country"), dims.get("payment"), dims.get("team")]
    candidates = [c for c in candidates if c is not None and c in df.columns]

    cols = st.columns(2)
    for i, d in enumerate(candidates[:2]):
        g = df.groupby(d)[revenue_col].sum(numeric_only=True).sort_values(ascending=False).head(12)
        top_name = str(g.index[0])
        top_val = float(g.iloc[0])

        fig = px.bar(
            g.reset_index(),
            x=d,
            y=revenue_col,
            color=d,                 # MULTI-COLOR
            title=f"{revenue_col} by {d}",
        )
        fig.update_traces(
            text=[human_money(v) for v in g.values],
            textposition="inside",
            hovertemplate=f"{d}: %{{x}}<br>{revenue_col}: %{{y:.2f}}<extra></extra>",
        )
        fig.update_layout(showlegend=False)
        fig = apply_theme(fig)

        with cols[i % 2]:
            st.caption(f"Commentary: Top segment is **{top_name}** with **{human_money(top_val)}**.")
            st.plotly_chart(fig, use_container_width=True)

        charts_for_export.append((f"{revenue_col} by {d}", fig_to_png_bytes(fig)))

# -----------------------------
# Trends (colorful markers/lines by default palette)
# -----------------------------
st.subheader("Trends")

if date_col is None or revenue_col is None:
    st.info("Trend charts require a Date-like field and a primary metric (e.g., Revenue/Sales).")
else:
    tmp = df[[date_col, revenue_col]].copy()
    tmp[revenue_col] = pd.to_numeric(tmp[revenue_col], errors="coerce")
    ts_total = tmp.groupby(date_col)[revenue_col].sum().sort_index()

    fig_total = px.line(
        ts_total.reset_index(),
        x=date_col,
        y=revenue_col,
        markers=True,
        title=f"{revenue_col} trend (total)",
    )
    fig_total = add_max_point_annotation(fig_total, ts_total.index, ts_total.values, label_prefix="Peak")
    fig_total = apply_theme(fig_total)
    st.caption("Commentary: " + chart_commentary_trend(revenue_col, ts_total))
    st.plotly_chart(fig_total, use_container_width=True)
    charts_for_export.append((f"{revenue_col} trend (total)", fig_to_png_bytes(fig_total)))

    breakdown_dims = []
    for k in ["country", "store", "channel", "category", "payment", "team"]:
        d = dims.get(k)
        if d and d in df.columns:
            breakdown_dims.append(d)
    breakdown_dims = list(dict.fromkeys(breakdown_dims))

    if breakdown_dims:
        for d in breakdown_dims[:2]:
            st.markdown(f"**{revenue_col} trend by {d} (top categories)**")
            top = top_categories(df, d, revenue_col, top_n=5)

            sm_cols = st.columns(2)
            for j, cat in enumerate(top):
                sub = df[df[d].astype(str) == cat][[date_col, revenue_col]].copy()
                sub[revenue_col] = pd.to_numeric(sub[revenue_col], errors="coerce")
                s_ts = sub.groupby(date_col)[revenue_col].sum().sort_index()
                if s_ts.empty:
                    continue

                fig_sm = px.line(
                    s_ts.reset_index(),
                    x=date_col,
                    y=revenue_col,
                    markers=True,
                    title=f"{cat}",
                )
                fig_sm = add_max_point_annotation(fig_sm, s_ts.index, s_ts.values, label_prefix="Peak")
                fig_sm = apply_theme(fig_sm, height=320)

                with sm_cols[j % 2]:
                    st.caption("Commentary: " + chart_commentary_trend(revenue_col, s_ts))
                    st.plotly_chart(fig_sm, use_container_width=True)

                charts_for_export.append((f"{revenue_col} trend — {d}: {cat}", fig_to_png_bytes(fig_sm)))
    else:
        st.info("No segment column detected for breakdown trend (e.g., Store/Channel/Category).")

# -----------------------------
# Correlation (R²) — colorful heatmap
# -----------------------------
st.subheader("Correlation")

if len(numeric_cols) < 2:
    st.info("Need at least 2 numeric columns to compute correlations.")
else:
    corr, r2 = pearson_r_and_r2(df, numeric_cols)
    z = r2.values
    x = list(r2.columns)
    y = list(r2.index)

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
            colorscale="Turbo",   # colorful heatmap
            colorbar=dict(title="R²"),
        )
    )
    fig_corr.update_layout(title="R² relationships (Pearson)")
    fig_corr = apply_theme(fig_corr, height=520)

    st.caption("Commentary: R² shows strength (0–1). Higher R² means stronger relationship; direction is in tooltip (R).")
    st.plotly_chart(fig_corr, use_container_width=True)
    charts_for_export.append(("R² relationships (Pearson)", fig_to_png_bytes(fig_corr)))

    r2u = r2.where(~np.eye(r2.shape[0], dtype=bool))
    pairs = r2u.stack().sort_values(ascending=False).head(6)
    st.markdown("**Key R² relationships (top pairs)**")
    for (a, b), v in pairs.items():
        r = float(corr.loc[a, b])
        st.write(f"• **{a} ↔ {b}**: R²={v:.2f} ({r2_strength_label(v)}), R={r:.2f} ({r_strength_label(r)})")

# -----------------------------
# Suggested Next Analyses (AI optional)
# -----------------------------
st.subheader("Suggested Next Analyses")
suggestions = ai_generate_suggestions(facts)

for i, s in enumerate(suggestions, 1):
    st.markdown(f"**{i}. {s['title']}**")
    st.write(f"• **Business Context:** {s['business_context']}")
    st.write(f"• **What to Do:** {s['what_to_do']}")
    st.write(f"• **Expected Insight:** {s['expected_insight']}")
    st.write(f"• **Outputs:** {s['outputs']}")
    st.write(f"• **Risks:** {s['risks']}")
    st.write("")

# -----------------------------
# Deeper dives
# -----------------------------
st.subheader("Deeper dives (one click)")

analyses_outputs: List[AnalysisOutput] = st.session_state.get("analyses_outputs", [])
ran = st.session_state.get("ran_analyses", False)

colA, colB = st.columns([1, 2])
with colA:
    run_btn = st.button("Run all 3 analyses", type="primary")
with colB:
    st.caption("One click generates charts + short commentary. (Designed to stay lightweight and runnable.)")

if run_btn:
    analyses_outputs = []
    if revenue_col:
        analyses_outputs.append(run_analysis_1_driver(df, revenue_col, dims.get("store") or dims.get("channel") or dims.get("category"), dims.get("channel")))
        analyses_outputs.append(run_analysis_2_variability(df, revenue_col, dims.get("channel") or dims.get("store") or dims.get("category")))
        analyses_outputs.append(run_analysis_3_discount_simple(df, revenue_col, discount_col))
    else:
        analyses_outputs.append(AnalysisOutput("1) Revenue driver & segment performance", None, ["No revenue-like metric detected."]))
        analyses_outputs.append(AnalysisOutput("2) Variability by best cut", None, ["No revenue-like metric detected."]))
        analyses_outputs.append(AnalysisOutput("3) Discount effectiveness (simple)", None, ["No revenue-like metric detected."]))

    st.session_state["analyses_outputs"] = analyses_outputs
    st.session_state["ran_analyses"] = True
    ran = True

if ran and analyses_outputs:
    for a in analyses_outputs:
        st.markdown(f"### {a.title}")
        for b in a.bullets:
            st.write("• " + b)
        if a.figure is not None:
            st.plotly_chart(a.figure, use_container_width=True)
        st.divider()

# -----------------------------
# AI Insights Report
# -----------------------------
st.subheader("AI Insights Report")
report_text = ai_generate_report(exec_bullets[:10], insights_bullets[:10], suggestions)
st.text(report_text)

# -----------------------------
# Export (optional)
# -----------------------------
st.subheader("Export")
st.caption("Note: This app is for demo/testing. Please avoid uploading confidential or regulated data.")

include_analyses = bool(st.session_state.get("ran_analyses", False))
analyses_outputs = st.session_state.get("analyses_outputs", [])

export_ok = REPORTLAB_OK or PPTX_OK
if not export_ok:
    st.warning("Exports are disabled because reportlab/python-pptx are not installed. The app still runs fine without them.")

cE1, cE2, cE3, cE4 = st.columns(4)

with cE1:
    if st.button("Build Executive Brief (PDF)", disabled=not REPORTLAB_OK):
        pdf_bytes = build_pdf(exec_bullets[:10], insights_bullets[:10], suggestions, charts_for_export, analyses_outputs, include_analyses=False)
        st.download_button("Download Executive Brief (PDF)", data=pdf_bytes, file_name="ecai_executive_brief.pdf", mime="application/pdf")

with cE2:
    if st.button("Build Slides (PPTX)", disabled=not PPTX_OK):
        ppt_bytes = build_pptx(exec_bullets[:10], insights_bullets[:10], suggestions, charts_for_export, analyses_outputs, include_analyses=False)
        st.download_button("Download Slides (PPTX)", data=ppt_bytes, file_name="ecai_insight_slides.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

with cE3:
    if st.button("Build Full Pack (PDF)", disabled=(not REPORTLAB_OK or not include_analyses)):
        pdf_bytes = build_pdf(exec_bullets[:10], insights_bullets[:10], suggestions, charts_for_export, analyses_outputs, include_analyses=True)
        st.download_button("Download Full Pack (PDF)", data=pdf_bytes, file_name="ecai_full_pack.pdf", mime="application/pdf")

with cE4:
    if st.button("Build Full Pack (PPTX)", disabled=(not PPTX_OK or not include_analyses)):
        ppt_bytes = build_pptx(exec_bullets[:10], insights_bullets[:10], suggestions, charts_for_export, analyses_outputs, include_analyses=True)
        st.download_button("Download Full Pack (PPTX)", data=ppt_bytes, file_name="ecai_full_pack.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

# -----------------------------
# Dev notes
# -----------------------------
with st.expander("Dev notes / FAQ"):
    st.markdown(
        """
**Colorful charts**
- We set a custom Plotly colorway and force multi-color bars using `color=<category>` then hide the legend.

**If your app didn't run before**
- This version makes exports + OpenAI optional so the app still loads even if those packages/keys are missing.

**Optional dependencies**
- PDF export: `reportlab`
- PPT export: `python-pptx`
- Export charts as images inside PDF/PPT: `kaleido==0.2.1`
- AI suggestions/report: `openai` + `OPENAI_API_KEY` in Streamlit secrets or env var

**Recommended requirements (minimum to run UI)**
- streamlit
- pandas
- numpy
- plotly
"""
    )
