# EC-AI Banking Engine v0.8.6 - Readable dashboard with sidebar thresholds
# Relationship Intelligence Prototype for Corporate & Investment Banking
# Streamlit single-file app

import math
import io
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="EC-AI Banking Engine v0.8.6",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Design system
# -----------------------------
NAVY = "#0B2545"
NAVY_2 = "#123C69"
BLUE = "#2F5D8C"
SLATE = "#6F7F8C"
SLATE_2 = "#8A99A6"
LIGHT = "#F4F7FA"
BORDER = "#D8E0E8"
GREEN = "#007A3D"
RED = "#B42318"
AMBER = "#B7791F"
PALETTE = [NAVY, BLUE, SLATE, SLATE_2, "#A8B3BD", "#CBD3DA"]

st.markdown(
    f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: Inter, Arial, sans-serif; }}
    .stApp {{ background: {LIGHT}; }}
    section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #061B33 0%, #0B2545 100%); }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}
    section[data-testid="stSidebar"] .stRadio label {{ font-size: 13px !important; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{ background: rgba(255,255,255,0.06); border-radius: 8px; padding: 4px 8px; margin: 2px 0; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: rgba(255,255,255,0.12); }}
    .main .block-container {{ padding-top: 1.25rem; max-width: 1500px; padding-left: 1.7rem; padding-right: 1.7rem; }}
    h1 {{ color: #061B33; font-size: 34px !important; font-weight: 800 !important; margin-bottom: 0.15rem !important; }}
    h2 {{ color: #061B33; font-size: 28px !important; font-weight: 800 !important; margin-top: 1.2rem !important; }}
    h3 {{ color: #061B33; font-size: 19px !important; font-weight: 800 !important; }}
    .subtitle {{ color:#526173; font-size:15px; margin-bottom: 18px; }}
    .top-filter {{ background:white; border:1px solid {BORDER}; border-radius:14px; padding:18px 22px; margin-bottom:20px; box-shadow:0 1px 2px rgba(10,35,66,.03); display:flex; align-items:center; gap:34px; flex-wrap:wrap; }}
    .filter-item {{ display:flex; align-items:baseline; gap:12px; }}
    .filter-label {{ font-size:13px; font-weight:800; color:#526173; text-transform:uppercase; letter-spacing:.05em; }}
    .filter-value {{ font-size:18px; color:#061B33; font-weight:700; }}
    .metric-card {{ background:white; border:1px solid {BORDER}; border-radius:12px; padding:22px 20px 18px 20px; min-height:128px; box-shadow:0 1px 2px rgba(10,35,66,.03); }}
    .metric-label {{ font-size:12px; font-weight:800; color:#526173; text-transform:uppercase; letter-spacing:.04em; }}
    .metric-value {{ color:#061B33; font-size:31px; font-weight:800; margin-top:10px; }}
    .metric-note {{ color:{GREEN}; font-size:14px; font-weight:700; margin-top:8px; }}
    .card {{ background:white; border:1px solid {BORDER}; border-radius:12px; padding:18px; box-shadow:0 1px 2px rgba(10,35,66,.03); }}
    .small-card {{ background:white; border:1px solid {BORDER}; border-radius:12px; padding:20px; min-height:220px; font-size:16px; }}
    .section-gap {{ height: 8px; }}
    .insight-box {{ background:white; border:1px solid {BORDER}; border-radius:12px; padding:20px 24px; font-size:16px; line-height:1.62; color:#061B33; }}
    .insight-box b {{ font-size:17px; }}
    .sidebar-brand {{ font-size:30px; font-weight:800; margin-top:10px; }}
    .sidebar-sub {{ font-size:14px; font-weight:700; opacity:.95; }}
    .sidebar-ver {{ font-size:12px; opacity:.85; margin-bottom:28px; }}
    .sidebar-section {{ font-size:12px; font-weight:800; opacity:.72; margin:24px 0 8px; letter-spacing:.04em; }}
    .footer {{ color:#526173; font-size:12px; margin-top:20px; }}
    div[data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:12px; }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{ background: white; border:1px solid {BORDER}; border-radius:12px; box-shadow:0 1px 2px rgba(10,35,66,.03); padding: 0.55rem 0.55rem 0.35rem 0.55rem; }}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Formatting helpers
# -----------------------------
def fmt_b(x: float, digits: int = 1) -> str:
    try:
        return f"${float(x):,.{digits}f}B"
    except Exception:
        return "-"


def fmt_m(x: float, digits: int = 1) -> str:
    try:
        return f"${float(x):,.{digits}f}M"
    except Exception:
        return "-"


def fmt_pct(x: float, digits: int = 1) -> str:
    try:
        return f"{float(x)*100:.{digits}f}%"
    except Exception:
        return "-"


def clean_number(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

# -----------------------------
# Demo data
# -----------------------------
@st.cache_data(show_spinner=False)
def make_demo_data(seed: int = 83) -> Dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    countries = ["Hong Kong", "Korea", "Japan", "Australia", "Singapore", "Taiwan"]
    country_rev = np.array([315.8, 277.6, 226.5, 214.3, 194.8, 119.2])
    country_exp = np.array([25.1, 20.6, 18.7, 15.4, 13.2, 9.4])
    country_dep = np.array([47.6, 39.4, 34.0, 29.1, 27.7, 17.1])
    roe = np.array([0.201, 0.186, 0.178, 0.169, 0.162, 0.148])

    rel_names = [
        "North Asia Energy", "Harbour Retail Corp", "Strategic Infrastructure Co", "CB Pacific Property",
        "Sample Financial Holdings", "Sample Shipping Ltd", "Summit Telecom Group", "Asia Healthcare Group",
        "Sample Industrials Ltd", "Eastern Logistics Holdings", "Sample Trading Co", "Global Manufacturing Ltd",
        "Example Infrastructure Co", "Sakura Tech Holdings", "Pacific Consumer Group", "Metro Real Estate Ltd",
        "Apex Fund Partners", "Green Mobility Group", "Orion Semiconductor", "Blue Ocean Shipping"
    ]
    sectors = ["Energy", "Retail", "Infrastructure", "Real Estate", "Financial Institutions", "Shipping", "Telecom", "Healthcare", "Industrials", "Logistics"]
    tiers = ["Strategic", "Core", "Emerging", "Flow"]
    products = [
        "Term Loan", "Revolver", "Trade LC", "Trade Finance", "Cash Management", "FX / Markets",
        "DCM", "Securitization", "Fund Finance", "Project Finance", "CMG / LAF", "Investment Banking"
    ]
    deposit_types = ["CASA", "Operational", "Time Deposit", "Others"]
    competitors = ["HSBC", "MUFG", "JP Morgan", "Goldman Sachs", "Citi", "DBS", "Standard Chartered", "BNP Paribas"]

    rel_rows = []
    for i, name in enumerate(rel_names):
        c = countries[i % len(countries)]
        sector = sectors[i % len(sectors)]
        tier = rng.choice(tiers, p=[0.25, 0.35, 0.25, 0.15])
        exp = float(rng.uniform(2.0, 12.5))
        facility = exp * float(rng.uniform(1.15, 1.9))
        dep = float(rng.uniform(2.0, 20.0))
        revenue = exp * float(rng.uniform(8.5, 18.5)) + dep * float(rng.uniform(1.2, 3.2))
        nii = revenue * float(rng.uniform(0.48, 0.72))
        rwa = exp * float(rng.uniform(0.50, 0.90))
        el = exp * float(rng.uniform(0.004, 0.018))
        lp = exp * float(rng.uniform(0.006, 0.020))
        r = float(rng.uniform(0.125, 0.215))
        wallet = revenue / float(rng.uniform(0.18, 0.55))
        current_share = revenue / wallet
        rel_rows.append({
            "Relationship_Name": name,
            "Country": c,
            "Sector": sector,
            "Client_Tier": tier,
            "Total_Revenue": revenue,
            "NII": nii,
            "Operating_Income": revenue * float(rng.uniform(0.72, 0.90)),
            "Lending_Drawn": exp,
            "Facility_Limit": facility,
            "RWA": rwa,
            "EL": el,
            "LP": lp,
            "Deposit_Balance": dep,
            "LTM_Group_RoE": r,
            "ThreeYr_Avg_GRoE": r + float(rng.normal(0, 0.01)),
            "Estimated_Wallet": wallet,
            "Current_Share": current_share,
            "Wallet_Gap": wallet - revenue,
            "Wallet_Penetration": current_share,
            "Primary_Banker": rng.choice(["RM A", "RM B", "RM C", "RM D"]),
        })
    relationships = pd.DataFrame(rel_rows)

    # Scale to target headline figures roughly
    relationships["Total_Revenue"] *= 1348.7 / relationships["Total_Revenue"].sum()
    relationships["NII"] *= 852.2 / relationships["NII"].sum()
    relationships["Operating_Income"] *= 1032.4 / relationships["Operating_Income"].sum()
    relationships["Lending_Drawn"] *= 102.4 / relationships["Lending_Drawn"].sum()
    relationships["Facility_Limit"] *= 154.0 / relationships["Facility_Limit"].sum()
    relationships["Deposit_Balance"] *= 195.1 / relationships["Deposit_Balance"].sum()
    relationships["RWA"] *= 72.3 / relationships["RWA"].sum()
    relationships["Estimated_Wallet"] = relationships["Total_Revenue"] / np.maximum(relationships["Current_Share"], 0.12)
    relationships["Wallet_Gap"] = relationships["Estimated_Wallet"] - relationships["Total_Revenue"]
    relationships["Wallet_Penetration"] = relationships["Total_Revenue"] / relationships["Estimated_Wallet"]

    # Country summary fixed to the blueprint
    country = pd.DataFrame({
        "Country": countries,
        "Total_Revenue": country_rev,
        "Lending_Drawn": country_exp,
        "Deposit_Balance": country_dep,
        "LTM_Group_RoE": roe,
    })

    product_rows = []
    for p in products:
        exposure = float(rng.uniform(2.0, 16.0))
        if p == "Term Loan": exposure *= 1.8
        if p in ["DCM", "Investment Banking", "FX / Markets"]:
            exposure *= 0.55
        revenue = exposure * float(rng.uniform(7, 18))
        deposit = float(rng.uniform(2.0, 20.0)) if p in ["Cash Management", "Trade Finance", "Trade LC", "FX / Markets"] else float(rng.uniform(0.2, 5.0))
        product_rows.append({"Product_Type": p, "Exposure": exposure, "Revenue": revenue, "Deposit_Balance": deposit})
    product = pd.DataFrame(product_rows)
    product["Exposure"] *= 102.4 / product["Exposure"].sum()
    product["Revenue"] *= 1348.7 / product["Revenue"].sum()

    deposit = pd.DataFrame({
        "Deposit_Type": ["CASA", "Operational", "Time Deposit", "Others"],
        "Liquidity_Class": ["Liquid", "Operational", "Term", "Other"],
        "Deposit_Balance": [96.0, 62.3, 36.7, 0.1],
        "Deposit_Revenue": [85.2, 44.9, 25.6, 1.0],
        "Maturity_Bucket": ["On Demand", "<= 3M", "3M – 12M", "> 2Y"],
    })
    maturity = pd.DataFrame({
        "Maturity_Bucket": ["On Demand", "<= 3M", "3M – 12M", "1Y – 2Y", "2Y – 5Y", "> 5Y"],
        "Deposit_Balance": [96.0, 42.6, 46.8, 34.2, 24.0, 14.6],
    })

    wallet_rows = []
    for _, rel in relationships.iterrows():
        for p in ["Lending", "Transaction Banking", "Markets", "DCM", "Securitization", "Fund Finance", "Project Finance", "Investment Banking"]:
            estimated = float(rng.uniform(8, 80))
            current = estimated * float(rng.uniform(0.05, 0.48))
            main_bank = rng.choice(competitors, p=[0.22, 0.18, 0.15, 0.08, 0.12, 0.10, 0.10, 0.05])
            wallet_rows.append({
                "Relationship_Name": rel["Relationship_Name"],
                "Country": rel["Country"],
                "Product_Family": p,
                "Estimated_Wallet": estimated,
                "Current_Revenue": current,
                "Wallet_Gap": estimated - current,
                "Wallet_Penetration": current / estimated,
                "Lead_Competitor": main_bank,
            })
    wallet = pd.DataFrame(wallet_rows)

    dsc_rows = []
    for ds_id in range(1001, 1071):
        rel = relationships.sample(1, random_state=int(ds_id)).iloc[0]
        prod = rng.choice(products, p=np.array([0.16,0.12,0.11,0.10,0.09,0.07,0.07,0.06,0.08,0.08,0.04,0.02]))
        facility = float(rng.uniform(80, 1200))
        util = float(rng.uniform(0.20, 0.90))
        spread = float(rng.uniform(0.55, 2.80))
        lp_bps = float(rng.uniform(5, 55))
        bac_bps = float(rng.uniform(8, 38))
        el_bps = float(rng.uniform(3, 28))
        nim_bps = max(5, spread * 100 - lp_bps - bac_bps - el_bps)
        tx_roe = float(rng.uniform(0.08, 0.28))
        screen_date = datetime(2024, 1, 1) + timedelta(days=int(rng.integers(0, 360)))
        expected_draw = facility * util / 1000.0
        lag_month = int(rng.choice([2,3,4,5], p=[0.18,0.35,0.32,0.15]))
        dsc_rows.append({
            "DS_ID": ds_id,
            "Relationship_Name": rel["Relationship_Name"],
            "Country": rel["Country"],
            "Product_Type": prod,
            "Facility_Limit_M": facility,
            "Expected_Utilization": util,
            "Expected_Draw_B": expected_draw,
            "Renewal_Type": rng.choice(["New", "Renewal", "Refinance"], p=[0.42,0.34,0.24]),
            "Committed_Flag": rng.choice(["Committed", "Uncommitted"], p=[0.56,0.44]),
            "Cross_Sell": rng.choice(["None", "Trade", "Markets", "TB + Markets", "IB"], p=[0.28,0.24,0.20,0.18,0.10]),
            "Base_Rate": rng.choice(["SOFR 3M", "SOFR 6M", "HIBOR", "TONA", "BBSW"]),
            "Spread_bps": spread * 100,
            "LP_bps": lp_bps,
            "BAC_bps": bac_bps,
            "EL_bps": el_bps,
            "NIM_bps": nim_bps,
            "Tx_RoE": tx_roe,
            "DSC_Quality_Index": float(rng.uniform(70, 112)),
            "Screen_Date": screen_date,
            "Expected_Drawdown_Date": screen_date + pd.DateOffset(months=lag_month),
            "Status": rng.choice(["Approved", "Pipeline", "Lost", "Deferred"], p=[0.62,0.20,0.10,0.08]),
        })
    dsc = pd.DataFrame(dsc_rows)
    # Demo facility tenor / final maturity profile for banking portfolio analytics.
    tenor_labels = ["< 1 Year", "1 – 3 Years", "3 – 5 Years", "5 – 10 Years", "10+ Years"]
    tenor_probs = [0.20, 0.30, 0.22, 0.17, 0.11]
    dsc["Tenor_Bucket"] = rng.choice(tenor_labels, size=len(dsc), p=tenor_probs)
    tenor_mid = {"< 1 Year": 0.6, "1 – 3 Years": 2.0, "3 – 5 Years": 4.0, "5 – 10 Years": 7.0, "10+ Years": 12.0}
    dsc["Tenor_Years"] = dsc["Tenor_Bucket"].map(tenor_mid).astype(float)

    months = pd.date_range("2023-04-01", periods=24, freq="MS")
    hist_rows = []
    for _, rel in relationships.iterrows():
        base_rev = rel["Total_Revenue"] / 12
        base_exp = rel["Lending_Drawn"]
        base_dep = rel["Deposit_Balance"]
        for mth in months:
            hist_rows.append({
                "Month": mth,
                "Relationship_Name": rel["Relationship_Name"],
                "Country": rel["Country"],
                "Revenue": max(0, base_rev * rng.normal(1, 0.14)),
                "NII": max(0, (rel["NII"] / 12) * rng.normal(1, 0.12)),
                "Lending_Drawn": max(0, base_exp * rng.normal(1, 0.07)),
                "Deposit_Balance": max(0, base_dep * rng.normal(1, 0.12)),
                "RWA": max(0, rel["RWA"] * rng.normal(1, 0.08)),
                "LTM_Group_RoE": max(0.03, rel["LTM_Group_RoE"] + rng.normal(0, 0.015)),
            })
    historical = pd.DataFrame(hist_rows)

    return {
        "relationships": relationships,
        "country": country,
        "product": product,
        "deposit": deposit,
        "maturity": maturity,
        "wallet": wallet,
        "dsc": dsc,
        "historical": historical,
    }

# -----------------------------
# Upload handling
# -----------------------------
def read_uploaded_excel(file) -> Dict[str, pd.DataFrame]:
    if file is None:
        return make_demo_data()
    try:
        xls = pd.ExcelFile(file)
        out = {}
        for sheet in xls.sheet_names:
            out[sheet.lower().replace(" ", "_")] = pd.read_excel(xls, sheet_name=sheet)
        demo = make_demo_data()
        # Map common sheet names, fallback to demo if missing.
        mapped = {
            "relationships": out.get("relationships", out.get("portfolio_data", demo["relationships"])),
            "country": out.get("country", demo["country"]),
            "product": out.get("product", out.get("products", demo["product"])),
            "deposit": out.get("deposit", out.get("deposits", demo["deposit"])),
            "maturity": out.get("maturity", demo["maturity"]),
            "wallet": out.get("wallet", demo["wallet"]),
            "dsc": out.get("dsc", out.get("deal_screening", demo["dsc"])),
            "historical": out.get("historical", demo["historical"]),
        }
        return mapped
    except Exception:
        return make_demo_data()

# -----------------------------
# Chart helpers
# -----------------------------
def chart_layout(fig: go.Figure, height: int = 310, show_legend: bool = False) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=42, r=24, t=32, b=42),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Arial", size=13, color=NAVY),
        showlegend=show_legend,
    )
    fig.update_xaxes(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=12, color=NAVY))
    fig.update_yaxes(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=12, color="#50627A"))
    return fig


def bar_fig(df: pd.DataFrame, x: str, y: str, title: str, unit: str = "M", height: int = 260, width: float = 0.34) -> go.Figure:
    d = df.sort_values(y, ascending=False).copy()
    colors = [PALETTE[i] if i < len(PALETTE) else SLATE_2 for i in range(len(d))]
    suffix = "B" if unit == "B" else "M"
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d[x], y=d[y], marker_color=colors, width=width,
        text=[f"${v:.1f}{suffix}" for v in d[y]], textposition="outside",
        textfont=dict(size=12, color=NAVY),
        hovertemplate=f"%{{x}}<br>%{{y:.1f}} {suffix}<extra></extra>",
    ))
    fig.update_layout(title=dict(text=title, x=0.0, font=dict(size=16, color=NAVY)))
    fig = chart_layout(fig, height=height)
    fig.update_yaxes(title_text="USD billion" if unit == "B" else "USD million")
    return fig


def combo_capital_fig(rel: pd.DataFrame, roe_floor: float) -> go.Figure:
    d = rel.sort_values("Lending_Drawn", ascending=False).head(14).copy()

    def short_name(name: str) -> str:
        words = str(name).replace(" Holdings", "").replace(" Group", "").replace(" Ltd", "").split()
        if len(words) <= 2:
            return "<br>".join(words)
        return "<br>".join(words[:2])

    d["Short_Name"] = d["Relationship_Name"].map(short_name)
    x = d["Short_Name"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=d["Lending_Drawn"], name="Lending Exposure (USD b)",
        marker_color=NAVY, width=0.34,
        text=[f"${v:.1f}B" for v in d["Lending_Drawn"]], textposition="outside",
        textfont=dict(size=11, color=NAVY), yaxis="y1",
        hovertemplate="%{customdata}<br>Lending Exposure: $%{y:.1f}B<extra></extra>",
        customdata=d["Relationship_Name"],
    ))
    fig.add_trace(go.Scatter(
        x=x, y=d["LTM_Group_RoE"]*100, name="LTM Group RoE (%)",
        mode="lines+markers", marker=dict(size=7, color=BLUE), line=dict(width=2.6, color=BLUE), yaxis="y2",
        hovertemplate="%{customdata}<br>RoE: %{y:.1f}%<extra></extra>",
        customdata=d["Relationship_Name"],
    ))
    # RoE floor is plotted against the secondary RoE axis, not the lending exposure axis.
    fig.add_trace(go.Scatter(
        x=x, y=[roe_floor*100] * len(d), name=f"RoE Floor ({roe_floor*100:.0f}%)",
        mode="lines", line=dict(color=AMBER, width=2, dash="dot"), yaxis="y2",
        hoverinfo="skip",
    ))
    fig.update_layout(
        title=dict(text="Capital Efficiency: Exposure vs LTM Group RoE", x=0, font=dict(size=17, color=NAVY)),
        template="plotly_white", height=455, margin=dict(l=58, r=62, t=62, b=118),
        paper_bgcolor="white", plot_bgcolor="white", font=dict(family="Inter, Arial", size=13, color=NAVY),
        legend=dict(orientation="h", y=1.10, x=0.0, font=dict(size=13)),
        yaxis=dict(title="Lending Exposure (USD b)", showgrid=False, zeroline=False, range=[0, max(12, float(d["Lending_Drawn"].max())*1.28)], titlefont=dict(size=13), tickfont=dict(size=12)),
        yaxis2=dict(title="RoE %", overlaying="y", side="right", showgrid=False, zeroline=False, range=[10, 24], titlefont=dict(size=13), tickfont=dict(size=12)),
        xaxis=dict(tickangle=0, tickfont=dict(size=10), showgrid=False, automargin=True),
        hovermode="x unified",
    )
    return fig


def roe_heatmap(country: pd.DataFrame, roe_floor: float) -> str:
    d = country.sort_values("LTM_Group_RoE", ascending=False).copy()
    min_r = min(0.10, float(d["LTM_Group_RoE"].min()))
    max_r = max(0.22, float(d["LTM_Group_RoE"].max()))
    cells = []
    for _, r in d.iterrows():
        val = float(r["LTM_Group_RoE"])
        pct = (val - min_r) / max(max_r - min_r, 0.001)
        # interpolate navy to light grey
        if val >= roe_floor:
            bg = NAVY if pct > 0.75 else BLUE if pct > 0.45 else SLATE
            color = "white"
        else:
            bg = "#D9DEE5"
            color = NAVY
        cells.append(f"<div style='background:{bg};color:{color};padding:26px 12px;text-align:center;border-right:1px solid white;min-height:96px;'><div style='font-size:15px'>{r['Country']}</div><div style='font-size:24px;font-weight:800;margin-top:8px'>{val*100:.1f}%</div></div>")
    return f"""
    <div class='card'>
      <div style='font-weight:800;color:{NAVY};font-size:14px;margin-bottom:12px;'>LTM Group RoE Heatmap by Country</div>
      <div style='display:flex;align-items:center;gap:10px;margin-bottom:8px;color:{NAVY};font-size:12px;'><span>10%</span><div style='height:10px;background:linear-gradient(90deg,#D9DEE5,{BLUE},{NAVY});border-radius:8px;flex:1;max-width:300px;'></div><span>22%</span></div>
      <div style='display:grid;grid-template-columns:repeat({len(cells)},1fr);border-radius:8px;overflow:hidden;border:1px solid {BORDER};'>{''.join(cells)}</div>
    </div>
    """


def donut_deposit(deposit: pd.DataFrame) -> go.Figure:
    d = deposit.copy()
    # Donut is deliberately centered within the left visual area, with legend on the lower-right.
    # This avoids overlap while keeping the chart visually balanced inside the card.
    fig = go.Figure(data=[go.Pie(
        labels=d["Deposit_Type"], values=d["Deposit_Balance"], hole=0.58,
        marker=dict(colors=[NAVY, BLUE, SLATE, "#CBD3DA"]),
        textinfo="none",
        domain=dict(x=[0.03, 0.58], y=[0.08, 0.95]),
        sort=False,
        hovertemplate="%{label}<br>$%{value:.1f}B (%{percent})<extra></extra>",
    )])
    total = d["Deposit_Balance"].sum()
    fig.update_layout(
        annotations=[dict(text=f"${total:.1f}B<br><span style='font-size:12px'>Total</span>", x=0.305, y=0.52, showarrow=False, font=dict(size=18, color=NAVY, family="Inter"))],
        legend=dict(
            x=0.68, y=0.12, xanchor="left", yanchor="bottom",
            orientation="v", font=dict(size=12, color=NAVY),
            bgcolor="rgba(255,255,255,0)", borderwidth=0,
            itemsizing="constant"
        ),
        title=dict(text="Deposits by Type (USD b)", x=0.0, font=dict(size=16, color=NAVY)),
    )
    fig = chart_layout(fig, height=300, show_legend=True)
    fig.update_layout(margin=dict(l=24, r=12, t=32, b=20))
    return fig


def maturity_fig(maturity: pd.DataFrame) -> go.Figure:
    d = maturity.copy().sort_values("Deposit_Balance", ascending=True)
    fig = go.Figure(go.Bar(
        x=d["Deposit_Balance"], y=d["Maturity_Bucket"], orientation="h",
        marker_color=["#8BB2E8", "#6D9BD6", "#4B7FC1", "#386BAB", "#28578F", NAVY],
        text=[f"{v:.1f}" for v in d["Deposit_Balance"]], textposition="outside",
        textfont=dict(size=12, color=NAVY), width=0.45,
    ))
    fig.update_layout(title=dict(text="Maturity Ladder (USD b)", x=0, font=dict(size=16, color=NAVY)))
    fig = chart_layout(fig, height=310)
    fig.update_xaxes(title_text="USD billion")
    return fig


def tenor_breakdown_fig(dsc: pd.DataFrame) -> go.Figure:
    """Breakdown of lending deals / facilities by final tenor bucket."""
    order = ["< 1 Year", "1 – 3 Years", "3 – 5 Years", "5 – 10 Years", "10+ Years"]
    d = dsc.copy()
    if "Tenor_Bucket" not in d.columns:
        # Fallback for uploaded files without tenor data.
        rng = np.random.default_rng(11)
        d["Tenor_Bucket"] = rng.choice(order, size=len(d), p=[0.20, 0.30, 0.22, 0.17, 0.11])
    value_col = "Expected_Draw_B" if "Expected_Draw_B" in d.columns else "Facility_Limit_M"
    agg = d.groupby("Tenor_Bucket")[value_col].sum().reindex(order).fillna(0).reset_index()
    # Facility_Limit_M is in USD million; convert to USD billion if needed.
    if value_col == "Facility_Limit_M":
        agg[value_col] = agg[value_col] / 1000.0
    agg = agg.sort_values(value_col, ascending=True)
    fig = go.Figure(go.Bar(
        x=agg[value_col], y=agg["Tenor_Bucket"], orientation="h",
        marker_color=["#8BB2E8", "#6D9BD6", "#4B7FC1", "#386BAB", NAVY],
        text=[f"{v:.1f}" for v in agg[value_col]], textposition="outside",
        textfont=dict(size=12, color=NAVY), width=0.48,
        hovertemplate="%{y}<br>$%{x:.1f}B<extra></extra>",
    ))
    fig.update_layout(title=dict(text="Tenor Breakdown of All Deals / Facilities (USD b)", x=0, font=dict(size=15, color=NAVY)))
    fig = chart_layout(fig, height=235)
    fig.update_layout(margin=dict(l=78, r=24, t=34, b=38))
    fig.update_xaxes(title_text="USD billion")
    return fig


def metric_card(label: str, value: str, note: str) -> str:
    return f"""
    <div class='metric-card'>
        <div class='metric-label'>{label}</div>
        <div class='metric-value'>{value}</div>
        <div class='metric-note'>{note}</div>
    </div>
    """


def top_filter_bar() -> None:
    st.markdown(
        """
        <div class='top-filter'>
          <div class='filter-item'><span class='filter-label'>Portfolio</span><span class='filter-value'>Corporate Banking</span></div>
          <div class='filter-item'><span class='filter-label'>Region</span><span class='filter-value'>Asia Demo</span></div>
          <div class='filter-item'><span class='filter-label'>Currency</span><span class='filter-value'>USD</span></div>
          <div class='filter-item'><span class='filter-label'>Period</span><span class='filter-value'>LTM / Demo</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Export sample Excel
# -----------------------------
def make_excel_download(data: Dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in data.items():
            df.to_excel(writer, index=False, sheet_name=name[:31])
    return output.getvalue()

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("<div class='sidebar-brand'>EC-AI</div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-sub'>Banking Intelligence</div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-ver'>v0.8.6 Demo</div>", unsafe_allow_html=True)

    st.markdown("<div class='sidebar-section'>EXECUTIVE OVERVIEW</div>", unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        [
            "Executive Dashboard", "Revenue & Exposure", "Capital Efficiency", "Deposit Intelligence",
            "Competitor Benchmarking", "Client Overview", "Wallet Intelligence", "Product Penetration",
            "Deal Screening (DSC)", "Portfolio Data", "AI Banker Commentary"
        ],
        label_visibility="collapsed",
        key="main_nav_v083",
    )

    st.markdown("<div class='sidebar-section'>DATA SOURCE</div>", unsafe_allow_html=True)
    data_mode = st.radio("Data source", ["Use Built-in Demo Data", "Upload File"], index=0, label_visibility="collapsed", key="data_source_v083")
    uploaded = None
    if data_mode == "Upload File":
        uploaded = st.file_uploader("Upload Excel", type=["xlsx"], key="upload_v083")

    st.markdown("<div class='sidebar-section'>THRESHOLD SETTINGS</div>", unsafe_allow_html=True)
    roe_floor_pct = st.slider("RoE floor (%)", 10, 30, 10, 1, key="roe_floor_v085_pct")
    roe_floor = roe_floor_pct / 100
    margin_floor = st.slider("Pricing floor (bps)", 20, 120, 50, 5, key="margin_floor_v085")
    st.caption("Demo thresholds only — configure for each institution / pilot.")

# Load data
if data_mode == "Upload File" and uploaded is not None:
    data = read_uploaded_excel(uploaded)
else:
    data = make_demo_data()

relationships = data["relationships"]
country = data["country"]
product = data["product"]
deposit = data["deposit"]
maturity = data["maturity"]
wallet = data["wallet"]
dsc = data["dsc"]
historical = data["historical"]

# -----------------------------
# Common top controls
# -----------------------------
top_filter_bar()

# -----------------------------
# Page renderers
# -----------------------------
def render_executive_dashboard():
    st.markdown("<h1>Executive Portfolio Overview</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>LTM performance summary — wallet, exposure, deposits, revenue and profitability.</div>", unsafe_allow_html=True)

    kpi_cols = st.columns(6)
    metrics = [
        ("Revenue", "$1.3B", "demo vs PY"),
        ("NII", "$852.2M", "Net interest income"),
        ("RWA", "$72.3B", "Risk weighted assets"),
        ("Lending Exposure", "$102.4B", "Drawn balance"),
        ("Deposits", "$195.1B", "Deposit franchise"),
        ("LTM Group RoE", "16.7%", "Portfolio return"),
    ]
    for col, (label, value, note) in zip(kpi_cols, metrics):
        with col:
            st.markdown(metric_card(label, value, note), unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        with st.container(border=True):
            st.plotly_chart(bar_fig(country, "Country", "Total_Revenue", "Revenue by Country (USD)", unit="M", height=310, width=0.38), use_container_width=True, config={"displayModeBar": False}, key="exec_rev_country_v084")
    with c2:
        with st.container(border=True):
            st.plotly_chart(bar_fig(country, "Country", "Lending_Drawn", "Exposure by Country (USD)", unit="B", height=310, width=0.38), use_container_width=True, config={"displayModeBar": False}, key="exec_exp_country_v084")

    st.markdown("<h2>Deposit Intelligence</h2>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Franchise strength, liquidity profile and treasury opportunities.</div>", unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns([1.05, 1.05, 0.92, 1.1], gap="large")
    with d1:
        with st.container(border=True):
            st.plotly_chart(bar_fig(country, "Country", "Deposit_Balance", "Deposits by Country", unit="B", height=300, width=0.38), use_container_width=True, config={"displayModeBar": False}, key="exec_dep_country_v084")
    with d2:
        with st.container(border=True):
            st.plotly_chart(donut_deposit(deposit), use_container_width=True, config={"displayModeBar": False}, key="exec_dep_donut_v084")
    with d3:
        casa = float(deposit.loc[deposit["Deposit_Type"].eq("CASA"), "Deposit_Balance"].sum() / deposit["Deposit_Balance"].sum())
        ltd = float(relationships["Lending_Drawn"].sum() / relationships["Deposit_Balance"].sum())
        pen = float(relationships["Total_Revenue"].sum() / relationships["Estimated_Wallet"].sum())
        st.markdown(
            f"""
            <div class='small-card'>
              <h3>Liquidity & Balance Sheet Indicators</h3>
              <div style='font-size:12px;color:#526173;line-height:1.35;margin:8px 0 16px 0;'>
                Measures the stability of deposit funding and the bank’s ability to support lending growth while meeting short-term liquidity requirements.
              </div>
              <div style='display:flex;justify-content:space-between;margin-bottom:13px;'><span>CASA Ratio</span><b style='color:{GREEN}'>{casa*100:.0f}%</b></div>
              <div style='display:flex;justify-content:space-between;margin-bottom:13px;'><span>Loan to Deposit Ratio</span><b style='color:{RED}'>{ltd*100:.0f}%</b></div>
              <div style='display:flex;justify-content:space-between;margin-bottom:13px;'><span>NSFR</span><b style='color:{GREEN}'>118%</b></div>
              <div style='display:flex;justify-content:space-between;'><span>LCR</span><b style='color:{GREEN}'>142%</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with d4:
        with st.container(border=True):
            st.plotly_chart(maturity_fig(maturity), use_container_width=True, config={"displayModeBar": False}, key="exec_maturity_v084")

    c3, c4 = st.columns([1.38, 1], gap="large")
    with c3:
        with st.container(border=True):
            st.plotly_chart(combo_capital_fig(relationships, roe_floor), use_container_width=True, config={"displayModeBar": False}, key="exec_capital_combo_v086")
    with c4:
        st.markdown(roe_heatmap(country, roe_floor), unsafe_allow_html=True)
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        tcol, icol = st.columns([0.86, 1.14], gap="large")
        with tcol:
            with st.container(border=True):
                st.plotly_chart(tenor_breakdown_fig(dsc), use_container_width=True, config={"displayModeBar": False}, key="exec_tenor_v086")
        with icol:
            st.markdown(
                """
                <div class='insight-box' style='font-size:13.5px;line-height:1.55;padding:16px 18px;min-height:235px;'>
                  <b style='font-size:16px;'>Key Insights</b><br><br>
                  • Hong Kong is the largest revenue and exposure contributor at <b>$315.8M</b> revenue and <b>$25.1B</b> exposure.<br>
                  • Portfolio RoE of <b>16.7%</b> is above the <b>10%</b> RoE floor in most country relationships.<br>
                  • CASA ratio at <b>49%</b> indicates a solid low-cost deposit base.<br>
                  • LCR at <b>142%</b> and NSFR at <b>118%</b> indicate strong short-term and structural funding resilience.<br>
                  • Loan to Deposit Ratio of <b>52%</b> leaves balance sheet headroom for selective lending growth.<br>
                  • Time deposits require active rollover and repricing management as rates change.<br>
                  • Tenor view highlights facility duration concentration across <b>1–3Y</b> and <b>3–5Y</b> buckets.<br>
                  • Use Relationship 360 to identify product gaps, treasury opportunities and IB wallet expansion.<br>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_revenue_exposure():
    st.markdown("<h1>Revenue & Exposure</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Historical portfolio revenue, exposure and product penetration view.</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(product, "Product_Type", "Revenue", "Revenue by Product Type", unit="M", height=390, width=0.32), use_container_width=True, key="rev_product_v083")
    with c2:
        st.plotly_chart(bar_fig(product, "Product_Type", "Exposure", "Exposure by Product Type", unit="B", height=390, width=0.32), use_container_width=True, key="exp_product_v083")
    st.markdown("<h2>Top Relationship Table</h2>", unsafe_allow_html=True)
    cols = ["Relationship_Name", "Country", "Sector", "Client_Tier", "Total_Revenue", "Lending_Drawn", "Facility_Limit", "Deposit_Balance", "LTM_Group_RoE"]
    st.dataframe(relationships[cols].sort_values("Total_Revenue", ascending=False), use_container_width=True, hide_index=True)


def render_capital_efficiency():
    st.markdown("<h1>Capital Efficiency</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Exposure, capital usage, RWA and profitability discipline.</div>", unsafe_allow_html=True)
    st.plotly_chart(combo_capital_fig(relationships, roe_floor), use_container_width=True, key="capital_combo_full_v083")
    low = relationships[relationships["LTM_Group_RoE"] < roe_floor].copy()
    st.markdown("<h2>Watchlist: Below Profitability Floor</h2>", unsafe_allow_html=True)
    if low.empty:
        st.success("No below-floor relationships detected.")
    else:
        st.dataframe(low[["Relationship_Name", "Country", "Sector", "Lending_Drawn", "RWA", "LTM_Group_RoE", "Deposit_Balance"]].sort_values("Lending_Drawn", ascending=False), use_container_width=True, hide_index=True)


def render_deposit_intelligence():
    st.markdown("<h1>Deposit Intelligence</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Deposit franchise, operational balance and treasury opportunity view.</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(country, "Country", "Deposit_Balance", "Deposits by Country", unit="B", height=300, width=0.36), use_container_width=True, key="dep_country_full_v083")
    with c2:
        st.plotly_chart(donut_deposit(deposit), use_container_width=True, key="dep_type_donut_full_v083")
    c3, c4 = st.columns([1, 1], gap="large")
    with c3:
        st.plotly_chart(maturity_fig(maturity), use_container_width=True, key="dep_maturity_full_v083")
    with c4:
        st.markdown("<div class='small-card'><h3>Deposit Commentary</h3><br>CASA and operational balances indicate relationship stickiness and treasury dialogue potential.<br><br>Use maturity ladder to identify rollover risk, repricing windows and liquidity concentration.</div>", unsafe_allow_html=True)
    st.markdown("<h2>Deposit Relationship Table</h2>", unsafe_allow_html=True)
    table = relationships[["Relationship_Name", "Country", "Client_Tier", "Deposit_Balance", "Total_Revenue"]].copy()
    table["Deposit_Type"] = np.random.default_rng(4).choice(["CASA", "Operational", "Time Deposit"], len(table))
    table["Liquidity_Class"] = table["Deposit_Type"].map({"CASA":"Liquid", "Operational":"Operational", "Time Deposit":"Term"})
    table["Deposit_Maturity_Date"] = [datetime(2024, 3, 31) + timedelta(days=int(x)) for x in np.random.default_rng(7).integers(15, 420, len(table))]
    table = table.rename(columns={"Total_Revenue": "Deposit_Revenue_Proxy"})
    st.dataframe(table.sort_values("Deposit_Balance", ascending=False), use_container_width=True, hide_index=True)


def render_competitor_benchmarking():
    st.markdown("<h1>Competitor Benchmarking</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Prototype view of estimated wallet, current share and competitor lead bank by product family.</div>", unsafe_allow_html=True)
    comp = wallet.groupby("Lead_Competitor", as_index=False).agg(Estimated_Wallet=("Estimated_Wallet", "sum"), Current_Revenue=("Current_Revenue", "sum"), Wallet_Gap=("Wallet_Gap", "sum"))
    comp["Penetration"] = comp["Current_Revenue"] / comp["Estimated_Wallet"]
    st.plotly_chart(bar_fig(comp, "Lead_Competitor", "Wallet_Gap", "Wallet Gap by Competitor Relationship", unit="M", height=340, width=0.36), use_container_width=True, key="competitor_gap_v083")
    st.dataframe(comp.sort_values("Wallet_Gap", ascending=False), use_container_width=True, hide_index=True)


def render_client_overview():
    st.markdown("<h1>Client Overview</h1>", unsafe_allow_html=True)
    client = st.selectbox("Select relationship", relationships["Relationship_Name"].sort_values().tolist(), key="client_select_v083")
    r = relationships[relationships["Relationship_Name"].eq(client)].iloc[0]
    st.markdown(
        f"""
        <div class='card'>
          <h2>{r['Relationship_Name']}</h2>
          <div style='font-size:15px;color:#526173'>{r['Sector']} · {r['Country']} · {r['Client_Tier']} client</div>
          <br>
          <b>Relationship logic:</b> Lending exposure is {fmt_b(r['Lending_Drawn'])}, deposits are {fmt_b(r['Deposit_Balance'])}, LTM Group RoE is {r['LTM_Group_RoE']*100:.1f}%.<br>
          <b>RM angle:</b> Identify the client’s true need from liquidity, capex, refinancing, cross-border trade, treasury control or capital markets access.
        </div>
        """, unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    for c, (label, val) in zip(c1, [("Revenue", fmt_m(r["Total_Revenue"])),]):
        c.markdown(metric_card(label, val, "LTM revenue"), unsafe_allow_html=True)
    c2.markdown(metric_card("Exposure", fmt_b(r["Lending_Drawn"]), "Drawn balance"), unsafe_allow_html=True)
    c3.markdown(metric_card("Deposits", fmt_b(r["Deposit_Balance"]), "Franchise"), unsafe_allow_html=True)
    c4.markdown(metric_card("Wallet Penetration", fmt_pct(r["Wallet_Penetration"]), "Estimated"), unsafe_allow_html=True)


def render_wallet_intelligence():
    st.markdown("<h1>Wallet Intelligence</h1>", unsafe_allow_html=True)
    w = wallet.groupby("Product_Family", as_index=False).agg(Estimated_Wallet=("Estimated_Wallet", "sum"), Current_Revenue=("Current_Revenue", "sum"), Wallet_Gap=("Wallet_Gap", "sum"))
    w["Penetration"] = w["Current_Revenue"] / w["Estimated_Wallet"]
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(w, "Product_Family", "Estimated_Wallet", "Estimated Wallet by Product", unit="M", height=390, width=0.32), use_container_width=True, key="wallet_est_v083")
    with c2:
        st.plotly_chart(bar_fig(w, "Product_Family", "Wallet_Gap", "Wallet Gap by Product", unit="M", height=390, width=0.32), use_container_width=True, key="wallet_gap_v083")
    st.dataframe(w.sort_values("Wallet_Gap", ascending=False), use_container_width=True, hide_index=True)


def render_product_penetration():
    st.markdown("<h1>Product Penetration</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Revenue and exposure across product hierarchy: lending, transaction banking, markets and IB products.</div>", unsafe_allow_html=True)
    prod = product.copy()
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(prod, "Product_Type", "Revenue", "Product Revenue", unit="M", height=350, width=0.30), use_container_width=True, key="prod_rev_v083")
    with c2:
        st.plotly_chart(bar_fig(prod, "Product_Type", "Exposure", "Product Exposure", unit="B", height=350, width=0.30), use_container_width=True, key="prod_exp_v083")
    st.dataframe(prod.sort_values("Revenue", ascending=False), use_container_width=True, hide_index=True)


def render_deal_screening():
    st.markdown("<h1>Deal Screening (DSC)</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mini DSC dashboard: approved amount, Tx RoE, NIM, hurdle and quality index.</div>", unsafe_allow_html=True)
    d = dsc.copy()
    d["Tx_RoE_Bucket"] = pd.cut(d["Tx_RoE"], bins=[0,0.10,0.15,0.20,1], labels=["0–10%", "10–15%", "15–20%", ">20%"])
    d["NIM_Bucket"] = pd.cut(d["NIM_bps"], bins=[-1,30,60,100,10000], labels=["Below 30 bps", "30–60 bps", "60–100 bps", "Over 100 bps"])

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Deals", f"{len(d)}", "screened sample"), unsafe_allow_html=True)
    c2.markdown(metric_card("Facility Limit", fmt_m(d["Facility_Limit_M"].sum()), "screened amount"), unsafe_allow_html=True)
    c3.markdown(metric_card("Avg Tx RoE", f"{d['Tx_RoE'].mean()*100:.1f}%", "transaction return"), unsafe_allow_html=True)
    c4.markdown(metric_card("Avg NIM", f"{d['NIM_bps'].mean():.0f} bps", "price margin"), unsafe_allow_html=True)

    by_month = d.assign(Month=pd.to_datetime(d["Screen_Date"]).dt.to_period("M").astype(str)).groupby("Month", as_index=False).agg(Facility_Limit_M=("Facility_Limit_M","sum"), Deals=("DS_ID","count"), Tx_RoE=("Tx_RoE","mean"), NIM_bps=("NIM_bps","mean"))
    c5, c6 = st.columns(2, gap="large")
    with c5:
        st.plotly_chart(bar_fig(by_month, "Month", "Facility_Limit_M", "Approved Amount by Month", unit="M", height=300, width=0.28), use_container_width=True, key="dsc_month_v083")
    with c6:
        by_country = d.groupby("Country", as_index=False).agg(Expected_Draw_B=("Expected_Draw_B","sum"), Tx_RoE=("Tx_RoE","mean"), NIM_bps=("NIM_bps","mean"), DSC_Quality_Index=("DSC_Quality_Index","mean"))
        st.plotly_chart(bar_fig(by_country, "Country", "Expected_Draw_B", "Expected Draw by Country", unit="B", height=300, width=0.36), use_container_width=True, key="dsc_country_v083")

    c7, c8 = st.columns(2, gap="large")
    with c7:
        bucket = d.groupby("NIM_Bucket", observed=True, as_index=False).agg(Facility_Limit_M=("Facility_Limit_M", "sum"), Deals=("DS_ID", "count"))
        st.plotly_chart(bar_fig(bucket, "NIM_Bucket", "Facility_Limit_M", "NIM Bucket by Facility Limit", unit="M", height=300, width=0.36), use_container_width=True, key="dsc_nim_bucket_v083")
    with c8:
        qual = d.groupby("Country", as_index=False).agg(DSC_Quality_Index=("DSC_Quality_Index", "mean"))
        st.plotly_chart(bar_fig(qual, "Country", "DSC_Quality_Index", "DSC Quality Index by Country", unit="M", height=300, width=0.36), use_container_width=True, key="dsc_quality_v083")

    st.markdown("<h2>Deal List</h2>", unsafe_allow_html=True)
    st.dataframe(d.sort_values("Facility_Limit_M", ascending=False), use_container_width=True, hide_index=True)


def render_portfolio_data():
    st.markdown("<h1>Portfolio Data</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Historical actual facilities, drawdown, revenue, deposits and RWA.</div>", unsafe_allow_html=True)
    excel_bytes = make_excel_download(data)
    st.download_button("Download sample banking data (Excel)", data=excel_bytes, file_name="ecai_banking_sample_data_v083.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_excel_v083")
    view = st.selectbox("Table", list(data.keys()), key="portfolio_table_select_v083")
    st.dataframe(data[view], use_container_width=True, hide_index=True)


def render_ai_banker_commentary():
    st.markdown("<h1>AI Banker Commentary</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Prototype RM pitch angles based on relationship profile, wallet gap and product need.</div>", unsafe_allow_html=True)
    client = st.selectbox("Select client", relationships["Relationship_Name"].sort_values().tolist(), key="ai_client_select_v083")
    r = relationships[relationships["Relationship_Name"].eq(client)].iloc[0]
    gap = wallet[wallet["Relationship_Name"].eq(client)].sort_values("Wallet_Gap", ascending=False).head(4)
    st.markdown(
        f"""
        <div class='insight-box'>
        <b>{client} — RM dialogue angle</b><br><br>
        • Relationship profile: {r['Sector']} client in {r['Country']} with {fmt_b(r['Lending_Drawn'])} lending exposure and {fmt_b(r['Deposit_Balance'])} deposits.<br>
        • True need hypothesis: {'liquidity and refinancing' if r['Lending_Drawn'] > r['Deposit_Balance'] else 'treasury control and operating balance stickiness'} plus selective capital markets / IB cross-sell.<br>
        • Pitch angle: lead with balance sheet needs, then connect to product gaps rather than generic product pushing.<br>
        </div>
        """, unsafe_allow_html=True,
    )
    st.markdown("<h2>Top Product Gap Angles</h2>", unsafe_allow_html=True)
    st.dataframe(gap[["Product_Family", "Estimated_Wallet", "Current_Revenue", "Wallet_Gap", "Wallet_Penetration", "Lead_Competitor"]], use_container_width=True, hide_index=True)

# -----------------------------
# Dispatch
# -----------------------------
if page == "Executive Dashboard":
    render_executive_dashboard()
elif page == "Revenue & Exposure":
    render_revenue_exposure()
elif page == "Capital Efficiency":
    render_capital_efficiency()
elif page == "Deposit Intelligence":
    render_deposit_intelligence()
elif page == "Competitor Benchmarking":
    render_competitor_benchmarking()
elif page == "Client Overview":
    render_client_overview()
elif page == "Wallet Intelligence":
    render_wallet_intelligence()
elif page == "Product Penetration":
    render_product_penetration()
elif page == "Deal Screening (DSC)":
    render_deal_screening()
elif page == "Portfolio Data":
    render_portfolio_data()
elif page == "AI Banker Commentary":
    render_ai_banker_commentary()

st.markdown("<div class='footer'>EC-AI Banking Intelligence Platform v0.8.4 · Demo data only · Do not use confidential bank data in public environments.</div>", unsafe_allow_html=True)
