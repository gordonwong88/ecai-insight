# app.py — EC-AI Insight (MVP)
# ------------------------------------------------------------
# Features (current build):
# - Upload CSV or Excel
# - Data preview + profile
# - Coverage / Missing / Confidence indicators
# - Auto key business cuts (Top bars) for a detected key metric
# - Auto time trend (Total + by Country/Region-like dimension)
# - Correlation heatmap (wider) + selected R² pairs
# - Executive Summary (7–10 bullets), Insights (10 bullets), Facts pack
# - Consultant-grade Suggested Next Analyses (3) + one-click "Run all 3 analyses"
# - AI Insights (OpenAI) using column statistics (safer than raw upload)
# - Export Executive Brief (PDF) + Slides (PPTX) with auto-fit text to prevent overflow
#
# Notes:
# - Avoid uploading confidential/regulatory data.
# - For Streamlit Cloud: set secrets -> OPENAI_API_KEY
# ------------------------------------------------------------

from __future__ import annotations

import io
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# Optional export libs (add to requirements.txt if needed)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pptx import Presentation
from pptx.util import Inches, Pt

# OpenAI (new SDK style)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# =============================
# Page config + light styling
# =============================
st.set_page_config(
    page_title="EC-AI Insight (MVP)",
    page_icon="🧠",
    layout="wide",
)

