# EC-AI Insight — Retail Sales MVP (Founder-first)
# Reconstructed v7 from recovered base
# Notes:
# - Safe Executive Dashboard for demo dataset
# - 3 Executive Insight Cards
# - Charts + commentary
# - Ask AI with suggested questions
# - PDF / PPT export
# - Demo dataset included

import io
import os
import re
import math
import textwrap
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px


LANG = "English"

UI_TEXT = {
    "Executive Summary": {"English": "CEO Decision Summary", "中文": "CEO 決策摘要"},
    "Charts & Insights": {"English": "Charts & Insights", "中文": "圖表與重點"},
    "AI Insights": {"English": "AI Insights", "中文": "AI 分析"},
    "CEO Briefing": {"English": "CEO Briefing", "中文": "CEO 簡報"},
    "Ask AI (CEO Q&A)": {"English": "Ask AI (CEO Q&A)", "中文": "Ask AI（CEO 問答）"},
    "Export Executive Pack": {"English": "Export Executive Pack", "中文": "匯出管理層簡報"},
    "Language / 語言": {"English": "Language / 語言", "中文": "Language / 語言"},
}

def T(key: str) -> str:
    return UI_TEXT.get(key, {}).get(LANG, key)


def L(en: str, zh: str) -> str:
    return zh if LANG == '中文' else en

# Optional: Ask AI chat
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# Optional: PPT export
try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.dml.color import RGBColor
    PPT_AVAILABLE = True
except Exception:
    PPT_AVAILABLE = False

# Optional: PDF export
try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.enums import TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False


# =========================================================
# Page config
# =========================================================
st.set_page_config(page_title="EC-AI Insight", layout="wide")

MAX_UPLOAD_MB = 5
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_PREVIEW_ROWS = 10
MAX_CORR_COLS = 12
SAFE_EXPORT_DEFAULT = 1


