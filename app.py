
# EC-AI Institutional Relationship OS v6.0
# v6.0: Executive Action Queue + PDF memo export + improved readability
# Run:
#   python -m streamlit run ecai_institutional_relationship_os_v6_0.py

import io
import re
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="EC-AI Institutional Portfolio Dashboard",
    page_icon="🏦",
    layout="wide",
)

st.markdown("""
<style>
.block-container {
    padding-top: 2.0rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1760px;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#061A36 0%,#0B2C55 100%);
}
[data-testid="stSidebar"] * {
    color: white;
}
.main-title {
    font-size: 44px;
    font-weight: 850;
    color: #071B3A;
    line-height: 1.15;
    margin: 10px 0 4px 0;
    padding-top: 8px;
    letter-spacing: -0.02em;
    overflow: visible;
}
.sub-title {
    color: #526173;
    font-size: 15px;
    margin-bottom: 18px;
}
.portfolio-card {
    background: white;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 16px 20px;
    margin-top: 8px;
    min-height: 92px;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
    overflow: visible;
}
.portfolio-label {
    font-size: 12px;
    color: #526173;
    font-weight: 800;
    text-transform: uppercase;
}
.portfolio-name {
    font-size: 23px;
    color: #071B3A;
    font-weight: 850;
    margin-top: 4px;
    line-height: 1.25;
}
.portfolio-date {
    font-size: 12px;
    color: #526173;
    margin-top: 6px;
}
.kpi-card {
    background: white;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 16px 18px;
    min-height: 104px;
    box-shadow: 0 1px 3px rgba(15,23,42,.06);
}
.kpi-label {
    color: #526173;
    font-size: 13px;
    font-weight: 700;
}
.kpi-value {
    color: #071B3A;
    font-size: 27px;
    font-weight: 850;
    margin-top: 8px;
}
.kpi-sub {
    color: #526173;
    font-size: 12px;
    margin-top: 4px;
}
.narrative-box {
    background: #F8FAFC;
    border-left: 5px solid #071B3A;
    border-radius: 12px;
    padding: 16px 22px;
    color: #071B3A;
    line-height: 1.6;
    font-size: 15px;
    margin-top: 16px;
    margin-bottom: 16px;
}
.ai-box {
    background: #F8FAFC;
    border-left: 5px solid #1565C0;
    border-radius: 12px;
    padding: 16px 22px;
    color: #071B3A;
    line-height: 1.6;
    font-size: 14px;
    margin-top: 14px;
}
.memo-card {
    background: #ffffff;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 18px 22px;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
}
.profile-card {
    background: #ffffff;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 18px 22px;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
    margin-bottom: 14px;
}
.profile-title {
    color: #071B3A;
    font-size: 22px;
    font-weight: 850;
    margin-bottom: 10px;
}
.profile-subtitle {
    color: #526173;
    font-size: 13px;
    margin-bottom: 12px;
}
.strategy-pill {
    display: inline-block;
    background: #EEF4FF;
    border: 1px solid #C7D7FE;
    color: #0B3D75;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 750;
    margin-right: 6px;
    margin-bottom: 6px;
}
.side-card {
    background: white;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(15,23,42,.05);
}
.side-title {
    color: #071B3A;
    font-size: 19px;
    font-weight: 800;
    margin-bottom: 10px;
}
.small-note {
    color: #526173;
    font-size: 13px;
}
.small-metric-card {
    background: #ffffff;
    border: 1px solid #E5E7EB;
    padding: 10px 8px;
    border-radius: 10px;
    min-height: 66px;
}
.small-metric-label {
    font-size: 11px;
    color: #6B7280;
    margin-bottom: 5px;
    font-weight: 700;
}
.small-metric-value {
    font-size: 17px;
    font-weight: 800;
    color: #0B1F3B;
    white-space: nowrap;
    overflow: visible;
}
.badge {
    color: white;
    padding: 3px 8px;
    border-radius: 7px;
    font-size: 11px;
    font-weight: 700;
}

/* v6.0 readability polish */
html, body, [class*="css"] { font-size: 16px; }
p, li, div { line-height: 1.45; }
[data-testid="stDataFrame"] div { font-size: 14px !important; }
[data-testid="stDataFrame"] th { font-size: 14px !important; font-weight: 800 !important; }
[data-testid="stDataFrame"] td { font-size: 14px !important; }
.stDownloadButton button, .stButton button { font-size: 14px !important; padding: 0.55rem 0.8rem !important; }
.narrative-box { font-size: 15px; }
.side-card { font-size: 14px; }


/* v6.0 readability upgrade */
html, body, [class*="css"] { font-size: 16px; }
div[data-testid="stDataFrame"] { font-size: 15px; }
.stDataFrame, .stTable { font-size: 15px; }
button, .stButton button, .stDownloadButton button { font-size: 15px !important; }


/* v6.0 readability upgrade */
html, body, [class*="css"] { font-size: 18px !important; }
p, li, div, span, label { font-size: 16px !important; line-height: 1.55 !important; }
h1 { font-size: 42px !important; }
h2 { font-size: 30px !important; }
h3 { font-size: 24px !important; }
.narrative-box, .ai-box, .side-card, .profile-card { font-size: 16px !important; }
.profile-title { font-size: 24px !important; }
.profile-subtitle, .small-note, .kpi-sub { font-size: 14px !important; }
.strategy-pill { font-size: 13px !important; padding: 7px 12px !important; }
[data-testid="stDataFrame"] div,
[data-testid="stDataFrame"] span,
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] td { font-size: 15.5px !important; }
.stDownloadButton button, .stButton button { font-size: 16px !important; padding: 0.65rem 1rem !important; }


/* v6.0 executive section header upgrade */
.ec-section-title {
    font-size: 34px !important;
    font-weight: 900 !important;
    color: #071B3A !important;
    margin-top: 34px !important;
    margin-bottom: 12px !important;
    letter-spacing: -0.02em !important;
    line-height: 1.18 !important;
}
.ec-section-subtitle {
    font-size: 16px !important;
    color: #526173 !important;
    margin-bottom: 14px !important;
}


/* v6.0 layout polish */
.hero-title {
    font-size: 48px !important;
    font-weight: 950 !important;
    color: #071B3A !important;
    letter-spacing: -0.035em !important;
    line-height: 1.08 !important;
    margin-top: 10px !important;
    margin-bottom: 10px !important;
}
.hero-subtitle {
    font-size: 22px !important;
    font-weight: 760 !important;
    color: #0B2C55 !important;
    margin-bottom: 18px !important;
}
.hero-body {
    font-size: 18px !important;
    line-height: 1.65 !important;
    color: #071B3A !important;
}
.hero-bullet {
    font-size: 17px !important;
    line-height: 1.55 !important;
    color: #071B3A !important;
}
.ec-section-title {
    font-size: 36px !important;
    margin-top: 42px !important;
}
.side-card {
    min-height: 96px !important;
}
.side-card b {
    font-size: 16px !important;
}
.side-card span {
    line-height: 1.2 !important;
}
div[data-testid="stDataFrame"] {
    border-radius: 12px !important;
}
[data-testid="stDataFrame"] div,
[data-testid="stDataFrame"] span,
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] td {
    font-size: 16px !important;
}
.kpi-card {
    min-height: 120px !important;
}
.kpi-label {
    font-size: 15px !important;
}
.kpi-value {
    font-size: 30px !important;
}
.kpi-sub {
    font-size: 14px !important;
}


/* v6.0 Executive Layout Refactor */
.ec-kpi-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin-top: 18px;
    margin-bottom: 22px;
}
.ec-kpi-wide-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin-top: 18px;
    margin-bottom: 22px;
}
.ec-kpi-tile {
    background: #FFFFFF;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 18px 20px;
    min-height: 112px;
    box-shadow: 0 1px 3px rgba(15,23,42,.06);
}
.ec-kpi-tile-label {
    font-size: 15px !important;
    color: #071B3A;
    font-weight: 800;
    margin-bottom: 8px;
}
.ec-kpi-tile-value {
    font-size: 28px !important;
    color: #071B3A;
    font-weight: 950;
    line-height: 1.1 !important;
}
.ec-kpi-tile-sub {
    font-size: 14px !important;
    color: #526173;
    margin-top: 8px;
}
.ec-export-row {
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr;
    gap: 16px;
    align-items: stretch;
    margin-top: 14px;
    margin-bottom: 18px;
}
.ec-export-card {
    background: #FFFFFF;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 16px 18px;
    min-height: 88px;
}
.ec-table-title {
    font-size: 22px !important;
    font-weight: 900;
    color: #071B3A;
    margin-top: 12px;
    margin-bottom: 10px;
}
.ec-full-width-box {
    width: 100%;
}


/* v6.0 lower grid alignment polish */
[data-testid="stDataFrame"] {
    min-height: auto !important;
}
.relationship-drilldown-card {
    min-height: 560px !important;
}


/* v6.0 Relationship 360 cleanup */
.r360-hero-card {
    background: #ffffff;
    border: 1px solid #D8DEE6;
    border-radius: 16px;
    padding: 22px 26px;
    margin-top: 14px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(15,23,42,.06);
}
.r360-name {
    font-size: 28px !important;
    font-weight: 950 !important;
    color: #071B3A;
    margin-bottom: 6px;
}
.r360-meta {
    font-size: 15px !important;
    color: #526173;
    margin-bottom: 14px;
}
.r360-summary {
    font-size: 16px !important;
    line-height: 1.65 !important;
    color: #071B3A;
    margin-top: 16px;
}
.r360-action {
    background:#F8FAFC;
    border-left:5px solid #1565C0;
    border-radius:12px;
    padding:16px 18px;
    margin-top:16px;
    font-size:16px !important;
    line-height:1.55 !important;
}
.r360-kpi-row {
    display:grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap:14px;
    margin-top: 12px;
    margin-bottom: 20px;
}
.r360-kpi {
    background:#ffffff;
    border:1px solid #D8DEE6;
    border-radius:14px;
    padding:14px 16px;
    min-height:88px;
}
.r360-kpi-label {
    font-size:14px !important;
    color:#526173;
    font-weight:800;
    margin-bottom:8px;
}
.r360-kpi-value {
    font-size:22px !important;
    font-weight:950;
    color:#071B3A;
}


/* v6.0 Portfolio Cognition layout cleanup */
.pc-summary-row {
    display:grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap:18px;
    margin-top:18px;
    margin-bottom:18px;
}
.pc-action-card {
    background:#ffffff;
    border:1px solid #D8DEE6;
    border-radius:14px;
    padding:18px 20px;
    min-height:120px;
    box-shadow:0 1px 3px rgba(15,23,42,.06);
}
.pc-action-title {
    font-size:16px !important;
    font-weight:900;
    color:#071B3A;
    margin-bottom:8px;
}
.pc-action-value {
    font-size:28px !important;
    font-weight:950;
    color:#071B3A;
    line-height:1.1 !important;
}
.pc-action-sub {
    font-size:14px !important;
    color:#526173;
    margin-top:8px;
}
.pc-actions-list {
    background:#ffffff;
    border:1px solid #D8DEE6;
    border-radius:14px;
    padding:18px 22px;
    margin-top:10px;
    margin-bottom:20px;
}
.pc-actions-list li {
    font-size:16px !important;
    margin-bottom:8px;
}


/* v6.0 Executive Command Center */
.ecc-hero {
    background: linear-gradient(135deg, #071B3A 0%, #0B2C55 58%, #123E70 100%);
    border-radius: 22px;
    padding: 32px 36px;
    color: #FFFFFF;
    margin-top: 18px;
    margin-bottom: 24px;
    box-shadow: 0 8px 24px rgba(7,27,58,.18);
}
.ecc-kicker {
    font-size: 14px !important;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: #BFD7FF;
    margin-bottom: 10px;
}
.ecc-title {
    font-size: 46px !important;
    font-weight: 950;
    letter-spacing: -0.035em;
    line-height: 1.05 !important;
    margin-bottom: 12px;
}
.ecc-subtitle {
    font-size: 18px !important;
    line-height: 1.55 !important;
    color: #EAF2FF;
    max-width: 980px;
}
.ecc-metric-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 18px;
    margin-top: 20px;
    margin-bottom: 24px;
}
.ecc-metric {
    background: #FFFFFF;
    border: 1px solid #D8DEE6;
    border-radius: 16px;
    padding: 20px 22px;
    min-height: 122px;
    box-shadow: 0 2px 6px rgba(15,23,42,.06);
}
.ecc-metric-label {
    font-size: 14px !important;
    color: #526173;
    font-weight: 850;
    text-transform: uppercase;
    letter-spacing: .03em;
    margin-bottom: 8px;
}
.ecc-metric-value {
    font-size: 32px !important;
    font-weight: 950;
    color: #071B3A;
    line-height: 1.1 !important;
}
.ecc-metric-sub {
    font-size: 14px !important;
    color: #526173;
    margin-top: 8px;
    line-height: 1.35 !important;
}
.ecc-action-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin-top: 14px;
    margin-bottom: 20px;
}
.ecc-action-card {
    background: #FFFFFF;
    border: 1px solid #D8DEE6;
    border-radius: 16px;
    padding: 20px 22px;
    box-shadow: 0 2px 6px rgba(15,23,42,.06);
    min-height: 190px;
}
.ecc-action-rank {
    display: inline-block;
    background: #EEF4FF;
    color: #0B3D75;
    border: 1px solid #C7D7FE;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 13px !important;
    font-weight: 850;
    margin-bottom: 10px;
}
.ecc-action-name {
    font-size: 22px !important;
    font-weight: 950;
    color: #071B3A;
    margin-bottom: 8px;
}
.ecc-action-type {
    font-size: 15px !important;
    font-weight: 850;
    color: #1565C0;
    margin-bottom: 10px;
}
.ecc-action-text {
    font-size: 15px !important;
    line-height: 1.5 !important;
    color: #071B3A;
}
.ecc-agenda {
    background: #F8FAFC;
    border-left: 6px solid #1565C0;
    border-radius: 14px;
    padding: 20px 24px;
    margin-top: 16px;
    margin-bottom: 24px;
}
.ecc-agenda-title {
    font-size: 20px !important;
    font-weight: 950;
    color: #071B3A;
    margin-bottom: 10px;
}
.ecc-agenda li {
    font-size: 16px !important;
    margin-bottom: 8px;
    line-height: 1.45 !important;
}
.ecc-small-link {
    font-size: 14px !important;
    color: #526173;
}


/* v6.0 card spacing */
.ecc-action-card { margin-bottom: 18px; }

/* v6.0 Executive Command Center redesign */
.block-container {
    padding-top: 1.3rem !important;
    padding-left: 3.2rem !important;
    padding-right: 3.2rem !important;
    max-width: 1680px !important;
}
.ecc-hero {
    background:
      radial-gradient(circle at 82% 20%, rgba(74,144,226,.28) 0%, rgba(74,144,226,0) 34%),
      linear-gradient(135deg, #061A36 0%, #0B2C55 52%, #123E70 100%) !important;
    border-radius: 26px !important;
    padding: 42px 46px !important;
    margin-top: 22px !important;
    margin-bottom: 26px !important;
    box-shadow: 0 14px 36px rgba(7,27,58,.22) !important;
}
.ecc-title {
    font-size: 56px !important;
    max-width: 980px;
}
.ecc-subtitle {
    font-size: 20px !important;
    max-width: 1080px !important;
}
.ecc-metric-row {
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
    gap: 20px !important;
    margin-top: 18px !important;
    margin-bottom: 30px !important;
}
.ecc-metric {
    border: 1px solid rgba(216,222,230,.95) !important;
    border-radius: 18px !important;
    min-height: 140px !important;
    padding: 22px 24px !important;
    box-shadow: 0 8px 18px rgba(15,23,42,.055) !important;
}
.ecc-metric-value {
    font-size: 36px !important;
}
.ecc-action-grid {
    display: grid !important;
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
    gap: 18px !important;
}
.ecc-action-card {
    min-height: 285px !important;
    border-radius: 18px !important;
    padding: 20px 22px !important;
    box-shadow: 0 8px 18px rgba(15,23,42,.055) !important;
}
.ecc-action-name {
    font-size: 22px !important;
    line-height: 1.15 !important;
}
.ecc-action-text {
    font-size: 15px !important;
}
.ecc-agenda {
    border-radius: 18px !important;
    padding: 24px 28px !important;
}
.ec-section-title {
    font-size: 38px !important;
    margin-top: 46px !important;
}
.ec-section-subtitle {
    font-size: 17px !important;
}
.command-strip {
    display:grid;
    grid-template-columns: 2fr 1fr;
    gap: 20px;
    margin-bottom: 24px;
}
.command-panel {
    background:#FFFFFF;
    border:1px solid #D8DEE6;
    border-radius:18px;
    padding:22px 24px;
    box-shadow:0 8px 18px rgba(15,23,42,.055);
}
.command-panel-title {
    font-size:20px !important;
    font-weight:950;
    color:#071B3A;
    margin-bottom:8px;
}
.command-panel-body {
    font-size:16px !important;
    color:#071B3A;
    line-height:1.55 !important;
}
.demo-wrap {
    margin-top: 12px;
    margin-bottom: 28px;
}


/* v6.0 emergency UI fixes */
.hero-title {
    font-size: 40px !important;
    line-height: 1.22 !important;
    letter-spacing: -0.025em !important;
    overflow: visible !important;
    padding-top: 4px !important;
    padding-bottom: 6px !important;
}
.ecc-title {
    font-size: 48px !important;
    line-height: 1.16 !important;
    overflow: visible !important;
}
.ecc-action-card {
    min-height: 245px !important;
    margin-bottom: 18px !important;
}


/* v6.0 multi-tab shell */
[data-baseweb="tab-list"] {
    gap: 8px;
    background: #F8FAFC;
    padding: 8px;
    border-radius: 14px;
    border: 1px solid #D8DEE6;
}
[data-baseweb="tab"] {
    height: 48px;
    padding: 0 18px;
    border-radius: 10px;
    font-weight: 800;
}
[data-baseweb="tab"][aria-selected="true"] {
    background: #071B3A;
    color: white;
}
.ec-module-note {
    background: #F8FAFC;
    border-left: 5px solid #1565C0;
    border-radius: 12px;
    padding: 16px 20px;
    margin-top: 14px;
    margin-bottom: 18px;
    color: #071B3A;
    font-size: 16px !important;
}

</style>
""", unsafe_allow_html=True)


