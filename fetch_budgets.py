"""
Download Arlington, MA annual budget PDFs (Revenue and Budget Summaries sections).
URLs pre-scraped from arlingtonma.gov via browser.
"""

import requests
from pathlib import Path
import time

OUTPUT_DIR = Path(__file__).parent / "input" / "budgets"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Pre-scraped PDF URLs (revenue and budget summaries per fiscal year)
PDF_URLS = {
    2007: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/17518/635327505423730000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/17508/635327505392330000",
    },
    2008: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/17502/635327503880100000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/17482/635327503880100000",
    },
    2009: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/16122/635306658703030000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/16102/635306658703030000",
    },
    # FY2010: no sub-page links found
    2011: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/16096/635306652779570000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/16074/635306652779570000",
    },
    2012: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/16068/635306649409800000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/16048/635306649409800000",
    },
    2013: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/16040/635306646376130000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/16020/635306646376130000",
    },
    2014: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/2660/635288110680470000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/2634/635288111826100000",
    },
    2015: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/17234/635321171118030000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/17208/635321411222200000",
    },
    2016: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/24481/635629849402930000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/24453/635629844969730000",
    },
    2017: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/29453/635950193791370000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/29423/635950193724770000",
    },
    2018: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/34122/636367600625630000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/34124/636367601093030000",
    },
    2019: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/41408/636682131932570000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/41410/636682132403200000",
    },
    2020: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/46064/636997318539700000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/46066/636997318755500000",
    },
    2021: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/50781/637317177447930000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/50785/637317146885570000",
    },
    2022: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/55614/637625749543000000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/55616/637625756240370000",
    },
    2023: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/60571/637952960282000000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/60573/637849224416470000",
    },
    2024: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/64673/638158602678730000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/64649/638158602607470000",
    },
    2025: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/70566/638549152935100000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/70568/638549152941900000",
    },
    2026: {
        "revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/74837/638870491653670000",
        "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/74839/638870491664400000",
    },
}


def download_pdf(url, filepath):
    """Download a PDF file."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        if resp.status_code == 200 and len(resp.content) > 1000:
            filepath.write_bytes(resp.content)
            size_kb = len(resp.content) / 1024
            print(f"    Saved {filepath.name} ({size_kb:.0f} KB)")
            return True
        else:
            print(f"    Failed ({resp.status_code}, {len(resp.content)} bytes)")
            return False
    except Exception as e:
        print(f"    Error: {e}")
        return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Arlington, MA — Budget PDF Downloader")
    print("=" * 60)
    print()

    total = 0
    for year in sorted(PDF_URLS.keys()):
        urls = PDF_URLS[year]
        print(f"FY{year}:")

        for section, url in urls.items():
            filepath = OUTPUT_DIR / f"fy{year}_{section}.pdf"
            if filepath.exists():
                print(f"  {section}: already downloaded")
                total += 1
                continue

            print(f"  {section}: downloading...")
            if download_pdf(url, filepath):
                total += 1
            time.sleep(0.5)

    print(f"\nDone. Total PDFs: {total}")
    print(f"Files in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
