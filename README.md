# Gujarat Industrial Estates & Land Intelligence Platform

An empirical econometrics web application and land intelligence system built with Flask, SQLite, and discrete step-function valuation engines for analyzing property dynamics, statutory allotment rates, and lifecycle appreciation across **312 GIDC and private industrial estates in Gujarat** over **27 fiscal years (FY 2000–01 to FY 2026–27)**.

---

## 🎯 Key Capabilities & Architecture

1. **Flask Interactive Web Portal (`app.py`)**:
   * **Executive Dashboard (`/`)**: High-level KPIs across 312 industrial parks, 33 districts, spatial distance buffers, and real-time empirical price evolution.
   * **Spatial GIS Map (`/map`)**: Interactive Leaflet GIS visualizer displaying all 312 estates with geocoded boundaries, district boundaries, and spatial proximity buffer rings (`<0.5km`, `0.5–1.5km`, `3–8km`).
   * **Difference-in-Differences Econometrics Studio (`/econometrics`)**: Dynamic OLS parameter estimation, pre/post anchor event studies ($T_0$), and control group benchmarking.
   * **Land Pricing & Statutory History (`/land-pricing-history`)**: Complete 27-year panel search and time-series visualization.
   * **Industrial Parks Directory (`/parks` & `/parks/<id>`)**: Comprehensive catalog of all 312 estates with registered anchor facilities (Tata Motors, Suzuki, Micron, Reliance, L&T, etc.) and chronological lifecycle timelines.
   * **Plot Dossier & Cadastral Valuation (`/plot-dossier/<id>`)**: Micro-level valuation waterfall integrating distance decay, road width, corner premiums, and infrastructure frontage.
   * **18 Core Relational Tables Export Hub (`/tables`)**: 1-click ZIP export and per-table CSV streaming with institutional metadata preambles and citation headers.

2. **Empirical 27-Year Panel Dataset (8,424 Records)**:
   * **Temporal Coverage**: 27 consecutive fiscal years (FY 2000–01 to FY 2026–27).
   * **Spatial Coverage**: 312 distinct GIDC industrial parks across all Gujarat districts.
   * **Ground Truth Governance**: Deconstructed from 24 official gazetted circulars with statutory step-function persistence. Zero synthetic interpolation, zero polynomial smoothing.

3. **1-to-1 Evidence Dossier Archive (`evidence_pdf_archive/`)**:
   * **25 Official Circular PDFs**: Complete repository of scanned and born-digital government notifications.
   * **Annual Evidence Dossiers (`evidence_pdf_archive/annual_evidence_by_year/`)**: Dedicated per-year CSV datasets and TXT institutional provenance dossiers linking each fiscal year directly to its primary circular PDF, official order date, and cryptographic SHA-256 digest.
   * **Master Annual Evidence Index**: Full tabular mapping in both CSV and Markdown formats.

4. **Publication-Grade Empirical Visualizations (`plots/`)**:
   * `01_gidc_key_clusters_27yr_price_evolution.png`: 27-year trajectory of Tier-1 industrial hubs (Sanand, Vapi, Ankleshwar, Naroda, Vatva, Halol, Jhagadia).
   * `02_step_function_persistence_vs_smoothing.png`: Contrast between empirical statutory persistence and artificial smoothing distortions.
   * `03_cross_district_gidc_appreciation.png`: Cross-district median appreciation across 2004, 2016, and 2026 anchors.
   * `04_all_312_estates_panel_distribution.png`: Panel distribution percentiles (P10, P25, Median, P75, P90, Max).
   * `gidc_empirical_price_explorer.html`: Searchable client-side SVG interactive dashboard.

5. **Automated Quality Gates & Test Suites**:
   * **Relational Unit Test Suite (`test_app.py`)**: 60 automated unit tests verifying routes, APIs, schema integrity, and zero-pollution baseline compliance.
   * **Anti-Synthetic Integrity Guardrail (`guardrails/dataset_integrity_guardrail.py`)**: Automated audit ensuring zero pseudo-random data generators, no stub files, and complete citation traceability.

---

## 🛠️ Repository Structure

