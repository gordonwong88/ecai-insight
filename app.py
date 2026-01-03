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
APP_TAGLINE = "Upload any dataset. Get an executive understanding. Know what to analyze next."

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()

# =============================
# Utility functions
# =============================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", "_", c.strip()) for c in df.columns]
    return df


def smart_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)

    # Parse date-like columns by name
    for c in df.columns:
        if "date" in c.lower() or "asof" in c.lower():
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Convert numeric-like object columns
    for c in df.select_dtypes(include="object").columns:
        sample = df[c].dropna().astype(str).head(300)
        if len(sample) == 0:
            continue
        numeric_ratio = sample.str.match(r"^\s*-?\d+(\.\d+)?\s*$").mean()
        if numeric_ratio >= 0.7:
            df[c] = (
                df[c]
                .astype(str)
                .replace({"(blank)": "", "NA": "", "N/A": "", "None": ""})
            )
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def basic_profile(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "missing_%": (df.isna().mean() * 100).round(2),
        "unique_values": [df[c].nunique(dropna=True) for c in df.columns]
    }).sort_values("missing_%", ascending=False)


# =============================
# Signal extraction (core logic)
# =============================
def extract_analysis_signals(df: pd.DataFrame) -> dict:
    signals = {
        "row_count": len(df),
        "column_count": df.shape[1],
        "numeric_columns": [],
        "categorical_columns": [],
        "date_columns": [],
        "strong_relationships": [],
        "high_variance_metrics": [],
        "data_quality_flags": []
    }

    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    date_cols = [c for c in df.columns if np.issubdtype(df[c].dtype, np.datetime64)]
    cat_cols = [c for c in df.columns if c not in num_cols and c not in date_cols]

    signals["numeric_columns"] = num_cols
    signals["categorical_columns"] = cat_cols
    signals["date_columns"] = date_cols

    # Strong relationships (R²)
    for i in range(len(num_cols)):
        for j in range(i + 1, len(num_cols)):
            a, b = num_cols[i], num_cols[j]
            valid = df[a].notna() & df[b].notna()
            if valid.sum() < 10:
                continue
            r = np.corrcoef(df.loc[valid, a], df.loc[valid, b])[0, 1]
            if not np.isnan(r):
                r2 = r ** 2
                if r2 >= 0.6:
                    signals["strong_relationships"].append({
                        "x": a,
                        "y": b,
                        "r2": round(float(r2), 2)
                    })

    # High variance metrics (CV)
    for c in num_cols:
        mean = df[c].mean(skipna=True)
        std = df[c].std(skipna=True)
        if mean and not np.isnan(mean):
            cv = abs(std / mean)
            if cv >= 0.5:
                signals["high_variance_metrics"].append(c)

    # Data quality flags
    for c in df.columns:
        miss = df[c].isna().mean()
        if miss >= 0.15:
            signals["data_quality_flags"].append(
                f"{c} has {round(miss*100,1)}% missing values"
            )

    return signals


def compute_coverage_and_confidence(df: pd.DataFrame, signals: dict) -> dict:
    # Coverage: overall completeness
    missing_avg = float(df.isna().mean().mean())  # 0..1
    coverage = max(0.0, min(1.0, 1.0 - missing_avg))

    # Confidence (heuristic score 0..100)
    rows = signals["row_count"]
    num_n = len(signals["numeric_columns"])
    cat_n = len(signals["categorical_columns"])
    rel_n = len(signals["strong_relationships"])
    has_time = len(signals["date_columns"]) > 0

    # Row score
    if rows < 30:
        row_score = 0.25
    elif rows < 100:
        row_score = 0.55
    elif rows < 500:
        row_score = 0.80
    else:
        row_score = 1.00

    # Structure score (needs at least some numeric or categorical)
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

    # Relationship boost
    rel_score = 0.0
    if rel_n >= 5:
        rel_score = 1.0
    elif rel_n >= 2:
        rel_score = 0.7
    elif rel_n == 1:
        rel_score = 0.4
    else:
        rel_score = 0.0

    # Combine
    confidence = (
        0.45 * coverage +
        0.25 * row_score +
        0.20 * structure_score +
        0.10 * rel_score
    )
    confidence = int(round(confidence * 100))

    # Labels
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
# AI Insights
# =============================
def generate_ai_output(signals: dict, indicators: dict) -> str:
    if not OPENAI_API_KEY:
        return "⚠️ OpenAI API key not configured. Add it in Streamlit → Settings → Secrets."

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
- Coverage (overall completeness): {indicators['coverage_pct']}%
- Avg missing rate: {indicators['missing_avg_pct']}%
- Confidence score: {indicators['confidence_score']} ({indicators['confidence_label']})
"""

    prompt = f"""