def section_title(title, subtitle=None):
    st.markdown(f'<div class="ec-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="ec-section-subtitle">{subtitle}</div>', unsafe_allow_html=True)

# =========================
# DATA
# =========================
rows = [
["ABC Infrastructure","Infrastructure","Singapore",8.5,1.2,54,93,64,"Treasury Growth"],
["Pacific Energy","Energy","Australia",9.2,1.4,49,84,70,"Treasury Growth"],
["Quantum Semicon","Semiconductor","Taiwan",6.1,3.1,84,87,29,"Strategic Growth"],
["Dragon Telecom","Telecom","China",5.9,2.4,73,81,47,"Strategic Growth"],
["Eastern Development Bank","Financials","Korea",5.0,4.4,91,86,24,"Crown Jewel"],
["Meridian Sovereign Fund","Sovereign","UAE",4.8,5.2,94,95,18,"Crown Jewel"],
["Quantum Infrastructure Fund","Infrastructure","UAE",8.9,3.2,88,94,22,"Crown Jewel"],
["Crest Capital Partners","Financials","Hong Kong",4.3,3.6,91,79,23,"Crown Jewel"],
["Sakura Financial","Financials","Japan",5.2,4.8,92,90,28,"Crown Jewel"],
["Titan Infrastructure Asia","Infrastructure","Philippines",8.2,1.5,58,92,61,"Treasury Growth"],
["Nova Infrastructure Holdings","Infrastructure","Vietnam",7.6,1.8,61,89,53,"Treasury Growth"],
["Terra Renewable Energy","Renewables","Australia",7.8,1.9,66,90,45,"Strategic Growth"],
["Titan Energy Partners","Energy","Qatar",9.5,2.5,71,89,52,"Treasury Growth"],
["Vertex Capital","Financials","Hong Kong",3.7,3.4,89,75,26,"Crown Jewel"],
["Orion Infrastructure","Infrastructure","India",8.0,2.0,65,91,57,"Treasury Growth"],
["Pacific Semiconductor","Semiconductor","Taiwan",6.3,3.0,83,88,30,"Strategic Growth"],
["Bluewave Offshore","Offshore Services","Malaysia",4.1,0.7,31,44,86,"Portfolio Review"],
["Oceanlink Shipping","Shipping","Hong Kong",6.4,0.8,35,42,88,"Portfolio Review"],
["Polaris Shipping","Shipping","Greece",5.7,0.6,25,38,92,"Portfolio Review"],
["Oceanic Bulk Carriers","Shipping","Greece",6.0,0.5,22,35,94,"Portfolio Review"],
]
cols = [
    "Relationship","Sector","Country","Exposure_USD_B","Deposits_USD_B",
    "Treasury_Score","Strategic_Score","Risk_Score","Priority"
]
df = pd.DataFrame(rows, columns=cols)

