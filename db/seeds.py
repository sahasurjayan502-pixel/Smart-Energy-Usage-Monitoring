"""
Initial Database Seeding for Utility Providers, Tariffs, and Appliance Catalogue.
Ensures essential reference data for Bengaluru / BESCOM (LT-1) and standard household appliances
is available in SQLite idempotently.
"""

import sqlite3
from typing import Optional
from pathlib import Path
from db.connection import get_db

SEED_CATEGORIES = [
    ("Cooling", "❄️"),
    ("Lighting", "💡"),
    ("Entertainment & IT", "💻"),
    ("Kitchen", "🍳"),
    ("Water & Heating", "🚿"),
    ("General Household", "🏠"),
]

# Standard household appliances with conservative engineering ratings and typical daily operating patterns
SEED_APPLIANCES = [
    # (Category, Name, calculation_method, rated_watt, annual_kwh, kwh_per_cycle, supports_standby, standby_watt, typical_hrs, typical_cycles, source_ref)
    ("Cooling", "Ceiling Fan", "rated_wattage", 55, None, None, 0, 0, 8.0, None, "BEE Star Label Standard"),
    ("Cooling", "Table Fan", "rated_wattage", 45, None, None, 0, 0, 6.0, None, "Standard Wattage Guide"),
    ("Kitchen", "Refrigerator (260L 3-Star)", "annual_kwh", None, 220.0, None, 0, 0, 24.0, None, "BEE Refrigerator Energy Label"),
    ("Cooling", "Air Conditioner (1.5 Ton 3-Star)", "rated_wattage", 1400, None, None, 1, 2, 6.0, None, "BEE AC Energy Rating Guideline"),
    ("Lighting", "LED Bulb (9W)", "rated_wattage", 9, None, None, 0, 0, 5.0, None, "Standard LED Specification"),
    ("Lighting", "Tube Light (20W LED)", "rated_wattage", 20, None, None, 0, 0, 4.0, None, "Standard LED Batten Spec"),
    ("Entertainment & IT", "Television (43\" Smart LED)", "rated_wattage", 75, None, None, 1, 1, 4.0, None, "Consumer Electronics Benchmark"),
    ("Entertainment & IT", "Laptop", "rated_wattage", 65, None, None, 1, 1, 6.0, None, "Typical Power Adapter Rating"),
    ("Entertainment & IT", "Desktop Computer", "rated_wattage", 150, None, None, 1, 2, 5.0, None, "Typical PC & Monitor Rating"),
    ("General Household", "Washing Machine (6.5kg)", "kwh_per_cycle", None, None, 0.65, 1, 1, None, 1.0, "BEE Washing Machine Star Rating"),
    ("Water & Heating", "Water Heater / Geyser (15L)", "rated_wattage", 2000, None, None, 0, 0, 1.0, None, "Storage Water Heater Spec"),
    ("Water & Heating", "Water Pump (1 HP)", "rated_wattage", 750, None, None, 0, 0, 1.0, None, "Domestic Monobloc Pump Spec"),
    ("Kitchen", "Microwave Oven", "rated_wattage", 1200, None, None, 1, 2, 0.5, None, "Convection Microwave Spec"),
    ("General Household", "Electric Iron", "rated_wattage", 1000, None, None, 0, 0, 0.5, None, "Dry/Steam Iron Spec"),
    ("Kitchen", "Induction Cooktop", "rated_wattage", 1500, None, None, 1, 1, 1.5, None, "Induction Cooker Spec"),
    ("Kitchen", "Mixer Grinder", "rated_wattage", 500, None, None, 0, 0, 0.5, None, "Domestic Mixer Grinder Spec"),
    ("Entertainment & IT", "Wi-Fi Router", "rated_wattage", 12, None, None, 0, 0, 24.0, None, "Broadband Router Power Spec"),
    ("General Household", "Other / Custom Appliance", "rated_wattage", 100, None, None, 0, 0, 1.0, None, "User-Defined Custom Load"),
]


