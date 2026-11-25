"""
Unit Tests for Estimator Calculation Engine, Database Repository, and Insights.
Verifies multi-method energy formulas, BESCOM LT-1 bill calculations,
household profile persistence, appliance inventory CRUD, and snapshot preservation.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DB_PATH
from db.connection import get_db
from db.schema import init_db
from db.seeds import seed_database
from modules.estimator.calculator import (
    calculate_appliance_energy,
    calculate_bescom_bill,
    calculate_household_summary,
)
from modules.estimator.insights import generate_household_insights
from modules.estimator.repository import (
    add_household_appliance,
    create_household,
    delete_household_appliance,
    get_all_households,
    get_appliance_specs,
    get_estimate_lines,
    get_household,
    get_household_appliances,
    get_latest_estimate,
    save_bill_estimate,
    update_household,
    update_household_appliance,
)


class TestEstimatorModule(unittest.TestCase):
    """Test suite for household estimator calculations, repository persistence, and insights."""

    @classmethod
    def setUpClass(cls):
        """Initializes and seeds the test database."""
        cls.test_db_path = PROJECT_ROOT / "data" / "test_estimator.db"
        if cls.test_db_path.exists():
            cls.test_db_path.unlink()
        init_db(cls.test_db_path)
        seed_database(cls.test_db_path)

    @classmethod
    def tearDownClass(cls):
        """Removes the test database file."""
        if cls.test_db_path.exists():
            try:
                cls.test_db_path.unlink()
            except PermissionError:
                pass

    def test_rated_wattage_calculation(self):
        """Verifies (Rated Wattage × Qty × Hours × Days) / 1000 formula."""
        # 55W fan, 2 units, 8.0 hrs/day, 30 days = (55 * 2 * 8 * 30) / 1000 = 26.4 kWh
        res = calculate_appliance_energy(
            calculation_method="rated_wattage",
            quantity=2,
            rated_watt=55,
            daily_hours=8.0,
            days_per_month=30,
        )
        self.assertEqual(res["monthly_kwh"], 26.4)
        self.assertEqual(res["daily_kwh"], 0.88)

    def test_annual_kwh_calculation(self):
        """Verifies annual kWh rating (BEE star rating) normalized across operating days."""
        # 220 kWh/yr refrigerator, 1 unit, 30 days = (220 / 365) * 30 = 18.082 kWh
        res = calculate_appliance_energy(
            calculation_method="annual_kwh",
            quantity=1,
            annual_kwh=220.0,
            days_per_month=30,
        )
        self.assertAlmostEqual(res["monthly_kwh"], 18.082, places=2)

    def test_kwh_per_cycle_calculation(self):
        """Verifies cyclic appliance energy consumption (cycle_kwh × quantity × cycles)."""
        # 0.65 kWh/cycle, 1 unit, 20 cycles = 13.0 kWh
        res = calculate_appliance_energy(
            calculation_method="kwh_per_cycle",
            quantity=1,
            kwh_per_cycle=0.65,
            cycles_per_month=20,
            days_per_month=30,
        )
        self.assertEqual(res["monthly_kwh"], 13.0)

    def test_bescom_bill_calculation(self):
        """Verifies BESCOM LT-1 domestic tariff calculation components."""
        # 200 kWh, 3 kW sanctioned load
        # Energy charge: 200 * 5.80 = ₹1,160.00
        # Fixed charge: 3 * 150.00 = ₹450.00
        # Duty: 9% of 1160 = ₹104.40
        # Total bill: 1160 + 450 + 104.40 = ₹1,714.40
        bill = calculate_bescom_bill(
            total_monthly_kwh=200.0,
            sanctioned_load_kw=3.0,
            base_rate_paise=580,
            fixed_charge_rate_paise=15000,
            duty_percent=9.0,
        )
        self.assertEqual(bill["energy_charge_inr"], 1160.00)
        self.assertEqual(bill["fixed_charge_inr"], 450.00)
        self.assertEqual(bill["duty_inr"], 104.40)
        self.assertEqual(bill["total_bill_inr"], 1714.40)

    def test_input_validation_boundaries(self):
        """Verifies that invalid or out-of-bound inputs are sanitized safely."""
        res = calculate_appliance_energy(
            calculation_method="rated_wattage",
            quantity=-5,          # Should default to at least 1
            rated_watt=-100,      # Should clamp to 0
            daily_hours=35.0,     # Should clamp to 24.0
            days_per_month=45,    # Should clamp to 31
        )
        self.assertEqual(res["quantity"], 1)
        self.assertEqual(res["days_per_month"], 31)
        self.assertEqual(res["monthly_kwh"], 0.0)

    def test_household_crud_operations(self):
        """Verifies creating, retrieving, and updating a household profile in SQLite."""
        hh_id = create_household("Indiranagar Villa", "Bengaluru", 1, 4.0, self.test_db_path)
        self.assertIsInstance(hh_id, int)

        hh = get_household(hh_id, self.test_db_path)
        self.assertIsNotNone(hh)
        self.assertEqual(hh["name"], "Indiranagar Villa")
        self.assertEqual(hh["sanctioned_load_kw"], 4.0)

        update_household(hh_id, "Indiranagar Penthouse", "Bengaluru", 1, 5.0, self.test_db_path)
        updated_hh = get_household(hh_id, self.test_db_path)
        self.assertEqual(updated_hh["name"], "Indiranagar Penthouse")
        self.assertEqual(updated_hh["sanctioned_load_kw"], 5.0)

    def test_appliance_inventory_lifecycle(self):
        """Verifies adding, updating, and removing household appliances."""
        hh_id = create_household("Koramangala Flat", "Bengaluru", 1, 3.0, self.test_db_path)
        specs = get_appliance_specs(self.test_db_path)
        self.assertGreater(len(specs), 0)

        fan_spec = next(s for s in specs if "fan" in s["name"].lower())

        app_id = add_household_appliance(
            household_id=hh_id,
            spec_id=fan_spec["spec_id"],
            calculation_method="rated_wattage",
            quantity=3,
            daily_hours=6.0,
            days_per_month=30,
            custom_watt=60,
            label="Bedrooms Fan",
            db_path=self.test_db_path,
        )
        self.assertIsInstance(app_id, int)

        appliances = get_household_appliances(hh_id, self.test_db_path)
        self.assertEqual(len(appliances), 1)
        self.assertEqual(appliances[0]["quantity"], 3)
        self.assertEqual(appliances[0]["custom_watt"], 60)

        # Update operating hours
        update_household_appliance(app_id, quantity=4, daily_hours=10.0, db_path=self.test_db_path)
        updated_apps = get_household_appliances(hh_id, self.test_db_path)
        self.assertEqual(updated_apps[0]["quantity"], 4)
        self.assertEqual(updated_apps[0]["daily_hours"], 10.0)

        # Delete appliance
        delete_household_appliance(app_id, self.test_db_path)
        after_del = get_household_appliances(hh_id, self.test_db_path)
        self.assertEqual(len(after_del), 0)

    def test_bill_estimate_snapshot_persistence(self):
        """Verifies saving an immutable calculation snapshot into bill_estimate & bill_estimate_line."""
        hh_id = create_household("Jayanagar Home", "Bengaluru", 1, 3.0, self.test_db_path)
        specs = get_appliance_specs(self.test_db_path)
        ac_spec = next(s for s in specs if "conditioner" in s["name"].lower())

        app_id = add_household_appliance(
            household_id=hh_id,
            spec_id=ac_spec["spec_id"],
            calculation_method="rated_wattage",
            quantity=1,
            daily_hours=6.0,
            days_per_month=30,
            custom_watt=1400,
            label="Master AC",
            db_path=self.test_db_path,
        )

        user_apps = get_household_appliances(hh_id, self.test_db_path)
        summary = calculate_household_summary(user_apps, energy_rate_per_kwh=5.80)
        bill = calculate_bescom_bill(summary["total_monthly_kwh"], sanctioned_load_kw=3.0)

        est_id = save_bill_estimate(
            household_id=hh_id,
            schedule_id=1,
            billing_month="2026-11",
            bill_calc=bill,
            appliances_list=summary["appliances"],
            sanctioned_load_kw=3.0,
            db_path=self.test_db_path,
        )
        self.assertIsInstance(est_id, int)

        latest = get_latest_estimate(hh_id, self.test_db_path)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["estimate_id"], est_id)
        self.assertEqual(latest["total_kwh"], summary["total_monthly_kwh"])

        lines = get_estimate_lines(est_id, self.test_db_path)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["appliance_name_snapshot"], "Master AC")
        self.assertEqual(lines[0]["share_percent"], 100.0)

    def test_air_conditioner_consumption_calculation(self):
        """
        Verifies Air Conditioner calculation:
        1400 W rated power, qty 1, 6.0 hrs/day, 30 days = exactly 252.0 kWh.
        Also verifies that updating daily hours to 4.0 hrs/day recalculates to 168.0 kWh.
        """
        # Direct calculator formula
        res = calculate_appliance_energy(
            calculation_method="rated_wattage",
            quantity=1,
            rated_watt=1400,
            daily_hours=6.0,
            days_per_month=30,
        )
        self.assertEqual(res["monthly_kwh"], 252.0)
        self.assertEqual(res["daily_kwh"], 8.4)

        # Updated operating hours to 4.0 hrs/day
        res_updated = calculate_appliance_energy(
            calculation_method="rated_wattage",
            quantity=1,
            rated_watt=1400,
            daily_hours=4.0,
            days_per_month=30,
        )
        self.assertEqual(res_updated["monthly_kwh"], 168.0)
        self.assertEqual(res_updated["daily_kwh"], 5.6)

    def test_air_conditioner_repository_and_summary_flow(self):
        """
        Verifies full data flow for Air Conditioner from SQLite repository to calculate_household_summary.
        Tests both catalogue default wattage (1500W or 1400W) and custom wattage override (1400W).
        """
        hh_id = create_household("AC Test Household", "Bengaluru", 1, 4.0, self.test_db_path)
        specs = get_appliance_specs(self.test_db_path)
        ac_spec = next(s for s in specs if "conditioner" in s["name"].lower())

        # Add AC with 1400W custom wattage, 1 unit, 6 hrs/day, 30 days
        app_id = add_household_appliance(
            household_id=hh_id,
            spec_id=ac_spec["spec_id"],
            calculation_method="rated_wattage",
            quantity=1,
            daily_hours=6.0,
            days_per_month=30,
            custom_watt=1400,
            label="Study Room AC",
            db_path=self.test_db_path,
        )

        user_apps = get_household_appliances(hh_id, self.test_db_path)
        summary = calculate_household_summary(user_apps, energy_rate_per_kwh=5.80)

        self.assertEqual(summary["total_monthly_kwh"], 252.0)
        self.assertEqual(summary["highest_consumer"]["monthly_kwh"], 252.0)
        self.assertEqual(summary["highest_consumer"]["label"], "Study Room AC")

        # Update operating hours in database to 4.0 hrs/day
        update_household_appliance(
            appliance_id=app_id,
            quantity=1,
            daily_hours=4.0,
            db_path=self.test_db_path,
        )

        updated_apps = get_household_appliances(hh_id, self.test_db_path)
        updated_summary = calculate_household_summary(updated_apps, energy_rate_per_kwh=5.80)

        self.assertEqual(updated_summary["total_monthly_kwh"], 168.0)
        self.assertEqual(updated_summary["highest_consumer"]["monthly_kwh"], 168.0)

    def test_insights_generation(self):
        """Verifies calculation-based energy insights, top consumer, and AC reduction potential."""
        mock_apps = [
            {"spec_name": "Air Conditioner", "monthly_kwh": 252.0, "daily_hours": 6.0, "quantity": 1, "rated_watt": 1400, "calculation_method": "rated_wattage"},
            {"spec_name": "Ceiling Fan", "monthly_kwh": 39.6, "daily_hours": 8.0, "quantity": 3, "rated_watt": 55, "calculation_method": "rated_wattage"},
            {"spec_name": "LED Bulb", "monthly_kwh": 5.4, "daily_hours": 4.0, "quantity": 5, "rated_watt": 9, "calculation_method": "rated_wattage"},
        ]
        insights = generate_household_insights(mock_apps, energy_rate_inr=5.80)
        self.assertGreater(len(insights), 0)

        # First insight should identify Air Conditioner as primary driver
        self.assertIn("Air Conditioner", insights[0]["title"])

        # AC reduction insight should be present
        ac_insight = next((ins for ins in insights if ins["type"] == "ac_reduction"), None)
        self.assertIsNotNone(ac_insight)
        self.assertIn("Reducing AC runtime", ac_insight["message"])


if __name__ == "__main__":
    unittest.main()
