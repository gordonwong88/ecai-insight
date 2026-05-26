# EC-AI Institutional Portfolio Dashboard v1.4
# LOCKED LAYOUT VERSION
# Run:
#   python -m streamlit run ecai_institutional_portfolio_dashboard_v1_4.py

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="EC-AI Institutional Portfolio Dashboard", page_icon="🏦", layout="wide")

st.markdown('''
<style>
.block-container { padding-top: 1.35rem; padding-left: 2rem; padding-right: 2rem; max-width: 1680px; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#061A36 0%,#0B2C55 100%); }
[data-testid="stSidebar"] * { color: white; }
.main-title { font-size: 42px; font-weight: 850; color: #071B3A; margin-bottom: 0px; letter-spacing: -0.02em; }
.sub-title { color: #526173; font-size: 15px; margin-top: -4px; margin-bottom: 18px; }
.portfolio-card { background: white; border: 1px solid #D8DEE6; border-radius: 14px; padding: 12px 18px; box-shadow: 0 1px 3px rgba(15,23,42,.05); }
.portfolio-label { font-size: 12px; color: #526173; font-weight: 700; text-transform: uppercase; }
.portfolio-name { font-size: 24px; color: #071B3A; font-weight: 850; margin-top: 2px; }
.portfolio-date { font-size: 12px; color: #526173; margin-top: 2px; }
.kpi-card { background: white; border: 1px solid #D8DEE6; border-radius: 14px; padding: 16px 18px; min-height: 106px; box-shadow: 0 1px 3px rgba(15,23,42,.06); }
.kpi-label { color: #526173; font-size: 13px; font-weight: 700; }
.kpi-value { color: #071B3A; font-size: 27px; font-weight: 850; margin-top: 8px; }
.kpi-sub { color: #526173; font-size: 12px; margin-top: 4px; }
.narrative-box { background: #F8FAFC; border-left: 5px solid #071B3A; border-radius: 12px; padding: 16px 22px; color: #071B3A; line-height: 1.6; font-size: 15px; margin-top: 16px; margin-bottom: 16px; }
.side-card { background: white; border: 1px solid #D8DEE6; border-radius: 14px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(15,23,42,.05); }
.side-title { color: #071B3A; font-size: 19px; font-weight: 800; margin-bottom: 10px; }
.small-note { color: #526173; font-size: 13px; }
</style>
''', unsafe_allow_html=True)

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
cols = ["Relationship","Sector","Country","Exposure_USD_B","Deposits_USD_B","Treasury_Score","Strategic_Score","Risk_Score","Priority"]
df = pd.DataFrame(rows, columns=cols)

def fmt_b(x): return f"USD {x:.1f}B"
def fmt_pct(x): return f"{x:.1f}%"

def quadrant(row):
    if row["Strategic_Score"] >= 70 and row["Treasury_Score"] >= 70: return "Crown Jewel"
    if row["Strategic_Score"] >= 70: return "Optimization Focus"
    if row["Treasury_Score"] >= 70: return "Treasury Anchor"
    return "Portfolio Review"

df["Quadrant"] = df.apply(quadrant, axis=1)

st.sidebar.markdown("## EC-AI")
st.sidebar.markdown("Institutional Relationship OS")
st.sidebar.markdown("v1.4")
st.sidebar.markdown("---")
selected_priority = st.sidebar.multiselect("Priority", sorted(df["Priority"].unique()), default=sorted(df["Priority"].unique()))
selected_country = st.sidebar.multiselect("Country", sorted(df["Country"].unique()), default=sorted(df["Country"].unique()))
st.sidebar.markdown("---")
st.sidebar.info("Hover over bubbles for detailed relationship information. Chart labels use number keys to preserve readability.")

view = df[df["Priority"].isin(selected_priority) & df["Country"].isin(selected_country)].copy()
if view.empty:
    st.warning("No relationships match the selected filters.")
    st.stop()

