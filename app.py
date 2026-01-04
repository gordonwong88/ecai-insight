import os
import re
import io
import datetime as dt
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# =============================
# Page config
# =============================
st.set_page_config(page_title="EC-AI Insight", layout="wide")

APP_TITLE = "EC-AI Insight"
APP_TAGLINE = "Upload any dataset. Get an executive understanding. See what matters instantly."

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()


# =============================
# Utility functions
# =============================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", "_", str(c).strip()) for c in df.columns]
    return df


def smart_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)

    # Parse date-like columns by name first
    for c in df.columns:
        lc = c.lower()
        if ("date" in lc) or ("asof" in lc) or ("month" in lc) or ("period" in lc):
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Convert numeric-like object columns
    for c in df.select_dtypes(include="object").columns:
        series = df[c]
        sample = series.dropna().astype(str).head(300)
        if len(sample) == 0:
            continue

        # Basic cleanup tokens
        series = series.astype(str).replace(
            {"(blank)": "", "NA": "", "N/A": "", "None": "", "nan": ""},
            regex=False,
        )
        series = series.replace(r"^\s+$", "", regex=True)

        numeric_ratio = sample.str.match(r"^\s*-?\d+(\.\d+)?\s*$").mean()
        if numeric_ratio >= 0.7:
            df[c] = pd.to_numeric(series, errors="coerce")
        else:
            df[c] = series.replace("", np.nan)

    return df


def basic_profile(df: pd.DataFrame) -> pd.DataFrame:
    return (
        pd.DataFrame(
            {
                "column": df.columns,
                "dtype": [str(t) for t in df.dtypes],
                "missing_%": (df.isna().mean() * 100).round(2),
                "unique_values": [df[c].nunique(dropna=True) for c in df.columns],
            }
        )
        .sort_values("missing_%", ascending=False)
        .reset_index(drop=True)
    )


def prioritize_numeric_columns(num_cols: list[str]) -> list[str]:
    """
    Rank numeric columns by business importance using naming heuristics.
    """
    priority_keywords = [
        ("revenue", 1),
        ("sales", 1),
        ("income", 1),
        ("gmv", 1),
        ("profit", 2),
        ("margin", 2),
        ("gross", 2),
        ("cogs", 3),
        ("cost", 3),
        ("expense", 3),
        ("price", 4),
        ("amount", 4),
        ("balance", 4),
        ("outstanding", 4),
        ("exposure", 4),
        ("limit", 4),
        ("volume", 5),
        ("units", 5),
        ("qty", 5),
        ("quantity", 5),
        ("count", 6),
        ("flag", 7),
        ("id", 9),
    ]

    scored = []
    for c in num_cols:
        score = 99
        lc = c.lower()
        for kw, s in priority_keywords:
            if kw in lc:
                score = s
                break
        scored.append((score, c))

    scored.sort(key=lambda x: (x[0], x[1].lower()))
    return [c for _, c in scored]


def prioritize_dimensions(cat_cols: list[str]) -> list[str]:
    """
    Rank categorical dimensions by how likely they are to be a "business cut".
    """
    priority = [
        "country",
        "region",
        "store",
        "team",
        "channel",
        "category",
        "industry",
        "sector",
        "segment",
        "client",
        "customer",
        "product",
    ]

    scored = []
    for c in cat_cols:
        lc = c.lower()
        s = 99
        for i, kw in enumerate(priority, start=1):
            if kw in lc:
                s = i
                break
        scored.append((s, c))

    scored.sort(key=lambda x: (x[0], x[1].lower()))
    return [c for _, c in scored]


def find_best_metric(num_cols: list[str]) -> str | None:
    if not num_cols:
        return None
    ranked = prioritize_numeric_columns(num_cols)
    for c in ranked:
        lc = c.lower()
        if ("revenue" in lc) or ("sales" in lc) or ("income" in lc) or ("gmv" in lc):
            return c
    return ranked[0]


def find_best_date_col(df: pd.DataFrame) -> str | None:
    date_cols = [c for c in df.columns if np.issubdtype(df[c].dtype, np.datetime64)]
    if not date_cols:
        return None
    for c in date_cols:
        if "date" in c.lower():
            return c
    return date_cols[0]


def to_month_period(series: pd.Series) -> pd.Series:
    s = pd.to_datetime(series, errors="coerce")
    return s.dt.to_period("M").dt.to_timestamp()


