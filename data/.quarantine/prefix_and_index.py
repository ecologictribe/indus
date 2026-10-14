"""Prefix files with gujarat_, write TXT sidecars, build index (csv+json)."""
import csv, json, zipfile
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(r"D:\IndustrialEstates\data")
PREFIX = "gujarat_"

# True originals before any rename (from pre-rename listing 2026-10-03)
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
    # strip leading quote chars then check for #
    t = s.lstrip('"\u201c\u201d\'')
    return t.startswith("#")

def is_blank_or_separator(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    # lines like ',,,,,' or '"",,,,' are effectively blank separators
    t = s.strip(' \t",\'\u201c\u201d')
    # remove commas left after stripping quotes/spaces
    t = t.replace(",", "").strip()
    return t == ""

def is_data_file(p: Path) -> bool:
    if not p.is_file():
        return False
    if p.name.startswith("."):
        return False
    # exclude our own artifacts
    if p.suffix == ".txt" and p.name.endswith(".meta.txt"):
        return False
    if p.name in ("gujarat_index.csv", "gujarat_index.json"):
        return False
    if p.name.endswith(".meta.txt"):
        return False
    # exclude quarantine dir contents (different dir anyway)
    return True

def analyze_csv(path: Path):
    """Return dict with header, cols, data_rows, total_lines, comment_lines."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception as e:
        return {"error": str(e)}
    total = len(text)
    comment = sum(1 for l in text if is_comment_line(l))
    blank = sum(1 for l in text if is_blank_or_separator(l) and not is_comment_line(l))
    # find first non-comment, non-blank line = header
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
        # geojson feature count
        if obj.get("type") == "FeatureCollection" and isinstance(obj.get("features"), list):
            info["n_features"] = len(obj["features"])
        if isinstance(obj.get("features"), list):
            info["n_features"] = len(obj["features"])
        if isinstance(obj.get("parks"), list):
            info["n_parks"] = len(obj["parks"])
    return info

def analyze_zip(path: Path):
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            return {"n_entries": len(names), "entries": names[:50]}
    except Exception as e:
        return {"error": str(e)}

# 1. Discover
all_files = sorted([p for p in DATA_DIR.iterdir() if is_data_file(p)], key=lambda p: p.name)
print(f"Found {len(all_files)} data files")

# 2. Rename
mapping = []  # (original, final)
for p in all_files:
    name = p.name
    if name.lower().startswith(PREFIX):
        # normalize prefix case to lowercase
        target_name = PREFIX + name[len(PREFIX):]
    else:
        target_name = PREFIX + name
    target = DATA_DIR / target_name
    if target_name != name:
        if target_name.lower() == name.lower():
            # case-only rename (Windows is case-insensitive): go via temp name
            tmp = DATA_DIR / (name + ".tmp_rename")
            p.rename(tmp)
            tmp.rename(target)
            print(f"RENAMED (case-normalized): {name} -> {target_name}")
        else:
            if target.exists():
                raise SystemExit(f"COLLISION: {name} -> {target_name} already exists")
            p.rename(target)
            print(f"RENAMED: {name} -> {target_name}")
        mapping.append((name, target_name))
    else:
        print(f"KEPT: {name} (already prefixed)")
        mapping.append((name, name))

orig_lookup = dict(mapping)
# Override with true pre-rename originals where known (fixes re-run losing history)
for final_name, true_orig in TRUE_ORIGINALS.items():
    # mapping is (seen_orig, final); replace seen_orig with true_orig
    for i, (seen_orig, fin) in enumerate(mapping):
        if fin == final_name:
            mapping[i] = (true_orig, fin)
orig_lookup = dict((fin, orig) for orig, fin in mapping)
# rebuild mapping as (orig, final) already fixed; need reverse for later loop? keep (orig, final)
# mapping currently (orig, final) after fix above, good.

# 3. Analyze finals + write meta txt
records = []
for orig, final_name in sorted(mapping, key=lambda x: x[1].lower()):
    fpath = DATA_DIR / final_name
    stat = fpath.stat()
    mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    ext = fpath.suffix.lower()
    info = {}
    if ext == ".csv":
        info = analyze_csv(fpath)
    elif ext in (".json", ".geojson"):
        info = analyze_json(fpath)
    elif ext == ".zip":
        info = analyze_zip(fpath)
    meta_name = final_name + ".meta.txt"
    meta_path = DATA_DIR / meta_name
    lines = []
    lines.append(f"meta_file: {meta_name}")
    lines.append(f"file_name: {final_name}")
    lines.append(f"original_name: {orig}")
    lines.append(f"prefix: {PREFIX}")
    lines.append(f"renamed: {orig != final_name}")
    lines.append(f"extension: {ext}")
    lines.append(f"size_bytes: {stat.st_size}")
    lines.append(f"modified_utc: {mtime_utc}")
    if ext == ".csv":
        lines.append(f"total_lines: {info.get('data_rows', '') and info.get('total_lines', '')}")
        lines.append(f"comment_lines(#): {info.get('comment_lines', '')}")
        lines.append(f"blank_lines: {info.get('blank_lines', '')}")
        lines.append(f"header: {info.get('header', '')}")
        lines.append(f"n_columns: {info.get('n_columns', '')}")
        lines.append(f"columns: {', '.join(info.get('columns', []))}")
        lines.append(f"data_rows: {info.get('data_rows', '')}")
        if "error" in info:
            lines.append(f"error: {info['error']}")
    elif ext in (".json", ".geojson"):
        if "error" in info:
            lines.append(f"error: {info['error']}")
        else:
            lines.append(f"json_type: {info.get('json_type', '')}")
            if "n_items" in info:
                lines.append(f"n_items: {info['n_items']}")
            if "n_features" in info:
                lines.append(f"n_features: {info['n_features']}")
            if "n_parks" in info:
                lines.append(f"n_parks: {info['n_parks']}")
            if "keys" in info:
                lines.append(f"keys: {', '.join(map(str, info['keys']))}")
    elif ext == ".zip":
        if "error" in info:
            lines.append(f"error: {info['error']}")
        else:
            lines.append(f"n_entries: {info.get('n_entries', '')}")
            for e in info.get("entries", []):
                lines.append(f"  zip_entry: {e}")
    else:
        lines.append("note: generic file, no row-level stats")
    lines.append(f"meta_created_utc: {datetime.now(timezone.utc).isoformat()}")
    meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"META: {meta_name}")
    rec = {
        "file_name": final_name,
        "original_name": orig,
        "renamed": orig != final_name,
        "extension": ext,
        "size_bytes": stat.st_size,
        "modified_utc": mtime_utc,
        "meta_file": meta_name,
        "data_rows": info.get("data_rows", "") if ext == ".csv" else info.get("n_features", info.get("n_parks", info.get("n_items", ""))) if ext in (".json", ".geojson") else info.get("n_entries", "") if ext == ".zip" else "",
        "n_columns": info.get("n_columns", "") if ext == ".csv" else "",
        "columns": ", ".join(info.get("columns", [])) if ext == ".csv" and info.get("columns") else "",
    }
    records.append(rec)

records.sort(key=lambda r: r["file_name"].lower())

# 4. Write index csv + json
index_csv = DATA_DIR / "gujarat_index.csv"
index_json = DATA_DIR / "gujarat_index.json"
with open(index_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["file_name", "original_name", "renamed", "extension", "size_bytes", "modified_utc", "meta_file", "data_rows", "n_columns", "columns"])
    w.writeheader()
    w.writerows(records)
payload = {
    "prefix": PREFIX,
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "n_files": len(records),
    "note": "Index covers data files only; each has a <file>.meta.txt sidecar. Index files themselves excluded to avoid self-reference.",
    "files": records,
}
index_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"INDEX: {index_csv.name} + {index_json.name} ({len(records)} files)")

# 5. Meta for the index files themselves
for idx_file in (index_csv, index_json):
    st = idx_file.stat()
    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    meta = DATA_DIR / (idx_file.name + ".meta.txt")
    meta.write_text(
        f"meta_file: {meta.name}\nfile_name: {idx_file.name}\noriginal_name: {idx_file.name}\n"
        f"prefix: {PREFIX}\nrenamed: False\nextension: {idx_file.suffix.lower()}\n"
        f"size_bytes: {st.st_size}\nmodified_utc: {mtime}\nnote: master index file listing all {len(records)} data files\n"
        f"meta_created_utc: {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )
    print(f"META: {meta.name}")
