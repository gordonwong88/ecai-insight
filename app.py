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
# Cleaning helpers
# -----------------------------
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", "_", c.strip()) for c in df.columns]
    return df


def _coerce_numeric(df: pd.DataFrame, col: str) -> None:
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
    - Parse date-like columns
    - Convert numeric-like columns (including those with blanks)
    """
    df = _normalize_columns(df)

    # Parse date-ish columns by name
    for c in df.columns:
        lc = c.lower()
        if lc == "date" or "date" in lc or "asof" in lc or "as_of" in lc:
            _coerce_date(df, c)

    # Convert any object column that looks mostly numeric
    for c in df.select_dtypes(include=["object"]).columns:
        sample = df[c].dropna().astype(str).head(300)
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
    cat_cols = [c for c in df.columns if c not in num_cols and not np.issubdtype(df[c].dtype, np.datetime64)]

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
# Smart detection (semantic mapping)
# -----------------------------
KEYWORDS = {
    # Metrics
    "approved_amount": ["approved", "approval", "limit", "commit", "committed", "facility", "dsc", "sanction", "credit_limit"],
    "outstanding":     ["outstanding", "os", "balance", "loan_balance", "drawn", "utilized", "exposure", "ead", "used"],
    "revenue":         ["revenue", "income", "fee", "fees", "gop", "nop", "profit", "pnl", "tb", "gm", "net_income"],
    "roe":             ["roe", "return_on_equity", "return", "ror", "raroc"],
    "usage":           ["usage", "util", "utilisation", "utilization", "expected_usage", "expected", "draw_ratio", "drawdown"],

    # Dimensions
    "country":         ["country", "market", "geo", "geography", "location", "office", "region"],
    "industry":        ["industry", "sector", "subsector", "sub_sector"],
    "client_size":     ["client_size", "size", "segment", "tier", "sme", "mid", "large"],
    "status":          ["status", "approval_status", "stage", "state", "decision"],
}


def _score_column(colname: str, keywords: list[str]) -> int:
    s = 0
    lc = colname.lower()
    for kw in keywords:
        if kw in lc:
            s += 3
    return s


def detect_columns(df: pd.DataFrame):
    cols = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = [c for c in cols if np.issubdtype(df[c].dtype, np.datetime64)]
    cat_cols = [c for c in cols if c not in numeric_cols and c not in datetime_cols]

    suggestions = {}

    # Metrics: choose among numeric columns
    for key in ["approved_amount", "outstanding", "revenue", "roe", "usage"]:
        best, best_score = None, -1
        for c in numeric_cols:
            score = _score_column(c, KEYWORDS[key])

            # Bias for amount-like columns: large scale
            if key in ("approved_amount", "outstanding", "revenue"):
                try:
                    med = float(df[c].median(skipna=True))
                    if med >= 1e6:
                        score += 1
                except Exception:
                    pass

            # Bias for ratio-like columns: around 0-1 or 0-100
            if key in ("roe", "usage"):
                try:
                    med = float(df[c].median(skipna=True))
                    if -5 <= med <= 5 or 0 <= med <= 100:
                        score += 1
                except Exception:
                    pass

            if score > best_score:
                best_score = score
                best = c

        suggestions[key] = best if best_score > 0 else None

    # Dims: choose among categorical columns
    for key in ["country", "industry", "client_size", "status"]:
        best, best_score = None, -1
        for c in cat_cols:
            score = _score_column(c, KEYWORDS[key])
            # bias: dims often have low/moderate cardinality
            try:
                nu = int(df[c].nunique(dropna=True))
                if 2 <= nu <= 50:
                    score += 1
            except Exception:
                pass
            if score > best_score:
                best_score = score
                best = c
        suggestions[key] = best if best_score > 0 else None

    # Date
    suggestions["date"] = datetime_cols[0] if datetime_cols else None
    suggestions["_numeric_cols"] = numeric_cols
    suggestions["_cat_cols"] = cat_cols
    return suggestions


# -----------------------------
# OpenAI insights (stats-only)
# -----------------------------
def generate_ai_insights(df: pd.DataFrame, mapping: dict) -> str:
    if not OPENAI_API_KEY:
        return (
            "🔑 **OpenAI API key not configured**.\n\n"
            "Add your key in Streamlit Cloud → App → **Settings → Secrets**:\n\n"
            "```toml\nOPENAI_API_KEY=\"sk-...\"\n```"
        )

    prof = basic_profile(df).head(30)

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    stats = None
    if num_cols:
        stats = df[num_cols].describe().T
        stats = stats[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]].round(4).head(25)

    overview = df_overview_text(df)
    mapping_text = "\n".join([f"- {k}: {v}" for k, v in mapping.items() if v])

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""
You are EC-AI Insight. Generate concise, business-friendly insights from dataset PROFILE ONLY.
Do NOT hallucinate. If unsure, say 'insufficient information'.
Return in markdown with these sections:
## Executive summary (3 bullets)
## Key patterns (5 bullets)
## Business view (by key dimension)
## Data quality checks (5 bullets)
## Suggested next analyses (3 bullets)

Dataset overview:
{overview}

Detected mapping (may be user-adjusted):
{mapping_text}

Top columns profile (first 30):
{prof.to_csv(index=False)}

Numeric summary stats (top numeric cols):
{stats.to_csv() if stats is not None else "No numeric columns."}
"""

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
# Auto-run guard (only once per file)
# -----------------------------
def get_file_signature(uploaded_file) -> str:
    # Good enough for MVP; avoids re-calling AI on every rerun
    return f"{uploaded_file.name}_{uploaded_file.size}"


