"""
SQLite Repository for Household Profile, Appliance Configuration, and Bill Estimates.
Provides normalized database persistence and retrieval functions for the Estimator module.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from db.connection import get_db


# ==============================================================================
# HOUSEHOLDS
# ==============================================================================

def get_all_households(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves all active (non-archived) households."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT h.household_id, h.name, h.city, h.provider_id, h.sanctioned_load_kw,
                   h.supply_phase, h.created_at, h.updated_at, p.name AS provider_name
            FROM household h
            LEFT JOIN utility_provider p ON h.provider_id = p.provider_id
            WHERE h.is_archived = 0
            ORDER BY h.household_id ASC;
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def get_household(household_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single household profile by ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT h.household_id, h.name, h.city, h.provider_id, h.sanctioned_load_kw,
                   h.supply_phase, h.created_at, h.updated_at, p.name AS provider_name
            FROM household h
            LEFT JOIN utility_provider p ON h.provider_id = p.provider_id
            WHERE h.household_id = ? AND h.is_archived = 0;
            """,
            (household_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def create_household(
    name: str,
    city: str = "Bengaluru",
    provider_id: int = 1,
    sanctioned_load_kw: float = 3.0,
    db_path: Optional[Path] = None,
) -> int:
    """Creates a new household profile and returns its new household_id."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO household (name, city, provider_id, sanctioned_load_kw)
            VALUES (?, ?, ?, ?);
            """,
            (name.strip(), city.strip(), int(provider_id), float(sanctioned_load_kw)),
        )
        conn.commit()
        return cursor.lastrowid


def update_household(
    household_id: int,
    name: str,
    city: str,
    provider_id: int,
    sanctioned_load_kw: float,
    db_path: Optional[Path] = None,
) -> None:
    """Updates an existing household profile."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE household
            SET name = ?, city = ?, provider_id = ?, sanctioned_load_kw = ?, updated_at = datetime('now')
            WHERE household_id = ?;
            """,
            (name.strip(), city.strip(), int(provider_id), float(sanctioned_load_kw), int(household_id)),
        )
        conn.commit()


# ==============================================================================
# PROVIDERS & TARIFF SCHEDULES
# ==============================================================================

