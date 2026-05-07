
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="EC-AI Banking Engine v0.4.2", layout="wide")

LOW_NIM_THRESHOLD_BPS = 30
TX_ROE_HURDLE = 0.15

NAVY = "#0B1F3B"
BLUE_GREY = "#40566B"
LIGHT_GREY = "#F3F6F8"
MID_GREY = "#D9E1E8"
TEXT = "#111827"
RED = "#B91C1C"
LIGHT_RED = "#FCA5A5"
LIGHT_GREEN = "#BBF7D0"
GREEN = "#16A34A"

st.markdown(
    f"""
<style>
.stApp {{
    background-color: #F7F9FB;
}}
.ec-hero {{
    background: linear-gradient(135deg, {NAVY} 0%, #12385F 55%, #1F6F73 100%);
    border-radius: 18px;
    padding: 28px 32px;
    color: white;
    margin-bottom: 20px;
}}
.ec-hero h1 {{
    font-size: 34px;
    margin-bottom: 6px;
}}
.ec-hero p {{
    font-size: 16px;
    opacity: 0.92;
}}
div[data-testid="stMetric"] {{
    background-color: white;
    border: 1px solid #E5E7EB;
    padding: 14px;
    border-radius: 14px;
}}
button[kind="secondary"] {{
    border-radius: 12px !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

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

    for c in ["Limit", "Lending_Drawn", "RWA", "Total_Revenue", "NIAT", "Deposit_Balance", "NIM_bps", "Net_Interest_Income"]:
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
    df["Below_Hurdle_Flag"] = df["Tx_RoE"] < TX_ROE_HURDLE

    def status(row):
        if row["Low_NIM_Flag"] and row["Below_Hurdle_Flag"]:
            return "Critical: Low NIM + Below Hurdle"
        if row["Low_NIM_Flag"]:
            return "Low NIM: Review / Sell-down"
        if row["Below_Hurdle_Flag"]:
            return "Below Tx RoE Hurdle"
        return "Above Hurdle"

    df["Status"] = df.apply(status, axis=1)
    return df

def grouped_view(df, group_cols):
    g = df.groupby(group_cols, dropna=False).agg({
        "Total_Revenue": "sum",
        "Lending_Drawn": "sum",
        "Deposit_Balance": "sum",
        "RWA": "sum",
        "NIAT": "sum",
        "Low_NIM_Flag": "sum",
        "Below_Hurdle_Flag": "sum"
    }).reset_index()

    nim = []
    for _, x in df.groupby(group_cols, dropna=False):
        nim.append(safe_div((x["NIM_bps"] * x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum()))
    g["NIM_bps"] = nim
    g["Tx_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Revenue_per_RWA"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    return g.sort_values("Total_Revenue", ascending=False)

def add_bar_labels(df, y_col):
    return [money(v) for v in df[y_col]]

def bar_chart(df, x, y, title):
    chart_df = df.copy()
    chart_df["Label"] = chart_df[y].apply(money)
    fig = px.bar(
        chart_df,
        x=x,
        y=y,
        text="Label",
        title=title,
        color_discrete_sequence=[NAVY],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=390,
        margin=dict(l=30, r=25, t=55, b=45),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color=TEXT),
        title=dict(font=dict(size=18, color=NAVY)),
        yaxis=dict(
            tickvals=[0, 1_000_000_000, 2_000_000_000, 3_000_000_000, 4_000_000_000, 5_000_000_000],
            ticktext=["0", "1.0B", "2.0B", "3.0B", "4.0B", "5.0B"],
            gridcolor="#E5E7EB"
        ),
        xaxis=dict(tickangle=-25),
    )
    return fig

def tx_roe_color(v):
    # User requested: 0-10% red, 10-15% light red, 15-20% light green, >20% moderate green
    if pd.isna(v):
        return "#E5E7EB"
    if v < 0.10:
        return RED
    if v < 0.15:
        return LIGHT_RED
    if v < 0.20:
        return LIGHT_GREEN
    return GREEN

def tx_roe_status_label(v):
    if pd.isna(v):
        return "N/A"
    if v < 0.10:
        return "Critical"
    if v < 0.15:
        return "Below Hurdle"
    if v < 0.20:
        return "Acceptable"
    return "Strong"

def tx_roe_heatmap_table(df, group_col):
    g = grouped_view(df, [group_col]).copy()
    g["Tx RoE"] = g["Tx_RoE"].apply(pct)
    g["Revenue"] = g["Total_Revenue"].apply(money)
    g["Lending Drawn"] = g["Lending_Drawn"].apply(money)
    g["RWA"] = g["RWA"].apply(money)
    g["NIM"] = g["NIM_bps"].round(1).astype(str) + " bps"
    g["Status"] = g["Tx_RoE"].apply(tx_roe_status_label)
    show = g[[group_col, "Revenue", "Lending Drawn", "RWA", "NIM", "Tx RoE", "Status"]].copy()

    def style_row(row):
        raw = g.loc[row.name, "Tx_RoE"]
        color = tx_roe_color(raw)
        text_color = "white" if color in [RED, GREEN] else "#111827"
        return [""] * (len(row)-2) + [f"background-color:{color}; color:{text_color}; font-weight:700;", f"background-color:{color}; color:{text_color}; font-weight:700;"]

    st.dataframe(show.style.apply(style_row, axis=1), use_container_width=True, hide_index=True)

def executive_summary(df):
    total_rev = df["Total_Revenue"].sum()
    total_drawn = df["Lending_Drawn"].sum()
    total_rwa = df["RWA"].sum()
    total_niat = df["NIAT"].sum()
    tx_roe = safe_div(total_niat, total_rwa)
    low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()
    below_hurdle_exposure = df.loc[df["Below_Hurdle_Flag"], "Lending_Drawn"].sum()

    top_country = grouped_view(df, ["Country"]).iloc[0]["Country"]
    top_product = grouped_view(df, ["Product"]).iloc[0]["Product"]

    lines = [
        f"Total revenue is {money(total_rev)}, with lending drawn of {money(total_drawn)} and RWA of {money(total_rwa)}.",
        f"Portfolio Tx RoE is {pct(tx_roe)} against the 15.0% favourable hurdle.",
        f"Low-NIM exposure is {money(low_nim_exposure)}. Below-hurdle exposure is {money(below_hurdle_exposure)}.",
        f"Top revenue contribution comes from {top_country} and {top_product}.",
    ]

    actions = [
        "Prioritize below-hurdle relationships with large lending drawn and weak NIM.",
        "Review low-NIM deals below 30bps for repricing, restructuring, or sell-down.",
        "Reallocate management attention toward countries/products with strong Tx RoE and scalable revenue contribution.",
    ]
    return lines, actions

st.markdown(
    """
<div class="ec-hero">
  <h1>EC-AI Banking Engine v0.4.2</h1>
  <p>Tx RoE / NIM / Revenue Decision Intelligence for executive banking management.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## EC-AI Banking Engine")
    uploaded = st.file_uploader("Upload banking performance file", type=["csv", "xlsx"])
    st.caption("Required: Client, Country, RM, Product, Lending_Drawn, RWA, Total_Revenue, NIAT")
    st.markdown("---")
    st.markdown("**Thresholds**")
    st.write("Tx RoE hurdle: 15%")
    st.write("Low NIM: <30bps")

if uploaded is None:
    st.info("Upload sample banking data to begin.")
    st.stop()

if uploaded.name.lower().endswith(".xlsx"):
    raw = pd.read_excel(uploaded)
else:
    raw = pd.read_csv(uploaded)

df = ensure_metrics(raw)

st.subheader("Executive Snapshot")
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "CEO Dashboard",
    "Revenue Engine",
    "Pricing & NIM Risk",
    "Capital Efficiency",
    "Country Portfolio",
    "Portfolio Data"
])

