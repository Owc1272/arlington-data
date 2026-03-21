"""
Fetch Arlington, MA crime data from FBI Crime Data Explorer (CDE).
Source: https://cde.ucr.cjis.gov
Agency: Arlington Police Department (ORI: MA0090200)

No authentication required. Uses the CDE internal API.
Output: website/data/crime.json
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

OUTPUT_PATH = Path(__file__).parent / "website" / "data" / "crime.json"
BASE = "https://cde.ucr.cjis.gov/LATEST"
ORI = "MA0090200"

# Main crime categories to fetch
SUMMARIZED_OFFENSES = {
    "ASS": "Aggravated Assault",
    "HOM": "Homicide",
    "RPE": "Rape",
    "ROB": "Robbery",
    "ARS": "Arson",
    "BUR": "Burglary",
    "LAR": "Larceny-theft",
    "MVT": "Motor Vehicle Theft",
}

# NIBRS-only offenses for recent years
NIBRS_OFFENSES = {
    "13B": "Simple Assault",
    "290": "Vandalism",
    "35A": "Drug/Narcotic Violations",
    "26A": "Fraud",
    "26F": "Identity Theft",
    "520": "Weapon Law Violations",
    "23C": "Shoplifting",
    "13C": "Intimidation",
}


def fetch_json(url):
    """Fetch JSON from CDE API."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        print(f"  HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    return None


def fetch_summarized_trends():
    """Fetch summarized (SRS) crime trends for Arlington PD."""
    print("Fetching summarized crime trends (2002-2023)...")
    results = {}

    for code, label in SUMMARIZED_OFFENSES.items():
        url = f"{BASE}/summarized/agency/{ORI}/{code}?from=01-2002&to=12-2023&type=counts"
        data = fetch_json(url)
        if not data:
            print(f"  {label}: no data")
            continue

        # Extract annual counts from monthly data
        offenses = data.get("offenses", {})
        actuals = offenses.get("actuals", {})

        # Find the Arlington offenses (not clearances)
        arlington_counts = None
        for key, vals in actuals.items():
            if "Offenses" in key or "offenses" in key:
                arlington_counts = vals
                break
        if not arlington_counts:
            # Try first key
            for key, vals in actuals.items():
                arlington_counts = vals
                break

        if arlington_counts:
            # Aggregate monthly to annual
            annual = {}
            for month_key, count in arlington_counts.items():
                # month_key is like "01-2010", "02-2010"
                parts = month_key.split("-")
                if len(parts) == 2:
                    year = int(parts[1])
                    annual[year] = annual.get(year, 0) + count

            results[code] = {
                "label": label,
                "annual": annual,
            }
            total = sum(annual.values())
            print(f"  {label}: {len(annual)} years, {total} total incidents")

        time.sleep(0.3)

    return results


def fetch_nibrs_details():
    """Fetch NIBRS detailed data for recent years."""
    print("\nFetching NIBRS details (2021-2023)...")
    results = {}

    for code, label in {**SUMMARIZED_OFFENSES, **NIBRS_OFFENSES}.items():
        url = f"{BASE}/nibrs/agency/{ORI}/{code}?from=01-2021&to=12-2023&type=totals"
        data = fetch_json(url)
        if not data:
            continue

        victim = data.get("victim", {})
        offender = data.get("offender", {})
        offense = data.get("offense", {})

        if victim or offender or offense:
            # Count is sum of victim sex counts (or age counts)
            victim_sex = victim.get("sex", {})
            total_count = sum(v for v in victim_sex.values() if isinstance(v, (int, float)))
            results[code] = {
                "label": label,
                "count": total_count,
                "victim_age": victim.get("age", {}),
                "victim_sex": victim_sex,
                "victim_race": victim.get("race", {}),
                "location": victim.get("location", {}),
            }
            print(f"  {label}: {total_count} incidents")

        time.sleep(0.3)

    return results


def build_annual_summary(summarized):
    """Build year-by-year totals for violent and property crime."""
    years = set()
    for code, data in summarized.items():
        years.update(data["annual"].keys())

    violent_codes = ["ASS", "HOM", "RPE", "ROB"]
    property_codes = ["BUR", "LAR", "MVT", "ARS"]

    annual = []
    for year in sorted(years):
        entry = {"year": year}
        entry["violent"] = sum(summarized.get(c, {}).get("annual", {}).get(year, 0) for c in violent_codes)
        entry["property"] = sum(summarized.get(c, {}).get("annual", {}).get(year, 0) for c in property_codes)
        entry["total"] = entry["violent"] + entry["property"]

        # Individual categories
        for code in SUMMARIZED_OFFENSES:
            entry[code.lower()] = summarized.get(code, {}).get("annual", {}).get(year, 0)

        annual.append(entry)

    return annual


def main():
    print("=" * 60)
    print("  Arlington, MA — Crime Data Fetcher")
    print("  Source: FBI Crime Data Explorer")
    print(f"  Agency: Arlington PD ({ORI})")
    print("=" * 60)
    print()

    summarized = fetch_summarized_trends()
    nibrs = fetch_nibrs_details()
    annual = build_annual_summary(summarized)

    # Summary stats from latest year
    latest = annual[-1] if annual else {}

    output = {
        "generated": datetime.now().isoformat(),
        "source": "FBI Crime Data Explorer (CDE)",
        "agency": "Arlington Police Department",
        "ori": ORI,
        "annual": annual,
        "offense_trends": {code: data["annual"] for code, data in summarized.items()},
        "offense_labels": {code: data["label"] for code, data in summarized.items()},
        "nibrs_details": nibrs,
        "summary": {
            "latest_year": latest.get("year"),
            "total_crimes": latest.get("total"),
            "violent_crimes": latest.get("violent"),
            "property_crimes": latest.get("property"),
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput: {OUTPUT_PATH}")
    print(f"Summary: {json.dumps(output['summary'], indent=2)}")


if __name__ == "__main__":
    main()