# =========================================================
# Global styling
# =========================================================
st.markdown(
    """
<style>
html, body, [class*="css"]  { font-size: 16px; }
p, li { font-size: 16px; line-height: 1.38; margin-bottom: 4px; }
small, .stCaption { font-size: 14px; }

h1 { font-size: 40px !important; margin-bottom: 0.25rem; }
h2 { font-size: 26px !important; margin-top: 1.2rem; }
h3 { font-size: 20px !important; margin-top: 1.0rem; }
h4 { font-size: 18px !important; margin-top: 0.9rem; }

.ec-space { margin-top: 4px; margin-bottom: 4px; }
.ec-tight { margin-top: 2px; margin-bottom: 2px; }
.ec-note { color: #555; font-size: 15px; margin-bottom: 4px; }
.ec-kicker { color: #555; font-size: 18px; }
.ec-subtle { color: #666; font-size: 15px; }

.ec-card {
  border: 1px solid rgba(17,24,39,0.08);
  border-radius: 16px;
  padding: 16px 16px 12px 16px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(17,24,39,0.04);
  min-height: 150px;
}
.ec-card-title {
  font-size: 13px;
  font-weight: 800;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 8px;
}
.ec-card-value {
  font-size: 28px;
  font-weight: 900;
  color: #111827;
  line-height: 1.1;
  margin-bottom: 8px;
}
.ec-card-note {
  font-size: 14px;
  color: #374151;
  line-height: 1.45;
}

.ec-note-box {
  border: 1px solid rgba(17,24,39,0.10);
  border-radius: 16px;
  padding: 16px 18px;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(17,24,39,0.05);
  font-size: 13px;
  color: #374151;
  line-height: 1.45;
}

.ec-insight-card {
  border: 1px solid rgba(17,24,39,0.10);
  border-radius: 16px;
  padding: 16px 18px;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(17,24,39,0.05);
  min-height: 100%;
  margin-top: 8px;
  min-height: 185px;
}
.ec-summary-card {
  border: 1px solid rgba(17,24,39,0.10);
  border-radius: 16px;
  padding: 14px 18px 10px 18px;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(17,24,39,0.05);
  margin-top: 6px;
}
.ec-summary-list { margin: 0; padding-left: 18px; }
.ec-summary-list li { margin-bottom: 3px; }
.ec-insight-section {
  margin-bottom: 6px;
}
.ec-insight-section:last-child {
  margin-bottom: 0;
}
.ec-insight-heading {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 6px;
}
.ec-insight-list {
  margin: 0;
  padding-left: 18px;
}
.ec-insight-list li {
  margin: 0 0 2px 0;
  color: #374151;
}

.ec-ai-answer {
  border: 1px solid rgba(17,24,39,0.08);
  border-radius: 14px;
  padding: 14px 16px;
  background: #ffffff;
  margin-bottom: 10px;
}

.ceo-briefing {
  border: 1px solid rgba(17,24,39,0.08);
  border-radius: 16px;
  padding: 18px 18px 14px 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 2px 8px rgba(17,24,39,0.04);
}
.ceo-briefing-title {
  font-size: 13px;
  font-weight: 800;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 8px;
}
.ceo-briefing-headline {
  font-size: 26px;
  font-weight: 900;
  color: #111827;
  margin-bottom: 10px;
}
.ceo-briefing ul {
  margin: 0.1rem 0 0.2rem 1.1rem;
}
.ceo-briefing li {
  margin-bottom: 0.2rem;
}
.ceo-confidence {
  display: inline-block;
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #EEF2FF;
  color: #1F2937;
  font-size: 12px;
  font-weight: 700;
}

[data-testid="stHorizontalBlock"] div.stButton > button {
  margin-top: 28px;
  height: 42px;
}

.ec-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: #F3F4F6;
  color: #374151;
  font-size: 12px;
  margin: 0 6px 8px 0;
}

.ec-section-title {
  margin: 6px 0 10px 0;
  font-weight: 900;
  font-size: 18px;
  color:#111827;
}

.ec-dashboard-note {
  margin-top: 6px;
  font-size: 12px;
  color:#374151;
  line-height: 1.35;
}

div[data-testid="stExpander"] > details { padding: 0.25rem 0.25rem 0.5rem 0.25rem; }

ul { margin-top: 0.1rem; margin-bottom: 0.35rem; padding-left: 1.15rem; }
li { margin-bottom: 0.15rem; }
h2, h3, h4 { margin-bottom: 0.35rem !important; }

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# Palette
# =========================================================
TABLEAU10 = [
    "#163A5F", "#2A5B84", "#3E7CA6", "#4FA3A5", "#6B7280",
    "#94A3B8", "#CBD5E1", "#E2E8F0", "#2D4F6C", "#7AA6C2"
]

CONSULTING_PALETTE = [
    "#163A5F",  # deep blue
    "#2A5B84",  # mc blue
    "#3E7CA6",  # lighter blue
    "#4FA3A5",  # teal
    "#6B7280",  # dark grey
    "#94A3B8",  # steel grey
    "#CBD5E1",  # light grey
    "#E2E8F0",  # pale grey
]


# =========================================================
# Basic helpers
# =========================================================


# =========================================================
# Export-safe chart label helper
# =========================================================
def export_safe_axis_title(text_en: str | None = None, text_zh: str | None = None) -> str | None:
    """Avoid broken Chinese glyphs on Plotly image exports used in PDF/PPT.
    For Chinese mode, suppress axis titles and rely on chart title + data labels instead.
    """
    if LANG == "中文":
        return None
    return text_en if text_en is not None else text_zh

def clean_display_text(s: str) -> str:
    if not s:
        return s

    raw = str(s).strip()
    low = raw.lower()

    if "persale" in low or "deepdiscount" in low:
        return ""

    s = raw
    s = s.replace("**", "").replace("*", "")
    s = s.replace("`", "").replace("```", "")
    s = s.replace("_", "")
    s = re.sub(r"\\\((.*?)\\\)", "", s)
    s = re.sub(r"\$[^\$]*\$", "", s)
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"[\[\]{}<>]", "", s)
    s = re.sub(r"[\.]{2,}", ".", s)

    letters = sum(ch.isalpha() for ch in s)
    if letters < 4:
        return ""

    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def emphasize_exec_keywords_html(text: str) -> str:
    if not text:
        return text or ""

    text = re.sub(r"(\$[0-9,.]+[KMB]?)", r"<b>\1</b>", text)
    text = re.sub(r"(\d+\.?\d*%)", r"<b>\1</b>", text)
    text = re.sub(r"(#\d+|top \d+)", r"<b>\1</b>", text, flags=re.I)
    text = re.sub(r"((HK|SG|JP|CN)-[A-Za-z0-9]+)", r"<b>\1</b>", text)
    text = re.sub(r"^(Takeaway:)", r"<b>\1</b>", text)
    text = re.sub(r"^(Next focus:)", r"<b>\1</b>", text)
    return text


def clean_col(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())


def fmt_currency(x: float) -> str:
    """Full currency format for executive readability: $86,400 instead of $86.4K."""
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        x = float(x)
    except Exception:
        return "—"
    sign = "-" if x < 0 else ""
    x = abs(x)
    return f"{sign}${x:,.0f}"


def fmt_pct(x: float, digits: int = 0) -> str:
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "—"
        return f"{x*100:.{digits}f}%"
    except Exception:
        return "—"


def _fmt_money(x: float) -> str:
    return fmt_currency(x)


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


def md_to_plain(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = s.replace("**", "")
    return s


def md_to_plain_lines(s: str) -> List[str]:
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


def safe_read_csv(uploaded_file):
    """Read CSV defensively to reduce Streamlit Cloud crashes."""
    if uploaded_file is None:
        return None
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > MAX_UPLOAD_BYTES:
        st.error(L(f"File too large. Please upload a CSV under {MAX_UPLOAD_MB}MB.", f"檔案過大，請上傳小於 {MAX_UPLOAD_MB}MB 的 CSV。"))
        st.stop()
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    try:
        return pd.read_csv(uploaded_file, low_memory=False)
    except Exception:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        return pd.read_csv(uploaded_file, encoding="latin-1", low_memory=False)


def safe_plotly_chart(fig: go.Figure, **kwargs) -> None:
    try:
        st.plotly_chart(fig, **kwargs)
    except Exception as e:
        st.warning(L(f"Chart rendering issue: {e}", f"圖表顯示出現問題：{e}"))


def safe_answer_question_with_openai(question: str, context: str) -> str:
    try:
        return answer_question_with_openai(question, context)
    except Exception as e:
        return L(f"Ask AI is temporarily unavailable: {e}", f"Ask AI 暫時無法使用：{e}")


def safe_download_button(label: str, data: bytes, file_name: str, mime: str, use_container_width: bool = True):
    if not data:
        st.warning(L("Export could not be generated for this selection.", "這次匯出未能成功產生。"))
        return
    st.download_button(label, data=data, file_name=file_name, mime=mime, use_container_width=use_container_width)


# =========================================================
# Column detection
# =========================================================
CANDIDATES = {
    "date": ["date", "orderdate", "transactiondate", "salesdate", "invoice_date", "day"],
    "store": ["store", "store_name", "shop", "branch", "location", "outlet"],
    "revenue": ["revenue", "sales", "amount", "net_sales", "total", "total_sales", "gmv"],
    "category": ["category", "product_category", "dept", "department", "cat"],
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
            for n, orig in norm.items():
                if n == cand_norm or cand_norm in n:
                    out[key] = orig
                    break
            if out[key] is not None:
                break

    if out["revenue"] is None:
        num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            out["revenue"] = num_cols[0]

    return out


# =========================================================
# Data model
# =========================================================
@dataclass
class RetailModel:
    df: pd.DataFrame
    col_date: str
    col_store: str
    col_revenue: str
    col_category: Optional[str] = None
    col_channel: Optional[str] = None
    col_payment: Optional[str] = None
    col_discount: Optional[str] = None
    col_qty: Optional[str] = None


def prep_retail(df_raw: pd.DataFrame) -> RetailModel:
    df = df_raw.copy()
    cols = detect_columns(df)

    if cols["date"] is None:
        raise ValueError("Could not detect a Date column. Please ensure your file includes a date field (e.g., Date, OrderDate).")
    if cols["revenue"] is None:
        raise ValueError("Could not detect a Revenue/Sales column. Please ensure your file includes a numeric revenue field (e.g., Revenue, Sales, Amount).")

    col_date = cols["date"]
    col_store = cols["store"] or "__store__"
    col_revenue = cols["revenue"]

    if cols["store"] is None:
        df[col_store] = "All Stores"

    df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
    df = df.dropna(subset=[col_date])

    df[col_revenue] = pd.to_numeric(df[col_revenue], errors="coerce")
    df = df.dropna(subset=[col_revenue])

    col_qty = cols["qty"]
    if col_qty is not None:
        df[col_qty] = pd.to_numeric(df[col_qty], errors="coerce")

    col_discount = cols["discount"]
    if col_discount is not None:
        df[col_discount] = pd.to_numeric(df[col_discount], errors="coerce")
        s = df[col_discount].dropna()
        if len(s) > 0 and s.quantile(0.95) > 1.5:
            df[col_discount] = df[col_discount] / 100.0
        df[col_discount] = df[col_discount].clip(lower=0, upper=1)

    for k in ["store", "category", "channel", "payment"]:
        c = cols.get(k)
        if c is not None:
            df[c] = df[c].astype(str).str.strip()

    return RetailModel(
        df=df,
        col_date=col_date,
        col_store=col_store,
        col_revenue=col_revenue,
        col_category=cols["category"],
        col_channel=cols["channel"],
        col_payment=cols["payment"],
        col_discount=col_discount,
        col_qty=col_qty,
    )


# =========================================================
# Demo dataset
# =========================================================
def build_demo_dataset(n: int = 900) -> pd.DataFrame:
    rng = np.random.default_rng(42)

    dates = pd.date_range("2025-01-01", periods=120, freq="D")
    stores = ["HK-CWB", "HK-MK", "HK-TST", "HK-KLN", "SG-MBS", "SG-ORC"]
    categories = ["Electronics", "Fashion", "Beauty", "Home", "Sports", "Kids"]
    channels = ["Store", "Online", "Marketplace"]
    payments = ["Visa", "Cash", "Mastercard", "FPS", "AlipayHK"]

    df = pd.DataFrame({
        "Date": rng.choice(dates, size=n),
        "Store": rng.choice(stores, size=n, p=[0.22, 0.18, 0.17, 0.15, 0.15, 0.13]),
        "Category": rng.choice(categories, size=n, p=[0.23, 0.21, 0.16, 0.14, 0.14, 0.12]),
        "Channel": rng.choice(channels, size=n, p=[0.58, 0.28, 0.14]),
        "Payment": rng.choice(payments, size=n),
        "Units": rng.integers(1, 6, size=n),
        "Discount": rng.choice([0, 0.02, 0.05, 0.10, 0.15, 0.25], size=n, p=[0.16, 0.20, 0.24, 0.20, 0.14, 0.06]),
    })

    base_price = {
        "Electronics": 820,
        "Fashion": 330,
        "Beauty": 180,
        "Home": 260,
        "Sports": 290,
        "Kids": 150,
    }

    store_factor = {
        "HK-CWB": 1.22,
        "HK-MK": 1.08,
        "HK-TST": 1.14,
        "HK-KLN": 0.96,
        "SG-MBS": 1.18,
        "SG-ORC": 1.04,
    }

    channel_factor = {
        "Store": 1.00,
        "Online": 0.93,
        "Marketplace": 0.88,
    }

    revenue = []
    cost = []

    for _, row in df.iterrows():
        cat = row["Category"]
        store = row["Store"]
        channel = row["Channel"]
        units = row["Units"]
        disc = row["Discount"]

        raw = base_price[cat] * store_factor[store] * channel_factor[channel]
        demand_noise = rng.normal(1.0, 0.12)
        rev = raw * units * (1 - disc) * demand_noise
        cst = rev * rng.uniform(0.50, 0.72)

        revenue.append(max(rev, 20))
        cost.append(max(cst, 10))

    df["Revenue"] = np.round(revenue, 2)
    df["Cost"] = np.round(cost, 2)
    df["Product"] = df["Category"] + " Item"

    return df.sort_values("Date").reset_index(drop=True)




def build_demo_dataset_2() -> pd.DataFrame:
    rows = [
        ["2025-01-01", "Central", "Electronics", "Store", 12000, 0.05, 40],
        ["2025-01-01", "Central", "Clothing", "Online", 8000, 0.20, 60],
        ["2025-01-01", "Causeway Bay", "Electronics", "Store", 15000, 0.10, 50],
        ["2025-01-01", "Causeway Bay", "Clothing", "Online", 6000, 0.25, 55],
        ["2025-01-02", "Central", "Electronics", "Store", 13000, 0.05, 42],
        ["2025-01-02", "Central", "Clothing", "Online", 7500, 0.20, 58],
        ["2025-01-02", "Causeway Bay", "Electronics", "Store", 16000, 0.10, 52],
        ["2025-01-02", "Causeway Bay", "Clothing", "Online", 5800, 0.30, 60],
        ["2025-01-03", "Central", "Electronics", "Store", 12500, 0.05, 41],
        ["2025-01-03", "Central", "Clothing", "Online", 7000, 0.25, 65],
        ["2025-01-03", "Causeway Bay", "Electronics", "Store", 17000, 0.10, 55],
        ["2025-01-03", "Causeway Bay", "Clothing", "Online", 5500, 0.30, 62],
    ]
    df = pd.DataFrame(rows, columns=["Date", "Store", "Category", "Channel", "Revenue", "Discount", "Transactions"])
    df["Date"] = pd.to_datetime(df["Date"])
    return df


# =========================================================
# Plot helpers
# =========================================================
def _build_unavailable_figure(
    title: str = "Chart unavailable",
    message: str = "This chart needs columns that are not present in the current dataset.",
    *,
    height: int = 320,
) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="center",
        font=dict(size=13, color="#6B7280"),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=24, r=24, t=56, b=24),
        paper_bgcolor="white",
        plot_bgcolor="white",
        title=dict(text=title, x=0.0, xanchor="left", font=dict(size=18, color="#111827")),
        font=dict(family="Inter, Arial, sans-serif", size=13, color="#111827"),
    )
    return fig


def apply_consulting_theme(
    fig: Optional[go.Figure],
    *,
    title: str | None = None,
    height: int | None = None,
    y_is_currency: bool = False,
    y_is_pct: bool = False,
) -> go.Figure:
    if fig is None:
        return _build_unavailable_figure(
            title=title or "Chart unavailable",
            message="This chart is unavailable for the current dataset.",
            height=height or 320,
        )

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
        tickfont=dict(
            family="Inter SemiBold, Inter, Arial, sans-serif",
            size=12,
            color="#374151",
        ),
        gridcolor="rgba(17,24,39,0.07)",
    )

    if y_is_currency:
        fig.update_yaxes(tickprefix="$", tickformat=",.2s")
    elif y_is_pct:
        fig.update_yaxes(tickformat=".0%")

    fig.update_traces(hoverlabel=dict(font_size=12), hovertemplate=None)
    return fig


def line_trend(df: pd.DataFrame, date_col: str, value_col: str, title: str) -> go.Figure:
    daily = df.groupby(pd.Grouper(key=date_col, freq="D"))[value_col].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily[date_col],
            y=daily[value_col],
            mode="lines",
            line=dict(width=3),
            hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>",
        )
    )
    fig = apply_consulting_theme(fig, title=title, height=360, y_is_currency=True)
    fig.update_xaxes(showgrid=False, tickformat="%b %d")
    return fig


def _wrap_axis_label(label: str, width: int = 12) -> str:
    parts = textwrap.wrap(str(label), width=width, break_long_words=False, break_on_hyphens=True)
    return "<br>".join(parts) if parts else str(label)


def bar_categorical(
    x_labels: List[str],
    y_values: List[float],
    title: str,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
    colors: Optional[List[str]] = None,
    text_fmt: str = ",.0f",
    y_is_currency: bool = True,
    label_wrap_width: int = 14,
    tick_angle: int = 0,
) -> go.Figure:
    base_x = [str(v) for v in x_labels]
    wrapped = [_wrap_axis_label(v, width=label_wrap_width) for v in base_x]
    y = [float(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else 0.0 for v in y_values]
    ranked = [f"{i+1}.<br>{lbl}" for i, lbl in enumerate(wrapped)]

    if colors is None:
        leader = CONSULTING_PALETTE[0]
        muted = "#D1D5DB"
        colors = [leader] + [muted] * max(0, len(ranked) - 1)
    else:
        colors = colors[: len(ranked)]

    ymax = max(y) if y else 0.0
    ypad = ymax * 0.16 if ymax > 0 else 1.0

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
            hovertemplate="%{customdata}<br>%{y:,.2f}<extra></extra>",
        )
    )

    fig = apply_consulting_theme(fig, title=title, height=400, y_is_currency=y_is_currency)
    fig.update_layout(bargap=0.78, margin=dict(l=48, r=26, t=62, b=86))

    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=ranked,
        title_text=x_title,
        showgrid=False,
        tickangle=tick_angle,
        automargin=True,
        tickfont=dict(family="Inter SemiBold, Inter, Arial, sans-serif", size=11, color="#111827"),
    )
    fig.update_yaxes(
        title_text=(None if LANG == "中文" else y_title),
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
        title=L("Top Revenue-Generating Stores (Top 5)", "收入最高門店（前 5 名）"),
        y_title=export_safe_axis_title("Revenue", "收入"),
        colors=colors,
        text_fmt=",.0f",
        label_wrap_width=12,
        tick_angle=0,
    )
    fig.update_layout(height=400)
    return fig, dfp


def store_small_multiples(m: RetailModel) -> Tuple[List[go.Figure], List[str]]:
    top = m.df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False).head(5).index.tolist()
    figs = []
    names = []

    for i, store in enumerate(top):
        sub = m.df[m.df[m.col_store] == store]
        daily = sub.groupby(pd.Grouper(key=m.col_date, freq="D"))[m.col_revenue].sum().reset_index()

        fig = go.Figure()
        color = CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)]
        fig.add_trace(
            go.Scatter(
                x=daily[m.col_date],
                y=daily[m.col_revenue],
                mode="lines+markers",
                line=dict(width=3, color=color),
                marker=dict(size=5, color=color),
                hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>",
            )
        )
        fig = apply_consulting_theme(fig, title=(f"門店趨勢 — {store}" if LANG=="中文" else f"Store Trend — {store}"), height=260, y_is_currency=True)
        fig.update_layout(showlegend=False)
        fig.update_xaxes(showgrid=False, tickformat="%b %d")

        figs.append(fig)
        names.append(store)

    return figs, names


def pricing_effectiveness(m: RetailModel) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_discount is None:
        return None

    df = m.df.dropna(subset=[m.col_discount]).copy()
    if len(df) < 6:
        return None

    bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
    labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
    df["Discount Band"] = pd.cut(df[m.col_discount], bins=bins, labels=labels)
    agg = df.groupby("Discount Band", observed=False)[m.col_revenue].mean().reindex(labels)

    dfp = agg.reset_index()
    dfp.columns = ["Discount Band", "Avg Revenue per Sale"]

    fig = bar_categorical(
        x_labels=dfp["Discount Band"].astype(str).tolist(),
        y_values=dfp["Avg Revenue per Sale"].fillna(0).tolist(),
        title=L("Pricing Effectiveness — Avg Revenue per Sale by Discount Level", "定價效果 — 不同折扣水平的平均每張訂單收入"),
        y_title=export_safe_axis_title("Avg Revenue per Sale", "平均每張訂單收入"),
        colors=[CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))],
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
        title=(f"收入按類別（前 {len(dfp)} 名）" if LANG=="中文" else f"Revenue by Category (Top {len(dfp)})"),
        y_title=export_safe_axis_title("Revenue", "收入"),
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
        title=(f"收入按渠道（前 {len(dfp)} 名）" if LANG=="中文" else f"Revenue by Channel (Top {len(dfp)})"),
        y_title=export_safe_axis_title("Revenue", "收入"),
        colors=colors,
        text_fmt=",.0f",
    )
    return fig, dfp


def volatility_by_channel(m: RetailModel) -> Optional[Tuple[go.Figure, pd.DataFrame]]:
    if m.col_channel is None:
        return None

    daily = m.df.groupby([m.col_channel, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    agg = daily.groupby(m.col_channel)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    agg["Volatility"] = agg["std"] / agg["mean"]
    agg = agg.sort_values("Volatility", ascending=False).dropna(subset=["Volatility"])

    if len(agg) == 0:
        return None

    dfp = agg[["Volatility"]].head(8).reset_index()
    dfp.columns = ["Channel", "Stability Variation"]

    colors = [CONSULTING_PALETTE[i % len(CONSULTING_PALETTE)] for i in range(len(dfp))]
    fig = bar_categorical(
        x_labels=dfp["Channel"].tolist(),
        y_values=dfp["Stability Variation"].tolist(),
        title=L("Sales Stability by Channel", "渠道銷售穩定性"),
        y_title=export_safe_axis_title("Variation", "變化幅度"),
        colors=colors,
        text_fmt=",.2f",
        y_is_currency=False,
    )
    return fig, dfp


# =========================================================
# Insights / summaries
# =========================================================

def get_pricing_signal(m: RetailModel) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (signal_label, signal_note, summary_bullet).
    Prefer channel+discount inefficiency when both are available; otherwise fall back to discount-band insight.
    """
    df = m.df.copy()
    if m.col_discount is None or m.col_discount not in df.columns:
        return None, None, None

    tmp = df.dropna(subset=[m.col_discount, m.col_revenue]).copy()
    if len(tmp) < 6:
        return None, None, None

    # First choice: channel-level pricing efficiency
    if m.col_channel and m.col_channel in tmp.columns:
        ch = tmp.groupby(m.col_channel).agg(
            revenue=(m.col_revenue, 'sum'),
            avg_discount=(m.col_discount, 'mean'),
            avg_revenue=(m.col_revenue, 'mean')
        ).sort_values('revenue', ascending=False)
        if len(ch) >= 2:
            high_disc = ch['avg_discount'].idxmax()
            low_disc = ch['avg_discount'].idxmin()
            if (
                ch.loc[high_disc, 'avg_discount'] > ch.loc[low_disc, 'avg_discount'] + 0.03
                and ch.loc[high_disc, 'revenue'] < ch['revenue'].max()
            ):
                label = L('Potential pricing signal', '潛在定價訊號')
                note = L(
                    f"{high_disc} runs the highest average discount ({fmt_pct(float(ch.loc[high_disc, 'avg_discount']), 0)}) but generates less revenue than {ch['revenue'].idxmax()}. This may reflect pricing, channel mix, or scale differences.",
                    f"{high_disc} 的平均折扣最高（{fmt_pct(float(ch.loc[high_disc, 'avg_discount']), 0)}），但收入仍低於 {ch['revenue'].idxmax()}。這可能與定價、渠道組合或規模差異有關。"
                )
                bullet = L(
                    f"{high_disc} shows higher discounting but weaker revenue contribution — a potential pricing signal that needs further validation.",
                    f"{high_disc} 折扣較高但收入貢獻較弱，屬於需要進一步驗證的潛在定價訊號。"
                )
                return label, note, bullet

    # Fallback: discount-band view
    bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
    labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
    tmp['disc_band'] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
    agg = tmp.groupby('disc_band', observed=False)[m.col_revenue].mean().dropna()
    if len(agg) >= 2:
        best_band = str(agg.sort_values(ascending=False).index[0])
        worst_band = str(agg.sort_values(ascending=True).index[0])
        best_avg = float(agg.loc[best_band])
        worst_avg = float(agg.loc[worst_band])
        if worst_avg < best_avg * 0.9:
            label = L('Potential pricing signal', '潛在定價訊號')
            note = L(
                f"{worst_band} discounting underperforms at {fmt_currency(worst_avg)} per order versus {best_band} at {fmt_currency(best_avg)}. This is a potential pricing signal and should be validated against category mix and campaign context.",
                f"{worst_band} 折扣水平的每單收入只有 {fmt_currency(worst_avg)}，低於 {best_band} 的 {fmt_currency(best_avg)}。這屬於潛在定價訊號，仍需結合類別組合及推廣背景作進一步驗證。"
            )
            bullet = L(
                f"Higher discount bands are not translating into stronger revenue per order — a potential pricing signal that needs further validation.",
                f"較高折扣水平未有轉化為更強的每單收入，屬於需要進一步驗證的潛在定價訊號。"
            )
            return label, note, bullet

    return None, None, None

def build_business_summary_points(m: RetailModel) -> List[str]:
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

    df_sorted = df.sort_values(m.col_date)
    mid = df_sorted[m.col_date].min() + pd.Timedelta(days=days / 2)
    rev_first = float(df_sorted.loc[df_sorted[m.col_date] <= mid, m.col_revenue].sum())
    rev_second = float(df_sorted.loc[df_sorted[m.col_date] > mid, m.col_revenue].sum())
    growth = (rev_second - rev_first) / rev_first if rev_first > 0 else np.nan

    daily = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol = daily.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol["ratio"] = vol["std"] / vol["mean"]
    most_volatile_store = str(vol["ratio"].sort_values(ascending=False).index[0]) if len(vol) else None

    _, _, pricing_bullet = get_pricing_signal(m)

    points: List[str] = []
    if LANG == "中文":
        if top_cat is not None and not np.isnan(top_cat_share) and not np.isnan(top_store_share):
            points.append(f"收入高度集中在 **{top_store}** 與 **{top_cat}**，分別佔總收入約 **{fmt_pct(top_store_share, 0)}** 與 **{fmt_pct(top_cat_share, 0)}**。")
        points.append(f"共有 **{days} 日** 數據，**{len(df):,} 筆交易**，總收入 **{fmt_currency(total_rev)}**。")
        if not np.isnan(top_store_share):
            points.append(f"收入集中：**{top_store}** 貢獻 **{fmt_currency(top_store_rev)}**，約佔總收入 **{fmt_pct(top_store_share, 0)}**。")
        if not np.isnan(top2_share) and len(store_rev) >= 3:
            points.append(f"**前兩大門店** 合共帶來 **{fmt_currency(top2_rev)}**，約佔 **{fmt_pct(top2_share, 0)}**。小幅改善已可帶動整體表現。")
        if top_cat is not None and not np.isnan(top_cat_share):
            points.append(f"按類別計，**{top_cat}** 是最大收入來源：**{fmt_currency(top_cat_rev)}**，約佔 **{fmt_pct(top_cat_share, 0)}**。")
        if pricing_bullet:
            points.append(pricing_bullet)
        if not np.isnan(growth):
            if growth > 0.03:
                points.append(f"動能向上：後半段收入比前半段高約 **{fmt_pct(growth, 0)}**。")
            elif growth < -0.03:
                points.append(f"動能轉弱：後半段收入比前半段低約 **{fmt_pct(abs(growth), 0)}**。")
            else:
                points.append("整體收入大致平穩，前後半段沒有明顯變化。")
        if most_volatile_store is not None:
            points.append(f"**{most_volatile_store}** 的日常銷售最不穩定，收入上落比其他門店更明顯。")
        points.append("下一步：先保護及改善頭部門店的庫存、排班與推廣執行，再把有效做法複製到其他門店。")
    else:
        if top_cat is not None and not np.isnan(top_cat_share) and not np.isnan(top_store_share):
            points.append(f"Revenue is highly concentrated in **{top_store}** and **{top_cat}**, which drive about **{fmt_pct(top_store_share, 0)}** and **{fmt_pct(top_cat_share, 0)}** of total revenue respectively.")
        points.append(f"You have **{days} days** of data with **{len(df):,} transactions** (total revenue **{fmt_currency(total_rev)}**).")
        if not np.isnan(top_store_share):
            points.append(f"Revenue is concentrated: **{top_store}** contributes **{fmt_currency(top_store_rev)}** (about **{fmt_pct(top_store_share, 0)}** of total).")
        if not np.isnan(top2_share) and len(store_rev) >= 3:
            points.append(f"The **top 2 stores** together generate **{fmt_currency(top2_rev)}** (about **{fmt_pct(top2_share, 0)}**). Small wins in these locations move the whole business.")
        if top_cat is not None and not np.isnan(top_cat_share):
            points.append(f"By category, **{top_cat}** is your largest driver: **{fmt_currency(top_cat_rev)}** (about **{fmt_pct(top_cat_share, 0)}**).")
        if pricing_bullet:
            points.append(pricing_bullet)
        if not np.isnan(growth):
            if growth > 0.03:
                points.append(f"Momentum is positive: the second half of the period delivered about **{fmt_pct(growth, 0)}** more revenue than the first half.")
            elif growth < -0.03:
                points.append(f"Momentum is softer: the second half of the period delivered about **{fmt_pct(abs(growth), 0)}** less revenue than the first half.")
            else:
                points.append("Overall revenue looks broadly stable across the period (no major shift between first vs second half).")
        if most_volatile_store is not None:
            points.append(f"**{most_volatile_store}** has the most unstable day-to-day sales pattern, with bigger ups and downs than other stores.")
        points.append("Next focus: protect and improve the top stores first availability, staffing, promotion discipline, then scale what works.")
    return points[:12]

def build_business_insights_sections(m: RetailModel) -> Dict[str, List[str]]:
    df = m.df
    total_rev = float(df[m.col_revenue].sum())

    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)
    top_store = str(store_rev.index[0]) if len(store_rev) else "—"
    top_store_rev = float(store_rev.iloc[0]) if len(store_rev) else np.nan
    top2 = store_rev.head(2)
    top2_share = float(top2.sum() / total_rev) if total_rev > 0 and len(top2) else np.nan

    cat_rev = df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False) if m.col_category else pd.Series(dtype=float)
    top_cat = str(cat_rev.index[0]) if len(cat_rev) else None
    top_cat_rev = float(cat_rev.iloc[0]) if len(cat_rev) else np.nan

    channel_rev = df.groupby(m.col_channel)[m.col_revenue].sum().sort_values(ascending=False) if m.col_channel else pd.Series(dtype=float)
    top_channel = str(channel_rev.index[0]) if len(channel_rev) else None
    top_channel_rev = float(channel_rev.iloc[0]) if len(channel_rev) else np.nan

    daily_store = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol_store = daily_store.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol_store["cv"] = vol_store["std"] / vol_store["mean"]
    vol_store = vol_store.dropna(subset=["cv"]).sort_values("cv", ascending=False)
    most_volatile_store = str(vol_store.index[0]) if len(vol_store) else None
    most_volatile_cv = float(vol_store.iloc[0]["cv"]) if len(vol_store) else np.nan

    most_volatile_chan = None
    most_volatile_chan_cv = np.nan
    if m.col_channel:
        daily_chan = df.groupby([m.col_channel, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
        vol_chan = daily_chan.groupby(m.col_channel)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
        vol_chan["cv"] = vol_chan["std"] / vol_chan["mean"]
        vol_chan = vol_chan.dropna(subset=["cv"]).sort_values("cv", ascending=False)
        most_volatile_chan = str(vol_chan.index[0]) if len(vol_chan) else None
        most_volatile_chan_cv = float(vol_chan.iloc[0]["cv"]) if len(vol_chan) else np.nan

    best_band = None
    best_avg = np.nan
    if m.col_discount is not None:
        tmp = df.dropna(subset=[m.col_discount]).copy()
        if len(tmp) >= 6:
            bins = [-0.000001, 0.02, 0.05, 0.10, 0.20, 1.0]
            labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
            tmp["disc_band"] = pd.cut(tmp[m.col_discount], bins=bins, labels=labels)
            agg = tmp.groupby("disc_band", observed=False)[m.col_revenue].mean()
            if agg.notna().sum() >= 2:
                best_band = str(agg.sort_values(ascending=False).index[0])
                best_avg = float(agg.loc[best_band])

    sections: Dict[str, List[str]] = {}
    if LANG == "中文":
        sections["收入來源"] = [
            f"收入主要由少數門店帶動 — **{top_store}** 排名第一，收入 **{fmt_currency(top_store_rev)}**。",
            *( [f"**前兩大門店** 合共貢獻約 **{fmt_pct(top2_share, 0)}** 收入，改善這兩間門店最能帶動整體表現。"] if not np.isnan(top2_share) else [] ),
            *( [f"最大類別：**{top_cat}**，收入 **{fmt_currency(top_cat_rev)}**。"] if top_cat is not None else [] ),
            *( [f"主要渠道：**{top_channel}**，收入 **{fmt_currency(top_channel_rev)}**。"] if top_channel is not None else [] ),
        ]
        risk = []
        if most_volatile_store is not None:
            risk.append(f"穩定性風險：**{most_volatile_store}** 日常銷售最不穩定，變異分數約 **{most_volatile_cv:.2f}**。")
        if most_volatile_chan is not None:
            risk.append(f"渠道波動亦值得留意 — **{most_volatile_chan}** 是最波動的渠道，變異分數約 **{most_volatile_chan_cv:.2f}**。")
        risk.append("集中風險：若收入過度依賴少數門店，該等門店一旦執行失準，整體業務都會受影響。")
        sections["風險所在"] = risk
        improve = []
        if best_band is not None:
            improve.append(f"折扣策略：**{best_band}** 的平均每單收入最好，約 **{fmt_currency(best_avg)}**。")
            improve.append("重點：適度折扣通常比大幅折扣更有效，折扣愈大未必帶來更好結果。")
        improve.append("頭部門店應先做好基本功：庫存、排班及推廣執行。")
        sections["可改善之處"] = improve
        sections["下一步重點"] = [
            f"先在頭部門店（尤其 **{top_store}**）建立簡單有效的營運打法，再複製到其他門店。",
            "先處理波動，再追求增長 — 穩定通常來自營運，而不是更多推廣。",
        ]
    else:
        money = [f"Revenue is driven by a small number of key stores — **{top_store}** is #1 with **{fmt_currency(top_store_rev)}**."]
        if not np.isnan(top2_share):
            money.append(f"The **top 2 stores** contribute about **{fmt_pct(top2_share, 0)}** of total revenue. Improvements here have the biggest impact.")
        if top_cat is not None:
            money.append(f"Top category: **{top_cat}** contributes **{fmt_currency(top_cat_rev)}**.")
        if top_channel is not None:
            money.append(f"Top channel: **{top_channel}** contributes **{fmt_currency(top_channel_rev)}**.")
        sections["Where the money is made"] = money
        risk = []
        if most_volatile_store is not None:
            risk.append(L(f"Predictability risk: **{most_volatile_store}** has the least stable day-to-day sales pattern.", f"穩定性風險：**{most_volatile_store}** 的日常銷售最不穩定。"))
        if most_volatile_chan is not None:
            risk.append(L(f"Channel stability matters too — **{most_volatile_chan}** is the least stable channel.", f"渠道穩定性同樣重要 —— **{most_volatile_chan}** 是最不穩定的渠道。"))
        risk.append("Concentration risk: when most revenue comes from a few stores, execution slips in those locations hit the whole business.")
        sections["Where risk exists"] = risk
        improve = []
        if best_band is not None:
            improve.append(f"The **{best_band}** discount range brings the highest revenue at **{fmt_currency(best_avg)}** per order.")
            improve.append("Takeaway: moderate discounts tend to perform better than aggressive ones — bigger discounts do not automatically lead to better results.")
        improve.append("In top stores, focus on fundamentals first: inventory, staffing, and promotion discipline.")
        sections["What can be improved"] = improve
        sections["What to focus on next"] = [
            f"Run a simple playbook on the top stores starting with **{top_store}** and scale what works.",
            "Fix volatility before chasing growth — stability usually comes from operations, not more campaigns.",
        ]
    return sections


# =========================================================
# Executive cards
# =========================================================
def profile_dataset(df: pd.DataFrame, m: RetailModel) -> Dict[str, object]:
    missing_rate = float(df.isna().mean().mean()) if len(df.columns) else 0.0
    date_days = int(df[m.col_date].nunique()) if m.col_date in df.columns else 0
    return {
        "row_count": int(len(df)),
        "date_days": date_days,
        "missing_rate": missing_rate,
        "has_discount": bool(m.col_discount and m.col_discount in df.columns),
        "has_channel": bool(m.col_channel and m.col_channel in df.columns),
        "has_category": bool(m.col_category and m.col_category in df.columns),
    }


def compute_confidence_score(profile: Dict[str, object]) -> int:
    score = 55
    if int(profile.get("row_count", 0)) >= 500:
        score += 10
    if int(profile.get("date_days", 0)) >= 90:
        score += 10
    if float(profile.get("missing_rate", 1.0)) <= 0.05:
        score += 10
    if bool(profile.get("has_discount")):
        score += 5
    if bool(profile.get("has_channel")):
        score += 5
    if bool(profile.get("has_category")):
        score += 5
    return max(50, min(score, 95))


def detect_insights(m: RetailModel) -> List[Dict[str, object]]:
    df = m.df
    insights: List[Dict[str, object]] = []
    total_rev = float(df[m.col_revenue].sum()) if len(df) else 0.0

    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)
    if len(store_rev) >= 2 and total_rev > 0:
        top1_name, top1_val = str(store_rev.index[0]), float(store_rev.iloc[0])
        top2_name, top2_val = str(store_rev.index[1]), float(store_rev.iloc[1])
        top2_share = (top1_val + top2_val) / total_rev
        if top2_share >= 0.40:
            insights.append({
                "type": "concentration",
                "priority": 1,
                "headline": f"Revenue is concentrated in {top1_name} and {top2_name}.",
                "evidence": [
                    f"{top1_name} and {top2_name} together generate {fmt_currency(top1_val + top2_val)}.",
                    f"That is about {fmt_pct(top2_share, 0)} of total revenue.",
                ],
            })

    if m.col_discount is not None:
        pe = pricing_effectiveness(m)
        if pe is not None:
            _, df_price = pe
            df_price = df_price.dropna(subset=["Avg Revenue per Sale"])
            if len(df_price) >= 2:
                best = df_price.sort_values("Avg Revenue per Sale", ascending=False).iloc[0]
                worst = df_price.sort_values("Avg Revenue per Sale", ascending=True).iloc[0]
                best_val = float(best["Avg Revenue per Sale"])
                worst_val = float(worst["Avg Revenue per Sale"])
                if worst_val < best_val * 0.9:
                    insights.append({
                        "type": "discount",
                        "priority": 2,
                        "headline": "Heavy discounting is hurting revenue per sale.",
                        "evidence": [
                            f"{best['Discount Band']} delivers {fmt_currency(best_val)} per sale.",
                            f"{worst['Discount Band']} delivers only {fmt_currency(worst_val)} per sale.",
                        ],
                    })

    daily = df.groupby([m.col_store, pd.Grouper(key=m.col_date, freq="D")])[m.col_revenue].sum().reset_index()
    vol = daily.groupby(m.col_store)[m.col_revenue].agg(["mean", "std"]).replace(0, np.nan)
    vol["cv"] = vol["std"] / vol["mean"]
    vol = vol.dropna(subset=["cv"]).sort_values("cv", ascending=False)
    if len(vol):
        store = str(vol.index[0])
        score = float(vol.iloc[0]["cv"])
        if score >= 0.70:
            insights.append({
                "type": "volatility",
                "priority": 3,
                "headline": f"{store} has unstable sales.",
                "evidence": [
                    f"{store} has the least stable day-to-day sales pattern in the dataset.",
                    f"Sales there move up and down more than other stores.",
                ],
            })

    if m.col_category is not None and total_rev > 0:
        cat_rev = df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False)
        if len(cat_rev):
            cat = str(cat_rev.index[0])
            share = float(cat_rev.iloc[0] / total_rev)
            if share >= 0.35:
                insights.append({
                    "type": "category",
                    "priority": 4,
                    "headline": f"{cat} is the main revenue driver.",
                    "evidence": [
                        f"{cat} contributes {fmt_currency(float(cat_rev.iloc[0]))}.",
                        f"That is about {fmt_pct(share, 0)} of total revenue.",
                    ],
                })

    df_sorted = df.sort_values(m.col_date)
    if len(df_sorted):
        days = max((df_sorted[m.col_date].max() - df_sorted[m.col_date].min()).days + 1, 1)
        mid = df_sorted[m.col_date].min() + pd.Timedelta(days=days / 2)
        rev_first = float(df_sorted.loc[df_sorted[m.col_date] <= mid, m.col_revenue].sum())
        rev_second = float(df_sorted.loc[df_sorted[m.col_date] > mid, m.col_revenue].sum())
        growth = (rev_second - rev_first) / rev_first if rev_first > 0 else np.nan
        if not np.isnan(growth) and abs(growth) >= 0.05:
            label = "improving" if growth > 0 else "softening"
            insights.append({
                "type": "momentum",
                "priority": 5,
                "headline": f"Revenue momentum is {label}.",
                "evidence": [
                    f"Second half revenue changed by {fmt_pct(growth, 0)} versus the first half.",
                ],
            })

    return sorted(insights, key=lambda x: int(x.get("priority", 99)))