# =============================
# Signal extraction & indicators
# =============================
def extract_analysis_signals(df: pd.DataFrame) -> dict:
    signals = {
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "numeric_columns": [],
        "categorical_columns": [],
        "date_columns": [],
        "strong_relationships": [],  # list of {x,y,r2,n}
        "high_variance_metrics": [],
        "data_quality_flags": [],
    }

    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    date_cols = [c for c in df.columns if np.issubdtype(df[c].dtype, np.datetime64)]
    cat_cols = [c for c in df.columns if (c not in num_cols) and (c not in date_cols)]

    signals["numeric_columns"] = num_cols
    signals["categorical_columns"] = cat_cols
    signals["date_columns"] = date_cols

    # Strong relationships (R²)
    for i in range(len(num_cols)):
        for j in range(i + 1, len(num_cols)):
            a, b = num_cols[i], num_cols[j]
            valid = df[a].notna() & df[b].notna()
            n = int(valid.sum())
            if n < 10:
                continue
            r = np.corrcoef(df.loc[valid, a], df.loc[valid, b])[0, 1]
            if not np.isnan(r):
                r2 = float(r**2)
                if r2 >= 0.60:
                    signals["strong_relationships"].append(
                        {"x": a, "y": b, "r2": round(r2, 3), "n": n}
                    )

    # High variance metrics (coefficient of variation)
    for c in num_cols:
        mean = df[c].mean(skipna=True)
        std = df[c].std(skipna=True)
        if mean is None or np.isnan(mean) or mean == 0:
            continue
        cv = float(abs(std / mean))
        if cv >= 0.50:
            signals["high_variance_metrics"].append(c)

    # Data quality flags
    for c in df.columns:
        miss = float(df[c].isna().mean())
        if miss >= 0.15:
            signals["data_quality_flags"].append(f"{c}: {round(miss*100,1)}% missing")

    return signals


def compute_coverage_and_confidence(df: pd.DataFrame, signals: dict) -> dict:
    missing_avg = float(df.isna().mean().mean())
    coverage = max(0.0, min(1.0, 1.0 - missing_avg))

    rows = int(signals["row_count"])
    num_n = len(signals["numeric_columns"])
    cat_n = len(signals["categorical_columns"])
    rel_n = len(signals["strong_relationships"])
    has_time = len(signals["date_columns"]) > 0

    if rows < 30:
        row_score = 0.25
    elif rows < 100:
        row_score = 0.55
    elif rows < 500:
        row_score = 0.80
    else:
        row_score = 1.00

    structure_score = 0.0
    if num_n >= 2:
        structure_score += 0.55
    elif num_n == 1:
        structure_score += 0.35

    if cat_n >= 1:
        structure_score += 0.30

    if has_time:
        structure_score += 0.15

    structure_score = min(1.0, structure_score)

    if rel_n >= 5:
        rel_score = 1.0
    elif rel_n >= 2:
        rel_score = 0.7
    elif rel_n == 1:
        rel_score = 0.4
    else:
        rel_score = 0.0

    confidence = (
        0.45 * coverage
        + 0.25 * row_score
        + 0.20 * structure_score
        + 0.10 * rel_score
    )
    confidence = int(round(confidence * 100))

    if confidence >= 80:
        conf_label = "High"
    elif confidence >= 55:
        conf_label = "Medium"
    else:
        conf_label = "Low"

    return {
        "coverage_pct": int(round(coverage * 100)),
        "missing_avg_pct": round(missing_avg * 100, 2),
        "confidence_score": confidence,
        "confidence_label": conf_label,
        "num_cols": num_n,
        "cat_cols": cat_n,
        "date_cols": len(signals["date_columns"]),
        "strong_pairs": rel_n,
    }


