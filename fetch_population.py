"""
Fetch historical population and demographic data for Arlington, MA.
Sources:
  - Hardcoded decennial Census data (1900-1990)
  - Census Bureau API: Decennial 2000, 2010, 2020
  - Census Bureau API: ACS 5-Year Estimates (2013-2022)

Output: website/data/population.json
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

OUTPUT_PATH = Path(__file__).parent / "website" / "data" / "population.json"

# Arlington, MA geography (county subdivision, not "place")
STATE = "25"
COUNTY = "017"  # Middlesex County
COUSUB = "01605"  # Arlington town

# Historical decennial Census data for Arlington, MA (1900-1990)
HISTORICAL_DECENNIAL = [
    {"year": 1900, "population": 8603},
    {"year": 1910, "population": 11187},
    {"year": 1920, "population": 18665},
    {"year": 1930, "population": 36094},
    {"year": 1940, "population": 40013},
    {"year": 1950, "population": 44353},
    {"year": 1960, "population": 49953},
    {"year": 1970, "population": 53524},
    {"year": 1980, "population": 48219},
    {"year": 1990, "population": 44630},
]

# ACS variables — split into two batches to stay under API limits
ACS_BATCH_1 = [
    "B01003_001E",  # Total population
    "B01002_001E",  # Median age
    "B01001_002E",  # Male
    "B01001_026E",  # Female
    "B02001_002E",  # White
    "B02001_003E",  # Black
    "B02001_005E",  # Asian
    "B02001_008E",  # Two or more races
    "B03003_003E",  # Hispanic or Latino
    "B25001_001E",  # Total housing units
    "B25003_002E",  # Owner-occupied
    "B25003_003E",  # Renter-occupied
    "B19013_001E",  # Median household income
    "B17001_002E",  # Below poverty level
    "NAME",
]

ACS_BATCH_2 = [
    # Age groups (from B01001) — male
    "B01001_003E", "B01001_004E", "B01001_005E", "B01001_006E",
    "B01001_007E", "B01001_008E", "B01001_009E", "B01001_010E",
    "B01001_011E", "B01001_012E", "B01001_013E", "B01001_014E",
    "B01001_015E", "B01001_016E", "B01001_017E", "B01001_018E",
    "B01001_019E", "B01001_020E", "B01001_021E", "B01001_022E",
    "B01001_023E", "B01001_024E", "B01001_025E",
    # Age groups (from B01001) — female
    "B01001_027E", "B01001_028E", "B01001_029E", "B01001_030E",
    "B01001_031E", "B01001_032E", "B01001_033E", "B01001_034E",
    "B01001_035E", "B01001_036E", "B01001_037E", "B01001_038E",
    "B01001_039E", "B01001_040E", "B01001_041E", "B01001_042E",
    "B01001_043E", "B01001_044E", "B01001_045E", "B01001_046E",
    "B01001_047E", "B01001_048E", "B01001_049E",
    "NAME",
]


def safe_int(val):
    """Convert a value to int, returning None if not possible.
    Filters Census sentinel values like -888888888, -666666666, -999999999."""
    if val is None:
        return None
    try:
        v = int(float(val))
        if v < -100000:  # Census sentinel values
            return None
        return v
    except (ValueError, TypeError):
        return None


def safe_float(val):
    """Convert a value to float, returning None if not possible."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def fetch_census_api(url):
    """Fetch from Census Bureau API with retry logic."""
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 204:
                return None
            print(f"  HTTP {resp.status_code}, retrying...")
        except requests.RequestException as e:
            print(f"  Request error: {e}, retrying...")
        time.sleep(1)
    return None