header_left, header_right = st.columns([4.7, 1.3], gap="large")
with header_left:
    st.markdown('<div class="main-title">Portfolio Cognition Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Executive view of institutional relationships | EC-AI Synthetic Institutional Portfolio Dataset v1.4</div>', unsafe_allow_html=True)
with header_right:
    st.markdown('''
    <div class="portfolio-card">
        <div class="portfolio-label">Portfolio</div>
        <div class="portfolio-name">EC-AI Institutional Portfolio</div>
        <div class="portfolio-date">As of May 15, 2025</div>
    </div>
    ''', unsafe_allow_html=True)

total_exposure = view["Exposure_USD_B"].sum()
total_deposits = view["Deposits_USD_B"].sum()
weighted_treasury = (view["Treasury_Score"] * view["Exposure_USD_B"]).sum() / total_exposure
weighted_strategic = (view["Strategic_Score"] * view["Exposure_USD_B"]).sum() / total_exposure
coverage = total_deposits / total_exposure * 100

kpis = [("Total Exposure", fmt_b(total_exposure), "Filtered portfolio"), ("Weighted Treasury Score", f"{weighted_treasury:.1f}", "Out of 100"), ("Weighted Strategic Score", f"{weighted_strategic:.1f}", "Out of 100"), ("Treasury Coverage", fmt_pct(coverage), "Deposits / exposure"), ("Priority Relationships", str(len(view)), "Filtered names")]
for col, (label, value, sub) in zip(st.columns(5), kpis):
    with col:
        st.markdown(f'''<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>''', unsafe_allow_html=True)

st.markdown('''<div class="narrative-box">The portfolio shows concentration in strategic infrastructure and financial relationships requiring treasury penetration enhancement. Management attention should focus on strategic relationships with weak deposit linkage while protecting crown-jewel funding relationships.</div>''', unsafe_allow_html=True)

main_left, main_mid, main_right = st.columns([3.3, 1.45, 1.05], gap="large")

key_df = view.sort_values(["Exposure_USD_B", "Strategic_Score", "Risk_Score"], ascending=[False, False, False]).reset_index(drop=True)
key_df["Chart_No"] = range(1, len(key_df) + 1)
key_map = dict(zip(key_df["Relationship"], key_df["Chart_No"]))
view["Chart_No"] = view["Relationship"].map(key_map)
view["Label"] = view["Chart_No"].astype(str)