def fmt_b(x):
    return f"USD {float(x):.1f}B"

def fmt_pct(x):
    return f"{float(x):.1f}%"

def quadrant(row):
    if row["Strategic_Score"] >= 70 and row["Treasury_Score"] >= 70:
        return "Crown Jewel"
    if row["Strategic_Score"] >= 70:
        return "Optimization Focus"
    if row["Treasury_Score"] >= 70:
        return "Treasury Anchor"
    return "Portfolio Review"

def generate_management_action(row):
    treasury = row["Treasury_Score"]
    strategic = row["Strategic_Score"]
    risk = row["Risk_Score"]
    exposure = row["Exposure_USD_B"]
    deposits = row["Deposits_USD_B"]
    sector = row["Sector"]
    priority = row["Priority"]

    actions = []

    if strategic >= 80 and treasury < 70:
        actions.append("Increase treasury penetration and operating wallet linkage.")

    if treasury >= 85 and strategic >= 85:
        actions.append("Protect crown-jewel funding relationship and maintain pricing discipline.")

    if risk >= 75:
        actions.append("Enhanced monitoring recommended due to elevated portfolio risk profile.")

    if exposure >= 8:
        actions.append("Senior management coverage recommended given material exposure size.")

    deposit_ratio = deposits / exposure if exposure else 0
    if deposit_ratio < 0.25 and strategic >= 75:
        actions.append("Relationship under-monetized from liquidity and deposit perspective.")

    if sector in ["Shipping", "Offshore Services"]:
        actions.append("Monitor refinancing and cyclical sector concentration risk.")

    if priority == "Strategic Growth" and treasury >= 70:
        actions.append("Expand wallet penetration through FX, cash management, and flow products.")

    if len(actions) == 0:
        actions.append("Relationship remains stable under current portfolio strategy.")

    return " ".join(actions)

def action_category(row):
    if row["Risk_Score"] >= 80:
        return "Risk Monitoring"
    if row["Strategic_Score"] >= 80 and row["Treasury_Score"] < 70:
        return "Treasury Deepening"
    if row["Treasury_Score"] >= 85 and row["Strategic_Score"] >= 80:
        return "Protect & Defend"
    if row["Exposure_USD_B"] >= 8:
        return "Senior Coverage"
    return "Maintain"

def management_priority_score(row, max_exposure):
    """EC-AI Intelligence Layer v1: Management Priority Score."""
    exposure_importance = (row["Exposure_USD_B"] / max_exposure * 100) if max_exposure else 0
    treasury_opportunity = max(0, 100 - row["Treasury_Score"])
    relationship_weakness = max(0, 100 - row["Strategic_Score"])
    risk_alert = row["Risk_Score"]

    score = (
        0.40 * exposure_importance
        + 0.25 * treasury_opportunity
        + 0.20 * relationship_weakness
        + 0.15 * risk_alert
    )
    return round(score, 1)


def management_priority_band(score):
    if score >= 80:
        return "Immediate Management Attention"
    if score >= 65:
        return "High Priority"
    if score >= 50:
        return "Monitor"
    return "Stable"


def management_priority_rationale(row):
    rationale = []

    if row["Exposure_USD_B"] >= 8:
        rationale.append("material exposure size")

    if row["Treasury_Score"] < 70:
        rationale.append("treasury opportunity")

    if row["Strategic_Score"] < 70:
        rationale.append("relationship strength gap")

    if row["Risk_Score"] >= 80:
        rationale.append("elevated risk signal")

    if not rationale:
        rationale.append("stable relationship profile")

    return ", ".join(rationale).capitalize() + "."


def priority_color(score):
    if score >= 75:
        return "#FEE2E2"  # red tint
    if score >= 65:
        return "#FFEDD5"  # orange tint
    if score >= 50:
        return "#DBEAFE"  # blue tint
    return "#DCFCE7"      # green tint


def priority_text_color(score):
    if score >= 75:
        return "#991B1B"
    if score >= 65:
        return "#9A3412"
    if score >= 50:
        return "#1E3A8A"
    return "#166534"


def executive_action_type(row):
    score = row["Management_Priority_Score"]
    risk = row["Risk_Score"]
    treasury = row["Treasury_Score"]
    strategic = row["Strategic_Score"]
    exposure = row["Exposure_USD_B"]
    sector = row["Sector"]

    if risk >= 85 and treasury < 70:
        return "Senior Risk & Treasury Review"
    if score >= 65 and sector in ["Shipping", "Offshore Services"]:
        return "Cyclical Exposure Review"
    if exposure >= 8 and strategic >= 80:
        return "Senior Coverage Agenda"
    if strategic >= 80 and treasury < 70:
        return "Treasury Deepening Plan"
    if risk >= 80:
        return "Risk Monitoring Escalation"
    if treasury < 70 and strategic < 70:
        return "Relationship Repositioning"
    return "Portfolio Monitoring"


def executive_action_recommendation(row):
    action_type = executive_action_type(row)
    name = row["Relationship"]
    sector = row["Sector"]

    if action_type == "Senior Risk & Treasury Review":
        return f"Schedule senior review with RM and Risk; agree treasury deepening plan and exposure monitoring for {name}."
    if action_type == "Cyclical Exposure Review":
        return f"Review refinancing risk and treasury wallet opportunity across {sector}; assign RM follow-up within 2 weeks."
    if action_type == "Senior Coverage Agenda":
        return f"Place {name} on senior coverage agenda; protect strategic relationship and identify wallet expansion opportunities."
    if action_type == "Treasury Deepening Plan":
        return f"Launch treasury deepening discussion covering deposits, cash management, FX and liquidity solutions."
    if action_type == "Risk Monitoring Escalation":
        return f"Move to enhanced monitoring cadence and request updated credit / sector view from coverage team."
    if action_type == "Relationship Repositioning":
        return f"Reassess relationship strategy; clarify target wallet, risk appetite and expected return contribution."
    return f"Maintain portfolio monitoring and update relationship action plan during next business review."


def build_executive_action_queue(data):
    q = data.sort_values("Management_Priority_Score", ascending=False).copy().head(8)
    q["Priority Rank"] = range(1, len(q) + 1)
    q["Priority Score"] = q["Management_Priority_Score"].map(lambda x: f"{x:.1f}")
    q["Why Management Should Care"] = q["Management_Priority_Rationale"]
    q["Executive Action Type"] = q.apply(executive_action_type, axis=1)
    q["Recommended Next Action"] = q.apply(executive_action_recommendation, axis=1)
    q["Owner"] = q["Executive Action Type"].map(lambda x: "RM + Risk" if "Risk" in x else ("Senior Coverage" if "Senior" in x else "RM + Treasury"))
    q["Timing"] = q["Management_Priority_Score"].map(lambda s: "This week" if s >= 65 else "Next review cycle")
    return q


def build_executive_agenda(data):
    q = build_executive_action_queue(data)
    high = q[q["Management_Priority_Score"] >= 65]
    risk_names = q[q["Risk_Score"] >= 80]["Relationship"].tolist()
    treasury_names = q[q["Treasury_Score"] < 70]["Relationship"].tolist()
    senior_names = q[q["Exposure_USD_B"] >= 8]["Relationship"].tolist()

    agenda = []
    if not high.empty:
        top = high.iloc[0]
        agenda.append(f"1. Open management review with {top['Relationship']} as the top priority relationship due to {top['Management_Priority_Rationale'].lower()}")
    else:
        agenda.append("1. No immediate high-priority relationship identified; maintain current portfolio monitoring cadence.")

    if treasury_names:
        agenda.append(f"2. Launch treasury deepening follow-up for {', '.join(treasury_names[:3])} to improve deposits, cash management and wallet penetration.")
    else:
        agenda.append("2. Treasury linkage appears stable across the filtered portfolio; focus on protecting existing wallet.")

    if risk_names:
        agenda.append(f"3. Request enhanced risk monitoring for {', '.join(risk_names[:3])}, particularly cyclical or refinancing-sensitive exposures.")
    else:
        agenda.append("3. No elevated risk alert above threshold; continue standard quarterly review cadence.")

    if senior_names:
        agenda.append(f"4. Add {', '.join(senior_names[:3])} to senior coverage discussion given material exposure size.")
    else:
        agenda.append("4. No material exposure concentration above senior-coverage threshold in the filtered view.")

    agenda.append("5. Ask each RM to return with a 30-day relationship action plan for high-priority names.")
    return agenda