st.markdown(
    """
<style>
/* tighten up top padding */
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
/* headings spacing */
h1, h2, h3 { letter-spacing: -0.2px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("EC-AI Insight (MVP)")
st.caption("Turning Data Into Intelligence — Upload a CSV/Excel to get instant profiling + insights.")


# =============================
# Utilities
# =============================
def is_probably_date(colname: str) -> bool:
    s = colname.lower()
    return any(k in s for k in ["date", "dt", "timestamp", "time"])


def safe_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def compute_missing_pct(df: pd.DataFrame) -> pd.Series:
    return df.isna().mean() * 100.0


def pick_date_column(df: pd.DataFrame) -> str | None:
    # Prefer columns with "date"/"time" in name AND parseable
    candidates = []
    for c in df.columns:
        if is_probably_date(c):
            parsed = safe_to_datetime(df[c])
            if parsed.notna().mean() > 0.7:
                candidates.append((c, parsed.notna().mean()))
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    # Otherwise: any column that parses well as datetime
    for c in df.columns:
        parsed = safe_to_datetime(df[c])
        if parsed.notna().mean() > 0.85:
            return c
    return None


def pick_key_metric(df: pd.DataFrame, num_cols: list[str]) -> str | None:
    """
    Heuristic: pick a revenue-like column, else biggest-variance numeric.
    """
    if not num_cols:
        return None

    priority_keywords = [
        "revenue",
        "sales",
        "gmv",
        "income",
        "profit",
        "amount",
        "balance",
        "outstanding",
        "spend",
        "cost",
        "cogs",
        "margin",
        "units",
        "qty",
        "volume",
    ]

    # exact-ish match on priority
    for kw in priority_keywords:
        for c in num_cols:
            if kw in c.lower():
                return c

    # fallback: most variance
    variances = {}
    for c in num_cols:
        s = safe_to_numeric(df[c])
        variances[c] = float(np.nanvar(s.values))
    return sorted(variances.items(), key=lambda x: x[1], reverse=True)[0][0]


def rank_categorical_columns(df: pd.DataFrame, cat_cols: list[str], max_unique: int = 40) -> list[str]:
    """
    Rank categorical columns to find useful business cuts:
    - prefer moderate cardinality (2..12) then 13..max_unique
    """
    scored = []
    for c in cat_cols:
        nunq = int(df[c].nunique(dropna=True))
        if nunq < 2:
            continue
        if nunq <= 12:
            score = 100 - nunq  # prefer fewer
        elif nunq <= max_unique:
            score = 50 - nunq
        else:
            continue
        scored.append((score, c, nunq))
    scored.sort(reverse=True)
    return [c for _, c, _ in scored]


def choose_time_granularity(n_points: int) -> str:
    """
    Decide time bucket: daily vs weekly vs monthly, based on points.
    """
    if n_points > 500:
        return "W"
    if n_points > 140:
        return "W"
    if n_points > 60:
        return "D"
    return "D"


def bucket_time(series: pd.Series, freq: str) -> pd.Series:
    s = safe_to_datetime(series)
    if freq == "W":
        return s.dt.to_period("W").dt.start_time
    if freq == "M":
        return s.dt.to_period("M").dt.to_timestamp()
    return s.dt.floor("D")


def fmt_one_decimal(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:.1f}"


def fmt_money_like(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    ax = abs(x)
    if ax >= 1e9:
        return f"{x/1e9:.1f}B"
    if ax >= 1e6:
        return f"{x/1e6:.1f}M"
    if ax >= 1e3:
        return f"{x/1e3:.1f}K"
    return f"{x:.1f}"


def infer_country_like(cat_cols_ranked: list[str]) -> str | None:
    for c in cat_cols_ranked:
        s = c.lower()
        if "country" in s or "region" in s or "market" in s or "geo" in s:
            return c
    return None


def infer_dimension_like(cat_cols_ranked: list[str], keywords: list[str]) -> str | None:
    for c in cat_cols_ranked:
        s = c.lower()
        if any(k in s for k in keywords):
            return c
    return None


# =============================
# Confidence + Coverage indicators
# =============================
def compute_coverage(df: pd.DataFrame) -> float:
    # "coverage": proportion of non-missing cells in dataset
    total_cells = df.shape[0] * df.shape[1]
    if total_cells == 0:
        return 0.0
    non_missing = total_cells - int(df.isna().sum().sum())
    return non_missing / total_cells


def compute_confidence_score(df: pd.DataFrame, num_cols: list[str], cat_cols: list[str], strong_r2_pairs: int) -> int:
    """
    A pragmatic demo scoring:
    - Coverage (0..40)
    - Rows/Cols adequacy (0..20)
    - Signal strength (0..20)
    - Mix of data types (0..20)
    """
    cov = compute_coverage(df)  # 0..1
    s = 0.0
    s += 40.0 * cov

    rows, cols = df.shape
    if rows >= 500:
        s += 20
    elif rows >= 100:
        s += 15
    elif rows >= 30:
        s += 10
    elif rows >= 10:
        s += 5

    # signal
    if strong_r2_pairs >= 8:
        s += 20
    elif strong_r2_pairs >= 4:
        s += 14
    elif strong_r2_pairs >= 2:
        s += 10
    elif strong_r2_pairs >= 1:
        s += 6

    # mix
    if len(num_cols) >= 4 and len(cat_cols) >= 2:
        s += 20
    elif len(num_cols) >= 3 and len(cat_cols) >= 1:
        s += 15
    elif len(num_cols) >= 2:
        s += 8

    return int(round(min(100.0, s)))


def confidence_label(score: int) -> str:
    if score >= 85:
        return f"{score} (High)"
    if score >= 65:
        return f"{score} (Medium)"
    return f"{score} (Low)"


# =============================
# Rule-based signal extraction
# =============================
def extract_signals(df: pd.DataFrame, date_col: str | None, key_metric: str | None, cat_cols_ranked: list[str], num_cols: list[str], r2_pairs: list[tuple[str, str, float]]) -> dict:
    """
    Deterministic “signals” to help the AI and also provide useful insights even without AI.
    """
    signals = {}

    rows, cols = df.shape
    signals["shape"] = {"rows": rows, "cols": cols}

    missing = compute_missing_pct(df).sort_values(ascending=False)
    signals["missing_top"] = missing.head(5).round(1).to_dict()

    if key_metric and key_metric in df.columns:
        s = safe_to_numeric(df[key_metric])
        signals["key_metric"] = key_metric
        signals["key_metric_stats"] = {
            "mean": float(np.nanmean(s)),
            "median": float(np.nanmedian(s)),
            "min": float(np.nanmin(s)),
            "max": float(np.nanmax(s)),
            "std": float(np.nanstd(s)),
        }

        # outliers (simple z-score)
        if np.nanstd(s) > 0:
            z = (s - np.nanmean(s)) / (np.nanstd(s) + 1e-9)
            signals["key_metric_outlier_pct"] = float((np.abs(z) > 3).mean() * 100.0)

    # best cuts
    best_cuts = []
    for c in cat_cols_ranked[:5]:
        nunq = int(df[c].nunique(dropna=True))
        best_cuts.append({"column": c, "unique": nunq})
    signals["best_cuts"] = best_cuts

    # time span
    if date_col:
        dt = safe_to_datetime(df[date_col])
        if dt.notna().any():
            signals["date_range"] = {
                "start": str(dt.min().date()),
                "end": str(dt.max().date()),
                "days": int((dt.max() - dt.min()).days),
            }

    # strong r2 pairs
    signals["top_r2_pairs"] = [{"x": a, "y": b, "r2": round(float(r2), 3)} for a, b, r2 in sorted(r2_pairs, key=lambda x: x[2], reverse=True)[:8]]

    # numeric summary (top 6)
    numeric_summary = []
    for c in num_cols[:12]:
        s = safe_to_numeric(df[c])
        numeric_summary.append({
            "col": c,
            "mean": float(np.nanmean(s)),
            "std": float(np.nanstd(s)),
            "min": float(np.nanmin(s)),
            "max": float(np.nanmax(s)),
        })
    signals["numeric_summary"] = numeric_summary

    return signals


# =============================
# AI prompts (Consultant-grade)
# =============================
def prompt_for_next_analyses(signals: dict) -> str:
    return f"""
You are a top-tier strategy & analytics consultant. Based ONLY on the following dataset signals (not raw data),
produce exactly 3 high-quality “Suggested next analyses”.

Requirements:
- Each suggestion must be specific, actionable, and tailored to the dataset.
- Each must include:
  1) Title (short)
  2) Relevance (1–2 sentences, tie to signals like top R² pairs, variance, date range, missingness)
  3) What to do (clear steps: group-by, trend, segmentation, driver analysis, hypothesis test, etc.)
  4) Expected insight (2–3 sentences with business interpretation examples)
  5) Outputs (what charts/tables to produce)
