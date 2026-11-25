"""
Historical Dataset Explorer.
Dedicated exploratory data analysis tool for the Kaggle 45,345-record Indian electricity dataset.
Strictly separated from personal household energy monitoring.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import streamlit as st
from config.settings import CSV_PATH, DB_PATH
from db.schema import init_db
from modules.analytics.charts import (
    plot_avg_bill_by_city,
    plot_correlation_heatmap,
    plot_hours_vs_bill,
    plot_monthly_bill_trends,
    plot_tariff_distribution,
)
from modules.analytics.loader import import_csv_to_analytics, is_already_imported
from modules.analytics.queries import get_city_summary, get_filter_options, load_filtered_readings

st.set_page_config(
    page_title="Historical Dataset Explorer — Smart Energy Usage Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure database and dataset are loaded
init_db(DB_PATH)
is_imported, meta = is_already_imported(CSV_PATH, DB_PATH)
if not is_imported:
    with st.spinner("Initializing database and ingesting dataset..."):
        import_csv_to_analytics(CSV_PATH, DB_PATH)

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
            margin-bottom: 1.25rem;
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
        .filter-card {
            background: #ffffff;
            border: 1px solid #e2ece5;
            border-radius: 14px;
            padding: 1.1rem 1.3rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }
        .kpi-box {
            background: #ffffff;
            border: 1px solid #e2ece5;
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }
        .kpi-title {
            font-size: 0.78rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
        }
        .kpi-val {
            font-size: 1.65rem;
            font-weight: 800;
            color: #0f172a;
            margin-top: 0.2rem;
            line-height: 1.2;
        }
        .kpi-sub {
            font-size: 0.78rem;
            color: #059669;
            font-weight: 600;
            margin-top: 0.3rem;
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
# HEADER & DATASET SEPARATION NOTICE
# ==============================================================================
st.markdown(
    """
    <div class="page-header">
        <div class="page-title">Historical Dataset Explorer</div>
        <div class="page-subtitle">
            Macro-level statistical exploration of 45,345 records across 16 Indian cities.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("ℹ️ Dataset Scientific Disclosures & Limitations (Read First)", expanded=False):
    st.markdown(
        """
        - **Synthetic Mathematical Identity:** In **100% of the 45,345 rows**, `ElectricityBill` is mathematically identical to `MonthlyHours × TariffRate`.
        - **Appliance Columns:** Columns (`Fan`, `Refrigerator`, etc.) are unverified counts and bear zero correlation with billing. They are **never** used in the Household Estimator.
        - **Zero Data Leakage:** This historical exploration dataset is strictly quarantined in `analytics_reading` and is completely decoupled from your personal household records.
        """
    )

# ==============================================================================
# FILTERS
# ==============================================================================
filter_opts = get_filter_options(DB_PATH)

col_f1, col_f2, col_f3 = st.columns([1.2, 1, 1], gap="medium")

with col_f1:
    all_cities = filter_opts["cities"]
    select_all_cities = st.checkbox("All Cities", value=True)
    if select_all_cities:
        selected_cities = st.multiselect("Select Cities", options=all_cities, default=all_cities, label_visibility="collapsed")
    else:
        selected_cities = st.multiselect("Select Cities", options=all_cities, default=all_cities[:5], label_visibility="collapsed")

with col_f2:
    all_months = filter_opts["months"]
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }
    selected_months = st.multiselect(
        "Months",
        options=all_months,
        default=all_months,
        format_func=lambda m: month_names.get(m, f"Month {m}"),
        placeholder="Filter Months",
        label_visibility="collapsed",
    )

with col_f3:
    all_companies = filter_opts["companies"]
    selected_companies = st.multiselect(
        "Companies",
        options=all_companies,
        default=[],
        placeholder="All Listed Companies",
        label_visibility="collapsed",
    )

# Query filtered readings from database
df_filtered = load_filtered_readings(
    cities=selected_cities if selected_cities else None,
    months=selected_months if selected_months else None,
    companies=selected_companies if selected_companies else None,
    db_path=DB_PATH,
)

