# EC-AI Insight — Retail Sales MVP (Founder-first)

def clean_display_text(s: str) -> str:
    """Clean model/AI text for on-screen executive readability.

    Goal: remove markdown/math artifacts and drop any corrupted fragments.
    """
    if not s:
        return s

    raw = s.strip()
    low = raw.lower()

    # Drop known corrupted fragments (example: '(1.7K **persale).Deepdiscount **10-201.1K).')
    if "persale" in low or "deepdiscount" in low:
        return ""

    # Remove common markdown / code artifacts
    s = raw
    s = s.replace("**", "").replace("*", "")
    s = s.replace("`", "").replace("```", "")
    s = s.replace("_", "")

    # Remove LaTeX-ish inline math: \( ... \) or $...$
    s = re.sub(r"\\\((.*?)\\\)", "", s)
    s = re.sub(r"\$[^\$]*\$", "", s)

    # Remove unmatched parentheses/brackets leftovers and repeated punctuation
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"[\[\]{}<>]", "", s)
    s = re.sub(r"[\.]{2,}", ".", s)

    # If the line is mostly symbols/numbers after cleaning, drop it
    letters = sum(ch.isalpha() for ch in s)
    if letters < 4:
        return ""

    # Normalize whitespace
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s

import io
import os
import re
import textwrap
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

import plotly.graph_objects as go
import plotly.express as px

# Optional: Ask AI chat
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# -----------------------------
# Ask AI helpers (minimal, stable)
# -----------------------------
def _get_openai_api_key() -> str | None:
    try:
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY")




def get_api_key() -> str | None:
    """Backwards-compatible alias."""
    return _get_openai_api_key()

def _fmt_money(x: float) -> str:
    try:
        x = float(x)
    except Exception:
        return "N/A"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000_000:
        return f"{sign}${x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:.1f}K"
    return f"{sign}${x:,.0f}"


def _fmt_pct(x: float) -> str:
    try:
        return f"{float(x)*100:.1f}%"
    except Exception:
        return "N/A"


def _safe_div(a: float, b: float) -> float:
    try:
        a = float(a)
        b = float(b)
        return a / b if b not in (0, 0.0) else float("nan")
    except Exception:
        return float("nan")


def _build_ai_context(df: pd.DataFrame, m) -> str:
    # Be defensive: some earlier versions accidentally pass a non-dict mapping.
    if not isinstance(m, dict):
        m = {}
    """Build a compact, fact-heavy context block for Ask AI."""
    if df is None or df.empty:
        return "No dataset loaded."

    col_date = m.get("date")
    col_rev = m.get("revenue")
    col_store = m.get("store")
    col_cat = m.get("category")
    col_channel = m.get("channel")
    col_disc = m.get("discount")

    overview_lines = []
    n_rows = len(df)

    date_min = date_max = None
    n_days = None
    if col_date and col_date in df.columns:
        d = pd.to_datetime(df[col_date], errors="coerce")
        date_min = d.min()
        date_max = d.max()
        if pd.notna(date_min) and pd.notna(date_max):
            n_days = int((date_max - date_min).days) + 1

    total_rev = None
    if col_rev and col_rev in df.columns:
        total_rev = float(pd.to_numeric(df[col_rev], errors="coerce").fillna(0).sum())

    overview_lines.append(f"Rows: {n_rows}")
    if n_days is not None:
        overview_lines.append(f"Date range: {date_min.date()} to {date_max.date()} ({n_days} days)")
    else:
        overview_lines.append("Date range: N/A (missing/invalid date column)")
    overview_lines.append(f"Total revenue: {_fmt_money(total_rev) if total_rev is not None else 'N/A'}")

    def top_contrib(col_name: str, top_n: int = 5):
        if not (col_name and col_name in df.columns and col_rev and col_rev in df.columns):
            return None
        tmp = df[[col_name, col_rev]].copy()
        tmp[col_rev] = pd.to_numeric(tmp[col_rev], errors="coerce").fillna(0)
        g = tmp.groupby(col_name, dropna=False)[col_rev].sum().sort_values(ascending=False)
        g = g[g.index.notna()]
        top = g.head(top_n)
        if top.empty:
            return None
        tot = float(g.sum())
        out = []
        for i, (k, v) in enumerate(top.items(), start=1):
            out.append({"rank": i, "name": str(k), "revenue": float(v), "share": float(_safe_div(v, tot)) if tot else float("nan")})
        return {"total": tot, "top": out}

    top_stores = top_contrib(col_store, 5)
    top_cats = top_contrib(col_cat, 5)
    top_channels = top_contrib(col_channel, 5)

    momentum_lines = []
    if col_date and col_date in df.columns and col_rev and col_rev in df.columns:
        tmp = df[[col_date, col_rev]].copy()
        tmp[col_date] = pd.to_datetime(tmp[col_date], errors="coerce")
        tmp[col_rev] = pd.to_numeric(tmp[col_rev], errors="coerce").fillna(0)
        tmp = tmp.dropna(subset=[col_date])
        daily = tmp.groupby(col_date, as_index=False)[col_rev].sum().sort_values(col_date)
        if len(daily) >= 10:
            mid = len(daily) // 2
            first = float(daily.iloc[:mid][col_rev].sum())
            second = float(daily.iloc[mid:][col_rev].sum())
            delta = second - first
            momentum_lines.append(f"First half revenue: {_fmt_money(first)}")
            momentum_lines.append(f"Second half revenue: {_fmt_money(second)} (Δ {_fmt_money(delta)})")
            if len(daily) >= 28:
                last14 = float(daily.iloc[-14:][col_rev].sum())
                prev14 = float(daily.iloc[-28:-14][col_rev].sum())
                mom14 = last14 - prev14
                momentum_lines.append(f"Last 14 days: {_fmt_money(last14)} vs prior 14: {_fmt_money(prev14)} (Δ {_fmt_money(mom14)})")
            peak_row = daily.loc[daily[col_rev].idxmax()]
            trough_row = daily.loc[daily[col_rev].idxmin()]
            momentum_lines.append(f"Peak day: {pd.to_datetime(peak_row[col_date]).date()} at {_fmt_money(peak_row[col_rev])}")
            momentum_lines.append(f"Lowest day: {pd.to_datetime(trough_row[col_date]).date()} at {_fmt_money(trough_row[col_rev])}")
        else:
            momentum_lines.append("Not enough daily points to compute momentum (need ~10+ days).")
    else:
        momentum_lines.append("Trend metrics unavailable (need date + revenue columns).")

    discount_lines = []
    if col_disc and col_disc in df.columns and col_rev and col_rev in df.columns:
        tmp = df[[col_disc, col_rev]].copy()
        tmp[col_rev] = pd.to_numeric(tmp[col_rev], errors="coerce").fillna(0)
        if pd.api.types.is_numeric_dtype(tmp[col_disc]) or pd.to_numeric(tmp[col_disc], errors="coerce").notna().mean() > 0.8:
            disc_num = pd.to_numeric(tmp[col_disc], errors="coerce")
            bins = [-float("inf"), 0.02, 0.05, 0.10, 0.20, float("inf")]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["discount_band"] = pd.cut(disc_num, bins=bins, labels=labels)
            band = "discount_band"
        else:
            band = col_disc
        g = tmp.groupby(band)[col_rev].agg(["mean", "count"]).reset_index()
        g = g.dropna(subset=[band]).sort_values("mean", ascending=False)
        if not g.empty:
            for _, r in g.head(5).iterrows():
                discount_lines.append(f"{r[band]}: avg {_fmt_money(r['mean'])} (n={int(r['count'])})")
    else:
        discount_lines.append("Discount metrics unavailable (need discount + revenue columns).")

    def format_top(title: str, obj):
        if not obj:
            return f"{title}: N/A"
        lines = [f"{title} (by revenue):"]
        for it in obj["top"]:
            lines.append(f"- {it['rank']}. {it['name']}: {_fmt_money(it['revenue'])} ({_fmt_pct(it['share'])})")
        if len(obj["top"]) >= 2 and obj["total"]:
            top1 = obj["top"][0]["revenue"]
            top2 = obj["top"][1]["revenue"]
            lines.append(f"Concentration: Top1 {_fmt_pct(_safe_div(top1, obj['total']))}, Top2 {_fmt_pct(_safe_div(top1+top2, obj['total']))}")
        return "\n".join(lines)

    context = f"""You are EC-AI Insight. Answer strictly using the dataset facts below.
Rules:
- ALWAYS reference actual numbers from this context (use $ amounts, dates, % shares).
- Do NOT invent metrics or give generic advice.
- If something is not in context, say 'Not available in this dataset/context' and specify what column/metric would be needed.

DATASET FACTS
{chr(10).join(overview_lines)}

{format_top('Top Stores', top_stores)}

{format_top('Top Categories', top_cats)}

{format_top('Top Channels', top_channels)}

Trend / Momentum:
{chr(10).join('- ' + s for s in momentum_lines)}

Discount effectiveness (avg revenue per sale, best bands first):
{chr(10).join('- ' + s for s in discount_lines)}

Available columns: {', '.join(map(str, df.columns))}
"""
    return context

