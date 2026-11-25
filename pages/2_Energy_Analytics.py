"""
Household Energy Analytics Dashboard.
Personalized energy analytics reoriented exclusively around the selected household's
configured appliances, consumption calculations, and BESCOM LT-1 tariff breakdown.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import streamlit as st
from config.settings import DB_PATH
from db.schema import init_db
from db.seeds import seed_database
from modules.estimator.calculator import calculate_bescom_bill, calculate_household_summary
from modules.estimator.charts import (
    plot_appliance_kwh_bar,
    plot_appliance_kwh_donut,
    plot_cost_breakdown_bar,
)
from modules.estimator.insights import generate_household_insights
from modules.estimator.repository import (
    get_active_tariff_schedule,
    get_all_households,
    get_household,
    get_household_appliances,
)

st.set_page_config(
    page_title="Energy Analytics — Smart Energy Usage Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database schema and seeds
init_db(DB_PATH)
seed_database(DB_PATH)

# ==============================================================================
# CSS STYLING
# ==============================================================================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #0f172a;
        }
        .stApp {
            background-color: #fafdfb;
        }
        [data-testid="stSidebarNav"] {
            display: none;
        }
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #edf5f0;
        }
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.5rem 0.25rem 1.25rem 0.25rem;
            border-bottom: 1px solid #f1f5f3;
            margin-bottom: 1rem;
        }
        .sidebar-brand-title {
            font-size: 1.1rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.2;
        }
        .page-header {
            margin-bottom: 1.5rem;
        }
        .page-title {
            font-size: 1.85rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 0.25rem;
        }
        .page-subtitle {
            font-size: 0.95rem;
            color: #475569;
        }
        .kpi-card-box {
            background: #ffffff;
            border: 1px solid #e2ece5;
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .kpi-title {
            font-size: 0.8rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .kpi-val {
            font-size: 1.7rem;
            font-weight: 800;
            color: #0f172a;
            margin-top: 0.25rem;
            line-height: 1.2;
        }
        .kpi-sub {
            font-size: 0.8rem;
            color: #059669;
            font-weight: 600;
            margin-top: 0.35rem;
        }
        .chart-box-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }
        .insight-card {
            background: #f0faf4;
            border: 1px solid #cbebd6;
            border-radius: 12px;
            padding: 1rem 1.15rem;
            margin-bottom: 0.85rem;
        }
        .insight-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #065f46;
            margin-bottom: 0.25rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .insight-text {
            font-size: 0.86rem;
            color: #1e293b;
            line-height: 1.45;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# SIDEBAR NAVIGATION
# ==============================================================================
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/>
                <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>
            </svg>
            <div class="sidebar-brand-title">Smart Energy<br>Usage Monitor</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_My_Household.py", label="My Household", icon="🏠")
    st.page_link("pages/2_Energy_Analytics.py", label="Energy Analytics", icon="📊")
    st.page_link("pages/3_Historical_Dataset_Explorer.py", label="Historical Dataset Explorer", icon="📈")

# ==============================================================================
# ACTIVE HOUSEHOLD CONTEXT
# ==============================================================================
households = get_all_households(DB_PATH)
if not households:
    st.info("No households found in the database. Please create a household profile first.")
    st.page_link("pages/1_My_Household.py", label="Go to My Household →", icon="🏠")
    st.stop()

hh_options = {h["household_id"]: f"{h['name']} ({h['city']})" for h in households}
current_hh_id = st.session_state.get("active_household_id", households[0]["household_id"])
if current_hh_id not in hh_options:
    current_hh_id = list(hh_options.keys())[0]

# Household Selector Header Bar
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Personal Energy Analytics Dashboard</div>'
        '<div class="page-subtitle">Comprehensive appliance-wise energy distribution, expenditure shares, and savings insights for your household.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with col_h2:
    selected_hh_id = st.selectbox(
        "Household",
        options=list(hh_options.keys()),
        format_func=lambda x: hh_options[x],
        index=list(hh_options.keys()).index(current_hh_id),
    )
    if selected_hh_id != current_hh_id:
        st.session_state["active_household_id"] = selected_hh_id
        st.rerun()

active_hh = get_household(selected_hh_id, DB_PATH)
user_appliances = get_household_appliances(selected_hh_id, DB_PATH)

# ==============================================================================
# EMPTY STATE HANDLING
# ==============================================================================
if not user_appliances:
    st.warning("⚠️ Your household dashboard is not ready yet. Add your appliances in My Household to see your energy consumption and cost breakdown.")
    st.page_link("pages/1_My_Household.py", label="Configure Appliances in My Household →", icon="🏠")
    st.stop()

# ==============================================================================
# CALCULATE HOUSEHOLD METRICS
# ==============================================================================
tariff = get_active_tariff_schedule(active_hh["provider_id"], DB_PATH)
energy_rate = (tariff["base_energy_rate_paise"] / 100.0) if tariff else 5.80

summary = calculate_household_summary(user_appliances, energy_rate_per_kwh=energy_rate)
bill = calculate_bescom_bill(
    total_monthly_kwh=summary["total_monthly_kwh"],
    sanctioned_load_kw=float(active_hh["sanctioned_load_kw"]),
    base_rate_paise=int(tariff["base_energy_rate_paise"]) if tariff else 580,
)

# ==============================================================================
# A. TOP-LEVEL KPI CARDS
# ==============================================================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4, gap="medium")

with kpi1:
    st.markdown(
        f'<div class="kpi-card-box">'
        f'<div class="kpi-title">Monthly Consumption</div>'
        f'<div class="kpi-val">{summary["total_monthly_kwh"]:,.1f} <span style="font-size: 1rem; font-weight: 500;">kWh</span></div>'
        f'<div class="kpi-sub">{summary["total_daily_kwh"]:,.1f} kWh / day avg</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with kpi2:
    st.markdown(
        f'<div class="kpi-card-box">'
        f'<div class="kpi-title">Estimated Monthly Cost</div>'
        f'<div class="kpi-val">₹{bill["total_bill_inr"]:,.0f}</div>'
        f'<div class="kpi-sub">₹{bill["energy_charge_inr"]:,.0f} variable energy</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with kpi3:
    st.markdown(
        f'<div class="kpi-card-box">'
        f'<div class="kpi-title">Configured Appliances</div>'
        f'<div class="kpi-val">{summary["total_appliance_units"]} <span style="font-size: 1rem; font-weight: 500;">units</span></div>'
        f'<div class="kpi-sub">{summary["appliance_count"]} unique device types</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with kpi4:
    top = summary["highest_consumer"]
    top_label = (top.get("label") or top.get("spec_name") or "None") if top else "None"
    top_val = f"{top['monthly_kwh']:,.1f} kWh" if top else "0 kWh"
    top_pct = f"({top.get('share_percent', 0)}% share)" if top else ""
    st.markdown(
        f'<div class="kpi-card-box">'
        f'<div class="kpi-title">Highest Consumer</div>'
        f'<div class="kpi-val" style="font-size: 1.25rem; margin-top: 0.4rem;">{top_label}</div>'
        f'<div class="kpi-sub">{top_val} {top_pct}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# B. CHARTS ROW 1: APPLIANCE ENERGY CONSUMPTION & COMPARISON
# ==============================================================================
st.markdown("### 📊 Appliance Energy Consumption")

col_c1, col_c2 = st.columns(2, gap="large")

with col_c1:
    st.markdown('<div class="chart-box-title">⚡ Energy Consumption Share (%)</div>', unsafe_allow_html=True)
    fig_kwh_donut = plot_appliance_kwh_donut(summary["appliances"])
    st.pyplot(fig_kwh_donut)
    plt.close(fig_kwh_donut)

with col_c2:
    st.markdown('<div class="chart-box-title">📈 Monthly Consumption Comparison (kWh)</div>', unsafe_allow_html=True)
    fig_kwh_bar = plot_appliance_kwh_bar(summary["appliances"])
    st.pyplot(fig_kwh_bar)
    plt.close(fig_kwh_bar)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# C. CHARTS ROW 2: MONTHLY BILL COMPONENT BREAKDOWN & ENERGY INSIGHTS
# ==============================================================================
col_bill_chart, col_insights_panel = st.columns([1.1, 1], gap="large")

with col_bill_chart:
    st.markdown("### 🧾 Monthly Bill Component Breakdown")
    fig_bill_bar = plot_cost_breakdown_bar(bill)
    st.pyplot(fig_bill_bar)
    plt.close(fig_bill_bar)

    st.markdown('<div style="font-weight: 700; color: #0f172a; margin-top: 1.25rem; margin-bottom: 0.5rem; font-size: 0.95rem;">Appliance-Wise Variable Cost Distribution</div>', unsafe_allow_html=True)
    
    table_rows = []
    for app in summary["appliances"]:
        app_name = app.get("label") or app.get("spec_name") or "Appliance"
        qty = app.get("quantity", 1)
        qty_str = f" ({qty}x)" if qty > 1 else ""
        monthly_kwh = f"{app.get('monthly_kwh', 0.0):.1f} kWh"
        var_cost = f"₹{app.get('variable_cost', 0.0):,.1f}"
        share = f"{app.get('share_percent', 0.0):.1f}%"
        table_rows.append(
            f'<tr style="border-bottom: 1px solid #f1f5f9;">'
            f'<td style="padding: 0.55rem 0.75rem; font-weight: 600; color: #1e293b; text-align: left;">{app_name}{qty_str}</td>'
            f'<td style="padding: 0.55rem 0.75rem; text-align: right; color: #475569; white-space: nowrap;">{monthly_kwh}</td>'
            f'<td style="padding: 0.55rem 0.75rem; text-align: right; font-weight: 700; color: #059669; white-space: nowrap;">{var_cost}</td>'
            f'<td style="padding: 0.55rem 0.75rem; text-align: right; color: #64748b; white-space: nowrap;">{share}</td>'
            f'</tr>'
        )

    table_html = (
        '<div style="background: #ffffff; border: 1px solid #e2ece5; border-radius: 10px; overflow: hidden; margin-top: 0.4rem; width: 100%; box-sizing: border-box;">'
        '<table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; line-height: 1.4;">'
        '<thead>'
        '<tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0; color: #475569; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em;">'
        '<th style="padding: 0.55rem 0.75rem; text-align: left;">Appliance</th>'
        '<th style="padding: 0.55rem 0.75rem; text-align: right; white-space: nowrap;">Energy</th>'
        '<th style="padding: 0.55rem 0.75rem; text-align: right; white-space: nowrap;">Variable Cost</th>'
        '<th style="padding: 0.55rem 0.75rem; text-align: right; white-space: nowrap;">Share</th>'
        '</tr>'
        '</thead>'
        '<tbody>'
        + "".join(table_rows)
        + '</tbody>'
        '</table>'
        '</div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)
    st.caption("ℹ️ Variable energy charge is ₹5.80/kWh. Fixed meter charges (₹150/kW) and 9% statutory duty apply at the household level.")

with col_insights_panel:
    st.markdown("### 💡 Actionable Energy-Saving Insights")
    insights = generate_household_insights(summary["appliances"], energy_rate_inr=energy_rate)

    if insights:
        for ins in insights:
            st.markdown(
                f'<div class="insight-card">'
                f'<div class="insight-title">{ins["icon"]} {ins["title"]}</div>'
                f'<div class="insight-text">{ins["message"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Configure your operating hours in My Household to generate customized energy savings insights.")
