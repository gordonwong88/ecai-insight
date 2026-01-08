import io
import re
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Optional exports
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN

# Optional OpenAI (AI Insights)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# -----------------------------
# App Config
# -----------------------------
st.set_page_config(
    page_title="EC-AI Insight (MVP)",
    page_icon="📊",
    layout="wide",
)
st.markdown("""
<style>
/* Hide Streamlit top header and toolbar */
header[data-testid="stHeader"] {display: none;}
div[data-testid="stToolbar"] {display: none;}
/* Remove extra top padding that appears after hiding header */
section.main > div {padding-top: 1rem;}
</style>
""", unsafe_allow_html=True)

APP_TITLE = "EC-AI Insight (MVP)"
APP_TAGLINE = "Turning Data Into Intelligence — Upload a CSV/Excel to get instant profiling + insights."

# Plotly default palette (colorful)
PLOTLY_TEMPLATE = "plotly_white"
PX_QUAL = px.colors.qualitative.Set2  # colorful but not too loud


# -----------------------------
# Helpers: detection / cleaning
# -----------------------------
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")


KEYWORDS = {
    "date": ["date", "dt", "day", "month", "period", "as_of"],
    "revenue": ["revenue", "sales", "income", "turnover", "gmv", "bookings"],
    "cost": ["cogs", "cost", "expense", "opex"],
    "profit": ["profit", "margin", "gross_margin", "net_income", "ebit"],
    "units": ["units", "qty", "quantity", "volume"],
    "discount": ["discount", "disc", "promo", "markdown"],
    "country": ["country", "region", "geo", "market"],
    "store": ["store", "branch", "location", "site", "outlet"],
    "channel": ["channel", "source", "platform"],
    "category": ["category", "product", "segment", "vertical", "industry", "sector"],
    "team": ["team", "owner", "rm", "salesperson", "rep", "agent"],
    "customer": ["customer", "client", "account", "buyer", "user_id", "customer_id", "client_id"],
    "status": ["status", "stage", "approval", "approved", "flag", "returned", "cancelled"],
}


def detect_date_col(df: pd.DataFrame) -> Optional[str]:
    # Prefer columns with date-like names
    cols = list(df.columns)
    scored = []
    for c in cols:
        cn = _norm(c)
        score = 0
        if any(k in cn for k in KEYWORDS["date"]):
            score += 3
        # actual dtype hint
        if np.issubdtype(df[c].dtype, np.datetime64):
            score += 4
        scored.append((score, c))
    scored.sort(reverse=True)
    best_score, best_col = scored[0] if scored else (0, None)

    # Try parsing if score low
    if best_col is None:
        return None

    if best_score >= 4:
        return best_col

    # Attempt parse top candidates
    candidates = [c for s, c in scored[:3]]
    for c in candidates:
        try:
            parsed = pd.to_datetime(df[c], errors="coerce", infer_datetime_format=True)
            if parsed.notna().mean() > 0.6:
                return c
        except Exception:
            pass
    return None


def coerce_dates(df: pd.DataFrame, date_col: Optional[str]) -> Tuple[pd.DataFrame, Optional[str]]:
    if not date_col:
        return df, None
    out = df.copy()
    try:
        out[date_col] = pd.to_datetime(out[date_col], errors="coerce", infer_datetime_format=True)
        if out[date_col].notna().mean() < 0.6:
            return df, None
        return out, date_col
    except Exception:
        return df, None