def answer_question_with_openai(question: str, context: str) -> str:
    """Ask AI using a fact-heavy context block. Always grounded."""
    api_key = get_api_key()
    if not api_key:
        return "OpenAI API key not configured. Add OPENAI_API_KEY in Streamlit secrets."

    if OpenAI is None:
        return "OpenAI SDK not installed. Add 'openai' to requirements.txt."

    q = (question or "").strip()
    if not q:
        return "Please enter a question."

    try:
        client = OpenAI(api_key=api_key)
        system = (context or "").strip()
        user = f"""Question:
{q}

Instructions:
- Answer using ONLY the dataset facts in the system context.
- Always cite numbers ($, %, dates) from the context when relevant.
- If the context lacks required info, say what is missing (which column/metric)."""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=380,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        response_text = (resp.choices[0].message.content or "").strip()
        return response_text or "No response."
    except Exception as e:
        return f"Ask AI error: {e}"


def format_ai_answer(answer: str) -> str:
    """Lightly structure Ask AI output for executive readability."""
    txt = (answer or "").strip()
    if not txt:
        return "No response."

    # Preserve explicit errors / config messages
    low = txt.lower()
    if low.startswith("openai api key") or low.startswith("openai sdk") or low.startswith("ask ai error"):
        return txt

    # Split into non-empty lines / bullets
    raw_lines = []
    for part in txt.replace("\r", "\n").split("\n"):
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"^[\-•\*\d\.)\s]+", "", part).strip()
        if part:
            raw_lines.append(part)

    if not raw_lines:
        return txt

    # If already clearly structured, keep it
    headings = ("answer:", "what happened", "why it matters", "recommended action", "next step", "so what")
    if any(line.lower().startswith(headings) for line in raw_lines[:4]):
        return "\n\n".join(raw_lines)

    answer_line = raw_lines[0]
    support = raw_lines[1:3]
    action = raw_lines[3:5] if len(raw_lines) > 3 else []

    blocks = [f"**Answer**\n{answer_line}"]
    if support:
        blocks.append("**Why this matters**\n" + "\n".join(f"- {x}" for x in support))
    if action:
        blocks.append("**Recommended action**\n" + "\n".join(f"- {x}" for x in action))
    return "\n\n".join(blocks)


# Export deps (optional at runtime)
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_LEFT


# -----------------------------
# Executive emphasis helper (HTML bold for reliable rendering)
# -----------------------------
def emphasize_exec_keywords_html(text: str) -> str:
    """
    Bold key executive signals using HTML <b> so emphasis always appears:
    - Money amounts ($)
    - Percentages (%)
    - Rankings (#1, Top 2)
    - Store/location codes (HK-, SG-, JP-, CN-)
    """
    if not text:
        return text or ""

    # Money
    text = re.sub(r"(\$[0-9,.]+[KMB]?)", r"<b>\1</b>", text)

    # Percentages
    text = re.sub(r"(\d+\.?\d*%)", r"<b>\1</b>", text)

    # Rankings
    text = re.sub(r"(#\d+|top \d+)", r"<b>\1</b>", text, flags=re.I)

    # Store / location codes
    text = re.sub(r"((HK|SG|JP|CN)-[A-Za-z0-9]+)", r"<b>\1</b>", text)

    # Lead-ins
    text = re.sub(r"^(Takeaway:)", r"<b>\1</b>", text)
    text = re.sub(r"^(Next focus:)", r"<b>\1</b>", text)

    return text


# -----------------------------
# Page config + global styling
# -----------------------------

# =========================
# Demo Dataset (Retail Fashion - Hong Kong, 8 weeks, HKD)
# =========================
def load_demo_dataset_fashion_hk(num_weeks: int = 8, seed: int = 42) -> pd.DataFrame:
    """Generate a realistic-looking retail fashion transaction dataset for demo.
    - Hong Kong market
    - 8 weeks by default
    - Includes Cost for margin analysis
    """
    rng = np.random.default_rng(seed)

    stores = [
        "Central", "Causeway Bay", "Tsim Sha Tsui", "Mong Kok",
        "Sha Tin", "Tsuen Wan", "Kowloon Bay", "Yuen Long"
    ]
    categories = ["Tops", "Bottoms", "Dresses", "Outerwear", "Accessories", "Shoes", "Activewear"]
    products_by_cat = {
        "Tops": ["Cotton T-Shirt", "Casual Shirt", "Polo Shirt", "Knit Sweater"],
        "Bottoms": ["Slim Fit Jeans", "Chino Pants", "Pleated Skirt", "Denim Shorts"],
        "Dresses": ["Summer Dress", "Wrap Dress", "Midi Dress"],
        "Outerwear": ["Denim Jacket", "Bomber Jacket", "Lightweight Coat", "Hoodie"],
        "Accessories": ["Leather Belt", "Canvas Tote", "Cap", "Sunglasses"],
        "Shoes": ["Running Shoes", "Sneakers", "Loafers"],
        "Activewear": ["Yoga Pants", "Sports Bra", "Training Tee"]
    }

    # Date range: last (num_weeks * 7) days, inclusive
    days = num_weeks * 7
    end_date = pd.Timestamp.today().normalize()
    dates = pd.date_range(end=end_date, periods=days, freq="D")

    rows = []
    # Demand seasonality: weekends slightly higher
    for d in dates:
        weekday = d.dayofweek  # Mon=0 ... Sun=6
        day_multiplier = 1.15 if weekday >= 5 else 1.0

        for store in stores:
            # Store traffic variance
            store_multiplier = 1.0 + (stores.index(store) - 3.5) * 0.02  # mild gradient
            # transactions per store per day
            n_txn = int(rng.integers(18, 32) * day_multiplier * store_multiplier)

            for _ in range(max(5, n_txn)):
                category = rng.choice(categories, p=[0.18, 0.16, 0.12, 0.13, 0.14, 0.14, 0.13])
                product = rng.choice(products_by_cat[category])

                # Units sold per transaction
                units = int(rng.integers(1, 5))

                # Price bands by category (HKD)
                if category in ["Outerwear", "Shoes"]:
                    price = float(rng.uniform(380, 980))
                elif category in ["Dresses"]:
                    price = float(rng.uniform(280, 720))
                elif category in ["Activewear"]:
                    price = float(rng.uniform(220, 650))
                elif category in ["Bottoms"]:
                    price = float(rng.uniform(260, 780))
                elif category in ["Accessories"]:
                    price = float(rng.uniform(120, 520))
                else:  # Tops
                    price = float(rng.uniform(160, 520))

                revenue = units * price

                # Cost ratio varies by category: accessories often higher margin
                if category in ["Accessories"]:
                    cost_ratio = float(rng.uniform(0.35, 0.55))
                elif category in ["Outerwear", "Shoes"]:
                    cost_ratio = float(rng.uniform(0.45, 0.68))
                else:
                    cost_ratio = float(rng.uniform(0.42, 0.65))

                cost = revenue * cost_ratio

                rows.append({
                    "Date": d,
                    "Store": store,
                    "Category": category,
                    "Product": product,
                    "Units": units,
                    "Revenue": round(revenue, 2),
                    "Cost": round(cost, 2),
                })

    df = pd.DataFrame(rows)
    return df


st.set_page_config(page_title="EC-AI Insight", layout="wide")

