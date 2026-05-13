
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="EC-AI Banking Engine v0.8.2", layout="wide", initial_sidebar_state="expanded")

# =========================================================
# CONFIGURABLE DEMO THRESHOLDS
# =========================================================
DEFAULT_PRICING_FLOOR_BPS = 50
DEFAULT_RELATIONSHIP_ROE_FLOOR = 0.18

# =========================================================
# EC-AI BANKING VISUAL LANGUAGE
# =========================================================
NAVY = "#08264A"
NAVY_2 = "#173A5E"
EXEC_BLUE = "#325B8C"
STEEL = "#6E7B87"
BLUE_GREY = "#7E8B97"
LIGHT_STEEL = "#D9DEE3"
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
    padding: 12px 16px;
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
    font-size: 13px;
    line-height: 1.35;
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
        "Term Loan", "Revolver", "Project Finance", "Fund Finance",
        "Structured Finance", "Trade LC", "AR Financing", "Supply Chain Finance",
        "FX / Markets", "Hedging", "Cash Management", "Deposits",
        "DCM", "ECM", "Syndication", "Securitization", "Advisory", "Guarantee"
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
        product = rng.choice(
            products,
            p=[0.12, 0.09, 0.06, 0.055, 0.045, 0.06, 0.045, 0.045,
               0.07, 0.035, 0.07, 0.06, 0.045, 0.025, 0.035, 0.025, 0.025, 0.09]
        )
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
        elif product in ["Trade Finance", "Trade LC", "AR Financing", "Supply Chain Finance"]:
            nim_bps = rng.choice([35, 60, 90, 120, 160], p=[0.15, 0.25, 0.25, 0.22, 0.13])
        elif product in ["FX / Markets", "Hedging", "DCM", "ECM", "Syndication", "Securitization", "Advisory", "Fund Finance", "Project Finance", "Structured Finance"]:
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

        maturity_days = int(rng.choice([30, 60, 90, 180, 365, 730], p=[0.20, 0.20, 0.22, 0.18, 0.14, 0.06]))
        deposit_maturity_date = (pd.Timestamp("2026-04-30") + pd.Timedelta(days=maturity_days)).date().isoformat()
        liquidity_profile = rng.choice(["Sticky", "Stable", "Rate Sensitive", "Short-Term"], p=[0.25, 0.35, 0.25, 0.15])
        deposit_revenue = deposit_balance * rng.uniform(0.0015, 0.0080)

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
            "Deposit_Revenue": round(deposit_revenue, 0),
            "Deposit_Maturity_Date": deposit_maturity_date,
            "Liquidity_Profile": liquidity_profile,
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
        "Wallet_Estimate", "Wallet_Share", "Wallet_Gap", "Deposit_Growth", "Deposit_Revenue"
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

    # Deal-screening profitability is transaction-level RoE; relationship screens use LTM / 3Y Group RoE.
    if "Tx_RoE" not in df.columns:
        product_factor = df["Product"].astype(str).map({
            "Project Finance": 1.08, "Fund Finance": 1.05, "Structured Finance": 1.08,
            "Securitization": 1.12, "DCM": 1.10, "ECM": 1.10, "Syndication": 1.06,
            "Term Loan": 0.98, "Revolver": 0.95, "Trade LC": 1.02, "AR Financing": 1.03,
            "Supply Chain Finance": 1.03, "FX / Markets": 1.10, "Hedging": 1.08
        }).fillna(1.0)
        df["Tx_RoE"] = (df["LTM_Group_RoE"] * product_factor).clip(lower=0.02, upper=0.45)
    else:
        df["Tx_RoE"] = pd.to_numeric(df["Tx_RoE"], errors="coerce").fillna(df["LTM_Group_RoE"])

    if "Renewal_Type" not in df.columns:
        df["Renewal_Type"] = np.resize(np.array(["New", "Renewal", "Refinance"]), len(df))
    if "Commitment_Type" not in df.columns:
        df["Commitment_Type"] = np.where(df["Product"].astype(str).str.contains("Revolver|LC|Guarantee", case=False, regex=True), "Committed", "Uncommitted")

    if "Wallet_Estimate" not in df.columns:
        df["Wallet_Estimate"] = df["Total_Revenue"] * 3.0

    if "Wallet_Share" not in df.columns:
        df["Wallet_Share"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["Wallet_Estimate"]), axis=1)

    if "Wallet_Gap" not in df.columns:
        df["Wallet_Gap"] = (df["Wallet_Estimate"] - df["Total_Revenue"]).clip(lower=0)

    if "Deposit_Growth" not in df.columns:
        df["Deposit_Growth"] = 0.0
    if "Deposit_Revenue" not in df.columns:
        df["Deposit_Revenue"] = 0.0
    if "Deposit_Maturity_Date" not in df.columns:
        df["Deposit_Maturity_Date"] = "N/A"
    if "Liquidity_Profile" not in df.columns:
        df["Liquidity_Profile"] = "Stable"

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
def axis_ticks(max_y, target_ticks=5):
    """Clean executive-scale axis ticks. Avoid dense unreadable tick marks."""
    max_y = float(max_y or 0)
    if max_y <= 0:
        return [0, 1], ["0", "1"]
    raw_step = max_y / target_ticks
    magnitude = 10 ** np.floor(np.log10(raw_step))
    step = np.ceil(raw_step / magnitude) * magnitude
    tick_max = np.ceil(max_y / step) * step
    ticks = list(np.arange(0, tick_max + step * 0.5, step))
    labels = ["0" if v == 0 else (f"{v/1_000_000_000:.1f}B" if v >= 1_000_000_000 else f"{v/1_000_000:.0f}M") for v in ticks]
    return ticks, labels


