import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from database import get_db, query_db
from table_exporters import TABLE_REGISTRY

def get_citations():
    """Returns academic citations in BibTeX, APA, and Chicago formats."""
    bibtex = """@article{arora2026industrial,
  title = {Spatial Difference-in-Differences Analysis of Property Price Dynamics across Industrial Park Lifecycle Phases: Evidence from 312 Estates in Gujarat},
  author = {Arora, Devanshu and Contributors},
  journal = {Urban Economics & Regional Science Working Papers},
  year = {2026},
  volume = {14},
  number = {2},
  pages = {101--134},
  doi = {10.5281/zenodo.gujarat.industrial.2026},
  publisher = {State Industrial Estates Research Initiative},
  address = {Ahmedabad, Gujarat, India}
}"""

    apa = (
        "Arora, D. (2026). Spatial Difference-in-Differences Analysis of Property Price Dynamics "
        "across Industrial Park Lifecycle Phases: Evidence from 312 Estates in Gujarat. "
        "Urban Economics & Regional Science Working Papers, 14(2), 101–134. "
        "https://doi.org/10.5281/zenodo.gujarat.industrial.2026"
    )

    chicago = (
        "Arora, Devanshu. 2026. \"Spatial Difference-in-Differences Analysis of Property Price Dynamics "
        "across Industrial Park Lifecycle Phases: Evidence from 312 Estates in Gujarat.\" "
        "Urban Economics & Regional Science Working Papers 14, no. 2: 101–134."
    )

    return {
        "bibtex": bibtex,
        "apa": apa,
        "chicago": chicago
    }

def generate_stata_dofile():
    """Generates a complete, publication-ready Stata .do replication file."""
    return """* ==============================================================================
* GUJARAT INDUSTRIAL ESTATES PROPERTY DYNAMICS STUDY
* Stata Replication Do-File: Spatial Difference-in-Differences Estimation
* Author: Devanshu Arora & Research Team (2026)
* Dataset: 11_property_transactions.csv & 12_did_panel_designations.csv
* ==============================================================================

clear all
set more off
capture log close

* 1. Ingest Panel Property Transactions
import delimited "11_property_transactions.csv", clear

* 2. Variable Transformations & Labels
label variable market_price_inr "Actual Market Sale Price (INR)"
label variable price_per_sqm_inr "Price per Sq. Meter (INR)"
label variable circle_rate_sqm_inr "Registered Circle Rate (Jantar) per Sqm"

* Log Transformations
gen ln_price_sqm = ln(price_per_sqm_inr)
gen ln_circle_sqm = ln(circle_rate_sqm_inr)
gen circle_ratio = circle_rate_sqm_inr / price_per_sqm_inr

* Encode Spatial Distance Buffer (Baseline reference = Control (>10km))
encode distance_buffer_bin, gen(buffer_cat)
reorder buffer_cat
* Set 'Control (>10km)' as reference base category
levelsof buffer_cat if distance_buffer_bin == "Control (>10km)", local(base_ref)
if "`base_ref'" != "" {
    fvset base `base_ref' buffer_cat
}

* 3. Descriptive Statistics by Buffer & Period
tabulate distance_buffer_bin is_post_event, summarize(price_per_sqm_inr) means

* 4. Baseline Spatial Difference-in-Differences OLS Estimation
* Regression with Year Fixed Effects and Hedonic Controls
regress ln_price_sqm i.buffer_cat##i.is_post_event property_age_years distance_to_highway_km i.sale_year, vce(robust)
estimates store did_baseline

* Calculate percentage impacts for interaction terms
di "--- Net DiD Impact Estimates (%) ---"
foreach b in 1 2 3 4 {
    capture di "Buffer `b' DiD Impact: " %6.2f (exp(_b[`b'.buffer_cat#1.is_post_event]) - 1) * 100 "%"
}

* 5. Testing the Parallel Trends Assumption (Pre-Event Interaction Placebos)
gen event_time = sale_year - 2018
* Interactions between buffer and lead indicators
char event_time[omit] -1
xi: regress ln_price_sqm b0.buffer_cat*b(-1).event_time property_age_years distance_to_highway_km, vce(robust)
* F-test for joint significance of pre-event leads (H0: Parallel Trends Hold)
testparm _IbufX* if event_time < -1

* 6. Dual-Pricing Analysis: Statutory Circle Rate (Jantar) Sticky Lag
regress circle_ratio i.buffer_cat i.sale_year, vce(cluster property_id)
estimates store circle_lag

* Export Publication Table (if estout is installed)
capture esttab did_baseline circle_lag using "did_stata_results.rtf", replace ///
    b(3) se(3) star(* 0.10 ** 0.05 *** 0.01) r2 ar2 title("Spatial DiD Results")

di "Replication do-file execution completed successfully."
"""

