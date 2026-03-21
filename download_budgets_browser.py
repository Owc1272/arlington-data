"""
Download Arlington budget PDFs using Playwright (real browser) to bypass Akamai CDN.
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "input" / "budgets"

PDF_URLS = {
    2007: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/17518/635327505423730000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/17508/635327505392330000"},
    2008: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/17502/635327503880100000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/17482/635327503880100000"},
    2009: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/16122/635306658703030000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/16102/635306658703030000"},
    2011: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/16096/635306652779570000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/16074/635306652779570000"},
    2012: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/16068/635306649409800000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/16048/635306649409800000"},
    2013: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/16040/635306646376130000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/16020/635306646376130000"},
    2014: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/2660/635288110680470000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/2634/635288111826100000"},
    2015: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/17234/635321171118030000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/17208/635321411222200000"},
    2016: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/24481/635629849402930000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/24453/635629844969730000"},
    2017: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/29453/635950193791370000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/29423/635950193724770000"},
    2018: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/34122/636367600625630000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/34124/636367601093030000"},
    2019: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/41408/636682131932570000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/41410/636682132403200000"},
    2020: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/46064/636997318539700000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/46066/636997318755500000"},
    2021: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/50781/637317177447930000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/50785/637317146885570000"},
    2022: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/55614/637625749543000000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/55616/637625756240370000"},
    2023: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/60571/637952960282000000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/60573/637849224416470000"},
    2024: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/64673/638158602678730000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/64649/638158602607470000"},
    2025: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/70566/638549152935100000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/70568/638549152941900000"},
    2026: {"revenue": "https://www.arlingtonma.gov/home/showpublisheddocument/74837/638870491653670000", "summaries": "https://www.arlingtonma.gov/home/showpublisheddocument/74839/638870491664400000"},
}


async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  Arlington Budget PDF Downloader (Playwright)")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Visit the main site first to get cookies
        print("Visiting Arlington website...")
        await page.goto("https://www.arlingtonma.gov/departments/town-manager/town-manager-s-annual-budget-financial-report", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        total = 0
        for year in sorted(PDF_URLS.keys()):
            sections = PDF_URLS[year]
            print(f"\nFY{year}:")
            for section, url in sections.items():
                filepath = OUTPUT_DIR / f"fy{year}_{section}.pdf"
                if filepath.exists() and filepath.stat().st_size > 1000:
                    print(f"  {section}: already downloaded")
                    total += 1
                    continue

                try:
                    resp = await context.request.get(url)
                    if resp.status == 200:
                        body = await resp.body()
                        filepath.write_bytes(body)
                        print(f"  {section}: saved ({len(body) // 1024} KB)")
                        total += 1
                    else:
                        print(f"  {section}: HTTP {resp.status}")
                except Exception as e:
                    print(f"  {section}: ERROR {e}")

                await asyncio.sleep(0.5)

        await browser.close()
        print(f"\nDone. Total PDFs: {total}")


if __name__ == "__main__":
    asyncio.run(main())
