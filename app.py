# app.py
# EC-AI Insight (MVP) — single-file Streamlit app
# Fix included:
# ✅ StreamlitDuplicateElementId (Plotly) -> every chart now has a UNIQUE key via show_chart()

from __future__ import annotations

import io
import os
import re
import math
import json
import textwrap
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from scipy import stats

# --- Optional libraries for export ---
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    PPTX_OK = True
except Exception:
    PPTX_OK = False

# plotly image export requires kaleido
try:
    import plotly.io as pio
    _ = pio.to_image(go.Figure(), format="png")
    KALEIDO_OK = True
except Exception:
    KALEIDO_OK = False

# --- OpenAI ---
OPENAI_KEY = None
if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
elif os.getenv("OPENAI_API_KEY"):
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")


# ----------------------------
# Page config + styling
# ----------------------------
st.set_page_config(
    page_title="EC-AI Insight (MVP)",
    page_icon="📊",
    layout="wide",
)

# Color palettes (Plotly qualitative)
PALETTE_MAIN = px.colors.qualitative.Set2
PALETTE_ALT = px.colors.qualitative.Safe
PALETTE_BOLD = px.colors.qualitative.Bold

st.markdown(
    """
<style>
.small-note { color: #6b7280; font-size: 0.9rem; }
.section-title { margin-top: 0.25rem; }
hr { margin: 1.2rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------
# Plotly rendering helper (FIX)
# ----------------------------
def show_chart(fig: go.Figure, key: str):
    """Always render Plotly charts with a unique key to avoid StreamlitDuplicateElementId."""
    return st.plotly_chart(fig, use_container_width=True, key=key)


# ----------------------------
# Helpers: type detection
# ----------------------------
def _clean_colname(c: str) -> str:
    c = str(c).strip()
    c = re.sub(r"\s+", "_", c)
    return c

def load_table(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()
    bio = io.BytesIO(raw)

    if name.endswith(".csv"):
        try:
            df = pd.read_csv(bio)
        except Exception:
            bio.seek(0)
            df = pd.read_csv(bio, encoding="latin-1")
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(bio)
    else:
        raise ValueError("Unsupported file type. Please upload CSV or Excel (.xlsx/.xls).")

    df.columns = [_clean_colname(c) for c in df.columns]
    return df

def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    date_like = [c for c in out.columns if re.search(r"(date|time|day|month|year)", c, re.I)]
    for c in out.columns:
        if c in date_like or out[c].dtype == "object":
            try:
                parsed = pd.to_datetime(out[c], errors="coerce", infer_datetime_format=True, utc=False)
                if parsed.notna().mean() >= 0.4:
                    out[c] = parsed
            except Exception:
                pass

    for c in out.columns:
        if out[c].dtype == "object":
            s = out[c].astype(str).str.replace(",", "", regex=False)
            s = s.str.replace("$", "", regex=False)
            s = s.str.replace("%", "", regex=False)
            num = pd.to_numeric(s, errors="coerce")
            if num.notna().mean() >= 0.7:
                out[c] = num

    return out

def get_numeric_cols(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

def get_categorical_cols(df: pd.DataFrame) -> List[str]:
    cats = []
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_categorical_dtype(df[c]):
            nun = df[c].nunique(dropna=True)
            if 2 <= nun <= 50:
                cats.append(c)
    return cats

def get_datetime_cols(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

def pick_metric_candidates(df: pd.DataFrame, numeric_cols: List[str]) -> List[str]:
    priority_patterns = [
        r"revenue|sales|gmv|income",
        r"profit|margin|ebit|pnl",
        r"amount|approved|limit|outstanding|balance|exposure|loan",
        r"cost|cogs|expense|spend",
        r"units|qty|volume|count",
        r"rate|pct|percent|ratio|util|usage",
    ]
    scores = {c: 0 for c in numeric_cols}
    for c in numeric_cols:
        for i, pat in enumerate(priority_patterns):
            if re.search(pat, c, re.I):
                scores[c] = max(scores[c], 100 - i * 10)
    for c in numeric_cols:
        if scores[c] == 0:
            try:
                scores[c] = float(np.nanstd(df[c].values))
            except Exception:
                scores[c] = 1
    ranked = sorted(numeric_cols, key=lambda x: scores.get(x, 0), reverse=True)
    return ranked

def pick_primary_metric(df: pd.DataFrame) -> Optional[str]:
    nums = get_numeric_cols(df)
    if not nums:
        return None
    ranked = pick_metric_candidates(df, nums)
    return ranked[0] if ranked else None

def detect_best_dimension(df: pd.DataFrame, prefer_keywords: List[str]) -> Optional[str]:
    cats = get_categorical_cols(df)
    if not cats:
        return None
    for kw in prefer_keywords:
        for c in cats:
            if re.search(kw, c, re.I):
                return c
    cand = sorted(cats, key=lambda c: df[c].nunique(dropna=True))
    return cand[0] if cand else None

def format_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    ax = abs(float(x))
    if ax >= 1e9:
        return f"${x/1e9:.1f}B"
    if ax >= 1e6:
        return f"${x/1e6:.1f}M"
    if ax >= 1e3:
        return f"${x/1e3:.1f}K"
    return f"${x:.1f}"

def format_number(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    ax = abs(float(x))
    if ax >= 1e9:
        return f"{x/1e9:.1f}B"
    if ax >= 1e6:
        return f"{x/1e6:.1f}M"
    if ax >= 1e3:
        return f"{x/1e3:.1f}K"
    return f"{x:.1f}"


# ----------------------------
# Indicators logic
# ----------------------------
@dataclass
class Indicators:
    coverage: float
    avg_missing: float
    confidence_score: int
    strong_r2_pairs: int

def compute_indicators(df: pd.DataFrame) -> Indicators:
    total_cells = df.shape[0] * df.shape[1] if df.shape[0] and df.shape[1] else 0
    missing_cells = int(df.isna().sum().sum()) if total_cells else 0
    coverage = 100.0 * (1.0 - (missing_cells / total_cells)) if total_cells else 0.0

    miss_by_col = df.isna().mean() * 100.0 if df.shape[1] else pd.Series([], dtype=float)
    avg_missing = float(miss_by_col.mean()) if len(miss_by_col) else 0.0

    nums = get_numeric_cols(df)
    strong = 0
    if len(nums) >= 2:
        corr = df[nums].corr(method="pearson")
        r2 = corr**2
        m = r2.values
        for i in range(m.shape[0]):
            for j in range(i+1, m.shape[1]):
                if not np.isnan(m[i, j]) and m[i, j] >= 0.7:
                    strong += 1

    nrows, ncols = df.shape
    numeric_ratio = (len(get_numeric_cols(df)) / ncols) if ncols else 0
    date_bonus = 1 if len(get_datetime_cols(df)) > 0 else 0
    size_score = min(1.0, math.log10(max(nrows, 1) + 1) / 5.0)
    missing_score = max(0.0, 1.0 - avg_missing/40.0)
    richness_score = min(1.0, numeric_ratio*1.2 + 0.2*date_bonus)

    conf = int(round(100 * (0.45*size_score + 0.35*missing_score + 0.20*richness_score)))
    conf = max(5, min(98, conf))

    return Indicators(
        coverage=coverage,
        avg_missing=avg_missing,
        confidence_score=conf,
        strong_r2_pairs=strong,
    )

def confidence_label(score: int) -> str:
    if score >= 85:
        return f"{score} (High)"
    if score >= 65:
        return f"{score} (Medium)"
    return f"{score} (Low)"


# ----------------------------
# Correlation / R² explanation
# ----------------------------
def r2_strength_label(r2: float) -> str:
    if np.isnan(r2):
        return "n/a"
    if r2 < 0.10:
        return "Very weak"
    if r2 < 0.30:
        return "Weak"
    if r2 < 0.60:
        return "Moderate"
    if r2 < 0.80:
        return "Strong"
    return "Very strong"


# ----------------------------
# Plot helpers (colorful)
# ----------------------------
def bar_topk(df: pd.DataFrame, dim: str, metric: str, agg: str = "sum", k: int = 12) -> pd.DataFrame:
    g = df.groupby(dim, dropna=False)[metric]
    s = g.mean() if agg == "mean" else g.sum()
    out = s.sort_values(ascending=False).head(k).reset_index()
    out.columns = [dim, metric]
    return out

def fig_bar(df: pd.DataFrame, dim: str, metric: str, title: str, money: bool = False, top_k: int = 12) -> go.Figure:
    d = bar_topk(df, dim, metric, agg="sum", k=top_k)
    fig = px.bar(
        d,
        x=dim,
        y=metric,
        title=title,
        text=metric,
        color=dim,
        color_discrete_sequence=PALETTE_MAIN,
    )

    fig.update_traces(
        text=[format_money(v) if money else format_number(v) for v in d[metric].values],
        textposition="inside",
        hovertemplate=f"{dim}=%{{x}}<br>{metric}=%{{y:.2f}}<extra></extra>",
    )
    if money:
        fig.update_yaxes(title_text=metric, tickprefix="$")

    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=60, b=10), height=420)
    return fig

def fig_trend_total(df: pd.DataFrame, date_col: str, metric: str, money: bool = False) -> go.Figure:
    d = df[[date_col, metric]].dropna().copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        return go.Figure()

    d = d.groupby(pd.Grouper(key=date_col, freq="D"))[metric].sum().reset_index()
    fig = px.line(
        d,
        x=date_col,
        y=metric,
        title=f"{metric} trend (total)",
        markers=True,
        color_discrete_sequence=PALETTE_BOLD,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=420)
    if money:
        fig.update_yaxes(tickprefix="$")
    return fig

def fig_trend_by_dim(df: pd.DataFrame, date_col: str, dim: str, metric: str, top_n: int = 5, money: bool = False) -> go.Figure:
    d = df[[date_col, dim, metric]].dropna().copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        return go.Figure()

    totals = d.groupby(dim)[metric].sum().sort_values(ascending=False)
    keep = list(totals.head(top_n).index)
    d = d[d[dim].isin(keep)]

    d = d.groupby([pd.Grouper(key=date_col, freq="D"), dim])[metric].sum().reset_index()
    fig = px.line(
        d,
        x=date_col,
        y=metric,
        color=dim,
        markers=True,
        title=f"{metric} trend by {dim} (top {len(keep)})",
        color_discrete_sequence=PALETTE_MAIN,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=460, legend_title_text=dim)
    if money:
        fig.update_yaxes(tickprefix="$")
    return fig

def small_multiples_trend(df: pd.DataFrame, date_col: str, dim: str, metric: str, top_n: int = 5, money: bool = False) -> List[go.Figure]:
    d = df[[date_col, dim, metric]].dropna().copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        return []

    totals = d.groupby(dim)[metric].sum().sort_values(ascending=False)
    keep = list(totals.head(top_n).index)

    figs: List[go.Figure] = []
    for i, val in enumerate(keep):
        dd = d[d[dim] == val].copy()
        dd = dd.groupby(pd.Grouper(key=date_col, freq="D"))[metric].sum().reset_index()
        fig = px.line(
            dd,
            x=date_col,
            y=metric,
            markers=True,
            title=f"{metric} trend — {dim}: {val}",
            color_discrete_sequence=[PALETTE_MAIN[i % len(PALETTE_MAIN)]],
        )
        fig.update_layout(margin=dict(l=10, r=10, t=60, b=10), height=320, showlegend=False)
        if money:
            fig.update_yaxes(tickprefix="$")
        figs.append(fig)

    return figs

def fig_corr_r2(df: pd.DataFrame, numeric_cols: List[str]) -> go.Figure:
    corr = df[numeric_cols].corr(method="pearson")
    r2 = corr ** 2
    fig = go.Figure(
        data=go.Heatmap(
            z=r2.values,
            x=numeric_cols,
            y=numeric_cols,
            colorscale="Blues",
            zmin=0,
            zmax=1,
            hovertemplate="X=%{x}<br>Y=%{y}<br>R²=%{z:.2f}<extra></extra>",
            colorbar=dict(title="R²"),
        )
    )
    fig.update_layout(title="Correlation (R²)", margin=dict(l=10, r=10, t=60, b=10), height=520)
    return fig


# ----------------------------
# Narrative generation: rule-based insights
# ----------------------------
def build_profile_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        rows.append(
            {
                "column": c,
                "dtype": str(df[c].dtype),
                "missing_%": round(float(df[c].isna().mean() * 100.0), 1),
                "unique_values": int(df[c].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)

def executive_summary_points(df: pd.DataFrame, primary_metric: Optional[str], date_col: Optional[str], indicators: Indicators) -> List[str]:
    nrows, ncols = df.shape
    pts = []
    pts.append(f"Dataset size: {nrows:,} rows × {ncols:,} columns; overall coverage is {indicators.coverage:.1f}% with avg missing {indicators.avg_missing:.1f}%.")

    if primary_metric:
        s = df[primary_metric]
        pts.append(
            f"Primary metric detected: **{primary_metric}** (mean {format_number(float(np.nanmean(s)))}; median {format_number(float(np.nanmedian(s)))}; range {format_number(float(np.nanmin(s)))}–{format_number(float(np.nanmax(s)))})."
        )

    nums = get_numeric_cols(df)
    cats = get_categorical_cols(df)
    dts = get_datetime_cols(df)
    pts.append(f"Column mix: {len(nums)} numeric, {len(cats)} categorical (2–50 unique), {len(dts)} datetime.")

    if date_col:
        dmin = pd.to_datetime(df[date_col], errors="coerce").min()
        dmax = pd.to_datetime(df[date_col], errors="coerce").max()
        if pd.notna(dmin) and pd.notna(dmax):
            pts.append(f"Time coverage detected in **{date_col}** from {dmin.date()} to {dmax.date()}.")

    if indicators.strong_r2_pairs > 0:
        pts.append(f"Found **{indicators.strong_r2_pairs}** strong numeric relationships (R² ≥ 0.70) worth prioritising.")
    else:
        pts.append("No very-strong numeric relationships (R² ≥ 0.70) detected; focus may be more segment-driven or require feature engineering.")

    top_missing = (df.isna().mean().sort_values(ascending=False) * 100).head(3)
    if len(top_missing) and top_missing.iloc[0] > 0:
        missing_txt = ", ".join([f"{c} ({v:.1f}%)" for c, v in top_missing.items() if v > 0])
        if missing_txt:
            pts.append(f"Highest missing columns: {missing_txt}. Consider imputation/filters before deeper modelling.")
    else:
        pts.append("Missingness is minimal across the dataset, supporting stable descriptive analysis.")

    return pts[:10]

def key_insights_points(df: pd.DataFrame, primary_metric: Optional[str], date_col: Optional[str]) -> List[str]:
    pts = []
    if not primary_metric:
        return ["No numeric primary metric detected; upload data with at least one numeric column to generate insights."]

    moneyish = bool(re.search(r"revenue|sales|income|amount|profit|cost|cogs", primary_metric, re.I))

    cats = get_categorical_cols(df)
    best_dim = None
    best_spread = -1.0
    best_tbl = None
    for c in cats:
        g = df.groupby(c)[primary_metric].sum()
        if g.shape[0] < 2:
            continue
        spread = float((g.max() - g.min()) / (g.mean() + 1e-9))
        if spread > best_spread:
            best_spread = spread
            best_dim = c
            best_tbl = g.sort_values(ascending=False)

    if best_dim and best_tbl is not None:
        top = best_tbl.index[0]
        bot = best_tbl.index[-1]
        pts.append(f"Performance is most differentiated by **{best_dim}**: top segment is **{top}** with {format_money(best_tbl.iloc[0]) if moneyish else format_number(best_tbl.iloc[0])}; lowest is **{bot}** with {format_money(best_tbl.iloc[-1]) if moneyish else format_number(best_tbl.iloc[-1])}.")
        share_top = float(best_tbl.iloc[0] / (best_tbl.sum() + 1e-9))
        pts.append(f"Concentration check: top {best_dim} contributes about **{share_top*100:.1f}%** of total {primary_metric}.")
    else:
        pts.append("No suitable categorical cut detected (need 2–50 unique values) to produce segment insights.")

    if date_col:
        d = df[[date_col, primary_metric]].dropna().copy()
        d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
        d = d.dropna(subset=[date_col])
        if not d.empty:
            daily = d.groupby(pd.Grouper(key=date_col, freq="D"))[primary_metric].sum()
            if daily.shape[0] >= 7:
                slope = np.polyfit(np.arange(len(daily)), daily.values, 1)[0]
                direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
                pts.append(f"Trend read: total {primary_metric} shows an overall **{direction}** movement across the period (simple linear trend).")
                cv = float(np.nanstd(daily.values) / (np.nanmean(daily.values) + 1e-9))
                pts.append(f"Volatility: daily coefficient of variation is ~**{cv:.2f}** (higher means more day-to-day swings).")

    nums = get_numeric_cols(df)
    if len(nums) >= 2:
        corr = df[nums].corr(method="pearson")
        r2 = (corr**2).where(~np.eye(len(nums), dtype=bool))
        max_idx = np.unravel_index(np.nanargmax(r2.values), r2.shape)
        a = nums[max_idx[0]]
        b = nums[max_idx[1]]
        r2max = float(r2.values[max_idx])
        pts.append(f"Strongest numeric relationship: **{a} ↔ {b}** with **R²={r2max:.2f}** ({r2_strength_label(r2max)}). This can guide driver/forecast hypotheses (not causation).")

    return pts[:10]


# ----------------------------
# Suggested next analyses (OpenAI + fallback)
# ----------------------------
def openai_chat(prompt: str, model: str = "gpt-4o-mini") -> str:
    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY not set.")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a senior analytics consultant. Be concise but highly specific and actionable."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        pass

    import requests
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "You are a senior analytics consultant. Be concise but highly specific and actionable."},
            {"role": "user", "content": prompt},
        ],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=45)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def suggested_next_analyses_fallback(df: pd.DataFrame, primary_metric: str, date_col: Optional[str], dims: List[str]) -> List[Dict[str, str]]:
    dims = [d for d in dims if d]
    dim1 = dims[0] if len(dims) > 0 else "segment"
    dim2 = dims[1] if len(dims) > 1 else dim1

    recs = []
    recs.append({
        "title": f"{primary_metric} driver & segment performance deep-dive",
        "Business Context": f"Identify which {dim1} segments contribute most to {primary_metric} and whether performance is concentrated or broadly distributed. This supports targeted investment and helps surface underperforming segments that may need intervention.",
        "Risks": "Segment-level correlations can be distorted by mix effects. Validate with controls (time/channel/category) before acting.",
        "Outputs": [
            f"Contribution table for {dim1} (top/bottom, share of total)",
            "Variance / concentration summary",
            "Short narrative: what differentiates best vs worst segments",
        ],
    })

    if date_col:
        recs.append({
            "title": f"{primary_metric} trend & seasonality scan (with anomaly flags)",
            "Business Context": f"Understand whether {primary_metric} is growing, declining, or cyclical across the observed period, and which segments (e.g., {dim1}/{dim2}) drive changes. Useful for planning and forecasting readiness.",
            "Risks": "Short time windows can overfit false seasonality; outliers can dominate perception.",
            "Outputs": [
                "Total trend chart with markers",
                f"Segment trend charts by {dim1} / {dim2}",
                "Peak/trough + anomaly list (dates/segments)",
            ],
        })
    else:
        recs.append({
            "title": "Time dimension setup (to enable forecasting later)",
            "Business Context": "No clear date/time column detected. Adding a time index enables trend, seasonality, and forecasting value.",
            "Risks": "Mixed granularities or inconsistent date formats can create misleading trends.",
            "Outputs": [
                "Recommended date column mapping",
                "Standard granularity suggestion (daily/weekly/monthly)",
                "Validation checks for continuity",
            ],
        })

    recs.append({
        "title": "Price/discount effectiveness & margin sanity check",
        "Business Context": f"Assess whether pricing levers (discount rates, unit prices) are improving {primary_metric} or eroding profitability. Helps refine promotion rules and prevents over-discounting.",
        "Risks": "Observed uplift may come from selection bias. Confirm with segmentation and controlled tests where possible.",
        "Outputs": [
            "Metric by discount bands",
            "Comparison across key segments",
            "Recommendation on healthy vs erosive bands",
        ],
    })
    return recs[:3]

def suggested_next_analyses(df: pd.DataFrame, primary_metric: str, date_col: Optional[str], dims: List[str]) -> List[Dict[str, str]]:
    facts = {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "primary_metric": primary_metric,
        "datetime_cols": get_datetime_cols(df),
        "categorical_cols": get_categorical_cols(df)[:12],
        "numeric_cols": get_numeric_cols(df)[:12],
    }

    if not OPENAI_KEY:
        return suggested_next_analyses_fallback(df, primary_metric, date_col, dims)

    prompt = f"""
You are generating a 'Suggested next analyses' section for a data analytics app.

Constraints:
- Provide EXACTLY 3 suggestions.
- Each suggestion must include:
  1) Title
  2) Business Context (3-5 sentences, specific to the dataset)
  3) Risks (1-2 sentences)
  4) Outputs (2-4 bullet points, concrete deliverables)