def generate_recommendations(insights: List[Dict[str, object]]) -> List[Dict[str, str]]:
    recs: List[Dict[str, str]] = []
    for ins in insights:
        itype = ins.get("type")
        evidence = ins.get("evidence", [])
        if itype == "concentration":
            recs.append({
                "title": L("Prioritize the top two stores", "優先處理頭兩大門店"),
                "reason": evidence[1] if len(evidence) > 1 else L("A small number of stores drive most revenue.", "少數門店帶來大部分收入。"),
            })
        elif itype == "discount":
            recs.append({
                "title": L("Reduce deep discounting", "減少過深折扣"),
                "reason": evidence[1] if len(evidence) > 1 else L("High discounts are reducing revenue per sale.", "高折扣正在拉低每單收入。"),
            })
        elif itype == "volatility":
            recs.append({
                "title": L("Stabilize the weakest store operations", "先穩定最弱門店的營運"),
                "reason": evidence[0] if evidence else L("One store shows unstable day-to-day sales.", "其中一間門店的日常銷售較不穩定。"),
            })
        elif itype == "category":
            recs.append({
                "title": L("Protect and grow the strongest category", "先守住並擴大最強類別"),
                "reason": evidence[1] if len(evidence) > 1 else L("One category drives a large share of revenue.", "其中一個類別帶來相當大比例的收入。"),
            })
        elif itype == "momentum":
            recs.append({
                "title": L("Review recent momentum and correct early", "及早檢視近期走勢並調整"),
                "reason": evidence[0] if evidence else L("Revenue direction has shifted meaningfully.", "收入走勢已出現明顯變化。"),
            })

    deduped: List[Dict[str, str]] = []
    seen = set()
    for rec in recs:
        if rec["title"] not in seen:
            deduped.append(rec)
            seen.add(rec["title"])
    return deduped[:3]