# Slightly larger, more executive typography.
st.markdown(
    """
<style>
/* Base */
html, body, [class*="css"]  { font-size: 16px; }
p, li { font-size: 16px; line-height: 1.55; }
small, .stCaption { font-size: 14px; }

/* Titles */
h1 { font-size: 40px !important; margin-bottom: 0.25rem; }
h2 { font-size: 26px !important; margin-top: 1.2rem; }
h3 { font-size: 20px !important; margin-top: 1.0rem; }
h4 { font-size: 18px !important; margin-top: 0.9rem; }

/* Extra spacing between subheaders + paragraphs */
.ec-space { margin-top: 10px; margin-bottom: 10px; }
.ec-tight { margin-top: 2px; margin-bottom: 2px; }
.ec-note { color: #555; font-size: 15px; }
.ec-kicker { color: #555; font-size: 18px; }
.ec-subtle { color: #666; font-size: 15px; }

/* Make expanders less cramped */
div[data-testid="stExpander"] > details { padding: 0.25rem 0.25rem 0.5rem 0.25rem; }
</style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Palette (Tableau-like)
# -----------------------------
TABLEAU10 = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"
]




# Consultancy palette (McKinsey-style: neutral base + restrained accents)
CONSULTING_PALETTE = [
    "#0B1F3B",  # deep navy (primary)
    "#2A6F97",  # blue (secondary)
    "#2F855A",  # green
    "#B7791F",  # amber
    "#9B2C2C",  # red
    "#4A5568",  # slate
    "#718096",  # gray
    "#A0AEC0",  # light gray
]

# -----------------------------
# Consultancy-grade Plotly theme (applies to all charts)
# -----------------------------
def apply_consulting_theme(
    fig: go.Figure,
    *,
    title: str | None = None,
    height: int | None = None,
    y_is_currency: bool = False,
    y_is_pct: bool = False,
) -> go.Figure:
    """Make charts look like a clean executive deck (stable, consistent)."""
    if title is not None:
        fig.update_layout(title=dict(text=title, x=0.0, xanchor="left"))

    fig.update_layout(
        template="plotly_white",
        height=height or fig.layout.height or 380,
        margin=dict(l=48, r=26, t=62, b=52),
        font=dict(family="Inter, Arial, sans-serif", size=13, color="#111827"),
        title=dict(font=dict(size=18, color="#111827")),
        paper_bgcolor="white",
        plot_bgcolor="white",
        colorway=CONSULTING_PALETTE,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12, color="#374151"),
        ),
    )

    fig.update_xaxes(
        title=None,
        showline=True,
        linewidth=1,
        linecolor="#374151",
        ticks="outside",
        tickfont=dict(size=12, color="#374151"),
        gridcolor="rgba(17,24,39,0.07)",
                    )
    fig.update_yaxes(
        title=None,
        showline=True,
        linewidth=1,
        linecolor="#374151",
        ticks="outside",
        tickfont=dict(family="Inter SemiBold, Inter, Arial, sans-serif", size=12, color="#374151"),
        gridcolor="rgba(17,24,39,0.07)",
                    )

    if y_is_currency:
        # $1.2M style ticks
        fig.update_yaxes(tickprefix="$", tickformat=",.2s")
    elif y_is_pct:
        fig.update_yaxes(tickformat=".0%")

    # Cleaner hover
    fig.update_traces(hoverlabel=dict(font_size=12), hovertemplate=None)

    return fig




# -----------------------------
# Executive Dashboard (6‑grid)
# -----------------------------
ONEPAGER_CSS = """
<style>
.ec-onepager-title{margin: 6px 0 10px 0; font-weight: 900; font-size: 18px; color:#111827;}
.ec-tile{
  border: 1px solid rgba(17,24,39,0.10);
  border-radius: 14px;
  padding: 12px 12px 10px 12px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(17,24,39,0.04);
  margin-bottom: 14px;
}
.ec-tile h4{margin:0 0 6px 0; font-size: 13px; font-weight: 900; color:#111827;}
.ec-tile .note{margin-top: 6px; font-size: 12px; color:#374151; line-height: 1.25;}
.ec-tile .note b{color:#111827;}
</style>
"""



DASH_NOTE_STYLE = "border:1px dashed rgba(17,24,39,0.25); border-radius:12px; padding:10px 12px; background:#ffffff; font-size:12px; color:#374151; line-height:1.35;"


def _dash_note(md: str) -> None:
    # md is simple markdown; convert **bold** to <b> for reliable rendering inside HTML
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md)
    st.markdown(f"<div style='{DASH_NOTE_STYLE}'>{html}</div>", unsafe_allow_html=True)

def render_onepager_dashboard(m, df) -> dict:
    st.markdown(ONEPAGER_CSS, unsafe_allow_html=True)
    st.markdown("<div class='ec-onepager-title'>Executive Dashboard</div>", unsafe_allow_html=True)

    # Build figures (unwrap tuples if returned)
    def _as_fig(obj):
        return obj[0] if isinstance(obj, tuple) and len(obj) else obj

    fig_trend = _as_fig(line_trend(df, m.col_date, m.col_revenue, "Revenue Trend (Daily)"))
    fig_trend = apply_consulting_theme(fig_trend, title="Revenue Trend (Daily)", height=320, y_is_currency=True)

    fig_topstores, df_top = top5_stores_bar(m)
    fig_topstores = apply_consulting_theme(fig_topstores, title="Top Stores (Top 5)", height=320, y_is_currency=True)
    top_store = df_top.iloc[0]["Store"] if len(df_top) else "Top store"

    fig_cat = _as_fig(revenue_by_category(m))
    fig_cat = apply_consulting_theme(fig_cat, title="Revenue by Category (Top 5)", height=320, y_is_currency=True)

    fig_price = _as_fig(pricing_effectiveness(m))
    fig_price = apply_consulting_theme(fig_price, title="Pricing Effectiveness", height=320, y_is_currency=True)

    fig_channel = _as_fig(revenue_by_channel(m))
    fig_channel = apply_consulting_theme(fig_channel, title="Revenue by Channel (Top 3)", height=320, y_is_currency=True)

    fig_vol = _as_fig(volatility_by_channel(m))
    fig_vol = apply_consulting_theme(fig_vol, title="Volatility by Channel", height=320, y_is_currency=False)

    r1 = st.columns(3, gap='small')
    with r1[0]:
        with st.container(border=True):
            st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
            _dash_note("Protect **momentum**; investigate spikes and dips.")
    with r1[1]:
        with st.container(border=True):
            st.plotly_chart(fig_topstores, use_container_width=True, config={"displayModeBar": False})
            _dash_note(f"Revenue is concentrated — prioritise **{top_store}** and top drivers.")
    with r1[2]:
        with st.container(border=True):
            st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})
            _dash_note("Double down on **top categories**; fix weak lines.")

    r2 = st.columns(3, gap='small')
    with r2[0]:
        with st.container(border=True):
            st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})
            _dash_note("Use **pricing discipline**; moderate discounts can outperform aggressive ones.")
    with r2[1]:
        with st.container(border=True):
            st.plotly_chart(fig_channel, use_container_width=True, config={"displayModeBar": False})
            _dash_note("Reallocate effort to channels that **convert**; fix weakest channel.")
    with r2[2]:
        with st.container(border=True):
            st.plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})
            _dash_note("Reduce volatility: stabilise operations where swings are highest.")

    figs_dict = {
        "Revenue Trend (Daily)": fig_trend,
        "Top Stores (Top 5)": fig_topstores,
        "Revenue by Category (Top 5)": fig_cat,
        "Pricing Effectiveness": fig_price,
        "Revenue by Channel (Top 3)": fig_channel,
        "Volatility by Channel": fig_vol,
    }

    st.markdown("---")
    return figs_dict

def plot_half_width(fig: go.Figure, *, config: dict | None = None) -> None:
    """Left-aligned half-width chart (consultant deck proportion)."""
    col1, col2 = st.columns([0.55, 0.45])
    with col1:
        if config is None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.plotly_chart(fig, use_container_width=True, config=config)



# -----------------------------
# Layout helpers
# -----------------------------





def line_trend(df: pd.DataFrame, date_col: str, value_col: str, title: str) -> go.Figure:
    """Executive-grade daily trend line for a single metric (defaults to currency)."""
    daily = df.groupby(pd.Grouper(key=date_col, freq="D"))[value_col].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily[date_col],
            y=daily[value_col],
            mode="lines",
            line=dict(width=3),
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2s}<extra></extra>",
        )
    )
    fig = apply_consulting_theme(fig, title=title, height=360, y_is_currency=True)
    fig.update_xaxes(showgrid=False, tickformat="%b %d")
    return fig


def safe_money(x: float) -> str:
    """Friendly money formatting without 'machine noise'."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    x = float(x)
    ax = abs(x)
    if ax >= 1_000_000_000:
        return f"${x/1_000_000_000:.2f}B"
    if ax >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    if ax >= 1_000:
        return f"${x/1_000:.1f}K"
    return f"${x:,.0f}"

def safe_pct(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x*100:.0f}%"

def clean_col(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

# -----------------------------
# Column detection
# -----------------------------
CANDIDATES = {
    "date": ["date", "orderdate", "transactiondate", "salesdate", "invoice_date", "day"],
    "store": ["store", "store_name", "shop", "branch", "location", "outlet"],
    "revenue": ["revenue", "sales", "amount", "net_sales", "total", "total_sales", "gmv"],
    "cost": ["cost", "cogs", "cost_of_goods", "costofgoods", "item_cost", "unit_cost"],
    "category": ["category", "product_category", "dept", "department", "cat"],
    "product": ["product", "product_name", "item", "item_name", "sku", "style"],
    "channel": ["channel", "sales_channel", "platform", "source"],
    "payment": ["payment", "payment_method", "tender", "paymethod"],
    "discount": ["discount", "discount_rate", "disc", "discount_pct", "promo_discount"],
    "qty": ["qty", "quantity", "units", "unit_sold", "items"]
}

def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols = list(df.columns)
    norm = {clean_col(c): c for c in cols}
    out: Dict[str, Optional[str]] = {k: None for k in CANDIDATES.keys()}
    for key, cands in CANDIDATES.items():
        for cand in cands:
            cand_norm = clean_col(cand)
            # exact or substring
            for n, orig in norm.items():
                if n == cand_norm or cand_norm in n:
                    out[key] = orig
                    break
            if out[key] is not None:
                break
    # Fallback for revenue: choose first numeric col if none found
    if out["revenue"] is None:
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            out["revenue"] = num_cols[0]
    return out

# -----------------------------
# Data prep
# -----------------------------


# -----------------------------
# Formatting helpers
# -----------------------------
CURRENCY_SYMBOL = "HK$"

def fmt_currency(x: float) -> str:
    """Short currency format: HK$1.50M / HK$86.4K / HK$950."""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        x = float(x)
    except Exception:
        return "—"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000_000:
        return f"{sign}{CURRENCY_SYMBOL}{x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"{sign}{CURRENCY_SYMBOL}{x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{sign}{CURRENCY_SYMBOL}{x/1_000:.1f}K"
    return f"{sign}{CURRENCY_SYMBOL}{x:.0f}"

def fmt_pct(x: float, digits: int = 0) -> str:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        return f"{x*100:.{digits}f}%"
    except Exception:
        return "—"


def md_to_plain(s: str) -> str:
    """Remove simple Markdown markers for clean exports (PDF/PPT)."""
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    # Leave single * alone unless it's paired (avoid nuking multiplication signs in data)
    s = s.replace("**", "")
    return s

def md_to_plain_lines(s: str) -> List[str]:
    """Split into lines and clean markdown per-line, keeping newlines."""
    if s is None:
        return []
    lines = str(s).split("\n")
    out = []
    for line in lines:
        line = md_to_plain(line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            out.append(line)
    return out

@dataclass
class RetailModel:
    df: pd.DataFrame
    col_date: str
    col_store: str
    col_revenue: str
    col_cost: Optional[str] = None
    col_category: Optional[str] = None
    col_product: Optional[str] = None
    col_channel: Optional[str] = None
    col_payment: Optional[str] = None
    col_discount: Optional[str] = None
    col_qty: Optional[str] = None

def prep_retail(df_raw: pd.DataFrame) -> RetailModel:
    df = df_raw.copy()

    cols = detect_columns(df)
    # Minimal requirements
    if cols["date"] is None:
        # try parse index as date?
        raise ValueError("Could not detect a Date column. Please ensure your file includes a date field (e.g., Date, OrderDate).")
    if cols["revenue"] is None:
        raise ValueError("Could not detect a Revenue/Sales column. Please ensure your file includes a numeric revenue field (e.g., Revenue, Sales, Amount).")

    col_date = cols["date"]
    col_store = cols["store"] or "__store__"
    col_revenue = cols["revenue"]

    # Create a default store if missing
    if cols["store"] is None:
        df[col_store] = "All Stores"

    # Parse dates
    df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
    df = df.dropna(subset=[col_date])

    # Revenue numeric
    df[col_revenue] = pd.to_numeric(df[col_revenue], errors="coerce")
    df = df.dropna(subset=[col_revenue])

    # Optional numeric
    col_qty = cols["qty"]
    if col_qty is not None:
        df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce")

    # Discount normalize: accept 0-1 or 0-100
    col_discount = cols["discount"]
    if col_discount is not None:
        df[col_discount] = pd.to_numeric(df[col_discount], errors="coerce")
        # If looks like percent 0-100
        s = df[col_discount].dropna()
        if len(s) > 0 and s.quantile(0.95) > 1.5:
            df[col_discount] = df[col_discount] / 100.0
        df[col_discount] = df[col_discount].clip(lower=0, upper=1)

    # Trim string columns
    for k in ["store", "category", "channel", "payment"]:
        c = cols.get(k)
        if c is not None:
            df[c] = df[c].astype(str).str.strip()

    # Keep only useful columns
    return RetailModel(
        df=df,
        col_date=col_date,
        col_store=col_store,
        col_revenue=col_revenue,
        col_cost=cols["cost"],
        col_category=cols["category"],
        col_product=cols["product"],
        col_channel=cols["channel"],
        col_payment=cols["payment"],
        col_discount=col_discount,
        col_qty=col_qty,
    )

# -----------------------------
# Insight helpers (human tone)
# -----------------------------
def build_business_summary_points(m: RetailModel) -> List[str]:
    """Founder-facing summary: concrete, human, and includes examples."""
    df = m.df
    dmin, dmax = df[m.col_date].min(), df[m.col_date].max()
    days = max((dmax - dmin).days + 1, 1)

    total_rev = float(df[m.col_revenue].sum())
    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)
    cat_rev = df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False) if m.col_category else pd.Series(dtype=float)

    top_store = str(store_rev.index[0]) if len(store_rev) else "—"
    top_store_rev = float(store_rev.iloc[0]) if len(store_rev) else np.nan
    top_store_share = (top_store_rev / total_rev) if total_rev > 0 and len(store_rev) else np.nan

    top2_rev = float(store_rev.iloc[:2].sum()) if len(store_rev) >= 2 else np.nan
    top2_share = (top2_rev / total_rev) if total_rev > 0 and len(store_rev) >= 2 else np.nan

    top_cat = str(cat_rev.index[0]) if len(cat_rev) else None
    top_cat_rev = float(cat_rev.iloc[0]) if len(cat_rev) else np.nan
    top_cat_share = (top_cat_rev / total_rev) if total_rev > 0 and len(cat_rev) else np.nan

    # Trend: first half vs second half
    df_sorted = df.sort_values(m.col_date)
    mid = df_sorted[m.col_date].min() + pd.Timedelta(days=days / 2)
    rev_first = float(df_sorted.loc[df_sorted[m.col_date] <= mid, m.col_revenue].sum())
    rev_second = float(df_sorted.loc[df_sorted[m.col_date] > mid, m.col_revenue].sum())
    growth = (rev_second - rev_first) / rev_first if rev_first > 0 else np.nan

    # Volatility proxy: daily revenue std / mean by store
    daily = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol = daily.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol["ratio"] = vol["std"] / vol["mean"]
    most_volatile_store = str(vol["ratio"].sort_values(ascending=False).index[0]) if len(vol) else None
    most_volatile_score = float(vol.loc[most_volatile_store, "ratio"]) if most_volatile_store in vol.index else np.nan

    # Discount effectiveness
    best_band = worst_band = None
    best_avg = worst_avg = np.nan
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 20:
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            agg = tmp.groupby("disc_band")[m.col_revenue].mean()
            if agg.notna().sum() >= 2:
                best_band = str(agg.sort_values(ascending=False).index[0])
                best_avg = float(agg.loc[best_band])
                worst_band = str(agg.sort_values(ascending=True).index[0])
                worst_avg = float(agg.loc[worst_band])

    points: List[str] = []

    # 1) Big picture
    points.append(f"You have **{days} days** of data with **{len(df):,} transactions** (total revenue **{fmt_currency(total_rev)}**).")

    # 2) Concentration
    if not np.isnan(top_store_share):
        points.append(f"Revenue is concentrated: **{top_store}** contributes **{fmt_currency(top_store_rev)}** (about **{fmt_pct(top_store_share, 0)}** of total).")

    if not np.isnan(top2_share):
        points.append(f"The **top 2 stores** together generate **{fmt_currency(top2_rev)}** (about **{fmt_pct(top2_share, 0)}**). Small wins in these locations move the whole business.")

    # 3) Category mix
    if top_cat is not None and not np.isnan(top_cat_share):
        points.append(f"By category, **{top_cat}** is your largest driver: **{fmt_currency(top_cat_rev)}** (about **{fmt_pct(top_cat_share, 0)}**).")

    # 4) Momentum
    if not np.isnan(growth):
        if growth > 0.03:
            points.append(f"Momentum is positive: the second half of the period delivered about **{fmt_pct(growth, 0)}** more revenue than the first half.")
        elif growth < -0.03:
            points.append(f"Momentum is softer: the second half of the period delivered about **{fmt_pct(growth, 0)}** less revenue than the first half.")
        else:
            points.append("Overall revenue looks broadly stable across the period (no major shift between first vs second half).")

    # 5) Stability / predictability
    if most_volatile_store is not None and not np.isnan(most_volatile_score):
        points.append(f"Day-to-day sales are not equally predictable. **{most_volatile_store}** shows the biggest swings (variability score ≈ **{most_volatile_score:.2f}**).")

    # 6) Discount discipline
    if best_band is not None and worst_band is not None:
        points.append(f"Discounting: **{best_band}** performs best on average (**{fmt_currency(best_avg)}** per sale). Deep discount **{worst_band}** underperforms (**{fmt_currency(worst_avg)}**).")
        points.append("Takeaway: moderate discounts tend to work better than aggressive ones — bigger discounts do not automatically lead to better results.")

    # 7) Next focus
    points.append("Next focus: protect and improve the top stores first (availability, staffing, promotion discipline), then scale what works.")

    # Keep it tight
    return points[:12]




def build_business_insights_sections(m: RetailModel) -> Dict[str, List[str]]:
    """Business Insights with concrete examples (names + numbers)."""
    df = m.df
    total_rev = float(df[m.col_revenue].sum())

    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)
    top_store = str(store_rev.index[0]) if len(store_rev) else "—"
    top_store_rev = float(store_rev.iloc[0]) if len(store_rev) else np.nan

    top2 = store_rev.head(2)
    top2_share = float(top2.sum() / total_rev) if total_rev > 0 and len(top2) else np.nan

    # Category / channel drivers
    cat_rev = df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False) if m.col_category else pd.Series(dtype=float)
    top_cat = str(cat_rev.index[0]) if len(cat_rev) else None
    top_cat_rev = float(cat_rev.iloc[0]) if len(cat_rev) else np.nan

    channel_rev = df.groupby(m.col_channel)[m.col_revenue].sum().sort_values(ascending=False) if m.col_channel else pd.Series(dtype=float)
    top_channel = str(channel_rev.index[0]) if len(channel_rev) else None
    top_channel_rev = float(channel_rev.iloc[0]) if len(channel_rev) else np.nan

    # Stability: daily CV per store + per channel
    daily_store = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol_store = daily_store.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol_store["cv"] = vol_store["std"] / vol_store["mean"]
    vol_store = vol_store.dropna(subset=["cv"]).sort_values("cv", ascending=False)
    most_volatile_store = str(vol_store.index[0]) if len(vol_store) else None
    most_volatile_cv = float(vol_store.iloc[0]["cv"]) if len(vol_store) else np.nan

    daily_chan = None
    most_volatile_chan = None
    most_volatile_chan_cv = np.nan
    if m.col_channel:
        daily_chan = df.groupby([m.col_channel, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
        vol_chan = daily_chan.groupby(m.col_channel)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
        vol_chan["cv"] = vol_chan["std"] / vol_chan["mean"]
        vol_chan = vol_chan.dropna(subset=["cv"]).sort_values("cv", ascending=False)
        most_volatile_chan = str(vol_chan.index[0]) if len(vol_chan) else None
        most_volatile_chan_cv = float(vol_chan.iloc[0]["cv"]) if len(vol_chan) else np.nan

    # Pricing: best discount band
    best_band = worst_band = None
    best_avg = worst_avg = np.nan
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 20:
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            agg = tmp.groupby("disc_band")[m.col_revenue].mean()
            if agg.notna().sum() >= 2:
                best_band = str(agg.sort_values(ascending=False).index[0])
                best_avg = float(agg.loc[best_band])
                worst_band = str(agg.sort_values(ascending=True).index[0])
                worst_avg = float(agg.loc[worst_band])

    sections: Dict[str, List[str]] = {}

    # Where money is made
    money_bullets = []
    money_bullets.append(
        f"Revenue is driven by a small number of key stores — **{top_store}** is #1 with **{fmt_currency(top_store_rev)}**."
    )
    if not np.isnan(top2_share):
        money_bullets.append(
            f"The **top 2 stores** contribute about **{fmt_pct(top2_share, 0)}** of total revenue. Improvements here have the biggest impact."
        )
    if top_cat is not None:
        money_bullets.append(
            f"Top category: **{top_cat}** contributes **{fmt_currency(top_cat_rev)}**."
        )
    if top_channel is not None:
        money_bullets.append(
            f"Top channel: **{top_channel}** contributes **{fmt_currency(top_channel_rev)}**."
        )
    sections["Where the money is made"] = money_bullets

    # Where risk exists
    risk_bullets = []
    if most_volatile_store is not None:
        risk_bullets.append(
            f"Predictability risk: **{most_volatile_store}** has the most uneven day-to-day sales (variability score ≈ **{most_volatile_cv:.2f}**)."
        )
    if most_volatile_chan is not None:
        risk_bullets.append(
            f"Channel stability matters too — **{most_volatile_chan}** is the most volatile channel (variability score ≈ **{most_volatile_chan_cv:.2f}**)."
        )
    risk_bullets.append(
        "Concentration risk: when most revenue comes from a few stores, execution slips in those locations hit the whole business."
    )
    sections["Where risk exists"] = risk_bullets

    # What can be improved
    improve_bullets = []
    if best_band is not None and worst_band is not None:
        improve_bullets.append(
            f"Discount discipline: **{best_band}** delivers the best average revenue per sale (**{fmt_currency(best_avg)}**). Deep discount **{worst_band}** underperforms (**{fmt_currency(worst_avg)}**)."
        )
        improve_bullets.append(
            "Takeaway: moderate discounts tend to perform better than aggressive ones — bigger discounts do not automatically lead to better results."
        )
    else:
        improve_bullets.append("Discounting works best when treated as an experiment (clear target + measure the lift), not a default habit.")
    improve_bullets.append("In top stores, focus on fundamentals first: inventory, staffing, and promotion discipline.")
    sections["What can be improved"] = improve_bullets

    # What to focus on next
    next_bullets = []
    next_bullets.append(f"Run a simple playbook on the top stores (starting with **{top_store}**) and scale what works.")
    next_bullets.append("Fix volatility before chasing growth — stability usually comes from operations, not more campaigns.")
    sections["What to focus on next"] = next_bullets

    return sections

def render_parallel_insight_cards(ins_sections: Dict[str, List[str]]) -> None:
    """Render first 3 business insight sections as parallel cards for a premium SaaS feel."""
    items = list(ins_sections.items())
    if not items:
        return

    icon_map = {
        "Where the money is": "◎",
        "What looks risky": "◌",
        "How to improve": "◍",
        "What to focus on next": "◉",
    }

    st.markdown("### AI-Generated Key Insights")
    st.caption("Automatically detected from your dataset")

    primary = items[0] if len(items) > 0 else None
    secondary = items[1] if len(items) > 1 else None
    tertiary = items[2] if len(items) > 2 else None
    remaining = items[3:] if len(items) > 3 else []

    def _card_title(title: str) -> str:
        icon = icon_map.get(title, "◦")
        return f"{icon} {title}"

    # Three-card row
    top_cols = st.columns(3, gap="small")
    for idx, item in enumerate([primary, secondary, tertiary]):
        with top_cols[idx]:
            if item is None:
                st.empty()
            else:
                title, bullets = item
                with st.container(border=True):
                    st.markdown(f"#### {_card_title(title)}")
                    for b in bullets[:3]:
                        clean = clean_display_text(b)
                        if clean:
                            st.markdown(f"• {emphasize_exec_keywords_html(clean)}", unsafe_allow_html=True)

    # Any remaining sections shown below in a clean full-width block
    if remaining:
        for sec_title, bullets in remaining:
            with st.container(border=True):
                st.markdown(f"#### {_card_title(sec_title)}")
                for b in bullets:
                    clean = clean_display_text(b)
                    if clean:
                        st.markdown(f"• {emphasize_exec_keywords_html(clean)}", unsafe_allow_html=True)

# -----------------------------
# Chart builders (strict categorical alignment)
# -----------------------------
def fig_style_common(fig: go.Figure, title: str) -> go.Figure:
    # Executive-grade defaults for all charts
    fig = apply_consulting_theme(fig, title=title, height=380, y_is_currency=True)
    # Slightly tighter for small multiples will be overridden where needed
    return fig

def bar_categorical(
    x_labels: List[str],
    y_values: List[float],
    title: str,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    colors: Optional[List[str]] = None,
    text_fmt: str = ",.0f",
) -> go.Figure:
    """
    Executive-style categorical bar chart (consultancy sweet spot):
    - Bars anchored at zero (no floating gap)
    - Thin bars + generous whitespace
    - Outside value labels (clean + readable)
    - Leader emphasis (Option 1): top bar highlighted, others muted
    - Left-aligned layout (full width)
    """
    base_x = [str(v) for v in x_labels]
    y = [float(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else 0.0 for v in y_values]

    ranked = [f"{i+1}. {lbl}" for i, lbl in enumerate(base_x)]

    if colors is None:
        leader = CONSULTING_PALETTE[0] if "CONSULTING_PALETTE" in globals() else TABLEAU10[0]
        muted = "#D1D5DB"
        colors = [leader] + [muted] * max(0, len(ranked) - 1)
    else:
        colors = colors[: len(ranked)]

    ymax = max(y) if y else 0.0
    ypad = ymax * 0.12 if ymax > 0 else 1.0

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=ranked,
            y=y,
            customdata=base_x,
            marker=dict(color=colors),
            width=0.22,
            text=y,
            texttemplate=f"%{{text:{text_fmt}}}",
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color="#111827", size=12),
            hovertemplate="%{customdata}<br>$%{y:,.2s}<extra></extra>",
        )
    )

    fig = apply_consulting_theme(fig, title=title, height=380, y_is_currency=True)
    fig.update_layout(bargap=0.78)

    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=ranked,
        title_text=x_title,
        showgrid=False,
        tickfont=dict(family="Inter SemiBold, Inter, Arial, sans-serif", size=12, color="#111827"),
    )
    fig.update_yaxes(
        title_text=y_title,
        range=[0, ymax + ypad],
        autorange=False,
        rangemode="tozero",
        tickfont=dict(family="Inter SemiBold, Inter, Arial, sans-serif", size=12, color="#111827"),
    )
    return fig

def top5_stores_bar(m: RetailModel) -> Tuple[go.Figure, pd.DataFrame]:
    s = m.df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False).head(5)
    dfp = s.reset_index()
    dfp.columns = ["Store", "Revenue"]
    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Store"].tolist(),
        y_values=dfp["Revenue"].tolist(),
        title="Top Revenue-Generating Stores (Top 5)",
        y_title="Revenue",
        colors=colors,
        text_fmt=",.0f",
    )
    fig.update_layout(height=380)
    return fig, dfp

def store_small_multiples(m: RetailModel) -> Tuple[List[go.Figure], List[str]]:
    # top 5 stores
    top = m.df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False).head(5).index.tolist()
    figs = []
    names = []
    for i, store in enumerate(top):
        sub = m.df[m.df[m.col_store] == store]
        daily = sub.groupby(pd.Grouper(key=m.col_date, freq="D"))[m.col_revenue].sum().reset_index()
        fig = go.Figure()
        color = TABLEAU10[i % len(TABLEAU10)]
        fig.add_trace(
            go.Scatter(
                x=daily[m.col_date],
                y=daily[m.col_revenue],
                mode="lines+markers",
                line=dict(width=3, color=color),
                marker=dict(size=5, color=color),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.0f}<extra></extra>",
            )
        )
        fig = apply_consulting_theme(fig, title=f"Store Trend — {store}", height=260, y_is_currency=True)
        fig.update_layout(showlegend=False)
        fig.update_xaxes(showgrid=False)
        fig.update_xaxes(tickformat="%b %d")
        figs.append(fig)
        names.append(store)
    return figs, names