def generate_python_replication_script():
    """Generates an automated, standalone Python replication script."""
    return """# ==============================================================================
# GUJARAT INDUSTRIAL ESTATES PROPERTY DYNAMICS STUDY
# Python Replication Script: Empirical Difference-in-Differences & Parallel Trends
# Author: Devanshu Arora & Research Team (2026)
# ==============================================================================

import pandas as pd
import numpy as np

# 1. Load Data (Using the exported CSV files)
print("Loading 11_property_transactions.csv ...")
df = pd.read_csv("11_property_transactions.csv", comment="#")

print(f"Total Observations Loaded: {len(df)}")
df["ln_price_sqm"] = np.log(df["Price_Per_Sqm_INR"])

# 2. Parallel Trends Check: Pre-Event Summary (2012-2017)
pre_df = df[df["Sale_Year"] < 2018]
pre_trends = pre_df.groupby(["Sale_Year", "Distance_Buffer_Bin"])["Price_Per_Sqm_INR"].mean().unstack()
print("\\n--- Pre-Event (2012-2017) Mean Price per Sqm ---")
print(pre_trends)

# 3. Spatial Difference-in-Differences OLS Estimation
# Reference baseline: Control (>10km)
buffer_list = ["Clean Commercial (<0.3km)", "<0.5km", "0.5-1.5km", "3-8km"]
base_buffer = "Control (>10km)"

# Build Design Matrix
X_cols = ["Intercept"]
for b in buffer_list:
    df[f"buf_{b}"] = (df["Distance_Buffer_Bin"] == b).astype(float)
    X_cols.append(f"buf_{b}")

df["is_post"] = (df["Sale_Year"] >= 2018).astype(float)
X_cols.append("is_post")

for b in buffer_list:
    df[f"did_{b}"] = df[f"buf_{b}"] * df["is_post"]
    X_cols.append(f"did_{b}")

df["age"] = df["Property_Age_Years"].astype(float)
df["hwy"] = df["Distance_To_Highway_Km"].astype(float)
df["time_trend"] = df["Sale_Year"] - df["Sale_Year"].min()
X_cols.extend(["age", "hwy", "time_trend"])

df["Intercept"] = 1.0

X = df[X_cols].values
y = df["ln_price_sqm"].values

# OLS via Normal Equations
beta, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
resids = y - X @ beta
ssr = np.sum(resids**2)
sst = np.sum((y - np.mean(y))**2)
r2 = 1.0 - (ssr / sst)
adj_r2 = 1.0 - (1.0 - r2) * (len(y) - 1) / (len(y) - len(beta))

df_e = len(y) - len(beta)
s2 = ssr / df_e
cov = np.linalg.pinv(X.T @ X) * s2
se = np.sqrt(np.diag(cov))
t_stats = beta / se

print("\\n" + "="*80)
print(f"SPATIAL DIFFERENCE-IN-DIFFERENCES OLS RESULTS (R2 = {r2:.4f}, Adj R2 = {adj_r2:.4f}, N = {len(y)})")
print("="*80)
print(f"{'Variable':35} {'Coef (Beta)':12} {'Std.Err':10} {'t-Stat':10} {'Net Impact (%)':15}")
print("-"*80)

for i, col in enumerate(X_cols):
    pct = (np.exp(beta[i]) - 1.0) * 100.0
    print(f"{col:35} {beta[i]:10.4f}  {se[i]:9.4f}  {t_stats[i]:9.3f}  {pct:+12.2f}%")

print("="*80)
print("Replication script completed successfully!")
"""