# =============================
# Facts pack (for AI + for deterministic insights)
# =============================
def build_facts_pack(df: pd.DataFrame) -> dict:
    raw_num_cols = df.select_dtypes(include=np.number).columns.tolist()
    num_cols_ranked = prioritize_numeric_columns(raw_num_cols)

    cat_cols = [
        c
        for c in df.columns
        if (c not in raw_num_cols) and (not np.issubdtype(df[c].dtype, np.datetime64))
    ]
    cat_cols_ranked = prioritize_dimensions(cat_cols)

    metric = find_best_metric(num_cols_ranked)
    dim1 = cat_cols_ranked[0] if len(cat_cols_ranked) >= 1 else None
    dim2 = cat_cols_ranked[1] if len(cat_cols_ranked) >= 2 else None
    date_col = find_best_date_col(df)

    facts = {
        "key_metric": metric,
        "key_dimensions_ranked": cat_cols_ranked[:5],
        "key_dimension_primary": dim1,
        "key_dimension_secondary": dim2,
        "date_col": date_col,
        "top_bottom_by_primary_dim": None,
        "concentration_top3_share": None,
        "trend_monthly": None,
        "metric_summary": None,
    }

    # Metric summary
    if metric:
        s = df[metric]
        facts["metric_summary"] = {
            "mean": float(s.mean(skipna=True)) if s.notna().any() else None,
            "median": float(s.median(skipna=True)) if s.notna().any() else None,
            "min": float(s.min(skipna=True)) if s.notna().any() else None,
            "max": float(s.max(skipna=True)) if s.notna().any() else None,
        }

    # Top/bottom segments
    if metric and dim1:
        by_dim = (
            df.groupby(dim1, dropna=False)[metric]
            .sum(min_count=1)
            .sort_values(ascending=False)
        )
        if len(by_dim) >= 1:
            top3 = by_dim.head(3)
            bot3 = by_dim.tail(3)
            facts["top_bottom_by_primary_dim"] = {
                "top3": {str(k): float(v) for k, v in top3.items()},
                "bottom3": {str(k): float(v) for k, v in bot3.items()},
                "count_segments": int(len(by_dim)),
            }
            total = float(by_dim.sum()) if np.isfinite(by_dim.sum()) else 0.0
            if total > 0 and len(by_dim) >= 3:
                facts["concentration_top3_share"] = round(float(top3.sum() / total), 3)

    # Trend
    if metric and date_col:
        tmp = df[[date_col, metric]].dropna()
        if len(tmp) >= 10:
            tmp = tmp.sort_values(date_col).copy()
            tmp["period"] = to_month_period(tmp[date_col])
            trend = tmp.groupby("period")[metric].sum(min_count=1)
            if len(trend) >= 2:
                start = float(trend.iloc[0])
                end = float(trend.iloc[-1])
                change_pct = (
                    ((end - start) / max(1e-9, abs(start))) * 100.0
                    if np.isfinite(start) and np.isfinite(end)
                    else None
                )
                facts["trend_monthly"] = {
                    "start_period": str(trend.index[0].date()),
                    "end_period": str(trend.index[-1].date()),
                    "start_value": start,
                    "end_value": end,
                    "change_pct": round(float(change_pct), 1) if change_pct is not None else None,
                    "period_points": int(len(trend)),
                }

    return facts


def format_facts_pack(facts: dict) -> str:
    return (
        f"Facts pack (computed):\n"
        f"- Key metric: {facts.get('key_metric')}\n"
        f"- Ranked dimensions: {facts.get('key_dimensions_ranked')}\n"
        f"- Primary dimension: {facts.get('key_dimension_primary')}\n"
        f"- Secondary dimension: {facts.get('key_dimension_secondary')}\n"
        f"- Date column: {facts.get('date_col')}\n"
        f"- Metric summary: {facts.get('metric_summary')}\n"
        f"- Top/Bottom by primary dimension: {facts.get('top_bottom_by_primary_dim')}\n"
        f"- Top3 concentration share: {facts.get('concentration_top3_share')}\n"
        f"- Monthly trend: {facts.get('trend_monthly')}\n"
    )


