import io
import csv
import json
import datetime
from database import query_db, get_db
from did_engine import run_did_regression, get_kpi_summary
from models import (
    get_parks,
    get_park_by_id,
    get_park_anchors,
    get_park_lifecycle_events,
    get_park_annual_metrics
)

DATA_DICTIONARY = {
    "distance_buffer_bin": "Categorical distance gradient (<0.5km = immediate proximity drag, 0.5-1.5km = intermediate zone, 3-8km = residential sweet spot, Clean Commercial <0.3km = clean baseline, Control >10km = macro control)",
    "market_transaction_price": "Actual registered transaction clearing price in Indian Rupees (INR)",
    "price_per_sqm": "Transaction value divided by property built-up area in square meters (INR/sqm)",
    "registered_circle_rate_sqm": "Statutory administrative valuation benchmark (Ready Reckoner / Jantar rate) in INR/sqm",
    "circle_to_market_ratio": "Ratio of registered circle rate to actual market price per sqm (circle_rate / price_per_sqm)",
    "did_interaction_term": "Difference-in-Differences interaction term: (is_treated * is_post_event)",
    "is_post_event": "Binary indicator (1 if sale year >= anchor commissioning year, 0 otherwise)",
    "cepi_score": "Comprehensive Environmental Pollution Index (higher values indicate severe industrial pollution)",
    "has_cetp": "Common Effluent Treatment Plant status (1 = Active Operational, 0 = None / Independent ETP)"
}

def get_base_metadata(filters=None):
    return {
        "project": "Gujarat Industrial Estates Property Dynamics Study",
        "jurisdiction": "State of Gujarat, India",
        "data_vintage": "2012–2025 Panel",
        "source": "GIDC Official Records, Gujarat State Industrial Policy, Spatial Geocoding",
        "export_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "filters_applied": filters or {}
    }

# -----------------------------------------------------------------------------
# Stop 1: Executive Dashboard Export
# -----------------------------------------------------------------------------

def export_dashboard_data(fmt='json'):
    conn = get_db()
    kpis = get_kpi_summary(conn)
    did = run_did_regression(conn, post_year=2018)
    
    meta = get_base_metadata()
    meta["description"] = "Executive KPI summary and baseline DiD econometrics metrics"
    
    payload = {
        "_metadata": meta,
        "kpis": kpis,
        "did_baseline_summary": did["summary"] if did else {},
        "net_effects_pct": did["summary"]["did_effects"] if did else {}
    }
    
    if fmt == 'json':
        return json.dumps(payload, indent=2), 'application/json', 'dashboard_summary.json'
        
    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# Project", meta["project"]])
    writer.writerow(["# Export Timestamp", meta["export_timestamp"]])
    writer.writerow([])
    writer.writerow(["Metric", "Value", "Unit / Context"])
    writer.writerow(["Total Industrial Parks", kpis["total_parks"], "Estates"])
    writer.writerow(["Total Gujarat Districts", kpis["total_districts"], "Districts"])
    writer.writerow(["Total Properties Tracked", kpis["total_properties"], "Parcels"])
    writer.writerow(["Total Panel Transactions", kpis["total_transactions"], "Sales (2012-2025)"])
    writer.writerow(["Average Market Price", kpis["avg_price_sqm"], "INR / sqm"])
    writer.writerow(["Average Statutory Circle Rate", kpis["avg_circle_sqm"], "INR / sqm"])
    writer.writerow(["Sweet Spot Premium (3-8km)", f"+{kpis['sweet_spot_pct']}%", "Net DiD Impact"])
    writer.writerow(["Immediate Proximity Drag (<0.5km)", f"{kpis['drag_pct']}%", "Negative Drag"])
    writer.writerow(["Clean Commercial Benchmark (<0.3km)", f"{kpis['clean_pct']}%", "Commercial Noise"])
    writer.writerow(["Regression Model R-Squared", did['summary']['r_squared'], "Goodness of Fit"])
    
    return output.getvalue(), 'text/csv', 'dashboard_summary.csv'

# -----------------------------------------------------------------------------
# Stop 2: DiD Econometrics Studio Export
# -----------------------------------------------------------------------------

