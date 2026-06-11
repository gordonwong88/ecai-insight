# EC-AI Institutional Relationship OS v8.0
# v8.0: Relationship Workspace becomes the primary operating environment
# Run:
#   python -m streamlit run ecai_institutional_relationship_os_v8_0.py

import io
import re
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="EC-AI Institutional Relationship OS v8.0",
    page_icon="🏦",
    layout="wide",
)

# -----------------------------
# CSS — executive workspace style
# -----------------------------
st.markdown(
    """
<style>
.block-container {padding-top: 1.0rem; padding-left: 1.8rem; padding-right: 1.8rem; max-width: 1920px;}
[data-testid="stSidebar"] {background: linear-gradient(180deg,#061A36 0%,#0B2C55 100%);} 
[data-testid="stSidebar"] * {color: white !important;}
[data-baseweb="tab-list"] {gap: 7px; background:#F8FAFC; padding:7px; border:1px solid #D8DEE6; border-radius:14px;}
[data-baseweb="tab"] {height:44px; padding:0 16px; border-radius:10px; font-weight:850; font-size:14px;}
[data-baseweb="tab"][aria-selected="true"] {background:#071B3A; color:white;}
.ec-hero {background: transparent; margin-bottom: 12px;}
.ec-title {font-size: 42px; line-height:1.12; font-weight:950; color:#071B3A; letter-spacing:-0.035em;}
.ec-sub {font-size: 20px; color:#0B2C55; font-weight:850; margin-top:4px;}
.ec-body {font-size: 15px; color:#526173; line-height:1.45; margin-top:5px; max-width:1280px;}
.section-title {font-size: 30px; font-weight: 950; color:#071B3A; margin-top:18px; margin-bottom:5px; letter-spacing:-0.02em;}
.section-sub {font-size: 15px; color:#526173; margin-bottom:12px;}
.workspace-header {background:linear-gradient(135deg,#071B3A 0%,#0B2C55 70%,#123E70 100%); color:white; border-radius:20px; padding:24px 28px; margin-top:12px; margin-bottom:16px; box-shadow:0 12px 26px rgba(7,27,58,.16);}
.workspace-name {font-size:38px; font-weight:950; line-height:1.1; letter-spacing:-0.03em;}
.workspace-meta {font-size:15px; color:#DCEBFF; margin-top:8px;}
.priority-badge {display:inline-block; border-radius:999px; padding:7px 12px; font-size:13px; font-weight:900; margin-top:14px;}
.card {background:white; border:1px solid #D8DEE6; border-radius:16px; padding:18px 20px; box-shadow:0 3px 10px rgba(15,23,42,.045); margin-bottom:14px;}
.card-title {font-size:19px; font-weight:950; color:#071B3A; margin-bottom:9px;}
.card-kicker {font-size:12px; color:#526173; font-weight:850; text-transform:uppercase; letter-spacing:.04em; margin-bottom:5px;}
.card-body {font-size:15.5px; line-height:1.55; color:#071B3A;}
.kpi-grid {display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:12px; margin-top:15px;}
.kpi {background:white; border:1px solid rgba(255,255,255,.30); border-radius:14px; padding:13px 14px; background:rgba(255,255,255,.10);}
.kpi-label {font-size:12px; color:#DCEBFF; font-weight:800; margin-bottom:5px;}
.kpi-value {font-size:22px; color:white; font-weight:950; line-height:1.1;}
.metric-card {background:#FFFFFF; border:1px solid #D8DEE6; border-radius:14px; padding:14px 16px; min-height:86px;}
.metric-label {font-size:13px; color:#526173; font-weight:850; margin-bottom:5px;}
.metric-value {font-size:25px; color:#071B3A; font-weight:950; line-height:1.1;}
.metric-sub {font-size:12px; color:#526173; margin-top:6px;}
.action-card {background:#F8FAFC; border-left:6px solid #1565C0; border-radius:16px; padding:18px 20px; margin-bottom:14px;}
.action-type {font-size:28px; font-weight:950; color:#071B3A; line-height:1.1;}
.action-row {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:14px;}
.action-mini {background:white; border:1px solid #D8DEE6; border-radius:12px; padding:12px 14px;}
.action-mini-label {font-size:12px; color:#526173; font-weight:850; margin-bottom:4px;}
.action-mini-value {font-size:16px; color:#071B3A; font-weight:950;}
.evidence-grid {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px;}
.outcome-grid {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px;}
.memo-box {background:#FFFFFF; border:1px solid #D8DEE6; border-radius:16px; padding:18px 20px; font-size:14.5px; line-height:1.55; color:#071B3A; max-height:520px; overflow:auto;}
.small-note {font-size:13px; color:#526173; line-height:1.45;}
.alert-high {background:#FEE2E2; color:#991B1B;}
.alert-med {background:#FFEDD5; color:#9A3412;}
.alert-low {background:#DCFCE7; color:#166534;}
[data-testid="stDataFrame"] div, [data-testid="stDataFrame"] span, [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td {font-size:13px !important;}
.stDownloadButton button, .stButton button {font-size:14px !important; padding:.58rem .9rem !important;}
@media (max-width: 1200px) {.kpi-grid,.evidence-grid,.outcome-grid,.action-row {grid-template-columns:repeat(2,minmax(0,1fr));}.ec-title{font-size:34px}.workspace-name{font-size:30px}}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Synthetic institutional portfolio data
# -----------------------------
rows = [
    ["ABC Infrastructure", "Infrastructure", "Singapore", "A", 8.5, 1.2, 54, 93, 64, 18, 2, 71, "Treasury Growth"],
    ["Pacific Energy", "Energy", "Australia", "A", 9.2, 1.4, 49, 84, 70, 16, 1, 78, "Treasury Growth"],
    ["Quantum Semicon", "Semiconductor", "Taiwan", "A+", 6.1, 3.1, 84, 87, 29, 41, 4, 86, "Strategic Growth"],
    ["Dragon Telecom", "Telecom", "China", "A", 5.9, 2.4, 73, 81, 47, 33, 3, 74, "Strategic Growth"],
    ["Eastern Development Bank", "Financials", "Korea", "A+", 5.0, 4.4, 91, 86, 24, 52, 6, 91, "Crown Jewel"],
    ["Meridian Sovereign Fund", "Sovereign", "UAE", "A+", 4.8, 5.2, 94, 95, 18, 58, 7, 94, "Crown Jewel"],
    ["Quantum Infrastructure Fund", "Infrastructure", "UAE", "A+", 8.9, 3.2, 88, 94, 22, 46, 5, 93, "Crown Jewel"],
    ["Crest Capital Partners", "Financials", "Hong Kong", "A", 4.3, 3.6, 91, 79, 23, 49, 5, 88, "Crown Jewel"],
    ["Sakura Financial", "Financials", "Japan", "A+", 5.2, 4.8, 92, 90, 28, 55, 6, 90, "Crown Jewel"],
    ["Titan Infrastructure Asia", "Infrastructure", "Philippines", "A", 8.2, 1.5, 58, 92, 61, 19, 2, 73, "Treasury Growth"],
    ["Nova Infrastructure Holdings", "Infrastructure", "Vietnam", "A", 7.6, 1.8, 61, 89, 53, 21, 2, 76, "Treasury Growth"],
    ["Terra Renewable Energy", "Renewables", "Australia", "A", 7.8, 1.9, 66, 90, 45, 24, 3, 79, "Strategic Growth"],
    ["Titan Energy Partners", "Energy", "Qatar", "A", 9.5, 2.5, 71, 89, 52, 28, 3, 81, "Treasury Growth"],
    ["Vertex Capital", "Financials", "Hong Kong", "A", 3.7, 3.4, 89, 75, 26, 45, 4, 85, "Crown Jewel"],
    ["Orion Infrastructure", "Infrastructure", "India", "A", 8.0, 2.0, 65, 91, 57, 23, 2, 75, "Treasury Growth"],
    ["Pacific Semiconductor", "Semiconductor", "Taiwan", "A", 6.3, 3.0, 83, 88, 30, 39, 4, 84, "Strategic Growth"],
    ["Bluewave Offshore", "Offshore Services", "Malaysia", "B", 4.1, 0.7, 31, 44, 86, 9, 0, 42, "Portfolio Review"],
    ["Oceanlink Shipping", "Shipping", "Hong Kong", "B", 6.4, 0.8, 35, 42, 88, 8, 1, 39, "Portfolio Review"],
    ["Polaris Shipping", "Shipping", "Greece", "B", 5.7, 0.6, 25, 38, 92, 7, 0, 33, "Portfolio Review"],
    ["Oceanic Bulk Carriers", "Shipping", "Greece", "B", 6.0, 0.5, 22, 35, 94, 6, 0, 29, "Portfolio Review"],
]
cols = [
    "Relationship", "Sector", "Country", "Strategic_Tier", "Exposure_USD_B", "Deposits_USD_B",
    "Treasury_Score", "Strategic_Score", "Risk_Score", "Wallet_Share_Pct",
    "Executive_Meetings_12M", "Competitive_Position", "Priority"
]
df = pd.DataFrame(rows, columns=cols)

# -----------------------------
# Decision engine
# -----------------------------
def fmt_b(x: float) -> str:
    return f"USD {float(x):.1f}B"


def fmt_pct_num(x: float) -> str:
    return f"{float(x):.0f}%"


def management_priority_score(row, max_exposure):
    exposure_importance = row["Exposure_USD_B"] / max_exposure * 100 if max_exposure else 0
    treasury_opportunity = max(0, 100 - row["Treasury_Score"])
    relationship_gap = max(0, 100 - row["Strategic_Score"])
    deposit_gap = max(0, 40 - row["Wallet_Share_Pct"]) * 1.6
    risk_alert = row["Risk_Score"]
    score = 0.30 * exposure_importance + 0.25 * treasury_opportunity + 0.15 * relationship_gap + 0.15 * deposit_gap + 0.15 * risk_alert
    return round(score, 1)


def priority_band(score):
    if score >= 75:
        return "Immediate Management Attention"
    if score >= 65:
        return "High Priority"
    if score >= 50:
        return "Active Monitor"
    return "Stable"


def priority_css(score):
    if score >= 75:
        return "alert-high"
    if score >= 65:
        return "alert-med"
    return "alert-low"


def management_priority_label(score):
    if score >= 75:
        return "HIGH"
    if score >= 65:
        return "MEDIUM-HIGH"
    if score >= 50:
        return "MONITOR"
    return "STABLE"


def action_type(row):
    if row["Risk_Score"] >= 85 and row["Treasury_Score"] < 60:
        return "Risk Escalation"
    if row["Risk_Score"] >= 80:
        return "Credit Review"
    if row["Strategic_Score"] >= 85 and row["Treasury_Score"] < 70:
        return "Treasury Deep Dive"
    if row["Wallet_Share_Pct"] < 20 and row["Strategic_Score"] >= 80:
        return "Wallet Expansion"
    if row["Executive_Meetings_12M"] <= 1 and row["Strategic_Score"] >= 75:
        return "Executive Engagement"
    if row["Deposits_USD_B"] / row["Exposure_USD_B"] < 0.22:
        return "Deposit Retention"
    if row["Strategic_Tier"] == "A+":
        return "Strategic Relationship Investment"
    return "Coverage Enhancement"


def action_owner(action):
    if action in ["Credit Review", "Risk Escalation"]:
        return "Coverage + Risk"
    if action in ["Treasury Deep Dive", "Deposit Retention", "Wallet Expansion"]:
        return "RM + Treasury"
    if action in ["Executive Engagement", "Strategic Relationship Investment"]:
        return "Coverage Director"
    return "Relationship Manager"


def action_timeline(score, action):
    if score >= 75 or action in ["Risk Escalation", "Credit Review"]:
        return "This week"
    if score >= 65:
        return "30 days"
    return "Next review cycle"


def action_confidence(row):
    signal_strength = (abs(70 - row["Treasury_Score"]) + abs(70 - row["Risk_Score"]) + abs(35 - row["Wallet_Share_Pct"])) / 3
    return min(94, max(68, round(72 + signal_strength * 0.55)))


def rationale_points(row):
    points = []
    if row["Exposure_USD_B"] >= 8:
        points.append("Material exposure size requires senior visibility")
    if row["Treasury_Score"] < 70:
        points.append("Treasury penetration is below desired relationship potential")
    if row["Wallet_Share_Pct"] < 25:
        points.append("Wallet share is under-monetized versus strategic importance")
    if row["Risk_Score"] >= 80:
        points.append("Risk indicators are elevated and need active monitoring")
    if row["Executive_Meetings_12M"] <= 1:
        points.append("Executive engagement cadence is low")
    if not points:
        points.append("Relationship remains strategically relevant and should be protected")
    return points[:4]


def ai_situation_report(row):
    wallet_ratio = row["Deposits_USD_B"] / row["Exposure_USD_B"] * 100 if row["Exposure_USD_B"] else 0
    action = row["Recommended_Action"]
    tone = "requires near-term management attention" if row["Management_Priority_Score"] >= 65 else "is stable but should remain under active coverage discipline"
    risk_sentence = " Risk indicators are elevated and require closer credit and sector review." if row["Risk_Score"] >= 80 else " Risk indicators are manageable under the current portfolio view."
    treasury_sentence = " Treasury penetration remains below strategic potential, creating a clear wallet expansion opportunity." if row["Treasury_Score"] < 70 else " Treasury linkage is comparatively strong and should be protected."
    return (
        f"{row['Relationship']} is a {row['Strategic_Tier']} institutional relationship in {row['Country']} with "
        f"{fmt_b(row['Exposure_USD_B'])} exposure and {fmt_b(row['Deposits_USD_B'])} deposits. "
        f"The relationship {tone} because management priority is driven by exposure relevance, wallet monetization, treasury penetration and risk signals. "
        f"Current deposit-to-exposure linkage is {wallet_ratio:.1f}%, while wallet share is {row['Wallet_Share_Pct']:.0f}%."
        f"{treasury_sentence}{risk_sentence} EC-AI recommends {action} as the next management action."
    )


def strategic_assessment(row):
    if row["Recommended_Action"] in ["Risk Escalation", "Credit Review"]:
        return "Risk discipline should take priority before additional wallet growth. Management should clarify refinancing sensitivity, sector outlook and exposure appetite."
    if row["Recommended_Action"] in ["Treasury Deep Dive", "Wallet Expansion", "Deposit Retention"]:
        return "The relationship is strategically valuable but under-monetized. Management should convert lending relevance into operating deposits, cash management, FX and flow wallet."
    if row["Recommended_Action"] == "Executive Engagement":
        return "The relationship has strategic value but executive access is insufficient. Senior banker engagement can strengthen positioning and improve competitive relevance."
    return "The relationship should be protected through disciplined coverage, continued wallet tracking and periodic senior review."


def expected_outcome(row):
    deposit_growth = max(0.05, min(0.32, (100 - row["Treasury_Score"]) / 220))
    deposit_uplift = row["Deposits_USD_B"] * deposit_growth
    wallet_uplift = max(3, min(12, int((100 - row["Wallet_Share_Pct"]) / 8)))
    revenue_uplift = row["Exposure_USD_B"] * (0.22 + wallet_uplift / 100)  # illustrative USD mm proxy
    probability = min(88, max(55, 92 - row["Risk_Score"] * 0.35 + row["Strategic_Score"] * 0.12))
    if row["Recommended_Action"] in ["Risk Escalation", "Credit Review"]:
        return {
            "Deposit Growth": "Defensive",
            "Wallet Expansion": "Selective",
            "Relationship Strength": "Stabilise",
            "Probability": f"{probability:.0f}%",
            "Detail": "Expected outcome is downside protection, clearer risk appetite and controlled follow-up actions."
        }
    return {
        "Deposit Growth": f"+USD {deposit_uplift:.1f}B",
        "Wallet Expansion": f"+{wallet_uplift} pts",
        "Relationship Strength": "Moderate → Strong" if row["Strategic_Score"] >= 75 else "Weak → Moderate",
        "Probability": f"{probability:.0f}%",
        "Detail": f"Expected outcome is improved liquidity linkage, broader product penetration and stronger executive positioning. Illustrative revenue opportunity: USD {revenue_uplift:.1f}M."
    }


def build_relationship_memo(row):
    outcome = expected_outcome(row)
    points = rationale_points(row)
    today = date.today().strftime("%d %B %Y")
    lines = []
    lines.append(f"# EC-AI Executive Relationship Memo")
    lines.append("")
    lines.append(f"**Relationship:** {row['Relationship']}")
    lines.append(f"**Date:** {today}")
    lines.append(f"**Management Priority:** {management_priority_label(row['Management_Priority_Score'])}")
    lines.append(f"**Recommended Action:** {row['Recommended_Action']}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(ai_situation_report(row))
    lines.append("")
    lines.append("## Strategic Assessment")
    lines.append(strategic_assessment(row))
    lines.append("")
    lines.append("## Why Management Should Care")
    for p in points:
        lines.append(f"- {p}.")
    lines.append("")
    lines.append("## Recommended Management Action")
    lines.append(f"- Action type: {row['Recommended_Action']}")
    lines.append(f"- Priority: {management_priority_label(row['Management_Priority_Score'])}")
    lines.append(f"- Owner: {row['Owner']}")
    lines.append(f"- Timeline: {row['Timeline']}")
    lines.append(f"- Confidence: {row['Confidence']}%")
    lines.append("")
    lines.append("## Supporting Evidence")
    lines.append(f"- Treasury score: {int(row['Treasury_Score'])}/100")
    lines.append(f"- Strategic score: {int(row['Strategic_Score'])}/100")
    lines.append(f"- Risk score: {int(row['Risk_Score'])}/100")
    lines.append(f"- Wallet share: {int(row['Wallet_Share_Pct'])}%")
    lines.append(f"- Executive meetings in last 12 months: {int(row['Executive_Meetings_12M'])}")
    lines.append("")
    lines.append("## Expected Outcome")
    lines.append(f"- Deposit growth: {outcome['Deposit Growth']}")
    lines.append(f"- Wallet expansion: {outcome['Wallet Expansion']}")
    lines.append(f"- Relationship strength: {outcome['Relationship Strength']}")
    lines.append(f"- Probability: {outcome['Probability']}")
    lines.append(f"- Note: {outcome['Detail']}")
    lines.append("")
    lines.append("---")
    lines.append("Generated by EC-AI Institutional Relationship OS v8.0")
    return "\n".join(lines)


def markdown_to_pdf(markdown_text: str) -> bytes:
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
    styles.add(ParagraphStyle(name="ECTitle", parent=styles["Title"], fontSize=18, leading=23, alignment=TA_LEFT, spaceAfter=12))
    styles.add(ParagraphStyle(name="ECH2", parent=styles["Heading2"], fontSize=13.5, leading=17, spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="ECBody", parent=styles["BodyText"], fontSize=10.3, leading=15.5, spaceAfter=5))
    styles.add(ParagraphStyle(name="ECSmall", parent=styles["BodyText"], fontSize=9, leading=12, textColor="#4B5563"))

    story = []
    for raw in str(markdown_text).splitlines():
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 0.07 * inch))
            continue
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe)
        if safe.startswith("# "):
            story.append(Paragraph(safe[2:], styles["ECTitle"]))
        elif safe.startswith("## "):
            story.append(Paragraph(safe[3:], styles["ECH2"]))
        elif safe.startswith("- "):
            story.append(Paragraph("• " + safe[2:], styles["ECBody"]))
        elif safe.startswith("---"):
            story.append(Spacer(1, 0.12 * inch))
        else:
            story.append(Paragraph(safe, styles["ECBody"]))
    doc.build(story)
    return buf.getvalue()


max_exposure = df["Exposure_USD_B"].max()
df["Management_Priority_Score"] = df.apply(lambda r: management_priority_score(r, max_exposure), axis=1)
df["Management_Priority_Band"] = df["Management_Priority_Score"].apply(priority_band)
df["Recommended_Action"] = df.apply(action_type, axis=1)
df["Owner"] = df["Recommended_Action"].apply(action_owner)
df["Timeline"] = df.apply(lambda r: action_timeline(r["Management_Priority_Score"], r["Recommended_Action"]), axis=1)
df["Confidence"] = df.apply(action_confidence, axis=1)
df["Attention_Label"] = df["Management_Priority_Score"].apply(management_priority_label)

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.markdown("## EC-AI")
st.sidebar.markdown("Institutional Relationship OS")
st.sidebar.markdown("**v8.0**")
st.sidebar.markdown("---")
st.sidebar.caption("Relationship Workspace is now the primary operating environment.")

countries = st.sidebar.multiselect("Country", sorted(df["Country"].unique()), default=sorted(df["Country"].unique()))
sectors = st.sidebar.multiselect("Sector", sorted(df["Sector"].unique()), default=sorted(df["Sector"].unique()))
view = df[df["Country"].isin(countries) & df["Sector"].isin(sectors)].copy()

if view.empty:
    st.warning("No relationships match the selected filters.")
    st.stop()

# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="ec-hero">
        <div class="ec-title">EC-AI Institutional Relationship OS v8.0</div>
        <div class="ec-sub">Management Attention Allocation for Institutional Banking</div>
        <div class="ec-body">
        EC-AI converts portfolio intelligence into relationship-level decisions: which relationships require management attention, what action should be taken, who owns it, and what outcome is expected.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Relationship Workspace first
tab_workspace, tab_command, tab_actions, tab_portfolio, tab_memo = st.tabs(
    [
        "Relationship Workspace",
        "Executive Command Center",
        "Management Actions",
        "Portfolio Intelligence",
        "Executive Memo Center",
    ]
)

# -----------------------------
# Relationship Workspace
# -----------------------------
with tab_workspace:
    default_relationship = view.sort_values("Management_Priority_Score", ascending=False).iloc[0]["Relationship"]
    selected = st.selectbox(
        "Select relationship",
        view.sort_values("Management_Priority_Score", ascending=False)["Relationship"].tolist(),
        index=view.sort_values("Management_Priority_Score", ascending=False)["Relationship"].tolist().index(default_relationship),
    )
    r = view[view["Relationship"] == selected].iloc[0]
    wallet_ratio = r["Deposits_USD_B"] / r["Exposure_USD_B"] * 100 if r["Exposure_USD_B"] else 0
    badge_class = priority_css(r["Management_Priority_Score"])

    st.markdown(
        f"""
        <div class="workspace-header">
            <div class="workspace-name">{r['Relationship']}</div>
            <div class="workspace-meta">{r['Country']} · {r['Sector']} · Strategic Tier {r['Strategic_Tier']} · {r['Priority']}</div>
            <span class="priority-badge {badge_class}">Management Priority: {r['Attention_Label']} · Score {r['Management_Priority_Score']:.1f}</span>
            <div class="kpi-grid">
                <div class="kpi"><div class="kpi-label">Exposure</div><div class="kpi-value">{fmt_b(r['Exposure_USD_B'])}</div></div>
                <div class="kpi"><div class="kpi-label">Deposits</div><div class="kpi-value">{fmt_b(r['Deposits_USD_B'])}</div></div>
                <div class="kpi"><div class="kpi-label">Wallet Share</div><div class="kpi-value">{fmt_pct_num(r['Wallet_Share_Pct'])}</div></div>
                <div class="kpi"><div class="kpi-label">Treasury</div><div class="kpi-value">{int(r['Treasury_Score'])}</div></div>
                <div class="kpi"><div class="kpi-label">Risk</div><div class="kpi-value">{int(r['Risk_Score'])}</div></div>
                <div class="kpi"><div class="kpi-label">Exec Meetings</div><div class="kpi-value">{int(r['Executive_Meetings_12M'])}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        st.markdown('<div class="card"><div class="card-kicker">AI Situation Report</div><div class="card-title">Executive Narrative</div><div class="card-body">' + ai_situation_report(r) + '</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><div class="card-kicker">Strategic Assessment</div><div class="card-title">What management should understand</div><div class="card-body">' + strategic_assessment(r) + '</div></div>', unsafe_allow_html=True)

    with right:
        st.markdown(
            f"""
            <div class="action-card">
                <div class="card-kicker">Recommended Management Action</div>
                <div class="action-type">{r['Recommended_Action']}</div>
                <div class="action-row">
                    <div class="action-mini"><div class="action-mini-label">Priority</div><div class="action-mini-value">{r['Attention_Label']}</div></div>
                    <div class="action-mini"><div class="action-mini-label">Owner</div><div class="action-mini-value">{r['Owner']}</div></div>
                    <div class="action-mini"><div class="action-mini-label">Timeline</div><div class="action-mini-value">{r['Timeline']}</div></div>
                    <div class="action-mini"><div class="action-mini-label">Confidence</div><div class="action-mini-value">{r['Confidence']}%</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="card"><div class="card-title">Why recommended</div><div class="card-body"><ul>' + "".join([f"<li>{p}</li>" for p in rationale_points(r)]) + '</ul></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Supporting Evidence</div><div class="section-sub">Only evidence that supports the recommended decision is shown.</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="evidence-grid">
            <div class="metric-card"><div class="metric-label">Treasury Penetration</div><div class="metric-value">{int(r['Treasury_Score'])}/100</div><div class="metric-sub">Peer aspiration: 80+</div></div>
            <div class="metric-card"><div class="metric-label">Deposit / Exposure Linkage</div><div class="metric-value">{wallet_ratio:.1f}%</div><div class="metric-sub">Operating liquidity linkage</div></div>
            <div class="metric-card"><div class="metric-label">Wallet Share</div><div class="metric-value">{int(r['Wallet_Share_Pct'])}%</div><div class="metric-sub">Peer benchmark: 35%</div></div>
            <div class="metric-card"><div class="metric-label">Competitive Position</div><div class="metric-value">{int(r['Competitive_Position'])}</div><div class="metric-sub">100 = strongest position</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Expected Outcome</div><div class="section-sub">Projected management outcome if the recommended action is executed.</div>', unsafe_allow_html=True)
    outcome = expected_outcome(r)
    st.markdown(
        f"""
        <div class="outcome-grid">
            <div class="metric-card"><div class="metric-label">Deposit Growth</div><div class="metric-value">{outcome['Deposit Growth']}</div><div class="metric-sub">Illustrative management target</div></div>
            <div class="metric-card"><div class="metric-label">Wallet Expansion</div><div class="metric-value">{outcome['Wallet Expansion']}</div><div class="metric-sub">Potential increase</div></div>
            <div class="metric-card"><div class="metric-label">Relationship Strength</div><div class="metric-value" style="font-size:20px;">{outcome['Relationship Strength']}</div><div class="metric-sub">Coverage outcome</div></div>
            <div class="metric-card"><div class="metric-label">Probability</div><div class="metric-value">{outcome['Probability']}</div><div class="metric-sub">Rule-based confidence</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="card"><div class="card-body">{outcome["Detail"]}</div></div>', unsafe_allow_html=True)

    memo = build_relationship_memo(r)
    memo_pdf = markdown_to_pdf(memo)
    st.markdown('<div class="section-title">Executive Memo</div><div class="section-sub">Generate a relationship-level management memo for review, committee discussion or banker follow-up.</div>', unsafe_allow_html=True)
    mcol1, mcol2 = st.columns([1.2, 1], gap="large")
    with mcol1:
        st.markdown('<div class="memo-box">' + memo.replace("\n", "<br>") + '</div>', unsafe_allow_html=True)
    with mcol2:
        safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", selected).strip("_").lower()
        st.download_button(
            "Download Executive Memo PDF",
            data=memo_pdf,
            file_name=f"ecai_executive_relationship_memo_{safe_name}_v8_0.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        st.download_button(
            "Download Memo Text",
            data=memo.encode("utf-8"),
            file_name=f"ecai_executive_relationship_memo_{safe_name}_v8_0.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.markdown('<div class="small-note">v8.0 memo is generated from the same decision engine used in the Relationship Workspace.</div>', unsafe_allow_html=True)

# -----------------------------
# Executive Command Center
# -----------------------------
with tab_command:
    command = view.sort_values("Management_Priority_Score", ascending=False).copy()
    high_count = int((command["Management_Priority_Score"] >= 65).sum())
    immediate_count = int((command["Management_Priority_Score"] >= 75).sum())
    top = command.iloc[0]
    total_exposure = command["Exposure_USD_B"].sum()
    total_deposits = command["Deposits_USD_B"].sum()
    portfolio_health = "Action Required" if immediate_count else ("Watchlist" if high_count >= 4 else "Stable")

    st.markdown('<div class="section-title">Executive Command Center</div><div class="section-sub">Answers the weekly management question: which relationships require attention now?</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="evidence-grid">
            <div class="metric-card"><div class="metric-label">Portfolio Health</div><div class="metric-value">{portfolio_health}</div><div class="metric-sub">Based on priority signals</div></div>
            <div class="metric-card"><div class="metric-label">Priority Relationships</div><div class="metric-value">{high_count}</div><div class="metric-sub">Score ≥ 65</div></div>
            <div class="metric-card"><div class="metric-label">Immediate Actions</div><div class="metric-value">{immediate_count}</div><div class="metric-sub">Score ≥ 75</div></div>
            <div class="metric-card"><div class="metric-label">Top Relationship</div><div class="metric-value" style="font-size:20px;">{top['Relationship']}</div><div class="metric-sub">{top['Recommended_Action']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="card"><div class="card-title">Executive Decision Brief</div><div class="card-body">The filtered portfolio has {fmt_b(total_exposure)} exposure and {fmt_b(total_deposits)} deposits. EC-AI identifies <b>{high_count}</b> relationships requiring management attention. The top priority is <b>{top["Relationship"]}</b>, where the recommended action is <b>{top["Recommended_Action"]}</b>.</div></div>',
        unsafe_allow_html=True,
    )

    top_cards = command.head(4).reset_index(drop=True)
    cols_cards = st.columns(4, gap="medium")
    for i, (_, row) in enumerate(top_cards.iterrows()):
        with cols_cards[i]:
            st.markdown(
                f"""
                <div class="card">
                    <div class="card-kicker">Priority #{i+1} · Score {row['Management_Priority_Score']:.1f}</div>
                    <div class="card-title">{row['Relationship']}</div>
                    <div class="card-body"><b>{row['Recommended_Action']}</b><br><br>{'; '.join(rationale_points(row))}.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# -----------------------------
# Management Actions
# -----------------------------
with tab_actions:
    st.markdown('<div class="section-title">Management Actions</div><div class="section-sub">Action queue by relationship, owner and timeline.</div>', unsafe_allow_html=True)
    actions = view.sort_values("Management_Priority_Score", ascending=False).copy()
    actions["Exposure"] = actions["Exposure_USD_B"].map(fmt_b)
    actions["Deposits"] = actions["Deposits_USD_B"].map(fmt_b)
    actions["Priority Score"] = actions["Management_Priority_Score"].map(lambda x: f"{x:.1f}")
    table = actions[[
        "Relationship", "Country", "Sector", "Exposure", "Deposits", "Recommended_Action", "Attention_Label", "Owner", "Timeline", "Confidence", "Priority Score"
    ]].rename(columns={"Recommended_Action": "Action Type", "Attention_Label": "Priority"})
    st.dataframe(table, use_container_width=True, hide_index=True, height=520)

    summary = actions.groupby("Recommended_Action").agg(Relationships=("Relationship", "count"), Avg_Priority=("Management_Priority_Score", "mean")).reset_index()
    summary["Avg_Priority"] = summary["Avg_Priority"].map(lambda x: f"{x:.1f}")
    st.markdown('<div class="section-title">Action Taxonomy Summary</div>', unsafe_allow_html=True)
    st.dataframe(summary.rename(columns={"Recommended_Action": "Action Type"}), use_container_width=True, hide_index=True, height=240)

# -----------------------------
# Portfolio Intelligence
# -----------------------------
with tab_portfolio:
    st.markdown('<div class="section-title">Portfolio Intelligence</div><div class="section-sub">Evidence layer only. The product is not the chart; the product is management attention allocation.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        fig = px.scatter(
            view,
            x="Treasury_Score",
            y="Strategic_Score",
            size="Exposure_USD_B",
            color="Recommended_Action",
            hover_name="Relationship",
            hover_data=["Country", "Sector", "Risk_Score", "Management_Priority_Score"],
            title="Relationship Positioning: Treasury vs Strategic Score",
        )
        fig.update_layout(height=470, template="plotly_white", legend_title_text="Action")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        bar = view.sort_values("Management_Priority_Score", ascending=False).head(10)
        fig2 = px.bar(bar, x="Management_Priority_Score", y="Relationship", orientation="h", color="Recommended_Action", title="Top Management Attention Signals")
        fig2.update_layout(height=470, template="plotly_white", yaxis={"categoryorder":"total ascending"}, legend_title_text="Action")
        st.plotly_chart(fig2, use_container_width=True)

    evidence = view.copy()
    evidence["Exposure"] = evidence["Exposure_USD_B"].map(fmt_b)
    evidence["Deposits"] = evidence["Deposits_USD_B"].map(fmt_b)
    evidence["Priority Score"] = evidence["Management_Priority_Score"].map(lambda x: f"{x:.1f}")
    st.dataframe(
        evidence[["Relationship", "Country", "Sector", "Strategic_Tier", "Exposure", "Deposits", "Treasury_Score", "Strategic_Score", "Risk_Score", "Wallet_Share_Pct", "Priority Score", "Recommended_Action"]],
        use_container_width=True,
        hide_index=True,
        height=360,
    )

# -----------------------------
# Executive Memo Center
# -----------------------------
with tab_memo:
    st.markdown('<div class="section-title">Executive Memo Center</div><div class="section-sub">Generate relationship-level memos or portfolio-level management briefs.</div>', unsafe_allow_html=True)
    memo_relationship = st.selectbox("Select memo relationship", view.sort_values("Management_Priority_Score", ascending=False)["Relationship"].tolist(), key="memo_select")
    memo_row = view[view["Relationship"] == memo_relationship].iloc[0]
    memo_text = build_relationship_memo(memo_row)
    memo_pdf = markdown_to_pdf(memo_text)
    l, rcol = st.columns([1.35, 1], gap="large")
    with l:
        st.markdown('<div class="memo-box">' + memo_text.replace("\n", "<br>") + '</div>', unsafe_allow_html=True)
    with rcol:
        safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", memo_relationship).strip("_").lower()
        st.download_button(
            "Download Relationship Memo PDF",
            data=memo_pdf,
            file_name=f"ecai_relationship_memo_{safe_name}_v8_0.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        portfolio_brief = [
            "# EC-AI Weekly Management Attention Brief",
            "",
            f"**Portfolio health:** {'Action Required' if int((view['Management_Priority_Score'] >= 75).sum()) else 'Watchlist'}",
            f"**Priority relationships:** {int((view['Management_Priority_Score'] >= 65).sum())}",
            "",
            "## Top Management Actions",
        ]
        for i, (_, rr) in enumerate(view.sort_values("Management_Priority_Score", ascending=False).head(8).iterrows(), 1):
            portfolio_brief.append(f"{i}. **{rr['Relationship']}** — {rr['Recommended_Action']} | Owner: {rr['Owner']} | Timeline: {rr['Timeline']} | Score: {rr['Management_Priority_Score']:.1f}")
        portfolio_brief.append("")
        portfolio_brief.append("## Management Agenda")
        portfolio_brief.append("- Open review with the highest priority relationship.")
        portfolio_brief.append("- Assign owner and 30-day action plan for each high-priority relationship.")
        portfolio_brief.append("- Separate growth actions from risk actions to avoid unclear accountability.")
        portfolio_brief.append("- Track closure in the next weekly management review.")
        portfolio_brief.append("")
        portfolio_brief.append("---")
        portfolio_brief.append("Generated by EC-AI Institutional Relationship OS v8.0")
        portfolio_text = "\n".join(portfolio_brief)
        portfolio_pdf = markdown_to_pdf(portfolio_text)
        st.download_button(
            "Download Weekly Portfolio Brief PDF",
            data=portfolio_pdf,
            file_name="ecai_weekly_management_attention_brief_v8_0.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        st.markdown('<div class="small-note">This center turns Relationship Workspace output into executive-ready documents.</div>', unsafe_allow_html=True)