def detect_metric_cols(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Detect key business metrics by column name + numeric type."""
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return {
            "revenue": None,
            "cost": None,
            "profit": None,
            "units": None,
            "discount": None,
        }

    def pick(keys: List[str]) -> Optional[str]:
        best = None
        best_score = -1
        for c in numeric_cols:
            cn = _norm(c)
            score = 0
            for k in keys:
                if k in cn:
                    score += 2
            # prefer columns with larger magnitude variability (often more meaningful)
            s = df[c].replace([np.inf, -np.inf], np.nan).dropna()
            if len(s) >= 5:
                score += min(2, float(np.log10(np.nanstd(s) + 1)) / 3)
            if score > best_score:
                best_score = score
                best = c
        return best if best_score >= 2 else None

    return {
        "revenue": pick(KEYWORDS["revenue"]),
        "cost": pick(KEYWORDS["cost"]),
        "profit": pick(KEYWORDS["profit"]),
        "units": pick(KEYWORDS["units"]),
        "discount": pick(KEYWORDS["discount"]),
    }


def detect_cuts(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Detect common categorical dimensions (cuts)."""
    cat_cols = [c for c in df.columns if (df[c].dtype == "object" or pd.api.types.is_categorical_dtype(df[c]))]
    # also allow low-cardinality non-object
    for c in df.columns:
        if c not in cat_cols and pd.api.types.is_numeric_dtype(df[c]):
            # treat as category if small number of unique values
            if df[c].nunique(dropna=True) <= 12:
                cat_cols.append(c)

    def pick(keys: List[str]) -> Optional[str]:
        best = None
        best_score = -1
        for c in cat_cols:
            cn = _norm(c)
            score = sum(2 for k in keys if k in cn)
            # prefer medium cardinality (good for charts)
            nun = df[c].nunique(dropna=True)
            if 2 <= nun <= 30:
                score += 1.5
            elif nun > 200:
                score -= 2
            if score > best_score:
                best_score = score
                best = c
        return best if best_score >= 2 else None

    # If "country" not found, we’ll still use store/channel/category for trend breakdown.
    return {
        "country": pick(KEYWORDS["country"]),
        "store": pick(KEYWORDS["store"]),
        "channel": pick(KEYWORDS["channel"]),
        "category": pick(KEYWORDS["category"]),
        "team": pick(KEYWORDS["team"]),
        "customer": pick(KEYWORDS["customer"]),
        "status": pick(KEYWORDS["status"]),
    }


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Standardize column names visually (keep original, but strip spaces)
    out.columns = [str(c).strip() for c in out.columns]

    # Convert obvious numeric strings
    for c in out.columns:
        if out[c].dtype == "object":
            # try numeric coercion if many look numeric
            s = out[c].astype(str).str.replace(",", "", regex=False).str.strip()
            coerced = pd.to_numeric(s, errors="coerce")
            if coerced.notna().mean() > 0.7:
                out[c] = coerced

    return out


def profile_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        missing_pct = float(df[c].isna().mean() * 100)
        nun = int(df[c].nunique(dropna=True))
        rows.append(
            {
                "column": c,
                "dtype": str(df[c].dtype),
                "missing_%": round(missing_pct, 1),
                "unique_values": nun,
            }
        )
    return pd.DataFrame(rows)


# -----------------------------
# Indicators logic
# -----------------------------
def compute_indicators(df: pd.DataFrame) -> Dict[str, object]:
    coverage = 100.0  # by definition: dataset loaded. we can interpret as "non-empty"
    avg_missing = float(df.isna().mean().mean() * 100) if df.size else 0.0

    # Confidence is a heuristic score 0-100:
    # - more rows/cols helps
    # - lower missing helps
    # - having at least 1 date + 2 numeric columns helps
    n_rows, n_cols = df.shape
    date_col = detect_date_col(df)
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    num_count = len(num_cols)

    score = 40
    score += min(20, math.log10(max(n_rows, 1) + 1) * 8)  # up to ~20
    score += min(10, n_cols)  # up to 10
    score += 12 if date_col else 0
    score += 8 if num_count >= 2 else (4 if num_count == 1 else 0)
    score -= min(30, avg_missing * 1.2)

    score = int(max(0, min(100, round(score))))
    band = "High" if score >= 80 else ("Medium" if score >= 55 else "Low")

    return {
        "coverage_pct": round(coverage, 0),
        "avg_missing_pct": round(avg_missing, 1),
        "confidence_score": score,
        "confidence_band": band,
    }


# -----------------------------
# Stats: correlation + R²
# -----------------------------
def corr_strength_label(r_abs: float) -> str:
    # Common heuristic for correlation strength
    # (not a law of nature, but a useful guide)
    if r_abs < 0.2:
        return "Very weak"
    if r_abs < 0.4:
        return "Weak"
    if r_abs < 0.6:
        return "Moderate"
    if r_abs < 0.8:
        return "Strong"
    return "Very strong"


def r2_strength_label(r2: float) -> str:
    if r2 < 0.04:
        return "Very weak"
    if r2 < 0.16:
        return "Weak"
    if r2 < 0.36:
        return "Moderate"
    if r2 < 0.64:
        return "Strong"
    return "Very strong"


def compute_r2_pairs(df: pd.DataFrame, numeric_cols: List[str], top_k: int = 4) -> List[Tuple[str, str, float, float]]:
    # Returns list: (x, y, r, r2) sorted by r2 desc
    pairs = []
    for i in range(len(numeric_cols)):
        for j in range(i + 1, len(numeric_cols)):
            a, b = numeric_cols[i], numeric_cols[j]
            sub = df[[a, b]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(sub) < 8:
                continue
            r = float(sub[a].corr(sub[b]))
            if np.isnan(r):
                continue
            r2 = r * r
            pairs.append((a, b, r, r2))
    pairs.sort(key=lambda x: x[3], reverse=True)
    return pairs[:top_k]


def corr_heatmap(df: pd.DataFrame, numeric_cols: List[str]) -> Optional[go.Figure]:
    if len(numeric_cols) < 2:
        return None

    corr = df[numeric_cols].replace([np.inf, -np.inf], np.nan).corr()
    # Annotate values with 1 decimal
    z = corr.values
    text = np.vectorize(lambda v: "" if pd.isna(v) else f"{v:.2f}")(z)

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=numeric_cols,
            y=numeric_cols,
            text=text,
            texttemplate="%{text}",
            colorscale="Blues",
            zmin=-1,
            zmax=1,
            colorbar=dict(title="r"),
        )
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=520,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


# -----------------------------
# Auto insight extraction (rule-based)
# -----------------------------
def fmt_num(x: float) -> str:
    # one decimal for charts & most UI numbers
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    ax = abs(float(x))
    if ax >= 1_000_000_000:
        return f"{x/1_000_000_000:.1f}B"
    if ax >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    if ax >= 1_000:
        return f"{x/1_000:.1f}k"
    return f"{x:.1f}"


def pick_default_numeric(df: pd.DataFrame, metrics: Dict[str, Optional[str]]) -> Optional[str]:
    # prioritize revenue, then profit, then cost, then first numeric
    for k in ["revenue", "profit", "cost", "units"]:
        if metrics.get(k) and pd.api.types.is_numeric_dtype(df[metrics[k]]):
            return metrics[k]
    nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    return nums[0] if nums else None


def key_insights_pack(df: pd.DataFrame, metrics: Dict[str, Optional[str]], cuts: Dict[str, Optional[str]], date_col: Optional[str]) -> List[str]:
    insights = []
    n_rows, n_cols = df.shape
    inds = compute_indicators(df)

    insights.append(f"Dataset loaded: **{n_rows:,} rows** × **{n_cols} columns**; avg missing **{inds['avg_missing_pct']}%**; confidence **{inds['confidence_score']} ({inds['confidence_band']})**.")

    # Numeric summaries
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if metrics.get("revenue"):
        s = df[metrics["revenue"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) > 0:
            insights.append(f"Revenue: avg **{fmt_num(s.mean())}**, median **{fmt_num(s.median())}**, range **{fmt_num(s.min())} → {fmt_num(s.max())}**.")
    if metrics.get("cost"):
        s = df[metrics["cost"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) > 0:
            insights.append(f"Cost/COGS: avg **{fmt_num(s.mean())}**; range **{fmt_num(s.min())} → {fmt_num(s.max())}**.")
    if metrics.get("profit"):
        s = df[metrics["profit"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) > 0:
            insights.append(f"Profit/Margin: avg **{fmt_num(s.mean())}**; range **{fmt_num(s.min())} → {fmt_num(s.max())}**.")

    # Top / bottom by key cut for revenue
    revenue_col = metrics.get("revenue")
    best_cut = None
    for k in ["country", "store", "channel", "category", "team"]:
        if cuts.get(k):
            best_cut = cuts[k]
            break

    if revenue_col and best_cut:
        tmp = df[[best_cut, revenue_col]].dropna()
        if len(tmp) > 0:
            agg = tmp.groupby(best_cut)[revenue_col].sum().sort_values(ascending=False)
            if len(agg) >= 2:
                top_name, top_val = agg.index[0], agg.iloc[0]
                bot_name, bot_val = agg.index[-1], agg.iloc[-1]
                insights.append(f"Revenue concentration: top **{best_cut}** is **{top_name} ({fmt_num(top_val)})**; lowest is **{bot_name} ({fmt_num(bot_val)})**.")

    # Trend comment
    if revenue_col and date_col:
        ts = df[[date_col, revenue_col]].dropna()
        if len(ts) > 5:
            ts = ts.sort_values(date_col)
            # resample weekly if too dense
            span_days = (ts[date_col].max() - ts[date_col].min()).days if pd.notna(ts[date_col].max()) else 0
            if span_days >= 45:
                ts2 = ts.set_index(date_col)[revenue_col].resample("W").sum().dropna()
            else:
                ts2 = ts.set_index(date_col)[revenue_col].resample("D").sum().dropna()

            if len(ts2) >= 3:
                first, last = ts2.iloc[0], ts2.iloc[-1]
                change = (last - first) / (abs(first) + 1e-9)
                direction = "up" if change > 0.05 else ("down" if change < -0.05 else "flat")
                insights.append(f"Revenue trend (total): **{direction}** over the period (start {fmt_num(first)} → end {fmt_num(last)}).")

    # Strong relationships
    if len(num_cols) >= 2:
        pairs = compute_r2_pairs(df, num_cols, top_k=3)
        if pairs:
            a, b, r, r2 = pairs[0]
            insights.append(f"Strongest numeric relationship: **{a} ↔ {b}** with r={r:.2f} ({corr_strength_label(abs(r))}), R²={r2:.2f} ({r2_strength_label(r2)}).")

    # Pad to ~10 bullets if needed (but keep useful)
    # Add data quality bullets
    miss_cols = df.isna().mean().sort_values(ascending=False)
    top_miss = miss_cols[miss_cols > 0].head(2)
    for c, v in top_miss.items():
        insights.append(f"Data quality: **{c}** has **{v*100:.1f}%** missing values — consider cleaning/imputation or excluding from key KPIs.")
    if not top_miss.empty:
        pass
    else:
        insights.append("Data quality: no material missingness detected — good for immediate analysis.")

    return insights[:10]


# -----------------------------
# Suggested next analyses (AI prompt + aligned w/ app)
# -----------------------------
def build_next_analyses_prompt(
    df: pd.DataFrame,
    metrics: Dict[str, Optional[str]],
    cuts: Dict[str, Optional[str]],
    date_col: Optional[str],
    r2_pairs: List[Tuple[str, str, float, float]],
) -> str:
    # Use ONLY summary stats to reduce data exposure risk
    n_rows, n_cols = df.shape
    prof = profile_table(df).to_dict("records")

    top_rel = []
    for a, b, r, r2 in r2_pairs[:3]:
        top_rel.append(
            {
                "pair": f"{a} vs {b}",
                "r": round(r, 3),
                "r2": round(r2, 3),
                "strength": corr_strength_label(abs(r)),
            }
        )

    prompt = f"""
You are a senior management consultant. Create exactly 3 "Suggested next analyses" for a dataset.
Make them feel practical and data-specific, not generic.

Output format:
1) Title
- Business Context: ...
- What to do: ...
- Expected Insight: ... (be specific; give examples of what patterns to look for)
- Outputs: ... (charts/tables)

Constraints:
- Exactly 3 analyses.
- The analyses MUST align with what an analytics app can do next (segment breakdowns, trends, elasticity/proxy, driver checks).
- Keep each analysis concise but meaningful (4 bullets max).
- Avoid jargon and avoid external data claims.

Dataset summary:
- Rows: {n_rows}, Columns: {n_cols}
- Date column detected: {date_col}
- Key metric guesses: {metrics}
- Key cuts detected: {cuts}
- Top numeric relationships (sample): {top_rel}
- Column profile (name, dtype, missing %, unique values): {prof[:25]}
"""
    return prompt.strip()


def parse_analyses_text(text: str) -> List[Dict[str, str]]:
    # Minimal parser: split by "1)" / "2)" / "3)"
    chunks = re.split(r"\n(?=\s*[1-3]\))", text.strip())
    out = []
    for ch in chunks:
        m = re.match(r"\s*([1-3])\)\s*(.+)", ch.strip())
        if not m:
            continue
        title = m.group(2).strip()
        out.append({"title": title, "body": ch.strip()})
    # If model didn't format perfectly, fallback to whole text
    if len(out) < 3:
        return [{"title": "Suggested next analyses", "body": text.strip()}]
    return out[:3]


# -----------------------------
# “Run analyses” (1-click) — simple, rule-based
# -----------------------------
def run_analysis_1_driver(df: pd.DataFrame, metrics: Dict[str, Optional[str]], cuts: Dict[str, Optional[str]]) -> Tuple[Optional[go.Figure], List[str]]:
    """Revenue driver scatter vs COGS (or closest numeric pair)"""
    notes = []
    revenue = metrics.get("revenue")
    cost = metrics.get("cost")

    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if revenue is None or (revenue not in num_cols):
        # fallback: pick first numeric
        revenue = num_cols[0] if num_cols else None

    if cost is None or (cost not in num_cols):
        # fallback: pick another numeric
        cost = None
        for c in num_cols:
            if c != revenue:
                cost = c
                break

    if revenue is None or cost is None:
        return None, ["Not enough numeric columns to run a driver scatter."]

    sub = df[[revenue, cost]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(sub) < 10:
        return None, ["Not enough clean rows to run a driver scatter."]

    r = float(sub[revenue].corr(sub[cost]))
    r2 = r * r
    notes.append(f"Correlation between **{revenue}** and **{cost}** is **r={r:.2f} ({corr_strength_label(abs(r))})**, R²={r2:.2f} ({r2_strength_label(r2)}).")
    notes.append("Use this as a *directional signal* — confirm with segment controls (e.g., store/channel/category) before acting.")

    fig = px.scatter(
        sub,
        x=cost,
        y=revenue,
        trendline="ols",
        template=PLOTLY_TEMPLATE,
        opacity=0.65,
        title=f"{revenue} vs {cost} (with trendline)",
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
    return fig, notes


def run_analysis_2_variability(df: pd.DataFrame, metrics: Dict[str, Optional[str]], cuts: Dict[str, Optional[str]]) -> Tuple[Optional[pd.DataFrame], Optional[go.Figure], List[str], Optional[str]]:
    """Pick best cut: where metric varies most (CV = coefficient of variation)."""
    notes = []
    revenue = metrics.get("revenue")
    if revenue is None or not pd.api.types.is_numeric_dtype(df.get(revenue, pd.Series(dtype=float))):
        revenue = pick_default_numeric(df, metrics)

    if revenue is None:
        return None, None, ["No numeric metric available for variability analysis."], None

    candidate_cuts = [cuts.get(k) for k in ["country", "store", "channel", "category", "team", "status"] if cuts.get(k)]
    # fallback: any object col with 2-12 uniques
    if not candidate_cuts:
        for c in df.columns:
            if df[c].dtype == "object" and 2 <= df[c].nunique(dropna=True) <= 12:
                candidate_cuts.append(c)

    if not candidate_cuts:
        return None, None, ["No suitable categorical column found for variability analysis."], None

    best = None
    best_cv = -1
    best_tbl = None

    for cut in candidate_cuts:
        tmp = df[[cut, revenue]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(tmp) < 20:
            continue
        agg = tmp.groupby(cut)[revenue].agg(["mean", "std", "count"]).reset_index()
        agg["cv (Coefficient of Variation)"] = agg["std"] / (agg["mean"].abs() + 1e-9)
        # weighted average CV
        w = agg["count"] / agg["count"].sum()
        cv_weighted = float((agg["cv (Coefficient of Variation)"] * w).sum())
        if cv_weighted > best_cv:
            best_cv = cv_weighted
            best = cut
            best_tbl = agg.sort_values("cv (Coefficient of Variation)", ascending=False)

    if best is None or best_tbl is None:
        return None, None, ["Not enough data density to compute variability by cut."], None

    # Format and chart
    tbl = best_tbl.copy()
    tbl["mean"] = tbl["mean"].round(1)
    tbl["std"] = tbl["std"].round(1)
    tbl["cv (Coefficient of Variation)"] = tbl["cv (Coefficient of Variation)"].round(2)

    fig = px.bar(
        tbl,
        x=best,
        y="cv (Coefficient of Variation)",
        template=PLOTLY_TEMPLATE,
        color=best,
        color_discrete_sequence=PX_QUAL,
        title=f"Variability (CV) of {revenue} by {best}",
    )
    fig.update_layout(height=380, showlegend=False, margin=dict(l=10, r=10, t=50, b=10))

    notes.append(f"Detected cut: **{best}**. Higher CV means that segments differ more in typical {revenue}.")
    notes.append("Use this to prioritize where segmentation matters most (e.g., different strategy per segment).")

    return tbl, fig, notes, best


def run_analysis_3_discount(df: pd.DataFrame, metrics: Dict[str, Optional[str]], cuts: Dict[str, Optional[str]]) -> Tuple[Optional[go.Figure], List[str]]:
    """Simplified discount effectiveness: avg revenue per transaction/row by discount band."""
    notes = []

    revenue = metrics.get("revenue") or pick_default_numeric(df, metrics)
    disc = metrics.get("discount")

    if revenue is None or disc is None:
        return None, ["Discount effectiveness requires a Revenue-like column and a Discount-like column."]

    if not pd.api.types.is_numeric_dtype(df[revenue]) or not pd.api.types.is_numeric_dtype(df[disc]):
        return None, ["Revenue/Discount columns must be numeric."]

    tmp = df[[revenue, disc]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(tmp) < 30:
        return None, ["Not enough clean rows for discount effectiveness."]

    # Normalize discount to 0-1 if looks like percent
    d = tmp[disc].copy()
    if d.max() > 1.5:  # likely 0-100
        d = d / 100.0

    bins = [-1e-9, 0.02, 0.05, 0.10, 0.15, 0.20, 10]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]

    tmp2 = tmp.copy()
    tmp2["Discount_Band"] = pd.cut(d, bins=bins, labels=labels)
    agg = tmp2.groupby("Discount_Band")[revenue].agg(["mean", "count"]).reset_index()
    agg["mean"] = agg["mean"].astype(float)

    # Clarify: average revenue per row/transaction
    notes.append(f"Metric shown: **average {revenue} per record/transaction** (not per customer unless the dataset has a customer ID and you aggregate by customer).")
    best = agg.sort_values("mean", ascending=False).head(1)
    worst = agg.sort_values("mean", ascending=True).head(1)
    if len(best) and len(worst):
        notes.append(f"Best-performing discount band: **{best['Discount_Band'].iloc[0]}** with avg **{fmt_num(best['mean'].iloc[0])}** (n={int(best['count'].iloc[0])}).")
        notes.append(f"Weakest discount band: **{worst['Discount_Band'].iloc[0]}** with avg **{fmt_num(worst['mean'].iloc[0])}** (n={int(worst['count'].iloc[0])}).")
    notes.append("Starting read only: confirm with controls (store/channel/category) to avoid mixing effects.")

    fig = px.bar(
        agg,
        x="Discount_Band",
        y="mean",
        template=PLOTLY_TEMPLATE,
        color="Discount_Band",
        color_discrete_sequence=PX_QUAL,
        title=f"Discount effectiveness: average {revenue} per transaction/record",
        text=agg["mean"].apply(fmt_num),
    )
    fig.update_traces(textposition="inside")
    fig.update_layout(height=420, showlegend=False, yaxis_title=f"Avg {revenue} per record", margin=dict(l=10, r=10, t=60, b=10))
    return fig, notes


# -----------------------------
# Trend charts (including small multiples)
# -----------------------------
def trend_total(df: pd.DataFrame, date_col: str, metric: str) -> Optional[go.Figure]:
    tmp = df[[date_col, metric]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(tmp) < 5:
        return None
    tmp = tmp.sort_values(date_col)
    tmp = tmp.set_index(date_col)[metric].resample("D").sum().dropna().reset_index()

    fig = px.line(
        tmp,
        x=date_col,
        y=metric,
        template=PLOTLY_TEMPLATE,
        title=f"{metric} trend (total)",
        markers=True,
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def trend_breakdown_small_multiples(
    df: pd.DataFrame,
    date_col: str,
    metric: str,
    by_col: str,
    top_n: int = 5,
) -> Optional[go.Figure]:
    tmp = df[[date_col, by_col, metric]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(tmp) < 30:
        return None

    # pick top categories by total metric
    totals = tmp.groupby(by_col)[metric].sum().sort_values(ascending=False)
    keep = list(totals.head(top_n).index)
    tmp = tmp[tmp[by_col].isin(keep)].copy()

    # daily aggregation
    tmp = tmp.sort_values(date_col)
    g = tmp.groupby([pd.Grouper(key=date_col, freq="D"), by_col])[metric].sum().reset_index()

    # Facet charts: one store one chart
    fig = px.line(
        g,
        x=date_col,
        y=metric,
        facet_col=by_col,
        facet_col_wrap=2,
        template=PLOTLY_TEMPLATE,
        markers=True,
        title=f"{metric} trend by {by_col} (top {top_n})",
        color=by_col,
        color_discrete_sequence=PX_QUAL,
    )
    fig.update_layout(height=650, showlegend=False, margin=dict(l=10, r=10, t=60, b=10))
    # clean facet titles
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return fig


# -----------------------------
# Export: PDF / PPTX
# -----------------------------
def make_pdf_bytes(title: str, bullets: List[str]) -> bytes:
    buff = io.BytesIO()
    c = canvas.Canvas(buff, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, title)
    y -= 30

    c.setFont("Helvetica", 11)
    for b in bullets:
        # wrap text
        lines = wrap_text(b.replace("**", ""), max_chars=100)
        for ln in lines:
            if y < 80:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 11)
            c.drawString(60, y, f"• {ln}" if ln == lines[0] else f"  {ln}")
            y -= 16

    c.showPage()
    c.save()
    buff.seek(0)
    return buff.read()


def wrap_text(s: str, max_chars: int = 90) -> List[str]:
    words = s.split()
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


def fit_text_frame(tf, text: str, max_font: int = 22, min_font: int = 10):
    # crude auto-fit: reduce font until fits number of lines threshold
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.LEFT

    # heuristic: reduce font for longer text
    length = len(text)
    size = max_font
    if length > 600:
        size = 12
    elif length > 450:
        size = 14
    elif length > 300:
        size = 16
    elif length > 200:
        size = 18
    else:
        size = max_font

    size = max(min_font, min(max_font, size))
    for run in p.runs:
        run.font.size = Pt(size)


def make_pptx_bytes(title: str, exec_summary: List[str], insights: List[str], suggested: List[Dict[str, str]]) -> bytes:
    prs = Presentation()
    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    tx = slide.shapes.add_textbox(Inches(0.7), Inches(0.8), Inches(12.0), Inches(1.2))
    tf = tx.text_frame
    tf.text = title
    tf.paragraphs[0].runs[0].font.size = Pt(34)
    tf.paragraphs[0].runs[0].font.bold = True

    sub = slide.shapes.add_textbox(Inches(0.7), Inches(1.7), Inches(12.0), Inches(0.6))
    sub_tf = sub.text_frame
    sub_tf.text = "Executive brief generated by EC-AI Insight"
    sub_tf.paragraphs[0].runs[0].font.size = Pt(16)

    # Slide 2: Exec summary
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    t = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(12.0), Inches(0.6))
    ttf = t.text_frame
    ttf.text = "Executive Summary"
    ttf.paragraphs[0].runs[0].font.size = Pt(26)
    ttf.paragraphs[0].runs[0].font.bold = True

    box = slide.shapes.add_textbox(Inches(0.7), Inches(1.2), Inches(12.3), Inches(5.8))
    body = "\n".join([f"• {x.replace('**','')}" for x in exec_summary])
    fit_text_frame(box.text_frame, body, max_font=18, min_font=11)

    # Slide 3: Key insights
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    t = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(12.0), Inches(0.6))
    ttf = t.text_frame
    ttf.text = "Key Insights"
    ttf.paragraphs[0].runs[0].font.size = Pt(26)
    ttf.paragraphs[0].runs[0].font.bold = True

    box = slide.shapes.add_textbox(Inches(0.7), Inches(1.2), Inches(12.3), Inches(5.8))
    body = "\n".join([f"• {x.replace('**','')}" for x in insights])
    fit_text_frame(box.text_frame, body, max_font=18, min_font=11)

    # Slides 4-6: suggested analyses
    for i, s in enumerate(suggested[:3], start=1):
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        t = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(12.0), Inches(0.6))
        ttf = t.text_frame
        ttf.text = f"Suggested next analysis #{i}"
        ttf.paragraphs[0].runs[0].font.size = Pt(24)
        ttf.paragraphs[0].runs[0].font.bold = True

        box = slide.shapes.add_textbox(Inches(0.7), Inches(1.2), Inches(12.3), Inches(5.8))
        fit_text_frame(box.text_frame, s["body"].replace("**", ""), max_font=16, min_font=10)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()


# -----------------------------
# AI Insights (OpenAI)
# -----------------------------
def ai_generate_summary_and_suggestions(
    df: pd.DataFrame,
    metrics: Dict[str, Optional[str]],
    cuts: Dict[str, Optional[str]],
    date_col: Optional[str],
    r2_pairs: List[Tuple[str, str, float, float]],
) -> Dict[str, object]:
    if OpenAI is None:
        return {"error": "openai package not available. Add 'openai' to requirements.txt."}

    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        return {"error": "OPENAI_API_KEY not found in Streamlit Secrets."}

    client = OpenAI(api_key=api_key)

    prompt = build_next_analyses_prompt(df, metrics, cuts, date_col, r2_pairs)

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        text = resp.output_text
        return {"text": text, "parsed": parse_analyses_text(text)}
    except Exception as e:
        return {"error": str(e)}


# -----------------------------
# UI
# -----------------------------
st.title(APP_TITLE)
st.caption(APP_TAGLINE)

uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])

if uploaded is None:
    st.info("Upload a dataset to start. Tip: try the retail / marketing / HR / SaaS / inventory dummy datasets you generated.")
    st.stop()

# Read data
try:
    if uploaded.name.lower().endswith(".csv"):
        df_raw = pd.read_csv(uploaded)
    else:
        df_raw = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Failed to read file: {e}")
    st.stop()

df_raw = clean_df(df_raw)

# Detect & coerce date
date_col_guess = detect_date_col(df_raw)
df, date_col = coerce_dates(df_raw, date_col_guess)

metrics = detect_metric_cols(df)
cuts = detect_cuts(df)

# Ensure we prioritize a meaningful numeric default (Revenue if possible)
default_numeric = pick_default_numeric(df, metrics)

# Build top-of-page Executive Summary + Key Insights (BEFORE preview)
st.markdown("## Executive Summary")
exec_summary = key_insights_pack(df, metrics, cuts, date_col)
for b in exec_summary[:7]:  # 7-10 points total (we'll show 7 here; the next section has deeper insights)
    st.markdown(f"- {b}")

st.markdown("## Key Insights")
insights = key_insights_pack(df, metrics, cuts, date_col)
# show full 10 bullets here (user requested 10)
for b in insights[:10]:
    st.markdown(f"- {b}")

# Indicators + explanation
inds = compute_indicators(df)
st.markdown("## Indicators")

with st.expander("How these indicators work (logic)", expanded=False):
    st.write(
        """
**Coverage**: A quick confirmation that the dataset is readable and non-empty (MVP definition).
**Avg Missing**: Average missing % across all cells (mean of column missing rates).
**Confidence** (0–100): A practical reliability score based on:
- number of rows/columns (more data = more stable),
- presence of a date column (enables trend analysis),
- number of numeric columns (enables metrics + correlations),
- and penalties for missingness.
This is a *heuristic* to guide users; it is not a statistical guarantee.
"""
    )

c1, c2, c3 = st.columns(3)
c1.metric("Coverage", f"{inds['coverage_pct']:.0f}%")
c2.metric("Avg Missing", f"{inds['avg_missing_pct']:.1f}%")
c3.metric("Confidence", f"{inds['confidence_score']} ({inds['confidence_band']})")

st.divider()

# Preview + profile
st.markdown("## Preview data")
st.dataframe(df.head(50), use_container_width=True)

st.markdown("## Data profile")
st.dataframe(profile_table(df), use_container_width=True)

st.divider()

# Quick exploration (keep as user-driven but default to best metric)
st.markdown("## Quick exploration")
num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
cat_cols = [c for c in df.columns if df[c].dtype == "object" or pd.api.types.is_categorical_dtype(df[c])]

colA, colB = st.columns(2)

if num_cols:
    default_num = default_numeric if default_numeric in num_cols else num_cols[0]
    num_choice = colA.selectbox("Numeric column", options=num_cols, index=num_cols.index(default_num))
else:
    num_choice = None
    colA.info("No numeric columns detected.")

if cat_cols:
    # prefer store/country/channel if found
    pref = None
    for k in ["store", "country", "channel", "category", "team"]:
        if cuts.get(k) and cuts[k] in cat_cols:
            pref = cuts[k]
            break
    cat_choice = colB.selectbox("Categorical column", options=cat_cols, index=cat_cols.index(pref) if pref in cat_cols else 0)
else:
    cat_choice = None
    colB.info("No categorical columns detected.")

if num_choice:
    left, right = st.columns(2)

    # distribution
    fig1 = px.histogram(
        df.dropna(subset=[num_choice]),
        x=num_choice,
        nbins=20,
        template=PLOTLY_TEMPLATE,
        title=f"Distribution of {num_choice}",
        color_discrete_sequence=[PX_QUAL[0]],
    )
    fig1.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
    left.plotly_chart(fig1, use_container_width=True)

    if cat_choice:
        # top categories by sum of chosen numeric
        tmp = df[[cat_choice, num_choice]].replace([np.inf, -np.inf], np.nan).dropna()
        agg = tmp.groupby(cat_choice)[num_choice].sum().sort_values(ascending=False).head(12).reset_index()
        fig2 = px.bar(
            agg,
            x=cat_choice,
            y=num_choice,
            template=PLOTLY_TEMPLATE,
            title=f"{num_choice} by {cat_choice} (Top categories)",
            color=cat_choice,
            color_discrete_sequence=PX_QUAL,
            text=agg[num_choice].apply(fmt_num),
        )
        fig2.update_traces(textposition="inside")
        fig2.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
        right.plotly_chart(fig2, use_container_width=True)

st.divider()

# Key business cuts (auto) — remove "(auto)" wording
st.markdown("## Key business cuts")

# Use detected revenue if present; else fallback to best numeric
primary_metric = metrics.get("revenue") or default_numeric

if primary_metric is None:
    st.info("No numeric metric available to generate key business cut charts.")
else:
    # Show two bar charts: metric by store/channel/category/team (first two available)
    cut_candidates = []
    for k in ["store", "channel", "country", "category", "team"]:
        if cuts.get(k) and cuts[k] in df.columns:
            cut_candidates.append(cuts[k])

    # De-duplicate
    cut_candidates = list(dict.fromkeys([c for c in cut_candidates if c is not None]))

    left, right = st.columns(2)
    if len(cut_candidates) >= 1:
        cut1 = cut_candidates[0]
        tmp = df[[cut1, primary_metric]].replace([np.inf, -np.inf], np.nan).dropna()
        agg = tmp.groupby(cut1)[primary_metric].sum().sort_values(ascending=False).head(12).reset_index()
        fig = px.bar(
            agg,
            x=cut1,
            y=primary_metric,
            template=PLOTLY_TEMPLATE,
            title=f"{primary_metric} by {cut1}",
            color=cut1,
            color_discrete_sequence=PX_QUAL,
            text=agg[primary_metric].apply(fmt_num),
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(height=420, showlegend=False, margin=dict(l=10, r=10, t=60, b=10))
        left.plotly_chart(fig, use_container_width=True)
    else:
        left.info("No suitable cut column detected for a bar breakdown.")

    if len(cut_candidates) >= 2:
        cut2 = cut_candidates[1]
        tmp = df[[cut2, primary_metric]].replace([np.inf, -np.inf], np.nan).dropna()
        agg = tmp.groupby(cut2)[primary_metric].sum().sort_values(ascending=False).head(12).reset_index()
        fig = px.bar(
            agg,
            x=cut2,
            y=primary_metric,
            template=PLOTLY_TEMPLATE,
            title=f"{primary_metric} by {cut2}",
            color=cut2,
            color_discrete_sequence=PX_QUAL,
            text=agg[primary_metric].apply(fmt_num),
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(height=420, showlegend=False, margin=dict(l=10, r=10, t=60, b=10))
        right.plotly_chart(fig, use_container_width=True)
    else:
        right.info("Only one cut column detected for breakdown charts.")

st.divider()

# Trends — remove "(auto)" and handle no country by using best available cut
st.markdown("## Trends")

if date_col and primary_metric:
    # Total trend
    fig_total = trend_total(df, date_col, primary_metric)
    if fig_total:
        st.plotly_chart(fig_total, use_container_width=True)
    else:
        st.info("Not enough data to build a total trend chart.")

    # Breakdown trend:
    # if country not available, use store/channel/category/team in that order
    breakdown_col = None
    for k in ["country", "store", "channel", "category", "team"]:
        if cuts.get(k):
            breakdown_col = cuts[k]
            break

    if breakdown_col:
        # If breakdown has too many categories, use small multiples for top 5
        fig_sm = trend_breakdown_small_multiples(df, date_col, primary_metric, breakdown_col, top_n=5)
        if fig_sm:
            st.plotly_chart(fig_sm, use_container_width=True)
        else:
            st.info(f"Not enough data to build breakdown trends by {breakdown_col}.")
    else:
        st.info("No suitable categorical column detected for trend breakdown (store/channel/category/team).")
else:
    st.info("No date-like column detected (or no primary metric). Trend charts require a Date and a numeric metric.")

st.divider()

# Correlation + R² explanation (remove '(numeric)')
st.markdown("## Correlation & R²")

with st.expander("How to read correlation (r) and R²", expanded=False):
    st.write(
        """
**Correlation (r)** measures direction + linear association (-1 to +1).
- |r| < 0.2 → very weak
- 0.2–0.4 → weak
- 0.4–0.6 → moderate
- 0.6–0.8 → strong
- 0.8–1.0 → very strong

**R²** is the *explained variance* for a simple linear relationship (0 to 1).  
R² = r² (for two-variable linear correlation).
- < 0.04 → very weak
- 0.04–0.16 → weak
- 0.16–0.36 → moderate
- 0.36–0.64 → strong
- 0.64–1.0 → very strong

These are practical heuristics (good for storytelling), not universal truths. Always sanity-check with business logic.
"""
    )

if num_cols and len(num_cols) >= 2:
    # Wider heatmap (use container width) + keep readable
    fig_corr = corr_heatmap(df, num_cols[:12])  # cap at 12 to stay readable
    if fig_corr:
        st.plotly_chart(fig_corr, use_container_width=True)

    pairs = compute_r2_pairs(df, num_cols, top_k=6)
    if pairs:
        st.markdown("### Key R² relationships (top pairs)")
        for a, b, r, r2 in pairs[:4]:
            st.markdown(
                f"- **{a} ↔ {b}**: r={r:.2f} ({corr_strength_label(abs(r))}), R²={r2:.2f} ({r2_strength_label(r2)})"
            )
else:
    st.info("Need at least 2 numeric columns for correlation and R².")

st.divider()

# Suggested next analyses — remove "(Aligned)" (title only)
st.markdown("## Suggested next analyses")

# Generate automatically (no click) but cached in session to avoid repeated charges
if "ai_suggestions" not in st.session_state:
    st.session_state.ai_suggestions = None
if "ai_error" not in st.session_state:
    st.session_state.ai_error = None

# Auto-run once per dataset load (but don’t spam: store by file name/size)
dataset_key = f"{uploaded.name}-{getattr(uploaded, 'size', 'na')}-{df.shape[0]}-{df.shape[1]}"
if "last_dataset_key" not in st.session_state:
    st.session_state.last_dataset_key = None

if st.session_state.last_dataset_key != dataset_key:
    st.session_state.last_dataset_key = dataset_key
    st.session_state.ai_suggestions = None
    st.session_state.ai_error = None

pairs = compute_r2_pairs(df, num_cols, top_k=4) if len(num_cols) >= 2 else []
ai_block = ai_generate_summary_and_suggestions(df, metrics, cuts, date_col, pairs)
if "error" in ai_block:
    st.session_state.ai_error = ai_block["error"]
else:
    st.session_state.ai_suggestions = ai_block.get("parsed", None)

if st.session_state.ai_error:
    st.warning(f"AI suggestions unavailable: {st.session_state.ai_error}")
else:
    suggestions = st.session_state.ai_suggestions or []
    # Render in clean format
    for i, s in enumerate(suggestions[:3], start=1):
        st.markdown(f"### {i}. {s.get('title','Suggested analysis')}")
        # Keep the body but remove duplicated header lines if present
        body = s.get("body", "")
        body = re.sub(r"^\s*[1-3]\)\s*", "", body.strip())
        st.markdown(body)

st.divider()

# Run all 3 analyses (one click) + add commentary bullets
st.markdown("## Run recommended analyses")

run = st.button("Run all 3 analyses", type="primary")

if run:
    st.markdown("### 1) Revenue driver & relationship check")
    fig, notes = run_analysis_1_driver(df, metrics, cuts)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    for n in notes:
        st.markdown(f"- {n}")

    st.markdown("### 2) Variability by best cut")
    tbl, fig2, notes2, cut_name = run_analysis_2_variability(df, metrics, cuts)
    if tbl is not None:
        st.dataframe(tbl, use_container_width=True)
    if fig2:
        st.plotly_chart(fig2, use_container_width=True)
    for n in notes2:
        st.markdown(f"- {n}")

    st.markdown("### 3) Discount effectiveness (simple)")
    fig3, notes3 = run_analysis_3_discount(df, metrics, cuts)
    if fig3:
        st.plotly_chart(fig3, use_container_width=True)
    for n in notes3:
        st.markdown(f"- {n}")

st.divider()

# Export
st.markdown("## Export")
pdf_bytes = make_pdf_bytes("EC-AI Insight — Executive Brief", exec_summary[:10])
pptx_bytes = make_pptx_bytes("EC-AI Insight — Executive Brief", exec_summary[:10], insights[:10], st.session_state.ai_suggestions or [])

st.download_button("Download Executive Brief (PDF)", data=pdf_bytes, file_name="ecai_insight_executive_brief.pdf", mime="application/pdf")
st.download_button("Download Slides (PPTX)", data=pptx_bytes, file_name="ecai_insight_slides.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

st.caption("Note: This app is for demo/testing. Please avoid uploading confidential or regulated data.")