def style_priority_table(styler):
    def score_style(v):
        try:
            s = float(v)
        except Exception:
            return ""
        return f"background-color: {priority_color(s)}; color: {priority_text_color(s)}; font-weight: 800;"

    # pandas 3 removed Styler.applymap; use Styler.map when available.
    if hasattr(styler, "map"):
        return styler.map(score_style, subset=["Priority Score"])
    return styler.applymap(score_style, subset=["Priority Score"])


def build_ai_reasoning_narrative(row):
    """Rule-based AI reasoning narrative v6.0: explains why management should care."""
    relationship = row["Relationship"]
    score = row["Management_Priority_Score"]
    band = row["Management_Priority_Band"]
    rationale = row["Management_Priority_Rationale"].replace(".", "").lower()
    action_type = row.get("Executive_Action_Type", row.get("AI_Action_Category", "Management Review"))

    if score >= 75:
        urgency = "requires immediate senior management attention"
    elif score >= 65:
        urgency = "should be included in this week's management review"
    elif score >= 50:
        urgency = "should remain on the active monitoring list"
    else:
        urgency = "appears stable under the current portfolio view"

    narrative = (
        f"{relationship} {urgency}. "
        f"The relationship has a Management Priority Score of {score:.1f}, classified as {band}. "
        f"The main management signal is {rationale}. "
        f"Recommended focus: {action_type}."
    )
    return narrative


def build_ai_reasoning_summary(data):
    """Executive-level reasoning summary across filtered portfolio."""
    if data.empty:
        return "No relationships available under current filters."

    top = data.sort_values("Management_Priority_Score", ascending=False).iloc[0]
    high_priority = data[data["Management_Priority_Score"] >= 65]
    risk_names = data[data["Risk_Score"] >= 80]
    treasury_gap = data[data["Treasury_Score"] < 70]

    lines = []
    lines.append(
        f"The highest management attention signal is {top['Relationship']} "
        f"with a priority score of {top['Management_Priority_Score']:.1f}."
    )

    lines.append(
        f"{len(high_priority)} relationships are classified as high priority, "
        f"indicating a near-term management review queue."
    )

    lines.append(
        f"{len(risk_names)} relationships show elevated risk indicators, "
        f"while {len(treasury_gap)} relationships show treasury monetization gaps."
    )

    lines.append(
        "The key management implication is to move from portfolio diagnosis to targeted relationship action: "
        "review high-priority names, assign banker follow-up, and track management closure."
    )

    return " ".join(lines)




def executive_command_center_action_type(row):
    """v6.0: simplified executive action type for command center cards."""
    score = row["Management_Priority_Score"]
    risk = row["Risk_Score"]
    treasury = row["Treasury_Score"]
    strategic = row["Strategic_Score"]
    exposure = row["Exposure_USD_B"]

    if score >= 75 or risk >= 85:
        return "Senior Risk & Treasury Review"
    if exposure >= 8:
        return "Senior Coverage Agenda"
    if strategic >= 80 and treasury < 70:
        return "Treasury Deepening"
    if risk >= 75:
        return "Risk Monitoring"
    return row.get("AI_Action_Category", "Management Review")


def executive_command_center_next_action(row):
    """v6.0: concise action recommendation for executive command center."""
    rel = row["Relationship"]
    action_type = executive_command_center_action_type(row)

    if action_type == "Senior Risk & Treasury Review":
        return f"Schedule senior review with Coverage, Risk and Treasury for {rel}; agree 30-day action plan."
    if action_type == "Senior Coverage Agenda":
        return f"Place {rel} on senior coverage agenda due to material exposure and strategic relevance."
    if action_type == "Treasury Deepening":
        return f"Launch treasury wallet discussion with {rel}; focus on deposits, cash management and flow products."
    if action_type == "Risk Monitoring":
        return f"Move {rel} to enhanced monitoring and review refinancing / cyclical exposure sensitivity."
    return f"Maintain current coverage cadence for {rel} and monitor for changes."


def build_command_center_agenda(data):
    """v6.0: management agenda based on top priority relationships."""
    top = data.sort_values("Management_Priority_Score", ascending=False).head(5).copy()
    if top.empty:
        return []
    treasury_names = top[top["Treasury_Score"] < 70]["Relationship"].head(3).tolist()
    risk_names = top[top["Risk_Score"] >= 80]["Relationship"].head(3).tolist()
    exposure_names = top[top["Exposure_USD_B"] >= 8]["Relationship"].head(3).tolist()

    agenda = []
    agenda.append(f"Open management review with {top.iloc[0]['Relationship']} as the top executive attention signal.")
    if treasury_names:
        agenda.append("Launch treasury deepening follow-up for " + ", ".join(treasury_names) + ".")
    if risk_names:
        agenda.append("Request enhanced risk monitoring for " + ", ".join(risk_names) + ".")
    if exposure_names:
        agenda.append("Add " + ", ".join(exposure_names) + " to senior coverage discussion.")
    agenda.append("Ask each RM to return with a 30-day relationship action plan for high-priority names.")
    return agenda[:5]


def build_management_memo(data):
    total_exposure = data["Exposure_USD_B"].sum()
    total_deposits = data["Deposits_USD_B"].sum()
    treasury_coverage = total_deposits / total_exposure * 100 if total_exposure else 0
    weighted_treasury = (data["Treasury_Score"] * data["Exposure_USD_B"]).sum() / total_exposure if total_exposure else 0
    weighted_strategic = (data["Strategic_Score"] * data["Exposure_USD_B"]).sum() / total_exposure if total_exposure else 0

    top_exposure = data.sort_values("Exposure_USD_B", ascending=False).head(5)
    treasury_deepening = data[data["AI_Action_Category"] == "Treasury Deepening"].sort_values("Exposure_USD_B", ascending=False)
    risk_monitoring = data[data["AI_Action_Category"] == "Risk Monitoring"].sort_values("Risk_Score", ascending=False)
    crown_jewels = data[data["AI_Action_Category"] == "Protect & Defend"].sort_values("Strategic_Score", ascending=False)

    lines = []
    lines.append("# EC-AI Institutional Portfolio Management Memo")
    lines.append("")
    lines.append("## Portfolio Overview")
    lines.append(f"- Total exposure: USD {total_exposure:.1f}B")
    lines.append(f"- Total deposits: USD {total_deposits:.1f}B")
    lines.append(f"- Treasury coverage: {treasury_coverage:.1f}%")
    lines.append(f"- Weighted Treasury Score: {weighted_treasury:.1f}")
    lines.append(f"- Weighted Strategic Score: {weighted_strategic:.1f}")
    lines.append("")
    lines.append("## Executive Interpretation")
    lines.append("The portfolio shows a concentration of strategically important institutional relationships with varying degrees of treasury penetration. Management attention should focus on relationships with high strategic value but lower treasury contribution, while protecting deposit-rich crown-jewel names and monitoring elevated-risk cyclical exposures.")
    lines.append("")
    lines.append("## Top Exposure Relationships")
    for _, r in top_exposure.iterrows():
        lines.append(f"- {r['Relationship']}: USD {r['Exposure_USD_B']:.1f}B exposure | Treasury {int(r['Treasury_Score'])} | Strategic {int(r['Strategic_Score'])} | {r['AI_Action_Category']}")
    lines.append("")
    lines.append("## Treasury Deepening Priorities")
    if treasury_deepening.empty:
        lines.append("- No treasury deepening priority identified under current rules.")
    else:
        for _, r in treasury_deepening.head(6).iterrows():
            lines.append(f"- {r['Relationship']}: {r['AI_Management_Action']}")
    lines.append("")
    lines.append("## Risk Monitoring Priorities")
    if risk_monitoring.empty:
        lines.append("- No elevated risk monitoring priority identified under current rules.")
    else:
        for _, r in risk_monitoring.head(6).iterrows():
            lines.append(f"- {r['Relationship']}: Risk Score {int(r['Risk_Score'])}. {r['AI_Management_Action']}")
    lines.append("")
    lines.append("## Crown-Jewel Relationship Protection")
    if crown_jewels.empty:
        lines.append("- No protect-and-defend relationship identified under current rules.")
    else:
        for _, r in crown_jewels.head(6).iterrows():
            lines.append(f"- {r['Relationship']}: {r['AI_Management_Action']}")
    lines.append("")
    lines.append("## AI Reasoning Summary")
    try:
        lines.append(build_ai_reasoning_summary(data))
    except Exception:
        lines.append("AI reasoning summary unavailable under current data view.")
    lines.append("")
    lines.append("## Recommended Management Agenda")
    lines.append("1. Prioritize treasury deepening for strategic relationships with weak deposit linkage.")
    lines.append("2. Review large exposure names for senior coverage and portfolio concentration.")
    lines.append("3. Monitor shipping, offshore, and other cyclical relationships with elevated risk scores.")
    lines.append("4. Protect high-quality funding relationships and maintain pricing discipline.")
    lines.append("5. Use relationship-level action categories to guide banker follow-up and management committee discussion.")
    lines.append("")
    lines.append("---")
    lines.append("Generated by EC-AI Institutional Relationship OS v6.0")
    return "\n".join(lines)


def build_management_memo_html(data):
    memo = build_management_memo(data)
    html = memo.replace("\n", "<br>")
    html = html.replace("# EC-AI Institutional Portfolio Management Memo", "<h2>EC-AI Institutional Portfolio Management Memo</h2>")
    html = html.replace("## Portfolio Overview", "<h3>Portfolio Overview</h3>")
    html = html.replace("## Executive Interpretation", "<h3>Executive Interpretation</h3>")
    html = html.replace("## Top Exposure Relationships", "<h3>Top Exposure Relationships</h3>")
    html = html.replace("## Treasury Deepening Priorities", "<h3>Treasury Deepening Priorities</h3>")
    html = html.replace("## Risk Monitoring Priorities", "<h3>Risk Monitoring Priorities</h3>")
    html = html.replace("## Crown-Jewel Relationship Protection", "<h3>Crown-Jewel Relationship Protection</h3>")
    html = html.replace("## Recommended Management Agenda", "<h3>Recommended Management Agenda</h3>")
    return f'<div class="narrative-box">{html}</div>'





