# app.py — EC-AI Insight (MVP)
# ------------------------------------------------------------
# Features:
# - Upload CSV/XLSX
# - Executive Dashboard (top): KPI cards + revenue charts (Tableau-style layout)
# - Data profile + Indicators (coverage, avg missing, confidence)
# - Auto business cuts + trends (colorful) + short commentary + top labels
# - Correlation heatmap (R² default) with strength labels + tooltip
# - AI Insights Report (Executive Summary + Key Insights + Suggested Next Analyses)
# - One-click "Run all 3 analyses" (rule-based + AI-aligned) with charts + bullet commentary
# - Export PDF / PPTX (with charts if kaleido available; else text-only)
# ------------------------------------------------------------

import io
import re
import math
import json
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import streamlit as st

# Optional exports
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
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

# Plotly image export (kaleido)
try:
    import plotly.io as pio
    _ = pio.to_image(go.Figure(), format="png")  # quick probe
    KALEIDO_OK = True
except Exception:
    KALEIDO_OK = False


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="EC-AI Insight (MVP)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# Styling (simple, clean, "Tableau-ish")
# -----------------------------
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
      .small-note { color: #6b7280; font-size: 0.9rem; }
      .section-title { font-size: 1.6rem; font-weight: 800; margin-top: 0.2rem; }
      .subtle { color: #6b7280; }
      .kpi-card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px 14px 10px 14px; }
      .kpi-label { color: #6b7280; font-size: 0.85rem; }
      .kpi-value { font-weight: 800; font-size: 1.3rem; margin-top: 4px; }
      .kpi-sub { color: #6b7280; font-size: 0.85rem; margin-top: 2px; }
      .divider { height: 1px; background: #e5e7eb; margin: 10px 0 18px 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

COLOR_SEQ = px.colors.qualitative.Set2 + px.colors.qualitative.Safe + px.colors.qualitative.Pastel

# -----------------------------
# Utilities
# -----------------------------
CURRENCY_HINTS = ["revenue", "sales", "amount", "income", "gm", "profit", "nop", "fee", "cost", "cogs", "margin", "balance"]
DATE_HINTS = ["date", "time", "month", "day", "dt", "period"]
DIM_HINTS = ["country", "region", "store", "channel", "category", "segment", "team", "industry", "sector", "product", "payment", "method"]

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower())

def human_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    x = float(x)
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000_000:
        return f"{sign}${x/1_000_000_000:.1f}B"
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:.1f}K"
    return f"{sign}${x:.0f}"

def fmt_1dp(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"{float(x):.1f}"

def safe_to_datetime(series: pd.Series) -> Optional[pd.Series]:
    try:
        dt = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
        if dt.notna().mean() >= 0.6:
            return dt
    except Exception:
        return None
    return None

def find_date_column(df: pd.DataFrame) -> Optional[str]:
    # prefer explicit datetime dtype
    for c in df.columns:
        if np.issubdtype(df[c].dtype, np.datetime64):
            return c
    # else try parse for columns with date hints
    candidates = []
    for c in df.columns:
        cn = _norm(c)
        if any(h in cn for h in DATE_HINTS):
            candidates.append(c)
    for c in candidates + list(df.columns):
        dt = safe_to_datetime(df[c])
        if dt is not None:
            return c
    return None

def find_numeric_targets(df: pd.DataFrame) -> List[str]:
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        return []
    # score by "business metric" hints
    scores = []
    for c in num_cols:
        cn = _norm(c)
        score = 0
        for h in CURRENCY_HINTS:
            if h in cn:
                score += 3
        # prefer non-binary
        uniq = df[c].nunique(dropna=True)
        if uniq <= 2:
            score -= 2
        # prefer wider variance
        if df[c].std(skipna=True) > 0:
            score += 1
        scores.append((score, c))
    scores.sort(reverse=True, key=lambda x: x[0])
    # take top 3-5 as "key metrics"
    return [c for _, c in scores[:5]]

def find_primary_metric(df: pd.DataFrame) -> Optional[str]:
    candidates = find_numeric_targets(df)
    if not candidates:
        return None
    # prefer revenue/sales if present
    for c in candidates:
        cn = _norm(c)
        if "revenue" in cn or "sales" in cn:
            return c
    return candidates[0]

def find_dimension_candidates(df: pd.DataFrame) -> List[str]:
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    # include low-cardinality ints as dims if sensible
    for c in df.select_dtypes(include=[np.number]).columns:
        if df[c].nunique(dropna=True) <= 12 and df[c].nunique(dropna=True) > 2:
            cat_cols.append(c)
    # score by hints and cardinality
    scored = []
    for c in cat_cols:
        cn = _norm(c)
        nun = df[c].nunique(dropna=True)
        if nun < 2:
            continue
        score = 0
        for h in DIM_HINTS:
            if h in cn:
                score += 3
        if 2 <= nun <= 20:
            score += 2
        elif nun <= 60:
            score += 1
        else:
            score -= 1
        scored.append((score, c))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [c for _, c in scored[:6]]

def coverage_and_missing(df: pd.DataFrame) -> Tuple[float, float]:
    # coverage = fraction of non-null cells
    total = df.shape[0] * df.shape[1] if df.shape[0] and df.shape[1] else 0
    if total == 0:
        return 0.0, 0.0
    non_null = df.notna().sum().sum()
    coverage = non_null / total
    avg_missing = 1.0 - coverage
    return coverage, avg_missing

def compute_confidence(df: pd.DataFrame, strong_r2_pairs: int) -> int:
    """
    A simple, explainable heuristic score 0-100:
    - Data completeness (coverage)
    - Row count (stability)
    - Presence of datetime (trend-readiness)
    - Numeric richness (# numeric)
    - Signal density (strong R² pairs)
    """
    cov, avg_miss = coverage_and_missing(df)
    n_rows, n_cols = df.shape
    n_num = len(df.select_dtypes(include=[np.number]).columns)
    has_date = find_date_column(df) is not None

    score = 0
    score += int(50 * cov)  # up to 50
    score += min(15, int(math.log10(max(n_rows, 1)) * 7))  # up to ~15
    score += min(10, n_num * 2)  # up to 10
    score += 8 if has_date else 0
    score += min(17, strong_r2_pairs * 3)  # up to 17

    return max(0, min(100, score))

def r_strength_label(r: float) -> str:
    a = abs(r)
    if a < 0.2:
        return "Very weak"
    if a < 0.4:
        return "Weak"
    if a < 0.6:
        return "Moderate"
    if a < 0.8:
        return "Strong"
    return "Very strong"

def r2_strength_label(r2: float) -> str:
    if r2 < 0.10:
        return "Very low"
    if r2 < 0.30:
        return "Low"
    if r2 < 0.50:
        return "Moderate"
    if r2 < 0.70:
        return "Strong"
    return "Very strong"

def make_r2_matrix(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    if len(cols) < 2:
        return pd.DataFrame()
    corr = df[cols].corr(numeric_only=True)
    r2 = corr**2
    return r2

def top_r2_pairs(r2: pd.DataFrame, k: int = 5, min_r2: float = 0.5) -> List[Tuple[str, str, float]]:
    pairs = []
    cols = list(r2.columns)
    for i in range(len(cols)):
        for j in range(i+1, len(cols)):
            v = float(r2.iloc[i, j])
            if not np.isnan(v) and v >= min_r2:
                pairs.append((cols[i], cols[j], v))
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs[:k]

def short_bar_commentary(grouped: pd.DataFrame, dim: str, metric: str) -> str:
    if grouped.empty:
        return ""
    top = grouped.iloc[0]
    return f"Top segment is **{top[dim]}** with **{human_money(top[metric])}**."

def add_value_labels_bar(fig: go.Figure, prefix: str = "$") -> go.Figure:
    # assumes single-trace bar
    fig.update_traces(
        texttemplate=f"{prefix}%{{text}}",
        textposition="inside",
        insidetextanchor="middle",
    )
    return fig

def make_bar_topN(df: pd.DataFrame, dim: str, metric: str, topn: int = 12) -> pd.DataFrame:
    g = df.groupby(dim, dropna=False)[metric].sum().reset_index()
    g = g.sort_values(metric, ascending=False).head(topn)
    # keep consistent formatting
    g[metric] = g[metric].astype(float)
    return g

def maybe_cast_currency(df: pd.DataFrame, metric: str) -> pd.Series:
    # ensure numeric float
    return pd.to_numeric(df[metric], errors="coerce")

def best_discount_band(df: pd.DataFrame, discount_col: str, metric: str) -> Optional[pd.DataFrame]:
    if discount_col not in df.columns or metric not in df.columns:
        return None
    s = pd.to_numeric(df[discount_col], errors="coerce")
    if s.notna().mean() < 0.6:
        return None

    # band in percent-like (0-1 or 0-100)
    maxv = s.max(skipna=True)
    if maxv <= 1.5:
        pct = s * 100
    else:
        pct = s

    bins = [-1e9, 2, 5, 10, 15, 20, 1e9]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    band = pd.cut(pct, bins=bins, labels=labels)
    tmp = df.copy()
    tmp["Discount_Band"] = band
    tmp[metric] = pd.to_numeric(tmp[metric], errors="coerce")
    out = tmp.groupby("Discount_Band")[metric].mean().reset_index()
    out["n"] = tmp.groupby("Discount_Band")[metric].count().values
    out = out.dropna(subset=["Discount_Band"])
    return out

def detect_discount_column(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        cn = _norm(c)
        if "discount" in cn and df[c].dtype != "object":
            return c
    return None

def detect_return_flag(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        cn = _norm(c)
        if "return" in cn and df[c].nunique(dropna=True) <= 6:
            return c
    return None

def detect_cost_col(df: pd.DataFrame) -> Optional[str]:
    for c in df.select_dtypes(include=[np.number]).columns:
        cn = _norm(c)
        if "cogs" in cn or "cost" in cn:
            return c
    return None

def detect_profit_col(df: pd.DataFrame) -> Optional[str]:
    for c in df.select_dtypes(include=[np.number]).columns:
        cn = _norm(c)
        if "profit" in cn or "margin" in cn or "gm" in cn:
            return c
    return None

def ensure_datetime_col(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    return out

def line_chart_total_and_split(
    df: pd.DataFrame,
    date_col: str,
    metric: str,
    dim: Optional[str] = None,
    topk: int = 5
) -> Tuple[Optional[go.Figure], List[go.Figure], str]:
    """
    Returns:
      - total trend fig (metric over time)
      - small multiples figs if dim provided
      - message
    """
    if date_col is None or date_col not in df.columns:
        return None, [], "No date column detected for time trend."

    dfx = df.copy()
    dfx[metric] = pd.to_numeric(dfx[metric], errors="coerce")
    dfx = dfx.dropna(subset=[date_col, metric])
    if dfx.empty:
        return None, [], "No valid rows for time trend."

    dfx = ensure_datetime_col(dfx, date_col)
    dfx = dfx.dropna(subset=[date_col])
    if dfx.empty:
        return None, [], "No valid datetime values for time trend."

    # daily aggregation
    g_total = dfx.groupby(pd.Grouper(key=date_col, freq="D"))[metric].sum().reset_index()
    fig_total = px.line(
        g_total,
        x=date_col,
        y=metric,
        markers=True,
        title=f"{metric} trend (total)",
        template="plotly_white",
    )
    fig_total.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    fig_total.update_traces(
        hovertemplate=f"Date=%{{x|%Y-%m-%d}}<br>{metric}=%{{y:,.2f}}<extra></extra>"
    )

    split_figs = []
    if dim and dim in dfx.columns:
        # top categories by total metric
        top = dfx.groupby(dim)[metric].sum().sort_values(ascending=False).head(topk).index.tolist()
        dfx2 = dfx[dfx[dim].isin(top)].copy()
        if not dfx2.empty:
            for cat in top:
                g = dfx2[dfx2[dim] == cat].groupby(pd.Grouper(key=date_col, freq="D"))[metric].sum().reset_index()
                fig = px.line(
                    g,
                    x=date_col,
                    y=metric,
                    markers=True,
                    title=f"{metric} trend — {dim}: {cat}",
                    template="plotly_white",
                )
                fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=260)
                fig.update_traces(
                    hovertemplate=f"{dim}={cat}<br>Date=%{{x|%Y-%m-%d}}<br>{metric}=%{{y:,.2f}}<extra></extra>"
                )
                split_figs.append(fig)

    return fig_total, split_figs, "ok"

def chart_commentary_top_point(df_agg: pd.DataFrame, dim: str, metric: str) -> str:
    if df_agg.empty:
        return ""
    top = df_agg.iloc[0]
    return f"Finding: **{top[dim]}** leads with **{human_money(top[metric])}**."

def annotate_top_bar(fig: go.Figure, x_vals: List, y_vals: List, metric: str) -> go.Figure:
    if not x_vals or not y_vals:
        return fig
    idx = int(np.nanargmax(y_vals))
    fig.add_annotation(
        x=x_vals[idx],
        y=y_vals[idx],
        text=f"Top: {human_money(y_vals[idx])}",
        showarrow=True,
        arrowhead=2,
        yshift=10,
    )
    return fig

def build_bar(df_agg: pd.DataFrame, dim: str, metric: str, title: str) -> go.Figure:
    fig = px.bar(
        df_agg,
        x=dim,
        y=metric,
        title=title,
        template="plotly_white",
        color=dim,
        color_discrete_sequence=COLOR_SEQ,
    )
    # label on bar (1 decimal K/M etc)
    texts = [human_money(v).replace("$", "") for v in df_agg[metric].tolist()]
    fig.update_traces(text=texts, textposition="inside", insidetextanchor="middle")
    # add $ prefix in text template
    fig.update_traces(texttemplate="$%{text}")
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
    return fig

def build_heatmap_r2(r2: pd.DataFrame) -> go.Figure:
    # heatmap with tooltip R²
    z = r2.values
    x = r2.columns.tolist()
    y = r2.index.tolist()
    text = [[f"R² = {z[i][j]:.2f}<br>{r2_strength_label(z[i][j])}" for j in range(len(x))] for i in range(len(y))]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=text,
            hovertemplate="%{text}<extra></extra>",
            colorscale="Blues",
        )
    )
    fig.update_layout(
        title="Correlation (R²)",
        template="plotly_white",
        margin=dict(l=10, r=10, t=50, b=10),
        height=520,
    )
    return fig

def ai_client():
    """
    OpenAI client. Requires:
      - st.secrets["OPENAI_API_KEY"]  (preferred)
    """
    key = None
    if "OPENAI_API_KEY" in st.secrets:
        key = st.secrets["OPENAI_API_KEY"]
    if not key:
        return None

    try:
        from openai import OpenAI
        return OpenAI(api_key=key)
    except Exception:
        return None

def ai_suggested_next_analyses(
    df: pd.DataFrame,
    metric: str,
    date_col: Optional[str],
    dims: List[str],
    r2_pairs: List[Tuple[str, str, float]],
    max_items: int = 3
) -> List[Dict[str, str]]:
    """
    Consultant-grade: 3 items with Business Context / Risks / Outputs.
    """
    client = ai_client()
    if client is None:
        # fallback rule-based suggestions
        base = []
        dims_pick = dims[:2] if dims else []
        base.append({
            "title": f"{metric} driver & segment performance",
            "business_context": f"Identify which segments drive {metric} and where performance gaps exist to focus actions and resource allocation.",
            "risks": "Risk of confounding (e.g., mix changes). Validate with controlled comparisons and consistent time windows.",
            "outputs": f"Top/bottom segments by {metric}; contribution waterfall; drivers vs. segment chart; short narrative of what changed and why."
        })
        if date_col:
            base.append({
                "title": f"{metric} trend & seasonality scan",
                "business_context": f"Detect trend, volatility, and potential seasonality to plan staffing, inventory, and targets.",
                "risks": "Short history can overstate patterns. Check for one-off spikes and calendar effects.",
                "outputs": f"Weekly trend, rolling averages, spike annotations, and split trends by {dims_pick[0] if dims_pick else 'top segments'}."
            })
        base.append({
            "title": "Discount / price-mix sanity check",
            "business_context": "Assess whether discounting is driving incremental value or eroding margins and quality of revenue.",
            "risks": "Discount bands may be correlated with channel/store mix. Segment the analysis before concluding causality.",
            "outputs": "Revenue/units by discount band, margin proxy if available, and recommended test design for validation."
        })
        return base[:max_items]

    # Build a compact profile payload (safe: no raw rows)
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    profile = {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "date_col": date_col,
        "key_metric": metric,
        "numeric_cols": num_cols[:20],
        "categorical_cols": cat_cols[:20],
        "top_dims": dims[:6],
        "r2_pairs": [{"a": a, "b": b, "r2": round(v, 3)} for a, b, v in r2_pairs],
        "missing_pct_avg": float(df.isna().mean().mean()),
    }

    prompt = f"""
You are a senior strategy & analytics consultant.
Given this dataset profile (NO raw rows), produce EXACTLY {max_items} "Suggested Next Analyses".

Rules:
- Each item must be specific to the columns present.
- Avoid vague phrasing.
- Each item must include:
  1) Title (short, business-style)
  2) Business Context (2-3 sentences, concrete)
  3) Risks (1-2 sentences, practical)
  4) Outputs (2-4 bullets of deliverables, concrete)
- Prefer analyses that a client would actually run next week.
- If a date column exists, include at least one time-based analysis.
- Use the strongest R² pairs to justify at least one recommendation.

Return JSON only as a list of objects with keys:
title, business_context, risks, outputs
where outputs is a single string with bullet points separated by "\\n- ".

Dataset profile:
{json.dumps(profile, ensure_ascii=False)}
""".strip()

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0.2,
        )
        txt = resp.output_text.strip()
        items = json.loads(txt)
        # sanitize
        cleaned = []
        for it in items[:max_items]:
            cleaned.append({
                "title": str(it.get("title", "")).strip(),
                "business_context": str(it.get("business_context", "")).strip(),
                "risks": str(it.get("risks", "")).strip(),
                "outputs": str(it.get("outputs", "")).strip(),
            })
        return cleaned[:max_items]
    except Exception:
        return ai_suggested_next_analyses(df, metric, date_col, dims, r2_pairs, max_items=max_items)

def ai_executive_summary_and_insights(
    df: pd.DataFrame,
    metric: str,
    date_col: Optional[str],
    dims: List[str],
    r2_pairs: List[Tuple[str, str, float]],
    key_facts: List[str],
    exec_points: int = 8,
    insight_points: int = 10,
) -> Tuple[List[str], List[str]]:
    """
    Returns (executive_summary_bullets, key_insights_bullets).
    Falls back to rule-based if no OpenAI.
    """
    client = ai_client()
    if client is None:
        # rule-based fallback
        exec_bullets = []
        exec_bullets.append(f"Dataset size: **{df.shape[0]:,} rows × {df.shape[1]:,} columns**.")
        cov, avg_miss = coverage_and_missing(df)
        exec_bullets.append(f"Data completeness: **{cov*100:.1f}% coverage**; average missing **{avg_miss*100:.1f}%**.")
        exec_bullets.append(f"Primary metric detected: **{metric}**.")
        if date_col:
            dmin = pd.to_datetime(df[date_col], errors="coerce").min()
            dmax = pd.to_datetime(df[date_col], errors="coerce").max()
            if pd.notna(dmin) and pd.notna(dmax):
                exec_bullets.append(f"Time span: **{dmin.date()} → {dmax.date()}** based on **{date_col}**.")
        if r2_pairs:
            a, b, v = r2_pairs[0]
            exec_bullets.append(f"Strongest relationship: **{a} ↔ {b} (R²={v:.2f}, {r2_strength_label(v)})**.")
        exec_bullets.extend(key_facts[:max(0, exec_points - len(exec_bullets))])
        exec_bullets = exec_bullets[:exec_points]

        insights = []
        # top segment insight
        dim0 = dims[0] if dims else None
        if dim0 and metric in df.columns:
            g = df.groupby(dim0)[metric].sum().sort_values(ascending=False)
            if len(g) >= 1:
                insights.append(f"Top {dim0} by total {metric}: **{g.index[0]}** with **{human_money(g.iloc[0])}**.")
            if len(g) >= 2:
                insights.append(f"Bottom {dim0} by total {metric}: **{g.index[-1]}** with **{human_money(g.iloc[-1])}**.")
        # volatility insight
        if metric in df.columns:
            s = pd.to_numeric(df[metric], errors="coerce")
            if s.notna().any():
                insights.append(f"{metric} distribution: median **{s.median():,.2f}**, 75th percentile **{s.quantile(0.75):,.2f}**.")
        insights.extend(key_facts[: max(0, insight_points - len(insights))])
        return exec_bullets[:exec_points], insights[:insight_points]

    # AI path: compact profile only
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    profile = {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "date_col": date_col,
        "key_metric": metric,
        "top_dims": dims[:6],
        "numeric_cols": num_cols[:20],
        "categorical_cols": cat_cols[:20],
        "r2_pairs": [{"a": a, "b": b, "r2": round(v, 3)} for a, b, v in r2_pairs[:6]],
        "facts_pack": key_facts[:12],
        "missing_pct_avg": float(df.isna().mean().mean()),
    }

    prompt = f"""
You are a senior analytics consultant writing for business executives.

Task:
1) Produce an Executive Summary with {exec_points} bullet points (7–10 range).
2) Produce Key Insights with {insight_points} bullet points (about 10).
Both must be data-specific and mention actual columns (from profile).

Rules:
- No raw rows, no confidential claims.
- Use R² pairs to justify at least 2 bullets.
- If date_col exists, include at least 2 time/trend bullets.
- Make bullets crisp, actionable, and specific.
- Avoid generic filler.

Return JSON with keys:
executive_summary (list of strings),
key_insights (list of strings)

Dataset profile:
{json.dumps(profile, ensure_ascii=False)}
""".strip()

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0.2,
        )
        obj = json.loads(resp.output_text.strip())
        es = [str(x).strip() for x in obj.get("executive_summary", [])][:exec_points]
        ki = [str(x).strip() for x in obj.get("key_insights", [])][:insight_points]
        if len(es) < exec_points:
            es += key_facts[: (exec_points - len(es))]
        if len(ki) < insight_points:
            ki += key_facts[: (insight_points - len(ki))]
        return es[:exec_points], ki[:insight_points]
    except Exception:
        return ai_executive_summary_and_insights(df, metric, date_col, dims, r2_pairs, key_facts, exec_points, insight_points)


# -----------------------------
# Export helpers
# -----------------------------
def fig_to_png_bytes(fig: go.Figure, width: int = 1400, height: int = 800) -> Optional[bytes]:
    if not KALEIDO_OK:
        return None
    try:
        import plotly.io as pio
        return pio.to_image(fig, format="png", width=width, height=height, scale=2)
    except Exception:
        return None

def export_pdf_text_only(title: str, sections: List[Tuple[str, List[str]]]) -> bytes:
    if not REPORTLAB_OK:
        return b""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    x = 2 * cm
    y = h - 2 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, title)
    y -= 1.0 * cm

    c.setFont("Helvetica", 10)
    for sec_title, bullets in sections:
        if y < 4 * cm:
            c.showPage()
            y = h - 2 * cm
            c.setFont("Helvetica", 10)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, sec_title)
        y -= 0.6 * cm

        c.setFont("Helvetica", 10)
        for b in bullets:
            lines = textwrap.wrap("• " + b, width=110)
            for line in lines:
                if y < 2 * cm:
                    c.showPage()
                    y = h - 2 * cm
                    c.setFont("Helvetica", 10)
                c.drawString(x, y, line)
                y -= 0.45 * cm
            y -= 0.1 * cm

        y -= 0.3 * cm

    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def export_pdf_with_charts(
    title: str,
    sections: List[Tuple[str, List[str]]],
    chart_pngs: List[Tuple[str, bytes]],
) -> bytes:
    # Simple: write text pages + embed charts full-width
    if not REPORTLAB_OK:
        return b""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    x = 2 * cm
    y = h - 2 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, title)
    y -= 1.0 * cm

    c.setFont("Helvetica", 10)
    for sec_title, bullets in sections:
        if y < 4 * cm:
            c.showPage()
            y = h - 2 * cm
            c.setFont("Helvetica", 10)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, sec_title)
        y -= 0.6 * cm

        c.setFont("Helvetica", 10)
        for b in bullets:
            lines = textwrap.wrap("• " + b, width=110)
            for line in lines:
                if y < 2 * cm:
                    c.showPage()
                    y = h - 2 * cm
                    c.setFont("Helvetica", 10)
                c.drawString(x, y, line)
                y -= 0.45 * cm
            y -= 0.1 * cm

        y -= 0.3 * cm

    # charts
    for chart_title, png in chart_pngs:
        c.showPage()
        y = h - 2 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, chart_title)
        y -= 0.8 * cm

        img_buf = io.BytesIO(png)
        # Fit image to page width
        img_w = w - 4 * cm
        img_h = h - 4 * cm
        c.drawImage(img_buf, x, 2 * cm, width=img_w, height=img_h, preserveAspectRatio=True, anchor='c')

    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def _fit_font_size(text: str, base: int = 20, min_size: int = 12) -> int:
    # crude but effective for overflow control
    n = len(text)
    if n <= 80:
        return base
    if n <= 140:
        return max(min_size, base - 4)
    if n <= 220:
        return max(min_size, base - 7)
    return min_size