```
.
├── app.py                      # Flask web application entrypoint & CLI commands
├── config.py                   # Environment and database configuration
├── database.py                 # SQLite connection manager & transactional helpers
├── models.py                   # High-level relational query models
├── data_loader.py              # Ingestion pipeline parsing CSVs into SQLite
├── test_app.py                 # Automated test suite (60 unit tests)
├── requirements.txt            # Python dependencies
├── did_engine.py               # Difference-in-Differences econometrics engine
├── econometric_advanced.py      # Spatial regression and decay modeling
├── land_intelligence.py        # Micro valuation waterfall & land analytics
├── plot_cadastral_engine.py    # Cadastral valuation engine
├── plot_decay_engine.py        # Distance decay engine
├── table_exporters.py          # Relational table exporter (18 tables)
├── exporters.py                # CSV and ZIP packaging utilities
├── provenance_system.py        # Cryptographic provenance registry
├── replication_suite.py        # Econometric replication verification
│
├── db/
│   ├── schema.sql              # Clean SQLite DDL schema (18 verified tables)
│   ├── init_schema.sql         # Database initialization script
│   ├── sqlite_schema.txt       # Schema documentation
│   └── industrial_estates.db   # Production SQLite database (8,424 panel rows)
│
├── data/                       # Curated relational CSV tables and metadata
│   ├── 16_industrial_land_price_history.csv  # Full 8,424-record panel
│   ├── 18_source_registry.csv                # Primary institutional citations
│   └── gujarat_01_*.csv ... gujarat_10_*.csv  # Core relational tables
│
├── evidence_pdf_archive/       # Government evidentiary records
│   ├── all_historical_circulars/             # 25 authentic circular PDFs
│   ├── annual_evidence_by_year/              # Per-year CSVs & TXT dossiers (2000–2027)
│   │   ├── FY_2000_01_allotment_rates.csv
│   │   ├── FY_2000_01_evidence_dossier.txt
│   │   ├── ...
│   │   ├── FY_2026_27_allotment_rates.csv
│   │   ├── FY_2026_27_evidence_dossier.txt
│   │   ├── MASTER_ANNUAL_EVIDENCE_INDEX.csv
│   │   └── MASTER_ANNUAL_EVIDENCE_INDEX.md
│   ├── scanned_pages_2004/                   # High-resolution scanned annexures
│   ├── COMPLETE_GIDC_HISTORICAL_CIRCULARS_INVENTORY.csv
│   └── EVIDENCE_VERIFICATION_REPORT.md
│
├── guardrails/
│   └── dataset_integrity_guardrail.py        # Zero-synthetic quality gate
│
├── plots/                      # High-resolution figures & interactive explorer
│   ├── 01_gidc_key_clusters_27yr_price_evolution.png
│   ├── 02_step_function_persistence_vs_smoothing.png
│   ├── 03_cross_district_gidc_appreciation.png
│   ├── 04_all_312_estates_panel_distribution.png
│   └── gidc_empirical_price_explorer.html
│
├── scripts/                    # Automated ingestion, plotting, and audit pipelines
│   ├── generate_annual_evidence_package.py   # Builds annual 1-to-1 evidence
│   ├── generate_empirical_price_plots.py     # Generates publication charts
│   ├── build_unified_ground_truth_pipeline.py# Full historical extraction
│   ├── extract_and_validate_2004_prices.py   # Specialized 2004 OCR pipeline
│   ├── download_official_pdfs.py             # Official circular fetcher
│   └── build_evidence_zip.py                 # Evidence distribution builder
│
├── spatial_map/                # Standalone interactive GIS map bundle
├── static/                     # CSS, Chart.js, and Leaflet scripts
└── templates/                  # Jinja2 HTML templates
```

---

## 🚀 Quickstart Guide

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/ecologictribe/indus.git
cd indus
pip install -r requirements.txt
```

### 2. Run the Web Application
```bash
python app.py
```
Open your browser at:
```
http://127.0.0.1:5000
```

### 3. Run Automated Unit Tests
```bash
python test_app.py
```
*Expected: 60/60 tests passing in ~1.5s.*

### 4. Run Dataset Integrity Guardrail
```bash
python guardrails/dataset_integrity_guardrail.py
```
*Expected: 0 violations across all Python, CSV, and PDF files.*

### 5. Generate Empirical Plots & Annual Evidence
```bash
# Generate high-resolution figures & HTML visualizer
python scripts/generate_empirical_price_plots.py

# Generate annual 1-to-1 CSV and TXT evidence dossiers
python scripts/generate_annual_evidence_package.py
```

---

## 📜 Empirical Methodology & Governance

* **Discrete Step-Function Persistence**: In accordance with administrative law and public circulars, land allotment rates remain constant at the governing board circular rate until an explicit revised circular is issued. No artificial interpolation or linear smoothing is applied.
* **Cryptographic Verification**: Every circular document has an associated SHA-256 digest recorded in the institutional provenance registry (`source_registry`).
* **Zero Synthetic Leakage**: All synthetic datasets, mock fixtures, and pseudo-random generators have been excised from the repository.

---

## ⚖️ License & Attribution

Published by the **Ecologic Tribe Research Initiative** & **Aplly.xyz**.
Derived from official public circulars issued by the **Gujarat Industrial Development Corporation (GIDC)**, Government of Gujarat.