def fetch_decennial():
    """Fetch decennial Census population for 2000, 2010, 2020."""
    results = list(HISTORICAL_DECENNIAL)

    # 2000 Decennial
    print("Fetching 2000 Decennial Census...")
    url = f"https://api.census.gov/data/2000/dec/sf1?get=P001001,NAME&for=county%20subdivision:{COUSUB}&in=state:{STATE}&in=county:{COUNTY}"
    data = fetch_census_api(url)
    if data and len(data) > 1:
        pop = safe_int(data[1][0])
        if pop:
            results.append({"year": 2000, "population": pop})
            print(f"  2000: {pop:,}")
    else:
        print("  2000: Using fallback")
        results.append({"year": 2000, "population": 42389})

    time.sleep(0.5)

    # 2010 Decennial
    print("Fetching 2010 Decennial Census...")
    url = f"https://api.census.gov/data/2010/dec/sf1?get=P001001,NAME&for=county%20subdivision:{COUSUB}&in=state:{STATE}&in=county:{COUNTY}"
    data = fetch_census_api(url)
    if data and len(data) > 1:
        pop = safe_int(data[1][0])
        if pop:
            results.append({"year": 2010, "population": pop})
            print(f"  2010: {pop:,}")
    else:
        print("  2010: Using fallback")
        results.append({"year": 2010, "population": 42844})

    time.sleep(0.5)

    # 2020 Decennial (uses different variable name)
    print("Fetching 2020 Decennial Census...")
    url = f"https://api.census.gov/data/2020/dec/pl?get=P1_001N,NAME&for=county%20subdivision:{COUSUB}&in=state:{STATE}&in=county:{COUNTY}"
    data = fetch_census_api(url)
    if data and len(data) > 1:
        pop = safe_int(data[1][0])
        if pop:
            results.append({"year": 2020, "population": pop})
            print(f"  2020: {pop:,}")
    else:
        print("  2020: Using fallback")
        results.append({"year": 2020, "population": 46204})

    results.sort(key=lambda x: x["year"])
    return results


def fetch_acs_year(year):
    """Fetch ACS 5-year estimate for a single year (two batched API calls)."""
    geo = f"for=county%20subdivision:{COUSUB}&in=state:{STATE}&in=county:{COUNTY}"
    base = f"https://api.census.gov/data/{year}/acs/acs5"

    # Batch 1: core demographics
    vars1 = ",".join(ACS_BATCH_1)
    data1 = fetch_census_api(f"{base}?get={vars1}&{geo}")
    if not data1 or len(data1) < 2:
        return None
    row = dict(zip(data1[0], data1[1]))

    time.sleep(0.3)

    # Batch 2: age detail
    vars2 = ",".join(ACS_BATCH_2)
    data2 = fetch_census_api(f"{base}?get={vars2}&{geo}")
    if data2 and len(data2) >= 2:
        row.update(dict(zip(data2[0], data2[1])))

    def val(key):
        return safe_int(row.get(key))

    def fval(key):
        return safe_float(row.get(key))

    # Aggregate age groups from detailed male+female breakdowns
    under_5 = (val("B01001_003E") or 0) + (val("B01001_027E") or 0)
    age_5_9 = (val("B01001_004E") or 0) + (val("B01001_028E") or 0)
    age_10_14 = (val("B01001_005E") or 0) + (val("B01001_029E") or 0)
    age_15_17 = (val("B01001_006E") or 0) + (val("B01001_030E") or 0)
    age_18_24 = sum(val(k) or 0 for k in [
        "B01001_007E", "B01001_008E", "B01001_009E", "B01001_010E",
        "B01001_031E", "B01001_032E", "B01001_033E", "B01001_034E"
    ])
    age_25_34 = sum(val(k) or 0 for k in [
        "B01001_011E", "B01001_012E", "B01001_035E", "B01001_036E"
    ])
    age_35_44 = sum(val(k) or 0 for k in [
        "B01001_013E", "B01001_014E", "B01001_037E", "B01001_038E"
    ])
    age_45_54 = sum(val(k) or 0 for k in [
        "B01001_015E", "B01001_016E", "B01001_039E", "B01001_040E"
    ])
    age_55_64 = sum(val(k) or 0 for k in [
        "B01001_017E", "B01001_018E", "B01001_019E",
        "B01001_041E", "B01001_042E", "B01001_043E"
    ])
    age_65_74 = sum(val(k) or 0 for k in [
        "B01001_020E", "B01001_021E", "B01001_022E",
        "B01001_044E", "B01001_045E", "B01001_046E"
    ])
    age_75_plus = sum(val(k) or 0 for k in [
        "B01001_023E", "B01001_024E", "B01001_025E",
        "B01001_047E", "B01001_048E", "B01001_049E"
    ])

    return {
        "year": year,
        "total_population": val("B01003_001E"),
        "male": val("B01001_002E"),
        "female": val("B01001_026E"),
        "median_age": fval("B01002_001E"),
        "age_distribution": {
            "under_5": under_5,
            "5_to_9": age_5_9,
            "10_to_14": age_10_14,
            "15_to_17": age_15_17,
            "18_to_24": age_18_24,
            "25_to_34": age_25_34,
            "35_to_44": age_35_44,
            "45_to_54": age_45_54,
            "55_to_64": age_55_64,
            "65_to_74": age_65_74,
            "75_plus": age_75_plus,
        },
        "race": {
            "white": val("B02001_002E"),
            "black": val("B02001_003E"),
            "asian": val("B02001_005E"),
            "two_or_more": val("B02001_008E"),
            "hispanic_latino": val("B03003_003E"),
        },
        "housing": {
            "total_units": val("B25001_001E"),
            "owner_occupied": val("B25003_002E"),
            "renter_occupied": val("B25003_003E"),
        },
        "income": {
            "median_household": val("B19013_001E"),
            "below_poverty": val("B17001_002E"),
        },
    }