def export_pptx(
    title: str,
    sections: List[Tuple[str, List[str]]],
    chart_pngs: List[Tuple[str, Optional[bytes]]],
) -> bytes:
    if not PPTX_OK:
        return b""
    prs = Presentation()
    # Use wide layout if available
    try:
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)
    except Exception:
        pass

    def add_title_slide():
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = title
        slide.placeholders[1].text = "Generated by EC-AI Insight (MVP)"

    def add_bullets_slide(sec_title: str, bullets: List[str]):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = sec_title
        body = slide.shapes.placeholders[1].text_frame
        body.clear()
        for i, b in enumerate(bullets):
            p = body.paragraphs[0] if i == 0 else body.add_paragraph()
            p.text = b
            p.level = 0
            p.font.size = Pt(18 if len(b) < 110 else 16)

    def add_chart_slide(chart_title: str, png: Optional[bytes]):
        slide = prs.slides.add_slide(prs.slide_layouts[5])  # title only
        slide.shapes.title.text = chart_title

        if png is None:
            # fallback text
            tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.8), Inches(5.4))
            tf = tx.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = "Chart image export not available (kaleido missing)."
            p.font.size = Pt(18)
            return

        img_stream = io.BytesIO(png)
        # Fit within margins
        slide.shapes.add_picture(img_stream, Inches(0.7), Inches(1.4), width=Inches(12.0))

    add_title_slide()

    # sections slides
    for sec_title, bullets in sections:
        # split long sections into chunks of ~8 bullets
        chunk = []
        for b in bullets:
            chunk.append(b)
            if len(chunk) >= 8:
                add_bullets_slide(sec_title, chunk)
                chunk = []
        if chunk:
            add_bullets_slide(sec_title, chunk)

    # charts slides
    for chart_title, png in chart_pngs:
        add_chart_slide(chart_title, png)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.getvalue()


