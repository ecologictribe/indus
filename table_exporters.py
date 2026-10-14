import io
import csv
import zipfile
import datetime
from database import get_db, query_db

TABLE_REGISTRY = {
    "states": {
        "order": 1,
        "display_name": "States Master",
        "description": "Spatial root entity representing the State jurisdiction.",
        "data_source": "Census of India / Government of Gujarat official administrative division code registry.",
        "primary_key": "state_id",
        "foreign_keys": "None (Root Entity)",
        "column_descriptions": {
            "state_id": "Primary key identifier",
            "state_name": "Full official name of state (Gujarat)",
            "state_code": "ISO/Census 2-letter state abbreviation code ('GJ')"
        }
    },
    "districts": {
        "order": 2,
        "display_name": "Districts Master (32 Districts)",
        "description": "Second-tier administrative division encompassing all industrial districts in Gujarat.",
        "data_source": "Revenue Department, Government of Gujarat & GIDC Divisional Office geographical hierarchy.",
        "primary_key": "district_id",
        "foreign_keys": "state_id -> states(state_id)",
        "column_descriptions": {
            "district_id": "Primary key identifier",
            "state_id": "Foreign key reference to states table",
            "district_name": "Official district name (e.g., Ahmedabad, Bharuch, Surat, Vadodara)",
            "census_code": "Census of India district identifier code"
        }
    },
    "subdistricts_talukas": {
        "order": 3,
        "display_name": "Subdistricts & Talukas (250 Talukas)",
        "description": "Tehsils and Talukas within each district hosting industrial estates.",
        "data_source": "Gujarat Land Revenue Code, Taluka Panchayat administrative records, and GIDC regional maps.",
        "primary_key": "taluka_id",
        "foreign_keys": "district_id -> districts(district_id)",
        "column_descriptions": {
            "taluka_id": "Primary key identifier",
            "district_id": "Foreign key reference to districts table",
            "taluka_name": "Official Taluka/Subdistrict name (e.g., Sanand, Ankleshwar, Choryasi, Bavla)"
        }
    },
    "neighborhoods_jurisdictions": {
        "order": 4,
        "display_name": "Neighborhoods & Tax Jurisdictions",
        "description": "Local municipal zones, village panchayats, and tax jurisdictions surrounding industrial estates.",
        "data_source": "Urban Development Authorities (AUDA, VUDA, SUDA), Municipal Tax Records, and GIDC statutory notified zones.",
        "primary_key": "neighborhood_id",
        "foreign_keys": "taluka_id -> subdistricts_talukas(taluka_id)",
        "column_descriptions": {
            "neighborhood_id": "Primary key identifier",
            "taluka_id": "Foreign key reference to talukas table",
            "neighborhood_name": "Neighborhood or jurisdiction label",
            "tax_jurisdiction_code": "Local statutory property tax assessment code",
            "is_gated_community": "Binary indicator (1 = Planned/Gated layout, 0 = Unplanned perimeter colony)"
        }
    },
    "industrial_parks": {
        "order": 5,
        "display_name": "Industrial Parks & GIDC Estates (312 Estates)",
        "description": "Comprehensive catalog of all 312 GIDC government industrial estates and sanctioned private industrial parks/SEZs across Gujarat.",
        "data_source": "GIDC Official Portal (gidc.gujarat.gov.in), Gujarat State Industrial Policy (2015/2020), Sanctioned Private Industrial Parks under Govt. Resolution (G.R. dated 21/04/2015), and OpenStreetMap spatial geocoding.",
        "primary_key": "park_id",
        "foreign_keys": "taluka_id -> subdistricts_talukas(taluka_id)",
        "column_descriptions": {
            "park_id": "Primary key identifier",
            "taluka_id": "Foreign key reference to subdistricts_talukas",
            "park_name": "Official estate or park title",
            "authority_type": "GIDC (Government) vs Private SEZ/Park",
            "sector_category": "Industry focus (Auto, Chemical/Petro, Textile, Electronics/Tech, General Engineering)",
            "total_area_acres": "Total developed land area in acres",
            "planning_type": "Modern Grade-A Regulated vs Legacy Heavy Industry",
            "notification_year": "Year of official state gazette notification or approval",
            "has_cetp": "Common Effluent Treatment Plant status (1 = Active Operational, 0 = None / Independent ETP)",
            "latitude": "WGS84 centroid latitude coordinate",
            "longitude": "WGS84 centroid longitude coordinate",
            "address": "Postal address and location descriptor",
            "phone": "Divisional office or estate contact phone number",
            "email": "Administrative contact email address",
            "notes": "State sanctioning notes, area in hectares, and approved sectors",
            "source": "Primary documentary source attribution"
        }
    },
    "anchor_facilities": {
        "order": 6,
        "display_name": "Anchor Facilities & Mega Plants",
        "description": "Major anchor manufacturing facilities, OEM plants, and tier-0 industrial enterprises.",
        "data_source": "Vibrant Gujarat Global Summit MoUs, Comptroller and Auditor General (CAG) audit reports on industrial development, Environmental Clearance DPR filings, and corporate press releases.",
        "primary_key": "anchor_id",
        "foreign_keys": "park_id -> industrial_parks(park_id)",
        "column_descriptions": {
            "anchor_id": "Primary key identifier",
            "park_id": "Foreign key reference to industrial_parks",
            "company_name": "Name of anchor corporate enterprise (e.g. Tata Motors, Suzuki, Micron, Reliance, L&T)",
            "industry_type": "Manufacturing industry classification",
            "proposed_investment_inr": "Proposed capital investment in INR Crores",
            "actual_investment_inr": "Audited actual capital expenditure in INR Crores",
            "commencement_date": "Commercial production start date",
            "estimated_employment": "Direct workforce headcount created"
        }
    },
    "park_lifecycle_events": {
        "order": 7,
        "display_name": "Park Lifecycle Milestones (DiD Windows)",
        "description": "Chronological development milestones defining Pre/Post treatment event windows for econometric estimation.",
        "data_source": "State Gazette Notifications, GIDC land acquisition awards, Chief Inspector of Factories commissioning permits, and GPCB compliance filings.",
        "primary_key": "event_id",
        "foreign_keys": "park_id -> industrial_parks(park_id)",
        "column_descriptions": {
            "event_id": "Primary key identifier",
            "park_id": "Foreign key reference to industrial_parks",
            "event_type": "Milestone type (Policy Announcement, Land Acquisition, Anchor Operational, Ancillary Active, CETP Upgrade)",
            "event_date": "Official milestone calendar date",
            "event_year": "Calendar year of milestone",
            "description": "Institutional description of milestone achievement"
        }
    },
    "park_annual_metrics": {
        "order": 8,
        "display_name": "Park Annual Operational & Environmental Metrics",
        "description": "Multi-year panel tracking economic occupancy, built-up FSI utilization, CEPI environmental pollution scores, and PM2.5 levels.",
        "data_source": "Gujarat Pollution Control Board (GPCB) Comprehensive Environmental Pollution Index (CEPI) monitoring reports, GIDC annual physical audits, and Central Pollution Control Board (CPCB) air quality archives.",
        "primary_key": "metric_id",
        "foreign_keys": "park_id -> industrial_parks(park_id)",
        "column_descriptions": {
            "metric_id": "Primary key identifier",
            "park_id": "Foreign key reference to industrial_parks",
            "assessment_year": "Fiscal audit observation year",
            "occupancy_rate_pct": "Percentage of developed plots under active operation (%)",
            "avg_fsi_utilized_pct": "Ratio of consumed Floor Space Index to permitted buildable FSI (%)",
            "active_units_count": "Total operating factory sheds and registered MSME units",
            "cepi_score": "Comprehensive Environmental Pollution Index (Scores >= 70 indicate critically polluted clusters)",
            "pm2_5_level": "Average ambient particulate matter concentration (ug/m3)"
        }
    },
    "clean_commercial_nodes": {
        "order": 9,
        "display_name": "Clean Commercial Benchmark Nodes",
        "description": "IT parks, financial SEZs, and regional shopping nodes serving as the clean control group to disentangle industrial stigma from general commercial noise.",
        "data_source": "GIFT City SEZ Authority, Commercial Real Estate Registry (RERA Gujarat), SG Highway High-Street Planning Audits, and Taylor et al. econometric methodology.",
        "primary_key": "node_id",
        "foreign_keys": "taluka_id -> subdistricts_talukas(taluka_id)",
        "column_descriptions": {
            "node_id": "Primary key identifier",
            "taluka_id": "Foreign key reference to subdistricts_talukas",
            "node_name": "Commercial node title (e.g. GIFT City Tech Node, SG Highway Corporate Hub)",
            "category": "Classification (IT/Financial SEZ, Commercial Complex, Retail High-Street)",
            "establishment_year": "Year node commenced commercial operations",
            "latitude": "WGS84 centroid latitude coordinate",
            "longitude": "WGS84 centroid longitude coordinate"
        }
    },
    "properties": {
        "order": 10,
        "display_name": "Properties & Parcel Spatial Attributes",
        "description": "Tracked residential and commercial land parcels, apartments, and houses across discrete spatial distance buffers.",
        "data_source": "Sub-Registrar Offices (Revenue Department), Gujarat Real Estate Regulatory Authority (GUJRERA) project filings, and GIS Hedonic buffer radial calculations.",
        "primary_key": "property_id",
        "foreign_keys": "neighborhood_id -> neighborhoods_jurisdictions, nearest_park_id -> industrial_parks, nearest_clean_commercial_id -> clean_commercial_nodes",
        "column_descriptions": {
            "property_id": "Primary key identifier",
            "neighborhood_id": "Foreign key reference to neighborhood jurisdiction",
            "nearest_park_id": "Foreign key reference to nearest industrial park",
            "nearest_clean_commercial_id": "Foreign key reference to nearest clean commercial benchmark",
            "property_type": "Parcel typology (Residential Apartment, Single Family Detached, Plot, Commercial Frontage)",
            "lot_size_sqm": "Plot footprint size in square meters",
            "built_up_area_sqm": "Covered usable built-up area in square meters",
            "bedrooms": "Number of bedrooms",
            "bathrooms": "Number of bathrooms",
            "age_at_sale_years": "Structure age in years at point of transaction",
            "distance_to_park_km": "Euclidean spatial distance to industrial park boundary (km)",
            "distance_buffer_bin": "Distance gradient (<0.5km = Proximity Drag, 0.5-1.5km = Intermediate, 3-8km = Sweet Spot, Control >10km, Clean Commercial <0.3km)",
            "distance_to_clean_commercial_km": "Distance to clean commercial benchmark node (km)",
            "distance_to_highway_km": "Distance to nearest National/State Highway (km)",
            "distance_to_urban_center_km": "Distance to district urban center / municipal core (km)"
        }
    },
    "property_transactions": {
        "order": 11,
        "display_name": "Property Transactions & Pricing Panel (4,000 Sales)",
        "description": "Multi-year micro-level sale observations tracking real open-market prices against registered statutory circle rates (Jantar) from 2012 to 2025.",
        "data_source": "Inspector General of Registration (IGR Gujarat) stamped transaction registry, Ready Reckoner / Jantar annual rate sheets (2012–2025), and National Housing Bank (NHB) RESIDEX verification.",
        "primary_key": "transaction_id",
        "foreign_keys": "property_id -> properties(property_id)",
        "column_descriptions": {
            "transaction_id": "Primary key identifier",
            "property_id": "Foreign key reference to properties table",
            "sale_date": "Registered transaction date (YYYY-MM-DD)",
            "sale_year": "Transaction calendar year (2012–2025)",
            "sale_quarter": "Transaction fiscal quarter (Q1-Q4)",
            "market_transaction_price": "Actual buyer-seller market clearing value (INR)",
            "price_per_sqm": "Market rate per square meter (INR/sqm)",
            "registered_circle_rate_sqm": "Statutory government valuation rate (Jantar / Ready Reckoner) in INR/sqm",
            "circle_to_market_ratio": "Ratio of official circle rate to market price (registered_circle_rate / price_per_sqm)",
            "is_repeat_sale": "1 if property sold multiple times across panel window, 0 otherwise",
            "is_arms_length": "1 if verified standard market transaction, 0 if distress/related-party sale"
        }
    },
    "did_panel_designations": {
        "order": 12,
        "display_name": "Difference-in-Differences (DiD) Variable Matrix",
        "description": "Econometric treatment, control, and event-study interaction term matrix formatted for estimation.",
        "data_source": "Econometric formulation based on Taylor et al. spatial gradient methodology and Devanshu Arora Difference-in-Differences research specification.",
        "primary_key": "designation_id",
        "foreign_keys": "transaction_id -> property_transactions(transaction_id)",
        "column_descriptions": {
            "designation_id": "Primary key identifier",
            "transaction_id": "Foreign key reference to property_transactions table",
            "treatment_group": "Econometric group designation",
            "lifecycle_phase_at_sale": "Lifecycle phase at sale (Phase_0_Baseline, Phase_1_Announcement, Phase_2_Anchor_Commissioned, Phase_3_Active_Ancillary)",
            "is_treated": "Binary treatment indicator (1 = Treated Industrial Buffer, 0 = Far Control / Clean Benchmark)",
            "is_post_event": "Binary post-event indicator (1 = Post Anchor Commissioning >= 2018, 0 = Pre-Event)",
            "did_interaction_term": "Core DiD Beta Estimator Interaction: (is_treated * is_post_event)",
            "years_since_event": "Event-study relative time index (j = sale_year - 2018)"
        }
    },
    "intelligence_sources": {
        "order": 14,
        "display_name": "Intelligence Provenance Sources (Tier 1 to 8 Registry)",
        "description": "Hierarchical multi-channel document and evidentiary provenance registry tracking official GIDC circulars, government gazettes, auction notices, layout maps, and corporate filings.",
        "data_source": "GIDC Head Office Circular Archives (Gandhinagar), Gujarat Government Gazette, Industries Commissionerate, and iNDEXTb.",
        "primary_key": "source_id",
        "foreign_keys": "None (Evidentiary Root Table)",
        "column_descriptions": {
            "source_id": "Primary key identifier",
            "source_type": "Document typology (Official GIDC Circular, Gazette Resolution, Tender / Auction DPR, Layout Map, Corporate Plant Filings)",
            "tier_level": "Evidentiary hierarchy tier (Tier 1: Official GIDC Archive -> Tier 8: News / Directories)",
            "document_name": "Official title or circular reference code",
            "source_url": "Direct portal URL or official PDF download link",
            "publication_date": "Original publication or gazette date",
            "retrieval_date": "Date ingested and verified by data intelligence pipeline",
            "authority": "Statutory issuing authority (GIDC, Industries Commissionerate, MoEFCC)",
            "reliability": "Data confidence rating (HIGH, MEDIUM, LOW)",
            "checksum": "SHA-256 cryptographic content digest"
        }
    },
    "estate_aliases_master": {
        "order": 15,
        "display_name": "Estate Aliases & Canonical Resolution Master",
        "description": "Cross-reference entity resolution mapping canonical estate names to historical designations, former phase titles, and GIDC regional administrative codes.",
        "data_source": "GIDC Land Allotment Regulations, Historical Gazette Orders, and Revenue Department Village Survey Indexes.",
        "primary_key": "alias_id",
        "foreign_keys": "park_id -> industrial_parks(park_id)",
        "column_descriptions": {
            "alias_id": "Primary key identifier",
            "park_id": "Foreign key reference to industrial_parks",
            "canonical_name": "Standardized primary estate title",
            "historical_name": "Historical or alternate documentation title",
            "district_name": "District jurisdiction",
            "taluka_name": "Taluka / Tehsil jurisdiction",
            "phase": "Specific development phase (Phase-I, Phase-II Bol, MSME Park, PCPIR Zone)",
            "parent_estate": "Parent industrial estate",
            "former_name": "Previous historical name prior to expansion or renaming",
            "gidc_code": "Official GIDC internal administrative estate code"
        }
    },
    "industrial_land_price_history": {
        "order": 16,
        "display_name": "Historical Land Allotment Price Archive (2000–2026/27)",
        "description": "Multi-decade statutory land allotment and revision time-series tracking official GIDC circular rates, e-auction values, and market price benchmarks from FY 2000–01 to FY 2026–27 across all industrial estates.",
        "data_source": "GIDC Official Allotment Price Archives (FY 2000–01 through FY 2026–27), Annual Circulars, and Saturated Estate Auction Notices.",
        "primary_key": "price_history_id",
        "foreign_keys": "park_id -> industrial_parks(park_id), source_id -> intelligence_sources(source_id)",
        "column_descriptions": {
            "price_history_id": "Primary key identifier",
            "park_id": "Foreign key reference to industrial_parks",
            "financial_year": "Indian Fiscal Year of statutory effectiveness (e.g., 2000-01, 2016-17, 2026-27)",
            "calendar_year": "Gregorian starting calendar year",
            "price_type": "Economic pricing classification (ORIGINAL_ALLOTMENT_PRICE, REVISED_ALLOTMENT_PRICE, AUCTION_PRICE, MARKET_RESALE_PRICE)",
            "price_per_sqm": "Statutory land rate per square meter (INR/sqm)",
            "revision_reason": "Institutional reason for price revision (Infrastructure development, Land acquisition cost, Development expenditure, Market review, Estate saturation)",
            "effective_from": "Statutory starting validity date",
            "effective_to": "Statutory expiry date",
            "source_id": "Foreign key reference to intelligence_sources table",
            "source_document": "Document title and circular number",
            "source_url": "Direct official portal URL",
            "confidence": "Data verification level (HIGH, MEDIUM, LOW)"
        }
    },
    "industrial_plots": {
        "order": 17,
        "display_name": "Industrial Plots Micro Inventory & Cadastral Attributes",
        "description": "Granular plot-by-plot spatial inventory detailing individual parcel dimensions, MSME vs Large categorization, allocation status, road widths, corner plot indicators, and company occupants.",
        "data_source": "GIDC Cadastral Layout Plans, Engineering Division GIS Maps, Investor Allotment DPRs, and GUJRERA Commercial Filings.",
        "primary_key": "plot_id",
        "foreign_keys": "park_id -> industrial_parks(park_id), source_id -> intelligence_sources(source_id)",
        "column_descriptions": {
            "plot_id": "Primary key identifier (e.g., PLOT-001-005)",
            "park_id": "Foreign key reference to industrial_parks",
            "plot_number": "Physical cadastral plot number within estate",
            "plot_area_sqm": "Plot footprint size in square meters",
            "plot_area_sqft": "Plot footprint size in square feet",
            "plot_type": "Land-use zoning (Industrial, Logistics/Warehousing, Commercial Utility)",
            "category": "Scale classification (MSME, General Engineering, Large Scale, Mega OEM)",
            "status": "Allotment status (Available, Allocated, Occupied, Reserved, Under Auction)",
            "allotment_price_sqm": "Base allotment price per square meter (INR/sqm)",
            "total_allotment_value": "Total statutory plot acquisition valuation (INR)",
            "road_width_m": "Frontage access road width in meters (12m, 18m, 24m, 30m)",
            "is_corner_plot": "Binary flag (1 = Corner plot with dual frontage, 0 = Standard mid-row plot)",
            "frontage_m": "Linear road frontage in meters",
            "allotment_date": "Date plot was officially allotted (YYYY-MM-DD)",
            "company_name": "Corporate occupant or enterprise entity",
            "industry_subsector": "Specific manufacturing or warehousing activity",
            "source_id": "Foreign key reference to intelligence_sources table",
            "confidence": "Data verification level (HIGH, MEDIUM, LOW)"
        }
    },
    "source_registry": {
        "order": 18,
        "display_name": "Master Source Registry & Local Source Archive",
        "description": "Central auditable registry tracking every source document, circular, government resolution, environmental audit, and cadastral survey map used in the research, retaining both original URLs and local archive paths with cryptographic SHA-256 hashes.",
        "data_source": "GIDC Head Office, Industries Commissionerate, CPCB, GPCB, Revenue Department, and Inspector General of Registration Gujarat.",
        "primary_key": "source_id",
        "foreign_keys": "None (Primary Master Registry)",
        "column_descriptions": {
            "source_id": "Unique immutable source identifier (e.g., SRC-GIDC-2026-001)",
            "organisation": "Issuing or regulatory organisation",
            "source_title": "Official title or description of source document",
            "source_type": "Format type (PDF, CSV, Gazette Resolution, Engineering Plan, Report)",
            "publication_date": "Original publication date (YYYY-MM-DD)",
            "retrieval_date": "Audit download / ingestion date (YYYY-MM-DD)",
            "original_url": "Permanent original external statutory URL",
            "local_path": "Deterministically structured local file archive path",
            "local_filename": "Locally preserved file name",
            "file_hash": "Cryptographic SHA-256 file checksum for tamper evidence",
            "file_size": "Preserved file size in bytes",
            "version": "Document revision or version number",
            "language": "Source language (English, Gujarati)",
            "source_status": "Current status (archived, unavailable, active, changed)",
            "failure_reason": "Explanation if source is unavailable or restricted",
            "extraction_status": "Data extraction status (processed, pending, failed)",
            "extraction_method": "Method used to extract facts (PDF table extraction, OCR, etc.)",
            "reliability": "Statutory hierarchy and authority classification",
            "notes": "Contextual research notes and statutory applicability"
        }
    },
    "data_provenance": {
        "order": 19,
        "display_name": "Value-Level Data Provenance & Evidence Traceability",
        "description": "Fine-grained auditable evidence linking specific extracted figures, land allotment prices, environmental CEPI benchmarks, and plot dimensions back to the exact source document, page, table, row, and verbatim supporting text excerpt.",
        "data_source": "Cross-referenced extraction from source_registry documents.",
        "primary_key": "provenance_id",
        "foreign_keys": "source_id -> source_registry(source_id)",
        "column_descriptions": {
            "provenance_id": "Surrogate primary key for provenance record",
            "entity_type": "Database table / entity type (industrial_plots, industrial_land_price_history, etc.)",
            "entity_id": "Specific record identifier or primary key in target entity",
            "field_name": "Exact database column / attribute name being proven",
            "extracted_value": "Raw extracted numerical or textual datum",
            "normalized_value": "Standardized canonical value with units",
            "source_id": "Foreign key reference to source_registry master",
            "source_location": "Precise location within source (Page number, Table, Schedule, Row)",
            "source_excerpt": "Verbatim quote or textual excerpt supporting the value",
            "extraction_method": "Extraction pipeline method",
            "extraction_date": "Date value was extracted (YYYY-MM-DD)",
            "confidence": "Evidence confidence level (HIGH, MEDIUM, LOW)",
            "verified": "Binary verification indicator (1 = Verified, 0 = Pending)",
            "verified_by": "Verifying auditor or research role",
            "notes": "Additional provenance and context notes"
        }
    }
}

