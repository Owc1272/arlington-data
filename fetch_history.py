"""
Scrape historical assessment data from Patriot Properties for a sample
of Arlington properties. Uses session-based navigation:
  1. Hit landing.asp?anum=X to set session
  2. Fetch g_previous.asp for year-by-year assessments
  3. Fetch g_sales.asp for full sales history
"""

import requests
import pandas as pd
import re
import time
from pathlib import Path
from bs4 import BeautifulSoup

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"
BASE = "https://arlington.patriotproperties.com"


def extract_anum(url):
    """Extract account number from assessor URL."""
    if pd.isna(url):
        return None
    m = re.search(r'anum=(\d+)', str(url))
    return m.group(1) if m else None


def scrape_previous_assessments(session, anum):
    """Fetch and parse the Previous Assessments table."""
    # Set session
    session.get(f"{BASE}/landing.asp?anum={anum}", timeout=15)

    # Get historical data
    r = session.get(f"{BASE}/g_previous.asp", timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = []
    table = soup.find("table")
    if not table:
        return rows

    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) >= 8:
            try:
                rows.append({
                    "Year": int(cells[0]),
                    "LandUseCode": cells[1],
                    "BuildingValue": int(cells[2].replace(",", "")) if cells[2] else 0,
                    "YardValue": int(cells[3].replace(",", "")) if cells[3] else 0,
                    "LandValue": int(cells[4].replace(",", "")) if cells[4] else 0,
                    "Acres": cells[5],
                    "SpecialLand": float(cells[6].replace(",", "")) if cells[6] else 0,
                    "TotalValue": int(cells[7].replace(",", "")) if cells[7] else 0,
                })
            except (ValueError, IndexError):
                pass

    return rows


def scrape_sales(session, anum):
    """Fetch and parse the Sales table."""
    # Session should already be set from previous call
    r = session.get(f"{BASE}/g_sales.asp", timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    rows = []
    table = soup.find("table")
    if not table:
        return rows

    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) >= 5:
            try:
                price_str = cells[1].replace(",", "").replace("$", "")
                rows.append({
                    "SaleDate": cells[0],
                    "SalePrice": int(price_str) if price_str.isdigit() else 0,
                    "LegalRef": cells[2],
                    "Grantor": cells[3],
                    "LUCAtSale": cells[4],
                })
            except (ValueError, IndexError):
                pass

    return rows


def main():
    INPUT_DIR.mkdir(exist_ok=True)

    # Load assessor data, filter to Appleton St
    df = pd.read_csv(INPUT_DIR / "assessor_data.csv", low_memory=False)
    appleton = df[df["RoadName"].str.contains("APPLETON", na=False, case=False)].copy()
    appleton["anum"] = appleton["AssessorURL"].apply(extract_anum)
    appleton = appleton[appleton["anum"].notna()].drop_duplicates(subset="anum")

    # Take up to 100
    sample = appleton.head(100)
    print(f"Scraping historical data for {len(sample)} Appleton St properties...\n")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    session = requests.Session()
    session.headers.update(headers)

    all_assessments = []
    all_sales = []
    errors = 0

    for i, (_, row) in enumerate(sample.iterrows()):
        anum = row["anum"]
        addr = row.get("FullAddress", "?")

        try:
            # Scrape assessments
            assessments = scrape_previous_assessments(session, anum)
            for a in assessments:
                a["anum"] = anum
                a["FullAddress"] = addr
                a["ParcelID"] = row.get("ParcelID", "")
            all_assessments.extend(assessments)

            # Scrape sales
            sales = scrape_sales(session, anum)
            for s in sales:
                s["anum"] = anum
                s["FullAddress"] = addr
                s["ParcelID"] = row.get("ParcelID", "")
            all_sales.extend(sales)

            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(sample)} done — {len(all_assessments)} assessment rows, {len(all_sales)} sales")

            time.sleep(0.3)

        except Exception as e:
            errors += 1
            print(f"  Error on {addr} (anum={anum}): {e}")

    print(f"\nDone! {errors} errors")
    print(f"  Assessment records: {len(all_assessments)}")
    print(f"  Sales records: {len(all_sales)}")

    # Save
    assess_df = pd.DataFrame(all_assessments)
    assess_path = INPUT_DIR / "appleton_historical_assessments.csv"
    assess_df.to_csv(assess_path, index=False)
    print(f"  Saved: {assess_path}")

    sales_df = pd.DataFrame(all_sales)
    sales_path = INPUT_DIR / "appleton_historical_sales.csv"
    sales_df.to_csv(sales_path, index=False)
    print(f"  Saved: {sales_path}")

    # Quick summary
    if len(assess_df) > 0:
        years = assess_df["Year"].unique()
        print(f"\n  Assessment years: {sorted(years)[0]} – {sorted(years)[-1]}")
        print(f"  Properties with history: {assess_df['anum'].nunique()}")

        # Show value trend
        yearly = assess_df.groupby("Year")["TotalValue"].median().reset_index()
        yearly = yearly.sort_values("Year")
        print(f"\n  Median Total Value by Year (Appleton St):")
        for _, r in yearly.iterrows():
            print(f"    {int(r['Year'])}: ${r['TotalValue']:,.0f}")


if __name__ == "__main__":
    main()