# -----------------------------
# Load data
# -----------------------------
def read_uploaded_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded)
    raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")


# -----------------------------
# Main UI
# -----------------------------
st.title("EC-AI Insight (MVP)")
st.caption("Turning Data Into Intelligence — Upload a CSV/Excel to get instant profiling + insights.")

uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
if not uploaded:
    st.info("Upload a file to begin.")
    st.stop()

try:
    df_raw = read_uploaded_file(uploaded)
except Exception as e:
    st.error(f"Failed to read file: {e}")
    st.stop()

if df_raw.empty:
    st.warning("The uploaded file is empty.")
    st.stop()

# Light cleaning: trim column names
df = df_raw.copy()
df.columns = [str(c).strip() for c in df.columns]

# Detect key columns
date_col = find_date_column(df)
if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

key_metric = find_primary_metric(df)
if not key_metric:
    st.error("No numeric metric detected. Please upload a dataset with at least one numeric column.")
    st.stop()

df[key_metric] = pd.to_numeric(df[key_metric], errors="coerce")

dims = find_dimension_candidates(df)
num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
r2 = make_r2_matrix(df, cols=num_cols[:12]) if len(num_cols) >= 2 else pd.DataFrame()
pairs = top_r2_pairs(r2, k=6, min_r2=0.5) if not r2.empty else []
strong_pairs_count = len(pairs)

