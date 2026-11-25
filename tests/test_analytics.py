"""
Unit Tests for Analytics Ingestion, Queries, and Visualizations.
Verifies idempotent ingestion of electricity_bill_dataset.csv, row count integrity,
query filtering, and chart generation.
"""

import sys
import unittest
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
from config.settings import CSV_PATH, DB_PATH
from modules.analytics.charts import (
    plot_avg_bill_by_city,
    plot_bill_distribution,
    plot_correlation_heatmap,
    plot_hours_vs_bill,
    plot_monthly_bill_trends,
    plot_tariff_distribution,
)
from modules.analytics.loader import import_csv_to_analytics, is_already_imported
from modules.analytics.queries import (
    get_city_summary,
    get_filter_options,
    get_monthly_trend,
    get_overview_metrics,
    load_filtered_readings,
)


class TestAnalyticsModule(unittest.TestCase):
    """Test suite for historical analytics data ingestion, queries, and charts."""

    @classmethod
    def setUpClass(cls):
        """Ensures the dataset is ingested once before running analytical tests."""
        cls.import_result = import_csv_to_analytics(CSV_PATH, DB_PATH)

    def test_import_row_count_and_status(self):
        """Verifies that exactly 45,345 records exist and import succeeds or confirms prior import."""
        self.assertIn(self.import_result["status"], ["success", "already_imported"])
        self.assertEqual(self.import_result["row_count"], 45345)

    def test_idempotent_import_prevents_duplicate_records(self):
        """Verifies that calling import_csv_to_analytics a second time returns already_imported."""
        second_result = import_csv_to_analytics(CSV_PATH, DB_PATH, force=False)
        self.assertEqual(second_result["status"], "already_imported")
        self.assertEqual(second_result["row_count"], 45345)

    def test_overview_metrics_calculation(self):
        """Verifies calculation of KPI overview metrics against known dataset audit values."""
        metrics = get_overview_metrics(DB_PATH)
        self.assertEqual(metrics["total_records"], 45345)
        self.assertEqual(metrics["total_cities"], 16)
        self.assertEqual(metrics["total_companies"], 32)
        self.assertTrue(metrics["motor_pump_always_zero"])
        self.assertGreater(metrics["avg_bill"], 4000)
        self.assertLess(metrics["avg_bill"], 5000)

    def test_filter_options_retrieval(self):
        """Verifies that filter options for cities, months, and companies are correctly populated."""
        options = get_filter_options(DB_PATH)
        self.assertEqual(len(options["cities"]), 16)
        self.assertEqual(len(options["months"]), 12)
        self.assertEqual(len(options["companies"]), 32)
        self.assertIn("Mumbai", options["cities"])
        self.assertIn("New Delhi", options["cities"])

    def test_filtered_query_loading(self):
        """Verifies that filtered data queries respect city and month filter selections."""
        df_filtered = load_filtered_readings(cities=["Mumbai"], months=[1, 2], db_path=DB_PATH)
        self.assertFalse(df_filtered.empty)
        self.assertTrue((df_filtered["city"] == "Mumbai").all())
        self.assertTrue(df_filtered["month"].isin([1, 2]).all())

    def test_city_and_monthly_summaries(self):
        """Verifies aggregation summaries by city and by month."""
        df = load_filtered_readings(cities=["Mumbai", "New Delhi"], db_path=DB_PATH)
        city_summary = get_city_summary(df)
        self.assertEqual(len(city_summary), 2)
        self.assertIn("avg_bill", city_summary.columns)

        monthly_trend = get_monthly_trend(df)
        self.assertFalse(monthly_trend.empty)
        self.assertIn("avg_bill", monthly_trend.columns)

    def test_chart_generation_functions(self):
        """Verifies that chart functions return valid Matplotlib Figure objects without error."""
        df = load_filtered_readings(cities=["Mumbai", "New Delhi"], db_path=DB_PATH)

        fig_city = plot_avg_bill_by_city(df)
        self.assertIsInstance(fig_city, plt.Figure)
        plt.close(fig_city)

        fig_trend = plot_monthly_bill_trends(df)
        self.assertIsInstance(fig_trend, plt.Figure)
        plt.close(fig_trend)

        fig_dist = plot_bill_distribution(df)
        self.assertIsInstance(fig_dist, plt.Figure)
        plt.close(fig_dist)

        fig_scatter = plot_hours_vs_bill(df)
        self.assertIsInstance(fig_scatter, plt.Figure)
        plt.close(fig_scatter)

        fig_tariff = plot_tariff_distribution(df)
        self.assertIsInstance(fig_tariff, plt.Figure)
        plt.close(fig_tariff)

        fig_corr = plot_correlation_heatmap(df)
        self.assertIsInstance(fig_corr, plt.Figure)
        plt.close(fig_corr)


if __name__ == "__main__":
    unittest.main()
