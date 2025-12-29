import os
import io
import pandas as pd
import numpy as np
import streamlit as st

import matplotlib.pyplot as plt
import plotly.express as px

from dotenv import load_dotenv
load_dotenv()

# ---- Optional: OpenAI (for AI insights text) ----
USE_AI = True
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def basic_profile(df: pd.DataFrame) -> pd.DataFrame:
    profile = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "missing_pct": (df.isna().mean() * 100).round(2),
        "n_unique": [df[c].nunique(dropna=True) for c in df.columns],
    })
    return profile.sort_values(["missing_pct", "n_unique"], ascending=[False, False])

def df_overview_text(df: pd.DataFrame) -> str:
    n_rows, n_cols = df.shape
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in df.columns if c not in num_cols]
    miss = (df.isna().mean() * 100).sort_values(ascending=False).head(5)

    lines = []
    lines.append(f"Rows: {n_rows:,} | Columns: {n_cols:,}")
    lines.append(f"Numeric columns: {len(num_cols)} | Categorical/other columns: {len(cat_cols)}")
    if len(miss) > 0:
        top_miss = ", ".join([f"{idx} ({val:.1f}%)" for idx, val in miss.items() if val > 0])
        if top_miss:
            lines.append(f"Top missing columns: {top_miss}")
    return "\n".join(lines)

def generate_ai_insights(df: pd.DataFrame) -> str:
    """
    Minimal, safe prompt: we only send column stats (not full data) to reduce leakage risk.
    """
    if not OPENAI_API_KEY:
        return "OPENAI_API_KEY not found. Add it to .env to enable AI insights."

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        profile = basic_profile(df).head(25)
        overview = df_overview_text(df)

        prompt = f"""
You are EC-AI Insight. Generate concise, business-friendly insights from the dataset profile only.
DO NOT ask for more data. DO NOT hallucinate.
Return:
1) 5 bullet insights
2) 3 recommended charts
3) 5 data quality checks

Dataset overview:
{overview}

Top columns profile (first 25):
{profile.to_csv(index=False)}
"""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise analytics assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return resp.choices[0].message.content

    except Exception as e:
        return f"AI insights error: {e}"

# ---- Streamlit UI ----
st.set_page_config(page_title="EC-AI Insight MVP", layout="wide")

st.markdown("## EC-AI Insight (MVP)")
st.caption("Turning Data Into Intelligence — Upload a CSV to get instant profiling + insights.")

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to begin.")
    st.stop()

# Load CSV (handles utf-8 + fallback)
try:
    df = pd.read_csv(uploaded)
except UnicodeDecodeError:
    df = pd.read_csv(uploaded, encoding="latin1")

st.success(f"Loaded dataset: {df.shape[0]:,} rows × {df.shape[1]:,} columns")

# Preview
with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(50), use_container_width=True)

# Profile table
st.markdown("### Data profile")
profile_df = basic_profile(df)
st.dataframe(profile_df, use_container_width=True, height=350)

# Charts
st.markdown("### Quick charts")

num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
cat_cols = [c for c in df.columns if c not in num_cols]

col1, col2 = st.columns(2)

with col1:
    if num_cols:
        chosen_num = st.selectbox("Numeric column (distribution)", num_cols)
        fig = px.histogram(df, x=chosen_num, nbins=30)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric columns detected.")

with col2:
    if cat_cols:
        chosen_cat = st.selectbox("Categorical column (top values)", cat_cols)
        vc = df[chosen_cat].astype(str).value_counts().head(20).reset_index()
        vc.columns = [chosen_cat, "count"]
        fig = px.bar(vc, x=chosen_cat, y="count")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No categorical columns detected (or all numeric).")

# Optional correlation
if len(num_cols) >= 2:
    st.markdown("### Correlation (numeric)")
    corr = df[num_cols].corr(numeric_only=True)
    fig = px.imshow(corr, text_auto=False, aspect="auto")
    st.plotly_chart(fig, use_container_width=True)

# AI insights
st.markdown("### AI Insights")
st.write("This generates insights from **column statistics only** (safer than sending full raw data).")

if st.button("Generate AI insights"):
    with st.spinner("Thinking..."):
        insights = generate_ai_insights(df) if USE_AI else "AI is disabled."
    st.markdown(insights)
