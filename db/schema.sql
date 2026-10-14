-- SQLite Database Schema for Industrial Park Property Dynamics Study
PRAGMA foreign_keys = ON;

-- MODULE 1: SPATIAL HIERARCHY & DRILL-DOWN (State -> District -> Taluka -> Neighborhood)
CREATE TABLE IF NOT EXISTS states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_name TEXT NOT NULL UNIQUE,
    state_code TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS districts (
    district_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id INTEGER NOT NULL,
    district_name TEXT NOT NULL,
    census_code TEXT,
    FOREIGN KEY (state_id) REFERENCES states(state_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS subdistricts_talukas (
    taluka_id INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id INTEGER NOT NULL,
    taluka_name TEXT NOT NULL,
    FOREIGN KEY (district_id) REFERENCES districts(district_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS neighborhoods_jurisdictions (
    neighborhood_id INTEGER PRIMARY KEY AUTOINCREMENT,
    taluka_id INTEGER NOT NULL,
    neighborhood_name TEXT NOT NULL,
    tax_jurisdiction_code TEXT,
    is_gated_community INTEGER DEFAULT 0,
    FOREIGN KEY (taluka_id) REFERENCES subdistricts_talukas(taluka_id) ON DELETE CASCADE
);

-- MODULE 2: INDUSTRIAL PARK LIFECYCLE & ANCHOR ENTITIES
CREATE TABLE IF NOT EXISTS industrial_parks (
    park_id INTEGER PRIMARY KEY AUTOINCREMENT,
    taluka_id INTEGER NOT NULL,
    park_name TEXT NOT NULL,
    authority_type TEXT,
    sector_category TEXT,
    total_area_acres REAL,
    planning_type TEXT,
    notification_year INTEGER,
    has_cetp INTEGER DEFAULT 0,
    latitude REAL,
    longitude REAL,
    address TEXT,
    phone TEXT,
    email TEXT,
    notes TEXT,
    source TEXT,
    inferred_lifecycle_stage TEXT DEFAULT 'Phase 1: Greenfield Inception',
    FOREIGN KEY (taluka_id) REFERENCES subdistricts_talukas(taluka_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS park_lifecycle_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_date DATE NOT NULL,
    event_year INTEGER NOT NULL,
    description TEXT,
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS anchor_facilities (
    anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    industry_type TEXT,
    proposed_investment_inr REAL,
    actual_investment_inr REAL,
    commencement_date DATE,
    estimated_employment INTEGER,
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS park_annual_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id INTEGER NOT NULL,
    assessment_year INTEGER NOT NULL,
    occupancy_rate_pct REAL,
    avg_fsi_utilized_pct REAL,
    active_units_count INTEGER,
    inferred_lifecycle_stage TEXT,
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE,
    UNIQUE(park_id, assessment_year)
);

-- MODULE 3: COMPARISON GROUPS & PARCEL SPATIAL ATTRIBUTES
CREATE TABLE IF NOT EXISTS clean_commercial_nodes (
    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
    taluka_id INTEGER NOT NULL,
    node_name TEXT NOT NULL,
    category TEXT,
    establishment_year INTEGER,
    latitude REAL,
    longitude REAL,
    FOREIGN KEY (taluka_id) REFERENCES subdistricts_talukas(taluka_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS properties (
    property_id INTEGER PRIMARY KEY AUTOINCREMENT,
    neighborhood_id INTEGER NOT NULL,
    nearest_park_id INTEGER NOT NULL,
    nearest_clean_commercial_id INTEGER,
    property_type TEXT NOT NULL,
    lot_size_sqm REAL,
    built_up_area_sqm REAL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    age_at_sale_years INTEGER,
    distance_to_park_km REAL NOT NULL,
    distance_buffer_bin TEXT NOT NULL,
    distance_to_clean_commercial_km REAL,
    distance_to_highway_km REAL,
    distance_to_urban_center_km REAL,
    FOREIGN KEY (neighborhood_id) REFERENCES neighborhoods_jurisdictions(neighborhood_id),
    FOREIGN KEY (nearest_park_id) REFERENCES industrial_parks(park_id),
    FOREIGN KEY (nearest_clean_commercial_id) REFERENCES clean_commercial_nodes(node_id)
);

-- MODULE 4: TRANSACTIONS & PRICING DATA (Dependent Variables)
CREATE TABLE IF NOT EXISTS property_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    sale_date DATE NOT NULL,
    sale_year INTEGER NOT NULL,
    sale_quarter INTEGER NOT NULL,
    market_transaction_price REAL NOT NULL,
    price_per_sqm REAL NOT NULL,
    registered_circle_rate_sqm REAL NOT NULL,
    circle_to_market_ratio REAL,
    is_repeat_sale INTEGER DEFAULT 0,
    is_arms_length INTEGER DEFAULT 1,
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
);

-- MODULE 5: DIFFERENCE-IN-DIFFERENCES (DiD) VARIABLE MATRIX
CREATE TABLE IF NOT EXISTS did_panel_designations (
    designation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    treatment_group TEXT NOT NULL,
    lifecycle_phase_at_sale TEXT NOT NULL,
    is_treated INTEGER NOT NULL,
    is_post_event INTEGER NOT NULL,
    did_interaction_term INTEGER NOT NULL,
    years_since_event INTEGER,
    FOREIGN KEY (transaction_id) REFERENCES property_transactions(transaction_id) ON DELETE CASCADE
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_districts_state ON districts(state_id);
CREATE INDEX IF NOT EXISTS idx_parks_taluka ON industrial_parks(taluka_id);
CREATE INDEX IF NOT EXISTS idx_properties_park ON properties(nearest_park_id);
CREATE INDEX IF NOT EXISTS idx_properties_buffer ON properties(distance_buffer_bin);
CREATE INDEX IF NOT EXISTS idx_transactions_year ON property_transactions(sale_year);
CREATE INDEX IF NOT EXISTS idx_did_interaction ON did_panel_designations(did_interaction_term);
CREATE INDEX IF NOT EXISTS idx_parks_lifecycle ON industrial_parks(inferred_lifecycle_stage);

-- MODULE 5: PROVENANCE SOURCES & INTELLIGENCE PIPELINE (TASKS T3 & T4)
CREATE TABLE IF NOT EXISTS intelligence_sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,
    tier_level TEXT NOT NULL,
    document_name TEXT NOT NULL,
    source_url TEXT,
    publication_date DATE,
    retrieval_date DATE,
    authority TEXT DEFAULT 'GIDC',
    reliability TEXT DEFAULT 'HIGH',
    checksum TEXT
);

CREATE TABLE IF NOT EXISTS estate_aliases_master (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id INTEGER NOT NULL,
    canonical_name TEXT NOT NULL,
    historical_name TEXT NOT NULL,
    district_name TEXT NOT NULL,
    taluka_name TEXT,
    phase TEXT,
    parent_estate TEXT,
    former_name TEXT,
    gidc_code TEXT,
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS industrial_land_price_history (
    price_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id INTEGER NOT NULL,
    financial_year TEXT NOT NULL,
    calendar_year INTEGER NOT NULL,
    price_type TEXT NOT NULL,
    price_per_sqm REAL NOT NULL,
    revision_reason TEXT,
    effective_from DATE NOT NULL,
    effective_to DATE,
    source_id INTEGER,
    source_document TEXT,
    source_url TEXT,
    confidence TEXT DEFAULT 'HIGH',
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES intelligence_sources(source_id),
    UNIQUE(park_id, financial_year, price_type)
);

CREATE TABLE IF NOT EXISTS industrial_plots (
    plot_id TEXT PRIMARY KEY,
    park_id INTEGER NOT NULL,
    plot_number TEXT NOT NULL,
    plot_area_sqm REAL NOT NULL,
    plot_area_sqft REAL NOT NULL,
    plot_type TEXT DEFAULT 'Industrial',
    category TEXT DEFAULT 'MSME',
    status TEXT DEFAULT 'Allocated',
    allotment_price_sqm REAL NOT NULL,
    total_allotment_value REAL NOT NULL,
    road_width_m REAL,
    is_corner_plot INTEGER DEFAULT 0,
    frontage_m REAL,
    allotment_date DATE,
    company_name TEXT,
    industry_subsector TEXT,
    source_id INTEGER,
    confidence TEXT DEFAULT 'HIGH',
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES intelligence_sources(source_id)
);

-- INDEXES FOR HISTORICAL PRICING & PLOT INTELLIGENCE
CREATE INDEX IF NOT EXISTS idx_land_price_park ON industrial_land_price_history(park_id);
CREATE INDEX IF NOT EXISTS idx_land_price_year ON industrial_land_price_history(calendar_year);
CREATE INDEX IF NOT EXISTS idx_land_price_type ON industrial_land_price_history(price_type);
CREATE INDEX IF NOT EXISTS idx_plots_park ON industrial_plots(park_id);
CREATE INDEX IF NOT EXISTS idx_plots_status ON industrial_plots(status);
CREATE INDEX IF NOT EXISTS idx_plots_area ON industrial_plots(plot_area_sqm);
CREATE INDEX IF NOT EXISTS idx_plots_price ON industrial_plots(allotment_price_sqm);
CREATE INDEX IF NOT EXISTS idx_aliases_canonical ON estate_aliases_master(canonical_name);

-- MODULE 6: SOURCE ARCHIVING, CENTRAL SOURCE REGISTRY & VALUE-LEVEL DATA PROVENANCE (TASK T5)
CREATE TABLE IF NOT EXISTS source_registry (
    source_id TEXT PRIMARY KEY,
    organisation TEXT NOT NULL,
    source_title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    publication_date DATE,
    retrieval_date DATE NOT NULL,
    original_url TEXT NOT NULL,
    local_path TEXT NOT NULL,
    local_filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    version TEXT DEFAULT '1.0',
    language TEXT DEFAULT 'English',
    source_status TEXT DEFAULT 'archived',
    failure_reason TEXT,
    extraction_status TEXT DEFAULT 'processed',
    extraction_method TEXT DEFAULT 'table extraction',
    reliability TEXT DEFAULT 'Official Statutory Document',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS data_provenance (
    provenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    extracted_value TEXT NOT NULL,
    normalized_value TEXT,
    source_id TEXT NOT NULL,
    source_location TEXT NOT NULL,
    source_excerpt TEXT NOT NULL,
    extraction_method TEXT DEFAULT 'PDF table extraction',
    extraction_date DATE NOT NULL,
    confidence TEXT DEFAULT 'HIGH',
    verified INTEGER DEFAULT 1,
    verified_by TEXT DEFAULT 'GIDC Cadastral Audit Team',
    notes TEXT,
    FOREIGN KEY (source_id) REFERENCES source_registry(source_id) ON DELETE CASCADE
);

-- INDEXES FOR VALUE-LEVEL PROVENANCE AUDIT
CREATE INDEX IF NOT EXISTS idx_prov_entity ON data_provenance(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_prov_source ON data_provenance(source_id);
CREATE INDEX IF NOT EXISTS idx_prov_field ON data_provenance(field_name);
CREATE INDEX IF NOT EXISTS idx_source_org ON source_registry(organisation);
CREATE INDEX IF NOT EXISTS idx_source_hash ON source_registry(file_hash);

