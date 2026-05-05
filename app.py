import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =============================
# EC-AI Insight Platform v0.2
# Banking focus: Tx RoE / NIM / Revenue / Exposure / Deposit intelligence
# =============================

st.set_page_config(page_title="EC-AI Insight Platform v0.2", layout="wide")

LOW_NIM_THRESHOLD_BPS = 30
TX_ROE_THRESHOLD = 0.15

# ---------- Styling ----------
st.markdown("""
<style>
    .main .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1500px;}
    h1, h2, h3 {letter-spacing: -0.02em;}
    .ecai-hero {
        padding: 24px 28px; border-radius: 18px;
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 72%, #0f766e 100%);
        color: white; margin-bottom: 18px;
    }
    .ecai-hero h1 {color: white; margin: 0; font-size: 2.1rem;}
    .ecai-hero p {color: #dbeafe; margin: 8px 0 0 0; font-size: 1.02rem;}
    .module-card {
        border: 1px solid #e5e7eb; border-radius: 18px; padding: 20px;
        background: #ffffff; box-shadow: 0 4px 18px rgba(15,23,42,0.06);
        min-height: 158px;
    }
    .module-card h3 {margin: 0 0 8px 0; color: #0f172a;}
    .module-card p {color: #475569; font-size: 0.95rem;}
    .tag {display:inline-block; padding: 4px 9px; border-radius: 999px; background:#eef2ff; color:#3730a3; font-size:0.78rem; margin-top:8px;}
    .metric-card {
        border: 1px solid #e5e7eb; border-radius: 16px; padding: 16px;
        background: #ffffff; box-shadow: 0 2px 12px rgba(15,23,42,0.04);
    }
    .metric-label {font-size: 0.82rem; color: #64748b; margin-bottom: 6px;}
    .metric-value {font-size: 1.55rem; font-weight: 650; color: #0f172a;}
    .metric-note {font-size: 0.78rem; color: #64748b; margin-top: 4px;}
    .insight-box {
        border-left: 4px solid #0f766e; background: #f8fafc; border-radius: 12px;
        padding: 14px 16px; margin-bottom: 10px; color: #0f172a;
    }
    .warning-box {
        border-left: 4px solid #dc2626; background: #fff7ed; border-radius: 12px;
        padding: 14px 16px; margin-bottom: 10px; color: #0f172a;
    }
    .small-muted {color:#64748b; font-size:0.86rem;}
</style>
""", unsafe_allow_html=True)

# ---------- Formatting ----------
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
        if pd.isna(x): return "-"
        return f"{float(x)*100:.1f}%"
    except Exception:
        return "-"

def bps(x):
    try:
        if pd.isna(x): return "-"
        return f"{float(x):,.1f} bps"
    except Exception:
        return "-"

def safe_div(a, b):
    try:
        if b == 0 or pd.isna(b):
            return np.nan
        return float(a) / float(b)
    except Exception:
        return np.nan

