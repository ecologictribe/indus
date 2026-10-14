import os
import zipfile
import csv

BASE_DIR = r"d:\aplly_articles"
ZIP_OUTPUT = os.path.join(BASE_DIR, "GIDC_Data_Provenance_Evidence_Package.zip")

pdf_2004 = os.path.join(BASE_DIR, "evidence_pdf_archive", "GIDC_Allotment_Price_Circular_2004_05.pdf")
pdf_2016 = os.path.join(BASE_DIR, "evidence_pdf_archive", "GIDC_Allotment_Price_Circular_2016_17.pdf")
pdf_2026 = os.path.join(BASE_DIR, "evidence_pdf_archive", "GIDC_Allotment_Price_Circular_2026_27.pdf")

report_md = os.path.join(BASE_DIR, "evidence_pdf_archive", "EVIDENCE_VERIFICATION_REPORT.md")
script_extract = os.path.join(BASE_DIR, "extract_and_validate_2004_prices.py")
script_guardrail = os.path.join(BASE_DIR, "guardrails", "dataset_integrity_guardrail.py")
verified_csv_2004 = os.path.join(BASE_DIR, "temp_industrial_land_price_2004_verified.csv")
audit_csv = os.path.join(BASE_DIR, "source_links_reachability_audit.csv")

scans_dir_2004 = os.path.join(BASE_DIR, "evidence_pdf_archive", "scanned_pages_2004")

with zipfile.ZipFile(ZIP_OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    # 1. Official Primary Circular PDFs (All 3 Key Anchors)
    if os.path.exists(pdf_2004):
        z.write(pdf_2004, arcname="official_circulars/GIDC_Allotment_Price_Circular_2004_05.pdf")
    if os.path.exists(pdf_2016):
        z.write(pdf_2016, arcname="official_circulars/GIDC_Allotment_Price_Circular_2016_17.pdf")
    if os.path.exists(pdf_2026):
        z.write(pdf_2026, arcname="official_circulars/GIDC_Allotment_Price_Circular_2026_27.pdf")

    # 2. Forensic Audit Report & Documentation
    if os.path.exists(report_md):
        z.write(report_md, arcname="EVIDENCE_VERIFICATION_REPORT.md")

    # 3. Verified Data & Audit Tables
    if os.path.exists(audit_csv):
        z.write(audit_csv, arcname="data/source_links_reachability_audit.csv")
    if os.path.exists(verified_csv_2004):
        z.write(verified_csv_2004, arcname="data/temp_industrial_land_price_2004_verified.csv")
    
    verified_csv_all = os.path.join(BASE_DIR, "temp_industrial_land_price_history_verified_all_years.csv")
    if os.path.exists(verified_csv_all):
        z.write(verified_csv_all, arcname="data/temp_industrial_land_price_history_verified_all_years.csv")
    
    inventory_csv = os.path.join(BASE_DIR, "evidence_pdf_archive", "COMPLETE_GIDC_HISTORICAL_CIRCULARS_INVENTORY.csv")
    if os.path.exists(inventory_csv):
        z.write(inventory_csv, arcname="data/COMPLETE_GIDC_HISTORICAL_CIRCULARS_INVENTORY.csv")

    # 4. Ingestion, Preprocessing & Guardrail Scripts
    if os.path.exists(script_extract):
        z.write(script_extract, arcname="scripts/extract_and_validate_2004_prices.py")
    if os.path.exists(script_guardrail):
        z.write(script_guardrail, arcname="scripts/dataset_integrity_guardrail.py")
    
    pipeline_script = os.path.join(BASE_DIR, "build_unified_ground_truth_pipeline.py")
    if os.path.exists(pipeline_script):
        z.write(pipeline_script, arcname="scripts/build_unified_ground_truth_pipeline.py")

    # 5. High-Resolution Scans for 2004 Annexure-A
    if os.path.exists(scans_dir_2004):
        for f in sorted(os.listdir(scans_dir_2004)):
            z.write(os.path.join(scans_dir_2004, f), arcname=f"scanned_pages_2004/{f}")

    # 6. High-Resolution Scans for 2026-27 Annexure-A
    p1_2026 = os.path.join(BASE_DIR, "page_1_2026.png")
    p2_2026 = os.path.join(BASE_DIR, "page_2_2026.png")
    if os.path.exists(p1_2026):
        z.write(p1_2026, arcname="scanned_pages_2026_27/page_1_circular_order_14_08_2026.png")
    if os.path.exists(p2_2026):
        z.write(p2_2026, arcname="scanned_pages_2026_27/page_2_annexure_a_ahmedabad_rates.png")

    # 7. Empirical Plots and Interactive Visualizer Dashboard
    plots_dir = os.path.join(BASE_DIR, "plots")
    if os.path.exists(plots_dir):
        for f in sorted(os.listdir(plots_dir)):
            z.write(os.path.join(plots_dir, f), arcname=f"plots/{f}")

    plot_script = os.path.join(BASE_DIR, "generate_empirical_price_plots.py")
    if os.path.exists(plot_script):
        z.write(plot_script, arcname="scripts/generate_empirical_price_plots.py")

print("Rebuilt complete ZIP archive.")
print(f"Archive path: {ZIP_OUTPUT}")
print(f"Archive size: {os.path.getsize(ZIP_OUTPUT):,} bytes")

with zipfile.ZipFile(ZIP_OUTPUT, 'r') as z:
    print("\nVerified ZIP Directory Tree:")
    for info in z.infolist():
        print(f" - {info.filename:<75} ({info.file_size:,} bytes)")
