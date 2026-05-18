# EC-AI Banking Engine v0.8.8.4 - Readable dashboard with sidebar thresholds
# Relationship Intelligence Prototype for Corporate & Investment Banking
# Streamlit single-file app

import math
import io
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def safe_sum(df, col: str, default: float = 0.0) -> float:
    """Return numeric sum safely without crashing if a column is missing."""
    try:
        if df is None or col not in df.columns:
            return default
        return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())
    except Exception:
        return default

def safe_mean(df, col: str, default=None):
    """Return numeric mean safely without crashing if a column is missing."""
    try:
        if df is None or col not in df.columns:
            return default
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            return default
        return float(s.mean())
    except Exception:
        return default

def safe_display_pct(x, digits: int = 1) -> str:
    """Safe percent display for percentage-point values."""
    try:
        if x is None or pd.isna(x):
            return "N/A"
        x = float(x)
        return f"{x:.{digits}f}%"
    except Exception:
        return "N/A"

import streamlit as st
import plotly.graph_objects as go

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="EC-AI Banking Engine v0.8.8.4",
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
    st.markdown("<div class='sidebar-ver'>v0.8.8.4 Demo</div>", unsafe_allow_html=True)

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



# =============================================================
# v0.8.8.4 STRATEGY UPGRADE LAYER
# Stronger executive strategy, RM action engine, cleaner DSC,
# richer wallet / product interpretation, and banker-grade tables.
# =============================================================

def fmt_bps(x: float, digits: int = 0) -> str:
    try:
        return f"{float(x):,.{digits}f}"
    except Exception:
        return "-"


def fmt_money_auto_m(v: float) -> str:
    """Input in USD million, display as M/B depending size."""
    try:
        v = float(v)
        if abs(v) >= 1000:
            return f"${v/1000:.1f}B"
        return f"${v:.1f}M"
    except Exception:
        return "-"


def style_banking_table(df: pd.DataFrame):
    """Executive-readable formatting for banking tables."""
    fmt = {}
    for c in df.columns:
        lc = c.lower()
        if "roe" in lc or "penetration" in lc or "share" in lc or "utilization" in lc:
            fmt[c] = "{:.1%}"
        elif "bps" in lc or c in ["LP", "EL", "NIM", "Spread"]:
            fmt[c] = "{:.0f}"
        elif any(k in lc for k in ["wallet", "revenue", "facility", "limit", "amount"]):
            fmt[c] = "{:,.1f}"
        elif any(k in lc for k in ["drawn", "exposure", "deposit", "rwa"]):
            fmt[c] = "{:,.1f}"
    return df.style.format(fmt)


