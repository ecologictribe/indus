-- Enable Foreign Key Constraints in SQLite
PRAGMA foreign_keys = ON;

-- ============================================================================
-- MODULE 1: SPATIAL HIERARCHY & DRILL-DOWN (State -> District -> Taluka)
-- ============================================================================

CREATE TABLE states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_name TEXT NOT NULL UNIQUE,
    state_code TEXT NOT NULL UNIQUE -- e.g., 'GJ' for Gujarat, 'PB' for Punjab
);

CREATE TABLE districts (
    district_id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id INTEGER NOT NULL,
    district_name TEXT NOT NULL,
    census_code TEXT,
    FOREIGN KEY (state_id) REFERENCES states(state_id) ON DELETE CASCADE
);

CREATE TABLE subdistricts_talukas (
    taluka_id INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id INTEGER NOT NULL,
    taluka_name TEXT NOT NULL,
    FOREIGN KEY (district_id) REFERENCES districts(district_id) ON DELETE CASCADE
);

CREATE TABLE neighborhoods_jurisdictions (
    neighborhood_id INTEGER PRIMARY KEY AUTOINCREMENT,
    taluka_id INTEGER NOT NULL,
    neighborhood_name TEXT NOT NULL,
    tax_jurisdiction_code TEXT,
    is_gated_community INTEGER DEFAULT 0, -- 1 = Gated/Planned, 0 = Unplanned/Adjacent Colony
    FOREIGN KEY (taluka_id) REFERENCES subdistricts_talukas(taluka_id) ON DELETE CASCADE
);

-- ============================================================================
-- MODULE 2: INDUSTRIAL PARK LIFECYCLE & ANCHOR ENTITIES
-- ============================================================================

CREATE TABLE industrial_parks (
    park_id INTEGER PRIMARY KEY AUTOINCREMENT,
    taluka_id INTEGER NOT NULL,
    park_name TEXT NOT NULL,
    authority_type TEXT, -- e.g., 'GIDC', 'MIDC', 'PSIEC', 'Private SEZ'
    sector_category TEXT, -- e.g., 'Auto Cluster', 'Textile Park', 'Chemical/Petrochemical', 'MSME Park', 'Logistics'
    total_area_acres REAL,
    planning_type TEXT, -- 'Modern Grade-A Regulated' vs 'Legacy Heavy Industry'
    notification_year INTEGER,
    has_cetp INTEGER DEFAULT 0, -- Common Effluent Treatment Plant (1=Yes, 0=No)
    FOREIGN KEY (taluka_id) REFERENCES subdistricts_talukas(taluka_id) ON DELETE CASCADE
);

-- Tracks key timeline milestones for Difference-in-Differences event windows
CREATE TABLE park_lifecycle_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id INTEGER NOT NULL,
    event_type TEXT NOT NULL, -- 'Policy Announcement', 'Land Acquisition Start', 'Trunk Infrastructure Ready', 'Anchor Plant Operational', 'Ancillary Cluster Active', 'Remediation/CETP Upgrade'
    event_date DATE NOT NULL,
    event_year INTEGER NOT NULL,
    description TEXT,
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE
);

-- Captures Anchor Facilities and large manufacturing plants
CREATE TABLE anchor_facilities (
    anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    industry_type TEXT,
    proposed_investment_inr REAL,
    actual_investment_inr REAL, -- To track actual vs DPR commitments (CAG audit metric)
    commencement_date DATE,
    estimated_employment INTEGER,
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE
);

-- Tracks annual operational density (Occupancy & FSI utilization)
CREATE TABLE park_annual_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    park_id INTEGER NOT NULL,
    assessment_year INTEGER NOT NULL,
    occupancy_rate_pct REAL, -- Percentage of developed plots active
    avg_fsi_utilized_pct REAL, -- Consumed FSI vs buildable FSI
    active_units_count INTEGER,
    cepi_score REAL, -- Comprehensive Environmental Pollution Index
    pm2_5_level REAL, -- Air quality metric (ug/m3)
    FOREIGN KEY (park_id) REFERENCES industrial_parks(park_id) ON DELETE CASCADE,
    UNIQUE(park_id, assessment_year)
);

-- ============================================================================
-- MODULE 3: COMPARISON GROUPS & PARCEL SPATIAL ATTRIBUTES
-- ============================================================================

