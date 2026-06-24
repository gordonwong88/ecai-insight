
# EC-AI Institutional Relationship OS v9.4
# v9.2: Real Top 10 S&P universe + MAS v1.2 + MAS explainability + top executive pack export
# Run:
#   python -m streamlit run ecai_institutional_relationship_os_v9_4.py

import io
import math
import re
from datetime import date
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="EC-AI Institutional Relationship OS v9.4",
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
[data-testid="stSidebar"] * { color: white; }
.ec-hero { background: transparent; margin: 0 0 16px 0; padding: 0; }
.ec-title { font-size: 38px !important; font-weight: 950 !important; color:#071B3A; letter-spacing:-0.035em; line-height:1.35 !important; margin-top:24px; margin-bottom:8px; padding-top:4px; }
.ec-subtitle { font-size: 20px !important; font-weight: 800; color:#0B2C55; margin-bottom:6px; }
.ec-body { font-size: 15px !important; color:#526173; line-height:1.45 !important; max-width: 1180px; }
[data-baseweb="tab-list"] { gap: 6px; background:#F8FAFC; padding:6px; border-radius:14px; border:1px solid #D8DEE6; margin-bottom:14px; }
[data-baseweb="tab"] { height:44px; padding:0 15px; border-radius:10px; font-weight:850; font-size:14px; }
[data-baseweb="tab"][aria-selected="true"] { background:#071B3A; color:white; }
.ec-section-title { font-size: 31px !important; font-weight: 950 !important; color:#071B3A; margin-top:18px; margin-bottom:6px; letter-spacing:-0.02em; line-height:1.12 !important; }
.ec-section-subtitle { font-size:15px !important; color:#526173; margin-bottom:12px; }
.ec-note { background:#F8FAFC; border-left:5px solid #1565C0; border-radius:12px; padding:13px 17px; margin:10px 0 15px 0; color:#071B3A; font-size:15px !important; line-height:1.5 !important; }
.ec-card { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:15px; padding:17px 19px; box-shadow:0 2px 8px rgba(15,23,42,.055); min-height:105px; }
.ec-card-label { color:#526173; font-size:12px !important; font-weight:900; text-transform:uppercase; letter-spacing:.03em; margin-bottom:6px; }
.ec-card-value { color:#071B3A; font-size:29px !important; font-weight:950; line-height:1.08 !important; }
.ec-card-sub { color:#526173; font-size:12px !important; margin-top:6px; line-height:1.3 !important; }
.ec-kpi-row { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:13px; margin:12px 0 15px 0; }
.ec-kpi-row4 { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:13px; margin:12px 0 15px 0; }
.ec-kpi-row3 { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:13px; margin:12px 0 15px 0; }
.ec-kpi-row2 { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:13px; margin:12px 0 15px 0; }
.ec-legend { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:15px; padding:17px 19px; margin:10px 0 15px; box-shadow:0 2px 8px rgba(15,23,42,.045); }
.ec-legend-title { font-size:20px !important; font-weight:950; color:#071B3A; margin-bottom:8px; }
.ec-legend-grid { display:grid; grid-template-columns: 1.1fr 1fr; gap:18px; }
.ec-pill { display:inline-block; border-radius:999px; padding:5px 10px; font-size:12px !important; font-weight:900; margin:3px 4px 3px 0; }
.ec-pill-red { background:#FEE2E2; color:#991B1B; border:1px solid #FECACA; }
.ec-pill-orange { background:#FFEDD5; color:#9A3412; border:1px solid #FED7AA; }
.ec-pill-blue { background:#DBEAFE; color:#1E3A8A; border:1px solid #BFDBFE; }
.ec-pill-green { background:#DCFCE7; color:#166534; border:1px solid #BBF7D0; }
.ec-action-card { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:16px; padding:17px 19px; min-height:208px; box-shadow:0 2px 8px rgba(15,23,42,.055); }
.ec-rank { display:inline-block; background:#EEF4FF; color:#0B3D75; border:1px solid #C7D7FE; border-radius:999px; padding:4px 10px; font-size:12px !important; font-weight:900; margin-bottom:8px; }
.ec-company { font-size:22px !important; font-weight:950; color:#071B3A; line-height:1.15 !important; margin-bottom:6px; }
.ec-action { font-size:15px !important; font-weight:900; color:#1565C0; margin-bottom:8px; }
.ec-text { font-size:14px !important; color:#071B3A; line-height:1.45 !important; }
.ec-table-title { font-size:21px !important; font-weight:950; color:#071B3A; margin:14px 0 8px; }
[data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span, [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td { font-size: 13.5px !important; }
.rw-hero { background:#FFFFFF; border:1px solid #D8DEE6; border-radius:17px; padding:22px 26px; box-shadow:0 2px 8px rgba(15,23,42,.055); margin:10px 0 15px; }
.rw-name { font-size:33px !important; font-weight:950; color:#071B3A; line-height:1.15 !important; margin-bottom:5px; }
.rw-meta { font-size:15px !important; color:#526173; margin-bottom:12px; }
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
    if row["Recommended_Action"] in ["Treasury Deep Dive", "Strategic Relationship Investment", "Relationship Recovery"]:
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
    lines.append("Generated by EC-AI Institutional Relationship OS v9.4 | MAS v1.2")
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
    lines.append("Generated by EC-AI Institutional Relationship OS v9.4")
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
    story.append(Paragraph("Generated by EC-AI Institutional Relationship OS v9.4 | Management Attention Allocation System", styles["ECSmall"]))
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
# Sidebar
# =========================
st.sidebar.markdown("## EC-AI")
st.sidebar.markdown("Institutional Relationship OS")
st.sidebar.markdown("**v9.4**")
st.sidebar.markdown("---")
st.sidebar.markdown("**Universe**")
st.sidebar.markdown("Top 10 public company relationships from S&P Screener")
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
  <div class="ec-title">EC-AI Institutional Relationship OS v9.4</div>
  <div class="ec-subtitle">Management Attention Allocation System powered by real S&P public company data</div>
  <div class="ec-body">A relationship intelligence platform that converts institutional company data into Management Attention Score, primary driver, recommended action and executive memo outputs.</div>
</div>
""", unsafe_allow_html=True)

# Top-level export controls for v9.2
_top_pdf = build_executive_pack_pdf(df, selected_company=df.iloc[0]["Company"])
st.markdown("<div class='ec-top-export'><b>Executive Pack Export</b><br>Generate a one-click PDF covering the Management Attention Queue, Portfolio Intelligence evidence, selected Relationship Workspace, AI Reasoning and Executive Memo.</div>", unsafe_allow_html=True)
exp1, exp2, exp3 = st.columns([1.2, 1.2, 4], gap="medium")
with exp1:
    st.download_button("📄 Generate Executive Pack PDF", data=_top_pdf, file_name="ecai_institutional_relationship_os_v9_4_executive_pack.pdf", mime="application/pdf", use_container_width=True)
with exp2:
    st.download_button("⬇️ Download MAS Scorecard CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="ecai_mas_v1_2_top10_relationships_v9_3_1.csv", mime="text/csv", use_container_width=True)

# =========================
# Tabs
# =========================
tab_queue, tab_command, tab_execution, tab_portfolio, tab_actions, tab_relationship, tab_reasoning, tab_memo = st.tabs([
    "Management Attention Queue",
    "Executive Command Center",
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
        fig = px.bar(df.sort_values("MAS"), x="MAS", y="Company", orientation="h", text="MAS", color="MAS_Band", color_discrete_map=MAS_BAND_COLORS, title="Management Attention Score by Relationship")
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        apply_mckinsey_layout(fig, height=420)
        fig.update_layout(showlegend=True, xaxis_title="MAS", yaxis_title="")
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
    st.dataframe(breakdown, use_container_width=True, hide_index=True, height=240)

    rel_pdf = build_executive_pack_pdf(df, selected_company=selected)
    st.download_button("Download Relationship Executive Pack PDF", data=rel_pdf, file_name=f"ecai_{selected.lower().replace(' ', '_')}_executive_pack_v9_2.pdf", mime="application/pdf")

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
        st.download_button("Generate Executive Pack PDF", data=pdf, file_name="ecai_institutional_relationship_os_v9_4_executive_pack.pdf", mime="application/pdf", use_container_width=True)
    with c2:
        st.download_button("Download MAS Scorecard CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="ecai_mas_v1_2_top10_relationships.csv", mime="text/csv", use_container_width=True)
    with c3:
        st.download_button("Download Memo Text", data=memo_text.encode("utf-8"), file_name="ecai_v9_2_4_management_memo.txt", mime="text/plain", use_container_width=True)

    with st.expander("Preview Executive Memo", expanded=True):
        st.markdown(f"<div class='memo-preview'>{memo_text.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption("EC-AI Institutional Relationship OS v9.4 | Management Attention Allocation System (MAS) v1.2 | Real S&P Top 10 Public Company Universe")
