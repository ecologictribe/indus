from pathlib import Path
from datetime import datetime, timezone
import zipfile

pkg = Path(r"D:\IndustrialEstates\data\gujarat_full_package_sources_data_meta.zip")
st = pkg.stat()
mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
z = zipfile.ZipFile(pkg)
names = z.namelist()
lines = [
    "meta_file: " + pkg.name + ".meta.txt",
    "file_name: " + pkg.name,
    "original_name: " + pkg.name,
    "prefix: gujarat_",
    "renamed: False",
    "extension: .zip",
    "size_bytes: %d" % st.st_size,
    "modified_utc: " + mtime,
    "",
    "--- PACKAGE ---",
    "description: Full distributable bundle: 14 datasets + 16 root metas + index (csv+json) + 2 index metas + 7 source-notes + 7 source metas = 46 files.",
    "n_files_inside: %d" % len(names),
    "layout: flat gujarat_* data + meta at top level; sources/gujarat_* notes + metas under sources/.",
    "excludes: data/.quarantine/ helper scripts; this package meta itself (lives alongside, not inside, to avoid self-reference).",
    "",
    "--- CONTENTS ---",
]
for n in names:
    lines.append("  - %s (%d bytes)" % (n, z.getinfo(n).file_size))
lines += [
    "",
    "--- READING ---",
    "CSVs carry a commented preamble (lines starting with #); load with pandas read_csv(..., comment='#').",
    "Each dataset has a <file>.meta.txt sidecar with table/PK/FK/source evidence; gujarat_index.csv/.json catalogues all 21 (14 data + 7 source-notes).",
    "sources/ notes retain legacy spellings (Industail, Transcation) quoted exactly; gujarat_property_price_scapper.txt is EMPTY (0 bytes).",
    "",
    "--- PROVENANCE ---",
    "meta_created_utc: " + datetime.now(timezone.utc).isoformat(),
    "generator: manual zip step after data/.quarantine/enrich_meta.py",
]
Path(str(pkg) + ".meta.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote " + pkg.name + ".meta.txt")