def bar_chart(df, x, y, title, height=320, max_items=None):
    chart_df = df.copy().sort_values(y, ascending=False)
    if max_items:
        chart_df = chart_df.head(max_items)
    chart_df["Label"] = chart_df[y].apply(money)
    fig = px.bar(chart_df, x=x, y=y, text="Label", title=title)
    fig.update_traces(
        marker_color=rank_colors(len(chart_df)),
        marker_line_width=0,
        textposition="outside",
        textfont=dict(size=11, color=NAVY),
        cliponaxis=False,
    )
    ticks, labels = axis_ticks(chart_df[y].max() if len(chart_df) else 0, target_ticks=5)
    fig.update_layout(
        height=height,
        margin=dict(l=30, r=22, t=48, b=54),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color=TEXT, family="Inter, Arial, sans-serif", size=11),
        title=dict(font=dict(size=16, color=NAVY, family="Inter, Arial, sans-serif")),
        yaxis=dict(tickvals=ticks, ticktext=labels, showgrid=False, zeroline=False, nticks=5),
        xaxis=dict(tickangle=0, tickfont=dict(size=10, color=TEXT), automargin=True),
        bargap=0.55,
        showlegend=False,
    )
    return fig


def dsc_combo_chart(df, group_col, value_col, rate_col, title, floor_value, rate_suffix="%", height=310):
    g = df.groupby(group_col, as_index=False).agg({value_col: "sum", rate_col: "mean"}).sort_values(value_col, ascending=False).head(8)
    if rate_col in ["Tx_RoE", "LTM_Group_RoE"]:
        g["Rate"] = g[rate_col] * 100
        floor_line = floor_value * 100
    else:
        g["Rate"] = g[rate_col]
        floor_line = floor_value
    fig = go.Figure()
    fig.add_trace(go.Bar(x=g[group_col], y=g[value_col], marker_color=rank_colors(len(g)), name="Approved / Facility Amount",
                         text=[money(v) for v in g[value_col]], textposition="outside", cliponaxis=False))
    fig.add_trace(go.Scatter(x=g[group_col], y=g["Rate"], yaxis="y2", mode="lines+markers+text", name=rate_col.replace("_", " "),
                             line=dict(color=EXEC_BLUE, width=2.5), marker=dict(size=8, color=EXEC_BLUE),
                             text=[f"{v:.1f}{rate_suffix}" for v in g["Rate"]], textposition="top center"))
    ticks, labels = axis_ticks(g[value_col].max(), 5)
    fig.update_layout(
        title=title, height=height, margin=dict(l=35, r=35, t=50, b=65),
        plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Inter, Arial, sans-serif", color=TEXT, size=11),
        xaxis=dict(tickangle=0, automargin=True, tickfont=dict(size=10)),
        yaxis=dict(title="Amount", tickvals=ticks, ticktext=labels, showgrid=False, zeroline=False),
        yaxis2=dict(title=rate_col.replace("_", " "), overlaying="y", side="right", showgrid=False, ticksuffix=rate_suffix, range=[0, max(30, g["Rate"].max()*1.25, floor_line*1.25)]),
        shapes=[dict(type="line", xref="paper", x0=0, x1=1, yref="y2", y0=floor_line, y1=floor_line, line=dict(color=RED, width=1.5, dash="dash"))],
        legend=dict(orientation="h", y=1.12), bargap=0.55
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
        height=360,
        margin=dict(l=35, r=35, t=58, b=70),
        xaxis=dict(tickangle=0, tickfont=dict(size=10), automargin=True),
        yaxis=dict(title="Lending Exposure (USD)", tickvals=ticks, ticktext=labels, showgrid=False, zeroline=False),
        yaxis2=dict(title="LTM Group RoE %", overlaying="y", side="right", ticksuffix="%", showgrid=False),
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
    '<div class="ec-hero"><h1>EC-AI Banking Engine v0.8</h1><p>AI-native Relationship Intelligence Platform for corporate and investment banking.</p></div>',
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
    st.caption("Demo thresholds only — configure for each institution / pilot. NII = Net Interest Income.")
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
# V0.8.2 BLUEPRINT LAYOUT HELPERS
# =========================================================
def section_header(title, subtitle=None):
    st.markdown(f'<div class="ec-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="ec-subtitle">{subtitle}</div>', unsafe_allow_html=True)

def kpi_card(label, value, delta=None):
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ''
    html = f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{delta_html}</div>'
    st.markdown(html, unsafe_allow_html=True)

def chart_card(fig, title=None, key=None):
    with st.container(border=True):
        if title:
            st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, key=key, config={"displayModeBar": False})

