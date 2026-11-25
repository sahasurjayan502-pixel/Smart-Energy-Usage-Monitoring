"""
Analytical Queries for Historical Electricity Dataset.
Provides query helpers, summary aggregations, and filter functions for Streamlit dashboard.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from config.settings import DB_PATH
from db.connection import get_db


def get_filter_options(db_path: Path = DB_PATH) -> Dict[str, List[Any]]:
    """Fetches unique cities, months, and companies available for filtering."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT city FROM analytics_reading ORDER BY city;")
        cities = [r[0] for r in cursor.fetchall() if r[0]]

        cursor.execute("SELECT DISTINCT month FROM analytics_reading ORDER BY month;")
        months = [r[0] for r in cursor.fetchall() if r[0] is not None]

        cursor.execute("SELECT DISTINCT company FROM analytics_reading ORDER BY company;")
        companies = [r[0] for r in cursor.fetchall() if r[0]]

    return {
        "cities": cities,
        "months": months,
        "companies": companies,
    }


def get_overview_metrics(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Computes high-level KPI overview statistics across the entire dataset."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_records,
                COUNT(DISTINCT city) AS total_cities,
                COUNT(DISTINCT company) AS total_companies,
                AVG(electricity_bill) AS avg_bill,
                AVG(monthly_hours) AS avg_hours,
                AVG(tariff_rate) AS avg_tariff,
                MIN(electricity_bill) AS min_bill,
                MAX(electricity_bill) AS max_bill
            FROM analytics_reading;
            """
        )
        row = cursor.fetchone()

        # Check MotorPump is always zero
        cursor.execute("SELECT COUNT(*) FROM analytics_reading WHERE motor_pump != 0;")
        non_zero_pumps = cursor.fetchone()[0]

    return {
        "total_records": row["total_records"],
        "total_cities": row["total_cities"],
        "total_companies": row["total_companies"],
        "avg_bill": round(row["avg_bill"], 2) if row["avg_bill"] else 0.0,
        "avg_hours": round(row["avg_hours"], 1) if row["avg_hours"] else 0.0,
        "avg_tariff": round(row["avg_tariff"], 2) if row["avg_tariff"] else 0.0,
        "min_bill": round(row["min_bill"], 2) if row["min_bill"] else 0.0,
        "max_bill": round(row["max_bill"], 2) if row["max_bill"] else 0.0,
        "motor_pump_always_zero": (non_zero_pumps == 0),
    }


def load_filtered_readings(
    cities: Optional[List[str]] = None,
    months: Optional[List[int]] = None,
    companies: Optional[List[str]] = None,
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """
    Loads analytics records applying user-selected filters.
    Returns a Pandas DataFrame for downstream visualization.
    """
    conditions = []
    params: List[Any] = []

    if cities:
        placeholders = ", ".join(["?"] * len(cities))
        conditions.append(f"city IN ({placeholders})")
        params.extend(cities)

    if months:
        placeholders = ", ".join(["?"] * len(months))
        conditions.append(f"month IN ({placeholders})")
        params.extend(months)

    if companies:
        placeholders = ", ".join(["?"] * len(companies))
        conditions.append(f"company IN ({placeholders})")
        params.extend(companies)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
    SELECT
        reading_id,
        city,
        company,
        month,
        monthly_hours,
        tariff_rate,
        electricity_bill,
        fan,
        refrigerator,
        air_conditioner,
        television,
        monitor,
        motor_pump
    FROM analytics_reading
    {where_clause};
    """

    with get_db(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=params)

    return df


def get_city_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates average bill, monthly hours, and tariff rate grouped by city."""
    if df.empty:
        return pd.DataFrame(columns=["city", "avg_bill", "avg_hours", "avg_tariff", "record_count"])

    summary = (
        df.groupby("city")
        .agg(
            avg_bill=("electricity_bill", "mean"),
            avg_hours=("monthly_hours", "mean"),
            avg_tariff=("tariff_rate", "mean"),
            record_count=("reading_id", "count"),
        )
        .reset_index()
    )
    summary.sort_values(by="avg_bill", ascending=False, inplace=True)
    return summary


def get_monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates month-by-month average bill and hours across the selected slice."""
    if df.empty:
        return pd.DataFrame(columns=["month", "avg_bill", "avg_hours"])

    trend = (
        df.groupby("month")
        .agg(
            avg_bill=("electricity_bill", "mean"),
            avg_hours=("monthly_hours", "mean"),
            record_count=("reading_id", "count"),
        )
        .reset_index()
    )
    trend.sort_values(by="month", inplace=True)
    return trend
