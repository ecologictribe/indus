"""Enrich gujarat_*.meta.txt + index using CSV preambles + sources/ + ZIP README + JSON _metadata."""
import csv, json, re, zipfile
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(r"D:\IndustrialEstates\data")
SOURCES_DIR = DATA_DIR / "sources"
PREFIX = "gujarat_"

TRUE_ORIGINALS = {
    "gujarat_01_states.csv": "01_states.csv",
    "gujarat_02_districts.csv": "02_districts.csv",
    "gujarat_03_subdistricts_talukas.csv": "03_subdistricts_talukas.csv",
    "gujarat_04_neighborhoods_jurisdictions.csv": "04_neighborhoods_jurisdictions.csv",
    "gujarat_05_industrial_parks.csv": "05_industrial_parks.csv",
    "gujarat_06_anchor_facilities.csv": "06_anchor_facilities.csv",
    "gujarat_07_park_lifecycle_events.csv": "07_park_lifecycle_events.csv",
    "gujarat_08_park_annual_metrics.csv": "08_park_annual_metrics.csv",
    "gujarat_10_properties_spatial_attributes_gujrat.csv": "10_properties_spatial_attributes_gujrat.csv",
    "gujarat_industrial_estates_all_12_tables_csv.zip": "gujarat_industrial_estates_all_12_tables_csv.zip",
    "gujarat_industrial_parks.csv": "gujarat_industrial_parks.csv",
    "gujarat_industrial_parks.geojson": "gujarat_industrial_parks.geojson",
    "gujarat_industrial_parks.json": "gujarat_industrial_parks.json",
    "gujarat_Industrial_Parks_and_GIDC_Estates.csv": "Gujarat_Industrial_Parks_and_GIDC_Estates.csv",
}

def is_comment_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    t = s.lstrip('"“”\'')
    return t.startswith("#")

