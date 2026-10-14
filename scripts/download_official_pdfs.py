import os
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

out_dir = r'd:\aplly_articles\official_gidc_pdfs'
os.makedirs(out_dir, exist_ok=True)

urls = {
    "allotment_price_2004_2005.pdf": "https://gidc.gujarat.gov.in/pdf/allotment-price/allotment-price-2004-2005.pdf",
    "CIRCULAR_ALLOTMENT_PRICE_2016.pdf": "https://gidc.gujarat.gov.in/pdf/Circular/CIRCULAR-ALLOTMENT-PRICE.pdf",
    "June_2022_GIDC_Sanand.pdf": "https://gidc.gujarat.gov.in/pdf/June%202022%20GIDC%20Sanand%20Industrial%20Estate.pdf",
    "allotmentprice.html": "https://gidc.gujarat.gov.in/allotmentprice"
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for fname, url in urls.items():
    dest = os.path.join(out_dir, fname)
    print(f"Downloading {url} to {dest}...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp, open(dest, 'wb') as f_out:
            f_out.write(resp.read())
        print(f"Saved {fname} ({os.path.getsize(dest)} bytes)")
    except Exception as e:
        print(f"Failed to download {url}: {e}")
