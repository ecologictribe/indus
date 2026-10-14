import os
import csv
import json
import shutil
import hashlib
import urllib.request
import ssl

# Define directories
BASE_DIR = r"d:\aplly_articles"
EVIDENCE_PDF_DIR = os.path.join(BASE_DIR, "evidence_pdf_archive")
PAGES_IMG_DIR = os.path.join(EVIDENCE_PDF_DIR, "scanned_pages_2004")
OUTPUT_CSV_PATH = os.path.join(BASE_DIR, "temp_industrial_land_price_2004_verified.csv")

os.makedirs(EVIDENCE_PDF_DIR, exist_ok=True)
os.makedirs(PAGES_IMG_DIR, exist_ok=True)

# Copy PDFs into the evidence folder
source_2004_pdf = os.path.join(BASE_DIR, "official_gidc_pdfs", "allotment_price_2004_2005.pdf")
source_2016_pdf = os.path.join(BASE_DIR, "official_gidc_pdfs", "CIRCULAR_ALLOTMENT_PRICE_2016.pdf")

dest_2004_pdf = os.path.join(EVIDENCE_PDF_DIR, "GIDC_Allotment_Price_Circular_2004_05.pdf")
dest_2016_pdf = os.path.join(EVIDENCE_PDF_DIR, "GIDC_Allotment_Price_Circular_2016_17.pdf")

if os.path.exists(source_2004_pdf):
    shutil.copy2(source_2004_pdf, dest_2004_pdf)
if os.path.exists(source_2016_pdf):
    shutil.copy2(source_2016_pdf, dest_2016_pdf)

# Copy page scans
src_scans = os.path.join(BASE_DIR, "official_gidc_pdfs", "extracted_pages_2004")
if os.path.exists(src_scans):
    for f in os.listdir(src_scans):
        shutil.copy2(os.path.join(src_scans, f), os.path.join(PAGES_IMG_DIR, f))

