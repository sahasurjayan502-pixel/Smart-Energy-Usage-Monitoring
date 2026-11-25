"""
Unit Tests for Database Schema and Relationship Integrity.
Verifies all 12 tables, foreign key constraints, cascading/set null rules,
and household deletion protection via ON DELETE RESTRICT and is_archived.
"""

import sqlite3
import sys
import unittest
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import get_connection, get_db
from db.schema import init_db


class TestSchemaIntegrity(unittest.TestCase):
    """Tests SQLite schema structure and relational constraints."""

    def setUp(self):
        """Creates an isolated in-memory or temporary test database."""
        self.test_db_path = PROJECT_ROOT / "data" / "test_energy_monitor.db"
        if self.test_db_path.exists():
            self.test_db_path.unlink()
        init_db(self.test_db_path)

    def tearDown(self):
        """Cleans up the test database file."""
        if self.test_db_path.exists():
            try:
                self.test_db_path.unlink()
            except PermissionError:
                pass

    def test_all_twelve_tables_exist(self):
        """Verifies that all 12 tables defined in architecture.md Version 1.2 exist."""
        expected_tables = {
            "utility_provider",
            "tariff_schedule",
            "tariff_slab",
            "tariff_component",
            "appliance_category",
            "appliance_spec",
            "household",
            "household_appliance",
            "bill_estimate",
            "bill_estimate_line",
            "analytics_metadata",
            "analytics_reading",
        }
        with get_db(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            actual_tables = {row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")}
            self.assertTrue(expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}")

    def test_schema_initialization_is_idempotent(self):
        """Verifies that running init_db() a second time causes no errors."""
        try:
            init_db(self.test_db_path)
        except Exception as e:
            self.fail(f"Second call to init_db() failed with error: {e}")

    def test_foreign_key_enforcement_active(self):
        """Verifies that foreign key enforcement is turned on and blocks orphaned records."""
        with get_db(self.test_db_path) as conn:
            cursor = conn.cursor()
            # Attempt inserting household with invalid provider_id
            with self.assertRaises(sqlite3.IntegrityError):
                cursor.execute(
                    """
                    INSERT INTO household (name, city, provider_id, sanctioned_load_kw)
                    VALUES ('Test Home', 'Bengaluru', 99999, 2.0);
                    """
                )

    def test_household_deletion_protection_via_restrict(self):
        """
        Verifies that deleting a household profile that has associated bill estimates
        is strictly blocked by ON DELETE RESTRICT to protect historical financial records.
        """
        with get_db(self.test_db_path) as conn:
            cursor = conn.cursor()

            # 1. Insert provider
            cursor.execute(
                "INSERT INTO utility_provider (code, name, state) VALUES ('BESCOM', 'BESCOM Ltd', 'Karnataka');"
            )
            provider_id = cursor.lastrowid

            # 2. Insert schedule
            cursor.execute(
                """
                INSERT INTO tariff_schedule (provider_id, category_code, category_name, tariff_version, effective_from, source_ref)
                VALUES (?, 'LT-1', 'Domestic', 'V1', '2026-04-01', 'KERC Order');
                """,
                (provider_id,),
            )
            schedule_id = cursor.lastrowid

            # 3. Insert household
            cursor.execute(
                "INSERT INTO household (name, city, provider_id, sanctioned_load_kw) VALUES ('My Flat', 'Bengaluru', ?, 3.0);",
                (provider_id,),
            )
            household_id = cursor.lastrowid

            # 4. Insert bill estimate linked to household
            cursor.execute(
                """
                INSERT INTO bill_estimate (
                    household_id, schedule_id, billing_month, total_kwh, sanctioned_load_kw_snapshot,
                    energy_tariff_type_snapshot, gross_energy_charge_paise, fixed_charge_rate_paise_snapshot,
                    fixed_charge_paise, duty_paise, net_payable_paise, tariff_version_snapshot,
                    applied_components_json, disclaimer_notice
                ) VALUES (
                    ?, ?, '2026-11', 150.0, 3.0,
                    'single_rate', 87000, 15000,
                    45000, 7830, 139830, 'V1',
                    '{}', 'Indicative estimate only.'
                );
                """,
                (household_id, schedule_id),
            )

            # 5. Attempt deleting household -> MUST raise IntegrityError because of ON DELETE RESTRICT
            with self.assertRaises(sqlite3.IntegrityError):
                cursor.execute("DELETE FROM household WHERE household_id = ?;", (household_id,))

            # 6. Verify household can be soft-archived instead of deleted
            cursor.execute("UPDATE household SET is_archived = 1 WHERE household_id = ?;", (household_id,))
            cursor.execute("SELECT is_archived FROM household WHERE household_id = ?;", (household_id,))
            row = cursor.fetchone()
            self.assertEqual(row["is_archived"], 1)

    def test_bill_estimate_line_snapshot_preserved_on_appliance_deletion(self):
        """
        Verifies that deleting an appliance from household_appliance sets household_appliance_id
        to NULL in bill_estimate_line (ON DELETE SET NULL) while preserving all snapshot strings.
        """
        with get_db(self.test_db_path) as conn:
            cursor = conn.cursor()

            # Provider & schedule
            cursor.execute("INSERT INTO utility_provider (code, name) VALUES ('BESCOM_TEST', 'BESCOM');")
            pid = cursor.lastrowid
            cursor.execute(
                "INSERT INTO tariff_schedule (provider_id, category_code, category_name, tariff_version, effective_from, source_ref) VALUES (?, 'LT-1', 'Domestic', 'V1', '2026-04-01', 'Ref');",
                (pid,),
            )
            sid = cursor.lastrowid

            # Category & Spec
            cursor.execute("INSERT INTO appliance_category (name) VALUES ('Cooling');")
            cat_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO appliance_spec (category_id, name, calculation_method, rated_watt, source_ref) VALUES (?, 'Fan', 'rated_wattage', 55, 'Ref');",
                (cat_id,),
            )
            spec_id = cursor.lastrowid

            # Household & Appliance
            cursor.execute("INSERT INTO household (name, provider_id) VALUES ('Villa', ?);", (pid,))
            hid = cursor.lastrowid
            cursor.execute(
                "INSERT INTO household_appliance (household_id, spec_id, calculation_method, quantity, daily_hours) VALUES (?, ?, 'rated_wattage', 2, 8.0);",
                (hid, spec_id),
            )
            appliance_id = cursor.lastrowid

            # Bill Estimate
            cursor.execute(
                """
                INSERT INTO bill_estimate (
                    household_id, schedule_id, billing_month, total_kwh, sanctioned_load_kw_snapshot,
                    energy_tariff_type_snapshot, gross_energy_charge_paise, fixed_charge_rate_paise_snapshot,
                    fixed_charge_paise, duty_paise, net_payable_paise, tariff_version_snapshot,
                    applied_components_json, disclaimer_notice
                ) VALUES (?, ?, '2026-11', 26.4, 1.0, 'single_rate', 15312, 15000, 15000, 1378, 31690, 'V1', '{}', 'Disclaimer');
                """,
                (hid, sid),
            )
            est_id = cursor.lastrowid

            # Estimate Line Item with snapshot data
            cursor.execute(
                """
                INSERT INTO bill_estimate_line (
                    estimate_id, household_appliance_id, appliance_name_snapshot, category_name_snapshot,
                    calculation_method_snapshot, power_spec_snapshot, quantity_snapshot,
                    usage_assumptions_snapshot, monthly_kwh, share_percent
                ) VALUES (?, ?, 'Ceiling Fan (55W)', 'Cooling', 'rated_wattage', '55 W', 2, '8.0 hrs/day, 30 days', 26.4, 100.0);
                """,
                (est_id, appliance_id),
            )
            line_id = cursor.lastrowid

            # Delete the appliance from active inventory
            cursor.execute("DELETE FROM household_appliance WHERE appliance_id = ?;", (appliance_id,))

            # Query the estimate line
            cursor.execute("SELECT * FROM bill_estimate_line WHERE line_id = ?;", (line_id,))
            line = cursor.fetchone()

            # Verification: foreign key is NULL, but snapshot data is completely intact
            self.assertIsNone(line["household_appliance_id"])
            self.assertEqual(line["appliance_name_snapshot"], "Ceiling Fan (55W)")
            self.assertEqual(line["monthly_kwh"], 26.4)
            self.assertEqual(line["share_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
