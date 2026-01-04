import io
import re
import math
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

import plotly.express as px
import plotly.graph_objects as go

# Optional exports
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# Optional AI
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ---------------------------
# UI / Page setup
# ---------------------------
st.set_page_config(
    page_title="EC-AI Insight (MVP)",
    page_icon="📊",
    layout="wide",
)

TITLE = "EC-AI Insight (MVP)"
TAGLINE = "Turning Data Into Intelligence — upload a file to get instant profiling + insights."

st.title(TITLE)
st.caption(TAGLINE)


# ---------------------------
# Helpers: detection & cleaning
# ---------------------------
COMMON_TIME_KEYS = ["date", "time", "timestamp", "day", "month", "week", "year"]
COMMON_METRIC_KEYS = [
    # business / finance
    "revenue", "sales", "income", "profit", "margin", "gm", "gross_margin", "cogs", "cost",
    "volume", "units", "qty", "quantity",
    # banking-ish
    "approved", "limit", "exposure", "outstanding", "balance", "usage", "utilization", "roe", "rwa",
    # marketing/sales ops
    "leads", "conversions", "conversion", "pipeline", "arr", "mrr", "churn"
]
COMMON_DIM_KEYS = [
    "country", "region", "market", "city",
    "store", "branch", "channel", "category", "product", "sku",
    "team", "segment", "client", "customer", "industry",
    "payment", "payment_method", "method", "source", "campaign"
]

PLOTLY_PALETTE = px.colors.qualitative.Set2 + px.colors.qualitative.Pastel + px.colors.qualitative.Bold


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower())


def detect_date_col(df: pd.DataFrame) -> str | None:
    # 1) name-based
    for c in df.columns:
        nc = _norm(c)
        if any(k in nc for k in COMMON_TIME_KEYS):
            # try parse
            try:
                pd.to_datetime(df[c], errors="raise")
                return c
            except Exception:
                pass

    # 2) dtype-based
    for c in df.columns:
        if np.issubdtype(df[c].dtype, np.datetime64):
            return c

    # 3) parse any object column that looks like dates
    for c in df.columns:
        if df[c].dtype == "object":
            parsed = pd.to_datetime(df[c], errors="coerce", infer_datetime_format=True)
            if parsed.notna().mean() >= 0.6:
                return c
    return None


def coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    dc = detect_date_col(df2)
    if dc is not None:
        df2[dc] = pd.to_datetime(df2[dc], errors="coerce", infer_datetime_format=True)
    return df2


