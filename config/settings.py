"""
Application Configuration and Constants.
Provides centralized path management and default parameters for Smart Energy Usage Monitor.
"""

from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
SEEDS_DIR = DATA_DIR / "seeds"

# Database path (energy_monitor.db in data directory)
DB_PATH = DATA_DIR / "energy_monitor.db"

# Source files
# The raw CSV may reside in the project root or in data/raw/
CSV_PATH_ROOT = PROJECT_ROOT / "electricity_bill_dataset.csv"
CSV_PATH_RAW = RAW_DATA_DIR / "electricity_bill_dataset.csv"
CSV_PATH = CSV_PATH_ROOT if CSV_PATH_ROOT.exists() else CSV_PATH_RAW

PDF_PATH = PROJECT_ROOT / "Tariff_and_Duty_of_Electricity_Supply_in_India-March_2026.pdf"

# Application metadata
APP_TITLE = "Smart Energy Usage Monitor"
APP_SUBTITLE = "Household Energy Estimator & Historical Analytics"
APP_VERSION = "1.2 (Phase 0 & 1 MVP)"

# Default domain settings
DEFAULT_PROVIDER_CODE = "BESCOM"
DEFAULT_CATEGORY_CODE = "LT-1"
DEFAULT_TARIFF_VERSION = "BESCOM-LT1-FY2026-27-V1"
BASE_ENERGY_RATE_PAISE = 580  # ₹5.80/kWh
FIXED_CHARGE_RATE_PAISE = 15000  # ₹150/kW/month
ELECTRICITY_DUTY_PERCENT = 9.0  # 9% on energy charge
GRUHA_JYOTHI_MAX_CEILING_KWH = 200.0  # 200 kWh ceiling
GRUHA_JYOTHI_BUFFER_RATIO = 1.10  # 10% buffer on 12-month average