- Keep wording crisp. Avoid generic fluff.
- Suggestions must align with what the app can realistically do next (trend, segmentation, driver analysis, sanity checks, variability, discount effectiveness, etc.).
- Use the dataset facts below. If a time column exists, include at least one trend/seasonality analysis.

Dataset facts (JSON):
{json.dumps(facts, indent=2)}

Return format MUST be valid JSON:
[
  {{"title": "...", "Business Context": "...", "Risks": "...", "Outputs": ["...","..."]}},
  ...
]
"""
    try:
        out = openai_chat(prompt, model="gpt-4o-mini")
        data = json.loads(out)
        cleaned = []
        for item in data[:3]:
            outputs = item.get("Outputs", [])
            if isinstance(outputs, str):
                outputs = [outputs]
            cleaned.append({
                "title": str(item.get("title", "")).strip(),
                "Business Context": str(item.get("Business Context", "")).strip(),
                "Risks": str(item.get("Risks", "")).strip(),
                "Outputs": [str(x).strip() for x in outputs if str(x).strip()],
            })
        if len(cleaned) == 3 and all(x["title"] for x in cleaned):
            return cleaned
    except Exception:
        pass

    return suggested_next_analyses_fallback(df, primary_metric, date_col, dims)


# ----------------------------
# 3 Analyses (auto runnable) with commentary
# ----------------------------
@dataclass
class AnalysisResult:
    title: str
    narrative_bullets: List[str]
    figs: List[go.Figure]

def analysis_driver_relationship(df: pd.DataFrame, metric: str, dims: List[str]) -> AnalysisResult:
    nums = get_numeric_cols(df)
    figs: List[go.Figure] = []
    bullets: List[str] = []

    if len(nums) >= 2:
        corr = df[nums].corr(method="pearson")
        r2 = corr**2
        other = None
        r2v = np.nan

        if metric in nums:
            cand = r2[metric].drop(index=metric, errors="ignore").sort_values(ascending=False)
            if len(cand):
                other = cand.index[0]
                r2v = float(cand.iloc[0])
        else:
            r2_mask = r2.where(~np.eye(len(nums), dtype=bool))
            idx = np.unravel_index(np.nanargmax(r2_mask.values), r2_mask.shape)
            metric = nums[idx[0]]
            other = nums[idx[1]]
            r2v = float(r2_mask.values[idx])

        if other:
            bullets.append(f"Top relationship found: **{metric} vs {other}** with **R²={r2v:.2f}** ({r2_strength_label(r2v)}).")
            bullets.append("Interpretation: higher R² means the variables move together more consistently; it does **not** prove causation.")
            bullets.append("Next step: segment this relationship by a key cut (Store/Channel/Category) to see where it strengthens or breaks.")

            d = df[[metric, other]].dropna()
            if not d.empty:
                fig = px.scatter(
                    d, x=other, y=metric, trendline="ols",
                    title=f"Driver view: {metric} vs {other} (with trendline)",
                    color_discrete_sequence=PALETTE_MAIN
                )
                fig.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10))
                figs.append(fig)

    dim = dims[0] if dims else None
    if dim and dim in df.columns and metric in df.columns:
        g = df.groupby(dim)[metric].sum().sort_values(ascending=False)
        if len(g) >= 2:
            bullets.append(f"Segment highlight: **{dim}** top is **{g.index[0]}** with {format_number(g.iloc[0])}.")
            bullets.append("Action idea: validate whether the top segment is driven by volume, price, or mix (compare with Units / Unit_Price if present).")

    return AnalysisResult(
        title="1) Revenue/Metric driver relationship scan",
        narrative_bullets=bullets[:6],
        figs=figs,
    )

def analysis_variability_by_best_cut(df: pd.DataFrame, metric: str) -> AnalysisResult:
    cats = get_categorical_cols(df)
    figs: List[go.Figure] = []
    bullets: List[str] = []

    best_dim = None
    best_cv = -1.0
    best_tbl = None

    for c in cats:
        g = df.groupby(c)[metric]
        if g.size().min() < 5:
            continue
        mean = g.mean()
        std = g.std()
        cv = (std / (mean.abs() + 1e-9)).replace([np.inf, -np.inf], np.nan)
        cv_mean = float(np.nanmean(cv.values)) if len(cv) else np.nan
        if not np.isnan(cv_mean) and cv_mean > best_cv:
            best_cv = cv_mean
            best_dim = c
            best_tbl = pd.DataFrame({
                c: mean.index,
                "mean": mean.values,
                "std": std.values,
                "count": g.count().values,
                "cv (coefficient of variation)": cv.values,
            }).sort_values("cv (coefficient of variation)", ascending=False)

    if best_dim is None or best_tbl is None or best_tbl.empty:
        bullets.append("No strong variability cut detected (need a categorical column with enough observations per group).")
        return AnalysisResult("2) Variability by best cut", bullets, [])

    bullets.append(f"Detected best cut: **{best_dim}** (highest average variability across groups).")
    bullets.append("**CV (coefficient of variation)** = std / mean. Higher CV means the metric is less stable within that segment.")
    bullets.append("Use this to spot segments where performance is unpredictable (risk) or opportunity-driven (target deeper analysis).")

    top = best_tbl.iloc[0]
    bullets.append(f"Highest-variability group: **{top[best_dim]}** (CV={top['cv (coefficient of variation)']:.2f}, n={int(top['count'])}).")

    show = best_tbl.head(10).copy()
    fig = px.bar(
        show,
        x=best_dim,
        y="cv (coefficient of variation)",
        title=f"Variability (CV) of {metric} by {best_dim}",
        color=best_dim,
        color_discrete_sequence=PALETTE_ALT,
        text="cv (coefficient of variation)",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10), showlegend=False)
    figs.append(fig)

    return AnalysisResult("2) Variability by best cut", bullets[:6], figs)

def analysis_discount_effectiveness_simple(df: pd.DataFrame, metric: str) -> AnalysisResult:
    figs: List[go.Figure] = []
    bullets: List[str] = []

    disc_col = None
    for c in df.columns:
        if re.search(r"discount", c, re.I) and pd.api.types.is_numeric_dtype(df[c]):
            disc_col = c
            break
    if not disc_col:
        bullets.append("No numeric discount column detected (e.g., Discount_Rate). Skipping discount effectiveness.")
        return AnalysisResult("3) Discount effectiveness", bullets, figs)

    d = df[[disc_col, metric]].dropna().copy()
    if d.empty:
        bullets.append("Not enough data to evaluate discount vs metric (missing values).")
        return AnalysisResult("3) Discount effectiveness", bullets, figs)

    if d[disc_col].max() > 1.5:
        d[disc_col] = d[disc_col] / 100.0

    bins = [-1, 0.02, 0.05, 0.10, 0.15, 0.20, 10]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    d["Discount_Band"] = pd.cut(d[disc_col], bins=bins, labels=labels)

    agg = d.groupby("Discount_Band")[metric].mean().reset_index()
    agg["n"] = d.groupby("Discount_Band")[metric].count().values

    bullets.append(f"Chart shows **average {metric} per record** by discount band (not per customer unless a customer ID is provided).")
    best = agg.loc[agg[metric].idxmax()]
    worst = agg.loc[agg[metric].idxmin()]
    bullets.append(f"Best-performing band: **{best['Discount_Band']}** with avg {format_number(best[metric])} (n={int(best['n'])}).")
    bullets.append(f"Weakest band: **{worst['Discount_Band']}** with avg {format_number(worst[metric])} (n={int(worst['n'])}).")
    bullets.append("Use this as a starting read; confirm with controls (Store/Channel/Category) to avoid mixing effects.")

    fig = px.bar(
        agg,
        x="Discount_Band",
        y=metric,
        title="Discount effectiveness (simple): average metric per record by discount band",
        color="Discount_Band",
        color_discrete_sequence=PALETTE_MAIN,
        text=metric,
    )
    fig.update_traces(text=[format_number(v) for v in agg[metric].values], textposition="inside")
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10), showlegend=False)
    figs.append(fig)

    return AnalysisResult("3) Discount effectiveness (simple)", bullets[:6], figs)


# ----------------------------
# Export helpers (PDF / PPTX)
# ----------------------------
def fig_to_png_bytes(fig: go.Figure, width: int = 1200, height: int = 700) -> Optional[bytes]:
    if not KALEIDO_OK:
        return None
    try:
        import plotly.io as pio
        return pio.to_image(fig, format="png", width=width, height=height, scale=2)
    except Exception:
        return None

def build_pdf_bytes(
    title: str,
    exec_points: List[str],
    insight_points: List[str],
    next_analyses: List[Dict[str, str]],
    figs: List[go.Figure],
    analyses: List[AnalysisResult],
) -> Optional[bytes]:
    if not REPORTLAB_OK:
        return None

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Executive Summary</b>", styles["Heading2"]))
    for p in exec_points:
        story.append(Paragraph(f"• {p}", styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Key Insights</b>", styles["Heading2"]))
    for p in insight_points:
        story.append(Paragraph(f"• {p}", styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Suggested Next Analyses</b>", styles["Heading2"]))
    for i, a in enumerate(next_analyses, 1):
        story.append(Paragraph(f"<b>{i}. {a.get('title','')}</b>", styles["BodyText"]))
        story.append(Paragraph(f"<b>Business Context:</b> {a.get('Business Context','')}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Risks:</b> {a.get('Risks','')}", styles["BodyText"]))
        outs = a.get("Outputs", [])
        if isinstance(outs, list) and outs:
            story.append(Paragraph("<b>Outputs:</b>", styles["BodyText"]))
            for o in outs:
                story.append(Paragraph(f"• {o}", styles["BodyText"]))
        story.append(Spacer(1, 8))
    story.append(Spacer(1, 8))

    if figs:
        story.append(Paragraph("<b>Charts</b>", styles["Heading2"]))
        for fig in figs[:6]:
            png = fig_to_png_bytes(fig, width=1100, height=650)
            if not png:
                continue
            img = RLImage(io.BytesIO(png))
            img.drawHeight = 3.5 * inch
            img.drawWidth = 6.5 * inch
            story.append(img)
            story.append(Spacer(1, 10))

    if analyses:
        story.append(Paragraph("<b>Further Analyses (Run All)</b>", styles["Heading2"]))
        for ar in analyses:
            story.append(Paragraph(f"<b>{ar.title}</b>", styles["BodyText"]))
            for b in ar.narrative_bullets:
                story.append(Paragraph(f"• {b}", styles["BodyText"]))
            for fig in ar.figs[:2]:
                png = fig_to_png_bytes(fig, width=1100, height=650)
                if not png:
                    continue
                img = RLImage(io.BytesIO(png))
                img.drawHeight = 3.5 * inch
                img.drawWidth = 6.5 * inch
                story.append(img)
                story.append(Spacer(1, 10))
            story.append(Spacer(1, 10))

    doc.build(story)
    return buff.getvalue()

def _ppt_add_textbox(slide, left, top, width, height, text, bold=False, font_size=20, align="left"):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bool(bold)
    p.alignment = PP_ALIGN.CENTER if align == "center" else PP_ALIGN.LEFT
    tf.word_wrap = True
    return tb

def _ppt_fit_font(text: str, base: int = 22) -> int:
    n = len(text)
    if n <= 140:
        return base
    if n <= 240:
        return max(16, base - 4)
    if n <= 360:
        return max(14, base - 6)
    return 12

def build_pptx_bytes(
    title: str,
    exec_points: List[str],
    insight_points: List[str],
    next_analyses: List[Dict[str, str]],
    charts: List[go.Figure],
    analyses: List[AnalysisResult],
) -> Optional[bytes]:
    if not PPTX_OK:
        return None

    prs = Presentation()

    def add_title_slide():
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _ppt_add_textbox(slide, Inches(0.6), Inches(0.7), Inches(12.0), Inches(1.0), title, bold=True, font_size=34)
        _ppt_add_textbox(slide, Inches(0.6), Inches(1.6), Inches(12.0), Inches(0.7),
                         "Executive Summary • Key Insights • Suggested Next Analyses", bold=False, font_size=16)
        return slide

    def add_bullets_slide(heading: str, bullets: List[str]):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _ppt_add_textbox(slide, Inches(0.6), Inches(0.4), Inches(12.0), Inches(0.8), heading, bold=True, font_size=28)
        box = slide.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(12.4), Inches(5.6))
        tf = box.text_frame
        tf.clear()
        tf.word_wrap = True
        for i, b in enumerate(bullets[:10]):
            p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
            p.text = f"• {b}"
            p.font.size = Pt(16)
        return slide

    def add_next_analyses_slide():
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _ppt_add_textbox(slide, Inches(0.6), Inches(0.4), Inches(12.0), Inches(0.8), "Suggested Next Analyses", bold=True, font_size=28)

        y = 1.2
        for i, a in enumerate(next_analyses[:3], 1):
            title_line = f"{i}. {a.get('title','')}"
            fs = _ppt_fit_font(title_line, base=18)
            _ppt_add_textbox(slide, Inches(0.8), Inches(y), Inches(12.6), Inches(0.35), title_line, bold=True, font_size=fs)
            y += 0.35

            bc = a.get("Business Context", "")
            risks = a.get("Risks", "")
            outs = a.get("Outputs", [])
            outs_txt = "\n".join([f"• {o}" for o in outs[:4]]) if isinstance(outs, list) else f"• {outs}"

            block = f"Business Context: {bc}\nRisks: {risks}\nOutputs:\n{outs_txt}"
            fs2 = _ppt_fit_font(block, base=14)
            _ppt_add_textbox(slide, Inches(0.95), Inches(y), Inches(12.3), Inches(1.35), block, bold=False, font_size=fs2)
            y += 1.45

        return slide

    def add_chart_slide(fig: go.Figure, heading: str):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _ppt_add_textbox(slide, Inches(0.6), Inches(0.35), Inches(12.0), Inches(0.6), heading, bold=True, font_size=24)
        png = fig_to_png_bytes(fig, width=1400, height=800)
        if not png:
            _ppt_add_textbox(slide, Inches(0.8), Inches(1.4), Inches(12.0), Inches(1.0),
                             "Chart export requires Kaleido. Add 'kaleido' to requirements.txt.", bold=False, font_size=16)
            return slide
        slide.shapes.add_picture(io.BytesIO(png), Inches(0.8), Inches(1.2), width=Inches(12.8))
        return slide

    add_title_slide()
    add_bullets_slide("Executive Summary", exec_points)
    add_bullets_slide("Key Insights", insight_points)
    add_next_analyses_slide()

    for i, fig in enumerate(charts[:6], 1):
        add_chart_slide(fig, f"Key Charts ({i})")

    if analyses:
        for ar in analyses:
            add_bullets_slide(ar.title, ar.narrative_bullets)
            for fig in ar.figs[:2]:
                add_chart_slide(fig, ar.title)

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


# ----------------------------
# UI
# ----------------------------
st.title("EC-AI Insight (MVP)")
st.caption("Turning Data Into Intelligence — Upload a CSV or Excel file to get profiling + insights.")
st.markdown('<div class="small-note">Note: This is a demo/testing app. Please avoid uploading confidential or regulated data.</div>', unsafe_allow_html=True)

uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])

if "df" not in st.session_state:
    st.session_state.df = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []
if "ai_report" not in st.session_state:
    st.session_state.ai_report = None

if uploaded:
    try:
        df0 = load_table(uploaded)
        df0 = coerce_types(df0)
        st.session_state.df = df0
        st.session_state.analysis_results = []
        st.session_state.ai_report = None
    except Exception as e:
        st.error(f"Failed to load file: {e}")
        st.stop()

df = st.session_state.df
if df is None:
    st.info("Upload a dataset to begin.")
    st.stop()

nrows, ncols = df.shape
st.success(f"Loaded dataset: {nrows:,} rows × {ncols:,} columns")

numeric_cols = get_numeric_cols(df)
cat_cols = get_categorical_cols(df)
dt_cols = get_datetime_cols(df)
primary_metric = pick_primary_metric(df)

money_like = bool(primary_metric and re.search(r"revenue|sales|income|amount|profit|cost|cogs|price", primary_metric, re.I))

date_col = None
if dt_cols:
    for c in dt_cols:
        if re.search("date", c, re.I):
            date_col = c
            break
    date_col = date_col or dt_cols[0]

ind = compute_indicators(df)

# --- TOP: Executive Summary + Key Insights ---
st.markdown("## Executive Summary")
exec_pts = executive_summary_points(df, primary_metric, date_col, ind)
for p in exec_pts:
    st.markdown(f"- {p}")

st.markdown("## Key Insights")
ins_pts = key_insights_points(df, primary_metric, date_col)
for p in ins_pts:
    st.markdown(f"- {p}")

st.markdown("---")

# --- Indicators block ---
st.markdown("## Indicators")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Coverage", f"{ind.coverage:.1f}%")
c2.metric("Avg Missing", f"{ind.avg_missing:.1f}%")
c3.metric("Confidence", confidence_label(ind.confidence_score))
c4.metric("Strong R² pairs", f"{ind.strong_r2_pairs}")

with st.expander("How these indicators work"):
    st.markdown(
        """