# =============================
# AI generation
# =============================
def generate_ai_output(signals: dict, indicators: dict, facts: dict) -> str:
    if not OPENAI_API_KEY:
        return "⚠️ OpenAI API key not configured. Add it in Streamlit → App settings → Secrets."

    analysis_context = f"""
Dataset size:
- Rows: {signals['row_count']}
- Columns: {signals['column_count']}

Structure:
- Numeric columns: {signals['numeric_columns']}
- Categorical columns: {signals['categorical_columns']}
- Date columns: {signals['date_columns']}

Signals:
- Strong numeric relationships (R² ≥ 0.6): {signals['strong_relationships']}
- High variance metrics: {signals['high_variance_metrics']}
- Data quality flags: {signals['data_quality_flags']}

Indicators:
- Coverage: {indicators['coverage_pct']}%
- Avg missing: {indicators['missing_avg_pct']}%
- Confidence score: {indicators['confidence_score']} ({indicators['confidence_label']})

{format_facts_pack(facts)}
"""

    prompt = f"""
You are EC-AI Insight, an executive analytics advisor.

NON-NEGOTIABLE RULES:
- Base every statement ONLY on the provided dataset context and facts pack.
- Do NOT assume industry, business goals, or external benchmarks.
- Do NOT invent variables, comparisons, or “best practices” claims.
- If something is not supported by the context, say it is not determinable.

OUTPUT FORMAT (MANDATORY). Use exactly these headings:

## Executive Summary
Write 7–10 bullets. Evidence-led and executive tone.

## Insights
Write EXACTLY 10 bullets.
- Each bullet must be specific and data-grounded (e.g., “Top segment by <metric> is <X>…”, “Trend <up/down> over <period>…”, “Concentration top3 share is <x%>…”).
- Include at least: (a) top/bottom segment info if available, (b) concentration, (c) one time trend if available, (d) key R² relationships if present, (e) one data quality caveat if applicable.

## Suggested next analyses
Provide EXACTLY 3 analyses, each in the structure below:

### 1) <Analysis name>
- Objective: <what the analysis answers>
- Why now: <explicitly cite which signals/indicators/facts motivate this>
- Approach: <3–5 concrete steps, actionable>
- Outputs: <specific charts/tables/tests the app/user should produce>
- Decisions enabled: <specific decision types this could support>

### 2) ...
### 3) ...

DATASET CONTEXT:
{analysis_context}
"""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are precise, non-speculative, and consultant-grade."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI error: {e}"


# =============================
# Parsing AI sections for export
# =============================
def _extract_bullets_under_heading(ai_text: str, heading: str, max_n: int) -> list[str]:
    if not ai_text:
        return []
    lines = ai_text.splitlines()
    in_section = False
    bullets: list[str] = []

    heading_re = re.compile(rf"^\s*##\s*{re.escape(heading)}\s*$", re.IGNORECASE)
    any_heading_re = re.compile(r"^\s*##\s+", re.IGNORECASE)

    for line in lines:
        l = line.strip()
        if heading_re.match(l):
            in_section = True
            continue
        if in_section and any_heading_re.match(l):
            break
        if in_section:
            if l.startswith(("-", "•")):
                bullets.append(l.lstrip("-• ").strip())
            elif re.match(r"^\d+[\).\s]\s*", l):
                bullets.append(re.sub(r"^\d+[\).\s]\s*", "", l).strip())
    return [b for b in bullets if b][:max_n]


def parse_exec_bullets(ai_text: str) -> list[str]:
    return _extract_bullets_under_heading(ai_text, "Executive Summary", 10)


def parse_insights_bullets(ai_text: str) -> list[str]:
    return _extract_bullets_under_heading(ai_text, "Insights", 10)


def parse_next_analyses_blocks(ai_text: str) -> list[dict]:
    """
    Returns list of {title:str, lines:list[str]} for up to 3 analyses.
    Expects '### 1) Name' etc.
    """
    if not ai_text:
        return []

    m = re.split(r"(?i)##\s+Suggested next analyses", ai_text, maxsplit=1)
    if len(m) < 2:
        return []

    section = m[1]
    parts = re.split(r"(?m)^\s*###\s*\d+\)\s*", section)

    blocks = []
    for p in parts[1:]:
        lines = [x.rstrip() for x in p.splitlines() if x.strip()]
        if not lines:
            continue
        title = lines[0].strip()
        body = lines[1:]
        blocks.append({"title": title, "lines": body})
        if len(blocks) == 3:
            break
    return blocks


# =============================
# Export helpers
# =============================
def wrap_text(text: str, max_chars: int):
    words = str(text).split()
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


