"""
Fetch all active Public Shade Trees from Arlington, MA GIS.
Filters to RemovedDate IS NULL (10,924 active trees).
"""

import requests
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime, timezone

BASE_URL = (
    "https://services2.arcgis.com/s1Sh73K7qtP9JdrG/arcgis/rest/services/"
    "Public_Shade_Trees/FeatureServer/0"
)
PAGE_SIZE = 2000
INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_page(offset=0):
    params = {
        "where": "RemovedDate IS NULL",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "f": "json",
    }
    resp = requests.get(f"{BASE_URL}/query", params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_all():
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
        time.sleep(0.5)

    print(f"  Total records fetched: {len(all_features)}")
    return all_features


def epoch_ms_to_date(val):
    if val is None:
        return None
    try:
        return datetime.fromtimestamp(val / 1000, tz=timezone.utc)
    except (ValueError, OSError, TypeError):
        return None


def build_dataframe(features):
    rows = []
    for f in features:
        row = f["attributes"]
        geom = f.get("geometry", {})
        row["lng"] = geom.get("x")
        row["lat"] = geom.get("y")
        rows.append(row)
    df = pd.DataFrame(rows)

    # Convert dates
    for col in ["PlantedDate", "RemovedDate"]:
        if col in df.columns:
            df[col] = df[col].apply(epoch_ms_to_date)

    if "PlantedDate" in df.columns:
        df["PlantedYear"] = df["PlantedDate"].apply(
            lambda d: d.year if d is not None else None
        )

    return df


def print_summary(df):
    print(f"\n{'='*60}")
    print("  Arlington, MA — Public Shade Trees Summary")
    print(f"{'='*60}\n")

    print(f"  Active trees: {len(df):,}")
    print(f"  With coordinates: {df['lat'].notna().sum():,}")

    if "CommonName" in df.columns:
        print(f"\n  Top 15 Species:")
        for name, count in df["CommonName"].value_counts().head(15).items():
            print(f"    {name:<35} {count:>5,}")

    if "DBH" in df.columns:
        dbh = df["DBH"].dropna()
        print(f"\n  Diameter at Breast Height (inches):")
        print(f"    Median: {dbh.median():.1f}")
        print(f"    Mean:   {dbh.mean():.1f}")
        print(f"    Max:    {dbh.max():.1f}")

    if "Height" in df.columns:
        ht = df["Height"].dropna()
        if len(ht) > 0:
            print(f"\n  Height (ft):")
            print(f"    Median: {ht.median():.0f}")
            print(f"    Mean:   {ht.mean():.0f}")
            print(f"    Max:    {ht.max():.0f}")

    if "Stormwater" in df.columns:
        sw = df["Stormwater"].dropna()
        print(f"\n  Stormwater Intercepted:")
        print(f"    Total: {sw.sum():,.0f} gal/yr")
        print(f"    Mean per tree: {sw.mean():,.0f} gal/yr")

    if "Pollutants" in df.columns:
        pol = df["Pollutants"].dropna()
        print(f"\n  Air Pollutants Removed:")
        print(f"    Total: {pol.sum():,.0f} oz/yr ({pol.sum()/16:,.0f} lbs/yr)")
        print(f"    Mean per tree: {pol.mean():,.1f} oz/yr")

    if "PlantedYear" in df.columns:
        py = df["PlantedYear"].dropna()
        if len(py) > 0:
            print(f"\n  Planting Year Range: {int(py.min())} – {int(py.max())}")
            print(f"  Trees with planting date: {len(py):,}")


def main():
    INPUT_DIR.mkdir(exist_ok=True)

    print("Fetching active Public Shade Trees...\n")
    features = fetch_all()

    json_path = INPUT_DIR / "trees_raw.json"
    print(f"\nSaving raw JSON to {json_path}...")
    with open(json_path, "w") as f:
        json.dump(features, f)

    print("Building DataFrame...")
    df = build_dataframe(features)

    csv_path = INPUT_DIR / "trees_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"CSV saved: {len(df):,} rows x {len(df.columns)} cols")

    print_summary(df)

    return df


if __name__ == "__main__":
    main()