def is_blank_or_separator(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    t = s.strip(' \t",\'“”')
    t = t.replace(",", "").strip()
    return t == ""

def clean_comment(line: str) -> str:
    """Strip leading # / quotes / trailing commas for preamble parsing."""
    s = line.strip()
    # remove trailing comma runs like ',,,,,'  (07 file)
    s = re.sub(r'(,+")?$', '', s)
    s = s.strip().rstrip(',')
    # strip leading quotes then #
    t = s.lstrip('"“”\' ')
    if t.startswith("#"):
        t = t[1:]
    return t.strip().strip('"').strip()

def parse_preamble(path: Path) -> dict:
    out = {"table_name": "", "display": "", "order": "", "total_declared": "",
           "export_ts": "", "data_source": "", "description": "", "pk": "", "fk": "",
           "coldefs": [], "raw_source_lines": []}
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception as e:
        return {"parse_error": str(e)}
    in_coldefs = False
    for l in lines:
        if not is_comment_line(l):
            if out["coldefs"] or out["table_name"]:
                # check if this is header (non-blank non-comment) -> stop
                if not is_blank_or_separator(l):
                    break
            continue
        c = clean_comment(l)
        if c == "Gujarat Industrial Parks Catalog Export":
            if not out["display"]:
                out["display"] = "Gujarat Industrial Parks Catalog"
            if not out["table_name"]:
                out["table_name"] = "catalog-312"
            in_coldefs = False
        elif c.startswith("Table Name:"):
            v = c.split("Table Name:", 1)[1].strip()
            # e.g. "states (States Master)" or "industrial_parks (Industrial Parks & GIDC Estates (312 Estates))"
            m = re.match(r'(\S+)\s*\((.*)\)\s*$', v)
            if m:
                out["table_name"] = m.group(1)
                out["display"] = m.group(2)
            else:
                out["table_name"] = v
            in_coldefs = False
        elif c.startswith("Table Order:"):
            out["order"] = c.split("Table Order:", 1)[1].strip()
            in_coldefs = False
        elif c.startswith("Total Records:"):
            out["total_declared"] = c.split("Total Records:", 1)[1].strip()
            in_coldefs = False
        elif c.startswith("Total Estates"):
            # catalog-export variant: "# Total Estates,312"
            out["total_declared"] = c.split("Total Estates", 1)[1].lstrip(",: ").strip() + " estates"
            if not out["table_name"]:
                out["table_name"] = "catalog-312"
            if not out["display"]:
                out["display"] = "Gujarat Industrial Parks Catalog"
            in_coldefs = False
        elif c.startswith("Export Timestamp"):
            if "," in c and c.startswith("Export Timestamp,"):
                # catalog variant "# Export Timestamp,2026-..."
                out["export_ts"] = c.split(",", 1)[1].strip()
            else:
                out["export_ts"] = c.split(":", 1)[1].strip() if ":" in c else c
                # keep full after colon(s)
                out["export_ts"] = c.partition(":")[2].strip() if c.startswith("Export Timestamp (UTC)") else out["export_ts"]
            in_coldefs = False
        elif c.startswith("DATA SOURCE:"):
            v = c.split("DATA SOURCE:", 1)[1].strip()
            out["data_source"] = v
            out["raw_source_lines"].append(v)
            in_coldefs = False
        elif c.startswith("Description:"):
            out["description"] = c.split("Description:", 1)[1].strip()
            in_coldefs = False
        elif c.startswith("Primary Key:"):
            out["pk"] = c.split("Primary Key:", 1)[1].strip()
            in_coldefs = False
        elif c.startswith("Foreign Key"):
            # "Foreign Key Constraints: ..."
            out["fk"] = c.split(":", 1)[1].strip() if ":" in c else c
            in_coldefs = False
        elif c.startswith("COLUMN DEFINITIONS"):
            in_coldefs = True
        elif in_coldefs and c.startswith("*"):
            out["coldefs"].append(c)
        elif c.startswith("===") or c.startswith("---"):
            if out["coldefs"]:
                in_coldefs = False
    return out

def analyze_csv(path: Path):
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception as e:
        return {"error": str(e)}
    total = len(text)
    comment = sum(1 for l in text if is_comment_line(l))
    blank = sum(1 for l in text if is_blank_or_separator(l) and not is_comment_line(l))
    header = None
    header_idx = None
    for i, l in enumerate(text):
        if is_blank_or_separator(l) or is_comment_line(l):
            continue
        header = l
        header_idx = i
        break
    if header is None:
        return {"total_lines": total, "comment_lines": comment, "blank_lines": blank,
                "header": "", "columns": [], "n_columns": 0, "data_rows": 0}
    try:
        cols = next(csv.reader([header]))
    except Exception:
        cols = [header]
    cols = [c.strip() for c in cols]
    data_rows = 0
    for l in text[header_idx+1:]:
        if is_blank_or_separator(l) or is_comment_line(l):
            continue
        data_rows += 1
    return {"total_lines": total, "comment_lines": comment, "blank_lines": blank,
            "header": header, "columns": cols, "n_columns": len(cols), "data_rows": data_rows}

def analyze_json(path: Path):
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception as e:
        return {"error": str(e)}
    info = {"json_type": type(obj).__name__}
    if isinstance(obj, list):
        info["n_items"] = len(obj)
    elif isinstance(obj, dict):
        info["keys"] = list(obj.keys())[:20]
        if isinstance(obj.get("features"), list):
            info["n_features"] = len(obj["features"])
        if isinstance(obj.get("parks"), list):
            info["n_parks"] = len(obj["parks"])
        if isinstance(obj.get("_metadata"), dict):
            info["_metadata"] = obj["_metadata"]
    return info

def analyze_zip(path: Path):
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            readme = ""
            try:
                readme = z.read("README_METADATA_AND_DATA_SOURCES.md").decode("utf-8", "replace")
            except Exception:
                pass
            return {"n_entries": len(names), "entries": names, "readme": readme}
    except Exception as e:
        return {"error": str(e)}

# ---- load sources/ verbatim (prefixed with gujarat_; exclude sidecars) ----
sources_content = {}
for p in sorted(SOURCES_DIR.glob("*.txt")):
    if p.name.endswith(".meta.txt"):
        continue
    try:
        t = p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        t = f"<read error: {e}>"
    sources_content[p.name] = t

print("Sources files studied:")
for k, v in sources_content.items():
    print(f" - {k}: {len(v)} chars, {len(v.splitlines())} lines")

# ---- load ZIP README manifest ----
zip_path = DATA_DIR / "gujarat_industrial_estates_all_12_tables_csv.zip"
zip_info = analyze_zip(zip_path)
readme_manifest = zip_info.get("readme", "")

# ---- per-dataset sources mapping (evidence-based; sources/ files now gujarat_-prefixed) ----
# Each entry: list of (source_filename, rationale)
SOURCE_MAP = {
    "gujarat_01_states.csv": [],
    "gujarat_02_districts.csv": [],
    "gujarat_03_subdistricts_talukas.csv": [],
    "gujarat_04_neighborhoods_jurisdictions.csv": [
        ("gujarat_neighbourhood_scapper.txt", "Same institutional attribution: AUDA/VUDA/SUDA + Municipal Tax Records + GIDC notified zones; matches preamble DATA SOURCE verbatim."),
    ],
    "gujarat_05_industrial_parks.csv": [
        ("gujarat_Industail_Parks.txt", "Exact match to preamble DATA SOURCE (GIDC portal, Industrial Policy 2015/2020, GR 21/04/2015, OSM geocoding). Note source filename has typo 'Industail'."),
    ],
    "gujarat_06_anchor_facilities.csv": [],
    "gujarat_07_park_lifecycle_events.csv": [
        ("gujarat_Park_lifecycle_events.txt", "Exact match to preamble DATA SOURCE (Gazette Notifications, GIDC awards, Factory permits, GPCB filings); source file body duplicates this attribution twice."),
    ],
    "gujarat_08_park_annual_metrics.csv": [],
    "gujarat_10_properties_spatial_attributes_gujrat.csv": [
        ("gujarat_Properties & Parcel Spatial Attributes.txt", "Exact match: Sub-Registrar Offices + GUJRERA + GIS hedonic buffers; description line also matches preamble Description verbatim."),
        ("gujarat_Clean Commercial Benchmark Nodes.txt", "Related via FK nearest_clean_commercial_id -> clean_commercial_nodes; explains control-group design (GIFT City SEZ, RERA, SG Highway audits, Taylor et al.). Table 09 lives only inside the ZIP."),
        ("gujarat_Property_Tracker_Transcation.txt", "Downstream pricing panel (table 11) built on these parcels: IGR stamped registry + Jantar/Ready Reckoner 2012-2025 + NHB RESIDEX; columns listed apply to 11_property_transactions.csv (ZIP-only). Note filename typo 'Transcation'."),
    ],
    "gujarat_industrial_estates_all_12_tables_csv.zip": [
        ("gujarat_Industail_Parks.txt", "Covers ZIP table 05_industrial_parks.csv."),
        ("gujarat_neighbourhood_scapper.txt", "Covers ZIP table 04_neighborhoods_jurisdictions.csv."),
        ("gujarat_Park_lifecycle_events.txt", "Covers ZIP table 07_park_lifecycle_events.csv."),
        ("gujarat_Properties & Parcel Spatial Attributes.txt", "Covers ZIP table 10_properties.csv (this repo's gujarat_10_... file is the same table under legacy 'gujrat' suffix)."),
        ("gujarat_Clean Commercial Benchmark Nodes.txt", "Covers ZIP-only table 09_clean_commercial_nodes.csv (IT parks / financial SEZs / shopping nodes as clean control; GIFT City SEZ, RERA, SG Highway, Taylor et al.)."),
        ("gujarat_Property_Tracker_Transcation.txt", "Covers ZIP-only table 11_property_transactions.csv (4,000 sales, market price vs Jantar circle rate, columns enumerated) and by extension 12_did_panel_designations.csv."),
        ("gujarat_property_price_scapper.txt", "EMPTY FILE (0 bytes) — placeholder with no content; likely intended price-scraper note for tables 11/12 but contributes nothing. Recorded explicitly so absence is not mistaken for evidence."),
    ],
    "gujarat_industrial_parks.csv": [
        ("gujarat_Industail_Parks.txt", "Same 312-estate universe as module-05 table: GIDC portal + Policy 2015/2020 + GR 21/04/2015 + OSM; flat catalog export variant (15 cols incl. Anchors_Count)."),
    ],
    "gujarat_industrial_parks.geojson": [
        ("gujarat_Industail_Parks.txt", "Spatial (GeoJSON FeatureCollection, 312 features) rendering of the same 312-estate catalog; OSM geocoding per source note."),
    ],
    "gujarat_industrial_parks.json": [
        ("gujarat_Industail_Parks.txt", "JSON variant of the 312-estate catalog (_metadata + parks[312]); same institutional sources."),
    ],
    "gujarat_Industrial_Parks_and_GIDC_Estates.csv": [
        ("gujarat_Industail_Parks.txt", "Human-readable 312-row directory variant (12 cols with contacts/notes/source); same GIDC/Policy/GR/OSM provenance."),
    ],
}

# original (pre-prefix) names of the 7 source notes, for provenance
SOURCE_ORIGINALS = {
    "gujarat_Clean Commercial Benchmark Nodes.txt": "Clean Commercial Benchmark Nodes.txt",
    "gujarat_Industail_Parks.txt": "Industail_Parks.txt",
    "gujarat_neighbourhood_scapper.txt": "neighbourhood_scapper.txt",
    "gujarat_Park_lifecycle_events.txt": "Park_lifecycle_events.txt",
    "gujarat_Properties & Parcel Spatial Attributes.txt": "Properties & Parcel Spatial Attributes.txt",
    "gujarat_property_price_scapper.txt": "property_price_scapper.txt",
    "gujarat_Property_Tracker_Transcation.txt": "Property_Tracker_Transcation.txt",
}

def is_data_file(p: Path) -> bool:
    if not p.is_file():
        return False
    if p.name.startswith("."):
        return False
    if p.suffix == ".txt" and p.name.endswith(".meta.txt"):
        return False
    if p.name in ("gujarat_index.csv", "gujarat_index.json"):
        return False
    if p.name.endswith(".meta.txt"):
        return False
    return True

data_files = sorted([p for p in DATA_DIR.iterdir() if is_data_file(p)], key=lambda p: p.name.lower())
print(f"Enriching {len(data_files)} data files")

records = []
now_iso = datetime.now(timezone.utc).isoformat()
for fpath in data_files:
    final_name = fpath.name
    orig = TRUE_ORIGINALS.get(final_name, final_name)
    renamed = orig != final_name
    stat = fpath.stat()
    mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    ext = fpath.suffix.lower()
    if ext == ".csv":
        info = analyze_csv(fpath)
        pre = parse_preamble(fpath)
    elif ext in (".json", ".geojson"):
        info = analyze_json(fpath)
        pre = {}
    elif ext == ".zip":
        info = {"n_entries": zip_info.get("n_entries", ""), "entries": zip_info.get("entries", [])}
        pre = {}
    else:
        info = {}
        pre = {}

    matched = SOURCE_MAP.get(final_name, [])
    # build enriched TXT
    L = []
    L.append(f"meta_file: {final_name}.meta.txt")
    L.append(f"file_name: {final_name}")
    L.append(f"original_name: {orig}")
    L.append(f"prefix: {PREFIX}")
    L.append(f"renamed: {renamed}")
    L.append(f"extension: {ext}")
    L.append(f"size_bytes: {stat.st_size}")
    L.append(f"modified_utc: {mtime_utc}")
    L.append("")
    L.append("--- TABLE / DATASET ---")
    if pre.get("table_name"):
        L.append(f"table_name: {pre.get('table_name','')}")
        L.append(f"display_title: {pre.get('display','')}")
        L.append(f"module_order: {pre.get('order','')}")
        L.append(f"description: {pre.get('description','')}")
        L.append(f"total_records_declared: {pre.get('total_declared','')}")
        L.append(f"export_timestamp_utc: {pre.get('export_ts','')}")
    elif ext in (".json", ".geojson") and isinstance(info.get("_metadata"), dict):
        md = info["_metadata"]
        L.append(f"table_name: (catalog export, not a numbered 01-12 module)")
        L.append(f"display_title: {md.get('project','')}")
        L.append(f"description: {md.get('jurisdiction','')} | vintage {md.get('data_vintage','')} | records {md.get('record_count','')}")
        L.append(f"export_timestamp_utc: {md.get('export_timestamp','')}")
    elif final_name == "gujarat_industrial_estates_all_12_tables_csv.zip":
        L.append("table_name: (archive of 12 core tables 01-12 + README_METADATA_AND_DATA_SOURCES.md)")
        L.append("display_title: 12 Core Database Tables Export Archive")
        L.append("description: One-click ZIP bundle of all 12 schema tables; includes tables 09/11/12 NOT present as standalone files in data/ root.")
    elif final_name in ("gujarat_industrial_parks.csv", "gujarat_Industrial_Parks_and_GIDC_Estates.csv"):
        L.append("table_name: (flat 312-estate catalog export, cf. module-05 industrial_parks)")
        L.append("display_title: Gujarat Industrial Parks Catalog")
        L.append("description: 312 GIDC + private estates with district/taluka, contacts, area, notification year, CETP flag.")
    else:
        L.append("table_name: (none declared in preamble)")
    L.append("")
    L.append("--- KEYS ---")
    if pre.get("pk"):
        L.append(f"primary_key: {pre.get('pk','')}")
        L.append(f"foreign_keys: {pre.get('fk','')}")
    elif final_name == "gujarat_10_properties_spatial_attributes_gujrat.csv":
        L.append("primary_key: property_id")
        L.append("foreign_keys: neighborhood_id -> neighborhoods_jurisdictions, nearest_park_id -> industrial_parks, nearest_clean_commercial_id -> clean_commercial_nodes")
    elif ext in (".json", ".geojson"):
        L.append("primary_key: park_id (per parks[]/features[].properties)")
        L.append("foreign_keys: (catalog export; relational keys defined in 01-12 modules, not in this file)")
    elif ext == ".zip":
        L.append("primary_key: (per-table; see README manifest: state_id, district_id, taluka_id, neighborhood_id, park_id, anchor_id, event_id, metric_id, node_id, property_id, transaction_id, designation_id)")
        L.append("foreign_keys: (per-table chain states->districts->talukas->neighborhoods/parks->anchors/events/metrics/properties->transactions->did_panel)")
    else:
        L.append("primary_key: (see preamble)")
    L.append("")
    L.append("--- DATA PROFILE ---")
    if ext == ".csv":
        L.append(f"header: {info.get('header','')}")
        L.append(f"n_columns: {info.get('n_columns','')}")
        L.append(f"columns: {', '.join(info.get('columns', []))}")
        L.append(f"data_rows_observed: {info.get('data_rows','')}")
        L.append(f"total_lines: {info.get('total_lines','')}")
        L.append(f"comment_lines(#): {info.get('comment_lines','')}")
        L.append(f"blank_or_separator_lines: {info.get('blank_lines','')}")
        if info.get("error"):
            L.append(f"error: {info['error']}")
    elif ext in (".json", ".geojson"):
        if info.get("error"):
            L.append(f"error: {info['error']}")
        else:
            L.append(f"json_type: {info.get('json_type','')}")
            for k in ("n_items", "n_features", "n_parks"):
                if k in info:
                    L.append(f"{k}: {info[k]}")
            if info.get("keys"):
                L.append(f"keys: {', '.join(map(str, info['keys']))}")
            if isinstance(info.get("_metadata"), dict):
                md = info["_metadata"]
                L.append(f"catalog_project: {md.get('project','')}")
                L.append(f"catalog_jurisdiction: {md.get('jurisdiction','')}")
                L.append(f"catalog_vintage: {md.get('data_vintage','')}")
                L.append(f"catalog_source: {md.get('source','')}")
                L.append(f"catalog_record_count: {md.get('record_count','')}")
    elif ext == ".zip":
        L.append(f"n_entries: {info.get('n_entries','')}")
        for e in info.get("entries", []):
            L.append(f"  zip_entry: {e} ({zipfile.ZipFile(fpath).getinfo(e).file_size} bytes)")
    L.append("")
    if ext == ".csv" and pre.get("coldefs"):
        L.append("--- COLUMN DEFINITIONS (verbatim preamble) ---")
        for cd in pre["coldefs"]:
            L.append(f"# {cd}")
        L.append("")
    L.append("--- DATA SOURCE (preamble verbatim) ---")
    if pre.get("data_source"):
        L.append(pre["data_source"])
    elif final_name == "gujarat_industrial_estates_all_12_tables_csv.zip":
        L.append("(per-table sources; see README manifest + SOURCES FOLDER EVIDENCE below; preamble N/A for archive)")
    elif ext in (".json", ".geojson") and isinstance(info.get("_metadata"), dict):
        L.append(str(info["_metadata"].get("source", "")))
    else:
        L.append("(no DATA SOURCE line in preamble; see SOURCES FOLDER EVIDENCE)")
    L.append("")
    L.append("--- SOURCES FOLDER EVIDENCE (data/sources/*.txt, studied 2026-10-03) ---")
    if matched:
        for i, (sfn, rationale) in enumerate(matched, 1):
            content = sources_content.get(sfn, "<missing>")
            L.append(f"[{i}] sources_file: sources/{sfn} ({len(content.encode('utf-8'))} bytes, {len(content.splitlines())} lines)")
            L.append(f"    mapping_rationale: {rationale}")
            L.append(f"    content_verbatim:")
            for cl in content.splitlines() or ["<EMPTY FILE - 0 lines>"]:
                L.append(f"      | {cl}" if cl.strip() else "      |")
    else:
        L.append("No dedicated file in data/sources/ for this dataset (all 7 source files were read; none matches).")
        L.append("Attribution rests on the CSV preamble DATA SOURCE + ZIP README manifest.")
        # still note the empty scraper so readers know it was checked
        if final_name.startswith("gujarat_08_") or final_name.startswith("gujarat_06_"):
            L.append("Checked: sources/gujarat_property_price_scapper.txt is EMPTY (0 bytes) - no evidence there either.")
    # filename typo notes (sources/ files are gujarat_-prefixed; legacy spellings preserved)
    if "Industail" in "".join([m[0] for m in matched]):
        L.append("NOTE: source filename is misspelled 'gujarat_Industail_Parks.txt' (should be Industrial); quoted exactly to avoid confusion.")
    if "Transcation" in "".join([m[0] for m in matched]):
        L.append("NOTE: source filename is misspelled 'gujarat_Property_Tracker_Transcation.txt' (should be Transaction); quoted exactly.")
    if final_name == "gujarat_10_properties_spatial_attributes_gujrat.csv":
        L.append("NOTE: this file's own name contains legacy misspelling '..._gujrat.csv'; inside the ZIP the same table is correctly named 10_properties.csv.")
    L.append("")
    L.append("--- ARCHIVE / RELATIONS ---")
    if final_name == "gujarat_industrial_estates_all_12_tables_csv.zip":
        L.append("Contains canonical 01-12 tables incl. three tables with NO standalone file in data/ root:")
        L.append("  - 09_clean_commercial_nodes.csv (see Clean Commercial Benchmark Nodes.txt)")
        L.append("  - 11_property_transactions.csv (see Property_Tracker_Transcation.txt for columns + IGR/Jantar/NHB provenance)")
        L.append("  - 12_did_panel_designations.csv (DiD matrix; Taylor et al. + Arora spec per README)")
        L.append("Standalone-file deltas: root has gujarat_10_properties_spatial_attributes_gujrat.csv (= ZIP 10_properties.csv); root LACKS 09/11/12 standalone.")
    elif final_name == "gujarat_10_properties_spatial_attributes_gujrat.csv":
        L.append("ZIP twin: 10_properties.csv inside gujarat_industrial_estates_all_12_tables_csv.zip (same 800-row table).")
        L.append("FK graph: neighborhoods_jurisdictions <- properties -> industrial_parks + clean_commercial_nodes (ZIP table 09); downstream: property_transactions (ZIP 11) -> did_panel (ZIP 12).")
    elif final_name.startswith("gujarat_0"):
        L.append(f"ZIP twin: {orig} inside gujarat_industrial_estates_all_12_tables_csv.zip (same module table).")
    elif final_name in ("gujarat_industrial_parks.csv", "gujarat_industrial_parks.json", "gujarat_industrial_parks.geojson", "gujarat_Industrial_Parks_and_GIDC_Estates.csv"):
        L.append("Sibling exports of the same 312-estate universe as module-05 gujarat_05_industrial_parks.csv (different projections: normalized module table vs flat catalog vs JSON vs GeoJSON vs human directory).")
    L.append("")
    L.append("--- PROVENANCE ---")
    L.append(f"meta_created_utc: {now_iso}")
    L.append("generator: data/.quarantine/enrich_meta.py (preamble parser + sources/ reader + ZIP README + JSON _metadata)")
    L.append("sources_consulted: CSV preamble + data/sources/*.txt (7 files) + ZIP README_METADATA_AND_DATA_SOURCES.md + JSON _metadata + observed row/col counts")
    L.append("")
    (DATA_DIR / (final_name + ".meta.txt")).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"META enriched: {final_name}.meta.txt ({len(L)} lines)")

    # index record
    if ext == ".csv":
        dr = info.get("data_rows", "")
        nc = info.get("n_columns", "")
        cols = ", ".join(info.get("columns", []))
    elif ext in (".json", ".geojson"):
        dr = info.get("n_features", info.get("n_parks", info.get("n_items", "")))
        nc, cols = "", ""
    else:
        dr = info.get("n_entries", "")
        nc, cols = "", ""
    src_files = "; ".join([m[0] for m in matched])
    # short sources note
    if not matched:
        src_note = "No dedicated sources/ file; preamble+README only."
    elif len(matched) == 1:
        src_note = matched[0][1][:160]
    else:
        src_note = f"{len(matched)} sources/ files (direct + FK-related); see meta."
    records.append({
        "file_name": final_name,
        "file_role": "data",
        "original_name": orig,
        "renamed": renamed,
        "extension": ext,
        "size_bytes": stat.st_size,
        "modified_utc": mtime_utc,
        "meta_file": final_name + ".meta.txt",
        "table_name": (pre.get("table_name", "") or ("catalog-312" if final_name in ("gujarat_industrial_parks.csv", "gujarat_Industrial_Parks_and_GIDC_Estates.csv") else "")) if ext == ".csv" else ("catalog-312" if ext in (".json", ".geojson") or final_name.startswith("gujarat_industrial_parks") or final_name.startswith("gujarat_Industrial") else ("archive-12" if ext == ".zip" else "")),
        "display_title": pre.get("display", "") or ("Gujarat Industrial Parks Catalog" if final_name in ("gujarat_industrial_parks.csv", "gujarat_Industrial_Parks_and_GIDC_Estates.csv") else ""),
        "description": pre.get("description", "") if pre.get("description") else (info.get("_metadata", {}).get("project", "") if isinstance(info.get("_metadata"), dict) else ("12-table ZIP archive" if ext == ".zip" else ("312-estate flat catalog (cf. module-05 industrial_parks)" if final_name in ("gujarat_industrial_parks.csv", "gujarat_Industrial_Parks_and_GIDC_Estates.csv") else ""))),
        "primary_key": pre.get("pk", ""),
        "preamble_source": pre.get("data_source", "") if pre.get("data_source") else (info.get("_metadata", {}).get("source", "") if isinstance(info.get("_metadata"), dict) else ""),
        "sources_files": src_files,
        "sources_note": src_note,
        "export_timestamp": pre.get("export_ts", "") if pre.get("export_ts") else (info.get("_metadata", {}).get("export_timestamp", "") if isinstance(info.get("_metadata"), dict) else ""),
        "data_rows": dr,
        "n_columns": nc,
        "columns": cols,
    })