def strategic_callout(title: str, bullets: List[str], tone: str = "blue") -> None:
    accent = {"blue": BLUE, "green": GREEN, "amber": AMBER, "red": RED}.get(tone, BLUE)
    bullet_html = "".join([f"<li>{b}</li>" for b in bullets])
    st.markdown(
        f"""
        <div class='insight-box' style='border-left:6px solid {accent}; padding:18px 22px; margin: 4px 0 18px 0;'>
          <b>{title}</b>
          <ul style='margin-top:10px; padding-left:20px;'>{bullet_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bar_fig(df: pd.DataFrame, x: str, y: str, title: str, unit: str = "M", height: int = 260, width: float = 0.34) -> go.Figure:
    """v0.8.8.4 upgraded bar chart: horizontal labels, larger values, cleaner executive display."""
    d = df.sort_values(y, ascending=False).copy()
    colors = [PALETTE[i] if i < len(PALETTE) else SLATE_2 for i in range(len(d))]
    suffix = "B" if unit == "B" else "M"
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d[x], y=d[y], marker_color=colors, width=width,
        text=[f"${v:.1f}{suffix}" if unit in ["M", "B"] else f"{v:.1f}" for v in d[y]],
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=13, color=NAVY),
        hovertemplate=f"%{{x}}<br>%{{y:.1f}} {suffix}<extra></extra>",
    ))
    fig.update_layout(title=dict(text=title, x=0.0, font=dict(size=16, color=NAVY)))
    fig = chart_layout(fig, height=height)
    fig.update_xaxes(tickangle=0, automargin=True, tickfont=dict(size=11, color=NAVY))
    fig.update_yaxes(title_text="USD billion" if unit == "B" else "USD million")
    return fig


def wallet_strategy_summary(w: pd.DataFrame) -> List[str]:
    d = w.sort_values("Wallet_Gap", ascending=False).copy()
    top = d.iloc[0]
    low_pen = d.sort_values("Penetration", ascending=True).iloc[0]
    comp = d.groupby("Lead_Competitor", as_index=False)["Wallet_Gap"].sum().sort_values("Wallet_Gap", ascending=False).head(1)
    comp_txt = comp.iloc[0]["Lead_Competitor"] if len(comp) else "key competitors"
    return [
        f"Largest monetisation gap sits in <b>{top['Product_Family']}</b> with estimated untapped wallet of <b>${top['Wallet_Gap']:.1f}M</b>.",
        f"Lowest penetration is <b>{low_pen['Product_Family']}</b> at <b>{low_pen['Penetration']*100:.1f}%</b>; this is the clearest under-served product angle.",
        f"Competitor-led leakage is visible around <b>{comp_txt}</b>; RM strategy should position a relationship-level solution, not a single-product pitch.",
        "Recommended play: lead with client treasury / funding need, then attach capital markets and transaction banking as a packaged relationship solution.",
    ]


def render_wallet_intelligence():
    st.markdown("<h1>Wallet Intelligence</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Identify where the bank is under-penetrated versus estimated client wallet potential across lending, transaction banking, markets and investment banking products.</div>", unsafe_allow_html=True)
    w = wallet.groupby("Product_Family", as_index=False).agg(
        Estimated_Wallet=("Estimated_Wallet", "sum"),
        Current_Revenue=("Current_Revenue", "sum"),
        Wallet_Gap=("Wallet_Gap", "sum"),
    )
    w["Penetration"] = w["Current_Revenue"] / w["Estimated_Wallet"]
    # Add competitor leakage by product for strategic reading.
    lead_comp = wallet.sort_values("Wallet_Gap", ascending=False).groupby("Product_Family").head(1)[["Product_Family", "Lead_Competitor"]]
    w = w.merge(lead_comp, on="Product_Family", how="left")

    strategic_callout("Executive interpretation", wallet_strategy_summary(w), "blue")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(w, "Product_Family", "Estimated_Wallet", "Estimated Wallet by Product", unit="M", height=410, width=0.30), use_container_width=True, key="wallet_est_v087")
    with c2:
        st.plotly_chart(bar_fig(w, "Product_Family", "Wallet_Gap", "Wallet Gap by Product", unit="M", height=410, width=0.30), use_container_width=True, key="wallet_gap_v087")
    strategic_callout("How to use this tab", [
        "Large wallet gap = revenue opportunity; high penetration = existing franchise strength.",
        "Low penetration in Transaction Banking / Markets usually points to treasury operating model, FX risk or cash management opportunity.",
        "Competitor-led products identify where rival banks are controlling the relationship conversation.",
    ], "green")
    st.dataframe(style_banking_table(w.sort_values("Wallet_Gap", ascending=False)), use_container_width=True, hide_index=True)


def render_product_penetration():
    st.markdown("<h1>Product Penetration</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Revenue and exposure across product hierarchy: lending, transaction banking, markets and investment banking products.</div>", unsafe_allow_html=True)
    prod = product.copy()
        total_rev = safe_sum(country, 'Revenue') or safe_sum(country, 'Total_Revenue')
        total_exp = safe_sum(country, 'Exposure') or safe_sum(country, 'Lending_Exposure')
    prod["Revenue_Share"] = prod["Revenue"] / total_rev
    prod["Exposure_Share"] = prod["Exposure"] / total_exp
    prod["Revenue_per_Exposure"] = prod["Revenue"] / prod["Exposure"].replace(0, np.nan)
    best = prod.sort_values("Revenue_per_Exposure", ascending=False).iloc[0]
    largest = prod.sort_values("Revenue", ascending=False).iloc[0]
    balance = prod.sort_values("Exposure", ascending=False).iloc[0]
    strategic_callout("Product strategy readout", [
        f"<b>{largest['Product_Type']}</b> is the largest revenue contributor at <b>${largest['Revenue']:.1f}M</b>.",
        f"<b>{balance['Product_Type']}</b> consumes the most balance sheet with <b>${balance['Exposure']:.1f}B</b> exposure.",
        f"Best revenue intensity is <b>{best['Product_Type']}</b>; use this to identify fee / spread-efficient products to scale.",
        "RM action: protect balance-sheet products, but attach fee products such as Markets, DCM, Cash Management and Investment Banking to improve relationship RoE.",
    ], "blue")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(prod, "Product_Type", "Revenue", "Product Revenue", unit="M", height=390, width=0.26), use_container_width=True, key="prod_rev_v087")
    with c2:
        st.plotly_chart(bar_fig(prod, "Product_Type", "Exposure", "Product Exposure", unit="B", height=390, width=0.26), use_container_width=True, key="prod_exp_v087")
    st.dataframe(style_banking_table(prod.sort_values("Revenue", ascending=False)), use_container_width=True, hide_index=True)


def render_deal_screening():
    st.markdown("<h1>Deal Screening (DSC)</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mini DSC dashboard: approved amount, Tx RoE, NIM, hurdle view and pricing quality.</div>", unsafe_allow_html=True)
    d = dsc.copy()
    d["Screen_Date"] = pd.to_datetime(d["Screen_Date"], errors="coerce")
    d["Tx_RoE_Bucket"] = pd.cut(d["Tx_RoE"], bins=[0,0.10,0.15,0.20,1], labels=["0–10%", "10–15%", "15–20%", ">20%"])
    d["NIM_Bucket"] = pd.cut(d["NIM_bps"], bins=[-1,30,60,100,10000], labels=["Below 30 bps", "30–60 bps", "60–100 bps", "Over 100 bps"])
    d["Pass_RoE"] = d["Tx_RoE"] >= roe_floor
    d["Pass_NIM"] = d["NIM_bps"] >= margin_floor
    d["Strategic_Decision"] = np.select(
        [d["Pass_RoE"] & d["Pass_NIM"], d["Pass_RoE"] & ~d["Pass_NIM"], ~d["Pass_RoE"] & d["Pass_NIM"]],
        ["Approve / Prioritise", "Reprice", "Reduce RWA / add fees"],
        default="Escalate / restructure"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Deals", f"{len(d)}", "screened sample"), unsafe_allow_html=True)
    c2.markdown(metric_card("Facility Limit", fmt_m(d["Facility_Limit_M"].sum()), "screened amount"), unsafe_allow_html=True)
    c3.markdown(metric_card("Avg Tx RoE", f"{d['Tx_RoE'].mean()*100:.1f}%", "transaction return"), unsafe_allow_html=True)
    c4.markdown(metric_card("Avg NIM", f"{d['NIM_bps'].mean():.0f} bps", "price margin"), unsafe_allow_html=True)

    pass_rate = float((d["Pass_RoE"] & d["Pass_NIM"]).mean())
    reprice_count = int((d["Strategic_Decision"].eq("Reprice")).sum())
    restructure_count = int((d["Strategic_Decision"].eq("Escalate / restructure")).sum())
    strategic_callout("Deal strategy readout", [
        f"<b>{pass_rate*100:.0f}%</b> of screened deals pass both RoE and NIM thresholds.",
        f"<b>{reprice_count}</b> deals pass RoE but miss pricing floor — candidates for repricing / fee uplift.",
        f"<b>{restructure_count}</b> deals miss both tests — candidates for RWA reduction, collateral improvement or relationship-level exception approval.",
        "Use DSC as a forward-looking control tower: not just approval volume, but quality of future balance-sheet deployment.",
    ], "amber")

    by_month = (d.dropna(subset=["Screen_Date"])
                .assign(Month=lambda x: x["Screen_Date"].dt.to_period("M").dt.to_timestamp())
                .groupby("Month", as_index=False)
                .agg(Facility_Limit_M=("Facility_Limit_M","sum"), Deals=("DS_ID","count"), Tx_RoE=("Tx_RoE","mean"), NIM_bps=("NIM_bps","mean")))
    by_month["Month_Label"] = by_month["Month"].dt.strftime("%b-%y")
    c5, c6 = st.columns(2, gap="large")
    with c5:
        st.plotly_chart(bar_fig(by_month, "Month_Label", "Facility_Limit_M", "Approved Amount by Month", unit="M", height=320, width=0.28), use_container_width=True, key="dsc_month_v087")
    with c6:
        by_country = d.groupby("Country", as_index=False).agg(Expected_Draw_B=("Expected_Draw_B","sum"), Tx_RoE=("Tx_RoE","mean"), NIM_bps=("NIM_bps","mean"))
        st.plotly_chart(bar_fig(by_country, "Country", "Expected_Draw_B", "Expected Draw by Country", unit="B", height=320, width=0.36), use_container_width=True, key="dsc_country_v087")

    c7, c8 = st.columns(2, gap="large")
    with c7:
        bucket = d.groupby("NIM_Bucket", observed=True, as_index=False).agg(Facility_Limit_M=("Facility_Limit_M", "sum"), Deals=("DS_ID", "count"))
        st.plotly_chart(bar_fig(bucket, "NIM_Bucket", "Facility_Limit_M", "NIM Bucket by Facility Limit", unit="M", height=320, width=0.36), use_container_width=True, key="dsc_nim_bucket_v087")
    with c8:
        decision = d.groupby("Strategic_Decision", as_index=False).agg(Facility_Limit_M=("Facility_Limit_M", "sum"), Deals=("DS_ID", "count"))
        st.plotly_chart(bar_fig(decision, "Strategic_Decision", "Facility_Limit_M", "Strategic Decision by Facility Limit", unit="M", height=320, width=0.36), use_container_width=True, key="dsc_decision_v087")

    st.markdown("<h2>Deal List</h2>", unsafe_allow_html=True)
    show_cols = ["DS_ID", "Relationship_Name", "Country", "Product_Type", "Facility_Limit_M", "Expected_Utilization", "Expected_Draw_B", "Spread_bps", "LP_bps", "BAC_bps", "EL_bps", "NIM_bps", "Tx_RoE", "Strategic_Decision", "Status"]
    show_cols = [c for c in show_cols if c in d.columns]
    st.dataframe(style_banking_table(d.sort_values("Facility_Limit_M", ascending=False)[show_cols]), use_container_width=True, hide_index=True)


def banker_need_hypothesis(r: pd.Series, gap: pd.DataFrame, client_dsc: pd.DataFrame) -> str:
    ltd = clean_number(r["Lending_Drawn"]) / max(clean_number(r["Deposit_Balance"]), 0.01)
    top_gap = gap.iloc[0]["Product_Family"] if len(gap) else "Transaction Banking"
    if ltd > 1.15:
        return f"funding, refinancing and balance-sheet optimisation, with {top_gap} as the first cross-sell angle"
    if clean_number(r["Deposit_Balance"]) > clean_number(r["Lending_Drawn"]) * 1.5:
        return f"treasury control, operating balance stickiness and liquidity monetisation, then connect to {top_gap} wallet gap"
    if len(client_dsc) and client_dsc["NIM_bps"].mean() < margin_floor:
        return "pricing improvement and fee attachment, because screened deal margins are below the pricing floor"
    return f"relationship deepening through {top_gap}, capital efficiency and selective product specialist engagement"


def build_ai_banker_strategy(client: str, r: pd.Series, gap: pd.DataFrame, client_dsc: pd.DataFrame) -> Dict[str, List[str]]:
    top_gap = gap.iloc[0] if len(gap) else None
    second_gap = gap.iloc[1] if len(gap) > 1 else None
    roe_txt = f"{r['LTM_Group_RoE']*100:.1f}%"
    deposit_to_loan = clean_number(r["Deposit_Balance"]) / max(clean_number(r["Lending_Drawn"]), 0.01)
    wallet_pen = clean_number(r["Wallet_Penetration"])
    dsc_avg_roe = client_dsc["Tx_RoE"].mean() if len(client_dsc) else np.nan
    dsc_avg_nim = client_dsc["NIM_bps"].mean() if len(client_dsc) else np.nan
    gap_text = f"<b>{top_gap['Product_Family']}</b> gap of <b>${top_gap['Wallet_Gap']:.1f}M</b>" if top_gap is not None else "product wallet gap not available"
    second_text = f" and <b>{second_gap['Product_Family']}</b>" if second_gap is not None else ""
    comp = str(top_gap["Lead_Competitor"]) if top_gap is not None else "lead competitor"

    return {
        "Relationship snapshot": [
            f"<b>{client}</b> is a <b>{r['Sector']}</b> client in <b>{r['Country']}</b> with <b>{fmt_b(r['Lending_Drawn'])}</b> lending exposure and <b>{fmt_b(r['Deposit_Balance'])}</b> deposits.",
            f"Deposit-to-loan multiple is approximately <b>{deposit_to_loan:.1f}x</b>, indicating {'a liquidity-rich treasury franchise' if deposit_to_loan > 1 else 'a lending-led relationship requiring balance-sheet discipline'}.",
            f"LTM Group RoE is <b>{roe_txt}</b> versus current floor of <b>{roe_floor*100:.0f}%</b>; relationship wallet penetration is <b>{wallet_pen*100:.1f}%</b>.",
        ],
        "Wallet gap analysis": [
            f"Largest monetisation opportunity is {gap_text}{second_text}.",
            f"Current lead competitor in the largest gap area is <b>{comp}</b>; this suggests the RM needs to shift the conversation from product pitching to relationship-level problem solving.",
            "Low penetration should be framed as unrealised client need: treasury control, funding resilience, risk hedging, capital markets access or strategic financing.",
        ],
        "Cross-sell strategy": [
            f"Primary pitch angle: <b>{banker_need_hypothesis(r, gap, client_dsc)}</b>.",
            "Lead with client business need first, then attach product specialists only after the need is clearly established.",
            "Recommended package: treasury / cash management + markets risk management + selective DCM / IB discussion where wallet gap supports it.",
        ],
        "Risk / return assessment": [
            f"Portfolio RoE signal is {'above hurdle and relationship-accretive' if r['LTM_Group_RoE'] >= roe_floor else 'below hurdle and requires pricing or RWA remediation'}.",
            (f"DSC read-through: average screened Tx RoE is <b>{dsc_avg_roe*100:.1f}%</b> and average NIM is <b>{dsc_avg_nim:.0f} bps</b>." if len(client_dsc) else "No DSC deals currently linked to this client in the demo data."),
            "Balance-sheet growth should be selective: prioritise higher RoE drawdowns and require fee / deposit attachment where lending consumes RWA.",
        ],
        "RM action plan": [
            "1. Open with a relationship review: liquidity position, debt maturity, funding plans and treasury operating model.",
            "2. Quantify wallet gap by product and show where the client already gives wallet to competitors.",
            "3. Ask for one senior client conversation around operating balances / refinancing / risk management rather than multiple disconnected product calls.",
            "4. Bring the right specialist only after the client need is validated: TB for cash, Markets for FX/rates, DCM/IB for funding or strategic activity.",
            "5. Track next action in a simple pipeline: need identified, product owner assigned, proposal date, expected revenue and competitor displacement target.",
        ]
    }


def render_ai_banker_commentary():
    st.markdown("<h1>AI Banker Commentary</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Executive Relationship Intelligence — RM pitch angles, wallet strategy, risk / return read-through and next-best actions.</div>", unsafe_allow_html=True)
    client = st.selectbox("Select client", relationships["Relationship_Name"].sort_values().tolist(), key="ai_client_select_v087")
    r = relationships[relationships["Relationship_Name"].eq(client)].iloc[0]
    gap = wallet[wallet["Relationship_Name"].eq(client)].sort_values("Wallet_Gap", ascending=False).head(5)
    client_dsc = dsc[dsc["Relationship_Name"].eq(client)].copy()

    sections = build_ai_banker_strategy(client, r, gap, client_dsc)
    top_cards = st.columns(5)
    kpis = [
        ("Exposure", fmt_b(r["Lending_Drawn"]), "Drawn"),
        ("Deposits", fmt_b(r["Deposit_Balance"]), "Franchise"),
        ("RoE", f"{r['LTM_Group_RoE']*100:.1f}%", "LTM Group"),
        ("Wallet Pen.", f"{r['Wallet_Penetration']*100:.1f}%", "Estimated"),
        ("Top Gap", gap.iloc[0]["Product_Family"] if len(gap) else "N/A", "Product angle"),
    ]
    for col, (label, val, note) in zip(top_cards, kpis):
        col.markdown(metric_card(label, val, note), unsafe_allow_html=True)

    for i, (title, bullets) in enumerate(sections.items()):
        tone = ["blue", "amber", "green", "red", "blue"][i % 5]
        strategic_callout(title, bullets, tone)

    st.markdown("<h2>Top Product Gap Angles</h2>", unsafe_allow_html=True)
    show = gap[["Product_Family", "Estimated_Wallet", "Current_Revenue", "Wallet_Gap", "Wallet_Penetration", "Lead_Competitor"]].copy()
    st.dataframe(style_banking_table(show), use_container_width=True, hide_index=True)

    st.markdown("<h2>Suggested RM Opening Script</h2>", unsafe_allow_html=True)
    script = f"""
    <div class='insight-box'>
      <b>Opening angle for {client}</b><br><br>
      “Based on your current relationship profile, we see a strong link between your balance sheet position and several under-penetrated wallet areas. Rather than discuss products separately, I suggest we start with your treasury and funding priorities, then identify where we can help reduce friction, improve returns, and consolidate wallet currently sitting with competitor banks.”
    </div>
    """
    st.markdown(script, unsafe_allow_html=True)



# =============================================================
# v0.8.8.4 HOTFIX LAYER — readability, strategy and table fixes
# =============================================================

def _wrap_axis_label(label, max_len=13):
    """Keep x-axis labels horizontal but readable by wrapping into 2-3 lines."""
    s = str(label)
    if len(s) <= max_len:
        return s
    parts = s.replace(" / ", "/").split()
    if len(parts) == 1:
        # Split on slash first, otherwise hard wrap.
        if "/" in s:
            return s.replace("/", "/<br>")
        return "<br>".join([s[i:i+max_len] for i in range(0, len(s), max_len)])
    lines, cur = [], ""
    for w in parts:
        if len((cur + " " + w).strip()) <= max_len:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return "<br>".join(lines[:3])


def _fmt_m_1(x):
    try:
        return f"${float(x):,.1f}M"
    except Exception:
        return "-"


def _fmt_b_1(x):
    try:
        return f"${float(x):,.1f}B"
    except Exception:
        return "-"


def _fmt_pct_1(x):
    try:
        return f"{float(x)*100:.1f}%"
    except Exception:
        return "-"


def bar_fig(df: pd.DataFrame, x: str, y: str, title: str, unit: str = "M", height: int = 260, width: float = 0.30) -> go.Figure:
    """Final v0.8.8.4 chart style: horizontal wrapped labels, larger values, wider chart margins."""
    d = df.sort_values(y, ascending=False).copy()
    colors = [PALETTE[i] if i < len(PALETTE) else SLATE_2 for i in range(len(d))]
    suffix = "B" if unit == "B" else "M"
    vals = pd.to_numeric(d[y], errors="coerce").fillna(0)
    labels = [f"${v:.1f}{suffix}" if unit in ["M", "B"] else f"{v:.1f}" for v in vals]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d[x].astype(str), y=vals, marker_color=colors, width=width,
        text=labels, textposition="outside", cliponaxis=False,
        textfont=dict(size=14, color=NAVY),
        hovertemplate=f"%{{x}}<br>%{{y:.1f}} {suffix}<extra></extra>",
    ))
    ymax = float(vals.max()) if len(vals) else 0
    fig.update_layout(
        title=dict(text=title, x=0.0, font=dict(size=17, color=NAVY)),
        template="plotly_white", height=height,
        margin=dict(l=52, r=24, t=44, b=92),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Inter, Arial", size=14, color=NAVY),
        showlegend=False,
        bargap=0.58,
    )
    fig.update_xaxes(
        showgrid=False, showline=False, zeroline=False, tickangle=0,
        tickmode="array", tickvals=d[x].astype(str).tolist(),
        ticktext=[_wrap_axis_label(v, 13) for v in d[x].astype(str).tolist()],
        tickfont=dict(size=12, color=NAVY), automargin=True,
    )
    fig.update_yaxes(
        title_text="USD billion" if unit == "B" else "USD million",
        showgrid=False, showline=False, zeroline=False,
        tickfont=dict(size=12, color="#50627A"),
        range=[0, ymax * 1.18 if ymax else 1],
    )
    return fig


def donut_deposit(deposit: pd.DataFrame) -> go.Figure:
    d = deposit.copy()
    total = float(d["Deposit_Balance"].sum())
    fig = go.Figure(data=[go.Pie(
        labels=d["Deposit_Type"], values=d["Deposit_Balance"], hole=0.62,
        marker=dict(colors=[NAVY, BLUE, SLATE, "#CBD3DA"]),
        textinfo="none", sort=False,
        domain=dict(x=[0.02, 0.62], y=[0.04, 0.96]),
        hovertemplate="%{label}<br>$%{value:.1f}B (%{percent})<extra></extra>",
    )])
    fig.update_layout(
        annotations=[dict(
            text=f"<b>${total:.1f}B</b><br><span style='font-size:11px'>Total</span>",
            x=0.32, y=0.50, xref="paper", yref="paper", showarrow=False,
            xanchor="center", yanchor="middle", align="center",
            font=dict(size=16, color=NAVY, family="Inter, Arial")
        )],
        legend=dict(
            x=0.72, y=0.20, xanchor="left", yanchor="bottom",
            orientation="v", font=dict(size=12, color=NAVY),
            bgcolor="rgba(255,255,255,0)", borderwidth=0,
            itemsizing="constant"
        ),
        title=dict(text="Deposits by Type (USD b)", x=0.0, font=dict(size=16, color=NAVY)),
        template="plotly_white", height=300,
        margin=dict(l=18, r=8, t=34, b=18),
        paper_bgcolor="white", plot_bgcolor="white", showlegend=True,
        font=dict(family="Inter, Arial", size=13, color=NAVY),
    )
    return fig


def style_banking_table(df: pd.DataFrame):
    """Executive-readable table formatting with right-aligned numeric headers."""
    fmt = {}
    for c in df.columns:
        lc = str(c).lower()
        if "roe" in lc or "penetration" in lc or "share" in lc or "utilization" in lc:
            fmt[c] = lambda v: _fmt_pct_1(v)
        elif "bps" in lc or any(k in lc for k in ["nim", "spread", "lp", "el", "bac"]):
            fmt[c] = lambda v: f"{float(v):,.0f} bps" if pd.notna(v) else "-"
        elif any(k in lc for k in ["wallet", "revenue", "facility", "limit", "amount"]):
            fmt[c] = lambda v: f"{float(v):,.1f}" if pd.notna(v) else "-"
        elif any(k in lc for k in ["drawn", "exposure", "deposit", "rwa", "balance"]):
            fmt[c] = lambda v: f"{float(v):,.1f}" if pd.notna(v) else "-"
    return (df.style.format(fmt)
            .set_properties(**{"text-align": "right"})
            .set_table_styles([
                {"selector": "th", "props": [("text-align", "right"), ("font-weight", "700")]},
                {"selector": "td", "props": [("text-align", "right")]},
            ]))


def competitor_table_format(df: pd.DataFrame):
    d = df.copy()
    for c in ["Estimated_Wallet", "Current_Revenue", "Wallet_Gap"]:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.style.format({
        "Estimated_Wallet": lambda v: f"${v:,.1f}M",
        "Current_Revenue": lambda v: f"${v:,.1f}M",
        "Wallet_Gap": lambda v: f"${v:,.1f}M",
        "Penetration": lambda v: f"{v*100:.1f}%",
    }).set_properties(**{"text-align": "right"}).set_table_styles([
        {"selector":"th", "props":[("text-align","right"),("font-weight","700")]}
    ])


def render_revenue_exposure():
    st.markdown("<h1>Revenue & Exposure</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Historical portfolio revenue, exposure and product penetration view.</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(product, "Product_Type", "Revenue", "Revenue by Product Type", unit="M", height=470, width=0.24), use_container_width=True, key="rev_product_v087_hotfix")
    with c2:
        st.plotly_chart(bar_fig(product, "Product_Type", "Exposure", "Exposure by Product Type", unit="B", height=470, width=0.24), use_container_width=True, key="exp_product_v087_hotfix")
    st.markdown("<h2>Top Relationship Table</h2>", unsafe_allow_html=True)
    cols = ["Relationship_Name", "Country", "Sector", "Client_Tier", "Total_Revenue", "Lending_Drawn", "Facility_Limit", "Deposit_Balance", "LTM_Group_RoE"]
    st.dataframe(style_banking_table(relationships[cols].sort_values("Total_Revenue", ascending=False)), use_container_width=True, hide_index=True)


def render_capital_efficiency():
    st.markdown("<h1>Capital Efficiency</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Exposure, capital usage, RWA and profitability discipline.</div>", unsafe_allow_html=True)
    avg_roe = float(relationships["LTM_Group_RoE"].mean())
    below = relationships[relationships["LTM_Group_RoE"] < roe_floor]
    largest_exposure = relationships.sort_values("Lending_Drawn", ascending=False).iloc[0]
    best_roe = relationships.sort_values("LTM_Group_RoE", ascending=False).iloc[0]
    strategic_callout("Capital strategy readout", [
        f"Portfolio average RoE is <b>{avg_roe*100:.1f}%</b> versus current floor of <b>{roe_floor*100:.0f}%</b>.",
        f"Largest exposure relationship is <b>{largest_exposure['Relationship_Name']}</b> with <b>{fmt_b(largest_exposure['Lending_Drawn'])}</b> drawn exposure — monitor capital usage and pricing discipline.",
        f"Highest-return relationship is <b>{best_roe['Relationship_Name']}</b> at <b>{best_roe['LTM_Group_RoE']*100:.1f}%</b>; use it as a benchmark for pricing, fee attachment and relationship structure.",
        "RM action: below-floor relationships need one of three levers — reprice, reduce RWA intensity, or attach fee / deposit products to lift total relationship return.",
    ], "blue")
    st.plotly_chart(combo_capital_fig(relationships, roe_floor), use_container_width=True, key="capital_combo_full_v087_hotfix")
    st.markdown("<h2>Watchlist: Below Profitability Floor</h2>", unsafe_allow_html=True)
    if below.empty:
        st.success("No below-floor relationships detected.")
    else:
        st.dataframe(style_banking_table(below[["Relationship_Name", "Country", "Sector", "Lending_Drawn", "RWA", "LTM_Group_RoE", "Deposit_Balance"]].sort_values("Lending_Drawn", ascending=False)), use_container_width=True, hide_index=True)


def render_deposit_intelligence():
    st.markdown("<h1>Deposit Intelligence</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Deposit franchise, operational balance and treasury opportunity view.</div>", unsafe_allow_html=True)
    casa = float(deposit.loc[deposit["Deposit_Type"].eq("CASA"), "Deposit_Balance"].sum() / deposit["Deposit_Balance"].sum())
    td = float(deposit.loc[deposit["Deposit_Type"].eq("Time Deposit"), "Deposit_Balance"].sum() / deposit["Deposit_Balance"].sum())
    largest_dep = country.sort_values("Deposit_Balance", ascending=False).iloc[0]
    maturity_top = maturity.sort_values("Deposit_Balance", ascending=False).iloc[0]
    strategic_callout("AI deposit strategy readout", [
        f"Total deposit franchise is <b>{fmt_b(relationships['Deposit_Balance'].sum())}</b>; <b>{largest_dep['Country']}</b> is the largest contributor at <b>{fmt_b(largest_dep['Deposit_Balance'])}</b>.",
        f"CASA ratio is <b>{casa*100:.0f}%</b>, giving the portfolio a meaningful low-cost and sticky funding base.",
        f"Time deposit share is approximately <b>{td*100:.0f}%</b>; this creates repricing and rollover conversations as rates change.",
        f"Largest maturity bucket is <b>{maturity_top['Maturity_Bucket']}</b> with <b>{fmt_b(maturity_top['Deposit_Balance'])}</b>; RM teams should monitor concentration and rollover dates.",
        "Treasury pitch angle: use operating balances, cash concentration, liquidity sweeping and FX flow visibility to convert deposit franchise into fee wallet.",
        "Management action: segment deposits by stability — operating balances for relationship stickiness, time deposits for repricing risk, and surplus liquidity for investment / markets dialogue.",
    ], "green")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(country, "Country", "Deposit_Balance", "Deposits by Country", unit="B", height=340, width=0.32), use_container_width=True, key="dep_country_full_v087_hotfix")
    with c2:
        st.plotly_chart(donut_deposit(deposit), use_container_width=True, key="dep_type_donut_full_v087_hotfix")
    c3, c4 = st.columns([1.15, .85], gap="large")
    with c3:
        st.plotly_chart(maturity_fig(maturity), use_container_width=True, key="dep_maturity_full_v087_hotfix")
    with c4:
        st.markdown("<div class='small-card'><h3>Deposit Commentary</h3><br><b>Liquidity profile</b> tells bankers whether deposits are stable operating balances, price-sensitive term money, or short-term liquidity. CASA and operational balances indicate stickiness; maturity ladder identifies rollover risk, repricing windows and treasury dialogue opportunities.<br><br><b>Banker angle:</b> do not pitch deposits alone — connect liquidity to cash management, FX, rates hedging, investment sweep and working-capital needs.</div>", unsafe_allow_html=True)
    st.markdown("<h2>Deposit Relationship Table</h2>", unsafe_allow_html=True)
    table = relationships[["Relationship_Name", "Country", "Client_Tier", "Deposit_Balance", "Total_Revenue"]].copy()
    table["Deposit_Type"] = np.random.default_rng(4).choice(["CASA", "Operational", "Time Deposit"], len(table))
    table["Liquidity_Class"] = table["Deposit_Type"].map({"CASA":"Liquid", "Operational":"Operational", "Time Deposit":"Term"})
    table["Deposit_Maturity_Date"] = [datetime(2024, 3, 31) + timedelta(days=int(x)) for x in np.random.default_rng(7).integers(15, 420, len(table))]
    table = table.rename(columns={"Total_Revenue": "Deposit_Revenue_Proxy"})
    st.dataframe(style_banking_table(table.sort_values("Deposit_Balance", ascending=False)), use_container_width=True, hide_index=True)


def render_competitor_benchmarking():
    st.markdown("<h1>Competitor Benchmarking</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Estimated wallet, current share and competitor lead bank by product family.</div>", unsafe_allow_html=True)
    comp = wallet.groupby("Lead_Competitor", as_index=False).agg(Estimated_Wallet=("Estimated_Wallet", "sum"), Current_Revenue=("Current_Revenue", "sum"), Wallet_Gap=("Wallet_Gap", "sum"))
    comp["Penetration"] = comp["Current_Revenue"] / comp["Estimated_Wallet"]
    comp = comp.sort_values("Estimated_Wallet", ascending=False).reset_index(drop=True)
    top_wallet = comp.iloc[0]
    low_pen = comp.sort_values("Penetration", ascending=True).iloc[0]
    strategic_callout("Competitor strategy readout", [
        f"Rank view is sorted by <b>estimated wallet size</b>, not only gap. <b>{top_wallet['Lead_Competitor']}</b> represents the largest competitor-linked wallet at <b>${top_wallet['Estimated_Wallet']:.1f}M</b>.",
        f"Lowest penetration competitor pocket is <b>{low_pen['Lead_Competitor']}</b> at <b>{low_pen['Penetration']*100:.1f}%</b>; this is the easiest story for displacement if the client need is clear.",
        "Use this tab to prepare competitor displacement plans: identify where the rival bank leads, what product family they control, and which client problem we can solve better.",
        "Pitch approach: avoid saying ‘we want more wallet’; instead lead with liquidity, refinancing, FX/rates risk, working-capital pain points or strategic funding needs.",
        "RM action: convert each large wallet gap into a named pursuit with product owner, client sponsor, next meeting date and expected revenue capture.",
    ], "amber")
    st.plotly_chart(bar_fig(comp, "Lead_Competitor", "Estimated_Wallet", "Estimated Wallet by Competitor Relationship", unit="M", height=360, width=0.34), use_container_width=True, key="competitor_wallet_v087_hotfix")
    st.dataframe(competitor_table_format(comp), use_container_width=True, hide_index=True)


def render_client_overview():
    st.markdown("<h1>Client Overview</h1>", unsafe_allow_html=True)
    client = st.selectbox("Select relationship", relationships["Relationship_Name"].sort_values().tolist(), key="client_select_v087_hotfix")
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
    c1.markdown(metric_card("Revenue", fmt_m(r["Total_Revenue"]), "LTM revenue"), unsafe_allow_html=True)
    c2.markdown(metric_card("Exposure", fmt_b(r["Lending_Drawn"]), "Drawn balance"), unsafe_allow_html=True)
    c3.markdown(metric_card("Deposits", fmt_b(r["Deposit_Balance"]), "Franchise"), unsafe_allow_html=True)
    c4.markdown(metric_card("Wallet Penetration", fmt_pct(r["Wallet_Penetration"]), "Estimated"), unsafe_allow_html=True)
    gap = wallet[wallet["Relationship_Name"].eq(client)].sort_values("Wallet_Gap", ascending=False).head(5)
    strategic_callout("Client strategy", [
        f"Top product gap is <b>{gap.iloc[0]['Product_Family']}</b> with <b>${gap.iloc[0]['Wallet_Gap']:.1f}M</b> untapped wallet." if len(gap) else "No wallet gap available.",
        "Start with the balance-sheet and treasury need, then connect product gaps into one relationship conversation.",
        "Use this page as a pre-call briefing: relationship scale, wallet gap, return profile and next-best pitch angle.",
    ], "blue")
    st.markdown("<h2>Product Gap Table</h2>", unsafe_allow_html=True)
    if len(gap):
        st.dataframe(style_banking_table(gap[["Product_Family", "Estimated_Wallet", "Current_Revenue", "Wallet_Gap", "Wallet_Penetration", "Lead_Competitor"]]), use_container_width=True, hide_index=True)


def render_product_penetration():
    st.markdown("<h1>Product Penetration</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Revenue and exposure across product hierarchy: lending, transaction banking, markets and investment banking products.</div>", unsafe_allow_html=True)
    prod = product.copy()
    total_rev = float(prod["Revenue"].sum())
    total_exp = float(prod["Exposure"].sum())
    prod["Revenue_Share"] = prod["Revenue"] / total_rev
    prod["Exposure_Share"] = prod["Exposure"] / total_exp
    prod["Revenue_per_Exposure"] = prod["Revenue"] / prod["Exposure"].replace(0, np.nan)
    best = prod.sort_values("Revenue_per_Exposure", ascending=False).iloc[0]
    largest = prod.sort_values("Revenue", ascending=False).iloc[0]
    strategic_callout("Product strategy readout", [
        f"<b>{largest['Product_Type']}</b> is the largest revenue contributor at <b>${largest['Revenue']:.1f}M</b>.",
        f"Best revenue intensity is <b>{best['Product_Type']}</b>; use this to identify fee / spread-efficient products to scale.",
        "RM action: protect balance-sheet products, but attach fee products such as Markets, DCM, Cash Management and Investment Banking to improve relationship RoE.",
    ], "blue")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(bar_fig(prod, "Product_Type", "Revenue", "Product Revenue", unit="M", height=470, width=0.24), use_container_width=True, key="prod_rev_v087_hotfix")
    with c2:
        st.plotly_chart(bar_fig(prod, "Product_Type", "Exposure", "Product Exposure", unit="B", height=470, width=0.24), use_container_width=True, key="prod_exp_v087_hotfix")
    st.dataframe(style_banking_table(prod.sort_values("Revenue", ascending=False)), use_container_width=True, hide_index=True)


def render_portfolio_data():
    st.markdown("<h1>Portfolio Data</h1>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Historical actual facilities, drawdown, revenue, deposits and RWA.</div>", unsafe_allow_html=True)
    excel_bytes = make_excel_download(data)
    st.download_button("Download sample banking data (Excel)", data=excel_bytes, file_name="ecai_banking_sample_data_v087.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_excel_v087_hotfix")
    view = st.selectbox("Table", list(data.keys()), key="portfolio_table_select_v087_hotfix")
    st.dataframe(style_banking_table(data[view]), use_container_width=True, hide_index=True)



# =============================================================
# v0.8.8.4 FINAL OVERRIDES — readability + red-error fixes
# =============================================================

def _safe_float_v088(v, default=np.nan):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def _fmt_num_1_v088(v):
    x = _safe_float_v088(v)
    return "-" if pd.isna(x) else f"{x:,.1f}"


def _fmt_money_m_1_v088(v):
    x = _safe_float_v088(v)
    return "-" if pd.isna(x) else f"${x:,.1f}M"


def _fmt_money_b_1_v088(v):
    x = _safe_float_v088(v)
    return "-" if pd.isna(x) else f"${x:,.1f}B"


def _fmt_pct_1_v088(v):
    x = _safe_float_v088(v)
    if pd.isna(x):
        return "-"
    if abs(x) <= 1.5:
        x = x * 100
    return f"{x:.1f}%"


def _fmt_bps_0_v088(v):
    x = _safe_float_v088(v)
    return "-" if pd.isna(x) else f"{x:,.0f} bps"


def _wrap_axis_label_v088(s: str, width: int = 12) -> str:
    s = str(s)
    words = s.split()
    if len(words) <= 1 and len(s) > width:
        return "<br>".join([s[i:i+width] for i in range(0, len(s), width)][:3])
    lines, cur = [], ""
    for w in words:
        if len((cur + " " + w).strip()) <= width:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return "<br>".join(lines[:3])


def style_banking_table(df: pd.DataFrame):
    """v0.8.8.4 safe table formatting — prevents red errors from mixed text/numeric fields."""
    d = df.copy()
    fmt = {}
    for c in d.columns:
        lc = str(c).lower()
        if lc.endswith('_bps') or lc in ['nim', 'spread', 'lp', 'el', 'bac', 'nim_bps', 'spread_bps', 'lp_bps', 'el_bps', 'bac_bps']:
            fmt[c] = _fmt_bps_0_v088
        elif any(k in lc for k in ['roe', 'penetration', 'share', 'utilization', 'ratio']):
            fmt[c] = _fmt_pct_1_v088
        elif any(k in lc for k in ['wallet', 'revenue', 'facility', 'limit', 'amount']):
            fmt[c] = _fmt_num_1_v088
        elif any(k in lc for k in ['drawn', 'exposure', 'deposit', 'rwa', 'balance', 'expected_draw']):
            fmt[c] = _fmt_num_1_v088
    return (d.style.format(fmt)
            .set_properties(**{'text-align': 'right', 'font-size': '13px'})
            .set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'right'), ('font-weight', '800'), ('font-size', '13px'), ('background-color', '#F7F9FC')]},
                {'selector': 'td', 'props': [('text-align', 'right'), ('font-size', '13px')]},
            ]))


def competitor_table_format(df: pd.DataFrame):
    d = df.copy()
    for c in ['Estimated_Wallet', 'Current_Revenue', 'Wallet_Gap', 'Penetration']:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors='coerce')
    return d.style.format({
        'Estimated_Wallet': _fmt_money_m_1_v088,
        'Current_Revenue': _fmt_money_m_1_v088,
        'Wallet_Gap': _fmt_money_m_1_v088,
        'Penetration': _fmt_pct_1_v088,
    }).set_properties(**{'text-align': 'right', 'font-size': '13px'}).set_table_styles([
        {'selector':'th', 'props':[('text-align','right'),('font-weight','800'),('background-color','#F7F9FC')]}
    ])


def bar_fig(df: pd.DataFrame, x: str, y: str, title: str, unit: str = 'M', height: int = 380, width: float = 0.26) -> go.Figure:
    """v0.8.8.4: larger value labels + readable horizontal/wrapped x-axis."""
    d = df.copy()
    d[y] = pd.to_numeric(d[y], errors='coerce').fillna(0)
    d = d.sort_values(y, ascending=False)
    colors = [PALETTE[i] if i < len(PALETTE) else SLATE_2 for i in range(len(d))]
    suffix = 'B' if unit == 'B' else 'M'
    vals = d[y].astype(float)
    labels = [f'${v:.1f}{suffix}' if unit in ['M','B'] else f'{v:.1f}' for v in vals]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d[x].astype(str), y=vals, marker_color=colors, width=width,
        text=labels, textposition='outside', cliponaxis=False,
        textfont=dict(size=16, color=NAVY, family='Inter, Arial'),
        hovertemplate=f'%{{x}}<br>%{{y:.1f}} {suffix}<extra></extra>',
    ))
    ymax = float(vals.max()) if len(vals) else 0
    fig.update_layout(
        title=dict(text=title, x=0.0, font=dict(size=17, color=NAVY)),
        template='plotly_white', height=height,
        margin=dict(l=58, r=32, t=52, b=118),
        paper_bgcolor='white', plot_bgcolor='white',
        font=dict(family='Inter, Arial', size=14, color=NAVY),
        showlegend=False, bargap=0.64,
    )
    fig.update_xaxes(
        showgrid=False, showline=False, zeroline=False, tickangle=0,
        tickmode='array', tickvals=d[x].astype(str).tolist(),
        ticktext=[_wrap_axis_label_v088(v, 12) for v in d[x].astype(str).tolist()],
        tickfont=dict(size=12, color=NAVY), automargin=True,
    )
    fig.update_yaxes(
        title_text='USD billion' if unit == 'B' else 'USD million',
        showgrid=False, showline=False, zeroline=False,
        tickfont=dict(size=12, color='#50627A'),
        range=[0, ymax * 1.25 if ymax else 1],
    )
    return fig


def donut_deposit(deposit: pd.DataFrame) -> go.Figure:
    """v0.8.8.4 centered donut with annotation exactly at donut centre."""
    d = deposit.copy()
    total = float(pd.to_numeric(d['Deposit_Balance'], errors='coerce').fillna(0).sum())
    fig = go.Figure(data=[go.Pie(
        labels=d['Deposit_Type'], values=d['Deposit_Balance'], hole=0.62,
        marker=dict(colors=[NAVY, BLUE, SLATE, '#CBD3DA']),
        textinfo='none', sort=False,
        domain=dict(x=[0.07, 0.63], y=[0.08, 0.94]),
        hovertemplate='%{label}<br>$%{value:.1f}B (%{percent})<extra></extra>',
    )])
    fig.update_layout(
        annotations=[dict(
            text=f"<b>${total:.1f}B</b><br><span style='font-size:12px'>Total</span>",
            x=0.35, y=0.51, xref='paper', yref='paper', showarrow=False,
            xanchor='center', yanchor='middle', align='center',
            font=dict(size=18, color=NAVY, family='Inter, Arial')
        )],
        legend=dict(x=0.74, y=0.18, xanchor='left', yanchor='bottom', orientation='v', font=dict(size=13, color=NAVY), bgcolor='rgba(255,255,255,0)', borderwidth=0),
        title=dict(text='Deposits by Type (USD b)', x=0.0, font=dict(size=17, color=NAVY)),
        template='plotly_white', height=330,
        margin=dict(l=18, r=12, t=42, b=18),
        paper_bgcolor='white', plot_bgcolor='white', showlegend=True,
        font=dict(family='Inter, Arial', size=14, color=NAVY),
    )
    return fig


def render_executive_dashboard():
    top_filter_bar()
    st.markdown('<h1>Executive Portfolio Overview</h1>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>LTM performance summary — wallet, exposure, deposits, revenue and profitability.</div>", unsafe_allow_html=True)
    total_rev = safe_sum(country, 'Revenue')
    total_exp = safe_sum(country, 'Exposure')
    total_dep = safe_sum(country, 'Deposit_Balance')
    avg_roe = safe_mean(country, 'LTM_Group_RoE')
    cards = st.columns(6, gap='small')
    vals = [('REVENUE', fmt_b(total_rev/1000), 'demo vs PY'), ('NII', '$852.2M', 'Net interest income'), ('RWA', '$72.3B', 'Risk weighted assets'), ('LENDING EXPOSURE', fmt_b(total_exp), 'Drawn balance'), ('DEPOSITS', fmt_b(total_dep), 'Deposit franchise'), ('LTM GROUP ROE', f'{avg_roe*100:.1f}%', 'Portfolio return')]
    for col, (label, val, sub) in zip(cards, vals):
        col.markdown(metric_card(label, val, sub), unsafe_allow_html=True)
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap='large')
    with c1:
        with st.container(border=True):
            st.plotly_chart(bar_fig(country, 'Country', 'Revenue', 'Revenue by Country (USD)', unit='M', height=360, width=0.34), use_container_width=True, config={'displayModeBar': False}, key='exec_rev_country_v088')
    with c2:
        with st.container(border=True):
            st.plotly_chart(bar_fig(country, 'Country', 'Exposure', 'Exposure by Country (USD)', unit='B', height=360, width=0.34), use_container_width=True, config={'displayModeBar': False}, key='exec_exp_country_v088')
    st.markdown('<h2>Deposit Intelligence</h2>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Franchise strength, liquidity profile and treasury opportunities.</div>", unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4, gap='large')
    with d1:
        with st.container(border=True):
            st.plotly_chart(bar_fig(country, 'Country', 'Deposit_Balance', 'Deposits by Country', unit='B', height=330, width=0.34), use_container_width=True, config={'displayModeBar': False}, key='exec_dep_country_v088')
    with d2:
        with st.container(border=True):
            st.plotly_chart(donut_deposit(deposit), use_container_width=True, config={'displayModeBar': False}, key='exec_dep_donut_v088')
    casa = deposit.loc[deposit['Deposit_Type'].eq('CASA'), 'Deposit_Balance'].sum() / deposit['Deposit_Balance'].sum()
    ltd = country['Exposure'].sum() / country['Deposit_Balance'].sum()
    with d3:
        st.markdown(f"""
        <div class='small-card'>
          <h3>Liquidity Profile</h3><br>
          <div style='display:flex;justify-content:space-between;margin-bottom:13px;'><span>CASA Ratio</span><b style='color:{GREEN}'>{casa*100:.0f}%</b></div>
          <div style='display:flex;justify-content:space-between;margin-bottom:13px;'><span>Loan to Deposit Ratio</span><b style='color:{RED}'>{ltd*100:.0f}%</b></div>
          <div style='display:flex;justify-content:space-between;margin-bottom:13px;'><span>NSFR</span><b style='color:{GREEN}'>118%</b></div>
          <div style='display:flex;justify-content:space-between;'><span>LCR</span><b style='color:{GREEN}'>142%</b></div>
        </div>""", unsafe_allow_html=True)
    with d4:
        with st.container(border=True):
            st.plotly_chart(maturity_fig(maturity), use_container_width=True, config={'displayModeBar': False}, key='exec_maturity_v088')
    c3, c4 = st.columns([1.25, 1], gap='large')
    with c3:
        with st.container(border=True):
            st.plotly_chart(combo_capital_fig(relationships, roe_floor), use_container_width=True, config={'displayModeBar': False}, key='exec_capital_combo_v088')
    with c4:
        st.markdown(roe_heatmap(country, roe_floor), unsafe_allow_html=True)
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.plotly_chart(tenor_breakdown_fig(dsc), use_container_width=True, config={'displayModeBar': False}, key='exec_tenor_v088')
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class='insight-box' style='font-size:14.5px;line-height:1.65;padding:18px 20px;'>
      <b style='font-size:18px;'>Key Insights & RM Action Plan</b><br><br>
      • <b>Hong Kong</b> is the largest revenue and exposure contributor, anchoring both relationship depth and balance-sheet deployment.<br>
      • Portfolio RoE is above the <b>10%</b> floor in most relationships, but capital discipline should remain active for below-floor names.<br>
      • CASA ratio near <b>49%</b> indicates a meaningful low-cost deposit base and treasury relationship stickiness.<br>
      • LCR and NSFR indicators show funding resilience; this creates capacity for selective high-quality lending growth.<br>
      • Deposit maturity and tenor views should be used to identify rollover risk, repricing windows and treasury dialogue timing.<br>
      • Next best action: use Relationship 360 to convert country/product gaps into named RM pursuits across treasury, markets and IB wallet expansion.
    </div>
    """, unsafe_allow_html=True)


