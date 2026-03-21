"""
Analyze Arlington, MA Assessor data for property value trends.

Generates interactive Plotly HTML charts saved to output/charts/.
Open any .html file in a browser to explore interactively.
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
    """Load assessor CSV and clean it up."""
    df = pd.read_csv(INPUT_DIR / "assessor_data.csv", low_memory=False)

    # Parse SaleDate
    df["SaleDate"] = pd.to_datetime(df["SaleDate"], errors="coerce")
    df["SaleYear"] = pd.to_numeric(df["SaleYear"], errors="coerce")

    # Filter helper: valid market sales (exclude $0, nominal $1/$10 transfers)
    df["ValidSale"] = (df["SalePrice"] > 1000) & (df["SaleYear"] >= 1980)

    return df


def save_chart(fig, name, height=600):
    """Save a Plotly figure as interactive HTML."""
    path = CHART_DIR / f"{name}.html"
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=40, t=80, b=60),
    )
    fig.write_html(str(path), include_plotlyjs="cdn")
    print(f"  Saved: {path}")


# ── Chart 1: Median Sale Price by Year ──────────────────────────────────────

def chart_price_trend(df):
    """Median and mean sale price by year, with transaction volume."""
    sales = df[df["ValidSale"]].copy()
    yearly = sales.groupby("SaleYear").agg(
        MedianPrice=("SalePrice", "median"),
        MeanPrice=("SalePrice", "mean"),
        NumSales=("SalePrice", "count"),
    ).reset_index()
    yearly = yearly[yearly["SaleYear"] <= 2025]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=yearly["SaleYear"], y=yearly["MedianPrice"],
            name="Median Sale Price", mode="lines+markers",
            line=dict(color="#2563eb", width=3),
            hovertemplate="Year: %{x}<br>Median: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=yearly["SaleYear"], y=yearly["MeanPrice"],
            name="Mean Sale Price", mode="lines",
            line=dict(color="#7c3aed", width=2, dash="dash"),
            hovertemplate="Year: %{x}<br>Mean: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=yearly["SaleYear"], y=yearly["NumSales"],
            name="Number of Sales", opacity=0.3,
            marker_color="#94a3b8",
            hovertemplate="Year: %{x}<br>Sales: %{y}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(title="Arlington, MA — Sale Price Trends (1980–2025)")
    fig.update_yaxes(title_text="Sale Price ($)", secondary_y=False, tickformat="$,.0f")
    fig.update_yaxes(title_text="Number of Sales", secondary_y=True)
    fig.update_xaxes(title_text="Year")

    save_chart(fig, "01_price_trends")


# ── Chart 2: Price Trends by Property Type ──────────────────────────────────

def chart_price_by_type(df):
    """Median sale price over time by land use category."""
    sales = df[df["ValidSale"]].copy()

    # Map to broader categories
    type_map = {
        "101  - One Family": "Single Family",
        "102  - Condo": "Condo",
        "104  - Two Family": "Two Family",
        "105  - Three Fam.": "Three Family",
        "111  - Apts. 4-8": "Apartments (4-8)",
        "112  - Apts. 8 Plus": "Apartments (8+)",
    }
    sales["PropType"] = sales["LUC_Desc"].map(type_map)
    sales = sales[sales["PropType"].notna()]

    yearly = (
        sales.groupby(["SaleYear", "PropType"])["SalePrice"]
        .median()
        .reset_index()
    )
    yearly = yearly[yearly["SaleYear"] <= 2025]

    fig = px.line(
        yearly, x="SaleYear", y="SalePrice", color="PropType",
        title="Arlington, MA — Median Sale Price by Property Type",
        labels={"SaleYear": "Year", "SalePrice": "Median Sale Price", "PropType": "Type"},
        markers=True,
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "02_price_by_type")


# ── Chart 3: Price by Zoning District ───────────────────────────────────────

def chart_price_by_zoning(df):
    """Box plot of current assessed values by zoning district."""
    # Top zoning districts by count
    top_zones = df["Z_Desc"].value_counts().head(8).index.tolist()
    subset = df[df["Z_Desc"].isin(top_zones) & (df["CurrentTotal"] > 0)].copy()

    fig = px.box(
        subset, x="Z_Desc", y="CurrentTotal", color="Z_Desc",
        title="Arlington, MA — Assessed Value Distribution by Zoning",
        labels={"Z_Desc": "Zoning District", "CurrentTotal": "Total Assessed Value"},
    )
    fig.update_yaxes(tickformat="$,.0f", range=[0, 3_000_000])
    fig.update_layout(showlegend=False)

    save_chart(fig, "03_value_by_zoning", height=650)


# ── Chart 4: Assessed Value vs Last Sale Price ──────────────────────────────

def chart_assessed_vs_sale(df):
    """Scatter: last sale price vs current assessed value, colored by sale year."""
    sales = df[
        df["ValidSale"]
        & (df["CurrentTotal"] > 0)
        & (df["SalePrice"] < 5_000_000)
        & (df["CurrentTotal"] < 5_000_000)
        & (df["SaleYear"] >= 2000)
    ].copy()

    fig = px.scatter(
        sales, x="SalePrice", y="CurrentTotal",
        color="SaleYear",
        color_continuous_scale="Viridis",
        opacity=0.5,
        title="Arlington, MA — Last Sale Price vs Current Assessed Value (sales since 2000)",
        labels={
            "SalePrice": "Last Sale Price",
            "CurrentTotal": "Current Assessed Value (FY2026)",
            "SaleYear": "Sale Year",
        },
        hover_data=["FullAddress", "SaleYear", "LUC_Desc"],
    )

    # Add 1:1 reference line
    max_val = 4_000_000
    fig.add_trace(
        go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode="lines", name="1:1 Line",
            line=dict(color="red", dash="dash", width=1),
        )
    )

    fig.update_xaxes(tickformat="$,.0f")
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "04_assessed_vs_sale", height=700)


# ── Chart 5: Appreciation — Current Value / Sale Price by Sale Year ─────────

def chart_appreciation(df):
    """How much have properties appreciated since their last sale?"""
    sales = df[
        df["ValidSale"]
        & (df["CurrentTotal"] > 0)
        & (df["SalePrice"] > 1000)
        & (df["SaleYear"] >= 1985)
        & (df["SaleYear"] <= 2025)
    ].copy()

    sales["Appreciation"] = (sales["CurrentTotal"] / sales["SalePrice"] - 1) * 100

    # Remove extreme outliers
    sales = sales[sales["Appreciation"].between(-50, 500)]

    yearly = sales.groupby("SaleYear").agg(
        MedianAppreciation=("Appreciation", "median"),
        Count=("Appreciation", "count"),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=yearly["SaleYear"], y=yearly["MedianAppreciation"],
            name="Median Appreciation %",
            marker_color=yearly["MedianAppreciation"].apply(
                lambda v: "#16a34a" if v >= 0 else "#dc2626"
            ),
            hovertemplate="Year sold: %{x}<br>Appreciation: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.update_layout(
        title="Arlington, MA — Property Appreciation: Current Assessed Value vs Sale Price",
        xaxis_title="Year of Last Sale",
    )
    fig.update_yaxes(
        title_text="Median Appreciation (%)",
        ticksuffix="%",
        secondary_y=False,
    )

    save_chart(fig, "05_appreciation_by_sale_year")


# ── Chart 6: Building Age Distribution ──────────────────────────────────────

def chart_year_built(df):
    """Distribution of year built, colored by current value."""
    built = df[(df["YearBuilt"] > 1800) & (df["YearBuilt"] <= 2025)].copy()

    # Bin by decade
    built["Decade"] = (built["YearBuilt"] // 10) * 10
    decade_stats = built.groupby("Decade").agg(
        Count=("YearBuilt", "count"),
        MedianValue=("CurrentTotal", "median"),
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=decade_stats["Decade"], y=decade_stats["Count"],
            name="Number of Properties",
            marker_color="#3b82f6",
            hovertemplate="Decade: %{x}s<br>Count: %{y}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=decade_stats["Decade"], y=decade_stats["MedianValue"],
            name="Median Assessed Value", mode="lines+markers",
            line=dict(color="#f97316", width=3),
            hovertemplate="Decade: %{x}s<br>Median Value: $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(title="Arlington, MA — Housing Stock Age & Value")
    fig.update_yaxes(title_text="Number of Properties", secondary_y=False)
    fig.update_yaxes(title_text="Median Assessed Value ($)", tickformat="$,.0f", secondary_y=True)
    fig.update_xaxes(title_text="Decade Built")

    save_chart(fig, "06_year_built_distribution")


# ── Chart 7: Land vs Building Value Ratio ───────────────────────────────────

def chart_land_vs_building(df):
    """Land value as % of total, by property type and decade built."""
    subset = df[
        (df["CurrentTotal"] > 0)
        & (df["landValue"] > 0)
        & (df["YearBuilt"] > 1800)
    ].copy()

    subset["LandPct"] = subset["landValue"] / subset["CurrentTotal"] * 100
    subset["Decade"] = (subset["YearBuilt"] // 10) * 10

    type_map = {
        "101  - One Family": "Single Family",
        "102  - Condo": "Condo",
        "104  - Two Family": "Two Family",
    }
    subset["PropType"] = subset["LUC_Desc"].map(type_map)
    subset = subset[subset["PropType"].notna() & (subset["Decade"] >= 1870)]

    decade_type = (
        subset.groupby(["Decade", "PropType"])["LandPct"]
        .median()
        .reset_index()
    )

    fig = px.line(
        decade_type, x="Decade", y="LandPct", color="PropType",
        title="Arlington, MA — Land Value as % of Total by Decade Built & Type",
        labels={"Decade": "Decade Built", "LandPct": "Land Value %", "PropType": "Type"},
        markers=True,
    )
    fig.update_yaxes(ticksuffix="%")

    save_chart(fig, "07_land_vs_building_ratio")


# ── Chart 8: Sale Price per SqFt Over Time by Zip ──────────────────────────

def chart_price_sqft_by_zip(df):
    """Price per square foot trends by zip code."""
    sales = df[
        df["ValidSale"]
        & (df["SalePricePerSqFt"].notna())
        & (df["SalePricePerSqFt"] > 0)
        & (df["SalePricePerSqFt"] < 500)
        & (df["SaleYear"] >= 2000)
        & (df["ZipCode"].notna())
    ].copy()

    yearly_zip = (
        sales.groupby(["SaleYear", "ZipCode"])["SalePricePerSqFt"]
        .median()
        .reset_index()
    )
    yearly_zip = yearly_zip[yearly_zip["SaleYear"] <= 2025]

    fig = px.line(
        yearly_zip, x="SaleYear", y="SalePricePerSqFt",
        color="ZipCode", markers=True,
        title="Arlington, MA — Median Sale Price per Sq Ft by Zip Code (2000–2025)",
        labels={
            "SaleYear": "Year",
            "SalePricePerSqFt": "Price per Sq Ft (lot)",
            "ZipCode": "Zip Code",
        },
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "08_price_sqft_by_zip")


# ── Chart 9: Heatmap — Median Value by Zoning × Land Use ───────────────────

def chart_zoning_landuse_heatmap(df):
    """Heatmap of median assessed value by zoning and land use."""
    top_zones = df["Z_Desc"].value_counts().head(6).index.tolist()
    top_luc = df["LUC_Desc"].value_counts().head(6).index.tolist()

    subset = df[
        df["Z_Desc"].isin(top_zones)
        & df["LUC_Desc"].isin(top_luc)
        & (df["CurrentTotal"] > 0)
    ]

    pivot = subset.pivot_table(
        values="CurrentTotal", index="LUC_Desc", columns="Z_Desc",
        aggfunc="median",
    )

    fig = px.imshow(
        pivot, text_auto="$,.0f",
        title="Arlington, MA — Median Assessed Value: Zoning × Land Use",
        labels=dict(x="Zoning District", y="Land Use", color="Median Value"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )

    save_chart(fig, "09_zoning_landuse_heatmap", height=500)


# ── Chart 10: Recent Sales Timeline ────────────────────────────────────────

def chart_recent_sales(df):
    """Interactive scatter of all sales since 2015, sized by price."""
    sales = df[
        df["ValidSale"]
        & (df["SaleYear"] >= 2015)
        & (df["SalePrice"] < 5_000_000)
    ].copy()

    sales["SaleDateStr"] = sales["SaleDate"].dt.strftime("%Y-%m-%d")

    fig = px.scatter(
        sales, x="SaleDate", y="SalePrice",
        color="LUC_Desc", size="GISSqFt",
        size_max=15, opacity=0.6,
        title="Arlington, MA — Individual Property Sales (2015–2025)",
        labels={
            "SaleDate": "Sale Date",
            "SalePrice": "Sale Price",
            "LUC_Desc": "Land Use",
            "GISSqFt": "Lot Size (sqft)",
        },
        hover_data=["FullAddress", "SaleDateStr", "YearBuilt", "Z_Desc"],
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "10_recent_sales_scatter", height=700)


def main():
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    df = load_data()
    print(f"  {len(df):,} parcels loaded\n")

    print("Generating charts...\n")

    chart_price_trend(df)
    chart_price_by_type(df)
    chart_price_by_zoning(df)
    chart_assessed_vs_sale(df)
    chart_appreciation(df)
    chart_year_built(df)
    chart_land_vs_building(df)
    chart_price_sqft_by_zip(df)
    chart_zoning_landuse_heatmap(df)
    chart_recent_sales(df)

    print(f"\nDone! Open any .html file in output/charts/ in your browser.")
    print(f"All charts are interactive — hover, zoom, pan, and filter.")


if __name__ == "__main__":
    main()