cov, avg_miss = coverage_and_missing(df)
confidence = compute_confidence(df, strong_pairs_count)

# Facts pack (rule-based)
facts_pack = []
facts_pack.append(f"Detected primary metric: **{key_metric}**.")
if date_col:
    dmin = df[date_col].min()
    dmax = df[date_col].max()
    if pd.notna(dmin) and pd.notna(dmax):
        facts_pack.append(f"Time span: **{dmin.date()} → {dmax.date()}**.")
facts_pack.append(f"Numeric columns: **{len(num_cols)}**; categorical-like columns: **{len(df.columns) - len(num_cols)}**.")
facts_pack.append(f"Completeness: **{cov*100:.1f}% coverage**, avg missing **{avg_miss*100:.1f}%**.")
if pairs:
    a, b, v = pairs[0]
    facts_pack.append(f"Strongest relationship: **{a} ↔ {b} (R²={v:.2f}, {r2_strength_label(v)})**.")

# AI-generated Executive Summary + Insights + Suggested Next Analyses (auto, no click)
exec_summary, key_insights = ai_executive_summary_and_insights(
    df=df,
    metric=key_metric,
    date_col=date_col,
    dims=dims,
    r2_pairs=pairs,
    key_facts=facts_pack,
    exec_points=8,
    insight_points=10,
)
suggested = ai_suggested_next_analyses(df, key_metric, date_col, dims, pairs, max_items=3)


