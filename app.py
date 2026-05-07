
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# EC-AI Banking Engine v0.4.1
# Executive Banking Intelligence OS
# Focus: Revenue / NIM / Tx RoE / Exposure / Deposit / Country Portfolio
# =====================================================

st.set_page_config(
    page_title="EC-AI Banking Engine v0.4.1",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LOW_NIM_THRESHOLD_BPS = 30
TX_ROE_THRESHOLD = 0.15
CRITICAL_TX_ROE = 0.05
WEAK_TX_ROE = 0.10
DFR_TARGET = 0.55

NAVY = "#071A2F"
NAVY_2 = "#0B1F3A"
BLUE_GREY = "#475569"
LIGHT_GREY = "#F3F6F9"
MID_GREY = "#CBD5E1"
TEXT = "#111827"
TEAL = "#0F766E"
GOOD = "#2E7D32"
LIGHT_GOOD = "#BFE8C5"
LIGHT_BAD = "#F5B5B5"
BAD = "#B91C1C"

# -----------------------------
# CSS / visual identity
# -----------------------------
st.markdown(
    f"""
<style>
[data-testid="stAppViewContainer"] {{
    background: #F7F9FC;
}}
.ec-hero {{
    background: linear-gradient(120deg, {NAVY} 0%, #0F3B4C 55%, {TEAL} 100%);
    border-radius: 22px;
    padding: 28px 34px;
    color: white;
    margin-bottom: 20px;
    box-shadow: 0 12px 28px rgba(7,26,47,0.22);
}}
.ec-hero-title {{
    font-size: 34px;
    font-weight: 850;
    letter-spacing: -0.02em;
    margin-bottom: 6px;
}}
.ec-hero-subtitle {{
    font-size: 16px;
    opacity: 0.90;
}}
.ec-kicker {{
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.13em;
    opacity: 0.75;
    margin-bottom: 6px;
}}
.ec-card {{
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 18px;
    padding: 16px 18px;
    box-shadow: 0 4px 14px rgba(15,23,42,0.04);
}}
.ec-card-title {{
    color: {BLUE_GREY};
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 800;
}}
.ec-card-value {{
    color: {NAVY};
    font-size: 25px;
    font-weight: 850;
    margin-top: 5px;
}}
.ec-card-note {{
    color: #64748B;
    font-size: 12px;
    margin-top: 2px;
}}
.stTabs [data-baseweb="tab-list"] {{
    gap: 10px;
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 16px;
    padding: 8px;
}}
.stTabs [data-baseweb="tab"] {{
    height: 48px;
    border-radius: 12px;
    padding: 0px 18px;
    font-size: 16px;
    font-weight: 750;
    color: {NAVY};
}}
.stTabs [aria-selected="true"] {{
    background: {NAVY};
    color: white;
}}
div[data-testid="stMetric"] {{
    background-color: white;
    border: 1px solid #E5E7EB;
    padding: 15px;
    border-radius: 16px;
    box-shadow: 0 4px 14px rgba(15,23,42,0.04);
}}
div[data-testid="stMetricLabel"] {{
    color: {BLUE_GREY};
    font-weight: 750;
}}
div[data-testid="stMetricValue"] {{
    color: {NAVY};
    font-weight: 850;
}}
.ec-section-title {{
    color: {NAVY};
    font-size: 22px;
    font-weight: 850;
    margin-top: 10px;
    margin-bottom: 6px;
}}
.ec-note {{
    color: #64748B;
    font-size: 14px;
}}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Formatting helpers
# -----------------------------
def money(x):
    try:
        x = float(x)
    except Exception:
        return "-"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000_000:
        return f"{sign}${x/1_000_000_000:,.2f}B"
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:,.1f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:,.1f}K"
    return f"{sign}${x:,.0f}"

def pct(x):
    try:
        if pd.isna(x):
            return "-"
        return f"{float(x)*100:.1f}%"
    except Exception:
        return "-"

def bps(x):
    try:
        if pd.isna(x):
            return "-"
        return f"{float(x):.1f} bps"
    except Exception:
        return "-"

def safe_div(a, b):
    try:
        a = float(a)
        b = float(b)
        if b == 0 or pd.isna(b):
            return np.nan
        return a / b
    except Exception:
        return np.nan

# -----------------------------
# Data helpers
# -----------------------------
def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
    return df

def find_col(df, options):
    cols_lower = {c.lower(): c for c in df.columns}
    for o in options:
        if o.lower() in cols_lower:
            return cols_lower[o.lower()]
    return None

def generate_sample_data(n=220, seed=42):
    rng = np.random.default_rng(seed)
    countries = ["Hong Kong", "Singapore", "Korea", "Taiwan", "Japan", "Australia", "India", "Indonesia"]
    rms = ["RM A", "RM B", "RM C", "RM D", "RM E", "RM F"]
    products = ["Term Loan", "Revolver", "Trade Finance", "Guarantee", "Deposit", "FX", "Bond", "Distribution"]
    client_types = ["Corporate", "Financial Institution", "Public Sector", "Sponsor / PF", "Commercial Subsidiary"]
    facility_types = ["Term Loan", "Committed Revolver", "Uncommitted Revolver", "Trade LC", "Guarantee", "Distribution"]
    deal_types = ["New", "Refinance", "Renewal"]
    portfolio_classes = ["Strategic Core", "Growth Opportunity", "Watchlist", "Optimize / Exit"]
    clients = [
        "Sample Property Group", "Sample Tech Holdings", "Sample Retail Ltd",
        "Sample Logistics Co", "Sample Energy Corp", "Sample Healthcare Group",
        "Sample Manufacturing Ltd", "Sample Financial Holdings", "Sample Infrastructure Co",
        "Sample Consumer Group", "Sample Shipping Ltd", "Sample Telecom Group",
        "Sample Public Utility", "Sample Sponsor Fund", "Sample Industrial Group"
    ]

    rows = []
    for i in range(n):
        country = rng.choice(countries, p=[.18,.14,.14,.12,.10,.12,.12,.08])
        product = rng.choice(products, p=[.23,.20,.16,.10,.09,.08,.08,.06])
        client_type = rng.choice(client_types, p=[.45,.20,.10,.12,.13])
        drawn = float(rng.uniform(20, 700) * 1_000_000)
        if product in ["Deposit", "FX"]:
            drawn *= rng.uniform(.15, .50)
        rwa = drawn * rng.uniform(.25, 1.05)

        # Balanced demo mix: weak, near hurdle, good, strong
        tx_bucket = rng.choice(["weak", "near", "good", "strong"], p=[.22,.25,.35,.18])
        if tx_bucket == "weak":
            tx_roe = rng.uniform(.03,.10)
            portfolio_class = rng.choice(["Watchlist", "Optimize / Exit"], p=[.55,.45])
        elif tx_bucket == "near":
            tx_roe = rng.uniform(.10,.15)
            portfolio_class = rng.choice(["Watchlist", "Growth Opportunity"], p=[.45,.55])
        elif tx_bucket == "good":
            tx_roe = rng.uniform(.15,.24)
            portfolio_class = rng.choice(["Strategic Core", "Growth Opportunity"], p=[.65,.35])
        else:
            tx_roe = rng.uniform(.24,.45)
            portfolio_class = rng.choice(["Strategic Core", "Growth Opportunity"], p=[.75,.25])

        niat = rwa * tx_roe
        revenue = niat / rng.uniform(.22,.48)
        nim = rng.choice([rng.uniform(12,29), rng.uniform(30,70), rng.uniform(70,130), rng.uniform(130,180)], p=[.23,.38,.29,.10])
        dep_ratio = rng.choice([rng.uniform(.05,.25), rng.uniform(.25,.65), rng.uniform(.65,1.65)], p=[.35,.45,.20])
        deposit = drawn * dep_ratio
        approved_amount = max(drawn * rng.uniform(1.0, 1.8), drawn)
        hereafter_groe = max(tx_roe + rng.normal(.015, .035), 0)
        rows.append({
            "Month": rng.choice(["Oct-25", "Nov-25", "Dec-25", "Jan-26", "Feb-26", "Mar-26"]),
            "Deal_ID": f"DEAL-{2000+i}",
            "Client": rng.choice(clients),
            "Country": country,
            "RM": rng.choice(rms),
            "Product": product,
            "Client_Type": client_type,
            "Portfolio_Class": portfolio_class,
            "Facility_Type": rng.choice(facility_types),
            "Deal_Type": rng.choice(deal_types, p=[.48,.32,.20]),
            "Committed_Flag": rng.choice(["Committed", "Uncommitted"], p=[.62,.38]),
            "Lending_Drawn": drawn,
            "Approved_Amount": approved_amount,
            "RWA": rwa,
            "Total_Revenue": revenue,
            "NIAT": niat,
            "Deposit_Balance": deposit,
            "NIM_bps": nim,
            "Hereafter_GRoE": hereafter_groe,
            "Distribution_Amount": approved_amount * rng.uniform(.05,.75),
        })
    return pd.DataFrame(rows)

def ensure_metrics(df):
    df = normalize_columns(df)
    colmap = {
        "Client": find_col(df, ["Client", "Customer", "Customer_Name", "Borrower", "Client_Name", "Relationship_Name"]),
        "Country": find_col(df, ["Country", "Booking_Country", "Region", "Office", "BP_Country", "GRM_Country"]),
        "RM": find_col(df, ["RM", "Relationship_Manager", "RM_Name", "Owner"]),
        "Product": find_col(df, ["Product", "Product_Type"]),
        "Client_Type": find_col(df, ["Client_Type", "Customer_Type", "Classification", "Client_Classification", "Business_Type"]),
        "Portfolio_Class": find_col(df, ["Portfolio_Class", "Portfolio_Bucket", "Management_Bucket", "Classification"]),
        "Facility_Type": find_col(df, ["Facility_Type", "Credit_Facility_Type", "Facility"]),
        "Deal_Type": find_col(df, ["Deal_Type", "Transaction_Type", "New_Refinance_Renewal"]),
        "Lending_Drawn": find_col(df, ["Lending_Drawn", "Lending_Outstanding", "Drawn", "Exposure", "Outstanding", "Loan_Drawn_End_Bal"]),
        "Approved_Amount": find_col(df, ["Approved_Amount", "Amount", "Deal_Size", "Total_Deal_Size"]),
        "RWA": find_col(df, ["RWA", "Risk_Weighted_Asset", "Risk_Weighted_Assets", "Total_SA_RWA"]),
        "Total_Revenue": find_col(df, ["Total_Revenue", "Revenue", "Gross_Revenue", "Income", "LTM_Revenue", "GOP"]),
        "NIAT": find_col(df, ["NIAT", "Net_Income_After_Tax", "Net_Income", "Profit_After_Tax", "NPAT"]),
        "Deposit_Balance": find_col(df, ["Deposit_Balance", "Deposit", "Deposits", "Deposit_Outstanding", "Depo_Bal_EOP"]),
        "NIM_bps": find_col(df, ["NIM_bps", "NIM", "NIM_Basis_Points", "Net_Interest_Margin_bps"]),
        "Net_Interest_Income": find_col(df, ["Net_Interest_Income", "NII"]),
        "Hereafter_GRoE": find_col(df, ["Hereafter_GRoE", "Hereafter_GROE", "GrROE", "GROE"]),
        "Distribution_Amount": find_col(df, ["Distribution_Amount", "Distribution_Volume", "Sell_Down_Amount"]),
        "Committed_Flag": find_col(df, ["Committed_Flag", "Committed", "Commitment_Type"]),
        "Month": find_col(df, ["Month", "YearMonth", "Date"]),
        "Deal_ID": find_col(df, ["Deal_ID", "Deal", "Transaction_ID", "Facility_ID", "DS_ID"]),
    }

    required = ["Client", "Country", "Product", "Lending_Drawn", "RWA", "Total_Revenue", "NIAT"]
    missing = [k for k in required if colmap[k] is None]
    if missing:
        st.error("Missing required banking columns: " + ", ".join(missing) + ". Required core fields are Client, Country, Product, Lending Drawn, RWA, Total Revenue and NIAT.")
        st.stop()

    rename = {v: k for k, v in colmap.items() if v is not None and v != k}
    df = df.rename(columns=rename)

    if "Client_Type" not in df.columns:
        df["Client_Type"] = "Corporate"
    if "Portfolio_Class" not in df.columns:
        df["Portfolio_Class"] = "Core"
    if "Facility_Type" not in df.columns:
        df["Facility_Type"] = df["Product"]
    if "Deal_Type" not in df.columns:
        df["Deal_Type"] = "Unknown"
    if "Deposit_Balance" not in df.columns:
        df["Deposit_Balance"] = 0
    if "Approved_Amount" not in df.columns:
        df["Approved_Amount"] = df["Lending_Drawn"]
    if "Distribution_Amount" not in df.columns:
        df["Distribution_Amount"] = 0
    if "Committed_Flag" not in df.columns:
        df["Committed_Flag"] = "Unknown"
    if "Month" not in df.columns:
        df["Month"] = "Current"
    if "Deal_ID" not in df.columns:
        df["Deal_ID"] = [f"DEAL-{i+1:04d}" for i in range(len(df))]

    numeric_cols = ["Lending_Drawn", "Approved_Amount", "RWA", "Total_Revenue", "NIAT", "Deposit_Balance", "NIM_bps", "Net_Interest_Income", "Hereafter_GRoE", "Distribution_Amount"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "NIM_bps" not in df.columns or df["NIM_bps"].isna().all() or df["NIM_bps"].sum() == 0:
        if "Net_Interest_Income" in df.columns:
            df["NIM_bps"] = df.apply(lambda r: safe_div(r["Net_Interest_Income"], r["Lending_Drawn"]) * 10000, axis=1)
        else:
            df["NIM_bps"] = np.nan

    if "Hereafter_GRoE" not in df.columns or df["Hereafter_GRoE"].sum() == 0:
        df["Hereafter_GRoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1) + 0.015

    df["Tx_RoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    df["Revenue_per_RWA"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    df["Deposit_to_Lending"] = df.apply(lambda r: safe_div(r["Deposit_Balance"], r["Lending_Drawn"]), axis=1)
    df["Distribution_Ratio"] = df.apply(lambda r: safe_div(r["Distribution_Amount"], r["Approved_Amount"]), axis=1)
    df["Low_NIM_Flag"] = df["NIM_bps"] < LOW_NIM_THRESHOLD_BPS
    df["Low_Tx_RoE_Flag"] = df["Tx_RoE"] < TX_ROE_THRESHOLD
    df["Above_Hurdle_Flag"] = df["Tx_RoE"] >= TX_ROE_THRESHOLD
    df["GRoE_Above_Hurdle_Flag"] = df["Hereafter_GRoE"] >= TX_ROE_THRESHOLD

    def classify(row):
        if row["Low_NIM_Flag"] and row["Low_Tx_RoE_Flag"]:
            return "Critical: Low NIM + Low Tx RoE"
        if row["Low_NIM_Flag"]:
            return "Low NIM: Reprice / Sell-down"
        if row["Low_Tx_RoE_Flag"]:
            return "Low Tx RoE: Improve return"
        if row["Deposit_Balance"] > row["Lending_Drawn"] and row["Total_Revenue"] > 0:
            return "Deposit rich / Cross-sell"
        return "Value creator"

    def watch_flag(row):
        tx = row["Tx_RoE"]
        if pd.isna(tx):
            return "Review"
        if tx < CRITICAL_TX_ROE:
            return "Critical"
        if tx < WEAK_TX_ROE:
            return "Weak"
        if tx < TX_ROE_THRESHOLD:
            return "Monitor"
        return "Healthy"

    df["Status"] = df.apply(classify, axis=1)
    df["Watchlist_Flag"] = df.apply(watch_flag, axis=1)
    return df

def grouped_view(df, group_cols):
    g = df.groupby(group_cols, dropna=False).agg({
        "Total_Revenue": "sum",
        "Lending_Drawn": "sum",
        "Deposit_Balance": "sum",
        "RWA": "sum",
        "NIAT": "sum",
        "Low_NIM_Flag": "sum",
        "Above_Hurdle_Flag": "mean",
        "GRoE_Above_Hurdle_Flag": "mean",
        "Distribution_Amount": "sum",
        "Approved_Amount": "sum",
    }).reset_index()

    nim_rows = []
    for _, x in df.groupby(group_cols, dropna=False):
        nim_rows.append(safe_div((x["NIM_bps"] * x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum()))
    g["NIM_bps"] = nim_rows
    g["Tx_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Revenue_per_RWA"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    g["Deposit_to_Lending"] = g.apply(lambda r: safe_div(r["Deposit_Balance"], r["Lending_Drawn"]), axis=1)
    g["Distribution_Ratio"] = g.apply(lambda r: safe_div(r["Distribution_Amount"], r["Approved_Amount"]), axis=1)
    return g.sort_values("Total_Revenue", ascending=False)

def display_table(df):
    show = df.copy()
    for c in ["Total_Revenue", "Lending_Drawn", "Deposit_Balance", "RWA", "NIAT", "Approved_Amount", "Distribution_Amount"]:
        if c in show.columns:
            show[c] = show[c].apply(money)
    for c in ["Tx_RoE", "Revenue_per_RWA", "Deposit_to_Lending", "Distribution_Ratio", "Above_Hurdle_Flag", "GRoE_Above_Hurdle_Flag", "Hereafter_GRoE"]:
        if c in show.columns:
            show[c] = show[c].apply(pct)
    if "NIM_bps" in show.columns:
        show["NIM_bps"] = show["NIM_bps"].apply(bps)
    st.dataframe(show, use_container_width=True, hide_index=True)

def portfolio_summary(df):
    total_rev = df["Total_Revenue"].sum()
    total_drawn = df["Lending_Drawn"].sum()
    total_rwa = df["RWA"].sum()
    total_niat = df["NIAT"].sum()
    tx_roe = safe_div(total_niat, total_rwa)
    low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()
    low_nim_share = safe_div(low_nim_exposure, total_drawn)
    hurdle_pass = df["Above_Hurdle_Flag"].mean()
    top_country = grouped_view(df, ["Country"]).iloc[0]["Country"]
    weakest_country_df = grouped_view(df, ["Country"]).sort_values("Tx_RoE", ascending=True)
    weakest_country = weakest_country_df.iloc[0]["Country"] if len(weakest_country_df) else "-"
    return {
        "total_rev": total_rev,
        "total_drawn": total_drawn,
        "total_rwa": total_rwa,
        "total_niat": total_niat,
        "tx_roe": tx_roe,
        "low_nim_exposure": low_nim_exposure,
        "low_nim_share": low_nim_share,
        "hurdle_pass": hurdle_pass,
        "top_country": top_country,
        "weakest_country": weakest_country,
    }

def management_summary(df):
    s = portfolio_summary(df)
    country = grouped_view(df, ["Country"])
    product = grouped_view(df, ["Product"])
    lines = [
        f"Portfolio revenue is {money(s['total_rev'])}, supported by lending drawn of {money(s['total_drawn'])} and RWA of {money(s['total_rwa'])}.",
        f"Portfolio Tx RoE is {pct(s['tx_roe'])}; hurdle pass ratio is {pct(s['hurdle_pass'])} against the 15.0% favourable threshold.",
        f"Low-NIM exposure is {money(s['low_nim_exposure'])}, representing {pct(s['low_nim_share'])} of total lending drawn.",
        f"Top revenue country is {s['top_country']}; weakest Tx RoE country is {s['weakest_country']}."
    ]
    actions = []
    if s["low_nim_share"] and s["low_nim_share"] > 0.10:
        actions.append("Prioritize low-NIM reviews: reprice, restructure or sell down exposures below 30bps.")
    if s["tx_roe"] and s["tx_roe"] < TX_ROE_THRESHOLD:
        actions.append("Improve portfolio mix by reducing capital-heavy low-return exposure and focusing new origination on above-hurdle relationships.")
    actions.append("Use the Country Portfolio tab to identify which markets require management intervention this month.")
    return lines, actions

def kpi_card(title, value, note=""):
    st.markdown(
        f"""
<div class="ec-card">
    <div class="ec-card-title">{title}</div>
    <div class="ec-card-value">{value}</div>
    <div class="ec-card-note">{note}</div>
</div>
""",
        unsafe_allow_html=True,
    )

def fig_layout(fig, title=None, height=420):
    fig.update_layout(
        template="plotly_white",
        height=height,
        title=dict(text=title or "", x=0.01, xanchor="left", font=dict(size=18, color=NAVY)),
        font=dict(color=TEXT, size=12),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=40, r=30, t=60, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    fig.update_xaxes(showline=True, linewidth=1, linecolor=MID_GREY, gridcolor="#E5E7EB")
    fig.update_yaxes(showline=True, linewidth=1, linecolor=MID_GREY, gridcolor="#E5E7EB")
    return fig

def roe_heatmap(country_product):
    z = country_product.values
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=country_product.columns,
        y=country_product.index,
        zmin=0,
        zmax=1,
        colorscale=[
            [0.0, BAD],
            [0.20, BAD],
            [0.40, LIGHT_BAD],
            [0.60, LIGHT_GOOD],
            [0.80, "#7BCB84"],
            [1.0, GOOD],
        ],
        colorbar=dict(title="Tx RoE", tickformat=".0%"),
        text=np.vectorize(lambda v: "" if pd.isna(v) else f"{v*100:.0f}%")(z),
        texttemplate="%{text}",
        hovertemplate="Country: %{y}<br>Product: %{x}<br>Tx RoE: %{z:.1%}<extra></extra>",
    ))
    fig_layout(fig, "Country × Product Tx RoE Heatmap", height=460)
    return fig

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("### EC-AI Banking Engine")
    st.caption("v0.4.1")
    use_sample = st.toggle("Use sample banking dataset", value=True)
    uploaded = st.file_uploader("Upload banking data", type=["csv", "xlsx"])
    st.markdown("---")
    st.markdown("**Thresholds**")
    low_nim = st.number_input("Low NIM threshold (bps)", value=LOW_NIM_THRESHOLD_BPS)
    roe_threshold = st.number_input("Tx RoE hurdle (%)", value=15.0) / 100

LOW_NIM_THRESHOLD_BPS = low_nim
TX_ROE_THRESHOLD = roe_threshold

# -----------------------------
# Load data
# -----------------------------
if uploaded is not None:
    if uploaded.name.lower().endswith(".xlsx"):
        raw = pd.read_excel(uploaded)
    else:
        raw = pd.read_csv(uploaded)
elif use_sample:
    raw = generate_sample_data()
else:
    raw = None

# -----------------------------
# Hero
# -----------------------------
st.markdown(
    """
<div class="ec-hero">
    <div class="ec-kicker">EC-AI Banking Engine v0.4.1</div>
    <div class="ec-hero-title">Executive Banking Intelligence OS</div>
    <div class="ec-hero-subtitle">Revenue · NIM · Tx RoE · Capital Efficiency · Country Portfolio · Balance Sheet Intelligence</div>
</div>
""",
    unsafe_allow_html=True,
)

if raw is None:
    st.info("Upload banking data or switch on the sample dataset in the sidebar.")
    st.stop()

df = ensure_metrics(raw)
summary = portfolio_summary(df)

# -----------------------------
# Executive snapshot
# -----------------------------
st.markdown('<div class="ec-section-title">Executive Snapshot</div>', unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    kpi_card("Total Revenue", money(summary["total_rev"]), "Portfolio income")
with k2:
    kpi_card("Lending Drawn", money(summary["total_drawn"]), "Balance sheet deployed")
with k3:
    kpi_card("Tx RoE", pct(summary["tx_roe"]), "NIAT / RWA")
with k4:
    kpi_card("Hurdle Pass", pct(summary["hurdle_pass"]), "Deals ≥ hurdle")
with k5:
    kpi_card("Low NIM Exposure", money(summary["low_nim_exposure"]), "< 30bps exposure")

st.markdown("<br>", unsafe_allow_html=True)

tabs = st.tabs([
    "CEO Dashboard",
    "Revenue Engine",
    "Pricing & NIM Risk",
    "Capital Efficiency",
    "Country Portfolio",
    "Balance Sheet",
    "Portfolio Data",
])

# -----------------------------
# CEO Dashboard
# -----------------------------
with tabs[0]:
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown('<div class="ec-section-title">Management Diagnosis</div>', unsafe_allow_html=True)
        lines, actions = management_summary(df)
        st.markdown("**What matters now**")
        for line in lines:
            st.markdown(f"- {line}")
        st.markdown("**Recommended management actions**")
        for action in actions:
            st.markdown(f"- {action}")
    with right:
        st.markdown('<div class="ec-section-title">Portfolio Health Mix</div>', unsafe_allow_html=True)
        health = df["Watchlist_Flag"].value_counts().reset_index()
        health.columns = ["Flag", "Count"]
        fig = px.bar(health, x="Flag", y="Count", color="Flag",
                     color_discrete_map={"Healthy": GOOD, "Monitor": "#F59E0B", "Weak": "#EA580C", "Critical": BAD, "Review": BLUE_GREY})
        fig_layout(fig, "Deal Health Classification", height=360)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="ec-section-title">Country × Product Performance Heatmap</div>', unsafe_allow_html=True)
    cp = df.pivot_table(index="Country", columns="Product", values="Tx_RoE", aggfunc="mean")
    st.plotly_chart(roe_heatmap(cp), use_container_width=True)

# -----------------------------
# Revenue Engine
# -----------------------------
with tabs[1]:
    c1, c2 = st.columns(2)
    country = grouped_view(df, ["Country"]).head(12)
    product = grouped_view(df, ["Product"]).head(12)

    with c1:
        fig = px.bar(country, x="Country", y="Total_Revenue", color_discrete_sequence=[NAVY])
        fig_layout(fig, "Revenue by Country", height=380)
        fig.update_yaxes(tickformat=",.2s", title=None)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(product, x="Product", y="Total_Revenue", color_discrete_sequence=[BLUE_GREY])
        fig_layout(fig, "Revenue by Product", height=380)
        fig.update_yaxes(tickformat=",.2s", title=None)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="ec-section-title">Top Revenue Contributors</div>', unsafe_allow_html=True)
    client = grouped_view(df, ["Client"]).head(15)
    display_table(client[["Client", "Total_Revenue", "Lending_Drawn", "RWA", "NIAT", "Tx_RoE", "NIM_bps"]])

# -----------------------------
# Pricing & NIM Risk
# -----------------------------
with tabs[2]:
    st.markdown('<div class="ec-section-title">Low NIM Watchlist</div>', unsafe_allow_html=True)
    low = df[df["Low_NIM_Flag"]].sort_values(["Lending_Drawn", "NIM_bps"], ascending=[False, True]).head(25)
    display_table(low[["Deal_ID", "Client", "Country", "Product", "Lending_Drawn", "Total_Revenue", "NIM_bps", "Tx_RoE", "Status"]])

    c1, c2 = st.columns(2)
    with c1:
        nim_country = grouped_view(df, ["Country"]).sort_values("NIM_bps")
        fig = px.bar(nim_country, x="Country", y="NIM_bps", color_discrete_sequence=[NAVY])
        fig.add_hline(y=LOW_NIM_THRESHOLD_BPS, line_dash="dash", line_color=BAD, annotation_text="Low NIM threshold")
        fig_layout(fig, "Weighted NIM by Country", height=380)
        fig.update_yaxes(title="NIM (bps)")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        nim_prod = grouped_view(df, ["Product"]).sort_values("NIM_bps")
        fig = px.bar(nim_prod, x="Product", y="NIM_bps", color_discrete_sequence=[BLUE_GREY])
        fig.add_hline(y=LOW_NIM_THRESHOLD_BPS, line_dash="dash", line_color=BAD, annotation_text="Low NIM threshold")
        fig_layout(fig, "Weighted NIM by Product", height=380)
        fig.update_yaxes(title="NIM (bps)")
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Capital Efficiency
# -----------------------------
with tabs[3]:
    st.markdown('<div class="ec-section-title">Capital Allocation Quadrant</div>', unsafe_allow_html=True)
    scatter = df.copy()
    scatter["Revenue_Size"] = scatter["Total_Revenue"].clip(lower=1)
    fig = px.scatter(
        scatter,
        x="Lending_Drawn",
        y="Tx_RoE",
        size="Revenue_Size",
        color="Country",
        hover_name="Client",
        hover_data=["Product", "NIM_bps", "RWA", "Total_Revenue", "Status"],
        color_discrete_sequence=[NAVY, TEAL, BLUE_GREY, "#2563EB", "#64748B", "#0891B2", "#334155", "#0E7490"],
    )
    fig.add_hline(y=TX_ROE_THRESHOLD, line_dash="dash", line_color=BAD, annotation_text="15% Tx RoE hurdle")
    fig.add_vline(x=df["Lending_Drawn"].median(), line_dash="dot", line_color=BLUE_GREY, annotation_text="Median exposure")
    fig_layout(fig, "Tx RoE vs Exposure Allocation", height=500)
    fig.update_yaxes(tickformat=".0%", title="Tx RoE")
    fig.update_xaxes(tickformat=",.2s", title="Lending Drawn")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="ec-section-title">Management Watchlist</div>', unsafe_allow_html=True)
    watch = df[(df["Tx_RoE"] < TX_ROE_THRESHOLD) | (df["Low_NIM_Flag"])].sort_values(["Watchlist_Flag", "Lending_Drawn"], ascending=[True, False]).head(30)
    display_table(watch[["Watchlist_Flag", "Deal_ID", "Client", "Country", "Product", "Lending_Drawn", "RWA", "Total_Revenue", "NIAT", "Tx_RoE", "NIM_bps", "Status"]])

# -----------------------------
# Country Portfolio
# -----------------------------
with tabs[4]:
    st.markdown('<div class="ec-section-title">Country Portfolio Cockpit</div>', unsafe_allow_html=True)
    country = grouped_view(df, ["Country"])
    display_table(country[["Country", "Total_Revenue", "Lending_Drawn", "Deposit_Balance", "RWA", "NIAT", "Tx_RoE", "NIM_bps", "Above_Hurdle_Flag", "Low_NIM_Flag", "Deposit_to_Lending"]])

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(country.sort_values("Tx_RoE"), x="Country", y="Tx_RoE", color_discrete_sequence=[NAVY])
        fig.add_hline(y=TX_ROE_THRESHOLD, line_dash="dash", line_color=BAD, annotation_text="Hurdle")
        fig_layout(fig, "Tx RoE by Country", height=400)
        fig.update_yaxes(tickformat=".0%", title="Tx RoE")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.scatter(country, x="Lending_Drawn", y="Total_Revenue", size="RWA", color="Country",
                         color_discrete_sequence=[NAVY, TEAL, BLUE_GREY, "#2563EB", "#64748B", "#0891B2", "#334155", "#0E7490"])
        fig_layout(fig, "Country Revenue vs Lending", height=400)
        fig.update_xaxes(tickformat=",.2s")
        fig.update_yaxes(tickformat=",.2s")
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Balance Sheet
# -----------------------------
with tabs[5]:
    st.markdown('<div class="ec-section-title">Balance Sheet & Deposit Support</div>', unsafe_allow_html=True)
    country = grouped_view(df, ["Country"])
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(country, x="Country", y=["Lending_Drawn", "Deposit_Balance"], barmode="group",
                     color_discrete_sequence=[NAVY, TEAL])
        fig_layout(fig, "Lending vs Deposit Balance by Country", height=420)
        fig.update_yaxes(tickformat=",.2s")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(country.sort_values("Deposit_to_Lending"), x="Country", y="Deposit_to_Lending",
                     color_discrete_sequence=[BLUE_GREY])
        fig.add_hline(y=DFR_TARGET, line_dash="dash", line_color=BAD, annotation_text="DFR reference")
        fig_layout(fig, "Deposit-to-Lending Ratio by Country", height=420)
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    display_table(country[["Country", "Lending_Drawn", "Deposit_Balance", "Deposit_to_Lending", "Total_Revenue", "Tx_RoE"]])

# -----------------------------
# Portfolio Data
# -----------------------------
with tabs[6]:
    st.markdown('<div class="ec-section-title">Portfolio Data</div>', unsafe_allow_html=True)
    st.caption("Raw data with EC-AI derived fields. Use this to validate flags and calculations.")
    display_table(df)
