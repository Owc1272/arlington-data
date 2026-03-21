"""
Fetch ACS 5-Year Estimate data from Arlington, MA GIS Open Data Hub.
Source: https://gis-arlingtonma.opendata.arcgis.com/datasets/04d200bd212f487a937ed3f79c3fb272_0/api
"""

import requests
import pandas as pd
import json
from pathlib import Path

BASE_URL = (
    "https://services2.arcgis.com/s1Sh73K7qtP9JdrG/arcgis/rest/services/"
    "ACS_5Year_Estimate/FeatureServer/0"
)

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"

# ACS DP05 variable code mappings (decoded from standard ACS table)
FIELD_LABELS = {
    # Population
    "HC01_VC03": "Total population",
    "HC01_VC04": "Male",
    "HC01_VC05": "Female",
    # Age groups
    "HC01_VC08": "Under 5 years",
    "HC01_VC09": "5 to 9 years",
    "HC01_VC10": "10 to 14 years",
    "HC01_VC11": "15 to 19 years",
    "HC01_VC12": "20 to 24 years",
    "HC01_VC13": "25 to 34 years",
    "HC01_VC14": "35 to 44 years",
    "HC01_VC15": "45 to 54 years",
    "HC01_VC16": "55 to 59 years",
    "HC01_VC17": "60 to 64 years",
    "HC01_VC18": "65 to 74 years",
    "HC01_VC19": "75 to 84 years",
    "HC01_VC20": "85 years and over",
    "HC01_VC23": "Median age (years)",
    # Housing
    "HC01_VC26": "Total housing units",
    "HC01_VC27": "Occupied housing units",
    "HC01_VC28": "Vacant housing units",
    "HC01_VC33": "Owner-occupied",
    "HC01_VC34": "Renter-occupied",
    # Race
    "HC01_VC43": "Total population (race)",
    "HC01_VC44": "One race",
    "HC01_VC45": "Two or more races",
    "HC01_VC49": "White",
    "HC01_VC50": "Black or African American",
    "HC01_VC51": "American Indian and Alaska Native",
    "HC01_VC56": "Asian",
    "HC01_VC70": "Two or more races",
    # Hispanic/Latino
    "HC01_VC77": "Total population (Hispanic/Latino)",
    "HC01_VC78": "Not Hispanic or Latino",
    "HC01_VC79": "Hispanic or Latino",
    # Income/Poverty
    "HC01_VC104": "Total households",
    "HC01_VC108": "Median household income (dollars)",
    "HC01_VC109": "Families below poverty level",
    "HC01_VC110": "Individuals below poverty level",
}


def fetch_data(out_fields="*", where="1=1"):
    """Query the ACS Feature Service and return JSON response."""
    params = {
        "where": where,
        "outFields": out_fields,
        "f": "json",
    }
    resp = requests.get(f"{BASE_URL}/query", params=params)
    resp.raise_for_status()
    return resp.json()


def to_dataframe(data):
    """Convert ArcGIS JSON response to a pandas DataFrame."""
    features = data.get("features", [])
    rows = [f["attributes"] for f in features]
    return pd.DataFrame(rows)


def summarize(df):
    """Print a human-readable summary using labeled field names."""
    if df.empty:
        print("No data returned.")
        return

    row = df.iloc[0]
    print(f"\n{'='*60}")
    print(f"  {row.get('GEO_display_label', 'Unknown Location')}")
    print(f"{'='*60}\n")

    sections = {
        "Population & Gender": ["HC01_VC03", "HC01_VC04", "HC01_VC05", "HC01_VC23"],
        "Age Distribution": [
            "HC01_VC08", "HC01_VC09", "HC01_VC10", "HC01_VC11", "HC01_VC12",
            "HC01_VC13", "HC01_VC14", "HC01_VC15", "HC01_VC16", "HC01_VC17",
            "HC01_VC18", "HC01_VC19", "HC01_VC20",
        ],
        "Housing": ["HC01_VC26", "HC01_VC27", "HC01_VC28", "HC01_VC33", "HC01_VC34"],
        "Race": ["HC01_VC49", "HC01_VC50", "HC01_VC51", "HC01_VC56", "HC01_VC70"],
        "Hispanic/Latino Origin": ["HC01_VC78", "HC01_VC79"],
        "Income & Poverty": ["HC01_VC104", "HC01_VC108", "HC01_VC109", "HC01_VC110"],
    }

    for section, fields in sections.items():
        print(f"  {section}")
        print(f"  {'-'*40}")
        for code in fields:
            label = FIELD_LABELS.get(code, code)
            val = row.get(code, "N/A")
            # Get percentage if available
            pct_code = code.replace("HC01_", "HC03_")
            pct = row.get(pct_code)
            if pct is not None and pct != val and not isinstance(pct, str):
                print(f"    {label:<40} {val:>10,}  ({pct}%)")
            elif isinstance(val, float) and val == int(val):
                print(f"    {label:<40} {int(val):>10,}")
            else:
                print(f"    {label:<40} {val:>10}")
        print()


def main():
    INPUT_DIR.mkdir(exist_ok=True)

    print("Fetching ACS 5-Year Estimate data for Arlington, MA...")
    data = fetch_data()

    # Save raw JSON
    json_path = INPUT_DIR / "acs_raw.json"
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Raw JSON saved to {json_path}")

    # Convert to DataFrame and save CSV
    df = to_dataframe(data)
    csv_path = INPUT_DIR / "acs_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path}")

    # Print summary
    summarize(df)


if __name__ == "__main__":
    main()
