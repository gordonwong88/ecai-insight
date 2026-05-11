import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="EC-AI Banking Engine v0.4.3", layout="wide", initial_sidebar_state="expanded")

LOW_NIM_THRESHOLD_BPS = 30
TX_ROE_HURDLE = 0.15

NAVY = "#071E3D"
NAVY_2 = "#0B2F55"
TEAL = "#1C7C7D"
BLUE_GREY = "#415A6B"
LIGHT_BG = "#F5F7FA"
CARD_BORDER = "#D9E2EC"
TEXT = "#111827"
MUTED = "#6B7280"
RED = "#B91C1C"
LIGHT_RED = "#FCA5A5"
LIGHT_GREEN = "#BBF7D0"
GREEN = "#16A34A"

st.markdown(f"""
<style>
.stApp {{ background-color: {LIGHT_BG}; color: {TEXT}; font-family: Inter, Arial, sans-serif; }}
.ec-hero {{ background: linear-gradient(135deg, {NAVY} 0%, {NAVY_2} 55%, {TEAL} 100%); border-radius: 20px; padding: 28px 34px; color: white; margin-bottom: 18px; box-shadow: 0 8px 22px rgba(7, 30, 61, 0.16); }}
.ec-hero h1 {{ font-size: 36px; line-height: 1.15; margin: 0 0 8px 0; font-weight: 800; letter-spacing: -0.02em; }}
.ec-hero p {{ font-size: 16px; line-height: 1.45; opacity: 0.92; margin: 0; }}
.ec-section-title {{ font-size: 22px; font-weight: 800; color: {NAVY}; margin: 8px 0 10px 0; }}
.ec-subtitle {{ color: {MUTED}; font-size: 14px; margin-top: -4px; margin-bottom: 16px; }}
div[data-testid="stMetric"] {{ background-color: white; border: 1px solid {CARD_BORDER}; padding: 14px 14px; border-radius: 16px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }}
div[data-testid="stMetricLabel"] {{ font-size: 13px; color: {MUTED}; }}
div[data-testid="stMetricValue"] {{ font-size: 24px; font-weight: 800; color: {NAVY}; }}
button[data-baseweb="tab"] {{ font-size: 16px !important; font-weight: 750 !important; padding: 12px 18px !important; margin-right: 4px !important; border-radius: 12px 12px 0 0 !important; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color: {NAVY} !important; background-color: #FFFFFF !important; border-bottom: 3px solid {TEAL} !important; }}
button[data-baseweb="tab"][aria-selected="false"] {{ color: {BLUE_GREY} !important; }}
.ec-card {{ background: white; border: 1px solid {CARD_BORDER}; border-radius: 16px; padding: 16px 18px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }}
.ec-alert-title {{ font-weight: 800; color: {NAVY}; font-size: 16px; margin-bottom: 6px; }}
.ec-alert-text {{ color: {TEXT}; font-size: 14px; line-height: 1.45; }}
</style>
""", unsafe_allow_html=True)

def money(x):
    try: x = float(x)
    except Exception: return "-"
    sign = "-" if x < 0 else ""; x = abs(x)
    if x >= 1_000_000_000: return f"{sign}${x/1_000_000_000:,.1f}B"
    if x >= 1_000_000: return f"{sign}${x/1_000_000:,.1f}M"
    if x >= 1_000: return f"{sign}${x/1_000:,.1f}K"
    return f"{sign}${x:,.0f}"

def pct(x):
    try: return f"{float(x)*100:.1f}%"
    except Exception: return "-"

def safe_div(a, b):
    try:
        if b == 0 or pd.isna(b): return np.nan
        return a / b
    except Exception: return np.nan

def tx_roe_color(v):
    if pd.isna(v): return "#E5E7EB"
    if v < 0.10: return RED
    if v < 0.15: return LIGHT_RED
    if v < 0.20: return LIGHT_GREEN
    return GREEN

def tx_roe_status_label(v):
    if pd.isna(v): return "N/A"
    if v < 0.10: return "Critical"
    if v < 0.15: return "Below Hurdle"
    if v < 0.20: return "Acceptable"
    return "Strong"