# ==============================================================================
# KEY DATASET METRICS
# ==============================================================================
if df_filtered.empty:
    st.warning("⚠️ No records match the selected filter criteria. Please broaden your selection.")
else:
    avg_bill = df_filtered["electricity_bill"].mean()
    avg_hrs = df_filtered["monthly_hours"].mean()
    avg_tr = df_filtered["tariff_rate"].mean()
    num_cities = df_filtered["city"].nunique()

    kpi1, kpi2, kpi3 = st.columns(3, gap="medium")

    with kpi1:
        st.markdown(
            f"""
            <div class="kpi-box">
                <div class="kpi-title">Filtered Records</div>
                <div class="kpi-val">{len(df_filtered):,}</div>
                <div class="kpi-sub">Across {num_cities} active cities</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi2:
        st.markdown(
            f"""
            <div class="kpi-box">
                <div class="kpi-title">Average Electricity Bill</div>
                <div class="kpi-val">₹{avg_bill:,.0f}</div>
                <div class="kpi-sub">Average unit rate: ₹{avg_tr:.2f} / kWh</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi3:
        st.markdown(
            f"""
            <div class="kpi-box">
                <div class="kpi-title">Average Monthly Hours</div>
                <div class="kpi-val">{avg_hrs:,.1f} h</div>
                <div class="kpi-sub">Operating runtime per month</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ==============================================================================
    # CHARTS
    # ==============================================================================
    col_c1, col_c2 = st.columns(2, gap="large")

    with col_c1:
        fig_city = plot_avg_bill_by_city(df_filtered)
        st.pyplot(fig_city)
        plt.close(fig_city)

    with col_c2:
        fig_trend = plot_monthly_bill_trends(df_filtered)
        st.pyplot(fig_trend)
        plt.close(fig_trend)

    st.markdown("<br>", unsafe_allow_html=True)

    col_h1, col_h2 = st.columns([2, 1], gap="large")
    with col_h1:
        fig_hours = plot_hours_vs_bill(df_filtered)
        st.pyplot(fig_hours)
        plt.close(fig_hours)
    with col_h2:
        st.markdown(
            """
            <div style="background: #ffffff; border: 1px solid #e2ece5; border-radius: 14px; padding: 1.4rem; height: 100%; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-weight: 700; color: #0f172a; font-size: 1.05rem; margin-bottom: 0.6rem;">
                    📐 Relationship Breakdown
                </div>
                <div style="color: #475569; font-size: 0.9rem; line-height: 1.55;">
                    The scatter plot illustrates the exact linear identity of the benchmark dataset:<br><br>
                    <code style="background: #eaf8ef; color: #047857; padding: 4px 8px; border-radius: 6px; font-weight: 600;">
                        Bill = MonthlyHours × TariffRate
                    </code><br><br>
                    Each distinct band reflects a discrete tariff rate between ₹7.40 and ₹9.30/kWh.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("📊 Additional Visualizations (Tariff Frequencies & Correlations)"):
        col_more1, col_more2 = st.columns(2, gap="medium")
        with col_more1:
            fig_tariff = plot_tariff_distribution(df_filtered)
            st.pyplot(fig_tariff)
            plt.close(fig_tariff)
        with col_more2:
            fig_corr = plot_correlation_heatmap(df_filtered)
            st.pyplot(fig_corr)
            plt.close(fig_corr)

    # ==============================================================================
    # DATA TABLE
    # ==============================================================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Historical Data Explorer")

    tab_data, tab_sum = st.tabs(["Sample Records (First 100)", "City-wise Aggregate Summary"])

    with tab_data:
        st.dataframe(df_filtered.head(100), width="stretch")

    with tab_sum:
        city_summary = get_city_summary(df_filtered)
        st.dataframe(
            city_summary.style.format({
                "avg_bill": "₹{:,.2f}",
                "avg_hours": "{:,.1f} h",
                "avg_tariff": "₹{:.2f}",
                "record_count": "{:,}",
            }),
            width="stretch",
        )
