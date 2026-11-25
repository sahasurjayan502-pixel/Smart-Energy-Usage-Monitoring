"""
Database Schema Initialization and Migration.
Defines all 12 normalized SQLite tables, relationships, constraints, and indexes
in exact conformance with architecture.md Version 1.2.
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import get_db

SCHEMA_SQL = """
-- ============================================================
-- 1. UTILITY PROVIDER
-- ============================================================
CREATE TABLE IF NOT EXISTS utility_provider (
    provider_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    state           TEXT    NOT NULL DEFAULT 'Karnataka',
    city_coverage   TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 2. TARIFF SCHEDULE (Base Tariff Header)
-- ============================================================
CREATE TABLE IF NOT EXISTS tariff_schedule (
    schedule_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id             INTEGER NOT NULL REFERENCES utility_provider(provider_id) ON DELETE RESTRICT,
    category_code           TEXT    NOT NULL,
    category_name           TEXT    NOT NULL,
    tariff_version          TEXT    NOT NULL,
    energy_tariff_type      TEXT    NOT NULL DEFAULT 'single_rate',
    base_energy_rate_paise  INTEGER,
    effective_from          TEXT    NOT NULL,
    effective_to            TEXT,
    scheme_name             TEXT    NOT NULL DEFAULT 'standard',
    source_ref              TEXT    NOT NULL,
    is_verified             INTEGER NOT NULL DEFAULT 0,
    notes                   TEXT,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (provider_id, category_code, effective_from, scheme_name)
);

-- ============================================================
-- 3. TARIFF SLABS (Tiered Energy Tariffs if applicable)
-- ============================================================
CREATE TABLE IF NOT EXISTS tariff_slab (
    slab_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id     INTEGER NOT NULL REFERENCES tariff_schedule(schedule_id) ON DELETE CASCADE,
    slab_order      INTEGER NOT NULL,
    unit_from       INTEGER NOT NULL,
    unit_to         INTEGER,
    rate_paise      INTEGER NOT NULL,
    description     TEXT,
    UNIQUE (schedule_id, slab_order)
);

-- ============================================================
-- 4. TARIFF COMPONENTS (Fixed, Duty, FPPCA, P&G, True-up)
-- ============================================================
CREATE TABLE IF NOT EXISTS tariff_component (
    component_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id         INTEGER NOT NULL REFERENCES tariff_schedule(schedule_id) ON DELETE CASCADE,
    component_type      TEXT    NOT NULL,
    calculation_method  TEXT    NOT NULL,
    rate_value          TEXT    NOT NULL,
    unit                TEXT    NOT NULL,
    billing_month       TEXT,
    effective_from      TEXT    NOT NULL,
    effective_to        TEXT,
    source_ref          TEXT    NOT NULL,
    is_verified         INTEGER NOT NULL DEFAULT 0,
    notes               TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 5. APPLIANCE CATEGORY
-- ============================================================
CREATE TABLE IF NOT EXISTS appliance_category (
    category_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    icon            TEXT
);

-- ============================================================
-- 6. APPLIANCE SPECIFICATIONS (Catalogue Source of Truth)
-- ============================================================
CREATE TABLE IF NOT EXISTS appliance_spec (
    spec_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id             INTEGER NOT NULL REFERENCES appliance_category(category_id) ON DELETE RESTRICT,
    name                    TEXT    NOT NULL,
    calculation_method      TEXT    NOT NULL,
    rated_watt              INTEGER,
    annual_kwh              REAL,
    kwh_per_cycle           REAL,
    supports_standby        INTEGER NOT NULL DEFAULT 0,
    standby_watt            INTEGER NOT NULL DEFAULT 0,
    efficiency_star         INTEGER,
    typical_usage_hrs_day   REAL,
    typical_cycles_per_month REAL,
    source_ref              TEXT    NOT NULL,
    is_verified             INTEGER NOT NULL DEFAULT 0,
    notes                   TEXT,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 7. HOUSEHOLD PROFILE (User Configuration)
-- ============================================================
CREATE TABLE IF NOT EXISTS household (
    household_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name                        TEXT    NOT NULL,
    city                        TEXT    NOT NULL DEFAULT 'Bengaluru',
    provider_id                 INTEGER NOT NULL REFERENCES utility_provider(provider_id) ON DELETE RESTRICT,
    sanctioned_load_kw          REAL    NOT NULL DEFAULT 1.0,
    supply_phase                TEXT    NOT NULL DEFAULT 'single',
    is_gruha_jyothi_eligible    INTEGER NOT NULL DEFAULT 0,
    gruha_jyothi_entitlement_source TEXT NOT NULL DEFAULT 'manual',
    gruha_jyothi_avg_monthly_kwh REAL,
    gruha_jyothi_entitled_units  REAL,
    is_archived                 INTEGER NOT NULL DEFAULT 0,
    created_at                  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at                  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 8. HOUSEHOLD APPLIANCES (User Appliance List)
-- ============================================================
CREATE TABLE IF NOT EXISTS household_appliance (
    appliance_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id            INTEGER NOT NULL REFERENCES household(household_id) ON DELETE CASCADE,
    spec_id                 INTEGER NOT NULL REFERENCES appliance_spec(spec_id) ON DELETE RESTRICT,
    calculation_method      TEXT    NOT NULL,
    quantity                INTEGER NOT NULL DEFAULT 1,
    daily_hours             REAL,
    days_per_month          INTEGER NOT NULL DEFAULT 30,
    standby_enabled         INTEGER NOT NULL DEFAULT 0,
    daily_standby_hours     REAL DEFAULT 0,
    cycles_per_month        REAL,
    custom_watt             INTEGER,
    custom_annual_kwh       REAL,
    custom_kwh_per_cycle    REAL,
    custom_monthly_kwh      REAL,
    label                   TEXT,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 9. BILL ESTIMATE (Immutable Calculation Snapshot Header)
-- ============================================================
CREATE TABLE IF NOT EXISTS bill_estimate (
    estimate_id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    household_id                    INTEGER NOT NULL REFERENCES household(household_id) ON DELETE RESTRICT,
    schedule_id                     INTEGER NOT NULL REFERENCES tariff_schedule(schedule_id) ON DELETE RESTRICT,
    billing_month                   TEXT    NOT NULL,
    total_kwh                       REAL    NOT NULL,
    sanctioned_load_kw_snapshot     REAL    NOT NULL,
    energy_tariff_type_snapshot     TEXT    NOT NULL,
    energy_rate_paise_snapshot      INTEGER,
    gross_energy_charge_paise       INTEGER NOT NULL,
    fixed_charge_rate_paise_snapshot INTEGER NOT NULL,
    fixed_charge_paise              INTEGER NOT NULL,
    duty_paise                      INTEGER NOT NULL,
    duty_status                     TEXT    NOT NULL DEFAULT 'verified',
    fppca_paise                     INTEGER NOT NULL DEFAULT 0,
    fppca_rate_paise_snapshot       INTEGER,
    fppca_status                    TEXT    NOT NULL DEFAULT 'missing',
    pg_surcharge_paise              INTEGER NOT NULL DEFAULT 0,
    pg_surcharge_status             TEXT    NOT NULL DEFAULT 'missing',
    true_up_paise                   INTEGER NOT NULL DEFAULT 0,
    true_up_status                  TEXT    NOT NULL DEFAULT 'missing',
    gruha_jyothi_eligible           INTEGER NOT NULL DEFAULT 0,
    gruha_jyothi_entitled_units_snapshot REAL,
    gruha_jyothi_status             TEXT    NOT NULL DEFAULT 'deferred_in_mvp',
    subsidy_paise                   INTEGER NOT NULL DEFAULT 0,
    net_payable_paise               INTEGER NOT NULL,
    tariff_version_snapshot         TEXT    NOT NULL,
    applied_components_json         TEXT    NOT NULL,
    has_unverified_components       INTEGER NOT NULL DEFAULT 0,
    disclaimer_notice               TEXT    NOT NULL,
    created_at                      TEXT    NOT NULL DEFAULT (datetime('now')),
    notes                           TEXT
);

-- ============================================================
-- 10. BILL ESTIMATE LINE ITEMS (Immutable Appliance Snapshots)
-- ============================================================
CREATE TABLE IF NOT EXISTS bill_estimate_line (
    line_id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    estimate_id                 INTEGER NOT NULL REFERENCES bill_estimate(estimate_id) ON DELETE CASCADE,
    household_appliance_id      INTEGER REFERENCES household_appliance(appliance_id) ON DELETE SET NULL,
    appliance_name_snapshot     TEXT    NOT NULL,
    category_name_snapshot      TEXT    NOT NULL,
    calculation_method_snapshot TEXT    NOT NULL,
    power_spec_snapshot         TEXT    NOT NULL,
    quantity_snapshot           INTEGER NOT NULL,
    usage_assumptions_snapshot  TEXT    NOT NULL,
    monthly_kwh                 REAL    NOT NULL,
    share_percent               REAL    NOT NULL
);

-- ============================================================
-- 11. ANALYTICS METADATA (Kaggle Dataset Import Ledger)
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_metadata (
    meta_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file     TEXT    NOT NULL UNIQUE,
    row_count       INTEGER NOT NULL,
    checksum        TEXT    NOT NULL,
    imported_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 12. ANALYTICS READINGS (Kaggle Dataset — Read-Only Analytical Store)
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_reading (
    reading_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_id             INTEGER NOT NULL REFERENCES analytics_metadata(meta_id) ON DELETE CASCADE,
    fan                 INTEGER,
    refrigerator        INTEGER,
    air_conditioner     INTEGER,
    television          INTEGER,
    monitor             INTEGER,
    motor_pump          INTEGER,
    month               INTEGER,
    city                TEXT,
    company             TEXT,
    monthly_hours       REAL,
    tariff_rate         REAL,
    electricity_bill    REAL
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_tariff_sched_provider    ON tariff_schedule(provider_id);
CREATE INDEX IF NOT EXISTS idx_tariff_sched_active      ON tariff_schedule(effective_to) WHERE effective_to IS NULL;
CREATE INDEX IF NOT EXISTS idx_tariff_comp_schedule     ON tariff_component(schedule_id);
CREATE INDEX IF NOT EXISTS idx_tariff_slab_schedule     ON tariff_slab(schedule_id);
CREATE INDEX IF NOT EXISTS idx_spec_category            ON appliance_spec(category_id);
CREATE INDEX IF NOT EXISTS idx_spec_method              ON appliance_spec(calculation_method);
CREATE INDEX IF NOT EXISTS idx_hh_appliance_household   ON household_appliance(household_id);
CREATE INDEX IF NOT EXISTS idx_estimate_household       ON bill_estimate(household_id);
CREATE INDEX IF NOT EXISTS idx_estimate_month           ON bill_estimate(billing_month);
CREATE INDEX IF NOT EXISTS idx_estimate_line_estimate   ON bill_estimate_line(estimate_id);
CREATE INDEX IF NOT EXISTS idx_analytics_city           ON analytics_reading(city);
CREATE INDEX IF NOT EXISTS idx_analytics_month          ON analytics_reading(month);
CREATE INDEX IF NOT EXISTS idx_analytics_company        ON analytics_reading(company);
"""


def init_db(db_path: Optional[Path] = None) -> None:
    """
    Initializes all tables and indexes in the SQLite database.
    This operation is safe to run multiple times (idempotent).
    """
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


if __name__ == "__main__":
    init_db()
    print("Database schema successfully initialized.")