def pricing_effectiveness(m: RetailModel) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_discount is None:
        return None
    df = m.df.dropna(subset=[m.col_discount]).copy()
    if len(df) < 20:
        return None
    bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
    labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
    df["Discount Band"] = pd.cut(df[m.col_discount], bins=bins, labels=labels)
    agg = df.groupby("Discount Band")[m.col_revenue].mean().reindex(labels)
    dfp = agg.reset_index()
    dfp.columns = ["Discount Band", "Avg Revenue per Sale"]
    fig = bar_categorical(
        x_labels=dfp["Discount Band"].astype(str).tolist(),
        y_values=dfp["Avg Revenue per Sale"].fillna(0).tolist(),
        title="Pricing Effectiveness — Avg Revenue per Sale by Discount Level",
        y_title="Avg Revenue per Sale",
        colors=[TABLEAU10[i % len(TABLEAU10)] for i in range(len(dfp))],
        text_fmt=",.0f",
    )
    return fig, dfp

def revenue_by_category(m: RetailModel, topn: int = 8) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_category is None:
        return None
    s = m.df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False).head(topn)
    dfp = s.reset_index()
    dfp.columns = ["Category", "Revenue"]
    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Category"].tolist(),
        y_values=dfp["Revenue"].tolist(),
        title=f"Revenue by Category (Top {len(dfp)})",
        y_title="Revenue",
        colors=colors,
        text_fmt=",.0f",
    )
    fig.update_layout(height=360)
    return fig, dfp