def parse_numeric_like(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert numeric-looking object columns to numeric when safe.
    Keep real categorical strings as object.
    """
    df2 = df.copy()
    for c in df2.columns:
        if df2[c].dtype == "object":
            # strip commas, percent signs
            s = df2[c].astype(str).str.replace(",", "", regex=False).str.strip()
            # If many entries are numeric-like, convert
            converted = pd.to_numeric(s.str.replace("%", "", regex=False), errors="coerce")
            ratio = converted.notna().mean()
            if ratio >= 0.85:
                df2[c] = converted
    return df2


def basic_profile(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    n = len(df)
    for c in df.columns:
        miss = df[c].isna().mean() * 100
        out.append(
            {
                "column": c,
                "dtype": str(df[c].dtype),
                "missing_%": round(miss, 1),
                "unique_values": int(df[c].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(out).sort_values(by=["missing_%", "unique_values"], ascending=[False, False])


def guess_primary_metric(df: pd.DataFrame) -> str | None:
    """
    Pick a 'most important' metric for auto-charts.
    Heuristic:
      - numeric columns with name matching key terms (revenue/sales/income/profit first)
      - otherwise the numeric column with highest variance / magnitude
    """
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        return None

    priority = ["revenue", "sales", "income", "profit", "margin", "gm", "gross_margin", "arr", "mrr"]
    for key in priority:
        for c in num_cols:
            if key in _norm(c):
                return c

    # fallback: high std * non-null ratio
    scores = []
    for c in num_cols:
        s = df[c].dropna()
        if len(s) < 5:
            continue
        scores.append((float(s.std()), float(s.mean()), c))
    if scores:
        scores.sort(reverse=True)
        return scores[0][2]

    return num_cols[0]


def guess_secondary_metrics(df: pd.DataFrame, primary: str | None) -> list[str]:
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        return []
    if primary and primary in num_cols:
        num_cols.remove(primary)

    # pick up to 3 useful ones
    useful = []
    for key in ["cogs", "cost", "units", "qty", "quantity", "profit", "margin", "discount", "outstanding", "balance"]:
        for c in num_cols:
            if key in _norm(c) and c not in useful:
                useful.append(c)
    # fill
    for c in num_cols:
        if c not in useful:
            useful.append(c)
        if len(useful) >= 3:
            break
    return useful[:3]


def candidate_dims(df: pd.DataFrame) -> list[str]:
    dims = []
    for c in df.columns:
        if df[c].dtype == "object" or pd.api.types.is_categorical_dtype(df[c]):
            u = df[c].nunique(dropna=True)
            if 2 <= u <= 50:
                dims.append(c)
    # also include low-cardinality integers that behave like categories
    for c in df.columns:
        if pd.api.types.is_integer_dtype(df[c]):
            u = df[c].nunique(dropna=True)
            if 2 <= u <= 25:
                dims.append(c)
    # prefer "known" dims
    dims_sorted = sorted(
        dims,
        key=lambda c: (
            0 if any(k in _norm(c) for k in COMMON_DIM_KEYS) else 1,
            df[c].nunique(dropna=True),
        ),
    )
    return dims_sorted


def pick_breakdown_dim(df: pd.DataFrame) -> str | None:
    dims = candidate_dims(df)
    if not dims:
        return None
    # Prefer "country/region-like", else any good dimension
    for key in ["country", "region", "market", "store", "channel", "category", "team", "segment", "payment"]:
        for d in dims:
            if key in _norm(d):
                return d
    return dims[0]


def compute_r2(x: pd.Series, y: pd.Series) -> float | None:
    s = pd.concat([x, y], axis=1).dropna()
    if len(s) < 8:
        return None
    xx = s.iloc[:, 0].astype(float).values
    yy = s.iloc[:, 1].astype(float).values
    if np.std(xx) == 0 or np.std(yy) == 0:
        return None
    r = np.corrcoef(xx, yy)[0, 1]
    if np.isnan(r):
        return None
    return float(r * r)


def format_compact(x: float) -> str:
    # human friendly: 1.2k, 3.4M, etc. one decimal
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    sign = "-" if x < 0 else ""
    x = abs(float(x))
    if x >= 1_000_000_000:
        return f"{sign}{x/1_000_000_000:.1f}B"
    if x >= 1_000_000:
        return f"{sign}{x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"{sign}{x/1_000:.1f}k"
    return f"{sign}{x:.1f}"


# ---------------------------
# Indicators logic (explainable)
# ---------------------------
def compute_indicators(df: pd.DataFrame, primary_metric: str | None) -> dict:
    coverage = 100.0  # file rows loaded; "coverage" here = usability of dataset for analysis
    # define usability as: % rows that have at least 80% non-missing
    row_non_missing = (df.notna().mean(axis=1) >= 0.8).mean() * 100
    coverage = float(row_non_missing)

    avg_missing = float(df.isna().mean().mean() * 100)

    # Confidence: rule-based, 0-100
    n_rows = len(df)
    n_cols = df.shape[1]
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    date_col = detect_date_col(df)

    score = 0
    # data volume
    if n_rows >= 5000:
        score += 30
    elif n_rows >= 1000:
        score += 24
    elif n_rows >= 200:
        score += 18
    elif n_rows >= 60:
        score += 12
    else:
        score += 8

    # completeness
    if avg_missing <= 1:
        score += 25
    elif avg_missing <= 5:
        score += 18
    elif avg_missing <= 12:
        score += 10
    else:
        score += 4

    # structure richness
    score += min(15, max(5, n_cols))  # 5..15
    score += min(15, len(numeric_cols) * 3)

    # time-series readiness
    if date_col is not None:
        score += 10

    # primary metric present
    if primary_metric is not None and primary_metric in numeric_cols:
        score += 5

    score = max(0, min(100, int(round(score))))
    confidence_label = "High" if score >= 80 else "Medium" if score >= 60 else "Low"

    return {
        "coverage": round(coverage, 1),
        "avg_missing": round(avg_missing, 1),
        "confidence": score,
        "confidence_label": confidence_label,
    }


# ---------------------------
# Charts
# ---------------------------
def fig_bar_topk(df: pd.DataFrame, dim: str, metric: str, k: int = 12) -> go.Figure:
    g = (
        df.groupby(dim, dropna=True)[metric]
        .sum(min_count=1)
        .sort_values(ascending=False)
        .head(k)
        .reset_index()
    )
    fig = px.bar(
        g,
        x=dim,
        y=metric,
        text=g[metric].map(lambda v: format_compact(v)),
        color=dim,
        color_discrete_sequence=PLOTLY_PALETTE,
    )
    fig.update_traces(textposition="inside")
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
    fig.update_yaxes(title=metric)
    return fig


def fig_trend_total(df: pd.DataFrame, date_col: str, metric: str, freq: str = "D") -> go.Figure:
    s = df[[date_col, metric]].dropna()
    if s.empty:
        return go.Figure()
    s = s.sort_values(date_col)
    # resample
    s = s.set_index(date_col)[metric].resample(freq).sum(min_count=1).reset_index()
    fig = px.line(
        s,
        x=date_col,
        y=metric,
        markers=True,
        color_discrete_sequence=PLOTLY_PALETTE,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    return fig


def fig_trend_breakdown(df: pd.DataFrame, date_col: str, dim: str, metric: str, topk: int = 6, freq: str = "D") -> go.Figure:
    s = df[[date_col, dim, metric]].dropna()
    if s.empty:
        return go.Figure()
    s = s.sort_values(date_col)

    # pick topk categories by total metric
    top = (
        s.groupby(dim)[metric].sum(min_count=1).sort_values(ascending=False).head(topk).index.tolist()
    )
    s = s[s[dim].isin(top)]
    # resample per category
    out = (
        s.set_index(date_col)
        .groupby(dim)[metric]
        .resample(freq)
        .sum(min_count=1)
        .reset_index()
    )
    fig = px.line(
        out,
        x=date_col,
        y=metric,
        color=dim,
        markers=True,
        color_discrete_sequence=PLOTLY_PALETTE,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), legend_title_text=dim)
    return fig


def fig_corr_heatmap(df: pd.DataFrame) -> tuple[go.Figure | None, pd.DataFrame | None]:
    num = df.select_dtypes(include=[np.number]).copy()
    if num.shape[1] < 2:
        return None, None
    corr = num.corr().round(2)
    fig = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Blues",
        zmin=-1,
        zmax=1,
    )
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig, corr


def fig_discount_effectiveness(df: pd.DataFrame, metric: str) -> tuple[go.Figure | None, list[str]]:
    """
    Replace hard-to-read scatter with:
      - bucket discount into bands
      - show avg metric by band (bar)
    """
    # find discount-like column
    discount_col = None
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]) and "discount" in _norm(c):
            discount_col = c
            break
    if discount_col is None:
        return None, ["No discount-like numeric column detected (e.g., Discount, Discount_Rate)."]

    s = df[[discount_col, metric]].dropna()
    if len(s) < 20:
        return None, ["Not enough rows with both discount and metric to assess discount effectiveness."]

    # If discount looks like 0..1, keep; if 0..100, normalize
    d = s[discount_col].astype(float)
    if d.max() > 1.5:
        d = d / 100.0
    d = d.clip(lower=0, upper=1)

    bins = [0, 0.02, 0.05, 0.1, 0.15, 0.2, 1.0]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    s = s.copy()
    s["Discount_Band"] = pd.cut(d, bins=bins, labels=labels, include_lowest=True)

    g = s.groupby("Discount_Band")[metric].agg(["mean", "count"]).reset_index()
    g["mean_label"] = g["mean"].map(lambda v: format_compact(v))

    fig = px.bar(
        g,
        x="Discount_Band",
        y="mean",
        text="mean_label",
        color="Discount_Band",
        color_discrete_sequence=PLOTLY_PALETTE,
    )
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
    fig.update_yaxes(title=f"Average {metric}")

    # commentary
    best = g.loc[g["mean"].idxmax()] if g["mean"].notna().any() else None
    worst = g.loc[g["mean"].idxmin()] if g["mean"].notna().any() else None
    bullets = []
    if best is not None and worst is not None:
        bullets.append(f"Best-performing discount band is **{best['Discount_Band']}** with avg **{format_compact(best['mean'])}** (n={int(best['count'])}).")
        bullets.append(f"Weakest band is **{worst['Discount_Band']}** with avg **{format_compact(worst['mean'])}** (n={int(worst['count'])}).")
        bullets.append("Use this as a **starting read**; confirm with controls (store/channel/category) to avoid mixing effects.")
    return fig, bullets


# ---------------------------
# Rule-based signals + insights pack
# ---------------------------
def signal_extraction(df: pd.DataFrame, primary_metric: str | None) -> dict:
    """
    Clean, explainable signal pack used for:
      - Key Insights bullets
      - Suggested next analyses quality
    """
    n_rows, n_cols = df.shape
    prof = basic_profile(df)

    date_col = detect_date_col(df)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    dims = candidate_dims(df)

    signals = {
        "shape": (n_rows, n_cols),
        "date_col": date_col,
        "numeric_cols": numeric_cols,
        "dims": dims,
        "avg_missing_pct": float(df.isna().mean().mean() * 100),
        "worst_missing_cols": prof.sort_values("missing_%", ascending=False).head(3)[["column", "missing_%"]].to_dict("records"),
        "primary_metric": primary_metric,
    }

    # Top R² pairs vs primary metric (if exists)
    r2_pairs = []
    if primary_metric and primary_metric in numeric_cols:
        for c in numeric_cols:
            if c == primary_metric:
                continue
            r2 = compute_r2(df[c], df[primary_metric])
            if r2 is not None:
                r2_pairs.append((c, r2))
        r2_pairs.sort(key=lambda t: t[1], reverse=True)
    signals["r2_vs_primary"] = r2_pairs[:5]

    # Best cut: pick a dimension where primary metric varies the most (CV)
    best_cut = None
    best_cv = None
    if primary_metric and dims:
        for d in dims:
            g = df.groupby(d)[primary_metric].sum(min_count=1)
            if g.notna().sum() < 2:
                continue
            cv = float(g.std() / g.mean()) if g.mean() not in [0, np.nan] and g.mean() != 0 else None
            if cv is None or np.isnan(cv):
                continue
            if best_cv is None or cv > best_cv:
                best_cv = cv
                best_cut = d
    signals["best_cut_dim"] = best_cut
    signals["best_cut_cv"] = best_cv

    return signals


def build_executive_summary(df: pd.DataFrame, signals: dict, indicators: dict) -> list[str]:
    n_rows, n_cols = signals["shape"]
    primary = signals["primary_metric"]
    avg_missing = indicators["avg_missing"]
    conf = indicators["confidence"]
    conf_label = indicators["confidence_label"]
    coverage = indicators["coverage"]
    date_col = signals["date_col"]

    bullets = []
    bullets.append(f"Dataset loaded: **{n_rows:,} rows × {n_cols:,} columns**. Usable-row coverage is **{coverage:.1f}%** with average missing rate **{avg_missing:.1f}%**.")
    bullets.append(f"Overall analysis confidence score is **{conf}/100 ({conf_label})**, driven by data volume, completeness, and numeric richness.")
    if primary:
        s = df[primary].dropna()
        if len(s) > 0:
            bullets.append(f"Primary metric detected as **{primary}** with average **{format_compact(s.mean())}**, median **{format_compact(s.median())}**, and range **{format_compact(s.min())} → {format_compact(s.max())}**.")
    if date_col:
        d = df[date_col].dropna()
        if len(d) > 0:
            bullets.append(f"Time field detected (**{date_col}**). Date range spans **{d.min().date()} → {d.max().date()}** across **{d.nunique():,} unique periods**.")
    worst = signals["worst_missing_cols"]
    if worst and worst[0]["missing_%"] > 0:
        bullets.append(f"Data quality watchlist: highest missing columns include **{worst[0]['column']} ({worst[0]['missing_%']}%)** and **{worst[1]['column']} ({worst[1]['missing_%']}%)** (if present).")
    if signals["r2_vs_primary"]:
        top = signals["r2_vs_primary"][0]
        bullets.append(f"Strongest linear relationship vs {primary}: **{top[0]}** with **R² = {top[1]:.2f}** (association, not causation).")
    if signals["best_cut_dim"]:
        bullets.append(f"Most differentiating business cut (by variability of {primary}) is **{signals['best_cut_dim']}** (Coefficient of Variation ≈ **{signals['best_cut_cv']:.2f}**).")

    # pad to 7–10 bullets (but keep tight and meaningful)
    dims = signals["dims"]
    if dims:
        bullets.append(f"Categorical dimensions detected (examples): **{', '.join(dims[:4])}**.")
    if len(signals["numeric_cols"]) > 0:
        bullets.append(f"Numeric measures detected: **{len(signals['numeric_cols'])}** columns available for correlation and driver analysis.")

    return bullets[:10]


def build_key_insights(df: pd.DataFrame, signals: dict) -> list[str]:
    """
    More “what this dataset is telling me” (10 bullets).
    """
    primary = signals["primary_metric"]
    date_col = signals["date_col"]
    dims = signals["dims"]

    bullets = []
    if not primary:
        return ["No primary metric detected. Add a numeric business metric column (e.g., Revenue/Sales/Profit) to unlock richer insights."]

    # 1) top/bottom by best cut
    cut = pick_breakdown_dim(df)
    if cut:
        g = df.groupby(cut)[primary].sum(min_count=1).sort_values(ascending=False)
        if len(g) >= 2:
            bullets.append(f"Top contributor by **{cut}** is **{g.index[0]}** at **{format_compact(g.iloc[0])}**, while lowest is **{g.index[-1]}** at **{format_compact(g.iloc[-1])}**.")
            share = float(g.iloc[0] / g.sum()) if g.sum() not in [0, np.nan] and g.sum() != 0 else None
            if share is not None and not np.isnan(share):
                bullets.append(f"Concentration signal: top {cut} accounts for **{share*100:.1f}%** of total {primary}.")
    else:
        bullets.append("No stable categorical dimension detected (2–50 unique values). Add a column like Country/Store/Channel/Category to unlock business cuts.")

    # 2) trend insights
    if date_col:
        s = df[[date_col, primary]].dropna().sort_values(date_col)
        if len(s) >= 10:
            # weekly for stability
            t = s.set_index(date_col)[primary].resample("W").sum(min_count=1)
            if t.notna().sum() >= 4:
                last = t.dropna().iloc[-1]
                prev = t.dropna().iloc[-2] if len(t.dropna()) >= 2 else None
                if prev is not None and prev != 0:
                    bullets.append(f"Recent trend: latest weekly {primary} is **{format_compact(last)}**, changing **{((last-prev)/prev)*100:.1f}%** vs prior week.")
                # peak / trough
                bullets.append(f"Peak weekly {primary} is **{format_compact(t.max())}**; trough is **{format_compact(t.min())}** (weekly aggregation).")
    else:
        bullets.append("No date/time field detected. Add a Date column to unlock time trend insights and forecasting readiness.")

    # 3) drivers from R²
    pairs = signals["r2_vs_primary"]
    if pairs:
        top2 = pairs[:2]
        bullets.append(f"Key driver candidates: {', '.join([f'**{c}** (R²={r2:.2f})' for c, r2 in top2])}.")
        bullets.append("Interpretation: these variables move together with the primary metric; validate with segmentation and controls before acting.")
    else:
        bullets.append("No strong linear driver found vs primary metric (or not enough numeric columns). Add more numeric measures to strengthen driver analysis.")

    # 4) variability
    if signals["best_cut_dim"]:
        bullets.append(f"Variability is highest across **{signals['best_cut_dim']}**, suggesting segmentation here can reveal operational differences (pricing mix, promotions, or cost structure).")

    # 5) data quality
    worst = signals["worst_missing_cols"]
    if worst and worst[0]["missing_%"] > 0:
        bullets.append(f"Data quality: prioritize fixing **{worst[0]['column']}** (missing {worst[0]['missing_%']}%) to avoid bias in segmentation and trend analysis.")

    # pad to 10 with useful defaults
    bullets.append("Actionable next step: confirm definitions (e.g., Revenue gross vs net, COGS inclusive vs exclusive) to ensure insights are decision-ready.")
    bullets.append("If you plan forecasting: ensure consistent time grain (daily/weekly), and check for seasonality and promotions calendar.")
    bullets.append("If this is performance reporting: add a target/plan column to quantify variance-to-plan and explain drivers of gaps.")

    return bullets[:10]


def build_suggested_next_analyses(df: pd.DataFrame, signals: dict) -> list[dict]:
    """
    3 consultant-grade suggestions, data-specific, consistent format.
    Each suggestion includes: title, why, what_to_do, expected_output.
    """
    primary = signals["primary_metric"]
    date_col = signals["date_col"]
    dims = signals["dims"]
    best_cut = signals["best_cut_dim"]
    r2_pairs = signals["r2_vs_primary"]

    suggestions = []

    # 1) Driver & segmentation
    if primary and (best_cut or dims):
        cut = best_cut or (dims[0] if dims else None)
        driver = r2_pairs[0][0] if r2_pairs else None
        title = f"{primary} driver & segment performance"
        why = f"Your dataset supports a clear business breakdown (e.g., {cut}) and enough numeric depth to test drivers."
        what_to_do = [
            f"Compute {primary} by **{cut}** (total + share of total).",
            f"If available, test top driver candidates (e.g., {driver}) within each {cut} segment (compare slopes / R²).",
            "Check concentration: top 1–3 segments contribution and whether it is stable over time."
        ]
        expected = [
            f"Top/bottom {cut} table with contribution and % share.",
            "Driver comparison summary (which segment is most sensitive).",
            "Recommended focus segments and hypotheses to validate."
        ]
        suggestions.append({"title": title, "why": why, "what": what_to_do, "expected": expected})

    # 2) Trend decomposition
    if primary and date_col:
        dim = best_cut or pick_breakdown_dim(df)
        title = f"{primary} trend & seasonality scan"
        why = f"A time field ({date_col}) is present, enabling trend detection and early forecasting readiness checks."
        what_to_do = [
            f"Plot {primary} over time (weekly). Identify peaks/troughs and regime shifts.",
            f"Break down the time trend by top 5–6 categories of **{dim}** (multi-line).",
            "If spikes exist, cross-check whether they align to discount/promo variables or category mix changes."
        ]
        expected = [
            "Total trend chart (weekly) with marked peaks.",
            f"Breakdown trend by {dim} with legend and top categories only.",
            "A short narrative of what changed and why (hypotheses)."
        ]
        suggestions.append({"title": title, "why": why, "what": what_to_do, "expected": expected})

    # 3) Pricing/discount effectiveness (if discount exists)
    if primary:
        has_discount = any(pd.api.types.is_numeric_dtype(df[c]) and "discount" in _norm(c) for c in df.columns)
        if has_discount:
            title = "Discount effectiveness & price/mix sanity check"
            why = "Discount variables can create large swings in revenue/profitability; you want a simple, decision-ready read first."
            what_to_do = [
                "Bucket discount into bands (0–2%, 2–5%, 5–10%, …).",
                f"Compare average **{primary}** by discount band and by key cut (store/channel/category).",
                "Validate whether higher discounts correlate with higher total revenue or just lower unit economics."
            ]
            expected = [
                "Discount band chart with clear winners/losers.",
                "Short notes: where discount works vs where it likely erodes value.",
                "Recommendation: test controlled experiments / guardrails."
            ]
            suggestions.append({"title": title, "why": why, "what": what_to_do, "expected": expected})

    # Ensure exactly 3 (best effort)
    # If fewer than 3, add a generic but still useful one
    while len(suggestions) < 3:
        suggestions.append({
            "title": "Data quality & definition audit (fast)",
            "why": "Cleaner inputs produce dramatically better insights and forecasting reliability.",
            "what": [
                "Confirm metric definitions (gross vs net, currency, inclusive/exclusive costs).",
                "Check duplicates, outliers, and missing patterns by segment.",
                "Standardize date grain and category naming to reduce fragmentation."
            ],
            "expected": [
                "A small checklist of fixes with priority order.",
                "Before/after impact on missingness and stability.",
                "Green-light for deeper modeling."
            ]
        })

    return suggestions[:3]


# ---------------------------
# “Run analyses” (charts + commentary)
# ---------------------------
def run_analysis_pack(df: pd.DataFrame, signals: dict) -> list[dict]:
    """
    Returns 3 analyses with visuals and commentary.
    """
    primary = signals["primary_metric"]
    date_col = signals["date_col"]
    dims = signals["dims"]

    pack = []

    # A1) Driver analysis (scatter only if meaningful; else summary)
    # Use strongest R² pair vs primary if available
    pair = signals["r2_vs_primary"][0] if signals["r2_vs_primary"] else None
    if primary and pair:
        xcol, r2 = pair
        s = df[[xcol, primary]].dropna()
        fig = px.scatter(
            s,
            x=xcol,
            y=primary,
            trendline="ols",
            color_discrete_sequence=PLOTLY_PALETTE,
        )
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        bullets = [
            f"Strongest linear association vs **{primary}** is **{xcol}** with **R² = {r2:.2f}**.",
            "If this is causal in your business context, treat it as a **driver candidate**; validate with segmentation and controls.",
            f"Next: split by your best dimension (e.g., {signals['best_cut_dim']}) to see whether the relationship is stable or segment-specific."
        ]
        pack.append({"title": f"1) Driver signal: {primary} vs {xcol}", "fig": fig, "bullets": bullets})
    else:
        pack.append({"title": "1) Driver signal", "fig": None, "bullets": ["Not enough numeric structure to produce a reliable driver chart. Add more numeric measures or increase row count."]})

    # A2) Variability by best cut (CV)
    if primary and signals["best_cut_dim"]:
        cut = signals["best_cut_dim"]
        g = df.groupby(cut)[primary].sum(min_count=1).dropna()
        stats = pd.DataFrame({
            cut: g.index,
            "mean": df.groupby(cut)[primary].mean(),
            "std": df.groupby(cut)[primary].std(),
            "count": df.groupby(cut)[primary].count(),
        }).reset_index(drop=True)
        stats["Coefficient of Variation (CV)"] = (stats["std"] / stats["mean"]).replace([np.inf, -np.inf], np.nan)
        stats = stats.sort_values("Coefficient of Variation (CV)", ascending=False)

        fig = px.bar(
            stats.head(12),
            x=cut,
            y="Coefficient of Variation (CV)",
            text=stats.head(12)["Coefficient of Variation (CV)"].map(lambda v: f"{v:.2f}" if pd.notna(v) else "-"),
            color=cut,
            color_discrete_sequence=PLOTLY_PALETTE,
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
        bullets = [
            f"**Coefficient of Variation (CV)** = std/mean. Higher CV means **more variability** across {cut}.",
            f"Segments with high CV often indicate **mix effects** (product/category), inconsistent performance, or outlier events.",
            f"Use this to prioritize where to investigate: start with the top 1–2 {cut} segments by CV."
        ]
        pack.append({"title": f"2) Variability by best cut ({cut})", "fig": fig, "table": stats, "bullets": bullets})
    else:
        pack.append({"title": "2) Variability by best cut", "fig": None, "bullets": ["No suitable categorical cut found (need 2–50 unique values). Add a dimension like Store/Channel/Category/Team."]})

    # A3) Discount effectiveness (simplified)
    if primary:
        fig, bullets = fig_discount_effectiveness(df, primary)
        pack.append({"title": "3) Discount effectiveness (simple)", "fig": fig, "bullets": bullets})
    else:
        pack.append({"title": "3) Discount effectiveness", "fig": None, "bullets": ["Primary metric not detected."]})

    return pack


# ---------------------------
# AI Insights (OpenAI) – optional
# ---------------------------
def get_openai_client():
    # Streamlit secrets preferred
    api_key = None
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    if not api_key:
        api_key = st.session_state.get("OPENAI_API_KEY")

    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)


def build_ai_prompt(executive: list[str], insights: list[str], suggestions: list[dict], indicators: dict, profile_df: pd.DataFrame, signals: dict) -> str:
    """
    Consultant-grade, data-specific prompt.
    IMPORTANT: We only send summary-level stats, not raw rows.
    """
    prof = profile_df.copy()
    prof = prof[["column", "dtype", "missing_%", "unique_values"]].to_dict("records")

    r2pairs = [{"col": c, "r2": round(r2, 3)} for c, r2 in signals.get("r2_vs_primary", [])]

    return f"""
You are a senior analytics consultant. Write a crisp, decision-ready insight report.
Constraints:
- Use bullet points.
- Be specific to the dataset facts provided.
- Avoid generic advice; if you suggest a next step, tie it to an observed pattern.
- Do NOT invent data.

Dataset indicators:
- Coverage (usable rows): {indicators['coverage']}%
- Avg missing: {indicators['avg_missing']}%
- Confidence score: {indicators['confidence']} ({indicators['confidence_label']})

Dataset shape: rows={signals['shape'][0]}, cols={signals['shape'][1]}
Date column detected: {signals['date_col']}
Primary metric detected: {signals['primary_metric']}
Best cut dimension: {signals['best_cut_dim']} (CV approx {signals.get('best_cut_cv')})

Column profile (summary):
{prof}

Top R² pairs vs primary (if any):
{r2pairs}

Executive Summary bullets:
{executive}

Key Insights bullets:
{insights}

Suggested next analyses (3):
{suggestions}

Now produce:
1) "AI Insights Report" (8–12 bullets) — expand on the Key Insights with concrete interpretation.
2) "Suggested Next Analyses (aligned)" — restate the same 3 suggestions but with stronger business context, risks, and what output looks like.
Keep it concise, consultant-grade, and data-specific.
"""


def call_openai(prompt: str) -> str:
    client = get_openai_client()
    if client is None:
        return "AI is not configured. Add OPENAI_API_KEY to Streamlit Secrets."

    # cheap + good default
    model = "gpt-4o-mini"
    resp = client.responses.create(
        model=model,
        input=prompt,
    )
    # responses API returns output_text
    return getattr(resp, "output_text", str(resp))


# ---------------------------
# Export helpers (PDF & PPTX)
# ---------------------------
def export_pdf(title: str, bullets: list[str], filename: str = "ecai_executive_brief.pdf") -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, title)
    y -= 30

    c.setFont("Helvetica", 11)
    for b in bullets:
        # wrap
        text = f"• {b}"
        lines = []
        line = ""
        for word in text.split():
            if len(line + " " + word) > 95:
                lines.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        if line:
            lines.append(line)

        for ln in lines:
            if y < 60:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 11)
            c.drawString(55, y, ln)
            y -= 16
        y -= 6

    c.save()
    buffer.seek(0)
    return buffer.read()


def add_textbox_fit(slide, x, y, w, h, text, font_size=20, bold=False):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    p.alignment = PP_ALIGN.LEFT
    return box


def shrink_to_fit(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def export_pptx(summary_title: str, executive: list[str], insights: list[str], suggestions: list[dict], filename: str = "ecai_insight_slides.pptx") -> bytes:
    prs = Presentation()
    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    add_textbox_fit(slide, Inches(0.7), Inches(0.6), Inches(12.0), Inches(1.0), summary_title, font_size=34, bold=True)
    add_textbox_fit(slide, Inches(0.7), Inches(1.5), Inches(12.0), Inches(0.6), "Executive Summary + Key Insights", font_size=18, bold=False)

    def bullet_slide(title: str, bullets: list[str]):
        s = prs.slides.add_slide(prs.slide_layouts[5])
        add_textbox_fit(s, Inches(0.7), Inches(0.4), Inches(12.0), Inches(0.6), title, font_size=28, bold=True)

        # Fit bullets: shrink if long
        body = s.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(12.2), Inches(5.7))
        tf = body.text_frame
        tf.word_wrap = True
        tf.clear()

        # Heuristic font size
        total_chars = sum(len(b) for b in bullets)
        fs = 18
        if total_chars > 1400:
            fs = 14
        elif total_chars > 950:
            fs = 16

        for i, b in enumerate(bullets[:12]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = "• " + shrink_to_fit(b, 220)
            p.font.size = Pt(fs)
            p.level = 0

        return s

    bullet_slide("Executive Summary", executive)
    bullet_slide("Key Insights", insights)

    # Suggested next analyses slide (short)
    s = prs.slides.add_slide(prs.slide_layouts[5])
    add_textbox_fit(s, Inches(0.7), Inches(0.4), Inches(12.0), Inches(0.6), "Suggested Next Analyses (3)", font_size=28, bold=True)

    body = s.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(12.2), Inches(5.7))
    tf = body.text_frame
    tf.word_wrap = True
    tf.clear()
    for i, sug in enumerate(suggestions[:3], start=1):
        p = tf.paragraphs[0] if i == 1 else tf.add_paragraph()
        p.text = f"{i}. {sug['title']}"
        p.font.size = Pt(18)
        p.font.bold = True

        p2 = tf.add_paragraph()
        p2.text = f"Why: {shrink_to_fit(sug['why'], 220)}"
        p2.font.size = Pt(14)

        p3 = tf.add_paragraph()
        p3.text = f"Output: {shrink_to_fit(', '.join(sug['expected'][:2]), 220)}"
        p3.font.size = Pt(14)

        tf.add_paragraph().text = ""

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()


# ---------------------------
# Upload
# ---------------------------
st.subheader("Upload data")

uploaded = st.file_uploader(
    "Upload a CSV or Excel file",
    type=["csv", "xlsx", "xls"],
    help="Tip: avoid confidential / regulated data for this MVP.",
)

if uploaded is None:
    st.info("Upload a file to begin. (CSV or Excel)")
    st.stop()

# Read file
try:
    if uploaded.name.lower().endswith(".csv"):
        df_raw = pd.read_csv(uploaded)
    else:
        df_raw = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()

# Clean
df = coerce_dates(df_raw)
df = parse_numeric_like(df)

# Detect primary metric & supporting signals
primary_metric = guess_primary_metric(df)
secondary_metrics = guess_secondary_metrics(df, primary_metric)

indicators = compute_indicators(df, primary_metric)
signals = signal_extraction(df, primary_metric)

profile = basic_profile(df)

executive = build_executive_summary(df, signals, indicators)
key_insights = build_key_insights(df, signals)
suggestions = build_suggested_next_analyses(df, signals)

# ---------------------------
# TOP: Executive Summary + Key Insights
# ---------------------------
st.subheader("Executive Summary")
for b in executive:
    st.write(f"• {b}")

st.subheader("Key Insights")
for b in key_insights:
    st.write(f"• {b}")

# Indicators + explanation
st.subheader("Indicators")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Coverage", f"{indicators['coverage']:.1f}%")
c2.metric("Avg Missing", f"{indicators['avg_missing']:.1f}%")
c3.metric("Confidence", f"{indicators['confidence']} ({indicators['confidence_label']})")
strong_pairs = len(signals.get("r2_vs_primary", []))
c4.metric("Strong R² pairs", f"{strong_pairs}")

with st.expander("How these indicators work"):
    st.markdown(
        """
