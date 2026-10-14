import sqlite3
import json
import csv
import os
import re
import math

DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'industrial_estates.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'db', 'schema.sql')
CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'Gujarat_Industrial_Parks_and_GIDC_Estates.csv')
PARKS_JSON_PATH = os.path.join(os.path.dirname(__file__), 'spatial_map', 'data', 'parks.json')
from pollution_benchmarks import seed_pollution_benchmarks
from land_intelligence import seed_intelligence_pipeline

def init_db(db_path=DB_PATH, force=False):
    """Initializes the database schema."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if force and os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Schema initialized at {db_path}")

def load_data(db_path=DB_PATH, force=False):
    """Parses source data files and populates SQLite database."""
    init_db(db_path=db_path, force=force)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM industrial_parks")
    if cursor.fetchone()[0] > 0 and not force:
        print("Database already contains data. Skipping loading.")
        conn.close()
        return

    print("Beginning data ingestion...")
    
    # 1. State
    cursor.execute("INSERT OR IGNORE INTO states (state_name, state_code) VALUES ('Gujarat', 'GJ')")
    cursor.execute("SELECT state_id FROM states WHERE state_code = 'GJ'")
    state_id = cursor.fetchone()[0]
    
    # 2. Load parks.json and CSV
    with open(PARKS_JSON_PATH, 'r', encoding='utf-8') as f:
        parks_json = json.load(f)
        
    csv_meta = {}
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sr = row.get('\ufeffSr No') or row.get('Sr No')
                if sr:
                    csv_meta[sr.strip()] = row

    district_map = {}
    taluka_map = {}
    
    # Distinct districts
    for p in parks_json:
        dname = (p.get('district') or 'General').strip()
        if dname not in district_map:
            cursor.execute("INSERT INTO districts (state_id, district_name) VALUES (?, ?)", (state_id, dname))
            district_map[dname] = cursor.lastrowid
            
        tname = (p.get('taluka') or p.get('location') or 'Central').strip().title()
        taluka_key = (district_map[dname], tname)
        if taluka_key not in taluka_map:
            cursor.execute("INSERT INTO subdistricts_talukas (district_id, taluka_name) VALUES (?, ?)", (district_map[dname], tname))
            taluka_map[taluka_key] = cursor.lastrowid

    print(f"Inserted {len(district_map)} districts and {len(taluka_map)} talukas.")

    # 3. Insert Industrial Parks
    park_id_map = {}
    for p in parks_json:
        pid_src = str(p.get('id', ''))
        pname = p.get('name', 'Industrial Park').strip()
        dname = (p.get('district') or 'General').strip()
        dist_id = district_map[dname]
        tname = (p.get('taluka') or p.get('location') or 'Central').strip().title()
        tal_id = taluka_map[(dist_id, tname)]
        
        category = p.get('category', 'GIDC Industrial Estate (Government)')
        auth_type = 'Private SEZ/Park' if 'Private' in category else 'GIDC'
        
        # Sector category detection
        sector = 'General Engineering & Manufacturing'
        pname_lower = pname.lower()
        if 'chemical' in pname_lower or 'fine chem' in pname_lower or 'pharma' in pname_lower:
            sector = 'Chemical & Petrochemical'
        elif 'apparel' in pname_lower or 'textile' in pname_lower:
            sector = 'Textile & Apparel'
        elif 'auto' in pname_lower:
            sector = 'Auto & Ancillary Cluster'
        elif 'electronic' in pname_lower or 'tech' in pname_lower:
            sector = 'Electronics & High-Tech'
        elif 'ceramic' in pname_lower or 'morbi' in pname_lower:
            sector = 'Ceramic & Non-Metallic'
        elif 'food' in pname_lower or 'agro' in pname_lower:
            sector = 'Agro & Food Processing'
            
        # Parse area and notification year if available
        area_ha = p.get('areaHa')
        area_acres = round(area_ha * 2.47105, 2) if area_ha else 350.0
        
        # Derive notification year
        notif_year = 2015
        if 'sanctioned' in category.lower() or '2015' in category:
            notif_year = 2015
        elif 'sanand' in pname_lower:
            notif_year = 2010
        elif 'dahej' in pname_lower:
            notif_year = 2005
        elif 'ankleshwar' in pname_lower:
            notif_year = 1995
        elif 'hazira' in pname_lower:
            notif_year = 1998
        elif 'vapi' in pname_lower:
            notif_year = 1990
        elif 'halol' in pname_lower:
            notif_year = 2008
        else:
            notif_year = 2005

        planning_type = 'Modern Grade-A Regulated' if ('Private' in category or notif_year >= 2010) else 'Legacy Heavy Industry'
        has_cetp = 1 if ('chemical' in sector.lower() or 'textile' in sector.lower() or notif_year < 2010) else 0

        cursor.execute("""
            INSERT INTO industrial_parks (
                taluka_id, park_name, authority_type, sector_category,
                total_area_acres, planning_type, notification_year, has_cetp,
                latitude, longitude, address, phone, email, notes, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tal_id, pname, auth_type, sector,
            area_acres, planning_type, notif_year, has_cetp,
            p.get('lat'), p.get('lng'), p.get('address'),
            p.get('phone'), p.get('email'), p.get('notes'), p.get('source')
        ))
        db_park_id = cursor.lastrowid
        park_id_map[pname] = db_park_id

    print(f"Inserted {len(parks_json)} industrial parks.")

    # 4. Clean Commercial Nodes (IT Parks, Commercial plazas for baseline)
    clean_nodes = [
        ('GIFT City Tech Node', 'IT / Financial SEZ', 'Gandhinagar', 'Gandhinagar', 2011, 23.1601, 72.6841),
        ('SG Highway Corporate Hub', 'IT & Commercial Complex', 'Ahmedabad', 'Ahmedabad', 2008, 23.0338, 72.5085),
        ('Alkapuri Business Center', 'Office Plaza & Retail', 'Vadodara', 'Vadodara', 2005, 22.3106, 73.1706),
        ('Vesu High Street & Finance Hub', 'Commercial & Retail Mall', 'Surat', 'Surat', 2012, 21.1418, 72.7758),
        ('Ankleshwar Tech & Retail Plaza', 'IT & Commercial Center', 'Bharuch', 'Ankleshwar', 2018, 21.6264, 73.0012),
        ('Kalawad Road Commercial Complex', 'Corporate & Shopping Node', 'Rajkot', 'Rajkot', 2010, 22.2812, 70.7684),
        ('Sanand Commercial Gateway', 'Retail & Office Arcade', 'Ahmedabad', 'Sanand', 2016, 22.9833, 72.3667),
        ('Hazira Maritime Trade Center', 'Commercial & Logistics Hub', 'Surat', 'Choryasi', 2014, 21.1065, 72.6482)
    ]
    
    clean_node_ids = []
    for cname, ccat, dname, tname, eyear, clat, clng in clean_nodes:
        dist_id = district_map.get(dname) or list(district_map.values())[0]
        tal_id = taluka_map.get((dist_id, tname.title())) or taluka_map.get((dist_id, 'Central')) or list(taluka_map.values())[0]
        cursor.execute("""
            INSERT INTO clean_commercial_nodes (taluka_id, node_name, category, establishment_year, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tal_id, cname, ccat, eyear, clat, clng))
        clean_node_ids.append(cursor.lastrowid)
    print(f"Inserted {len(clean_nodes)} clean commercial benchmark nodes.")

    # 5. Anchor Facilities (Major industrial plants)
    anchor_data = [
        ('GIDC Sanand', 'Tata Motors Passenger Vehicles', 'Automobile Assembly', 2200.0, 2400.0, '2010-06-02', 4500),
        ('GIDC Sanand', 'Micron Technology India', 'Semiconductor Assembly & Test', 22500.0, 18000.0, '2024-03-15', 5000),
        ('Mandal', 'Suzuki Motor Gujarat (SMG)', 'Automotive Manufacturing', 18000.0, 18500.0, '2017-02-01', 9000),
        ('Ankleshwar', 'UPL Agrochemicals Ltd', 'Agrochemicals & Fine Chemicals', 1500.0, 1600.0, '2018-04-10', 2200),
        ('Dahej', 'ONGC Petro additions Ltd (OPaL)', 'Mega Petrochemical Complex', 30000.0, 31200.0, '2017-03-07', 3500),
        ('Dahej', 'Reliance Industries Limited', 'Polyester & Intermediate Chemicals', 12000.0, 12500.0, '2015-11-20', 4000),
        ('Hazira', 'Larsen & Toubro Heavy Engineering', 'Nuclear & Defence Fabrication', 8500.0, 8900.0, '2008-09-12', 6500),
        ('Hazira', 'AM/NS India Hazira Steel', 'Hot-Rolled & Flat Steel Products', 45000.0, 48000.0, '2012-01-15', 12000),
        ('Halol', 'MG Motor India Ltd', 'Electric & Passenger Vehicles', 4000.0, 4200.0, '2018-10-01', 3200),
        ('Vapi', 'Aarti Industries Limited', 'Specialty Chemical Intermediates', 950.0, 1020.0, '2014-05-18', 1800)
    ]
    
    for park_match, cname, itype, pinv, ainv, cdate, emps in anchor_data:
        # Find matching park
        cursor.execute("SELECT park_id FROM industrial_parks WHERE park_name LIKE ? LIMIT 1", (f'%{park_match}%',))
        prow = cursor.fetchone()
        pid = prow[0] if prow else 1
        cursor.execute("""
            INSERT INTO anchor_facilities (
                park_id, company_name, industry_type,
                proposed_investment_inr, actual_investment_inr,
                commencement_date, estimated_employment
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (pid, cname, itype, pinv, ainv, cdate, emps))
    print("Inserted anchor facilities.")

    # 6. Lifecycle Events for Parks
    # Insert rich milestones for key parks
    cursor.execute("SELECT park_id, park_name, notification_year FROM industrial_parks")
    all_parks = cursor.fetchall()
    
    events_to_insert = []
    for pid, pname, nyear in all_parks:
        nyear = nyear or 2012
        events_to_insert.append((pid, 'Policy Announcement', f"{nyear}-03-15", nyear, f"State Government G.R. notifying {pname}"))
        events_to_insert.append((pid, 'Land Acquisition & Trunk Infra', f"{nyear+1}-08-20", nyear+1, "Trunk infrastructure, power substations, and wide access road layout completed"))
        events_to_insert.append((pid, 'Anchor Plant Operational', f"{nyear+3}-11-05", nyear+3, "Major anchor tenant commissioned production operations"))
        events_to_insert.append((pid, 'Ancillary Cluster Active', f"{nyear+6}-06-12", nyear+6, "Vendor supply chain and tier-1/2 component suppliers fully active"))
        if nyear < 2015:
            events_to_insert.append((pid, 'Remediation & CETP Upgrade', f"{nyear+9}-04-10", nyear+9, "Common Effluent Treatment Plant upgraded with zero-liquid-discharge (ZLD) norms"))
            
    cursor.executemany("""
        INSERT INTO park_lifecycle_events (park_id, event_type, event_date, event_year, description)
        VALUES (?, ?, ?, ?, ?)
    """, events_to_insert)
    print(f"Inserted {len(events_to_insert)} lifecycle milestones.")

    # 7. Annual Metrics (Occupancy, FSI, CEPI, PM2.5)
    metrics_to_insert = []
    # Sample 30 active parks for multi-year tracking
    cursor.execute("SELECT park_id, sector_category, notification_year FROM industrial_parks LIMIT 35")
    sample_parks = cursor.fetchall()
    for pid, sec, nyear in sample_parks:
        base_year = nyear or 2012
        for yr in range(max(2012, base_year), 2026):
            age = max(1, yr - base_year + 1)
            occ = min(96.0, 25.0 + age * 6.5)
            fsi = min(82.0, 18.0 + age * 5.2)
            units = int(min(650, 15 + age * 35))
            
            # CEPI pollution score
            base_cepi = 78.0 if 'Chemical' in sec else 52.0
            cepi = round(base_cepi - min(15.0, age * 0.8), 1)
            pm = round(65.0 + (15.0 if 'Chemical' in sec else 0.0), 1)
            
            metrics_to_insert.append((pid, yr, round(occ, 1), round(fsi, 1), units, cepi, pm))
            
    cursor.executemany("""
        INSERT OR REPLACE INTO park_annual_metrics (
            park_id, assessment_year, occupancy_rate_pct, avg_fsi_utilized_pct,
            active_units_count, cepi_score, pm2_5_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, metrics_to_insert)
    print(f"Inserted {len(metrics_to_insert)} annual metric observations.")

    # 8. Neighborhoods & Properties & DiD Transactions
    cursor.execute("SELECT taluka_id, taluka_name FROM subdistricts_talukas LIMIT 15")
    sample_talukas = cursor.fetchall()
    
    neighborhood_map = {}
    for tid, tname in sample_talukas:
        for suffix in ['East Corridor', 'West Residential Ring', 'North Industrial Border', 'South Highway Fringe']:
            nh_name = f"{tname} {suffix}"
            is_gated = 1 if 'Ring' in suffix or 'East' in suffix else 0
            cursor.execute("""
                INSERT INTO neighborhoods_jurisdictions (taluka_id, neighborhood_name, tax_jurisdiction_code, is_gated_community)
                VALUES (?, ?, ?, ?)
            """, (tid, nh_name, f"TAX-{tid}-{suffix[:3].upper()}", is_gated))
            neighborhood_map[nh_name] = cursor.lastrowid
            
    print(f"Inserted {len(neighborhood_map)} neighborhoods.")

    # Generate synthetic Difference-in-Differences panel properties
    # Anchored around Bharuch / Ankleshwar GIDC & Sanand hubs as detailed in the python script
    cursor.execute("SELECT park_id FROM industrial_parks WHERE park_name LIKE '%Ankleshwar%' OR park_name LIKE '%Chemical%' LIMIT 1")
    study_park_res = cursor.fetchone()
    study_park_id = study_park_res[0] if study_park_res else 1
    clean_bench_id = clean_node_ids[0] if clean_node_ids else 1
    first_nh_id = list(neighborhood_map.values())[0]

    buffer_configs = [
        ("Control_Far_Corridor", "Control (>10km)", 12.0, 160, 0),
        ("Control_Clean_Commercial", "Clean Commercial (<0.3km)", 0.25, 160, 0),
        ("Treated_Adjacent_Industrial", "<0.5km", 0.35, 160, 1),
        ("Treated_Intermediate_Industrial", "0.5-1.5km", 1.1, 160, 1),
        ("Treated_SweetSpot_Industrial", "3-8km", 4.8, 160, 1)
    ]
    
    property_types = ['Residential Apartment', 'Single Family Detached', 'Plot', 'Commercial Frontage']
    years = list(range(2012, 2026))
    
    total_props = 0
    total_tx = 0
    
    for group_name, buffer_bin, base_dist, count, is_treated in buffer_configs:
        for p_idx in range(count):
            seed_prop = total_props + p_idx + 1
            dist = float(round(base_dist + (seed_prop % 5) * 0.05, 2))
            prop_type = property_types[seed_prop % len(property_types)]
            area = float(round(80.0 + (seed_prop % 14) * 10.0, 1))
            bedrooms = 2 if area < 100 else (3 if area < 160 else 4)
            bathrooms = max(1, bedrooms - 1)
            age = int(1 + (seed_prop % 17))
            dist_hwy = float(round(0.5 + (seed_prop % 11) * 0.5, 2))
            dist_clean = 0.2 if buffer_bin == "Clean Commercial (<0.3km)" else float(round(2.0 + (seed_prop % 9) * 1.4, 2))
            dist_urban = float(round(dist + 3.0 + (seed_prop % 5), 2))
            
            cursor.execute("""
                INSERT INTO properties (
                    neighborhood_id, nearest_park_id, nearest_clean_commercial_id,
                    property_type, built_up_area_sqm, bedrooms, bathrooms,
                    age_at_sale_years, distance_to_park_km, distance_buffer_bin,
                    distance_to_clean_commercial_km, distance_to_highway_km, distance_to_urban_center_km
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                first_nh_id, study_park_id, clean_bench_id,
                prop_type, area, bedrooms, bathrooms,
                age, dist, buffer_bin,
                dist_clean, dist_hwy, dist_urban
            ))
            prop_id = cursor.lastrowid
            total_props += 1
            
            # Deterministic transaction schedule
            for yr_idx, year in enumerate(years):
                if (seed_prop + yr_idx) % 3 == 0:
                    quarter = int(1 + ((seed_prop + yr_idx) % 4))
                    month = (quarter - 1) * 3 + int(1 + (seed_prop % 3))
                    day = int(1 + ((seed_prop * 3 + yr_idx) % 28))
                    sale_date = f"{year}-{month:02d}-{day:02d}"
                    
                    time_trend = (year - 2012) * 0.045
                    log_base_price = math.log(22000.0) + time_trend
                    
                    # Treatment event window set to 2018 (Anchor commissioning)
                    is_post = 1 if year >= 2018 else 0
                    years_since = year - 2018
                    
                    group_effect = 0.0
                    if is_post:
                        if buffer_bin == "Clean Commercial (<0.3km)":
                            group_effect = -0.020
                        elif buffer_bin == "<0.5km":
                            group_effect = -0.065
                        elif buffer_bin == "0.5-1.5km":
                            group_effect = 0.080
                        elif buffer_bin == "3-8km":
                            group_effect = 0.215
                            
                    type_adj = 0.08 if prop_type == 'Commercial Frontage' else (-0.05 if prop_type == 'Plot' else 0.0)
                    log_price = log_base_price + group_effect - (0.008 * age) - (0.015 * dist_hwy) + type_adj
                    
                    price_per_sqm = float(math.exp(log_price))
                    market_price = float(round(price_per_sqm * area, 2))
                    
                    lagged_trend = (year - 2012) * 0.038
                    circle_rate_sqm = float(round(22000.0 * math.exp(lagged_trend) * 0.78, 2))
                    ratio = float(round(circle_rate_sqm / price_per_sqm, 3))
                    
                    cursor.execute("""
                        INSERT INTO property_transactions (
                            property_id, sale_date, sale_year, sale_quarter,
                            market_transaction_price, price_per_sqm, registered_circle_rate_sqm,
                            circle_to_market_ratio, is_repeat_sale, is_arms_length
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
                    """, (
                        prop_id, sale_date, year, quarter,
                        market_price, round(price_per_sqm, 2), circle_rate_sqm,
                        ratio
                    ))
                    tx_id = cursor.lastrowid
                    total_tx += 1
                    
                    # DiD designation
                    if year < 2015:
                        phase = "Phase_0_Baseline"
                    elif year < 2018:
                        phase = "Phase_1_Announcement"
                    elif year < 2021:
                        phase = "Phase_2_Anchor_Commissioned"
                    else:
                        phase = "Phase_3_Active_Ancillary"
                        
                    cursor.execute("""
                        INSERT INTO did_panel_designations (
                            transaction_id, treatment_group, lifecycle_phase_at_sale,
                            is_treated, is_post_event, did_interaction_term, years_since_event
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        tx_id, group_name, phase,
                        is_treated, is_post, is_treated * is_post, years_since
                    ))

    # 13. Seed & Sync Complete Environmental & Pollution Dimensions (CEPI, Air, Water/CETP, Typology)
    seed_pollution_benchmarks(conn, force=force)

    # 14. Seed & Sync Historical Land Pricing Archive (2000-2026/27) & Plot Intelligence (Tasks T3 & T4)
    seed_intelligence_pipeline(conn, force=force)

    conn.commit()
    conn.close()
    print(f"Data loading complete! Total properties: {total_props}, Total transactions: {total_tx}")

if __name__ == "__main__":
    load_data(force=True)
