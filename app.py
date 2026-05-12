
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="EC-AI Banking Engine v0.7", layout="wide", initial_sidebar_state="expanded")

# =========================================================
# CONFIGURABLE DEMO THRESHOLDS
# =========================================================
DEFAULT_PRICING_FLOOR_BPS = 30
DEFAULT_RELATIONSHIP_ROE_FLOOR = 0.12

# =========================================================
# EC-AI BANKING VISUAL LANGUAGE
# =========================================================
NAVY = "#0B1F33"
NAVY_2 = "#12395B"
EXEC_BLUE = "#1F4E79"
STEEL = "#5B6770"
BLUE_GREY = "#6F8293"
LIGHT_STEEL = "#D9E1E8"
LIGHT_BG = "#F4F6F8"
CARD_BORDER = "#D7DEE6"
TEXT = "#111827"
MUTED = "#667085"
RED = "#A63D40"
LIGHT_RED = "#F2C7C9"
LIGHT_GREEN = "#CFE8D8"
GREEN = "#3E7B5A"
WARNING = "#C97A2B"

st.markdown(f"""
<style>
.stApp {{
    background-color: {LIGHT_BG};
    color: {TEXT};
    font-family: Inter, Arial, sans-serif;
}}

.ec-hero {{
    background: linear-gradient(135deg, {NAVY} 0%, {NAVY_2} 62%, {EXEC_BLUE} 100%);
    border-radius: 20px;
    padding: 28px 34px;
    color: white;
    margin-bottom: 18px;
    box-shadow: 0 12px 26px rgba(11, 31, 51, 0.18);
}}

.ec-hero h1 {{
    font-size: 36px;
    line-height: 1.15;
    margin: 0 0 8px 0;
    font-weight: 800;
    letter-spacing: -0.02em;
}}

.ec-hero p {{
    font-size: 16px;
    line-height: 1.45;
    opacity: 0.92;
    margin: 0;
}}

.ec-section-title {{
    font-size: 22px;
    font-weight: 800;
    color: {NAVY};
    margin: 8px 0 10px 0;
}}

.ec-subtitle {{
    color: {MUTED};
    font-size: 14px;
    margin-top: -4px;
    margin-bottom: 16px;
}}

div[data-testid="stMetric"] {{
    background-color: white;
    border: 1px solid {CARD_BORDER};
    padding: 14px 14px;
    border-radius: 16px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}}

div[data-testid="stMetricLabel"] {{
    font-size: 13px;
    color: {MUTED};
}}

div[data-testid="stMetricValue"] {{
    font-size: 24px;
    font-weight: 800;
    color: {NAVY};
}}

button[data-baseweb="tab"] {{
    font-size: 16px !important;
    font-weight: 750 !important;
    padding: 12px 18px !important;
    margin-right: 4px !important;
    border-radius: 12px 12px 0 0 !important;
}}

button[data-baseweb="tab"][aria-selected="true"] {{
    color: {NAVY} !important;
    background-color: #FFFFFF !important;
    border-bottom: 3px solid {EXEC_BLUE} !important;
}}

button[data-baseweb="tab"][aria-selected="false"] {{
    color: {BLUE_GREY} !important;
}}

.ec-card {{
    background: white;
    border: 1px solid {CARD_BORDER};
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}}

.ec-alert-title {{
    font-weight: 800;
    color: {NAVY};
    font-size: 16px;
    margin-bottom: 6px;
}}

.ec-alert-text {{
    color: {TEXT};
    font-size: 14px;
    line-height: 1.45;
}}
</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================
def money(x):
    try:
        x = float(x)
    except Exception:
        return "-"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000_000:
        return f"{sign}${x/1_000_000_000:,.1f}B"
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:,.1f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:,.1f}K"
    return f"{sign}${x:,.0f}"


def pct(x):
    try:
        return f"{float(x)*100:.1f}%"
    except Exception:
        return "-"


def safe_div(a, b):
    try:
        if b == 0 or pd.isna(b):
            return np.nan
        return a / b
    except Exception:
        return np.nan


def roe_color(v):
    if pd.isna(v):
        return "#E5E7EB"
    if v < 0.10:
        return RED
    if v < 0.15:
        return LIGHT_RED
    if v < 0.20:
        return LIGHT_GREEN
    return GREEN


def roe_status_label(v):
    if pd.isna(v):
        return "N/A"
    if v < 0.10:
        return "Critical"
    if v < 0.15:
        return "Below Profit Floor"
    if v < 0.20:
        return "Acceptable"
    return "Strong"


def rank_colors(n):
    base = [NAVY, EXEC_BLUE, STEEL, BLUE_GREY, "#8A98A6", "#AAB4BE", LIGHT_STEEL, "#E6EBF0"]
    return [base[min(i, len(base)-1)] for i in range(n)]


# =========================================================
# DEMO DATA WITH DEPOSITS + WALLET SHARE PROTOTYPE
# =========================================================
@st.cache_data
def make_demo_data(n=200, seed=7):
    rng = np.random.default_rng(seed)

    countries = ["Hong Kong", "Singapore", "Japan", "Korea", "Taiwan", "Australia"]
    products = [
        "Term Loan", "Revolver", "Trade Finance", "FX / Markets",
        "Cash Management", "Deposits", "DCM", "Fund Finance", "Guarantee"
    ]
    rms = ["RM - David", "RM - Michael", "RM - Sarah", "RM - Jason", "RM - Emily", "RM - Chris"]
    sectors = [
        "Property", "Infrastructure", "Healthcare", "Technology",
        "Shipping", "Energy", "Consumer", "Industrial", "Financial Institutions"
    ]
    clients = [
        "Pacific Property Group", "Eastern Logistics Holdings", "Global Manufacturing Ltd",
        "Summit Telecom Group", "Harbour Retail Corp", "North Asia Energy",
        "Strategic Infrastructure Co", "Asia Healthcare Group", "Sample Financial Holdings",
        "Sample Infrastructure Co", "Sample Shipping Ltd", "Sample Trading Co",
        "Sample Industrials Ltd", "Sample Telecom Group"
    ]
    tiers = ["Strategic", "Core", "Emerging", "Flow"]
    deposit_types = ["CASA", "Operational", "Time Deposit"]

    rows = []
    for i in range(n):
        country = rng.choice(countries, p=[0.20, 0.17, 0.17, 0.16, 0.15, 0.15])
        product = rng.choice(products, p=[0.23, 0.17, 0.12, 0.11, 0.10, 0.10, 0.06, 0.06, 0.05])
        client = rng.choice(clients)
        sector = rng.choice(sectors)
        rm = rng.choice(rms)
        tier = rng.choice(tiers, p=[0.25, 0.35, 0.25, 0.15])

        facility_limit = int(rng.integers(80, 1800)) * 1_000_000
        utilization = rng.uniform(0.15, 0.92)
        lending_drawn = facility_limit * utilization

        if product == "Revolver":
            nim_bps = rng.choice([18, 24, 28, 36, 48, 65], p=[0.18, 0.22, 0.18, 0.20, 0.14, 0.08])
        elif product == "Term Loan":
            nim_bps = rng.choice([25, 35, 55, 80, 110, 140], p=[0.10, 0.18, 0.26, 0.22, 0.16, 0.08])
        elif product == "Trade Finance":
            nim_bps = rng.choice([35, 60, 90, 120, 160], p=[0.15, 0.25, 0.25, 0.22, 0.13])
        elif product in ["FX / Markets", "DCM", "Fund Finance"]:
            nim_bps = rng.choice([45, 75, 110, 150, 210], p=[0.12, 0.24, 0.28, 0.23, 0.13])
        elif product in ["Cash Management", "Deposits"]:
            nim_bps = rng.choice([20, 40, 70, 100], p=[0.20, 0.30, 0.30, 0.20])
        else:
            nim_bps = rng.choice([30, 55, 85, 120, 180], p=[0.15, 0.25, 0.25, 0.22, 0.13])

        rwa_density = rng.choice([0.35, 0.50, 0.65, 0.85, 1.00, 1.20], p=[0.15, 0.18, 0.22, 0.22, 0.15, 0.08])
        rwa = lending_drawn * rwa_density

        nii = lending_drawn * float(nim_bps) / 10000
        fee = int(rng.integers(0, 14)) * 400_000
        revenue = nii + fee

        ltm_group_roe_target = rng.choice([0.06, 0.11, 0.14, 0.17, 0.22, 0.28], p=[0.15, 0.18, 0.17, 0.22, 0.18, 0.10])
        niat = rwa * ltm_group_roe_target * rng.uniform(0.85, 1.15)

        deposit_balance = int(rng.integers(50, 1800)) * 1_000_000
        if product in ["Deposits", "Cash Management"]:
            deposit_balance = int(rng.integers(300, 2800)) * 1_000_000

        deposit_type = rng.choice(deposit_types, p=[0.45, 0.35, 0.20])
        operational_flag = rng.choice(["Yes", "No"], p=[0.70, 0.30])
        deposit_growth = rng.uniform(-0.08, 0.25)

        ltm_group_roe = safe_div(niat, rwa)
        three_year_avg_groe = max(0.01, ltm_group_roe * rng.uniform(0.80, 1.20))

        wallet_estimate = max(revenue * rng.uniform(2.0, 5.0), revenue + 1)
        wallet_share = safe_div(revenue, wallet_estimate)
        wallet_gap = max(wallet_estimate - revenue, 0)

        rows.append({
            "Month": "2026-04",
            "Client": client,
            "Client_Tier": tier,
            "Country": country,
            "RM": rm,
            "Relationship_Owner": rm,
            "Sector": sector,
            "Product": product,
            "Facility_ID": f"FAC-{1000+i}",
            "Deal_ID": f"DEAL-{2000+i}",
            "Limit": round(facility_limit, 0),
            "Facility_Limit": round(facility_limit, 0),
            "Lending_Drawn": round(lending_drawn, 0),
            "RWA": round(rwa, 0),
            "NIM_bps": round(float(nim_bps), 1),
            "Net_Interest_Income": round(nii, 0),
            "Fee_Income": round(fee, 0),
            "Total_Revenue": round(revenue, 0),
            "Revenue": round(revenue, 0),
            "NIAT": round(niat, 0),
            "LTM_Group_RoE": round(ltm_group_roe, 4),
            "ThreeY_Avg_GRoE": round(three_year_avg_groe, 4),
            "Deposit_Balance": round(deposit_balance, 0),
            "Deposit_Type": deposit_type,
            "Operational_Deposit_Flag": operational_flag,
            "Deposit_Growth": round(deposit_growth, 4),
            "Wallet_Estimate": round(wallet_estimate, 0),
            "Wallet_Share": round(wallet_share, 4),
            "Wallet_Gap": round(wallet_gap, 0)
        })

    return pd.DataFrame(rows)


# =========================================================
# DATA PREP
# =========================================================
def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
    return df


def ensure_metrics(df):
    df = normalize_columns(df)
    required = ["Client", "Country", "RM", "Product", "Lending_Drawn", "RWA", "Total_Revenue", "NIAT"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}")
        st.stop()

    for c in [
        "Limit", "Facility_Limit", "Lending_Drawn", "RWA", "Total_Revenue", "Revenue",
        "NIAT", "Deposit_Balance", "NIM_bps", "Net_Interest_Income",
        "Wallet_Estimate", "Wallet_Share", "Wallet_Gap", "Deposit_Growth"
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "Facility_Limit" not in df.columns:
        df["Facility_Limit"] = df["Limit"] if "Limit" in df.columns else df["Lending_Drawn"]

    if "Revenue" not in df.columns:
        df["Revenue"] = df["Total_Revenue"]

    if "NIM_bps" not in df.columns:
        df["NIM_bps"] = df.apply(lambda r: safe_div(r.get("Net_Interest_Income", 0), r["Lending_Drawn"]) * 10000, axis=1)

    if "Deposit_Balance" not in df.columns:
        df["Deposit_Balance"] = 0

    if "Sector" not in df.columns:
        df["Sector"] = "General"

    if "Client_Tier" not in df.columns:
        df["Client_Tier"] = "Core"

    if "Relationship_Owner" not in df.columns:
        df["Relationship_Owner"] = df["RM"]

    if "Deposit_Type" not in df.columns:
        df["Deposit_Type"] = "CASA"

    if "Operational_Deposit_Flag" not in df.columns:
        df["Operational_Deposit_Flag"] = "Yes"

    if "Deal_ID" not in df.columns:
        df["Deal_ID"] = [f"DEAL-{i+1}" for i in range(len(df))]

    if "LTM_Group_RoE" not in df.columns:
        df["LTM_Group_RoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)

    if "ThreeY_Avg_GRoE" not in df.columns:
        df["ThreeY_Avg_GRoE"] = df["LTM_Group_RoE"]

    if "Wallet_Estimate" not in df.columns:
        df["Wallet_Estimate"] = df["Total_Revenue"] * 3.0

    if "Wallet_Share" not in df.columns:
        df["Wallet_Share"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["Wallet_Estimate"]), axis=1)

    if "Wallet_Gap" not in df.columns:
        df["Wallet_Gap"] = (df["Wallet_Estimate"] - df["Total_Revenue"]).clip(lower=0)

    if "Deposit_Growth" not in df.columns:
        df["Deposit_Growth"] = 0.0

    df["Revenue_per_RWA"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    return df


def grouped_view(df, group_cols):
    g = df.groupby(group_cols, dropna=False).agg({
        "Total_Revenue": "sum",
        "Facility_Limit": "sum",
        "Lending_Drawn": "sum",
        "Deposit_Balance": "sum",
        "RWA": "sum",
        "NIAT": "sum",
        "Wallet_Estimate": "sum",
        "Wallet_Gap": "sum"
    }).reset_index()

    nim = []
    for _, x in df.groupby(group_cols, dropna=False):
        nim.append(safe_div((x["NIM_bps"] * x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum()))

    g["NIM_bps"] = nim
    g["LTM_Group_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Wallet_Share"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["Wallet_Estimate"]), axis=1)
    return g.sort_values("Total_Revenue", ascending=False)


# =========================================================
# CHARTS
# =========================================================
def bar_chart(df, x, y, title):
    chart_df = df.copy().sort_values(y, ascending=False)
    chart_df["Label"] = chart_df[y].apply(money)
    fig = px.bar(chart_df, x=x, y=y, text="Label", title=title)
    fig.update_traces(
        marker_color=rank_colors(len(chart_df)),
        marker_line_width=0,
        textposition="outside",
        textfont=dict(size=12, color=NAVY),
        cliponaxis=False,
    )
    max_y = chart_df[y].max() if len(chart_df) else 0
    step = 1_000_000_000
    tick_max = max(step, np.ceil(max_y / step) * step)
    ticks = list(np.arange(0, tick_max + step, step))
    labels = ["0"] + [f"{v/1_000_000_000:.1f}B" for v in ticks[1:]]
    fig.update_layout(
        height=410,
        margin=dict(l=35, r=25, t=60, b=70),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color=TEXT, family="Inter, Arial, sans-serif"),
        title=dict(font=dict(size=18, color=NAVY, family="Inter, Arial, sans-serif")),
        yaxis=dict(tickvals=ticks, ticktext=labels, gridcolor="#E9EEF3", zeroline=False),
        xaxis=dict(tickangle=0, tickfont=dict(size=11, color=TEXT)),
        bargap=0.34,
        showlegend=False,
    )
    return fig


def combo_exposure_roe(df):
    ranked = grouped_view(df, ["Client"]).sort_values("Lending_Drawn", ascending=False).head(15)
    ranked["LTM Group RoE %"] = ranked["LTM_Group_RoE"] * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ranked["Client"],
        y=ranked["Lending_Drawn"],
        name="Lending Drawn",
        marker_color=NAVY,
        yaxis="y1",
        text=[money(v) for v in ranked["Lending_Drawn"]],
        textposition="outside",
        cliponaxis=False
    ))
    fig.add_trace(go.Scatter(
        x=ranked["Client"],
        y=ranked["LTM Group RoE %"],
        name="LTM Group RoE %",
        mode="lines+markers",
        marker=dict(color=EXEC_BLUE, size=9),
        line=dict(color=EXEC_BLUE, width=3),
        yaxis="y2"
    ))

    max_y = ranked["Lending_Drawn"].max() if len(ranked) else 0
    step = 1_000_000_000
    tick_max = max(step, np.ceil(max_y / step) * step)
    ticks = list(np.arange(0, tick_max + step, step))
    labels = ["0"] + [f"{v/1_000_000_000:.1f}B" for v in ticks[1:]]

    fig.update_layout(
        title="Capital Efficiency: Exposure vs LTM Group RoE",
        height=500,
        margin=dict(l=35, r=35, t=60, b=110),
        xaxis=dict(tickangle=-30),
        yaxis=dict(title="Lending Drawn", tickvals=ticks, ticktext=labels, gridcolor="#E5E7EB"),
        yaxis2=dict(title="LTM Group RoE %", overlaying="y", side="right", ticksuffix="%"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=1.10),
        font=dict(family="Inter, Arial, sans-serif", color=TEXT)
    )
    return fig


def heatmap_table(df, group_col):
    g = grouped_view(df, [group_col]).copy()
    g["Revenue"] = g["Total_Revenue"].apply(money)
    g["Lending Drawn"] = g["Lending_Drawn"].apply(money)
    g["RWA Display"] = g["RWA"].apply(money)
    g["NIM"] = g["NIM_bps"].round(1).astype(str) + " bps"
    g["LTM Group RoE"] = g["LTM_Group_RoE"].apply(pct)
    g["Status"] = g["LTM_Group_RoE"].apply(roe_status_label)
    show = g[[group_col, "Revenue", "Lending Drawn", "RWA Display", "NIM", "LTM Group RoE", "Status"]].copy()

    def style_row(row):
        raw = g.loc[row.name, "LTM_Group_RoE"]
        color = roe_color(raw)
        text_color = "white" if color in [RED, GREEN] else "#111827"
        styles = [""] * len(row)
        styles[-2] = f"background-color:{color}; color:{text_color}; font-weight:800;"
        styles[-1] = f"background-color:{color}; color:{text_color}; font-weight:800;"
        return styles

    st.dataframe(show.style.apply(style_row, axis=1), use_container_width=True, hide_index=True)


def executive_watchlist(df, roe_floor, pricing_floor):
    watch = df[(df["LTM_Group_RoE"] < roe_floor) | (df["NIM_bps"] < pricing_floor)].copy()
    if watch.empty:
        return pd.DataFrame()

    watch["Severity"] = np.select(
        [
            (watch["LTM_Group_RoE"] < 0.10) & (watch["NIM_bps"] < pricing_floor),
            (watch["LTM_Group_RoE"] < 0.10),
            (watch["NIM_bps"] < pricing_floor),
            (watch["LTM_Group_RoE"] < roe_floor)
        ],
        ["🔴 Critical", "🔴 Low LTM Group RoE", "🟠 Pricing Review", "🟡 Below Profit Floor"],
        default="🟡 Monitor"
    )

    watch = watch.sort_values(["LTM_Group_RoE", "Lending_Drawn"], ascending=[True, False]).head(15)
    out = watch[["Severity", "Client", "Country", "Product", "Lending_Drawn", "RWA", "Total_Revenue", "NIM_bps", "LTM_Group_RoE"]].copy()
    out["Lending Drawn"] = out["Lending_Drawn"].apply(money)
    out["RWA"] = out["RWA"].apply(money)
    out["Revenue"] = out["Total_Revenue"].apply(money)
    out["NIM"] = out["NIM_bps"].round(1).astype(str) + " bps"
    out["LTM Group RoE"] = out["LTM_Group_RoE"].apply(pct)
    return out[["Severity", "Client", "Country", "Product", "Lending Drawn", "RWA", "Revenue", "NIM", "LTM Group RoE"]]


# =========================================================
# APP HEADER / SIDEBAR
# =========================================================
st.markdown(
    '<div class="ec-hero"><h1>EC-AI Banking Engine v0.7</h1><p>Relationship intelligence / deposits / wallet share / revenue decision engine for corporate banking.</p></div>',
    unsafe_allow_html=True
)

with st.sidebar:
    st.markdown("## EC-AI Banking Engine")
    st.caption("Relationship Intelligence Prototype")
    data_mode = st.radio("Data source", ["Use Built-in Demo Data", "Upload File"], index=0)

    uploaded = None
    if data_mode == "Upload File":
        uploaded = st.file_uploader("Upload banking performance file", type=["csv", "xlsx"])
        st.caption("Required: Client, Country, RM, Product, Lending_Drawn, RWA, Total_Revenue, NIAT")

    st.markdown("---")
    st.markdown("### Configurable Thresholds")
    st.caption("Demo thresholds only — configure for each institution / pilot.")
    roe_floor = st.slider("Relationship profitability floor", 0.05, 0.30, DEFAULT_RELATIONSHIP_ROE_FLOOR, 0.01, format="%.2f")
    pricing_floor = st.slider("Pricing / margin floor (bps)", 0, 150, DEFAULT_PRICING_FLOOR_BPS, 5)


if data_mode == "Use Built-in Demo Data":
    raw = make_demo_data()
else:
    if uploaded is None:
        st.info("Upload a banking performance file or switch to built-in demo data.")
        st.stop()
    raw = pd.read_excel(uploaded) if uploaded.name.lower().endswith(".xlsx") else pd.read_csv(uploaded)

df = ensure_metrics(raw)


# =========================================================
# EXECUTIVE SNAPSHOT
# =========================================================
st.markdown('<div class="ec-section-title">Executive Snapshot</div>', unsafe_allow_html=True)
st.markdown('<div class="ec-subtitle">Portfolio revenue, exposure, deposits, wallet share and relationship profitability.</div>', unsafe_allow_html=True)

total_revenue = df["Total_Revenue"].sum()
total_drawn = df["Lending_Drawn"].sum()
total_limit = df["Facility_Limit"].sum()
total_deposit = df["Deposit_Balance"].sum()
total_rwa = df["RWA"].sum()
total_niat = df["NIAT"].sum()
portfolio_roe = safe_div(total_niat, total_rwa)
wallet_share = safe_div(total_revenue, df["Wallet_Estimate"].sum())

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Revenue", money(total_revenue))
c2.metric("Facility Limit", money(total_limit))
c3.metric("Lending Drawn", money(total_drawn))
c4.metric("Deposit Balance", money(total_deposit))
c5.metric("LTM Group RoE", pct(portfolio_roe))
c6.metric("Wallet Share", pct(wallet_share))


# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "CEO Dashboard",
    "Revenue Engine",
    "Relationship 360",
    "Deposit Intelligence",
    "Pricing & NIM Risk",
    "Capital Efficiency",
    "Portfolio Data"
])


# =========================================================
# CEO DASHBOARD
# =========================================================
with tab1:
    st.markdown('<div class="ec-section-title">CEO Dashboard</div>', unsafe_allow_html=True)

    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        st.markdown('<div class="ec-card"><div class="ec-alert-title">Management Summary</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ec-alert-text">• Total revenue is {money(total_revenue)}, supported by lending drawn of {money(total_drawn)} and deposits of {money(total_deposit)}.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ec-alert-text">• Portfolio LTM Group RoE is {pct(portfolio_roe)} against a configurable relationship profitability floor.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ec-alert-text">• Estimated wallet share is {pct(wallet_share)}, indicating remaining relationship white-space opportunity.</div>', unsafe_allow_html=True)
        st.markdown('<br><div class="ec-alert-title">Recommended Actions</div>', unsafe_allow_html=True)
        st.markdown('<div class="ec-alert-text">• Prioritize high-limit relationships with weak wallet share and low deposit penetration.</div>', unsafe_allow_html=True)
        st.markdown('<div class="ec-alert-text">• Review pricing and profitability pressure in low-return relationships.</div>', unsafe_allow_html=True)
        st.markdown('<div class="ec-alert-text">• Use Relationship 360 to identify product gaps and cross-sell opportunities.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="ec-card"><div class="ec-alert-title">LTM Group RoE Heatmap by Country</div>', unsafe_allow_html=True)
        heatmap_table(df, "Country")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Executive Watchlist")
    watch = executive_watchlist(df, roe_floor, pricing_floor)
    if watch.empty:
        st.success("No pricing / profitability watchlist relationships detected.")
    else:
        st.dataframe(watch, use_container_width=True, hide_index=True)

    st.markdown("### Revenue by Country")
    st.plotly_chart(
        bar_chart(grouped_view(df, ["Country"]).head(8), "Country", "Total_Revenue", "CEO Dashboard — Revenue by Country"),
        use_container_width=True,
        key="ceo_revenue_country"
    )


# =========================================================
# REVENUE ENGINE
# =========================================================
with tab2:
    st.markdown('<div class="ec-section-title">Revenue Engine</div>', unsafe_allow_html=True)

    a, b = st.columns(2, gap="large")
    with a:
        st.plotly_chart(
            bar_chart(grouped_view(df, ["Country"]).head(8), "Country", "Total_Revenue", "Revenue by Country"),
            use_container_width=True,
            key="revenue_country"
        )
    with b:
        st.plotly_chart(
            bar_chart(grouped_view(df, ["Product"]).head(8), "Product", "Total_Revenue", "Revenue by Product Type"),
            use_container_width=True,
            key="revenue_product"
        )

    c, d = st.columns(2, gap="large")
    with c:
        st.plotly_chart(
            bar_chart(grouped_view(df, ["Product"]).head(8), "Product", "Lending_Drawn", "Exposure by Product Type"),
            use_container_width=True,
            key="exposure_product"
        )
    with d:
        st.plotly_chart(
            bar_chart(grouped_view(df, ["Product"]).head(8), "Product", "Deposit_Balance", "Deposits by Product Type"),
            use_container_width=True,
            key="deposit_product"
        )

    st.markdown('<div class="ec-section-title">Top Revenue Relationships</div>', unsafe_allow_html=True)
    client = grouped_view(df, ["Client"]).head(15)
    view = client.copy()
    view["Facility Limit"] = view["Facility_Limit"].apply(money)
    view["Revenue"] = view["Total_Revenue"].apply(money)
    view["Lending Drawn"] = view["Lending_Drawn"].apply(money)
    view["Deposits"] = view["Deposit_Balance"].apply(money)
    view["Wallet Share"] = view["Wallet_Share"].apply(pct)
    view["LTM Group RoE"] = view["LTM_Group_RoE"].apply(pct)
    view["NIM"] = view["NIM_bps"].round(1).astype(str) + " bps"
    st.dataframe(view[["Client", "Facility Limit", "Revenue", "Lending Drawn", "Deposits", "NIM", "LTM Group RoE", "Wallet Share"]], use_container_width=True, hide_index=True)


# =========================================================
# RELATIONSHIP 360
# =========================================================
with tab3:
    st.markdown('<div class="ec-section-title">Relationship 360</div>', unsafe_allow_html=True)
    st.markdown('<div class="ec-subtitle">Client-level relationship economics, deposits, wallet share and product penetration.</div>', unsafe_allow_html=True)

    selected_client = st.selectbox("Select Relationship", sorted(df["Client"].unique()), key="relationship360_client_selector")
    client_df = df[df["Client"] == selected_client].copy()

    client_country = client_df["Country"].mode().iloc[0] if not client_df["Country"].mode().empty else "-"
    client_sector = client_df["Sector"].mode().iloc[0] if not client_df["Sector"].mode().empty else "-"
    client_tier = client_df["Client_Tier"].mode().iloc[0] if not client_df["Client_Tier"].mode().empty else "-"
    owner = client_df["Relationship_Owner"].mode().iloc[0] if not client_df["Relationship_Owner"].mode().empty else "-"

    st.markdown(f"""
    <div class="ec-card">
        <div class="ec-alert-title">{selected_client}</div>
        <div class="ec-alert-text">{client_tier} Client | {client_country} | {client_sector} | Relationship Owner: {owner}</div>
    </div>
    """, unsafe_allow_html=True)

    total_limit_c = client_df["Facility_Limit"].sum()
    total_drawn_c = client_df["Lending_Drawn"].sum()
    total_revenue_c = client_df["Total_Revenue"].sum()
    total_deposits_c = client_df["Deposit_Balance"].sum()
    total_rwa_c = client_df["RWA"].sum()
    total_niat_c = client_df["NIAT"].sum()
    ltm_groe_c = safe_div(total_niat_c, total_rwa_c)
    utilization_c = safe_div(total_drawn_c, total_limit_c)
    wallet_estimate_c = client_df["Wallet_Estimate"].sum()
    wallet_share_c = safe_div(total_revenue_c, wallet_estimate_c)
    wallet_gap_c = max(wallet_estimate_c - total_revenue_c, 0)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Facility Limit", money(total_limit_c))
    c2.metric("Lending Drawn", money(total_drawn_c))
    c3.metric("Utilization", pct(utilization_c))
    c4.metric("Revenue", money(total_revenue_c))
    c5.metric("Deposits", money(total_deposits_c))
    c6.metric("LTM Group RoE", pct(ltm_groe_c))

    st.markdown("### Wallet Share Prototype")
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Estimated Wallet", money(wallet_estimate_c))
    w2.metric("Current Revenue", money(total_revenue_c))
    w3.metric("Wallet Share", pct(wallet_share_c))
    w4.metric("Wallet Gap", money(wallet_gap_c))

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("### Revenue by Product")
        product_rev = client_df.groupby("Product", as_index=False)["Total_Revenue"].sum().sort_values("Total_Revenue", ascending=False)
        st.plotly_chart(bar_chart(product_rev, "Product", "Total_Revenue", "Relationship 360 — Revenue by Product"), use_container_width=True, key="rel360_revenue_product")

    with right:
        st.markdown("### Exposure by Product")
        product_exp = client_df.groupby("Product", as_index=False)["Lending_Drawn"].sum().sort_values("Lending_Drawn", ascending=False)
        st.plotly_chart(bar_chart(product_exp, "Product", "Lending_Drawn", "Relationship 360 — Exposure by Product"), use_container_width=True, key="rel360_exposure_product")

    st.markdown("### Product Penetration Table")
    product_table = client_df.groupby("Product", as_index=False).agg({
        "Facility_Limit": "sum",
        "Lending_Drawn": "sum",
        "Total_Revenue": "sum",
        "Deposit_Balance": "sum",
        "RWA": "sum",
        "NIAT": "sum"
    })
    product_table["LTM_Group_RoE"] = product_table.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    product_table["Utilization"] = product_table.apply(lambda r: safe_div(r["Lending_Drawn"], r["Facility_Limit"]), axis=1)
    show_pt = product_table.copy()
    show_pt["Facility Limit"] = show_pt["Facility_Limit"].apply(money)
    show_pt["Lending Drawn"] = show_pt["Lending_Drawn"].apply(money)
    show_pt["Revenue"] = show_pt["Total_Revenue"].apply(money)
    show_pt["Deposits"] = show_pt["Deposit_Balance"].apply(money)
    show_pt["Utilization"] = show_pt["Utilization"].apply(pct)
    show_pt["LTM Group RoE"] = show_pt["LTM_Group_RoE"].apply(pct)
    st.dataframe(show_pt[["Product", "Facility Limit", "Lending Drawn", "Revenue", "Deposits", "Utilization", "LTM Group RoE"]], use_container_width=True, hide_index=True)

    st.markdown("### AI Banker Commentary")
    commentary = []
    if wallet_share_c < 0.30:
        commentary.append("Wallet capture appears underpenetrated relative to the estimated relationship wallet. This suggests white-space opportunity.")
    elif wallet_share_c < 0.60:
        commentary.append("Wallet capture is moderate. Selective cross-sell and product deepening may improve relationship economics.")
    else:
        commentary.append("Wallet capture appears strong. Management focus should be on retention and pricing discipline.")

    if utilization_c < 0.40:
        commentary.append("Facility utilization is relatively low, suggesting unused relationship capacity or a need to review committed limit efficiency.")
    elif utilization_c > 0.80:
        commentary.append("Facility utilization is high, indicating deep lending engagement and potential need to monitor concentration and refinancing risk.")

    if total_deposits_c < total_drawn_c * 0.25:
        commentary.append("Deposit penetration appears weak relative to lending exposure. Cash management and treasury engagement may be a priority.")
    else:
        commentary.append("Deposit base provides relationship stickiness and potential treasury value.")

    product_count = client_df["Product"].nunique()
    if product_count <= 2:
        commentary.append("Product penetration is narrow. Cross-sell opportunities may exist across trade, markets, cash management, DCM or fund finance products.")
    else:
        commentary.append("Product usage is diversified across multiple banking products.")

    for item in commentary:
        st.markdown(f"- {item}")


# =========================================================
# DEPOSIT INTELLIGENCE
# =========================================================
with tab4:
    st.markdown('<div class="ec-section-title">Deposit Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="ec-subtitle">Deposit franchise, operational balance and treasury opportunity view.</div>', unsafe_allow_html=True)

    d1, d2 = st.columns(2, gap="large")
    with d1:
        st.plotly_chart(
            bar_chart(grouped_view(df, ["Country"]).head(8), "Country", "Deposit_Balance", "Deposits by Country"),
            use_container_width=True,
            key="deposits_country"
        )
    with d2:
        deposit_type = df.groupby("Deposit_Type", as_index=False)["Deposit_Balance"].sum()
        st.plotly_chart(
            bar_chart(deposit_type, "Deposit_Type", "Deposit_Balance", "Deposits by Type"),
            use_container_width=True,
            key="deposits_type"
        )

    st.markdown("### Deposit Relationship Table")
    deposit_rel = grouped_view(df, ["Client"]).head(20)
    dep = deposit_rel.copy()
    dep["Deposits"] = dep["Deposit_Balance"].apply(money)
    dep["Lending Drawn"] = dep["Lending_Drawn"].apply(money)
    dep["Revenue"] = dep["Total_Revenue"].apply(money)
    dep["LTM Group RoE"] = dep["LTM_Group_RoE"].apply(pct)
    st.dataframe(dep[["Client", "Deposits", "Lending Drawn", "Revenue", "LTM Group RoE"]], use_container_width=True, hide_index=True)


# =========================================================
# PRICING & NIM
# =========================================================
with tab5:
    st.markdown('<div class="ec-section-title">Pricing & NIM Risk</div>', unsafe_allow_html=True)
    low = df[df["NIM_bps"] < pricing_floor].copy()
    a, b, c = st.columns(3)
    a.metric("Pricing Review Deals", len(low))
    b.metric("Pricing Review Exposure", money(low["Lending_Drawn"].sum() if len(low) else 0))
    c.metric("Configurable Floor", f"{pricing_floor} bps")

    if len(low):
        low["Lending Drawn"] = low["Lending_Drawn"].apply(money)
        low["Revenue"] = low["Total_Revenue"].apply(money)
        low["LTM Group RoE"] = low["LTM_Group_RoE"].apply(pct)
        low["NIM"] = low["NIM_bps"].round(1).astype(str) + " bps"
        st.dataframe(low[["Deal_ID", "Client", "Country", "Product", "Lending Drawn", "Revenue", "NIM", "LTM Group RoE"]], use_container_width=True, hide_index=True)
    else:
        st.success("No pricing review deals detected.")


# =========================================================
# CAPITAL EFFICIENCY
# =========================================================
with tab6:
    st.markdown('<div class="ec-section-title">Capital Efficiency</div>', unsafe_allow_html=True)
    st.plotly_chart(combo_exposure_roe(df), use_container_width=True, key="capital_exposure_roe")

    st.markdown("### Capital Efficiency Watchlist")
    watch = executive_watchlist(df, roe_floor, pricing_floor)
    if watch.empty:
        st.success("No pricing / profitability watchlist relationships detected.")
    else:
        st.dataframe(watch, use_container_width=True, hide_index=True)


# =========================================================
# PORTFOLIO DATA
# =========================================================
with tab7:
    st.markdown('<div class="ec-section-title">Portfolio Data</div>', unsafe_allow_html=True)
    show = df.copy()
    show["LTM Group RoE"] = show["LTM_Group_RoE"].apply(pct)
    show["Wallet Share"] = show["Wallet_Share"].apply(pct)
    st.dataframe(show, use_container_width=True)