with main_left:
    st.markdown("## Portfolio Cognition Quadrant")
    st.markdown('<div class="small-note">X-axis: Treasury Score | Y-axis: Strategic Score | Bubble size: Exposure in USD billions<br>Names are moved to the reference table to avoid chart congestion.</div>', unsafe_allow_html=True)
    color_map = {"Treasury Growth":"#1565C0", "Strategic Growth":"#5E35B1", "Crown Jewel":"#D32F2F", "Portfolio Review":"#F57C00"}
    fig = px.scatter(view, x="Treasury_Score", y="Strategic_Score", size="Exposure_USD_B", color="Priority", text="Label", hover_name="Relationship", size_max=31, color_discrete_map=color_map, hover_data={"Country": True, "Sector": True, "Exposure_USD_B": ":.1f", "Deposits_USD_B": ":.1f", "Risk_Score": True, "Chart_No": False, "Label": False})
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
    fig.update_traces(textposition="middle center", textfont=dict(size=11, color="white", family="Arial Black"), marker=dict(opacity=0.78, line=dict(width=1, color="white")))
    fig.update_layout(template="plotly_white", height=570, margin=dict(l=10, r=10, t=20, b=20), showlegend=False, font=dict(family="Inter, Arial", size=11, color="#071B3A"), xaxis=dict(title="Treasury Score", range=[0,100], dtick=10, gridcolor="rgba(17,24,39,.08)"), yaxis=dict(title="Strategic Score", range=[0,100], dtick=10, gridcolor="rgba(17,24,39,.08)"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

with main_mid:
    st.markdown("### Relationship Reference")
    st.caption("By chart number")
    ref = key_df[["Chart_No", "Relationship", "Exposure_USD_B"]].copy()
    ref = ref.rename(columns={"Chart_No":"#", "Exposure_USD_B":"Exposure (USD B)"})
    ref["Exposure (USD B)"] = ref["Exposure (USD B)"].map(lambda x: f"{x:.1f}")
    st.dataframe(ref, use_container_width=True, hide_index=True, height=570)

with main_right:
    st.markdown('<div class="side-title">Portfolio Concentration</div>', unsafe_allow_html=True)
    top5_pct = view.nlargest(5, "Exposure_USD_B")["Exposure_USD_B"].sum() / total_exposure * 100
    infra_pct = view[view["Sector"] == "Infrastructure"]["Exposure_USD_B"].sum() / total_exposure * 100
    shipping_pct = view[view["Sector"].isin(["Shipping", "Aviation"])] ["Exposure_USD_B"].sum() / total_exposure * 100
    st.markdown(f'<div class="side-card"><b>Top 5 Relationships</b><br><span style="font-size:24px;font-weight:850;color:#071B3A;">{top5_pct:.1f}%</span><br>of portfolio exposure</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="side-card"><b>Infrastructure Concentration</b><br><span style="font-size:24px;font-weight:850;color:#071B3A;">{infra_pct:.1f}%</span><br>of total exposure</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="side-card"><b>Shipping & Aviation Risk</b><br><span style="font-size:24px;font-weight:850;color:#071B3A;">{shipping_pct:.1f}%</span><br>of exposure</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-title">Top Management Actions</div>', unsafe_allow_html=True)
    st.markdown('''<div class="side-card">1. Deepen treasury linkage for infrastructure relationships<br><br>2. Monitor refinancing-sensitive shipping exposures<br><br>3. Protect crown-jewel deposit relationships<br><br>4. Expand wallet penetration across strategic names</div>''', unsafe_allow_html=True)

lower_left, lower_right = st.columns([3.35, 1.65], gap="large")
with lower_left:
    st.markdown("## Management Attention Priorities")
    attention = view.sort_values(["Strategic_Score", "Risk_Score", "Exposure_USD_B"], ascending=[False, False, False]).copy()
    attention["Exposure (USD B)"] = attention["Exposure_USD_B"].map(lambda x: f"{x:.1f}")
    attention["Deposits (USD B)"] = attention["Deposits_USD_B"].map(lambda x: f"{x:.1f}")
    st.dataframe(attention[["Relationship", "Quadrant", "Priority", "Country", "Sector", "Exposure (USD B)", "Deposits (USD B)", "Treasury_Score", "Strategic_Score", "Risk_Score"]], use_container_width=True, hide_index=True, height=330)

with lower_right:
    st.markdown("## Relationship Quick Drilldown")
    selected = st.selectbox("Select relationship", view["Relationship"].tolist())
    row = view[view["Relationship"] == selected].iloc[0]
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Exposure", fmt_b(row["Exposure_USD_B"]))
    d2.metric("Deposits", fmt_b(row["Deposits_USD_B"]))
    d3.metric("Treasury", int(row["Treasury_Score"]))
    d4.metric("Strategic", int(row["Strategic_Score"]))
    d5.metric("Risk", int(row["Risk_Score"]))
    if row["Quadrant"] == "Optimization Focus":
        msg = "Strategically important relationship requiring treasury deepening and stronger operational wallet linkage."
    elif row["Quadrant"] == "Crown Jewel":
        msg = "High-quality relationship combining strategic relevance with strong treasury contribution."
    elif row["Quadrant"] == "Treasury Anchor":
        msg = "Relationship remains valuable from a liquidity and funding perspective."
    else:
        msg = "Relationship may warrant portfolio review given weaker economics and strategic positioning."
    st.markdown(f'<div class="narrative-box">{msg}</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption("EC-AI Institutional Portfolio Prototype v1.4 | Locked layout version")