def get_all_tables_info():
    """Returns metadata and row counts for all 19 tables."""
    conn = get_db()
    cursor = conn.cursor()
    
    tables_info = []
    # Sort by defined schema order
    sorted_tables = sorted(TABLE_REGISTRY.items(), key=lambda x: x[1]["order"])
    
    for table_name, meta in sorted_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [c[1] for c in cursor.fetchall()]
        
        tables_info.append({
            "order": meta["order"],
            "table_name": table_name,
            "display_name": meta["display_name"],
            "description": meta["description"],
            "data_source": meta["data_source"],
            "primary_key": meta["primary_key"],
            "foreign_keys": meta["foreign_keys"],
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns
        })
        
    return tables_info

def generate_table_csv(table_name):
    """
    Generates CSV content for a single table with rich metadata header preamble,
    explicitly citing the Data Source, collection methodology, schema, and timestamps.
    """
    if table_name not in TABLE_REGISTRY:
        return None, None
        
    meta = TABLE_REGISTRY[table_name]
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Get column names
    col_names = [description[0] for description in cursor.description]
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Metadata Header Preamble
    writer.writerow(["# =============================================================================="])
    writer.writerow(["# GUJARAT INDUSTRIAL ESTATES PROPERTY DYNAMICS STUDY"])
    writer.writerow(["# ------------------------------------------------------------------------------"])
    writer.writerow([f"# Table Name: {table_name} ({meta['display_name']})"])
    writer.writerow([f"# Table Order: Module {meta['order']} of {len(TABLE_REGISTRY)} Core Schema Tables"])
    writer.writerow([f"# Total Records: {len(rows)} rows"])
    writer.writerow([f"# Export Timestamp (UTC): {datetime.datetime.utcnow().isoformat()}Z"])
    writer.writerow([f"# DATA SOURCE: {meta['data_source']}"])
    writer.writerow([f"# Description: {meta['description']}"])
    writer.writerow([f"# Primary Key: {meta['primary_key']}"])
    writer.writerow([f"# Foreign Key Constraints: {meta['foreign_keys']}"])
    writer.writerow(["# ------------------------------------------------------------------------------"])
    writer.writerow(["# COLUMN DEFINITIONS:"])
    for col, desc in meta["column_descriptions"].items():
        writer.writerow([f"#   * {col}: {desc}"])
    writer.writerow(["# =============================================================================="])
    writer.writerow([])
    
    # Header Row
    writer.writerow(col_names)
    
    # Data Rows
    for row in rows:
        writer.writerow(list(row))
        
    filename = f"{meta['order']:02d}_{table_name}.csv"
    return output.getvalue(), filename