def render_revenue_exposure():
    st.markdown('<h1>Revenue & Exposure</h1>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Historical portfolio revenue, exposure and product penetration view.</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap='large')
    with c1:
        st.plotly_chart(bar_fig(product, 'Product_Type', 'Revenue', 'Revenue by Product Type', unit='M', height=540, width=0.20), use_container_width=True, key='rev_product_v088_final')
    with c2:
        st.plotly_chart(bar_fig(product, 'Product_Type', 'Exposure', 'Exposure by Product Type', unit='B', height=540, width=0.20), use_container_width=True, key='exp_product_v088_final')
    st.markdown('<h2>Top Relationship Table</h2>', unsafe_allow_html=True)
    cols = ['Relationship_Name', 'Country', 'Sector', 'Client_Tier', 'Total_Revenue', 'Lending_Drawn', 'Facility_Limit', 'Deposit_Balance', 'LTM_Group_RoE']
    st.dataframe(style_banking_table(relationships[cols].sort_values('Total_Revenue', ascending=False)), use_container_width=True, hide_index=True)


def render_capital_efficiency():
    st.markdown('<h1>Capital Efficiency</h1>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Exposure, capital usage, RWA and profitability discipline.</div>", unsafe_allow_html=True)
    avg_roe = float(relationships['LTM_Group_RoE'].mean())
    below = relationships[relationships['LTM_Group_RoE'] < roe_floor]
    largest_exposure = relationships.sort_values('Lending_Drawn', ascending=False).iloc[0]
    best_roe = relationships.sort_values('LTM_Group_RoE', ascending=False).iloc[0]
    strategic_callout('Capital strategy readout', [
        f"Portfolio average RoE is <b>{avg_roe*100:.1f}%</b> versus current floor of <b>{roe_floor*100:.0f}%</b>.",
        f"Largest exposure relationship is <b>{largest_exposure['Relationship_Name']}</b> with <b>{fmt_b(largest_exposure['Lending_Drawn'])}</b> drawn exposure — monitor capital usage and pricing discipline.",
        f"Highest-return relationship is <b>{best_roe['Relationship_Name']}</b> at <b>{best_roe['LTM_Group_RoE']*100:.1f}%</b>; use it as pricing and fee-attachment benchmark.",
        'RM action: below-floor relationships need one of three levers — reprice, reduce RWA intensity, or attach fee / deposit products to lift total relationship return.',
        'Management action: focus balance-sheet growth on relationships where exposure, deposits and fee wallet can work together rather than lending-only growth.'
    ], 'blue')
    st.plotly_chart(combo_capital_fig(relationships, roe_floor), use_container_width=True, key='capital_combo_full_v088')
    st.markdown('<h2>Watchlist: Below Profitability Floor</h2>', unsafe_allow_html=True)
    if below.empty:
        st.success('No below-floor relationships detected.')
    else:
        st.dataframe(style_banking_table(below[['Relationship_Name','Country','Sector','Lending_Drawn','RWA','LTM_Group_RoE','Deposit_Balance']].sort_values('Lending_Drawn', ascending=False)), use_container_width=True, hide_index=True)


def render_deposit_intelligence():
    st.markdown('<h1>Deposit Intelligence</h1>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Deposit franchise, operational balance and treasury opportunity view.</div>", unsafe_allow_html=True)
    casa = float(deposit.loc[deposit['Deposit_Type'].eq('CASA'), 'Deposit_Balance'].sum() / deposit['Deposit_Balance'].sum())
    td = float(deposit.loc[deposit['Deposit_Type'].eq('Time Deposit'), 'Deposit_Balance'].sum() / deposit['Deposit_Balance'].sum())
    largest_dep = country.sort_values('Deposit_Balance', ascending=False).iloc[0]
    maturity_top = maturity.sort_values('Deposit_Balance', ascending=False).iloc[0]
    strategic_callout('AI deposit strategy readout', [
        f"Total deposit franchise is <b>{fmt_b(relationships['Deposit_Balance'].sum())}</b>; <b>{largest_dep['Country']}</b> is the largest contributor at <b>{fmt_b(largest_dep['Deposit_Balance'])}</b>.",
        f"CASA ratio is <b>{casa*100:.0f}%</b>, giving the portfolio a meaningful low-cost and sticky funding base.",
        f"Time deposit share is approximately <b>{td*100:.0f}%</b>; this creates repricing and rollover conversations as rates change.",
        f"Largest maturity bucket is <b>{maturity_top['Maturity_Bucket']}</b> with <b>{fmt_b(maturity_top['Deposit_Balance'])}</b>; RM teams should monitor concentration and rollover dates.",
        'Treasury pitch angle: use operating balances, cash concentration, liquidity sweeping and FX flow visibility to convert deposit franchise into fee wallet.',
        'Management action: segment deposits by stability — operating balances for relationship stickiness, time deposits for repricing risk, and surplus liquidity for investment / markets dialogue.',
    ], 'green')
    c1, c2 = st.columns(2, gap='large')
    with c1:
        st.plotly_chart(bar_fig(country, 'Country', 'Deposit_Balance', 'Deposits by Country', unit='B', height=390, width=0.34), use_container_width=True, key='dep_country_full_v088')
    with c2:
        st.plotly_chart(donut_deposit(deposit), use_container_width=True, key='dep_type_donut_full_v088')
    c3, c4 = st.columns([1.2, .8], gap='large')
    with c3:
        st.plotly_chart(maturity_fig(maturity), use_container_width=True, key='dep_maturity_full_v088')
    with c4:
        st.markdown("<div class='small-card'><h3>Deposit Commentary</h3><br><b>Liquidity profile</b> tells bankers whether deposits are stable operating balances, price-sensitive term money, or short-term liquidity. CASA and operational balances indicate stickiness; maturity ladder identifies rollover risk, repricing windows and treasury dialogue opportunities.<br><br><b>Banker angle:</b> do not pitch deposits alone — connect liquidity to cash management, FX, rates hedging, investment sweep and working-capital needs.</div>", unsafe_allow_html=True)
    st.markdown('<h2>Deposit Relationship Table</h2>', unsafe_allow_html=True)
    table = relationships[['Relationship_Name', 'Country', 'Client_Tier', 'Deposit_Balance', 'Total_Revenue']].copy()
    table['Deposit_Type'] = np.random.default_rng(4).choice(['CASA', 'Operational', 'Time Deposit'], len(table))
    table['Liquidity_Class'] = table['Deposit_Type'].map({'CASA':'Liquid', 'Operational':'Operational', 'Time Deposit':'Term'})
    table['Deposit_Maturity_Date'] = [datetime(2024, 3, 31) + timedelta(days=int(x)) for x in np.random.default_rng(7).integers(15, 420, len(table))]
    table = table.rename(columns={'Total_Revenue': 'Deposit_Revenue_Proxy'})
    st.dataframe(style_banking_table(table.sort_values('Deposit_Balance', ascending=False)), use_container_width=True, hide_index=True)


def render_competitor_benchmarking():
    st.markdown('<h1>Competitor Benchmarking</h1>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Estimated wallet, current share and competitor lead bank by product family.</div>", unsafe_allow_html=True)
    comp = wallet.groupby('Lead_Competitor', as_index=False).agg(Estimated_Wallet=('Estimated_Wallet','sum'), Current_Revenue=('Current_Revenue','sum'), Wallet_Gap=('Wallet_Gap','sum'))
    comp['Penetration'] = comp['Current_Revenue'] / comp['Estimated_Wallet']
    comp = comp.sort_values('Estimated_Wallet', ascending=False).reset_index(drop=True)
    top_wallet = comp.iloc[0]; largest_gap = comp.sort_values('Wallet_Gap', ascending=False).iloc[0]; low_pen = comp.sort_values('Penetration', ascending=True).iloc[0]
    strategic_callout('Competitor strategy readout', [
        f"Rank is by <b>estimated wallet size</b>. <b>{top_wallet['Lead_Competitor']}</b> is the largest wallet pool at <b>${top_wallet['Estimated_Wallet']:.1f}M</b>.",
        f"Largest absolute wallet gap is with <b>{largest_gap['Lead_Competitor']}</b> at <b>${largest_gap['Wallet_Gap']:.1f}M</b>; this should become a named RM pursuit.",
        f"Lowest penetration pocket is <b>{low_pen['Lead_Competitor']}</b> at <b>{low_pen['Penetration']*100:.1f}%</b>; this is a good displacement target if the client need is clear.",
        'Banker use case: identify which competitor controls the wallet, then prepare a product-specific attack plan rather than generic cross-sell.',
        'Pitch angle: lead with client pain points — liquidity, refinancing, FX / rates exposure, working capital, or capital markets access — then map EC-AI wallet gap to the right product specialist.',
        'Management action: convert top gaps into pursuit owner, next meeting, product partner and expected revenue capture.',
    ], 'amber')
    st.plotly_chart(bar_fig(comp, 'Lead_Competitor', 'Estimated_Wallet', 'Estimated Wallet by Competitor Relationship', unit='M', height=420, width=0.30), use_container_width=True, key='competitor_wallet_v088_final')
    st.dataframe(competitor_table_format(comp), use_container_width=True, hide_index=True)


def render_product_penetration():
    st.markdown('<h1>Product Penetration</h1>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Revenue and exposure across product hierarchy: lending, transaction banking, markets and investment banking products.</div>", unsafe_allow_html=True)
    prod = product.copy()
    total_rev = float(prod['Revenue'].sum()); total_exp = float(prod['Exposure'].sum())
    prod['Revenue_Share'] = prod['Revenue'] / total_rev
    prod['Exposure_Share'] = prod['Exposure'] / total_exp
    prod['Revenue_per_Exposure'] = prod['Revenue'] / prod['Exposure'].replace(0, np.nan)
    best = prod.sort_values('Revenue_per_Exposure', ascending=False).iloc[0]
    largest = prod.sort_values('Revenue', ascending=False).iloc[0]
    strategic_callout('Product strategy readout', [
        f"<b>{largest['Product_Type']}</b> is the largest revenue contributor at <b>${largest['Revenue']:.1f}M</b>.",
        f"Best revenue intensity is <b>{best['Product_Type']}</b>; use this to identify fee / spread-efficient products to scale.",
        'RM action: protect balance-sheet products, but attach fee products such as Markets, DCM, Cash Management and Investment Banking to improve relationship RoE.',
    ], 'blue')
    c1, c2 = st.columns(2, gap='large')
    with c1:
        st.plotly_chart(bar_fig(prod, 'Product_Type', 'Revenue', 'Product Revenue', unit='M', height=540, width=0.20), use_container_width=True, key='prod_rev_v088_final')
    with c2:
        st.plotly_chart(bar_fig(prod, 'Product_Type', 'Exposure', 'Product Exposure', unit='B', height=540, width=0.20), use_container_width=True, key='prod_exp_v088_final')
    st.dataframe(style_banking_table(prod.sort_values('Revenue', ascending=False)), use_container_width=True, hide_index=True)


def render_deal_screening():
    st.markdown('<h1>Deal Screening (DSC)</h1>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Mini DSC dashboard: approved amount, Tx RoE, NIM, hurdle view and pricing quality.</div>", unsafe_allow_html=True)
    d = dsc.copy()
    d['Screen_Date'] = pd.to_datetime(d['Screen_Date'], errors='coerce')
    d['Tx_RoE_Bucket'] = pd.cut(d['Tx_RoE'], bins=[0,0.10,0.15,0.20,1], labels=['0–10%', '10–15%', '15–20%', '>20%'])
    d['NIM_Bucket'] = pd.cut(d['NIM_bps'], bins=[-1,30,60,100,10000], labels=['Below 30 bps', '30–60 bps', '60–100 bps', 'Over 100 bps'])
    d['Pass_RoE'] = d['Tx_RoE'] >= roe_floor; d['Pass_NIM'] = d['NIM_bps'] >= margin_floor
    d['Strategic_Decision'] = np.select([d['Pass_RoE'] & d['Pass_NIM'], d['Pass_RoE'] & ~d['Pass_NIM'], ~d['Pass_RoE'] & d['Pass_NIM']], ['Approve / Prioritise', 'Reprice', 'Reduce RWA / add fees'], default='Escalate / restructure')
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card('Deals', f'{len(d)}', 'screened sample'), unsafe_allow_html=True)
    c2.markdown(metric_card('Facility Limit', fmt_m(d['Facility_Limit_M'].sum()), 'screened amount'), unsafe_allow_html=True)
    c3.markdown(metric_card('Avg Tx RoE', f"{d['Tx_RoE'].mean()*100:.1f}%", 'transaction return'), unsafe_allow_html=True)
    c4.markdown(metric_card('Avg NIM', f"{d['NIM_bps'].mean():.0f} bps", 'price margin'), unsafe_allow_html=True)
    pass_rate = float((d['Pass_RoE'] & d['Pass_NIM']).mean())
    strategic_callout('Deal strategy readout', [
        f"<b>{pass_rate*100:.0f}%</b> of screened deals pass both RoE and NIM thresholds.",
        'Use DSC as a forward-looking control tower: not just approval volume, but quality of future balance-sheet deployment.',
        'Reprice low-NIM deals, restructure below-hurdle RoE deals, and attach fee/deposit wallet where lending consumes RWA.',
    ], 'amber')
    by_month = (d.dropna(subset=['Screen_Date']).assign(Month=lambda x: x['Screen_Date'].dt.to_period('M').dt.to_timestamp()).groupby('Month', as_index=False).agg(Facility_Limit_M=('Facility_Limit_M','sum'), Deals=('DS_ID','count'), Tx_RoE=('Tx_RoE','mean'), NIM_bps=('NIM_bps','mean')))
    by_month['Month_Label'] = by_month['Month'].dt.strftime('%b-%y')
    c5, c6 = st.columns(2, gap='large')
    with c5:
        st.plotly_chart(bar_fig(by_month, 'Month_Label', 'Facility_Limit_M', 'Approved Amount by Month', unit='M', height=390, width=0.30), use_container_width=True, key='dsc_month_v088_final')
    with c6:
        by_country = d.groupby('Country', as_index=False).agg(Expected_Draw_B=('Expected_Draw_B','sum'), Tx_RoE=('Tx_RoE','mean'), NIM_bps=('NIM_bps','mean'))
        st.plotly_chart(bar_fig(by_country, 'Country', 'Expected_Draw_B', 'Expected Draw by Country', unit='B', height=390, width=0.34), use_container_width=True, key='dsc_country_v088_final')
    c7, c8 = st.columns(2, gap='large')
    with c7:
        bucket = d.groupby('NIM_Bucket', observed=True, as_index=False).agg(Facility_Limit_M=('Facility_Limit_M','sum'), Deals=('DS_ID','count'))
        st.plotly_chart(bar_fig(bucket, 'NIM_Bucket', 'Facility_Limit_M', 'NIM Bucket by Facility Limit', unit='M', height=390, width=0.34), use_container_width=True, key='dsc_nim_bucket_v088_final')
    with c8:
        decision = d.groupby('Strategic_Decision', as_index=False).agg(Facility_Limit_M=('Facility_Limit_M','sum'), Deals=('DS_ID','count'))
        st.plotly_chart(bar_fig(decision, 'Strategic_Decision', 'Facility_Limit_M', 'Strategic Decision by Facility Limit', unit='M', height=390, width=0.30), use_container_width=True, key='dsc_decision_v088_final')
    st.markdown('<h2>Deal List</h2>', unsafe_allow_html=True)
    show_cols = ['DS_ID','Relationship_Name','Country','Product_Type','Facility_Limit_M','Expected_Utilization','Expected_Draw_B','Spread_bps','LP_bps','BAC_bps','EL_bps','NIM_bps','Tx_RoE','Strategic_Decision','Status']
    show_cols = [c for c in show_cols if c in d.columns]
    st.dataframe(style_banking_table(d.sort_values('Facility_Limit_M', ascending=False)[show_cols]), use_container_width=True, hide_index=True)


def render_portfolio_data():
    st.markdown('<h1>Portfolio Data</h1>', unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Historical actual facilities, drawdown, revenue, deposits and RWA.</div>", unsafe_allow_html=True)
    excel_bytes = make_excel_download(data)
    st.download_button('Download sample banking data (Excel)', data=excel_bytes, file_name='ecai_banking_sample_data_v088.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='download_excel_v088_final')
    view = st.selectbox('Table', list(data.keys()), key='portfolio_table_select_v088_final')
    st.dataframe(style_banking_table(data[view]), use_container_width=True, hide_index=True)

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

st.markdown("<div class='footer'>EC-AI Banking Intelligence Platform v0.8.8.4 · Demo data only · Do not use confidential bank data in public environments.</div>", unsafe_allow_html=True)