def build_pdf_bytes(title: str, indicators: dict, exec_bullets: list[str], insights_bullets: list[str], analyses: list[dict]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    x = 2 * cm
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, title)

    y -= 0.7 * cm
    c.setFont("Helvetica", 9)
    c.drawString(x, y, f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y -= 0.8 * cm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "Indicators")
    y -= 0.5 * cm
    c.setFont("Helvetica", 9)
    c.drawString(
        x,
        y,
        f"Coverage: {indicators['coverage_pct']}% | Avg Missing: {indicators['missing_avg_pct']}% | "
        f"Confidence: {indicators['confidence_score']} ({indicators['confidence_label']})",
    )
    y -= 0.5 * cm
    c.drawString(
        x,
        y,
        f"Numeric cols: {indicators['num_cols']} | Categorical cols: {indicators['cat_cols']} | "
        f"Date cols: {indicators['date_cols']} | Strong pairs: {indicators['strong_pairs']}",
    )

    def ensure_space():
        nonlocal y
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm

    # Executive Summary
    y -= 0.9 * cm
    ensure_space()
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Executive Summary")
    y -= 0.6 * cm
    c.setFont("Helvetica", 9)

    for i, b in enumerate(exec_bullets[:10], start=1):
        for wline in wrap_text(f"{i}. {b}", 95):
            ensure_space()
            c.drawString(x, y, wline)
            y -= 0.45 * cm

    # Insights
    y -= 0.4 * cm
    ensure_space()
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Insights")
    y -= 0.6 * cm
    c.setFont("Helvetica", 9)

    for i, b in enumerate(insights_bullets[:10], start=1):
        for wline in wrap_text(f"{i}. {b}", 95):
            ensure_space()
            c.drawString(x, y, wline)
            y -= 0.45 * cm

    # Next analyses
    y -= 0.4 * cm
    ensure_space()
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Suggested Next Analyses (Top 3)")
    y -= 0.6 * cm
    c.setFont("Helvetica", 9)

    for idx, a in enumerate(analyses[:3], start=1):
        for wline in wrap_text(f"{idx}) {a['title']}", 95):
            ensure_space()
            c.drawString(x, y, wline)
            y -= 0.45 * cm

        for raw in a["lines"][:30]:
            for wline in wrap_text(raw.strip(), 95):
                ensure_space()
                c.drawString(x + 0.4 * cm, y, wline)
                y -= 0.45 * cm

        y -= 0.2 * cm

    c.save()
    buffer.seek(0)
    return buffer.read()


def _pick_font_size(text_len: int) -> int:
    if text_len <= 650:
        return 18
    if text_len <= 950:
        return 16
    if text_len <= 1250:
        return 14
    return 12


def build_pptx_bytes(title: str, indicators: dict, exec_bullets: list[str], insights_bullets: list[str], analyses: list[dict]) -> bytes:
    try:
        from pptx import Presentation
        from pptx.util import Pt
    except Exception:
        return b""

    prs = Presentation()

    # Slide 1 - Title
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    subtitle = slide.placeholders[1]
    subtitle.text = (
        f"Coverage: {indicators['coverage_pct']}% | Avg Missing: {indicators['missing_avg_pct']}%\n"
        f"Confidence: {indicators['confidence_score']} ({indicators['confidence_label']}) | "
        f"Strong pairs: {indicators['strong_pairs']}"
    )

    # Slide 2 - Executive Summary
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Executive Summary"
    tf = slide.shapes.placeholders[1].text_frame
    tf.clear()

    exec_trim = exec_bullets[:8]
    for b in exec_trim:
        p = tf.add_paragraph()
        p.text = b
        p.level = 0

    all_text = "\n".join(exec_trim)
    fs = _pick_font_size(len(all_text))
    for p in tf.paragraphs:
        for run in p.runs:
            run.font.size = Pt(fs)

    # Slide 3 - Insights
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Insights"
    tf = slide.shapes.placeholders[1].text_frame
    tf.clear()

    ins_trim = insights_bullets[:8]
    for b in ins_trim:
        p = tf.add_paragraph()
        p.text = b
        p.level = 0

    all_text = "\n".join(ins_trim)
    fs = _pick_font_size(len(all_text))
    for p in tf.paragraphs:
        for run in p.runs:
            run.font.size = Pt(fs)

    # Slides 4-6 - One analysis per slide
    for idx, a in enumerate(analyses[:3], start=1):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Suggested Next Analysis {idx}: {a['title']}"

        tf = slide.shapes.placeholders[1].text_frame
        tf.clear()

        lines = a["lines"][:16]
        for line in lines:
            p = tf.add_paragraph()
            p.text = line
            p.level = 0

        all_text = "\n".join(lines)
        fs = _pick_font_size(len(all_text))
        for p in tf.paragraphs:
            for run in p.runs:
                run.font.size = Pt(fs)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()


