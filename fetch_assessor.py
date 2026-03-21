"""
Fetch all Parcels with Assessor Info from Arlington, MA GIS Open Data Hub.

The API returns max 2,000 records per request, so we paginate using
resultOffset. Saves raw JSON and a clean CSV for analysis.

Source: https://gis-arlingtonma.opendata.arcgis.com
Service: Parcels_with_Assessor_Info/FeatureServer/0
"""

import requests
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime, timezone

BASE_URL = (
    "https://services2.arcgis.com/s1Sh73K7qtP9JdrG/arcgis/rest/services/"
    "Parcels_with_Assessor_Info/FeatureServer/0"
)
PAGE_SIZE = 2000
INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_page(offset=0):
    """Fetch one page of records from the Feature Service."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "f": "json",
    }
    resp = requests.get(f"{BASE_URL}/query", params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_all():
    """Paginate through all records and return combined feature list."""
    all_features = []
    offset = 0

    while True:
        print(f"  Fetching records {offset} – {offset + PAGE_SIZE - 1}...")
        data = fetch_page(offset)
        features = data.get("features", [])
        all_features.extend(features)

        if not data.get("exceededTransferLimit", False) or len(features) == 0:
            break

        offset += PAGE_SIZE
        time.sleep(0.5)  # be polite to the server

    print(f"  Total records fetched: {len(all_features)}")
    return all_features


def epoch_ms_to_date(val):
    """Convert ArcGIS epoch milliseconds to datetime, or return None."""
    if val is None:
        return None
    try:
        return datetime.fromtimestamp(val / 1000, tz=timezone.utc)
    except (ValueError, OSError, TypeError):
        return None


def build_dataframe(features):
    """Convert raw features to a clean DataFrame."""
    rows = [f["attributes"] for f in features]
    df = pd.DataFrame(rows)

    # Convert epoch‑ms date columns to datetime
    date_cols = ["SaleDate", "DateLastPulled"]
    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].apply(epoch_ms_to_date)

    # Derive useful columns
    if "SaleDate" in df.columns:
        df["SaleYear"] = df["SaleDate"].apply(
            lambda d: d.year if d is not None else None
        )

    if "CurrentTotal" in df.columns and "GISSqFt" in df.columns:
        df["ValuePerSqFt"] = df.apply(
            lambda r: (
                r["CurrentTotal"] / r["GISSqFt"]
                if r["GISSqFt"] and r["GISSqFt"] > 0 and r["CurrentTotal"]
                else None
            ),
            axis=1,
        )

    if "SalePrice" in df.columns and "GISSqFt" in df.columns:
        df["SalePricePerSqFt"] = df.apply(
            lambda r: (
                r["SalePrice"] / r["GISSqFt"]
                if r["GISSqFt"]
                and r["GISSqFt"] > 0
                and r["SalePrice"]
                and r["SalePrice"] > 100
                else None
            ),
            axis=1,
        )

    return df


def print_summary(df):
    """Print overview statistics."""
    print(f"\n{'='*60}")
    print("  Arlington, MA — Assessor Data Summary")
    print(f"{'='*60}\n")

    print(f"  Total parcels: {len(df):,}")
    print(f"  Parcels with sale data: {df['SalePrice'].notna().sum():,}")

    valid_sales = df[(df["SalePrice"].notna()) & (df["SalePrice"] > 100)]
    print(f"  Parcels with valid sale price (>$100): {len(valid_sales):,}")

    if "SaleYear" in df.columns:
        years = valid_sales["SaleYear"].dropna()
        print(f"  Sale year range: {int(years.min())} – {int(years.max())}")

    print(f"\n  Current Assessed Values (FY2026):")
    for col, label in [
        ("CurrentTotal", "Total Value"),
        ("BuildValue", "Building Value"),
        ("landValue", "Land Value"),
    ]:
        if col in df.columns:
            vals = df[col].dropna()
            print(f"    {label}:")
            print(f"      Median: ${vals.median():,.0f}")
            print(f"      Mean:   ${vals.mean():,.0f}")
            print(f"      Min:    ${vals.min():,.0f}")
            print(f"      Max:    ${vals.max():,.0f}")

    if "SalePrice" in valid_sales.columns:
        print(f"\n  Last Sale Prices (valid sales):")
        sp = valid_sales["SalePrice"].dropna()
        print(f"    Median: ${sp.median():,.0f}")
        print(f"    Mean:   ${sp.mean():,.0f}")
        print(f"    Min:    ${sp.min():,.0f}")
        print(f"    Max:    ${sp.max():,.0f}")

    if "Z_Desc" in df.columns:
        print(f"\n  Zoning Distribution:")
        for zone, count in df["Z_Desc"].value_counts().head(10).items():
            print(f"    {zone:<30} {count:>6,}")

    if "LUC_Desc" in df.columns:
        print(f"\n  Land Use Distribution:")
        for luc, count in df["LUC_Desc"].value_counts().head(10).items():
            print(f"    {luc:<30} {count:>6,}")

    if "YearBuilt" in df.columns:
        yb = df["YearBuilt"].dropna()
        print(f"\n  Year Built:")
        print(f"    Oldest: {int(yb.min())}")
        print(f"    Newest: {int(yb.max())}")
        print(f"    Median: {int(yb.median())}")


def main():
    INPUT_DIR.mkdir(exist_ok=True)

    print("Fetching all Parcels with Assessor Info from Arlington, MA GIS...\n")
    features = fetch_all()

    # Save raw JSON
    json_path = INPUT_DIR / "assessor_raw.json"
    print(f"\nSaving raw JSON to {json_path}...")
    with open(json_path, "w") as f:
        json.dump(features, f)

    # Build and save DataFrame
    print("Building DataFrame...")
    df = build_dataframe(features)

    csv_path = INPUT_DIR / "assessor_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"CSV saved to {csv_path} ({len(df):,} rows x {len(df.columns)} cols)")

    # Summary
    print_summary(df)

    return df


if __name__ == "__main__":
    main()
