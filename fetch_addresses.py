"""
Fetch all address points with coordinates, join with assessor data,
and generate interactive Folium maps.
"""

import requests
import pandas as pd
import json
import time
from pathlib import Path

BASE_URL = (
    "https://services2.arcgis.com/s1Sh73K7qtP9JdrG/arcgis/rest/services/"
    "Current_Arlington_Address_Points_(view)/FeatureServer/0"
)
PAGE_SIZE = 2000
INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_page(offset=0):
    params = {
        "where": "1=1",
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


def build_dataframe(features):
    rows = []
    for f in features:
        row = f["attributes"]
        geom = f.get("geometry", {})
        row["lng"] = geom.get("x")
        row["lat"] = geom.get("y")
        rows.append(row)
    return pd.DataFrame(rows)


def join_with_assessor(addr_df):
    assessor_path = INPUT_DIR / "assessor_data.csv"
    if not assessor_path.exists():
        print("  WARNING: assessor_data.csv not found, skipping join.")
        return addr_df

    print("  Loading assessor data...")
    assessor = pd.read_csv(assessor_path, low_memory=False)

    addr_df["parcel_id_clean"] = addr_df["parcel_id"].astype(str).str.strip()
    assessor["ParcelID_clean"] = assessor["ParcelID"].astype(str).str.strip()

    joined = addr_df.merge(
        assessor,
        left_on="parcel_id_clean",
        right_on="ParcelID_clean",
        how="left",
        suffixes=("_addr", "_assess"),
    )

    matched = joined["ParcelID_clean"].notna().sum()
    print(f"  Matched: {matched:,} / {len(addr_df):,} addresses ({matched/len(addr_df)*100:.1f}%)")

    return joined


def main():
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Fetching all address points...\n")
    features = fetch_all()

    json_path = INPUT_DIR / "addresses_raw.json"
    print(f"\nSaving raw JSON to {json_path}...")
    with open(json_path, "w") as f:
        json.dump(features, f)

    print("Building DataFrame...")
    df = build_dataframe(features)
    csv_path = INPUT_DIR / "addresses_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"Addresses CSV saved: {len(df):,} rows")

    print("\nJoining with assessor data...")
    joined = join_with_assessor(df)
    joined_path = OUTPUT_DIR / "addresses_assessor_joined.csv"
    joined.to_csv(joined_path, index=False)
    print(f"Joined CSV saved: {len(joined):,} rows x {len(joined.columns)} cols")

    # Quick stats
    has_coords = joined[(joined["lat"].notna()) & (joined["lng"].notna())]
    has_value = has_coords[has_coords["CurrentTotal"].notna() & (has_coords["CurrentTotal"] > 0)]
    print(f"\n  Addresses with coordinates: {len(has_coords):,}")
    print(f"  With assessed value: {len(has_value):,}")

    return joined


if __name__ == "__main__":
    main()