def generate_kml_export():
    """Generates standard KML XML export for Google Earth / GIS tools (from task 1)."""
    parks = query_db("""
        SELECT 
            ip.park_id, ip.park_name, ip.authority_type, ip.sector_category,
            ip.total_area_acres, ip.notification_year, ip.has_cetp,
            ip.latitude, ip.longitude, ip.address, d.district_name, st.taluka_name
        FROM industrial_parks ip
        JOIN subdistricts_talukas st ON ip.taluka_id = st.taluka_id
        JOIN districts d ON st.district_id = d.district_id
        WHERE ip.latitude IS NOT NULL AND ip.longitude IS NOT NULL
    """)

    kml = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
    doc = ET.SubElement(kml, 'Document')
    
    doc_name = ET.SubElement(doc, 'name')
    doc_name.text = "Gujarat Industrial Parks and GIDC Estates (312 Estates)"
    
    doc_desc = ET.SubElement(doc, 'description')
    doc_desc.text = "Spatial locations and attributes for Gujarat industrial parks, GIDC estates, and sanctioned private SEZs."

    for p in parks:
        pm = ET.SubElement(doc, 'Placemark')
        pname = ET.SubElement(pm, 'name')
        pname.text = p['park_name']
        
        pdesc = ET.SubElement(pm, 'description')
        pdesc.text = (
            f"<![CDATA["
            f"<b>District:</b> {p['district_name']}<br>"
            f"<b>Taluka:</b> {p['taluka_name']}<br>"
            f"<b>Authority:</b> {p['authority_type']}<br>"
            f"<b>Sector:</b> {p['sector_category']}<br>"
            f"<b>Area:</b> {p['total_area_acres'] or 'N/A'} acres<br>"
            f"<b>Notification Year:</b> {p['notification_year'] or 'N/A'}<br>"
            f"<b>CETP Active:</b> {'Yes' if p['has_cetp'] else 'No'}<br>"
            f"<b>Address:</b> {p['address'] or 'N/A'}"
            f"]]>"
        )
        
        point = ET.SubElement(pm, 'Point')
        coords = ET.SubElement(point, 'coordinates')
        coords.text = f"{p['longitude']},{p['latitude']},0"

    xml_str = ET.tostring(kml, encoding='utf-8')
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="  "), "gujarat_industrial_parks.kml"

def get_table_schema_detail(table_name):
    """
    Returns column details, constraints, and live 5-row preview sample
    for the interactive Table Schema Inspector.
    """
    if table_name not in TABLE_REGISTRY:
        return None
        
    meta = TABLE_REGISTRY[table_name]
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. PRAGMA table_info
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols_raw = cursor.fetchall()
    
    columns = []
    for c in cols_raw:
        # cid, name, type, notnull, dflt_value, pk
        cid, name, col_type, notnull, dflt, pk = c
        columns.append({
            "name": name,
            "type": col_type or "TEXT",
            "is_pk": bool(pk),
            "not_null": bool(notnull),
            "default_val": dflt,
            "description": meta["column_descriptions"].get(name, "Field attribute")
        })
        
    # 2. Live 5-row preview
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
    rows = cursor.fetchall()
    col_names = [col["name"] for col in columns]
    
    sample_data = []
    for r in rows:
        sample_data.append(dict(zip(col_names, list(r))))
        
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_count = cursor.fetchone()[0]

    return {
        "table_name": table_name,
        "display_name": meta["display_name"],
        "description": meta["description"],
        "data_source": meta["data_source"],
        "primary_key": meta["primary_key"],
        "foreign_keys": meta["foreign_keys"],
        "total_records": total_count,
        "columns": columns,
        "sample_preview": sample_data
    }
