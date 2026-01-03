import os
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# =============================
# Page config
# =============================
st.set_page_config(
    page_title="EC-AI Insight",
    layout="wide"
)

APP_TITLE = "EC-AI Insight"
APP_TAGLINE = "Upload any dataset. Get an executive understanding. Know what to analyze next."

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "").strip()

# =============================
# Utility functions
# =============================
def normalize_columns(df):
    df = df.copy()
    df.columns = [re.sub(r"\s+", "_", c.strip()) for c in df.columns]
    return df


def smart_clean(df):
    df = normalize_columns(df)

    # Parse date-like columns
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


def basic_profile(df):
    return pd.DataFrame({
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "missing_%": (df.isna().mean() * 100).round(2),
        "unique_values": [df[c].nunique(dropna=True) for c in df.columns]
    }).sort_values("missing_%", ascending=False)


# =============================
# Signal extraction (core logic)
# =============================
def extract_analysis_signals(df):
    signals = {
        "row_count": len(df),
        "column_count": df.shape[1],
        "numeric_columns": [],
        "categorical_columns": [],
        "strong_relationships": [],
        "high_variance_metrics": [],
        "has_time_dimension": False,
        "data_quality_flags": []
    }

    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    date_cols = [c for c in df.columns if np.issubdtype(df[c].dtype, np.datetime64)]
    cat_cols = [c for c in df.columns if c not in num_cols and c not in date_cols]

    signals["numeric_columns"] = num_cols
    signals["categorical_columns"] = cat_cols
    signals["has_time_dimension"] = len(date_cols) > 0

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

    # Data quality
    for c in df.columns:
        miss = df[c].isna().mean()
        if miss >= 0.15:
            signals["data_quality_flags"].append(
                f"{c} has {round(miss*100,1)}% missing values"
            )

    return signals


# =============================
# AI Insights
# =============================
def generate_ai_insights(signals):
    if not OPENAI_API_KEY:
        return "⚠️ OpenAI API key not configured."

    analysis_context = f"""
Dataset size:
Rows = {signals['row_count']}
Columns = {signals['column_count']}

Numeric columns:
{signals['numeric_columns']}

Categorical columns:
{signals['categorical_columns']}

Strong numeric relationships (R² ≥ 0.6):
{signals['strong_relationships']}

High variance numeric metrics:
{signals['high_variance_metrics']}

Time dimension present:
{signals['has_time_dimension']}

Data quality flags:
{signals['data_quality_flags']}
"""

    prompt = f"""
You are EC-AI Insight, an executive analytics advisor.

Your job is to:
- Summarize what the data structurally reveals
- Highlight what matters most
- Recommend where analysis effort should focus next

STRICT RULES:
- Base all statements ONLY on the provided signals
- Do NOT assume industry or business context
- Do NOT predict future outcomes
- Do NOT invent variables or benchmarks

OUTPUT FORMAT (MANDATORY):

## Executive Summary
Provide 7–10 concise bullet points.
Each bullet should reflect:
- data readiness
- structural patterns
- variability
- relationships
- analytical opportunities
Write in professional, executive-level language.

## Suggested next analyses
Provide EXACTLY 3 items.
Each item must include:
1) Analysis name
2) Why it is relevant (cite signal)
3) What decision or insight it would enable

DATASET SIGNALS:
{analysis_context}
"""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise, non-speculative analytics advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return resp.choices[0].message.content

    except Exception as e:
        return f"AI insight error: {e}"


# =============================
# UI
# =============================
st.markdown(f"## {APP_TITLE}")
st.caption(APP_TAGLINE)

uploaded = st.file_uploader("Upload CSV file", type=["csv"])

if not uploaded:
    st.info("Upload a CSV file to begin.")
    st.stop()

df_raw = pd.read_csv(uploaded)
df = smart_clean(df_raw)

st.success(f"Loaded dataset: {df.shape[0]:,} rows × {df.shape[1]:,} columns")

# Preview
with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(50), use_container_width=True)

# Data profile
st.markdown("### Data profile")
st.dataframe(basic_profile(df), use_container_width=True, height=360)

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

with c2:
    if cat_cols:
        col = st.selectbox("Categorical column", cat_cols)
        vc = df[col].astype(str).value_counts().head(20).reset_index()
        vc.columns = [col, "count"]
        fig = px.bar(vc, x=col, y="count", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

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

# =============================
# AI Insights (auto, once per upload)
# =============================
signals = extract_analysis_signals(df)
file_sig = f"{uploaded.name}_{uploaded.size}"

if "ai_sig" not in st.session_state or st.session_state.ai_sig != file_sig:
    with st.spinner("Generating executive summary and recommendations..."):
        st.session_state.ai_output = generate_ai_insights(signals)
        st.session_state.ai_sig = file_sig

st.markdown(st.session_state.ai_output)