# =============================
# File loading (CSV + Excel with optional sheet pick)
# =============================
def load_input_file(uploaded_file) -> tuple[pd.DataFrame, str]:
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        try:
            df = pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            df = pd.read_csv(uploaded_file, encoding="latin1")
        return df, "csv"

    if name.endswith(".xlsx") or name.endswith(".xls"):
        xls = pd.ExcelFile(uploaded_file)
        sheets = xls.sheet_names
        sheet = sheets[0]
        if len(sheets) > 1:
            sheet = st.selectbox("Select sheet", sheets, index=0)
        df = pd.read_excel(xls, sheet_name=sheet)
        return df, f"excel:{sheet}"

    raise ValueError("Unsupported file type")


# =============================
# UI
# =============================
st.markdown(f"## {APP_TITLE}")
st.caption(APP_TAGLINE)

uploaded = st.file_uploader("Upload CSV or Excel (XLSX)", type=["csv", "xlsx", "xls"])
if not uploaded:
    st.info("Upload a CSV/XLSX file to begin.")
    st.stop()

df_raw, source_sig = load_input_file(uploaded)
df = smart_clean(df_raw)

st.success(f"Loaded dataset: {df.shape[0]:,} rows × {df.shape[1]:,} columns")

with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(50), use_container_width=True)

st.markdown("### Data profile")
st.dataframe(basic_profile(df), use_container_width=True, height=360)

signals = extract_analysis_signals(df)
facts = build_facts_pack(df)
ind = compute_coverage_and_confidence(df, signals)

st.markdown("### Indicators")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Coverage", f"{ind['coverage_pct']}%")
m2.metric("Avg Missing", f"{ind['missing_avg_pct']}%")
m3.metric("Confidence", f"{ind['confidence_score']} ({ind['confidence_label']})")
m4.metric("Strong R² Pairs", f"{ind['strong_pairs']}")
st.progress(ind["confidence_score"] / 100)

# =============================
# Smart auto charts (first run)
# =============================
st.markdown("### Key business cuts (auto)")

raw_num_cols = df.select_dtypes(include=np.number).columns.tolist()
num_cols_ranked = prioritize_numeric_columns(raw_num_cols)
cat_cols = [
    c
    for c in df.columns
    if (c not in raw_num_cols) and (not np.issubdtype(df[c].dtype, np.datetime64))
]
cat_cols_ranked = prioritize_dimensions(cat_cols)

key_metric = facts.get("key_metric")
dim1 = facts.get("key_dimension_primary")
dim2 = facts.get("key_dimension_secondary")
date_col = facts.get("date_col")

cA, cB = st.columns(2)

with cA:
    if key_metric and dim1:
        topn = 12
        agg = (
            df.groupby(dim1, dropna=False)[key_metric]
            .sum(min_count=1)
            .sort_values(ascending=False)
            .head(topn)
            .reset_index()
        )
        fig = px.bar(
            agg,
            x=dim1,
            y=key_metric,
            text_auto=True,
            title=f"{key_metric} by {dim1} (Top {topn})",
        )
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Auto chart A unavailable (need a key metric + a categorical dimension).")

with cB:
    if key_metric and dim2:
        topn = 12
        agg = (
            df.groupby(dim2, dropna=False)[key_metric]
            .sum(min_count=1)
            .sort_values(ascending=False)
            .head(topn)
            .reset_index()
        )
        fig = px.bar(
            agg,
            x=dim2,
            y=key_metric,
            text_auto=True,
            title=f"{key_metric} by {dim2} (Top {topn})",
        )
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Auto chart B unavailable (need a second categorical dimension).")