# ---- source-note metas + index rows (sources/ files themselves are prefixed too) ----
# reverse map: source file -> datasets that cite it
reverse_map = {}
for ds, lst in SOURCE_MAP.items():
    for sfn, _ in lst:
        reverse_map.setdefault(sfn, []).append(ds)
for sfn in sorted(sources_content.keys()):
    spath = SOURCES_DIR / sfn
    if not spath.exists():
        continue
    sorig = SOURCE_ORIGINALS.get(sfn, sfn)
    sstat = spath.stat()
    smtime = datetime.fromtimestamp(sstat.st_mtime, tz=timezone.utc).isoformat()
    content = sources_content[sfn]
    cited_by = sorted(reverse_map.get(sfn, []))
    SL = []
    SL.append(f"meta_file: {sfn}.meta.txt")
    SL.append(f"file_name: sources/{sfn}")
    SL.append(f"original_name: sources/{sorig}")
    SL.append(f"prefix: {PREFIX}")
    SL.append(f"renamed: {sorig != sfn}")
    SL.append(f"extension: .txt")
    SL.append(f"size_bytes: {sstat.st_size}")
    SL.append(f"modified_utc: {smtime}")
    SL.append("")
    SL.append("--- ROLE ---")
    SL.append("file_role: source-note (provenance note in data/sources/, not a dataset)")
    SL.append(f"description: Provenance/method note cited by {len(cited_by)} dataset(s).")
    if sstat.st_size == 0:
        SL.append("NOTE: EMPTY FILE (0 bytes) - placeholder with no content.")
    SL.append("")
    SL.append("--- CONTENT VERBATIM ---")
    for cl in content.splitlines() or ["<EMPTY FILE - 0 lines>"]:
        SL.append(f"  | {cl}" if cl.strip() else "  |")
    SL.append("")
    SL.append("--- CITED BY (datasets whose meta quotes this note) ---")
    if cited_by:
        for ds in cited_by:
            SL.append(f"  - {ds}")
    else:
        SL.append("  (not directly cited; general background)")
    if "Industail" in sfn:
        SL.append("NOTE: filename misspelled 'Industail' (should be Industrial); quoted exactly.")
    if "Transcation" in sfn:
        SL.append("NOTE: filename misspelled 'Transcation' (should be Transaction); quoted exactly.")
    SL.append("")
    SL.append("--- PROVENANCE ---")
    SL.append(f"meta_created_utc: {datetime.now(timezone.utc).isoformat()}")
    SL.append("generator: data/.quarantine/enrich_meta.py (sources/ pass)")
    (SOURCES_DIR / (sfn + ".meta.txt")).write_text("\n".join(SL) + "\n", encoding="utf-8")
    print(f"META source: sources/{sfn}.meta.txt")
    records.append({
        "file_name": f"sources/{sfn}",
        "file_role": "source-note",
        "original_name": f"sources/{sorig}",
        "renamed": sorig != sfn,
        "extension": ".txt",
        "size_bytes": sstat.st_size,
        "modified_utc": smtime,
        "meta_file": f"sources/{sfn}.meta.txt",
        "table_name": "(source-note)",
        "display_title": sfn,
        "description": (content.strip().splitlines()[0][:200] if content.strip() else "(empty file)"),
        "primary_key": "",
        "preamble_source": "",
        "sources_files": "",
        "sources_note": f"Cited by {len(cited_by)} dataset(s): {', '.join(cited_by)[:200]}" if cited_by else "Background note.",
        "export_timestamp": "",
        "data_rows": len(content.splitlines()),
        "n_columns": "",
        "columns": "",
    })