def revenue_by_channel(m: RetailModel, topn: int = 8) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_channel is None:
        return None
    s = m.df.groupby(m.col_channel)[m.col_revenue].sum().sort_values(ascending=False).head(topn)
    dfp = s.reset_index()
    dfp.columns = ["Channel", "Revenue"]
    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Channel"].tolist(),
        y_values=dfp["Revenue"].tolist(),
        title=f"Revenue by Channel (Top {len(dfp)})",
        y_title="Revenue",
        colors=colors,
        text_fmt=",.0f",
    )
    return fig, dfp

def volatility_by_channel(m: RetailModel) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_channel is None:
        return None
    # daily revenue per channel
    daily = m.df.groupby([m.col_channel, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    agg = daily.groupby(m.col_channel)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    agg["Volatility"] = agg["std"] / agg["mean"]
    agg = agg.sort_values("Volatility", ascending=False).dropna(subset=["Volatility"])
    if len(agg) == 0:
        return None
    dfp = agg[["Volatility"]].head(8).reset_index()
    dfp.columns = ["Channel", "Volatility (relative)"]
    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Channel"].tolist(),
        y_values=dfp["Volatility (relative)"].tolist(),
        title=f"Channel Stability — Which Channels Swing the Most",
        y_title="Relative Volatility",
        colors=colors,
        text_fmt=",.2f",
    )
    return fig, dfp

# -----------------------------
# Chart-specific insights (short, human)
# -----------------------------
def insight_block(title: str, what: List[str], why: List[str], action: List[str]) -> None:
    st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)
    st.markdown("**What this shows**")
    for w in what:
        st.markdown(f"- {clean_display_text(w)}")
    st.markdown("**Why it matters**")
    for w in why:
        st.markdown(f"- {clean_display_text(w)}")
    st.markdown("**What to do**")
    for a in action:
        st.markdown(f"- {clean_display_text(a)}")
    st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)