# -----------------------------
# UI
# -----------------------------
st.markdown(f"## {APP_TITLE}")
st.caption(APP_TAGLINE)

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to begin.")
    st.stop()

try:
    df_raw = pd.read_csv(uploaded)
except UnicodeDecodeError:
    df_raw = pd.read_csv(uploaded, encoding="latin1")

df = smart_clean(df_raw)
suggest = detect_columns(df)

st.success(f"Loaded dataset: {df.shape[0]:,} rows × {df.shape[1]:,} columns")


# -----------------------------
# Sidebar mapping (Smart + Override)
# -----------------------------
st.sidebar.markdown("## Mapping")
st.sidebar.caption("Auto-detected fields. Override if your column names differ.")

numeric_cols = suggest["_numeric_cols"]
cat_cols = suggest["_cat_cols"]
date_col = suggest["date"]

def pick_default(options, default):
    if default in options:
        return options.index(default)
    return 0

dim_options = ["(none)"] + cat_cols
metric_options = ["(none)"] + numeric_cols

country_col = st.sidebar.selectbox("Country / Region", dim_options, index=pick_default(dim_options, suggest["country"]))
industry_col = st.sidebar.selectbox("Industry / Sector", dim_options, index=pick_default(dim_options, suggest["industry"]))
size_col = st.sidebar.selectbox("Client size / Segment", dim_options, index=pick_default(dim_options, suggest["client_size"]))
status_col = st.sidebar.selectbox("Status / Stage", dim_options, index=pick_default(dim_options, suggest["status"]))

approved_col = st.sidebar.selectbox("Approved / Limit amount", metric_options, index=pick_default(metric_options, suggest["approved_amount"]))
outstanding_col = st.sidebar.selectbox("Outstanding / Balance", metric_options, index=pick_default(metric_options, suggest["outstanding"]))
revenue_col = st.sidebar.selectbox("Revenue / Income", metric_options, index=pick_default(metric_options, suggest["revenue"]))
roe_col = st.sidebar.selectbox("RoE / Return", metric_options, index=pick_default(metric_options, suggest["roe"]))
usage_col = st.sidebar.selectbox("Usage / Utilization", metric_options, index=pick_default(metric_options, suggest["usage"]))

def none_to_none(x):
    return None if x == "(none)" else x

mapping = {
    "date": date_col,
    "country": none_to_none(country_col),
    "industry": none_to_none(industry_col),
    "client_size": none_to_none(size_col),
    "status": none_to_none(status_col),
    "approved_amount": none_to_none(approved_col),
    "outstanding": none_to_none(outstanding_col),
    "revenue": none_to_none(revenue_col),
    "roe": none_to_none(roe_col),
    "usage": none_to_none(usage_col),
}

st.sidebar.markdown("---")
st.sidebar.caption("Tip: If charts look odd, adjust mapping (e.g., choose the right revenue column).")


# Preview
with st.expander("Preview data", expanded=True):
    st.dataframe(df.head(50), use_container_width=True)

# Profile
st.markdown("### Data profile (post-clean)")
profile_df = basic_profile(df)
st.dataframe(profile_df, use_container_width=True, height=360)


# Quick charts
st.markdown("### Quick charts")

num_cols2 = df.select_dtypes(include=[np.number]).columns.tolist()
datetime_cols = [c for c in df.columns if np.issubdtype(df[c].dtype, np.datetime64)]
cat_cols2 = [c for c in df.columns if c not in num_cols2 and c not in datetime_cols]

c1, c2 = st.columns(2)

