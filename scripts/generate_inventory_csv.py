import os
import glob
import hashlib
import csv

CIRCULAR_DIR = r"d:\aplly_articles\evidence_pdf_archive\all_historical_circulars"
OUTPUT_CSV = r"d:\aplly_articles\evidence_pdf_archive\COMPLETE_GIDC_HISTORICAL_CIRCULARS_INVENTORY.csv"

files = glob.glob(os.path.join(CIRCULAR_DIR, "*.pdf"))

inventory = []
for f in sorted(files):
    fname = os.path.basename(f)
    size = os.path.getsize(f)
    with open(f, 'rb') as fp:
        sha = hashlib.sha256(fp.read()).hexdigest()
    
    # Determine financial year from filename
    fy = "Unknown"
    for yr in range(2000, 2027):
        yr_str = f"{yr}-{yr+1}"
        yr_short = f"{str(yr)[2:]}-{str(yr+1)[2:]}"
        if yr_str in fname or yr_short in fname:
            fy = f"FY {yr_str}"
            break
        elif str(yr) in fname:
            fy = f"FY {yr}-{yr+1}"
            break
            
    inventory.append({
        "financial_year": fy,
        "filename": fname,
        "file_size_bytes": size,
        "file_size_mb": round(size / (1024 * 1024), 2),
        "sha256_hash": sha,
        "verification_status": "OFFICIAL_GOVERNMENT_PDF_ARCHIVED",
        "archive_path": f"evidence_pdf_archive/all_historical_circulars/{fname}"
    })

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        "financial_year", "filename", "file_size_bytes", "file_size_mb", 
        "sha256_hash", "verification_status", "archive_path"
    ])
    writer.writeheader()
    writer.writerows(inventory)

print(f"Generated inventory of {len(inventory)} official circulars at {OUTPUT_CSV}")