def build_management_memo_pdf(data) -> bytes:
    """Generate an executive PDF version of the EC-AI management memo."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT

    memo = build_management_memo(data)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ECTitle", parent=styles["Title"], fontSize=18, leading=22, alignment=TA_LEFT, spaceAfter=14))
    styles.add(ParagraphStyle(name="ECH2", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=12, spaceAfter=7))
    styles.add(ParagraphStyle(name="ECBody", parent=styles["BodyText"], fontSize=10.5, leading=16, spaceAfter=6))
    styles.add(ParagraphStyle(name="ECSmall", parent=styles["BodyText"], fontSize=9, leading=12, textColor="#4B5563"))

    story = []
    for raw in memo.splitlines():
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 0.08 * inch))
            continue
        safe = (line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        safe = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe)
        if safe.startswith("# "):
            story.append(Paragraph(safe[2:], styles["ECTitle"]))
        elif safe.startswith("## "):
            story.append(Paragraph(safe[3:], styles["ECH2"]))
        elif safe.startswith("- "):
            story.append(Paragraph("• " + safe[2:], styles["ECBody"]))
        elif re.match(r"^\d+\.\s", safe):
            story.append(Paragraph(safe, styles["ECBody"]))
        elif safe.startswith("---"):
            story.append(Spacer(1, 0.10 * inch))
            story.append(Paragraph("Generated by EC-AI Institutional Relationship OS v6.0", styles["ECSmall"]))
        else:
            story.append(Paragraph(safe, styles["ECBody"]))

    doc.build(story)
    return buf.getvalue()


def build_markdown_memo_pdf(memo_text: str, title_override: str | None = None) -> bytes:
    """Generate readable PDF from EC-AI markdown-style memo text."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ECTitle2", parent=styles["Title"], fontSize=18, leading=22, alignment=TA_LEFT, spaceAfter=14))
    styles.add(ParagraphStyle(name="ECH2b", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=12, spaceAfter=7))
    styles.add(ParagraphStyle(name="ECBody2", parent=styles["BodyText"], fontSize=10.8, leading=16.5, spaceAfter=6))
    styles.add(ParagraphStyle(name="ECSmall2", parent=styles["BodyText"], fontSize=9, leading=12, textColor="#4B5563"))

    story = []
    for raw in str(memo_text).splitlines():
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 0.08 * inch))
            continue

        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe)

        if safe.startswith("# "):
            title = title_override or safe[2:]
            story.append(Paragraph(title, styles["ECTitle2"]))
        elif safe.startswith("## "):
            story.append(Paragraph(safe[3:], styles["ECH2b"]))
        elif safe.startswith("- "):
            story.append(Paragraph("• " + safe[2:], styles["ECBody2"]))
        elif re.match(r"^\d+\.\s", safe):
            story.append(Paragraph(safe, styles["ECBody2"]))
        elif safe.startswith("---"):
            story.append(Spacer(1, 0.10 * inch))
        else:
            story.append(Paragraph(safe, styles["ECBody2"]))

    doc.build(story)
    return buf.getvalue()


def relationship_360_assessment(row):
    exposure = row["Exposure_USD_B"]
    deposits = row["Deposits_USD_B"]
    treasury = row["Treasury_Score"]
    strategic = row["Strategic_Score"]
    risk = row["Risk_Score"]
    sector = row["Sector"]

    wallet_ratio = deposits / exposure * 100 if exposure else 0

    if strategic >= 85:
        strategic_view = "Core strategic institutional relationship"
    elif strategic >= 70:
        strategic_view = "Important strategic relationship"
    else:
        strategic_view = "Non-core portfolio relationship"

    if wallet_ratio >= 60:
        wallet_view = "Strong wallet penetration"
    elif wallet_ratio >= 35:
        wallet_view = "Moderate wallet penetration"
    else:
        wallet_view = "Under-monetized relationship"

    if treasury >= 85:
        treasury_view = "Strong treasury linkage"
    elif treasury >= 70:
        treasury_view = "Acceptable treasury linkage"
    else:
        treasury_view = "Treasury deepening required"

    if risk >= 80:
        risk_view = "Elevated risk profile requiring active monitoring"
    elif risk >= 60:
        risk_view = "Moderate portfolio risk profile"
    else:
        risk_view = "Stable portfolio risk profile"

    if sector in ["Shipping", "Offshore Services"]:
        sector_view = "Cyclical sector exposure with refinancing sensitivity"
    elif sector == "Infrastructure":
        sector_view = "Long-tenor strategic infrastructure exposure"
    elif sector == "Financials":
        sector_view = "Funding-sensitive financial institution relationship"
    else:
        sector_view = "Standard sector monitoring"

    return strategic_view, wallet_view, treasury_view, risk_view, sector_view, wallet_ratio