def seed_database(db_path: Optional[Path] = None) -> None:
    """
    Seeds initial reference records for utility providers, BESCOM LT-1 tariff schedules,
    appliance categories, and verified appliance specifications.
    This operation is strictly idempotent (safe to run multiple times).
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # 1. Utility Provider: BESCOM
        cursor.execute(
            """
            INSERT OR IGNORE INTO utility_provider (code, name, state, city_coverage)
            VALUES ('BESCOM', 'Bengaluru Electricity Supply Company Ltd', 'Karnataka', 'Bengaluru');
            """
        )
        cursor.execute("SELECT provider_id FROM utility_provider WHERE code = 'BESCOM';")
        provider_row = cursor.fetchone()
        if not provider_row:
            return
        provider_id = provider_row[0]

        # 2. Tariff Schedule: BESCOM LT-1 Domestic (FY 2026-27 Base Rate: ₹5.80 / kWh -> 580 paise)
        cursor.execute(
            """
            INSERT OR IGNORE INTO tariff_schedule (
                provider_id, category_code, category_name, tariff_version,
                energy_tariff_type, base_energy_rate_paise, effective_from,
                scheme_name, source_ref, is_verified, notes
            ) VALUES (
                ?, 'LT-1', 'Domestic Lighting & Household Power', 'BESCOM-LT1-FY2026-27-V1',
                'single_rate', 580, '2026-04-01',
                'standard', 'KERC Tariff Order FY 2026-27', 1,
                'Bengaluru Domestic LT-1 tariff with single energy rate'
            );
            """,
            (provider_id,),
        )
        cursor.execute(
            "SELECT schedule_id FROM tariff_schedule WHERE provider_id = ? AND category_code = 'LT-1';",
            (provider_id,),
        )
        schedule_row = cursor.fetchone()
        if schedule_row:
            schedule_id = schedule_row[0]

            # 3. Tariff Components: Fixed Charge (₹150/kW/month) & Electricity Duty (9%)
            cursor.execute(
                """
                SELECT count(*) FROM tariff_component WHERE schedule_id = ?;
                """,
                (schedule_id,),
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    INSERT INTO tariff_component (
                        schedule_id, component_type, calculation_method, rate_value, unit,
                        effective_from, source_ref, is_verified, notes
                    ) VALUES
                    (?, 'fixed_charge', 'per_kw_monthly', '15000', 'paise/kW/month', '2026-04-01', 'KERC Order Sec 4.1', 1, 'Fixed charge of ₹150.00/kW/month'),
                    (?, 'duty', 'percentage', '9.0', 'percent', '2026-04-01', 'Karnataka Electricity Duty Act', 1, '9.0% electricity duty on energy charges');
                    """,
                    (schedule_id, schedule_id),
                )

        # 4. Appliance Categories
        category_map = {}
        for cat_name, icon in SEED_CATEGORIES:
            cursor.execute(
                """
                INSERT OR IGNORE INTO appliance_category (name, icon)
                VALUES (?, ?);
                """,
                (cat_name, icon),
            )
            cursor.execute("SELECT category_id FROM appliance_category WHERE name = ?;", (cat_name,))
            category_map[cat_name] = cursor.fetchone()[0]

        # 5. Appliance Specifications Catalogue
        for (cat_name, name, method, watt, annual_kwh, kwh_per_cycle, supports_standby, standby_watt, typical_hrs, typical_cycles, source_ref) in SEED_APPLIANCES:
            cat_id = category_map.get(cat_name)
            if not cat_id:
                continue

            cursor.execute(
                """
                SELECT spec_id FROM appliance_spec WHERE name = ?;
                """,
                (name,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO appliance_spec (
                        category_id, name, calculation_method, rated_watt, annual_kwh,
                        kwh_per_cycle, supports_standby, standby_watt, typical_usage_hrs_day,
                        typical_cycles_per_month, source_ref, is_verified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                    """,
                    (cat_id, name, method, watt, annual_kwh, kwh_per_cycle, supports_standby, standby_watt, typical_hrs, typical_cycles, source_ref),
                )