with c1:
    if num_cols2:
        chosen_num = st.selectbox("Numeric column", num_cols2, key="numcol")
        if len(df) > 100:
            fig = px.histogram(df, x=chosen_num, nbins=30)
        else:
            fig = px.box(df, y=chosen_num, points="all")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No numeric columns detected.")

with c2:
    if cat_cols2:
        chosen_cat = st.selectbox("Categorical column (top values)", cat_cols2, key="catcol")
        vc = df[chosen_cat].astype(str).value_counts().head(20).reset_index()
        vc.columns = [chosen_cat, "count"]
        fig = px.bar(vc, x=chosen_cat, y="count", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No categorical columns detected (or all numeric / dates).")


# Business breakdown (semantic-driven)
st.markdown("### Business breakdown (smart)")

dims = [mapping["country"], mapping["industry"], mapping["client_size"], mapping["status"]]
dims = [d for d in dims if d and d in df.columns]

metrics = [mapping["revenue"], mapping["approved_amount"], mapping["outstanding"], mapping["roe"], mapping["usage"]]
metrics = [m for m in metrics if m and m in df.columns]

if dims and metrics:
    group_dim = st.selectbox("Group by", dims, key="groupby")
    metric = st.selectbox("Metric", metrics, key="metric")

    amount_like = {mapping["revenue"], mapping["approved_amount"], mapping["outstanding"]}
    default_agg = "Sum" if metric in amount_like else "Mean"

    agg_choice = st.radio(
        "Aggregation",
        ["Mean", "Sum"],
        horizontal=True,
        index=0 if default_agg == "Mean" else 1
    )

    if agg_choice == "Sum":
        grp_df = df.groupby(group_dim, dropna=False)[metric].sum().reset_index()
    else:
        grp_df = df.groupby(group_dim, dropna=False)[metric].mean().reset_index()

    grp_df = grp_df.sort_values(metric, ascending=False)
    fig = px.bar(grp_df, x=group_dim, y=metric, text_auto=".2s")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("To show business breakdown, map at least 1 dimension (e.g., Country) and 1 metric (e.g., Revenue). Use the sidebar Mapping panel.")


# Correlation + R²
if len(num_cols2) >= 2:
    st.markdown("### Correlation (numeric)")
    corr = df[num_cols2].corr(numeric_only=True).round(2)
    fig = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Blues",
        zmin=-1, zmax=1
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Key R² relationships (smart)")
    candidates = []
    if mapping["approved_amount"] and mapping["outstanding"]:
        candidates.append((mapping["approved_amount"], mapping["outstanding"]))
    if mapping["outstanding"] and mapping["revenue"]:
        candidates.append((mapping["outstanding"], mapping["revenue"]))
    if mapping["approved_amount"] and mapping["revenue"]:
        candidates.append((mapping["approved_amount"], mapping["revenue"]))
    if mapping["usage"] and mapping["outstanding"]:
        candidates.append((mapping["usage"], mapping["outstanding"]))
    if mapping["roe"] and mapping["revenue"]:
        candidates.append((mapping["roe"], mapping["revenue"]))

    uniq = []
    for a, b in candidates:
        if a in df.columns and b in df.columns and (a, b) not in uniq:
            uniq.append((a, b))

    if not uniq:
        st.caption("Map key metrics in the sidebar (Approved/Outstanding/Revenue/Usage/RoE) to see meaningful R² highlights.")
    else:
        for a, b in uniq:
            r2 = r_squared(df[a], df[b])
            if r2 is None:
                st.write(f"**{a} → {b}** : R² = (insufficient data)")
            else:
                st.write(f"**{a} → {b}** : R² = **{r2}**")


# -----------------------------
# AI Insights (AUTO, no click)
# -----------------------------
st.markdown("### AI Insights")
st.caption("Auto-generated from **profile + summary statistics only** (safer than sending full raw data).")

file_sig = get_file_signature(uploaded)

# Initialize state
if "ai_insights" not in st.session_state:
    st.session_state.ai_insights = None
    st.session_state.ai_sig = None
    st.session_state.ai_mapping_sig = None

# Optional: also re-run if mapping changed materially
mapping_sig = str(mapping)

should_run = (st.session_state.ai_sig != file_sig) or (st.session_state.ai_mapping_sig != mapping_sig)

if should_run:
    with st.spinner("Generating AI insights..."):
        st.session_state.ai_insights = generate_ai_insights(df, mapping)
        st.session_state.ai_sig = file_sig
        st.session_state.ai_mapping_sig = mapping_sig

# Display
st.markdown(st.session_state.ai_insights or "No insights yet.")