# ---------- Data logic ----------
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

    numeric_cols = ["Lending_Drawn", "RWA", "Total_Revenue", "NIAT", "Deposit_Balance", "NIM_bps", "Net_Interest_Income", "NOP", "GOP"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "NIM_bps" not in df.columns:
        if "Net_Interest_Income" in df.columns:
            df["NIM_bps"] = df.apply(lambda r: safe_div(r["Net_Interest_Income"], r["Lending_Drawn"]) * 10000, axis=1)
        else:
            df["NIM_bps"] = np.nan

    if "Deposit_Balance" not in df.columns:
        df["Deposit_Balance"] = 0
    if "GOP" not in df.columns:
        df["GOP"] = df["Total_Revenue"]
    if "NOP" not in df.columns:
        df["NOP"] = df["NIAT"]

    df["Tx_RoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    df["Revenue_per_RWA"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    df["Revenue_per_Lending"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["Lending_Drawn"]), axis=1)
    df["Deposit_to_Lending"] = df.apply(lambda r: safe_div(r["Deposit_Balance"], r["Lending_Drawn"]), axis=1)
    df["Low_NIM_Flag"] = df["NIM_bps"] < LOW_NIM_THRESHOLD_BPS
    df["Low_Tx_RoE_Flag"] = df["Tx_RoE"] < TX_ROE_THRESHOLD

    def classify(row):
        if row["Low_NIM_Flag"] and row["Low_Tx_RoE_Flag"]:
            return "Critical: Low NIM + Low Tx RoE"
        if row["Low_NIM_Flag"]:
            return "Low NIM: Reprice / Sell-down"
        if row["Low_Tx_RoE_Flag"]:
            return "Low Tx RoE: Improve return"
        if row["Deposit_Balance"] > row["Lending_Drawn"] and row["Total_Revenue"] > 0:
            return "Deposit Rich / Cross-sell"
        return "Value Creator"

    df["Status"] = df.apply(classify, axis=1)
    return df

def weighted_avg_nim(x):
    return safe_div((x["NIM_bps"] * x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum())

def grouped_view(df, group_cols):
    g = df.groupby(group_cols, dropna=False).agg({
        "Total_Revenue": "sum",
        "Lending_Drawn": "sum",
        "Deposit_Balance": "sum",
        "RWA": "sum",
        "NIAT": "sum",
        "GOP": "sum",
        "NOP": "sum",
        "Low_NIM_Flag": "sum",
        "Low_Tx_RoE_Flag": "sum",
    }).reset_index()
    nim = df.groupby(group_cols, dropna=False).apply(weighted_avg_nim).reset_index(name="NIM_bps")
    g = g.merge(nim, on=group_cols, how="left")
    g["Tx_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Revenue_per_RWA"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    g["Deposit_to_Lending"] = g.apply(lambda r: safe_div(r["Deposit_Balance"], r["Lending_Drawn"]), axis=1)
    return g.sort_values("Total_Revenue", ascending=False)

# ---------- UI helpers ----------
def metric_card(label, value, note=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)

def plot_bar(df, x, y, title, height=330):
    fig = px.bar(df, x=x, y=y, text_auto=False)
    fig.update_layout(
        title=title,
        height=height,
        margin=dict(l=20, r=20, t=52, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        font=dict(size=12),
    )
    fig.update_yaxes(gridcolor="#e5e7eb", zerolinecolor="#111827")
    fig.update_xaxes(tickangle=0)
    st.plotly_chart(fig, use_container_width=True)

def plot_scatter(df):
    fig = px.scatter(
        df, x="Lending_Drawn", y="Tx_RoE", size="Total_Revenue", color="Status",
        hover_data=["Client", "Country", "RM", "Product", "NIM_bps", "RWA"],
        title="Client portfolio map: exposure vs Tx RoE"
    )
    fig.add_hline(y=TX_ROE_THRESHOLD, line_dash="dash", annotation_text="15% Tx RoE threshold")
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=52, b=30), plot_bgcolor="white", paper_bgcolor="white")
    fig.update_yaxes(tickformat=".1%", gridcolor="#e5e7eb")
    st.plotly_chart(fig, use_container_width=True)

def format_table(df):
    out = df.copy()
    for c in ["Total_Revenue", "Lending_Drawn", "Deposit_Balance", "RWA", "NIAT", "GOP", "NOP"]:
        if c in out.columns:
            out[c] = out[c].apply(money)
    for c in ["Tx_RoE", "Revenue_per_RWA", "Revenue_per_Lending", "Deposit_to_Lending"]:
        if c in out.columns:
            out[c] = out[c].apply(pct)
    if "NIM_bps" in out.columns:
        out["NIM_bps"] = out["NIM_bps"].apply(bps)
    return out

# ---------- Page modules ----------
def home_page():
    st.markdown("""
    <div class="ecai-hero">
        <h1>EC-AI Insight Platform</h1>
        <p>Executive intelligence for SME performance, banking profitability, and insurance benchmarking.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="module-card">
            <h3>SME Insight</h3>
            <p>Sales, customer, channel, pricing and product performance insights for business owners.</p>
            <span class="tag">Existing MVP</span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="module-card">
            <h3>Banking Insight</h3>
            <p>Tx RoE, NIM, revenue, exposure, RWA and deposit intelligence for management reporting.</p>
            <span class="tag">v0.2 Focus</span>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="module-card">
            <h3>Insurance Benchmark</h3>
            <p>Broker-side benchmarking for benefits, insurers, premium competitiveness and client positioning.</p>
            <span class="tag">Prototype</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Founder direction")
    st.markdown("""
    <div class="insight-box">
    Keep EC-AI as one platform. Banking Insight becomes a premium module focused on management decisions, not generic dashboarding.
    </div>
    """, unsafe_allow_html=True)

def banking_page():
    global LOW_NIM_THRESHOLD_BPS, TX_ROE_THRESHOLD
    st.markdown("""
    <div class="ecai-hero">
        <h1>EC-AI Banking Insight v0.2</h1>
        <p>Tx RoE / NIM / Revenue / Exposure / Deposit intelligence for management reporting.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.sidebar.file_uploader("Upload banking performance CSV", type=["csv"])
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Thresholds**")
    low_nim = st.sidebar.number_input("Low NIM threshold (bps)", value=LOW_NIM_THRESHOLD_BPS, step=5)
    tx_roe_threshold = st.sidebar.number_input("Tx RoE threshold (%)", value=15.0, step=1.0) / 100

    LOW_NIM_THRESHOLD_BPS = low_nim
    TX_ROE_THRESHOLD = tx_roe_threshold

    if uploaded is None:
        st.info("Upload the banking CSV to begin. Required columns: Client, Country, RM, Product, Lending_Drawn, RWA, Total_Revenue, NIAT.")
        return

    df = ensure_metrics(pd.read_csv(uploaded))

    total_revenue = df["Total_Revenue"].sum()
    total_drawn = df["Lending_Drawn"].sum()
    total_deposit = df["Deposit_Balance"].sum()
    total_rwa = df["RWA"].sum()
    total_niat = df["NIAT"].sum()
    portfolio_tx_roe = safe_div(total_niat, total_rwa)
    low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()
    low_nim_share = safe_div(low_nim_exposure, total_drawn)

    st.subheader("Executive Snapshot")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: metric_card("Total Revenue", money(total_revenue), "Revenue pool")
    with c2: metric_card("Lending Drawn", money(total_drawn), "Drawn exposure")
    with c3: metric_card("Deposit Balance", money(total_deposit), "Balance sheet support")
    with c4: metric_card("Tx RoE", pct(portfolio_tx_roe), f"Target {pct(TX_ROE_THRESHOLD)}")
    with c5: metric_card("Low NIM Exposure", money(low_nim_exposure), f"{pct(low_nim_share)} of drawn")

    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Executive Summary", "Profitability", "NIM / Pricing", "Exposure & RWA", "Deposits", "Raw Data"
    ])

    with tab1:
        st.subheader("Management Diagnosis")
        top_country = grouped_view(df, ["Country"]).iloc[0]["Country"]
        top_product = grouped_view(df, ["Product"]).iloc[0]["Product"]
        top_rm = grouped_view(df, ["RM"]).iloc[0]["RM"]

        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.markdown(f"""
            <div class="insight-box"><b>Revenue engine:</b> Total revenue is {money(total_revenue)}, with strongest contribution from <b>{top_country}</b>, <b>{top_product}</b>, and <b>{top_rm}</b>.</div>
            <div class="insight-box"><b>Capital return:</b> Portfolio Tx RoE is <b>{pct(portfolio_tx_roe)}</b> versus the favourable threshold of <b>{pct(TX_ROE_THRESHOLD)}</b>.</div>
            """, unsafe_allow_html=True)
        with col_b:
            box_class = "warning-box" if low_nim_share and low_nim_share > 0.10 else "insight-box"
            st.markdown(f"""
            <div class="{box_class}"><b>Pricing pressure:</b> Low-NIM exposure is <b>{money(low_nim_exposure)}</b>, representing <b>{pct(low_nim_share)}</b> of lending drawn.</div>
            <div class="insight-box"><b>Management action:</b> Focus on high exposure / weak return clients for repricing, sell-down, restructuring, or deposit/revenue cross-sell.</div>
            """, unsafe_allow_html=True)

        left, right = st.columns(2)
        with left:
            plot_bar(grouped_view(df, ["Country"]).head(10), "Country", "Total_Revenue", "Revenue by Country")
        with right:
            plot_bar(grouped_view(df, ["Product"]).head(10), "Product", "Total_Revenue", "Revenue by Product")

    with tab2:
        st.subheader("Profitability: Tx RoE and client return")
        plot_scatter(df)
        client = grouped_view(df, ["Client", "Country", "RM"])
        cols = ["Client", "Country", "RM", "Total_Revenue", "Lending_Drawn", "RWA", "NIAT", "Tx_RoE", "NIM_bps", "Revenue_per_RWA"]
        st.dataframe(format_table(client[cols]), use_container_width=True, height=420)

    with tab3:
        st.subheader("NIM / Pricing: low NIM and repricing candidates")
        low = df[df["Low_NIM_Flag"]].sort_values(["Lending_Drawn", "Total_Revenue"], ascending=False)
        c1, c2 = st.columns(2)
        with c1:
            plot_bar(grouped_view(df, ["Product"]).sort_values("NIM_bps").head(10), "Product", "NIM_bps", "Weighted NIM by Product")
        with c2:
            plot_bar(grouped_view(df, ["Country"]).sort_values("NIM_bps").head(10), "Country", "NIM_bps", "Weighted NIM by Country")
        st.markdown("#### Low-NIM deal list")
        view_cols = ["Deal_ID", "Client", "Country", "RM", "Product", "Lending_Drawn", "RWA", "Total_Revenue", "NIM_bps", "Tx_RoE", "Status"]
        st.dataframe(format_table(low[[c for c in view_cols if c in low.columns]]), use_container_width=True, height=380)

    with tab4:
        st.subheader("Exposure & RWA efficiency")
        c1, c2 = st.columns(2)
        with c1:
            plot_bar(grouped_view(df, ["Country"]).head(10), "Country", "RWA", "RWA by Country")
        with c2:
            plot_bar(grouped_view(df, ["Product"]).head(10), "Product", "Revenue_per_RWA", "Revenue per RWA by Product")
        country = grouped_view(df, ["Country"])
        st.dataframe(format_table(country), use_container_width=True, height=360)

    with tab5:
        st.subheader("Deposits and balance sheet support")
        c1, c2 = st.columns(2)
        with c1:
            plot_bar(grouped_view(df, ["Country"]).head(10), "Country", "Deposit_Balance", "Deposit Balance by Country")
        with c2:
            plot_bar(grouped_view(df, ["Client"]).head(10), "Client", "Deposit_to_Lending", "Top Deposit-to-Lending Clients")
        dep = grouped_view(df, ["Client", "Country", "RM"])
        st.dataframe(format_table(dep[["Client", "Country", "RM", "Deposit_Balance", "Lending_Drawn", "Deposit_to_Lending", "Total_Revenue", "Tx_RoE"]]), use_container_width=True, height=380)

    with tab6:
        st.subheader("Raw Data with Derived Metrics")
        st.dataframe(format_table(df), use_container_width=True, height=520)

def placeholder_page(title, status):
    st.markdown(f"""
    <div class="ecai-hero">
        <h1>{title}</h1>
        <p>{status}</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("This module is preserved as part of the EC-AI platform structure. Banking Insight is the active v0.2 build focus.")

# ---------- Router ----------
st.sidebar.title("EC-AI Insight")
module = st.sidebar.radio("Module", ["Home", "Banking Insight", "SME Insight", "Insurance Benchmark"])
st.sidebar.caption("v0.2 platform shell + banking clean UI")

if module == "Home":
    home_page()
elif module == "Banking Insight":
    banking_page()
elif module == "SME Insight":
    placeholder_page("EC-AI SME Insight", "Sales, customer, product and channel performance intelligence.")
else:
    placeholder_page("EC-AI Insurance Benchmark", "Broker-side benefit benchmarking and client positioning analytics.")
