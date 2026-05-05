
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="EC-AI Banking Insight v0.1", layout="wide")

LOW_NIM_THRESHOLD_BPS = 30
TX_ROE_THRESHOLD = 0.15

def money(x):
    try:
        x = float(x)
    except Exception:
        return "-"
    if abs(x) >= 1_000_000_000:
        return f"${x/1_000_000_000:,.2f}B"
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:,.1f}M"
    if abs(x) >= 1_000:
        return f"${x/1_000:,.1f}K"
    return f"${x:,.0f}"

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

    for c in ["Lending_Drawn", "RWA", "Total_Revenue", "NIAT", "Deposit_Balance", "NIM_bps", "Net_Interest_Income"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "NIM_bps" not in df.columns:
        if "Net_Interest_Income" in df.columns:
            df["NIM_bps"] = df.apply(lambda r: safe_div(r["Net_Interest_Income"], r["Lending_Drawn"]) * 10000, axis=1)
        else:
            df["NIM_bps"] = np.nan

    if "Deposit_Balance" not in df.columns:
        df["Deposit_Balance"] = 0

    df["Tx_RoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    df["Revenue_per_RWA"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    df["Low_NIM_Flag"] = df["NIM_bps"] < LOW_NIM_THRESHOLD_BPS
    df["Low_Tx_RoE_Flag"] = df["Tx_RoE"] < TX_ROE_THRESHOLD

    def classify(row):
        if row["Low_NIM_Flag"] and row["Low_Tx_RoE_Flag"]:
            return "Critical: Low NIM + Low Tx RoE"
        if row["Low_NIM_Flag"]:
            return "Low NIM: Review / Sell-down"
        if row["Low_Tx_RoE_Flag"]:
            return "Low Tx RoE: Reprice / Restructure"
        if row["Deposit_Balance"] > row["Lending_Drawn"] and row["Total_Revenue"] > 0:
            return "Deposit Rich / Cross-sell"
        return "Value Creator"

    df["Status"] = df.apply(classify, axis=1)
    return df

def grouped_view(df, group_cols):
    g = df.groupby(group_cols, dropna=False).agg({
        "Total_Revenue": "sum",
        "Lending_Drawn": "sum",
        "Deposit_Balance": "sum",
        "RWA": "sum",
        "NIAT": "sum",
        "Low_NIM_Flag": "sum"
    }).reset_index()

    nim_rows = []
    for _, x in df.groupby(group_cols, dropna=False):
        nim_rows.append(safe_div((x["NIM_bps"] * x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum()))
    g["NIM_bps"] = nim_rows
    g["Tx_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Revenue_per_RWA"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    return g.sort_values("Total_Revenue", ascending=False)

def executive_summary(df):
    total_rev = df["Total_Revenue"].sum()
    total_drawn = df["Lending_Drawn"].sum()
    total_rwa = df["RWA"].sum()
    total_niat = df["NIAT"].sum()
    tx_roe = safe_div(total_niat, total_rwa)
    low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()
    low_nim_share = safe_div(low_nim_exposure, total_drawn)

    top_country = grouped_view(df, ["Country"]).iloc[0]["Country"]
    top_rm = grouped_view(df, ["RM"]).iloc[0]["RM"]
    top_product = grouped_view(df, ["Product"]).iloc[0]["Product"]

    lines = [
        f"Total revenue is {money(total_rev)}, supported by lending drawn of {money(total_drawn)} and total RWA of {money(total_rwa)}.",
        f"Portfolio Tx RoE is {pct(tx_roe)}, compared with the 15.0% favourable threshold.",
        f"Low-NIM exposure is {money(low_nim_exposure)}, representing {pct(low_nim_share)} of total lending drawn.",
        f"The top revenue country is {top_country}, the top RM is {top_rm}, and the strongest product contributor is {top_product}.",
    ]

    actions = []
    if low_nim_share and low_nim_share > 0.10:
        actions.append("Review low-NIM exposure and consider repricing, restructuring, or sell-down for deals below 30bps.")
    if tx_roe and tx_roe < TX_ROE_THRESHOLD:
        actions.append("Prioritize Tx RoE recovery by improving pricing discipline and reducing capital-heavy low-return exposure.")
    actions.append("Focus management discussion on clients with high exposure but weak revenue / Tx RoE contribution.")
    return lines, actions

st.title("EC-AI Banking Insight v0.1")
st.caption("Revenue, NIM, Tx RoE and exposure efficiency intelligence for management reporting.")

uploaded = st.file_uploader("Upload banking performance CSV", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to begin. Use the sample dataset generated with this app structure.")
    st.stop()

raw = pd.read_csv(uploaded)
df = ensure_metrics(raw)

st.subheader("Executive Overview")

total_revenue = df["Total_Revenue"].sum()
total_drawn = df["Lending_Drawn"].sum()
total_deposit = df["Deposit_Balance"].sum()
total_rwa = df["RWA"].sum()
total_niat = df["NIAT"].sum()
portfolio_tx_roe = safe_div(total_niat, total_rwa)
low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Revenue", money(total_revenue))
c2.metric("Lending Drawn", money(total_drawn))
c3.metric("Deposit Balance", money(total_deposit))
c4.metric("Tx RoE", pct(portfolio_tx_roe))
c5.metric("Low NIM Exposure", money(low_nim_exposure))

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Executive Summary", "Client Profitability", "Deal Screening", "Country / RM View", "Raw Data"
])

with tab1:
    st.subheader("Management Summary")
    lines, actions = executive_summary(df)

    st.markdown("### What matters")
    for line in lines:
        st.markdown(f"- {line}")

    st.markdown("### Recommended management actions")
    for action in actions:
        st.markdown(f"- {action}")

    st.markdown("### Revenue by Country")
    country = grouped_view(df, ["Country"])
    st.bar_chart(country.set_index("Country")["Total_Revenue"])

    st.markdown("### Revenue by Product")
    product = grouped_view(df, ["Product"])
    st.bar_chart(product.set_index("Product")["Total_Revenue"])

with tab2:
    st.subheader("Client Profitability")
    client = grouped_view(df, ["Client"])
    client["Tx_RoE"] = client["Tx_RoE"].apply(pct)
    client["NIM_bps"] = client["NIM_bps"].round(1)
    st.dataframe(client, use_container_width=True)

with tab3:
    st.subheader("Deal Screening Insight")
    view_cols = [
        "Deal_ID", "Client", "Country", "RM", "Product", "Lending_Drawn", "RWA",
        "Total_Revenue", "NIAT", "NIM_bps", "Tx_RoE", "Status"
    ]
    available_cols = [c for c in view_cols if c in df.columns]
    deal_view = df[available_cols].copy()
    if "Tx_RoE" in deal_view.columns:
        deal_view["Tx_RoE"] = deal_view["Tx_RoE"].apply(pct)
    st.dataframe(deal_view.sort_values("Status"), use_container_width=True)

with tab4:
    st.subheader("Country Performance")
    country = grouped_view(df, ["Country"])
    country["Tx_RoE"] = country["Tx_RoE"].apply(pct)
    st.dataframe(country, use_container_width=True)

    st.subheader("RM Performance")
    rm = grouped_view(df, ["RM"])
    rm["Tx_RoE"] = rm["Tx_RoE"].apply(pct)
    st.dataframe(rm, use_container_width=True)

with tab5:
    st.subheader("Raw Data with Derived Metrics")
    df_show = df.copy()
    df_show["Tx_RoE"] = df_show["Tx_RoE"].apply(pct)
    st.dataframe(df_show, use_container_width=True)