records.sort(key=lambda r: r["file_name"].lower())
index_csv = DATA_DIR / "gujarat_index.csv"
index_json = DATA_DIR / "gujarat_index.json"
with open(index_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["file_name", "file_role", "original_name", "renamed", "extension", "size_bytes", "modified_utc", "meta_file", "table_name", "display_title", "description", "primary_key", "preamble_source", "sources_files", "sources_note", "export_timestamp", "data_rows", "n_columns", "columns"])
    w.writeheader()
    w.writerows(records)
payload = {
    "prefix": PREFIX,
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "n_files": len(records),
    "note": "Enriched index: each data row joins observed file stats + preamble (table/order/PK/FK/source) + data/sources/*.txt evidence. TXT sidecar holds verbatim excerpts. Index covers 14 data files + 7 source-notes (21 rows); meta/index artifacts excluded to avoid self-reference. data/sources/ files are gujarat_-prefixed (legacy spellings Industail/Transcation preserved exactly).",
    "sources_folder": {k: {"bytes": len(v.encode('utf-8')), "lines": len(v.splitlines()), "head": v[:400]} for k, v in sources_content.items()},
    "files": records,
}
index_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"INDEX enriched: {index_csv.name} + {index_json.name} ({len(records)} files)")

for idx_file in (index_csv, index_json):
    st = idx_file.stat()
    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    meta = DATA_DIR / (idx_file.name + ".meta.txt")
    meta.write_text(
        f"meta_file: {meta.name}\nfile_name: {idx_file.name}\noriginal_name: {idx_file.name}\n"
        f"prefix: {PREFIX}\nrenamed: False\nextension: {idx_file.suffix.lower()}\n"
        f"size_bytes: {st.st_size}\nmodified_utc: {mtime}\n"
        f"description: Enriched master index joining preamble + sources/ evidence for all {len(records)} files (14 data + 7 source-notes).\n"
        f"enrichment: file_role/table_name/display_title/description/primary_key/preamble_source/sources_files/sources_note/export_timestamp per row; verbatim sources/ excerpts live in per-file metas.\n"
        f"sources_folder: 7 prefixed files studied ({', '.join(sorted(sources_content.keys()))}); gujarat_property_price_scapper.txt is EMPTY (0 bytes).\n"
        f"meta_created_utc: {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )
    print(f"META: {meta.name}")