# Verified tabular data from Annexure-A of Circular GIDC/O&m/CIR/ACCTTS/REV/6 dated 01/04/2004
# Format: (District, Estate Name, Sector, Official Rate Rs/sqm)
VERIFIED_2004_ANNEXURE_A = [
    # AHMEDABAD
    ("Ahmedabad", "Naroda", "Industrial", 800),
    ("Ahmedabad", "Odhav", "Industrial", 900),
    ("Ahmedabad", "Vatva", "Industrial", 800),
    ("Ahmedabad", "Zone-D", "Industrial", 700),
    ("Ahmedabad", "Dholka", "Industrial", 110),
    ("Ahmedabad", "Sanand (RIDC)", "Industrial", 150),
    ("Ahmedabad", "Kerala", "Industrial", 125),
    ("Ahmedabad", "Dhandhuka", "Industrial", 60),
    ("Ahmedabad", "Viramgam", "Industrial", 150),
    ("Ahmedabad", "Kathwada", "Industrial", 800),

    # GANDHINAGAR
    ("Gandhinagar", "Gandhinagar (Engg)", "Industrial", 1500),
    ("Gandhinagar", "Gandhinagar (Elect)", "Industrial", 300),
    ("Gandhinagar", "Dehgam", "Industrial", 150),
    ("Gandhinagar", "Manasa", "Industrial", 125),
    ("Gandhinagar", "Bhat", "Industrial", 1250),

    # MEHSANA
    ("Mehsana", "Chansama", "Industrial", 125),
    ("Mehsana", "Kukerwada", "Industrial", 75),
    ("Mehsana", "Kadi", "Industrial", 150),
    ("Mehsana", "Chhatral", "Industrial", 125),
    ("Mehsana", "Mehsana - I", "Industrial", 500),
    ("Mehsana", "Mehsana - II", "Industrial", 200),
    ("Mehsana", "Kalol (N.G)", "Industrial", 250),
    ("Mehsana", "Kheralu", "Industrial", 50),
    ("Mehsana", "Visnagar", "Industrial", 450),
    ("Mehsana", "Ranasan", "Industrial", 125),
    ("Mehsana", "Gozariya", "Industrial", 100),

    # SABARKANTHA
    ("Sabarkantha", "Himatnagar", "Industrial", 250),
    ("Sabarkantha", "Idar", "Industrial", 75),
    ("Sabarkantha", "Modasa", "Industrial", 75),
    ("Sabarkantha", "Malpur (RIDC)", "Industrial", 10),
    ("Sabarkantha", "Talod", "Industrial", 85),
    ("Sabarkantha", "Bhiloda", "Industrial", 160),

    # PATAN
    ("Patan", "Patan", "Industrial", 250),
    ("Patan", "Lunva", "Industrial", 10),
    ("Patan", "Balisana", "Industrial", 70),

    # BANASKANTHA
    ("Banaskantha", "Palanpur", "Industrial", 500),
    ("Banaskantha", "Ambaji - I", "Industrial", 100),
    ("Banaskantha", "Disa", "Industrial", 230),
    ("Banaskantha", "Sihori (RIDC)", "Industrial", 10),
    ("Banaskantha", "Chandisar", "Industrial", 100),
    ("Banaskantha", "Deodar", "Industrial", 170),

    # KHEDA
    ("Kheda", "Balasinor", "Industrial", 60),
    ("Kheda", "Thasra", "Industrial", 100),
    ("Kheda", "Nadiad I & II", "Industrial", 690),
    ("Kheda", "Nadiad (Bansaw Mill)", "Industrial", 500),
    ("Kheda", "Kapadwanj", "Industrial", 100),
    ("Kheda", "Matar", "Industrial", 150),

    # ANAND
    ("Anand", "Umreth", "Industrial", 100),
    ("Anand", "Borsad", "Industrial", 200),
    ("Anand", "Sojitra", "Industrial", 125),
    ("Anand", "Petlad", "Industrial", 100),
    ("Anand", "Khambhat", "Industrial", 200),
    ("Anand", "V.U.Nagar", "Industrial", 500),

    # VADODARA
    ("Vadodara", "Dabhoi", "Industrial", 60),
    ("Vadodara", "Makarpura", "Industrial", 1500),
    ("Vadodara", "Nandesari", "Industrial", 600),
    ("Vadodara", "Pavi Jetpur (RIDC)", "Industrial", 10),
    ("Vadodara", "Sankheda", "Industrial", 20),
    ("Vadodara", "Vaghodia", "Industrial", 100),
    ("Vadodara", "Ranoli", "Industrial", 500),
    ("Vadodara", "Por-Ramangamdi", "Industrial", 450),
    ("Vadodara", "Savli (General)", "Industrial", 250),
    ("Vadodara", "P.C.C.", "Industrial", 540),

    # PANCHMAHAL
    ("Panchmahal", "Godhra", "Industrial", 150),
    ("Panchmahal", "Halol", "Industrial", 120),
    ("Panchmahal", "Kalol (P.M)", "Industrial", 90),
    ("Panchmahal", "Jambughoda (RIDC)", "Industrial", 10),

    # DAHOD
    ("Dahod", "Dahod - I", "Industrial", 500),
    ("Dahod", "Dahod - II", "Industrial", 170),
    ("Dahod", "Devgadhbariya", "Industrial", 45),

    # BHARUCH
    ("Bharuch", "Ankleshwar", "Industrial", 360),
    ("Bharuch", "Bharuch", "Industrial", 250),
    ("Bharuch", "Palej", "Industrial", 80),
    ("Bharuch", "Panoli", "Industrial", 300),
    ("Bharuch", "Jambusar (RIDC)", "Industrial", 10),
    ("Bharuch", "Vagra (RIDC)", "Industrial", 10),
    ("Bharuch", "Vilayat", "Industrial", 250),
    ("Bharuch", "Jhagadia", "Industrial", 250),
    ("Bharuch", "Dahej Gen.zone", "Industrial", 275),
    ("Bharuch", "Dahej Service zone", "Industrial", 450),

    # NARMADA
    ("Narmada", "Rajpipla - II", "Industrial", 60),
    ("Narmada", "Dediyapada (RIDC)", "Industrial", 22),

    # SURAT
    ("Surat", "Pandesara", "Industrial", 1000),
    ("Surat", "Katargam", "Industrial", 1200),
    ("Surat", "Katodara", "Industrial", 1500),
    ("Surat", "Bardoli", "Industrial", 60),
    ("Surat", "Sachin", "Industrial", 470),
    ("Surat", "Valod", "Industrial", 25),
    ("Surat", "Hazira (GIDC) Land undev", "Industrial", 550),
    ("Surat", "Olpad", "Industrial", 125),
    ("Surat", "Doswada", "Industrial", 30),
    ("Surat", "Apparel Park - Sachin", "Industrial", 650),

    # NAVSARI
    ("Navsari", "Navsari", "Industrial", 150),
    ("Navsari", "Unai", "Industrial", 10),
    ("Navsari", "Bilimora", "Industrial", 150),

    # VALSAD
    ("Valsad", "Sarigam (Plastic Zone)", "Industrial", 225),
    ("Valsad", "Sarigam", "Industrial", 210),
    ("Valsad", "Umargam", "Industrial", 300),
    ("Valsad", "Vapi", "Industrial", 500),
    ("Valsad", "Valsad", "Industrial", 200),
    ("Valsad", "Pardi", "Industrial", 120),
    ("Valsad", "Dungra (Garment Zone)", "Industrial", 175),

    # SURENDRANAGAR
    ("Surendranagar", "Dhrangadhra", "Industrial", 50),
    ("Surendranagar", "Limdi", "Industrial", 60),
    ("Surendranagar", "Surendranagar", "Industrial", 350),
    ("Surendranagar", "Thangadh", "Industrial", 100),
    ("Surendranagar", "Bamanbore", "Industrial", 60),
    ("Surendranagar", "Chotila (RIDC)", "Industrial", 20),
    ("Surendranagar", "Halvad", "Industrial", 100),
    ("Surendranagar", "Sayla (RIDC)", "Industrial", 20),
    ("Surendranagar", "Lakhtar", "Industrial", 100),

    # JAMNAGAR
    ("Jamnagar", "Jamnagar - I", "Industrial", 900),
    ("Jamnagar", "Jamnagar - II", "Industrial", 775),
    ("Jamnagar", "Jamnagar-III (Expansion)", "Industrial", 750),
    ("Jamnagar", "Arambhada", "Industrial", 200),
    ("Jamnagar", "Jamkhambhaliya", "Industrial", 100),
    ("Jamnagar", "Dhrol (RIDC)", "Industrial", 25),
    ("Jamnagar", "Bhatia (RIDC)", "Industrial", 25),
    ("Jamnagar", "Bhanvad", "Industrial", 200),
    ("Jamnagar", "Upleta", "Industrial", 150),

    # RAJKOT
    ("Rajkot", "Aji", "Industrial", 2000),
    ("Rajkot", "Bhaktinagar", "Industrial", 3500),
    ("Rajkot", "Morbi", "Industrial", 500),
    ("Rajkot", "Vankaner", "Industrial", 75),
    ("Rajkot", "Jetpur", "Industrial", 200),
    ("Rajkot", "Kuvadva", "Industrial", 50),
    ("Rajkot", "Padadhari (RIDC)", "Industrial", 100),
    ("Rajkot", "Lodhika", "Industrial", 225),
    ("Rajkot", "Jasdan", "Industrial", 100),
    ("Rajkot", "Gondal - I", "Industrial", 500),
    ("Rajkot", "Gondal - II", "Industrial", 150),
    ("Rajkot", "Rafaleshwar", "Industrial", 150),
    ("Rajkot", "Dhoraji", "Industrial", 100),

    # BHAVNAGAR
    ("Bhavnagar", "Chitra", "Industrial", 300),
    ("Bhavnagar", "Mahuva", "Industrial", 300),
    ("Bhavnagar", "Sihor - I", "Industrial", 150),
    ("Bhavnagar", "Sihor - II", "Industrial", 300),
    ("Bhavnagar", "Valbhipur (RIDC)", "Industrial", 50),
    ("Bhavnagar", "Dhasa (RIDC)", "Industrial", 100),
    ("Bhavnagar", "Vithalwadi", "Industrial", 1500),
    ("Bhavnagar", "Vartej", "Industrial", 250),
    ("Bhavnagar", "Botad", "Industrial", 150),
    ("Bhavnagar", "Palitana", "Industrial", 125),

    # AMRELI
    ("Amreli", "Amreli", "Industrial", 200),
    ("Amreli", "Jafrabad (RIDC)", "Industrial", 10),
    ("Amreli", "Liliya (RIDC)", "Industrial", 10),
    ("Amreli", "Rajula", "Industrial", 30),
    ("Amreli", "Babra - I & II", "Industrial", 125),
    ("Amreli", "Damnagar", "Industrial", 55),

    # JUNAGADH
    ("Junagadh", "Junagadh - I", "Industrial", 250),
    ("Junagadh", "Junagadh - II", "Industrial", 200),
    ("Junagadh", "Veraval", "Industrial", 400),
    ("Junagadh", "Visavadar (RIDC)", "Industrial", 10),
    ("Junagadh", "Sheel", "Industrial", 125),

    # PORBANDAR
    ("Porbandar", "Porbandar", "Industrial", 150),
    ("Porbandar", "Ranavav", "Industrial", 175),
    ("Porbandar", "Miyani", "Industrial", 90),

    # KUTCH
    ("Kutch", "Gandhidham", "Industrial", 1800),
    ("Kutch", "Madhapur", "Industrial", 70),
    ("Kutch", "Mundra (RIDC)", "Industrial", 50),
    ("Kutch", "Bhuj", "Industrial", 70),
    ("Kutch", "Anjar", "Industrial", 125),
    ("Kutch", "Mandvi", "Industrial", 125),
    ("Kutch", "Mandvi-New", "Industrial", 100),
    ("Kutch", "Nagor-New Bhuj", "Industrial", 100),
    ("Kutch", "Anjar-New", "Industrial", 100),
    ("Kutch", "Nakhatrana", "Industrial", 100),
    ("Kutch", "Makhel", "Industrial", 100),
    ("Kutch", "Dhrub", "Industrial", 210),
    ("Kutch", "Mithi-Rohar", "Industrial", 260),

    # HOUSING SECTOR (Page 6)
    ("Ahmedabad", "Naroda (Housing)", "Housing", 1000),
    ("Gandhinagar", "Gandhinagar (Housing)", "Housing", 1450),
    ("Mehsana", "Mehsana-I (Housing)", "Housing", 1000),
    ("Mehsana", "Mehsana-II (Housing)", "Housing", 250),
    ("Mehsana", "Chhatral (Housing)", "Housing", 340),
    ("Anand", "V.U. Nagar (Housing)", "Housing", 600),
    ("Vadodara", "Por-Ramangamdi (Housing)", "Housing", 550),
    ("Panchmahal", "Halol (Housing)", "Housing", 200),
    ("Vadodara", "Vaghodia (Housing)", "Housing", 165),
    ("Vadodara", "Makarpura (Housing)", "Housing", 2500),
    ("Bharuch", "Ankleshwar-I, II, III (Housing)", "Housing", 700),
    ("Bharuch", "Bharuch (Housing)", "Housing", 300),
    ("Bharuch", "Panoli (Raw Land Housing)", "Housing", 330),
    ("Surat", "Sachin (Housing)", "Housing", 675),
    ("Surat", "Pandesara (Housing)", "Housing", 1250),
    ("Valsad", "Bulsar (Housing)", "Housing", 225),
    ("Navsari", "Navsari (Housing)", "Housing", 225),
    ("Valsad", "Vapi Dungra (Housing)", "Housing", 320),
    ("Valsad", "Vapi Chanod (Housing)", "Housing", 300),
    ("Valsad", "Vapi Morarji Circle (Housing)", "Housing", 500),
    ("Valsad", "Vapi NH (Housing)", "Housing", 600),
    ("Valsad", "Umargam Old (Housing)", "Housing", 300),
    ("Valsad", "Umargam New Drainage (Housing)", "Housing", 600),
    ("Valsad", "Sarigam (Housing)", "Housing", 275),
    ("Bhavnagar", "Chitra (Housing)", "Housing", 800),
    ("Surendranagar", "Surendranagar (Housing)", "Housing", 450),
    ("Surendranagar", "Thangadh (Housing)", "Housing", 150),
    ("Jamnagar", "Jamnagar-I (Housing)", "Housing", 5000),
    ("Junagadh", "Junagadh (Housing)", "Housing", 300),
    ("Porbandar", "Porbandar (Housing)", "Housing", 300),
    ("Rajkot", "Lodhika (Housing)", "Housing", 360),
]

