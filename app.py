import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="EC-AI Banking Engine v0.6", layout="wide", initial_sidebar_state="expanded")

# Demo thresholds only. Keep these configurable for client pilots.
PRICING_FLOOR_BPS = 30
RELATIONSHIP_ROE_FLOOR = 0.12

# EC-AI Banking Visual Language v0.1 — dark navy / blue grey / steel palette
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
CHART_PALETTE = [NAVY, EXEC_BLUE, STEEL, BLUE_GREY, "#8A98A6", "#B8C2CC", LIGHT_STEEL]

st.markdown(f"""
<style>
.stApp {{ background-color: {LIGHT_BG}; color: {TEXT}; font-family: Inter, Arial, sans-serif; }}
.ec-hero {{ background: linear-gradient(135deg, {NAVY} 0%, {NAVY_2} 62%, {EXEC_BLUE} 100%); border-radius: 20px; padding: 28px 34px; color: white; margin-bottom: 18px; box-shadow: 0 12px 26px rgba(11, 31, 51, 0.18); }}
.ec-hero h1 {{ font-size: 36px; line-height: 1.15; margin: 0 0 8px 0; font-weight: 800; letter-spacing: -0.02em; }}
.ec-hero p {{ font-size: 16px; line-height: 1.45; opacity: 0.92; margin: 0; }}
.ec-section-title {{ font-size: 22px; font-weight: 800; color: {NAVY}; margin: 8px 0 10px 0; }}
.ec-subtitle {{ color: {MUTED}; font-size: 14px; margin-top: -4px; margin-bottom: 16px; }}
div[data-testid="stMetric"] {{ background-color: white; border: 1px solid {CARD_BORDER}; padding: 14px 14px; border-radius: 16px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }}
div[data-testid="stMetricLabel"] {{ font-size: 13px; color: {MUTED}; }}
div[data-testid="stMetricValue"] {{ font-size: 24px; font-weight: 800; color: {NAVY}; }}
button[data-baseweb="tab"] {{ font-size: 16px !important; font-weight: 750 !important; padding: 12px 18px !important; margin-right: 4px !important; border-radius: 12px 12px 0 0 !important; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color: {NAVY} !important; background-color: #FFFFFF !important; border-bottom: 3px solid {EXEC_BLUE} !important; }}
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
    if v < 0.15: return "Below Profit Floor"
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
        tier = rng.choice(["Strategic", "Core", "Emerging", "Flow"], p=[0.25,0.35,0.25,0.15])
        ltm_group_roe = safe_div(niat, rwa)
        three_year_avg_groe = max(0.01, ltm_group_roe * rng.uniform(0.80, 1.20))
        rows.append({"Month":"2026-04","Client":client,"Client_Tier":tier,"Country":country,"RM":rm,"Sector":sector,"Product":product,"Facility_ID":f"FAC-{1000+i}","Deal_ID":f"DEAL-{2000+i}","Limit":round(limit,0),"Lending_Drawn":round(lending_drawn,0),"RWA":round(rwa,0),"NIM_bps":round(float(nim_bps),1),"Net_Interest_Income":round(nii,0),"Fee_Income":round(fee,0),"Total_Revenue":round(revenue,0),"NIAT":round(niat,0),"LTM_Group_RoE":round(ltm_group_roe,4),"ThreeY_Avg_GRoE":round(three_year_avg_groe,4),"Deposit_Balance":round(deposit,0)})
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
    if "Client_Tier" not in df.columns: df["Client_Tier"] = "Core"
    if "Deal_ID" not in df.columns: df["Deal_ID"] = [f"DEAL-{i+1}" for i in range(len(df))]
    if "LTM_Group_RoE" not in df.columns:
        df["LTM_Group_RoE"] = df.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    else:
        df["LTM_Group_RoE"] = pd.to_numeric(df["LTM_Group_RoE"], errors="coerce").fillna(0)
    if "ThreeY_Avg_GRoE" not in df.columns:
        df["ThreeY_Avg_GRoE"] = df["LTM_Group_RoE"]
    else:
        df["ThreeY_Avg_GRoE"] = pd.to_numeric(df["ThreeY_Avg_GRoE"], errors="coerce").fillna(0)
    df["Revenue_per_RWA"] = df.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    df["Pricing_Floor_Flag"] = df["NIM_bps"] < PRICING_FLOOR_BPS
    df["Below_Relationship_RoE_Flag"] = df["LTM_Group_RoE"] < RELATIONSHIP_ROE_FLOOR
    df["Status"] = "Healthy"
    return df

def grouped_view(df, group_cols):
    g = df.groupby(group_cols, dropna=False).agg({"Total_Revenue":"sum","Limit":"sum","Lending_Drawn":"sum","Deposit_Balance":"sum","RWA":"sum","NIAT":"sum","Pricing_Floor_Flag":"sum","Below_Relationship_RoE_Flag":"sum"}).reset_index()
    nim = []
    for _, x in df.groupby(group_cols, dropna=False):
        nim.append(safe_div((x["NIM_bps"]*x["Lending_Drawn"]).sum(), x["Lending_Drawn"].sum()))
    g["NIM_bps"] = nim
    g["LTM_Group_RoE"] = g.apply(lambda r: safe_div(r["NIAT"], r["RWA"]), axis=1)
    g["Revenue_per_RWA"] = g.apply(lambda r: safe_div(r["Total_Revenue"], r["RWA"]), axis=1)
    g["Utilization"] = g.apply(lambda r: safe_div(r["Lending_Drawn"], r["Limit"]), axis=1) if "Limit" in g.columns else np.nan
    return g.sort_values("Total_Revenue", ascending=False)

def rank_colors(n):
    """Premium rank-based colours: top item dark navy, next blue, others steel/grey."""
    base = [NAVY, EXEC_BLUE, STEEL, BLUE_GREY, "#8A98A6", "#AAB4BE", LIGHT_STEEL, "#E6EBF0"]
    return [base[min(i, len(base)-1)] for i in range(n)]

def bar_chart(df, x, y, title, color=NAVY):
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
    tick_max = max(step, np.ceil(max_y/step)*step)
    ticks = list(np.arange(0, tick_max+step, step))
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

def combo_exposure_txroe(df):
    ranked = grouped_view(df, ["Client"]).sort_values("Lending_Drawn", ascending=False).head(15)
    ranked["LTM Group RoE %"] = ranked["LTM_Group_RoE"] * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ranked["Client"], y=ranked["Lending_Drawn"], name="Lending Drawn", marker_color=NAVY, yaxis="y1", text=[money(v) for v in ranked["Lending_Drawn"]], textposition="outside", cliponaxis=False))
    fig.add_trace(go.Scatter(x=ranked["Client"], y=ranked["LTM Group RoE %"], name="LTM Group RoE %", mode="lines+markers+text", marker=dict(color=EXEC_BLUE, size=9), line=dict(color=EXEC_BLUE, width=3), yaxis="y2", text=[f"{v:.1f}%" for v in ranked["LTM Group RoE %"]], textposition="top center"))
    max_y = ranked["Lending_Drawn"].max() if len(ranked) else 0
    step = 1_000_000_000; tick_max = max(step, np.ceil(max_y/step)*step)
    ticks = list(np.arange(0, tick_max+step, step)); labels = ["0"] + [f"{v/1_000_000_000:.1f}B" for v in ticks[1:]]
    fig.update_layout(title="Capital Efficiency: Exposure vs LTM Group RoE", height=500, margin=dict(l=35,r=35,t=60,b=110), xaxis=dict(tickangle=-35), yaxis=dict(title="Lending Drawn", tickvals=ticks, ticktext=labels, gridcolor="#E5E7EB"), yaxis2=dict(title="LTM Group RoE %", overlaying="y", side="right", ticksuffix="%", range=[0, max(30, ranked["LTM Group RoE %"].max()+5)]), plot_bgcolor="white", paper_bgcolor="white", legend=dict(orientation="h", y=1.10), font=dict(family="Inter, Arial, sans-serif", color=TEXT))
    return fig

def tx_roe_heatmap_table(df, group_col):
    g = grouped_view(df, [group_col]).copy()
    g["Revenue"] = g["Total_Revenue"].apply(money); g["Lending Drawn"] = g["Lending_Drawn"].apply(money); g["RWA Display"] = g["RWA"].apply(money); g["NIM"] = g["NIM_bps"].round(1).astype(str) + " bps"; g["LTM Group RoE"] = g["LTM_Group_RoE"].apply(pct); g["Status"] = g["LTM_Group_RoE"].apply(tx_roe_status_label)
    show = g[[group_col,"Revenue","Lending Drawn","RWA Display","NIM","LTM Group RoE","Status"]].copy()
    def style_row(row):
        raw = g.loc[row.name, "LTM_Group_RoE"]; color = tx_roe_color(raw); text_color = "white" if color in [RED, GREEN] else "#111827"
        styles = [""] * len(row); styles[-2] = f"background-color:{color}; color:{text_color}; font-weight:800;"; styles[-1] = f"background-color:{color}; color:{text_color}; font-weight:800;"; return styles
    st.dataframe(show.style.apply(style_row, axis=1), use_container_width=True, hide_index=True)

def executive_watchlist(df):
    watch = df[(df["Below_Relationship_RoE_Flag"]) | (df["Pricing_Floor_Flag"])].copy()
    if watch.empty: return pd.DataFrame()
    watch["Severity"] = np.select([(watch["LTM_Group_RoE"]<0.10)&(watch["Pricing_Floor_Flag"]),(watch["LTM_Group_RoE"]<0.10),(watch["Pricing_Floor_Flag"]),(watch["LTM_Group_RoE"]<0.15)], ["🔴 Critical","🔴 Low LTM Group RoE","🟠 Pricing Review","🟡 Below Profit Floor"], default="🟡 Monitor")
    watch = watch.sort_values(["LTM_Group_RoE", "Lending_Drawn"], ascending=[True, False]).head(15)
    out = watch[["Severity","Client","Country","Product","Lending_Drawn","RWA","Total_Revenue","NIM_bps","LTM_Group_RoE","Status"]].copy()
    out["Lending Drawn"] = out["Lending_Drawn"].apply(money); out["RWA"] = out["RWA"].apply(money); out["Revenue"] = out["Total_Revenue"].apply(money); out["NIM"] = out["NIM_bps"].round(1).astype(str) + " bps"; out["LTM Group RoE"] = out["LTM_Group_RoE"].apply(pct)
    return out[["Severity","Client","Country","Product","Lending Drawn","RWA","Revenue","NIM","LTM Group RoE","Status"]]

def executive_summary(df):
    total_rev = df["Total_Revenue"].sum(); total_drawn = df["Lending_Drawn"].sum(); total_rwa = df["RWA"].sum(); total_niat = df["NIAT"].sum(); tx_roe = safe_div(total_niat,total_rwa)
    low_nim_exposure = df.loc[df["Pricing_Floor_Flag"], "Lending_Drawn"].sum(); below_profit_floor_exposure = df.loc[df["Below_Relationship_RoE_Flag"], "Lending_Drawn"].sum()
    top_country = grouped_view(df, ["Country"]).iloc[0]["Country"]; top_product = grouped_view(df, ["Product"]).iloc[0]["Product"]; weakest_country = grouped_view(df, ["Country"]).sort_values("LTM_Group_RoE").iloc[0]["Country"]
    lines = [f"Total revenue is {money(total_rev)}, supported by lending drawn of {money(total_drawn)} and RWA of {money(total_rwa)}.", f"Portfolio LTM Group RoE is {pct(tx_roe)} against the configurable profitability floor.", f"Pricing-floor exposure is {money(low_nim_exposure)}; below-profitability floor exposure is {money(below_profit_floor_exposure)}.", f"Top revenue contribution comes from {top_country} and {top_product}, while {weakest_country} requires profitability review."]
    actions = ["Prioritize relationships with high exposure, profitability pressure and pricing review for repricing or sell-down review.", "Protect strong-return countries/products with strong LTM Group RoE and revenue contribution is scalable.", "Use the watchlist as the management discussion queue for monthly portfolio review."]
    return lines, actions

st.markdown('<div class="ec-hero"><h1>EC-AI Banking Engine v0.6</h1><p>Portfolio profitability / pricing / revenue decision intelligence for banking management.</p></div>', unsafe_allow_html=True)

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
    st.caption("Demo thresholds only — not copied from any bank. Adjust for each client / pilot.")
    roe_floor = st.slider("Relationship profitability floor", 0.05, 0.30, RELATIONSHIP_ROE_FLOOR, 0.01, format="%.2f")
    pricing_floor = st.slider("Pricing / margin floor (bps)", 0, 150, PRICING_FLOOR_BPS, 5)
    st.markdown("---")
    st.caption("v0.6: v0.5 visual base + Relationship 360 + configurable thresholds")

if data_mode == "Use Built-in Demo Data": raw = make_demo_data()
else:
    if uploaded is None:
        st.info("Upload a banking performance file or switch to built-in demo data."); st.stop()
    raw = pd.read_excel(uploaded) if uploaded.name.lower().endswith(".xlsx") else pd.read_csv(uploaded)

df = ensure_metrics(raw)
# Apply configurable demo thresholds after data is prepared.
df["Pricing_Floor_Flag"] = df["NIM_bps"] < pricing_floor
df["Below_Relationship_RoE_Flag"] = df["LTM_Group_RoE"] < roe_floor
df["Status"] = df.apply(lambda row: "Critical: Pricing + Profitability" if row["Pricing_Floor_Flag"] and row["Below_Relationship_RoE_Flag"] else ("Pricing Review" if row["Pricing_Floor_Flag"] else ("Profitability Review" if row["Below_Relationship_RoE_Flag"] else "Healthy")), axis=1)

st.markdown('<div class="ec-section-title">Executive Snapshot</div>', unsafe_allow_html=True)
st.markdown('<div class="ec-subtitle">Portfolio-level revenue, exposure, deposits, LTM Group RoE and pricing risk.</div>', unsafe_allow_html=True)

total_revenue = df["Total_Revenue"].sum(); total_drawn = df["Lending_Drawn"].sum(); total_deposit = df["Deposit_Balance"].sum(); total_rwa = df["RWA"].sum(); total_niat = df["NIAT"].sum(); portfolio_tx_roe = safe_div(total_niat,total_rwa); low_nim_exposure = df.loc[df["Pricing_Floor_Flag"], "Lending_Drawn"].sum()

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Total Revenue", money(total_revenue)); c2.metric("Lending Drawn", money(total_drawn)); c3.metric("Deposit Balance", money(total_deposit)); c4.metric("LTM Group RoE", pct(portfolio_tx_roe)); c5.metric("Pricing Review Exposure", money(low_nim_exposure))

tab1,tab2,tab3,tab4,tab5,tab6,tab7 = st.tabs(["CEO Dashboard","Revenue Engine","Relationship 360","Pricing & NIM Risk","Capital Efficiency","Country Portfolio","Portfolio Data"])

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
        st.markdown('<div class="ec-card"><div class="ec-alert-title">LTM Group RoE Heatmap by Country</div>', unsafe_allow_html=True)
        tx_roe_heatmap_table(df, "Country")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("### Executive Watchlist")
    watch = executive_watchlist(df)
    if watch.empty:
        st.success("No pricing / profitability watchlist relationships detected.")
    else:
        st.dataframe(watch, use_container_width=True, hide_index=True)
    st.markdown("### Revenue by Country")
    st.plotly_chart(bar_chart(grouped_view(df,["Country"]).head(8), "Country", "Total_Revenue", "CEO Dashboard — Revenue by Country"), use_container_width=True, key="plot_ceo_revenue_country_v044")

with tab2:
    st.markdown('<div class="ec-section-title">Revenue Engine</div>', unsafe_allow_html=True)
    a,b = st.columns(2, gap="large")
    with a: st.plotly_chart(bar_chart(grouped_view(df,["Country"]).head(8), "Country", "Total_Revenue", "Revenue Engine — Revenue by Country"), use_container_width=True, key="plot_revenue_country_v044")
    with b: st.plotly_chart(bar_chart(grouped_view(df,["Product"]).head(8), "Product", "Total_Revenue", "Revenue by Product Type", BLUE_GREY), use_container_width=True, key="plot_revenue_product_v044")
    st.markdown('<div class="ec-section-title">Top Revenue Relationships</div>', unsafe_allow_html=True)
    client = grouped_view(df,["Client"]).head(15); view = client.copy(); view["Revenue"] = view["Total_Revenue"].apply(money); view["Facility Limit"] = view["Limit"].apply(money); view["Lending Drawn"] = view["Lending_Drawn"].apply(money); view["Utilization"] = view["Utilization"].apply(pct); view["LTM Group RoE"] = view["LTM_Group_RoE"].apply(pct); view["NIM"] = view["NIM_bps"].round(1).astype(str)+" bps"
    st.dataframe(view[["Client","Revenue","Facility Limit","Lending Drawn","Utilization","NIM","LTM Group RoE"]], use_container_width=True, hide_index=True)

with tab3:
    st.markdown('<div class="ec-section-title">Relationship 360</div>', unsafe_allow_html=True)
    st.markdown('<div class="ec-subtitle">Single-client relationship view: limits, utilisation, revenue, deposits, profitability and product penetration.</div>', unsafe_allow_html=True)

    client_list = sorted(df["Client"].dropna().unique())
    selected_client = st.selectbox("Select Relationship", client_list, key="relationship_360_client_selector")
    client_df = df[df["Client"] == selected_client].copy()

    rel_country = client_df["Country"].mode().iloc[0] if not client_df["Country"].mode().empty else "-"
    rel_tier = client_df["Client_Tier"].mode().iloc[0] if "Client_Tier" in client_df.columns and not client_df["Client_Tier"].mode().empty else "Core"
    rel_sector = client_df["Sector"].mode().iloc[0] if "Sector" in client_df.columns and not client_df["Sector"].mode().empty else "General"

    total_limit = client_df["Limit"].sum()
    total_drawn = client_df["Lending_Drawn"].sum()
    total_revenue = client_df["Total_Revenue"].sum()
    total_deposit = client_df["Deposit_Balance"].sum()
    total_rwa = client_df["RWA"].sum()
    total_niat = client_df["NIAT"].sum()
    rel_groe = safe_div(total_niat, total_rwa)
    rel_util = safe_div(total_drawn, total_limit)

    st.markdown(f"""
    <div class="ec-card">
      <div class="ec-alert-title">{selected_client}</div>
      <div class="ec-alert-text">Country: <b>{rel_country}</b> &nbsp; | &nbsp; Sector: <b>{rel_sector}</b> &nbsp; | &nbsp; Tier: <b>{rel_tier}</b></div>
    </div>
    """, unsafe_allow_html=True)

    r1,r2,r3,r4,r5 = st.columns(5)
    r1.metric("Facility Limit", money(total_limit))
    r2.metric("Lending Drawn", money(total_drawn))
    r3.metric("Utilization", pct(rel_util))
    r4.metric("Revenue", money(total_revenue))
    r5.metric("LTM Group RoE", pct(rel_groe))

    r6,r7,r8 = st.columns(3)
    r6.metric("Deposit Balance", money(total_deposit))
    r7.metric("RWA", money(total_rwa))
    r8.metric("Product Count", str(client_df["Product"].nunique()))

    left, right = st.columns([1.05,0.95], gap="large")

    with left:
        st.markdown("### Product Penetration")
        product_view = client_df.groupby("Product", as_index=False).agg({"Total_Revenue":"sum", "Limit":"sum", "Lending_Drawn":"sum"}).sort_values("Total_Revenue", ascending=False)
        product_view["Label"] = product_view["Total_Revenue"].apply(money)
        fig_rel = px.bar(product_view, x="Product", y="Total_Revenue", text="Label", title="Revenue by Product")
        fig_rel.update_traces(marker_color=rank_colors(len(product_view)), textposition="outside", cliponaxis=False)
        fig_rel.update_layout(height=410, plot_bgcolor="white", paper_bgcolor="white", xaxis_tickangle=0, showlegend=False, yaxis=dict(gridcolor="#E9EEF3"), title=dict(font=dict(size=18, color=NAVY)))
        st.plotly_chart(fig_rel, use_container_width=True, key="relationship_360_product_penetration")

    with right:
        st.markdown("### Banker Commentary")
        comments = []
        if rel_groe >= roe_floor + 0.08:
            comments.append("Relationship demonstrates strong profitability and strategic value relative to the configured floor.")
        elif rel_groe >= roe_floor:
            comments.append("Relationship profitability is acceptable, with selective growth opportunities.")
        else:
            comments.append("Relationship profitability requires management review and optimisation.")

        if rel_util < 0.40:
            comments.append("Low utilisation suggests wallet expansion, activation or cross-sell opportunity.")
        elif rel_util > 0.80:
            comments.append("High utilisation indicates deep lending engagement; monitor limit headroom and concentration.")

        if total_deposit < total_drawn * 0.20:
            comments.append("Deposit penetration appears relatively weak versus lending exposure.")
        else:
            comments.append("Deposit contribution provides balance sheet support to the relationship.")

        if client_df["Product"].nunique() <= 2:
            comments.append("Product penetration is narrow; consider trade, FX, cash or markets cross-sell where relevant.")

        st.markdown('<div class="ec-card">', unsafe_allow_html=True)
        for c in comments:
            st.markdown(f'<div class="ec-alert-text">• {c}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Relationship Product Table")
    table = product_view.copy()
    table["Facility Limit"] = table["Limit"].apply(money)
    table["Lending Drawn"] = table["Lending_Drawn"].apply(money)
    table["Revenue"] = table["Total_Revenue"].apply(money)
    table["Utilization"] = table.apply(lambda r: pct(safe_div(r["Lending_Drawn"], r["Limit"])), axis=1)
    st.dataframe(table[["Product", "Facility Limit", "Lending Drawn", "Utilization", "Revenue"]], use_container_width=True, hide_index=True)

with tab4:
    st.markdown('<div class="ec-section-title">Pricing & NIM Risk</div>', unsafe_allow_html=True)
    low = df[df["Pricing_Floor_Flag"]].copy(); a,b,c = st.columns(3); a.metric("Pricing Review Deals", len(low)); b.metric("Pricing Review Exposure", money(low["Lending_Drawn"].sum() if len(low) else 0)); c.metric("Configurable Floor", f"{pricing_floor} bps")
    if len(low):
        low["Lending Drawn"] = low["Lending_Drawn"].apply(money); low["Revenue"] = low["Total_Revenue"].apply(money); low["LTM Group RoE"] = low["LTM_Group_RoE"].apply(pct); low["NIM"] = low["NIM_bps"].round(1).astype(str)+" bps"
        st.dataframe(low[["Deal_ID","Client","Country","Product","Lending Drawn","Revenue","NIM","LTM Group RoE","Status"]], use_container_width=True, hide_index=True)
    else: st.success("No pricing review deals detected.")

with tab5:
    st.markdown('<div class="ec-section-title">Capital Efficiency</div>', unsafe_allow_html=True)
    st.plotly_chart(combo_exposure_txroe(df), use_container_width=True, key="plot_capital_exposure_txroe_v044")
    st.markdown("### Capital Efficiency Watchlist")
    watch = executive_watchlist(df)
    if watch.empty:
        st.success("No pricing / profitability watchlist relationships detected.")
    else:
        st.dataframe(watch, use_container_width=True, hide_index=True)

with tab6:
    st.markdown('<div class="ec-section-title">Country Portfolio</div>', unsafe_allow_html=True)
    st.markdown("### Country-Level Portfolio Quality")
    tx_roe_heatmap_table(df, "Country")
    st.markdown("### Country Portfolio Table")
    country = grouped_view(df,["Country"]).copy(); country["Revenue"] = country["Total_Revenue"].apply(money); country["Lending Drawn"] = country["Lending_Drawn"].apply(money); country["Deposits"] = country["Deposit_Balance"].apply(money); country["RWA"] = country["RWA"].apply(money); country["LTM Group RoE"] = country["LTM_Group_RoE"].apply(pct); country["NIM"] = country["NIM_bps"].round(1).astype(str)+" bps"
    st.dataframe(country[["Country","Revenue","Lending Drawn","Deposits","RWA","NIM","LTM Group RoE","Pricing_Floor_Flag","Below_Relationship_RoE_Flag"]], use_container_width=True, hide_index=True)

with tab7:
    st.markdown('<div class="ec-section-title">Portfolio Data</div>', unsafe_allow_html=True)
    show = df.copy(); show["LTM Group RoE"] = show["LTM_Group_RoE"].apply(pct)
    st.dataframe(show, use_container_width=True)
