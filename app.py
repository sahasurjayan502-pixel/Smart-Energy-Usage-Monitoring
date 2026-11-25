"""
Smart Energy Usage Monitor — Application Entry Point.
Clean, personal household-focused landing page providing two primary navigation paths:
1. Configure My Household
2. View Energy Analytics
Plus independent access to the Historical Dataset Explorer.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from config.settings import APP_SUBTITLE, APP_TITLE, APP_VERSION, CSV_PATH, DB_PATH
from db.schema import init_db
from db.seeds import seed_database
from modules.analytics.loader import import_csv_to_analytics, is_already_imported

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database schema and seeds
init_db(DB_PATH)
seed_database(DB_PATH)

# Ingest historical dataset into SQLite if not already imported
is_imported, meta = is_already_imported(CSV_PATH, DB_PATH)
if not is_imported:
    with st.spinner("Initializing analytics store..."):
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
        .top-badge-container {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 0.5rem;
        }
        .top-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            background: #ffffff;
            border: 1px solid #e2ece5;
            border-radius: 9999px;
            padding: 0.25rem 0.8rem;
            font-size: 0.75rem;
            font-weight: 600;
            color: #475569;
        }
        .badge-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: #059669;
        }
        .hero-banner {
            background: linear-gradient(135deg, #eaf8ef 0%, #edf9f2 60%, #f4fbf7 100%);
            border: 1px solid #d4eedb;
            border-radius: 20px;
            padding: 1.6rem 2rem;
            margin-bottom: 1.75rem;
        }
        .hero-title {
            font-size: 2rem;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.2;
            letter-spacing: -0.02em;
            margin-bottom: 0.4rem;
        }
        .hero-subtitle {
            font-size: 1rem;
            color: #334155;
            line-height: 1.5;
            margin: 0;
        }
        .module-card {
            background: #ffffff;
            border: 1px solid #e2ece5;
            border-radius: 16px;
            padding: 1.4rem;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }
        .card-header-row {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            margin-bottom: 0.75rem;
        }
        .card-icon-pill {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .icon-green {
            background-color: #e6f7ec;
            color: #059669;
        }
        .icon-blue {
            background-color: #eff6ff;
            color: #2563eb;
        }
        .card-title-text {
            font-size: 1.2rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
        }
        .card-desc-text {
            font-size: 0.92rem;
            color: #475569;
            line-height: 1.55;
            min-height: 3.5rem;
            margin-bottom: 1.25rem;
        }
        .secondary-section-box {
            background: #ffffff;
            border: 1px solid #e2ece5;
            border-radius: 14px;
            padding: 1.1rem 1.4rem;
            margin-top: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
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
# MAIN HERO BANNER
# ==============================================================================
st.markdown(
    f"""
    <div class="top-badge-container">
        <div class="top-badge">
            <div class="badge-dot"></div>
            <span>v{APP_VERSION} • Household Edition</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="hero-banner">
        <div class="hero-title">{APP_TITLE}</div>
        <div class="hero-subtitle">
            Configure your household appliances, calculate estimated electricity bills,
            and monitor personalized energy consumption insights.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# TWO PRIMARY MODULE CARDS
# ==============================================================================
col_card1, col_card2 = st.columns(2, gap="large")

with col_card1:
    with st.container(border=True):
        st.markdown(
            """
            <div class="card-header-row">
                <div class="card-icon-pill icon-green">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                        <polyline points="9 22 9 12 15 12 15 22"/>
                    </svg>
                </div>
                <div class="card-title-text">My Household</div>
            </div>
            <div class="card-desc-text">
                Select your home appliances, customize wattages, adjust daily runtime hours,
                and calculate your estimated monthly consumption and BESCOM LT-1 bill.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/1_My_Household.py",
            label="Configure My Household →",
            icon="🏠",
        )

with col_card2:
    with st.container(border=True):
        st.markdown(
            """
            <div class="card-header-row">
                <div class="card-icon-pill icon-blue">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="20" x2="18" y2="10"/>
                        <line x1="12" y1="20" x2="12" y2="4"/>
                        <line x1="6" y1="20" x2="6" y2="14"/>
                    </svg>
                </div>
                <div class="card-title-text">Energy Analytics</div>
            </div>
            <div class="card-desc-text">
                View your personalized energy dashboard with appliance donut charts,
                expenditure shares, daily breakdowns, and actionable energy-saving insights.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/2_Energy_Analytics.py",
            label="View Energy Analytics →",
            icon="📊",
        )

# ==============================================================================
# INDEPENDENT HISTORICAL BENCHMARK EXPLORER
# ==============================================================================
st.markdown("<br>", unsafe_allow_html=True)
with st.container(border=True):
    col_hist_text, col_hist_btn = st.columns([3, 1], gap="medium")
    with col_hist_text:
        st.markdown("**📈 Historical Dataset Explorer (Independent Macro Benchmark)**")
        st.caption("Explore statistical macro distributions, city comparisons, and seasonal trends across 45,345 records.")
    with col_hist_btn:
        st.page_link(
            "pages/3_Historical_Dataset_Explorer.py",
            label="Open Dataset Explorer →",
            icon="📈",
        )
