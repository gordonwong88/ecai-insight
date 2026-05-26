
# EC-AI Institutional Portfolio Dashboard v1.8
# Locked v1.8 layout + Management Memo Generator
# Run:
#   python -m streamlit run ecai_institutional_portfolio_dashboard_v1_8.py

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
    lines.append("Generated by EC-AI Institutional Relationship OS v1.8")
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

df["Quadrant"] = df.apply(quadrant, axis=1)
df["AI_Management_Action"] = df.apply(generate_management_action, axis=1)
df["AI_Action_Category"] = df.apply(action_category, axis=1)

# =========================
# SIDEBAR
# =========================
st.sidebar.markdown("## EC-AI")
st.sidebar.markdown("Institutional Relationship OS")
st.sidebar.markdown("v1.8")
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
# HEADER
# =========================
header_left, header_right = st.columns([4.6, 1.4], gap="large")
with header_left:
    st.markdown('<div class="main-title">Portfolio Cognition Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Executive view of institutional relationships | EC-AI Synthetic Institutional Portfolio Dataset v1.8</div>',
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

memo_col1, memo_col2 = st.columns([1.2, 3.8], gap="large")

with memo_col1:
    st.download_button(
        "Download Management Memo",
        data=memo_text.encode("utf-8"),
        file_name="ecai_institutional_portfolio_management_memo_v1_8.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "Download Action Table CSV",
        data=view[["Relationship", "Country", "Sector", "Exposure_USD_B", "Deposits_USD_B", "Treasury_Score", "Strategic_Score", "Risk_Score", "AI_Action_Category", "AI_Management_Action"]].to_csv(index=False).encode("utf-8"),
        file_name="ecai_ai_management_action_table_v1_8.csv",
        mime="text/csv",
        use_container_width=True,
    )

with memo_col2:
    with st.expander("Preview Management Memo", expanded=True):
        st.markdown(build_management_memo_html(view), unsafe_allow_html=True)


st.markdown("---")
st.caption("EC-AI Institutional Portfolio Prototype v1.8 | AI Management Action Engine + Management Memo Generator")
