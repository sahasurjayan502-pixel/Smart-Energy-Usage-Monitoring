"""
My Household — Interactive Household Appliance & Energy Estimator.
Allows users to configure household profiles, select appliances from a searchable catalogue,
adjust rated wattage, daily operating hours, and calculate energy consumption and electricity bills.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
from config.settings import DB_PATH
from db.schema import init_db
from db.seeds import seed_database
from modules.estimator.calculator import (
    calculate_appliance_energy,
    calculate_bescom_bill,
    calculate_household_summary,
)
from modules.estimator.repository import (
    add_household_appliance,
    create_household,
    delete_household_appliance,
    get_active_tariff_schedule,
    get_all_households,
    get_appliance_specs,
    get_household,
    get_household_appliances,
    get_utility_providers,
    save_bill_estimate,
    update_household,
    update_household_appliance,
)

st.set_page_config(
    page_title="My Household — Smart Energy Usage Monitor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database schema and seeds idempotently
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
        .card-box {
            background: #ffffff;
            border: 1px solid #e2ece5;
            border-radius: 14px;
            padding: 1.25rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }
        .section-header {
            font-size: 1.1rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .kpi-pill {
            background: #ffffff;
            border: 1px solid #e2ece5;
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
        }
        .kpi-pill-val {
            font-size: 1.5rem;
            font-weight: 800;
            color: #059669;
        }
        .kpi-pill-lbl {
            font-size: 0.78rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            margin-top: 0.2rem;
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
# 1. HOUSEHOLD PROFILE SELECTION & MANAGEMENT
# ==============================================================================
households = get_all_households(DB_PATH)
providers = get_utility_providers(DB_PATH)

# Automatically create a default household if database is empty
if not households:
    provider_id = providers[0]["provider_id"] if providers else 1
    default_id = create_household("My Bengaluru Flat", "Bengaluru", provider_id, 3.0, DB_PATH)
    households = get_all_households(DB_PATH)

# Active household in session state
if "active_household_id" not in st.session_state:
    st.session_state["active_household_id"] = households[0]["household_id"]

hh_options = {h["household_id"]: f"{h['name']} ({h['city']})" for h in households}
current_hh_id = st.session_state["active_household_id"]
if current_hh_id not in hh_options:
    current_hh_id = list(hh_options.keys())[0]
    st.session_state["active_household_id"] = current_hh_id

# Header
st.markdown(
    """
    <div class="page-header">
        <div class="page-title">My Household & Appliance Configurator</div>
        <div class="page-subtitle">
            Configure your household appliances, set daily usage hours, and calculate your estimated electricity bill.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Profile Switcher / Editor Bar
with st.container():
    col_sel, col_new, col_edit = st.columns([2.5, 1, 1], gap="small")
    with col_sel:
        selected_id = st.selectbox(
            "Active Household Profile",
            options=list(hh_options.keys()),
            format_func=lambda x: hh_options[x],
            index=list(hh_options.keys()).index(current_hh_id),
            label_visibility="collapsed",
        )
        if selected_id != st.session_state["active_household_id"]:
            st.session_state["active_household_id"] = selected_id
            st.rerun()

    with col_new:
        show_create = st.button("➕ New Household", use_container_width=True)

    with col_edit:
        show_edit_profile = st.button("✏️ Edit Profile", use_container_width=True)

# Create New Household Form
if show_create:
    with st.expander("Create New Household Profile", expanded=True):
        with st.form("create_household_form"):
            new_name = st.text_input("Household Name", value="Home")
            new_city = st.text_input("City", value="Bengaluru")
            prov_opts = {p["provider_id"]: f"{p['code']} — {p['name']}" for p in providers}
            new_prov_id = st.selectbox("Electricity Provider", options=list(prov_opts.keys()), format_func=lambda x: prov_opts[x])
            new_load = st.number_input("Sanctioned Load (kW)", min_value=0.5, max_value=25.0, value=3.0, step=0.5)

            if st.form_submit_button("Save Household"):
                if new_name.strip():
                    created_id = create_household(new_name, new_city, new_prov_id, new_load, DB_PATH)
                    st.session_state["active_household_id"] = created_id
                    st.success("New household created successfully!")
                    st.rerun()

