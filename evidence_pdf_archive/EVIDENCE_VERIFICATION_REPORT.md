# Formal Data Provenance Audit & Verification Report
**Subject:** Empirical Investigation of Dataset Provenance, Circular Attribution, and Ground-Truth Allotment Rates  
**Reference Case:** Gujarat Industrial Estates Property Dynamics Study  
**Lead Investigator / Trainer Desk:** From the Desk of Puneet Arora, Aplly.xyz Trainer  
**Date of Audit:** October 13, 2026  

---

## Executive Summary (BLUF)

A forensic audit of the dataset files (`05_industrial_parks.csv`, `14_intelligence_sources.csv`, and `16_industrial_land_price_history.csv`) and the underlying generation pipeline (`land_intelligence.py`) was performed in response to the research guide's feedback:

> *"Hi, I am having trouble figuring out the source of the datasets. The park list itself seems largely correct, but the price file cites 12 source links of which 8 do not work, it attributes twelve years of prices to a single 2004 circular that only contains 2004 prices, and it does not match that circular even for 2004.."*

### Audit Verdict: **100% VERIFIED & CONFIRMED**
All four statements made by the research guide are factually accurate, reproducible, and supported by documentary and programmatic evidence:

1. **Park List Authenticity:** The master park catalog (`05_industrial_parks.csv`, 312 records) is valid and largely representative of official GIDC notified estates, talukas, and coordinates.
2. **Broken URLs (8 of 12 Fail):** Exactly 12 unique URLs are cited across the intelligence sources registry and price history file. Direct live HTTP network tests confirm that **8 links fail** (four 404 errors, two fabricated portal endpoints, one unresolvable DNS domain, and one 403 Forbidden endpoint), while only **4 links resolve**.
3. **Twelve-Year Circular Attribution Fallacy:** In `16_industrial_land_price_history.csv`, all price records spanning 12 consecutive fiscal years (FY 2004–05 through FY 2015–16, totaling 3,744 entries) are attributed to a single document: `NO: GIDC/IO&m/CIR/ACCTS/REV/6 (Allotment Rates 2004-05)`. Circular `GIDC/O&m/CIR/ACCTTS/REV/6` was issued on April 1, 2004, and strictly establishes rates effective from April 1, 2004; it contains zero data for subsequent years.
4. **Severe Price Discrepancy (Even for 2004):** The prices in `16_industrial_land_price_history.csv` do not match the circular even for FY 2004–05. The code in `land_intelligence.py` generated prices synthetically via pseudo-random walks and CAGR equations (`np.random.choice` and trend extrapolation), creating errors ranging from $-81.5\%$ to $+873.3\%$ compared to statutory reality.

---

## 1. Evidence Matrix: Verification of the 12 Source Links

Across `14_intelligence_sources.csv` and `16_industrial_land_price_history.csv`, exactly 12 unique URLs were indexed. Network probes conducted on October 13, 2026, yielded the following audit results:

| # | Cited URL | Issuing Authority / Document Cited | Live HTTP Status | Verification Outcome |
|---|---|---|---|---|
| **1** | `https://gidc.gujarat.gov.in/allotment_archive_2000` | GIDC Historical Gazette Order 2000-01 | **HTTP 404** | ❌ **Failed (Fabricated URL)** |
| **2** | `https://gidc.gujarat.gov.in/allotment_archive_2001` | GIDC Historical Gazette Order 2001-01 | **HTTP 404** | ❌ **Failed (Fabricated URL)** |
| **3** | `https://gidc.gujarat.gov.in/allotment_archive_2002` | GIDC Historical Gazette Order 2002-01 | **HTTP 404** | ❌ **Failed (Fabricated URL)** |
| **4** | `https://gidc.gujarat.gov.in/allotment_archive_2003` | GIDC Historical Gazette Order 2003-01 | **HTTP 404** | ❌ **Failed (Fabricated URL)** |
| **5** | `https://gidc.gujarat.gov.in/auction_notices` | GIDC Public Auction Notice FY 2024 | **HTTP 404** | ❌ **Failed (Broken Link)** |
| **6** | `https://gidc.gujarat.gov.in/maps/sanand2_bol_cadastral` | Sanand-II Bol Cadastral Map | **HTTP 404** | ❌ **Failed (Broken Link)** |
| **7** | `https://industries.gujarat.gov.in/gr_private_parks_2015` | GR Private Industrial Park Scheme 2015 | **DNS Err (11001)** | ❌ **Failed (Host Unreachable)** |
| **8** | `https://vibrantgujarat.com/mou_records` | Vibrant Gujarat Global Summit MoUs DPR | **HTTP 403** | ❌ **Failed (Forbidden Access)** |
| **9** | `https://gidc.gujarat.gov.in/allotmentprice` | GIDC FY 2026-27 Allotment Rate Sheet | **HTTP 200** | ✅ **Working (Active Portal Page)** |
| **10** | `https://gidc.gujarat.gov.in/pdf/Circular/CIRCULAR-ALLOTMENT-PRICE.pdf` | GIDC Allotment Price Circular 01/04/2016 | **HTTP 200** | ✅ **Working (Valid Official PDF)** |
| **11** | `https://gidc.gujarat.gov.in/pdf/June%202022%20GIDC%20Sanand%20Industrial%20Estate.pdf` | Sanand Industrial Estate Charges 2022-23 | **HTTP 200** | ✅ **Working (Valid Official PDF)** |
| **12** | `https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2004-2005.pdf` | GIDC Circular NO: GIDC/O&m/CIR/ACCTTS/REV/6 | **HTTP 200** | ✅ **Working (Valid Official PDF)** |

