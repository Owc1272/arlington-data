"""
Fetch all Buildings data from Arlington Structures (view) layer 4,
join with assessor data, and save combined dataset.

Source: Arlington_Structures_(view)/FeatureServer/4
"""

import requests
import pandas as pd
import json
import time
from pathlib import Path

BASE_URL = (
    "https://services2.arcgis.com/s1Sh73K7qtP9JdrG/arcgis/rest/services/"
    "Arlington_Structures_(view)/FeatureServer/4"
)
PAGE_SIZE = 2000
INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_page(offset=0):
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
    rows = [f["attributes"] for f in features]
    df = pd.DataFrame(rows)

    # Convert edit date
    if "last_edited_date" in df.columns:
        df["last_edited_date"] = pd.to_datetime(
            df["last_edited_date"], unit="ms", errors="coerce"
        )

    return df


def join_with_assessor(bldg_df):
    """Join buildings to assessor data on parcel ID."""
    assessor_path = INPUT_DIR / "assessor_data.csv"
    if not assessor_path.exists():
        print("  WARNING: assessor_data.csv not found, skipping join.")
        return bldg_df

    print("  Loading assessor data...")
    assessor = pd.read_csv(assessor_path, low_memory=False)

    # The join key: buildings have Parcel_id, assessor has ParcelID
    # Clean up for matching
    bldg_df["Parcel_id_clean"] = bldg_df["Parcel_id"].astype(str).str.strip()
    assessor["ParcelID_clean"] = assessor["ParcelID"].astype(str).str.strip()

    print(f"  Buildings with parcel ID: {bldg_df['Parcel_id_clean'].notna().sum():,}")
    print(f"  Assessor parcels: {len(assessor):,}")

    # Join — buildings to assessor (many buildings can share a parcel)
    joined = bldg_df.merge(
        assessor,
        left_on="Parcel_id_clean",
        right_on="ParcelID_clean",
        how="left",
        suffixes=("_bldg", "_assess"),
    )

    matched = joined["ParcelID_clean"].notna().sum()
    print(f"  Matched: {matched:,} / {len(bldg_df):,} buildings ({matched/len(bldg_df)*100:.1f}%)")

    return joined


def print_summary(df, joined_df):
    print(f"\n{'='*60}")
    print("  Arlington, MA — Buildings Data Summary")
    print(f"{'='*60}\n")

    print(f"  Total buildings: {len(df):,}")

    if "StrucType" in df.columns:
        print(f"\n  Structure Types:")
        for st, count in df["StrucType"].value_counts().head(10).items():
            print(f"    {st:<30} {count:>6,}")

    if "AreaSqFt" in df.columns:
        area = df["AreaSqFt"].dropna()
        print(f"\n  Building Footprint (sqft):")
        print(f"    Median: {area.median():,.0f}")
        print(f"    Mean:   {area.mean():,.0f}")
        print(f"    Max:    {area.max():,.0f}")

    if "TopHeight" in df.columns:
        ht = df["TopHeight"].dropna()
        if len(ht) > 0:
            print(f"\n  Building Height (ft):")
            print(f"    Median: {ht.median():,.1f}")
            print(f"    Mean:   {ht.mean():,.1f}")
            print(f"    Max:    {ht.max():,.1f}")

    if "CurrentTotal" in joined_df.columns:
        has_val = joined_df[joined_df["CurrentTotal"].notna() & (joined_df["CurrentTotal"] > 0)]
        if len(has_val) > 0:
            has_val = has_val.copy()
            has_val["ValuePerBldgSqFt"] = has_val["CurrentTotal"] / has_val["AreaSqFt"]
            vpsf = has_val["ValuePerBldgSqFt"].dropna()
            vpsf = vpsf[vpsf.between(1, 5000)]
            print(f"\n  Assessed Value per Building SqFt (joined):")
            print(f"    Median: ${vpsf.median():,.0f}")
            print(f"    Mean:   ${vpsf.mean():,.0f}")


def main():
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Fetching all Buildings from Arlington Structures...\n")
    features = fetch_all()

    # Save raw JSON
    json_path = INPUT_DIR / "buildings_raw.json"
    print(f"\nSaving raw JSON to {json_path}...")
    with open(json_path, "w") as f:
        json.dump(features, f)

    # Build DataFrame
    print("Building DataFrame...")
    df = build_dataframe(features)

    csv_path = INPUT_DIR / "buildings_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"Buildings CSV saved: {len(df):,} rows x {len(df.columns)} cols")

    # Join with assessor
    print("\nJoining with assessor data...")
    joined = join_with_assessor(df)

    joined_path = OUTPUT_DIR / "buildings_assessor_joined.csv"
    joined.to_csv(joined_path, index=False)
    print(f"Joined CSV saved: {len(joined):,} rows x {len(joined.columns)} cols")

    # Summary
    print_summary(df, joined)

    return df, joined


if __name__ == "__main__":
    main()