@st.cache_data
def make_demo_data(n=180, seed=7):
    rng = np.random.default_rng(seed)
    countries = ["Hong Kong", "Singapore", "Japan", "Korea", "Taiwan", "Australia"]
    products = ["Term Loan", "Revolver", "Trade Finance", "Deposit", "FX", "Guarantee"]
    rms = ["RM A", "RM B", "RM C", "RM D", "RM E", "RM F"]
    sectors = ["Property", "Technology", "Retail", "Logistics", "Energy", "Healthcare", "Manufacturing", "Financial Institutions"]
    clients = ["Sample Property Group", "Sample Tech Holdings", "Sample Retail Ltd", "Sample Logistics Co", "Sample Energy Corp", "Sample Healthcare Group", "Sample Manufacturing Ltd", "Sample Financial Holdings", "Sample Infrastructure Co", "Sample Consumer Group", "Sample Shipping Ltd", "Sample Telecom Group", "Sample Trading Co", "Sample Industrials Ltd"]
    rows = []
    for i in range(n):
        country = rng.choice(countries, p=[0.20,0.17,0.17,0.16,0.15,0.15])
        product = rng.choice(products, p=[0.30,0.22,0.14,0.12,0.12,0.10])
        client, sector, rm = rng.choice(clients), rng.choice(sectors), rng.choice(rms)
        limit = int(rng.integers(80,1500))*1_000_000
        lending_drawn = limit * rng.uniform(0.15,0.92)
        if product == "Revolver": nim_bps = rng.choice([18,24,28,36,48,65], p=[0.18,0.22,0.18,0.20,0.14,0.08])
        elif product == "Term Loan": nim_bps = rng.choice([25,35,55,80,110,140], p=[0.10,0.18,0.26,0.22,0.16,0.08])
        elif product == "Trade Finance": nim_bps = rng.choice([35,60,90,120,160], p=[0.15,0.25,0.25,0.22,0.13])
        elif product == "Deposit": nim_bps = rng.choice([20,40,70,100], p=[0.20,0.30,0.30,0.20])
        else: nim_bps = rng.choice([30,55,85,120,180], p=[0.15,0.25,0.25,0.22,0.13])
        rwa_density = rng.choice([0.35,0.50,0.65,0.85,1.00,1.20], p=[0.15,0.18,0.22,0.22,0.15,0.08])
        rwa = lending_drawn * rwa_density
        nii = lending_drawn * nim_bps / 10000
        fee = int(rng.integers(0,12))*400_000
        revenue = nii + fee
        tx_roe_target = rng.choice([0.06,0.11,0.14,0.17,0.22,0.28], p=[0.15,0.18,0.17,0.22,0.18,0.10])
        niat = rwa * tx_roe_target * rng.uniform(0.85,1.15)
        deposit = int(rng.integers(0,900))*1_000_000
        if product == "Deposit": deposit = int(rng.integers(300,2500))*1_000_000
        rows.append({"Month":"2026-04","Client":client,"Country":country,"RM":rm,"Sector":sector,"Product":product,"Facility_ID":f"FAC-{1000+i}","Deal_ID":f"DEAL-{2000+i}","Limit":round(limit,0),"Lending_Drawn":round(lending_drawn,0),"RWA":round(rwa,0),"NIM_bps":round(float(nim_bps),1),"Net_Interest_Income":round(nii,0),"Fee_Income":round(fee,0),"Total_Revenue":round(revenue,0),"NIAT":round(niat,0),"Deposit_Balance":round(deposit,0)})
    return pd.DataFrame(rows)

def normalize_columns(df):
    df = df.copy(); df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]; return df