- Avoid generic phrases like “look deeper”. Make it feel like real consulting deliverables.

Dataset signals:
{signals}

Return in clean markdown with numbering 1..3.
""".strip()


def prompt_for_executive_summary(signals: dict) -> str:
    return f"""
Write an Executive Summary of 7–10 bullet points. Be crisp, factual, and business-oriented.
Use dataset signals only. Avoid speculation. Include:
- dataset size and coverage/missing
- key metric magnitude and variability
- 2–3 strongest relationships (R²)
- key segmentation opportunities (best cuts)
- any notable data quality notes
Signals:
{signals}
""".strip()


def prompt_for_insights(signals: dict) -> str:
    return f"""
Generate exactly 10 bullet-point Insights (NOT next steps).
These should interpret what the data likely shows based on signals:
- highlight top segments/cuts to watch
- explain what strong R² pairs imply (careful: correlation not causation)
- mention time period range and potential seasonality checks
- include concrete examples of how a business user would interpret these findings
Signals:
{signals}
""".strip()


# =============================
# OpenAI client + safe payload
# =============================
def get_openai_client() -> OpenAI | None:
    if OpenAI is None:
        return None
    key = st.secrets.get("OPENAI_API_KEY", None)
    if not key:
        return None
    return OpenAI(api_key=key)


def build_safe_column_stats(df: pd.DataFrame, max_cat_values: int = 12) -> dict:
    """
    Build a minimal, safer representation:
    - numeric: count, mean, std, min, max, missing%
    - categorical: top values (up to max_cat_values), missing%
    - date: min/max
    """
    out = {"columns": {}, "shape": {"rows": df.shape[0], "cols": df.shape[1]}}
    missing_pct = compute_missing_pct(df)

    for c in df.columns:
        col = df[c]
        entry = {"missing_pct": float(missing_pct[c])}

        # datetime?
        dt = safe_to_datetime(col)
        if dt.notna().mean() > 0.85:
            entry["type"] = "datetime"
            entry["min"] = str(dt.min())
            entry["max"] = str(dt.max())
            out["columns"][c] = entry
            continue

        num = safe_to_numeric(col)
        if num.notna().mean() > 0.85:
            entry["type"] = "numeric"
            entry["count"] = int(num.notna().sum())
            entry["mean"] = float(np.nanmean(num))
            entry["std"] = float(np.nanstd(num))
            entry["min"] = float(np.nanmin(num))
            entry["max"] = float(np.nanmax(num))
            out["columns"][c] = entry
            continue

        # categorical/text
        entry["type"] = "categorical"
        vc = col.astype(str).replace("nan", np.nan).dropna().value_counts().head(max_cat_values)
        entry["top_values"] = vc.to_dict()
        entry["unique"] = int(col.nunique(dropna=True))
        out["columns"][c] = entry

    return out


def ai_generate_markdown(prompt: str, model: str = "gpt-4o-mini") -> str:
    client = get_openai_client()
    if client is None:
        return "AI is not configured. Please set `OPENAI_API_KEY` in Streamlit secrets."
    try:
        resp = client.responses.create(
            model=model,
            input=prompt,
        )
        # new SDK returns output_text
        return resp.output_text
    except Exception as e:
        return f"AI request failed: {e}"


# =============================
# One-click analyses (rule-based)
# =============================
@st.cache_data(show_spinner=False)
def run_analysis_revenue_drivers(df: pd.DataFrame, key_metric: str, num_cols: list[str]) -> dict:
    out = {}
    candidates = [c for c in num_cols if c != key_metric]
    if not candidates:
        return out
    tmp = df[[key_metric] + candidates].copy()
    tmp = tmp.apply(pd.to_numeric, errors="coerce")
    corr = tmp.corr(numeric_only=True)[key_metric].drop(key_metric)
    corr = corr.sort_values(key=lambda x: np.abs(x), ascending=False).head(8)
    out["driver_table"] = corr.reset_index().rename(columns={"index": "candidate", key_metric: "corr"})
    fig = px.bar(out["driver_table"], x="candidate", y="corr", title=f"Top numeric relationships vs {key_metric}")
    fig.update_traces(texttemplate="%{y:.1f}", textposition="outside", cliponaxis=False)
    fig.update_yaxes(tickformat=".1f")
    fig.update_layout(height=380, margin=dict(l=20, r=20, t=60, b=20))
    out["driver_chart"] = fig
    return out


@st.cache_data(show_spinner=False)
def run_analysis_variability_by_cut(df: pd.DataFrame, key_metric: str, cat_cols_ranked: list[str]) -> dict:
    out = {}
    best_cat = None
    for c in cat_cols_ranked:
        nunq = df[c].nunique(dropna=True)
        if 2 <= nunq <= 12:
            best_cat = c
            break
    if not best_cat:
        return out

    agg = df.groupby(best_cat, dropna=False)[key_metric].agg(["mean", "std", "count"]).reset_index()
    agg["cv"] = (agg["std"] / agg["mean"]).replace([np.inf, -np.inf], np.nan)
    agg = agg.sort_values("cv", ascending=False)

    out["cut"] = best_cat
    out["table"] = agg

    fig = px.bar(agg.head(12), x=best_cat, y="cv", title=f"Variability (CV) of {key_metric} by {best_cat}")
    fig.update_traces(texttemplate="%{y:.1f}", textposition="outside", cliponaxis=False)
    fig.update_yaxes(tickformat=".1f")
    fig.update_layout(height=380, margin=dict(l=20, r=20, t=60, b=20))
    out["chart"] = fig
    return out


@st.cache_data(show_spinner=False)
def run_analysis_discount_effectiveness(df: pd.DataFrame) -> dict:
    out = {}
    disc = None
    rev = None
    for c in df.columns:
        if "discount" in c.lower():
            disc = c
    for c in df.columns:
        if c.lower() in ["revenue", "sales", "gmv"] or "revenue" in c.lower() or "sales" in c.lower():
            rev = c
            break

    if disc and rev:
        tmp = df[[disc, rev]].copy()
        tmp[disc] = pd.to_numeric(tmp[disc], errors="coerce")
        tmp[rev] = pd.to_numeric(tmp[rev], errors="coerce")
        tmp = tmp.dropna()
        if len(tmp) >= 10:
            fig = px.scatter(tmp, x=disc, y=rev, trendline="ols", title=f"{rev} vs {disc} (with trendline)")
            fig.update_traces(marker=dict(size=8))
            fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
            out["scatter"] = fig
    return out


# =============================
# Export helpers: PDF + PPTX
# =============================
def make_pdf_bytes(title: str, bullets: list[str], footer: str = "") -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    x = 50
    y = height - 60

    c.setFont("Helvetica-Bold", 18)
    c.drawString(x, y, title)
    y -= 30

    c.setFont("Helvetica", 11)
    for b in bullets:
        # simple wrapping
        lines = wrap_text(f"• {b}", 95)
        for line in lines:
            if y < 80:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 11)
            c.drawString(x, y, line)
            y -= 16
        y -= 6

    if footer:
        if y < 80:
            c.showPage()
            y = height - 80
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(x, 40, footer)

    c.save()
    buffer.seek(0)
    return buffer.read()


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines = []
    cur = []
    for w in words:
        if len(" ".join(cur + [w])) <= max_chars:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def autofit_text_in_box(shape, text: str, max_font: int = 28, min_font: int = 12):
    """
    Very simple fitting: reduce font until text line count looks OK.
    """
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text

    # crude heuristic: characters per "line"
    chars = len(text)
    # estimate lines based on 60 chars/line (for 16:9 slide)
    est_lines = max(1, math.ceil(chars / 60))

    font_size = max_font
    while font_size > min_font:
        # allow ~9 lines at 18pt, ~12 lines at 14pt
        allowance = 9 if font_size >= 18 else 12
        if est_lines <= allowance:
            break
        font_size -= 2

    run.font.size = Pt(font_size)


def make_pptx_bytes(
    title: str,
    exec_bullets: list[str],
    insights_bullets: list[str],
    next_analyses: list[dict],
) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    # Slide 1: Title
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = "Executive brief generated by EC-AI Insight"

    # Slide 2: Executive Summary
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # Title Only
    slide.shapes.title.text = "Executive Summary"
    box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.8), Inches(5.6))
    txt = "\n".join([f"• {b}" for b in exec_bullets])
    autofit_text_in_box(box, txt, max_font=22, min_font=12)

    # Slide 3: Insights
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Insights"
    box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.8), Inches(5.6))
    txt = "\n".join([f"• {b}" for b in insights_bullets])
    autofit_text_in_box(box, txt, max_font=22, min_font=12)

    # Slide 4: Suggested next analyses
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Suggested next analyses"
    box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.8), Inches(5.6))

    lines = []
    for i, item in enumerate(next_analyses, 1):
        lines.append(f"{i}. {item.get('title','')}")
        lines.append(f"   • Relevance: {item.get('relevance','')}")
        lines.append(f"   • What to do: {item.get('what_to_do','')}")
        lines.append(f"   • Expected insight: {item.get('expected_insight','')}")
        lines.append("")
    autofit_text_in_box(box, "\n".join(lines).strip(), max_font=20, min_font=12)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()


def parse_next_analyses_markdown(md: str) -> list[dict]:
    """
    Parse the AI markdown into structured items for PPTX.
    If parsing fails, return 3 rough items from headings.
    """
    items = []
    blocks = re.split(r"\n(?=\d\.)", md.strip())
    for b in blocks:
        b = b.strip()
        if not re.match(r"^\d\.", b):
            continue
        # extract title = first line after "1."
        first_line = b.splitlines()[0]
        title = re.sub(r"^\d\.\s*", "", first_line).strip()
        relevance = extract_field(b, "Relevance")
        what_to_do = extract_field(b, "What to do")
        expected_insight = extract_field(b, "Expected insight")
        outputs = extract_field(b, "Outputs")
        items.append({
            "title": title,
            "relevance": relevance,
            "what_to_do": what_to_do,
            "expected_insight": expected_insight,
            "outputs": outputs,
        })
    if len(items) >= 3:
        return items[:3]

    # fallback
    return [
        {"title": "Segment performance deep-dive", "relevance": "Validate where performance concentrates.", "what_to_do": "Group by key cut; compare distributions.", "expected_insight": "Identify biggest drivers and laggards.", "outputs": "Bar, box, table"},
        {"title": "Time trend & seasonality checks", "relevance": "Quantify changes over time.", "what_to_do": "Aggregate by time bucket; compare periods.", "expected_insight": "Spot seasonality and inflection points.", "outputs": "Line charts"},
        {"title": "Driver / sensitivity analysis", "relevance": "Measure relationships among metrics.", "what_to_do": "Correlations, R² pairs, regression.", "expected_insight": "Prioritize controllable drivers.", "outputs": "Scatter + regression summary"},
    ]


def extract_field(block: str, field: str) -> str:
    # match "Field:" line(s)
    m = re.search(rf"{field}\s*:\s*(.+)", block, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


# =============================
# Sidebar controls
# =============================
with st.sidebar:
    st.header("Upload")
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    st.divider()
    st.header("Settings")
    max_rows_preview = st.slider("Preview rows", 10, 200, 50, 10)
    topn = st.slider("Top N for bar charts", 5, 20, 12, 1)
    strong_r2_threshold = st.slider("Strong R² threshold", 0.6, 0.95, 0.8, 0.05)
    st.caption("Tip: For very large datasets, consider sampling before upload.")
    st.divider()
    st.caption("Note: This app is for demo/testing. Please avoid uploading confidential or regulated data.")


# =============================
# Load data
# =============================
def load_dataframe(file) -> pd.DataFrame:
    if file is None:
        return pd.DataFrame()
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(file)
    raise ValueError("Unsupported file type.")


df_raw = load_dataframe(uploaded) if uploaded else pd.DataFrame()

if df_raw.empty:
    st.info("Upload a CSV or Excel file to begin.")
    st.stop()

# basic cleaning
df = df_raw.copy()

# Normalize column names slightly (keep original)
# (We avoid aggressive renaming; business users may want exact names.)
# Convert obvious numeric strings to numeric
for c in df.columns:
    if df[c].dtype == object:
        # attempt numeric conversion if most values look numeric
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().mean() > 0.9:
            df[c] = s

# Identify date column and coerce
date_col = pick_date_column(df)
if date_col:
    df[date_col] = safe_to_datetime(df[date_col])

# identify numeric/categorical
num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
cat_cols = [c for c in df.columns if c not in num_cols and c != date_col]

cat_cols_ranked = rank_categorical_columns(df, cat_cols, max_unique=40)

key_metric = pick_key_metric(df, num_cols)

# Preview + profile
st.success(f"Loaded dataset: {df.shape[0]} rows × {df.shape[1]} columns")

with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(max_rows_preview), use_container_width=True)

st.markdown("## Data profile")
profile = pd.DataFrame(
    {
        "column": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "missing_%": compute_missing_pct(df).round(1).values,
        "unique_values": [int(df[c].nunique(dropna=True)) for c in df.columns],
    }
)
st.dataframe(profile, use_container_width=True, hide_index=True)

# =============================
# Correlation + R² pairs (used for signals & confidence)
# =============================
r2_pairs = []
strong_pairs = []
if len(num_cols) >= 2:
    corr_df = df[num_cols].corr(numeric_only=True)

    # compute R² for all pairs
    for i, a in enumerate(num_cols):
        for b in num_cols[i + 1 :]:
            r = corr_df.loc[a, b]
            if pd.notna(r):
                r2 = float(r * r)
                r2_pairs.append((a, b, r2))
                if r2 >= strong_r2_threshold:
                    strong_pairs.append((a, b, r2))
else:
    corr_df = None

# Indicators
coverage = compute_coverage(df)
avg_missing = float(compute_missing_pct(df).mean())
confidence = compute_confidence_score(df, num_cols, cat_cols, len(strong_pairs))

st.markdown("## Indicators")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Coverage", f"{coverage*100:.1f}%")
c2.metric("Avg Missing", f"{avg_missing:.1f}%")
c3.metric("Confidence", confidence_label(confidence))
c4.metric("Strong R² Pairs", f"{len(strong_pairs)}")

st.progress(min(1.0, max(0.0, coverage)), text="Coverage gauge")


# =============================
# Auto charts (key business cuts)
# =============================
st.markdown("## Key business cuts (auto)")

if key_metric is None:
    st.warning("No numeric metric detected for auto charts.")
else:
    # choose two best categorical cuts
    dim1 = cat_cols_ranked[0] if len(cat_cols_ranked) >= 1 else None
    dim2 = cat_cols_ranked[1] if len(cat_cols_ranked) >= 2 else None

    # If no ranked cat col, fallback to any cat col
    if dim1 is None and len(cat_cols) >= 1:
        dim1 = cat_cols[0]
    if dim2 is None and len(cat_cols) >= 2:
        dim2 = cat_cols[1]

    colL, colR = st.columns(2)

    def bar_top(df_in: pd.DataFrame, dim: str, metric: str, title: str):
        agg = df_in.groupby(dim, dropna=False)[metric].sum(min_count=1).reset_index()
        agg = agg.sort_values(metric, ascending=False).head(topn)

        fig = px.bar(agg, x=dim, y=metric, title=title)
        fig.update_traces(texttemplate="%{y:.1f}", textposition="outside", cliponaxis=False)
        fig.update_yaxes(tickformat=".1f")
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
        return fig

    if dim1:
        with colL:
            st.plotly_chart(
                bar_top(df, dim1, key_metric, f"{key_metric} by {dim1} (Top {topn})"),
                use_container_width=True,
            )
    if dim2:
        with colR:
            st.plotly_chart(
                bar_top(df, dim2, key_metric, f"{key_metric} by {dim2} (Top {topn})"),
                use_container_width=True,
            )


# =============================
# Trend charts (Total + by Country/Region-like)
# =============================
if key_metric and date_col:
    st.markdown("## Trend (auto)")

    tmp = df[[date_col, key_metric]].dropna().copy()
    tmp = tmp.sort_values(date_col)

    if len(tmp) >= 10:
        freq = choose_time_granularity(len(tmp))
        tmp["period"] = bucket_time(tmp[date_col], freq)

        # Chart 1: Total trend
        total = tmp.groupby("period")[key_metric].sum(min_count=1).reset_index()

        fig_total = px.line(
            total,
            x="period",
            y=key_metric,
            markers=True,
            title=f"{key_metric} trend over time (Total)",
        )
        fig_total.update_traces(
            mode="lines+markers",
            marker=dict(size=7),
            hovertemplate="%{x|%Y-%m-%d}<br>" + f"{key_metric}: %{{y:.1f}}<extra></extra>",
        )
        fig_total.update_yaxes(tickformat=".1f")
        fig_total.update_layout(height=380, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig_total, use_container_width=True)

        # Chart 2: by Country/Region-like
        country_like = infer_country_like(cat_cols_ranked)
        if country_like:
            tmp2 = df[[date_col, key_metric, country_like]].dropna().copy()
            tmp2["period"] = bucket_time(tmp2[date_col], freq)
            by_cty = tmp2.groupby(["period", country_like])[key_metric].sum(min_count=1).reset_index()

            fig_cty = px.line(
                by_cty,
                x="period",
                y=key_metric,
                color=country_like,
                markers=True,
                title=f"{key_metric} trend over time by {country_like}",
            )
            fig_cty.update_traces(mode="lines+markers", marker=dict(size=7))
            fig_cty.update_yaxes(tickformat=".1f")
            fig_cty.update_layout(
                height=420,
                margin=dict(l=20, r=20, t=60, b=20),
                legend_title_text=country_like,
            )
            st.plotly_chart(fig_cty, use_container_width=True)
        else:
            st.info("No Country/Region-like column detected for breakdown trend.")
    else:
        st.info("Not enough date points to plot a reliable time trend.")


# =============================
# Correlation heatmap (wider) + R² relationships
# =============================
st.markdown("## Correlation (numeric)")

if corr_df is None:
    st.info("Not enough numeric columns for correlation.")
else:
    # Wider / larger chart
    fig_corr = px.imshow(
        corr_df.round(2),
        text_auto=True,
        aspect="auto",
        title="Correlation matrix (numeric)",
        zmin=-1,
        zmax=1,
    )
    fig_corr.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("### Key R² relationships (selected pairs)")
    if not r2_pairs:
        st.write("No numeric pairs available.")
    else:
        # show top 6
        top_pairs = sorted(r2_pairs, key=lambda x: x[2], reverse=True)[:6]
        for a, b, r2 in top_pairs:
            st.write(f"**{a} → {b}** : R² = `{r2:.3f}`")


# =============================
# Signals + Executive Summary + Insights + Facts pack
# =============================
signals = extract_signals(df, date_col, key_metric, cat_cols_ranked, num_cols, r2_pairs)
signals["coverage"] = round(coverage * 100.0, 1)
signals["avg_missing"] = round(avg_missing, 1)
signals["confidence"] = confidence
signals["strong_r2_pairs_count"] = len(strong_pairs)

st.markdown("## Executive Summary")
# rule-based bullets (fast) + optionally AI polish
exec_bullets = []
rows, cols = df.shape
exec_bullets.append(f"Dataset has **{rows} rows** and **{cols} columns** with **{signals['coverage']}% coverage** and **{signals['avg_missing']}% average missingness**.")
if key_metric:
    km = signals.get("key_metric_stats", {})
    exec_bullets.append(f"Key metric **{key_metric}** averages **{fmt_money_like(km.get('mean'))}** (median **{fmt_money_like(km.get('median'))}**) with range **{fmt_money_like(km.get('min'))} → {fmt_money_like(km.get('max'))}**.")
if signals.get("top_r2_pairs"):
    top_r2 = signals["top_r2_pairs"][:3]
    r2_text = ", ".join([f"{p['x']} vs {p['y']} (R² {p['r2']})" for p in top_r2])
    exec_bullets.append(f"Strongest numeric relationships include: **{r2_text}**.")
if date_col and signals.get("date_range"):
    dr = signals["date_range"]
    exec_bullets.append(f"Time coverage runs from **{dr['start']}** to **{dr['end']}** (~{dr['days']} days), suitable for trend and seasonality checks.")
if cat_cols_ranked:
    exec_bullets.append(f"Best segmentation dimensions include: **{', '.join(cat_cols_ranked[:3])}**, enabling clear business cuts.")
missing_top = signals.get("missing_top", {})
if missing_top:
    worst = list(missing_top.items())[0]
    if worst[1] > 0:
        exec_bullets.append(f"Highest missingness appears in **{worst[0]}** at **{worst[1]}%**, which may impact analysis quality if it’s a key driver.")
exec_bullets.append(f"Overall analysis confidence is **{confidence_label(confidence)}**, based on coverage, dataset size, and detected signal strength.")

# pad to 7–10 bullets
while len(exec_bullets) < 7:
    exec_bullets.append("Data structure supports both descriptive insights and hypothesis-driven diagnostics across key segments.")

exec_bullets = exec_bullets[:10]

for b in exec_bullets:
    st.write(f"• {b}")

st.markdown("## Insights")
insights_bullets = []

# rule-based insight bullets (10)
if key_metric and cat_cols_ranked:
    best_dim = cat_cols_ranked[0]
    agg = df.groupby(best_dim, dropna=False)[key_metric].sum(min_count=1).reset_index().sort_values(key_metric, ascending=False)
    if len(agg) >= 2:
        top_seg = agg.iloc[0]
        bot_seg = agg.iloc[-1]
        insights_bullets.append(f"Top {best_dim} by total **{key_metric}** is **{top_seg[best_dim]}** (~{fmt_money_like(top_seg[key_metric])}), while the lowest is **{bot_seg[best_dim]}** (~{fmt_money_like(bot_seg[key_metric])}).")

if date_col and key_metric:
    tmp = df[[date_col, key_metric]].dropna().copy()
    if len(tmp) >= 10:
        freq = choose_time_granularity(len(tmp))
        tmp["period"] = bucket_time(tmp[date_col], freq)
        t = tmp.groupby("period")[key_metric].sum(min_count=1)
        if len(t) >= 3:
            first = float(t.iloc[0])
            last = float(t.iloc[-1])
            delta = last - first
            pct = (delta / first * 100.0) if first != 0 else np.nan
            insights_bullets.append(f"{key_metric} total changes from ~{fmt_money_like(first)} to ~{fmt_money_like(last)} over the period (Δ {fmt_money_like(delta)}, {fmt_one_decimal(pct)}%).")

# relationships insights
for p in signals.get("top_r2_pairs", [])[:3]:
    insights_bullets.append(f"High alignment between **{p['x']}** and **{p['y']}** (R² {p['r2']}) suggests these metrics move together; useful for driver prioritization (correlation ≠ causation).")

# missingness
worst_items = [(k, v) for k, v in missing_top.items() if v > 0]
if worst_items:
    k, v = worst_items[0]
    insights_bullets.append(f"Data quality watch-out: **{k}** has {v}% missing; consider imputation rules or excluding from key decisions if critical.")

# segmentation opportunities
if cat_cols_ranked:
    insights_bullets.append(f"Segmentation is strongest via **{', '.join(cat_cols_ranked[:3])}** — use these for performance ranking and exception detection.")
else:
    insights_bullets.append("No strong categorical segmentation detected; consider adding business dimensions (region, product, channel, customer type).")

# pad to exactly 10
while len(insights_bullets) < 10:
    insights_bullets.append("A focused set of KPI cuts plus time-trend monitoring will improve decision clarity and reduce noise in day-to-day interpretation.")

insights_bullets = insights_bullets[:10]
for b in insights_bullets:
    st.write(f"• {b}")

with st.expander("Facts pack (auto)", expanded=False):
    st.json(signals)


# =============================
# Suggested next analyses (AI + one-click execution)
# =============================
st.markdown("## Suggested next analyses")

# We generate suggestions via AI, but also allow fallback deterministic suggestions.
suggestions_md = ""
client_ready_suggestions = []

# Build once (cached in session)
if "suggestions_md" not in st.session_state:
    # Try AI
    safe_stats = build_safe_column_stats(df)
    prompt = prompt_for_next_analyses(signals | {"safe_column_stats": safe_stats})
    suggestions_md = ai_generate_markdown(prompt, model="gpt-4o-mini")
    st.session_state["suggestions_md"] = suggestions_md
else:
    suggestions_md = st.session_state["suggestions_md"]

st.markdown(suggestions_md)

# one-click run buttons
st.markdown("### Run suggested analyses (beta)")
colA, colB = st.columns([1, 2])
with colA:
    run_all = st.button("Run all 3 analyses (1 click)")
with colB:
    st.caption("Beta: free one-click analyses. Later you can gate heavy runs behind Pro/credits.")

b1 = st.button("Run #1 Numeric drivers")
b2 = st.button("Run #2 Variability by best cut")
b3 = st.button("Run #3 Discount effectiveness")

if key_metric and (run_all or b1):
    st.subheader("1) Numeric drivers")
    res1 = run_analysis_revenue_drivers(df, key_metric, num_cols)
    if "driver_table" in res1:
        st.dataframe(res1["driver_table"], use_container_width=True, hide_index=True)
        st.plotly_chart(res1["driver_chart"], use_container_width=True)
    else:
        st.info("Not enough numeric columns to assess drivers.")

if key_metric and (run_all or b2):
    st.subheader("2) Variability by best cut")
    res2 = run_analysis_variability_by_cut(df, key_metric, cat_cols_ranked)
    if "table" in res2:
        st.caption(f"Detected cut: **{res2['cut']}**")
        st.dataframe(res2["table"].head(20), use_container_width=True, hide_index=True)
        st.plotly_chart(res2["chart"], use_container_width=True)
    else:
        st.info("No suitable categorical cut detected (need 2–12 unique values).")

if run_all or b3:
    st.subheader("3) Discount effectiveness")
    res3 = run_analysis_discount_effectiveness(df)
    if "scatter" in res3:
        st.plotly_chart(res3["scatter"], use_container_width=True)
    else:
        st.info("No discount + revenue/sales columns detected in this dataset.")


# =============================
# AI Insights (auto-run, no click)
# =============================
st.markdown("## AI Insights")

safe_stats = build_safe_column_stats(df)
ai_prompt = f"""
You are a senior analytics consultant. Generate a structured insight report based ONLY on column statistics (no raw rows).
Provide:
1) Executive summary (5 bullets)
2) Key patterns (5 bullets)
3) Business view by key dimension (3–5 bullets)
4) Data quality checks (3 bullets)
5) Suggested next analyses (3 items, each with 2–3 sentences of detail)

