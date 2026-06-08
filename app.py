
# EC-AI Institutional Relationship OS v2.1
# v2.1: Executive Action Queue + PDF memo export + improved readability
# Run:
#   python -m streamlit run ecai_institutional_relationship_os_v2_1.py

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

/* v2.1 readability polish */
html, body, [class*="css"] { font-size: 16px; }
p, li, div { line-height: 1.45; }
[data-testid="stDataFrame"] div { font-size: 14px !important; }
[data-testid="stDataFrame"] th { font-size: 14px !important; font-weight: 800 !important; }
[data-testid="stDataFrame"] td { font-size: 14px !important; }
.stDownloadButton button, .stButton button { font-size: 14px !important; padding: 0.55rem 0.8rem !important; }
.narrative-box { font-size: 15px; }
.side-card { font-size: 14px; }

</style>
""", unsafe_allow_html=True)

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
    lines.append("## Recommended Management Agenda")
    lines.append("1. Prioritize treasury deepening for strategic relationships with weak deposit linkage.")
    lines.append("2. Review large exposure names for senior coverage and portfolio concentration.")
    lines.append("3. Monitor shipping, offshore, and other cyclical relationships with elevated risk scores.")
    lines.append("4. Protect high-quality funding relationships and maintain pricing discipline.")
    lines.append("5. Use relationship-level action categories to guide banker follow-up and management committee discussion.")
    lines.append("")
    lines.append("---")
    lines.append("Generated by EC-AI Institutional Relationship OS v2.1")
    return "\\n".join(lines)


def build_management_memo_html(data):
    memo = build_management_memo(data)
    html = memo.replace("\\n", "<br>")
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
    styles.add(ParagraphStyle(name="ECTitle", parent=styles["Title"], fontSize=20, leading=24, alignment=TA_LEFT, spaceAfter=12))
    styles.add(ParagraphStyle(name="ECH2", parent=styles["Heading2"], fontSize=15, leading=19, spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="ECBody", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=5))
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
            story.append(Paragraph("Generated by EC-AI Institutional Relationship OS v2.1", styles["ECSmall"]))
        else:
            story.append(Paragraph(safe, styles["ECBody"]))

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
    lines.append("Generated by EC-AI Institutional Relationship OS v2.1")
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
st.sidebar.markdown("v2.1")
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
st.markdown("""
# EC-AI Institutional Relationship OS

### AI-Powered Executive Relationship Intelligence

EC-AI transforms institutional portfolio data into:

• **Portfolio Cognition**  
• **AI Management Action Engine**  
• **Relationship 360 Intelligence**  
• **Executive Management Memo Generation**