def fetch_acs_annual():
    """Fetch ACS 5-year estimates for multiple years."""
    results = []
    for year in range(2009, 2024):
        print(f"Fetching ACS 5-Year {year}...")
        entry = fetch_acs_year(year)
        if entry:
            print(f"  Population: {entry['total_population']:,}")
            results.append(entry)
        else:
            print(f"  Not available, skipping")
        time.sleep(0.5)
    return results


# --- Additional ACS datasets: Profiles (DP) and Subject Tables (S) ---

# B-tables (stable variable codes across all years)
# Education: B15002 (by sex, need to aggregate male+female)
EDUCATION_VARS = [
    "B15002_001E",  # Total pop 25+
    # Male education levels
    "B15002_003E", "B15002_004E", "B15002_005E", "B15002_006E",  # No school thru 8th
    "B15002_007E", "B15002_008E", "B15002_009E", "B15002_010E",  # 9th-12th no diploma
    "B15002_011E",  # HS graduate (male)
    "B15002_012E", "B15002_013E",  # Some college (male)
    "B15002_014E",  # Associate's (male)
    "B15002_015E",  # Bachelor's (male)
    "B15002_016E", "B15002_017E", "B15002_018E",  # Master's, professional, doctorate (male)
    # Female education levels
    "B15002_020E", "B15002_021E", "B15002_022E", "B15002_023E",  # No school thru 8th
    "B15002_024E", "B15002_025E", "B15002_026E", "B15002_027E",  # 9th-12th no diploma
    "B15002_028E",  # HS graduate (female)
    "B15002_029E", "B15002_030E",  # Some college (female)
    "B15002_031E",  # Associate's (female)
    "B15002_032E",  # Bachelor's (female)
    "B15002_033E", "B15002_034E", "B15002_035E",  # Master's, professional, doctorate (female)
    "NAME",
]

# Employment: B23025 (employment status)
EMPLOYMENT_VARS = [
    "B23025_001E",  # Total pop 16+
    "B23025_002E",  # In labor force
    "B23025_004E",  # Employed
    "B23025_005E",  # Unemployed
    "NAME",
]

# Occupation: C24010 (occupation by sex)
OCCUPATION_VARS = [
    "C24010_001E",  # Total civilian employed 16+
    "C24010_003E",  # Mgmt/business/science/arts (male)
    "C24010_019E",  # Service (male)
    "C24010_027E",  # Sales/office (male)
    "C24010_033E",  # Construction/maintenance (male)
    "C24010_037E",  # Production/transport (male)
    "C24010_039E",  # Mgmt/business/science/arts (female)
    "C24010_055E",  # Service (female)
    "C24010_063E",  # Sales/office (female)
    "C24010_069E",  # Construction/maintenance (female)
    "C24010_073E",  # Production/transport (female)
    "NAME",
]

# Housing: B25001, B25003, B25077, B25064, B25024 (all stable)
HOUSING_DETAIL_VARS = [
    "B25077_001E",  # Median home value
    "B25064_001E",  # Median gross rent
    "B25024_001E",  # Total housing units (by structure type)
    "B25024_002E",  # 1 detached
    "B25024_003E",  # 1 attached
    "B25024_004E",  # 2 units
    "B25024_005E",  # 3-4 units
    "B25024_006E",  # 5-9 units
    "B25024_007E",  # 10-19 units
    "B25024_008E",  # 20-49 units
    "B25024_009E",  # 50+ units
    "B25024_010E",  # Mobile home
    "B25002_001E",  # Total units
    "B25002_002E",  # Occupied
    "B25002_003E",  # Vacant
    "NAME",
]