def export_econometrics_data(post_year=2018, property_type='ALL', buffer_filter='ALL', export_type='model_json'):
    conn = get_db()
    did = run_did_regression(conn, post_year=post_year, property_type=property_type, buffer_filter=buffer_filter)
    
    filters = {
        "anchor_event_year": post_year,
        "property_type": property_type,
        "buffer_filter": buffer_filter
    }
    meta = get_base_metadata(filters)
    meta["methodology"] = "Spatial Difference-in-Differences OLS regression on log(price_per_sqm)"
    meta["baseline_reference"] = "Control Far Corridor (>10km)"
    meta["data_dictionary"] = DATA_DICTIONARY
    
    if export_type == 'model_json':
        payload = {
            "_metadata": meta,
            "model_summary": did["summary"],
            "coefficients": did["coefficients"],
            "price_trajectories": did["trajectories"],
            "valuation_ratios": did["ratios"],
            "bar_impact_data": did["bar_data"]
        }
        return json.dumps(payload, indent=2), 'application/json', f'did_econometric_model_{post_year}.json'
        
    elif export_type == 'coefficients_csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["# Model Specification", "log(price_per_sqm) ~ Buffer * Post + Controls"])
        writer.writerow(["# Event Year T0", post_year])
        writer.writerow(["# Property Segment", property_type])
        writer.writerow(["# R-Squared", did['summary']['r_squared']])
        writer.writerow(["# Observations N", did['summary']['n_obs']])
        writer.writerow([])
        writer.writerow(["Parameter_Variable", "Coefficient_Beta", "Std_Error", "t_Statistic", "p_Value", "CI_Lower_95", "CI_Upper_95", "Net_Impact_Percent"])
        for c in did["coefficients"]:
            writer.writerow([
                c["term"], c["coef"], c["std_err"], c["t_stat"],
                c["p_val"], c["ci_lower"], c["ci_upper"], c["pct_impact"]
            ])
        return output.getvalue(), 'text/csv', f'did_coefficients_{post_year}.csv'
        
    elif export_type == 'trajectories_csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["# Spatial Buffer Mean Price Trajectories (INR/sqm)"])
        writer.writerow(["# Anchor Event Year", post_year])
        writer.writerow([])
        headers = ["Sale_Year"] + list(did["trajectories"]["series"].keys())
        writer.writerow(headers)
        
        years = did["trajectories"]["years"]
        for idx, yr in enumerate(years):
            row = [yr]
            for buf in did["trajectories"]["series"].keys():
                val = did["trajectories"]["series"][buf][idx]
                row.append(val if val is not None else "")
            writer.writerow(row)
        return output.getvalue(), 'text/csv', f'spatial_trajectories_{post_year}.csv'

# -----------------------------------------------------------------------------
# Stop 3: Industrial Parks Directory & Map Export
# -----------------------------------------------------------------------------