def ensure_metrics(df):
    df = normalize_columns(df)
    required = ["Client","Country","RM","Product","Lending_Drawn","RWA","Total_Revenue","NIAT"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}"); st.stop()
    for c in ["Limit","Lending_Drawn","RWA","Total_Revenue","NIAT","Deposit_Balance","NIM_bps","Net_Interest_Income"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    if "NIM_bps" not in df.columns:
        df["NIM_bps"] = df.apply(lambda r: safe_div(r.get("Net_Interest_Income", 0), r["Lending_Drawn"])*10000, axis=1)
    if "Deposit_Balance" not in df.columns: df["Deposit_Balance"] = 0
    if "Sector" not in df.columns: df["Sector"] = "General"
    if "Deal_ID" not in df.columns: df["Deal_ID"] = [f"DEAL-{i+1}" for i in range(len(df))]
    df["Tx_RoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    df["Revenue_per_RWA"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    df["Low_NIM_Flag"] = df["NIM_bps"] < LOW_NIM_THRESHOLD_BPS
    df["Below_Hurdle_Flag"] = df["Tx_RoE"] < TX_ROE_HURDLE
    def status(row):
        if row["Low_NIM_Flag"] and row["Below_Hurdle_Flag"]: return "Critical: Low NIM + Below Hurdle"
        if row["Low_NIM_Flag"]: return "Low NIM: Review / Sell-down"
        if row["Below_Hurdle_Flag"]: return "Below Tx RoE Hurdle"
        return "Above Hurdle"
    df["Status"] = df.apply(status, axis=1)
    return df

def grouped_view(df, group_cols):
    g = df.groupby(group_cols, dropna=False).agg({"Total_Revenue":"sum","Lending_Drawn":"sum","Deposit_Balance":"sum","RWA":"sum","NIAT":"sum","Low_NIM_Flag":"sum","Below_Hurdle_Flag":"sum"}).reset_index()
    nim = []
    for _, x in df.groupby(group_cols, dropna=False):
        nim.append(safe_div((x["NIM_bps"]*x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum()))
    g["NIM_bps"] = nim
    g["Tx_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Revenue_per_RWA"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    return g.sort_values("Total_Revenue", ascending=False)

def bar_chart(df, x, y, title, color=NAVY):
    chart_df = df.copy(); chart_df["Label"] = chart_df[y].apply(money)
    fig = px.bar(chart_df, x=x, y=y, text="Label", title=title, color_discrete_sequence=[color])
    max_y = chart_df[y].max() if len(chart_df) else 0
    step = 1_000_000_000; tick_max = max(step, np.ceil(max_y/step)*step)
    ticks = list(np.arange(0, tick_max+step, step)); labels = ["0"] + [f"{v/1_000_000_000:.1f}B" for v in ticks[1:]]
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=390, margin=dict(l=35,r=25,t=55,b=55), plot_bgcolor="white", paper_bgcolor="white", font=dict(color=TEXT, family="Inter, Arial, sans-serif"), title=dict(font=dict(size=18, color=NAVY)), yaxis=dict(tickvals=ticks, ticktext=labels, gridcolor="#E5E7EB"), xaxis=dict(tickangle=-25))
    return fig

def combo_exposure_txroe(df):
    ranked = grouped_view(df, ["Client"]).sort_values("Lending_Drawn", ascending=False).head(15)
    ranked["Tx RoE %"] = ranked["Tx_RoE"] * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ranked["Client"], y=ranked["Lending_Drawn"], name="Lending Drawn", marker_color=NAVY, yaxis="y1", text=[money(v) for v in ranked["Lending_Drawn"]], textposition="outside", cliponaxis=False))
    fig.add_trace(go.Scatter(x=ranked["Client"], y=ranked["Tx RoE %"], name="Tx RoE %", mode="lines+markers+text", marker=dict(color=TEAL, size=9), line=dict(color=TEAL, width=3), yaxis="y2", text=[f"{v:.1f}%" for v in ranked["Tx RoE %"]], textposition="top center"))
    max_y = ranked["Lending_Drawn"].max() if len(ranked) else 0
    step = 1_000_000_000; tick_max = max(step, np.ceil(max_y/step)*step)
    ticks = list(np.arange(0, tick_max+step, step)); labels = ["0"] + [f"{v/1_000_000_000:.1f}B" for v in ticks[1:]]
    fig.update_layout(title="Top Exposure Relationships: Lending Drawn vs Tx RoE", height=500, margin=dict(l=35,r=35,t=60,b=110), xaxis=dict(tickangle=-35), yaxis=dict(title="Lending Drawn", tickvals=ticks, ticktext=labels, gridcolor="#E5E7EB"), yaxis2=dict(title="Tx RoE %", overlaying="y", side="right", ticksuffix="%", range=[0, max(30, ranked["Tx RoE %"].max()+5)]), plot_bgcolor="white", paper_bgcolor="white", legend=dict(orientation="h", y=1.10), font=dict(family="Inter, Arial, sans-serif", color=TEXT))
    return fig

def tx_roe_heatmap_table(df, group_col):
    g = grouped_view(df, [group_col]).copy()
    g["Revenue"] = g["Total_Revenue"].apply(money); g["Lending Drawn"] = g["Lending_Drawn"].apply(money); g["RWA Display"] = g["RWA"].apply(money); g["NIM"] = g["NIM_bps"].round(1).astype(str) + " bps"; g["Tx RoE"] = g["Tx_RoE"].apply(pct); g["Status"] = g["Tx_RoE"].apply(tx_roe_status_label)
    show = g[[group_col,"Revenue","Lending Drawn","RWA Display","NIM","Tx RoE","Status"]].copy()
    def style_row(row):
        raw = g.loc[row.name, "Tx_RoE"]; color = tx_roe_color(raw); text_color = "white" if color in [RED, GREEN] else "#111827"
        styles = [""] * len(row); styles[-2] = f"background-color:{color}; color:{text_color}; font-weight:800;"; styles[-1] = f"background-color:{color}; color:{text_color}; font-weight:800;"; return styles
    st.dataframe(show.style.apply(style_row, axis=1), use_container_width=True, hide_index=True)

def executive_watchlist(df):
    watch = df[(df["Below_Hurdle_Flag"]) | (df["Low_NIM_Flag"])].copy()
    if watch.empty: return pd.DataFrame()
    watch["Severity"] = np.select([(watch["Tx_RoE"]<0.10)&(watch["Low_NIM_Flag"]),(watch["Tx_RoE"]<0.10),(watch["Low_NIM_Flag"]),(watch["Tx_RoE"]<0.15)], ["🔴 Critical","🔴 Low Tx RoE","🟠 Low NIM","🟡 Below Hurdle"], default="🟡 Monitor")
    watch = watch.sort_values(["Tx_RoE", "Lending_Drawn"], ascending=[True, False]).head(15)
    out = watch[["Severity","Client","Country","Product","Lending_Drawn","RWA","Total_Revenue","NIM_bps","Tx_RoE","Status"]].copy()
    out["Lending Drawn"] = out["Lending_Drawn"].apply(money); out["RWA"] = out["RWA"].apply(money); out["Revenue"] = out["Total_Revenue"].apply(money); out["NIM"] = out["NIM_bps"].round(1).astype(str) + " bps"; out["Tx RoE"] = out["Tx_RoE"].apply(pct)
    return out[["Severity","Client","Country","Product","Lending Drawn","RWA","Revenue","NIM","Tx RoE","Status"]]

def executive_summary(df):
    total_rev = df["Total_Revenue"].sum(); total_drawn = df["Lending_Drawn"].sum(); total_rwa = df["RWA"].sum(); total_niat = df["NIAT"].sum(); tx_roe = safe_div(total_niat,total_rwa)
    low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum(); below_hurdle_exposure = df.loc[df["Below_Hurdle_Flag"], "Lending_Drawn"].sum()
    top_country = grouped_view(df, ["Country"]).iloc[0]["Country"]; top_product = grouped_view(df, ["Product"]).iloc[0]["Product"]; weakest_country = grouped_view(df, ["Country"]).sort_values("Tx_RoE").iloc[0]["Country"]
    lines = [f"Total revenue is {money(total_rev)}, supported by lending drawn of {money(total_drawn)} and RWA of {money(total_rwa)}.", f"Portfolio Tx RoE is {pct(tx_roe)} against the 15.0% favourable hurdle.", f"Low-NIM exposure is {money(low_nim_exposure)}; below-hurdle exposure is {money(below_hurdle_exposure)}.", f"Top revenue contribution comes from {top_country} and {top_product}, while {weakest_country} requires profitability review."]
    actions = ["Prioritize relationships with high exposure, low Tx RoE and low NIM for repricing or sell-down review.", "Protect strong-return countries/products where Tx RoE is above 20% and revenue contribution is scalable.", "Use the watchlist as the management discussion queue for monthly portfolio review."]
    return lines, actions

st.markdown('<div class="ec-hero"><h1>EC-AI Banking Engine v0.4.3</h1><p>Tx RoE / NIM / Revenue Decision Intelligence for executive banking management.</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## EC-AI Banking Engine")
    st.caption("Demo-ready executive prototype")
    data_mode = st.radio("Data source", ["Use Built-in Demo Data", "Upload File"], index=0)
    uploaded = None
    if data_mode == "Upload File":
        uploaded = st.file_uploader("Upload banking performance file", type=["csv", "xlsx"])
        st.caption("Required: Client, Country, RM, Product, Lending_Drawn, RWA, Total_Revenue, NIAT")
    st.markdown("---")
    st.markdown("### Thresholds")
    st.write("Tx RoE hurdle: **15%**")
    st.write("Low NIM: **<30bps**")
    st.markdown("---")
    st.caption("v0.4.3: demo data + clearer executive UX + watchlist")

if data_mode == "Use Built-in Demo Data": raw = make_demo_data()
else:
    if uploaded is None:
        st.info("Upload a banking performance file or switch to built-in demo data."); st.stop()
    raw = pd.read_excel(uploaded) if uploaded.name.lower().endswith(".xlsx") else pd.read_csv(uploaded)

df = ensure_metrics(raw)

st.markdown('<div class="ec-section-title">Executive Snapshot</div>', unsafe_allow_html=True)
st.markdown('<div class="ec-subtitle">Portfolio-level revenue, exposure, deposits, Tx RoE and pricing risk.</div>', unsafe_allow_html=True)

total_revenue = df["Total_Revenue"].sum(); total_drawn = df["Lending_Drawn"].sum(); total_deposit = df["Deposit_Balance"].sum(); total_rwa = df["RWA"].sum(); total_niat = df["NIAT"].sum(); portfolio_tx_roe = safe_div(total_niat,total_rwa); low_nim_exposure = df.loc[df["Low_NIM_Flag"], "Lending_Drawn"].sum()

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Total Revenue", money(total_revenue)); c2.metric("Lending Drawn", money(total_drawn)); c3.metric("Deposit Balance", money(total_deposit)); c4.metric("Tx RoE", pct(portfolio_tx_roe)); c5.metric("Low NIM Exposure", money(low_nim_exposure))

tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["CEO Dashboard","Revenue Engine","Pricing & NIM Risk","Capital Efficiency","Country Portfolio","Portfolio Data"])

with tab1:
    st.markdown('<div class="ec-section-title">CEO Dashboard</div>', unsafe_allow_html=True)
    lines, actions = executive_summary(df)
    left, right = st.columns([1.05,0.95], gap="large")
    with left:
        st.markdown('<div class="ec-card"><div class="ec-alert-title">Management Summary</div>', unsafe_allow_html=True)
        for line in lines: st.markdown(f'<div class="ec-alert-text">• {line}</div>', unsafe_allow_html=True)
        st.markdown('<br><div class="ec-alert-title">Recommended Actions</div>', unsafe_allow_html=True)
        for action in actions: st.markdown(f'<div class="ec-alert-text">• {action}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="ec-card"><div class="ec-alert-title">Tx RoE Heatmap by Country</div>', unsafe_allow_html=True)
        tx_roe_heatmap_table(df, "Country")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("### Executive Watchlist")
    watch = executive_watchlist(df)
    st.success("No below-hurdle or low-NIM relationships detected.") if watch.empty else st.dataframe(watch, use_container_width=True, hide_index=True)
    st.markdown("### Revenue by Country")
    st.plotly_chart(bar_chart(grouped_view(df,["Country"]).head(8), "Country", "Total_Revenue", "CEO Dashboard — Revenue by Country"), use_container_width=True, key="plot_ceo_revenue_country_v044")

with tab2:
    st.markdown('<div class="ec-section-title">Revenue Engine</div>', unsafe_allow_html=True)
    a,b = st.columns(2, gap="large")
    with a: st.plotly_chart(bar_chart(grouped_view(df,["Country"]).head(8), "Country", "Total_Revenue", "Revenue Engine — Revenue by Country"), use_container_width=True, key="plot_revenue_country_v044")
    with b: st.plotly_chart(bar_chart(grouped_view(df,["Product"]).head(8), "Product", "Total_Revenue", "Revenue by Product Type", BLUE_GREY), use_container_width=True, key="plot_revenue_product_v044")
    st.markdown("### Top Revenue Relationships")
    client = grouped_view(df,["Client"]).head(15); view = client.copy(); view["Revenue"] = view["Total_Revenue"].apply(money); view["Lending Drawn"] = view["Lending_Drawn"].apply(money); view["Tx RoE"] = view["Tx_RoE"].apply(pct); view["NIM"] = view["NIM_bps"].round(1).astype(str)+" bps"
    st.dataframe(view[["Client","Revenue","Lending Drawn","NIM","Tx RoE"]], use_container_width=True, hide_index=True)

with tab3:
    st.markdown('<div class="ec-section-title">Pricing & NIM Risk</div>', unsafe_allow_html=True)
    low = df[df["Low_NIM_Flag"]].copy(); a,b,c = st.columns(3); a.metric("Low NIM Deals", len(low)); b.metric("Low NIM Exposure", money(low["Lending_Drawn"].sum() if len(low) else 0)); c.metric("Threshold", f"{LOW_NIM_THRESHOLD_BPS} bps")
    if len(low):
        low["Lending Drawn"] = low["Lending_Drawn"].apply(money); low["Revenue"] = low["Total_Revenue"].apply(money); low["Tx RoE"] = low["Tx_RoE"].apply(pct); low["NIM"] = low["NIM_bps"].round(1).astype(str)+" bps"
        st.dataframe(low[["Deal_ID","Client","Country","Product","Lending Drawn","Revenue","NIM","Tx RoE","Status"]], use_container_width=True, hide_index=True)
    else: st.success("No low-NIM deals detected.")

with tab4:
    st.markdown('<div class="ec-section-title">Capital Efficiency</div>', unsafe_allow_html=True)
    st.plotly_chart(combo_exposure_txroe(df), use_container_width=True, key="plot_capital_exposure_txroe_v044")
    st.markdown("### Capital Efficiency Watchlist")
    watch = executive_watchlist(df); st.success("No watchlist relationships detected.") if watch.empty else st.dataframe(watch, use_container_width=True, hide_index=True)

with tab5:
    st.markdown('<div class="ec-section-title">Country Portfolio</div>', unsafe_allow_html=True)
    st.markdown("### Country-Level Portfolio Quality")
    tx_roe_heatmap_table(df, "Country")
    st.markdown("### Country Portfolio Table")
    country = grouped_view(df,["Country"]).copy(); country["Revenue"] = country["Total_Revenue"].apply(money); country["Lending Drawn"] = country["Lending_Drawn"].apply(money); country["Deposits"] = country["Deposit_Balance"].apply(money); country["RWA"] = country["RWA"].apply(money); country["Tx RoE"] = country["Tx_RoE"].apply(pct); country["NIM"] = country["NIM_bps"].round(1).astype(str)+" bps"
    st.dataframe(country[["Country","Revenue","Lending Drawn","Deposits","RWA","NIM","Tx RoE","Low_NIM_Flag","Below_Hurdle_Flag"]], use_container_width=True, hide_index=True)

with tab6:
    st.markdown('<div class="ec-section-title">Portfolio Data</div>', unsafe_allow_html=True)
    show = df.copy(); show["Tx RoE"] = show["Tx_RoE"].apply(pct)
    st.dataframe(show, use_container_width=True)
