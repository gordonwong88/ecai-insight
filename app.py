# EC-AI Institutional Portfolio Dashboard v1.2
# Executive Cognition Cleanup Version
# Run:
# python -m streamlit run ecai_institutional_portfolio_dashboard_v1_2.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="EC-AI Institutional Portfolio Dashboard",
    page_icon="🏦",
    layout="wide"
)

# =========================================================
# STYLE
# =========================================================

st.markdown("""
<style>

.block-container {
    padding-top: 1.2rem;
    max-width: 1500px;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#081B33 0%, #0C315A 100%);
}

[data-testid="stSidebar"] * {
    color: white;
}

.main-title {
    font-size: 46px;
    font-weight: 800;
    color: #071B3A;
    margin-bottom: 0px;
}

.sub-title {
    color: #526173;
    font-size: 15px;
    margin-top: -6px;
    margin-bottom: 20px;
}

.kpi-card {
    background: white;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.06);
}

.kpi-label {
    font-size: 13px;
    color: #526173;
    font-weight: 600;
}

.kpi-value {
    font-size: 28px;
    color: #071B3A;
    font-weight: 850;
    margin-top: 8px;
}

.kpi-sub {
    font-size: 12px;
    color: #7B8794;
    margin-top: 4px;
}

.narrative-box {
    background: #F8FAFC;
    border-left: 5px solid #071B3A;
    border-radius: 12px;
    padding: 18px 22px;
    margin-top: 16px;
    margin-bottom: 18px;
    color: #071B3A;
    line-height: 1.6;
    font-size: 16px;
}

.side-card {
    background: white;
    border: 1px solid #D8DEE6;
    border-radius: 14px;
    padding: 16px 18px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.05);
}

.side-title {
    color: #071B3A;
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 14px;
}

.small-note {
    color: #526173;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# SYNTHETIC DATASET
# =========================================================

rows = [
["ABC Infrastructure","Infrastructure","Singapore",8.5,1.2,54,93,64,"Treasury Growth"],
["Sakura Financial","Financials","Japan",5.2,4.8,92,90,28,"Crown Jewel"],
["Oceanlink Shipping","Shipping","Hong Kong",6.4,0.8,35,42,88,"Portfolio Review"],
["Pacific Energy","Energy","Australia",9.2,1.4,49,84,70,"Treasury Growth"],
["Dragon Telecom","Telecom","China",5.9,2.4,73,81,47,"Strategic Growth"],
["Meridian Sovereign Fund","Sovereign","UAE",4.8,5.2,94,95,18,"Crown Jewel"],
["Quantum Infrastructure Fund","Infrastructure","UAE",8.9,3.2,88,94,22,"Crown Jewel"],
["Orion Infrastructure","Infrastructure","India",8.0,2.0,65,91,57,"Treasury Growth"],
["Titan Infrastructure Asia","Infrastructure","Philippines",8.2,1.5,58,92,61,"Treasury Growth"],
["Terra Renewable Energy","Renewables","Australia",7.8,1.9,66,90,45,"Strategic Growth"],
["Quantum Semicon","Semiconductor","Taiwan",6.1,3.1,84,87,29,"Strategic Growth"],
["Pacific Semiconductor","Semiconductor","Taiwan",6.3,3.0,83,88,30,"Strategic Growth"],
["Nova Infrastructure Holdings","Infrastructure","Vietnam",7.6,1.8,61,89,53,"Treasury Growth"],
["Titan Energy Partners","Energy","Qatar",9.5,2.5,71,89,52,"Treasury Growth"],
["Eastern Development Bank","Financials","Korea",5.0,4.4,91,86,24,"Crown Jewel"],
["Vertex Capital","Financials","Hong Kong",3.7,3.4,89,75,26,"Crown Jewel"],
["Crest Capital Partners","Financials","Hong Kong",4.3,3.6,91,79,23,"Crown Jewel"],
["Bluewave Offshore","Offshore Services","Malaysia",4.1,0.7,31,44,86,"Portfolio Review"],
["Polaris Shipping","Shipping","Greece",5.7,0.6,25,38,92,"Portfolio Review"],
["Oceanic Bulk Carriers","Shipping","Greece",6.0,0.5,22,35,94,"Portfolio Review"],
]

cols = [
    "Relationship",
    "Sector",
    "Country",
    "Exposure_USD_B",
    "Deposits_USD_B",
    "Treasury_Score",
    "Strategic_Score",
    "Risk_Score",
    "Priority"
]

df = pd.DataFrame(rows, columns=cols)

# =========================================================
# HELPERS
# =========================================================

def fmt_b(x):
    return f"USD {x:.1f}B"

def fmt_pct(x):
    return f"{x:.1f}%"

def quadrant(row):

    if row["Strategic_Score"] >= 70 and row["Treasury_Score"] >= 70:
        return "Crown Jewel"

    elif row["Strategic_Score"] >= 70:
        return "Optimization Focus"

    elif row["Treasury_Score"] >= 70:
        return "Treasury Anchor"

    return "Portfolio Review"

df["Quadrant"] = df.apply(quadrant, axis=1)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown("## EC-AI")
st.sidebar.markdown("Institutional Relationship OS")
st.sidebar.markdown("v1.2")

st.sidebar.markdown("---")

selected_priority = st.sidebar.multiselect(
    "Priority",
    sorted(df["Priority"].unique()),
    default=sorted(df["Priority"].unique())
)

selected_country = st.sidebar.multiselect(
    "Country",
    sorted(df["Country"].unique()),
    default=sorted(df["Country"].unique())
)

view = df[
    df["Priority"].isin(selected_priority)
    & df["Country"].isin(selected_country)
].copy()

# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">Portfolio Cognition Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">Executive view of institutional relationships | EC-AI Synthetic Institutional Portfolio Dataset v1.2</div>',
    unsafe_allow_html=True
)

# =========================================================
# KPI STRIP
# =========================================================

total_exposure = view["Exposure_USD_B"].sum()
total_deposits = view["Deposits_USD_B"].sum()

weighted_treasury = (
    view["Treasury_Score"] * view["Exposure_USD_B"]
).sum() / total_exposure

weighted_strategic = (
    view["Strategic_Score"] * view["Exposure_USD_B"]
).sum() / total_exposure

coverage = total_deposits / total_exposure * 100

kpis = [
    ("Total Exposure", fmt_b(total_exposure), "Filtered portfolio"),
    ("Weighted Treasury Score", f"{weighted_treasury:.1f}", "Out of 100"),
    ("Weighted Strategic Score", f"{weighted_strategic:.1f}", "Out of 100"),
    ("Treasury Coverage", fmt_pct(coverage), "Deposits / exposure"),
    ("Priority Relationships", str(len(view)), "Filtered names"),
]

cols_kpi = st.columns(5)

for col, (label, value, sub) in zip(cols_kpi, kpis):

    with col:

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# EXECUTIVE NARRATIVE
# =========================================================

st.markdown("""
<div class="narrative-box">

The portfolio shows concentration in strategic infrastructure and financial relationships requiring treasury penetration enhancement.

Management attention should focus on strategic relationships with weak deposit linkage while protecting crown-jewel funding relationships.

</div>
""", unsafe_allow_html=True)

# =========================================================
# MAIN LAYOUT
# =========================================================

left, right = st.columns([4.8, 1.4], gap="large")

# =========================================================
# QUADRANT
# =========================================================

with left:

    st.markdown("## Portfolio Cognition Quadrant")

    st.markdown(
        '<div class="small-note">X-axis: Treasury Score | Y-axis: Strategic Score | Bubble size: Exposure in USD billions</div>',
        unsafe_allow_html=True
    )

    important_names = set(
        view.nlargest(6, "Exposure_USD_B")["Relationship"]
    )

    view["Label"] = view["Relationship"].where(
        view["Relationship"].isin(important_names),
        ""
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
        size_max=36,
        color_discrete_map=color_map,
        hover_data={
            "Country": True,
            "Sector": True,
            "Exposure_USD_B": ":.1f",
            "Deposits_USD_B": ":.1f",
            "Risk_Score": True,
            "Label": False
        }
    )

    # Quadrants

    fig.add_shape(
        type="rect",
        x0=0,
        y0=70,
        x1=70,
        y1=100,
        fillcolor="rgba(255,152,0,0.10)",
        line_width=0
    )

    fig.add_shape(
        type="rect",
        x0=70,
        y0=70,
        x1=100,
        y1=100,
        fillcolor="rgba(76,175,80,0.10)",
        line_width=0
    )

    fig.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=70,
        y1=70,
        fillcolor="rgba(244,67,54,0.06)",
        line_width=0
    )

    fig.add_shape(
        type="rect",
        x0=70,
        y0=0,
        x1=100,
        y1=70,
        fillcolor="rgba(33,150,243,0.06)",
        line_width=0
    )

    fig.add_vline(
        x=70,
        line_width=1,
        line_dash="dash",
        line_color="#9CA3AF"
    )

    fig.add_hline(
        y=70,
        line_width=1,
        line_dash="dash",
        line_color="#9CA3AF"
    )

    # Labels

    fig.add_annotation(
        x=22,
        y=96,
        text="<b>OPTIMIZATION FOCUS</b>",
        showarrow=False,
        font=dict(size=14)
    )

    fig.add_annotation(
        x=87,
        y=96,
        text="<b>CROWN JEWEL</b>",
        showarrow=False,
        font=dict(size=14)
    )

    fig.add_annotation(
        x=22,
        y=8,
        text="<b>PORTFOLIO REVIEW</b>",
        showarrow=False,
        font=dict(size=14)
    )

    fig.add_annotation(
        x=87,
        y=8,
        text="<b>TREASURY ANCHOR</b>",
        showarrow=False,
        font=dict(size=14)
    )

    fig.update_traces(
        textposition="top center",
        textfont=dict(size=10),
        marker=dict(
            opacity=0.82,
            line=dict(width=1, color="white")
        )
    )

    fig.update_layout(
        template="plotly_white",
        height=650,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        font=dict(family="Inter, Arial", size=12),
        xaxis=dict(
            title="Treasury Score",
            range=[0,100],
            dtick=10
        ),
        yaxis=dict(
            title="Strategic Score",
            range=[0,100],
            dtick=10
        )
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# RIGHT PANEL
# =========================================================

with right:

    st.markdown(
        '<div class="side-title">Portfolio Concentration</div>',
        unsafe_allow_html=True
    )

    top5_pct = (
        view.nlargest(5, "Exposure_USD_B")["Exposure_USD_B"].sum()
        / total_exposure * 100
    )

    st.markdown(f"""
    <div class="side-card">
    <b>Top 5 Relationships</b><br>
    {top5_pct:.1f}% of portfolio exposure
    </div>
    """, unsafe_allow_html=True)

    infra_pct = (
        view[view["Sector"]=="Infrastructure"]["Exposure_USD_B"].sum()
        / total_exposure * 100
    )

    st.markdown(f"""
    <div class="side-card">
    <b>Infrastructure Concentration</b><br>
    {infra_pct:.1f}% of total exposure
    </div>
    """, unsafe_allow_html=True)

    ship_pct = (
        view[
            view["Sector"].isin(["Shipping","Aviation"])
        ]["Exposure_USD_B"].sum()
        / total_exposure * 100
    )

    st.markdown(f"""
    <div class="side-card">
    <b>Shipping & Aviation Risk</b><br>
    {ship_pct:.1f}% of exposure
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="side-title">Top Management Actions</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div class="side-card">

    1. Deepen treasury linkage for infrastructure relationships<br><br>

    2. Monitor refinancing-sensitive shipping exposures<br><br>

    3. Protect crown-jewel deposit relationships<br><br>

    4. Expand wallet penetration across strategic names

    </div>
    """, unsafe_allow_html=True)

# =========================================================
# MANAGEMENT TABLE
# =========================================================

st.markdown("## Management Attention Priorities")

attention = view.sort_values(
    ["Strategic_Score","Risk_Score","Exposure_USD_B"],
    ascending=[False,False,False]
).copy()

attention["Exposure"] = attention["Exposure_USD_B"].map(fmt_b)
attention["Deposits"] = attention["Deposits_USD_B"].map(fmt_b)

st.dataframe(
    attention[
        [
            "Relationship",
            "Quadrant",
            "Priority",
            "Country",
            "Sector",
            "Exposure",
            "Deposits",
            "Treasury_Score",
            "Strategic_Score",
            "Risk_Score"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

# =========================================================
# RELATIONSHIP DRILLDOWN
# =========================================================

st.markdown("## Relationship Quick Drilldown")

selected = st.selectbox(
    "Select relationship",
    view["Relationship"].tolist()
)

row = view[
    view["Relationship"] == selected
].iloc[0]

d1, d2, d3, d4, d5 = st.columns(5)

d1.metric("Exposure", fmt_b(row["Exposure_USD_B"]))
d2.metric("Deposits", fmt_b(row["Deposits_USD_B"]))
d3.metric("Treasury Score", int(row["Treasury_Score"]))
d4.metric("Strategic Score", int(row["Strategic_Score"]))
d5.metric("Risk Score", int(row["Risk_Score"]))

if row["Quadrant"] == "Optimization Focus":

    msg = """
    Strategically important relationship requiring treasury deepening
    and stronger operational wallet linkage.
    """

elif row["Quadrant"] == "Crown Jewel":

    msg = """
    High-quality relationship combining strategic relevance with
    strong treasury contribution.
    """

elif row["Quadrant"] == "Treasury Anchor":

    msg = """
    Relationship remains valuable from a liquidity and funding perspective.
    """

else:

    msg = """
    Relationship may warrant portfolio review given weaker economics
    and strategic positioning.
    """

st.markdown(
    f'''
    <div class="narrative-box">
    {msg}
    </div>
    ''',
    unsafe_allow_html=True
)

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "EC-AI Institutional Portfolio Prototype v1.2 | Executive Cognition Cleanup"
)