**Coverage** = % of rows that are “usable” (at least 80% non-missing fields).  
**Avg Missing** = average missing rate across all columns.  
**Confidence (0–100)** = rule-based score combining:
- Row count (more data → higher)
- Completeness (lower missing → higher)
- Numeric richness (more numeric columns → higher)
- Time-series readiness (date detected → higher)
- Primary metric detected (small bonus)

These are **not** statistical guarantees—just quick “readiness” signals for this MVP.
"""
    )

st.divider()

# ---------------------------
# Preview
# ---------------------------
st.subheader("Preview data")
st.dataframe(df.head(50), use_container_width=True)

st.subheader("Data profile")
st.dataframe(profile, use_container_width=True)

st.divider()

# ---------------------------
# Quick exploration (smarter defaults)
# ---------------------------
st.subheader("Quick exploration")

num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
cat_cols = candidate_dims(df)

# Default numeric: primary metric if exists, else first numeric
default_num = primary_metric if primary_metric in num_cols else (num_cols[0] if num_cols else None)
default_cat = pick_breakdown_dim(df) if cat_cols else None

qc1, qc2 = st.columns(2)
with qc1:
    num_selected = st.selectbox("Numeric column", options=num_cols if num_cols else ["(no numeric columns)"], index=(num_cols.index(default_num) if default_num in num_cols else 0))
with qc2:
    cat_selected = st.selectbox("Categorical column", options=cat_cols if cat_cols else ["(no categorical columns)"], index=(cat_cols.index(default_cat) if default_cat in cat_cols else 0))

if num_cols:
    left, right = st.columns(2)

    with left:
        # histogram for numeric distribution
        fig = px.histogram(df, x=num_selected, nbins=20, color_discrete_sequence=PLOTLY_PALETTE)
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        if cat_cols:
            g = df.groupby(cat_selected)[num_selected].count().reset_index(name="count")
            fig = px.bar(g, x=cat_selected, y="count", color=cat_selected, color_discrete_sequence=PLOTLY_PALETTE)
            fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No categorical column detected for the right-side chart.")
else:
    st.warning("No numeric columns detected—charts are limited.")

st.divider()

# ---------------------------
# Key business cuts (clean titles)
# ---------------------------
st.subheader("Key business cuts")

if primary_metric is None:
    st.info("No primary metric detected, so business-cut charts are limited.")
else:
    dims = candidate_dims(df)
    if not dims:
        st.info("No suitable categorical dimension detected (need 2–50 unique values).")
    else:
        # pick two best dims for bar charts
        dim1 = pick_breakdown_dim(df)
        dim2 = None
        for d in dims:
            if d != dim1:
                dim2 = d
                break

        colA, colB = st.columns(2)
        with colA:
            st.markdown(f"**{primary_metric} by {dim1}**")
            st.plotly_chart(fig_bar_topk(df, dim1, primary_metric, k=12), use_container_width=True)
        with colB:
            if dim2:
                st.markdown(f"**{primary_metric} by {dim2}**")
                st.plotly_chart(fig_bar_topk(df, dim2, primary_metric, k=12), use_container_width=True)
            else:
                st.info("Only one suitable categorical dimension detected.")

st.divider()

# ---------------------------
# Trend (smarter fallback dims)
# ---------------------------
st.subheader("Trend")

date_col = detect_date_col(df)
if primary_metric is None:
    st.info("No primary metric detected for trend charts.")
elif date_col is None:
    st.info("No date/time-like column detected. Add a Date column to unlock trends.")
else:
    # Choose frequency based on span
    span_days = (df[date_col].max() - df[date_col].min()).days if df[date_col].notna().any() else 0
    freq = "D"
    if span_days >= 180:
        freq = "W"
    if span_days >= 730:
        freq = "M"

    st.markdown(f"**Total {primary_metric} over time**")
    st.plotly_chart(fig_trend_total(df, date_col, primary_metric, freq=freq), use_container_width=True)

    breakdown_dim = pick_breakdown_dim(df)
    if breakdown_dim is not None:
        st.markdown(f"**{primary_metric} trend by {breakdown_dim} (top categories)**")
        st.plotly_chart(fig_trend_breakdown(df, date_col, breakdown_dim, primary_metric, topk=6, freq=freq), use_container_width=True)
    else:
        st.info("No stable categorical column detected for a breakdown trend (try adding Store/Channel/Category/Team/Payment columns).")

st.divider()

# ---------------------------
# Correlation (wider)
# ---------------------------
st.subheader("Correlation")

fig_corr, corr_df = fig_corr_heatmap(df)
if fig_corr is None:
    st.info("Not enough numeric columns to compute correlation.")
else:
    st.plotly_chart(fig_corr, use_container_width=True)

    # Key R² relationships
    if primary_metric and signals.get("r2_vs_primary"):
        st.markdown("**Key R² relationships (vs primary metric)**")
        for c, r2 in signals["r2_vs_primary"][:5]:
            st.write(f"- {c} → {primary_metric}: **R² = {r2:.3f}**")

st.divider()

# ---------------------------
# Suggested next analyses (single bold title) + Run all
# ---------------------------
st.subheader("Suggested next analyses")

for i, s in enumerate(suggestions, start=1):
    st.markdown(f"**{i}. {s['title']}**")
    st.write(f"**Why it matters:** {s['why']}")
    st.write("**What to do:**")
    for w in s["what"]:
        st.write(f"• {w}")
    st.write("**Expected output:**")
    for e in s["expected"]:
        st.write(f"• {e}")
    st.write("")

run_now = st.button("Run all 3 analyses now (beta)", type="primary")

if run_now:
    st.subheader("Generated analyses (beta)")
    pack = run_analysis_pack(df, signals)
    for item in pack:
        st.markdown(f"**{item['title']}**")
        if item.get("fig") is not None:
            st.plotly_chart(item["fig"], use_container_width=True)
        if item.get("table") is not None:
            st.dataframe(item["table"], use_container_width=True)
        # Commentary bullets
        for b in item.get("bullets", []):
            st.write(f"• {b}")
        st.write("")

st.divider()

# ---------------------------
# AI Insights Report (auto-run)
# ---------------------------
st.subheader("AI Insights Report")

# Auto-generate without click, but only once per upload (cached in session)
# (Costs tokens; keep lightweight)
auto_ai = st.toggle("Auto-generate AI insights", value=True, help="Uses your OpenAI API key via Streamlit Secrets. Costs a small amount per run.")
ai_out_key = f"ai_out::{uploaded.name}::{len(df)}::{df.shape[1]}"

if auto_ai:
    if ai_out_key not in st.session_state:
        with st.spinner("Generating AI insights…"):
            prompt = build_ai_prompt(executive, key_insights, suggestions, indicators, profile, signals)
            try:
                st.session_state[ai_out_key] = call_openai(prompt)
            except Exception as e:
                st.session_state[ai_out_key] = f"AI error: {e}"

    st.markdown(st.session_state[ai_out_key])
else:
    st.info("Toggle on to generate AI insights.")

st.divider()

# ---------------------------
# Export
# ---------------------------
st.subheader("Export")

pdf_bytes = export_pdf("EC-AI Insight — Executive Brief", executive)
st.download_button(
    "Download Executive Brief (PDF)",
    data=pdf_bytes,
    file_name="ecai_executive_brief.pdf",
    mime="application/pdf",
)

pptx_bytes = export_pptx("EC-AI Insight — Summary", executive, key_insights, suggestions)
st.download_button(
    "Download Slides (PPTX)",
    data=pptx_bytes,
    file_name="ecai_insight_slides.pptx",
    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
)

st.caption("Note: This MVP is for demo/testing. Please avoid uploading confidential or regulated data.")
