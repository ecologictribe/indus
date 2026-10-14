"""
Dataset Integrity & Anti-Synthetic Guardrail Engine
=====================================================
Mandatory quality gate enforcing the 'Zero Synthetic Leakage' policy:
1. Detects pseudo-random/algorithmic generation in data pipelines (random, np.random, faker).
2. Prevents multi-year blanket attribution of single-year circulars.
3. Detects fabricated URL patterns (e.g. archive_{year}).
4. Rejects stub/fake PDF files (< 1KB).
5. Enforces step-function persistence over artificial mathematical interpolation.
"""

import os
import re
import csv
import sys
import glob
import hashlib
from typing import List, Dict, Tuple

class GuardrailViolation:
    def __init__(self, severity: str, rule: str, target: str, message: str, line_no: int = None):
        self.severity = severity # 'FATAL' or 'WARNING'
        self.rule = rule
        self.target = target
        self.message = message
        self.line_no = line_no

    def __str__(self):
        line_str = f":L{self.line_no}" if self.line_no else ""
        return f"[{self.severity}] [{self.rule}] {self.target}{line_str} -> {self.message}"


class DatasetIntegrityGuardrail:
    FORBIDDEN_CODE_PATTERNS = [
        (r'np\.random\.(choice|uniform|randint|normal|rand)', "NumPy random generator used in data creation"),
        (r'random\.(choice|uniform|randint|sample)', "Standard random generator used in data creation"),
        (r'Faker\(', "Faker library used for data fabrication"),
        (r'\*\*\s*\(\s*(?:yr|year)\s*-\s*20\d\d\s*\)', "CAGR compounding formula used to project historical prices"),
    ]

    FABRICATED_URL_PATTERNS = [
        r'allotment_archive_\d{4}',
        r'archive_\d{4}',
        r'fake_url',
        r'dummy_source',
        r'placeholder',
    ]

    def audit_python_file(self, filepath: str) -> List[GuardrailViolation]:
        violations = []
        if "tests" in filepath or "test_" in filepath or "guardrail" in filepath:
            return violations # Test suites are exempted from code scan

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(f, 1):
                clean_line = line.strip()
                if clean_line.startswith('#'):
                    continue
                for pattern, desc in self.FORBIDDEN_CODE_PATTERNS:
                    if re.search(pattern, clean_line):
                        violations.append(GuardrailViolation(
                            severity="FATAL",
                            rule="NO_SYNTHETIC_CODE_IN_PIPELINE",
                            target=filepath,
                            message=f"{desc} detected: '{clean_line[:80]}'",
                            line_no=idx
                        ))
        return violations

    def audit_csv_dataset(self, filepath: str) -> List[GuardrailViolation]:
        violations = []
        rows = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            for r in reader:
                if not r or r[0].startswith('#') or r[0].startswith('"#'):
                    continue
                rows.append(r)

        if not rows:
            return violations

        header = rows[0]
        data_rows = [dict(zip(header, r)) for r in rows[1:] if len(r) == len(header)]

        # Check 1: Multi-Year Single Circular Attribution
        # If dataset has financial_year / year and source_document / source_circular_no
        doc_years = {}
        for row in data_rows:
            fy = row.get('financial_year') or row.get('year') or row.get('calendar_year')
            doc = row.get('source_document') or row.get('source_circular_no') or row.get('source_id')
            provenance_status = (row.get('provenance_status') or row.get('confidence_level') or row.get('audit_notes') or "").upper()

            if doc and fy:
                doc_years.setdefault(doc, set()).add(fy)

        for doc, years in doc_years.items():
            # If doc explicitly mentions a single year (e.g. 2004 or 2016) but covers > 2 distinct financial years
            single_year_match = re.search(r'20\d\d', str(doc))
            if single_year_match and len(years) > 2:
                # Check if rows declare STATUTORY_PERSISTENCE
                has_persistence_declared = any(
                    "PERSISTENCE" in (r.get('price_type') or r.get('revision_reason') or r.get('audit_notes') or r.get('provenance_tier') or "")
                    for r in data_rows if (r.get('source_document') == doc or r.get('source_circular_no') == doc)
                )
                if not has_persistence_declared:
                    violations.append(GuardrailViolation(
                        severity="FATAL",
                        rule="MULTI_YEAR_CIRCULAR_OVER_ATTRIBUTION",
                        target=filepath,
                        message=f"Document '{doc}' is an annual circular but is attributed across {len(years)} years ({sorted(years)[:4]}...) without explicit STATUTORY_PERSISTENCE qualification."
                    ))

        # Check 2: Fabricated URLs
        for row in data_rows:
            url = row.get('source_url') or row.get('official_pdf_url') or ""
            for pat in self.FABRICATED_URL_PATTERNS:
                if re.search(pat, url):
                    violations.append(GuardrailViolation(
                        severity="FATAL",
                        rule="FABRICATED_URL_DETECTED",
                        target=filepath,
                        message=f"Fabricated URL pattern detected: '{url}'"
                    ))
                    break

        return violations

    def audit_pdf_file(self, filepath: str) -> List[GuardrailViolation]:
        violations = []
        size = os.path.getsize(filepath)
        if size < 1024: # Less than 1 KB is almost certainly a stub or fake PDF
            violations.append(GuardrailViolation(
                severity="FATAL",
                rule="FAKE_STUB_PDF_DETECTED",
                target=filepath,
                message=f"File size is only {size} bytes. Real circulars/documents must be > 1 KB authentic scanned files."
            ))
        else:
            # Check valid PDF magic header
            with open(filepath, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
                    violations.append(GuardrailViolation(
                        severity="FATAL",
                        rule="CORRUPT_OR_FAKE_PDF_HEADER",
                        target=filepath,
                        message=f"File does not start with valid %PDF- magic bytes (got {header})"
                    ))
        return violations


def run_full_guardrail(scan_dir: str) -> bool:
    print("=" * 80)
    print("RUNNING ZERO-SYNTHETIC DATASET INTEGRITY GUARDRAIL AUDIT")
    print(f"Target Directory: {scan_dir}")
    print("=" * 80)

    guard = DatasetIntegrityGuardrail()
    all_violations: List[GuardrailViolation] = []

    # 1. Audit Python scripts
    py_files = glob.glob(os.path.join(scan_dir, "**", "*.py"), recursive=True)
    for pf in py_files:
        violations = guard.audit_python_file(pf)
        all_violations.extend(violations)

    # 2. Audit CSV datasets
    csv_files = glob.glob(os.path.join(scan_dir, "**", "*.csv"), recursive=True)
    for cf in csv_files:
        violations = guard.audit_csv_dataset(cf)
        all_violations.extend(violations)

    # 3. Audit PDF files
    pdf_files = glob.glob(os.path.join(scan_dir, "**", "*.pdf"), recursive=True)
    for pdf in pdf_files:
        violations = guard.audit_pdf_file(pdf)
        all_violations.extend(violations)

    # Report results
    fatals = [v for v in all_violations if v.severity == "FATAL"]
    warnings = [v for v in all_violations if v.severity == "WARNING"]

    if not all_violations:
        print("\n[PASSED] All files adhere strictly to the Zero-Synthetic Data Integrity Guardrail.")
        print(f"Audited: {len(py_files)} Python files, {len(csv_files)} CSV files, {len(pdf_files)} PDF files.")
        return True
    else:
        print(f"\n[FAILED] Detected {len(fatals)} FATAL VIOLATIONS and {len(warnings)} WARNINGS:")
        print("-" * 80)
        for v in all_violations:
            print(f" - {v}")
        print("-" * 80)
        print("\nACTION REQUIRED: Remove synthetic generators, replace stubs with verified primary documents, and enforce discrete step-function persistence.")
        return False


if __name__ == "__main__":
    default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    target = sys.argv[1] if len(sys.argv) > 1 else default_dir
    success = run_full_guardrail(target)
    sys.exit(0 if success else 1)
