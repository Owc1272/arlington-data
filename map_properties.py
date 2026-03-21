"""
Generate interactive Folium maps of Arlington property data.
Maps are saved as HTML files in output/maps/.
"""

import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
MAP_DIR = OUTPUT_DIR / "maps"

# Arlington center
CENTER = [42.4154, -71.1568]


def load_data():
    df = pd.read_csv(OUTPUT_DIR / "addresses_assessor_joined.csv", low_memory=False)
    df["SaleDate"] = pd.to_datetime(df.get("SaleDate"), errors="coerce")
    df["SaleYear"] = pd.to_numeric(df.get("SaleYear"), errors="coerce")
    # Filter to rows with valid coords
    df = df[df["lat"].notna() & df["lng"].notna()].copy()
    return df


def value_color(val):
    """Color scale for property values."""
    if val < 500_000:
        return "#22c55e"  # green
    elif val < 750_000:
        return "#84cc16"  # lime
    elif val < 1_000_000:
        return "#eab308"  # yellow
    elif val < 1_500_000:
        return "#f97316"  # orange
    elif val < 2_000_000:
        return "#ef4444"  # red
    else:
        return "#7c3aed"  # purple


def year_color(year):
    """Color scale for year built."""
    if pd.isna(year) or year < 1850:
        return "#6b7280"  # gray
    elif year < 1900:
        return "#7c3aed"  # purple
    elif year < 1920:
        return "#2563eb"  # blue
    elif year < 1940:
        return "#0891b2"  # cyan
    elif year < 1960:
        return "#22c55e"  # green
    elif year < 1980:
        return "#eab308"  # yellow
    elif year < 2000:
        return "#f97316"  # orange
    else:
        return "#ef4444"  # red


def sale_recency_color(year):
    """Color by how recently the property sold."""
    if pd.isna(year):
        return "#d1d5db"  # light gray
    elif year >= 2020:
        return "#ef4444"  # red - recent
    elif year >= 2015:
        return "#f97316"  # orange
    elif year >= 2010:
        return "#eab308"  # yellow
    elif year >= 2000:
        return "#22c55e"  # green
    else:
        return "#3b82f6"  # blue - older


# ── Map 1: Property Values ─────────────────────────────────────────────────

def map_property_values(df):
    """Circle markers colored by assessed value."""
    m = folium.Map(location=CENTER, zoom_start=14, tiles="CartoDB positron")

    subset = df[df["CurrentTotal"].notna() & (df["CurrentTotal"] > 0)].copy()
    # De-duplicate by coordinates to avoid overplotting condos
    subset = subset.sort_values("CurrentTotal", ascending=False).drop_duplicates(
        subset=["lat", "lng"]
    )

    for _, row in subset.iterrows():
        val = row["CurrentTotal"]
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=3,
            color=value_color(val),
            fill=True,
            fill_color=value_color(val),
            fill_opacity=0.7,
            weight=0.5,
            popup=folium.Popup(
                f"<b>{row.get('FullAddr', 'N/A')}</b><br>"
                f"Value: ${val:,.0f}<br>"
                f"Land: ${row.get('landValue', 0):,.0f}<br>"
                f"Building: ${row.get('BuildValue', 0):,.0f}<br>"
                f"Zoning: {row.get('Z_Desc', 'N/A')}<br>"
                f"Year Built: {int(row['YearBuilt']) if pd.notna(row.get('YearBuilt')) else 'N/A'}",
                max_width=250,
            ),
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
    padding:12px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:13px;">
    <b>Assessed Value</b><br>
    <span style="color:#22c55e;">&#9679;</span> &lt; $500K<br>
    <span style="color:#84cc16;">&#9679;</span> $500K–$750K<br>
    <span style="color:#eab308;">&#9679;</span> $750K–$1M<br>
    <span style="color:#f97316;">&#9679;</span> $1M–$1.5M<br>
    <span style="color:#ef4444;">&#9679;</span> $1.5M–$2M<br>
    <span style="color:#7c3aed;">&#9679;</span> &gt; $2M
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    path = MAP_DIR / "map_property_values.html"
    m.save(str(path))
    print(f"  Saved: {path}")


# ── Map 2: Value Heatmap ───────────────────────────────────────────────────

def map_value_heatmap(df):
    """Heatmap weighted by assessed value."""
    m = folium.Map(location=CENTER, zoom_start=14, tiles="CartoDB dark_matter")

    subset = df[df["CurrentTotal"].notna() & (df["CurrentTotal"] > 0)].copy()
    subset = subset.drop_duplicates(subset=["lat", "lng"])

    heat_data = [
        [row["lat"], row["lng"], row["CurrentTotal"] / 1_000_000]
        for _, row in subset.iterrows()
    ]

    HeatMap(
        heat_data,
        min_opacity=0.3,
        radius=12,
        blur=15,
        max_zoom=16,
    ).add_to(m)

    path = MAP_DIR / "map_value_heatmap.html"
    m.save(str(path))
    print(f"  Saved: {path}")


# ── Map 3: Year Built ──────────────────────────────────────────────────────