# =============================
# 1) EXECUTIVE DASHBOARD (TOP)
# =============================
st.markdown('<div class="section-title">Executive Dashboard</div>', unsafe_allow_html=True)
st.caption("A quick, executive view of the most important numbers and revenue cuts.")

# KPI cards
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown('<div class="kpi-card"><div class="kpi-label">Rows × Columns</div>'
                f'<div class="kpi-value">{df.shape[0]:,} × {df.shape[1]:,}</div>'
                f'<div class="kpi-sub">Data size</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown('<div class="kpi-card"><div class="kpi-label">Coverage</div>'
                f'<div class="kpi-value">{cov*100:.1f}%</div>'
                f'<div class="kpi-sub">Non-missing cells</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown('<div class="kpi-card"><div class="kpi-label">Avg Missing</div>'
                f'<div class="kpi-value">{avg_miss*100:.1f}%</div>'
                f'<div class="kpi-sub">Across all columns</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown('<div class="kpi-card"><div class="kpi-label">Confidence</div>'
                f'<div class="kpi-value">{confidence} ({ "High" if confidence>=80 else "Medium" if confidence>=60 else "Low"})</div>'
                f'<div class="kpi-sub">Heuristic reliability score</div></div>', unsafe_allow_html=True)

with st.expander("How Coverage / Avg Missing / Confidence work (logic)"):
    st.markdown(
        """
- **Coverage** = (non-null cells) / (total cells). If coverage is 100%, it means no missing values anywhere.
- **Avg Missing** = 1 − Coverage.
- **Confidence** (0–100) is a transparent heuristic:
  - Higher **coverage** boosts the score (largest weight).
  - More **rows** improves stability.
  - More **numeric columns** increases analyzable signal.
  - Having a **date** column increases trend-readiness.
  - More **strong R² pairs** increases signal density.
        """.strip()
    )

