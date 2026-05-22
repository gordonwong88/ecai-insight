
# EC-AI Institutional Portfolio Dashboard v1.1
# Correct file for: EC-AI Synthetic Institutional Portfolio Dataset v1
# Run:
#   python -m streamlit run ecai_institutional_portfolio_dashboard_v1_1.py

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="EC-AI | Institutional Portfolio Dashboard",
    page_icon="🏦",
    layout="wide",
)

# ----------------------------
# Styling
# ----------------------------
NAVY = "#071B3A"
BLUE = "#0F4C81"
SLATE = "#526173"
BORDER = "#D8DEE6"
BG = "#F6F8FB"

st.markdown(
    """
<style>
.block-container {padding-top: 1.4rem; max-width: 1500px;}
[data-testid="stSidebar"] {background: linear-gradient(180deg,#061A36 0%,#0B2C55 100%);}
[data-testid="stSidebar"] * {color: white;}
.ec-kicker {color:#526173;font-size:15px;margin-top:-8px;margin-bottom:16px;}
.kpi-card {
    background:white;border:1px solid #D8DEE6;border-radius:14px;
    padding:16px 18px;box-shadow:0 1px 3px rgba(15,23,42,.06);
    min-height:96px;
}
.kpi-label {color:#526173;font-size:13px;font-weight:600;}
.kpi-value {color:#071B3A;font-size:28px;font-weight:850;margin-top:8px;}
.kpi-sub {color:#526173;font-size:12px;margin-top:2px;}
.narrative {
    background:#F8FAFC;border-left:5px solid #071B3A;border-radius:12px;
    padding:18px 22px;color:#071B3A;font-size:16px;line-height:1.55;
    margin-top:14px;margin-bottom:18px;
}
.section-card {
    background:white;border:1px solid #D8DEE6;border-radius:14px;
    padding:18px 18px;box-shadow:0 1px 3px rgba(15,23,42,.05);
}
.small-note {color:#526173;font-size:13px;}
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------
# Data
# ----------------------------
ROWS = [
["ABC Infrastructure","Infrastructure","Singapore",8.5,1.2,58,7.2,115,54,93,64,88,"Treasury Deepening"],
["Sakura Financial","Financials","Japan",5.2,4.8,82,14.1,92,92,90,28,66,"Maintain Coverage"],
["Oceanlink Shipping","Shipping","Hong Kong",6.4,0.8,41,4.9,98,35,42,88,39,"Risk Monitoring"],
["Lion City REIT","Real Estate","Singapore",7.1,1.0,49,5.8,105,46,79,72,55,"Repricing Review"],
["Zenith Manufacturing","Manufacturing","Thailand",3.8,1.9,63,10.8,132,68,76,44,91,"FX Monetization"],
["Nippon Industrial","Industrials","Japan",2.9,3.5,85,11.2,126,88,58,35,61,"Treasury Anchor"],
["Mekong Aviation","Aviation","Vietnam",4.6,0.5,33,3.8,92,28,51,91,42,"Portfolio Review"],
["Pacific Energy","Energy","Australia",9.2,1.4,46,6.4,108,49,84,70,74,"Treasury Deepening"],
["Dragon Telecom","Telecom","China",5.9,2.4,69,9.8,121,73,81,47,89,"Wallet Expansion"],
["Atlas Logistics","Logistics","Hong Kong",2.4,2.9,81,10.5,119,87,61,32,58,"Treasury Anchor"],
["Meridian Sovereign Fund","Sovereign","UAE",4.8,5.2,88,13.5,84,94,95,18,62,"Maintain Coverage"],
["Harbor Manufacturing","Manufacturing","Korea",3.5,2.7,74,11.1,127,81,64,36,73,"Treasury Expansion"],
["Global Trade Holdings","Trading","Singapore",4.2,3.8,79,10.7,118,85,69,41,77,"Maintain Coverage"],
["Horizon Commodities","Commodities","Indonesia",5.5,0.9,39,5.2,103,34,48,83,57,"Portfolio Review"],
["Bluewave Offshore","Offshore Services","Malaysia",4.1,0.7,36,4.7,96,31,44,86,40,"Risk Monitoring"],
["ASEAN Retail Group","Retail","Thailand",2.8,1.8,67,12.2,137,71,73,38,90,"Wallet Expansion"],
["Nova Mobility","Mobility","China",3.9,1.5,59,9.4,125,62,78,46,92,"Growth Focus"],
["Quantum Semicon","Semiconductor","Taiwan",6.1,3.1,76,13.1,143,84,87,29,81,"Strategic Expansion"],
["Eastern Development Bank","Financials","Korea",5.0,4.4,83,12.8,89,91,86,24,67,"Maintain Coverage"],
["Crest Infrastructure","Infrastructure","Indonesia",7.4,1.1,52,7.0,112,51,88,63,82,"Treasury Deepening"],
["Summit Petrochem","Chemicals","Singapore",4.6,1.3,55,8.1,116,57,72,54,76,"Wallet Expansion"],
["Polaris Shipping","Shipping","Greece",5.7,0.6,29,4.2,90,25,38,92,34,"Portfolio Review"],
["Orion Infrastructure","Infrastructure","India",8.0,2.0,61,8.5,118,65,91,57,84,"Treasury Expansion"],
["Vertex Capital","Financials","Hong Kong",3.7,3.4,86,13.4,91,89,75,26,69,"Crown Jewel"],
["Delta Aviation Leasing","Aviation","Ireland",6.8,0.8,37,5.0,95,33,59,85,51,"Risk Monitoring"],
["Titan Energy Partners","Energy","Qatar",9.5,2.5,64,8.9,122,71,89,52,80,"Treasury Expansion"],
["Evergreen Ports","Ports","Singapore",4.4,2.2,71,10.9,129,78,77,33,74,"Operational Deepening"],
["Solaris Utilities","Utilities","Australia",5.3,1.7,60,8.7,114,63,80,49,79,"Treasury Expansion"],
["Infinity Data Centers","Technology","Japan",3.3,2.1,73,12.5,138,79,83,27,86,"Growth Focus"],
["Alpine Mining Group","Mining","Canada",7.0,0.9,42,5.5,101,38,55,81,48,"Portfolio Review"],
["Metro Transit Holdings","Transportation","Hong Kong",6.2,1.6,57,7.9,111,59,82,58,77,"Treasury Deepening"],
["Prime Healthcare Asia","Healthcare","Singapore",3.1,2.0,75,12.1,135,82,74,31,85,"Wallet Expansion"],
["Unity Consumer Group","Consumer","China",2.7,1.9,69,11.3,131,74,71,39,88,"Growth Focus"],
["Vertex Logistics Asia","Logistics","Vietnam",3.8,2.5,78,10.2,124,83,68,34,72,"Treasury Anchor"],
["Sterling Real Assets","Real Estate","UK",6.5,1.0,48,6.1,106,44,76,74,58,"Repricing Review"],
["Nexus Trade Finance","Trade Finance","Singapore",4.0,3.0,80,11.5,128,86,70,29,73,"Treasury Anchor"],
["Falcon Marine Group","Marine","Norway",5.6,0.7,35,4.8,93,30,46,89,41,"Portfolio Review"],
["Terra Renewable Energy","Renewables","Australia",7.8,1.9,62,8.8,118,66,90,45,83,"Strategic Expansion"],
["BluePeak Telecom","Telecom","Malaysia",4.9,2.3,70,10.1,125,77,78,37,87,"Wallet Expansion"],
["Quantum Infrastructure Fund","Infrastructure","UAE",8.9,3.2,77,12.9,101,88,94,22,79,"Crown Jewel"],
["Horizon Payment Systems","Fintech","Singapore",3.6,2.8,84,13.0,136,90,81,24,92,"Growth Focus"],
["Pacific Semiconductor","Semiconductor","Taiwan",6.3,3.0,75,12.7,142,83,88,30,84,"Strategic Expansion"],
["Evergreen Aviation Services","Aviation","Japan",5.2,1.1,50,6.3,100,47,65,69,63,"Risk Monitoring"],
["Atlas Consumer Brands","Consumer","Indonesia",2.9,1.7,66,10.9,130,72,67,41,85,"Wallet Expansion"],
["Crest Capital Partners","Financials","Hong Kong",4.3,3.6,82,13.6,90,91,79,23,70,"Crown Jewel"],
["Nova Infrastructure Holdings","Infrastructure","Vietnam",7.6,1.8,59,8.2,116,61,89,53,82,"Treasury Deepening"],
["Vertex Industrial Asia","Industrials","Korea",3.4,2.6,79,11.7,127,84,66,32,71,"Treasury Anchor"],
["Oceanic Bulk Carriers","Shipping","Greece",6.0,0.5,28,4.0,89,22,35,94,30,"Portfolio Review"],
["Summit Digital Networks","Telecom","India",5.1,2.4,71,10.6,124,78,80,39,88,"Wallet Expansion"],
["Titan Infrastructure Asia","Infrastructure","Philippines",8.2,1.5,56,7.8,113,58,92,61,81,"Treasury Deepening"],
]

COLS = [
    "Relationship","Sector","Country","Exposure_USD_B","Deposits_USD_B",
    "CASA_pct","RoE_pct","Spread_bps","Treasury_Score","Strategic_Score",
    "Risk_Score","Wallet_Score","Priority"
]

@st.cache_data
def load_data():
    return pd.DataFrame(ROWS, columns=COLS)

df = load_data()

def fmt_b(x): return f"USD {x:.1f}B"
def fmt_pct(x): return f"{x:.1f}%"

def quadrant(row):
    if row["Strategic_Score"] >= 70 and row["Treasury_Score"] >= 70:
        return "Crown Jewel"
    if row["Strategic_Score"] >= 70 and row["Treasury_Score"] < 70:
        return "Optimization Focus"
    if row["Strategic_Score"] < 70 and row["Treasury_Score"] >= 70:
        return "Treasury Anchor"
    return "Portfolio Review"

df["Quadrant"] = df.apply(quadrant, axis=1)
df["Treasury_Penetration_pct"] = df["Deposits_USD_B"] / df["Exposure_USD_B"] * 100

# ----------------------------
# Sidebar
# ----------------------------
st.sidebar.markdown("## EC-AI")
st.sidebar.markdown("Institutional Prototype")
st.sidebar.markdown("v1.1")
st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")
st.sidebar.radio("", ["Portfolio Overview", "Relationship Drilldown", "Treasury Analytics", "Risk & Concentration", "Management Actions"], index=0)
st.sidebar.markdown("---")

st.sidebar.markdown("### Filters")
selected_priority = st.sidebar.multiselect("Priority", sorted(df["Priority"].unique()), default=sorted(df["Priority"].unique()))
selected_country = st.sidebar.multiselect("Country", sorted(df["Country"].unique()), default=sorted(df["Country"].unique()))
selected_sector = st.sidebar.multiselect("Sector", sorted(df["Sector"].unique()), default=sorted(df["Sector"].unique()))

label_mode = st.sidebar.radio(
    "Bubble labels",
    ["Show only priority names", "Show all names", "Hide names"],
    index=0,
    help="Use 'Show only priority names' to prevent overcrowding."
)

view = df[
    df["Priority"].isin(selected_priority)
    & df["Country"].isin(selected_country)
    & df["Sector"].isin(selected_sector)
].copy()

# Labels: solve overcrowding
top_exposure_names = set(view.nlargest(10, "Exposure_USD_B")["Relationship"])
priority_names = set(view[(view["Strategic_Score"] >= 85) | (view["Risk_Score"] >= 85) | (view["Exposure_USD_B"] >= 7.5)]["Relationship"])
label_names = top_exposure_names.union(priority_names)

if label_mode == "Show all names":
    view["Label"] = view["Relationship"]
elif label_mode == "Hide names":
    view["Label"] = ""
else:
    view["Label"] = view["Relationship"].where(view["Relationship"].isin(label_names), "")

# ----------------------------
# Header
# ----------------------------
st.title("Portfolio Cognition Dashboard")
st.markdown("<div class='ec-kicker'>Executive view of institutional relationships | EC-AI Synthetic Institutional Portfolio Dataset v1</div>", unsafe_allow_html=True)

# KPI calculations
total_exposure = view["Exposure_USD_B"].sum()
total_deposits = view["Deposits_USD_B"].sum()
weighted_treasury = (view["Treasury_Score"] * view["Exposure_USD_B"]).sum() / total_exposure if total_exposure else 0
weighted_strategic = (view["Strategic_Score"] * view["Exposure_USD_B"]).sum() / total_exposure if total_exposure else 0
avg_penetration = total_deposits / total_exposure * 100 if total_exposure else 0
high_priority = int(((view["Strategic_Score"] >= 85) | (view["Risk_Score"] >= 85)).sum())

kpis = [
    ("Total Exposure", fmt_b(total_exposure), "Filtered portfolio"),
    ("Weighted Treasury Score", f"{weighted_treasury:.1f}", "Out of 100"),
    ("Weighted Strategic Score", f"{weighted_strategic:.1f}", "Out of 100"),
    ("Avg. Treasury Penetration", fmt_pct(avg_penetration), "Deposits / exposure"),
    ("High Priority Relationships", f"{high_priority}", "Strategic or risk-sensitive"),
]

cols = st.columns(5)
for col, (label, value, sub) in zip(cols, kpis):
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

# ----------------------------
# Narrative
# ----------------------------
st.markdown(
    """
<div class="narrative">
The portfolio shows a clear split between crown-jewel relationships, treasury-anchor names, and strategic relationships requiring deeper wallet penetration.
Management attention should focus on high strategic / low treasury relationships, while preserving deposit-rich relationships that support funding quality.
</div>
""",
    unsafe_allow_html=True,
)

# ----------------------------
# Quadrant + side panel
# ----------------------------
left, right = st.columns([4.7, 1.45], gap="large")

with left:
    st.markdown("### Portfolio Cognition Quadrant")
    st.markdown("<div class='small-note'>X-axis: Treasury Score | Y-axis: Strategic Score | Bubble size: Exposure in USD billions</div>", unsafe_allow_html=True)

    color_map = {
        "Crown Jewel": "#E53935",
        "Treasury Deepening": "#1565C0",
        "Treasury Expansion": "#1976D2",
        "Maintain Coverage": "#2E7D32",
        "Treasury Anchor": "#00897B",
        "Portfolio Review": "#F57C00",
        "Risk Monitoring": "#D32F2F",
        "Repricing Review": "#8E24AA",
        "Wallet Expansion": "#00ACC1",
        "Growth Focus": "#7CB342",
        "Strategic Expansion": "#5E35B1",
        "FX Monetization": "#FB8C00",
        "Operational Deepening": "#6D4C41",
    }

    fig = px.scatter(
        view,
        x="Treasury_Score",
        y="Strategic_Score",
        size="Exposure_USD_B",
        color="Priority",
        color_discrete_map=color_map,
        text="Label",
        hover_name="Relationship",
        hover_data={
            "Sector": True,
            "Country": True,
            "Quadrant": True,
            "Exposure_USD_B": ":.1f",
            "Deposits_USD_B": ":.1f",
            "Treasury_Penetration_pct": ":.1f",
            "RoE_pct": ":.1f",
            "Risk_Score": True,
            "Wallet_Score": True,
            "Label": False,
        },
        size_max=44,
    )

    # Quadrant shading
    fig.add_shape(type="rect", x0=0, y0=70, x1=70, y1=100, fillcolor="rgba(255,152,0,0.10)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=70, y0=70, x1=100, y1=100, fillcolor="rgba(76,175,80,0.10)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=0, y0=0, x1=70, y1=70, fillcolor="rgba(244,67,54,0.08)", line_width=0, layer="below")
    fig.add_shape(type="rect", x0=70, y0=0, x1=100, y1=70, fillcolor="rgba(33,150,243,0.08)", line_width=0, layer="below")
    fig.add_vline(x=70, line_width=1, line_dash="dash", line_color="#9CA3AF")
    fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="#9CA3AF")

    fig.add_annotation(x=33, y=96, text="<b>OPTIMIZATION FOCUS</b><br>High Strategic / Low Treasury", showarrow=False, align="left", font=dict(size=13, color="#8A3B00"))
    fig.add_annotation(x=88, y=96, text="<b>CROWN JEWEL</b><br>High Strategic / High Treasury", showarrow=False, align="right", font=dict(size=13, color="#0B6B2E"))
    fig.add_annotation(x=33, y=8, text="<b>PORTFOLIO REVIEW</b><br>Low Strategic / Low Treasury", showarrow=False, align="left", font=dict(size=13, color="#8B1E1E"))
    fig.add_annotation(x=88, y=8, text="<b>TREASURY ANCHOR</b><br>Low Strategic / High Treasury", showarrow=False, align="right", font=dict(size=13, color="#0B3D75"))

    fig.update_traces(
        textposition="top center",
        textfont=dict(size=10, color="#111827"),
        marker=dict(line=dict(width=1, color="white"), opacity=0.83),
    )

    fig.update_layout(
        height=650,
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20),
        legend_title_text="Priority",
        font=dict(family="Inter, Arial", size=12, color="#071B3A"),
        xaxis=dict(title="Treasury Score", range=[0, 100], dtick=10, gridcolor="rgba(17,24,39,0.08)"),
        yaxis=dict(title="Strategic Score", range=[0, 100], dtick=10, gridcolor="rgba(17,24,39,0.08)"),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

with right:
    st.markdown("### Top Exposure")
    top5 = view.nlargest(5, "Exposure_USD_B")[["Relationship", "Exposure_USD_B", "Priority"]].copy()
    for _, r in top5.iterrows():
        st.markdown(f"**{r['Relationship']}**  \n{fmt_b(r['Exposure_USD_B'])} · {r['Priority']}")
        st.markdown("---")

    st.markdown("### Interpretation Guide")
    st.info(
        "Top-right: protect and deepen.\n\n"
        "Top-left: strategic relationships needing treasury penetration.\n\n"
        "Bottom-right: funding anchors to maintain.\n\n"
        "Bottom-left: review economics and resource allocation."
    )

# ----------------------------
# Tables
# ----------------------------
st.markdown("### Management Attention Priorities")

attention = view.sort_values(
    ["Strategic_Score", "Risk_Score", "Exposure_USD_B"],
    ascending=[False, False, False],
).head(12).copy()

attention["Exposure"] = attention["Exposure_USD_B"].map(fmt_b)
attention["Deposits"] = attention["Deposits_USD_B"].map(fmt_b)
attention["Treasury Penetration"] = attention["Treasury_Penetration_pct"].map(fmt_pct)

st.dataframe(
    attention[
        [
            "Relationship","Quadrant","Priority","Country","Sector","Exposure","Deposits",
            "Treasury_Score","Strategic_Score","Risk_Score","Treasury Penetration"
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

# ----------------------------
# Drilldown
# ----------------------------
st.markdown("### Relationship Quick Drilldown")
selected = st.selectbox("Select relationship", view["Relationship"].tolist())
row = view[view["Relationship"] == selected].iloc[0]

d1, d2, d3, d4, d5 = st.columns(5)
d1.metric("Exposure", fmt_b(row["Exposure_USD_B"]))
d2.metric("Deposits", fmt_b(row["Deposits_USD_B"]))
d3.metric("Treasury Score", int(row["Treasury_Score"]))
d4.metric("Strategic Score", int(row["Strategic_Score"]))
d5.metric("RoE", fmt_pct(row["RoE_pct"]))

if row["Quadrant"] == "Optimization Focus":
    rel_text = "Strategically important relationship requiring treasury deepening and wallet penetration improvement."
elif row["Quadrant"] == "Crown Jewel":
    rel_text = "High-quality relationship combining strategic relevance, funding linkage, and strong management importance."
elif row["Quadrant"] == "Treasury Anchor":
    rel_text = "Relationship is valuable from a deposit and funding contribution perspective; cross-sell selectively."
else:
    rel_text = "Relationship may warrant portfolio review given weaker strategic relevance and lower treasury contribution."

st.markdown(f"<div class='narrative'>{rel_text}</div>", unsafe_allow_html=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Synthetic Portfolio Dataset CSV",
    csv,
    "ecai_synthetic_institutional_portfolio_dataset_v1.csv",
    "text/csv",
)