You are EC-AI Insight, an executive analytics advisor.

STRICT RULES:
- Base all statements ONLY on the provided context
- Do NOT assume industry/business context
- Do NOT predict future outcomes
- Do NOT invent variables or benchmarks

OUTPUT FORMAT (MANDATORY):

## Executive Summary
Provide 7–10 concise bullet points.
- Must be grounded in the signals and indicators (coverage/confidence/relationships)
- Must be non-speculative and professional

## Suggested next analyses
Provide EXACTLY 3 items.
Each item must include:
1) Analysis name
2) Why it is relevant (explicitly reference signals)
3) What decision or insight it would enable

DATASET CONTEXT:
{analysis_context}
"""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are precise, non-speculative, and executive-grade."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI error: {e}"


def parse_sections(ai_text: str):
    """
    Extract Executive Summary bullets and Suggested next analyses section text (best-effort).
    """
    exec_bullets = []
    next_analyses_lines = []

    if not ai_text:
        return exec_bullets, ""

    lines = ai_text.splitlines()
    mode = None

    for line in lines:
        l = line.strip()
        if l.lower().startswith("## executive summary"):
            mode = "exec"
            continue
        if l.lower().startswith("## suggested next analyses"):
            mode = "next"
            continue

        if mode == "exec":
            if l.startswith(("-", "•")):
                exec_bullets.append(l.lstrip("-• ").strip())
            elif re.match(r"^\d+[\).\s]\s*", l):
                exec_bullets.append(re.sub(r"^\d+[\).\s]\s*", "", l).strip())

        if mode == "next":
            if l:
                next_analyses_lines.append(line)

    return exec_bullets, "\n".join(next_analyses_lines).strip()


# =============================
# Exporters
# =============================
def build_pdf_bytes(title: str, indicators: dict, exec_bullets: list[str], next_analyses_text: str) -> bytes:
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
    c.drawString(x, y, f"Coverage: {indicators['coverage_pct']}% | Avg Missing: {indicators['missing_avg_pct']}% | "
                       f"Confidence: {indicators['confidence_score']} ({indicators['confidence_label']})")
    y -= 0.5 * cm
    c.drawString(x, y, f"Numeric cols: {indicators['num_cols']} | Categorical cols: {indicators['cat_cols']} | "
                       f"Date cols: {indicators['date_cols']} | Strong pairs: {indicators['strong_pairs']}")

    # Executive Summary
    y -= 0.9 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Executive Summary")
    y -= 0.6 * cm
    c.setFont("Helvetica", 9)

    for i, b in enumerate(exec_bullets[:10], start=1):
        wrapped = wrap_text(f"{i}. {b}", 95)
        for wline in wrapped:
            if y < 2 * cm:
                c.showPage()
                y = height - 2 * cm
                c.setFont("Helvetica", 9)
            c.drawString(x, y, wline)
            y -= 0.45 * cm

    # Suggested next analyses
    y -= 0.3 * cm
    c.setFont("Helvetica-Bold", 11)
    if y < 2 * cm:
        c.showPage()
        y = height - 2 * cm
    c.drawString(x, y, "Suggested Next Analyses (Top 3)")
    y -= 0.6 * cm
    c.setFont("Helvetica", 9)

    for line in next_analyses_text.splitlines():
        if not line.strip():
            continue
        wrapped = wrap_text(line.strip(), 95)
        for wline in wrapped:
            if y < 2 * cm:
                c.showPage()
                y = height - 2 * cm
                c.setFont("Helvetica", 9)
            c.drawString(x, y, wline)
            y -= 0.45 * cm

    c.save()
    buffer.seek(0)
    return buffer.read()


def wrap_text(text: str, max_chars: int):
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


def build_pptx_bytes(title: str, indicators: dict, exec_bullets: list[str], next_analyses_text: str) -> bytes:
    """
    Slide export (PPTX). Uses python-pptx.
    If python-pptx isn't installed, return empty bytes and we show a message.
    """
    try:
        from pptx import Presentation
    except Exception:
        return b""

    prs = Presentation()

    # Slide 1 - Title
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = (
        f"Coverage: {indicators['coverage_pct']}% | Avg Missing: {indicators['missing_avg_pct']}%\n"
        f"Confidence: {indicators['confidence_score']} ({indicators['confidence_label']})"
    )

    # Slide 2 - Executive Summary
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Executive Summary"
    tf = slide.shapes.placeholders[1].text_frame
    tf.clear()
    for b in exec_bullets[:10]:
        p = tf.add_paragraph()
        p.text = b
        p.level = 0

    # Slide 3 - Suggested Next Analyses
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Suggested Next Analyses"
    tf = slide.shapes.placeholders[1].text_frame
    tf.clear()
    for line in next_analyses_text.splitlines():
        l = line.strip()
        if not l:
            continue
        p = tf.add_paragraph()
        p.text = l
        p.level = 0

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()


# =============================
# UI
# =============================
st.markdown(f"## {APP_TITLE}")
st.caption(APP_TAGLINE)

uploaded = st.file_uploader("Upload CSV file", type=["csv"])

if not uploaded:
    st.info("Upload a CSV file to begin.")
    st.stop()

try:
    df_raw = pd.read_csv(uploaded)
except UnicodeDecodeError:
    df_raw = pd.read_csv(uploaded, encoding="latin1")

df = smart_clean(df_raw)

st.success(f"Loaded dataset: {df.shape[0]:,} rows × {df.shape[1]:,} columns")

# Preview
with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(50), use_container_width=True)

# Data profile
st.markdown("### Data profile")
profile_df = basic_profile(df)
st.dataframe(profile_df, use_container_width=True, height=360)

# Signals + indicators
signals = extract_analysis_signals(df)
ind = compute_coverage_and_confidence(df, signals)

st.markdown("### Indicators")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Coverage", f"{ind['coverage_pct']}%")
m2.metric("Avg Missing", f"{ind['missing_avg_pct']}%")
m3.metric("Confidence", f"{ind['confidence_score']} ({ind['confidence_label']})")
m4.metric("Strong R² Pairs", f"{ind['strong_pairs']}")

st.progress(ind["confidence_score"] / 100)

# Quick exploration
st.markdown("### Quick exploration")
num_cols = df.select_dtypes(include=np.number).columns.tolist()
cat_cols = [c for c in df.columns if c not in num_cols and not np.issubdtype(df[c].dtype, np.datetime64)]

c1, c2 = st.columns(2)
with c1:
    if num_cols:
        col = st.selectbox("Numeric column", num_cols)
        fig = px.box(df, y=col, points="all") if len(df) < 100 else px.histogram(df, x=col)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric columns detected.")

with c2:
    if cat_cols:
        col = st.selectbox("Categorical column", cat_cols)
        vc = df[col].astype(str).value_counts().head(20).reset_index()
        vc.columns = [col, "count"]
        fig = px.bar(vc, x=col, y="count", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No categorical columns detected.")

# Correlation
if len(num_cols) >= 2:
    st.markdown("### Correlation (numeric)")
    corr = df[num_cols].corr().round(2)
    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale="Blues",
        zmin=-1,
        zmax=1
    )
    st.plotly_chart(fig, use_container_width=True)

# AI Output (auto, once per upload)
file_sig = f"{uploaded.name}_{uploaded.size}"

if "ai_sig" not in st.session_state or st.session_state.ai_sig != file_sig:
    with st.spinner("Generating Executive Summary and Suggested Next Analyses..."):
        st.session_state.ai_output = generate_ai_output(signals, ind)
        st.session_state.ai_sig = file_sig

ai_output = st.session_state.ai_output
st.markdown(ai_output)

# Exports
st.markdown("### Export")
exec_bullets, next_analyses_text = parse_sections(ai_output)

title = f"EC-AI Insight Brief — {uploaded.name}"

pdf_bytes = build_pdf_bytes(title, ind, exec_bullets, next_analyses_text)
st.download_button(
    label="📄 Download Executive Brief (PDF)",
    data=pdf_bytes,
    file_name="ecai_insight_executive_brief.pdf",
    mime="application/pdf"
)

pptx_bytes = build_pptx_bytes(title, ind, exec_bullets, next_analyses_text)
if pptx_bytes:
    st.download_button(
        label="📊 Download Slides (PPTX)",
        data=pptx_bytes,
        file_name="ecai_insight_slides.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
else:
    st.caption("Slides export requires `python-pptx`. Add it to requirements.txt to enable PPTX download.")

st.caption("Note: This app is for demo/testing. Please avoid uploading confidential or regulated data.")