# -----------------------------
# Export helpers (PDF + PPT with charts + commentary)
# -----------------------------
def fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> bytes:
    # Requires kaleido
    return fig.to_image(format="png", scale=scale)

def render_chart_with_commentary(
    fig,
    *,
    what_points=None,
    why_points=None,
    todo_points=None,
    left_ratio=3,
    right_ratio=1,
    height=None,
):
    """Standard left-chart + right-commentary layout used across EC-AI Insight."""
    what_points = what_points or []
    why_points = why_points or []
    todo_points = todo_points or []

    col_l, col_r = st.columns([left_ratio, right_ratio], gap="large")
    with col_l:
        if height is not None:
            try:
                fig.update_layout(height=height)
            except Exception:
                pass
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown(
            """
<div style="border:1.6px dashed #C8CCD0; border-radius:12px; padding:16px 18px; background:#FFFFFF;">
""",
            unsafe_allow_html=True,
        )
        insight_block(
            what_points=what_points,
            why_points=why_points,
            todo_points=todo_points,
        )
        st.markdown("</div>", unsafe_allow_html=True)



def _safe_bullet_lines(lines: List[str], limit: int = 4) -> List[str]:
    out = []
    for line in lines or []:
        t = clean_display_text(md_to_plain(line))
        if t:
            out.append(t)
    return out[:limit]


def _collect_exec_export_content(summary_points: List[str], insight_sections: Dict[str, List[str]]) -> Dict[str, List[str]]:
    summary = _safe_bullet_lines(summary_points, limit=6)
    insight_bullets: List[str] = []
    for title, bullets in list((insight_sections or {}).items())[:3]:
        cleaned = _safe_bullet_lines(bullets, limit=2)
        for b in cleaned:
            insight_bullets.append(f"{title}: {b}")
    return {
        "summary": summary[:4],
        "insights": insight_bullets[:6],
    }


def build_pdf_exec_brief(
    title: str,
    subtitle: str,
    summary_points: List[str],
    insight_sections: Dict[str, List[str]],
    chart_items: List[Tuple[str, go.Figure, str]],
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ECTitle", parent=styles["Title"], fontSize=22, leading=26, alignment=TA_LEFT, textColor="#0B1F3B"))
    styles.add(ParagraphStyle(name="ECSub", parent=styles["BodyText"], fontSize=11, leading=14, textColor="#4B5563"))
    styles.add(ParagraphStyle(name="ECHead", parent=styles["Heading2"], fontSize=14, leading=18, textColor="#0B1F3B", spaceAfter=6))
    styles.add(ParagraphStyle(name="ECBody", parent=styles["BodyText"], fontSize=10.5, leading=13.5, textColor="#111827"))
    styles.add(ParagraphStyle(name="ECSmall", parent=styles["BodyText"], fontSize=9, leading=11, textColor="#6B7280"))

    content = _collect_exec_export_content(summary_points, insight_sections)
    story = []

    # Cover / summary page
    story.append(Paragraph(title, styles["ECTitle"]))
    story.append(Paragraph(subtitle, styles["ECSub"]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("Executive Summary", styles["ECHead"]))

    summary_table_data = []
    left_col = [Paragraph(f"• {x}", styles["ECBody"]) for x in content["summary"][:2]]
    right_col = [Paragraph(f"• {x}", styles["ECBody"]) for x in content["summary"][2:4]]
    while len(left_col) < 2:
        left_col.append(Paragraph("", styles["ECBody"]))
    while len(right_col) < 2:
        right_col.append(Paragraph("", styles["ECBody"]))
    summary_table_data.append([left_col[0], right_col[0]])
    summary_table_data.append([left_col[1], right_col[1]])
    tbl = Table(summary_table_data, colWidths=[3.55 * inch, 3.55 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Management Implications", styles["ECHead"]))
    for bullet in content["insights"][:5]:
        story.append(Paragraph(f"• {bullet}", styles["ECBody"]))

    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph("Prepared by EC-AI Insight | Turning Data Into Intelligence", styles["ECSmall"]))

    # Chart pages
    for ctitle, fig, commentary in chart_items:
        story.append(PageBreak())
        story.append(Paragraph(ctitle, styles["ECHead"]))
        lines = _safe_bullet_lines(str(commentary).split("\n"), limit=5)
        if lines:
            for line in lines:
                story.append(Paragraph(f"• {line}", styles["ECBody"]))
            story.append(Spacer(1, 0.08 * inch))
        png = fig_to_png_bytes(fig, scale=2)
        img_buf = io.BytesIO(png)
        img = RLImage(img_buf, width=7.0 * inch, height=3.55 * inch)
        story.append(img)
        story.append(Spacer(1, 0.10 * inch))
        story.append(Paragraph("EC-AI executive note: focus on the decision implied by this chart, not the chart alone.", styles["ECSmall"]))

    doc.build(story)
    return buf.getvalue()


def _ppt_fill(shape, color_hex: str):
    fill = shape.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(color_hex.replace("#", ""))


def _ppt_add_textbox(slide, left, top, width, height, text, font_size=18, bold=False, color="#111827", align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = RGBColor.from_string(color.replace("#", ""))
    return box


def _ppt_add_bullet_box(slide, left, top, width, height, heading, bullets, bg="#F8FAFC", border="#D1D5DB"):
    rect = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    _ppt_fill(rect, bg)
    rect.line.color.rgb = RGBColor.from_string(border.replace("#", ""))
    rect.line.width = Pt(1.0)
    tf = rect.text_frame
    tf.word_wrap = True
    tf.clear()
    p0 = tf.paragraphs[0]
    p0.text = heading
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = RGBColor.from_string("0B1F3B")
    for bullet in bullets[:5]:
        pp = tf.add_paragraph()
        pp.text = bullet
        pp.level = 0
        pp.font.size = Pt(11.5)
        pp.font.color.rgb = RGBColor.from_string("374151")
    return rect


def _ppt_add_footer(slide, page_text: str):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(7.0), Inches(11.95), Inches(0.02))
    _ppt_fill(line, "#D1D5DB")
    line.line.fill.background()
    _ppt_add_textbox(slide, Inches(0.7), Inches(7.05), Inches(5.5), Inches(0.22), "EC-AI Insight | Turning Data Into Intelligence", font_size=9, color="#6B7280")
    _ppt_add_textbox(slide, Inches(11.5), Inches(7.05), Inches(1.1), Inches(0.22), page_text, font_size=9, color="#6B7280", align=PP_ALIGN.RIGHT)


def build_ppt_talking_deck(
    deck_title: str,
    subtitle: str,
    summary_points: List[str],
    insight_sections: Dict[str, List[str]],
    chart_items: List[Tuple[str, go.Figure, str]],
) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    content = _collect_exec_export_content(summary_points, insight_sections)

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.55))
    _ppt_fill(band, "#0B1F3B")
    band.line.fill.background()
    _ppt_add_textbox(slide, Inches(0.75), Inches(1.05), Inches(8.8), Inches(0.8), deck_title, font_size=26, bold=True, color="#0B1F3B")
    _ppt_add_textbox(slide, Inches(0.75), Inches(1.85), Inches(8.4), Inches(0.5), subtitle, font_size=14, color="#4B5563")
    hero = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.75), Inches(2.5), Inches(5.0), Inches(2.2))
    _ppt_fill(hero, "#F8FAFC")
    hero.line.color.rgb = RGBColor.from_string("D1D5DB")
    _ppt_add_textbox(slide, Inches(1.0), Inches(2.85), Inches(4.5), Inches(0.35), "Executive storyline", font_size=16, bold=True, color="#0B1F3B")
    for i, bullet in enumerate(content["summary"][:3]):
        _ppt_add_textbox(slide, Inches(1.0), Inches(3.25 + i*0.42), Inches(4.3), Inches(0.32), f"• {bullet}", font_size=12, color="#374151")
    right = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.2), Inches(2.5), Inches(6.1), Inches(2.2))
    _ppt_fill(right, "#0B1F3B")
    right.line.fill.background()
    _ppt_add_textbox(slide, Inches(6.55), Inches(2.92), Inches(5.3), Inches(0.42), "Prepared for executive review", font_size=18, bold=True, color="#FFFFFF")
    _ppt_add_textbox(slide, Inches(6.55), Inches(3.45), Inches(5.2), Inches(0.8), "A concise, decision-oriented summary of revenue performance, concentration, pricing signals, and next actions.", font_size=13, color="#E5E7EB")
    _ppt_add_footer(slide, "1")

    # Executive summary slide
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _ppt_add_textbox(slide, Inches(0.7), Inches(0.45), Inches(8.0), Inches(0.45), "Executive Summary", font_size=24, bold=True, color="#0B1F3B")
    _ppt_add_textbox(slide, Inches(0.7), Inches(0.88), Inches(8.5), Inches(0.28), "What senior management should know now", font_size=11, color="#6B7280")
    _ppt_add_bullet_box(slide, Inches(0.7), Inches(1.35), Inches(3.95), Inches(2.25), "Key takeaways", content["summary"][:4])
    _ppt_add_bullet_box(slide, Inches(4.9), Inches(1.35), Inches(3.95), Inches(2.25), "Business implications", content["insights"][:4], bg="#FFFFFF")
    _ppt_add_bullet_box(slide, Inches(9.1), Inches(1.35), Inches(3.5), Inches(2.25), "Recommended next actions", [
        "Protect top-revenue stores first.",
        "Use pricing with discipline, not as a default lever.",
        "Stabilise volatile channels / locations before scaling.",
        "Use the following charts to guide discussion.",
    ], bg="#F9FAFB")
    # add summary strip
    strip = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.7), Inches(4.0), Inches(11.9), Inches(1.6))
    _ppt_fill(strip, "#F8FAFC")
    strip.line.color.rgb = RGBColor.from_string("D1D5DB")
    _ppt_add_textbox(slide, Inches(0.95), Inches(4.28), Inches(11.2), Inches(0.32), "Management framing", font_size=15, bold=True, color="#0B1F3B")
    framing = "This deck is designed to move from fact base to implication: where revenue is concentrated, where risk sits, and which management actions should be prioritised next."
    _ppt_add_textbox(slide, Inches(0.95), Inches(4.72), Inches(11.1), Inches(0.55), framing, font_size=12, color="#374151")
    _ppt_add_footer(slide, "2")

    # Chart slides
    page = 3
    for ctitle, fig, bullets in chart_items:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _ppt_add_textbox(slide, Inches(0.7), Inches(0.42), Inches(8.8), Inches(0.45), ctitle, font_size=22, bold=True, color="#0B1F3B")
        _ppt_add_textbox(slide, Inches(0.7), Inches(0.84), Inches(8.8), Inches(0.25), "Executive-grade chart commentary", font_size=10.5, color="#6B7280")

        png = fig_to_png_bytes(fig, scale=2)
        img_stream = io.BytesIO(png)
        slide.shapes.add_picture(img_stream, Inches(0.7), Inches(1.25), width=Inches(7.7), height=Inches(4.7))

        lines = _safe_bullet_lines(str(bullets).split("\n"), limit=5)
        takeaway = lines[0] if lines else "Use this chart to discuss the business implication, not just the visual."
        implications = lines[1:3] if len(lines) > 1 else ["Translate the signal into operational action."]
        actions = ["Confirm root cause with local owners.", "Decide where to protect, fix, or scale."]

        _ppt_add_bullet_box(slide, Inches(8.7), Inches(1.25), Inches(3.9), Inches(1.55), "Headline takeaway", [takeaway], bg="#0B1F3B", border="#0B1F3B")
        # recolor text for dark box
        dark_shape = slide.shapes[-1]
        for para in dark_shape.text_frame.paragraphs:
            para.font.color.rgb = RGBColor.from_string("FFFFFF")
            para.font.size = Pt(11.5 if para.text != "Headline takeaway" else 15)
        _ppt_add_bullet_box(slide, Inches(8.7), Inches(2.98), Inches(3.9), Inches(1.35), "Why it matters", implications, bg="#F8FAFC")
        _ppt_add_bullet_box(slide, Inches(8.7), Inches(4.48), Inches(3.9), Inches(1.45), "Management action", actions, bg="#FFFFFF")
        _ppt_add_footer(slide, str(page))
        page += 1

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()