Use concrete language and quantify with the stats given (means/ranges/top categories). Avoid generic fluff.
Column statistics:
{safe_stats}
""".strip()

ai_text = ai_generate_markdown(ai_prompt, model="gpt-4o-mini")
st.markdown(ai_text)


# =============================
# Export: PDF + PPTX
# =============================
st.markdown("## Export")

# Prepare bullets for PDF and PPTX
pdf_bullets = [re.sub(r"\*\*(.*?)\*\*", r"\1", b) for b in exec_bullets]  # strip bold
footer = "This app is for demo/testing. Please avoid uploading confidential or regulated data."

pdf_bytes = make_pdf_bytes("Executive Brief — EC-AI Insight", pdf_bullets, footer=footer)

st.download_button(
    "Download Executive Brief (PDF)",
    data=pdf_bytes,
    file_name="ecai_executive_brief.pdf",
    mime="application/pdf",
)

# PPTX uses AI next-analyses parsing
parsed_analyses = parse_next_analyses_markdown(suggestions_md)
pptx_bytes = make_pptx_bytes(
    title="EC-AI Insight — Executive Brief",
    exec_bullets=[re.sub(r"\*\*(.*?)\*\*", r"\1", b) for b in exec_bullets][:10],
    insights_bullets=[re.sub(r"\*\*(.*?)\*\*", r"\1", b) for b in insights_bullets][:10],
    next_analyses=parsed_analyses,
)

st.download_button(
    "Download Slides (PPTX)",
    data=pptx_bytes,
    file_name="ecai_insight_slides.pptx",
    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
)

st.caption("Note: This app is for demo/testing. Please avoid uploading confidential or regulated data.")