def generate_priority_actions(m: RetailModel) -> List[Dict[str, str]]:
    insights = detect_insights(m)
    recs = generate_recommendations(insights)
    if len(recs) < 3:
        df = m.df
        total_rev = float(df[m.col_revenue].sum()) if len(df) else 0.0
        if m.col_category is not None and total_rev > 0:
            cat_rev = df.groupby(m.col_category)[m.col_revenue].sum().sort_values(ascending=False)
            if len(cat_rev):
                recs.append({
                    "title": L("Protect the strongest category", "保護最強類別"),
                    "reason": L(f"{cat_rev.index[0]} contributes about {fmt_pct(float(cat_rev.iloc[0] / total_rev), 0)} of revenue.", f"{cat_rev.index[0]} 約佔整體收入 {fmt_pct(float(cat_rev.iloc[0] / total_rev), 0)}。"),
                })
        if len(recs) < 3:
            recs.append({
                "title": L("Keep the top revenue drivers healthy", "先顧好主要收入來源"),
                "reason": L("Focus on stock, staffing, and execution in the best-performing parts of the business.", "先把表現最好的業務部分的庫存、排班和執行做好。"),
            })
    return recs[:3]


def build_ceo_briefing(actions: List[Dict[str, str]], confidence: int) -> Dict[str, object]:
    return {
        "headline": L("Top 3 management actions", "三個最重要管理行動"),
        "actions": actions[:3],
        "confidence": confidence,
    }




def _localize_reason_text(text: str) -> str:
    txt = (text or "").strip()
    if LANG != "中文":
        return txt
    repl = [
        ("That is about ", "約佔"),
        (" of total revenue.", " 的總收入。"),
        ("delivers only ", "只帶來每單收入 "),
        (" per sale.", "。"),
        (" has the least stable day-to-day sales pattern in the dataset.", " 是整個數據集中日常銷售最不穩定的門店。"),
        (" contributes about ", " 約佔 "),
        (" of revenue.", " 的收入。"),
        ("Focus on stock, staffing, and execution in the best-performing parts of the business.", "先把表現最好的業務部分的庫存、排班和執行做好。"),
    ]
    for a,b in repl:
        txt = txt.replace(a,b)
    return txt