def export_parks_data(district='ALL', category='ALL', search='', fmt='csv'):
    parks = get_parks(district=district, category=category, search=search)
    
    filters = {
        "district": district,
        "category": category,
        "search_query": search
    }
    meta = get_base_metadata(filters)
    meta["record_count"] = len(parks)
    meta["data_dictionary"] = {
        "authority_type": "GIDC (Govt) vs Private SEZ/Park",
        "has_cetp": "1 if Common Effluent Treatment Plant active, 0 otherwise",
        "total_area_acres": "Total developed land size in acres"
    }
    
    if fmt == 'geojson':
        features = []
        for p in parks:
            if p['latitude'] and p['longitude']:
                feat = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(p['longitude']), float(p['latitude'])]
                    },
                    "properties": {
                        "park_id": p['park_id'],
                        "park_name": p['park_name'],
                        "district_name": p['district_name'],
                        "taluka_name": p['taluka_name'],
                        "authority_type": p['authority_type'],
                        "sector_category": p['sector_category'],
                        "total_area_acres": p['total_area_acres'],
                        "notification_year": p['notification_year'],
                        "has_cetp": p['has_cetp'],
                        "phone": p['phone'],
                        "email": p['email'],
                        "anchor_count": p['anchor_count']
                    }
                }
                features.append(feat)
        payload = {
            "type": "FeatureCollection",
            "_metadata": meta,
            "features": features
        }
        return json.dumps(payload, indent=2), 'application/geo+json', 'gujarat_industrial_parks.geojson'
        
    elif fmt == 'json':
        payload = {
            "_metadata": meta,
            "parks": [dict(p) for p in parks]
        }
        return json.dumps(payload, indent=2), 'application/json', 'gujarat_industrial_parks.json'
        
    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# Gujarat Industrial Parks Catalog Export"])
    writer.writerow(["# Export Timestamp", meta["export_timestamp"]])
    writer.writerow(["# Total Estates", len(parks)])
    writer.writerow([])
    writer.writerow([
        "Park_ID", "Park_Name", "District", "Taluka", "Authority_Type",
        "Sector_Category", "Total_Area_Acres", "Notification_Year", "CETP_Active",
        "Latitude", "Longitude", "Phone", "Email", "Address", "Anchors_Count"
    ])
    for p in parks:
        writer.writerow([
            p['park_id'], p['park_name'], p['district_name'], p['taluka_name'], p['authority_type'],
            p['sector_category'], p['total_area_acres'] or '', p['notification_year'] or '', p['has_cetp'],
            p['latitude'] or '', p['longitude'] or '', p['phone'] or '', p['email'] or '',
            p['address'] or '', p['anchor_count']
        ])
    return output.getvalue(), 'text/csv', 'gujarat_industrial_parks.csv'

# -----------------------------------------------------------------------------
# Stop 4: Individual Park Dossier Export
# -----------------------------------------------------------------------------