def get_utility_providers(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves active utility providers."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT provider_id, code, name, state, city_coverage
            FROM utility_provider
            WHERE is_active = 1
            ORDER BY provider_id ASC;
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def get_active_tariff_schedule(provider_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the active domestic LT-1 tariff schedule for a provider."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT schedule_id, provider_id, category_code, category_name,
                   tariff_version, base_energy_rate_paise, effective_from
            FROM tariff_schedule
            WHERE provider_id = ? AND category_code = 'LT-1' AND effective_to IS NULL
            LIMIT 1;
            """,
            (int(provider_id),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# ==============================================================================
# APPLIANCE SPECIFICATIONS (CATALOGUE)
# ==============================================================================

def get_appliance_categories(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves all appliance categories."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT category_id, name, icon FROM appliance_category ORDER BY category_id ASC;")
        return [dict(row) for row in cursor.fetchall()]


def get_appliance_specs(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves the full standard appliance catalogue."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.spec_id, s.category_id, c.name AS category_name, c.icon AS category_icon,
                   s.name, s.calculation_method, s.rated_watt, s.annual_kwh, s.kwh_per_cycle,
                   s.typical_usage_hrs_day, s.typical_cycles_per_month
            FROM appliance_spec s
            JOIN appliance_category c ON s.category_id = c.category_id
            ORDER BY c.category_id ASC, s.name ASC;
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def get_appliance_spec_by_id(spec_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single appliance specification by spec_id."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.spec_id, s.category_id, c.name AS category_name, c.icon AS category_icon,
                   s.name, s.calculation_method, s.rated_watt, s.annual_kwh, s.kwh_per_cycle,
                   s.typical_usage_hrs_day, s.typical_cycles_per_month
            FROM appliance_spec s
            JOIN appliance_category c ON s.category_id = c.category_id
            WHERE s.spec_id = ?;
            """,
            (int(spec_id),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# ==============================================================================
# HOUSEHOLD APPLIANCES (USER INVENTORY)
# ==============================================================================

def get_household_appliances(household_id: int, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves all appliances configured for a household with full spec and category metadata."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ha.appliance_id, ha.household_id, ha.spec_id, ha.calculation_method,
                   ha.quantity, ha.daily_hours, ha.days_per_month, ha.cycles_per_month,
                   ha.custom_watt, ha.custom_annual_kwh, ha.custom_kwh_per_cycle,
                   ha.custom_monthly_kwh, ha.label,
                   s.name AS spec_name, s.rated_watt, s.rated_watt AS default_watt,
                   s.annual_kwh, s.annual_kwh AS default_annual_kwh,
                   s.kwh_per_cycle, s.kwh_per_cycle AS default_kwh_per_cycle,
                   c.name AS category_name, c.icon AS category_icon
            FROM household_appliance ha
            JOIN appliance_spec s ON ha.spec_id = s.spec_id
            JOIN appliance_category c ON s.category_id = c.category_id
            WHERE ha.household_id = ?
            ORDER BY ha.appliance_id ASC;
            """,
            (int(household_id),),
        )
        return [dict(row) for row in cursor.fetchall()]


def add_household_appliance(
    household_id: int,
    spec_id: int,
    calculation_method: str,
    quantity: int = 1,
    daily_hours: Optional[float] = None,
    days_per_month: int = 30,
    custom_watt: Optional[float] = None,
    custom_annual_kwh: Optional[float] = None,
    custom_kwh_per_cycle: Optional[float] = None,
    cycles_per_month: Optional[float] = None,
    custom_monthly_kwh: Optional[float] = None,
    label: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Adds an appliance to the user's household inventory."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO household_appliance (
                household_id, spec_id, calculation_method, quantity, daily_hours,
                days_per_month, cycles_per_month, custom_watt, custom_annual_kwh, custom_kwh_per_cycle,
                custom_monthly_kwh, label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                int(household_id),
                int(spec_id),
                calculation_method,
                max(1, int(quantity)),
                daily_hours,
                max(1, min(31, int(days_per_month))),
                cycles_per_month,
                custom_watt,
                custom_annual_kwh,
                custom_kwh_per_cycle,
                custom_monthly_kwh,
                label.strip() if label else None,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def update_household_appliance(
    appliance_id: int,
    quantity: int,
    daily_hours: Optional[float],
    days_per_month: int = 30,
    custom_watt: Optional[float] = None,
    custom_annual_kwh: Optional[float] = None,
    label: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Updates quantity, hours, days, or custom wattage for an appliance."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE household_appliance
            SET quantity = ?, daily_hours = ?, days_per_month = ?,
                custom_watt = ?, custom_annual_kwh = ?, label = ?
            WHERE appliance_id = ?;
            """,
            (
                max(1, int(quantity)),
                daily_hours,
                max(1, min(31, int(days_per_month))),
                custom_watt,
                custom_annual_kwh,
                label.strip() if label else None,
                int(appliance_id),
            ),
        )
        conn.commit()


def delete_household_appliance(appliance_id: int, db_path: Optional[Path] = None) -> None:
    """Removes an appliance from the user's household inventory."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM household_appliance WHERE appliance_id = ?;", (int(appliance_id),))
        conn.commit()


# ==============================================================================
# BILL ESTIMATES & CALCULATION PERSISTENCE
# ==============================================================================

def save_bill_estimate(
    household_id: int,
    schedule_id: int,
    billing_month: str,
    bill_calc: Dict[str, Any],
    appliances_list: List[Dict[str, Any]],
    sanctioned_load_kw: float,
    tariff_version: str = "BESCOM-LT1-FY2026-27-V1",
    db_path: Optional[Path] = None,
) -> int:
    """
    Persists an immutable calculation snapshot of the household's estimated bill
    and individual appliance line items into bill_estimate and bill_estimate_line.
    """
    applied_json = json.dumps({
        "energy_rate_inr": bill_calc.get("energy_rate_inr", 5.80),
        "fixed_charge_rate_inr": bill_calc.get("fixed_charge_rate_inr", 150.0),
        "duty_percent": bill_calc.get("duty_percent", 9.0),
    })

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bill_estimate (
                household_id, schedule_id, billing_month, total_kwh,
                sanctioned_load_kw_snapshot, energy_tariff_type_snapshot,
                energy_rate_paise_snapshot, gross_energy_charge_paise,
                fixed_charge_rate_paise_snapshot, fixed_charge_paise,
                duty_paise, net_payable_paise, tariff_version_snapshot,
                applied_components_json, disclaimer_notice
            ) VALUES (?, ?, ?, ?, ?, 'single_rate', 580, ?, 15000, ?, ?, ?, ?, ?, ?);
            """,
            (
                int(household_id),
                int(schedule_id),
                billing_month,
                bill_calc["total_kwh"],
                sanctioned_load_kw,
                bill_calc["energy_charge_paise"],
                bill_calc["fixed_charge_paise"],
                bill_calc["duty_paise"],
                bill_calc["net_payable_paise"],
                tariff_version,
                applied_json,
                "Indicative estimate calculated using verified BESCOM LT-1 base tariff schedules. "
                "Actual meter bill may include verified FPPCA, meter rent, or local municipal surcharges.",
            ),
        )
        estimate_id = cursor.lastrowid

        # Insert immutable line items
        for app in appliances_list:
            display_name = app.get("label") or app.get("spec_name") or "Appliance"
            cat_name = app.get("category_name") or "General"
            method = app.get("calculation_method") or "rated_wattage"
            monthly_kwh = app.get("monthly_kwh", 0.0)
            share_pct = app.get("share_percent", 0.0)
            qty = app.get("quantity", 1)

            if method == "annual_kwh":
                power_spec = f"{app.get('custom_annual_kwh') or app.get('default_annual_kwh') or 0} kWh/yr"
                usage_str = f"{app.get('days_per_month', 30)} days/mo"
            elif method == "kwh_per_cycle":
                power_spec = f"{app.get('custom_kwh_per_cycle') or 0.65} kWh/cycle"
                usage_str = f"{app.get('cycles_per_month', 30)} cycles/mo"
            else:
                power_spec = f"{app.get('custom_watt') or app.get('default_watt') or 0} W"
                usage_str = f"{app.get('daily_hours', 0)} h/day, {app.get('days_per_month', 30)} days/mo"

            cursor.execute(
                """
                INSERT INTO bill_estimate_line (
                    estimate_id, household_appliance_id, appliance_name_snapshot,
                    category_name_snapshot, calculation_method_snapshot,
                    power_spec_snapshot, quantity_snapshot, usage_assumptions_snapshot,
                    monthly_kwh, share_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    estimate_id,
                    app.get("appliance_id"),
                    display_name,
                    cat_name,
                    method,
                    power_spec,
                    qty,
                    usage_str,
                    monthly_kwh,
                    share_pct,
                ),
            )

        conn.commit()
        return estimate_id


def get_latest_estimate(household_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent bill estimate for a household."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT estimate_id, household_id, schedule_id, billing_month, total_kwh,
                   sanctioned_load_kw_snapshot, gross_energy_charge_paise,
                   fixed_charge_paise, duty_paise, net_payable_paise,
                   tariff_version_snapshot, applied_components_json,
                   disclaimer_notice, created_at
            FROM bill_estimate
            WHERE household_id = ?
            ORDER BY estimate_id DESC
            LIMIT 1;
            """,
            (int(household_id),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_estimate_lines(estimate_id: int, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves the line items for a specific bill estimate snapshot."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT line_id, estimate_id, household_appliance_id, appliance_name_snapshot,
                   category_name_snapshot, calculation_method_snapshot, power_spec_snapshot,
                   quantity_snapshot, usage_assumptions_snapshot, monthly_kwh, share_percent
            FROM bill_estimate_line
            WHERE estimate_id = ?
            ORDER BY monthly_kwh DESC;
            """,
            (int(estimate_id),),
        )
        return [dict(row) for row in cursor.fetchall()]