def load_clean_csv(filepath):
    rows = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        for r in reader:
            if not r or r[0].startswith('#') or r[0].startswith('"#'):
                continue
            rows.append(r)
    header = rows[0]
    return [dict(zip(header, row)) for row in rows[1:]]

# Load existing datasets
parks_file = r'D:\IndustrialEstates\send_data\gujarat_industrial_estates_all_data_devanshu\05_industrial_parks.csv'
prices_file = r'D:\IndustrialEstates\send_data\gujarat_industrial_estates_all_data_devanshu\16_industrial_land_price_history.csv'

parks = load_clean_csv(parks_file)
prices = load_clean_csv(prices_file)

# Build lookup by estate name and park_id
p2004 = {p['park_id']: p for p in prices if p.get('financial_year') == '2004-05'}

# Mapping helper
def match_park(estate_name, district_name, parks_list):
    clean_estate = estate_name.lower().replace("gidc", "").replace("(ridc)", "").replace("(engg)", "").replace("(elect)", "").replace("- i", "").replace("- ii", "").strip()
    # Direct search
    for p in parks_list:
        pname = p['park_name'].lower()
        if clean_estate and clean_estate in pname:
            return p
    # Secondary search on estate words
    words = [w for w in clean_estate.split() if len(w) > 3]
    for w in words:
        for p in parks_list:
            if w in p['park_name'].lower():
                return p
    return None