# Commuting: B08301 (means of transport, stable)
COMMUTE_VARS = [
    "B08301_001E",  # Total workers
    "B08301_003E",  # Drove alone
    "B08301_004E",  # Carpooled
    "B08301_010E",  # Public transit
    "B08301_018E",  # Bicycle
    "B08301_019E",  # Walked
    "B08301_021E",  # Worked from home
    "B08303_001E",  # Total (travel time base)
    "NAME",
]


def fetch_btable_year(year, variables):
    """Fetch ACS 5-year B-table variables for a single year."""
    geo = f"for=county%20subdivision:{COUSUB}&in=state:{STATE}&in=county:{COUNTY}"
    var_str = ",".join(variables)
    url = f"https://api.census.gov/data/{year}/acs/acs5?get={var_str}&{geo}"
    data = fetch_census_api(url)
    if not data or len(data) < 2:
        return None
    return dict(zip(data[0], data[1]))


def fetch_additional_datasets():
    """Fetch education, employment, occupation, housing, commuting for all available years using stable B-tables."""
    results = []

    for year in range(2009, 2024):
        print(f"Fetching additional data for {year}...")
        entry = {"year": year}

        def val(row, key):
            return safe_int(row.get(key)) if row else None

        # Education (B15002)
        row = fetch_btable_year(year, EDUCATION_VARS)
        if row:
            # Aggregate male + female
            less_than_9th = sum(val(row, k) or 0 for k in ["B15002_003E","B15002_004E","B15002_005E","B15002_006E","B15002_020E","B15002_021E","B15002_022E","B15002_023E"])
            no_diploma = sum(val(row, k) or 0 for k in ["B15002_007E","B15002_008E","B15002_009E","B15002_010E","B15002_024E","B15002_025E","B15002_026E","B15002_027E"])
            hs_grad = (val(row, "B15002_011E") or 0) + (val(row, "B15002_028E") or 0)
            some_college = sum(val(row, k) or 0 for k in ["B15002_012E","B15002_013E","B15002_029E","B15002_030E"])
            associates = (val(row, "B15002_014E") or 0) + (val(row, "B15002_031E") or 0)
            bachelors = (val(row, "B15002_015E") or 0) + (val(row, "B15002_032E") or 0)
            graduate = sum(val(row, k) or 0 for k in ["B15002_016E","B15002_017E","B15002_018E","B15002_033E","B15002_034E","B15002_035E"])
            entry["education"] = {
                "pop_25_plus": val(row, "B15002_001E"),
                "less_than_9th": less_than_9th,
                "no_diploma": no_diploma,
                "high_school": hs_grad,
                "some_college": some_college,
                "associates": associates,
                "bachelors": bachelors,
                "graduate": graduate,
            }
        time.sleep(0.3)

        # Employment (B23025)
        row = fetch_btable_year(year, EMPLOYMENT_VARS)
        if row:
            entry["employment"] = {
                "pop_16_plus": val(row, "B23025_001E"),
                "in_labor_force": val(row, "B23025_002E"),
                "employed": val(row, "B23025_004E"),
                "unemployed": val(row, "B23025_005E"),
            }
        time.sleep(0.3)

        # Occupation (C24010)
        row = fetch_btable_year(year, OCCUPATION_VARS)
        if row:
            entry["occupation"] = {
                "mgmt_business_science_arts": (val(row,"C24010_003E") or 0) + (val(row,"C24010_039E") or 0),
                "service": (val(row,"C24010_019E") or 0) + (val(row,"C24010_055E") or 0),
                "sales_office": (val(row,"C24010_027E") or 0) + (val(row,"C24010_063E") or 0),
                "construction_maintenance": (val(row,"C24010_033E") or 0) + (val(row,"C24010_069E") or 0),
                "production_transportation": (val(row,"C24010_037E") or 0) + (val(row,"C24010_073E") or 0),
            }
        time.sleep(0.3)

        # Housing detail (B25077, B25064, B25024, B25002)
        row = fetch_btable_year(year, HOUSING_DETAIL_VARS)
        if row:
            entry["housing_detail"] = {
                "total_units": val(row, "B25002_001E"),
                "occupied": val(row, "B25002_002E"),
                "vacant": val(row, "B25002_003E"),
                "median_home_value": val(row, "B25077_001E"),
                "median_rent": val(row, "B25064_001E"),
            }
            entry["housing_structure"] = {
                "single_detached": val(row, "B25024_002E"),
                "single_attached": val(row, "B25024_003E"),
                "two_units": val(row, "B25024_004E"),
                "three_four": val(row, "B25024_005E"),
                "five_nine": val(row, "B25024_006E"),
                "ten_nineteen": val(row, "B25024_007E"),
                "twenty_plus": (val(row, "B25024_008E") or 0) + (val(row, "B25024_009E") or 0),
                "mobile": val(row, "B25024_010E"),
            }
        time.sleep(0.3)

        # Commuting (B08301)
        row = fetch_btable_year(year, COMMUTE_VARS)
        if row:
            total = val(row, "B08301_001E") or 1
            entry["commute"] = {
                "total_workers": val(row, "B08301_001E"),
                "drove_alone": val(row, "B08301_003E"),
                "carpooled": val(row, "B08301_004E"),
                "public_transit": val(row, "B08301_010E"),
                "bicycle": val(row, "B08301_018E"),
                "walked": val(row, "B08301_019E"),
                "wfh": val(row, "B08301_021E"),
                # Calculate percentages
                "drove_alone_pct": round((val(row, "B08301_003E") or 0) / total * 100, 1),
                "public_transit_pct": round((val(row, "B08301_010E") or 0) / total * 100, 1),
                "walked_pct": round((val(row, "B08301_019E") or 0) / total * 100, 1),
                "bicycle_pct": round((val(row, "B08301_018E") or 0) / total * 100, 1),
                "wfh_pct": round((val(row, "B08301_021E") or 0) / total * 100, 1),
            }
        time.sleep(0.3)

        # Only add if we got at least some data
        if len(entry) > 1:
            print(f"  OK ({len(entry) - 1} sections)")
            results.append(entry)
        else:
            print(f"  No data")

    return results