-- Clean commercial properties to act as comparison baseline for stigma disentanglement
CREATE TABLE clean_commercial_nodes (
    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
    taluka_id INTEGER NOT NULL,
    node_name TEXT NOT NULL,
    category TEXT, -- e.g., 'IT Park', 'Shopping Center', 'Office Complex'
    establishment_year INTEGER,
    FOREIGN KEY (taluka_id) REFERENCES subdistricts_talukas(taluka_id) ON DELETE CASCADE
);

-- Individual residential or commercial properties tracked in the study
CREATE TABLE properties (
    property_id INTEGER PRIMARY KEY AUTOINCREMENT,
    neighborhood_id INTEGER NOT NULL,
    nearest_park_id INTEGER NOT NULL,
    nearest_clean_commercial_id INTEGER,
    property_type TEXT NOT NULL, -- 'Single Family Detached', 'Apartment', 'Plot', 'Commercial Frontage'
    lot_size_sqm REAL,
    built_up_area_sqm REAL,
    bedrooms INTEGER,
    bathrooms INTEGER,
    age_at_sale_years INTEGER,
    distance_to_park_km REAL NOT NULL, -- Continuous distance
    distance_buffer_bin TEXT NOT NULL, -- '0-0.5km', '0.5-1.5km', '1.5-3.0km', '3-8km'
    distance_to_clean_commercial_km REAL,
    distance_to_highway_km REAL,
    distance_to_urban_center_km REAL,
    FOREIGN KEY (neighborhood_id) REFERENCES neighborhoods_jurisdictions(neighborhood_id),
    FOREIGN KEY (nearest_park_id) REFERENCES industrial_parks(park_id),
    FOREIGN KEY (nearest_clean_commercial_id) REFERENCES clean_commercial_nodes(node_id)
);

-- ============================================================================
-- MODULE 4: TRANSACTIONS & PRICING DATA (Dependent Variables)
-- ============================================================================

CREATE TABLE property_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    sale_date DATE NOT NULL,
    sale_year INTEGER NOT NULL,
    sale_quarter INTEGER NOT NULL,
    market_transaction_price REAL NOT NULL, -- Actual market sale value (INR)
    price_per_sqm REAL NOT NULL,
    registered_circle_rate_sqm REAL NOT NULL, -- Official statutory rate (Guideline/Ready Reckoner)
    circle_to_market_ratio REAL, -- Calculation: circle_rate / (market_price / area)
    is_repeat_sale INTEGER DEFAULT 0, -- 1 if house sold multiple times across panel window
    is_arms_length INTEGER DEFAULT 1, -- Filter for non-distress standard market transactions
    FOREIGN KEY (property_id) REFERENCES properties(property_id) ON DELETE CASCADE
);

-- ============================================================================
-- MODULE 5: DIFFERENCE-IN-DIFFERENCES (DiD) VARIABLE MATRIX
-- ============================================================================

-- Stores treatment and control designations for econometric estimation
CREATE TABLE did_panel_designations (
    designation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    treatment_group TEXT NOT NULL, -- 'Treated_Industrial_Near (<0.5km)', 'Partial_Treatment (0.5-1.5km)', 'Control_Clean_Commercial (<0.3km)', 'Control_Insulated_Residential (3-8km)'
    lifecycle_phase_at_sale TEXT NOT NULL, -- 'Phase_1_Pre_Announcement', 'Phase_2_Anchor_Construction', 'Phase_3_Active_Ancillary', 'Phase_4_Maturation_Remediation'
    is_treated INTEGER NOT NULL, -- Binary indicator (1 = Treated, 0 = Control)
    is_post_event INTEGER NOT NULL, -- Binary indicator (1 = Post Lifecycle Event, 0 = Pre)
    did_interaction_term INTEGER NOT NULL, -- Interaction: (is_treated * is_post_event)
    years_since_event INTEGER, -- Event-study relative time indicator (j years)
    FOREIGN KEY (transaction_id) REFERENCES property_transactions(transaction_id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES FOR FAST PANEL & SPATIAL QUERYING
-- ============================================================================

CREATE INDEX idx_districts_state ON districts(state_id);
CREATE INDEX idx_parks_taluka ON industrial_parks(taluka_id);
CREATE INDEX idx_properties_park ON properties(nearest_park_id);
CREATE INDEX idx_properties_buffer ON properties(distance_buffer_bin);
CREATE INDEX idx_transactions_year ON property_transactions(sale_year);
CREATE INDEX idx_did_interaction ON did_panel_designations(did_interaction_term);