if key_metric and date_col:
    tmp = df[[date_col, key_metric]].dropna()
    if len(tmp) >= 10:
        tmp = tmp.sort_values(date_col).copy()
        tmp["period"] = to_month_period(tmp[date_col])
        trend = tmp.groupby("period")[key_metric].sum(min_count=1).reset_index()
        fig = px.line(
            trend,
            x="period",
            y=key_metric,
            markers=True,
            title=f"{key_metric} trend over time (monthly)",
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough date points to plot a reliable time trend.")


# =============================
# Quick exploration (still useful for manual exploration)
# =============================
st.markdown("### Quick exploration")

c1, c2 = st.columns(2)

with c1:
    if num_cols_ranked:
        # Default to key metric (revenue/sales etc.) if available
        default_col = key_metric if key_metric in num_cols_ranked else num_cols_ranked[0]
        idx = num_cols_ranked.index(default_col)
        col = st.selectbox("Numeric column (prioritized)", num_cols_ranked, index=idx)

        unique_vals = df[col].nunique(dropna=True)

        if unique_vals <= 10:
            vc = df[col].value_counts().sort_index().reset_index()
            vc.columns = [col, "Count"]
            fig = px.bar(vc, x=col, y="Count", text_auto=True, title=f"Distribution of {col}")
        elif len(df) < 200:
            fig = px.box(df, y=col, points="outliers", title=f"Distribution of {col}")
        else:
            fig = px.histogram(df, x=col, nbins=30, title=f"Distribution of {col}")

        fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric columns detected.")

with c2:
    if cat_cols_ranked:
        col = st.selectbox("Categorical column", cat_cols_ranked)
        vc = df[col].astype(str).value_counts().head(20).reset_index()
        vc.columns = [col, "count"]
        fig = px.bar(vc, x=col, y="count", text_auto=True, title=f"Top values of {col}")
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No categorical columns detected.")


# =============================
# Correlation (numeric) — wide/full width
# =============================
if len(num_cols_ranked) >= 2:
    st.markdown("### Correlation (numeric)")
    corr = df[num_cols_ranked].corr().round(2)

    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale="Blues",
        zmin=-1,
        zmax=1,
        aspect="auto",
    )
    fig.update_layout(
        height=650,
        margin=dict(l=20, r=20, t=50, b=20),
        coloraxis_colorbar=dict(title="Correlation", thickness=14),
    )
    fig.update_xaxes(side="bottom", tickangle=45)
    fig.update_yaxes(autorange="reversed")

    st.plotly_chart(fig, use_container_width=True)

# =============================
# AI output (auto once per upload)
# =============================
file_sig = f"{uploaded.name}_{uploaded.size}_{source_sig}"
if ("ai_sig" not in st.session_state) or (st.session_state.ai_sig != file_sig):
    with st.spinner("Generating Executive Summary, Insights, and Suggested Next Analyses..."):
        st.session_state.ai_output = generate_ai_output(signals, ind, facts)
        st.session_state.ai_sig = file_sig

ai_output = st.session_state.ai_output
st.markdown(ai_output)

# =============================
# Export
# =============================
st.markdown("### Export")

exec_bullets = parse_exec_bullets(ai_output)
insights_bullets = parse_insights_bullets(ai_output)
analyses = parse_next_analyses_blocks(ai_output)

brief_title = f"EC-AI Insight Brief — {uploaded.name}"

pdf_bytes = build_pdf_bytes(brief_title, ind, exec_bullets, insights_bullets, analyses)
st.download_button(
    label="📄 Download Executive Brief (PDF)",
    data=pdf_bytes,
    file_name="ecai_insight_executive_brief.pdf",
    mime="application/pdf",
)

pptx_bytes = build_pptx_bytes(brief_title, ind, exec_bullets, insights_bullets, analyses)
if pptx_bytes:
    st.download_button(
        label="📊 Download Slides (PPTX)",
        data=pptx_bytes,
        file_name="ecai_insight_slides.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
else:
    st.caption("Slides export requires `python-pptx`. Add it to requirements.txt to enable PPTX download.")

# =============================
# Product hooks (placeholder links)
# =============================
st.markdown("---")
st.markdown("### Next: EC-AI Product Suite")

p1, p2, p3 = st.columns(3)

with p1:
    st.markdown("#### EC Predict")
    st.caption("Forecasting & prediction (time-series, drivers, what-if).")
    st.link_button("Open EC Predict (coming soon)", "https://ecai.com.hk")

with p2:
    st.markdown("#### EC Automate")
    st.caption("Automation workflows (cleaning, refresh, reporting).")
    st.link_button("Open EC Automate (coming soon)", "https://ecai.com.hk")

with p3:
    st.markdown("#### EC Optimize")
    st.caption("Optimization & KPI improvement suggestions.")
    st.link_button("Open EC Optimize (coming soon)", "https://ecai.com.hk")

st.caption("Note: Demo/testing only. Avoid uploading confidential or regulated data.")