# Executive charts (prefer revenue/sales if present, otherwise key_metric)
metric_exec = key_metric

# Choose 2 dims for executive cuts
exec_dims = dims[:2] if dims else []
c1, c2 = st.columns(2)

if exec_dims:
    d0 = exec_dims[0]
    agg0 = make_bar_topN(df.dropna(subset=[metric_exec]), d0, metric_exec, topn=12)
    fig0 = build_bar(agg0, d0, metric_exec, title=f"{metric_exec} by {d0}")
    with c1:
        st.plotly_chart(fig0, use_container_width=True)
        st.caption(chart_commentary_top_point(agg0, d0, metric_exec))

if len(exec_dims) > 1:
    d1 = exec_dims[1]
    agg1 = make_bar_topN(df.dropna(subset=[metric_exec]), d1, metric_exec, topn=12)
    fig1 = build_bar(agg1, d1, metric_exec, title=f"{metric_exec} by {d1}")
    with c2:
        st.plotly_chart(fig1, use_container_width=True)
        st.caption(chart_commentary_top_point(agg1, d1, metric_exec))

# Total trend (executive)
if date_col:
    fig_total, _, msg = line_chart_total_and_split(df, date_col, metric_exec, dim=None)
    if fig_total is not None:
        st.plotly_chart(fig_total, use_container_width=True)
        st.caption("Finding: This chart shows overall movement over time; use it to spot spikes, trend direction, and volatility.")
else:
    st.info("No date column detected — trend charts will be limited to non-time cuts.")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# =============================
# 2) EXEC SUMMARY + KEY INSIGHTS (before preview)
# =============================
st.markdown('<div class="section-title">Executive Summary</div>', unsafe_allow_html=True)
for b in exec_summary:
    st.markdown(f"- {b}")

st.markdown('<div class="section-title" style="margin-top:10px;">Key Insights</div>', unsafe_allow_html=True)
for b in key_insights:
    st.markdown(f"- {b}")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# =============================
# Preview data
# =============================
with st.expander("Preview data", expanded=False):
    st.dataframe(df.head(50), use_container_width=True)

# Data profile
st.markdown('<div class="section-title">Data profile</div>', unsafe_allow_html=True)
profile = pd.DataFrame({
    "column": df.columns,
    "dtype": [str(df[c].dtype) for c in df.columns],
    "missing_%": [(df[c].isna().mean() * 100) for c in df.columns],
    "unique_values": [df[c].nunique(dropna=True) for c in df.columns],
})
profile["missing_%"] = profile["missing_%"].map(lambda x: round(float(x), 1))
st.dataframe(profile.sort_values("missing_%", ascending=False), use_container_width=True)

# Indicators row (repeat for visibility)
st.markdown('<div class="section-title">Indicators</div>', unsafe_allow_html=True)
i1, i2, i3, i4 = st.columns(4)
with i1:
    st.metric("Coverage", f"{cov*100:.1f}%")
with i2:
    st.metric("Avg Missing", f"{avg_miss*100:.1f}%")
with i3:
    st.metric("Confidence", f"{confidence} ({ 'High' if confidence>=80 else 'Medium' if confidence>=60 else 'Low'})")
with i4:
    st.metric("Strong R² Pairs", f"{strong_pairs_count}")

# Correlation / R² explanation
with st.expander("How to read Correlation and R² (quick guide)", expanded=False):
    st.markdown(
        """
**Correlation (R)** ranges from -1 to +1 and measures direction + strength (linear).  
**R²** ranges from 0 to 1 and measures **how much variance is explained** (linear).

**R² strength guide (rule-of-thumb, context dependent):**
- **0.00–0.10**: Very low  
- **0.10–0.30**: Low  
- **0.30–0.50**: Moderate  
- **0.50–0.70**: Strong  
- **0.70–1.00**: Very strong

Important: high R² does **not** prove causality — validate with business logic, segmentation, and controls.
        """.strip()
    )

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# =============================
# 3) Key business cuts + trends
# =============================
st.markdown('<div class="section-title">Key business cuts</div>', unsafe_allow_html=True)