with tab1:
    st.subheader("CEO Dashboard")
    lines, actions = executive_summary(df)
    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown("### Management Summary")
        for line in lines:
            st.markdown(f"- {line}")
        st.markdown("### Recommended Actions")
        for action in actions:
            st.markdown(f"- {action}")
    with right:
        st.markdown("### Tx RoE Heatmap by Country")
        tx_roe_heatmap_table(df, "Country")

    st.markdown("### Revenue by Country")
    country = grouped_view(df, ["Country"]).head(8)
    st.plotly_chart(bar_chart(country, "Country", "Total_Revenue", "Revenue by Country"), use_container_width=True)

with tab2:
    st.subheader("Revenue Engine")
    c1, c2 = st.columns(2)
    with c1:
        country = grouped_view(df, ["Country"]).head(8)
        st.plotly_chart(bar_chart(country, "Country", "Total_Revenue", "Revenue by Country"), use_container_width=True)
    with c2:
        product = grouped_view(df, ["Product"]).head(8)
        st.plotly_chart(bar_chart(product, "Product", "Total_Revenue", "Revenue by Product Type"), use_container_width=True)

    st.markdown("### Top Revenue Relationships")
    client = grouped_view(df, ["Client"]).head(15)
    view = client.copy()
    view["Revenue"] = view["Total_Revenue"].apply(money)
    view["Lending Drawn"] = view["Lending_Drawn"].apply(money)
    view["Tx RoE"] = view["Tx_RoE"].apply(pct)
    view["NIM"] = view["NIM_bps"].round(1).astype(str) + " bps"
    st.dataframe(view[["Client", "Revenue", "Lending Drawn", "NIM", "Tx RoE"]], use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Pricing & NIM Risk")
    low = df[df["Low_NIM_Flag"]].copy()
    st.metric("Low NIM Deal Count", len(low))
    if len(low):
        low["Lending Drawn"] = low["Lending_Drawn"].apply(money)
        low["Revenue"] = low["Total_Revenue"].apply(money)
        low["Tx RoE"] = low["Tx_RoE"].apply(pct)
        low["NIM"] = low["NIM_bps"].round(1).astype(str) + " bps"
        st.dataframe(low[["Deal_ID", "Client", "Country", "Product", "Lending Drawn", "Revenue", "NIM", "Tx RoE", "Status"]], use_container_width=True, hide_index=True)
    else:
        st.success("No low-NIM deals detected.")

with tab4:
    st.subheader("Capital Efficiency")
    st.markdown("### Capital Efficiency Watchlist")
    watch = df[(df["Below_Hurdle_Flag"]) | (df["Low_NIM_Flag"])].copy()
    watch = watch.sort_values(["Below_Hurdle_Flag", "Lending_Drawn"], ascending=[False, False]).head(20)
    watch["Lending Drawn"] = watch["Lending_Drawn"].apply(money)
    watch["RWA Display"] = watch["RWA"].apply(money)
    watch["Revenue"] = watch["Total_Revenue"].apply(money)
    watch["Tx RoE"] = watch["Tx_RoE"].apply(pct)
    watch["NIM"] = watch["NIM_bps"].round(1).astype(str) + " bps"
    st.dataframe(watch[["Client", "Country", "Product", "Lending Drawn", "RWA Display", "Revenue", "NIM", "Tx RoE", "Status"]], use_container_width=True, hide_index=True)

    st.markdown("### Exposure vs Tx RoE Ranking")
    ranked = grouped_view(df, ["Client"]).sort_values("Lending_Drawn", ascending=False).head(15)
    ranked["Tx RoE %"] = ranked["Tx_RoE"] * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ranked["Client"],
        y=ranked["Lending_Drawn"],
        name="Lending Drawn",
        marker_color=NAVY,
        yaxis="y1",
        text=[money(v) for v in ranked["Lending_Drawn"]],
        textposition="outside"
    ))
    fig.add_trace(go.Scatter(
        x=ranked["Client"],
        y=ranked["Tx RoE %"],
        name="Tx RoE %",
        mode="lines+markers+text",
        marker_color=GREEN,
        line=dict(color=GREEN, width=3),
        yaxis="y2",
        text=[f"{v:.1f}%" for v in ranked["Tx RoE %"]],
        textposition="top center"
    ))
    fig.update_layout(
        title="Top Exposure Relationships: Lending Drawn vs Tx RoE",
        height=480,
        xaxis=dict(tickangle=-35),
        yaxis=dict(title="Lending Drawn", tickvals=[0,1e9,2e9,3e9,4e9,5e9], ticktext=["0","1.0B","2.0B","3.0B","4.0B","5.0B"]),
        yaxis2=dict(title="Tx RoE %", overlaying="y", side="right", ticksuffix="%"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("Country Portfolio")
    st.markdown("### Country-Level Portfolio Quality")
    tx_roe_heatmap_table(df, "Country")

    st.markdown("### Country Portfolio Table")
    country = grouped_view(df, ["Country"]).copy()
    country["Revenue"] = country["Total_Revenue"].apply(money)
    country["Lending Drawn"] = country["Lending_Drawn"].apply(money)
    country["Deposits"] = country["Deposit_Balance"].apply(money)
    country["RWA Display"] = country["RWA"].apply(money)
    country["Tx RoE"] = country["Tx_RoE"].apply(pct)
    country["NIM"] = country["NIM_bps"].round(1).astype(str) + " bps"
    st.dataframe(country[["Country", "Revenue", "Lending Drawn", "Deposits", "RWA Display", "NIM", "Tx RoE", "Low_NIM_Flag", "Below_Hurdle_Flag"]], use_container_width=True, hide_index=True)

with tab6:
    st.subheader("Portfolio Data")
    show = df.copy()
    show["Tx RoE"] = show["Tx_RoE"].apply(pct)
    st.dataframe(show, use_container_width=True)
