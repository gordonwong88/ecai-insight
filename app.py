import os
import re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# Optional local dev support; Streamlit Cloud uses st.secrets
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="EC-AI Insight MVP", layout="wide")

APP_TITLE = "EC-AI Insight (MVP)"
APP_TAGLINE = "Turning Data Into Intelligence — Upload a CSV to get instant profiling + insights."

# Prefer Streamlit Secrets, fallback to env
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip()


# -----------------------------
# Helpers: cleaning & profiling
# -----------------------------
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", "_", c.strip()) for c in df.columns]
    return df


def _coerce_numeric(df: pd.DataFrame, col: str) -> None:
    """
    Converts messy numeric columns (e.g., '(blank)', '', 'NA') to float with NaN.
    """
    df[col] = (
        df[col]
        .astype(str)
        .replace({"(blank)": "", "blank": "", "nan": "", "None": "", "NA": "", "N/A": ""})
    )
    df[col] = pd.to_numeric(df[col], errors="coerce")


def _coerce_date(df: pd.DataFrame, col: str) -> None:
    df[col] = pd.to_datetime(df[col], errors="coerce")


def smart_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Minimal, safe cleaning:
    - Normalize column names
    - Parse Date if column name contains 'date'
    - Convert obvious numeric columns to numeric (including Expected_Usage)
    """
    df = _normalize_columns(df)

    # Auto-detect date-ish columns
    for c in df.columns:
        if c.lower() == "date" or "date" in c.lower():
            _coerce_date(df, c)

    # Convert numeric-like columns (common finance fields)
    likely_numeric = {
        "Expected_Usage", "RoE_pct", "Revenue_USD",
        "DSC_Approved_Amount", "Actual_Loan_Outstanding",
        "Loan_Average_Balance", "Deposit_Average_Balance",
    }
    for c in df.columns:
        if c in likely_numeric:
            _coerce_numeric(df, c)

    # Also try to convert any object column that looks mostly numeric
    for c in df.select_dtypes(include=["object"]).columns:
        # if >70% values look numeric, convert
        sample = df[c].dropna().astype(str).head(200)
        if len(sample) == 0:
            continue
        numeric_like = sample.str.match(r"^\s*-?\d+(\.\d+)?\s*$").mean()
        if numeric_like >= 0.7:
            _coerce_numeric(df, c)

    return df


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

    miss = (df.isna().mean() * 100).sort_values(ascending=False).head(8)
    miss = miss[miss > 0]

    lines = []
    lines.append(f"Rows: {n_rows:,} | Columns: {n_cols:,}")
    lines.append(f"Numeric columns: {len(num_cols)} | Categorical/other columns: {len(cat_cols)}")
    if len(miss) > 0:
        top_miss = ", ".join([f"{idx} ({val:.1f}%)" for idx, val in miss.items()])
        lines.append(f"Top missing columns: {top_miss}")
    return "\n".join(lines)


def r_squared(x: pd.Series, y: pd.Series):
    valid = x.notna() & y.notna()
    if valid.sum() < 3:
        return None
    r = np.corrcoef(x[valid], y[valid])[0, 1]
    if np.isnan(r):
        return None
    return float(np.round(r ** 2, 3))


# -----------------------------
# OpenAI insights (stats-only)
# -----------------------------
def generate_ai_insights(df: pd.DataFrame) -> str:
    if not OPENAI_API_KEY or "YOUR_" in OPENAI_API_KEY.upper():
        return (
            "🔑 **OpenAI API key not configured**.\n\n"
            "1) Create/copy a real API key from the OpenAI developer platform\n"
            "2) Add it to Streamlit Cloud → App → **Settings → Secrets**:\n\n"
            "```toml\nOPENAI_API_KEY=\"sk-...\"\n```\n"
            "Then rerun and click **Generate AI insights** again."
        )

    # Only send profile + summary stats (no raw rows)
    prof = basic_profile(df).head(30)

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    stats = None
    if num_cols:
        stats = df[num_cols].describe().T
        stats = stats[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]].round(4).head(20)

    overview = df_overview_text(df)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt_parts = []
        prompt_parts.append("You are EC-AI Insight. Generate concise, business-friendly insights from dataset PROFILE ONLY.")
        prompt_parts.append("Do NOT hallucinate. If unsure, say 'insufficient information'.")
        prompt_parts.append("Return in markdown with these sections:")
        prompt_parts.append("## Executive summary (3 bullets)")
        prompt_parts.append("## Key patterns (5 bullets)")
        prompt_parts.append("## Data quality checks (5 bullets)")
        prompt_parts.append("## Suggested next analyses (3 bullets)")
        prompt_parts.append("")
        prompt_parts.append("Dataset overview:")
        prompt_parts.append(overview)
        prompt_parts.append("")
        prompt_parts.append("Top columns profile (first 30):")
        prompt_parts.append(prof.to_csv(index=False))

        if stats is not None:
            prompt_parts.append("")
            prompt_parts.append("Numeric summary stats (top 20 numeric cols):")
            prompt_parts.append(stats.to_csv())

        prompt = "\n".join(prompt_parts)

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise analytics assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content

    except Exception as e:
        return f"AI insights error: {e}"


# -----------------------------
# UI
# -----------------------------
st.markdown(f"## {APP_TITLE}")
st.caption(APP_TAGLINE)

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to begin.")
    st.stop()

# Load CSV with encoding fallback
try:
    df_raw = pd.read_csv(uploaded)
except UnicodeDecodeError:
    df_raw = pd.read_csv(uploaded, encoding="latin1")

df = smart_clean(df_raw)

st.success(f"Loaded dataset: {df.shape[0]:,} rows × {df.shape[1]:,} columns")

# Preview
with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(50), use_container_width=True)

# Profile
st.markdown("### Data profile (post-clean)")
profile_df = basic_profile(df)
st.dataframe(profile_df, use_container_width=True, height=360)

# Quick charts (more sensible for small N)
st.markdown("### Quick charts")

num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
cat_cols = [c for c in df.columns if c not in num_cols]

c1, c2 = st.columns(2)

with c1:
    if num_cols:
        chosen_num = st.selectbox("Numeric column", num_cols, key="numcol")
        if len(df) > 100:
            fig = px.histogram(df, x=chosen_num, nbins=30)
        else:
            fig = px.box(df, y=chosen_num, points="all")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric columns detected.")

with c2:
    if cat_cols:
        chosen_cat = st.selectbox("Categorical column (top values)", cat_cols, key="catcol")
        vc = df[chosen_cat].astype(str).value_counts().head(20).reset_index()
        vc.columns = [chosen_cat, "count"]
        fig = px.bar(vc, x=chosen_cat, y="count", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No categorical columns detected (or all numeric).")

# Business breakdown
st.markdown("### Business breakdown")
dims = [d for d in ["Country", "Industry", "Client_Size"] if d in df.columns]
metrics = [m for m in ["Revenue_USD", "DSC_Approved_Amount", "Actual_Loan_Outstanding", "RoE_pct"] if m in df.columns]

if dims and metrics:
    group_dim = st.selectbox("Group by", dims, key="groupby")
    metric = st.selectbox("Metric", metrics, key="metric")

    agg_choice = st.radio("Aggregation", ["Mean", "Sum"], horizontal=True)
    if agg_choice == "Sum":
        grp_df = df.groupby(group_dim, dropna=False)[metric].sum().reset_index()
    else:
        grp_df = df.groupby(group_dim, dropna=False)[metric].mean().reset_index()

    grp_df = grp_df.sort_values(metric, ascending=False)

    fig = px.bar(grp_df, x=group_dim, y=metric, text_auto=".2s")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Business breakdown will appear when Country/Industry/Client_Size and metrics columns exist.")

# Correlation
if len(num_cols) >= 2:
    st.markdown("### Correlation (numeric)")
    corr = df[num_cols].corr(numeric_only=True).round(2)

    fig = px.imshow(
        corr,
        text_auto=True,          # show numbers on each box
        aspect="auto",
        color_continuous_scale="Blues",
        zmin=-1, zmax=1
    )
    st.plotly_chart(fig, use_container_width=True)

    # R² section
    st.markdown("### Key R² relationships (selected pairs)")
    candidate_pairs = []
    # Common finance pairs if present:
    if "DSC_Approved_Amount" in df.columns and "Actual_Loan_Outstanding" in df.columns:
        candidate_pairs.append(("DSC_Approved_Amount", "Actual_Loan_Outstanding"))
    if "Actual_Loan_Outstanding" in df.columns and "Revenue_USD" in df.columns:
        candidate_pairs.append(("Actual_Loan_Outstanding", "Revenue_USD"))
    if "DSC_Approved_Amount" in df.columns and "Revenue_USD" in df.columns:
        candidate_pairs.append(("DSC_Approved_Amount", "Revenue_USD"))
    if "RoE_pct" in df.columns and "Revenue_USD" in df.columns:
        candidate_pairs.append(("RoE_pct", "Revenue_USD"))

    if not candidate_pairs:
        st.caption("Tip: Add named finance columns (Revenue_USD, DSC_Approved_Amount, etc.) to show R² highlights.")
    else:
        for a, b in candidate_pairs:
            r2 = r_squared(df[a], df[b])
            if r2 is None:
                st.write(f"**{a} → {b}** : R² = (insufficient data)")
            else:
                st.write(f"**{a} → {b}** : R² = **{r2}**")

# AI Insights
st.markdown("### AI Insights")
st.caption("Generates insights from **profile + summary statistics only** (safer than sending full raw data).")

if st.button("Generate AI insights"):
    with st.spinner("Generating insights..."):
        insights = generate_ai_insights(df)
    st.markdown(insights)