def render_summary_card(summary_points: List[str]) -> None:
    bullet_html = "".join(
        f"<li>{emphasize_exec_keywords_html(clean_display_text(p))}</li>"
        for p in summary_points[:8] if clean_display_text(p)
    )
    st.markdown(
        f"""
<div class="ec-summary-card">
  <div class="ec-card-title">{T('Executive Summary')}</div>
  <ul class="ec-summary-list">{bullet_html}</ul>
</div>
""",
        unsafe_allow_html=True,
    )


def render_ceo_briefing(briefing: Dict[str, object]) -> None:
    actions = briefing.get("actions", [])
    lines = []
    for i, item in enumerate(actions, start=1):
        title = emphasize_exec_keywords_html(clean_display_text(item.get("title", "")))
        reason = emphasize_exec_keywords_html(clean_display_text(_localize_reason_text(item.get("reason", ""))))
        lines.append(f"<li><b>{i}. {title}</b><br><span style='color:#4B5563'>{reason}</span></li>")
    actions_html = ''.join(lines)
    st.markdown(f"""
<div class='ceo-briefing'>
  <div class='ceo-briefing-title'>{T('CEO Briefing')}</div>
  <div class='ceo-briefing-headline'>{briefing.get('headline', L('Top management actions', '三個最重要管理行動'))}</div>
  <ul>{actions_html}</ul>
  <div class='ceo-confidence'>{L('Recommendation confidence', '建議可信度')}: {briefing.get('confidence', 0)}%</div>
</div>
""", unsafe_allow_html=True)


def build_exec_cards(m: RetailModel) -> List[Dict[str, str]]:
    df = m.df
    total_rev = float(df[m.col_revenue].sum())
    store_rev = df.groupby(m.col_store)[m.col_revenue].sum().sort_values(ascending=False)

    top_store = str(store_rev.index[0]) if len(store_rev) else "—"
    top_store_rev = float(store_rev.iloc[0]) if len(store_rev) else np.nan
    top_store_share = (top_store_rev / total_rev) if total_rev > 0 and len(store_rev) else np.nan

    df_sorted = df.sort_values(m.col_date)
    dmin, dmax = df_sorted[m.col_date].min(), df_sorted[m.col_date].max()
    days = max((dmax - dmin).days + 1, 1)
    mid = df_sorted[m.col_date].min() + pd.Timedelta(days=days / 2)
    rev_first = float(df_sorted.loc[df_sorted[m.col_date] <= mid, m.col_revenue].sum())
    rev_second = float(df_sorted.loc[df_sorted[m.col_date] > mid, m.col_revenue].sum())
    growth = (rev_second - rev_first) / rev_first if rev_first > 0 else np.nan

    growth_label = L("Stable", "平穩")
    if not np.isnan(growth):
        if growth > 0.03:
            growth_label = L("Positive", "向上")
        elif growth < -0.03:
            growth_label = L("Softer", "轉弱")

    pricing_label, pricing_note, _ = get_pricing_signal(m)

    cards = [
        {
            "title": L("Revenue Concentration", "收入集中度"),
            "value": fmt_currency(top_store_rev) if not np.isnan(top_store_rev) else "—",
            "note": L(f"{top_store} is the leading store at about {fmt_pct(top_store_share, 0)} of total revenue.", f"{top_store} 是領先門店，約佔總收入 {fmt_pct(top_store_share, 0)}。") if not np.isnan(top_store_share) else L("Top store concentration unavailable.", "未能判斷頭部門店集中度。"),
        },
        {
            "title": L("Momentum", "動能"),
            "value": growth_label,
            "note": L(f"Second half vs first half: {fmt_pct(growth, 0)}.", f"後半段對比前半段：{fmt_pct(growth, 0)}。") if not np.isnan(growth) else L("Not enough information to assess momentum.", "資料不足，未能判斷動能。"),
        },
        {
            "title": L("Pricing Signal", "定價訊號"),
            "value": pricing_label or "N/A",
            "note": pricing_note or L("Discount signal unavailable for this dataset.", "這份數據未能判斷折扣訊號。"),
        },
    ]
    return cards

def render_parallel_insight_cards(cards: List[Dict[str, str]]) -> None:
    cols = st.columns(3, gap="small")
    for i, card in enumerate(cards[:3]):
        with cols[i]:
            st.markdown(
                f"""
<div class="ec-card">
  <div class="ec-card-title">{card.get("title","")}</div>
  <div class="ec-card-value">{card.get("value","")}</div>
  <div class="ec-card-note">{card.get("note","")}</div>
</div>
""",
                unsafe_allow_html=True,
            )


# =========================================================
# Commentary block
# =========================================================
def _html_bullets(items) -> str:
    rows = []
    for item in (items or []):
        _t = clean_display_text(item)
        if _t:
            rows.append(f"<li>{emphasize_exec_keywords_html(_t)}</li>")
    return "".join(rows)