# Build verified output records
output_rows = []
fieldnames = [
    "record_id",
    "district_name",
    "circular_estate_name",
    "sector_type",
    "official_allotment_price_2004",
    "currency_unit",
    "financial_year",
    "effective_date",
    "source_circular_no",
    "source_authority",
    "official_pdf_url",
    "provenance_tier",
    "confidence_level",
    "matched_park_id",
    "matched_park_name",
    "dataset_erroneous_price_2004",
    "price_difference_inr",
    "percentage_error",
    "audit_notes"
]

rec_id = 1
for district, estate, sector, official_rate in VERIFIED_2004_ANNEXURE_A:
    matched = match_park(estate, district, parks)
    park_id = matched['park_id'] if matched else ""
    park_name = matched['park_name'] if matched else ""
    
    # Check old erroneous price in dataset
    old_price_str = ""
    diff = ""
    pct_err = ""
    notes = "Verified from Annexure-A of official GIDC Circular"
    
    if park_id and park_id in p2004:
        old_val = float(p2004[park_id]['price_per_sqm'])
        old_price_str = f"{old_val:.1f}"
        diff_val = old_val - official_rate
        diff = f"{diff_val:+.1f}"
        pct_val = ((old_val - official_rate) / official_rate) * 100
        pct_err = f"{pct_val:+.1f}%"
        notes = f"Variance: old synthetic price was {diff_val:+.1f} INR/sqm ({pct_val:+.1f}%)"
    
    output_rows.append({
        "record_id": rec_id,
        "district_name": district,
        "circular_estate_name": estate,
        "sector_type": sector,
        "official_allotment_price_2004": official_rate,
        "currency_unit": "INR/sqm",
        "financial_year": "2004-05",
        "effective_date": "2004-04-01",
        "source_circular_no": "GIDC/O&m/CIR/ACCTTS/REV/6",
        "source_authority": "Gujarat Industrial Development Corporation (GIDC)",
        "official_pdf_url": "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2004-2005.pdf",
        "provenance_tier": "Tier 1: Official Statutory Circular",
        "confidence_level": "VERIFIED_GROUND_TRUTH",
        "matched_park_id": park_id,
        "matched_park_name": park_name,
        "dataset_erroneous_price_2004": old_price_str,
        "price_difference_inr": diff,
        "percentage_error": pct_err,
        "audit_notes": notes
    })
    rec_id += 1

# Write to CSV
with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"Successfully generated {OUTPUT_CSV_PATH}")
print(f"Total verified circular records: {len(output_rows)}")