- **Coverage**: percentage of all cells that are **not missing** across the whole dataset.
- **Avg Missing**: the **average missing rate across columns** (mean of each column’s missing%).
- **Strong R² pairs**: among numeric columns, count of pairs with **R² ≥ 0.70** (upper triangle only).
- **Confidence** (0–100): practical score combining dataset size, missingness, and richness of numeric/time columns.
  - This is a **readiness indicator** for analysis — **not** a model accuracy score.
"""
    )

st.markdown("---")

with st.expander("Preview data", expanded=False):
    st.dataframe(df.head(50), use_container_width=True)

st.markdown("## Data profile")
profile = build_profile_table(df)
st.dataframe(profile, use_container_width=True)

st.markdown("---")

# --- Key business cuts ---
st.markdown("## Key business cuts")

store_like = detect_best_dimension(df, ["store", "branch", "site", "location"])
channel_like = detect_best_dimension(df, ["channel", "platform", "source"])
category_like = detect_best_dimension(df, ["category", "product", "segment", "industry", "sector"])
country_like = detect_best_dimension(df, ["country", "region", "market", "geo"])

if not primary_metric:
    st.warning("No numeric metric detected to build business cuts.")
else:
    left, right = st.columns(2)

    if store_like:
        fig1 = fig_bar(df, store_like, primary_metric, f"{primary_metric} by {store_like}", money=money_like, top_k=12)
        top_seg = bar_topk(df, store_like, primary_metric, agg="sum", k=1).iloc[0]
        with left:
            st.caption(f"Commentary: Top {store_like} is {top_seg[store_like]} with {format_money(top_seg[primary_metric]) if money_like else format_number(top_seg[primary_metric])}.")
            show_chart(fig1, key="cuts_store_bar")
    else:
        left.info("No Store-like column detected for this dataset.")

    if channel_like:
        fig2 = fig_bar(df, channel_like, primary_metric, f"{primary_metric} by {channel_like}", money=money_like, top_k=12)
        top_seg = bar_topk(df, channel_like, primary_metric, agg="sum", k=1).iloc[0]
        with right:
            st.caption(f"Commentary: Top {channel_like} is {top_seg[channel_like]} with {format_money(top_seg[primary_metric]) if money_like else format_number(top_seg[primary_metric])}.")
            show_chart(fig2, key="cuts_channel_bar")
    else:
        right.info("No Channel-like column detected for this dataset.")

st.markdown("---")

# --- Trends ---
st.markdown("## Trends")

if primary_metric and date_col:
    fig_total = fig_trend_total(df, date_col, primary_metric, money=money_like)
    st.caption("Commentary: Total metric over time; look for sustained upward/downward movement and volatility.")
    show_chart(fig_total, key="trend_total")

    breakdown_dim = None
    for cand in [country_like, store_like, channel_like, category_like]:
        if cand:
            breakdown_dim = cand
            break

    if breakdown_dim:
        if breakdown_dim == store_like and store_like:
            st.subheader(f"{primary_metric} trend by {store_like} (small multiples)")
            st.caption("Commentary: Each panel shows per-segment movement; compare stability and spikes across segments.")
            figs = small_multiples_trend(df, date_col, store_like, primary_metric, top_n=5, money=money_like)
            if figs:
                cols = st.columns(2)
                for i, f in enumerate(figs):
                    with cols[i % 2]:
                        show_chart(f, key=f"trend_small_{i}")
            else:
                st.info("Not enough data to build small-multiples trend.")
        else:
            fig_by = fig_trend_by_dim(df, date_col, breakdown_dim, primary_metric, top_n=5, money=money_like)
            st.caption(f"Commentary: Top segments by total {primary_metric} and how each segment evolves over time.")
            show_chart(fig_by, key="trend_breakdown")
    else:
        st.info("No suitable segment column found for trend breakdown (Store/Channel/Category/Country).")
else:
    st.info("No datetime column detected; trends require a date/time field.")

st.markdown("---")

# --- Correlation (R²) ---
st.markdown("## Correlation")

if len(numeric_cols) < 2:
    st.info("Need at least 2 numeric columns to compute correlations.")
else:
    fig_r2 = fig_corr_r2(df, numeric_cols)
    show_chart(fig_r2, key="corr_r2")

    with st.expander("How to read Correlation and R² (auto-labeled strength)"):
        st.markdown(
            """