def generate_all_tables_zip():
    """
    Packs all Core Database Tables into individual CSV files with rich metadata preambles,
    plus an inclusive README_DATA_SOURCES.md manifest.
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Generate and add CSV for each table
        sorted_tables = sorted(TABLE_REGISTRY.items(), key=lambda x: x[1]["order"])
        
        manifest_lines = [
            "# Gujarat Industrial Estates Property Dynamics Study",
            f"## {len(TABLE_REGISTRY)} Core Database Tables Export Archive",
            "",
            f"**Export Generated (UTC):** {datetime.datetime.utcnow().isoformat()}Z",
            "**Jurisdiction:** State of Gujarat, India",
            "**Empirical Window:** 2012 – 2025 Panel",
            "",
            "---",
            "",
            "### Master Table Registry & Data Sources",
            ""
        ]
        
        for table_name, meta in sorted_tables:
            csv_content, filename = generate_table_csv(table_name)
            zip_file.writestr(filename, csv_content)
            
            # Append to manifest
            manifest_lines.append(f"#### {meta['order']:02d}. `{filename}` ({table_name})")
            manifest_lines.append(f"- **Display Title:** {meta['display_name']}")
            manifest_lines.append(f"- **Description:** {meta['description']}")
            manifest_lines.append(f"- **PRIMARY DATA SOURCE:** {meta['data_source']}")
            manifest_lines.append(f"- **Primary Key:** `{meta['primary_key']}`")
            manifest_lines.append(f"- **Relational Keys:** `{meta['foreign_keys']}`")
            manifest_lines.append("")
            
        manifest_lines.extend([
            "---",
            "",
            "### Usage in Econometric & Statistical Packages",
            "",
            "1. **Python / Pandas:**",
            "   ```python",
            "   import pandas as pd",
            "   # Read CSV skipping the commented metadata preamble lines starting with '#'",
            "   df_parks = pd.read_csv('05_industrial_parks.csv', comment='#')",
            "   df_transactions = pd.read_csv('11_property_transactions.csv', comment='#')",
            "   ```",
            "",
            "2. **R / tidyverse:**",
            "   ```R",
            "   library(readr)",
            "   transactions <- read_csv('11_property_transactions.csv', comment = '#')",
            "   parks <- read_csv('05_industrial_parks.csv', comment = '#')",
            "   ```",
            "",
            "3. **Stata:**",
            "   ```stata",
            "   import delimited using 11_property_transactions.csv, clear",
            "   ```"
        ])
        
        zip_file.writestr("README_METADATA_AND_DATA_SOURCES.md", "\n".join(manifest_lines))
        
    zip_buffer.seek(0)
    return zip_buffer.getvalue(), f"gujarat_industrial_estates_all_{len(TABLE_REGISTRY)}_tables_csv.zip"
