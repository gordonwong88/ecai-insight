import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# EC-AI Banking Engine v0.3
# Focus: Tx RoE / NIM / Revenue / Exposure intelligence
# =====================================================

st.set_page_config(
    page_title="EC-AI Banking Engine v0.3",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LOW_NIM_THRESHOLD_BPS = 30
TX_ROE_THRESHOLD = 0.15
CRITICAL_TX_ROE = 0.05
WEAK_TX_ROE = 0.10

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


def ensure_metrics(df):
    df = normalize_columns(df)

    # Flexible mapping so the app survives slightly different banking CSV labels
    colmap = {
        "Client": find_col(df, ["Client", "Customer", "Customer_Name", "Borrower", "Client_Name"]),
        "Country": find_col(df, ["Country", "Booking_Country", "Region", "Office"]),
        "RM": find_col(df, ["RM", "Relationship_Manager", "RM_Name", "Owner"]),
        "Product": find_col(df, ["Product", "Facility_Type", "Deal_Type", "Product_Type"]),
        "Lending_Drawn": find_col(df, ["Lending_Drawn", "Lending_Outstanding", "Drawn", "Exposure", "Outstanding"]),
        "RWA": find_col(df, ["RWA", "Risk_Weighted_Asset", "Risk_Weighted_Assets"]),
        "Total_Revenue": find_col(df, ["Total_Revenue", "Revenue", "Gross_Revenue", "Income"]),
        "NIAT": find_col(df, ["NIAT", "Net_Income_After_Tax", "Net_Income", "Profit_After_Tax"]),
        "Deposit_Balance": find_col(df, ["Deposit_Balance", "Deposit", "Deposits", "Deposit_Outstanding"]),
        "NIM_bps": find_col(df, ["NIM_bps", "NIM", "NIM_Basis_Points", "Net_Interest_Margin_bps"]),
        "Net_Interest_Income": find_col(df, ["Net_Interest_Income", "NII"]),
        "Deal_ID": find_col(df, ["Deal_ID", "Deal", "Transaction_ID", "Facility_ID"]),
    }

    required_standard = ["Client", "Country", "RM", "Product", "Lending_Drawn", "RWA", "Total_Revenue", "NIAT"]
    missing = [k for k in required_standard if colmap[k] is None]
    if missing:
        st.error(
            "Missing required banking columns: " + ", ".join(missing) +
            ". Required core fields are Client, Country, RM, Product, Lending Drawn, RWA, Total Revenue and NIAT."
        )
        st.stop()

    # Rename mapped columns to standard names
    rename = {v: k for k, v in colmap.items() if v is not None and v != k}
    df = df.rename(columns=rename)

    if "Deposit_Balance" not in df.columns:
        df["Deposit_Balance"] = 0
    if "Deal_ID" not in df.columns:
        df["Deal_ID"] = [f"DEAL-{i+1:04d}" for i in range(len(df))]

    numeric_cols = [
        "Lending_Drawn", "RWA", "Total_Revenue", "NIAT", "Deposit_Balance",
        "NIM_bps", "Net_Interest_Income"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # NIM logic: if no NIM_bps, derive from NII / lending drawn
    if "NIM_bps" not in df.columns or df["NIM_bps"].isna().all():
        if "Net_Interest_Income" in df.columns:
            df["NIM_bps"] = df.apply(lambda r: safe_div(r["Net_Interest_Income"], r["Lending_Drawn"]) * 10000, axis=1)
        else:
            df["NIM_bps"] = np.nan

    df["Tx_RoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    df["Revenue_per_RWA"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    df["Deposit_to_Lending"] = df.apply(lambda r: safe_div(r["Deposit_Balance"], r["Lending_Drawn"]), axis=1)
    df["Low_NIM_Flag"] = df["NIM_bps"] < LOW_NIM_THRESHOLD_BPS
    df["Low_Tx_RoE_Flag"] = df["Tx_RoE"] < TX_ROE_THRESHOLD

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
    g = df.groupby(group_cols, dropna=False).agg({
        "Total_Revenue": "sum",
        "Lending_Drawn": "sum",
        "Deposit_Balance": "sum",
        "RWA": "sum",
        "NIAT": "sum",
        "Low_NIM_Flag": "sum",
        "Low_Tx_RoE_Flag": "sum",
    }).reset_index()

    nim_rows = []
    for _, x in df.groupby(group_cols, dropna=False):
        nim_rows.append(safe_div((x["NIM_bps"] * x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum()))
    g["NIM_bps"] = nim_rows
    g["Tx_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Revenue_per_RWA"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    g["Deposit_to_Lending"] = g.apply(lambda r: safe_div(r["Deposit_Balance"], r["Lending_Drawn"]), axis=1)
    return g.sort_values("Total_Revenue", ascending=False)


def build_watchlist(df):
    exposure_threshold = df["Lending_Drawn"].quantile(0.60) if len(df) else 0
    w = df[(df["Tx_RoE"] < TX_ROE_THRESHOLD) & (df["Lending_Drawn"] >= exposure_threshold)].copy()
    if w.empty:
        w = df[df["Tx_RoE"] < TX_ROE_THRESHOLD].copy()
    return w.sort_values(["Tx_RoE", "Lending_Drawn"], ascending=[True, False])


def executive_lines(df):
    total_rev = df["Total_Revenue"].sum()
    total_drawn = df["Lending_Drawn"].sum()
    total_rwa = df["RWA"].sum()
    total_niat = df["NIAT"].sum()
    tx_roe = safe_div(total_niat, total_rwa)
    low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()
    low_nim_share = safe_div(low_nim_exposure, total_drawn)

    top_country = grouped_view(df, ["Country"]).iloc[0]["Country"] if not df.empty else "-"
    top_rm = grouped_view(df, ["RM"]).iloc[0]["RM"] if not df.empty else "-"
    top_product = grouped_view(df, ["Product"]).iloc[0]["Product"] if not df.empty else "-"

    diagnosis = [
        ("Revenue engine", f"Total revenue is {money(total_rev)}, led by {top_country}, {top_product}, and {top_rm}."),
        ("Capital return", f"Portfolio Tx RoE is {pct(tx_roe)} versus the favourable threshold of {pct(TX_ROE_THRESHOLD)}."),
        ("Pricing pressure", f"Low-NIM exposure is {money(low_nim_exposure)}, representing {pct(low_nim_share)} of lending drawn."),
        ("Management action", "Focus on high exposure / weak return clients for repricing, sell-down, restructuring, or deposit/revenue cross-sell."),
    ]
    return diagnosis


def format_table(df):
    out = df.copy()
    for c in ["Total_Revenue", "Lending_Drawn", "Deposit_Balance", "RWA", "NIAT"]:
        if c in out.columns:
            out[c] = out[c].apply(money)
    if "Tx_RoE" in out.columns:
        out["Tx_RoE"] = out["Tx_RoE"].apply(pct)
    if "Revenue_per_RWA" in out.columns:
        out["Revenue_per_RWA"] = out["Revenue_per_RWA"].apply(pct)
    if "Deposit_to_Lending" in out.columns:
        out["Deposit_to_Lending"] = out["Deposit_to_Lending"].apply(pct)
    if "NIM_bps" in out.columns:
        out["NIM_bps"] = out["NIM_bps"].apply(bps)
    return out


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .main {background:#ffffff;}
    .hero {
        padding: 34px 34px;
        border-radius: 18px;
        background: linear-gradient(110deg, #101d34 0%, #102946 52%, #0f766e 100%);
        color: white;
        margin-bottom: 28px;
        box-shadow: 0 10px 28px rgba(15, 29, 52, 0.12);
    }
    .hero h1 {font-size: 34px; margin:0; color:white; font-weight:800;}
    .hero p {font-size: 16px; margin-top:22px; color:#f8fafc;}
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px 18px;
        box-shadow: 0 6px 18px rgba(15,23,42,0.04);
        min-height: 110px;
    }
    .metric-label {font-size: 13px; color:#64748b; margin-bottom:10px;}
    .metric-value {font-size: 28px; font-weight:800; color:#0f172a;}
    .metric-note {font-size:12px; color:#64748b; margin-top:8px;}
    .diag-card {
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 14px;
        background:#f8fafc;
        border-left: 5px solid #0f766e;
        font-size: 15px;
        line-height: 1.65;
    }
    .diag-risk {border-left-color:#dc2626; background:#fff7ed;}
    .section-title {font-size: 28px; font-weight:800; color:#0f172a; margin-top:18px; margin-bottom:14px;}
    .small-muted {font-size:12px; color:#64748b;}
    div[data-testid="stMetricValue"] {font-size: 26px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# App header
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <h1>EC-AI Banking Engine v0.3</h1>
        <p>Tx RoE / NIM / Revenue / Exposure Decision Intelligence</p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded = st.file_uploader("Upload banking performance CSV", type=["csv"])

if uploaded is None:
    st.info("Upload a banking performance CSV to begin. Core columns: Client, Country, RM, Product, Lending_Drawn, RWA, Total_Revenue, NIAT. Optional: Deposit_Balance, NIM_bps, Net_Interest_Income, Deal_ID.")
    st.stop()

raw = pd.read_csv(uploaded)
df = ensure_metrics(raw)

# -----------------------------
# Executive Snapshot
# -----------------------------
total_revenue = df["Total_Revenue"].sum()
total_drawn = df["Lending_Drawn"].sum()
total_deposit = df["Deposit_Balance"].sum()
total_rwa = df["RWA"].sum()
total_niat = df["NIAT"].sum()
portfolio_tx_roe = safe_div(total_niat, total_rwa)
low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()
low_nim_share = safe_div(low_nim_exposure, total_drawn)

st.markdown('<div class="section-title">Executive Snapshot</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
metric_data = [
    (c1, "Total Revenue", money(total_revenue), "Revenue pool"),
    (c2, "Lending Drawn", money(total_drawn), "Drawn exposure"),
    (c3, "Deposit Balance", money(total_deposit), "Balance sheet support"),
    (c4, "Tx RoE", pct(portfolio_tx_roe), f"Target {pct(TX_ROE_THRESHOLD)}"),
    (c5, "Low NIM Exposure", money(low_nim_exposure), f"{pct(low_nim_share)} of drawn"),
]
for col, label, value, note in metric_data:
    col.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "CEO Dashboard", "Revenue Engine", "Pricing & NIM Risk", "Capital Efficiency", "Balance Sheet", "Portfolio Data"
])

with tab1:
    st.subheader("Management Diagnosis")
    diag = executive_lines(df)
    left, right = st.columns(2)
    for i, (title, text) in enumerate(diag):
        target_col = left if i in [0, 1] else right
        risk_class = " diag-risk" if "Pricing" in title else ""
        target_col.markdown(
            f"<div class='diag-card{risk_class}'><b>{title}:</b> {text}</div>",
            unsafe_allow_html=True,
        )

    st.markdown("### Tx RoE vs Exposure Allocation")
    st.caption("Bubble size = revenue. This highlights capital-heavy clients with weak return.")
    scatter_df = df.copy()
    scatter_df["Tx_RoE_pct"] = scatter_df["Tx_RoE"] * 100
    scatter_df["Revenue_Size"] = scatter_df["Total_Revenue"].clip(lower=1)

    fig = px.scatter(
        scatter_df,
        x="Lending_Drawn",
        y="Tx_RoE_pct",
        size="Revenue_Size",
        color="Country",
        hover_name="Client",
        hover_data={
            "RM": True,
            "Product": True,
            "Lending_Drawn": ":,.0f",
            "RWA": ":,.0f",
            "Total_Revenue": ":,.0f",
            "NIAT": ":,.0f",
            "NIM_bps": ":.1f",
            "Tx_RoE_pct": ":.1f",
            "Revenue_Size": False,
        },
        labels={"Lending_Drawn": "Lending Drawn", "Tx_RoE_pct": "Tx RoE (%)"},
        title="Capital Allocation Map: Tx RoE vs Lending Drawn",
    )
    fig.add_hline(
        y=TX_ROE_THRESHOLD * 100,
        line_dash="dash",
        annotation_text="15% favourable threshold",
        annotation_position="top left",
    )
    fig.update_layout(height=520, margin=dict(l=20, r=20, t=65, b=30), legend_title_text="Country")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Management Watchlist")
    watch = build_watchlist(df)
    watch_cols = ["Watchlist_Flag", "Client", "Country", "RM", "Product", "Lending_Drawn", "RWA", "Total_Revenue", "NIAT", "Tx_RoE", "NIM_bps", "Status"]
    st.dataframe(format_table(watch[watch_cols].head(20)), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Revenue Engine")
    cc1, cc2 = st.columns(2)
    country = grouped_view(df, ["Country"])
    product = grouped_view(df, ["Product"])

    fig_country = px.bar(country, x="Country", y="Total_Revenue", title="Revenue by Country", text_auto=".2s")
    fig_country.update_layout(height=420, margin=dict(l=10, r=10, t=55, b=20))
    cc1.plotly_chart(fig_country, use_container_width=True)

    fig_product = px.bar(product, x="Product", y="Total_Revenue", title="Revenue by Product", text_auto=".2s")
    fig_product.update_layout(height=420, margin=dict(l=10, r=10, t=55, b=20))
    cc2.plotly_chart(fig_product, use_container_width=True)

    st.markdown("### Country / RM Revenue Table")
    country_rm = grouped_view(df, ["Country", "RM"])
    st.dataframe(format_table(country_rm), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Pricing & NIM Risk")
    low = df[df["Low_NIM_Flag"]].sort_values("Lending_Drawn", ascending=False).copy()
    st.markdown(f"Low-NIM rule: **NIM < {LOW_NIM_THRESHOLD_BPS} bps**")

    pc1, pc2 = st.columns([1.15, 1])
    nim_country = grouped_view(low if not low.empty else df, ["Country"])
    fig_nim = px.bar(nim_country, x="Country", y="Lending_Drawn", title="Low-NIM Exposure by Country", text_auto=".2s")
    fig_nim.update_layout(height=420, margin=dict(l=10, r=10, t=55, b=20))
    pc1.plotly_chart(fig_nim, use_container_width=True)

    product_low = grouped_view(low if not low.empty else df, ["Product"])
    fig_nim_prod = px.bar(product_low, x="Product", y="Lending_Drawn", title="Low-NIM Exposure by Product", text_auto=".2s")
    fig_nim_prod.update_layout(height=420, margin=dict(l=10, r=10, t=55, b=20))
    pc2.plotly_chart(fig_nim_prod, use_container_width=True)

    st.markdown("### Low-NIM Deal List")
    cols = ["Deal_ID", "Client", "Country", "RM", "Product", "Lending_Drawn", "Total_Revenue", "NIM_bps", "Tx_RoE", "Status"]
    st.dataframe(format_table(low[cols].head(50)), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Capital Efficiency")
    client = grouped_view(df, ["Client"])
    client["Client_Flag"] = client.apply(lambda r: "Low Return" if r["Tx_RoE"] < TX_ROE_THRESHOLD else "Healthy", axis=1)

    fig_cap = px.scatter(
        client,
        x="RWA",
        y="Tx_RoE",
        size="Total_Revenue",
        color="Client_Flag",
        hover_name="Client",
        title="Client Capital Efficiency: Tx RoE vs RWA",
        labels={"Tx_RoE": "Tx RoE", "RWA": "RWA"},
    )
    fig_cap.add_hline(y=TX_ROE_THRESHOLD, line_dash="dash", annotation_text="15% threshold")
    fig_cap.update_layout(height=520, margin=dict(l=20, r=20, t=65, b=30))
    st.plotly_chart(fig_cap, use_container_width=True)

    st.markdown("### Client Profitability Table")
    st.dataframe(format_table(client.sort_values("Tx_RoE", ascending=True)), use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Balance Sheet")
    dep_country = grouped_view(df, ["Country"])
    fig_dep = go.Figure()
    fig_dep.add_bar(x=dep_country["Country"], y=dep_country["Lending_Drawn"], name="Lending Drawn")
    fig_dep.add_bar(x=dep_country["Country"], y=dep_country["Deposit_Balance"], name="Deposit Balance")
    fig_dep.update_layout(barmode="group", title="Lending vs Deposit Balance by Country", height=460, margin=dict(l=10, r=10, t=55, b=20))
    st.plotly_chart(fig_dep, use_container_width=True)

    st.markdown("### Deposit Support View")
    dep_cols = ["Country", "RM", "Total_Revenue", "Lending_Drawn", "Deposit_Balance", "Deposit_to_Lending", "Tx_RoE"]
    dep_view = grouped_view(df, ["Country", "RM"])[dep_cols]
    st.dataframe(format_table(dep_view), use_container_width=True, hide_index=True)

with tab6:
    st.subheader("Portfolio Data")
    view_cols = [
        "Deal_ID", "Client", "Country", "RM", "Product", "Lending_Drawn", "Deposit_Balance", "RWA",
        "Total_Revenue", "NIAT", "NIM_bps", "Tx_RoE", "Revenue_per_RWA", "Deposit_to_Lending", "Status"
    ]
    available_cols = [c for c in view_cols if c in df.columns]
    st.dataframe(format_table(df[available_cols]), use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download enriched CSV", data=csv, file_name="ecai_banking_engine_enriched.csv", mime="text/csv")