def build_summary(decennial, acs_annual):
    """Build summary statistics from the latest available data."""
    latest = acs_annual[-1] if acs_annual else None
    if not latest:
        return {}

    # Find 10-year growth from decennial data
    dec_2020 = next((d for d in decennial if d["year"] == 2020), None)
    dec_2010 = next((d for d in decennial if d["year"] == 2010), None)
    growth_rate = None
    if dec_2020 and dec_2010:
        growth_rate = round((dec_2020["population"] - dec_2010["population"]) / dec_2010["population"] * 100, 1)

    housing = latest.get("housing", {})
    total_units = housing.get("total_units")
    owner = housing.get("owner_occupied")
    owner_pct = None
    if total_units and owner and total_units > 0:
        occupied = (owner or 0) + (housing.get("renter_occupied") or 0)
        if occupied > 0:
            owner_pct = round(owner / occupied * 100, 1)

    return {
        "current_population": latest["total_population"],
        "data_year": latest["year"],
        "growth_rate_10yr": growth_rate,
        "median_age": latest.get("median_age"),
        "median_income": latest.get("income", {}).get("median_household"),
        "total_housing_units": total_units,
        "owner_occupied_pct": owner_pct,
    }


def main():
    print("=" * 60)
    print("  Arlington, MA — Population Data Fetcher")
    print("  Source: US Census Bureau API")
    print("=" * 60)
    print()

    # Fetch decennial data
    print("--- Decennial Census (1900-2020) ---")
    decennial = fetch_decennial()
    print(f"Total decennial records: {len(decennial)}")
    print()

    # Fetch ACS annual data
    print("--- ACS 5-Year Estimates (2013-2023) ---")
    acs_annual = fetch_acs_annual()
    print(f"Total ACS years: {len(acs_annual)}")
    print()

    # Fetch additional datasets (DP02, DP03, DP04, S0801)
    print("--- Additional Datasets (DP02/DP03/DP04/S0801) ---")
    additional = fetch_additional_datasets()
    print(f"Total additional years: {len(additional)}")
    print()

    # Build summary
    summary = build_summary(decennial, acs_annual)

    # Assemble output
    output = {
        "generated": datetime.now().isoformat(),
        "source": "US Census Bureau",
        "geography": "Arlington town, Middlesex County, Massachusetts",
        "decennial": decennial,
        "acs_annual": acs_annual,
        "additional": additional,
        "summary": summary,
    }

    # Write JSON
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Output saved to {OUTPUT_PATH}")
    print(f"Summary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