def map_year_built(df):
    """Properties colored by year built."""
    m = folium.Map(location=CENTER, zoom_start=14, tiles="CartoDB positron")

    subset = df[df["YearBuilt"].notna() & (df["YearBuilt"] > 1800)].copy()
    subset = subset.drop_duplicates(subset=["lat", "lng"])

    for _, row in subset.iterrows():
        yr = row["YearBuilt"]
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=2.5,
            color=year_color(yr),
            fill=True,
            fill_color=year_color(yr),
            fill_opacity=0.7,
            weight=0.5,
            popup=folium.Popup(
                f"<b>{row.get('FullAddr', 'N/A')}</b><br>"
                f"Year Built: {int(yr)}<br>"
                f"Value: ${row.get('CurrentTotal', 0):,.0f}<br>"
                f"Type: {row.get('LUC_Desc', 'N/A')}",
                max_width=250,
            ),
        ).add_to(m)

    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
    padding:12px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:13px;">
    <b>Year Built</b><br>
    <span style="color:#7c3aed;">&#9679;</span> Before 1900<br>
    <span style="color:#2563eb;">&#9679;</span> 1900–1919<br>
    <span style="color:#0891b2;">&#9679;</span> 1920–1939<br>
    <span style="color:#22c55e;">&#9679;</span> 1940–1959<br>
    <span style="color:#eab308;">&#9679;</span> 1960–1979<br>
    <span style="color:#f97316;">&#9679;</span> 1980–1999<br>
    <span style="color:#ef4444;">&#9679;</span> 2000+
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    path = MAP_DIR / "map_year_built.html"
    m.save(str(path))
    print(f"  Saved: {path}")


# ── Map 4: Recent Sales ────────────────────────────────────────────────────

def map_recent_sales(df):
    """Sales since 2015, sized by price."""
    m = folium.Map(location=CENTER, zoom_start=14, tiles="CartoDB positron")

    subset = df[
        (df["SalePrice"].notna())
        & (df["SalePrice"] > 1000)
        & (df["SalePrice"] < 5_000_000)
        & (df["SaleYear"].notna())
        & (df["SaleYear"] >= 2015)
    ].copy()
    subset = subset.drop_duplicates(subset=["lat", "lng"])

    for _, row in subset.iterrows():
        price = row["SalePrice"]
        radius = max(3, min(12, price / 200_000))

        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=radius,
            color=sale_recency_color(row["SaleYear"]),
            fill=True,
            fill_color=sale_recency_color(row["SaleYear"]),
            fill_opacity=0.6,
            weight=0.5,
            popup=folium.Popup(
                f"<b>{row.get('FullAddr', 'N/A')}</b><br>"
                f"Sale Price: ${price:,.0f}<br>"
                f"Sale Date: {row['SaleDate'].strftime('%Y-%m-%d') if pd.notna(row['SaleDate']) else 'N/A'}<br>"
                f"Current Value: ${row.get('CurrentTotal', 0):,.0f}<br>"
                f"Type: {row.get('LUC_Desc', 'N/A')}",
                max_width=250,
            ),
        ).add_to(m)

    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
    padding:12px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:13px;">
    <b>Sale Year</b> (size = price)<br>
    <span style="color:#ef4444;">&#9679;</span> 2020–2025<br>
    <span style="color:#f97316;">&#9679;</span> 2015–2019<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    path = MAP_DIR / "map_recent_sales.html"
    m.save(str(path))
    print(f"  Saved: {path}")


# ── Map 5: Value per SqFt ──────────────────────────────────────────────────

def map_value_per_sqft(df):
    """Assessed value per lot sqft — highlights undervalued/premium land."""
    m = folium.Map(location=CENTER, zoom_start=14, tiles="CartoDB positron")

    subset = df[
        (df["CurrentTotal"].notna())
        & (df["CurrentTotal"] > 0)
        & (df["GISSqFt"].notna())
        & (df["GISSqFt"] > 500)
    ].copy()
    subset = subset.drop_duplicates(subset=["lat", "lng"])
    subset["ValPerSqFt"] = subset["CurrentTotal"] / subset["GISSqFt"]

    def vpsf_color(v):
        if v < 50:
            return "#22c55e"
        elif v < 100:
            return "#84cc16"
        elif v < 150:
            return "#eab308"
        elif v < 200:
            return "#f97316"
        elif v < 300:
            return "#ef4444"
        else:
            return "#7c3aed"

    for _, row in subset.iterrows():
        v = row["ValPerSqFt"]
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=3,
            color=vpsf_color(v),
            fill=True,
            fill_color=vpsf_color(v),
            fill_opacity=0.7,
            weight=0.5,
            popup=folium.Popup(
                f"<b>{row.get('FullAddr', 'N/A')}</b><br>"
                f"Value/Lot SqFt: ${v:,.0f}<br>"
                f"Total Value: ${row['CurrentTotal']:,.0f}<br>"
                f"Lot Size: {row['GISSqFt']:,.0f} sqft<br>"
                f"Zoning: {row.get('Z_Desc', 'N/A')}",
                max_width=250,
            ),
        ).add_to(m)

    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
    padding:12px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:13px;">
    <b>Value per Lot SqFt</b><br>
    <span style="color:#22c55e;">&#9679;</span> &lt; $50<br>
    <span style="color:#84cc16;">&#9679;</span> $50–$100<br>
    <span style="color:#eab308;">&#9679;</span> $100–$150<br>
    <span style="color:#f97316;">&#9679;</span> $150–$200<br>
    <span style="color:#ef4444;">&#9679;</span> $200–$300<br>
    <span style="color:#7c3aed;">&#9679;</span> &gt; $300
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    path = MAP_DIR / "map_value_per_sqft.html"
    m.save(str(path))
    print(f"  Saved: {path}")


def main():
    MAP_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    df = load_data()
    print(f"  {len(df):,} geocoded records\n")

    print("Generating maps...\n")
    map_property_values(df)
    map_value_heatmap(df)
    map_year_built(df)
    map_recent_sales(df)
    map_value_per_sqft(df)

    print(f"\nDone! 5 maps in {MAP_DIR}")


if __name__ == "__main__":
    main()