# Edit Active Household Form
active_hh = get_household(st.session_state["active_household_id"], DB_PATH)
if show_edit_profile and active_hh:
    with st.expander("Edit Household Profile", expanded=True):
        with st.form("edit_household_form"):
            edit_name = st.text_input("Household Name", value=active_hh["name"])
            edit_city = st.text_input("City", value=active_hh["city"])
            prov_opts = {p["provider_id"]: f"{p['code']} — {p['name']}" for p in providers}
            current_prov_idx = list(prov_opts.keys()).index(active_hh["provider_id"]) if active_hh["provider_id"] in prov_opts else 0
            edit_prov_id = st.selectbox("Electricity Provider", options=list(prov_opts.keys()), format_func=lambda x: prov_opts[x], index=current_prov_idx)
            edit_load = st.number_input("Sanctioned Load (kW)", min_value=0.5, max_value=25.0, value=float(active_hh["sanctioned_load_kw"]), step=0.5)

            if st.form_submit_button("Update Profile"):
                update_household(active_hh["household_id"], edit_name, edit_city, edit_prov_id, edit_load, DB_PATH)
                st.success("Profile updated!")
                st.rerun()

# Profile summary banner
active_hh = get_household(st.session_state["active_household_id"], DB_PATH)
if not active_hh:
    st.stop()

st.caption(
    f"📍 **{active_hh['name']}** • City: {active_hh['city']} • Provider: {active_hh.get('provider_name', 'BESCOM')} • "
    f"Sanctioned Load: **{active_hh['sanctioned_load_kw']} kW**"
)

st.markdown("---")

# ==============================================================================
# 2. SEARCHABLE APPLIANCE CATALOGUE & ADD FORM
# ==============================================================================
specs = get_appliance_specs(DB_PATH)
spec_options = {s["spec_id"]: f"{s['category_icon']} {s['name']} ({s['category_name']})" for s in specs}

with st.expander("➕ Add an Appliance to Household", expanded=False):
    selected_spec_id = st.selectbox(
        "Choose Appliance from Catalogue",
        options=list(spec_options.keys()),
        format_func=lambda x: spec_options[x],
    )
    spec_item = next((s for s in specs if s["spec_id"] == selected_spec_id), specs[0])
    method = spec_item["calculation_method"]

    with st.form("add_appliance_form"):
        col_a1, col_a2, col_a3 = st.columns(3)

        with col_a1:
            app_label = st.text_input("Custom Label / Room (Optional)", placeholder=f"e.g. Living Room {spec_item['name']}")
            app_qty = st.number_input("Quantity", min_value=1, max_value=50, value=1, step=1)

        with col_a2:
            if method == "annual_kwh":
                st.info("⭐ BEE Star Rated Appliance (Annual Energy Rating)")
                def_annual = float(spec_item["annual_kwh"] or 220.0)
                app_annual_kwh = st.number_input("Annual Consumption (kWh/yr)", min_value=10.0, max_value=2000.0, value=def_annual, step=10.0)
                app_watt = None
                app_hours = 24.0
                app_cycle_kwh = None
            elif method == "kwh_per_cycle":
                st.info("🔄 Batch Cyclic Appliance")
                def_cycle = float(spec_item["kwh_per_cycle"] or 0.65)
                app_cycle_kwh = st.number_input("Energy per Cycle (kWh)", min_value=0.1, max_value=10.0, value=def_cycle, step=0.05)
                app_annual_kwh = None
                app_watt = None
                app_hours = None
            else:
                def_watt = int(spec_item["rated_watt"] or 60)
                app_watt = st.number_input("Rated Wattage (W)", min_value=1, max_value=10000, value=def_watt, step=5)
                def_hrs = float(spec_item["typical_usage_hrs_day"] or 4.0)
                app_hours = st.slider("Daily Operating Hours (hrs/day)", min_value=0.5, max_value=24.0, value=min(24.0, def_hrs), step=0.5)
                app_annual_kwh = None
                app_cycle_kwh = None

        with col_a3:
            app_days = st.number_input("Operating Days per Month", min_value=1, max_value=31, value=30, step=1)
            cycles_mo = st.number_input("Cycles per Month", min_value=1, max_value=90, value=30, step=1) if method == "kwh_per_cycle" else None

        if st.form_submit_button("Add to Household", type="primary"):
            add_household_appliance(
                household_id=active_hh["household_id"],
                spec_id=selected_spec_id,
                calculation_method=method,
                quantity=app_qty,
                daily_hours=app_hours,
                days_per_month=app_days,
                custom_watt=app_watt,
                custom_annual_kwh=app_annual_kwh,
                custom_kwh_per_cycle=app_cycle_kwh,
                cycles_per_month=cycles_mo,
                label=app_label if app_label.strip() else None,
                db_path=DB_PATH,
            )
            st.success(f"Added {spec_item['name']}!")
            st.rerun()