**What you are seeing here is R²** (Pearson correlation squared).  
- **R** ranges from -1 to +1 (direction + strength).  
- **R²** ranges from 0 to 1 and represents the *strength of association*, ignoring direction.

**Strength guide (heuristic):**
- R² < 0.10 → Very weak  
- 0.10–0.30 → Weak  
- 0.30–0.60 → Moderate  
- 0.60–0.80 → Strong  
- 0.80–1.00 → Very strong  

High R² pairs are good **priorities for driver exploration**, but are **not causation**.
"""
        )

st.markdown("---")

# --- AI Insights Report ---
st.markdown("## AI Insights Report")

auto_ai = st.checkbox("Auto-generate AI summary (uses OpenAI credits)", value=True)
regen = st.button("Regenerate AI report")

def build_ai_report() -> Dict[str, object]:
    dims_hint = [d for d in [store_like, channel_like, category_like, country_like] if d]
    next3 = suggested_next_analyses(df, primary_metric or "metric", date_col, dims_hint)
    return {"executive_summary": exec_pts, "key_insights": ins_pts, "suggested_next_analyses": next3}

if (auto_ai and st.session_state.ai_report is None) or regen:
    if not OPENAI_KEY:
        st.warning("OPENAI_API_KEY not found. Using rule-based suggestions (still high quality).")
    st.session_state.ai_report = build_ai_report()

ai_report = st.session_state.ai_report

if ai_report:
    st.subheader("Suggested Next Analyses")
    next3 = ai_report.get("suggested_next_analyses", [])
    for i, a in enumerate(next3[:3], 1):
        st.markdown(f"**{i}. {a.get('title','')}**")
        st.markdown(f"- **Business Context:** {a.get('Business Context','')}")
        st.markdown(f"- **Risks:** {a.get('Risks','')}")
        outs = a.get("Outputs", [])
        if isinstance(outs, list) and outs:
            st.markdown("- **Outputs:**")
            for o in outs[:6]:
                st.markdown(f"  - {o}")
        st.markdown("")

st.markdown("---")

# --- Run all 3 analyses ---
st.markdown("## Further analyses (one click)")
run_all = st.button("Run all 3 analyses")

if run_all:
    dims_hint = [d for d in [store_like, channel_like, category_like, country_like, detect_best_dimension(df, ["payment"])] if d]
    res1 = analysis_driver_relationship(df, primary_metric or numeric_cols[0], dims_hint)
    res2 = analysis_variability_by_best_cut(df, primary_metric or numeric_cols[0])
    res3 = analysis_discount_effectiveness_simple(df, primary_metric or numeric_cols[0])
    st.session_state.analysis_results = [res1, res2, res3]

analysis_results: List[AnalysisResult] = st.session_state.analysis_results

if analysis_results:
    for ai, ar in enumerate(analysis_results):
        st.subheader(ar.title)
        for b in ar.narrative_bullets:
            st.markdown(f"- {b}")
        for fi, fig in enumerate(ar.figs):
            show_chart(fig, key=f"analysis_{ai}_fig_{fi}")

st.markdown("---")

# --- Export section ---
st.markdown("## Export")
colA, colB = st.columns(2)

def collect_core_charts() -> List[go.Figure]:
    charts: List[go.Figure] = []
    if primary_metric:
        if store_like:
            charts.append(fig_bar(df, store_like, primary_metric, f"{primary_metric} by {store_like}", money=money_like, top_k=12))
        if channel_like:
            charts.append(fig_bar(df, channel_like, primary_metric, f"{primary_metric} by {channel_like}", money=money_like, top_k=12))
    if primary_metric and date_col:
        charts.append(fig_trend_total(df, date_col, primary_metric, money=money_like))
    if len(numeric_cols) >= 2:
        charts.append(fig_corr_r2(df, numeric_cols))
    return charts

core_charts = collect_core_charts()

with colA:
    if st.button("Download Executive Brief (PDF)"):
        if not REPORTLAB_OK:
            st.error("PDF export requires reportlab. Add it to requirements.txt.")
        else:
            pdf_bytes = build_pdf_bytes(
                title="EC-AI Insight — Executive Brief",
                exec_points=exec_pts,
                insight_points=ins_pts,
                next_analyses=ai_report.get("suggested_next_analyses", []) if ai_report else suggested_next_analyses_fallback(df, primary_metric or "metric", date_col, []),
                figs=core_charts,
                analyses=analysis_results,
            )
            if not KALEIDO_OK:
                st.warning("Charts in PDF require Kaleido (plotly image export). Add 'kaleido' to requirements.txt.")
            if pdf_bytes:
                st.download_button("Click to download PDF", data=pdf_bytes, file_name="ecai_executive_brief.pdf", mime="application/pdf")

with colB:
    if st.button("Download Slides (PPTX)"):
        if not PPTX_OK:
            st.error("PPTX export requires python-pptx. Add it to requirements.txt.")
        else:
            pptx_bytes = build_pptx_bytes(
                title="EC-AI Insight — Slides",
                exec_points=exec_pts,
                insight_points=ins_pts,
                next_analyses=ai_report.get("suggested_next_analyses", []) if ai_report else suggested_next_analyses_fallback(df, primary_metric or "metric", date_col, []),
                charts=core_charts,
                analyses=analysis_results,
            )
            if not KALEIDO_OK:
                st.warning("Charts in PPTX require Kaleido (plotly image export). Add 'kaleido' to requirements.txt.")
            if pptx_bytes:
                st.download_button(
                    "Click to download PPTX",
                    data=pptx_bytes,
                    file_name="ecai_insight_slides.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )

st.markdown('<div class="small-note">Tip: For best exports, add <b>kaleido</b> to requirements.txt so charts embed into PDF/PPTX.</div>', unsafe_allow_html=True)
