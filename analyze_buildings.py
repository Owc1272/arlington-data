"""
Analyze Arlington buildings joined with assessor data.
Generates interactive Plotly charts in output/charts/.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"
CHART_DIR = OUTPUT_DIR / "charts"


def load_data():
    """Load buildings-only and joined datasets."""
    bldg = pd.read_csv(INPUT_DIR / "buildings_data.csv", low_memory=False)
    joined = pd.read_csv(OUTPUT_DIR / "buildings_assessor_joined.csv", low_memory=False)

    # Parse dates
    for col in ["SaleDate"]:
        if col in joined.columns:
            joined[col] = pd.to_datetime(joined[col], errors="coerce")

    joined["SaleYear"] = pd.to_numeric(joined.get("SaleYear"), errors="coerce")
    joined["ValidSale"] = (
        joined["SalePrice"].notna()
        & (joined["SalePrice"] > 1000)
        & (joined["SaleYear"].notna())
        & (joined["SaleYear"] >= 1980)
    )

    return bldg, joined


def save_chart(fig, name, height=600):
    path = CHART_DIR / f"{name}.html"
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=40, t=80, b=60),
    )
    fig.write_html(str(path), include_plotlyjs="cdn")
    print(f"  Saved: {path}")


# ── Chart 11: Building Footprint Size Distribution ─────────────────────────

def chart_footprint_distribution(bldg):
    """Histogram of building footprint sizes by structure type."""
    df = bldg[
        (bldg["AreaSqFt"].notna())
        & (bldg["AreaSqFt"] > 0)
        & (bldg["AreaSqFt"] < 10_000)
        & (bldg["StrucType"].isin(["Building", "Out Building"]))
    ].copy()

    fig = px.histogram(
        df, x="AreaSqFt", color="StrucType",
        nbins=80, barmode="overlay", opacity=0.7,
        title="Arlington, MA — Building Footprint Size Distribution",
        labels={"AreaSqFt": "Footprint Area (sqft)", "StrucType": "Type"},
    )
    fig.update_xaxes(title_text="Footprint Area (sqft)")
    fig.update_yaxes(title_text="Count")

    save_chart(fig, "11_footprint_distribution")


# ── Chart 12: Building Height Distribution ──────────────────────────────────

def chart_height_distribution(bldg):
    """Histogram of building heights."""
    df = bldg[
        (bldg["TopHeight"].notna())
        & (bldg["TopHeight"] > 0)
        & (bldg["StrucType"] == "Building")
    ].copy()

    # Heights seem to be elevations — compute actual building height
    if "BaseElev" in df.columns:
        df["ActualHeight"] = df["TopHeight"] - df["BaseElev"]
        df = df[df["ActualHeight"] > 0]
        height_col = "ActualHeight"
        label = "Building Height (Top - Base, ft)"
    else:
        height_col = "TopHeight"
        label = "Top Height (ft)"

    fig = px.histogram(
        df, x=height_col, nbins=60,
        title="Arlington, MA — Building Height Distribution",
        labels={height_col: label},
        color_discrete_sequence=["#3b82f6"],
    )
    fig.update_yaxes(title_text="Count")

    save_chart(fig, "12_height_distribution")


# ── Chart 13: Value per Building SqFt by Zoning ────────────────────────────

def chart_value_per_sqft_by_zone(joined):
    """Box plot of assessed value per building sqft across zones."""
    df = joined[
        (joined["CurrentTotal"].notna())
        & (joined["CurrentTotal"] > 0)
        & (joined["AreaSqFt"].notna())
        & (joined["AreaSqFt"] > 100)
        & (joined["StrucType"] == "Building")
    ].copy()

    df["ValuePerBldgSqFt"] = df["CurrentTotal"] / df["AreaSqFt"]
    df = df[df["ValuePerBldgSqFt"].between(10, 5000)]

    top_zones = df["Z_Desc"].value_counts().head(8).index.tolist()
    df = df[df["Z_Desc"].isin(top_zones)]

    fig = px.box(
        df, x="Z_Desc", y="ValuePerBldgSqFt", color="Z_Desc",
        title="Arlington, MA — Assessed Value per Building Sqft by Zoning",
        labels={"Z_Desc": "Zoning District", "ValuePerBldgSqFt": "Value per Bldg SqFt ($)"},
    )
    fig.update_yaxes(tickformat="$,.0f", range=[0, 3000])
    fig.update_layout(showlegend=False)

    save_chart(fig, "13_value_per_sqft_by_zone", height=650)


# ── Chart 14: Building Size vs Assessed Value ───────────────────────────────

def chart_size_vs_value(joined):
    """Scatter of building footprint vs assessed value, colored by zoning."""
    df = joined[
        (joined["CurrentTotal"].notna())
        & (joined["CurrentTotal"] > 0)
        & (joined["CurrentTotal"] < 5_000_000)
        & (joined["AreaSqFt"].notna())
        & (joined["AreaSqFt"] > 100)
        & (joined["AreaSqFt"] < 10_000)
        & (joined["StrucType"] == "Building")
    ].copy()

    top_zones = df["Z_Desc"].value_counts().head(6).index.tolist()
    df = df[df["Z_Desc"].isin(top_zones)]

    fig = px.scatter(
        df, x="AreaSqFt", y="CurrentTotal",
        color="Z_Desc", opacity=0.4,
        title="Arlington, MA — Building Footprint vs Assessed Value",
        labels={
            "AreaSqFt": "Building Footprint (sqft)",
            "CurrentTotal": "Total Assessed Value",
            "Z_Desc": "Zoning",
        },
        hover_data=["FullAddr", "YearBuilt", "LUC_Desc"],
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "14_size_vs_value", height=700)


# ── Chart 15: Height vs Value by Land Use ───────────────────────────────────

def chart_height_vs_value(joined):
    """Building height vs assessed value."""
    df = joined[
        (joined["CurrentTotal"].notna())
        & (joined["CurrentTotal"] > 0)
        & (joined["CurrentTotal"] < 10_000_000)
        & (joined["TopHeight"].notna())
        & (joined["BaseElev"].notna())
        & (joined["StrucType"] == "Building")
    ].copy()

    df["ActualHeight"] = df["TopHeight"] - df["BaseElev"]
    df = df[(df["ActualHeight"] > 5) & (df["ActualHeight"] < 150)]

    type_map = {
        "101  - One Family": "Single Family",
        "102  - Condo": "Condo",
        "104  - Two Family": "Two Family",
        "105  - Three Fam.": "Three Family",
        "111  - Apts. 4-8": "Apartments (4-8)",
        "112  - Apts. 8 Plus": "Apartments (8+)",
    }
    df["PropType"] = df["LUC_Desc"].map(type_map)
    df = df[df["PropType"].notna()]

    fig = px.scatter(
        df, x="ActualHeight", y="CurrentTotal",
        color="PropType", opacity=0.4,
        title="Arlington, MA — Building Height vs Assessed Value by Property Type",
        labels={
            "ActualHeight": "Building Height (ft)",
            "CurrentTotal": "Total Assessed Value",
            "PropType": "Property Type",
        },
        hover_data=["FullAddr", "YearBuilt"],
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "15_height_vs_value", height=700)


# ── Chart 16: Footprint Size by Decade Built ────────────────────────────────

def chart_footprint_by_decade(joined):
    """How has building size changed over time?"""
    df = joined[
        (joined["AreaSqFt"].notna())
        & (joined["AreaSqFt"] > 100)
        & (joined["AreaSqFt"] < 10_000)
        & (joined["YearBuilt"].notna())
        & (joined["YearBuilt"] > 1850)
        & (joined["YearBuilt"] <= 2025)
        & (joined["StrucType"] == "Building")
    ].copy()

    df["Decade"] = (df["YearBuilt"] // 10) * 10

    decade_stats = df.groupby("Decade").agg(
        MedianFootprint=("AreaSqFt", "median"),
        MeanFootprint=("AreaSqFt", "mean"),
        Count=("AreaSqFt", "count"),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=decade_stats["Decade"], y=decade_stats["Count"],
            name="Number of Buildings", marker_color="#94a3b8", opacity=0.4,
            hovertemplate="Decade: %{x}s<br>Count: %{y}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=decade_stats["Decade"], y=decade_stats["MedianFootprint"],
            name="Median Footprint", mode="lines+markers",
            line=dict(color="#2563eb", width=3),
            hovertemplate="Decade: %{x}s<br>Median: %{y:,.0f} sqft<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=decade_stats["Decade"], y=decade_stats["MeanFootprint"],
            name="Mean Footprint", mode="lines",
            line=dict(color="#7c3aed", width=2, dash="dash"),
            hovertemplate="Decade: %{x}s<br>Mean: %{y:,.0f} sqft<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.update_layout(title="Arlington, MA — Building Footprint Size by Decade Built")
    fig.update_yaxes(title_text="Footprint Area (sqft)", secondary_y=False)
    fig.update_yaxes(title_text="Number of Buildings", secondary_y=True)
    fig.update_xaxes(title_text="Decade Built")

    save_chart(fig, "16_footprint_by_decade")


# ── Chart 17: Value Density — Value per Lot SqFt vs Building Coverage ───────

def chart_value_density(joined):
    """How does building coverage ratio relate to value density?"""
    df = joined[
        (joined["CurrentTotal"].notna())
        & (joined["CurrentTotal"] > 0)
        & (joined["AreaSqFt"].notna())
        & (joined["AreaSqFt"] > 50)
        & (joined["GISSqFt"].notna())
        & (joined["GISSqFt"] > 500)
        & (joined["StrucType"] == "Building")
    ].copy()

    df["CoverageRatio"] = df["AreaSqFt"] / df["GISSqFt"]
    df["ValuePerLotSqFt"] = df["CurrentTotal"] / df["GISSqFt"]

    # Filter reasonable ranges
    df = df[
        (df["CoverageRatio"] > 0.01)
        & (df["CoverageRatio"] < 1.0)
        & (df["ValuePerLotSqFt"] > 10)
        & (df["ValuePerLotSqFt"] < 2000)
    ]

    top_zones = df["Z_Desc"].value_counts().head(5).index.tolist()
    df = df[df["Z_Desc"].isin(top_zones)]

    fig = px.scatter(
        df, x="CoverageRatio", y="ValuePerLotSqFt",
        color="Z_Desc", opacity=0.3,
        title="Arlington, MA — Building Coverage vs Value Density",
        labels={
            "CoverageRatio": "Building Coverage Ratio (bldg sqft / lot sqft)",
            "ValuePerLotSqFt": "Assessed Value per Lot SqFt ($)",
            "Z_Desc": "Zoning",
        },
        hover_data=["FullAddr", "LUC_Desc"],
    )
    fig.update_yaxes(tickformat="$,.0f")
    fig.update_xaxes(tickformat=".0%")

    save_chart(fig, "17_value_density", height=700)


# ── Chart 18: Structure Type Breakdown with Value ───────────────────────────

def chart_structure_type_value(joined):
    """Buildings vs outbuildings — count and value comparison."""
    df = joined[
        (joined["StrucType"].isin(["Building", "Out Building"]))
        & (joined["CurrentTotal"].notna())
        & (joined["CurrentTotal"] > 0)
    ].copy()

    stats = df.groupby("StrucType").agg(
        Count=("StrucType", "count"),
        MedianArea=("AreaSqFt", "median"),
        MedianValue=("CurrentTotal", "median"),
        TotalValue=("CurrentTotal", "sum"),
    ).reset_index()

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=["Count", "Median Footprint (sqft)", "Median Assessed Value"],
    )

    fig.add_trace(
        go.Bar(x=stats["StrucType"], y=stats["Count"],
               marker_color=["#3b82f6", "#f97316"], name="Count"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=stats["StrucType"], y=stats["MedianArea"],
               marker_color=["#3b82f6", "#f97316"], name="Area"),
        row=1, col=2,
    )
    fig.add_trace(
        go.Bar(x=stats["StrucType"], y=stats["MedianValue"],
               marker_color=["#3b82f6", "#f97316"], name="Value"),
        row=1, col=3,
    )

    fig.update_layout(
        title="Arlington, MA — Buildings vs Out Buildings",
        showlegend=False,
    )
    fig.update_yaxes(tickformat="$,.0f", row=1, col=3)

    save_chart(fig, "18_structure_type_comparison")


# ── Chart 19: Top 50 Most Valuable Buildings ────────────────────────────────

def chart_top_buildings(joined):
    """Horizontal bar chart of the 50 most valuable buildings."""
    df = joined[
        (joined["CurrentTotal"].notna())
        & (joined["CurrentTotal"] > 0)
        & (joined["StrucType"] == "Building")
        & (joined["FullAddr"].notna())
    ].copy()

    # De-duplicate by address (take highest value per address)
    df = df.sort_values("CurrentTotal", ascending=False).drop_duplicates(subset="FullAddr")
    top50 = df.nlargest(50, "CurrentTotal")

    top50 = top50.sort_values("CurrentTotal", ascending=True)
    labels = top50["FullAddr"].str.title()

    fig = go.Figure(go.Bar(
        x=top50["CurrentTotal"],
        y=labels,
        orientation="h",
        marker_color="#2563eb",
        hovertemplate="%{y}<br>Value: $%{x:,.0f}<br><extra></extra>",
        text=top50["CurrentTotal"].apply(lambda v: f"${v:,.0f}"),
        textposition="outside",
    ))

    fig.update_layout(
        title="Arlington, MA — 50 Most Valuable Properties (by assessment)",
        xaxis_title="Total Assessed Value",
        xaxis_tickformat="$,.0f",
    )

    save_chart(fig, "19_top_50_buildings", height=1200)


# ── Chart 20: Sale Price Appreciation by Building Size ──────────────────────

def chart_appreciation_by_size(joined):
    """Do larger buildings appreciate faster?"""
    df = joined[
        joined["ValidSale"]
        & (joined["CurrentTotal"] > 0)
        & (joined["SalePrice"] > 1000)
        & (joined["SalePrice"] < 5_000_000)
        & (joined["AreaSqFt"].notna())
        & (joined["AreaSqFt"] > 100)
        & (joined["StrucType"] == "Building")
        & (joined["SaleYear"] >= 2000)
        & (joined["SaleYear"] <= 2023)
    ].copy()

    df["Appreciation"] = (df["CurrentTotal"] / df["SalePrice"] - 1) * 100
    df = df[df["Appreciation"].between(-50, 500)]

    # Bin by footprint size
    df["SizeBin"] = pd.cut(
        df["AreaSqFt"],
        bins=[0, 800, 1200, 1600, 2000, 3000, 10000],
        labels=["<800", "800-1200", "1200-1600", "1600-2000", "2000-3000", "3000+"],
    )

    fig = px.box(
        df, x="SizeBin", y="Appreciation", color="SizeBin",
        title="Arlington, MA — Appreciation (Assessed vs Sale) by Building Footprint Size",
        labels={"SizeBin": "Building Footprint (sqft)", "Appreciation": "Appreciation (%)"},
    )
    fig.update_yaxes(ticksuffix="%")
    fig.update_layout(showlegend=False)

    save_chart(fig, "20_appreciation_by_building_size", height=650)


def main():
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    bldg, joined = load_data()
    print(f"  {len(bldg):,} buildings, {len(joined):,} joined rows\n")

    print("Generating charts...\n")

    chart_footprint_distribution(bldg)
    chart_height_distribution(bldg)
    chart_value_per_sqft_by_zone(joined)
    chart_size_vs_value(joined)
    chart_height_vs_value(joined)
    chart_footprint_by_decade(joined)
    chart_value_density(joined)
    chart_structure_type_value(joined)
    chart_top_buildings(joined)
    chart_appreciation_by_size(joined)

    print(f"\nDone! 10 new charts in {CHART_DIR}")


if __name__ == "__main__":
    main()