# ==============================================================================
# 3. CONFIGURED APPLIANCES INVENTORY & EDITING
# ==============================================================================
user_appliances = get_household_appliances(active_hh["household_id"], DB_PATH)

st.markdown("### Configured Household Appliances")

if not user_appliances:
    st.info(
        "💡 No appliances configured for this household yet. Click **'➕ Add an Appliance to Household'** above "
        "to select fans, refrigerators, ACs, lights, and other devices."
    )
else:
    # Calculate energy summary
    tariff = get_active_tariff_schedule(active_hh["provider_id"], DB_PATH)
    energy_rate = (tariff["base_energy_rate_paise"] / 100.0) if tariff else 5.80
    summary = calculate_household_summary(user_appliances, energy_rate_per_kwh=energy_rate)

    # Render interactive cards or editing rows
    for app in summary["appliances"]:
        app_id = app["appliance_id"]
        app_name = app.get("label") or app["spec_name"]
        cat_icon = app.get("category_icon", "⚡")
        method = app["calculation_method"]
        monthly_kwh = app["monthly_kwh"]
        var_cost = app["variable_cost"]

        with st.container(border=True):
            col_icon, col_spec, col_usage, col_metrics, col_del = st.columns([0.8, 2.5, 3.2, 2.2, 0.8], gap="medium")

            with col_icon:
                st.markdown(f"<div style='font-size: 2rem; text-align: center; padding-top: 0.3rem;'>{cat_icon}</div>", unsafe_allow_html=True)

            with col_spec:
                st.markdown(f"**{app_name}**")
                if method == "annual_kwh":
                    st.caption(f"⭐ Rating: {app.get('custom_annual_kwh') or app.get('default_annual_kwh')} kWh/yr")
                elif method == "kwh_per_cycle":
                    st.caption(f"🔄 Rating: {app.get('custom_kwh_per_cycle') or 0.65} kWh/cycle")
                else:
                    st.caption(f"⚡ Power: {app.get('custom_watt') or app.get('default_watt')} W")

            with col_usage:
                # Direct inline editing for quantity and hours
                c_u1, c_u2 = st.columns(2)
                with c_u1:
                    new_qty = st.number_input("Qty", min_value=1, max_value=50, value=int(app["quantity"]), key=f"qty_{app_id}")
                with c_u2:
                    if method == "annual_kwh":
                        st.caption("24 h/day (Cyclic BEE)")
                        new_hrs = 24.0
                    elif method == "kwh_per_cycle":
                        st.caption(f"{app.get('days_per_month', 30)} cycles/mo")
                        new_hrs = None
                    else:
                        new_hrs = st.number_input("Hours/day", min_value=0.1, max_value=24.0, value=float(app.get("daily_hours") or 4.0), step=0.5, key=f"hrs_{app_id}")

                # If values changed, save automatically
                if new_qty != app["quantity"] or (new_hrs is not None and new_hrs != app.get("daily_hours")):
                    update_household_appliance(app_id, new_qty, new_hrs, app.get("days_per_month", 30), app.get("custom_watt"), app.get("custom_annual_kwh"), app.get("label"), DB_PATH)
                    st.rerun()

            with col_metrics:
                st.markdown(f"**{monthly_kwh:,.1f} kWh / mo**")
                st.caption(f"₹{var_cost:,.2f} var cost ({app.get('share_percent', 0.0)}%)")

            with col_del:
                if st.button("🗑️", key=f"del_{app_id}", help=f"Remove {app_name}"):
                    delete_household_appliance(app_id, DB_PATH)
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ==============================================================================
    # 4. HOUSEHOLD CONSUMPTION & BILL SUMMARY
    # ==============================================================================
    st.markdown("### Estimated Energy Consumption & Electricity Bill")

    bill = calculate_bescom_bill(
        total_monthly_kwh=summary["total_monthly_kwh"],
        sanctioned_load_kw=float(active_hh["sanctioned_load_kw"]),
        base_rate_paise=int(tariff["base_energy_rate_paise"]) if tariff else 580,
    )

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        st.markdown(
            f"""
            <div class="kpi-pill">
                <div class="kpi-pill-val">{summary['total_appliance_units']}</div>
                <div class="kpi-pill-lbl">Configured Devices</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="kpi-pill">
                <div class="kpi-pill-val">{summary['total_daily_kwh']:,.1f}</div>
                <div class="kpi-pill-lbl">Est. Daily kWh</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="kpi-pill">
                <div class="kpi-pill-val">{summary['total_monthly_kwh']:,.1f}</div>
                <div class="kpi-pill-lbl">Est. Monthly kWh</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="kpi-pill">
                <div class="kpi-pill-val">₹{bill['total_bill_inr']:,.0f}</div>
                <div class="kpi-pill-lbl">Est. Monthly Bill</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Tariff Breakdown Details
    with st.expander("🧾 View BESCOM LT-1 Bill Calculation Breakdown", expanded=True):
        st.markdown(
            f"""
            - **Variable Energy Charges:** `{bill['total_kwh']:,.1f} kWh` × `₹{bill['energy_rate_inr']:.2f}/kWh` = **₹{bill['energy_charge_inr']:,.2f}**
            - **Fixed Demand Charges:** `{bill['sanctioned_load_kw']} kW` × `₹{bill['fixed_charge_rate_inr']:.2f}/kW/month` = **₹{bill['fixed_charge_inr']:,.2f}**
            - **Karnataka Electricity Duty (9.0% on energy):** **₹{bill['duty_inr']:,.2f}**
            - **Total Estimated Monthly Bill:** **₹{bill['total_bill_inr']:,.2f}**
            """
        )
        st.caption("Note: Indicative estimate for Domestic LT-1. Actual utility bills may include municipal cess or meter rent.")

    # Save & Calculate Action
    col_save, col_nav = st.columns([2, 2], gap="medium")
    with col_save:
        if st.button("💾 Save & Snapshot Bill Estimate", type="primary", use_container_width=True):
            sched_id = tariff["schedule_id"] if tariff else 1
            est_id = save_bill_estimate(
                household_id=active_hh["household_id"],
                schedule_id=sched_id,
                billing_month="2026-11",
                bill_calc=bill,
                appliances_list=summary["appliances"],
                sanctioned_load_kw=float(active_hh["sanctioned_load_kw"]),
                db_path=DB_PATH,
            )
            st.success(f"Snapshot #{est_id} saved successfully in SQLite database!")

    with col_nav:
        st.page_link(
            "pages/2_Energy_Analytics.py",
            label="View Personal Energy Analytics Dashboard →",
            icon="📊",
            help="Open appliance charts and personal energy analytics",
        )