Traditional dashboards show data.  
**EC-AI is designed to show management actions.**
""")

st.markdown("## 🎬 Product Demo")

demo_left, demo_right = st.columns([1.9, 1.1], gap="large")

with demo_left:
    st.video("https://youtu.be/Cc5pDDt0nMY")
    st.caption("Watch a short overview of EC-AI Institutional Relationship OS.")

with demo_right:
    st.markdown(
        """
        <div class="narrative-box">
        <b>What EC-AI does</b><br><br>
        EC-AI turns institutional portfolio data into executive relationship intelligence.
        It helps identify treasury opportunities, strategic relationship priorities,
        concentration risk, and banker coverage actions.
        <br><br>
        <b>Core engines</b><br>
        • Portfolio Cognition<br>
        • AI Management Action Engine<br>
        • Relationship 360 Intelligence<br>
        • Management Memo Generator
        </div>
        """,
        unsafe_allow_html=True,
    )

st.success("""
Explore the live platform below.
""")

st.divider()

# =========================
# HEADER
# =========================
header_left, header_right = st.columns([4.6, 1.4], gap="large")
with header_left:
    st.markdown('<div class="main-title">Portfolio Cognition Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Executive view of institutional relationships | EC-AI Synthetic Institutional Portfolio Dataset v2.1</div>',
        unsafe_allow_html=True,
    )

with header_right:
    st.markdown(
        """
        <div class="portfolio-card">
            <div class="portfolio-label">Portfolio</div>
            <div class="portfolio-name">EC-AI Institutional Portfolio</div>
            <div class="portfolio-date">As of May 15, 2025</div>
        </div>
        """,
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
# MAIN GRID
# =========================
main_left, main_mid, main_right = st.columns([3.4, 1.5, 1.05], gap="large")

key_df = view.sort_values(
    ["Exposure_USD_B", "Strategic_Score", "Risk_Score"],
    ascending=[False, False, False],
).reset_index(drop=True)
key_df["Chart_No"] = range(1, len(key_df) + 1)
key_map = dict(zip(key_df["Relationship"], key_df["Chart_No"]))
view["Chart_No"] = view["Relationship"].map(key_map)
view["Label"] = view["Chart_No"].astype(str)

# =========================
# QUADRANT CHART
# =========================
with main_left:
    st.markdown("## Portfolio Cognition Quadrant")
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
        size_max=28,
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

    fig.add_annotation(x=22, y=96, text="<b>OPTIMIZATION FOCUS</b>", showarrow=False, font=dict(size=12, color="#6B4E16"))
    fig.add_annotation(x=88, y=96, text="<b>CROWN JEWEL</b>", showarrow=False, font=dict(size=12, color="#0B6B2E"))
    fig.add_annotation(x=22, y=8, text="<b>PORTFOLIO REVIEW</b>", showarrow=False, font=dict(size=12, color="#7F1D1D"))
    fig.add_annotation(x=88, y=8, text="<b>TREASURY ANCHOR</b>", showarrow=False, font=dict(size=12, color="#0B3D75"))

    fig.update_traces(
        textposition="middle center",
        textfont=dict(size=10, color="white", family="Arial Black"),
        marker=dict(opacity=0.78, line=dict(width=1, color="white")),
    )

    fig.update_layout(
        template="plotly_white",
        height=640,
        margin=dict(l=10, r=10, t=20, b=20),
        showlegend=False,
        font=dict(family="Inter, Arial", size=11, color="#071B3A"),
        xaxis=dict(title="Treasury Score", range=[0, 100], dtick=10, gridcolor="rgba(17,24,39,.08)"),
        yaxis=dict(title="Strategic Score", range=[0, 100], dtick=10, gridcolor="rgba(17,24,39,.08)"),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

# =========================
# RELATIONSHIP REFERENCE
# =========================
with main_mid:
    st.markdown("### Relationship Reference")
    st.caption("By chart number")
    ref = key_df[["Chart_No", "Relationship", "Exposure_USD_B"]].copy()
    ref = ref.rename(columns={"Chart_No": "#", "Exposure_USD_B": "Exposure (USD B)"})
    ref["Exposure (USD B)"] = ref["Exposure (USD B)"].map(lambda x: f"{x:.1f}")
    st.dataframe(ref, use_container_width=True, hide_index=True, height=640)

# =========================
# RIGHT PANEL
# =========================
with main_right:
    st.markdown('<div class="side-title">Portfolio Concentration</div>', unsafe_allow_html=True)

    top5_pct = view.nlargest(5, "Exposure_USD_B")["Exposure_USD_B"].sum() / total_exposure * 100
    infra_pct = view[view["Sector"] == "Infrastructure"]["Exposure_USD_B"].sum() / total_exposure * 100
    shipping_pct = view[view["Sector"].isin(["Shipping", "Aviation"])]["Exposure_USD_B"].sum() / total_exposure * 100

    st.markdown(f'<div class="side-card"><b>Top 5 Relationships</b><br><span style="font-size:24px;font-weight:850;color:#071B3A;">{top5_pct:.1f}%</span><br>of portfolio exposure</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="side-card"><b>Infrastructure Concentration</b><br><span style="font-size:24px;font-weight:850;color:#071B3A;">{infra_pct:.1f}%</span><br>of total exposure</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="side-card"><b>Shipping & Aviation Risk</b><br><span style="font-size:24px;font-weight:850;color:#071B3A;">{shipping_pct:.1f}%</span><br>of exposure</div>', unsafe_allow_html=True)

    st.markdown('<div class="side-title">Top Management Actions</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="side-card">
        1. Deepen treasury linkage for infrastructure relationships<br><br>
        2. Monitor refinancing-sensitive shipping exposures<br><br>
        3. Protect crown-jewel deposit relationships<br><br>
        4. Expand wallet penetration across strategic names
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# LOWER GRID
# =========================
lower_left, lower_right = st.columns([3.35, 1.65], gap="large")

with lower_left:
    st.markdown("## Management Attention Priorities")
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
        height=330,
    )

with lower_right:
    st.markdown("## Relationship Quick Drilldown")
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
        <div class="ai-box">
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
st.markdown("## Executive Intelligence Layer")
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

pcol1, pcol2 = st.columns([1.35, 3.65], gap="large")

with pcol1:
    avg_priority_score = priority_view["Management_Priority_Score"].mean()
    top_priority_name = priority_view.iloc[0]["Relationship"]
    high_priority_count = int((priority_view["Management_Priority_Score"] >= 65).sum())

    st.markdown(
        f"""
        <div class="side-card">
        <b>Average Priority Score</b><br>
        <span style="font-size:28px;font-weight:850;color:#071B3A;">{avg_priority_score:.1f}</span><br>
        across filtered relationships
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="side-card">
        <b>Top Management Priority</b><br>
        <span style="font-size:18px;font-weight:850;color:#071B3A;">{top_priority_name}</span><br>
        requires management review
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="side-card">
        <b>High Priority Relationships</b><br>
        <span style="font-size:28px;font-weight:850;color:#071B3A;">{high_priority_count}</span><br>
        score >= 65
        </div>
        """,
        unsafe_allow_html=True,
    )

with pcol2:
    st.markdown("### Top Relationships Requiring Management Attention")
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
        height=360,
    )

st.markdown(
    """
    <div class="ai-box">
    <b>Management Priority Score v2.1 Formula</b><br><br>
    40% Exposure Importance + 25% Treasury Opportunity + 20% Relationship Weakness + 15% Risk Alert<br><br>
    <b>Score Colours:</b> Red ≥ 75 | Orange 65–74.9 | Blue 50–64.9 | Green &lt; 50
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================
# EXECUTIVE ACTION QUEUE
# =========================
st.markdown("## Executive Action Queue")
st.markdown(
    """
    <div class="narrative-box">
    The Executive Action Queue translates priority scores into management-ready actions.
    This moves EC-AI from portfolio diagnosis to decision support: what changed, why it matters,
    who should act, and when follow-up is required.
    </div>
    """,
    unsafe_allow_html=True,
)