def render_insight_card(what_points=None, why_points=None, todo_points=None) -> None:
    what_html = _html_bullets(what_points)
    why_html = _html_bullets(why_points)
    todo_html = _html_bullets(todo_points)

    st.markdown(
        f"""
<div class='ec-insight-card'>
  <div class='ec-insight-section'>
    <div class='ec-insight-heading'>{L('What this shows', '這張圖顯示什麼')}</div>
    <ul class='ec-insight-list'>{what_html}</ul>
  </div>
  <div class='ec-insight-section'>
    <div class='ec-insight-heading'>{L('Why it matters', '為什麼重要')}</div>
    <ul class='ec-insight-list'>{why_html}</ul>
  </div>
  <div class='ec-insight-section'>
    <div class='ec-insight-heading'>{L('What to do', '應採取什麼行動')}</div>
    <ul class='ec-insight-list'>{todo_html}</ul>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def insight_block(what_points=None, why_points=None, todo_points=None) -> None:
    render_insight_card(what_points=what_points, why_points=why_points, todo_points=todo_points)


def render_chart_with_commentary(
    fig: go.Figure,
    *,
    what_points=None,
    why_points=None,
    todo_points=None,
    boxed_commentary: bool = True,
    left_ratio: int = 2,
    right_ratio: int = 1,
    height: Optional[int] = None,
):
    what_points = what_points or []
    why_points = why_points or []
    todo_points = todo_points or []

    col_l, col_r = st.columns([left_ratio, right_ratio], gap="large")
    with col_l:
        try:
            if height is not None:
                fig.update_layout(height=height)
        except Exception:
            pass
        safe_plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_r:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        render_insight_card(what_points=what_points, why_points=why_points, todo_points=todo_points)


# =========================================================
# Ask AI
# =========================================================
def _get_openai_api_key() -> str | None:
    try:
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY")


def get_api_key() -> str | None:
    return _get_openai_api_key()


def _build_ai_context(df: pd.DataFrame, m: RetailModel) -> str:
    if df is None or df.empty:
        return "No dataset loaded."

    col_date = m.col_date
    col_rev = m.col_revenue
    col_store = m.col_store
    col_cat = m.col_category
    col_channel = m.col_channel
    col_disc = m.col_discount

    overview_lines = []
    n_rows = len(df)

    d = pd.to_datetime(df[col_date], errors="coerce")
    date_min = d.min()
    date_max = d.max()
    n_days = int((date_max - date_min).days) + 1 if pd.notna(date_min) and pd.notna(date_max) else None

    total_rev = float(pd.to_numeric(df[col_rev], errors="coerce").fillna(0).sum())

    overview_lines.append(f"Rows: {n_rows}")
    overview_lines.append(f"Date range: {date_min.date()} to {date_max.date()} ({n_days} days)" if n_days is not None else "Date range: N/A")
    overview_lines.append(f"Total revenue: {_fmt_money(total_rev)}")

    def top_contrib(col_name: Optional[str], top_n: int = 5):
        if not (col_name and col_name in df.columns and col_rev in df.columns):
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

    discount_lines = []
    if col_disc and col_disc in df.columns:
        tmp2 = df[[col_disc, col_rev]].copy()
        tmp2[col_rev] = pd.to_numeric(tmp2[col_rev], errors="coerce").fillna(0)
        disc_num = pd.to_numeric(tmp2[col_disc], errors="coerce")
        bins = [-float("inf"), 0.02, 0.05, 0.10, 0.20, float("inf")]
        labels = ["0–2%", "2–5%", "5–10%", "10–20%", "20%+"]
        tmp2["discount_band"] = pd.cut(disc_num, bins=bins, labels=labels)
        g = tmp2.groupby("discount_band", observed=False)[col_rev].agg(["mean", "count"]).reset_index()
        g = g.dropna(subset=["discount_band"]).sort_values("mean", ascending=False)
        if not g.empty:
            for _, r in g.head(5).iterrows():
                discount_lines.append(f"{r['discount_band']}: avg {_fmt_money(r['mean'])} (n={int(r['count'])})")

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
    api_key = get_api_key()
    if not api_key:
        return L("OpenAI API key not configured. Add OPENAI_API_KEY in Streamlit secrets.", "未設定 OpenAI API key，請在 Streamlit secrets 加入 OPENAI_API_KEY。")
    if OpenAI is None:
        return L("OpenAI SDK not installed. Add 'openai' to requirements.txt.", "未安裝 OpenAI SDK，請在 requirements.txt 加入 openai。")

    q = (question or "").strip()
    if not q:
        return L("Please enter a question.", "請先輸入問題。")

    q_lower = q.lower()
    if LANG == "中文":
        base_style = "請用繁體中文回答，語氣要簡單、直接、像香港中小企老闆看得明的管理建議。避免學術語氣，避免太多術語。所有答案都要用短句。若適合，先給一句直接答案，再用2至3點重點，最後列出管理層應做的事。務必引用數字。"
        if any(k in q_lower for k in ["how can i improve", "improve my business", "top 3", "three actions", "management action", "management actions", "what should management", "focus on next", "改善業務", "三個", "管理行動", "優先", "下一步"]):
            answer_style = "先用一句話直接回答，然後列出剛好3個管理行動。每個行動下面只用一句原因，並引用一個實際數字。"
        elif any(k in q_lower for k in ["why", "explain", "what explains", "driver", "drivers", "underperforming", "原因", "解釋", "表現", "風險"]):
            answer_style = "先直接說答案，再用2至3點列出證據。不要用學術語言。"
        else:
            answer_style = "用簡單管理語言回答，短句、易讀、可執行。"
    else:
        base_style = "Answer in simple, clear business English for a non-technical CEO. Use short sentences and real numbers from the dataset."
        if any(k in q_lower for k in ["how can i improve", "improve my business", "top 3", "three actions", "management action", "management actions", "what should management", "focus on next", "改善業務", "三個", "管理行動", "優先", "下一步"]):
            answer_style = "Use simple business language. Start with one short direct answer. Then show exactly 3 numbered actions. Each action should have one short reason with a real number from the dataset. Keep sentences short and easy to scan. Avoid academic words and avoid the headings Key Insight, Business Meaning, or Recommended Action."
        elif any(k in q_lower for k in ["why", "explain", "what explains", "driver", "drivers", "underperforming", "原因", "解釋", "表現", "風險"]):
            answer_style = "Use simple business language. Start with the direct answer in 1-2 sentences, then add 2-3 bullets with plain-English evidence. Avoid jargon and repetitive template headings."
        elif any(k in q_lower for k in ["which", "compare", "better", "worse", "largest", "smallest"]):
            answer_style = "Give the answer first in one sentence, then show the comparison using the most relevant numbers. Keep words short and clear."
        else:
            answer_style = "Answer in a simple, human, executive tone. Use short sentences, easy words, and practical management language."

    try:
        client = OpenAI(api_key=api_key)
        system = (context or "").strip() + "\n\n" + base_style
        user = f"Question:\n{q}\n\nInstructions:\n- Answer using ONLY the dataset facts in the system context.\n- Always cite numbers ($, %, dates) from the context when relevant.\n- If the context lacks required info, say what is missing (which column/metric).\n- {answer_style}"
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=420,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        response_text = (resp.choices[0].message.content or "").strip()
        return response_text or L("No response.", "沒有回應。")
    except Exception as e:
        return f"Ask AI error: {e}"



def render_structured_ai_answer(answer: str) -> None:
    """Render AI answer safely; keep simple and support bold markdown."""
    txt = (answer or "").strip()
    if not txt:
        return
    # normalize bullets for readability
    txt = txt.replace("•", "- ")
    st.markdown(txt)


# =========================================================
# Exports
# =========================================================
def fig_to_png_bytes(fig: go.Figure, scale: int = 2) -> bytes:
    export_fig = go.Figure(fig)
    try:
        export_fig.update_layout(title=None, title_text=None, margin=dict(t=20))
    except Exception:
        pass
    try:
        return export_fig.to_image(format="png", scale=scale)
    except Exception:
        return b""


def build_pdf_exec_brief(
    title: str,
    subtitle: str,
    summary_points: List[str],
    chart_items: List[Tuple[str, go.Figure, str]],
) -> bytes:
    if not PDF_AVAILABLE:
        raise RuntimeError("ReportLab is not installed. Add reportlab to requirements.txt.")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    cjk_font = None
    if LANG == "中文":
        try:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            cjk_font = "STSong-Light"
        except Exception:
            cjk_font = None
    body_font = cjk_font or "Helvetica"
    title_font = cjk_font or "Helvetica-Bold"
    styles.add(ParagraphStyle(name="ECBody", parent=styles["BodyText"], fontName=body_font, fontSize=11, leading=13, textColor="#374151"))
    styles.add(ParagraphStyle(name="ECTitle", parent=styles["Title"], fontName=title_font, fontSize=20, leading=22, alignment=TA_LEFT, textColor="#163A5F"))
    styles.add(ParagraphStyle(name="ECSub", parent=styles["BodyText"], fontName=body_font, fontSize=12, leading=14, textColor="#4B5563"))

    story = []
    story.append(Paragraph(title, styles["ECTitle"]))
    story.append(Paragraph(subtitle, styles["ECSub"]))
    story.append(Spacer(1, 0.04 * inch))

    story.append(Paragraph(f"<b>{L('Executive Summary', '執行摘要')}</b>", styles["ECBody"]))
    if summary_points:
        first_three = [md_to_plain(clean_display_text(p)) for p in summary_points[:3] if clean_display_text(p)]
        for p in first_three:
            story.append(Paragraph(f"• {p}", styles["ECBody"]))
        story.append(Spacer(1, 0.10*inch))
        story.append(Paragraph(f"<b>{L('Detailed observations', '詳細觀察')}</b>", styles["ECBody"]))
    for p in summary_points[3:12]:
        _t = md_to_plain(p)
        _t = clean_display_text(_t)
        if _t:
            story.append(Paragraph(f"• {_t}", styles["ECBody"]))
    story.append(Spacer(1, 0.04 * inch))

    story.append(Paragraph(f"<b>{L('Key Charts & Commentary', '重點圖表與解讀')}</b>", styles["ECBody"]))
    story.append(Spacer(1, 0.06 * inch))

    for (ctitle, fig, commentary) in chart_items:
        story.append(Paragraph(f"<b>{ctitle}</b>", styles["ECBody"]))
        if commentary:
            for line in md_to_plain_lines(commentary):
                story.append(Paragraph(f"• {line}", styles["ECBody"]))
        story.append(Spacer(1, 0.04 * inch))
        png = fig_to_png_bytes(fig, scale=SAFE_EXPORT_DEFAULT)
        if png:
            img_buf = io.BytesIO(png)
            img = RLImage(img_buf, width=6.7 * inch, height=3.2 * inch)
            story.append(img)
            story.append(Spacer(1, 0.10 * inch))
        else:
            story.append(Paragraph(L("Chart image export unavailable for this chart.", "此圖表暫時無法匯出圖片。"), styles["ECBody"]))
            story.append(Spacer(1, 0.10 * inch))

    doc.build(story)
    return buf.getvalue()


def _ppt_add_textbox(slide, left, top, width, height, text, font_size=18, bold=False, color=(17,24,39)):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    try:
        tf.margin_left = Pt(2)
        tf.margin_right = Pt(2)
        tf.margin_top = Pt(1)
        tf.margin_bottom = Pt(1)
    except Exception:
        pass
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = RGBColor(*color)
    try:
        p.font.name = "Microsoft JhengHei" if LANG == "中文" else "Aptos"
    except Exception:
        pass
    try:
        p.space_after = Pt(2)
        p.space_before = Pt(0)
        p.line_spacing = 1.0
    except Exception:
        pass
    return box


def _ppt_add_filled_box(slide, left, top, width, height, fill_rgb, line_rgb=(229,231,235), radius=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(*fill_rgb)
    shape.line.color.rgb = RGBColor(*line_rgb)
    return shape


def _ppt_clip_text(text: str, max_chars: int = 150) -> str:
    text = md_to_plain(clean_display_text(text or ""))
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def build_ppt_talking_deck(
    deck_title: str,
    chart_items: List[Tuple[str, go.Figure, str]],
    summary_points: Optional[List[str]] = None,
    exec_cards: Optional[List[Dict[str, str]]] = None,
) -> bytes:
    if not PPT_AVAILABLE:
        raise RuntimeError("python-pptx is not installed. Add python-pptx to requirements.txt.")

    summary_points = summary_points or []
    exec_cards = exec_cards or []

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _ppt_add_filled_box(slide, 0, 0, 13.333, 7.5, (245,247,250), line_rgb=(245,247,250))
    _ppt_add_filled_box(slide, 0.0, 0.0, 13.333, 0.45, (11,31,59), line_rgb=(11,31,59))
    _ppt_add_textbox(slide, 0.8, 1.0, 11.5, 0.8, deck_title, font_size=28, bold=True, color=(11,31,59))
    _ppt_add_textbox(slide, 0.8, 1.9, 10.5, 0.5, L("Executive storyline deck", "管理層故事線簡報"), font_size=16, color=(75,85,99))
    _ppt_add_textbox(slide, 0.8, 2.8, 11.0, 1.1, L("This pack highlights where revenue is made, where performance is fragile, and what management should do next.", "這份簡報重點說明收入來源、表現脆弱點，以及管理層下一步應做什麼。"), font_size=18, color=(31,41,55))

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _ppt_add_textbox(slide, 0.6, 0.35, 12.0, 0.5, L("CEO Decision Summary", "CEO 決策摘要"), font_size=24, bold=True, color=(17,24,39))
    _ppt_add_textbox(slide, 0.6, 0.8, 12.0, 0.3, L("Headline messages management can act on immediately", "管理層可立即採取行動的重點信息"), font_size=12, color=(107,114,128))
    card_lefts = [0.6, 4.45, 8.3]
    for i, card in enumerate(exec_cards[:3]):
        _ppt_add_filled_box(slide, card_lefts[i], 1.25, 3.35, 1.65, (255,255,255), line_rgb=(229,231,235), radius=True)
        _ppt_add_textbox(slide, card_lefts[i]+0.18, 1.42, 3.0, 0.25, str(card.get("title","")), font_size=10, bold=True, color=(107,114,128))
        _ppt_add_textbox(slide, card_lefts[i]+0.18, 1.72, 3.0, 0.45, str(card.get("value","")), font_size=21, bold=True, color=(17,24,39))
        _ppt_add_textbox(slide, card_lefts[i]+0.18, 2.18, 3.0, 0.55, _ppt_clip_text(str(card.get("note","")), 120), font_size=10.5, color=(55,65,81))

    _ppt_add_filled_box(slide, 0.6, 3.2, 12.1, 3.6, (255,255,255), line_rgb=(229,231,235), radius=True)
    _ppt_add_textbox(slide, 0.85, 3.42, 4.0, 0.3, L("What management should know", "管理層應知道的重點"), font_size=13, bold=True, color=(17,24,39))
    y = 3.78
    for point in summary_points[:6]:
        txt = _ppt_clip_text(point, 150)
        if txt:
            _ppt_add_textbox(slide, 0.95, y, 11.2, 0.38, u"• " + txt, font_size=12.5, color=(31,41,55))
            y += 0.48

    for idx, (ctitle, fig, bullets) in enumerate(chart_items, start=1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        _ppt_add_textbox(slide, 0.55, 0.28, 12.1, 0.42, ctitle, font_size=21, bold=True, color=(17,24,39))

        raw_lines = [md_to_plain(l).strip().lstrip("-• ").strip() for l in str(bullets).split("\n") if str(l).strip()]
        what = raw_lines[0] if len(raw_lines) > 0 else "This chart highlights the main commercial pattern in the data."
        why = raw_lines[1] if len(raw_lines) > 1 else "This matters because management attention should follow the areas with the largest commercial impact."
        action = raw_lines[2] if len(raw_lines) > 2 else L("Prioritise the most important driver first, then scale what works.", "先集中處理最重要的驅動因素，再把有效做法擴大。")
        observation = raw_lines[3] if len(raw_lines) > 3 else L("Identify the main driver, any spikes, and the key management lever.", "先找出主要驅動因素、任何明顯波動，以及最關鍵的管理槓桿。")

        _ppt_add_filled_box(slide, 0.55, 0.82, 12.1, 0.52, (243,244,246), line_rgb=(229,231,235), radius=True)
        _ppt_add_textbox(slide, 0.72, 0.98, 11.8, 0.2, f"{L("Headline takeaway", "頁面重點")}: {_ppt_clip_text(what, 135)}", font_size=11.5, bold=True, color=(17,24,39))

        png = fig_to_png_bytes(fig, scale=SAFE_EXPORT_DEFAULT)
        if png:
            img_stream = io.BytesIO(png)
            slide.shapes.add_picture(img_stream, Inches(0.55), Inches(1.55), width=Inches(7.0), height=Inches(4.5))
        else:
            _ppt_add_textbox(slide, 0.8, 2.4, 6.5, 0.6, L("Chart image export unavailable.", "圖表圖片暫時無法匯出。"), font_size=16, color=(107,114,128))

        _ppt_add_filled_box(slide, 7.85, 1.55, 4.85, 4.75, (255,255,255), line_rgb=(229,231,235), radius=True)
        _ppt_add_textbox(slide, 8.1, 1.78, 4.3, 0.22, L("What this shows", "這張圖顯示什麼"), font_size=12, bold=True, color=(17,24,39))
        _ppt_add_textbox(slide, 8.12, 2.02, 4.2, 0.58, u"• " + _ppt_clip_text(what, 145), font_size=10.5, color=(55,65,81))

        _ppt_add_textbox(slide, 8.1, 2.68, 4.3, 0.22, L("Why it matters", "為什麼重要"), font_size=12, bold=True, color=(17,24,39))
        _ppt_add_textbox(slide, 8.12, 2.92, 4.2, 0.72, u"• " + _ppt_clip_text(why, 170), font_size=10.5, color=(55,65,81))

        _ppt_add_textbox(slide, 8.1, 3.74, 4.3, 0.22, L("What to do", "應採取什麼行動"), font_size=12, bold=True, color=(17,24,39))
        _ppt_add_textbox(slide, 8.12, 3.98, 4.2, 0.72, u"• " + _ppt_clip_text(action, 170), font_size=10.5, color=(55,65,81))

        _ppt_add_filled_box(slide, 8.02, 4.92, 4.55, 1.18, (248,250,252), line_rgb=(229,231,235), radius=True)
        _ppt_add_textbox(slide, 8.24, 5.14, 4.0, 0.18, L("Key observation", "關鍵觀察"), font_size=11.5, bold=True, color=(17,24,39))
        _ppt_add_textbox(slide, 8.24, 5.34, 4.12, 0.62, _ppt_clip_text(observation, 100), font_size=9.2, color=(55,65,81))

        _ppt_add_textbox(slide, 0.58, 6.3, 12.0, 0.24, f"{L("Slide", "第")} {idx + 2} {L("| EC-AI Insight", "頁 | EC-AI Insight")}", font_size=9, color=(107,114,128))

    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


# =========================================================
# Executive dashboard
# =========================================================
def _dash_note(md: str) -> None:
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md)
    st.markdown(f"<div class='ec-dashboard-note'>{html}</div>", unsafe_allow_html=True)


def render_onepager_dashboard(m: RetailModel, df: pd.DataFrame) -> dict:
    st.markdown(f"<div class='ec-section-title'>{L("Executive Dashboard", "管理儀表板")}</div>", unsafe_allow_html=True)

    def _as_fig(obj):
        return obj[0] if isinstance(obj, tuple) and len(obj) else obj

    def _note_for_chart(fig, normal_note: str, fallback_note: str) -> str:
        return fallback_note if fig is None else normal_note

    fig_trend_raw = line_trend(df, m.col_date, m.col_revenue, "Revenue Trend (Daily)")
    fig_trend = apply_consulting_theme(fig_trend_raw, title=L("Revenue Trend (Daily)", "收入趨勢（每日）"), height=320, y_is_currency=True)

    fig_topstores_raw, df_top = top5_stores_bar(m)
    fig_topstores = apply_consulting_theme(fig_topstores_raw, title=L("Top Stores (Top 5)", "收入最高門店（前 5 名）"), height=320, y_is_currency=True)
    top_store = df_top.iloc[0]["Store"] if len(df_top) else "Top store"

    fig_cat_raw = _as_fig(revenue_by_category(m, topn=5))
    fig_cat = apply_consulting_theme(fig_cat_raw, title=L("Revenue by Category (Top 5)", "收入按類別（前 5 名）"), height=320, y_is_currency=True)

    fig_price_raw = _as_fig(pricing_effectiveness(m))
    fig_price = apply_consulting_theme(fig_price_raw, title=L("Pricing Effectiveness", "定價效果"), height=320, y_is_currency=True)

    fig_channel_raw = _as_fig(revenue_by_channel(m, topn=3))
    fig_channel = apply_consulting_theme(fig_channel_raw, title=L("Revenue by Channel (Top 3)", "收入按渠道（前 3 名）"), height=320, y_is_currency=True)

    fig_vol_raw = _as_fig(volatility_by_channel(m))
    fig_vol = apply_consulting_theme(fig_vol_raw, title=L("Sales Stability by Channel", "渠道銷售穩定性"), height=320, y_is_currency=False)

    r1 = st.columns(3, gap="small")
    with r1[0]:
        with st.container(border=True):
            safe_plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})
            _dash_note(L("Protect **momentum**; investigate spikes and dips.", "保護**動能**；留意高低波動。"))
    with r1[1]:
        with st.container(border=True):
            safe_plotly_chart(fig_topstores, use_container_width=True, config={"displayModeBar": False})
            _dash_note(L(f"Revenue is concentrated — prioritise **{top_store}** and top drivers.", f"收入集中 — 優先處理 **{top_store}** 及主要收入來源。"))
    with r1[2]:
        with st.container(border=True):
            safe_plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})
            _dash_note(_note_for_chart(
                fig_cat_raw,
                "Double down on **top categories**; fix weak lines.",
                "Category insight unavailable — this dataset may not include a usable category field.",
            ))

    r2 = st.columns(3, gap="small")
    with r2[0]:
        with st.container(border=True):
            safe_plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})
            _dash_note(_note_for_chart(
                fig_price_raw,
                "Use **pricing discipline**; moderate discounts can outperform aggressive ones.",
                "Pricing insight unavailable — this dataset does not include a usable discount column.",
            ))
    with r2[1]:
        with st.container(border=True):
            safe_plotly_chart(fig_channel, use_container_width=True, config={"displayModeBar": False})
            _dash_note(_note_for_chart(
                fig_channel_raw,
                "Reallocate effort to channels that **convert**; fix weakest channel.",
                "Channel insight unavailable — this dataset does not include a usable channel column.",
            ))
    with r2[2]:
        with st.container(border=True):
            safe_plotly_chart(fig_vol, use_container_width=True, config={"displayModeBar": False})
            _dash_note(_note_for_chart(
                fig_vol_raw,
                "Improve stability: focus on channels with the biggest day-to-day swings.",
                "Volatility-by-channel unavailable — this dataset does not include a usable channel column.",
            ))

    return {
        "Revenue Trend (Daily)": fig_trend,
        L("Top Stores (Top 5)", "收入最高門店（前 5 名）"): fig_topstores,
        L("Revenue by Category (Top 5)", "收入按類別（前 5 名）"): fig_cat,
        L("Pricing Effectiveness", "定價效果"): fig_price,
        L("Revenue by Channel (Top 3)", "收入按渠道（前 3 名）"): fig_channel,
        L("Sales Stability by Channel", "渠道銷售穩定性"): fig_vol,
    }


def render_questions_this_answers():
    st.markdown(f"### {L('What questions this answers', '這份分析回答什麼問題')}")
    st.markdown(
        f"""
<div class="ec-summary-card">
  <ul class="ec-summary-list">
    <li>{L("What’s driving my revenue?", "什麼在帶動我的收入？")}</li>
    <li>{L("Which part of the business is underperforming?", "哪一部分業務表現較弱？")}</li>
    <li>{L("Where might I be losing money or efficiency?", "哪裡可能正在流失收入或效率？")}</li>
    <li>{L("What should I do next?", "下一步應該做什麼？")}</li>
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )


