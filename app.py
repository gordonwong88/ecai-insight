import os
import io
import re
import textwrap
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Optional deps for exports
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# -------------------------
# App config + styling
# -------------------------
st.set_page_config(
    page_title="EC-AI Insight",
    page_icon="📈",
    layout="wide",
)

BASE_FONT = 18  # bump overall readability

CUSTOM_CSS = f"""
<style>
html, body, [class*="css"]  {{
  font-size: {BASE_FONT}px !important;
}}
h1 {{ font-size: 42px !important; margin-bottom: 0.2rem; }}
h2 {{ font-size: 28px !important; margin-top: 1.2rem; }}
h3 {{ font-size: 22px !important; margin-top: 1.0rem; }}
.small-muted {{ color: #6b7280; font-size: 14px; }}
.ec-card {{
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 16px 18px;
  margin: 10px 0 16px 0;
}}
.ec-kpi {{
  display:flex; gap: 14px; flex-wrap: wrap;
}}
.ec-kpi .k {{
  background:#f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 12px 14px;
  min-width: 180px;
}}
.ec-kpi .k .t {{
  font-size: 13px;
  color:#6b7280;
  margin-bottom: 4px;
}}
.ec-kpi .k .v {{
  font-size: 22px;
  font-weight: 700;
  color:#0f172a;
}}
hr {{
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 18px 0;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Plotly defaults: "consultancy grade" = clean, no zoom UI
PLOTLY_TEMPLATE = "plotly_white"
COLOR_SEQ = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7"]

PLOT_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": "reset",
    "showTips": False,
    "responsive": True,
}

# -------------------------
# Helpers
# -------------------------
def money(x: float) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    ax = abs(float(x))
    if ax >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if ax >= 1_000:
        return f"${x/1_000:.1f}K"
    return f"${x:,.0f}"

def pct(x: float, digits: int = 0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"{x*100:.{digits}f}%"

def safe_text(s: str) -> str:
    # Remove accidental markdown artifacts like ** or stray asterisks
    if s is None:
        return ""
    s = re.sub(r"\*\*", "", str(s))
    s = s.replace("*", "")
    return s

def wrap_lines(lines: List[str], width: int = 92) -> List[str]:
    out = []
    for l in lines:
        l = safe_text(l).strip()
        if not l:
            continue
        out.extend(textwrap.wrap(l, width=width))
    return out

def fig_style(fig: go.Figure, title: Optional[str] = None) -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        font=dict(size=16),
        title=dict(text=title or "", x=0.0, xanchor="left"),
        margin=dict(l=40, r=20, t=60 if title else 30, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        dragmode=False,
    )
    fig.update_xaxes(
        title_font=dict(size=14),
        tickfont=dict(size=13),
        showgrid=False,
        zeroline=False,
        type="category",  # fixes category tick positioning issues
    )
    fig.update_yaxes(
        title_font=dict(size=14),
        tickfont=dict(size=13),
        showgrid=True,
        gridcolor="rgba(0,0,0,0.06)",
        zeroline=False,
    )
    return fig

def fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> Optional[bytes]:
    # Prefer kaleido
    try:
        return pio.to_image(fig, format="png", scale=scale, engine="kaleido")
    except Exception:
        try:
            return fig.to_image(format="png", scale=scale)
        except Exception:
            return None

# -------------------------
# Column detection + model
# -------------------------
def _find_col(cols: List[str], keywords: List[str]) -> Optional[str]:
    for k in keywords:
        for c in cols:
            if k in c.lower():
                return c
    return None

def guess_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    cols = list(df.columns)
    cols_l = [c.lower() for c in cols]

    col_date = _find_col(cols, ["date", "day", "order date", "txn date", "transaction date"])
    col_rev = _find_col(cols, ["revenue", "sales", "amount", "gmv", "net sales", "total"])
    col_cost = _find_col(cols, ["cogs", "cost"])
    col_store = _find_col(cols, ["store", "branch", "location", "shop"])
    col_cat = _find_col(cols, ["category", "product category", "dept", "department"])
    col_channel = _find_col(cols, ["channel", "platform", "source"])
    col_discount = _find_col(cols, ["discount", "discount_rate", "disc"])
    col_qty = _find_col(cols, ["qty", "quantity", "units"])
    col_unit_price = _find_col(cols, ["unit_price", "unit price", "price"])
    col_returned = _find_col(cols, ["returned", "return_flag", "is_return", "refund"])

    return {
        "date": col_date,
        "revenue": col_rev,
        "cost": col_cost,
        "store": col_store,
        "category": col_cat,
        "channel": col_channel,
        "discount": col_discount,
        "qty": col_qty,
        "unit_price": col_unit_price,
        "returned": col_returned,
    }

def coerce_numeric(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    # strip %, $ and commas
    ss = s.astype(str).str.replace(",", "", regex=False)
    ss = ss.str.replace("$", "", regex=False)
    ss = ss.str.replace("%", "", regex=False)
    return pd.to_numeric(ss, errors="coerce")

def coerce_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")

@dataclass
class RetailModel:
    col_date: str
    col_revenue: str
    col_store: Optional[str] = None
    col_category: Optional[str] = None
    col_channel: Optional[str] = None
    col_discount: Optional[str] = None
    col_cost: Optional[str] = None
    col_qty: Optional[str] = None
    col_unit_price: Optional[str] = None
    col_returned: Optional[str] = None

def validate_and_prepare(df: pd.DataFrame, model: RetailModel) -> pd.DataFrame:
    d = df.copy()

    # rename canonical for ease
    rename = {}
    rename[model.col_revenue] = "Revenue"
    rename[model.col_date] = "Date"
    if model.col_store: rename[model.col_store] = "Store"
    if model.col_category: rename[model.col_category] = "Category"
    if model.col_channel: rename[model.col_channel] = "Channel"
    if model.col_discount: rename[model.col_discount] = "Discount"
    if model.col_cost: rename[model.col_cost] = "COGS"
    if model.col_qty: rename[model.col_qty] = "Qty"
    if model.col_unit_price: rename[model.col_unit_price] = "UnitPrice"
    if model.col_returned: rename[model.col_returned] = "Returned"

    d = d.rename(columns=rename)

    d["Revenue"] = coerce_numeric(d["Revenue"]).fillna(0.0)
    d["Date"] = coerce_date(d["Date"])
    d = d.dropna(subset=["Date"])

    # optional numeric fields
    if "Discount" in d.columns:
        disc = coerce_numeric(d["Discount"])
        # if looks like 0-100, scale down to 0-1
        if disc.dropna().max() > 1.5:
            disc = disc / 100.0
        d["Discount"] = disc.clip(lower=0, upper=1)
    if "COGS" in d.columns:
        d["COGS"] = coerce_numeric(d["COGS"])
    if "Qty" in d.columns:
        d["Qty"] = coerce_numeric(d["Qty"])
    if "UnitPrice" in d.columns:
        d["UnitPrice"] = coerce_numeric(d["UnitPrice"])
    if "Returned" in d.columns:
        rr = d["Returned"]
        if rr.dtype == bool:
            d["Returned"] = rr.astype(int)
        else:
            d["Returned"] = coerce_numeric(rr).fillna(0).clip(0, 1)

    # fill cats
    for c in ["Store", "Category", "Channel"]:
        if c in d.columns:
            d[c] = d[c].astype(str).fillna("Unknown")
    return d

# -------------------------
# Insight engine (CEO-grade with examples)
# -------------------------
def compute_core(df: pd.DataFrame) -> Dict:
    out = {}
    out["n_rows"] = len(df)
    out["days"] = int(df["Date"].dt.date.nunique())
    out["revenue_total"] = float(df["Revenue"].sum())
    out["date_min"] = df["Date"].min()
    out["date_max"] = df["Date"].max()

    # Store contributions
    if "Store" in df.columns:
        s = df.groupby("Store", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
        out["store_rank"] = s
    else:
        out["store_rank"] = None

    # Category contributions
    if "Category" in df.columns:
        c = df.groupby("Category", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
        out["cat_rank"] = c
    else:
        out["cat_rank"] = None

    # Channel contributions
    if "Channel" in df.columns:
        ch = df.groupby("Channel", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
        out["channel_rank"] = ch
    else:
        out["channel_rank"] = None

    # Trend
    daily = df.groupby(df["Date"].dt.date, as_index=False)["Revenue"].sum()
    daily = daily.rename(columns={"Date": "Date"})
    out["daily"] = daily

    # Discount bands
    if "Discount" in df.columns:
        bins = [0, 0.02, 0.05, 0.10, 0.15, 0.20, 1.0]
        labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
        dd = df.copy()
        dd["DiscBand"] = pd.cut(dd["Discount"].fillna(0), bins=bins, labels=labels, include_lowest=True, right=True)
        # revenue per sale
        band = dd.groupby("DiscBand", as_index=False)["Revenue"].mean().rename(columns={"Revenue": "AvgRevenue"})
        out["discount_band"] = band
        # also total count per band
        cnt = dd.groupby("DiscBand", as_index=False).size().rename(columns={"size": "Transactions"})
        out["discount_cnt"] = cnt
    else:
        out["discount_band"] = None
        out["discount_cnt"] = None

    # Stability / volatility per store (CV of daily revenue)
    if "Store" in df.columns:
        tmp = df.copy()
        tmp["Day"] = tmp["Date"].dt.date
        sday = tmp.groupby(["Store", "Day"], as_index=False)["Revenue"].sum()
        g = sday.groupby("Store")["Revenue"]
        vol = (g.std() / g.mean()).replace([np.inf, -np.inf], np.nan)
        vol = vol.fillna(0).sort_values(ascending=False)
        out["store_vol"] = vol.reset_index().rename(columns={"Revenue": "CV"})
    else:
        out["store_vol"] = None

    # Channel volatility (CV of daily revenue)
    if "Channel" in df.columns:
        tmp = df.copy()
        tmp["Day"] = tmp["Date"].dt.date
        cday = tmp.groupby(["Channel", "Day"], as_index=False)["Revenue"].sum()
        g = cday.groupby("Channel")["Revenue"]
        vol = (g.std() / g.mean()).replace([np.inf, -np.inf], np.nan)
        vol = vol.fillna(0).sort_values(ascending=False)
        out["channel_vol"] = vol.reset_index().rename(columns={"Revenue": "CV"})
    else:
        out["channel_vol"] = None

    # margin estimate if COGS present
    if "COGS" in df.columns:
        margin = (df["Revenue"] - df["COGS"])
        out["gross_margin_total"] = float(margin.sum())
        out["gross_margin_pct"] = float((margin.sum() / df["Revenue"].sum()) if df["Revenue"].sum() else np.nan)
    else:
        out["gross_margin_total"] = None
        out["gross_margin_pct"] = None

    return out

def build_business_summary(core: Dict) -> List[str]:
    total = core["revenue_total"]
    days = core["days"]
    n = core["n_rows"]

    bullets = []
    bullets.append(f"You have {days} days of data across {n:,} transactions (total revenue {money(total)}).")

    # concentration
    if core.get("store_rank") is not None and len(core["store_rank"]) >= 1:
        s = core["store_rank"]
        top1 = s.iloc[0]
        top1_share = (top1["Revenue"]/total) if total else 0
        bullets.append(f"Revenue is concentrated: {top1['Store']} contributes {money(top1['Revenue'])} (about {pct(top1_share)} of total).")

        if len(s) >= 2:
            top2 = s.iloc[:2]["Revenue"].sum()
            bullets.append(f"The top 2 stores together generate {money(top2)} (about {pct(top2/total) if total else '-'}). Small wins in these locations move the whole business.")

    if core.get("cat_rank") is not None and len(core["cat_rank"]) >= 1:
        c = core["cat_rank"].iloc[0]
        bullets.append(f"By category, {c['Category']} is your largest driver at {money(c['Revenue'])} (about {pct(c['Revenue']/total) if total else '-'}).")

    # momentum (first half vs second half)
    daily = core["daily"]
    if len(daily) >= 10:
        mid = len(daily) // 2
        first = daily.iloc[:mid]["Revenue"].sum()
        second = daily.iloc[mid:]["Revenue"].sum()
        if first > 0:
            delta = (second/first) - 1
            direction = "more" if delta >= 0 else "less"
            bullets.append(f"Momentum is {'positive' if delta>=0 else 'soft'}: the second half delivered about {abs(delta)*100:.0f}% {direction} revenue than the first half.")

    # volatility
    if core.get("store_vol") is not None and len(core["store_vol"]) >= 1:
        sv = core["store_vol"].sort_values("CV", ascending=False).iloc[0]
        bullets.append(f"Sales are not equally predictable: {sv['Store']} shows the biggest day-to-day swings (variability score ≈ {sv['CV']:.2f}).")

    # discounting
    if core.get("discount_band") is not None:
        band = core["discount_band"].dropna()
        if len(band) >= 2:
            best = band.sort_values("AvgRevenue", ascending=False).iloc[0]
            worst = band.sort_values("AvgRevenue", ascending=True).iloc[0]
            bullets.append(f"Discounting: {best['DiscBand']} performs best on average ({money(best['AvgRevenue'])} per sale). {worst['DiscBand']} underperforms ({money(worst['AvgRevenue'])} per sale).")
            bullets.append("Takeaway: moderate discounts tend to work better than aggressive ones — bigger discounts do not automatically lead to better results.")

    # next focus
    bullets.append("Next focus: protect and improve the top stores first (inventory, staffing, execution), then scale what works.")
    return bullets

def build_business_insights(core: Dict) -> Dict[str, List[str]]:
    total = core["revenue_total"]
    s = core.get("store_rank")
    c = core.get("cat_rank")
    ch = core.get("channel_rank")
    sv = core.get("store_vol")
    dv = core.get("channel_vol")
    band = core.get("discount_band")

    insights = {
        "Where the money is made": [],
        "Where risk exists": [],
        "What can be improved": [],
        "What to focus on next": [],
    }

    if s is not None and len(s) >= 2:
        t1, t2 = s.iloc[0], s.iloc[1]
        insights["Where the money is made"].append(
            f"Your revenue is led by a small number of stores — {t1['Store']} ({money(t1['Revenue'])}, {pct(t1['Revenue']/total)}) and {t2['Store']} ({money(t2['Revenue'])}, {pct(t2['Revenue']/total)})."
        )
        top5 = s.iloc[:5]["Revenue"].sum()
        insights["Where the money is made"].append(
            f"The top 5 stores contribute {pct(top5/total) if total else '-'} of total revenue. These locations are your biggest levers."
        )
    elif s is not None and len(s) == 1:
        t1 = s.iloc[0]
        insights["Where the money is made"].append(
            f"Most revenue comes from {t1['Store']} ({money(t1['Revenue'])}, {pct(t1['Revenue']/total) if total else '-'})."
        )

    if c is not None and len(c) >= 3:
        c1, c2 = c.iloc[0], c.iloc[1]
        insights["Where the money is made"].append(
            f"Category leaders are clear: {c1['Category']} ({money(c1['Revenue'])}) and {c2['Category']} ({money(c2['Revenue'])})."
        )
    if ch is not None and len(ch) >= 1:
        ch1 = ch.iloc[0]
        insights["Where the money is made"].append(
            f"Channel mix matters: {ch1['Channel']} is currently your top channel ({money(ch1['Revenue'])})."
        )

    if sv is not None and len(sv) >= 1:
        s_v = sv.sort_values("CV", ascending=False).iloc[0]
        insights["Where risk exists"].append(
            f"Volatility is concentrated: {s_v['Store']} is the most unstable (variability score ≈ {s_v['CV']:.2f}), which makes forecasting and staffing harder."
        )
    if dv is not None and len(dv) >= 1:
        c_v = dv.sort_values("CV", ascending=False).iloc[0]
        insights["Where risk exists"].append(
            f"Channel volatility is highest in {c_v['Channel']} (variability score ≈ {c_v['CV']:.2f}). Consider tightening promo planning and supply on this channel."
        )
    if s is not None and len(s) >= 2:
        top2_share = s.iloc[:2]["Revenue"].sum()/total if total else 0
        insights["Where risk exists"].append(
            f"Concentration risk is real: if the top 2 stores soften, ~{pct(top2_share)} of revenue is exposed."
        )

    if band is not None:
        b = band.dropna()
        if len(b) >= 2:
            best = b.sort_values("AvgRevenue", ascending=False).iloc[0]
            # pick a high-discount band (10%+)
            high = b[b["DiscBand"].isin(["10–15%", "15–20%", "20%+"])]
            if len(high) > 0:
                high_worst = high.sort_values("AvgRevenue").iloc[0]
                insights["What can be improved"].append(
                    f"Discount discipline beats aggressive discounting: {best['DiscBand']} has the best revenue per sale ({money(best['AvgRevenue'])}), while {high_worst['DiscBand']} is weaker ({money(high_worst['AvgRevenue'])})."
                )
            else:
                worst = b.sort_values("AvgRevenue").iloc[0]
                insights["What can be improved"].append(
                    f"Discount discipline beats aggressive discounting: {best['DiscBand']} performs best ({money(best['AvgRevenue'])} per sale) vs {worst['DiscBand']} ({money(worst['AvgRevenue'])})."
                )
            insights["What can be improved"].append(
                "Treat deep discounts as experiments: set a goal (volume, new customers, clearance) and measure whether it actually improves revenue per sale."
            )

    if core.get("gross_margin_pct") is not None and not np.isnan(core["gross_margin_pct"]):
        insights["What can be improved"].append(
            f"Gross margin is about {pct(core['gross_margin_pct'], 1)} overall. Check margin by store/category to avoid growing low-quality revenue."
        )

    insights["What to focus on next"].append(
        "Protect the top stores first: ensure stock availability, staffing, and execution discipline in your #1–#2 locations."
    )
    insights["What to focus on next"].append(
        "Stabilize volatility before scaling: inconsistent performance is often operational (stock-outs, staffing gaps, promo inconsistency)."
    )
    insights["What to focus on next"].append(
        "Scale what works: keep the discount band that performs best, and stop what doesn’t improve revenue per sale."
    )

    return insights

# -------------------------
# Charts (each with commentary)
# -------------------------
def chart_top_stores(df: pd.DataFrame, top_n: int = 5) -> Tuple[go.Figure, str]:
    s = df.groupby("Store", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False).head(top_n)
    fig = px.bar(
        s,
        x="Store",
        y="Revenue",
        text="Revenue",
        color="Store",
        color_discrete_sequence=COLOR_SEQ,
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, bargap=0.45)
    fig = fig_style(fig, "Top Stores by Revenue")
    fig.update_yaxes(title="Revenue")
    fig.update_xaxes(title="", categoryorder="total descending")
    # commentary
    total = df["Revenue"].sum()
    top1 = s.iloc[0]
    comment = f"Your #1 store is {top1['Store']} at {money(top1['Revenue'])} ({pct(top1['Revenue']/total) if total else '-'} of total). Protect inventory and staffing here first — it’s your biggest lever."
    return fig, comment

def chart_revenue_trend(df: pd.DataFrame) -> Tuple[go.Figure, str]:
    d = df.groupby(df["Date"].dt.date, as_index=False)["Revenue"].sum()
    d.columns = ["Date", "Revenue"]
    fig = px.line(d, x="Date", y="Revenue")
    fig.update_traces(mode="lines", line=dict(width=3))
    # label top 2 peaks
    if len(d) >= 3:
        peaks = d.nlargest(2, "Revenue")
        fig.add_trace(go.Scatter(
            x=peaks["Date"], y=peaks["Revenue"],
            mode="markers+text",
            text=[money(v) for v in peaks["Revenue"]],
            textposition="top center",
            showlegend=False
        ))
    fig = fig_style(fig, "Revenue Trend")
    fig.update_yaxes(title="Revenue")
    fig.update_xaxes(title="")
    comment = "Use this to spot promotion spikes vs. normal baseline. Peaks often correspond to specific campaigns, events, or stock timing."
    return fig, comment

def chart_discount_effect(df: pd.DataFrame) -> Tuple[Optional[go.Figure], Optional[str]]:
    if "Discount" not in df.columns:
        return None, None
    bins = [0, 0.02, 0.05, 0.10, 0.15, 0.20, 1.0]
    labels = ["0–2%", "2–5%", "5–10%", "10–15%", "15–20%", "20%+"]
    dd = df.copy()
    dd["DiscBand"] = pd.cut(dd["Discount"].fillna(0), bins=bins, labels=labels, include_lowest=True, right=True)
    g = dd.groupby("DiscBand", as_index=False)["Revenue"].mean().rename(columns={"Revenue": "AvgRevenue"}).dropna()
    if g.empty:
        return None, None
    fig = px.bar(
        g,
        x="DiscBand",
        y="AvgRevenue",
        color="DiscBand",
        color_discrete_sequence=COLOR_SEQ,
        text="AvgRevenue"
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, bargap=0.45)
    fig = fig_style(fig, "Pricing & Discount Effectiveness")
    fig.update_xaxes(title="Discount band", type="category", categoryorder="array", categoryarray=labels)
    fig.update_yaxes(title="Average revenue per sale")
    best = g.sort_values("AvgRevenue", ascending=False).iloc[0]
    worst = g.sort_values("AvgRevenue", ascending=True).iloc[0]
    comment = f"Best-performing band is {best['DiscBand']} at {money(best['AvgRevenue'])} per sale. Weakest is {worst['DiscBand']} at {money(worst['AvgRevenue'])}. Bigger discounts do not automatically improve results."
    return fig, comment

def chart_top_categories(df: pd.DataFrame, top_n: int = 5) -> Tuple[Optional[go.Figure], Optional[str]]:
    if "Category" not in df.columns:
        return None, None
    c = df.groupby("Category", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False).head(top_n)
    fig = px.bar(c, x="Category", y="Revenue", color="Category", text="Revenue", color_discrete_sequence=COLOR_SEQ)
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, bargap=0.45)
    fig = fig_style(fig, "Top Categories by Revenue")
    fig.update_xaxes(title="", type="category", categoryorder="total descending")
    fig.update_yaxes(title="Revenue")
    top = c.iloc[0]
    comment = f"Your top category is {top['Category']} at {money(top['Revenue'])}. Consider protecting availability and pricing here — it’s a core driver."
    return fig, comment

def chart_channel_mix(df: pd.DataFrame) -> Tuple[Optional[go.Figure], Optional[str]]:
    if "Channel" not in df.columns:
        return None, None
    ch = df.groupby("Channel", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
    fig = px.bar(ch, x="Channel", y="Revenue", color="Channel", text="Revenue", color_discrete_sequence=COLOR_SEQ)
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, bargap=0.45)
    fig = fig_style(fig, "Revenue by Channel")
    fig.update_xaxes(title="", type="category", categoryorder="total descending")
    fig.update_yaxes(title="Revenue")
    top = ch.iloc[0]
    comment = f"Your strongest channel is {top['Channel']} at {money(top['Revenue'])}. Use this as the benchmark when allocating budget and stock."
    return fig, comment

def chart_store_stability(df: pd.DataFrame, top_n: int = 5) -> Tuple[Optional[go.Figure], Optional[str]]:
    if "Store" not in df.columns:
        return None, None
    tmp = df.copy()
    tmp["Day"] = tmp["Date"].dt.date
    sday = tmp.groupby(["Store", "Day"], as_index=False)["Revenue"].sum()
    g = sday.groupby("Store")["Revenue"]
    cv = (g.std() / g.mean()).replace([np.inf, -np.inf], np.nan).fillna(0).sort_values(ascending=False)
    cv = cv.reset_index().rename(columns={"Revenue": "CV"}).head(top_n)
    fig = px.bar(cv, x="Store", y="CV", color="Store", text="CV", color_discrete_sequence=COLOR_SEQ)
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, bargap=0.45)
    fig = fig_style(fig, "Store Volatility (higher = less stable)")
    fig.update_yaxes(title="Variability score (CV)")
    fig.update_xaxes(title="", categoryorder="total descending")
    top = cv.iloc[0]
    comment = f"Most volatile store is {top['Store']} (CV {top['CV']:.2f}). Stabilizing this improves forecasting, staffing, and inventory planning."
    return fig, comment

# -------------------------
# "Ask EC-AI" rule-based Q&A (no key shown)
# -------------------------
SUGGESTED_QUESTIONS = [
    "What are my top 3 business priorities?",
    "Which store should I protect first and why?",
    "Are discounts helping or hurting?",
    "Where is volatility coming from?",
    "What should I investigate next week?",
]

def answer_question_rule_based(question: str, core: Dict) -> str:
    q = (question or "").lower().strip()
    total = core["revenue_total"]
    s = core.get("store_rank")
    c = core.get("cat_rank")
    band = core.get("discount_band")
    sv = core.get("store_vol")

    if "top 3" in q or "priorit" in q:
        out = []
        if s is not None and len(s) >= 1:
            out.append(f"1) Protect your #1 store ({s.iloc[0]['Store']}) — it drives {pct(s.iloc[0]['Revenue']/total) if total else '-'} of revenue.")
        if band is not None:
            b = band.dropna()
            if len(b) > 0:
                best = b.sort_values("AvgRevenue", ascending=False).iloc[0]
                out.append(f"2) Keep discounting disciplined — {best['DiscBand']} is currently best per sale.")
        if sv is not None and len(sv) > 0:
            v = sv.sort_values("CV", ascending=False).iloc[0]
            out.append(f"3) Reduce volatility in {v['Store']} — it is the most unstable and makes planning harder.")
        return "\n".join(out) if out else "I need store/discount fields to answer this precisely."
    if "store" in q and ("protect" in q or "focus" in q or "first" in q):
        if s is not None and len(s) >= 1:
            top = s.iloc[0]
            return f"Start with {top['Store']} ({money(top['Revenue'])}, {pct(top['Revenue']/total) if total else '-'} of total). Small improvements here move the whole business the most."
        return "I need a Store column to answer this."
    if "discount" in q:
        if band is not None:
            b = band.dropna()
            if len(b) >= 2:
                best = b.sort_values("AvgRevenue", ascending=False).iloc[0]
                worst = b.sort_values("AvgRevenue", ascending=True).iloc[0]
                return f"Discounts are not linear: {best['DiscBand']} performs best ({money(best['AvgRevenue'])} per sale), while {worst['DiscBand']} is weakest ({money(worst['AvgRevenue'])}). Use deep discounts only with clear goals and measurement."
        return "I need a Discount column to answer this."
    if "volatil" in q or "stable" in q:
        if sv is not None and len(sv) > 0:
            v = sv.sort_values("CV", ascending=False).iloc[0]
            return f"Volatility is concentrated in {v['Store']} (CV {v['CV']:.2f}). Check for stock-outs, staffing gaps, or inconsistent promotions there."
        return "I need a Store column to compute volatility."
    if "next week" in q or "investigate" in q:
        out = []
        if c is not None and len(c) >= 1:
            out.append(f"Check your top category ({c.iloc[0]['Category']}) — is performance driven by price, volume, or availability?")
        if s is not None and len(s) >= 2:
            out.append(f"Compare the #1 vs #2 stores ({s.iloc[0]['Store']} vs {s.iloc[1]['Store']}) — what operational differences explain the gap?")
        if band is not None:
            out.append("Review discount experiments — did higher discounts improve revenue per sale or only volume?")
        return "\n".join(out) if out else "I can suggest next checks once I detect store/category/discount fields."
    return "Ask about priorities, stores, discounts, volatility, or what to check next — I’ll answer using your data."

# -------------------------
# PDF + PPT exports (Executive Brief v1)
# -------------------------
def make_exec_brief_pdf(title: str, summary: List[str], insights: Dict[str, List[str]], chart_pngs: List[Tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    x0 = 0.85 * inch
    y = h - 0.9 * inch

    def draw_h1(t):
        nonlocal y
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x0, y, t)
        y -= 0.35 * inch

    def draw_h2(t):
        nonlocal y
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x0, y, t)
        y -= 0.22 * inch

    def draw_bullets(items, font=11, leading=14, max_lines=26):
        nonlocal y
        c.setFont("Helvetica", font)
        wrapped = []
        for it in items:
            it = safe_text(it)
            wrapped.extend(["• " + s for s in textwrap.wrap(it, width=105)])
        for line in wrapped[:max_lines]:
            if y < 1.0 * inch:
                c.showPage()
                y = h - 0.9 * inch
                c.setFont("Helvetica", font)
            c.drawString(x0, y, line)
            y -= (leading / 72.0) * inch
        y -= 0.12 * inch

    draw_h1(title)
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.4, 0.45, 0.5)
    c.drawString(x0, y, "EC-AI Executive Brief v1")
    c.setFillColorRGB(0, 0, 0)
    y -= 0.3 * inch

    draw_h2("Business Summary")
    draw_bullets(summary, font=11)

    draw_h2("Business Insights")
    for sec, bullets in insights.items():
        if not bullets:
            continue
        c.setFont("Helvetica-Bold", 12)
        if y < 1.2 * inch:
            c.showPage()
            y = h - 0.9 * inch
        c.drawString(x0, y, sec)
        y -= 0.2 * inch
        draw_bullets(bullets, font=11, max_lines=24)

    # charts
    if chart_pngs:
        c.showPage()
        y = h - 0.9 * inch
        draw_h1("Key Charts")
        for chart_title, png in chart_pngs:
            if png is None:
                continue
            if y < 3.3 * inch:
                c.showPage()
                y = h - 0.9 * inch
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x0, y, chart_title)
            y -= 0.15 * inch
            # place image
            img_w = w - 2 * x0
            img_h = 3.0 * inch
            c.drawImage(io.BytesIO(png), x0, y - img_h, width=img_w, height=img_h, preserveAspectRatio=True, anchor='n')
            y -= (img_h + 0.35 * inch)

    c.save()
    buf.seek(0)
    return buf.read()

def make_ppt_pack(title: str, summary: List[str], charts: List[Tuple[str, bytes, str]]) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9
    prs.slide_height = Inches(7.5)

    def add_title(slide, t):
        tx = slide.shapes.add_textbox(Inches(0.7), Inches(0.4), Inches(12.0), Inches(0.7))
        p = tx.text_frame.paragraphs[0]
        p.text = t
        p.font.size = Pt(30)
        p.font.bold = True
        p.font.color.rgb = RGBColor(15, 23, 42)

    def add_bullets(slide, bullets, x, y, w, h, font=18):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.clear()
        for i, b in enumerate(bullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = safe_text(b)
            p.level = 0
            p.font.size = Pt(font)
            p.font.color.rgb = RGBColor(51, 65, 85)

    # Cover
    s0 = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s0, title)
    add_bullets(s0, ["Sales performance, explained clearly.", "Business summary + key charts (Executive Brief v1)."], 0.75, 1.35, 12.0, 1.2, font=18)

    # Summary slide
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s1, "Business Summary")
    add_bullets(s1, summary[:10], 0.75, 1.3, 6.3, 5.7, font=16)

    # Chart slides
    for chart_title, png, comment in charts:
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        add_title(sl, chart_title)
        # commentary
        add_bullets(sl, [comment], 0.75, 1.3, 5.9, 1.5, font=16)
        if png:
            img = io.BytesIO(png)
            sl.shapes.add_picture(img, Inches(0.75), Inches(2.2), width=Inches(12.0), height=Inches(4.9))

    out = io.BytesIO()
    prs.save(out)
    out.seek(0)
    return out.read()

# -------------------------
# UI
# -------------------------
st.title("EC-AI Insight")
st.write("Sales performance, explained clearly.")
st.caption("Upload your sales data and get a short executive brief — what’s working, what’s risky, and where to focus next.")

st.markdown("<hr>", unsafe_allow_html=True)

uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])

with st.expander("Column mapping (only if auto-detection is wrong)", expanded=False):
    st.write("If the app picked the wrong columns, choose them here and re-run.")
    mapping_help = "Tip: revenue should be numeric; date should be a date column."
    st.caption(mapping_help)

df_raw = None
if uploaded is not None:
    try:
        if uploaded.name.lower().endswith(".csv"):
            df_raw = pd.read_csv(uploaded)
        else:
            df_raw = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read file: {e}")

if df_raw is None:
    st.info("Upload a dataset to start.")
    st.stop()

# auto-guess
guess = guess_columns(df_raw)

# mapping UI (optional)
all_cols = list(df_raw.columns)
col_date = st.session_state.get("map_date") or guess["date"] or (all_cols[0] if all_cols else None)
col_revenue = st.session_state.get("map_revenue") or guess["revenue"] or (all_cols[1] if len(all_cols) > 1 else None)

# Use expander controls but keep clean UI
with st.expander("Column mapping (only if auto-detection is wrong)", expanded=False):
    col_date = st.selectbox("Date column", options=all_cols, index=all_cols.index(col_date) if col_date in all_cols else 0, key="map_date")
    col_revenue = st.selectbox("Revenue column", options=all_cols, index=all_cols.index(col_revenue) if col_revenue in all_cols else 0, key="map_revenue")
    col_store = st.selectbox("Store column (optional)", options=["(none)"] + all_cols, index=(["(none)"] + all_cols).index(guess["store"]) if guess["store"] in all_cols else 0, key="map_store")
    col_category = st.selectbox("Category column (optional)", options=["(none)"] + all_cols, index=(["(none)"] + all_cols).index(guess["category"]) if guess["category"] in all_cols else 0, key="map_category")
    col_channel = st.selectbox("Channel column (optional)", options=["(none)"] + all_cols, index=(["(none)"] + all_cols).index(guess["channel"]) if guess["channel"] in all_cols else 0, key="map_channel")
    col_discount = st.selectbox("Discount column (optional)", options=["(none)"] + all_cols, index=(["(none)"] + all_cols).index(guess["discount"]) if guess["discount"] in all_cols else 0, key="map_discount")
    col_cost = st.selectbox("COGS/Cost column (optional)", options=["(none)"] + all_cols, index=(["(none)"] + all_cols).index(guess["cost"]) if guess["cost"] in all_cols else 0, key="map_cost")
    col_qty = st.selectbox("Quantity column (optional)", options=["(none)"] + all_cols, index=(["(none)"] + all_cols).index(guess["qty"]) if guess["qty"] in all_cols else 0, key="map_qty")
    col_unit_price = st.selectbox("Unit price column (optional)", options=["(none)"] + all_cols, index=(["(none)"] + all_cols).index(guess["unit_price"]) if guess["unit_price"] in all_cols else 0, key="map_unit_price")
    col_returned = st.selectbox("Returned flag column (optional)", options=["(none)"] + all_cols, index=(["(none)"] + all_cols).index(guess["returned"]) if guess["returned"] in all_cols else 0, key="map_returned")

def none_to_none(v: str) -> Optional[str]:
    return None if v == "(none)" else v

model = RetailModel(
    col_date=col_date,
    col_revenue=col_revenue,
    col_store=none_to_none(st.session_state.get("map_store", "(none)")),
    col_category=none_to_none(st.session_state.get("map_category", "(none)")),
    col_channel=none_to_none(st.session_state.get("map_channel", "(none)")),
    col_discount=none_to_none(st.session_state.get("map_discount", "(none)")),
    col_cost=none_to_none(st.session_state.get("map_cost", "(none)")),
    col_qty=none_to_none(st.session_state.get("map_qty", "(none)")),
    col_unit_price=none_to_none(st.session_state.get("map_unit_price", "(none)")),
    col_returned=none_to_none(st.session_state.get("map_returned", "(none)")),
)

try:
    df = validate_and_prepare(df_raw, model)
except Exception as e:
    st.error(f"Data load error: {e}")
    st.stop()

core = compute_core(df)
summary = build_business_summary(core)
insights = build_business_insights(core)

# KPI strip
st.markdown('<div class="ec-kpi">', unsafe_allow_html=True)
kpi_html = []
kpi_html.append(f'<div class="k"><div class="t">Total revenue</div><div class="v">{money(core["revenue_total"])}</div></div>')
kpi_html.append(f'<div class="k"><div class="t">Transactions</div><div class="v">{core["n_rows"]:,}</div></div>')
kpi_html.append(f'<div class="k"><div class="t">Days covered</div><div class="v">{core["days"]}</div></div>')
if core.get("gross_margin_pct") is not None and not np.isnan(core["gross_margin_pct"]):
    kpi_html.append(f'<div class="k"><div class="t">Gross margin (est.)</div><div class="v">{pct(core["gross_margin_pct"], 1)}</div></div>')
st.markdown("".join(kpi_html) + "</div>", unsafe_allow_html=True)

# Business Summary
st.markdown('<div class="ec-card">', unsafe_allow_html=True)
st.subheader("Business Summary")
for b in summary:
    st.write("• " + safe_text(b))
st.markdown("</div>", unsafe_allow_html=True)

# Business Insights
st.markdown('<div class="ec-card">', unsafe_allow_html=True)
st.subheader("Business Insights")
for sec, bullets in insights.items():
    st.markdown(f"### {sec}")
    for b in bullets:
        st.write("• " + safe_text(b))
    st.write("")  # spacing
st.markdown("</div>", unsafe_allow_html=True)

# Key charts (fixed set, executive v1)
st.subheader("Key Charts")

charts_for_export: List[Tuple[str, go.Figure, str]] = []

colA, colB = st.columns(2)

with colA:
    if "Store" in df.columns:
        fig, comment = chart_top_stores(df)
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
        st.caption(comment)
        charts_for_export.append(("Top Stores by Revenue", fig, comment))
    fig, comment = chart_revenue_trend(df)
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG)
    st.caption(comment)
    charts_for_export.append(("Revenue Trend", fig, comment))

with colB:
    f, cmt = chart_discount_effect(df)
    if f is not None:
        st.plotly_chart(f, use_container_width=True, config=PLOT_CONFIG)
        st.caption(cmt)
        charts_for_export.append(("Pricing & Discount Effectiveness", f, cmt))
    f, cmt = chart_top_categories(df)
    if f is not None:
        st.plotly_chart(f, use_container_width=True, config=PLOT_CONFIG)
        st.caption(cmt)
        charts_for_export.append(("Top Categories by Revenue", f, cmt))
    f, cmt = chart_channel_mix(df)
    if f is not None:
        st.plotly_chart(f, use_container_width=True, config=PLOT_CONFIG)
        st.caption(cmt)
        charts_for_export.append(("Revenue by Channel", f, cmt))
    f, cmt = chart_store_stability(df)
    if f is not None:
        st.plotly_chart(f, use_container_width=True, config=PLOT_CONFIG)
        st.caption(cmt)
        charts_for_export.append(("Store Volatility", f, cmt))

# Ask EC-AI (no key input shown)
st.subheader("Ask EC-AI")
st.caption("Ask a business question — EC-AI will answer using your uploaded data.")
q1 = st.selectbox("Suggested questions", options=["(choose one)"] + SUGGESTED_QUESTIONS)
free_q = st.text_input("Or ask your own question", value="", placeholder="e.g., Which store is my biggest risk and why?")

question = free_q.strip() if free_q.strip() else (q1 if q1 != "(choose one)" else "")
if question:
    st.markdown('<div class="ec-card">', unsafe_allow_html=True)
    st.markdown(f"**Question:** {safe_text(question)}")
    # Only rule-based for public demo; you can later wire server-side OPENAI_API_KEY
    ans = answer_question_rule_based(question, core)
    st.markdown(safe_text(ans).replace("\n", "<br>"), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Exports
st.subheader("Export")
st.caption("Exports are generated from the same Executive Brief content shown above (summary, insights, key charts).")

col1, col2 = st.columns(2)

with col1:
    if st.button("Generate Executive Brief (PDF)"):
        chart_pngs = []
        for t, fig, _ in charts_for_export[:6]:
            png = fig_to_png_bytes(fig, scale=2)
            if png:
                chart_pngs.append((t, png))
        pdf_bytes = make_exec_brief_pdf("EC-AI Executive Brief", summary, insights, chart_pngs)
        st.download_button("Download PDF", data=pdf_bytes, file_name="ecai_executive_brief_v1.pdf", mime="application/pdf")

with col2:
    if st.button("Generate Insights Pack (PPTX)"):
        chart_items = []
        for t, fig, cmt in charts_for_export[:7]:
            png = fig_to_png_bytes(fig, scale=2)
            chart_items.append((t, png, cmt))
        ppt_bytes = make_ppt_pack("EC-AI Insights Pack", summary, chart_items)
        st.download_button("Download PPTX", data=ppt_bytes, file_name="ecai_insights_pack_v1.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