# -----------------------------
# Sidebar: upload + diagnostics
# -----------------------------
st.title("EC-AI Insight")
st.markdown("<div class='ec-kicker'>Sales performance, explained clearly.</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='ec-subtle'>Upload your sales data and get a short business briefing — what’s working, what’s risky, and where to focus next.</div>",
    unsafe_allow_html=True
)

st.divider()

with st.sidebar:
    st.header("Data")
    up = st.file_uploader("Upload CSV", type=["csv"])
    demo_clicked = st.button("🚀 Try Demo Dataset (Retail Fashion, HK)")
    st.caption("Tip: First load on Streamlit Cloud may take 30–60 seconds if the app was asleep.")

    st.header("Exports")
    export_scale = st.slider("Export image scale", min_value=1, max_value=3, value=2, help="Higher = clearer charts, but slower exports.")

    st.header("Diagnostics")
    try:
        import plotly
        import importlib.util
        st.write("Plotly:", plotly.__version__)
        st.write("Kaleido installed:", importlib.util.find_spec("kaleido") is not None)
    except Exception as e:
        st.write("Diagnostics unavailable:", e)

# Load data
if "demo_df_raw" not in st.session_state:
    st.session_state.demo_df_raw = None

df_raw = None
data_source = None

if demo_clicked:
    st.session_state.demo_df_raw = load_demo_dataset_fashion_hk()
    df_raw = st.session_state.demo_df_raw
    data_source = "demo"
elif up is not None:
    try:
        df_raw = pd.read_csv(up)
    except Exception:
        up.seek(0)
        df_raw = pd.read_csv(up, encoding="latin-1")
    data_source = "upload"
else:
    st.info("Upload a CSV to begin, or click **Try Demo Dataset**.")

if df_raw is None:
    st.stop()

# Prep
try:
    m = prep_retail(df_raw)
except Exception as e:
    st.error(f"Data load error: {e}")
    st.stop()

df = m.df

# -----------------------------
# Executive Summary / AI Insights / Charts
# -----------------------------
summary_points = build_business_summary_points(m)
ins_sections = build_business_insights_sections(m)

# -----------------------------
# Executive Dashboard (6-grid)
# -----------------------------
try:
    export_figures = render_onepager_dashboard(m, df)
except Exception as _e:
    st.warning(f"Executive Dashboard unavailable: {_e}")

# -----------------------------
# Key Performance Visuals (v7 flow = charts first)
# -----------------------------
st.subheader("Charts & Insights")

# 1) Overall trend
fig_trend = line_trend(df, m.col_date, m.col_revenue, "Revenue Trend (Daily)")
col_l, col_r = st.columns([2, 1], gap="large")
with col_l:
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
with col_r:
    insight_block(
        "Revenue Trend",
        what=["Overall revenue direction over time (daily total)."],
        why=["Sets the context: growth vs stability.", "Helps spot spikes that may come from promotions or one-off events."],
        action=["If the trend is flat, focus on execution and mix. If it’s rising, protect top drivers and scale carefully."],
    )

# 2) Top 5 stores
fig_topstores, df_topstores = top5_stores_bar(m)
col_l, col_r = st.columns([2, 1], gap="large")
with col_l:
    st.plotly_chart(fig_topstores, use_container_width=True, config={"displayModeBar": False})
with col_r:
    top_store_name = df_topstores.iloc[0]["Store"] if len(df_topstores) else "Top store"
    insight_block(
        "Top Stores",
        what=[f"Revenue is concentrated in a small number of stores, led by **{top_store_name}**."],
        why=["Top stores disproportionately drive outcomes.", "Operational issues in one key store can move the whole month."],
        action=["Prioritise stock availability, staffing, and execution in the top stores before expanding elsewhere."],
    )

# 3) Store stability (mini charts)
st.markdown("### Store Stability (Top 5)")
figs, store_names = store_small_multiples(m)
cols = st.columns(2)
for i, fig in enumerate(figs):
    with cols[i % 2]:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
insight_block(
    "Store Stability",
    what=["Some stores are steady while others swing day-to-day."],
    why=["Volatility makes forecasting and inventory planning harder.", "Stability is often execution (not market demand)."],
    action=["Fix volatility first (availability, staffing, promotion timing). Use stable stores as benchmarks for best practices."],
)