# =========================================================
# Main app
# =========================================================
with st.sidebar:
    LANG = st.selectbox(T("Language / 語言"), ["English", "中文"], index=0)

st.title("EC-AI Insight")
st.markdown(f"<div class='ec-kicker'>{L('Know what’s happening, what’s working, and what to do next — in seconds.', '即時掌握正在發生什麼、哪些做法有效，以及下一步該做什麼。')}</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='ec-subtle'>{L('Turn raw business data into clear answers for executives, owners, and decision makers.', '把原始業務數據轉化為管理層、老闆和決策者可直接採用的清晰答案。')}</div>",
    unsafe_allow_html=True
)
st.divider()

with st.sidebar:
    st.header(L("Data Source", "資料來源"))
    if "use_demo_dataset" not in st.session_state:
        st.session_state.use_demo_dataset = False
    if "demo_dataset_choice" not in st.session_state:
        st.session_state.demo_dataset_choice = 1

    up = st.file_uploader(L("Upload CSV", "上傳 CSV"), type=["csv"])
    if up is not None:
        st.session_state.use_demo_dataset = False

    if st.button(L("🚀 Try Demo Dataset 1 (Retail Fashion, HK)", "🚀 使用示範數據 1（香港零售時裝）"), use_container_width=True):
        st.session_state.use_demo_dataset = True
        st.session_state.demo_dataset_choice = 1

    if st.button(L("🚀 Try Demo Dataset 2 (Sales & Channel Strategy)", "🚀 使用示範數據 2（銷售與渠道策略）"), use_container_width=True):
        st.session_state.use_demo_dataset = True
        st.session_state.demo_dataset_choice = 2

    if st.session_state.use_demo_dataset:
        if st.session_state.get("demo_dataset_choice", 1) == 2:
            st.caption(L("Using demo dataset 2: advanced business insights for channel strategy.", "正在使用示範數據 2：較進階的渠道策略商業洞察。"))
        else:
            st.caption(L("Using demo dataset 1: built-in retail fashion dataset.", "正在使用示範數據 1：內置零售時裝示範數據。"))
    else:
        st.caption(L("Tip: first load on Streamlit Cloud may take 30–60 seconds if the app was asleep.", "提示：若 Streamlit Cloud 之前休眠，首次載入可能需要 30–60 秒。"))

    st.header(L("Exports", "匯出"))
    export_scale = st.slider(L("Export image scale", "匯出圖像清晰度"), min_value=1, max_value=3, value=2, help=L("Higher = clearer charts, but slower exports.", "數值越高，圖像越清晰，但匯出會較慢。"))

    st.header(L("Diagnostics", "診斷資訊"))
    try:
        import plotly
        import importlib.util
        st.write("Plotly:", plotly.__version__)
        st.write(L("Kaleido installed:", "已安裝 Kaleido："), importlib.util.find_spec("kaleido") is not None)
        st.write(L("OpenAI installed:", "已安裝 OpenAI："), OpenAI is not None)
        st.write(L("PPT export:", "PPT 匯出："), PPT_AVAILABLE)
        st.write(L("PDF export:", "PDF 匯出："), PDF_AVAILABLE)
    except Exception as e:
        st.write(L("Diagnostics unavailable:", "無法顯示診斷資訊："), e)

# Load data
df_raw = None
if st.session_state.get("use_demo_dataset", False):
    if st.session_state.get("demo_dataset_choice", 1) == 2:
        df_raw = build_demo_dataset_2()
    else:
        df_raw = build_demo_dataset()
elif up is not None:
    df_raw = safe_read_csv(up)

if df_raw is None:
    st.info(L("Upload a CSV or click a demo dataset to begin.", "請上傳 CSV，或按示範數據開始。"))
    st.stop()

# Prep
try:
    m = prep_retail(df_raw)
except Exception as e:
    st.error(f"{L("Data load error", "資料載入錯誤")}: {e}")
    st.stop()

df = m.df

render_questions_this_answers()
st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)

st.markdown(f"**{L('Example input data (preview)', '輸入數據範例（預覽）')}**")
preview_df = df.head(MAX_PREVIEW_ROWS).copy()

if m.col_discount and m.col_discount in preview_df.columns:
    preview_df[m.col_discount] = preview_df[m.col_discount].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "")

if m.col_revenue and m.col_revenue in preview_df.columns:
    preview_df[m.col_revenue] = preview_df[m.col_revenue].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")

if m.col_date and m.col_date in preview_df.columns:
    preview_df[m.col_date] = pd.to_datetime(preview_df[m.col_date], errors="coerce").dt.strftime("%Y-%m-%d")

st.dataframe(preview_df, use_container_width=True, hide_index=True)
st.caption(L('This is the type of business data EC-AI turns into clear decisions.', '這就是 EC-AI 轉化為清晰決策的業務數據類型。'))
st.divider()

# Summary / cards / insights
summary_points = build_business_summary_points(m)
exec_cards = build_exec_cards(m)
ins_sections = build_business_insights_sections(m)
profile = profile_dataset(df, m)
confidence_score = compute_confidence_score(profile)
detected_insights = detect_insights(m)
priority_actions = generate_priority_actions(m)
ceo_briefing = build_ceo_briefing(priority_actions, confidence_score)

# Executive Dashboard
try:
    export_figures = render_onepager_dashboard(m, df)
except Exception as e:
    st.warning(f"{L("Executive Dashboard unavailable", "無法顯示管理儀表板")}: {e}")
    export_figures = {}

st.divider()

# Executive Summary + 3 insight cards
st.subheader(T("Executive Summary"))
render_parallel_insight_cards(exec_cards)
st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)
render_summary_card(summary_points)
st.markdown("<div class='ec-space'></div>", unsafe_allow_html=True)
render_ceo_briefing(ceo_briefing)

st.divider()

# Charts & Insights
st.subheader(T("Charts & Insights"))

# 1) Overall trend
fig_trend = line_trend(df, m.col_date, m.col_revenue, L("Revenue Trend (Daily)", "收入趨勢（每日）"))
render_chart_with_commentary(
    fig_trend,
    what_points=[L("Overall revenue direction over time (daily total).", "顯示每日總收入的整體走勢。")],
    why_points=[L("Sets the context: growth vs stability.", "幫你判斷是增長還是平穩。"), L("Helps spot spikes that may come from promotions or one-off events.", "有助找出推廣或一次性事件帶來的高低波動。")],
    todo_points=[L("If the trend is flat, focus on execution and mix. If it’s rising, protect top drivers and scale carefully.", "如果走勢平穩，就先改善執行與產品組合；如果正在上升，就保護主要增長來源並小心擴張。")],
    boxed_commentary=True,
)

# 2) Top 5 stores
fig_topstores, df_topstores = top5_stores_bar(m)
top_store_name = df_topstores.iloc[0]["Store"] if len(df_topstores) else "Top store"
render_chart_with_commentary(
    fig_topstores,
    what_points=[L(f"Revenue is concentrated in a small number of stores, led by **{top_store_name}**.", f"收入集中在少數門店，其中 **{top_store_name}** 最突出。")],
    why_points=[L("Top stores disproportionately drive outcomes.", "頭部門店對整體表現影響最大。"), L("Operational issues in one key store can move the whole month.", "只要一間核心門店出現營運問題，整個月表現都可能受影響。")],
    todo_points=[L("Prioritise stock availability, staffing, and execution in the top stores before expanding elsewhere.", "在擴張之前，先把頭部門店的庫存、排班及執行做好。")],
    boxed_commentary=True,
)

