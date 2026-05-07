import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# EC-AI Banking Engine v0.4
# Institutional Decision Intelligence Architecture
# =====================================================

st.set_page_config(
    page_title="EC-AI Banking Engine v0.4",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LOW_NIM_THRESHOLD_BPS = 30
TX_ROE_THRESHOLD = 0.15
CRITICAL_TX_ROE = 0.05
WEAK_TX_ROE = 0.10
DFR_TARGET = 0.55

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


def pct_raw(x):
    try:
        if pd.isna(x):
            return "-"
        return f"{float(x):.1f}%"
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


def generate_sample_data(n=180, seed=42):
    rng = np.random.default_rng(seed)
    countries = ["Hong Kong", "Singapore", "Korea", "Taiwan", "Japan", "Australia", "India", "Indonesia"]
    rms = ["RM A", "RM B", "RM C", "RM D", "RM E", "RM F"]
    products = ["Term Loan", "Revolver", "Trade Finance", "Guarantee", "Deposit", "FX", "Bond", "Distribution"]
    segments = ["Local Corp", "FI", "GSB", "AIBD"]
    facility_types = ["Term Loan", "Revolver (C)", "Revolver (U)", "Committed LC", "Uncommitted LC"]
    deal_types = ["New", "Refinance", "Renewal"]
    priority = ["Priority", "Core+", "Core-", "Non-Priority"]
    rows = []
    for i in range(n):
        country = rng.choice(countries, p=[.18,.14,.14,.12,.10,.12,.12,.08])
        product = rng.choice(products, p=[.22,.20,.16,.12,.08,.08,.08,.06])
        segment = rng.choice(segments, p=[.48,.24,.18,.10])
        drawn = float(rng.uniform(20, 650) * 1_000_000)
        if product in ["Deposit", "FX"]:
            drawn *= rng.uniform(.15, .55)
        rwa = drawn * rng.uniform(.25, .95)
        # Mix strong and weak returns; some above 15% hurdle by design
        target_roe = rng.choice([rng.uniform(.04,.10), rng.uniform(.10,.15), rng.uniform(.15,.24), rng.uniform(.24,.45)], p=[.22,.28,.35,.15])
        niat = rwa * target_roe
        revenue = niat / rng.uniform(.18,.45)
        nim = rng.choice([rng.uniform(12,29), rng.uniform(30,70), rng.uniform(70,130)], p=[.25,.45,.30])
        dep_ratio = rng.choice([rng.uniform(.05,.25), rng.uniform(.25,.65), rng.uniform(.65,1.6)], p=[.35,.45,.20])
        deposit = drawn * dep_ratio
        approved_amount = drawn * rng.uniform(1.0, 1.8)
        hereafter_groe = target_roe + rng.normal(.015, .035)
        rows.append({
            "Deal_ID": f"DEAL-{2000+i}",
            "Client": rng.choice(["Sample Financial Holdings", "Sample Infrastructure Co", "Sample Logistics Co", "Sample Property Group", "Sample Healthcare Group", "Sample Telecom Group", "Sample Energy Corp", "Sample Manufacturing Ltd", "Sample Retail Ltd"]),
            "Country": country,
            "RM": rng.choice(rms),
            "Product": product,
            "Segment": segment,
            "Facility_Type": rng.choice(facility_types),
            "Deal_Type": rng.choice(deal_types, p=[.48,.32,.20]),
            "Priority_Segment": rng.choice(priority, p=[.25,.35,.25,.15]),
            "Lending_Drawn": drawn,
            "Approved_Amount": approved_amount,
            "RWA": rwa,
            "Total_Revenue": revenue,
            "NIAT": niat,
            "Deposit_Balance": deposit,
            "NIM_bps": nim,
            "Hereafter_GRoE": max(hereafter_groe, 0),
            "Distribution_Amount": approved_amount * rng.uniform(.05,.75),
            "Committed_Flag": rng.choice(["Committed", "Uncommitted"], p=[.62,.38]),
            "Month": rng.choice(["Oct-25", "Nov-25", "Dec-25", "Jan-26", "Feb-26", "Mar-26"]),
        })
    return pd.DataFrame(rows)


def ensure_metrics(df):
    df = normalize_columns(df)
    colmap = {
        "Client": find_col(df, ["Client", "Customer", "Customer_Name", "Borrower", "Client_Name", "Relationship_Name"]),
        "Country": find_col(df, ["Country", "Booking_Country", "Region", "Office", "BP_Country", "GRM_Country"]),
        "RM": find_col(df, ["RM", "Relationship_Manager", "RM_Name", "Owner"]),
        "Product": find_col(df, ["Product", "Facility_Type", "Deal_Type", "Product_Type"]),
        "Segment": find_col(df, ["Segment", "Parent_Segment", "Business_Line"]),
        "Facility_Type": find_col(df, ["Facility_Type", "Credit_Facility_Type", "Facility"]),
        "Deal_Type": find_col(df, ["Deal_Type", "Transaction_Type", "New_Refinance_Renewal"]),
        "Priority_Segment": find_col(df, ["Priority_Segment", "Sector_Priority", "Priority"]),
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
    defaults = {
        "RM": "RM Unknown", "Segment": "Unknown", "Facility_Type": df["Product"] if "Product" in df.columns else "Unknown",
        "Deal_Type": "Unknown", "Priority_Segment": "Core", "Deposit_Balance": 0,
        "Approved_Amount": df["Lending_Drawn"] if "Lending_Drawn" in df.columns else 0,
        "Distribution_Amount": 0, "Committed_Flag": "Unknown", "Month": "Current"
    }
    for c, v in defaults.items():
        if c not in df.columns:
            df[c] = v
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

    df["Tx_RoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    if "Hereafter_GRoE" not in df.columns or df["Hereafter_GRoE"].sum() == 0:
        df["Hereafter_GRoE"] = df["Tx_RoE"] + 0.015
    df["Revenue_per_RWA"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    df["Deposit_to_Lending"] = df.apply(lambda r: safe_div(r["Deposit_Balance"], r["Lending_Drawn"]), axis=1)
    df["Distribution_Ratio"] = df.apply(lambda r: safe_div(r["Distribution_Amount"], r["Approved_Amount"]), axis=1)
    df["Low_NIM_Flag"] = df["NIM_bps"] < LOW_NIM_THRESHOLD_BPS
    df["Low_Tx_RoE_Flag"] = df["Tx_RoE"] < TX_ROE_THRESHOLD
    df["Above_Hurdle_Flag"] = df["Tx_RoE"] >= TX_ROE_THRESHOLD
    df["GRoE_Above_Hurdle_Flag"] = df["Hereafter_GRoE"] >= TX_ROE_THRESHOLD

    def classify(row):
        if row["Low_NIM_Flag"] and row["Low_Tx_RoE_Flag"]:
            return "🔴 Critical: Low NIM + Low Tx RoE"
        if row["Low_NIM_Flag"]:
            return "🟠 Low NIM: Reprice / Sell-down"
        if row["Low_Tx_RoE_Flag"]:
            return "🟡 Low Tx RoE: Improve return"
        if row["Deposit_Balance"] > row["Lending_Drawn"] and row["Total_Revenue"] > 0:
            return "🟢 Deposit rich / Cross-sell"
        return "🟢 Value creator"

    def watch_flag(row):
        tx = row["Tx_RoE"]
        if pd.isna(tx):
            return "⚪ Review"
        if tx < CRITICAL_TX_ROE:
            return "🔴 Critical"
        if tx < WEAK_TX_ROE:
            return "🟠 Weak"
        if tx < TX_ROE_THRESHOLD:
            return "🟡 Monitor"
        return "🟢 Healthy"

    df["Status"] = df.apply(classify, axis=1)
    df["Watchlist_Flag"] = df.apply(watch_flag, axis=1)
    return df


def grouped_view(df, group_cols):
    if df.empty:
        return pd.DataFrame(columns=group_cols)
    g = df.groupby(group_cols, dropna=False).agg({
        "Total_Revenue": "sum", "Lending_Drawn": "sum", "Approved_Amount": "sum", "Deposit_Balance": "sum",
        "RWA": "sum", "NIAT": "sum", "Distribution_Amount": "sum", "Low_NIM_Flag": "sum",
        "Low_Tx_RoE_Flag": "sum", "Above_Hurdle_Flag": "sum", "GRoE_Above_Hurdle_Flag": "sum", "Deal_ID": "count"
    }).reset_index().rename(columns={"Deal_ID":"Deal_Count"})
    nim_rows = []
    for _, x in df.groupby(group_cols, dropna=False):
        nim_rows.append(safe_div((x["NIM_bps"] * x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum()))
    g["NIM_bps"] = nim_rows
    g["Tx_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Hereafter_GRoE"] = g.apply(lambda r: safe_div((df.loc[df[group_cols[0]] == r[group_cols[0]], "Hereafter_GRoE"] * df.loc[df[group_cols[0]] == r[group_cols[0]], "Approved_Amount"]).sum(), df.loc[df[group_cols[0]] == r[group_cols[0]], "Approved_Amount"].sum()) if len(group_cols)==1 else np.nan, axis=1)
    g["Revenue_per_RWA"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    g["Deposit_to_Lending"] = g.apply(lambda r: safe_div(r["Deposit_Balance"], r["Lending_Drawn"]), axis=1)
    g["Distribution_Ratio"] = g.apply(lambda r: safe_div(r["Distribution_Amount"], r["Approved_Amount"]), axis=1)
    g["Hurdle_Pass_Rate"] = g.apply(lambda r: safe_div(r["Above_Hurdle_Flag"], r["Deal_Count"]), axis=1)
    return g.sort_values("Total_Revenue", ascending=False)


def build_watchlist(df):
    exposure_threshold = df["Lending_Drawn"].quantile(0.60) if len(df) else 0
    w = df[(df["Tx_RoE"] < TX_ROE_THRESHOLD) & (df["Lending_Drawn"] >= exposure_threshold)].copy()
    if w.empty:
        w = df[df["Tx_RoE"] < TX_ROE_THRESHOLD].copy()
    return w.sort_values(["Tx_RoE", "Lending_Drawn"], ascending=[True, False])


def format_table(df):
    out = df.copy()
    for c in ["Total_Revenue", "Lending_Drawn", "Approved_Amount", "Deposit_Balance", "RWA", "NIAT", "Distribution_Amount"]:
        if c in out.columns:
            out[c] = out[c].apply(money)
    for c in ["Tx_RoE", "Hereafter_GRoE", "Revenue_per_RWA", "Deposit_to_Lending", "Distribution_Ratio", "Hurdle_Pass_Rate"]:
        if c in out.columns:
            out[c] = out[c].apply(pct)
    if "NIM_bps" in out.columns:
        out["NIM_bps"] = out["NIM_bps"].apply(bps)
    return out


def executive_signals(df):
    total_rev = df["Total_Revenue"].sum()
    total_drawn = df["Lending_Drawn"].sum()
    total_rwa = df["RWA"].sum()
    total_niat = df["NIAT"].sum()
    tx_roe = safe_div(total_niat, total_rwa)
    low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()
    low_nim_share = safe_div(low_nim_exposure, total_drawn)
    pass_rate = safe_div(df["Above_Hurdle_Flag"].sum(), len(df))
    dfr = safe_div(df["Deposit_Balance"].sum(), total_drawn)
    top_country = grouped_view(df, ["Country"]).iloc[0]["Country"]
    top_product = grouped_view(df, ["Product"]).iloc[0]["Product"]
    return [
        ("Portfolio health", f"Tx RoE is {pct(tx_roe)} with hurdle pass rate of {pct(pass_rate)}. Management should separate value creators from capital-heavy underperformers."),
        ("Revenue engine", f"Total revenue is {money(total_rev)}, led by {top_country} and {top_product}."),
        ("Pricing pressure", f"Low-NIM exposure is {money(low_nim_exposure)}, representing {pct(low_nim_share)} of lending drawn."),
        ("Balance sheet discipline", f"Deposit funding ratio is {pct(dfr)} versus indicative target of {pct(DFR_TARGET)}."),
    ]

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.main {background:#ffffff;}
.hero {padding: 34px 34px; border-radius: 18px; background: linear-gradient(110deg, #101d34 0%, #102946 52%, #0f766e 100%); color: white; margin-bottom: 24px; box-shadow: 0 10px 28px rgba(15, 29, 52, 0.12);} 
.hero h1 {font-size: 36px; margin:0; color:white; font-weight:800;}
.hero p {font-size: 16px; margin-top:20px; color:#f8fafc;}
.metric-card {background:#fff; border:1px solid #e2e8f0; border-radius:16px; padding:20px 18px; box-shadow:0 6px 18px rgba(15,23,42,0.04); min-height:115px;}
.metric-label {font-size:13px; color:#64748b; margin-bottom:10px;}
.metric-value {font-size:28px; font-weight:800; color:#0f172a;}
.metric-note {font-size:12px; color:#64748b; margin-top:8px;}
.diag-card {border-radius:14px; padding:16px 18px; margin-bottom:14px; background:#f8fafc; border-left:5px solid #0f766e; font-size:15px; line-height:1.65;}
.diag-risk {border-left-color:#dc2626; background:#fff7ed;}
.section-title {font-size:28px; font-weight:800; color:#0f172a; margin-top:18px; margin-bottom:14px;}
.module-card {border:1px solid #e2e8f0; border-radius:14px; padding:15px; background:#fbfdff; min-height:110px;}
/* make Streamlit tabs easier to navigate */
button[data-baseweb="tab"] {font-size:16px !important; font-weight:700 !important; padding:14px 18px !important; border-radius:12px 12px 0 0 !important;}
button[data-baseweb="tab"][aria-selected="true"] {color:#dc2626 !important; border-bottom:3px solid #dc2626 !important; background:#fff7f7 !important;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header and data load
# -----------------------------
st.markdown("""
<div class="hero">
  <h1>EC-AI Banking Engine v0.4</h1>
  <p>Institutional Decision Intelligence for Tx RoE / NIM / Revenue / Exposure / Balance Sheet / Distribution</p>
</div>
""", unsafe_allow_html=True)

upload_col, option_col = st.columns([2,1])
with upload_col:
    uploaded = st.file_uploader("Upload banking performance CSV", type=["csv"])
with option_col:
    use_sample = st.toggle("Use EC-AI sample banking data", value=(uploaded is None))

if uploaded is not None:
    raw = pd.read_csv(uploaded)
elif use_sample:
    raw = generate_sample_data()
else:
    st.info("Upload a CSV or switch on sample data. Core columns: Client, Country, Product, Lending_Drawn, RWA, Total_Revenue, NIAT. Optional: RM, Segment, Facility_Type, Deal_Type, Deposit_Balance, NIM_bps, Approved_Amount, Hereafter_GRoE, Distribution_Amount.")
    st.stop()

df = ensure_metrics(raw)

# Executive snapshot
total_revenue = df["Total_Revenue"].sum()
total_drawn = df["Lending_Drawn"].sum()
total_deposit = df["Deposit_Balance"].sum()
total_rwa = df["RWA"].sum()
total_niat = df["NIAT"].sum()
portfolio_tx_roe = safe_div(total_niat, total_rwa)
low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()
low_nim_share = safe_div(low_nim_exposure, total_drawn)
hurdle_pass = safe_div(df["Above_Hurdle_Flag"].sum(), len(df))
dfr = safe_div(total_deposit, total_drawn)

st.markdown('<div class="section-title">Executive Snapshot</div>', unsafe_allow_html=True)
c1,c2,c3,c4,c5,c6 = st.columns(6)
for col, label, value, note in [
    (c1,"Total Revenue",money(total_revenue),"Revenue pool"),
    (c2,"Lending Drawn",money(total_drawn),"Drawn exposure"),
    (c3,"Deposit Balance",money(total_deposit),"Funding support"),
    (c4,"Tx RoE",pct(portfolio_tx_roe),f"Target {pct(TX_ROE_THRESHOLD)}"),
    (c5,"Hurdle Pass",pct(hurdle_pass),"Deal quality"),
    (c6,"Low NIM Exposure",money(low_nim_exposure),f"{pct(low_nim_share)} of drawn"),
]:
    col.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>", unsafe_allow_html=True)

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Executive Command", "Deal Intelligence", "Revenue Engine", "Pricing & NIM", "Capital & RWA", "Balance Sheet", "Portfolio Data"
])

with tab1:
    st.subheader("Management Diagnosis")
    l,r = st.columns(2)
    for i,(title,text) in enumerate(executive_signals(df)):
        target = l if i in [0,1] else r
        risk_class = " diag-risk" if title in ["Pricing pressure", "Balance sheet discipline"] else ""
        target.markdown(f"<div class='diag-card{risk_class}'><b>{title}:</b> {text}</div>", unsafe_allow_html=True)

    st.markdown("### Executive Command Center")
    k1,k2,k3 = st.columns(3)
    country = grouped_view(df,["Country"])
    seg = grouped_view(df,["Segment"])
    product = grouped_view(df,["Product"])
    fig1 = px.bar(country.sort_values("Total_Revenue", ascending=False).head(8), x="Country", y="Total_Revenue", title="Revenue by Country", text_auto=".2s")
    fig1.update_layout(height=360, margin=dict(l=10,r=10,t=50,b=20))
    k1.plotly_chart(fig1, use_container_width=True)
    fig2 = px.bar(seg.sort_values("Tx_RoE", ascending=False), x="Segment", y="Tx_RoE", title="Tx RoE by Segment", text_auto=".1%")
    fig2.add_hline(y=TX_ROE_THRESHOLD, line_dash="dash", annotation_text="15%")
    fig2.update_yaxes(tickformat=".0%")
    fig2.update_layout(height=360, margin=dict(l=10,r=10,t=50,b=20))
    k2.plotly_chart(fig2, use_container_width=True)
    fig3 = px.bar(product.sort_values("Hurdle_Pass_Rate", ascending=True), x="Product", y="Hurdle_Pass_Rate", title="Hurdle Pass Rate by Product", text_auto=".0%")
    fig3.update_yaxes(tickformat=".0%")
    fig3.update_layout(height=360, margin=dict(l=10,r=10,t=50,b=20))
    k3.plotly_chart(fig3, use_container_width=True)

    st.markdown("### Management Watchlist")
    watch_cols = ["Watchlist_Flag","Deal_ID","Client","Country","RM","Product","Segment","Lending_Drawn","RWA","Total_Revenue","Tx_RoE","Hereafter_GRoE","NIM_bps","Status"]
    st.dataframe(format_table(build_watchlist(df)[watch_cols].head(25)), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Deal Intelligence Engine")
    st.caption("Quality of approved business: hurdle pass, committed/uncommitted mix, facility type, tenor/product economics and management actions.")
    a,b = st.columns([1.2,1])
    scatter = df.copy()
    scatter["Tx_RoE_pct"] = scatter["Tx_RoE"]*100
    fig = px.scatter(scatter, x="Approved_Amount", y="Tx_RoE_pct", size="Lending_Drawn", color="Status", hover_name="Client", hover_data=["Country","RM","Product","Facility_Type","Deal_Type","NIM_bps"], title="Approved Amount vs Tx RoE")
    fig.add_hline(y=TX_ROE_THRESHOLD*100, line_dash="dash", annotation_text="15% hurdle")
    fig.update_layout(height=480, margin=dict(l=10,r=10,t=55,b=20))
    a.plotly_chart(fig, use_container_width=True)
    deal_mix = grouped_view(df,["Deal_Type"])
    fig_mix = px.bar(deal_mix, x="Deal_Type", y="Approved_Amount", color="Deal_Type", title="Approved Amount by Deal Type", text_auto=".2s")
    fig_mix.update_layout(height=480, margin=dict(l=10,r=10,t=55,b=20), showlegend=False)
    b.plotly_chart(fig_mix, use_container_width=True)

    st.markdown("### Hurdle / Quality Matrix")
    matrix = grouped_view(df,["Country","Segment"])
    matrix["Hurdle_Pass_Rate_Display"] = matrix["Hurdle_Pass_Rate"]*100
    fig_hm = px.density_heatmap(matrix, x="Segment", y="Country", z="Hurdle_Pass_Rate_Display", histfunc="avg", text_auto=".1f", title="Hurdle Pass Rate Heatmap (%)")
    fig_hm.update_layout(height=460, margin=dict(l=10,r=10,t=55,b=20))
    st.plotly_chart(fig_hm, use_container_width=True)

with tab3:
    st.subheader("Revenue Engine")
    c1,c2 = st.columns(2)
    country = grouped_view(df,["Country"])
    product = grouped_view(df,["Product"])
    fig_country = px.bar(country, x="Country", y="Total_Revenue", title="Revenue by Country", text_auto=".2s")
    fig_country.update_layout(height=420, margin=dict(l=10,r=10,t=55,b=20))
    c1.plotly_chart(fig_country, use_container_width=True)
    fig_product = px.bar(product, x="Product", y="Total_Revenue", title="Revenue by Product", text_auto=".2s")
    fig_product.update_layout(height=420, margin=dict(l=10,r=10,t=55,b=20))
    c2.plotly_chart(fig_product, use_container_width=True)
    st.markdown("### Country / RM Revenue Table")
    st.dataframe(format_table(grouped_view(df,["Country","RM"])), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Pricing & NIM Risk")
    low = df[df["Low_NIM_Flag"]].sort_values("Lending_Drawn", ascending=False).copy()
    st.markdown(f"Low-NIM rule: **NIM < {LOW_NIM_THRESHOLD_BPS} bps**")
    pc1, pc2 = st.columns(2)
    nim_country = grouped_view(low if not low.empty else df,["Country"])
    fig_nim = px.bar(nim_country, x="Country", y="Lending_Drawn", title="Low-NIM Exposure by Country", text_auto=".2s")
    fig_nim.update_layout(height=420, margin=dict(l=10,r=10,t=55,b=20))
    pc1.plotly_chart(fig_nim, use_container_width=True)
    bucket_df = df.copy()
    bucket_df["NIM_Bucket"] = pd.cut(bucket_df["NIM_bps"], bins=[-999,30,60,100,999], labels=["<30 bps","30-60 bps","60-100 bps",">100 bps"])
    bucket = bucket_df.groupby("NIM_Bucket", dropna=False)["Lending_Drawn"].sum().reset_index()
    fig_bucket = px.bar(bucket, x="NIM_Bucket", y="Lending_Drawn", title="NIM Bucket by Exposure", text_auto=".2s")
    fig_bucket.update_layout(height=420, margin=dict(l=10,r=10,t=55,b=20))
    pc2.plotly_chart(fig_bucket, use_container_width=True)
    st.markdown("### Low-NIM Deal List")
    cols = ["Deal_ID","Client","Country","RM","Product","Facility_Type","Lending_Drawn","Total_Revenue","NIM_bps","Tx_RoE","Status"]
    st.dataframe(format_table(low[cols].head(50)), use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Capital & RWA Intelligence")
    client = grouped_view(df,["Client"])
    client["Client_Flag"] = client.apply(lambda r: "Low Return" if r["Tx_RoE"] < TX_ROE_THRESHOLD else "Above Hurdle", axis=1)
    fig_cap = px.scatter(client, x="RWA", y="Tx_RoE", size="Total_Revenue", color="Client_Flag", hover_name="Client", title="Client Capital Efficiency: Tx RoE vs RWA", labels={"Tx_RoE":"Tx RoE", "RWA":"RWA"})
    fig_cap.add_hline(y=TX_ROE_THRESHOLD, line_dash="dash", annotation_text="15% threshold")
    fig_cap.update_yaxes(tickformat=".0%")
    fig_cap.update_layout(height=520, margin=dict(l=20,r=20,t=65,b=30))
    st.plotly_chart(fig_cap, use_container_width=True)
    st.markdown("### Client Profitability Table")
    st.dataframe(format_table(client.sort_values("Tx_RoE", ascending=True)), use_container_width=True, hide_index=True)

with tab6:
    st.subheader("Balance Sheet Intelligence")
    dep_country = grouped_view(df,["Country"])
    fig_dep = go.Figure()
    fig_dep.add_bar(x=dep_country["Country"], y=dep_country["Lending_Drawn"], name="Lending Drawn")
    fig_dep.add_bar(x=dep_country["Country"], y=dep_country["Deposit_Balance"], name="Deposit Balance")
    fig_dep.update_layout(barmode="group", title="Lending vs Deposit Balance by Country", height=440, margin=dict(l=10,r=10,t=55,b=20))
    st.plotly_chart(fig_dep, use_container_width=True)
    dep_country["DFR_Status"] = np.where(dep_country["Deposit_to_Lending"] >= DFR_TARGET, "On / Above Target", "Below Target")
    fig_dfr = px.bar(dep_country.sort_values("Deposit_to_Lending"), x="Country", y="Deposit_to_Lending", color="DFR_Status", title="Deposit Funding Ratio by Country", text_auto=".0%")
    fig_dfr.add_hline(y=DFR_TARGET, line_dash="dash", annotation_text="Indicative DFR target")
    fig_dfr.update_yaxes(tickformat=".0%")
    fig_dfr.update_layout(height=420, margin=dict(l=10,r=10,t=55,b=20))
    st.plotly_chart(fig_dfr, use_container_width=True)
    st.markdown("### Deposit Support View")
    dep_cols = ["Country","RM","Total_Revenue","Lending_Drawn","Deposit_Balance","Deposit_to_Lending","Tx_RoE"]
    st.dataframe(format_table(grouped_view(df,["Country","RM"])[dep_cols]), use_container_width=True, hide_index=True)

with tab7:
    st.subheader("Portfolio Data")
    view_cols = ["Deal_ID","Client","Country","RM","Segment","Product","Facility_Type","Deal_Type","Priority_Segment","Committed_Flag","Lending_Drawn","Approved_Amount","Deposit_Balance","RWA","Total_Revenue","NIAT","NIM_bps","Tx_RoE","Hereafter_GRoE","Revenue_per_RWA","Deposit_to_Lending","Distribution_Ratio","Status"]
    available_cols = [c for c in view_cols if c in df.columns]
    st.dataframe(format_table(df[available_cols]), use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download enriched CSV", data=csv, file_name="ecai_banking_engine_v0_4_enriched.csv", mime="text/csv")
