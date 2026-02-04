# EC-AI Insight (MVP) — Executive Brief v1 (Launch Freeze)
# Streamlit app: CEO-grade narrative + curated charts + PDF/PPT export.
# Default: Executive Mode. Advanced mode is optional.

import io
import datetime as _dt
import textwrap
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


# -----------------------------
# Global styling
# -----------------------------
st.set_page_config(
    page_title="EC-AI Insight (MVP)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_FONT_PX = 18
H1_PX = 40
H2_PX = 26
H3_PX = 20
SMALL_PX = 16

EC_BLUE = "#1F77B4"
EC_ORANGE = "#FF7F0E"
EC_RED = "#D62728"
EC_TEAL = "#17A2B8"
EC_GREEN = "#2CA02C"
EC_YELLOW = "#F2C94C"

PALETTE_5 = [EC_BLUE, EC_ORANGE, EC_RED, EC_TEAL, EC_GREEN]
PALETTE_6 = [EC_BLUE, EC_ORANGE, EC_RED, EC_TEAL, EC_GREEN, EC_YELLOW]

# Signal 4 — remove zoom/toolbar clutter
PLOT_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "showTips": False,
}

st.markdown(
    f"""
    <style>
      html, body, [class*="css"]  {{
        font-size: {BASE_FONT_PX}px !important;
      }}
      .ec-title {{ font-size: {H1_PX}px; font-weight: 800; margin-bottom: 2px; }}
      .ec-subtitle {{ font-size: {SMALL_PX}px; color: #6b7280; margin-top: 0px; margin-bottom: 18px; }}
      .ec-section-title {{ font-size: {H2_PX}px; font-weight: 800; margin-top: 10px; margin-bottom: 6px; }}
      .ec-subheader {{ font-size: {H3_PX}px; font-weight: 800; margin-top: 8px; margin-bottom: 6px; }}
      .ec-card {{ border: 1px solid #E5E7EB; border-radius: 14px; padding: 14px 16px; background: #FFFFFF; }}
      .ec-note {{ color: #6b7280; font-size: {SMALL_PX}px; line-height: 1.4; }}
      .ec-bullets li {{ margin-bottom: 10px; }}
      .block-container {{ padding-top: 1.2rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Utilities
# -----------------------------
def _fmt_money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    x = float(x)
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
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x*100:.1f}%"


def _clean_text(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("**", "").strip()


def _wrap_lines(text: str, width: int = 95) -> List[str]:
    return textwrap.wrap(_clean_text(text), width=width, break_long_words=False)


def _ensure_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _detect_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    lowered = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    for c in df.columns:
        cl = c.lower()
        for cand in candidates:
            if cand.lower() in cl:
                return c
    return None


def _normalize_discount_rate(x: pd.Series) -> pd.Series:
    s = _ensure_numeric(x).copy()
    finite = s.dropna()
    if len(finite) and finite.max() > 1.0:
        s = s / 100.0
    return s.clip(lower=0)


def _discount_band(rate: float) -> str:
    if rate is None or (isinstance(rate, float) and np.isnan(rate)):
        return "Unknown"
    r = float(rate)
    if r < 0.02:
        return "0–2%"
    if r < 0.05:
        return "2–5%"
    if r < 0.10:
        return "5–10%"
    if r < 0.15:
        return "10–15%"
    if r < 0.20:
        return "15–20%"
    return "20%+"


DISCOUNT_ORDER = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]


def _fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> bytes:
    try:
        return fig.to_image(format="png", scale=scale)
    except Exception as e:
        raise RuntimeError(
            "Chart export failed. Ensure 'kaleido' is in requirements.txt and Plotly is installed. "
            f"Original error: {e}"
        ) from e


# -----------------------------
# Schema + preparation
# -----------------------------
@dataclass
class Schema:
    date: Optional[str]
    revenue: Optional[str]
    store: Optional[str]
    category: Optional[str]
    channel: Optional[str]
    discount: Optional[str]
    payment: Optional[str]


def infer_schema(df: pd.DataFrame) -> Schema:
    return Schema(
        date=_detect_col(df, ["date", "order_date", "transaction_date", "invoice_date"]),
        revenue=_detect_col(df, ["revenue", "sales", "amount", "total", "net_sales"]),
        store=_detect_col(df, ["store", "location", "shop", "branch"]),
        category=_detect_col(df, ["category", "product_category", "dept", "department"]),
        channel=_detect_col(df, ["channel", "sales_channel", "source"]),
        discount=_detect_col(df, ["discount_rate", "discount", "promo", "markdown"]),
        payment=_detect_col(df, ["payment_method", "payment", "tender", "pay_method"]),
    )


def prepare_df(df: pd.DataFrame, schema: Schema) -> pd.DataFrame:
    out = df.copy()
    out["_date"] = _to_datetime(out[schema.date]) if schema.date and schema.date in out.columns else pd.NaT
    out["_revenue"] = _ensure_numeric(out[schema.revenue]) if schema.revenue and schema.revenue in out.columns else np.nan
    out["_discount_rate"] = _normalize_discount_rate(out[schema.discount]) if schema.discount and schema.discount in out.columns else np.nan

    def _string_col(col: Optional[str], name: str) -> None:
        if col and col in out.columns:
            out[name] = out[col].astype(str).fillna("Unknown")
        else:
            out[name] = "Unknown"

    _string_col(schema.store, "_store")
    _string_col(schema.category, "_category")
    _string_col(schema.channel, "_channel")
    _string_col(schema.payment, "_payment")

    out["_discount_band"] = out["_discount_rate"].apply(_discount_band)
    return out


# -----------------------------
# Metrics tables
# -----------------------------
def compute_store_revenue(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("_store", dropna=False)["_revenue"].sum().reset_index()
    g = g.sort_values("_revenue", ascending=False)
    total = g["_revenue"].sum()
    g["share"] = g["_revenue"] / total if total else np.nan
    return g


def compute_category_revenue(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("_category", dropna=False)["_revenue"].sum().reset_index()
    g = g.sort_values("_revenue", ascending=False)
    total = g["_revenue"].sum()
    g["share"] = g["_revenue"] / total if total else np.nan
    return g


def compute_channel_revenue(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("_channel", dropna=False)["_revenue"].sum().reset_index()
    g = g.sort_values("_revenue", ascending=False)
    total = g["_revenue"].sum()
    g["share"] = g["_revenue"] / total if total else np.nan
    return g


def compute_store_daily(df: pd.DataFrame) -> pd.DataFrame:
    if df["_date"].isna().all():
        return pd.DataFrame(columns=["_date", "_store", "_revenue"])
    return df.dropna(subset=["_date"]).groupby(["_date", "_store"])["_revenue"].sum().reset_index()


def compute_channel_daily(df: pd.DataFrame) -> pd.DataFrame:
    if df["_date"].isna().all():
        return pd.DataFrame(columns=["_date", "_channel", "_revenue"])
    return df.dropna(subset=["_date"]).groupby(["_date", "_channel"])["_revenue"].sum().reset_index()


def compute_volatility_cv(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 2:
        return np.nan
    m = s.mean()
    if m == 0:
        return np.nan
    return float(s.std(ddof=1) / m)


def compute_store_volatility(df_daily: pd.DataFrame) -> pd.DataFrame:
    if df_daily.empty:
        return pd.DataFrame(columns=["_store", "cv"])
    g = df_daily.groupby("_store")["_revenue"].apply(compute_volatility_cv).reset_index(name="cv")
    return g.sort_values("cv", ascending=False)


def compute_channel_volatility(df_channel_daily: pd.DataFrame) -> pd.DataFrame:
    if df_channel_daily.empty:
        return pd.DataFrame(columns=["_channel", "cv"])
    g = df_channel_daily.groupby("_channel")["_revenue"].apply(compute_volatility_cv).reset_index(name="cv")
    return g.sort_values("cv", ascending=False)


def compute_discount_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("_discount_band")["_revenue"].agg(["count", "sum", "mean"]).reset_index()
    g = g.rename(columns={"count": "transactions", "sum": "total_revenue", "mean": "avg_revenue_per_sale"})
    g["_discount_band"] = pd.Categorical(g["_discount_band"], categories=DISCOUNT_ORDER, ordered=True)
    return g.sort_values("_discount_band")


def compute_pareto(df_store: pd.DataFrame) -> pd.DataFrame:
    d = df_store.copy()
    d["cum_share"] = d["share"].cumsum()
    d["rank"] = np.arange(1, len(d) + 1)
    return d


# -----------------------------
# Charts (frozen)
# -----------------------------
def fig_revenue_by_store(df_store: pd.DataFrame, top_n: int = 10) -> go.Figure:
    d = df_store.head(top_n).sort_values("_revenue", ascending=True)
    fig = px.bar(
        d,
        x="_revenue",
        y="_store",
        orientation="h",
        text=d["_revenue"].apply(_fmt_money),
        labels={"_revenue": "Revenue", "_store": "Store"},
        title="Revenue by Store (Top 10)",
    )
    fig.update_traces(marker_color=EC_BLUE, textposition="outside", cliponaxis=False)
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=20), title=dict(x=0.0, font=dict(size=22)))
    return fig


def fig_pareto(df_pareto: pd.DataFrame, top_n: int = 15) -> go.Figure:
    d = df_pareto.head(top_n).copy()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=d["_store"],
            y=d["_revenue"],
            marker_color=EC_BLUE,
            text=d["_revenue"].apply(_fmt_money),
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=d["_store"],
            y=d["cum_share"],
            yaxis="y2",
            mode="lines+markers",
            line=dict(width=3, color=EC_ORANGE),
        )
    )
    fig.update_layout(
        title="Revenue Concentration (Pareto view)",
        height=420,
        margin=dict(l=10, r=10, t=60, b=60),
        title=dict(x=0.0, font=dict(size=22)),
        xaxis=dict(type="category", tickfont=dict(size=13)),
        yaxis=dict(title="Revenue"),
        yaxis2=dict(title="Cumulative share", overlaying="y", side="right", tickformat=".0%", range=[0, 1]),
        showlegend=False,
    )
    return fig


def fig_revenue_by_category(df_cat: pd.DataFrame, top_n: int = 5) -> go.Figure:
    d = df_cat.head(top_n).copy()
    order = list(d["_category"])
    fig = px.bar(
        d,
        x="_category",
        y="_revenue",
        color="_category",
        category_orders={"_category": order},
        color_discrete_sequence=PALETTE_6,
        text=d["_revenue"].apply(_fmt_money),
        labels={"_category": "Category", "_revenue": "Revenue"},
        title="Revenue by Category (Top 5)",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=60, b=40),
        title=dict(x=0.0, font=dict(size=22)),
        xaxis=dict(type="category"),
        showlegend=False,
        bargap=0.45,
    )
    return fig


def fig_pricing_effectiveness(df_discount: pd.DataFrame) -> go.Figure:
    # Force all bands to exist in the same order so labels align (fixes your “bar label cannot align” issue)
    d = df_discount.set_index("_discount_band").reindex(DISCOUNT_ORDER).reset_index()
    d["avg_revenue_per_sale"] = d["avg_revenue_per_sale"].fillna(0)

    fig = px.bar(
        d,
        x="_discount_band",
        y="avg_revenue_per_sale",
        category_orders={"_discount_band": DISCOUNT_ORDER},
        color="_discount_band",
        color_discrete_sequence=PALETTE_6,
        text=d["avg_revenue_per_sale"].apply(lambda v: _fmt_money(v) if v else "—"),
        labels={"_discount_band": "Discount band", "avg_revenue_per_sale": "Average revenue per sale"},
        title="Pricing Effectiveness (Average revenue per sale by discount band)",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=60, b=40),
        title=dict(x=0.0, font=dict(size=22)),
        xaxis=dict(type="category", tickmode="array", tickvals=DISCOUNT_ORDER, ticktext=DISCOUNT_ORDER),
        showlegend=False,
        bargap=0.45,
    )
    return fig


def fig_channel_revenue(df_channel: pd.DataFrame) -> go.Figure:
    d = df_channel.copy()
    order = list(d["_channel"])
    fig = px.bar(
        d,
        x="_channel",
        y="_revenue",
        color="_channel",
        category_orders={"_channel": order},
        color_discrete_sequence=PALETTE_6,
        text=d["_revenue"].apply(_fmt_money),
        labels={"_channel": "Channel", "_revenue": "Revenue"},
        title="Revenue by Channel",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=60, b=40),
        title=dict(x=0.0, font=dict(size=22)),
        xaxis=dict(type="category"),
        showlegend=False,
        bargap=0.45,
    )
    return fig


def fig_channel_volatility(df_channel_vol: pd.DataFrame) -> go.Figure:
    d = df_channel_vol.copy()
    if d.empty:
        fig = go.Figure()
        fig.update_layout(title="Channel Stability (Volatility score)", height=320)
        return fig
    order = list(d["_channel"])
    fig = px.bar(
        d,
        x="_channel",
        y="cv",
        color="_channel",
        category_orders={"_channel": order},
        color_discrete_sequence=PALETTE_6,
        text=d["cv"].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "—"),
        labels={"_channel": "Channel", "cv": "Volatility score (CV)"},
        title="Channel Stability (higher = less stable)",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=60, b=40),
        title=dict(x=0.0, font=dict(size=22)),
        xaxis=dict(type="category"),
        showlegend=False,
        bargap=0.45,
    )
    return fig


def fig_store_stability_small_multiples(df_daily: pd.DataFrame, top_stores: List[str]) -> List[go.Figure]:
    figs = []
    color_map = {s: PALETTE_5[i % len(PALETTE_5)] for i, s in enumerate(top_stores)}
    for store in top_stores:
        d = df_daily[df_daily["_store"] == store].sort_values("_date")
        fig = px.line(d, x="_date", y="_revenue", labels={"_date": "Date", "_revenue": "Revenue"}, title=store)
        fig.update_traces(line=dict(width=3, color=color_map.get(store, EC_BLUE)))
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=50, b=30), title=dict(x=0.0, font=dict(size=18)))
        figs.append(fig)
    return figs


# -----------------------------
# CEO-grade narrative (with concrete examples)
# -----------------------------
def build_business_insights(
    df: pd.DataFrame,
    df_store: pd.DataFrame,
    df_cat: pd.DataFrame,
    df_store_vol: pd.DataFrame,
    df_channel_vol: pd.DataFrame,
    df_discount: pd.DataFrame,
) -> Dict[str, List[str]]:
    total_rev = float(df["_revenue"].sum()) if df["_revenue"].notna().any() else 0.0

    top1 = df_store.iloc[0] if len(df_store) else None
    top2 = df_store.iloc[1] if len(df_store) > 1 else None
    cat1 = df_cat.iloc[0] if len(df_cat) else None
    cat2 = df_cat.iloc[1] if len(df_cat) > 1 else None

    top2_share = None
    if top1 is not None and top2 is not None and total_rev > 0:
        top2_share = float((top1["_revenue"] + top2["_revenue"]) / total_rev)

    most_vol_store = df_store_vol.iloc[0] if len(df_store_vol) else None
    most_vol_channel = df_channel_vol.iloc[0] if len(df_channel_vol) else None

    best_band = None
    if len(df_discount):
        d = df_discount[df_discount["_discount_band"].isin(DISCOUNT_ORDER)].sort_values("avg_revenue_per_sale", ascending=False)
        best_band = d.iloc[0] if len(d) else None

    money = []
    if top1 is not None:
        money.append(f"Revenue is led by **{_clean_text(top1['_store'])}** ({_fmt_money(top1['_revenue'])}).")
    if top2 is not None:
        money.append(f"The #2 contributor is **{_clean_text(top2['_store'])}** ({_fmt_money(top2['_revenue'])}).")
    if top2_share is not None:
        money.append(f"Together, the top two stores contribute about **{_fmt_pct(top2_share)}** of total revenue — small execution gains there move the whole business.")
    if cat1 is not None:
        money.append(f"Top category by revenue is **{_clean_text(cat1['_category'])}** ({_fmt_money(cat1['_revenue'])}).")
    if cat2 is not None:
        money.append(f"Second strongest category is **{_clean_text(cat2['_category'])}** ({_fmt_money(cat2['_revenue'])}).")

    risk = []
    if most_vol_store is not None and pd.notna(most_vol_store.get("cv", np.nan)):
        risk.append(f"Performance is uneven: **{_clean_text(most_vol_store['_store'])}** has the highest day-to-day volatility (CV ≈ **{most_vol_store['cv']:.2f}**).")
    if top2_share is not None:
        risk.append("Revenue concentration increases downside risk — a slip in top stores can materially impact total results.")
    if most_vol_channel is not None and pd.notna(most_vol_channel.get("cv", np.nan)):
        risk.append(f"Channel predictability differs: **{_clean_text(most_vol_channel['_channel'])}** is the least stable channel (CV ≈ **{most_vol_channel['cv']:.2f}**).")

    improve = []
    if best_band is not None and pd.notna(best_band.get("avg_revenue_per_sale", np.nan)):
        improve.append(f"Moderate discounts tend to perform better: **{_clean_text(best_band['_discount_band'])}** has the highest average revenue per sale ({_fmt_money(best_band['avg_revenue_per_sale'])}).")
        improve.append("Bigger discounts do **not** automatically lead to better results — treat deep discounts as experiments with clear targets.")
    improve.append("Consistency (stock, staffing, execution) typically delivers higher ROI than launching new campaigns.")

    next_steps = [
        "Strengthen execution in top stores first (availability, staffing, promotion discipline) — then scale improvements.",
        "Stabilize volatile stores/channels before pushing growth through heavier discounting or expansion.",
        "Use pricing discipline as the guardrail: grow revenue **per sale**, not just volume.",
    ]

    summary = []
    if top1 is not None and top2 is not None:
        summary.append(f"Sales are concentrated: **{_clean_text(top1['_store'])}** and **{_clean_text(top2['_store'])}** are the top two revenue contributors.")
    if top2_share is not None:
        summary.append(f"Top two stores contribute about **{_fmt_pct(top2_share)}** of total revenue — protecting them is priority #1.")
    if cat1 is not None:
        summary.append(f"Category mix matters: **{_clean_text(cat1['_category'])}** is the top revenue driver.")
    if cat2 is not None:
        summary.append(f"**{_clean_text(cat2['_category'])}** is the second strongest category — a clear lever for focused growth.")
    if best_band is not None:
        summary.append(f"Pricing: **{_clean_text(best_band['_discount_band'])}** delivers the best revenue per sale; deep discounts are not automatically better.")
    if most_vol_store is not None and pd.notna(most_vol_store.get("cv", np.nan)):
        summary.append(f"Operational risk: **{_clean_text(most_vol_store['_store'])}** is the most volatile store — forecasting and planning will be harder there.")
    if most_vol_channel is not None and pd.notna(most_vol_channel.get("cv", np.nan)):
        summary.append(f"Channel stability differs: **{_clean_text(most_vol_channel['_channel'])}** is the least stable channel.")
    summary.append("Fastest ROI typically comes from improving execution in top stores (availability, staffing, promo discipline).")
    summary.append("Use promotions as controlled tests with measurable targets — stop what doesn’t improve revenue per sale.")
    summary.append("Focus sequence: **protect top stores → stabilize volatility → scale what works**.")
    while len(summary) < 10:
        summary.append("Keep reporting simple: decisions first, details on demand (Executive vs Advanced mode).")

    return {"summary": summary[:10], "money": money, "risk": risk, "improve": improve, "next": next_steps}


# -----------------------------
# Exports
# -----------------------------
def make_executive_brief_pdf(
    title: str,
    subtitle: str,
    insights: Dict[str, List[str]],
    figures: List[Tuple[str, go.Figure, str]],
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    W, H = LETTER

    def draw_title():
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, H - 55, title)
        c.setFont("Helvetica", 11)
        c.setFillGray(0.35)
        c.drawString(50, H - 72, subtitle)
        c.setFillGray(0)
        c.setFont("Helvetica", 10)
        c.drawString(50, H - 88, f"Generated: {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.line(50, H - 98, W - 50, H - 98)

    def draw_bullets(y: float, header: str, bullets: List[str], font_size=11, leading=15, width_chars=95):
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, header)
        y -= 18
        c.setFont("Helvetica", font_size)
        for b in bullets:
            lines = _wrap_lines(b, width=width_chars)
            for li, line in enumerate(lines):
                prefix = "• " if li == 0 else "  "
                c.drawString(55, y, prefix + line)
                y -= leading
                if y < 90:
                    c.showPage()
                    draw_title()
                    y = H - 120
                    c.setFont("Helvetica", font_size)
        return y - 6

    def draw_chart_page(chart_title: str, fig: go.Figure, caption: str):
        c.showPage()
        draw_title()
        y_top = H - 120
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y_top, chart_title)
        y_top -= 16

        img_bytes = _fig_to_png_bytes(fig, scale=2)
        img = ImageReader(io.BytesIO(img_bytes))
        iw, ih = img.getSize()
        max_w, max_h = W - 100, 360
        scale = min(max_w / iw, max_h / ih)
        draw_w, draw_h = iw * scale, ih * scale
        c.drawImage(img, 50, y_top - draw_h, width=draw_w, height=draw_h, mask="auto")

        y_cap = y_top - draw_h - 18
        c.setFont("Helvetica", 11)
        for line in _wrap_lines(caption, width=95):
            c.drawString(50, y_cap, line)
            y_cap -= 14

    draw_title()
    y = H - 120
    y = draw_bullets(y, "Business Summary (CEO-grade)", insights.get("summary", []))
    y = draw_bullets(y, "Where the money is made", insights.get("money", []))
    y = draw_bullets(y, "Where risk exists", insights.get("risk", []))
    y = draw_bullets(y, "What can be improved", insights.get("improve", []))
    y = draw_bullets(y, "What to focus on next", insights.get("next", []))

    for chart_title, fig, caption in figures:
        draw_chart_page(chart_title, fig, caption)

    c.save()
    buf.seek(0)
    return buf.read()


def make_talking_deck_ppt(title: str, slides: List[Tuple[str, go.Figure, List[str]]]) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Title slide
    s0 = prs.slides.add_slide(prs.slide_layouts[5])
    tx = s0.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(12.0), Inches(1.0)).text_frame
    p = tx.paragraphs[0]
    p.text = title
    p.font.size = Pt(34)
    p.font.bold = True
    p.font.color.rgb = RGBColor(0, 0, 0)

    sub = s0.shapes.add_textbox(Inches(0.8), Inches(1.7), Inches(12.0), Inches(0.7)).text_frame
    p2 = sub.paragraphs[0]
    p2.text = "Executive Brief v1 — one insight per slide (16:9)"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(90, 98, 108)

    for slide_title, fig, bullets in slides:
        s = prs.slides.add_slide(prs.slide_layouts[5])

        tbox = s.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12.0), Inches(0.9)).text_frame
        tbox.word_wrap = True
        tp = tbox.paragraphs[0]
        tp.text = slide_title
        tp.font.size = Pt(26)
        tp.font.bold = True
        tp.font.color.rgb = RGBColor(0, 0, 0)

        img = io.BytesIO(_fig_to_png_bytes(fig, scale=2))
        s.shapes.add_picture(img, Inches(0.7), Inches(1.3), width=Inches(8.1), height=Inches(5.6))

        b = s.shapes.add_textbox(Inches(9.0), Inches(1.35), Inches(4.0), Inches(5.5)).text_frame
        b.word_wrap = True
        b.clear()
        for i, line in enumerate(bullets[:4]):
            para = b.paragraphs[0] if i == 0 else b.add_paragraph()
            para.text = _clean_text(line)
            para.level = 0
            para.font.size = Pt(16)
            para.font.color.rgb = RGBColor(30, 41, 59)

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()


# -----------------------------
# UI
# -----------------------------
st.markdown('<div class="ec-title">EC-AI Insight (MVP)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ec-subtitle">CEO-grade business insights for retail sales data — clear decisions, not charts for charts’ sake.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Upload")
    up = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    st.markdown("---")
    exec_mode = st.toggle("Executive Mode (default)", value=True)
    show_advanced = st.toggle("Show Advanced Sections", value=False)
    st.markdown("---")
    st.markdown("### Export")
    export_pdf = st.button("Generate Executive Brief (PDF)")
    export_ppt = st.button("Generate PPT Talking Deck (16:9)")
    st.caption("PDF = executive brief. PPT = one insight per slide.")

if not up:
    st.info("Upload a dataset to generate the Executive Brief.")
    st.stop()

try:
    if up.name.lower().endswith(".csv"):
        df_raw = pd.read_csv(up)
    else:
        df_raw = pd.read_excel(up)
except Exception as e:
    st.error(f"Failed to read file: {e}")
    st.stop()

schema = infer_schema(df_raw)

# Advanced mapping
if show_advanced:
    with st.sidebar:
        st.markdown("### Advanced: column mapping")
        cols = [None] + list(df_raw.columns)

        def _idx(v):
            return cols.index(v) if v in df_raw.columns else 0

        schema = Schema(
            date=st.selectbox("Date column", cols, index=_idx(schema.date)),
            revenue=st.selectbox("Revenue column", cols, index=_idx(schema.revenue)),
            store=st.selectbox("Store column", cols, index=_idx(schema.store)),
            category=st.selectbox("Category column", cols, index=_idx(schema.category)),
            channel=st.selectbox("Channel column", cols, index=_idx(schema.channel)),
            discount=st.selectbox("Discount column", cols, index=_idx(schema.discount)),
            payment=st.selectbox("Payment column", cols, index=_idx(schema.payment)),
        )

df = prepare_df(df_raw, schema)
if df["_revenue"].isna().all():
    st.error("Revenue column not found or not numeric. Use Advanced mapping in the sidebar.")
    st.stop()

# Compute
df_store = compute_store_revenue(df)
df_cat = compute_category_revenue(df)
df_channel = compute_channel_revenue(df)
df_daily = compute_store_daily(df)
df_store_vol = compute_store_volatility(df_daily)
df_channel_daily = compute_channel_daily(df)
df_channel_vol = compute_channel_volatility(df_channel_daily)
df_discount = compute_discount_table(df)
df_pareto = compute_pareto(df_store)

insights = build_business_insights(df, df_store, df_cat, df_store_vol, df_channel_vol, df_discount)

# Frozen chart set
fig_store = fig_revenue_by_store(df_store, top_n=10)
fig_p = fig_pareto(df_pareto, top_n=15)
fig_cat = fig_revenue_by_category(df_cat, top_n=5)
fig_discount = fig_pricing_effectiveness(df_discount)
fig_chan_rev = fig_channel_revenue(df_channel)
fig_chan_vol = fig_channel_volatility(df_channel_vol)

top5_stores = list(df_store.head(5)["_store"]) if len(df_store) else []
stability_figs = fig_store_stability_small_multiples(df_daily, top5_stores) if (len(top5_stores) and not df_daily.empty) else []

# Executive UI
if exec_mode:
    st.divider()
    st.markdown('<div class="ec-section-title">Business Summary</div>', unsafe_allow_html=True)
    st.markdown('<div class="ec-card">', unsafe_allow_html=True)
    st.markdown("<ul class='ec-bullets'>" + "".join([f"<li>{b}</li>" for b in insights["summary"]]) + "</ul>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="ec-section-title">Business Insights</div>', unsafe_allow_html=True)

    def section_block(title: str, bullets: List[str]):
        st.markdown(f'<div class="ec-subheader">{title}</div>', unsafe_allow_html=True)
        st.markdown('<div class="ec-card">', unsafe_allow_html=True)
        st.markdown("<ul class='ec-bullets'>" + "".join([f"<li>{b}</li>" for b in bullets]) + "</ul>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    section_block("Where the money is made", insights["money"])
    section_block("Where risk exists", insights["risk"])
    section_block("What can be improved", insights["improve"])
    section_block("What to focus on next", insights["next"])

    st.divider()
    st.markdown('<div class="ec-section-title">Key Charts</div>', unsafe_allow_html=True)
    st.markdown('<div class="ec-note">Only the charts that “earn the right to exist” in Executive Mode. No zoom, no clutter.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(fig_store, use_container_width=True, config=PLOT_CONFIG)
        st.caption("Caption: Revenue is concentrated — top stores drive outsized impact on total performance.")
    with c2:
        st.plotly_chart(fig_p, use_container_width=True, config=PLOT_CONFIG)
        st.caption("Caption: Pareto view shows how quickly revenue accumulates in a small number of stores.")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(fig_cat, use_container_width=True, config=PLOT_CONFIG)
        st.caption("Caption: Category mix matters — focus on the categories that actually generate revenue.")
    with c4:
        st.plotly_chart(fig_discount, use_container_width=True, config=PLOT_CONFIG)
        st.caption("Caption: Pricing effectiveness — moderate discounts can outperform aggressive discounting.")

    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(fig_chan_rev, use_container_width=True, config=PLOT_CONFIG)
        st.caption("Caption: Channel revenue contribution — useful for scaling decisions.")
    with c6:
        st.plotly_chart(fig_chan_vol, use_container_width=True, config=PLOT_CONFIG)
        st.caption("Caption: Channel stability — volatility signals forecasting/operational risk.")

    if stability_figs:
        st.divider()
        st.markdown('<div class="ec-section-title">Store Stability (Top 5)</div>', unsafe_allow_html=True)
        st.markdown('<div class="ec-note">One store per chart. One store = one color (Tableau-like clarity).</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, fig in enumerate(stability_figs):
            with cols[i % 2]:
                st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

    st.divider()
    st.markdown('<div class="ec-section-title">Real Comparisons (Tables)</div>', unsafe_allow_html=True)

    t1, t2 = st.columns(2)
    with t1:
        st.markdown("**Top Stores (Revenue + Share)**")
        tbl = df_store.head(10).copy()
        tbl["Revenue"] = tbl["_revenue"].apply(_fmt_money)
        tbl["Share"] = tbl["share"].apply(_fmt_pct)
        st.dataframe(tbl[["_store", "Revenue", "Share"]].rename(columns={"_store": "Store"}), use_container_width=True, hide_index=True)
    with t2:
        st.markdown("**Discount Bands (Revenue per sale)**")
        dtab = df_discount.copy()
        dtab["Avg revenue per sale"] = dtab["avg_revenue_per_sale"].apply(_fmt_money)
        dtab["Total revenue"] = dtab["total_revenue"].apply(_fmt_money)
        st.dataframe(
            dtab[["_discount_band", "transactions", "Total revenue", "Avg revenue per sale"]]
            .rename(columns={"_discount_band": "Discount band", "transactions": "Transactions"}),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    with st.expander("Why EC-AI vs ChatGPT / Google Analytics / Adobe Analytics"):
        st.markdown(
            """
            **The difference is the output (CEO-grade decisions).**
            
            - **Google/Adobe Analytics**: great at tracking events and traffic, but they don’t translate data into *CEO decisions* automatically.
            - **ChatGPT**: can explain your data, but it doesn’t give you a repeatable executive brief + “one-click deck” that a team can reuse weekly.
            - **EC-AI**: turns raw transaction data into **decision-ready narrative + rankings**, and exports it as a brief + talking deck.
            
            **AI functions EC-AI provides that traditional tools don’t (for SME owners):**
            1. Auto “Executive Brief” narrative (CEO-grade, with concrete examples)
            2. Auto-selection of only the charts that matter (default vs advanced)
            3. Decision metrics (concentration, stability, pricing effectiveness)
            4. Weekly repeatability (same structure every run)
            5. One-click export to PDF + PPT with charts
            """
        )

# Advanced
if show_advanced:
    st.divider()
    st.markdown('<div class="ec-section-title">Advanced (optional)</div>', unsafe_allow_html=True)

    with st.expander("Preview data"):
        st.dataframe(df_raw.head(50), use_container_width=True)

    with st.expander("Data profile"):
        prof = pd.DataFrame(
            {
                "column": df_raw.columns,
                "dtype": [str(df_raw[c].dtype) for c in df_raw.columns],
                "missing_%": [(df_raw[c].isna().mean() * 100) for c in df_raw.columns],
                "unique": [df_raw[c].nunique(dropna=True) for c in df_raw.columns],
            }
        ).sort_values("missing_%", ascending=True)
        st.dataframe(prof, use_container_width=True, hide_index=True)

    with st.expander("Correlations (numeric only)"):
        num = df.select_dtypes(include=[np.number]).copy()
        if num.shape[1] < 2:
            st.info("Not enough numeric columns for correlation.")
        else:
            corr = num.corr(numeric_only=True)
            fig = px.imshow(corr, text_auto=".2f", aspect="auto", title="Correlation heatmap (advanced)")
            fig.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)

# Export
pdf_figures = [
    ("Revenue by Store (Top 10)", fig_store, "Revenue is concentrated in a small number of stores. Protect and optimize the top stores first."),
    ("Revenue Concentration (Pareto)", fig_p, "The Pareto view shows how quickly revenue accumulates among top stores."),
    ("Revenue by Category (Top 5)", fig_cat, "Category mix is a key lever. Focus growth efforts where revenue is actually generated."),
    ("Pricing Effectiveness", fig_discount, "Moderate discounts can outperform aggressive discounting. Measure revenue per sale, not just volume."),
    ("Revenue by Channel", fig_chan_rev, "Channels contribute differently to revenue. Use this to guide scaling decisions."),
    ("Channel Stability", fig_chan_vol, "Higher volatility indicates higher forecasting and operational risk."),
]

ppt_slides = [
    ("Revenue is concentrated in top stores", fig_store, insights["money"][:3]),
    ("Revenue concentration creates downside risk", fig_p, ["When revenue is concentrated, execution slips in top stores materially impact the total."]),
    ("Category mix is a growth lever", fig_cat, insights["money"][-2:]),
    ("Moderate discounts often outperform", fig_discount, insights["improve"][:2]),
    ("Channel mix and stability matter", fig_chan_rev, ["Use channel revenue + stability together to decide where to scale."]),
    ("Stability: where forecasting is hardest", fig_chan_vol, insights["risk"][-2:]),
]

if export_pdf or export_ppt:
    st.sidebar.markdown("---")
    if export_pdf:
        try:
            pdf_bytes = make_executive_brief_pdf(
                "EC-AI Executive Brief",
                "Retail sales insights — CEO-grade narrative + selected charts",
                insights,
                pdf_figures,
            )
            st.sidebar.success("PDF ready.")
            st.sidebar.download_button(
                "Download Executive Brief (PDF)",
                data=pdf_bytes,
                file_name="ecai_executive_brief_v1.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.sidebar.error(f"PDF export failed: {e}")

    if export_ppt:
        try:
            ppt_bytes = make_talking_deck_ppt("EC-AI Talking Deck", ppt_slides)
            st.sidebar.success("PPT ready.")
            st.sidebar.download_button(
                "Download Talking Deck (PPTX)",
                data=ppt_bytes,
                file_name="ecai_talking_deck_v1_16x9.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
        except Exception as e:
            st.sidebar.error(f"PPT export failed: {e}")