**Audit Conclusion:** Exactly 8 out of 12 cited links are non-functional (66.7% failure rate), confirming the guide's explicit statement.

---

## 2. Root Cause Analysis: How the Synthetic Data Leaked into the Price History

Inspection of the underlying data-generation script (`D:\IndustrialEstates\land_intelligence.py`, lines 150–176) exposes how the synthetic numbers and improper attributions were generated:

```python
# Synthetic stochastic walk and CAGR formula used instead of circular data:
pct_step = np.random.choice([0.0, 0.05, 0.08, 0.14, 0.22], p=[0.35, 0.25, 0.20, 0.12, 0.08])
current_price = current_price * (1.0 + pct_step)
expected_trend = base_p * ((1.0 + overall_cagr) ** (yr - 2000))
current_price = 0.5 * current_price + 0.5 * expected_trend
p_val = round(current_price, 0)

# Blind attribution of 12 years (2004 through 2015) to a single circular:
elif yr >= 2004:
    doc_name = "NO: GIDC/IO&m/CIR/ACCTS/REV/6 (Allotment Rates 2004-05)"
    doc_url = "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2004-2005.pdf"
    sid = sources_map.get(doc_name, default_src)
```

This explains both discrepancies:
1. **The 12-Year Over-Attribution:** Any record between calendar years 2004 and 2015 was unconditionally tagged with the 2004 circular.
2. **The Price Divergence:** The prices were generated via mathematical random walks rather than parsing the official circular table.

---

## 3. Discrepancy Evidence: Official 2004 Circular vs. Dataset Values

The genuine official circular downloaded from `https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2004-2005.pdf` (`GIDC/O&m/CIR/ACCTTS/REV/6`, 6 pages) contains the official Annexure-A rate schedule approved at the Corporation's 416th board meeting.

The table below contrasts the ground-truth statutory rates against the erroneous values in `16_industrial_land_price_history.csv` for FY 2004–05:

| Industrial Estate | District | Official Circular (Annexure-A) | Dataset Price (`16_...price_history.csv`) | Discrepancy (INR/sqm) | Error Percentage |
|---|---|---|---|---|---|
| **GIDC Naroda** | Ahmedabad | **₹800** | ₹918.0 | +₹118.0 | +14.8% |
| **GIDC Odhav** | Ahmedabad | **₹900** | ₹593.0 | -₹307.0 | -34.1% |
| **GIDC Vatva** | Ahmedabad | **₹800** | ₹955.0 | +₹155.0 | +19.4% |
| **GIDC Kathwada** | Ahmedabad | **₹800** | ₹561.0 | -₹239.0 | -29.9% |
| **GIDC Sanand (RIDC)** | Ahmedabad | **₹150** | ₹413.0 | +₹263.0 | +175.3% |
| **GIDC Dhandhuka** | Ahmedabad | **₹60** | ₹584.0 | +₹524.0 | +873.3% |
| **GIDC Gandhinagar (Engg)** | Gandhinagar | **₹1,500** | ₹277.0 | -₹1,223.0 | -81.5% |
| **GIDC Bhat** | Gandhinagar | **₹1,250** | ₹266.0 | -₹984.0 | -78.7% |
| **GIDC Ankleshwar** | Bharuch | **₹360** | ₹640.0 | +₹280.0 | +77.8% |
| **GIDC Dahej (Gen)** | Bharuch | **₹275** | ₹633.0 | +₹358.0 | +130.2% |
| **GIDC Pandesara** | Surat | **₹1,000** | ₹569.0 | -₹431.0 | -43.1% |
| **GIDC Sachin** | Surat | **₹470** | ₹579.0 | +₹109.0 | +23.2% |
| **GIDC Vapi** | Valsad | **₹500** | ₹274.0 | -₹226.0 | -45.2% |
| **GIDC Gandhidham** | Kutch | **₹1,800** | ₹1,267.0 | -₹533.0 | -29.6% |
| **GIDC Aji** | Rajkot | **₹2,000** | ₹259.0 | -₹1,741.0 | -87.1% |
| **GIDC Bhaktinagar** | Rajkot | **₹3,500** | ₹259.0 | -₹3,241.0 | -92.6% |

---

## 4. Deliverables Summary

In compliance with requirements, the evidentiary workspace has been prepared with full provenance assets:

1. **Evidentiary PDF Folder:**
   - **Path:** `d:\aplly_articles\evidence_pdf_archive\`
   - Contains the genuine 2.46 MB official GIDC Circular `GIDC_Allotment_Price_Circular_2004_05.pdf`, the 2.56 MB `GIDC_Allotment_Price_Circular_2016_17.pdf`, and high-resolution scanned page extracts (`page_1` through `page_6`) under `scanned_pages_2004/`.
2. **Preprocessing & Extraction Python Script:**
   - **Path:** `d:\aplly_articles\extract_and_validate_2004_prices.py`
   - Automates extraction of Annexure-A tables across all Gujarat districts, performs entity matching against the master park list (`05_industrial_parks.csv`), executes error audits against legacy datasets, and outputs verified datasets.
3. **New Temporary Verified CSV File:**
   - **Path:** `d:\aplly_articles\temp_industrial_land_price_2004_verified.csv`
   - Contains 201 audited statutory rate records (Industrial and Housing sectors) directly transcribed from the official circular, with audit variance flags, circular reference metadata, and provenance tags.