action_queue = build_executive_action_queue(view)

q_left, q_right = st.columns([3.7, 1.3], gap="large")
with q_left:
    queue_display = action_queue[
        [
            "Priority Rank",
            "Relationship",
            "Priority Score",
            "Management_Priority_Band",
            "Why Management Should Care",
            "Executive Action Type",
            "Recommended Next Action",
            "Owner",
            "Timing",
        ]
    ].copy()
    queue_display = queue_display.rename(columns={"Management_Priority_Band": "Priority Band"})
    st.dataframe(
        style_priority_table(queue_display.style),
        use_container_width=True,
        hide_index=True,
        height=420,
    )

with q_right:
    immediate_count = int((action_queue["Management_Priority_Score"] >= 75).sum())
    this_week_count = int((action_queue["Management_Priority_Score"] >= 65).sum())
    top_action_type = action_queue.iloc[0]["Executive Action Type"]

    st.markdown(
        f"""
        <div class="side-card">
        <b>Immediate Actions</b><br>
        <span style="font-size:28px;font-weight:850;color:#991B1B;">{immediate_count}</span><br>
        score ≥ 75
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="side-card">
        <b>This Week Queue</b><br>
        <span style="font-size:28px;font-weight:850;color:#9A3412;">{this_week_count}</span><br>
        score ≥ 65
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="side-card">
        <b>Top Action Theme</b><br>
        <span style="font-size:18px;font-weight:850;color:#071B3A;">{top_action_type}</span><br>
        based on highest priority signal
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("### EC-AI Recommended Management Agenda")
agenda = build_executive_agenda(view)
agenda_html = "<br><br>".join(agenda)
st.markdown(
    f"""
    <div class="ai-box">
    <b>Executive Agenda for Management Review</b><br><br>
    {agenda_html}
    </div>
    """,
    unsafe_allow_html=True,
)

st.download_button(
    "Download Executive Action Queue CSV",
    data=queue_display.to_csv(index=False).encode("utf-8"),
    file_name="ecai_executive_action_queue_v2_1.csv",
    mime="text/csv",
    use_container_width=False,
)


# =========================
# ACTION ENGINE SUMMARY
# =========================
st.markdown("## AI Management Action Summary")
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



# =========================
# RELATIONSHIP 360 INTELLIGENCE
# =========================
st.markdown("## Relationship 360 Intelligence")
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

rcol1, rcol2 = st.columns([2.55, 1.45], gap="large")

with rcol1:
    profile_html = (
        '<div class="profile-card">'
        f'<div class="profile-title">{r360["Relationship"]}</div>'
        f'<div class="profile-subtitle">{r360["Country"]} · {r360["Sector"]} · {r360["Priority"]}</div>'
        f'<span class="strategy-pill">{strategic_view}</span>'
        f'<span class="strategy-pill">{wallet_view}</span>'
        f'<span class="strategy-pill">{risk_view}</span>'
        '<br><br>'
        '<b>Executive Relationship Summary</b><br><br>'
        f'{r360["Relationship"]} is positioned as a <b>{r360["Priority"]}</b> relationship with '
        f'<b>USD {r360["Exposure_USD_B"]:.1f}B</b> exposure and '
        f'<b>USD {r360["Deposits_USD_B"]:.1f}B</b> deposits. '
        f'The relationship has a <b>{int(r360["Strategic_Score"])}</b> strategic score, '
        f'<b>{int(r360["Treasury_Score"])}</b> treasury score, and '
        f'<b>{int(r360["Risk_Score"])}</b> risk score.'
        '<br><br>'
        f'<b>Sector View:</b> {sector_view}<br><br>'
        '<b>AI Recommended Action:</b><br>'
        f'<span style="color:#1565C0;font-weight:750;">{r360["AI_Management_Action"]}</span>'
        '</div>'
    )
    st.markdown(profile_html, unsafe_allow_html=True)

    st.markdown("### Banker Coverage Strategy")

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

    st.dataframe(strategy_table, use_container_width=True, hide_index=True, height=210)

with rcol2:
    st.markdown("### Relationship Metrics")

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

    st.dataframe(metrics_table, use_container_width=True, hide_index=True, height=270)

    st.markdown("### 360 Assessment")

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

    st.dataframe(assessment_table, use_container_width=True, hide_index=True, height=230)

r360_memo = build_relationship_360_memo(r360)

st.download_button(
    "Download Relationship 360 Memo",
    data=r360_memo.encode("utf-8"),
    file_name=f"ecai_relationship_360_{selected_360.replace(' ', '_').lower()}_v2_1.md",
    mime="text/markdown",
    use_container_width=False,
)


# =========================
# MANAGEMENT MEMO GENERATOR
# =========================
st.markdown("## Management Memo Generator")
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

memo_col1, memo_col2 = st.columns([3.8, 1.2], gap="large")

with memo_col1:
    with st.expander("Preview Management Memo", expanded=True):
        st.markdown(build_management_memo_html(view), unsafe_allow_html=True)

with memo_col2:
    st.markdown(
        """
        <div class="side-card">
        <b>Export Tools</b><br><br>
        Download the executive memo or export the underlying AI action table for further review.
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        memo_pdf = build_management_memo_pdf(view)
        st.download_button(
            "Download Management Memo PDF",
            data=memo_pdf,
            file_name="ecai_institutional_portfolio_management_memo_v2_1.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.warning(f"PDF export unavailable: {e}")
        st.download_button(
            "Download Management Memo Text",
            data=memo_text.encode("utf-8"),
            file_name="ecai_institutional_portfolio_management_memo_v2_1.txt",
            mime="text/plain",
            use_container_width=True,
        )
    st.download_button(
        "Download Action Table CSV",
        data=view[["Relationship", "Country", "Sector", "Exposure_USD_B", "Deposits_USD_B", "Treasury_Score", "Strategic_Score", "Risk_Score", "Management_Priority_Score", "Management_Priority_Band", "Management_Priority_Rationale", "AI_Action_Category", "AI_Management_Action"]].to_csv(index=False).encode("utf-8"),
        file_name="ecai_ai_management_action_table_v2_1.csv",
        mime="text/csv",
        use_container_width=True,
    )


st.markdown("---")
st.caption("EC-AI Institutional Relationship OS v2.1 | Executive Intelligence Layer + AI Management Action Engine + Relationship 360 Intelligence + Management Memo Generator")