# 3) Store stability
st.markdown(f"### {L('Store Stability (Top 5)', '門店穩定性（前 5 名）')}")
figs, store_names = store_small_multiples(m)
cols = st.columns(2)
for i, fig in enumerate(figs):
    with cols[i % 2]:
        safe_plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

render_insight_card(
    what_points=[L("Some stores are more stable, while others vary more from day to day.", "有些門店表現較穩定，有些則每天變化較大。")],
    why_points=[L("Low stability makes forecasting and inventory planning harder.", "穩定性較低會令預測及庫存計劃更困難。"), L("Day-to-day variation often points to execution issues, not just demand.", "日常波動往往反映執行問題，而不只是需求變化。")],
    todo_points=[L("Use more stable stores as benchmarks. Review staffing, stock availability, and promotion timing in less stable stores.", "以較穩定門店作為基準，並檢視較不穩定門店的排班、庫存和推廣時點。")],
)

# 4) Pricing Effectiveness
pe = pricing_effectiveness(m)
if pe is not None:
    fig_price, df_price = pe
    render_chart_with_commentary(
        fig_price,
        what_points=[L("Moderate discounts often perform better than aggressive discounting.", "適度折扣通常比大幅折扣表現更好。")],
        why_points=[L("Large discounts can erode revenue quality without improving outcomes.", "大折扣可能拉低收入質素，卻未必改善結果。"), L("Pricing discipline is a repeatable advantage.", "有紀律的定價策略是可複製的優勢。")],
        todo_points=[L("Use small discounts as default. Treat deep discounts as experiments with clear goals and limits.", "以小折扣作為基本策略；大折扣只應在有清晰目標與限制下測試。")],
        boxed_commentary=True,
    )
else:
    st.info(L("Pricing Effectiveness is unavailable (no usable discount column found).", "未能顯示定價效果（找不到可用的折扣欄位）。"))

# 5) Revenue by Category
cat = revenue_by_category(m, topn=8)
if cat is not None:
    fig_cat, _ = cat
    render_chart_with_commentary(
        fig_cat,
        what_points=[L("A few categories typically drive most revenue.", "通常只有少數類別帶動大部分收入。")],
        why_points=[L("Category mix often matters more than SKU count.", "類別組合往往比 SKU 數量更重要。"), L("Weak categories can drag overall performance.", "弱勢類別會拖慢整體表現。")],
        todo_points=[L("Double down on winner categories (stock depth, placement). Review whether weak categories need repositioning or removal.", "加強贏家類別的庫存深度與陳列，同時檢視弱勢類別是否需要重新定位或淘汰。")],
        boxed_commentary=True,
    )
else:
    st.info(L("Category Mix is unavailable (no usable category column found).", "未能顯示類別組合（找不到可用的類別欄位）。"))

# 6) Revenue by Channel
ch = revenue_by_channel(m, topn=8)
if ch is not None:
    fig_ch, _ = ch
    render_chart_with_commentary(
        fig_ch,
        what_points=[L("Channels contribute very differently to revenue.", "不同渠道對收入的貢獻差異很大。")],
        why_points=[L("Scaling the right channel can be cheaper than opening new stores.", "把資源放在正確渠道，成本可能比開新店更低。"), L("Channel concentration adds risk if one channel weakens.", "若收入集中於單一渠道，一旦轉弱便會帶來風險。")],
        todo_points=[L("Invest more in high-performing channels. Fix or rethink consistently weak channels.", "把更多資源投放在高表現渠道；長期弱勢渠道則要改善或重新思考定位。")],
        boxed_commentary=True,
    )
else:
    st.info(L("Channels view is unavailable (no usable channel column found).", "未能顯示渠道分析（找不到可用的渠道欄位）。"))

st.divider()

def render_ai_insight_cards(ins_sections: Dict[str, List[str]]) -> None:
    items = list(ins_sections.items())
    rows = [items[i:i+2] for i in range(0, len(items), 2)]
    for row in rows:
        cols = st.columns(2, gap="small")
        for idx, (sec_title, bullets) in enumerate(row):
            with cols[idx]:
                bullet_html = "".join(
                    f"<li>{emphasize_exec_keywords_html(clean_display_text(b))}</li>"
                    for b in bullets if clean_display_text(b)
                )
                st.markdown(
                    f"""
<div class="ec-insight-card">
  <div class="ec-card-title">{sec_title}</div>
  <div class="ec-insight-section">
    <ul class="ec-insight-list">{bullet_html}</ul>
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )

# AI Insights
st.subheader(T("AI Insights"))
render_ai_insight_cards(ins_sections)

st.divider()

# Advanced analytics
with st.expander(L("Advanced analytics (optional)", "進階分析（可選）"), expanded=False):
    st.caption(L("Optional deeper diagnostics for power users. Collapsed by default to keep the UI executive-clean.", "提供進一步診斷分析，預設收起以保持版面簡潔。"))
    try:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])][:MAX_CORR_COLS]
        if len(num_cols) >= 2:
            corr = df[num_cols].corr(numeric_only=True)
            if m.col_revenue in corr.columns:
                top_corr = (
                    corr[m.col_revenue]
                    .drop(labels=[m.col_revenue], errors="ignore")
                    .sort_values(key=lambda s: s.abs(), ascending=False)
                    .head(10)
                    .reset_index()
                    .rename(columns={"index": "Metric", m.col_revenue: "Correlation"})
                )
                st.markdown(f"**{L('Top correlations with Revenue (directional)', '與收入最相關的指標（方向性）')}**")
                st.dataframe(top_corr, use_container_width=True, hide_index=True)

            st.markdown(f"**{L('Correlation heatmap (numeric metrics)', '相關系數熱力圖（數值指標）')}**")
            fig_corr = px.imshow(
                corr.round(2),
                text_auto=".2f",
                aspect="auto",
                color_continuous_scale="Blues",
            )
            fig_corr.update_traces(textfont=dict(color="white", size=12))
            fig_corr.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=420)
            safe_plotly_chart(fig_corr, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info(L("Not enough numeric columns to compute correlations.", "沒有足夠數值欄位可計算相關性。"))
    except Exception as e:
        st.warning(f"Advanced analytics unavailable: {e}")

# Ask AI
st.subheader(T("Ask AI (CEO Q&A)"))
st.caption(L("Ask questions about your data (for example: Why did revenue soften? Which store should I fix first?)", "就你的數據發問（例如：為何收入轉弱？應先改善哪一間門店？）"))

_context_lines: List[str] = []
try:
    _context_lines.append(f"Dataset: {len(df)} rows, {df[m.col_date].nunique()} days.")
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

st.markdown(f"**{L('Suggested Questions', '建議問題')}**")
selected_question = None
sq1, sq2, sq3 = st.columns(3)
with sq1:
    if st.button(L("Which store should I fix first?", "我應先改善哪一間門店？"), use_container_width=True):
        selected_question = L("Which store should I fix first and why?", "我應先改善哪一間門店？原因是什麼？")
with sq2:
    if st.button(L("Is discounting helping or hurting?", "折扣是在幫忙還是在拖累表現？"), use_container_width=True):
        selected_question = L("Is discounting helping or hurting revenue quality?", "折扣對收入質素是幫助還是傷害？")
with sq3:
    if st.button(L("What should management do next?", "管理層下一步應做什麼？"), use_container_width=True):
        selected_question = L("What should management focus on next based on this dataset?", "根據這份數據，管理層下一步應重點做什麼？")

if selected_question:
    st.session_state.ask_ai_question = selected_question

q_col, btn_col = st.columns([0.82, 0.18])
with q_col:
    user_q = st.text_input(
        L("Ask EC-AI…", "向 EC-AI 發問…"),
        value=st.session_state.get("ask_ai_question", ""),
        key="ask_ai_question_input",
        placeholder=L("E.g., What should I focus on next week?", "例如：我下星期應重點做什麼？"),
    )
with btn_col:
    ask_clicked = st.button(L("Ask", "提問"), use_container_width=True)

run_question = selected_question or (user_q.strip() if ask_clicked and user_q.strip() else "")
if run_question:
    with st.spinner(L("Thinking…", "思考中…")):
        answer = safe_answer_question_with_openai(run_question, context_text)
    st.session_state.ask_ai_question = run_question
    st.session_state.ask_ai_history.insert(0, (run_question, answer))
    deduped = []
    seen = set()
    for q, a in st.session_state.ask_ai_history:
        if q not in seen:
            deduped.append((q, a))
            seen.add(q)
    st.session_state.ask_ai_history = deduped[:6]

for q, a in st.session_state.ask_ai_history[:3]:
    st.markdown(f"**Q:** {q}")
    render_structured_ai_answer(a)

st.divider()

# Export pack
st.subheader(T("Export Executive Pack"))
st.caption(L("Download a shareable executive-ready brief (PDF) or slide pack (PPTX).", "下載可分享的管理層摘要（PDF）或投影片（PPTX）。"))

chart_items: List[Tuple[str, go.Figure, str]] = []

try:
    chart_items.append((
        L("Revenue Trend (Daily)", "收入趨勢（每日）"),
        fig_trend,
        L("Trend line of daily revenue.\nUse this to spot spikes and dips and protect momentum.", "每日收入趨勢線。\n用來找出高低波動，並保護主要增長動能。")
    ))
except Exception:
    pass

try:
    chart_items.append((
        L("Top Revenue-Generating Stores (Top 5)", "收入最高門店（前 5 名）"),
        fig_topstores,
        L("Revenue concentration by store.\nPrioritise execution in the top stores first.", "按門店顯示收入集中情況。\n應先把資源放在頭部門店的執行上。")
    ))
except Exception:
    pass

try:
    if pe is not None:
        chart_items.append((
            L("Pricing Effectiveness — Avg Revenue per Sale by Discount Level", "定價效果 — 不同折扣水平的平均每單收入"),
            fig_price,
            L("Compares average revenue per sale across discount levels.\nUse moderate discounts by default; treat deep discounts as controlled tests.", "比較不同折扣水平的每張訂單平均收入。\n以適度折扣作基本策略，大折扣只作受控測試。")
        ))
except Exception:
    pass

try:
    if cat is not None:
        chart_items.append((
            L("Revenue by Category", "按類別收入"),
            fig_cat,
            L("Shows which categories drive revenue.\nDouble down on winners; fix or trim weak categories.", "顯示哪些類別帶動收入。\n加強贏家類別，並改善或淘汰弱勢類別。")
        ))
except Exception:
    pass

try:
    if ch is not None:
        chart_items.append((
            L("Revenue by Channel", "按渠道收入"),
            fig_ch,
            L("Channel contribution to revenue.\nReallocate effort to channels that consistently perform.", "顯示各渠道對收入的貢獻。\n把資源重新分配到長期表現較好的渠道。")
        ))
except Exception:
    pass

c1, c2 = st.columns(2)

with c1:
    if st.button(L("Generate PDF Executive Brief", "產生 PDF 管理摘要"), use_container_width=True):
        try:
            pdf_bytes = build_pdf_exec_brief(
                title=L("EC-AI Insight — Executive Brief", "EC-AI 智能分析 — 管理摘要"),
                subtitle=L("Sales performance, explained clearly.", "把銷售表現講清楚。"),
                summary_points=summary_points,
                chart_items=chart_items,
            )
            safe_download_button(
                L("Download PDF", "下載 PDF"),
                data=pdf_bytes,
                file_name=("ecai_executive_brief_zh.pdf" if LANG=="中文" else "ecai_executive_brief.pdf"),
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

with c2:
    if st.button(L("Generate Executive Pack (PPTX)", "產生管理層簡報（PPTX）"), use_container_width=True):
        try:
            pptx_bytes = build_ppt_talking_deck(
                deck_title=L("EC-AI Insight — Executive Pack", "EC-AI 智能分析 — 管理簡報"),
                chart_items=chart_items,
                summary_points=summary_points,
                exec_cards=exec_cards,
            )
            safe_download_button(
                L("Download PPTX", "下載 PPTX"),
                data=pptx_bytes,
                file_name=("ecai_executive_pack_zh.pptx" if LANG=="中文" else "ecai_executive_pack.pptx"),
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PPT generation failed: {e}")
