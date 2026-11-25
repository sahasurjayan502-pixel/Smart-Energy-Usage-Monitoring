# Smart Energy Usage Monitor

> **Version 1.2 · Phase 0 & Phase 1 MVP**  
> A household-focused energy monitoring and estimation application built with Python and Streamlit.

---

## Overview

**Smart Energy Usage Monitor** is a modular desktop web application that helps Indian households:

- **Estimate** their monthly electricity bill based on the appliances they own and how often they use them.
- **Analyse** historical electricity consumption trends through an interactive data explorer.
- **Understand** where their energy spend goes, appliance by appliance, and act on data-driven savings insights.

The application runs entirely locally on your machine — no cloud services, no account required.

---

## Features

### My Household
- Create and manage one or more household profiles with sanctioned load and provider settings.
- Add appliances from a curated catalogue (Fans, ACs, Refrigerators, Lighting, Water Heaters, and more).
- Configure custom wattage, daily operating hours, and operating days per month per appliance.
- Automatically calculates monthly kWh consumption for each appliance using three methods:
  - **Rated Wattage** — `(W × qty × hours × days) / 1000`
  - **Annual kWh Rating** — BEE star-rated appliances (e.g. refrigerators)
  - **kWh per Cycle** — Cyclic appliances (e.g. washing machines, dishwashers)

### Energy Analytics
- Real-time household energy dashboard driven entirely by configured appliance data.
- **4 KPI Cards:** Monthly consumption (kWh), estimated monthly bill (₹), configured appliance count, and highest-consuming device.
- **Appliance Energy Donut Chart** — percentage share of total consumption.
- **Monthly Consumption Bar Chart** — appliance-by-appliance comparison.
- **BESCOM LT-1 Bill Breakdown** — energy charges, fixed meter charges, and 9% electricity duty.
- **Appliance-Wise Variable Cost Table** — per-appliance kWh, ₹ variable cost, and share %.
- **Actionable Energy-Saving Insights** — specific, calculation-based recommendations (never generic advice).

### Historical Dataset Explorer
- Interactive explorer of a 45,345-row electricity billing dataset from Indian cities.
- Filter by city, month, and electricity distribution company.
- KPI summary cards and Matplotlib/Seaborn visualisations of trends.

> ⚠️ **Data transparency note:** The external dataset's `ElectricityBill` column is mathematically derived from `MonthlyHours × TariffRate` in 100% of rows and does not represent genuine smart-meter readings. All limitations are disclosed inline in the application.

---

## Application Pages

| Page | Description |
|---|---|
| **Home** | Welcome portal with module cards linking to each section |
| **My Household** | Appliance configuration, usage settings, and household management |
| **Energy Analytics** | Live household consumption dashboard and bill breakdown |
| **Historical Dataset Explorer** | External dataset analysis and trend exploration |

---

## Project Structure

```
Smart_Energy_Usage_moniter/
├── app.py                              # Streamlit entry point & sidebar navigation
├── architecture.md                     # System architecture specification (v1.2)
├── requirements.txt                    # Python package dependencies
├── README.md                           # This file
│
├── config/
│   ├── __init__.py
│   └── settings.py                     # Centralized paths & domain constants
│
├── data/
│   ├── seeds/                          # Verified JSON seed data (appliance catalogue, tariffs)
│   └── raw/                            # Place electricity_bill_dataset.csv here (see below)
│
├── db/
│   ├── __init__.py
│   ├── connection.py                   # SQLite connection factory (FK + WAL pragma)
│   ├── schema.py                       # 12-table DDL with indexes and constraints
│   └── seeds.py                        # Idempotent seed loader
│
├── modules/
│   ├── analytics/
│   │   ├── charts.py                   # Matplotlib/Seaborn chart builders
│   │   ├── loader.py                   # Idempotent CSV ingestion with SHA-256 dedup
│   │   └── queries.py                  # Analytical SQL queries and aggregations
│   └── estimator/
│       ├── calculator.py               # Multi-method energy & bill calculation engine
│       ├── charts.py                   # Appliance chart builders (donut, bar)
│       ├── insights.py                 # Calculation-based energy-saving insight generator
│       └── repository.py              # SQLite CRUD — households, appliances, estimates
│
├── pages/
│   ├── 1_My_Household.py               # Household & appliance configuration UI
│   ├── 2_Energy_Analytics.py           # Personal energy dashboard
│   └── 3_Historical_Dataset_Explorer.py # External dataset explorer
│
└── tests/
    ├── test_analytics.py               # Ingestion, query, and chart tests
    ├── test_estimator.py               # Calculator, repository, and insights tests
    └── test_schema.py                  # Schema integrity and constraint tests
```

