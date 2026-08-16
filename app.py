
# EC-AI Executive Review Workspace — Stage 1-C.2 Polish Build
# Hotfix v3: Executive Briefing queue uses unique External Rating / Attention Rating columns.
# Hotfix v4: Executive Briefing bar chart rebuilt as a single-trace horizontal bar with thicker bars.
# Stage 1-C.2: shared visual polish across Briefing, Review, Relationships, Execution and Portfolio.
# v9.2: Real Top 10 S&P universe + MAS v1.2 + MAS explainability + top executive pack export
# Run:
#   python -m streamlit run ecai_stage_1_c_1_full_build.py

import io
import math
import re
from datetime import date, datetime
from typing import Any, Dict
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="EC-AI Executive Review Workspace — Stage 1-C.2",
    page_icon="🏦",
    layout="wide",
)

# =========================
# CSS
# =========================
st.markdown("""
<style>
.block-container { padding-top: 4.5rem; padding-left: 1.8rem; padding-right: 1.8rem; max-width: 1920px; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#061A36 0%,#0B2C55 100%); }
.ec-hero { background: transparent; margin: 0 0 16px 0; padding: 0; }
.ec-title { font-size: 38px !important; font-weight: 950 !important; color:#071B3A; letter-spacing:-0.035em; line-height:1.35 !important; margin-top:24px; margin-bottom:8px; padding-top:4px; }
.ec-subtitle { font-size: 20px !important; font-weight: 800; color:#0B2C55; margin-bottom:6px; }
.ec-body { font-size: 16px !important; color:#526173; line-height:1.45 !important; max-width: 1180px; }
[data-baseweb="tab-list"] { gap: 6px; background:#F8FAFC; padding:6px; border-radius:14px; border:1px solid #D8DEE6; margin-bottom:14px; }
[data-baseweb="tab"] { height:46px; padding:0 16px; border-radius:10px; font-weight:850; font-size:15px; }
[data-baseweb="tab"][aria-selected="true"] { background:#071B3A; color:white; }
.ec-section-title { font-size: 31px !important; font-weight: 950 !important; color:#071B3A; margin-top:18px; margin-bottom:6px; letter-spacing:-0.02em; line-height:1.12 !important; }
.ec-section-subtitle { font-size:16px !important; color:#526173; margin-bottom:12px; }
.ec-note { background:#F8FAFC; border-left:5px solid #1565C0; border-radius:12px; padding:13px 17px; margin:10px 0 15px 0; color:#071B3A; font-size:16px !important; line-height:1.5 !important; }
.ec-card { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:15px; padding:17px 19px; box-shadow:0 2px 8px rgba(15,23,42,.055); min-height:105px; }
.ec-card-label { color:#526173; font-size:13px !important; font-weight:900; text-transform:uppercase; letter-spacing:.03em; margin-bottom:6px; }
.ec-card-value { color:#071B3A; font-size:29px !important; font-weight:950; line-height:1.08 !important; }
.ec-card-sub { color:#526173; font-size:13px !important; margin-top:6px; line-height:1.3 !important; }
.ec-kpi-row { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:13px; margin:12px 0 15px 0; }
.ec-kpi-row4 { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:13px; margin:12px 0 15px 0; }
.ec-kpi-row3 { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:13px; margin:12px 0 15px 0; }
.ec-kpi-row2 { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:13px; margin:12px 0 15px 0; }
.ec-legend { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:15px; padding:17px 19px; margin:10px 0 15px; box-shadow:0 2px 8px rgba(15,23,42,.045); }
.ec-legend-title { font-size:20px !important; font-weight:950; color:#071B3A; margin-bottom:8px; }
.ec-legend-grid { display:grid; grid-template-columns: 1.1fr 1fr; gap:18px; }
.ec-pill { display:inline-block; border-radius:999px; padding:5px 10px; font-size:13px !important; font-weight:900; margin:3px 4px 3px 0; }
.ec-pill-red { background:#FEE2E2; color:#991B1B; border:1px solid #FECACA; }
.ec-pill-orange { background:#FFEDD5; color:#9A3412; border:1px solid #FED7AA; }
.ec-pill-blue { background:#DBEAFE; color:#1E3A8A; border:1px solid #BFDBFE; }
.ec-pill-green { background:#DCFCE7; color:#166534; border:1px solid #BBF7D0; }
.ec-action-card { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:16px; padding:17px 19px; min-height:208px; box-shadow:0 2px 8px rgba(15,23,42,.055); }
.ec-rank { display:inline-block; background:#EEF4FF; color:#0B3D75; border:1px solid #C7D7FE; border-radius:999px; padding:4px 10px; font-size:12px !important; font-weight:900; margin-bottom:8px; }
.ec-company { font-size:22px !important; font-weight:950; color:#071B3A; line-height:1.15 !important; margin-bottom:6px; }
.ec-action { font-size:15px !important; font-weight:900; color:#1565C0; margin-bottom:8px; }
.ec-text { font-size:15px !important; color:#071B3A; line-height:1.45 !important; }
.ec-table-title { font-size:21px !important; font-weight:950; color:#071B3A; margin:14px 0 8px; }
[data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span, [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td { font-size: 14.5px !important; }
.rw-hero { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:17px; padding:22px 26px; box-shadow:0 2px 8px rgba(15,23,42,.055); margin:10px 0 15px; }
.rw-name { font-size:33px !important; font-weight:950; color:#071B3A; line-height:1.15 !important; margin-bottom:5px; }
.rw-meta { font-size:16px !important; color:#526173; margin-bottom:12px; }
.rw-alert { background:#FEF3C7; border-left:6px solid #F59E0B; border-radius:13px; padding:15px 17px; color:#071B3A; margin:12px 0 15px; }
.rw-alert-title { font-size:18px !important; font-weight:950; margin-bottom:6px; }
.rw-card { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:14px; padding:15px 17px; min-height:120px; }
.rw-card-label { color:#526173; font-size:12px !important; font-weight:900; margin-bottom:6px; text-transform:uppercase; }
.rw-card-value { color:#071B3A; font-size:24px !important; font-weight:950; line-height:1.1 !important; }
.memo-preview { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:15px; padding:20px 24px; color:#071B3A; line-height:1.55 !important; }
.stDownloadButton button, .stButton button { font-size:14px !important; padding:0.6rem 0.9rem !important; font-weight:800 !important; }

.ec-top-export { background:#F8FAFC; border-left:5px solid #0B2C55; border-radius:13px; padding:13px 17px; margin:12px 0 12px 0; color:#071B3A; }
.explain-card { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:14px; padding:15px 17px; margin:10px 0; }
.explain-title { font-size:17px !important; font-weight:950; color:#071B3A; margin-bottom:8px; }
.explain-grid { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:10px; }
.explain-cell { background:#F8FAFC; border:1px solid #E6EAF0; border-radius:12px; padding:10px 12px; min-height:82px; }
.explain-label { color:#526173; font-size:11px !important; font-weight:900; text-transform:uppercase; letter-spacing:.03em; }
.explain-value { color:#071B3A; font-size:22px !important; font-weight:950; margin:4px 0; }

.exec-status-pill { display:inline-block; border-radius:999px; padding:5px 10px; font-size:12px !important; font-weight:900; }
.exec-not-started { background:#F3F4F6; color:#374151; border:1px solid #D1D5DB; }
.exec-assigned { background:#E8EEF7; color:#0B2C55; border:1px solid #AFC4DD; }
.exec-progress { background:#DBEAFE; color:#1E3A8A; border:1px solid #BFDBFE; }
.exec-monitoring { background:#F8FAFC; color:#4B5563; border:1px solid #CBD5E1; }
.exec-completed { background:#DCFCE7; color:#166534; border:1px solid #BBF7D0; }
.exec-escalated { background:#FEF3C7; color:#92400E; border:1px solid #FCD34D; }
.exec-panel { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:15px; padding:17px 19px; box-shadow:0 2px 8px rgba(15,23,42,.045); }


.workflow-step { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:14px; padding:14px 16px; min-height:112px; box-shadow:0 2px 8px rgba(15,23,42,.045); }
.workflow-step-label { color:#526173; font-size:11px !important; font-weight:950; text-transform:uppercase; letter-spacing:.04em; margin-bottom:7px; }
.workflow-step-value { color:#071B3A; font-size:18px !important; font-weight:950; line-height:1.15 !important; }
.workflow-step-sub { color:#526173; font-size:12px !important; margin-top:7px; line-height:1.35 !important; }
.workflow-lane { background:#F8FAFC; border:1px solid #E6EAF0; border-radius:15px; padding:14px 16px; margin:10px 0; }
.workflow-lane-title { color:#071B3A; font-size:17px !important; font-weight:950; margin-bottom:7px; }
.workflow-lane-text { color:#071B3A; font-size:14px !important; line-height:1.45 !important; }


.rel360-grid { display:grid; grid-template-columns: 1.1fr 1fr; gap:15px; margin:12px 0 16px 0; }
.rel360-panel { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:16px; padding:18px 20px; box-shadow:0 2px 8px rgba(15,23,42,.045); min-height:180px; }
.rel360-panel-title { font-size:19px !important; font-weight:950; color:#071B3A; margin-bottom:8px; }
.timeline-item { border-left:4px solid #365F9C; padding:1px 0 9px 14px; margin-left:4px; }
.timeline-date { font-size:12px !important; font-weight:950; color:#526173; text-transform:uppercase; letter-spacing:.04em; }
.timeline-event { font-size:16px !important; font-weight:850; color:#071B3A; line-height:1.35; }
.network-node { display:inline-block; padding:8px 12px; margin:5px 6px 5px 0; border-radius:999px; background:#F8FAFC; border:1px solid #D8DEE6; color:#071B3A; font-size:13px !important; font-weight:850; }
.network-node-core { background:#071B3A; color:white; border:1px solid #071B3A; }
.product-strong { background:#DCFCE7; color:#166534; border-radius:999px; padding:4px 9px; font-weight:900; }
.product-medium { background:#DBEAFE; color:#1E3A8A; border-radius:999px; padding:4px 9px; font-weight:900; }
.product-low { background:#FEF3C7; color:#92400E; border-radius:999px; padding:4px 9px; font-weight:900; }



/* v10.0.3 Wallet Sizing Engine */
.wallet-source-note { background:#EEF4FA; border-left:5px solid #2F5D8A; border-radius:12px; padding:13px 16px; margin:10px 0 14px; color:#071B3A; font-size:15px; line-height:1.45; }
.wallet-card-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:12px 0 15px; }
.wallet-card { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:14px; padding:15px 17px; box-shadow:0 2px 8px rgba(15,23,42,.045); min-height:104px; }
.wallet-card-label { color:#526173; font-size:12px; font-weight:900; text-transform:uppercase; letter-spacing:.035em; }
.wallet-card-value { color:#071B3A; font-size:27px; font-weight:950; margin-top:6px; line-height:1.1; }
.wallet-card-sub { color:#526173; font-size:13px; margin-top:6px; }
.wallet-opportunity { background:#F8FAFC; border:1px solid #D8DEE6; border-radius:14px; padding:15px 17px; margin:10px 0; }
.wallet-opportunity-title { color:#071B3A; font-size:18px; font-weight:950; margin-bottom:7px; }
.wallet-opportunity-text { color:#071B3A; font-size:15px; line-height:1.5; }

/* v10.0.1 Relationship 360 clean layout */
.rel360-shell { margin-top: 8px; }
.rel360-header-card { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:18px; padding:22px 26px; box-shadow:0 2px 8px rgba(15,23,42,.055); margin:12px 0 14px; }
.rel360-name { font-size:34px !important; font-weight:950; color:#071B3A; line-height:1.1; margin-bottom:4px; }
.rel360-meta { color:#526173; font-size:15px !important; margin-bottom:12px; }
.rel360-command { background:#F8FAFC; border-left:5px solid #071B3A; border-radius:14px; padding:17px 20px; margin:14px 0; color:#071B3A; }
.rel360-command-title { font-size:18px !important; font-weight:950; margin-bottom:8px; color:#071B3A; }
.rel360-panel-clean { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:16px; padding:14px 18px; box-shadow:0 2px 8px rgba(15,23,42,.045); min-height:0; }
.rel360-wide-panel { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:16px; padding:18px 20px; box-shadow:0 2px 8px rgba(15,23,42,.045); margin:14px 0 16px; }
.rel360-panel-title-clean { font-size:20px !important; font-weight:950; color:#071B3A; margin-bottom:10px; }
.wallet-grid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:12px; margin-top:10px; }
.wallet-mini { background:#F8FAFC; border:1px solid #E6EAF0; border-radius:13px; padding:13px 15px; min-height:82px; }
.wallet-label { color:#526173; font-size:11px !important; font-weight:950; text-transform:uppercase; letter-spacing:.04em; }
.wallet-value { color:#071B3A; font-size:24px !important; font-weight:950; margin-top:4px; }
.wallet-sub { color:#526173; font-size:12px !important; margin-top:4px; }
.product-table-clean table { width:100%; border-collapse:collapse; font-size:15px; }
.product-table-clean th { background:#F8FAFC; color:#526173; text-transform:uppercase; font-size:12px; letter-spacing:.04em; padding:8px 10px; border:1px solid #E6EAF0; }
.product-table-clean td { padding:8px 10px; border:1px solid #E6EAF0; color:#071B3A; }

.mas-breakdown-table table { width:100%; border-collapse:collapse; font-size:15px; }
.mas-breakdown-table th { background:#F8FAFC; color:#526173; font-weight:900; padding:10px; border:1px solid #E6EAF0; }
.mas-breakdown-table td { padding:10px; border:1px solid #E6EAF0; color:#071B3A; }
.mas-breakdown-table th:nth-child(2), .mas-breakdown-table th:nth-child(3), .mas-breakdown-table td:nth-child(2), .mas-breakdown-table td:nth-child(3) { text-align:right; }

</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def section_title(title: str, subtitle: str | None = None):
    st.markdown(f'<div class="ec-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="ec-section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def clean_company(name: str) -> str:
    name = re.sub(r"\s*\([^)]*\)", "", str(name)).strip()
    replacements = {
        "Taiwan Semiconductor Manufacturing Company Limited": "TSMC",
        "Toyota Motor Corporation": "Toyota",
        "Alibaba Group Holding Limited": "Alibaba",
        "Tencent Holdings Limited": "Tencent",
        "CK Hutchison Holdings Limited": "CK Hutchison",
        "Jardine Matheson Holdings Limited": "Jardine Matheson",
        "BHP Group Limited": "BHP",
        "HSBC Holdings plc": "HSBC",
        "DBS Bank Ltd.": "DBS",
        "Rio Tinto plc": "Rio Tinto",
    }
    return replacements.get(name, name)


def safe_float(x, default=None):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def fmt_b(x, na="N/A"):
    if x is None or pd.isna(x):
        return na
    return f"USD {float(x):,.1f}B"


def fmt_pct(x, na="N/A"):
    if x is None or pd.isna(x):
        return na
    return f"{float(x):.1f}%"


def fmt_score(x):
    if x is None or pd.isna(x):
        return "N/A"
    return f"{float(x):.1f}"


def band(score: float) -> str:
    if score >= 80:
        return "Executive Attention"
    if score >= 61:
        return "Management Attention"
    if score >= 41:
        return "Review"
    return "Monitor"


def band_pill_class(score: float) -> str:
    if score >= 80:
        return "ec-pill-red"
    if score >= 61:
        return "ec-pill-orange"
    if score >= 41:
        return "ec-pill-blue"
    return "ec-pill-green"

# =========================
# Dataset: S&P Top 10 Universe
# Values loaded from Gordon's S&P Screener export and normalized to USD B.
# Market Cap and EV fields are USD MM in export; financial statement fields are USD thousands.
# =========================
raw_rows = [
    {"Company":"Alibaba", "Country":"China", "Sector":"Broadline Retail", "Rating":"A+", "Outlook":"Stable", "EV_B":248940.092004/1000, "MarketCap_B":244549.162085/1000, "Revenue_B":144192676.102609/1e6, "Revenue_Growth":2.742, "EBITDA_B":15508667.667875/1e6, "NetIncome_B":14385461.557271/1e6, "Assets_B":276853596.63819/1e6, "Debt_B":40844666.051574/1e6, "Equity_B":163289065.22709/1e6, "Cash_B":19069504.42551/1e6, "InterestExpense_B":1379427.82056/1e6, "EBITDA_Margin":10.756, "ROE":9.216},
    {"Company":"BHP", "Country":"Australia", "Sector":"Metals and Mining", "Rating":"NR", "Outlook":"NR", "EV_B":236745.249574/1000, "MarketCap_B":214939.946357/1000, "Revenue_B":None, "Revenue_Growth":-7.898, "EBITDA_B":None, "NetIncome_B":None, "Assets_B":None, "Debt_B":None, "Equity_B":None, "Cash_B":13466000/1e6, "InterestExpense_B":None, "EBITDA_Margin":48.7, "ROE":24.713},
    {"Company":"CK Hutchison", "Country":"Hong Kong", "Sector":"Industrial Conglomerates", "Rating":"A", "Outlook":"Stable", "EV_B":73863.627865/1000, "MarketCap_B":33477.957378/1000, "Revenue_B":35922242.843789/1e6, "Revenue_Growth":-0.467, "EBITDA_B":6112538.365601/1e6, "NetIncome_B":2484729.977161/1e6, "Assets_B":148478436.659681/1e6, "Debt_B":42991273.89414/1e6, "Equity_B":88443156.471624/1e6, "Cash_B":18468440.737956/1e6, "InterestExpense_B":1586404.52388/1e6, "EBITDA_Margin":17.016, "ROE":2.889},
    {"Company":"DBS", "Country":"Singapore", "Sector":"Banks", "Rating":"AA-", "Outlook":"Stable", "EV_B":None, "MarketCap_B":None, "Revenue_B":17724025.650135/1e6, "Revenue_Growth":1.994, "EBITDA_B":None, "NetIncome_B":None, "Assets_B":698525925.00052/1e6, "Debt_B":58620153.505272/1e6, "Equity_B":54555561.633688/1e6, "Cash_B":36060424.672496/1e6, "InterestExpense_B":10557397.681109/1e6, "EBITDA_Margin":None, "ROE":15.596},
    {"Company":"HSBC", "Country":"United Kingdom", "Sector":"Banks", "Rating":"A-", "Outlook":"Positive", "EV_B":None, "MarketCap_B":324753.0/1000, "Revenue_B":74173000/1e6, "Revenue_Growth":3.24, "EBITDA_B":None, "NetIncome_B":None, "Assets_B":3306011000/1e6, "Debt_B":None, "Equity_B":197270000/1e6, "Cash_B":214707000/1e6, "InterestExpense_B":61680000/1e6, "EBITDA_Margin":None, "ROE":11.611},
    {"Company":"Jardine Matheson", "Country":"Bermuda", "Sector":"Industrial Conglomerates", "Rating":"A+", "Outlook":"Stable", "EV_B":53167.28/1000, "MarketCap_B":18339.28/1000, "Revenue_B":34217000/1e6, "Revenue_Growth":-4.366, "EBITDA_B":None, "NetIncome_B":None, "Assets_B":86136000/1e6, "Debt_B":18151000/1e6, "Equity_B":54647000/1e6, "Cash_B":8563000/1e6, "InterestExpense_B":664000/1e6, "EBITDA_Margin":13.891, "ROE":6.096},
    {"Company":"Rio Tinto", "Country":"United Kingdom", "Sector":"Metals and Mining", "Rating":"A", "Outlook":"Stable", "EV_B":None, "MarketCap_B":None, "Revenue_B":None, "Revenue_Growth":None, "EBITDA_B":None, "NetIncome_B":None, "Assets_B":None, "Debt_B":None, "Equity_B":None, "Cash_B":None, "InterestExpense_B":None, "EBITDA_Margin":None, "ROE":None},
    {"Company":"TSMC", "Country":"Taiwan", "Sector":"Semiconductors", "Rating":"AA-", "Outlook":"Stable", "EV_B":1985418.0/1000, "MarketCap_B":2056434.0/1000, "Revenue_B":133069172.905942/1e6, "Revenue_Growth":31.605, "EBITDA_B":None, "NetIncome_B":None, "Assets_B":270823938.595944/1e6, "Debt_B":34220443.143767/1e6, "Equity_B":185503090.457933/1e6, "Cash_B":94922988.833347/1e6, "InterestExpense_B":402394.112618/1e6, "EBITDA_Margin":69.593, "ROE":36.210},
    {"Company":"Tencent", "Country":"China", "Sector":"Interactive Media and Services", "Rating":"A+", "Outlook":"Stable", "EV_B":501991.7/1000, "MarketCap_B":497673.6/1000, "Revenue_B":108207822.997037/1e6, "Revenue_Growth":13.86, "EBITDA_B":None, "NetIncome_B":None, "Assets_B":297414967.56213/1e6, "Debt_B":58791863.522337/1e6, "Equity_B":175664308.055709/1e6, "Cash_B":31572766.50759/1e6, "InterestExpense_B":1859896.348685/1e6, "EBITDA_Margin":36.755, "ROE":20.515},
    {"Company":"Toyota", "Country":"Japan", "Sector":"Automobiles", "Rating":"A+", "Outlook":"Stable", "EV_B":414723.3/1000, "MarketCap_B":221564.4/1000, "Revenue_B":336748929.820736/1e6, "Revenue_Growth":5.513, "EBITDA_B":None, "NetIncome_B":None, "Assets_B":663641547.11541/1e6, "Debt_B":276195586.11102/1e6, "Equity_B":257979719.85948/1e6, "Cash_B":62168468.68278/1e6, "InterestExpense_B":400584.442216/1e6, "EBITDA_Margin":11.074, "ROE":10.233},
]

# =========================
# Scoring Engine MAS v1.2
# =========================
def score_revenue(x):
    if x is None or pd.isna(x): return 5
    if x < 10: return 2
    if x < 50: return 5
    if x < 100: return 7
    if x < 250: return 9
    return 10

def score_assets(x):
    if x is None or pd.isna(x): return 5
    if x < 50: return 2
    if x < 250: return 5
    if x < 500: return 7
    if x < 1000: return 9
    return 10

def score_marketcap(x):
    if x is None or pd.isna(x): return 2
    if x < 20: return 1
    if x < 100: return 2
    if x < 500: return 3
    if x < 1000: return 4
    return 5

def score_debt(x):
    if x is None or pd.isna(x): return 4
    if x < 10: return 2
    if x < 50: return 5
    if x < 100: return 7
    if x < 250: return 9
    return 10

def score_interest(x):
    if x is None or pd.isna(x): return 3
    if x < 0.5: return 1
    if x < 2.0: return 3
    return 5

def score_ev(x):
    if x is None or pd.isna(x): return 2
    if x < 50: return 1
    if x < 200: return 2
    if x < 500: return 3
    if x < 1000: return 4
    return 5

def score_cash(x):
    if x is None or pd.isna(x): return 2
    if x < 10: return 1
    if x < 50: return 3
    return 5

def score_growth_attention(x):
    # In MAS, deteriorating growth requires more attention.
    if x is None or pd.isna(x): return 5
    if x > 20: return 2  # elite growth still requires strategic attention, but not remediation
    if x >= 10: return 3
    if x >= 0: return 5
    if x >= -10: return 8
    return 10

def score_margin_attention(x):
    if x is None or pd.isna(x): return 5
    if x > 30: return 2
    if x >= 20: return 3
    if x >= 10: return 5
    if x >= 5: return 8
    return 10

def score_roe_attention(x):
    if x is None or pd.isna(x): return 3
    if x > 20: return 1
    if x >= 15: return 2
    if x >= 10: return 3
    if x >= 5: return 4
    return 5

def rating_bucket(rating: str) -> str:
    if rating is None or pd.isna(rating): return "NR"
    r = str(rating).upper().strip()
    if r in ["NR", "N/A", "NONE", "NAN"]: return "NR"
    return r

def score_rating(rating):
    r = rating_bucket(rating)
    if r == "NR": return 3
    if r.startswith("AAA") or r.startswith("AA"):
        return 1
    if r.startswith("A"):
        return 2
    if r.startswith("BBB"):
        return 3
    if r.startswith("BB"):
        return 4
    return 5

def score_outlook(outlook):
    if outlook is None or pd.isna(outlook): return 3
    o = str(outlook).lower().strip()
    if "positive" in o: return 1
    if "negative" in o: return 5
    if "nr" in o: return 3
    return 3

def strategic_score(r):
    return score_revenue(r["Revenue_B"]) + score_assets(r["Assets_B"]) + score_marketcap(r["MarketCap_B"])

def wallet_score(r):
    return score_debt(r["Debt_B"]) + score_interest(r["InterestExpense_B"]) + score_ev(r["EV_B"]) + score_cash(r["Cash_B"])

def health_score(r):
    return score_growth_attention(r["Revenue_Growth"]) + score_margin_attention(r["EBITDA_Margin"]) + score_roe_attention(r["ROE"])

def risk_score(r):
    return score_rating(r["Rating"]) + score_outlook(r["Outlook"])

def primary_driver(row):
    scores = {
        "Strategic Importance": row["Strategic_Score"],
        "Wallet Opportunity": row["Wallet_Score"],
        "Relationship Health": row["Health_Score"],
        "Coverage Strength": row["Coverage_Score"],
        "Risk Signals": row["Risk_Score"],
    }
    return max(scores, key=scores.get)

def recommended_action(row):
    driver = row["Primary_Driver"]
    if row["Risk_Score"] >= 8:
        return "Credit Review"
    if driver == "Wallet Opportunity" and row["Wallet_Score"] >= 17:
        return "Treasury Deep Dive"
    if driver == "Relationship Health" and row["Health_Score"] >= 17:
        return "Relationship Recovery"
    if row["Strategic_Score"] >= 23 and row["Coverage_Score"] >= 7:
        return "Executive Engagement"
    if row["Sector"] in ["Industrial Conglomerates", "Interactive Media and Services"] and row["Strategic_Score"] >= 18:
        return "Cross-Border Expansion"
    if row["Strategic_Score"] >= 20:
        return "Strategic Relationship Investment"
    return "Portfolio Monitoring"

def expected_outcome(row):
    action = row["Recommended_Action"]
    if action == "Treasury Deep Dive":
        return "Expand treasury wallet, identify funding opportunities and deepen operating relationship."
    if action == "Executive Engagement":
        return "Strengthen senior connectivity, protect strategic franchise and align relationship priorities."
    if action == "Relationship Recovery":
        return "Stabilize relationship momentum, address deterioration signals and recover revenue trajectory."
    if action == "Credit Review":
        return "Validate risk appetite, refresh credit view and agree risk mitigation actions."
    if action == "Cross-Border Expansion":
        return "Coordinate regional coverage and identify cross-border treasury, FX and liquidity opportunities."
    if action == "Strategic Relationship Investment":
        return "Protect long-term strategic franchise and grow multi-product wallet share."
    return "Maintain active monitoring and refresh relationship plan during next review."

def ai_reasoning(row):
    parts = []
    parts.append(f"{row['Company']} is classified as {row['MAS_Band']} with a Management Attention Score of {row['MAS']:.1f}.")
    parts.append(f"The primary driver is {row['Primary_Driver']}.")
    if pd.notna(row["Revenue_B"]): parts.append(f"Revenue scale is {fmt_b(row['Revenue_B'])}.")
    if pd.notna(row["Debt_B"]): parts.append(f"Debt exposure proxy is {fmt_b(row['Debt_B'])}, supporting wallet opportunity assessment.")
    if pd.notna(row["Revenue_Growth"]): parts.append(f"Revenue growth is {fmt_pct(row['Revenue_Growth'])}.")
    if pd.notna(row["EBITDA_Margin"]): parts.append(f"EBITDA margin is {fmt_pct(row['EBITDA_Margin'])}.")
    if row["Rating"] and row["Rating"] != "NR": parts.append(f"External rating is {row['Rating']} with {row['Outlook']} outlook.")
    parts.append(f"Recommended action: {row['Recommended_Action']}.")
    return " ".join(parts)

def data_quality(row):
    fields = ["Revenue_B", "Assets_B", "Debt_B", "MarketCap_B", "Revenue_Growth", "EBITDA_Margin", "ROE", "Rating"]
    filled = sum(0 if row.get(f) is None or pd.isna(row.get(f)) or str(row.get(f)).strip() == "" else 1 for f in fields)
    return round(filled / len(fields) * 100, 0)

# Build dataframe
df = pd.DataFrame(raw_rows)
df["Coverage_Score"] = 7
for col in ["Strategic_Score", "Wallet_Score", "Health_Score", "Risk_Score"]:
    pass
df["Strategic_Score"] = df.apply(strategic_score, axis=1)
df["Wallet_Score"] = df.apply(wallet_score, axis=1)
df["Health_Score"] = df.apply(health_score, axis=1)
df["Risk_Score"] = df.apply(risk_score, axis=1)
df["MAS"] = df["Strategic_Score"] + df["Wallet_Score"] + df["Health_Score"] + df["Coverage_Score"] + df["Risk_Score"]
df["MAS_Band"] = df["MAS"].apply(band)
df["Primary_Driver"] = df.apply(primary_driver, axis=1)
df["Recommended_Action"] = df.apply(recommended_action, axis=1)
df["Expected_Outcome"] = df.apply(expected_outcome, axis=1)
df["AI_Reasoning"] = df.apply(ai_reasoning, axis=1)
df["Data_Quality"] = df.apply(data_quality, axis=1)
df["Rank"] = df["MAS"].rank(method="first", ascending=False).astype(int)
df = df.sort_values("MAS", ascending=False).reset_index(drop=True)
df["Rank"] = range(1, len(df) + 1)

# =========================
# Management Execution Hub data
# =========================
def owner_for_action(action, driver):
    if action == "Treasury Deep Dive":
        return "Treasury Team"
    if action in ["Strategic Relationship Investment", "Executive Engagement"]:
        return "Coverage Director"
    if action == "Relationship Recovery":
        return "Senior Banker"
    if action == "Credit Review":
        return "Credit Risk"
    if action == "Cross-Border Expansion":
        return "Regional Coverage"
    return "Relationship Manager"


def priority_for_row(row):
    if row["MAS"] >= 61:
        return "High"
    if row["Recommended_Action"] in ["Treasury Deep Dive", "Strategic Relationship Investment", "Relationship Recovery"]:
        return "Medium-High"
    return "Medium"


def due_for_row(row):
    if row["MAS"] >= 61:
        return "30 Days"
    if row["Recommended_Action"] in ["Treasury Deep Dive", "Strategic Relationship Investment"]:
        return "45 Days"
    return "60 Days"


def status_for_row(row):
    mapping = {
        "Toyota": "In Progress",
        "HSBC": "Assigned",
        "DBS": "In Progress",
        "Alibaba": "Not Started",
        "CK Hutchison": "Monitoring",
        "Tencent": "Assigned",
        "TSMC": "Assigned",
        "Jardine Matheson": "Monitoring",
        "BHP": "Not Started",
        "Rio Tinto": "Not Started",
    }
    return mapping.get(row["Company"], "Not Started")


def progress_for_status(status):
    return {
        "Completed": 100,
        "In Progress": 60,
        "Assigned": 30,
        "Monitoring": 20,
        "Not Started": 0,
        "Deferred": 0,
    }.get(status, 0)


def impact_for_action(action):
    return {
        "Treasury Deep Dive": "Deposit / Treasury Wallet",
        "Strategic Relationship Investment": "Executive Connectivity",
        "Executive Engagement": "Senior Management Access",
        "Relationship Recovery": "Revenue Recovery",
        "Credit Review": "Risk Mitigation",
        "Cross-Border Expansion": "Cross-Border Revenue",
        "Portfolio Monitoring": "Relationship Monitoring",
    }.get(action, "Relationship Impact")


def build_execution_df(data):
    rows = []
    for _, r in data.iterrows():
        status = status_for_row(r)
        rows.append({
            "Rank": int(r["Rank"]),
            "Relationship": r["Company"],
            "MAS": float(r["MAS"]),
            "Action": r["Recommended_Action"],
            "Owner": owner_for_action(r["Recommended_Action"], r["Primary_Driver"]),
            "Priority": priority_for_row(r),
            "Due": due_for_row(r),
            "Status": status,
            "Progress_%": progress_for_status(status),
            "Impact": impact_for_action(r["Recommended_Action"]),
            "Next Step": next_step_for_row(r),
        })
    return pd.DataFrame(rows)


def next_step_for_row(row):
    action = row["Recommended_Action"]
    company = row["Company"]
    if action == "Treasury Deep Dive":
        return f"Schedule treasury wallet review for {company}; quantify deposits, FX, cash management and funding needs."
    if action == "Strategic Relationship Investment":
        return f"Confirm executive sponsor for {company}; prepare 30-day senior coverage plan."
    if action == "Relationship Recovery":
        return f"Review relationship deterioration signals for {company}; agree recovery owner and next client touchpoint."
    if action == "Cross-Border Expansion":
        return f"Map regional wallet for {company}; identify cross-border treasury and liquidity opportunities."
    if action == "Credit Review":
        return f"Refresh credit view for {company}; confirm risk appetite and exposure strategy."
    return f"Keep {company} under active monitoring and refresh MAS next cycle."


def follow_up_for_row(row):
    if row["MAS"] >= 61:
        return "Weekly"
    action = row.get("Action", row.get("Recommended_Action", ""))
    if action in ["Treasury Deep Dive", "Strategic Relationship Investment", "Relationship Recovery"]:
        return "Bi-weekly"
    return "Monthly"


def closure_criteria_for_action(action):
    return {
        "Treasury Deep Dive": "Treasury wallet review completed and next product opportunity agreed.",
        "Strategic Relationship Investment": "Executive sponsor assigned and senior client touchpoint completed.",
        "Executive Engagement": "Senior management meeting completed and relationship agenda agreed.",
        "Relationship Recovery": "Recovery plan agreed with accountable owner and next client action logged.",
        "Credit Review": "Credit stance refreshed and exposure strategy confirmed.",
        "Cross-Border Expansion": "Regional wallet map completed and cross-border opportunity pipeline identified.",
        "Portfolio Monitoring": "Next review date set and monitoring rationale documented.",
    }.get(action, "Owner confirms next action and closure evidence before next review.")


def workflow_stage_for_status(status):
    return {
        "Not Started": "1. Triage",
        "Assigned": "2. Owner Assigned",
        "In Progress": "3. Execution",
        "Monitoring": "4. Follow-up",
        "Completed": "5. Closure",
        "Deferred": "Deferred",
    }.get(status, "1. Triage")


def sla_status_for_row(row):
    if row["Priority"] == "High" and row["Status"] in ["Not Started", "Deferred"]:
        return "At Risk"
    if row["Status"] in ["In Progress", "Assigned"]:
        return "On Track"
    if row["Status"] == "Completed":
        return "Closed"
    return "Monitor"


def enrich_execution_workflow(execution):
    out = execution.copy()
    out["Workflow Stage"] = out["Status"].apply(workflow_stage_for_status)
    out["Follow-up Cadence"] = out.apply(follow_up_for_row, axis=1)
    out["Closure Criteria"] = out["Action"].apply(closure_criteria_for_action)
    out["SLA Status"] = out.apply(sla_status_for_row, axis=1)
    out["Management Decision"] = out.apply(
        lambda r: "Escalate to senior sponsor" if r["Priority"] == "High" or r["MAS"] >= 61 else "Track in next portfolio review",
        axis=1,
    )
    return out


execution_df = enrich_execution_workflow(build_execution_df(df))

# =========================
# Export / Memo functions
# =========================
def queue_table(data):
    out = data[["Rank", "Company", "Country", "Sector", "Rating", "Outlook", "MAS", "MAS_Band", "Primary_Driver", "Recommended_Action", "Expected_Outcome"]].copy()
    out["MAS"] = out["MAS"].map(lambda x: f"{x:.1f}")
    return out


def scorecard_table(data):
    out = data[["Company", "Strategic_Score", "Wallet_Score", "Health_Score", "Coverage_Score", "Risk_Score", "MAS", "MAS_Band", "Primary_Driver"]].copy()
    for c in ["Strategic_Score", "Wallet_Score", "Health_Score", "Coverage_Score", "Risk_Score", "MAS"]:
        out[c] = out[c].map(lambda x: f"{x:.1f}")
    return out


def raw_table(data):
    cols = ["Company", "Country", "Sector", "Rating", "Outlook", "Revenue_B", "Revenue_Growth", "EBITDA_Margin", "ROE", "Assets_B", "Debt_B", "Equity_B", "Cash_B", "InterestExpense_B", "MarketCap_B", "EV_B", "Data_Quality"]
    return data[cols].copy()


def build_portfolio_memo(data):
    total_rev = data["Revenue_B"].sum(skipna=True)
    total_assets = data["Assets_B"].sum(skipna=True)
    total_debt = data["Debt_B"].sum(skipna=True)
    avg_mas = data["MAS"].mean()
    top = data.iloc[0]
    attention = int((data["MAS"] >= 61).sum())
    lines = []
    lines.append("# EC-AI Institutional Relationship Management Memo")
    lines.append("")
    lines.append("## Portfolio Universe")
    lines.append(f"- Universe: {len(data)} public company relationships")
    lines.append(f"- Total revenue: {fmt_b(total_rev)}")
    lines.append(f"- Total assets: {fmt_b(total_assets)}")
    lines.append(f"- Total debt: {fmt_b(total_debt)}")
    lines.append(f"- Average MAS: {avg_mas:.1f}")
    lines.append(f"- Relationships requiring management attention: {attention}")
    lines.append("")
    lines.append("## Executive Interpretation")
    lines.append("The portfolio is concentrated in strategic APAC and global institutional relationships across banks, technology, industrials, mining and conglomerates. EC-AI ranks relationships using Management Attention Score v1.2, combining strategic importance, wallet opportunity, relationship health, coverage and risk signals.")
    lines.append("")
    lines.append("## Top Relationships Requiring Management Attention")
    for _, r in data.head(5).iterrows():
        lines.append(f"- {r['Rank']}. {r['Company']}: MAS {r['MAS']:.1f} | Driver: {r['Primary_Driver']} | Action: {r['Recommended_Action']}")
    lines.append("")
    lines.append("## Recommended Management Agenda")
    lines.append(f"1. Open the portfolio review with {top['Company']} as the highest management attention signal.")
    lines.append("2. Review wallet-driven opportunities where debt, enterprise value and funding wallet are material.")
    lines.append("3. Review strategic relationships requiring senior executive engagement and relationship investment.")
    lines.append("4. Investigate any relationships with weak growth, low profitability or incomplete S&P data coverage.")
    lines.append("5. Use relationship-level MAS drivers to assign actions to Coverage, Treasury, Risk and senior management.")
    lines.append("")
    lines.append("## MAS Legend")
    lines.append("- 0-40: Monitor")
    lines.append("- 41-60: Review")
    lines.append("- 61-80: Management Attention")
    lines.append("- 81-100: Executive Attention")
    lines.append("")
    lines.append("---")
    lines.append("Generated by EC-AI Institutional Relationship OS v10.0.3 Alpha | MAS v1.2")
    return "\n".join(lines)


def build_relationship_memo(row):
    lines = []
    lines.append(f"# Relationship Intelligence Memo: {row['Company']}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"{row['Company']} is a {row['MAS_Band']} relationship with MAS {row['MAS']:.1f}. The primary driver is {row['Primary_Driver']}. Recommended action: {row['Recommended_Action']}.")
    lines.append("")
    lines.append("## Relationship Snapshot")
    lines.append(f"- Country: {row['Country']}")
    lines.append(f"- Sector: {row['Sector']}")
    lines.append(f"- Rating / Outlook: {row['Rating']} / {row['Outlook']}")
    lines.append(f"- Revenue: {fmt_b(row['Revenue_B'])}")
    lines.append(f"- Assets: {fmt_b(row['Assets_B'])}")
    lines.append(f"- Debt: {fmt_b(row['Debt_B'])}")
    lines.append(f"- Market Capitalization: {fmt_b(row['MarketCap_B'])}")
    lines.append("")
    lines.append("## MAS Score Breakdown")
    lines.append(f"- Strategic Importance: {row['Strategic_Score']:.1f} / 25")
    lines.append(f"- Wallet Opportunity: {row['Wallet_Score']:.1f} / 25")
    lines.append(f"- Relationship Health: {row['Health_Score']:.1f} / 25")
    lines.append(f"- Coverage Strength: {row['Coverage_Score']:.1f} / 15")
    lines.append(f"- Risk Signals: {row['Risk_Score']:.1f} / 10")
    lines.append("")
    lines.append("## AI Situation Report")
    lines.append(row["AI_Reasoning"])
    lines.append("")
    lines.append("## Expected Outcome")
    lines.append(row["Expected_Outcome"])
    lines.append("")
    lines.append("## Management Recommendation")
    lines.append(f"Assign {row['Company']} to the {row['Recommended_Action']} workflow and review progress at the next management attention meeting.")
    lines.append("")
    lines.append("---")
    lines.append("Generated by EC-AI Institutional Relationship OS v10.0.3 Alpha")
    return "\n".join(lines)


def render_markdown_to_story(text, styles):
    from reportlab.platypus import Paragraph, Spacer
    story = []
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 7))
            continue
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if safe.startswith("# "):
            story.append(Paragraph(safe[2:], styles["ECTitle"]))
        elif safe.startswith("## "):
            story.append(Paragraph(safe[3:], styles["ECH2"]))
        elif safe.startswith("- "):
            story.append(Paragraph("• " + safe[2:], styles["ECBody"]))
        elif re.match(r"^\d+\.\s", safe):
            story.append(Paragraph(safe, styles["ECBody"]))
        elif safe.startswith("---"):
            story.append(Spacer(1, 10))
        else:
            story.append(Paragraph(safe, styles["ECBody"]))
    return story


def build_executive_pack_pdf(data, selected_company=None):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=0.55*inch, rightMargin=0.55*inch, topMargin=0.55*inch, bottomMargin=0.55*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ECTitle", parent=styles["Title"], fontSize=18, leading=22, alignment=TA_LEFT, spaceAfter=12))
    styles.add(ParagraphStyle(name="ECH2", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="ECBody", parent=styles["BodyText"], fontSize=9.4, leading=13.5, spaceAfter=5))
    styles.add(ParagraphStyle(name="ECSmall", parent=styles["BodyText"], fontSize=8.2, leading=10.5, textColor="#4B5563"))
    story = []
    story += render_markdown_to_story(build_portfolio_memo(data), styles)
    story.append(PageBreak())

    story.append(Paragraph("Management Attention Queue", styles["ECTitle"]))
    q = queue_table(data).head(10)
    table_data = [["Rank", "Company", "MAS", "Band", "Driver", "Action"]]
    for _, r in q.iterrows():
        table_data.append([str(r["Rank"]), r["Company"], r["MAS"], r["MAS_Band"], r["Primary_Driver"], r["Recommended_Action"]])
    table = Table(table_data, colWidths=[0.45*inch, 1.3*inch, 0.55*inch, 1.15*inch, 1.4*inch, 1.6*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#071B3A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7.4),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#D8DEE6")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("MAS Formula", styles["ECH2"]))
    story.append(Paragraph("Strategic Importance 25%, Wallet Opportunity 25%, Relationship Health 25%, Coverage Strength 15%, Risk Signals 10%.", styles["ECBody"]))
    story.append(PageBreak())

    target = selected_company or data.iloc[0]["Company"]
    row = data[data["Company"] == target]
    if row.empty:
        row = data.head(1)
    story += render_markdown_to_story(build_relationship_memo(row.iloc[0]), styles)
    story.append(PageBreak())

    story.append(Paragraph("AI Reasoning Extract", styles["ECTitle"]))
    for _, r in data.head(8).iterrows():
        story.append(Paragraph(f"<b>{r['Rank']}. {r['Company']} | MAS {r['MAS']:.1f} | {r['Recommended_Action']}</b>", styles["ECBody"]))
        story.append(Paragraph(r["AI_Reasoning"], styles["ECBody"]))
        story.append(Spacer(1, 6))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Generated by EC-AI Institutional Relationship OS v10.0.3 Alpha | Management Attention Allocation System", styles["ECSmall"]))
    doc.build(story)
    return buf.getvalue()


# =========================
# v9.2.2 Visual / Explainability Helpers
# =========================
MCKINSEY_NAVY = "#071B3A"
MCKINSEY_BLUE = "#365F9C"
MCKINSEY_SKY = "#AFC4DD"
MCKINSEY_STEEL = "#5D6B7A"
MCKINSEY_SLATE = "#9AA4B2"
MCKINSEY_LIGHT = "#E8EEF7"
MCKINSEY_GRAY = "#D8DEE6"
MCKINSEY_ORANGE = "#8C6D31"

MAS_BAND_COLORS = {
    "Executive Attention": "#071B3A",
    "Management Attention": "#365F9C",
    "Review": "#AFC4DD",
    "Monitor": "#D8DEE6",
}

ACTION_COLORS = {
    "Strategic Relationship Investment": MCKINSEY_NAVY,
    "Portfolio Monitoring": MCKINSEY_SLATE,
    "Relationship Recovery": MCKINSEY_BLUE,
    "Treasury Deep Dive": MCKINSEY_ORANGE,
    "Cross-Border Expansion": MCKINSEY_STEEL,
    "Credit Review": "#7A1E1E",
    "Executive Engagement": "#3B4A60",
}

RELATIONSHIP_CHART_COLORS = {
    "Toyota": "#071B3A",
    "HSBC": "#1F4E79",
    "Alibaba": "#365F9C",
    "DBS": "#2A6F97",
    "CK Hutchison": "#4A6FA5",
    "Tencent": "#5D7FA6",
    "TSMC": "#6B8DB5",
    "Jardine Matheson": "#7A8FA8",
    "BHP": "#8D99AE",
    "Rio Tinto": "#A6B3C2",
}


def apply_mckinsey_layout(fig, height=420, title=None):
    fig.update_layout(
        template="plotly_white",
        height=height,
        title=dict(text=title or fig.layout.title.text, font=dict(size=17, color=MCKINSEY_NAVY)),
        font=dict(color=MCKINSEY_NAVY, size=12),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(title=None, orientation="v", font=dict(size=11, color=MCKINSEY_NAVY)),
        margin=dict(l=20, r=20, t=52, b=30),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E6EAF0", zeroline=False, title_font=dict(color=MCKINSEY_STEEL), tickfont=dict(color=MCKINSEY_STEEL))
    fig.update_yaxes(showgrid=False, zeroline=False, title_font=dict(color=MCKINSEY_STEEL), tickfont=dict(color=MCKINSEY_STEEL))
    return fig


def render_explainability_block(row):
    """Render MAS pillar explainability; keeps MAS transparent and safe."""
    values = [
        ("Strategic importance", row.get("Strategic_Score", 0), 25, "Scale: revenue, assets, market cap"),
        ("Wallet opportunity", row.get("Wallet_Score", 0), 25, "Debt, EV, cash, interest expense"),
        ("Relationship health", row.get("Health_Score", 0), 25, "Growth, margin, ROE signals"),
        ("Coverage strength", row.get("Coverage_Score", 0), 15, "Neutral proxy until CRM data"),
        ("Risk signals", row.get("Risk_Score", 0), 10, "Rating and outlook"),
    ]
    cells = []
    for label, val, maxv, desc in values:
        try:
            val_num = float(val)
            pct = max(0, min(100, (val_num / maxv) * 100)) if maxv else 0
            val_txt = f"{val_num:.1f}"
        except Exception:
            pct = 0
            val_txt = "N/A"
        cells.append(f"""
        <div class="explain-cell">
          <div class="explain-label">{label}</div>
          <div class="explain-value">{val_txt}<span style="font-size:12px;color:#6B7A90;"> / {maxv}</span></div>
          <div style="height:7px;background:#E8EEF7;border-radius:999px;overflow:hidden;margin:5px 0 6px;">
            <div style="height:7px;width:{pct:.0f}%;background:#365F9C;border-radius:999px;"></div>
          </div>
          <div class="ec-card-sub">{desc}</div>
        </div>
        """)
    return f"""
    <div class="explain-card">
      <div class="explain-title">Why this relationship appears in the queue</div>
      <div class="ec-text" style="margin-bottom:10px;">
        MAS {float(row.get('MAS', 0)):.1f} is driven primarily by <b>{row.get('Primary_Driver', 'N/A')}</b>.
        The breakdown below shows the five explainable inputs behind the action recommendation.
      </div>
      <div class="explain-grid">{''.join(cells)}</div>
    </div>
    """


def safe_explainability_block(row):
    """Safe wrapper so no tab can fail if explainability rendering encounters unexpected data."""
    try:
        return render_explainability_block(row)
    except Exception:
        company = row.get("Company", "relationship") if hasattr(row, "get") else "relationship"
        return f"""
        <div class="ec-note">
          <b>MAS Explainability</b><br>
          Explainability could not be rendered for {company}. Core MAS score, driver and action remain available.
        </div>
        """


def render_explainability_native(row):
    """Native Streamlit MAS explainability cards. Avoids raw HTML rendering bugs."""
    try:
        company = row.get("Company", "relationship")
        mas = float(row.get("MAS", 0))
        driver = row.get("Primary_Driver", "N/A")
        st.markdown(
            f"""
            <div class="explain-card">
              <div class="explain-title">Why this relationship appears in the queue</div>
              <div class="ec-text" style="margin-bottom:10px;">
                MAS {mas:.1f} is driven primarily by <b>{driver}</b>.
                The breakdown below shows the five explainable inputs behind the action recommendation.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        pillars = [
            ("Strategic Importance", float(row.get("Strategic_Score", 0)), 25, "Scale: revenue, assets, market cap"),
            ("Wallet Opportunity", float(row.get("Wallet_Score", 0)), 25, "Debt, EV, cash, interest expense"),
            ("Relationship Health", float(row.get("Health_Score", 0)), 25, "Growth, margin, ROE signals"),
            ("Coverage Strength", float(row.get("Coverage_Score", 0)), 15, "Neutral proxy until CRM data"),
            ("Risk Signals", float(row.get("Risk_Score", 0)), 10, "Rating and outlook"),
        ]
        cols = st.columns(5, gap="small")
        for col, (label, score, max_score, desc) in zip(cols, pillars):
            with col:
                st.markdown(
                    f"""
                    <div class="rw-card">
                      <div class="rw-card-label">{label}</div>
                      <div class="rw-card-value">{score:.1f}<span style="font-size:13px;color:#526173;"> / {max_score}</span></div>
                      <div style="height:7px;background:#E8EEF7;border-radius:999px;overflow:hidden;margin:7px 0 8px;">
                        <div style="height:7px;width:{max(0,min(100,score/max_score*100)):.0f}%;background:#365F9C;border-radius:999px;"></div>
                      </div>
                      <div class="ec-card-sub">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    except Exception:
        company = row.get("Company", "relationship") if hasattr(row, "get") else "relationship"
        st.markdown(f"<div class='ec-note'><b>MAS Explainability</b><br>Could not render details for {company}. Core MAS score, driver and action remain available.</div>", unsafe_allow_html=True)


# =========================
# Relationship 360 Helpers v10.0.3 Alpha
# =========================
def relationship_timeline(company: str):
    base = {
        "Toyota": [
            ("Jan 2026", "Executive relationship review completed; strategic importance confirmed."),
            ("Mar 2026", "Capital structure review identified large funding wallet and DCM opportunity."),
            ("May 2026", "MAS moved into Management Attention band due to scale and wallet opportunity."),
            ("Jun 2026", "Strategic Relationship Investment workflow recommended."),
        ],
        "DBS": [
            ("Jan 2026", "Regional financial institution coverage review completed."),
            ("Apr 2026", "Treasury and liquidity wallet opportunity flagged by S&P balance sheet profile."),
            ("Jun 2026", "Treasury Deep Dive assigned to Treasury Team and Coverage."),
        ],
        "CK Hutchison": [
            ("Feb 2026", "Conglomerate relationship flagged for cross-segment complexity."),
            ("Apr 2026", "Growth momentum weakened; relationship health driver increased."),
            ("Jun 2026", "Relationship Recovery workflow recommended for senior coverage follow-up."),
        ],
        "TSMC": [
            ("Jan 2026", "Strategic franchise review completed; AA- external rating confirmed."),
            ("May 2026", "High growth and profitability metrics confirmed strong franchise quality."),
            ("Jun 2026", "Strategic Relationship Investment recommended to protect senior connectivity."),
        ],
        "Tencent": [
            ("Feb 2026", "Technology relationship review completed."),
            ("May 2026", "Growth and international ecosystem signals suggest cross-border opportunity."),
            ("Jun 2026", "Cross-Border Expansion workflow recommended."),
        ],
    }
    return base.get(company, [
        ("Jan 2026", "Relationship entered EC-AI public company universe."),
        ("Apr 2026", "S&P financial and credit signals refreshed."),
        ("Jun 2026", "MAS v1.2 action recommendation generated."),
    ])


def relationship_network(row):
    action = row.get("Recommended_Action", "Portfolio Monitoring")
    core = ["Coverage", "Relationship Manager", "Country Head"]
    if "Treasury" in action:
        core += ["Treasury", "Liquidity Solutions", "FX"]
    elif "Recovery" in action:
        core += ["Senior Banker", "Credit", "Treasury"]
    elif "Cross-Border" in action:
        core += ["Regional Coverage", "Treasury", "Transaction Banking"]
    elif "Strategic" in action:
        core += ["Coverage Director", "Senior Sponsor", "Treasury", "DCM"]
    else:
        core += ["Portfolio Monitoring", "Risk", "Coverage"]
    return list(dict.fromkeys(core))


def product_penetration(row):
    company = row.get("Company", "")
    action = row.get("Recommended_Action", "")
    debt = safe_float(row.get("Debt_B"), 0) or 0
    cash = safe_float(row.get("Cash_B"), 0) or 0
    sector = str(row.get("Sector", ""))
    products = []
    products.append(["Loans", "Strong" if debt > 50 else "Medium", "Balance sheet funding relationship potential"])
    products.append(["Deposits / Liquidity", "Strong" if cash > 50 else "Medium" if cash > 10 else "Low", "Cash and liquidity pool indicator"])
    products.append(["Treasury", "Low" if "Treasury" in action or debt > 80 else "Medium", "FX, liquidity and treasury wallet opportunity"])
    products.append(["DCM", "Low" if debt > 50 else "Medium", "Debt stack suggests bond/refinancing review"])
    products.append(["ECM / Advisory", "Medium" if sector not in ["Banks"] else "Low", "Strategic dialogue and capital markets optionality"])
    products.append(["Cross-Border", "Strong" if company in ["Toyota", "HSBC", "Tencent", "Alibaba", "CK Hutchison", "Jardine Matheson"] else "Medium", "Regional footprint and multi-market operating model"])
    return pd.DataFrame(products, columns=["Product", "Penetration / Potential", "Rationale"])


def status_badge(status: str) -> str:
    cls = {"Strong":"product-strong", "Medium":"product-medium", "Low":"product-low"}.get(status, "product-medium")
    return f'<span class="{cls}">{status}</span>'


# =========================
# Wallet Sizing Engine v1.0 (v10.0.3)
# =========================
WALLET_INPUT_COLUMNS = [
    "Company", "Public_Private", "Financial_Data_Source",
    "Total_Debt_B", "Cash_And_Equivalents_B",
    "MUFG_Exposure_B", "MUFG_Deposits_B",
    "MUFG_TB_Revenue_M", "MUFG_GM_Revenue_M",
    "Coalition_TB_Wallet_M", "Coalition_GM_Wallet_M",
    "Current_MUFG_Revenue_M", "Data_Confidence",
]


def wallet_template(base_df: pd.DataFrame) -> pd.DataFrame:
    """Blank internal-data template. Public-company balance-sheet fields are prefilled from S&P."""
    out = pd.DataFrame({
        "Company": base_df["Company"],
        "Public_Private": "Public",
        "Financial_Data_Source": "S&P",
        "Total_Debt_B": base_df["Debt_B"],
        "Cash_And_Equivalents_B": base_df["Cash_B"],
        "MUFG_Exposure_B": pd.NA,
        "MUFG_Deposits_B": pd.NA,
        "MUFG_TB_Revenue_M": pd.NA,
        "MUFG_GM_Revenue_M": pd.NA,
        "Coalition_TB_Wallet_M": pd.NA,
        "Coalition_GM_Wallet_M": pd.NA,
        "Current_MUFG_Revenue_M": pd.NA,
        "Data_Confidence": "To Validate",
    })
    return out[WALLET_INPUT_COLUMNS]


def illustrative_wallet_data(base_df: pd.DataFrame) -> pd.DataFrame:
    """Illustrative placeholders only; never presented as MUFG actuals."""
    out = wallet_template(base_df)
    debt = pd.to_numeric(out["Total_Debt_B"], errors="coerce").fillna(0)
    cash = pd.to_numeric(out["Cash_And_Equivalents_B"], errors="coerce").fillna(0)
    # Deterministic placeholders to keep the demo functional.
    out["MUFG_Exposure_B"] = (debt * 0.035).round(3)
    out["MUFG_Deposits_B"] = (cash * 0.025).round(3)
    out["MUFG_TB_Revenue_M"] = (cash * 0.55).clip(lower=1.5).round(1)
    out["MUFG_GM_Revenue_M"] = (debt * 0.11).clip(lower=1.0).round(1)
    out["Coalition_TB_Wallet_M"] = (cash * 4.2).clip(lower=8).round(1)
    out["Coalition_GM_Wallet_M"] = (debt * 1.15).clip(lower=8).round(1)
    out["Current_MUFG_Revenue_M"] = (out["MUFG_TB_Revenue_M"] + out["MUFG_GM_Revenue_M"]).round(1)
    out["Data_Confidence"] = "Illustrative"
    return out


def safe_rate(numerator, denominator):
    n = pd.to_numeric(pd.Series([numerator]), errors="coerce").iloc[0]
    d = pd.to_numeric(pd.Series([denominator]), errors="coerce").iloc[0]
    if pd.isna(n) or pd.isna(d) or d <= 0:
        return None
    return float(n / d)


def build_wallet_engine(wallet_input: pd.DataFrame) -> pd.DataFrame:
    out = wallet_input.copy()
    numeric_cols = [c for c in WALLET_INPUT_COLUMNS if c.endswith("_B") or c.endswith("_M")]
    for c in numeric_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["Lending_Capture_Rate"] = out.apply(lambda r: safe_rate(r["MUFG_Exposure_B"], r["Total_Debt_B"]), axis=1)
    out["Deposit_Capture_Rate"] = out.apply(lambda r: safe_rate(r["MUFG_Deposits_B"], r["Cash_And_Equivalents_B"]), axis=1)
    out["TB_Capture_Rate"] = out.apply(lambda r: safe_rate(r["MUFG_TB_Revenue_M"], r["Coalition_TB_Wallet_M"]), axis=1)
    out["GM_Capture_Rate"] = out.apply(lambda r: safe_rate(r["MUFG_GM_Revenue_M"], r["Coalition_GM_Wallet_M"]), axis=1)
    out["Estimated_Total_Wallet_M"] = out[["Coalition_TB_Wallet_M", "Coalition_GM_Wallet_M"]].sum(axis=1, min_count=1)
    fallback_current = out[["MUFG_TB_Revenue_M", "MUFG_GM_Revenue_M"]].sum(axis=1, min_count=1)
    out["Current_MUFG_Revenue_M"] = out["Current_MUFG_Revenue_M"].fillna(fallback_current)
    out["Total_Wallet_Capture_Rate"] = out.apply(lambda r: safe_rate(r["Current_MUFG_Revenue_M"], r["Estimated_Total_Wallet_M"]), axis=1)
    out["Wallet_Gap_M"] = (out["Estimated_Total_Wallet_M"] - out["Current_MUFG_Revenue_M"]).clip(lower=0)

    def opportunity(r):
        rates = {
            "Lending / DCM": r.get("Lending_Capture_Rate"),
            "Deposits / Liquidity": r.get("Deposit_Capture_Rate"),
            "Transaction Banking": r.get("TB_Capture_Rate"),
            "Global Markets": r.get("GM_Capture_Rate"),
        }
        valid = {k: v for k, v in rates.items() if v is not None and not pd.isna(v)}
        return min(valid, key=valid.get) if valid else "Data Validation"
    out["Primary_Wallet_Opportunity"] = out.apply(opportunity, axis=1)
    return out


def fmt_rate(x):
    return "N/A" if x is None or pd.isna(x) else f"{x*100:.1f}%"


def wallet_reasoning(row) -> str:
    opp = row.get("Primary_Wallet_Opportunity", "Data Validation")
    gap = row.get("Wallet_Gap_M")
    if opp == "Lending / DCM":
        rationale = "Low lending capture relative to the client's total debt indicates lending, refinancing and DCM potential."
    elif opp == "Deposits / Liquidity":
        rationale = "Low deposit capture relative to cash and cash equivalents indicates liquidity and operating-balance potential."
    elif opp == "Transaction Banking":
        rationale = "Low TB capture versus the Coalition benchmark indicates cash-management, payments and trade opportunity."
    elif opp == "Global Markets":
        rationale = "Low GM capture versus the Coalition benchmark indicates FX, rates and hedging opportunity."
    else:
        rationale = "Complete and validate internal and external wallet fields before prioritising a product action."
    gap_text = "N/A" if pd.isna(gap) else f"USD {gap:,.1f}M"
    return f"Primary opportunity: {opp}. {rationale} Estimated revenue wallet gap: {gap_text}."


# =============================================================================
# STAGE 1-C.1 — MASTER APP SHELL
# =============================================================================
# IMPORTANT MIGRATION BOUNDARY
# ----------------------------
# Everything above this point is the retained v10 institutional backend:
# S&P data, Score/MAS v1.2, recommendation logic, execution workflow,
# memo/PDF export functions, visual helpers, Relationship 360 helpers and
# Wallet Sizing Engine v1.0.
#
# Stage 1-C replaces the application shell and primary navigation, while
# mapping proven v10 content into the six locked workspaces as a functional
# migration bridge. The legacy ten-tab source remains below st.stop() for
# reference and is intentionally not executed.

@dataclass(frozen=True)
class Workspace:
    key: str
    label: str
    eyebrow: str
    title: str
    subtitle: str


WORKSPACES: Dict[str, Workspace] = {
    "briefing": Workspace(
        key="briefing",
        label="Executive Briefing",
        eyebrow="EXECUTIVE REVIEW",
        title="Executive Briefing",
        subtitle="What requires management attention now, what changed, and what should be reviewed next.",
    ),
    "review": Workspace(
        key="review",
        label="Review",
        eyebrow="MANAGEMENT REVIEW",
        title="Review",
        subtitle="Work through material relationship issues, management questions and recommendations requiring judgement.",
    ),
    "relationships": Workspace(
        key="relationships",
        label="Relationships",
        eyebrow="RELATIONSHIP INTELLIGENCE",
        title="Relationships",
        subtitle="Understand each institutional relationship in context: performance, wallet, signals, history and next actions.",
    ),
    "decisions": Workspace(
        key="decisions",
        label="Decisions",
        eyebrow="MANAGEMENT DECISIONS",
        title="Decisions",
        subtitle="Capture approved, modified, deferred and rejected management decisions with a clear audit trail.",
    ),
    "execution": Workspace(
        key="execution",
        label="Execution",
        eyebrow="MANAGEMENT EXECUTION",
        title="Execution",
        subtitle="Track implementation, exceptions, ownership, due dates and outcomes for actions that require execution.",
    ),
    "portfolio": Workspace(
        key="portfolio",
        label="Portfolio",
        eyebrow="PORTFOLIO INTELLIGENCE",
        title="Portfolio",
        subtitle="Identify material portfolio patterns, attention signals and relationships that should be promoted into Review.",
    ),
}

NAV_ORDER = ["briefing", "review", "relationships", "decisions", "execution", "portfolio"]
LABEL_TO_KEY = {WORKSPACES[k].label: k for k in NAV_ORDER}
KEY_TO_LABEL = {k: WORKSPACES[k].label for k in NAV_ORDER}


# =============================================================================
# CENTRALIZED STAGE 1-B DESIGN TOKENS / SHELL STYLING
# =============================================================================
STAGE_1C_SHELL_CSS = r"""
<style>
:root {
    --ec-navy-950:#071B3A;
    --ec-navy-900:#0B2C55;
    --ec-blue-700:#365F9C;
    --ec-blue-500:#5D7FA6;
    --ec-blue-200:#AFC4DD;
    --ec-slate-700:#526173;
    --ec-slate-500:#7B8794;
    --ec-slate-300:#C7D0DA;
    --ec-slate-200:#D8DEE6;
    --ec-slate-100:#E8EEF3;
    --ec-slate-050:#F5F7FA;
    --ec-white:#FFFFFF;
    --ec-green:#2F855A;
    --ec-amber:#9A6A1F;
    --ec-red:#9B2C2C;
    --ec-radius-sm:8px;
    --ec-radius-md:12px;
    --ec-radius-lg:16px;
    --ec-shadow-sm:0 1px 2px rgba(15,23,42,.04);
    --ec-shadow-md:0 4px 14px rgba(15,23,42,.055);
}

html, body, [class*="css"] {
    font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
}
.stApp { background:var(--ec-slate-050); color:var(--ec-navy-950); }
#MainMenu { visibility:hidden; }
footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent; height:0; }

/* Locked desktop reference canvas */
.block-container {
    max-width:1440px !important;
    padding-top:1.35rem !important;
    padding-bottom:2.5rem !important;
    padding-left:2.15rem !important;
    padding-right:2.15rem !important;
}

/* Persistent navigation rail */
section[data-testid="stSidebar"] {
    width:248px !important;
    min-width:248px !important;
    background:linear-gradient(180deg,#071B3A 0%,#0B2C55 100%) !important;
    border-right:1px solid rgba(255,255,255,.08);
}
section[data-testid="stSidebar"] > div { width:248px !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top:.8rem; }

.ec-brand { padding:10px 6px 20px; border-bottom:1px solid rgba(255,255,255,.14); margin-bottom:15px; }
.ec-brand-mark { color:#FFF; font-size:25px; font-weight:900; letter-spacing:-.03em; line-height:1; }
.ec-brand-product { color:#DCE7F4; font-size:12.5px; font-weight:700; line-height:1.35; margin-top:7px; }
.ec-brand-stage { display:inline-block; margin-top:10px; color:#C7D8EC; font-size:10.5px; font-weight:800; letter-spacing:.07em; text-transform:uppercase; }
.ec-sidebar-section { color:#9FB4CD; font-size:10.5px; font-weight:850; text-transform:uppercase; letter-spacing:.08em; margin:18px 6px 8px; }

section[data-testid="stSidebar"] div[role="radiogroup"] { gap:4px; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label {
    min-height:42px; padding:0 12px !important; border-radius:9px; display:flex; align-items:center;
    border:1px solid transparent; transition:background .12s ease,border-color .12s ease;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background:rgba(255,255,255,.075); }
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
    background:#FFF; border-color:rgba(255,255,255,.96); box-shadow:0 2px 8px rgba(0,0,0,.10);
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label p { color:#E7EEF7 !important; font-size:14px !important; font-weight:760 !important; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p { color:#071B3A !important; font-weight:850 !important; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display:none; }
section[data-testid="stSidebar"] div[role="radiogroup"] [data-testid="stMarkdownContainer"] { margin:0; }

/* Sidebar selectbox remains legible on navy */
section[data-testid="stSidebar"] label p { color:#DCE7F4 !important; }
section[data-testid="stSidebar"] [data-baseweb="select"] > div { background:rgba(255,255,255,.10); border-color:rgba(255,255,255,.18); }
section[data-testid="stSidebar"] [data-baseweb="select"] span { color:#FFFFFF !important; }

.ec-sidebar-context { margin:11px 6px 0; padding:12px 13px; border-radius:11px; background:rgba(255,255,255,.075); border:1px solid rgba(255,255,255,.13); }
.ec-sidebar-context-label { color:#9FB4CD; font-size:10px; font-weight:850; letter-spacing:.06em; text-transform:uppercase; }
.ec-sidebar-context-value { color:#FFF; font-size:13px; font-weight:760; margin-top:4px; line-height:1.35; }
.ec-sidebar-engine { color:#AFC4DD; font-size:11px; line-height:1.55; margin:14px 7px 0; }

/* Page identity */
.ec-shell-topbar { display:flex; align-items:flex-start; justify-content:space-between; gap:24px; padding:2px 0 18px; border-bottom:1px solid var(--ec-slate-200); margin-bottom:23px; }
.ec-page-eyebrow { color:var(--ec-blue-700); font-size:11px; font-weight:900; letter-spacing:.085em; text-transform:uppercase; margin-bottom:7px; }
.ec-page-title { color:var(--ec-navy-950); font-size:31px; line-height:1.06; font-weight:900; letter-spacing:-.035em; margin:0; }
.ec-page-subtitle { color:var(--ec-slate-700); font-size:14.5px; line-height:1.48; max-width:820px; margin-top:8px; }
.ec-top-context { display:flex; align-items:stretch; gap:8px; padding-top:2px; flex-shrink:0; }
.ec-context-chip { background:#FFF; border:1px solid var(--ec-slate-200); border-radius:10px; padding:9px 12px; min-width:116px; box-shadow:var(--ec-shadow-sm); }
.ec-context-chip-label { color:var(--ec-slate-500); font-size:9.5px; font-weight:850; text-transform:uppercase; letter-spacing:.06em; }
.ec-context-chip-value { color:var(--ec-navy-950); font-size:12.5px; font-weight:820; margin-top:3px; }

/* Stage 1-C.2 shared workspace polish */
.ec-workspace { min-height:0; }
.ec-card { min-height:112px; display:flex; flex-direction:column; justify-content:flex-start; }
.ec-card-value { overflow-wrap:anywhere; }
.ec-table-title { margin-top:18px !important; margin-bottom:9px !important; }
.ec-note { margin-top:10px !important; margin-bottom:16px !important; }
.stage1c-rel-grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; align-items:stretch; margin-top:10px; }
.stage1c-rel-grid .rel360-panel-clean { min-height:338px; height:100%; box-sizing:border-box; }
.stage1c-rel-grid .product-table-clean table { table-layout:fixed; }
.stage1c-rel-grid .product-table-clean th:nth-child(1), .stage1c-rel-grid .product-table-clean td:nth-child(1) { width:24%; }
.stage1c-rel-grid .product-table-clean th:nth-child(2), .stage1c-rel-grid .product-table-clean td:nth-child(2) { width:25%; }
.stage1c-rel-grid .product-table-clean th:nth-child(3), .stage1c-rel-grid .product-table-clean td:nth-child(3) { width:51%; }
div[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; }
div[data-testid="stDataFrame"] [role="columnheader"] { font-weight:800 !important; }

/* Stage 1-C.1 workspace frame */
.ec-build-placeholder { background:#FFF; border:1px solid var(--ec-slate-200); border-radius:14px; padding:22px 24px; box-shadow:var(--ec-shadow-sm); }
.ec-build-placeholder-kicker { color:var(--ec-blue-700); font-size:10.5px; font-weight:900; text-transform:uppercase; letter-spacing:.07em; }
.ec-build-placeholder-title { color:var(--ec-navy-950); font-size:18px; font-weight:850; margin-top:6px; }
.ec-build-placeholder-copy { color:var(--ec-slate-700); font-size:14px; line-height:1.5; margin-top:6px; max-width:800px; }
.ec-engine-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:11px; margin-top:18px; }
.ec-engine-card { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:11px; padding:12px 13px; min-height:78px; }
.ec-engine-label { color:#7B8794; font-size:9.5px; font-weight:900; text-transform:uppercase; letter-spacing:.055em; }
.ec-engine-value { color:#071B3A; font-size:16px; font-weight:900; margin-top:5px; }
.ec-engine-sub { color:#526173; font-size:10.5px; margin-top:3px; }
.ec-shell-footer { color:var(--ec-slate-500); font-size:11px; padding-top:28px; margin-top:32px; border-top:1px solid var(--ec-slate-200); }

@media (max-width:1100px) {
    .block-container { padding-left:1.2rem !important; padding-right:1.2rem !important; }
    .ec-shell-topbar { flex-direction:column; }
    .ec-top-context { width:100%; flex-wrap:wrap; }
    .ec-engine-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .stage1c-rel-grid { grid-template-columns:1fr; }
}
</style>
"""
st.markdown(STAGE_1C_SHELL_CSS, unsafe_allow_html=True)


# =============================================================================
# SHARED APPLICATION STATE CONTRACT
# =============================================================================
def init_stage_1c_state():
    defaults = {
        "active_page": "briefing",
        "selected_relationship": None,
        "active_review_item_id": None,
        "active_decision_id": None,
        "active_execution_action_id": None,
        "active_portfolio_signal_id": None,
        "review_cycle": "Current Review",
        "portfolio_universe": "Top 10 Public Relationships",
        "data_mode": "S&P Public Company Baseline",
        "shell_version": "Stage 1-C.6",
        "decision_history": [],
        "decision_execution_actions": [],
        "decision_flash": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_stage_1c_sidebar():
    st.sidebar.markdown(
        """
        <div class="ec-brand">
            <div class="ec-brand-mark">EC-AI</div>
            <div class="ec-brand-product">Executive Review Workspace</div>
            <div class="ec-brand-stage">Stage 1-C · Implementation</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<div class="ec-sidebar-section">Workspace</div>', unsafe_allow_html=True)

    current_key = st.session_state.get("active_page", "briefing")
    current_label = KEY_TO_LABEL.get(current_key, KEY_TO_LABEL["briefing"])
    nav_labels = [KEY_TO_LABEL[k] for k in NAV_ORDER]
    selected_label = st.sidebar.radio(
        "Primary navigation",
        options=nav_labels,
        index=nav_labels.index(current_label),
        label_visibility="collapsed",
        key="stage_1c_primary_navigation",
    )
    selected_key = LABEL_TO_KEY[selected_label]
    st.session_state.active_page = selected_key

    st.sidebar.markdown('<div class="ec-sidebar-section">Context</div>', unsafe_allow_html=True)
    relationship_options = ["Portfolio context"] + df["Company"].tolist()
    current_rel = st.session_state.get("selected_relationship") or "Portfolio context"
    if current_rel not in relationship_options:
        current_rel = "Portfolio context"
    selected_rel = st.sidebar.selectbox(
        "Relationship",
        relationship_options,
        index=relationship_options.index(current_rel),
        key="stage_1c_relationship_context",
    )
    st.session_state.selected_relationship = None if selected_rel == "Portfolio context" else selected_rel

    st.sidebar.markdown(
        f"""
        <div class="ec-sidebar-context">
            <div class="ec-sidebar-context-label">Review Cycle</div>
            <div class="ec-sidebar-context-value">{st.session_state.review_cycle}</div>
        </div>
        <div class="ec-sidebar-context">
            <div class="ec-sidebar-context-label">Universe</div>
            <div class="ec-sidebar-context-value">{len(df)} public relationships</div>
        </div>
        <div class="ec-sidebar-engine">
            Backend retained<br>
            Score / MAS v1.2 · Action Matrix · Wallet Sizing · Execution Workflow · PDF/Memo Engine
        </div>
        """,
        unsafe_allow_html=True,
    )
    return selected_key


def render_stage_1c_topbar(workspace):
    relationship_context = st.session_state.selected_relationship or "Portfolio"
    st.markdown(
        f"""
        <div class="ec-shell-topbar">
            <div>
                <div class="ec-page-eyebrow">{workspace.eyebrow}</div>
                <div class="ec-page-title">{workspace.title}</div>
                <div class="ec-page-subtitle">{workspace.subtitle}</div>
            </div>
            <div class="ec-top-context">
                <div class="ec-context-chip">
                    <div class="ec-context-chip-label">Review Cycle</div>
                    <div class="ec-context-chip-value">{st.session_state.review_cycle}</div>
                </div>
                <div class="ec-context-chip">
                    <div class="ec-context-chip-label">Context</div>
                    <div class="ec-context-chip-value">{relationship_context}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _stage1c_metric_row(cards):
    """Render a compact row of executive metrics using retained v10 card styles."""
    cols = st.columns(len(cards), gap="small")
    for col, (label, value, sub) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="ec-card">
                    <div class="ec-card-label">{label}</div>
                    <div class="ec-card-value">{value}</div>
                    <div class="ec-card-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _stage1c_dataframe(data, *, height=320, column_config=None):
    """Shared executive table renderer for Stage 1-C.2."""
    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
        height=height,
        column_config=column_config or {},
    )


def _decision_history_df():
    """Return decision audit history as a dataframe (latest first)."""
    records = st.session_state.get("decision_history", [])
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).iloc[::-1].reset_index(drop=True)


def _latest_decision_by_relationship():
    """Return the latest decision record for each relationship."""
    latest = {}
    for record in st.session_state.get("decision_history", []):
        latest[record.get("Relationship")] = record
    return latest


def _next_stage1c_id(prefix: str, collection_key: str) -> str:
    """Generate compact human-readable IDs within the current Streamlit session."""
    return f"{prefix}-{len(st.session_state.get(collection_key, [])) + 1:04d}"


def _execution_fields_for_decision(row, final_action: str):
    """Derive sensible execution defaults from retained v10 engines without changing their rules."""
    row_copy = row.copy()
    row_copy["Recommended_Action"] = final_action
    owner = owner_for_action(final_action, row_copy.get("Primary_Driver", ""))
    due = due_for_row(row_copy)
    next_step = next_step_for_row(row_copy)
    closure = closure_criteria_for_action(final_action)
    return owner, due, next_step, closure


def _record_stage1c_decision(
    row,
    *,
    decision: str,
    final_action: str,
    rationale: str,
    decision_owner: str,
    decision_date,
    requires_execution: bool,
    execution_owner: str | None = None,
    execution_due: str | None = None,
    execution_next_step: str | None = None,
):
    """Persist one management decision in session state and optionally create an execution action."""
    if decision not in {"Approved", "Modified", "Deferred", "Rejected"}:
        raise ValueError("Unsupported management decision.")

    execution_id = None
    if decision in {"Deferred", "Rejected"}:
        requires_execution = False

    decision_id = _next_stage1c_id("DEC", "decision_history")

    if requires_execution:
        execution_id = _next_stage1c_id("ACT", "decision_execution_actions")
        default_owner, default_due, default_next, default_closure = _execution_fields_for_decision(row, final_action)
        row_for_execution = row.copy()
        row_for_execution["Recommended_Action"] = final_action
        action_record = {
            "Execution Action ID": execution_id,
            "Decision ID": decision_id,
            "Relationship": row["Company"],
            "Score": float(row["MAS"]),
            "Action": final_action,
            "Owner": execution_owner or default_owner,
            "Priority": priority_for_row(row_for_execution),
            "Due": execution_due or default_due,
            "Status": "Assigned",
            "Progress_%": 0,
            "Follow-up Cadence": "Weekly" if float(row["MAS"]) >= 61 else "Bi-weekly",
            "SLA Status": "On Track",
            "Impact": impact_for_action(final_action),
            "Next Step": execution_next_step or default_next,
            "Closure Criteria": default_closure,
            "Outcome": "Pending",
            "Created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        st.session_state.decision_execution_actions.append(action_record)

    record = {
        "Decision ID": decision_id,
        "Decision Date": decision_date.strftime("%Y-%m-%d") if hasattr(decision_date, "strftime") else str(decision_date),
        "Relationship": row["Company"],
        "Score": float(row["MAS"]),
        "Attention Rating": row["MAS_Band"],
        "Original Recommendation": row["Recommended_Action"],
        "Management Decision": decision,
        "Final Action": final_action,
        "Rationale": rationale.strip(),
        "Decision Owner": decision_owner.strip(),
        "Execution Required": "Yes" if requires_execution else "No",
        "Execution Action ID": execution_id or "—",
        "Recorded": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    st.session_state.decision_history.append(record)
    st.session_state.active_decision_id = decision_id
    if execution_id:
        st.session_state.active_execution_action_id = execution_id
    return record


def _selected_relationship_row(default_to_top=True):
    selected = st.session_state.get("selected_relationship")
    if selected and selected in df["Company"].tolist():
        return df[df["Company"] == selected].iloc[0]
    return df.iloc[0] if default_to_top and len(df) else None


def render_stage_1c_briefing():
    """Functional bridge: legacy executive/queue intelligence inside the new shell."""
    total_revenue = df["Revenue_B"].sum(skipna=True)
    avg_score = float(df["MAS"].mean())
    attention_count = int((df["MAS"] >= 61).sum())
    open_actions = int((execution_df["Status"] != "Completed").sum())
    top = df.iloc[0]

    st.markdown(
        f"""
        <div class="ec-note">
          <b>Executive Summary</b><br>
          EC-AI identifies <b>{attention_count}</b> relationship(s) at Management Attention or above.
          The highest-ranked relationship is <b>{top['Company']}</b> with Score <b>{top['MAS']:.1f}</b>,
          driven by <b>{top['Primary_Driver']}</b>. Recommended action: <b>{top['Recommended_Action']}</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    _stage1c_metric_row([
        ("Relationships", f"{len(df)}", "Public-company universe"),
        ("Average Score", f"{avg_score:.1f}", "Portfolio attention level"),
        ("Attention", f"{attention_count}", "Score ≥ 61"),
        ("Open Actions", f"{open_actions}", "Execution workflow"),
        ("Total Revenue", fmt_b(total_revenue), "S&P relationship universe"),
    ])

    st.markdown('<div class="ec-table-title">Top Relationships Requiring Management Attention</div>', unsafe_allow_html=True)
    q = queue_table(df).head(6).copy()
    # Keep the external credit rating distinct from EC-AI's attention rating.
    # Streamlit/PyArrow requires unique dataframe column names.
    q = q.rename(columns={
        "Rank": "Priority",
        "Company": "Relationship",
        "Rating": "External Rating",
        "MAS": "Score",
        "MAS_Band": "Attention Rating",
        "Primary_Driver": "Primary Driver",
        "Recommended_Action": "Recommendation",
        "Expected_Outcome": "Expected Outcome",
    })
    _stage1c_dataframe(
        q,
        height=270,
        column_config={
            "Priority": st.column_config.NumberColumn("Priority", width="small"),
            "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
            "Country": st.column_config.TextColumn("Country", width="small"),
            "Sector": st.column_config.TextColumn("Sector", width="medium"),
            "External Rating": st.column_config.TextColumn("External Rating", width="small"),
            "Outlook": st.column_config.TextColumn("Outlook", width="small"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Attention Rating": st.column_config.TextColumn("Attention Rating", width="medium"),
            "Primary Driver": st.column_config.TextColumn("Primary Driver", width="medium"),
            "Recommendation": st.column_config.TextColumn("Recommendation", width="large"),
            "Expected Outcome": st.column_config.TextColumn("Expected Outcome", width="large"),
        },
    )

    c1, c2 = st.columns([1.75, 1], gap="large")
    with c1:
        mas_plot_df = df.sort_values("MAS")
        briefing_bar_colors = [RELATIONSHIP_CHART_COLORS.get(c, MCKINSEY_BLUE) for c in mas_plot_df["Company"]]
        fig = go.Figure(
            go.Bar(
                x=mas_plot_df["MAS"],
                y=mas_plot_df["Company"],
                orientation="h",
                text=[f"{v:.1f}" for v in mas_plot_df["MAS"]],
                textposition="outside",
                marker=dict(color=briefing_bar_colors),
                hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}<extra></extra>",
            )
        )
        fig.update_traces(textfont=dict(size=12), cliponaxis=False)
        apply_mckinsey_layout(fig, height=430)
        fig.update_layout(
            title="Management Attention by Relationship",
            showlegend=False,
            xaxis_title="Score",
            yaxis_title="",
            bargap=0.24,
            margin=dict(l=20, r=48, t=52, b=30),
        )
        fig.update_xaxes(range=[0, max(70, float(mas_plot_df["MAS"].max()) + 8)], dtick=10)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        action_mix = df["Recommended_Action"].value_counts().reset_index()
        action_mix.columns = ["Action", "Count"]
        fig2 = px.pie(
            action_mix,
            values="Count",
            names="Action",
            title="Recommended Action Mix",
            color="Action",
            color_discrete_map=ACTION_COLORS,
            hole=0.58,
        )
        fig2.update_traces(textinfo="percent", marker=dict(line=dict(color="white", width=2.5)), pull=0)
        apply_mckinsey_layout(fig2, height=430)
        fig2.update_layout(legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02))
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="ec-table-title">Recommended Management Agenda</div>', unsafe_allow_html=True)
    agenda = [
        f"Open with {top['Company']} as the highest management-attention signal.",
        "Separate wallet-led growth opportunities from relationship-health remediation issues.",
        "Confirm which recommendations require management judgement in Review.",
        "Move approved actions requiring implementation into Execution with an accountable owner.",
    ]
    st.markdown("<div class='ec-note'><ol>" + "".join([f"<li>{x}</li>" for x in agenda]) + "</ol></div>", unsafe_allow_html=True)


def render_stage_1c_review():
    """Functional bridge for management review using the retained attention queue and explainability."""
    attention = df[df["MAS"] >= 41].copy().sort_values("MAS", ascending=False)
    high = int((df["MAS"] >= 61).sum())
    review_count = int(((df["MAS"] >= 41) & (df["MAS"] < 61)).sum())
    _stage1c_metric_row([
        ("Review Items", f"{len(attention)}", "Score ≥ 41"),
        ("Management Attention", f"{high}", "Score ≥ 61"),
        ("Review Band", f"{review_count}", "Score 41–60"),
        ("Action Types", f"{df['Recommended_Action'].nunique()}", "Recommendation engine"),
    ])

    st.markdown('<div class="ec-table-title">Review Queue</div>', unsafe_allow_html=True)
    review_table = attention[["Rank", "Company", "MAS", "MAS_Band", "Primary_Driver", "Recommended_Action", "Expected_Outcome"]].copy()
    review_table.columns = ["Priority", "Relationship", "Score", "Attention Rating", "Primary Driver", "Recommendation", "Expected Outcome"]
    review_table["Score"] = review_table["Score"].map(lambda x: f"{x:.1f}")
    _stage1c_dataframe(
        review_table,
        height=350,
        column_config={
            "Priority": st.column_config.NumberColumn("Priority", width="small"),
            "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Attention Rating": st.column_config.TextColumn("Attention Rating", width="medium"),
            "Primary Driver": st.column_config.TextColumn("Primary Driver", width="medium"),
            "Recommendation": st.column_config.TextColumn("Recommendation", width="large"),
            "Expected Outcome": st.column_config.TextColumn("Expected Outcome", width="large"),
        },
    )

    default_row = _selected_relationship_row()
    options = attention["Company"].tolist() if len(attention) else df["Company"].tolist()
    default_company = default_row["Company"] if default_row is not None and default_row["Company"] in options else options[0]
    selected = st.selectbox("Review relationship", options, index=options.index(default_company), key="stage1c_review_relationship")
    st.session_state.selected_relationship = selected
    row = df[df["Company"] == selected].iloc[0]

    st.markdown(
        f"""
        <div class="rw-alert">
          <div class="rw-alert-title">Management Review Item · {row['Company']}</div>
          <b>Score / Rating:</b> {row['MAS']:.1f} · {row['MAS_Band']}<br>
          <b>Management question:</b> Should management proceed with <b>{row['Recommended_Action']}</b>?<br>
          <b>AI situation report:</b> {row['AI_Reasoning']}<br><br>
          <b>Expected outcome:</b> {row['Expected_Outcome']}
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_explainability_native(row)


def render_stage_1c_relationships():
    """Functional bridge for the locked consolidated Relationships workspace."""
    row = _selected_relationship_row()
    default_company = row["Company"] if row is not None else df.iloc[0]["Company"]
    options = df["Company"].tolist()
    selected = st.selectbox("Select relationship", options, index=options.index(default_company), key="stage1c_relationship_profile")
    st.session_state.selected_relationship = selected
    r = df[df["Company"] == selected].iloc[0]

    wallet_engine_df_local = build_wallet_engine(illustrative_wallet_data(df))
    wr = wallet_engine_df_local[wallet_engine_df_local["Company"] == selected].iloc[0]
    current_wallet_m = safe_float(wr.get("Current_MUFG_Revenue_M"), 0) or 0
    estimated_wallet_m = safe_float(wr.get("Estimated_Total_Wallet_M"), 0) or 0
    wallet_gap_m = safe_float(wr.get("Wallet_Gap_M"), 0) or 0
    capture_rate = (safe_float(wr.get("Total_Wallet_Capture_Rate"), 0) or 0) * 100

    st.markdown(
        f"""
        <div class="rel360-header-card">
          <div class="rel360-name">{r['Company']}</div>
          <div class="rel360-meta">{r['Country']} · {r['Sector']} · Rating {r['Rating']} / {r['Outlook']}</div>
          <span class="ec-pill {band_pill_class(r['MAS'])}">{r['MAS_Band']} · Score {r['MAS']:.1f}</span>
          <span class="ec-pill ec-pill-blue">Driver: {r['Primary_Driver']}</span>
          <span class="ec-pill ec-pill-green">Action: {r['Recommended_Action']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _stage1c_metric_row([
        ("Revenue", fmt_b(r["Revenue_B"]), f"Growth {fmt_pct(r['Revenue_Growth'])}"),
        ("Assets", fmt_b(r["Assets_B"]), "Balance-sheet scale"),
        ("Debt", fmt_b(r["Debt_B"]), "Funding wallet proxy"),
        ("Market Cap", fmt_b(r["MarketCap_B"]), "Strategic importance proxy"),
    ])

    st.markdown(
        f"""
        <div class="rel360-command">
          <div class="rel360-command-title">Relationship Interpretation</div>
          <div class="ec-text">{r['AI_Reasoning']} <b>Expected outcome:</b> {r['Expected_Outcome']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ec-table-title">Wallet Opportunity</div>', unsafe_allow_html=True)
    _stage1c_metric_row([
        ("Current Wallet Proxy", f"USD {current_wallet_m:,.1f}M", "Illustrative current revenue"),
        ("Estimated Wallet", f"USD {estimated_wallet_m:,.1f}M", "Coalition TB + GM proxy"),
        ("Wallet Gap", f"USD {wallet_gap_m:,.1f}M", "Potential upside"),
        ("Capture Rate", f"{capture_rate:,.0f}%", "Current / estimated"),
    ])
    st.markdown(f"<div class='ec-note'><b>Wallet interpretation:</b> {wallet_reasoning(wr)} <b>Mode:</b> Illustrative demo placeholders.</div>", unsafe_allow_html=True)

    timeline_html = "".join([
        f'<div class="timeline-item"><div class="timeline-date">{dt}</div><div class="timeline-event">{ev}</div></div>'
        for dt, ev in relationship_timeline(r["Company"])
    ])
    pp = product_penetration(r).copy()
    pp["Penetration / Potential"] = pp["Penetration / Potential"].map(status_badge)
    relationship_panels_html = f'''    <div class="stage1c-rel-grid">
      <div class="rel360-panel-clean">
        <div class="rel360-panel-title-clean">Relationship Timeline</div>
        {timeline_html}
      </div>
      <div class="rel360-panel-clean">
        <div class="rel360-panel-title-clean">Product Penetration & Wallet Opportunity</div>
        <div class="product-table-clean">{pp.to_html(index=False, escape=False)}</div>
      </div>
    </div>
    '''
    st.markdown(relationship_panels_html, unsafe_allow_html=True)

    st.markdown('<div class="ec-table-title">Score / Rating Breakdown</div>', unsafe_allow_html=True)
    render_explainability_native(r)


def render_stage_1c_decisions():
    """Stage 1-C.6 management decision capture, audit trail and execution hand-off."""
    decision_candidates = df[df["MAS"] >= 41].copy().sort_values("MAS", ascending=False)
    history = st.session_state.get("decision_history", [])
    execution_actions = st.session_state.get("decision_execution_actions", [])
    latest_by_rel = _latest_decision_by_relationship()

    approved = sum(1 for r in history if r.get("Management Decision") == "Approved")
    modified = sum(1 for r in history if r.get("Management Decision") == "Modified")
    deferred_rejected = sum(1 for r in history if r.get("Management Decision") in {"Deferred", "Rejected"})
    pending = sum(1 for company in decision_candidates["Company"] if company not in latest_by_rel)

    _stage1c_metric_row([
        ("Pending Decisions", f"{pending}", "Material Review Items awaiting judgement"),
        ("Approved / Modified", f"{approved + modified}", "Management decisions requiring follow-through"),
        ("Deferred / Rejected", f"{deferred_rejected}", "No execution action created"),
        ("Execution Actions", f"{len(execution_actions)}", "Created only when implementation is required"),
    ])

    if st.session_state.get("decision_flash"):
        st.success(st.session_state.decision_flash)
        st.session_state.decision_flash = None

    st.markdown(
        """
        <div class="ec-note"><b>Management decision rule.</b><br>
        EC-AI recommends; management decides. Record <b>Approved</b>, <b>Modified</b>, <b>Deferred</b> or <b>Rejected</b> with rationale.
        Approved or Modified decisions create an Execution Action <b>only when implementation is actually required</b>.
        Deferred and Rejected decisions never create execution work.</div>
        """,
        unsafe_allow_html=True,
    )

    # Decision queue with current status
    d = decision_candidates[["Rank", "Company", "MAS", "MAS_Band", "Primary_Driver", "Recommended_Action", "Expected_Outcome"]].copy()
    d["Decision Status"] = d["Company"].map(
        lambda c: latest_by_rel.get(c, {}).get("Management Decision", "Pending")
    )
    d["Final Action"] = d["Company"].map(
        lambda c: latest_by_rel.get(c, {}).get("Final Action", "—")
    )
    d = d.rename(columns={
        "Rank": "Priority",
        "Company": "Relationship",
        "MAS": "Score",
        "MAS_Band": "Attention Rating",
        "Primary_Driver": "Primary Driver",
        "Recommended_Action": "Recommendation",
        "Expected_Outcome": "Expected Outcome",
    })
    d["Score"] = d["Score"].map(lambda x: f"{x:.1f}")
    st.markdown('<div class="ec-table-title">Decision Queue</div>', unsafe_allow_html=True)
    _stage1c_dataframe(
        d,
        height=330,
        column_config={
            "Priority": st.column_config.NumberColumn("Priority", width="small"),
            "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Attention Rating": st.column_config.TextColumn("Attention Rating", width="medium"),
            "Primary Driver": st.column_config.TextColumn("Primary Driver", width="medium"),
            "Recommendation": st.column_config.TextColumn("Recommendation", width="large"),
            "Decision Status": st.column_config.TextColumn("Decision Status", width="medium"),
            "Final Action": st.column_config.TextColumn("Final Action", width="large"),
            "Expected Outcome": st.column_config.TextColumn("Expected Outcome", width="large"),
        },
    )

    # Decision capture
    st.markdown('<div class="ec-table-title">Record Management Decision</div>', unsafe_allow_html=True)
    candidates = decision_candidates["Company"].tolist()
    current_rel = st.session_state.get("selected_relationship")
    default_index = candidates.index(current_rel) if current_rel in candidates else 0
    selected_company = st.selectbox(
        "Review item",
        candidates,
        index=default_index,
        key="stage1c_decision_relationship",
    )
    st.session_state.selected_relationship = selected_company
    row = decision_candidates[decision_candidates["Company"] == selected_company].iloc[0]
    latest = latest_by_rel.get(selected_company)

    latest_note = ""
    if latest:
        latest_note = (
            f"<br><br><b>Latest recorded decision:</b> {latest['Management Decision']} · "
            f"{latest['Final Action']} · {latest['Decision Date']} · {latest['Decision Owner']}"
        )

    st.markdown(
        f"""
        <div class="ec-note">
          <b>{selected_company}</b> · Score / Rating {row['MAS']:.1f} · {row['MAS_Band']}<br>
          <b>EC-AI recommendation:</b> {row['Recommended_Action']}<br>
          <b>Management question:</b> Should management proceed with this recommendation, modify it, defer it or reject it?<br>
          <b>Expected outcome:</b> {row['Expected_Outcome']}{latest_note}
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 1], gap="large")
    with left:
        management_decision = st.radio(
            "Management decision",
            ["Approved", "Modified", "Deferred", "Rejected"],
            horizontal=True,
            key="stage1c_management_decision",
        )

        action_taxonomy = [
            "Strategic Relationship Investment",
            "Portfolio Monitoring",
            "Relationship Recovery",
            "Treasury Deep Dive",
            "Cross-Border Expansion",
            "Credit Review",
            "Executive Engagement",
        ]
        if row["Recommended_Action"] not in action_taxonomy:
            action_taxonomy.append(row["Recommended_Action"])

        if management_decision == "Approved":
            final_action = row["Recommended_Action"]
            st.markdown(f"**Final action:** {final_action}")
        elif management_decision == "Modified":
            final_action = st.selectbox(
                "Modified final action",
                action_taxonomy,
                index=action_taxonomy.index(row["Recommended_Action"]),
                key="stage1c_modified_action",
            )
        elif management_decision == "Deferred":
            final_action = "Deferred — no current action"
            st.markdown("**Final action:** Deferred — no current action")
        else:
            final_action = "Rejected — no action"
            st.markdown("**Final action:** Rejected — no action")

        decision_owner = st.text_input(
            "Decision owner / forum",
            value="Management Review",
            key="stage1c_decision_owner",
        )
        decision_date = st.date_input(
            "Decision date",
            value=date.today(),
            key="stage1c_decision_date",
        )
        rationale = st.text_area(
            "Decision rationale",
            placeholder="Record the management judgement, modification, reason for deferral, or reason for rejection.",
            height=120,
            key="stage1c_decision_rationale",
        )

    with right:
        execution_allowed = management_decision in {"Approved", "Modified"}
        default_execution = execution_allowed and final_action != "Portfolio Monitoring"
        if execution_allowed:
            requires_execution = st.checkbox(
                "Implementation is required — create Execution Action",
                value=default_execution,
                key=f"stage1c_requires_execution_{management_decision}_{selected_company}",
                help="Only create an Execution Action when someone must actually implement the management decision.",
            )
        else:
            requires_execution = False
            st.info("Deferred and Rejected decisions do not create Execution Actions.")

        default_exec_owner, default_due, default_next, default_closure = _execution_fields_for_decision(row, final_action)
        if requires_execution:
            execution_owner = st.text_input(
                "Execution owner",
                value=default_exec_owner,
                key=f"stage1c_execution_owner_{selected_company}",
            )
            due_options = ["30 Days", "45 Days", "60 Days"]
            due_index = due_options.index(default_due) if default_due in due_options else 1
            execution_due = st.selectbox(
                "Due",
                due_options,
                index=due_index,
                key=f"stage1c_execution_due_{selected_company}",
            )
            execution_next_step = st.text_area(
                "Initial next step",
                value=default_next,
                height=95,
                key=f"stage1c_execution_next_step_{selected_company}",
            )
            st.caption(f"Closure criteria: {default_closure}")
        else:
            execution_owner = None
            execution_due = None
            execution_next_step = None
            st.markdown(
                "<div class='ec-note'><b>No execution hand-off.</b><br>The decision will be captured in the audit trail only.</div>",
                unsafe_allow_html=True,
            )

    record_clicked = st.button(
        "Record Decision",
        type="primary",
        use_container_width=True,
        key="stage1c_record_decision",
    )
    if record_clicked:
        if not rationale.strip():
            st.error("Please enter the management rationale before recording the decision.")
        elif not decision_owner.strip():
            st.error("Please enter the decision owner or management forum.")
        elif requires_execution and (not execution_owner or not execution_owner.strip()):
            st.error("Please assign an execution owner.")
        else:
            record = _record_stage1c_decision(
                row,
                decision=management_decision,
                final_action=final_action,
                rationale=rationale,
                decision_owner=decision_owner,
                decision_date=decision_date,
                requires_execution=requires_execution,
                execution_owner=execution_owner,
                execution_due=execution_due,
                execution_next_step=execution_next_step,
            )
            if record["Execution Required"] == "Yes":
                st.session_state.decision_flash = (
                    f"{record['Decision ID']} recorded. Linked Execution Action {record['Execution Action ID']} created."
                )
            else:
                st.session_state.decision_flash = f"{record['Decision ID']} recorded. No Execution Action created."
            st.rerun()

    # Audit trail
    st.markdown('<div class="ec-table-title">Decision Audit Trail</div>', unsafe_allow_html=True)
    audit = _decision_history_df()
    if audit.empty:
        st.info("No management decisions have been recorded in this session yet.")
    else:
        audit_display = audit.copy()
        audit_display["Score"] = audit_display["Score"].map(lambda x: f"{float(x):.1f}")
        _stage1c_dataframe(
            audit_display,
            height=285,
            column_config={
                "Decision ID": st.column_config.TextColumn("Decision ID", width="small"),
                "Decision Date": st.column_config.TextColumn("Decision Date", width="small"),
                "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
                "Score": st.column_config.TextColumn("Score", width="small"),
                "Management Decision": st.column_config.TextColumn("Decision", width="medium"),
                "Original Recommendation": st.column_config.TextColumn("Original Recommendation", width="large"),
                "Final Action": st.column_config.TextColumn("Final Action", width="large"),
                "Rationale": st.column_config.TextColumn("Rationale", width="large"),
                "Decision Owner": st.column_config.TextColumn("Decision Owner", width="medium"),
                "Execution Required": st.column_config.TextColumn("Execution?", width="small"),
                "Execution Action ID": st.column_config.TextColumn("Execution Action ID", width="small"),
                "Recorded": st.column_config.TextColumn("Recorded", width="medium"),
            },
        )
        st.download_button(
            "Download Decision Audit CSV",
            data=audit.to_csv(index=False).encode("utf-8"),
            file_name="ecai_stage_1_c_6_decision_audit.csv",
            mime="text/csv",
            key="stage1c_download_decision_audit",
        )

    # Execution hand-off preview
    st.markdown('<div class="ec-table-title">Execution Actions Created from Decisions</div>', unsafe_allow_html=True)
    if not execution_actions:
        st.info("No execution actions have been created from management decisions yet.")
    else:
        exec_from_decisions = pd.DataFrame(execution_actions).iloc[::-1].reset_index(drop=True)
        exec_from_decisions["Score"] = exec_from_decisions["Score"].map(lambda x: f"{float(x):.1f}")
        _stage1c_dataframe(
            exec_from_decisions,
            height=240,
            column_config={
                "Execution Action ID": st.column_config.TextColumn("Action ID", width="small"),
                "Decision ID": st.column_config.TextColumn("Decision ID", width="small"),
                "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
                "Score": st.column_config.TextColumn("Score", width="small"),
                "Action": st.column_config.TextColumn("Action", width="large"),
                "Owner": st.column_config.TextColumn("Owner", width="medium"),
                "Due": st.column_config.TextColumn("Due", width="small"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Next Step": st.column_config.TextColumn("Next Step", width="large"),
                "Outcome": st.column_config.TextColumn("Outcome", width="medium"),
            },
        )

    st.caption(
        "Stage 1-C.6 prototype persistence: decision records and linked execution actions persist through Streamlit session state during the active app session. Durable database persistence is a later backend integration step."
    )


def render_stage_1c_execution():
    """Execution bridge with Stage 1-C.6 decision-created actions surfaced above the retained v10 register."""
    decision_actions = st.session_state.get("decision_execution_actions", [])
    total_actions = len(execution_df)
    actioned = int((execution_df["Status"].isin(["Assigned", "In Progress", "Monitoring", "Completed"])).sum())
    at_risk = int((execution_df["SLA Status"] == "At Risk").sum())
    exceptions = execution_df[(execution_df["SLA Status"] == "At Risk") | (execution_df["Priority"] == "High")].copy()
    closure_ready = int((execution_df["Status"].isin(["Monitoring", "Completed"])).sum())
    coverage_pct = (actioned / total_actions * 100) if total_actions else 0

    _stage1c_metric_row([
        ("Decision-Linked", f"{len(decision_actions)}", "Created from Approved / Modified decisions"),
        ("Execution Register", f"{total_actions}", "Retained v10 migration baseline"),
        ("Exceptions", f"{len(exceptions)}", "High priority / at risk"),
        ("Closure Ready", f"{closure_ready}", "Monitoring or completed"),
    ])

    st.markdown('<div class="ec-table-title">Decision-Created Execution Actions</div>', unsafe_allow_html=True)
    if not decision_actions:
        st.info("No execution actions have been created from Decisions yet. Approve or modify a Review Item and mark implementation as required.")
    else:
        decision_exec = pd.DataFrame(decision_actions).iloc[::-1].reset_index(drop=True)
        decision_exec["Score"] = decision_exec["Score"].map(lambda x: f"{float(x):.1f}")
        _stage1c_dataframe(
            decision_exec[["Execution Action ID", "Decision ID", "Relationship", "Score", "Action", "Owner", "Due", "Status", "Next Step", "Outcome"]],
            height=230,
            column_config={
                "Execution Action ID": st.column_config.TextColumn("Action ID", width="small"),
                "Decision ID": st.column_config.TextColumn("Decision ID", width="small"),
                "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
                "Score": st.column_config.TextColumn("Score", width="small"),
                "Action": st.column_config.TextColumn("Action", width="large"),
                "Owner": st.column_config.TextColumn("Owner", width="medium"),
                "Due": st.column_config.TextColumn("Due", width="small"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Next Step": st.column_config.TextColumn("Next Step", width="large"),
                "Outcome": st.column_config.TextColumn("Outcome", width="medium"),
            },
        )

    st.markdown(
        "<div class='ec-note'><b>Migration note.</b><br>The decision-linked actions above follow the locked Review → Decision → Execution workflow. The retained v10 execution register remains below as the migration baseline until Stage 1-C.7 rebuilds Execution around decision-created actions.</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ec-table-title">Execution Exceptions</div>', unsafe_allow_html=True)
    if exceptions.empty:
        st.info("No execution exceptions under the current v10 workflow data.")
    else:
        ex = exceptions[["Relationship", "MAS", "Action", "Owner", "Status", "Due", "SLA Status", "Next Step"]].copy()
        ex = ex.rename(columns={"MAS": "Score"})
        ex["Score"] = ex["Score"].map(lambda x: f"{x:.1f}")
        _stage1c_dataframe(
            ex,
            height=205,
            column_config={
                "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
                "Score": st.column_config.TextColumn("Score", width="small"),
                "Action": st.column_config.TextColumn("Action", width="large"),
                "Owner": st.column_config.TextColumn("Owner", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Due": st.column_config.TextColumn("Due", width="small"),
                "SLA Status": st.column_config.TextColumn("SLA Status", width="small"),
                "Next Step": st.column_config.TextColumn("Next Step", width="large"),
            },
        )

    st.markdown('<div class="ec-table-title">Action Register</div>', unsafe_allow_html=True)
    exec_display = execution_df[["Rank", "Relationship", "MAS", "Action", "Owner", "Priority", "Due", "Status", "Progress_%", "Follow-up Cadence", "SLA Status", "Impact"]].copy()
    exec_display = exec_display.rename(columns={"MAS": "Score"})
    exec_display["Score"] = exec_display["Score"].map(lambda x: f"{x:.1f}")
    _stage1c_dataframe(
        exec_display,
        height=365,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Action": st.column_config.TextColumn("Action", width="large"),
            "Owner": st.column_config.TextColumn("Owner", width="medium"),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
            "Due": st.column_config.TextColumn("Due", width="small"),
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Progress_%": st.column_config.NumberColumn("Progress %", width="small", format="%d%%"),
            "Follow-up Cadence": st.column_config.TextColumn("Follow-up", width="small"),
            "SLA Status": st.column_config.TextColumn("SLA", width="small"),
            "Impact": st.column_config.TextColumn("Impact", width="medium"),
        },
    )

    c1, c2 = st.columns([0.9, 2.1], gap="large")
    with c1:
        status_order = ["Not Started", "Assigned", "In Progress", "Monitoring", "Completed", "Deferred"]
        status_df = execution_df["Status"].value_counts().reindex(status_order).fillna(0).reset_index()
        status_df.columns = ["Status", "Count"]
        status_df = status_df[status_df["Count"] > 0]
        fig_status = px.bar(status_df, x="Count", y="Status", orientation="h", text="Count", title="Execution Status")
        fig_status.update_traces(marker_color=MCKINSEY_BLUE, textposition="outside")
        apply_mckinsey_layout(fig_status, height=350)
        fig_status.update_layout(showlegend=False, xaxis_title="Actions", yaxis_title="", bargap=0.30, margin=dict(l=18, r=34, t=52, b=30))
        fig_status.update_xaxes(dtick=1)
        st.plotly_chart(fig_status, use_container_width=True, config={"displayModeBar": False})
    with c2:
        tracker = execution_df[["Relationship", "Owner", "Action", "Status", "Due", "Follow-up Cadence", "Next Step", "Closure Criteria"]].copy()
        st.markdown('<div class="ec-table-title">Owner Follow-up Tracker</div>', unsafe_allow_html=True)
        _stage1c_dataframe(
            tracker,
            height=350,
            column_config={
                "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
                "Owner": st.column_config.TextColumn("Owner", width="medium"),
                "Action": st.column_config.TextColumn("Action", width="large"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Due": st.column_config.TextColumn("Due", width="small"),
                "Follow-up Cadence": st.column_config.TextColumn("Follow-up", width="small"),
                "Next Step": st.column_config.TextColumn("Next Step", width="large"),
                "Closure Criteria": st.column_config.TextColumn("Closure Criteria", width="large"),
            },
        )


def render_stage_1c_portfolio():
    """Functional bridge from the retained Portfolio Intelligence evidence layer."""
    largest = df.sort_values("Revenue_B", ascending=False).iloc[0]["Company"]
    _stage1c_metric_row([
        ("Relationships", f"{len(df)}", "Public-company universe"),
        ("Rated", f"{int((df['Rating'] != 'NR').sum())}", "External rating available"),
        ("Data Quality", f"{df['Data_Quality'].mean():.0f}%", "Average field coverage"),
        ("Largest Revenue", largest, "By LTM revenue"),
    ])

    st.markdown("<div class='ec-note'><b>Portfolio Intelligence is the supporting evidence layer.</b><br>Material patterns should be promoted into Review rather than decided directly from this screen.</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        plot_df = df.dropna(subset=["Revenue_B", "Debt_B"]).copy()
        fig = px.scatter(
            plot_df,
            x="Revenue_B",
            y="Debt_B",
            size="Assets_B",
            size_max=34,
            color="MAS_Band",
            color_discrete_map=MAS_BAND_COLORS,
            hover_name="Company",
            text="Company",
            title="Revenue vs Debt · Wallet Opportunity Evidence",
        )
        label_positions = {
            "Toyota": "top center", "DBS": "top left", "CK Hutchison": "middle left",
            "Tencent": "top left", "TSMC": "top right", "Alibaba": "bottom right",
            "Jardine Matheson": "bottom left", "HSBC": "top right", "BHP": "top center", "Rio Tinto": "top center",
        }
        for trace in fig.data:
            trace.update(
                textposition=[label_positions.get(str(company), "top center") for company in trace.text],
                marker_line_width=1.4,
                marker_line_color="white",
            )
        apply_mckinsey_layout(fig, height=440)
        fig.update_layout(xaxis_title="Revenue (USD B)", yaxis_title="Debt (USD B)", legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        debt_df = df.dropna(subset=["Debt_B"]).sort_values("Debt_B", ascending=False)
        fig2 = px.bar(debt_df, x="Company", y="Debt_B", title="Debt by Relationship", text="Debt_B")
        fig2.update_traces(texttemplate="%{text:.1f}B", textposition="outside", marker_color=MCKINSEY_BLUE, width=0.58, cliponaxis=False)
        apply_mckinsey_layout(fig2, height=440)
        fig2.update_layout(xaxis_title="", yaxis_title="Debt (USD B)", bargap=0.32, margin=dict(l=20, r=25, t=52, b=42))
        fig2.update_xaxes(showgrid=False, tickangle=0)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="ec-table-title">Relationship Master Table</div>', unsafe_allow_html=True)
    display = raw_table(df)
    for c in ["Revenue_B", "Assets_B", "Debt_B", "Equity_B", "Cash_B", "InterestExpense_B", "MarketCap_B", "EV_B"]:
        display[c] = display[c].map(lambda x: None if pd.isna(x) else round(float(x), 1))
    _stage1c_dataframe(
        display,
        height=355,
        column_config={
            "Company": st.column_config.TextColumn("Company", width="medium"),
            "Country": st.column_config.TextColumn("Country", width="medium"),
            "Sector": st.column_config.TextColumn("Sector", width="large"),
            "Rating": st.column_config.TextColumn("Rating", width="small"),
            "Outlook": st.column_config.TextColumn("Outlook", width="small"),
        },
    )


def render_stage_1c_workspace(workspace):
    """Route the new shell to functional v10-backed workspace content."""
    renderers = {
        "briefing": render_stage_1c_briefing,
        "review": render_stage_1c_review,
        "relationships": render_stage_1c_relationships,
        "decisions": render_stage_1c_decisions,
        "execution": render_stage_1c_execution,
        "portfolio": render_stage_1c_portfolio,
    }
    renderer = renderers.get(workspace.key)
    if renderer is None:
        st.error(f"No renderer configured for {workspace.label}.")
        return
    renderer()

def render_stage_1c_footer():
    st.markdown(
        """
        <div class="ec-shell-footer">
            EC-AI Executive Review Workspace · Stage 1-C.6 Decisions Build · v10 institutional engines retained
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stage_1c_page(page_key):
    workspace = WORKSPACES.get(page_key, WORKSPACES["briefing"])
    render_stage_1c_topbar(workspace)
    render_stage_1c_workspace(workspace)


def stage_1c_main():
    init_stage_1c_state()
    page_key = render_stage_1c_sidebar()
    render_stage_1c_page(page_key)
    render_stage_1c_footer()


stage_1c_main()

# Hard migration boundary: the complete v10.0.3 UI source is retained below for
# implementation reference, but Stage 1-C.1 must not render the legacy ten-tab app.
st.stop()

# =============================================================================
# LEGACY v10.0.3 RENDERING SOURCE — RETAINED TEMPORARILY, NOT EXECUTED
# =============================================================================
# =========================
# Sidebar
# =========================
st.sidebar.markdown("## EC-AI")
st.sidebar.markdown("Institutional Relationship OS")
st.sidebar.markdown("**v10.0.3 Alpha**")
st.sidebar.markdown("---")
st.sidebar.markdown("**Universe**")
st.sidebar.markdown("Top 10 public company relationships from S&P Screener")
st.sidebar.markdown("---")
st.sidebar.markdown("**Wallet Sizing Data**")
_wallet_template = wallet_template(df)
st.sidebar.download_button(
    "Download Wallet Input Template",
    data=_wallet_template.to_csv(index=False).encode("utf-8"),
    file_name="ecai_v10_0_3_wallet_input_template.csv",
    mime="text/csv",
    use_container_width=True,
)
wallet_upload = st.sidebar.file_uploader("Upload Wallet Input CSV", type=["csv"], key="wallet_input_upload")
if wallet_upload is not None:
    try:
        wallet_input_df = pd.read_csv(wallet_upload)
        missing = [c for c in WALLET_INPUT_COLUMNS if c not in wallet_input_df.columns]
        if missing:
            st.sidebar.error("Missing wallet columns: " + ", ".join(missing))
            wallet_input_df = illustrative_wallet_data(df)
            wallet_data_mode = "Illustrative fallback"
        else:
            wallet_input_df = wallet_input_df[WALLET_INPUT_COLUMNS]
            wallet_data_mode = "Uploaded internal / external data"
    except Exception as exc:
        st.sidebar.error(f"Wallet upload error: {exc}")
        wallet_input_df = illustrative_wallet_data(df)
        wallet_data_mode = "Illustrative fallback"
else:
    wallet_input_df = illustrative_wallet_data(df)
    wallet_data_mode = "Illustrative demo placeholders"
wallet_engine_df = build_wallet_engine(wallet_input_df)
st.sidebar.caption(f"Mode: {wallet_data_mode}")
st.sidebar.markdown("---")
st.sidebar.markdown("**Engine**")
st.sidebar.markdown("MAS v1.2")
st.sidebar.markdown("Action Matrix v1.0")
st.sidebar.markdown("Executive Memo Engine")

# =========================
# Header
# =========================
st.markdown("""
<div class="ec-hero">
  <div class="ec-title">EC-AI Institutional Relationship OS v10.0.3 Alpha</div>
  <div class="ec-subtitle">Management Attention Allocation System powered by real S&P public company data</div>
  <div class="ec-body">A relationship intelligence platform that converts institutional company data into Management Attention Score, primary driver, recommended action and executive memo outputs.</div>
</div>
""", unsafe_allow_html=True)

# Top-level export controls for v9.2
_top_pdf = build_executive_pack_pdf(df, selected_company=df.iloc[0]["Company"])
st.markdown("<div class='ec-top-export'><b>Executive Pack Export</b><br>Generate a one-click PDF covering the Management Attention Queue, Portfolio Intelligence evidence, selected Relationship Workspace, AI Reasoning and Executive Memo.</div>", unsafe_allow_html=True)
exp1, exp2, exp3 = st.columns([1.2, 1.2, 4], gap="medium")
with exp1:
    st.download_button("📄 Generate Executive Pack PDF", data=_top_pdf, file_name="ecai_institutional_relationship_os_v10_0_3_alpha_executive_pack.pdf", mime="application/pdf", use_container_width=True)
with exp2:
    st.download_button("⬇️ Download MAS Scorecard CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="ecai_mas_v1_2_top10_relationships_v10_0_3_alpha.csv", mime="text/csv", use_container_width=True)

# =========================
# Tabs
# =========================
tab_queue, tab_command, tab_rel360, tab_wallet, tab_execution, tab_portfolio, tab_actions, tab_relationship, tab_reasoning, tab_memo = st.tabs([
    "Management Attention Queue",
    "Executive Command Center",
    "Relationship 360",
    "Wallet Intelligence",
    "Management Execution Hub",
    "Portfolio Intelligence",
    "Management Actions",
    "Relationship Workspace",
    "AI Reasoning",
    "Executive Memo",
])

# =========================
# Tab 1: Management Attention Queue
# =========================
with tab_queue:
    section_title("Top Relationships Requiring Management Attention", "Real Top 10 S&P universe ranked by EC-AI MAS v1.2.")
    total_revenue = df["Revenue_B"].sum(skipna=True)
    total_assets = df["Assets_B"].sum(skipna=True)
    total_debt = df["Debt_B"].sum(skipna=True)
    avg_mas = df["MAS"].mean()
    attention_count = int((df["MAS"] >= 61).sum())
    st.markdown(f"""
    <div class="ec-kpi-row5 ec-kpi-row">
      <div class="ec-card"><div class="ec-card-label">Total Revenue</div><div class="ec-card-value">{fmt_b(total_revenue)}</div><div class="ec-card-sub">S&P Top 10 universe</div></div>
      <div class="ec-card"><div class="ec-card-label">Total Assets</div><div class="ec-card-value">{fmt_b(total_assets)}</div><div class="ec-card-sub">Balance sheet scale</div></div>
      <div class="ec-card"><div class="ec-card-label">Total Debt</div><div class="ec-card-value">{fmt_b(total_debt)}</div><div class="ec-card-sub">Wallet opportunity proxy</div></div>
      <div class="ec-card"><div class="ec-card-label">Average MAS</div><div class="ec-card-value">{avg_mas:.1f}</div><div class="ec-card-sub">Management Attention Score</div></div>
      <div class="ec-card"><div class="ec-card-label">Attention Count</div><div class="ec-card-value">{attention_count}</div><div class="ec-card-sub">MAS ≥ 61</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="ec-legend">
      <div class="ec-legend-title">Management Attention Score (MAS) Legend</div>
      <div class="ec-legend-grid">
        <div>
          <span class="ec-pill ec-pill-green">0-40 Monitor</span>
          <span class="ec-pill ec-pill-blue">41-60 Review</span>
          <span class="ec-pill ec-pill-orange">61-80 Management Attention</span>
          <span class="ec-pill ec-pill-red">81-100 Executive Attention</span>
        </div>
        <div class="ec-text"><b>MAS Formula:</b> Strategic Importance 25% + Wallet Opportunity 25% + Relationship Health 25% + Coverage Strength 15% + Risk Signals 10%.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    q = queue_table(df)
    st.dataframe(q, use_container_width=True, hide_index=True, height=360)

    c1, c2 = st.columns([2, 1], gap="large")
    with c1:
        mas_plot_df = df.sort_values("MAS")
        fig = px.bar(
            mas_plot_df,
            x="MAS",
            y="Company",
            orientation="h",
            text="MAS",
            color="Company",
            color_discrete_map=RELATIONSHIP_CHART_COLORS,
            title="Management Attention Score by Relationship",
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        apply_mckinsey_layout(fig, height=420)
        fig.update_layout(showlegend=False, xaxis_title="MAS", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        action_mix = df["Recommended_Action"].value_counts().reset_index()
        action_mix.columns = ["Action", "Count"]
        fig2 = px.pie(action_mix, values="Count", names="Action", title="Action Mix", color="Action", color_discrete_map=ACTION_COLORS, hole=0.58)
        fig2.update_traces(textinfo="percent", textfont=dict(color="white", size=13), marker=dict(line=dict(color="white", width=2)))
        apply_mckinsey_layout(fig2, height=420)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# =========================
# Tab 2: Executive Command Center
# =========================
with tab_command:
    top = df.iloc[0]
    section_title("Executive Command Center", "Monday-morning briefing for Head of Corporate Banking, Coverage Director or Country CEO.")
    st.markdown(f"""
    <div class="ec-note">
      <b>Executive Brief</b><br>
      EC-AI identified <b>{attention_count}</b> relationships in the management attention band or above. The highest-ranked relationship is <b>{top['Company']}</b> with MAS <b>{top['MAS']:.1f}</b>, driven by <b>{top['Primary_Driver']}</b>. Recommended next action: <b>{top['Recommended_Action']}</b>.
    </div>
    """, unsafe_allow_html=True)

    top4 = df.head(4).reset_index(drop=True)
    cols = st.columns(4, gap="medium")
    for i, r in top4.iterrows():
        with cols[i]:
            st.markdown(f"""
            <div class="ec-action-card">
              <div class="ec-rank">Priority #{int(r['Rank'])} · MAS {r['MAS']:.1f}</div>
              <div class="ec-company">{r['Company']}</div>
              <div class="ec-action">{r['Recommended_Action']}</div>
              <div class="ec-text"><b>Driver:</b> {r['Primary_Driver']}<br><br><b>Why it matters:</b><br>{r['AI_Reasoning']}</div>
            </div>
            """, unsafe_allow_html=True)

    section_title("Recommended Management Agenda", "Suggested discussion flow for the next relationship review.")
    agenda = [
        f"Open the review with {top['Company']} as the highest management attention signal.",
        "Separate wallet-led opportunities from health-led remediation issues.",
        "Assign Treasury Deep Dive cases to Treasury and Coverage jointly.",
        "Assign Executive Engagement cases to senior sponsor / Coverage Director.",
        "Refresh data completeness for missing BHP and Rio Tinto fields before expanding to Top 25.",
    ]
    st.markdown("<div class='ec-note'><ol>" + "".join([f"<li>{x}</li>" for x in agenda]) + "</ol></div>", unsafe_allow_html=True)


# =========================
# Tab 3: Relationship 360
# =========================
with tab_rel360:
    section_title("Relationship 360 Intelligence", "Single-client view combining relationship context, wallet opportunity, execution network and MAS drivers.")
    selected_360 = st.selectbox("Select Relationship 360 profile", df["Company"].tolist(), index=0, key="rel360_select")
    r360 = df[df["Company"] == selected_360].iloc[0]

    wallet_match = wallet_engine_df[wallet_engine_df["Company"] == selected_360]
    if wallet_match.empty:
        wallet_row = build_wallet_engine(illustrative_wallet_data(df[df["Company"] == selected_360])).iloc[0]
    else:
        wallet_row = wallet_match.iloc[0]
    current_wallet_m = safe_float(wallet_row.get("Current_MUFG_Revenue_M"), 0) or 0
    estimated_wallet_m = safe_float(wallet_row.get("Estimated_Total_Wallet_M"), 0) or 0
    wallet_gap_m = safe_float(wallet_row.get("Wallet_Gap_M"), 0) or 0
    capture_rate = (safe_float(wallet_row.get("Total_Wallet_Capture_Rate"), 0) or 0) * 100

    st.markdown(f"""
    <div class="rel360-shell">
      <div class="rel360-header-card">
        <div class="rel360-name">{r360['Company']}</div>
        <div class="rel360-meta">{r360['Country']} · {r360['Sector']} · Rating {r360['Rating']} / {r360['Outlook']}</div>
        <span class="ec-pill {band_pill_class(r360['MAS'])}">{r360['MAS_Band']} · MAS {r360['MAS']:.1f}</span>
        <span class="ec-pill ec-pill-blue">Primary Driver: {r360['Primary_Driver']}</span>
        <span class="ec-pill ec-pill-green">Action: {r360['Recommended_Action']}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="ec-kpi-row4">
      <div class="ec-card"><div class="ec-card-label">Revenue</div><div class="ec-card-value">{fmt_b(r360['Revenue_B'])}</div><div class="ec-card-sub">Growth {fmt_pct(r360['Revenue_Growth'])}</div></div>
      <div class="ec-card"><div class="ec-card-label">Assets</div><div class="ec-card-value">{fmt_b(r360['Assets_B'])}</div><div class="ec-card-sub">Balance sheet scale</div></div>
      <div class="ec-card"><div class="ec-card-label">Debt</div><div class="ec-card-value">{fmt_b(r360['Debt_B'])}</div><div class="ec-card-sub">Funding wallet proxy</div></div>
      <div class="ec-card"><div class="ec-card-label">Expected Outcome</div><div class="ec-card-value" style="font-size:21px !important;">{r360['Expected_Outcome']}</div><div class="ec-card-sub">Management objective</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="rel360-command">
      <div class="rel360-command-title">Relationship Command Brief</div>
      <div class="ec-text">
        <b>{r360['Company']}</b> is ranked as <b>{r360['MAS_Band']}</b> with MAS <b>{r360['MAS']:.1f}</b>.
        The main driver is <b>{r360['Primary_Driver']}</b>. EC-AI recommends <b>{r360['Recommended_Action']}</b>.
        The immediate management objective is to validate the wallet gap, confirm owner accountability and execute the next senior-client touchpoint.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="rel360-wide-panel">
      <div class="rel360-panel-title-clean">Wallet Intelligence Preview</div>
      <div class="ec-text">Wallet Sizing Engine v1.0 combining S&P / GCARS financial capacity, CHUB internal exposure and revenue, and Coalition TB / GM wallet benchmarks. Demo placeholders are clearly labelled until an internal CSV is uploaded.</div>
      <div class="wallet-grid">
        <div class="wallet-mini"><div class="wallet-label">Current Wallet Proxy</div><div class="wallet-value">USD {current_wallet_m:,.1f}M</div><div class="wallet-sub">Current MUFG revenue</div></div>
        <div class="wallet-mini"><div class="wallet-label">Estimated Wallet</div><div class="wallet-value">USD {estimated_wallet_m:,.1f}M</div><div class="wallet-sub">Coalition TB + GM wallet</div></div>
        <div class="wallet-mini"><div class="wallet-label">Wallet Gap</div><div class="wallet-value">USD {wallet_gap_m:,.1f}M</div><div class="wallet-sub">Potential upside</div></div>
        <div class="wallet-mini"><div class="wallet-label">Capture Rate</div><div class="wallet-value">{capture_rate:,.0f}%</div><div class="wallet-sub">Current / estimated</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="wallet-card-grid">
      <div class="wallet-card"><div class="wallet-card-label">Lending Capture</div><div class="wallet-card-value">{fmt_rate(wallet_row.get('Lending_Capture_Rate'))}</div><div class="wallet-card-sub">MUFG exposure / client total debt</div></div>
      <div class="wallet-card"><div class="wallet-card-label">Deposit Capture</div><div class="wallet-card-value">{fmt_rate(wallet_row.get('Deposit_Capture_Rate'))}</div><div class="wallet-card-sub">MUFG deposits / cash equivalents</div></div>
      <div class="wallet-card"><div class="wallet-card-label">TB Capture</div><div class="wallet-card-value">{fmt_rate(wallet_row.get('TB_Capture_Rate'))}</div><div class="wallet-card-sub">MUFG TB revenue / Coalition TB wallet</div></div>
      <div class="wallet-card"><div class="wallet-card-label">GM Capture</div><div class="wallet-card-value">{fmt_rate(wallet_row.get('GM_Capture_Rate'))}</div><div class="wallet-card-sub">MUFG GM revenue / Coalition GM wallet</div></div>
    </div>
    <div class="wallet-opportunity">
      <div class="wallet-opportunity-title">Wallet Sizing Interpretation</div>
      <div class="wallet-opportunity-text">{wallet_reasoning(wallet_row)} <b>Data mode:</b> {wallet_data_mode}. <b>Confidence:</b> {wallet_row.get('Data_Confidence','N/A')}.</div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")
    with left:
        timeline_html = "".join([
            f'<div class="timeline-item"><div class="timeline-date">{dt}</div><div class="timeline-event">{ev}</div></div>'
            for dt, ev in relationship_timeline(r360["Company"])
        ])
        st.markdown(
            f'<div class="rel360-panel-clean"><div class="rel360-panel-title-clean">Relationship Timeline</div>{timeline_html}</div>',
            unsafe_allow_html=True,
        )
    with right:
        pp = product_penetration(r360)
        pp_display = pp.copy()
        pp_display["Penetration / Potential"] = pp_display["Penetration / Potential"].map(status_badge)
        product_html = pp_display.to_html(index=False, escape=False)
        st.markdown(
            f'<div class="rel360-panel-clean"><div class="rel360-panel-title-clean">Product Penetration & Wallet Opportunity</div><div class="product-table-clean">{product_html}</div></div>',
            unsafe_allow_html=True,
        )

    nodes = relationship_network(r360)
    node_html = f'<span class="network-node network-node-core">{r360["Company"]}</span>'
    for n in nodes:
        node_html += f'<span class="network-node">{n}</span>'
    st.markdown(f"""
    <div class="rel360-wide-panel">
      <div class="rel360-panel-title-clean">Relationship Network</div>
      <div class="ec-text">Coverage and product partners required to execute the recommended action.</div><br>
      {node_html}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="rel360-wide-panel">
      <div class="rel360-panel-title-clean">Relationship 360 AI Summary</div>
      <div class="ec-text">
        <b>{r360['Company']}</b> should be reviewed as a relationship-level management agenda item.
        The relationship combines <b>{r360['Primary_Driver']}</b>, wallet opportunity signals and execution requirements.
        Next 30 days: confirm owner, validate wallet opportunity, agree executive follow-up and update execution status in the Management Execution Hub.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="rel360-wide-panel"><div class="rel360-panel-title-clean">MAS Driver Breakdown</div>', unsafe_allow_html=True)
    render_explainability_native(r360)
    st.markdown('</div>', unsafe_allow_html=True)


# =========================
# Tab 4: Wallet Intelligence
# =========================
with tab_wallet:
    section_title("Wallet Intelligence & Sizing", "Compare MUFG's current relationship capture with client financial capacity and external Coalition wallet benchmarks.")
    st.markdown(f"""
    <div class="wallet-source-note">
      <b>Data architecture:</b> Public companies use S&P; private companies use GCARS. Internal exposure, deposits and revenue come from CHUB / MUFG sources. External TB and GM wallet benchmarks come from Coalition.<br>
      <b>Current mode:</b> {wallet_data_mode}. Illustrative values are not MUFG actuals and should be replaced using the downloadable wallet input template.
    </div>
    """, unsafe_allow_html=True)

    selected_wallet = st.selectbox("Select relationship for wallet sizing", wallet_engine_df["Company"].tolist(), key="wallet_intel_select")
    wr = wallet_engine_df[wallet_engine_df["Company"] == selected_wallet].iloc[0]

    st.markdown(f"""
    <div class="wallet-card-grid">
      <div class="wallet-card"><div class="wallet-card-label">Estimated Total Wallet</div><div class="wallet-card-value">USD {safe_float(wr.get('Estimated_Total_Wallet_M'),0):,.1f}M</div><div class="wallet-card-sub">Coalition TB + GM benchmark</div></div>
      <div class="wallet-card"><div class="wallet-card-label">Current MUFG Revenue</div><div class="wallet-card-value">USD {safe_float(wr.get('Current_MUFG_Revenue_M'),0):,.1f}M</div><div class="wallet-card-sub">TB + GM / uploaded total</div></div>
      <div class="wallet-card"><div class="wallet-card-label">Wallet Gap</div><div class="wallet-card-value">USD {safe_float(wr.get('Wallet_Gap_M'),0):,.1f}M</div><div class="wallet-card-sub">Estimated minus current</div></div>
      <div class="wallet-card"><div class="wallet-card-label">Total Capture</div><div class="wallet-card-value">{fmt_rate(wr.get('Total_Wallet_Capture_Rate'))}</div><div class="wallet-card-sub">Current revenue / estimated wallet</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="wallet-card-grid">
      <div class="wallet-card"><div class="wallet-card-label">Lending Capture</div><div class="wallet-card-value">{fmt_rate(wr.get('Lending_Capture_Rate'))}</div><div class="wallet-card-sub">Exposure / total debt</div></div>
      <div class="wallet-card"><div class="wallet-card-label">Deposit Capture</div><div class="wallet-card-value">{fmt_rate(wr.get('Deposit_Capture_Rate'))}</div><div class="wallet-card-sub">Deposits / cash equivalents</div></div>
      <div class="wallet-card"><div class="wallet-card-label">TB Capture</div><div class="wallet-card-value">{fmt_rate(wr.get('TB_Capture_Rate'))}</div><div class="wallet-card-sub">TB revenue / Coalition TB wallet</div></div>
      <div class="wallet-card"><div class="wallet-card-label">GM Capture</div><div class="wallet-card-value">{fmt_rate(wr.get('GM_Capture_Rate'))}</div><div class="wallet-card-sub">GM revenue / Coalition GM wallet</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="wallet-opportunity">
      <div class="wallet-opportunity-title">Recommended Wallet Focus: {wr.get('Primary_Wallet_Opportunity','Data Validation')}</div>
      <div class="wallet-opportunity-text">{wallet_reasoning(wr)}</div>
    </div>
    """, unsafe_allow_html=True)

    wallet_display = wallet_engine_df[[
        "Company", "Financial_Data_Source", "Total_Debt_B", "Cash_And_Equivalents_B",
        "MUFG_Exposure_B", "MUFG_Deposits_B", "Lending_Capture_Rate", "Deposit_Capture_Rate",
        "TB_Capture_Rate", "GM_Capture_Rate", "Estimated_Total_Wallet_M", "Current_MUFG_Revenue_M",
        "Wallet_Gap_M", "Total_Wallet_Capture_Rate", "Primary_Wallet_Opportunity", "Data_Confidence"
    ]].copy()
    for c in ["Lending_Capture_Rate", "Deposit_Capture_Rate", "TB_Capture_Rate", "GM_Capture_Rate", "Total_Wallet_Capture_Rate"]:
        wallet_display[c] = wallet_display[c].map(fmt_rate)
    st.markdown('<div class="ec-table-title">Portfolio Wallet Sizing Table</div>', unsafe_allow_html=True)
    st.dataframe(wallet_display, use_container_width=True, hide_index=True, height=390)
    st.download_button(
        "Download Wallet Sizing Output CSV",
        data=wallet_engine_df.to_csv(index=False).encode("utf-8"),
        file_name="ecai_v10_0_3_wallet_sizing_output.csv",
        mime="text/csv",
    )


# =========================
# Tab 3: Management Execution Hub
# =========================
with tab_execution:
    section_title("Management Execution Hub", "Owner → Status → Due Date → Follow-up → Closure. This is the v9.4 execution workflow layer.")
    total_actions = len(execution_df)
    in_progress = int((execution_df["Status"] == "In Progress").sum())
    completed = int((execution_df["Status"] == "Completed").sum())
    actioned = int((execution_df["Status"].isin(["Assigned", "In Progress", "Monitoring", "Completed"])).sum())
    escalation = int(((execution_df["Priority"] == "High") | (execution_df["MAS"] >= 61)).sum())
    at_risk = int((execution_df["SLA Status"] == "At Risk").sum())
    coverage_pct = (actioned / total_actions * 100) if total_actions else 0
    closure_ready = int((execution_df["Status"].isin(["Monitoring", "Completed"])).sum())

    st.markdown(f"""
    <div class="ec-kpi-row4">
      <div class="ec-card"><div class="ec-card-label">Total Actions</div><div class="ec-card-value">{total_actions}</div><div class="ec-card-sub">From MAS action engine</div></div>
      <div class="ec-card"><div class="ec-card-label">Action Coverage</div><div class="ec-card-value">{coverage_pct:.0f}%</div><div class="ec-card-sub">Assigned / active / completed</div></div>
      <div class="ec-card"><div class="ec-card-label">Closure Ready</div><div class="ec-card-value">{closure_ready}</div><div class="ec-card-sub">Monitoring or completed</div></div>
      <div class="ec-card"><div class="ec-card-label">At Risk</div><div class="ec-card-value">{at_risk}</div><div class="ec-card-sub">High priority without action</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="ec-note">
      <b>Execution Workflow</b><br>
      v9.4 closes the loop from management attention to accountable ownership. Each relationship now has an owner, status, due timing, follow-up cadence, closure criteria and management decision path.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ec-table-title">Management Workflow Pipeline</div>', unsafe_allow_html=True)
    w1, w2, w3, w4, w5 = st.columns(5, gap="small")
    workflow_counts = execution_df["Workflow Stage"].value_counts().to_dict()
    workflow_steps = ["1. Triage", "2. Owner Assigned", "3. Execution", "4. Follow-up", "5. Closure"]
    workflow_sub = {
        "1. Triage": "Needs owner confirmation",
        "2. Owner Assigned": "Accountability established",
        "3. Execution": "Action underway",
        "4. Follow-up": "Monitor outcome",
        "5. Closure": "Evidence completed",
    }
    for col, step in zip([w1, w2, w3, w4, w5], workflow_steps):
        with col:
            st.markdown(f"""
            <div class="workflow-step">
              <div class="workflow-step-label">{step}</div>
              <div class="workflow-step-value">{int(workflow_counts.get(step, 0))} relationships</div>
              <div class="workflow-step-sub">{workflow_sub[step]}</div>
            </div>
            """, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2], gap="large")
    with c1:
        st.markdown('<div class="ec-table-title">Execution Status Mix</div>', unsafe_allow_html=True)
        status_order = ["Not Started", "Assigned", "In Progress", "Monitoring", "Completed", "Deferred"]
        status_df = execution_df["Status"].value_counts().reindex(status_order).fillna(0).reset_index()
        status_df.columns = ["Status", "Count"]
        status_df = status_df[status_df["Count"] > 0]
        status_colors = {
            "Not Started": "#D8DEE6",
            "Assigned": "#AFC4DD",
            "In Progress": "#365F9C",
            "Monitoring": "#9AA4B2",
            "Completed": "#2F855A",
            "Deferred": "#5D6B7A",
        }
        fig_status = px.bar(status_df, x="Count", y="Status", orientation="h", text="Count", color="Status", color_discrete_map=status_colors)
        fig_status.update_traces(textposition="outside")
        apply_mckinsey_layout(fig_status, height=320, title="Actions by Status")
        fig_status.update_layout(showlegend=False, xaxis_title="Actions", yaxis_title="")
        st.plotly_chart(fig_status, use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.markdown('<div class="ec-table-title">Management Action Execution Queue</div>', unsafe_allow_html=True)
        exec_display = execution_df[["Rank", "Relationship", "MAS", "Action", "Owner", "Priority", "Due", "Status", "Progress_%", "Follow-up Cadence", "SLA Status", "Impact"]].copy()
        exec_display["MAS"] = exec_display["MAS"].map(lambda x: f"{x:.1f}")
        st.dataframe(exec_display, use_container_width=True, hide_index=True, height=335)

    section_title("Owner Follow-up Tracker", "What each owner needs to do before the next review cycle.")
    tracker = execution_df[["Relationship", "Owner", "Action", "Status", "Due", "Follow-up Cadence", "Next Step", "Closure Criteria"]].copy()
    st.dataframe(tracker, use_container_width=True, hide_index=True, height=300)

    section_title("Executive Escalation Panel", "Relationships requiring senior sponsorship or cross-functional coordination.")
    escalation_df = execution_df[(execution_df["Priority"] == "High") | (execution_df["MAS"] >= 61)].head(4)
    if escalation_df.empty:
        st.markdown("<div class='ec-note'><b>No immediate escalation.</b><br>All relationships are below executive escalation threshold under current MAS settings.</div>", unsafe_allow_html=True)
    else:
        cols = st.columns(min(4, len(escalation_df)), gap="medium")
        for i, (_, r) in enumerate(escalation_df.iterrows()):
            with cols[i]:
                st.markdown(f"""
                <div class="ec-action-card">
                  <div class="ec-rank">Escalation · MAS {float(r['MAS']):.1f}</div>
                  <div class="ec-company">{r['Relationship']}</div>
                  <div class="ec-action">{r['Action']}</div>
                  <div class="ec-text"><b>Owner:</b> {r['Owner']}<br><b>Status:</b> {r['Status']}<br><b>Due:</b> {r['Due']}<br><b>SLA:</b> {r['SLA Status']}<br><b>Decision:</b> {r['Management Decision']}</div>
                </div>
                """, unsafe_allow_html=True)

    section_title("AI Recommended Next Steps", "Suggested execution plan by relationship.")
    for _, r in execution_df.head(5).iterrows():
        with st.expander(f"{r['Relationship']} · {r['Action']} · {r['Owner']} · {r['Status']}", expanded=(r['Rank'] == 1)):
            st.markdown(f"""
            <div class="workflow-lane">
              <div class="workflow-lane-title">Next management action</div>
              <div class="workflow-lane-text">{r['Next Step']}</div>
            </div>
            <div class="workflow-lane">
              <div class="workflow-lane-title">Follow-up cadence</div>
              <div class="workflow-lane-text">{r['Follow-up Cadence']} until closure criteria is met.</div>
            </div>
            <div class="workflow-lane">
              <div class="workflow-lane-title">Closure criteria</div>
              <div class="workflow-lane-text">{r['Closure Criteria']}</div>
            </div>
            <div class="workflow-lane">
              <div class="workflow-lane-title">Management decision</div>
              <div class="workflow-lane-text">{r['Management Decision']}</div>
            </div>
            """, unsafe_allow_html=True)

# =========================
# Tab 4: Portfolio Intelligence
# =========================
with tab_portfolio:
    section_title("Portfolio Intelligence", "Evidence layer for the real S&P Top 10 institutional relationship universe.")
    st.markdown("<div class='ec-note'><b>Portfolio Intelligence is now the evidence layer.</b><br>The product is the Management Attention Queue. This tab explains the company scale, balance sheet wallet and external risk profile behind the queue.</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="ec-kpi-row4">
      <div class="ec-card"><div class="ec-card-label">Companies</div><div class="ec-card-value">{len(df)}</div><div class="ec-card-sub">Top 10 public universe</div></div>
      <div class="ec-card"><div class="ec-card-label">Investment Grade</div><div class="ec-card-value">{int((df['Rating'] != 'NR').sum())}</div><div class="ec-card-sub">External rating available</div></div>
      <div class="ec-card"><div class="ec-card-label">Avg Data Quality</div><div class="ec-card-value">{df['Data_Quality'].mean():.0f}%</div><div class="ec-card-sub">S&P field coverage</div></div>
      <div class="ec-card"><div class="ec-card-label">Largest Revenue</div><div class="ec-card-value" style="font-size:22px !important;">{df.sort_values('Revenue_B', ascending=False).iloc[0]['Company']}</div><div class="ec-card-sub">By LTM revenue</div></div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        plot_df = df.dropna(subset=["Revenue_B", "Debt_B"]).copy()
        fig = px.scatter(plot_df, x="Revenue_B", y="Debt_B", size="Assets_B", color="MAS_Band", color_discrete_map=MAS_BAND_COLORS, hover_name="Company", text="Company", title="Revenue vs Debt: Wallet Opportunity Evidence")
        fig.update_traces(textposition="top center")
        apply_mckinsey_layout(fig, height=470)
        fig.update_layout(xaxis_title="Revenue (USD B)", yaxis_title="Debt (USD B)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        fig = px.bar(df.sort_values("Debt_B", ascending=False), x="Company", y="Debt_B", title="Debt by Relationship", text="Debt_B")
        fig.update_traces(texttemplate="%{text:.1f}B", textposition="outside")
        fig.update_traces(marker_color=MCKINSEY_BLUE)
        apply_mckinsey_layout(fig, height=470)
        fig.update_layout(xaxis_title="", yaxis_title="Debt (USD B)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="ec-table-title">S&P Relationship Master Table</div>', unsafe_allow_html=True)
    display = raw_table(df)
    for c in ["Revenue_B", "Assets_B", "Debt_B", "Equity_B", "Cash_B", "InterestExpense_B", "MarketCap_B", "EV_B"]:
        display[c] = display[c].map(lambda x: None if pd.isna(x) else round(float(x), 1))
    st.dataframe(display, use_container_width=True, hide_index=True, height=330)

# =========================
# Tab 4: Management Actions
# =========================
with tab_actions:
    section_title("Management Actions", "Action engine output from MAS v1.2 primary drivers.")
    action_summary = df["Recommended_Action"].value_counts().reset_index()
    action_summary.columns = ["Recommended Action", "Relationship Count"]
    c1, c2 = st.columns([1, 3], gap="large")
    with c1:
        st.markdown('<div class="ec-table-title">Action Mix</div>', unsafe_allow_html=True)
        st.dataframe(action_summary, use_container_width=True, hide_index=True, height=260)
    with c2:
        action_df = df[["Rank", "Company", "MAS", "Primary_Driver", "Recommended_Action", "Expected_Outcome"]].copy()
        action_df["MAS"] = action_df["MAS"].map(lambda x: f"{x:.1f}")
        st.markdown('<div class="ec-table-title">Relationship Action Queue</div>', unsafe_allow_html=True)
        st.dataframe(action_df, use_container_width=True, hide_index=True, height=260)

    section_title("Wallet Opportunity Focus", "Relationships where balance sheet scale, debt, cash and interest expense suggest wallet opportunity.")
    wallet_df = df.sort_values("Wallet_Score", ascending=False)[["Company", "Debt_B", "Cash_B", "InterestExpense_B", "EV_B", "Wallet_Score", "Recommended_Action"]].copy()
    for c in ["Debt_B", "Cash_B", "InterestExpense_B", "EV_B"]:
        wallet_df[c] = wallet_df[c].map(lambda x: "N/A" if pd.isna(x) else f"{x:.1f}")
    st.dataframe(wallet_df, use_container_width=True, hide_index=True, height=300)

# =========================
# Tab 5: Relationship Workspace
# =========================
with tab_relationship:
    section_title("Relationship Workspace", "Single-relationship intelligence object using the real S&P Top 10 universe.")
    selected = st.selectbox("Select relationship", df["Company"].tolist(), index=0)
    row = df[df["Company"] == selected].iloc[0]
    st.markdown(f"""
    <div class="rw-hero">
      <div class="rw-name">{row['Company']}</div>
      <div class="rw-meta">{row['Country']} · {row['Sector']} · Rating {row['Rating']} / {row['Outlook']}</div>
      <span class="ec-pill {band_pill_class(row['MAS'])}">{row['MAS_Band']} · MAS {row['MAS']:.1f}</span>
      <span class="ec-pill ec-pill-blue">Driver: {row['Primary_Driver']}</span>
      <span class="ec-pill ec-pill-green">Action: {row['Recommended_Action']}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="rw-alert">
      <div class="rw-alert-title">Executive Alert</div>
      {row['AI_Reasoning']}<br><br>
      <b>Expected outcome:</b> {row['Expected_Outcome']}
    </div>
    """, unsafe_allow_html=True)

    render_explainability_native(row)

    st.markdown(f"""
    <div class="ec-kpi-row4">
      <div class="rw-card"><div class="rw-card-label">Revenue</div><div class="rw-card-value">{fmt_b(row['Revenue_B'])}</div><div class="ec-card-sub">Revenue growth {fmt_pct(row['Revenue_Growth'])}</div></div>
      <div class="rw-card"><div class="rw-card-label">Assets</div><div class="rw-card-value">{fmt_b(row['Assets_B'])}</div><div class="ec-card-sub">Balance sheet scale</div></div>
      <div class="rw-card"><div class="rw-card-label">Debt</div><div class="rw-card-value">{fmt_b(row['Debt_B'])}</div><div class="ec-card-sub">Wallet opportunity proxy</div></div>
      <div class="rw-card"><div class="rw-card-label">Market Cap</div><div class="rw-card-value">{fmt_b(row['MarketCap_B'])}</div><div class="ec-card-sub">Strategic importance proxy</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ec-table-title">Relationship Memo Preview</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='ec-note'>{build_relationship_memo(row).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    st.markdown('<div class="ec-table-title">MAS Breakdown</div>', unsafe_allow_html=True)
    breakdown = pd.DataFrame({
        "Pillar": ["Strategic Importance", "Wallet Opportunity", "Relationship Health", "Coverage Strength", "Risk Signals"],
        "Score": [row["Strategic_Score"], row["Wallet_Score"], row["Health_Score"], row["Coverage_Score"], row["Risk_Score"]],
        "Max": [25, 25, 25, 15, 10],
    })
    st.markdown(
        '<div class="mas-breakdown-table">' + breakdown.to_html(index=False, escape=False) + '</div>',
        unsafe_allow_html=True,
    )

    rel_pdf = build_executive_pack_pdf(df, selected_company=selected)
    st.download_button("Download Relationship Executive Pack PDF", data=rel_pdf, file_name=f"ecai_{selected.lower().replace(' ', '_')}_relationship_360_pack_v10_0.pdf", mime="application/pdf")

# =========================
# Tab 6: AI Reasoning
# =========================
with tab_reasoning:
    section_title("AI Reasoning Layer", "Relationship-level narrative explanation for MAS drivers, recommended actions and expected outcomes.")
    for _, r in df.iterrows():
        with st.expander(f"#{int(r['Rank'])} {r['Company']} · MAS {r['MAS']:.1f} · {r['Recommended_Action']}", expanded=(r['Rank'] <= 3)):
            st.markdown(f"""
            <div class="ec-note">
              <b>Primary Driver:</b> {r['Primary_Driver']}<br>
              <b>MAS Band:</b> {r['MAS_Band']}<br><br>
              <b>AI Reasoning:</b><br>{r['AI_Reasoning']}<br><br>
              <b>Expected Outcome:</b><br>{r['Expected_Outcome']}
            </div>
            """, unsafe_allow_html=True)
            render_explainability_native(r)

# =========================
# Tab 7: Executive Memo
# =========================
with tab_memo:
    section_title("Executive Memo Center", "One-click executive pack export for all key tabs and the selected relationship.")
    memo_text = build_portfolio_memo(df)
    st.markdown("<div class='ec-note'><b>Generate Executive Pack</b><br>Exports MAS Queue, Portfolio Intelligence, Relationship Workspace, AI Reasoning extract and Executive Memo into one PDF.</div>", unsafe_allow_html=True)
    pdf = build_executive_pack_pdf(df, selected_company=df.iloc[0]["Company"])
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.download_button("Generate Executive Pack PDF", data=pdf, file_name="ecai_institutional_relationship_os_v10_0_3_alpha_executive_pack.pdf", mime="application/pdf", use_container_width=True)
    with c2:
        st.download_button("Download MAS Scorecard CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="ecai_mas_v1_2_top10_relationships.csv", mime="text/csv", use_container_width=True)
    with c3:
        st.download_button("Download Memo Text", data=memo_text.encode("utf-8"), file_name="ecai_v10_0_3_alpha_management_memo.txt", mime="text/plain", use_container_width=True)

    with st.expander("Preview Executive Memo", expanded=True):
        st.markdown(f"<div class='memo-preview'>{memo_text.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("EC-AI Institutional Relationship OS v10.0.3 Alpha | Management Attention Allocation System (MAS) v1.2 | Real S&P Top 10 Public Company Universe")
