import os
import urllib.request
import urllib.error
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2000-2001.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2001-2002.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2003-2004.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2004-2005.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2005-2006.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2006-2007.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2006-2007-1.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2014-2015.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2015-2016.pdf",
    "https://gidc.gujarat.gov.in/Document/LinkManagment/Draw%20Result/allotment-price-2016-1707092022053326.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/Allotment-Price-2018-19.pdf",
    "https://gidc.gujarat.gov.in/pdf/allotment-price/Allotment-Price-2020-21.pdf",
    "https://gidc.gujarat.gov.in/Document/LinkManagment/Draw%20Result/522082022041917.pdf",
    "https://gidc.gujarat.gov.in/Document/LinkManagment/Circulars/allotment-price-22-2317042023012437.pdf",
    "https://gidc.gujarat.gov.in/Document/LinkManagment/Circulars/final-ap-2023-24-with-circular-1804202318042023014956.pdf"
]

out_dir = r"d:\aplly_articles\evidence_pdf_archive\all_historical_circulars"
os.makedirs(out_dir, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

print(f"Testing & downloading {len(set(urls))} unique URLs...", flush=True)

for url in sorted(set(urls)):
    filename = url.split('/')[-1]
    # Clean filename of URL encodings
    filename = urllib.parse.unquote(filename)
    dest = os.path.join(out_dir, filename)
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            content = resp.read()
            with open(dest, 'wb') as f:
                f.write(content)
            print(f"[HTTP {resp.status} - SUCCESS] {filename} ({len(content):,} bytes) from {url}", flush=True)
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code} - FAILED] {filename} from {url}", flush=True)
    except Exception as e:
        print(f"[ERROR - {e}] {filename} from {url}", flush=True)