---

## Database Schema (12 Tables)

The application auto-initialises an SQLite database (`data/energy_monitor.db`) on first run. The database is **not committed to version control** — it is generated from schema and seed scripts.

| Table | Purpose |
|---|---|
| `appliance_category` | Device categories (Cooling, Lighting, Kitchen, etc.) |
| `appliance_spec` | Standard appliance catalogue with power ratings and BEE data |
| `tariff_provider` | Electricity distribution companies (e.g. BESCOM) |
| `tariff_category` | Consumer categories (e.g. LT-1 Domestic) |
| `tariff_schedule` | Active tariff versions with energy rate and fixed charge in paise |
| `household` | User household profiles |
| `household_appliance` | Per-household appliance inventory with custom overrides |
| `bill_estimate` | Immutable billing calculation snapshots |
| `bill_estimate_line` | Line-item detail per appliance per estimate |
| `analytics_reading` | External dataset records (isolated, no FK to households) |
| `import_log` | CSV ingestion audit log with SHA-256 hash |
| `import_log_detail` | Per-row import details |

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### 1. Clone the Repository

```bash
git clone https://github.com/sahasurjayan502-pixel/Smart-Energy-Usage-Monitoring.git
cd Smart-Energy-Usage-Monitoring
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Add the Historical Dataset

The historical electricity dataset is not included in this repository due to its size and redistribution licensing. To enable the Historical Dataset Explorer:

1. Download `electricity_bill_dataset.csv` from [Kaggle](https://www.kaggle.com) (search: "Indian Electricity Bill Dataset").
2. Place it in the project root **or** in `data/raw/electricity_bill_dataset.csv`.
3. The application will auto-detect and ingest it on first launch.

> The dataset is **not required** to use My Household or Energy Analytics — those pages run entirely from the SQLite database.

### 4. Run Tests

```bash
python -m pytest tests/ -v
```

All 23 tests should pass.

### 5. Launch the Application

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

---

## Tariff Configuration (BESCOM LT-1 · FY 2026–27)

The default tariff constants used in BESCOM LT-1 billing calculations:

| Parameter | Value |
|---|---|
| Base energy charge | ₹5.80 / kWh (580 paise/kWh) |
| Fixed meter charge | ₹150.00 / kW / month |
| Electricity duty | 9% on energy charges |
| Gruha Jyothi ceiling | 200 kWh/month (200 units free for eligible households) |

> Gruha Jyothi subsidy calculations are **deferred in the MVP** pending KERC settlement circular verification. Entitlement indicators are shown informally.

---

## Design Principles

1. **Privacy first** — All data stays on your machine. No network calls, no telemetry.
2. **Transparent calculations** — Every kWh figure and ₹ amount is derived by formula, not hardcoded.
3. **Data integrity** — SQLite WAL mode, foreign key enforcement, cascade/restrict constraints.
4. **Honest data disclosures** — Limitations of external datasets are stated inline, not hidden.
5. **Modular architecture** — Analytics and estimator are fully decoupled modules.

---

## Tech Stack

| Component | Technology |
|---|---|
| UI Framework | [Streamlit](https://streamlit.io) 1.62+ |
| Database | SQLite (via Python `sqlite3`) |
| Visualisation | Matplotlib, Seaborn |
| Data Processing | Pandas, NumPy |
| Testing | unittest, pytest |
| Language | Python 3.10+ |

---

## Planned Features (Future Phases)

- **Phase 2:** ESP32 / IoT smart meter integration for live readings
- **Phase 3:** Bill history timeline, monthly comparison reports
- **Phase 4:** Multi-household management and sharing
- **Phase 5:** Tariff comparison across Indian DISCOMs
- **Phase 6:** Export to PDF / Excel

---

## License

This project is provided for personal and educational use. The external dataset and PDF tariff document, if present locally, retain their original licenses and are not redistributed in this repository.

---

## Author

Developed as a personal energy monitoring MVP.  
Architecture specification: [`architecture.md`](architecture.md) · Version 1.2