# Choose up to 2 best dims for bar cuts
bar_dims = dims[:2]
if not bar_dims:
    st.info("No suitable dimension columns detected for business cuts.")
else:
    left, right = st.columns(2)
    for idx, dim in enumerate(bar_dims[:2]):
        agg = make_bar_topN(df.dropna(subset=[metric_exec]), dim, metric_exec, topn=12)
        fig = build_bar(agg, dim, metric_exec, title=f"{metric_exec} by {dim}")
        # label top point
        fig = annotate_top_bar(fig, agg[dim].tolist(), agg[metric_exec].tolist(), metric_exec)
        caption = short_bar_commentary(agg, dim, metric_exec)
        if idx == 0:
            with left:
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"Commentary: {caption}")
        else:
            with right:
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"Commentary: {caption}")

# Trend breakdown: prefer country/region/store/channel/category/payment/team keywords; fallback dims[0]
trend_dim = None
if dims:
    # choose a "trend-friendly" dim by keyword
    for c in dims:
        cn = _norm(c)
        if any(k in cn for k in ["country", "region", "store", "channel", "category", "payment", "team"]):
            trend_dim = c
            break
    if trend_dim is None:
        trend_dim = dims[0]

if date_col:
    st.markdown('<div class="section-title">Trends</div>', unsafe_allow_html=True)
    fig_total, smalls, msg = line_chart_total_and_split(df, date_col, metric_exec, dim=trend_dim, topk=5)
    if fig_total is not None:
        st.plotly_chart(fig_total, use_container_width=True)
        st.caption("Finding: Total trend highlights overall momentum and volatility across the full dataset.")

    if smalls:
        st.caption(f"Breakdown: small-multiple trends for top {trend_dim} categories (one chart per category).")
        # show as a grid (2 per row)
        for i in range(0, len(smalls), 2):
            cA, cB = st.columns(2)
            with cA:
                st.plotly_chart(smalls[i], use_container_width=True)
                st.caption("Finding: Use this mini-chart to see whether the segment is trending up/down and when spikes occur.")
            if i + 1 < len(smalls):
                with cB:
                    st.plotly_chart(smalls[i+1], use_container_width=True)
                    st.caption("Finding: Compare timing of peaks/troughs vs other segments to spot mix-driven changes.")
    else:
        st.info(f"No suitable {trend_dim}-based trend breakdown available.")
else:
    st.info("No date column detected — trend charts are not available.")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# =============================
# 4) Correlation (R²)
# =============================
st.markdown('<div class="section-title">Correlation</div>', unsafe_allow_html=True)
if r2.empty or r2.shape[0] < 2:
    st.info("Not enough numeric columns to compute correlation.")
else:
    fig_hm = build_heatmap_r2(r2)
    st.plotly_chart(fig_hm, use_container_width=True)
    if pairs:
        st.markdown("**Key R² relationships (selected pairs):**")
        for a, b, v in pairs:
            st.markdown(f"- **{a} ↔ {b}**: R² = **{v:.3f}** ({r2_strength_label(v)})")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# =============================
# 5) Suggested Next Analyses
# =============================
st.markdown('<div class="section-title">Suggested Next Analyses</div>', unsafe_allow_html=True)
for i, it in enumerate(suggested, 1):
    st.markdown(f"**{i}. {it['title']}**")
    st.markdown(f"- **Business Context:** {it['business_context']}")
    st.markdown(f"- **Risks:** {it['risks']}")
    st.markdown(f"- **Outputs:**")
    for line in it["outputs"].split("\n- "):
        line = line.replace("- ", "").strip()
        if line:
            st.markdown(f"  - {line}")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# =============================
# 6) Run all 3 analyses (with commentary)
# =============================
st.markdown('<div class="section-title">Further analyses (one click)</div>', unsafe_allow_html=True)

run_all = st.button("Run all 3 analyses")
analysis_charts: List[Tuple[str, go.Figure]] = []
analysis_notes: Dict[str, List[str]] = {}

if run_all:
    # 1) Driver analysis using strongest R² pair if available
    if pairs:
        a, b, v = pairs[0]
        tmp = df[[a, b]].copy()
        tmp[a] = pd.to_numeric(tmp[a], errors="coerce")
        tmp[b] = pd.to_numeric(tmp[b], errors="coerce")
        tmp = tmp.dropna()
        if not tmp.empty:
            fig = px.scatter(tmp, x=a, y=b, trendline="ols", template="plotly_white",
                             title=f"1) Driver scan: {b} vs {a} (R²≈{v:.2f})",
                             color_discrete_sequence=COLOR_SEQ)
            fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
            analysis_charts.append(("Driver scan", fig))
            analysis_notes["Driver scan"] = [
                f"Relationship strength is **R²={v:.2f}** ({r2_strength_label(v)}).",
                "Use this as a screening signal — validate with segmentation (e.g., store/channel/category) to avoid mix effects.",
                "If business logic supports it, this pair can be a candidate feature/driver in later predictive work (separate EC Predict phase).",
            ]

    # 2) Variability by best cut (Coefficient of Variation = CV)
    best_dim = dims[0] if dims else None
    if best_dim and metric_exec in df.columns:
        s = pd.to_numeric(df[metric_exec], errors="coerce")
        tmp = df[[best_dim, metric_exec]].copy()
        tmp[metric_exec] = s
        tmp = tmp.dropna(subset=[best_dim, metric_exec])
        if not tmp.empty:
            g = tmp.groupby(best_dim)[metric_exec].agg(["mean", "std", "count"]).reset_index()
            g["CV (Coefficient of Variation)"] = (g["std"] / g["mean"]).replace([np.inf, -np.inf], np.nan)
            g = g.sort_values("CV (Coefficient of Variation)", ascending=False)
            fig = px.bar(
                g.head(10),
                x=best_dim,
                y="CV (Coefficient of Variation)",
                color=best_dim,
                color_discrete_sequence=COLOR_SEQ,
                template="plotly_white",
                title=f"2) Variability by best cut: CV of {metric_exec} by {best_dim}",
            )
            fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
            analysis_charts.append(("Variability", fig))
            top_row = g.iloc[0]
            analysis_notes["Variability"] = [
                f"Highest variability segment is **{top_row[best_dim]}** (CV={top_row['CV (Coefficient of Variation)']:.2f}).",
                "Higher CV means the metric is less stable and may need tighter controls or deeper segmentation.",
                "Use this to prioritize which segments deserve diagnostic deep dives first.",
            ]

    # 3) Discount effectiveness (simple)
    disc_col = detect_discount_column(df)
    if disc_col:
        out = best_discount_band(df, disc_col, metric_exec)
        if out is not None and not out.empty:
            fig = px.bar(
                out,
                x="Discount_Band",
                y=metric_exec,
                template="plotly_white",
                color="Discount_Band",
                color_discrete_sequence=COLOR_SEQ,
                title=f"3) Discount effectiveness: average {metric_exec} per transaction by discount band",
            )
            # clarify meaning in axis title
            fig.update_yaxes(title=f"Average {metric_exec} per row (transaction/order)")
            fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
            # label bars
            fig.update_traces(text=[f"{v/1000:.1f}k" if v >= 1000 else f"{v:.0f}" for v in out[metric_exec]],
                              textposition="inside", texttemplate="%{text}")
            analysis_charts.append(("Discount effectiveness", fig))

            # notes
            best_idx = int(np.nanargmax(out[metric_exec].values))
            worst_idx = int(np.nanargmin(out[metric_exec].values))
            best_band = out.iloc[best_idx]["Discount_Band"]
            worst_band = out.iloc[worst_idx]["Discount_Band"]
            analysis_notes["Discount effectiveness"] = [
                f"Chart shows **average {metric_exec} per row (transaction/order)** across discount bands.",
                f"Best-performing band is **{best_band}**; weakest band is **{worst_band}** (directional read).",
                "Next: split by store/channel/category to confirm the result isn’t driven by mix differences.",
            ]

    # Render analyses
    if analysis_charts:
        for name, fig in analysis_charts:
            st.plotly_chart(fig, use_container_width=True)
            notes = analysis_notes.get(name, [])
            if notes:
                st.markdown("**Commentary**")
                for n in notes:
                    st.markdown(f"- {n}")
    else:
        st.info("No further analyses could be generated from this dataset (missing required columns).")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# =============================
