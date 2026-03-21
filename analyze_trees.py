"""
Analyze Arlington public shade trees and correlate with property values.
Generates interactive charts and maps.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from folium.plugins import HeatMap
from pathlib import Path
from scipy.spatial import cKDTree

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"
CHART_DIR = OUTPUT_DIR / "charts"
MAP_DIR = OUTPUT_DIR / "maps"
CENTER = [42.4154, -71.1568]


def load_data():
    trees = pd.read_csv(INPUT_DIR / "trees_data.csv", low_memory=False)
    trees["PlantedDate"] = pd.to_datetime(trees.get("PlantedDate"), errors="coerce")
    trees["PlantedYear"] = pd.to_numeric(trees.get("PlantedYear"), errors="coerce")

    props = pd.read_csv(OUTPUT_DIR / "addresses_assessor_joined.csv", low_memory=False)
    props = props[props["lat"].notna() & props["lng"].notna()].copy()

    return trees, props


def save_chart(fig, name, height=600):
    path = CHART_DIR / f"{name}.html"
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=40, t=80, b=60),
    )
    fig.write_html(str(path), include_plotlyjs="cdn")
    print(f"  Saved: {path}")


def count_nearby_trees(props, trees, radius_deg=0.001):
    """Count trees within ~110m (0.001 deg) of each property."""
    tree_coords = trees[["lat", "lng"]].dropna().values
    tree_dbh = trees.loc[trees["lat"].notna(), "DBH"].fillna(0).values
    tree_stormwater = trees.loc[trees["lat"].notna(), "Stormwater"].fillna(0).values

    prop_coords = props[["lat", "lng"]].values

    tree_kd = cKDTree(tree_coords)

    counts = []
    avg_dbh = []
    total_stormwater = []

    for i in range(len(prop_coords)):
        idxs = tree_kd.query_ball_point(prop_coords[i], radius_deg)
        counts.append(len(idxs))
        if len(idxs) > 0:
            avg_dbh.append(np.mean(tree_dbh[idxs]))
            total_stormwater.append(np.sum(tree_stormwater[idxs]))
        else:
            avg_dbh.append(0)
            total_stormwater.append(0)

    props["NearbyTrees"] = counts
    props["AvgNearbyDBH"] = avg_dbh
    props["NearbyStormwater"] = total_stormwater

    return props


# ── Chart 21: Top Species ──────────────────────────────────────────────────

def chart_species(trees):
    top20 = trees["CommonName"].value_counts().head(20).reset_index()
    top20.columns = ["Species", "Count"]
    top20 = top20.sort_values("Count", ascending=True)

    fig = go.Figure(go.Bar(
        x=top20["Count"], y=top20["Species"],
        orientation="h", marker_color="#22c55e",
        text=top20["Count"], textposition="outside",
    ))
    fig.update_layout(title="Arlington, MA — Top 20 Public Shade Tree Species")
    fig.update_xaxes(title_text="Number of Trees")

    save_chart(fig, "21_top_species", height=650)


# ── Chart 22: Tree Size Distribution by Species ────────────────────────────

def chart_size_by_species(trees):
    top8 = trees["CommonName"].value_counts().head(8).index.tolist()
    subset = trees[trees["CommonName"].isin(top8) & trees["DBH"].notna()].copy()

    fig = px.box(
        subset, x="CommonName", y="DBH", color="CommonName",
        title="Arlington, MA — Tree Diameter by Species (Top 8)",
        labels={"CommonName": "Species", "DBH": "Diameter at Breast Height (in)"},
    )
    fig.update_layout(showlegend=False)

    save_chart(fig, "22_size_by_species", height=600)


# ── Chart 23: Planting History ─────────────────────────────────────────────

def chart_planting_history(trees):
    planted = trees[trees["PlantedYear"].notna() & (trees["PlantedYear"] >= 1980)].copy()

    yearly = planted.groupby("PlantedYear").size().reset_index(name="Count")
    yearly = yearly[yearly["PlantedYear"] <= 2025]

    # Top species planted each year
    top5_species = planted["CommonName"].value_counts().head(5).index.tolist()
    planted_sp = planted[planted["CommonName"].isin(top5_species)]
    yearly_sp = planted_sp.groupby(["PlantedYear", "CommonName"]).size().reset_index(name="Count")
    yearly_sp = yearly_sp[yearly_sp["PlantedYear"] <= 2025]

    fig = make_subplots(rows=2, cols=1, subplot_titles=[
        "Total Trees Planted per Year",
        "Top 5 Species Planted per Year",
    ])

    fig.add_trace(
        go.Bar(x=yearly["PlantedYear"], y=yearly["Count"],
               marker_color="#22c55e", name="All"),
        row=1, col=1,
    )

    colors = ["#2563eb", "#ef4444", "#f97316", "#7c3aed", "#0891b2"]
    for i, species in enumerate(top5_species):
        sp = yearly_sp[yearly_sp["CommonName"] == species]
        fig.add_trace(
            go.Scatter(x=sp["PlantedYear"], y=sp["Count"],
                       name=species, mode="lines+markers",
                       line=dict(color=colors[i % len(colors)])),
            row=2, col=1,
        )

    fig.update_layout(title="Arlington, MA — Tree Planting History", height=700)

    save_chart(fig, "23_planting_history", height=700)


# ── Chart 24: Stormwater & Pollutant Removal by Species ────────────────────

def chart_environmental_value(trees):
    species_env = trees.groupby("CommonName").agg(
        Count=("CommonName", "count"),
        TotalStormwater=("Stormwater", "sum"),
        TotalPollutants=("Pollutants", "sum"),
        MeanDBH=("DBH", "mean"),
    ).reset_index()
    species_env = species_env[species_env["Count"] >= 50]
    species_env["StormwaterPerTree"] = species_env["TotalStormwater"] / species_env["Count"]
    species_env["PollutantsPerTree"] = species_env["TotalPollutants"] / species_env["Count"]

    fig = px.scatter(
        species_env, x="StormwaterPerTree", y="PollutantsPerTree",
        size="Count", color="MeanDBH",
        color_continuous_scale="YlGn",
        hover_name="CommonName",
        title="Arlington, MA — Environmental Value by Species (trees with 50+ count)",
        labels={
            "StormwaterPerTree": "Avg Stormwater Intercepted (gal/yr/tree)",
            "PollutantsPerTree": "Avg Pollutants Removed (oz/yr/tree)",
            "MeanDBH": "Mean DBH (in)",
            "Count": "Number of Trees",
        },
    )

    save_chart(fig, "24_environmental_value", height=650)


# ── Chart 25: Trees vs Property Values Correlation ─────────────────────────

def chart_trees_vs_value(props):
    """Do more nearby trees = higher property values?"""
    df = props[
        (props["CurrentTotal"].notna())
        & (props["CurrentTotal"] > 0)
        & (props["CurrentTotal"] < 3_000_000)
        & (props["NearbyTrees"].notna())
    ].copy()

    # Bin by tree count
    df["TreeBin"] = pd.cut(
        df["NearbyTrees"],
        bins=[-1, 0, 2, 5, 10, 20, 100],
        labels=["0", "1-2", "3-5", "6-10", "11-20", "20+"],
    )

    bin_stats = df.groupby("TreeBin", observed=True).agg(
        MedianValue=("CurrentTotal", "median"),
        MeanValue=("CurrentTotal", "mean"),
        Count=("CurrentTotal", "count"),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=bin_stats["TreeBin"], y=bin_stats["MedianValue"],
            name="Median Assessed Value",
            marker_color="#22c55e",
            hovertemplate="Trees nearby: %{x}<br>Median Value: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=bin_stats["TreeBin"], y=bin_stats["Count"],
            name="Number of Properties", mode="lines+markers",
            line=dict(color="#94a3b8", width=2),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Arlington, MA — Property Value vs Nearby Tree Count (within ~110m)",
    )
    fig.update_yaxes(title_text="Median Assessed Value ($)", tickformat="$,.0f", secondary_y=False)
    fig.update_yaxes(title_text="Number of Properties", secondary_y=True)
    fig.update_xaxes(title_text="Number of Nearby Trees")

    save_chart(fig, "25_trees_vs_property_value")


# ── Chart 26: Tree Canopy Size vs Property Values ──────────────────────────

def chart_canopy_vs_value(props):
    """Does average nearby tree size correlate with value?"""
    df = props[
        (props["CurrentTotal"].notna())
        & (props["CurrentTotal"] > 0)
        & (props["CurrentTotal"] < 3_000_000)
        & (props["AvgNearbyDBH"] > 0)
    ].copy()

    df["DBHBin"] = pd.cut(
        df["AvgNearbyDBH"],
        bins=[0, 6, 12, 18, 24, 100],
        labels=["<6 in", "6-12 in", "12-18 in", "18-24 in", "24+ in"],
    )

    fig = px.box(
        df, x="DBHBin", y="CurrentTotal", color="DBHBin",
        title="Arlington, MA — Property Value by Avg Nearby Tree Size",
        labels={
            "DBHBin": "Avg Nearby Tree Diameter",
            "CurrentTotal": "Total Assessed Value",
        },
    )
    fig.update_yaxes(tickformat="$,.0f", range=[0, 2_500_000])
    fig.update_layout(showlegend=False)

    save_chart(fig, "26_canopy_size_vs_value", height=600)


# ── Map: Tree Canopy ───────────────────────────────────────────────────────

def map_tree_canopy(trees):
    """Map all trees colored by species group."""
    m = folium.Map(location=CENTER, zoom_start=14, tiles="CartoDB positron")

    top_species = trees["CommonName"].value_counts().head(6).index.tolist()
    colors = {
        top_species[0]: "#22c55e",  # Norway Maple
        top_species[1]: "#ef4444",  # Ash
        top_species[2]: "#2563eb",  # Red Maple
        top_species[3]: "#f97316",  # Honey Locust
        top_species[4]: "#7c3aed",  # Callery Pear
        top_species[5]: "#0891b2",  # London Planetree
    }

    subset = trees[trees["lat"].notna()].copy()

    for _, row in subset.iterrows():
        species = row.get("CommonName", "Unknown")
        color = colors.get(species, "#6b7280")
        dbh = row.get("DBH", 0) or 0
        radius = max(2, min(10, dbh / 5))

        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=0.3,
            popup=folium.Popup(
                f"<b>{species}</b><br>"
                f"DBH: {dbh:.0f} in<br>"
                f"Height: {row.get('Height', 'N/A')} ft<br>"
                f"Stormwater: {row.get('Stormwater', 0):,.0f} gal/yr<br>"
                f"Location: {row.get('AddrNum', '')} {row.get('RoadName', '')}",
                max_width=250,
            ),
        ).add_to(m)

    legend_items = "".join(
        f'<span style="color:{colors[s]};">&#9679;</span> {s}<br>'
        for s in top_species
    )
    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
    padding:12px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:12px;">
    <b>Species</b> (size = DBH)<br>
    {legend_items}
    <span style="color:#6b7280;">&#9679;</span> Other
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    path = MAP_DIR / "map_tree_canopy.html"
    m.save(str(path))
    print(f"  Saved: {path}")


# ── Map: Tree Density Heatmap ──────────────────────────────────────────────

def map_tree_heatmap(trees):
    """Heatmap weighted by stormwater interception."""
    m = folium.Map(location=CENTER, zoom_start=14, tiles="CartoDB dark_matter")

    subset = trees[trees["lat"].notna() & trees["Stormwater"].notna()].copy()

    heat_data = [
        [row["lat"], row["lng"], row["Stormwater"] / 1000]
        for _, row in subset.iterrows()
    ]

    HeatMap(
        heat_data, min_opacity=0.3,
        radius=10, blur=12, max_zoom=16,
    ).add_to(m)

    path = MAP_DIR / "map_tree_stormwater_heatmap.html"
    m.save(str(path))
    print(f"  Saved: {path}")


# ── Map: Trees + Property Values Combined ──────────────────────────────────

def map_trees_and_values(trees, props):
    """Overlay tree canopy on property value map."""
    m = folium.Map(location=CENTER, zoom_start=14, tiles="CartoDB positron")

    # Property values layer
    val_group = folium.FeatureGroup(name="Property Values")
    prop_subset = props[
        props["CurrentTotal"].notna() & (props["CurrentTotal"] > 0)
    ].drop_duplicates(subset=["lat", "lng"]).copy()

    def value_color(val):
        if val < 500_000:
            return "#fed7aa"
        elif val < 1_000_000:
            return "#fb923c"
        elif val < 1_500_000:
            return "#ea580c"
        else:
            return "#9a3412"

    for _, row in prop_subset.iterrows():
        val = row["CurrentTotal"]
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=2, color=value_color(val),
            fill=True, fill_color=value_color(val),
            fill_opacity=0.5, weight=0,
        ).add_to(val_group)

    val_group.add_to(m)

    # Trees layer
    tree_group = folium.FeatureGroup(name="Trees")
    tree_subset = trees[trees["lat"].notna()].copy()

    for _, row in tree_subset.iterrows():
        dbh = row.get("DBH", 0) or 0
        radius = max(2, min(8, dbh / 6))
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=radius, color="#22c55e",
            fill=True, fill_color="#22c55e",
            fill_opacity=0.6, weight=0.3,
            popup=folium.Popup(
                f"<b>{row.get('CommonName', '?')}</b><br>DBH: {dbh:.0f} in",
                max_width=200,
            ),
        ).add_to(tree_group)

    tree_group.add_to(m)

    folium.LayerControl().add_to(m)

    path = MAP_DIR / "map_trees_and_values.html"
    m.save(str(path))
    print(f"  Saved: {path}")


def main():
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    MAP_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    trees, props = load_data()
    print(f"  {len(trees):,} trees, {len(props):,} properties\n")

    print("Computing nearby tree counts for each property...")
    props = count_nearby_trees(props, trees)
    has_trees = (props["NearbyTrees"] > 0).sum()
    print(f"  Properties with 1+ nearby tree: {has_trees:,}\n")

    print("Generating charts...\n")
    chart_species(trees)
    chart_size_by_species(trees)
    chart_planting_history(trees)
    chart_environmental_value(trees)
    chart_trees_vs_value(props)
    chart_canopy_vs_value(props)

    print("\nGenerating maps...\n")
    map_tree_canopy(trees)
    map_tree_heatmap(trees)
    map_trees_and_values(trees, props)

    print(f"\nDone! Charts in {CHART_DIR}, maps in {MAP_DIR}")


if __name__ == "__main__":
    main()