def bar_chart_v2(df, x, y, title, height=260, max_items=None):
    chart_df = df.copy().sort_values(y, ascending=False)
    if max_items:
        chart_df = chart_df.head(max_items)
    chart_df["Label"] = chart_df[y].apply(money)
    fig = px.bar(chart_df, x=x, y=y, text="Label", title=title)
    fig.update_traces(marker_color=rank_colors(len(chart_df)), marker_line_width=0, textposition="outside", textfont=dict(size=11, color=NAVY), cliponaxis=False, width=0.42)
    ticks, labels = axis_ticks(chart_df[y].max() if len(chart_df) else 0, target_ticks=4)
    fig.update_layout(height=height, margin=dict(l=28, r=18, t=35, b=42), plot_bgcolor="white", paper_bgcolor="white", font=dict(color=TEXT, family="Inter, Arial, sans-serif", size=11), title=dict(font=dict(size=14, color=NAVY)), yaxis=dict(tickvals=ticks, ticktext=labels, showgrid=False, zeroline=False), xaxis=dict(tickangle=0, tickfont=dict(size=10, color=TEXT), automargin=True), bargap=0.62, showlegend=False)
    return fig

def exposure_roe_clean(df):
    ranked = grouped_view(df, ["Client"]).sort_values("Lending_Drawn", ascending=False).head(12)
    ranked["LTM Group RoE %"] = ranked["LTM_Group_RoE"] * 100
    ranked["Short_Client"] = ranked["Client"].astype(str).str.replace("Sample ", "", regex=False).str.replace(" Holdings", "", regex=False).str.replace(" Group", "", regex=False).str.slice(0, 14)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ranked["Short_Client"], y=ranked["Lending_Drawn"], name="Lending Exposure", marker_color=NAVY, text=[money(v) for v in ranked["Lending_Drawn"]], textposition="outside", cliponaxis=False, width=0.42))
    fig.add_trace(go.Scatter(x=ranked["Short_Client"], y=ranked["LTM Group RoE %"], name="LTM Group RoE %", mode="lines+markers", marker=dict(color=EXEC_BLUE, size=7), line=dict(color=EXEC_BLUE, width=2.2), yaxis="y2"))
    max_y = ranked["Lending_Drawn"].max() if len(ranked) else 0
    ticks, labels = axis_ticks(max_y, target_ticks=4)
    fig.update_layout(title="Capital Efficiency: Exposure vs LTM Group RoE", height=310, margin=dict(l=36, r=36, t=48, b=52), plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Inter, Arial, sans-serif", size=10, color=TEXT), xaxis=dict(tickangle=0, tickfont=dict(size=9), automargin=True, showgrid=False), yaxis=dict(title="Lending Exposure", tickvals=ticks, ticktext=labels, showgrid=False, zeroline=False), yaxis2=dict(title="RoE %", overlaying="y", side="right", ticksuffix="%", showgrid=False), legend=dict(orientation="h", y=1.16))
    return fig

st.markdown("""
<style>
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #08264A 0%, #031B33 100%); }
section[data-testid="stSidebar"] * { color: #F8FAFC !important; }
section[data-testid="stSidebar"] .stRadio label { background: rgba(255,255,255,0.06); border-radius: 10px; padding: 5px 8px; margin: 3px 0; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#CBD5E1 !important; }
.block-container { padding-top: 1.2rem; padding-left: 1.7rem; padding-right: 1.7rem; max-width: 1500px; }
.topbar { background:white; border:1px solid #D7DEE6; border-radius:16px; padding:14px 18px; margin-bottom:14px; box-shadow:0 1px 2px rgba(15,23,42,0.04); }
.kpi-card { background:white; border:1px solid #D7DEE6; border-radius:14px; padding:14px 16px; min-height:92px; box-shadow:0 1px 2px rgba(15,23,42,0.04); }
.kpi-label { font-size:12px; color:#667085; font-weight:700; text-transform:uppercase; letter-spacing:.02em; }
.kpi-value { font-size:24px; color:#08264A; font-weight:850; margin-top:7px; }
.kpi-delta { font-size:12px; color:#087443; margin-top:5px; font-weight:650; }
.chart-title { font-size:15px; color:#08264A; font-weight:850; margin-bottom:2px; }
.ec-card p, .ec-alert-text { font-size:14px !important; }
[data-testid="stVerticalBlockBorderWrapper"] { background:white; border-radius:16px; }
hr { margin: 1.2rem 0; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# APP HEADER / SIDEBAR — V0.8.2 BLUEPRINT
# =========================================================
with st.sidebar:
    st.markdown("# EC-AI")
    st.markdown("**Banking Intelligence**  \nv0.8.2")
    st.markdown("---")
    nav = st.radio("Navigate", ["Executive Dashboard", "Revenue & Exposure", "Capital Efficiency", "Deposit Intelligence", "Competitor Benchmarking", "Client Overview", "Wallet Intelligence", "Product Penetration", "Deal Screening (DSC)", "Portfolio Data"], index=0, label_visibility="collapsed")
    st.markdown("---")
    data_mode = st.radio("Data source", ["Use Built-in Demo Data", "Upload File"], index=0)
    uploaded = None
    if data_mode == "Upload File":
        uploaded = st.file_uploader("Upload banking performance file", type=["csv", "xlsx"])
    st.markdown("---")
    st.markdown("### Threshold Settings")
    roe_floor = st.slider("RoE floor", 0.05, 0.30, DEFAULT_RELATIONSHIP_ROE_FLOOR, 0.01, format="%.2f")
    pricing_floor = st.slider("Pricing floor (bps)", 0, 150, DEFAULT_PRICING_FLOOR_BPS, 5)
    st.caption("Demo thresholds only — not institution-specific.")

if data_mode == "Use Built-in Demo Data":
    raw = make_demo_data()
else:
    if uploaded is None:
        st.info("Upload a banking performance file or switch to built-in demo data.")
        st.stop()
    raw = pd.read_excel(uploaded) if uploaded.name.lower().endswith(".xlsx") else pd.read_csv(uploaded)

df = ensure_metrics(raw)

total_revenue = df["Total_Revenue"].sum(); total_nii = df["Net_Interest_Income"].sum(); total_drawn = df["Lending_Drawn"].sum(); total_deposit = df["Deposit_Balance"].sum(); total_rwa = df["RWA"].sum(); total_niat = df["NIAT"].sum(); portfolio_roe = safe_div(total_niat, total_rwa); wallet_share = safe_div(total_revenue, df["Wallet_Estimate"].sum())

st.markdown('<div class="topbar"><b>Business Unit</b>&nbsp;&nbsp; GCIB &nbsp;&nbsp;&nbsp;&nbsp; <b>Country Cluster</b>&nbsp;&nbsp; Asia &nbsp;&nbsp;&nbsp;&nbsp; <b>Currency</b>&nbsp;&nbsp; USD &nbsp;&nbsp;&nbsp;&nbsp; <b>Time Period</b>&nbsp;&nbsp; LTM / Demo</div>', unsafe_allow_html=True)

if nav == "Executive Dashboard":
    section_header("Executive Portfolio Overview", "LTM performance summary — wallet, exposure, deposits, revenue and profitability.")
    cols = st.columns(6)
    for col, label, val, delta in zip(cols, ["Revenue","NII","RWA","Lending Exposure","Deposits","LTM Group RoE"], [money(total_revenue),money(total_nii),money(total_rwa),money(total_drawn),money(total_deposit),pct(portfolio_roe)], ["demo vs PY","Net interest income","Risk weighted assets","Drawn balance","Deposit franchise","Portfolio return"]):
        with col: kpi_card(label, val, delta)
    c1, c2 = st.columns(2, gap="large")
    with c1: chart_card(bar_chart_v2(grouped_view(df, ["Country"]), "Country", "Total_Revenue", "Revenue by Country (USD)", height=260, max_items=6), key="ex_rev_country")
    with c2: chart_card(bar_chart_v2(grouped_view(df, ["Country"]), "Country", "Lending_Drawn", "Exposure by Country (USD)", height=260, max_items=6), key="ex_exp_country")
    section_header("Deposit Intelligence", "Franchise strength, liquidity profile and treasury opportunities.")
    d1, d2, d3 = st.columns([1,1,1.05], gap="large")
    with d1: chart_card(bar_chart_v2(grouped_view(df, ["Country"]), "Country", "Deposit_Balance", "Deposits by Country", height=210, max_items=6), key="ex_dep_country")
    with d2:
        dep_type = df.groupby("Deposit_Type", as_index=False)["Deposit_Balance"].sum()
        chart_card(bar_chart_v2(dep_type, "Deposit_Type", "Deposit_Balance", "Deposits by Type", height=210), key="ex_dep_type")
    with d3:
        st.markdown('<div class="ec-card"><div class="ec-alert-title">Liquidity Profile</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ec-alert-text">CASA / operational balances provide relationship stickiness and treasury dialogue.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ec-alert-text">Loan-to-deposit ratio: <b>{pct(safe_div(total_drawn,total_deposit))}</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ec-alert-text">Estimated wallet penetration: <b>{pct(wallet_share)}</b></div></div>', unsafe_allow_html=True)
    c3, c4 = st.columns([1.15,.85], gap="large")
    with c3: chart_card(exposure_roe_clean(df), key="ex_cap_eff")
    with c4:
        top_country=grouped_view(df,["Country"]).iloc[0]
        st.markdown('<div class="ec-card"><div class="ec-alert-title">Key Insights</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ec-alert-text">• {top_country.Country} is the largest revenue contributor at <b>{money(top_country.Total_Revenue)}</b>.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ec-alert-text">• RoE floor is set at <b>{roe_floor*100:.0f}%</b> for demo purposes.</div>', unsafe_allow_html=True)
        st.markdown('<div class="ec-alert-text">• Use Relationship 360 to identify product gaps, deposit opportunities and IB wallet expansion.</div></div>', unsafe_allow_html=True)

elif nav == "Revenue & Exposure":
    section_header("Revenue & Exposure", "Actual historical revenue, exposure and product distribution.")
    c1,c2=st.columns(2,gap="large")
    with c1: chart_card(bar_chart_v2(grouped_view(df,["Product"]),"Product","Total_Revenue","Revenue by Product",height=300,max_items=10),key="rev_prod")
    with c2: chart_card(bar_chart_v2(grouped_view(df,["Product"]),"Product","Lending_Drawn","Exposure by Product",height=300,max_items=10),key="exp_prod")
    c3,c4=st.columns(2,gap="large")
    with c3: chart_card(bar_chart_v2(grouped_view(df,["Country"]),"Country","Total_Revenue","Revenue by Country",height=300),key="rev_country")
    with c4: chart_card(bar_chart_v2(grouped_view(df,["Country"]),"Country","Lending_Drawn","Exposure by Country",height=300),key="exp_country")

elif nav == "Capital Efficiency":
    section_header("Capital Efficiency", "Exposure vs LTM Group RoE. Gridlines removed for a cleaner institutional look.")
    chart_card(exposure_roe_clean(df), key="cap_eff_clean")
    watch=executive_watchlist(df,roe_floor,pricing_floor); st.dataframe(watch, use_container_width=True, hide_index=True) if not watch.empty else st.success("No pricing / profitability watchlist relationships detected.")

elif nav == "Deposit Intelligence":
    section_header("Deposit Intelligence", "Deposit balance, deposit revenue, maturity and liquidity profile.")
    c1,c2=st.columns(2,gap="large")
    with c1: chart_card(bar_chart_v2(grouped_view(df,["Country"]),"Country","Deposit_Balance","Deposits by Country",height=230,max_items=6),key="dep_country")
    with c2:
        dep_type=df.groupby("Deposit_Type",as_index=False)["Deposit_Balance"].sum(); chart_card(bar_chart_v2(dep_type,"Deposit_Type","Deposit_Balance","Deposits by Type",height=230),key="dep_type")
    dep_detail=df[["Client","Country","Deposit_Type","Liquidity_Profile","Operational_Deposit_Flag","Deposit_Balance","Deposit_Revenue","Deposit_Maturity_Date"]].copy(); dep_detail["Deposit Balance"]=dep_detail["Deposit_Balance"].apply(money); dep_detail["Deposit Revenue"]=dep_detail["Deposit_Revenue"].apply(money)
    st.dataframe(dep_detail[["Client","Country","Deposit_Type","Liquidity_Profile","Operational_Deposit_Flag","Deposit Balance","Deposit Revenue","Deposit_Maturity_Date"]],use_container_width=True,hide_index=True)

elif nav == "Competitor Benchmarking":
    section_header("Competitor Benchmarking", "Wallet sizing prototype using common global banking competitors.")
    competitors=["HSBC","J.P. Morgan","Goldman Sachs","Citi","MUFG","SMBC","Standard Chartered","BNP Paribas"]; rng=np.random.default_rng(12); comp=pd.DataFrame({"Bank":competitors,"Estimated Wallet":rng.integers(80,380,len(competitors))*1_000_000}); comp.loc[comp["Bank"].eq("MUFG"),"Estimated Wallet"]=total_revenue; comp["Current Share"]=comp["Estimated Wallet"]/comp["Estimated Wallet"].sum(); comp["Wallet Gap"]=comp["Estimated Wallet"].max()-comp["Estimated Wallet"]
    chart_card(bar_chart_v2(comp,"Bank","Estimated Wallet","Estimated Captured Wallet by Bank",height=320),key="comp_wallet")
    comp_show=comp.copy(); comp_show["Estimated Wallet"]=comp_show["Estimated Wallet"].apply(money); comp_show["Current Share"]=comp_show["Current Share"].apply(pct); comp_show["Wallet Gap"]=comp_show["Wallet Gap"].apply(money); st.dataframe(comp_show,use_container_width=True,hide_index=True)

elif nav in ["Client Overview","Wallet Intelligence","Product Penetration"]:
    section_header("Relationship 360", "Client-specific banking view: exposure, deposits, wallet and product white space.")
    client=st.selectbox("Select Client",sorted(df["Client"].unique())); cdf=df[df["Client"].eq(client)]
    mcols=st.columns(5)
    for col, label, val in zip(mcols,["Client","Revenue","Exposure","Deposits","Wallet Share"],[client,money(cdf["Total_Revenue"].sum()),money(cdf["Lending_Drawn"].sum()),money(cdf["Deposit_Balance"].sum()),pct(safe_div(cdf["Total_Revenue"].sum(),cdf["Wallet_Estimate"].sum()))]):
        with col: kpi_card(label,val)
    c1,c2=st.columns(2,gap="large")
    with c1: chart_card(bar_chart_v2(grouped_view(cdf,["Product"]),"Product","Total_Revenue","Client Revenue by Product",height=260,max_items=8),key="rel_rev_prod")
    with c2: chart_card(bar_chart_v2(grouped_view(cdf,["Product"]),"Product","Lending_Drawn","Client Exposure by Product",height=260,max_items=8),key="rel_exp_prod")
    st.markdown("### AI Banker Commentary")
    st.markdown("- Pitch angle: diagnose whether the client need is refinancing, capex funding, working capital, hedging, treasury centralisation or IB execution.")
    st.markdown("- Product gap check: assess DCM / syndication / project finance / fund finance / securitization / trade LC / AR financing / cash management penetration.")
    st.markdown("- Wallet strategy: compare current revenue against estimated wallet, current share, wallet gap and penetration.")

elif nav == "Deal Screening (DSC)":
    section_header("Deal Screening / Pricing Engine", "DSC-style mini dashboard: facility amount, Tx RoE, NIM bucket and quality flag.")
    m1,m2,m3,m4=st.columns(4); m1.metric("Screened Deals",len(df)); m2.metric("Facility Amount",money(df["Facility_Limit"].sum())); m3.metric("Below Tx RoE Floor",len(df[df["Tx_RoE"]<roe_floor])); m4.metric("Below Margin Floor",len(df[df["NIM_bps"]<pricing_floor]))
    c1,c2=st.columns(2,gap="large")
    with c1: chart_card(dsc_combo_chart(df,"Product","Facility_Limit","Tx_RoE","Tx RoE by Product",roe_floor,"%",height=300),key="dsc1")
    with c2: chart_card(dsc_combo_chart(df,"Country","Facility_Limit","Tx_RoE","Tx RoE by Country",roe_floor,"%",height=300),key="dsc2")
    bucket_df=df.copy(); bucket_df["NIM Bucket"]=pd.cut(bucket_df["NIM_bps"],bins=[-1,50,75,100,150,9999],labels=["<50 bps","50-75 bps","75-100 bps","100-150 bps",">150 bps"]); chart_card(bar_chart_v2(bucket_df.groupby("NIM Bucket",as_index=False,observed=False)["Facility_Limit"].sum(),"NIM Bucket","Facility_Limit","Facility Amount by NIM Bucket",height=270),key="dsc_bucket")
    show=df.copy().sort_values("Facility_Limit",ascending=False).head(35); show["Facility Limit"]=show["Facility_Limit"].apply(money); show["Tx RoE"]=show["Tx_RoE"].apply(pct); show["NIM"]=show["NIM_bps"].round(1).astype(str)+" bps"; show["Quality Flag"]=np.where((show["Tx_RoE"]<roe_floor)|(show["NIM_bps"]<pricing_floor),"Review","Pass")
    st.dataframe(show[["Deal_ID","Client","Country","RM","Product","Renewal_Type","Commitment_Type","Facility Limit","Tx RoE","NIM","Quality Flag"]],use_container_width=True,hide_index=True)

elif nav == "Portfolio Data":
    section_header("Portfolio Data", "Historical portfolio data: actual facilities, drawdown, revenue and deposits.")
    st.dataframe(df,use_container_width=True,hide_index=True)
    from io import BytesIO
    excel_buffer=BytesIO()
    with pd.ExcelWriter(excel_buffer,engine="openpyxl") as writer:
        df.to_excel(writer,index=False,sheet_name="Portfolio_Data"); grouped_view(df,["Country"]).to_excel(writer,index=False,sheet_name="Country_Summary"); grouped_view(df,["Product"]).to_excel(writer,index=False,sheet_name="Product_Summary")
    st.download_button("Download demo portfolio data as Excel",data=excel_buffer.getvalue(),file_name="ecai_banking_engine_v0_8_2_demo_data.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.caption("EC-AI Banking Intelligence Platform v0.8.2 | Demo data only | Framework inspired by general corporate banking analytics practice.")
