"""
Historical Electricity Dataset Loader.
Performs idempotent ingestion of electricity_bill_dataset.csv into the SQLite analytics table,
tracking file checksums in analytics_metadata to prevent duplicate imports on restart.
"""

import hashlib
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from config.settings import CSV_PATH, DB_PATH
from db.connection import get_db
from db.schema import init_db

# Expected 12 columns in source CSV
EXPECTED_COLUMNS = [
    "Fan",
    "Refrigerator",
    "AirConditioner",
    "Television",
    "Monitor",
    "MotorPump",
    "Month",
    "City",
    "Company",
    "MonthlyHours",
    "TariffRate",
    "ElectricityBill",
]

# Mapping to database snake_case columns
COLUMN_MAPPING = {
    "Fan": "fan",
    "Refrigerator": "refrigerator",
    "AirConditioner": "air_conditioner",
    "Television": "television",
    "Monitor": "monitor",
    "MotorPump": "motor_pump",
    "Month": "month",
    "City": "city",
    "Company": "company",
    "MonthlyHours": "monthly_hours",
    "TariffRate": "tariff_rate",
    "ElectricityBill": "electricity_bill",
}


def compute_file_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file for change-detection and idempotency."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_already_imported(csv_path: Path, db_path: Path = DB_PATH) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Checks analytics_metadata to determine if the CSV has already been ingested.
    Returns (already_imported, metadata_dict).
    """
    if not csv_path.exists():
        return False, None

    checksum = compute_file_sha256(csv_path)
    source_filename = csv_path.name

    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT meta_id, source_file, row_count, checksum, imported_at
            FROM analytics_metadata
            WHERE checksum = ? OR source_file = ?;
            """,
            (checksum, source_filename),
        )
        row = cursor.fetchone()
        if row:
            # Also verify readings actually exist in analytics_reading
            cursor.execute("SELECT COUNT(*) FROM analytics_reading WHERE meta_id = ?;", (row["meta_id"],))
            reading_count = cursor.fetchone()[0]
            if reading_count > 0:
                return True, dict(row)

    return False, None


def import_csv_to_analytics(
    csv_path: Path = CSV_PATH, db_path: Path = DB_PATH, force: bool = False
) -> Dict[str, Any]:
    """
    Idempotently imports electricity_bill_dataset.csv into the analytics_reading table.
    Validates column presence and record counts. Never modifies the source CSV file.
    """
    init_db(db_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Source CSV file not found at: {csv_path}")

    # Check for existing import unless force=True
    already_done, existing_meta = is_already_imported(csv_path, db_path)
    if already_done and not force:
        return {
            "status": "already_imported",
            "source_file": existing_meta["source_file"],
            "row_count": existing_meta["row_count"],
            "checksum": existing_meta["checksum"],
            "imported_at": existing_meta["imported_at"],
            "message": "Dataset has already been imported; skipped to prevent duplicates.",
        }

    # Load and validate with Pandas
    df = pd.read_csv(csv_path)

    missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Source CSV is missing required columns: {missing_cols}")

    # Prepare DataFrame for database insertion
    df_db = df[EXPECTED_COLUMNS].copy()
    df_db.rename(columns=COLUMN_MAPPING, inplace=True)

    checksum = compute_file_sha256(csv_path)
    source_name = csv_path.name
    row_count = len(df_db)

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # If forcing re-import, remove old metadata and readings
        if force:
            cursor.execute("DELETE FROM analytics_metadata WHERE source_file = ?;", (source_name,))

        # Insert metadata record
        cursor.execute(
            """
            INSERT INTO analytics_metadata (source_file, row_count, checksum)
            VALUES (?, ?, ?);
            """,
            (source_name, row_count, checksum),
        )
        meta_id = cursor.lastrowid

        # Attach meta_id column
        df_db["meta_id"] = meta_id

        # Reorder columns to match database schema
        db_cols = ["meta_id"] + list(COLUMN_MAPPING.values())
        records = df_db[db_cols].to_records(index=False).tolist()

        # Bulk insert records in single transaction
        insert_sql = f"""
        INSERT INTO analytics_reading (
            meta_id, fan, refrigerator, air_conditioner, television,
            monitor, motor_pump, month, city, company,
            monthly_hours, tariff_rate, electricity_bill
        ) VALUES ({', '.join(['?'] * len(db_cols))});
        """
        cursor.executemany(insert_sql, records)

    return {
        "status": "success",
        "source_file": source_name,
        "row_count": row_count,
        "checksum": checksum,
        "meta_id": meta_id,
        "message": f"Successfully imported {row_count:,} records into analytics_reading.",
    }


if __name__ == "__main__":
    result = import_csv_to_analytics()
    print("CSV Import Result:")
    for k, v in result.items():
        print(f"  {k}: {v}")