def export_park_dossier(park_id, fmt='json'):
    park = get_park_by_id(park_id)
    if not park:
        return None, None, None
        
    anchors = get_park_anchors(park_id)
    events = get_park_lifecycle_events(park_id)
    metrics = get_park_annual_metrics(park_id)
    
    meta = get_base_metadata({"park_id": park_id, "park_name": park['park_name']})
    meta["description"] = f"Complete empirical factsheet and lifecycle dossier for {park['park_name']}"
    meta["distance_buffers"] = {
        "drag_zone_km": "<0.5km",
        "intermediate_km": "0.5-1.5km",
        "sweet_spot_km": "3.0-8.0km"
    }
    
    if fmt == 'json':
        payload = {
            "_metadata": meta,
            "park_profile": dict(park),
            "anchors": [dict(a) for a in anchors],
            "lifecycle_events": [dict(e) for e in events],
            "annual_density_metrics": [dict(m) for m in metrics]
        }
        safe_name = "".join(c for c in park['park_name'] if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_').lower()
        return json.dumps(payload, indent=2), 'application/json', f'park_{park_id}_{safe_name}_dossier.json'
        
    # CSV format: exports chronological events and metrics
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# Park Dossier:", park['park_name']])
    writer.writerow(["# District:", park['district_name'], "Taluka:", park['taluka_name']])
    writer.writerow(["# Category:", park['sector_category'], "Area:", f"{park['total_area_acres']} acres"])
    writer.writerow([])
    writer.writerow(["--- LIFECYCLE MILESTONES ---"])
    writer.writerow(["Event_ID", "Event_Type", "Event_Date", "Event_Year", "Description"])
    for e in events:
        writer.writerow([e['event_id'], e['event_type'], e['event_date'], e['event_year'], e['description']])
        
    writer.writerow([])
    writer.writerow(["--- ANNUAL METRICS PANEL ---"])
    writer.writerow(["Assessment_Year", "Occupancy_Rate_Pct", "Avg_FSI_Utilized_Pct", "Active_Units_Count", "CEPI_Score", "PM2_5_Level"])
    for m in metrics:
        writer.writerow([m['assessment_year'], m['occupancy_rate_pct'], m['avg_fsi_utilized_pct'], m['active_units_count'], m['cepi_score'], m['pm2_5_level']])
        
    safe_name = "".join(c for c in park['park_name'] if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_').lower()
    return output.getvalue(), 'text/csv', f'park_{park_id}_{safe_name}_timeline_metrics.csv'

# -----------------------------------------------------------------------------
# Stop 5: Property Transactions & DiD Panel Export
# -----------------------------------------------------------------------------

def export_transactions_data(buffer_bin='ALL', property_type='ALL', year='ALL', search='', fmt='csv'):
    where_clauses = ["1=1"]
    params = []
    
    if buffer_bin and buffer_bin != 'ALL':
        where_clauses.append("p.distance_buffer_bin = ?")
        params.append(buffer_bin)
    if property_type and property_type != 'ALL':
        where_clauses.append("p.property_type = ?")
        params.append(property_type)
    if year and year != 'ALL':
        where_clauses.append("pt.sale_year = ?")
        params.append(int(year))
    if search:
        where_clauses.append("(ip.park_name LIKE ? OR nj.neighborhood_name LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s])
        
    where_sql = " AND ".join(where_clauses)
    
    query = f"""
        SELECT 
            pt.transaction_id,
            pt.sale_date,
            pt.sale_year,
            pt.sale_quarter,
            pt.market_transaction_price,
            pt.price_per_sqm,
            pt.registered_circle_rate_sqm,
            pt.circle_to_market_ratio,
            p.property_id,
            p.property_type,
            p.built_up_area_sqm,
            p.distance_buffer_bin,
            p.distance_to_park_km,
            p.distance_to_highway_km,
            p.age_at_sale_years,
            ip.park_name,
            nj.neighborhood_name,
            did.treatment_group,
            did.lifecycle_phase_at_sale,
            did.is_treated,
            did.is_post_event,
            did.did_interaction_term,
            did.years_since_event
        FROM property_transactions pt
        JOIN properties p ON pt.property_id = p.property_id
        JOIN industrial_parks ip ON p.nearest_park_id = ip.park_id
        JOIN neighborhoods_jurisdictions nj ON p.neighborhood_id = nj.neighborhood_id
        LEFT JOIN did_panel_designations did ON pt.transaction_id = did.transaction_id
        WHERE {where_sql}
        ORDER BY pt.sale_date DESC
    """
    rows = query_db(query, params)
    
    filters = {
        "buffer_bin": buffer_bin,
        "property_type": property_type,
        "sale_year": year,
        "search_query": search
    }
    meta = get_base_metadata(filters)
    meta["record_count"] = len(rows)
    meta["data_dictionary"] = DATA_DICTIONARY
    
    if fmt == 'json':
        payload = {
            "_metadata": meta,
            "transactions": [dict(r) for r in rows]
        }
        return json.dumps(payload, indent=2), 'application/json', 'property_transactions_panel.json'
        
    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["# Gujarat Property Transactions DiD Panel Export"])
    writer.writerow(["# Export Timestamp", meta["export_timestamp"]])
    writer.writerow(["# Records Exported", len(rows)])
    writer.writerow([])
    writer.writerow([
        "Transaction_ID", "Sale_Date", "Sale_Year", "Sale_Quarter",
        "Market_Price_INR", "Price_Per_Sqm_INR", "Circle_Rate_Sqm_INR", "Circle_To_Market_Ratio",
        "Property_ID", "Property_Type", "Area_Sqm", "Distance_Buffer_Bin",
        "Distance_To_Park_Km", "Distance_To_Highway_Km", "Property_Age_Years",
        "Nearest_Park_Name", "Neighborhood_Name", "Treatment_Group",
        "Lifecycle_Phase", "Is_Treated", "Is_Post_Event", "DiD_Interaction_Term", "Years_Since_Event"
    ])
    for r in rows:
        writer.writerow([
            r['transaction_id'], r['sale_date'], r['sale_year'], r['sale_quarter'],
            r['market_transaction_price'], r['price_per_sqm'], r['registered_circle_rate_sqm'], r['circle_to_market_ratio'],
            r['property_id'], r['property_type'], r['built_up_area_sqm'], r['distance_buffer_bin'],
            r['distance_to_park_km'], r['distance_to_highway_km'], r['age_at_sale_years'],
            r['park_name'], r['neighborhood_name'], r['treatment_group'] or '',
            r['lifecycle_phase_at_sale'] or '', r['is_treated'], r['is_post_event'],
            r['did_interaction_term'], r['years_since_event']
        ])
    return output.getvalue(), 'text/csv', 'property_transactions_panel.csv'