# 7) AI Insights Report (Summary)
# =============================
st.markdown('<div class="section-title">AI Insights Report</div>', unsafe_allow_html=True)

st.markdown("**1) Executive Summary**")
for b in exec_summary:
    st.markdown(f"- {b}")

st.markdown("**2) Key Insights**")
for b in key_insights:
    st.markdown(f"- {b}")

st.markdown("**3) Suggested Next Analyses**")
for i, it in enumerate(suggested, 1):
    st.markdown(f"**{i}. {it['title']}**")
    st.markdown(f"- **Business Context:** {it['business_context']}")
    st.markdown(f"- **Risks:** {it['risks']}")
    st.markdown(f"- **Outputs:**")
    for line in it["outputs"].split("\n- "):
        line = line.replace("- ", "").strip()
        if line:
            st.markdown(f"  - {line}")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# =============================
# 8) Export
# =============================
st.markdown('<div class="section-title">Export</div>', unsafe_allow_html=True)
st.caption("Download a brief for sharing. For chart exports, install kaleido (see note below).")

# Collect charts for export (executive + correlation + analyses if run)
export_figs: List[Tuple[str, go.Figure]] = []

# Executive: include those built if available
try:
    if bar_dims:
        if "agg0" in locals():
            export_figs.append((f"{metric_exec} by {bar_dims[0]}", fig0))
        if len(bar_dims) > 1 and "agg1" in locals():
            export_figs.append((f"{metric_exec} by {bar_dims[1]}", fig1))
    if date_col and "fig_total" in locals() and fig_total is not None:
        export_figs.append((f"{metric_exec} trend (total)", fig_total))
    if not r2.empty:
        export_figs.append(("Correlation (R²)", fig_hm))
    if run_all and analysis_charts:
        for name, fig in analysis_charts:
            export_figs.append((f"Further analysis — {name}", fig))
except Exception:
    pass

sections = [
    ("Executive Summary", exec_summary),
    ("Key Insights", key_insights),
    ("Suggested Next Analyses", [
        f"{i}. {it['title']} — {it['business_context']}"
        for i, it in enumerate(suggested, 1)
    ]),
]

# Build chart PNGs if possible
chart_pngs = []
ppt_chart_pngs = []
if export_figs:
    for t, f in export_figs:
        png = fig_to_png_bytes(f)
        chart_pngs.append((t, png))
        ppt_chart_pngs.append((t, png))

colA, colB = st.columns(2)

with colA:
    if st.button("Download Executive Brief (PDF)"):
        if not REPORTLAB_OK:
            st.error("PDF export requires reportlab.")
        else:
            if KALEIDO_OK:
                # include charts
                pdf_bytes = export_pdf_with_charts("EC-AI Insight — Executive Brief", sections, [(t, p) for t, p in chart_pngs if p is not None])
                if not pdf_bytes:
                    pdf_bytes = export_pdf_text_only("EC-AI Insight — Executive Brief", sections)
            else:
                st.warning("Chart export not available (install kaleido). Exporting text-only PDF.")
                pdf_bytes = export_pdf_text_only("EC-AI Insight — Executive Brief", sections)

            st.download_button(
                "Click to download PDF",
                data=pdf_bytes,
                file_name="ecai_executive_brief.pdf",
                mime="application/pdf",
            )

with colB:
    if st.button("Download Slides (PPTX)"):
        if not PPTX_OK:
            st.error("PPTX export requires python-pptx.")
        else:
            pptx_bytes = export_pptx("EC-AI Insight — Slides", sections, ppt_chart_pngs)
            st.download_button(
                "Click to download PPTX",
                data=pptx_bytes,
                file_name="ecai_insight_slides.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

if not KALEIDO_OK:
    st.info("Optional: to include charts in exports, add `kaleido` to requirements.txt (Plotly image export).")

st.caption("Note: This app is for demo/testing. Please avoid uploading confidential or regulated data.")