def build_relationship_360_memo(row):
    strategic_view, wallet_view, treasury_view, risk_view, sector_view, wallet_ratio = relationship_360_assessment(row)

    lines = []
    lines.append(f"# Relationship 360 Profile: {row['Relationship']}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(f"{row['Relationship']} is a {row['Priority']} relationship in the {row['Sector']} sector, located in {row['Country']}.")
    lines.append(f"- Strategic assessment: {strategic_view}")
    lines.append(f"- Treasury assessment: {treasury_view}")
    lines.append(f"- Wallet assessment: {wallet_view} ({wallet_ratio:.1f}% deposits / exposure)")
    lines.append(f"- Risk assessment: {risk_view}")
    lines.append(f"- Sector view: {sector_view}")
    lines.append("")
    lines.append("## Core Metrics")
    lines.append(f"- Exposure: USD {row['Exposure_USD_B']:.1f}B")
    lines.append(f"- Deposits: USD {row['Deposits_USD_B']:.1f}B")
    lines.append(f"- Treasury Score: {int(row['Treasury_Score'])}")
    lines.append(f"- Strategic Score: {int(row['Strategic_Score'])}")
    lines.append(f"- Risk Score: {int(row['Risk_Score'])}")
    lines.append("")
    lines.append("## AI Recommended Action")
    lines.append(row["AI_Management_Action"])
    lines.append("")
    lines.append("## Banker Coverage Strategy")
    if row["Exposure_USD_B"] >= 8:
        lines.append("- Maintain quarterly senior management engagement.")
    else:
        lines.append("- Maintain regular relationship manager coverage.")
    if wallet_ratio < 35:
        lines.append("- Launch treasury deepening discussion focused on operating deposits and cash management.")
    else:
        lines.append("- Protect existing wallet and maintain treasury linkage.")
    if row["Risk_Score"] >= 80:
        lines.append("- Move to monthly risk monitoring cadence.")
    else:
        lines.append("- Maintain quarterly risk review cadence.")
    lines.append("- Identify FX, hedging, liquidity, and transaction banking cross-sell opportunities.")
    lines.append("")
    lines.append("---")
    lines.append("Generated by EC-AI Institutional Relationship OS v6.0")
    return "\n".join(lines)

df["Quadrant"] = df.apply(quadrant, axis=1)
df["AI_Management_Action"] = df.apply(generate_management_action, axis=1)
df["AI_Action_Category"] = df.apply(action_category, axis=1)

# =========================
# EC-AI INTELLIGENCE LAYER v1
# =========================
max_exposure_for_priority = df["Exposure_USD_B"].max()
df["Management_Priority_Score"] = df.apply(
    lambda r: management_priority_score(r, max_exposure_for_priority),
    axis=1,
)
df["Management_Priority_Band"] = df["Management_Priority_Score"].apply(management_priority_band)
df["Management_Priority_Rationale"] = df.apply(management_priority_rationale, axis=1)

# =========================
# SIDEBAR
# =========================
st.sidebar.markdown("## EC-AI")
st.sidebar.markdown("Institutional Relationship OS")
st.sidebar.markdown("v6.0")
st.sidebar.markdown("---")

selected_priority = st.sidebar.multiselect(
    "Priority",
    sorted(df["Priority"].unique()),
    default=sorted(df["Priority"].unique()),
)

selected_country = st.sidebar.multiselect(
    "Country",
    sorted(df["Country"].unique()),
    default=sorted(df["Country"].unique()),
)

st.sidebar.markdown("---")
st.sidebar.info("Hover over bubbles for details. Chart labels use number keys; relationship names are shown in the reference table.")

view = df[df["Priority"].isin(selected_priority) & df["Country"].isin(selected_country)].copy()

if view.empty:
    st.warning("No relationships match the selected filters.")
    st.stop()


# =========================
# HOMEPAGE INTRODUCTION
# =========================
st.markdown(
    """
    <div class="hero-title">EC-AI Institutional Relationship OS</div>
    <div class="hero-subtitle">Transform Portfolio Data into Executive Actions</div>
    <div class="hero-body">
    EC-AI converts portfolio, relationship and risk signals into executive priorities,
    AI reasoning narratives, management actions and decision-ready memos.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()


# =========================
# EC-AI OS v6.0 MULTI-TAB SHELL
# =========================
section_title("EC-AI OS v6.0", "Multi-Tab Institutional Relationship Operating System")

tab_command, tab_portfolio, tab_actions, tab_relationship, tab_reasoning, tab_memo = st.tabs(
    [
        "Executive Command Center",
        "Portfolio Intelligence",
        "Management Actions",
        "Relationship Workspace",
        "AI Reasoning",
        "Executive Memo",
    ]
)

with tab_command:
    # =========================
    # EXECUTIVE COMMAND CENTER v6.0
    # =========================
    command_view = view.sort_values("Management_Priority_Score", ascending=False).copy()
    command_view["Executive_Action_Type"] = command_view.apply(executive_command_center_action_type, axis=1)
    command_view["Executive_Next_Action"] = command_view.apply(executive_command_center_next_action, axis=1)

    total_priority = int((command_view["Management_Priority_Score"] >= 65).sum())
    immediate_actions = int((command_view["Management_Priority_Score"] >= 75).sum())
    top_command = command_view.iloc[0]
    top_theme = command_view["Executive_Action_Type"].value_counts().idxmax()

    if immediate_actions > 0:
        portfolio_health = "Action Required"
    elif total_priority >= 4:
        portfolio_health = "Watchlist"
    else:
        portfolio_health = "Stable"

    st.markdown(
        f"""
        <div class="ecc-hero">
            <div class="ecc-kicker">EC-AI v6.0 · Executive Command Center</div>
            <div class="ecc-title">What should management act on next?</div>
            <div class="ecc-subtitle">
            EC-AI converts institutional relationship data into executive actions:
            priority signals, reasoning themes, recommended next steps and management agenda.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="ecc-metric-row">
            <div class="ecc-metric">
                <div class="ecc-metric-label">Portfolio Health</div>
                <div class="ecc-metric-value">{portfolio_health}</div>
                <div class="ecc-metric-sub">Based on high-priority and immediate-action relationships</div>
            </div>
            <div class="ecc-metric">
                <div class="ecc-metric-label">Priority Relationships</div>
                <div class="ecc-metric-value">{total_priority}</div>
                <div class="ecc-metric-sub">Management Priority Score ≥ 65</div>
            </div>
            <div class="ecc-metric">
                <div class="ecc-metric-label">Immediate Actions</div>
                <div class="ecc-metric-value">{immediate_actions}</div>
                <div class="ecc-metric-sub">Management Priority Score ≥ 75</div>
            </div>
            <div class="ecc-metric">
                <div class="ecc-metric-label">Top Theme</div>
                <div class="ecc-metric-value" style="font-size:24px !important;">{top_theme}</div>
                <div class="ecc-metric-sub">Most common executive action category</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="command-strip">
            <div class="command-panel">
                <div class="command-panel-title">Executive Decision Brief</div>
                <div class="command-panel-body">
                The current portfolio is classified as <b>{portfolio_health}</b>.
                EC-AI identified <b>{total_priority}</b> priority relationships and
                <b>{immediate_actions}</b> immediate actions. The dominant management theme is
                <b>{top_theme}</b>, indicating that management should focus on relationship-level follow-up rather than broad dashboard review.
                </div>
            </div>
            <div class="command-panel">
                <div class="command-panel-title">Top Relationship</div>
                <div class="command-panel-body">
                <b>{top_command["Relationship"]}</b><br>
                Priority Score: <b>{top_command["Management_Priority_Score"]:.1f}</b><br>
                Action: <b>{top_command["Executive_Action_Type"]}</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section_title("Top Management Actions", "Highest-priority relationships requiring management attention.")

    top_actions = command_view.head(4).reset_index(drop=True)

    row1 = st.columns(2, gap="large")
    row2 = st.columns(2, gap="large")
    card_cols = list(row1) + list(row2)

    for idx, r in top_actions.iterrows():
        rank = idx + 1
        with card_cols[idx]:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div class="ecc-action-rank">Priority #{rank} · Score {r["Management_Priority_Score"]:.1f}</div>
                    <div class="ecc-action-name">{r["Relationship"]}</div>
                    <div class="ecc-action-type">{r["Executive_Action_Type"]}</div>
                    <div class="ecc-action-text"><b>Why it matters:</b><br>{r["Management_Priority_Rationale"]}</div>
                    <br>
                    <div class="ecc-action-text"><b>Next action:</b><br>{r["Executive_Next_Action"]}</div>
                    """,
                    unsafe_allow_html=True,
                )

    section_title("Executive Management Agenda", "Suggested discussion flow for the next management review.")
    agenda_items = build_command_center_agenda(command_view)
    agenda_html = '<div class="ecc-agenda"><div class="ecc-agenda-title">Recommended Agenda</div><ol>'
    for item in agenda_items:
        agenda_html += f"<li>{item}</li>"
    agenda_html += "</ol></div>"
    st.markdown(agenda_html, unsafe_allow_html=True)

    with st.expander("View Executive Command Center Action Table", expanded=False):
        ecc_table = command_view[[
            "Relationship",
            "Country",
            "Sector",
            "Exposure_USD_B",
            "Treasury_Score",
            "Strategic_Score",
            "Risk_Score",
            "Management_Priority_Score",
            "Management_Priority_Band",
            "Executive_Action_Type",
            "Executive_Next_Action",
        ]].copy()
        ecc_table["Exposure_USD_B"] = ecc_table["Exposure_USD_B"].map(lambda x: f"{x:.1f}")
        ecc_table["Management_Priority_Score"] = ecc_table["Management_Priority_Score"].map(lambda x: f"{x:.1f}")
        st.dataframe(ecc_table, use_container_width=True, hide_index=True, height=360)


with tab_portfolio:
    st.markdown(
        """
        <div class="ec-module-note">
        <b>Portfolio Intelligence</b><br>
        Evidence layer for portfolio structure, relationship positioning, exposure concentration and reference tables.
        </div>
        """,
        unsafe_allow_html=True,
    )
    # =========================
    # HEADER
    # =========================
    st.markdown('<div class="main-title">Portfolio Cognition Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Executive view of institutional relationships | EC-AI Synthetic Institutional Portfolio Dataset v6.0</div>',
        unsafe_allow_html=True,
    )

    # =========================
    # KPI STRIP
    # =========================
    total_exposure = view["Exposure_USD_B"].sum()
    total_deposits = view["Deposits_USD_B"].sum()
    weighted_treasury = (view["Treasury_Score"] * view["Exposure_USD_B"]).sum() / total_exposure
    weighted_strategic = (view["Strategic_Score"] * view["Exposure_USD_B"]).sum() / total_exposure
    coverage = total_deposits / total_exposure * 100
    risk_alerts = int((view["Risk_Score"] >= 80).sum())

    kpis = [
        ("Total Exposure", fmt_b(total_exposure), "Filtered portfolio"),
        ("Weighted Treasury Score", f"{weighted_treasury:.1f}", "Out of 100"),
        ("Weighted Strategic Score", f"{weighted_strategic:.1f}", "Out of 100"),
        ("Treasury Coverage", fmt_pct(coverage), "Deposits / exposure"),
        ("AI Risk Alerts", str(risk_alerts), "Risk score ≥ 80"),
    ]

    for col, (label, value, sub) in zip(st.columns(5), kpis):
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="narrative-box">
        The portfolio shows concentration in strategic infrastructure and financial relationships requiring treasury penetration enhancement.
        The AI Management Action Engine highlights where management should deepen treasury linkage, protect funding relationships, and monitor elevated risk names.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # PORTFOLIO COGNITION FULL-WIDTH
    # =========================
    key_df = view.sort_values(
        ["Exposure_USD_B", "Strategic_Score", "Risk_Score"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    key_df["Chart_No"] = range(1, len(key_df) + 1)
    key_map = dict(zip(key_df["Relationship"], key_df["Chart_No"]))
    view["Chart_No"] = view["Relationship"].map(key_map)
    view["Label"] = view["Chart_No"].astype(str)

    section_title("Portfolio Cognition Quadrant", "Treasury strength, strategic value, exposure size and relationship priority.")
    st.markdown(
        '<div class="small-note">X-axis: Treasury Score | Y-axis: Strategic Score | Bubble size: Exposure in USD billions<br>Names are moved to the reference table to avoid chart congestion.</div>',
        unsafe_allow_html=True,
    )

    color_map = {
        "Treasury Growth": "#1565C0",
        "Strategic Growth": "#5E35B1",
        "Crown Jewel": "#D32F2F",
        "Portfolio Review": "#F57C00",
    }

    fig = px.scatter(
        view,
        x="Treasury_Score",
        y="Strategic_Score",
        size="Exposure_USD_B",
        color="Priority",
        text="Label",
        hover_name="Relationship",
        size_max=32,
        color_discrete_map=color_map,
        hover_data={
            "Country": True,
            "Sector": True,
            "Exposure_USD_B": ":.1f",
            "Deposits_USD_B": ":.1f",
            "Risk_Score": True,
            "AI_Action_Category": True,
            "Chart_No": False,
            "Label": False,
        },
    )

    fig.add_shape(type="rect", x0=0, y0=70, x1=70, y1=100, fillcolor="rgba(255,152,0,0.10)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=70, y0=70, x1=100, y1=100, fillcolor="rgba(76,175,80,0.10)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=0, y0=0, x1=70, y1=70, fillcolor="rgba(244,67,54,0.06)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=70, y0=0, x1=100, y1=70, fillcolor="rgba(33,150,243,0.06)", line_width=0, layer="below")
    fig.add_vline(x=70, line_width=1, line_dash="dash", line_color="#9CA3AF")
    fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="#9CA3AF")

    fig.add_annotation(x=22, y=96, text="<b>OPTIMIZATION FOCUS</b>", showarrow=False, font=dict(size=13, color="#6B4E16"))
    fig.add_annotation(x=88, y=96, text="<b>CROWN JEWEL</b>", showarrow=False, font=dict(size=13, color="#0B6B2E"))
    fig.add_annotation(x=22, y=8, text="<b>PORTFOLIO REVIEW</b>", showarrow=False, font=dict(size=13, color="#7F1D1D"))
    fig.add_annotation(x=88, y=8, text="<b>TREASURY ANCHOR</b>", showarrow=False, font=dict(size=13, color="#0B3D75"))

    fig.update_traces(
        textposition="middle center",
        textfont=dict(size=11, color="white", family="Arial Black"),
        marker=dict(opacity=0.80, line=dict(width=1, color="white")),
    )

    fig.update_layout(
        template="plotly_white",
        height=720,
        margin=dict(l=10, r=10, t=20, b=20),
        showlegend=False,
        font=dict(family="Inter, Arial", size=13, color="#071B3A"),
        xaxis=dict(title="Treasury Score", range=[0, 100], dtick=10, gridcolor="rgba(17,24,39,.08)"),
        yaxis=dict(title="Strategic Score", range=[0, 100], dtick=10, gridcolor="rgba(17,24,39,.08)"),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

    top5_pct = view.nlargest(5, "Exposure_USD_B")["Exposure_USD_B"].sum() / total_exposure * 100
    infra_pct = view[view["Sector"] == "Infrastructure"]["Exposure_USD_B"].sum() / total_exposure * 100
    shipping_pct = view[view["Sector"].isin(["Shipping", "Aviation"])]["Exposure_USD_B"].sum() / total_exposure * 100

    st.markdown(
        f"""
        <div class="pc-summary-row">
            <div class="pc-action-card">
                <div class="pc-action-title">Top 5 Relationships</div>
                <div class="pc-action-value">{top5_pct:.1f}%</div>
                <div class="pc-action-sub">of portfolio exposure</div>
            </div>
            <div class="pc-action-card">
                <div class="pc-action-title">Infrastructure Concentration</div>
                <div class="pc-action-value">{infra_pct:.1f}%</div>
                <div class="pc-action-sub">of total exposure</div>
            </div>
            <div class="pc-action-card">
                <div class="pc-action-title">Shipping & Aviation Risk</div>
                <div class="pc-action-value">{shipping_pct:.1f}%</div>
                <div class="pc-action-sub">of exposure</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ec-table-title">Top Management Actions</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="pc-actions-list">
        <ol>
            <li>Deepen treasury linkage for infrastructure relationships.</li>
            <li>Monitor refinancing-sensitive shipping exposures.</li>
            <li>Protect crown-jewel deposit relationships.</li>
            <li>Expand wallet penetration across strategic names.</li>
        </ol>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ec-table-title">Relationship Reference</div>', unsafe_allow_html=True)
    st.caption("By chart number")
    ref = key_df[["Chart_No", "Relationship", "Country", "Sector", "Exposure_USD_B"]].copy()
    ref = ref.rename(columns={"Chart_No": "#", "Exposure_USD_B": "Exposure (USD B)"})
    ref["Exposure (USD B)"] = ref["Exposure (USD B)"].map(lambda x: f"{x:.1f}")
    st.dataframe(ref, use_container_width=True, hide_index=True, height=360)


with tab_actions:
    st.markdown(
        """
        <div class="ec-module-note">
        <b>Management Actions</b><br>
        Converts relationship signals into banker follow-up priorities, action categories and executive queues.
        </div>
        """,
        unsafe_allow_html=True,
    )
    # =========================
    # LOWER GRID
    # =========================
    with st.expander("Portfolio Relationship Workbench", expanded=False):
        lower_left, lower_right = st.columns([3.75, 1.45], gap="large")

        with lower_left:
            section_title("Management Attention Priorities", "Relationship-level management focus based on exposure, strategic importance and risk.")
            attention = view.sort_values(["Strategic_Score", "Risk_Score", "Exposure_USD_B"], ascending=[False, False, False]).copy()
            attention["Exposure (USD B)"] = attention["Exposure_USD_B"].map(lambda x: f"{x:.1f}")
            attention["Deposits (USD B)"] = attention["Deposits_USD_B"].map(lambda x: f"{x:.1f}")

            st.dataframe(
                attention[
                    [
                        "Relationship","Quadrant","Priority","Country","Sector",
                        "Exposure (USD B)","Deposits (USD B)",
                        "Treasury_Score","Strategic_Score","Risk_Score","AI_Action_Category",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                height=560,
            )

        with lower_right:
            section_title("Relationship Quick Drilldown", "Single relationship view with action recommendation.")
            selected = st.selectbox("Select relationship", view["Relationship"].tolist())
            row = view[view["Relationship"] == selected].iloc[0]

            def small_metric(label, value):
                st.markdown(
                    f"""
                    <div class="small-metric-card">
                        <div class="small-metric-label">{label}</div>
                        <div class="small-metric-value">{value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            d1, d2, d3, d4, d5 = st.columns(5)
            with d1:
                small_metric("Exposure", fmt_b(row["Exposure_USD_B"]))
            with d2:
                small_metric("Deposits", fmt_b(row["Deposits_USD_B"]))
            with d3:
                small_metric("Treasury", int(row["Treasury_Score"]))
            with d4:
                small_metric("Strategic", int(row["Strategic_Score"]))
            with d5:
                small_metric("Risk", int(row["Risk_Score"]))

            if row["Quadrant"] == "Optimization Focus":
                msg = "Strategically important relationship requiring treasury deepening and stronger operational wallet linkage."
            elif row["Quadrant"] == "Crown Jewel":
                msg = "High-quality relationship combining strategic relevance with strong treasury contribution."
            elif row["Quadrant"] == "Treasury Anchor":
                msg = "Relationship remains valuable from a liquidity and funding perspective."
            else:
                msg = "Relationship may warrant portfolio review given weaker economics and strategic positioning."

            st.markdown(f'<div class="narrative-box">{msg}</div>', unsafe_allow_html=True)

            st.markdown("### AI Management Action Engine")
            st.markdown(
                f"""
                <div class="ai-box" style="min-height:150px;">
                <b>Recommended Management Action</b><br><br>
                {row["AI_Management_Action"]}<br><br>
                <b>Action Category:</b> {row["AI_Action_Category"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # =========================
    # EXECUTIVE INTELLIGENCE LAYER
    # =========================
    section_title("Executive Intelligence Layer", "Portfolio metrics converted into management attention signals.")
    st.markdown(
        """
        <div class="narrative-box">
        EC-AI Intelligence Layer converts portfolio metrics into an executive attention signal.
        The Management Priority Score combines exposure importance, treasury opportunity,
        relationship weakness, and risk alert indicators.
        </div>
        """,
        unsafe_allow_html=True,
    )

    priority_view = view.sort_values("Management_Priority_Score", ascending=False).copy()
    priority_view["Exposure (USD B)"] = priority_view["Exposure_USD_B"].map(lambda x: f"{x:.1f}")
    priority_view["Deposits (USD B)"] = priority_view["Deposits_USD_B"].map(lambda x: f"{x:.1f}")
    priority_view["Priority Score"] = priority_view["Management_Priority_Score"].map(lambda x: f"{x:.1f}")

    avg_priority_score = priority_view["Management_Priority_Score"].mean()
    top_priority_name = priority_view.iloc[0]["Relationship"]
    high_priority_count = int((priority_view["Management_Priority_Score"] >= 65).sum())

    st.markdown(
        f"""
        <div class="ec-kpi-row">
            <div class="ec-kpi-tile">
                <div class="ec-kpi-tile-label">Average Priority Score</div>
                <div class="ec-kpi-tile-value">{avg_priority_score:.1f}</div>
                <div class="ec-kpi-tile-sub">Across filtered relationships</div>
            </div>
            <div class="ec-kpi-tile">
                <div class="ec-kpi-tile-label">Top Management Priority</div>
                <div class="ec-kpi-tile-value" style="font-size:22px !important;">{top_priority_name}</div>
                <div class="ec-kpi-tile-sub">Requires management review</div>
            </div>
            <div class="ec-kpi-tile">
                <div class="ec-kpi-tile-label">High Priority Relationships</div>
                <div class="ec-kpi-tile-value">{high_priority_count}</div>
                <div class="ec-kpi-tile-sub">Score >= 65</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ec-table-title">Top Relationships Requiring Management Attention</div>', unsafe_allow_html=True)
    st.dataframe(
        priority_view[
            [
                "Relationship",
                "Country",
                "Sector",
                "Exposure (USD B)",
                "Treasury_Score",
                "Strategic_Score",
                "Risk_Score",
                "Priority Score",
                "Management_Priority_Band",
                "Management_Priority_Rationale",
            ]
        ].head(10),
        use_container_width=True,
        hide_index=True,
        height=420,
    )

    st.markdown(
        """
        <div class="ai-box">
        <b>Management Priority Score v6.0 Formula</b><br><br>
        40% Exposure Importance + 25% Treasury Opportunity + 20% Relationship Weakness + 15% Risk Alert<br><br>
        <b>Score Colours:</b> Red ≥ 75 | Orange 65–74.9 | Blue 50–64.9 | Green &lt; 50
        </div>
        """,
        unsafe_allow_html=True,
    )


    # =========================
    # ACTION ENGINE SUMMARY
    # =========================
    section_title("AI Management Action Summary", "Action categories and AI-generated management recommendations.")
    summary = view["AI_Action_Category"].value_counts().reset_index()
    summary.columns = ["Action Category", "Relationship Count"]
    s1, s2 = st.columns([1.2, 3.8], gap="large")

    with s1:
        st.dataframe(summary, use_container_width=True, hide_index=True, height=220)

    with s2:
        engine_table = view[[
            "Relationship", "AI_Action_Category", "AI_Management_Action"
        ]].sort_values(["AI_Action_Category", "Relationship"])
        st.dataframe(engine_table, use_container_width=True, hide_index=True, height=220)




with tab_relationship:
    # =========================
    # RELATIONSHIP 360 INTELLIGENCE
    # =========================
    section_title("Relationship 360 Intelligence", "Single-client executive profile, wallet analysis, risk view and coverage strategy.")
    st.markdown(
        """
        <div class="narrative-box">
        Relationship 360 converts portfolio-level analytics into a single-client operating profile:
        executive summary, wallet analysis, risk view, and banker coverage strategy.
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_360 = st.selectbox(
        "Select relationship for 360 profile",
        view["Relationship"].tolist(),
        key="relationship_360_select",
    )

    r360 = view[view["Relationship"] == selected_360].iloc[0]
    strategic_view, wallet_view, treasury_view, risk_view, sector_view, wallet_ratio = relationship_360_assessment(r360)

    st.markdown(
        f"""
        <div class="r360-hero-card">
            <div class="r360-name">{r360["Relationship"]}</div>
            <div class="r360-meta">{r360["Country"]} · {r360["Sector"]} · {r360["Priority"]}</div>
            <span class="strategy-pill">{strategic_view}</span>
            <span class="strategy-pill">{wallet_view}</span>
            <span class="strategy-pill">{risk_view}</span>
            <div class="r360-summary">
                <b>Executive Relationship Summary</b><br><br>
                {r360["Relationship"]} is positioned as a <b>{r360["Priority"]}</b> relationship with
                <b>USD {r360["Exposure_USD_B"]:.1f}B</b> exposure and
                <b>USD {r360["Deposits_USD_B"]:.1f}B</b> deposits.
                The relationship has a <b>{int(r360["Strategic_Score"])}</b> strategic score,
                <b>{int(r360["Treasury_Score"])}</b> treasury score, and
                <b>{int(r360["Risk_Score"])}</b> risk score.
                <br><br>
                <b>Sector View:</b> {sector_view}
            </div>
            <div class="r360-action">
                <b>AI Recommended Action</b><br><br>
                <span style="color:#1565C0;font-weight:850;">{r360["AI_Management_Action"]}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="r360-kpi-row">
            <div class="r360-kpi">
                <div class="r360-kpi-label">Exposure</div>
                <div class="r360-kpi-value">USD {r360["Exposure_USD_B"]:.1f}B</div>
            </div>
            <div class="r360-kpi">
                <div class="r360-kpi-label">Deposits</div>
                <div class="r360-kpi-value">USD {r360["Deposits_USD_B"]:.1f}B</div>
            </div>
            <div class="r360-kpi">
                <div class="r360-kpi-label">Wallet Ratio</div>
                <div class="r360-kpi-value">{wallet_ratio:.1f}%</div>
            </div>
            <div class="r360-kpi">
                <div class="r360-kpi-label">Strategic Score</div>
                <div class="r360-kpi-value">{int(r360["Strategic_Score"])}</div>
            </div>
            <div class="r360-kpi">
                <div class="r360-kpi-label">Risk Score</div>
                <div class="r360-kpi-value">{int(r360["Risk_Score"])}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics_table = pd.DataFrame({
        "Metric": [
            "Exposure",
            "Deposits",
            "Wallet Ratio",
            "Treasury Score",
            "Strategic Score",
            "Risk Score",
            "Action Category",
        ],
        "Value": [
            f'USD {r360["Exposure_USD_B"]:.1f}B',
            f'USD {r360["Deposits_USD_B"]:.1f}B',
            f"{wallet_ratio:.1f}%",
            int(r360["Treasury_Score"]),
            int(r360["Strategic_Score"]),
            int(r360["Risk_Score"]),
            r360["AI_Action_Category"],
        ],
    })

    assessment_table = pd.DataFrame({
        "Dimension": [
            "Strategic Importance",
            "Treasury Quality",
            "Wallet Penetration",
            "Portfolio Risk",
            "Sector View",
        ],
        "Assessment": [
            strategic_view,
            treasury_view,
            wallet_view,
            risk_view,
            sector_view,
        ],
    })

    tcol1, tcol2 = st.columns(2, gap="large")
    with tcol1:
        st.markdown('<div class="ec-table-title">Relationship Metrics</div>', unsafe_allow_html=True)
        st.dataframe(metrics_table, use_container_width=True, hide_index=True, height=260)
    with tcol2:
        st.markdown('<div class="ec-table-title">360 Assessment</div>', unsafe_allow_html=True)
        st.dataframe(assessment_table, use_container_width=True, hide_index=True, height=260)

    strategy_table = pd.DataFrame({
        "Coverage Area": [
            "Senior Coverage",
            "Treasury Penetration",
            "Wallet Expansion",
            "Risk Monitoring",
            "Relationship Objective",
        ],
        "Recommended Action": [
            "Quarterly senior management engagement" if r360["Exposure_USD_B"] >= 8 else "Standard banker coverage cadence",
            "Launch operating wallet / deposits discussion" if wallet_ratio < 35 else "Protect existing treasury linkage",
            "FX, hedging, liquidity and cash management cross-sell",
            "Monthly monitoring" if r360["Risk_Score"] >= 80 else "Quarterly review",
            r360["AI_Action_Category"],
        ],
    })

    st.markdown('<div class="ec-table-title">Banker Coverage Strategy</div>', unsafe_allow_html=True)
    st.dataframe(strategy_table, use_container_width=True, hide_index=True, height=230)

    r360_memo = build_relationship_360_memo(r360)

    try:
        r360_pdf = build_markdown_memo_pdf(
            r360_memo,
            title_override=f"Relationship 360 Profile: {selected_360}",
        )
        st.download_button(
            "Download Relationship 360 Memo PDF",
            data=r360_pdf,
            file_name=f"ecai_relationship_360_{selected_360.replace(' ', '_').lower()}_v6_0.pdf",
            mime="application/pdf",
            use_container_width=False,
        )
    except Exception as e:
        st.warning(f"Relationship 360 PDF export unavailable: {e}")
        st.download_button(
            "Download Relationship 360 Memo Text",
            data=r360_memo.encode("utf-8"),
            file_name=f"ecai_relationship_360_{selected_360.replace(' ', '_').lower()}_v6_0.txt",
            mime="text/plain",
            use_container_width=False,
        )



with tab_reasoning:
    # =========================
    # AI REASONING LAYER v6.0
    # =========================
    section_title("AI Reasoning Layer", "Priority signals translated into executive interpretation and management logic.")
    st.markdown(
        """
        <div class="narrative-box">
        EC-AI Reasoning Layer translates priority signals into executive interpretation.
        This layer explains why management should care, what the main signal is, and what action should follow.
        </div>
        """,
        unsafe_allow_html=True,
    )

    reasoning_view = priority_view.copy()

    if "Executive_Action_Type" not in reasoning_view.columns:
        reasoning_view["Executive_Action_Type"] = reasoning_view["AI_Action_Category"]

    reasoning_view["AI_Reasoning_Narrative"] = reasoning_view.apply(build_ai_reasoning_narrative, axis=1)

    top_reasoning = reasoning_view.iloc[0]

    st.markdown(
        f"""
        <div class="ec-kpi-wide-row">
            <div class="ec-kpi-tile">
                <div class="ec-kpi-tile-label">Top AI Reasoning Signal</div>
                <div class="ec-kpi-tile-value" style="font-size:22px !important;">{top_reasoning["Relationship"]}</div>
                <div class="ec-kpi-tile-sub">Priority score {top_reasoning["Management_Priority_Score"]:.1f}</div>
            </div>
            <div class="ec-kpi-tile">
                <div class="ec-kpi-tile-label">Reasoning Theme</div>
                <div class="ec-kpi-tile-value" style="font-size:22px !important;">{top_reasoning.get("Executive_Action_Type", top_reasoning["AI_Action_Category"])}</div>
                <div class="ec-kpi-tile-sub">Generated from priority signals</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ec-table-title">Executive Reasoning Summary</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="ai-box">
        {build_ai_reasoning_summary(reasoning_view)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ec-table-title">Relationship-Level AI Reasoning</div>', unsafe_allow_html=True)
    reasoning_table = reasoning_view[
        [
            "Relationship",
            "Priority Score",
            "Management_Priority_Band",
            "AI_Reasoning_Narrative",
        ]
    ].head(8)

    st.dataframe(
        reasoning_table,
        use_container_width=True,
        hide_index=True,
        height=360,
    )




with tab_memo:
    # =========================
    # MANAGEMENT MEMO GENERATOR
    # =========================
    section_title("Management Memo Generator", "Generate executive-ready PDF memo from portfolio intelligence and AI action outputs.")
    st.markdown(
        """
        <div class="narrative-box">
        Generate an executive-ready management memo summarizing portfolio exposure, treasury deepening priorities,
        risk monitoring names, crown-jewel relationships, and recommended management agenda.
        </div>
        """,
        unsafe_allow_html=True,
    )

    memo_text = build_management_memo(view)
    memo_pdf = build_management_memo_pdf(view)

    st.markdown(
        """
        <div class="ec-export-row">
            <div class="ec-export-card">
                <b>Export Tools</b><br><br>
                Download the executive memo or export the underlying AI action table for further review.
            </div>
            <div></div>
            <div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    download_col1, download_col2, download_col3 = st.columns([1, 1, 1], gap="medium")
    with download_col1:
        st.download_button(
            "Download Management Memo PDF",
            data=memo_pdf,
            file_name="ecai_institutional_portfolio_management_memo_v6_0.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with download_col2:
        st.download_button(
            "Download Action Table CSV",
            data=view[["Relationship", "Country", "Sector", "Exposure_USD_B", "Deposits_USD_B", "Treasury_Score", "Strategic_Score", "Risk_Score", "Management_Priority_Score", "Management_Priority_Band", "Management_Priority_Rationale", "AI_Action_Category", "AI_Management_Action"]].to_csv(index=False).encode("utf-8"),
            file_name="ecai_ai_management_action_table_v6_0.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with download_col3:
        st.download_button(
            "Download Memo Text",
            data=memo_text.encode("utf-8"),
            file_name="ecai_institutional_portfolio_management_memo_v6_0.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with st.expander("Preview Management Memo", expanded=True):
        st.markdown(build_management_memo_html(view), unsafe_allow_html=True)



st.markdown("---")
st.caption("EC-AI Institutional Relationship OS v6.0 | Executive Intelligence Layer + AI Management Action Engine + Relationship 360 Intelligence + Management Memo Generator")