# 4) Pricing effectiveness
pe = pricing_effectiveness(m)
if pe is not None:
    fig_price, df_price = pe
    col_chart, col_comment = st.columns([2, 1], gap="medium")
    with col_chart:
        st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})
    with col_comment:
        insight_block(
            "Pricing Effectiveness",
            what=["Moderate discounts often perform better than aggressive discounting."],
            why=["Large discounts can erode revenue quality without improving outcomes.", "Pricing discipline is a repeatable advantage."],
            action=["Use small discounts as default. Treat deep discounts as experiments with clear goals and limits."],
        )
else:
    st.info("Pricing Effectiveness is unavailable (no usable discount column found).")

# 5) Revenue by Category
cat = revenue_by_category(m, topn=8)
if cat is not None:
    fig_cat, _ = cat
    col_chart, col_comment = st.columns([2, 1], gap="medium")
    with col_chart:
        st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})
    with col_comment:
        insight_block(
            "Category Mix",
            what=["A few categories typically drive most revenue."],
            why=["Category mix often matters more than SKU count.", "Weak categories can drag overall performance."],
            action=["Double down on winner categories (stock depth, placement). Review whether weak categories need repositioning or removal."],
        )
else:
    st.info("Category Mix is unavailable (no usable category column found).")

# 6) Revenue by Channel
ch = revenue_by_channel(m, topn=8)
if ch is not None:
    fig_ch, _ = ch
    col_chart, col_comment = st.columns([2, 1], gap="large")
    with col_chart:
        st.plotly_chart(fig_ch, use_container_width=True, config={"displayModeBar": False})
    with col_comment:
        st.markdown(
            "<div style='border:1px dashed #C8CCD0; padding:14px; border-radius:8px; background:#FAFBFC;'>",
            unsafe_allow_html=True,
        )
        insight_block(
            "Channels",
            what=["Channels contribute very differently to revenue."],
            why=["Scaling the right channel can be cheaper than opening new stores.", "Channel concentration adds risk if one channel weakens."],
            action=["Invest more in high-performing channels. Fix or rethink consistently weak channels."],
        )
        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Channels view is unavailable (no usable channel column found).")

st.divider()

# -----------------------------
# Executive Summary (after charts)
# -----------------------------
st.subheader("Executive Summary")
for p in summary_points[:12]:
    _t = clean_display_text(p)
    if _t:
        st.markdown(f"• {emphasize_exec_keywords_html(_t)}", unsafe_allow_html=True)

st.divider()

# -----------------------------
# Business Insights (v7 cards)
# -----------------------------
render_parallel_insight_cards(ins_sections)

st.divider()

# -----------------------------
# Test elements (v7 rebuild marker)
# -----------------------------
with st.expander("Test Elements", expanded=False):
    st.caption("Recovered reconstruction block for v7 validation.")
    t1, t2, t3 = st.columns(3)
    t1.metric("Rows", f"{len(df):,}")
    try:
        t2.metric("Date Points", f"{df[m.col_date].nunique():,}" if m.col_date else "N/A")
    except Exception:
        t2.metric("Date Points", "N/A")
    try:
        t3.metric("Revenue", _fmt_money(pd.to_numeric(df[m.col_revenue], errors="coerce").fillna(0).sum()) if m.col_revenue else "N/A")
    except Exception:
        t3.metric("Revenue", "N/A")
    st.caption("Use this section to sanity-check the recovered build before locking future versions.")

# -----------------------------
# Advanced analytics + Ask AI + Exports (restored)
# -----------------------------
st.divider()

with st.expander("Advanced analytics (optional)", expanded=False):
    st.caption("Optional deeper diagnostics for power users. Collapsed by default to keep the UI executive-clean.")
    try:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(num_cols) >= 2:
            corr = df[num_cols].corr(numeric_only=True)
            # Show top correlations with revenue if available
            if m.col_revenue in corr.columns:
                top_corr = (
                    corr[m.col_revenue]
                    .drop(labels=[m.col_revenue], errors="ignore")
                    .sort_values(key=lambda s: s.abs(), ascending=False)
                    .head(10)
                    .reset_index()
                    .rename(columns={"index": "Metric", m.col_revenue: "Correlation"})
                )
                st.markdown("**Top correlations with Revenue (directional)**")
                st.dataframe(top_corr, use_container_width=True, hide_index=True)
            st.markdown("**Correlation heatmap (numeric metrics)**")
            fig_corr = px.imshow(
                corr,
                text_auto=False,
                aspect="auto",
                color_continuous_scale="Blues",
            )
            fig_corr.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=420)
            st.plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Not enough numeric columns to compute correlations.")
    except Exception as e:
        st.warning(f"Advanced analytics unavailable: {e}")

st.subheader("Ask AI (CEO Q&A)")
st.caption("Ask questions about your data (e.g., “Why did revenue drop?” “Which store should I fix first?”).")

# Build a lightweight context from the generated insights
_context_lines: List[str] = []
try:
    _context_lines.append(f"Dataset: {len(df)} rows, {df[m.col_date].nunique() if m.col_date else 'NA'} days.")
except Exception:
    pass
try:
    _context_lines += [f"- {clean_display_text(x)}" for x in summary_points if clean_display_text(x)]
except Exception:
    pass
try:
    for sec_title, bullets in ins_sections.items():
        _context_lines.append(f"{sec_title}:")
        _context_lines += [f"- {clean_display_text(x)}" for x in bullets if clean_display_text(x)]
except Exception:
    pass
dashboard_notes = "\n".join([x for x in _context_lines if x]).strip()
context_text = _build_ai_context(df, m)
if dashboard_notes:
    context_text = context_text + "\n\nDASHBOARD INSIGHTS (auto-generated):\n" + dashboard_notes
if "ask_ai_history" not in st.session_state:
    st.session_state.ask_ai_history = []
if "ask_ai_question" not in st.session_state:
    st.session_state.ask_ai_question = ""

st.markdown("#### Suggested Questions")
sq1, sq2, sq3 = st.columns(3)
with sq1:
    if st.button("What is driving revenue growth?", use_container_width=True):
        st.session_state.ask_ai_question = "What is driving revenue growth?"
with sq2:
    if st.button("Which store or category should I focus on?", use_container_width=True):
        st.session_state.ask_ai_question = "Which store or category should I focus on?"
with sq3:
    if st.button("How can I improve revenue or margins?", use_container_width=True):
        st.session_state.ask_ai_question = "How can I improve revenue or margins?"

q_col, btn_col = st.columns([0.82, 0.18])
with q_col:
    user_q = st.text_input("Ask EC-AI…", value=st.session_state.ask_ai_question, key="ask_ai_question_input", placeholder="E.g., What should I focus on next week?")
with btn_col:
    ask_clicked = st.button("Ask", use_container_width=True)

if ask_clicked and user_q.strip():
    st.session_state.ask_ai_question = user_q.strip()
    with st.spinner("Thinking…"):
        answer = answer_question_with_openai(user_q.strip(), context_text)
        answer = format_ai_answer(answer)
    st.session_state.ask_ai_history.insert(0, (user_q.strip(), answer))
    st.session_state.ask_ai_history = st.session_state.ask_ai_history[:6]

for q, a in st.session_state.ask_ai_history[:3]:
    with st.container(border=True):
        st.markdown(f"**Q:** {q}")
        st.markdown(a)

st.divider()
st.divider()

st.subheader("Export Executive Pack")
st.caption("Download a shareable executive-ready brief (PDF) or slide pack (PPTX).")

# Build chart items for export (only include charts that exist)
chart_items: List[Tuple[str, go.Figure, str]] = []

try:
    chart_items.append((
        "Revenue Trend (Daily)",
        fig_trend,
        "• Trend line of daily revenue.\n• Use this to spot spikes/dips and protect momentum."
    ))
except Exception:
    pass

try:
    chart_items.append((
        "Top Revenue-Generating Stores (Top 5)",
        fig_topstores,
        "• Revenue concentration by store.\n• Prioritise execution in the top stores first."
    ))
except Exception:
    pass

try:
    if pe is not None:
        chart_items.append((
            "Pricing Effectiveness — Avg Revenue per Sale by Discount Level",
            fig_price,
            "• Compares average revenue per sale across discount levels.\n• Use moderate discounts by default; treat deep discounts as controlled tests."
        ))
except Exception:
    pass

try:
    if cat is not None:
        chart_items.append((
            "Revenue by Category",
            fig_cat,
            "• Shows which categories drive revenue.\n• Double down on winners; fix or trim weak categories."
        ))
except Exception:
    pass

try:
    if ch is not None:
        chart_items.append((
            "Revenue by Channel",
            fig_ch,
            "• Channel contribution to revenue.\n• Reallocate effort to channels that consistently perform."
        ))
except Exception:
    pass

c1, c2 = st.columns(2)

with c1:
    if st.button("Generate PDF Executive Brief", use_container_width=True):
        try:
            pdf_bytes = build_pdf_exec_brief(
                title="EC-AI Insight — Executive Brief",
                subtitle="Sales performance, explained clearly.",
                summary_points=summary_points,
                insight_sections=ins_sections,
                chart_items=chart_items,
            )
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name="ecai_executive_brief.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

with c2:
    if st.button("Generate Executive Pack (PPTX)", use_container_width=True):
        try:
            pptx_bytes = build_ppt_talking_deck(
                deck_title="EC-AI Insight — Executive Pack",
                subtitle="McKinsey-style executive storyline with summary, implications, and chart-by-chart actions.",
                summary_points=summary_points,
                insight_sections=ins_sections,
                chart_items=chart_items,
            )
            st.download_button(
                "Download PPTX",
                data=pptx_bytes,
                file_name="ecai_executive_pack.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PPT generation failed: {e}")
