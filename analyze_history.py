"""
Analyze historical assessment data for Appleton St properties.
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
    assess = pd.read_csv(INPUT_DIR / "appleton_historical_assessments.csv")
    sales = pd.read_csv(INPUT_DIR / "appleton_historical_sales.csv")
    sales["SaleDate"] = pd.to_datetime(sales["SaleDate"], errors="coerce")
    return assess, sales


def save_chart(fig, name, height=600):
    path = CHART_DIR / f"{name}.html"
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=40, t=80, b=60),
    )
    fig.write_html(str(path), include_plotlyjs="cdn")
    print(f"  Saved: {path}")


# ── Chart 27: Appleton St — Median Assessment Over Time ────────────────────

def chart_median_trend(assess):
    yearly = assess.groupby("Year").agg(
        MedianTotal=("TotalValue", "median"),
        MedianBuilding=("BuildingValue", "median"),
        MedianLand=("LandValue", "median"),
        Count=("TotalValue", "count"),
    ).reset_index()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["MedianTotal"],
        name="Total Value", mode="lines+markers",
        line=dict(color="#2563eb", width=3),
        hovertemplate="Year: %{x}<br>Total: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["MedianLand"],
        name="Land Value", mode="lines",
        line=dict(color="#f97316", width=2),
        hovertemplate="Year: %{x}<br>Land: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["MedianBuilding"],
        name="Building Value", mode="lines",
        line=dict(color="#22c55e", width=2),
        hovertemplate="Year: %{x}<br>Building: $%{y:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        title="Appleton St, Arlington — Median Assessed Value (1992–2026)",
        xaxis_title="Fiscal Year",
    )
    fig.update_yaxes(title_text="Assessed Value ($)", tickformat="$,.0f")

    save_chart(fig, "27_appleton_median_trend")


# ── Chart 28: Year-over-Year Change ────────────────────────────────────────

def chart_yoy_change(assess):
    yearly = assess.groupby("Year")["TotalValue"].median().reset_index()
    yearly = yearly.sort_values("Year")
    yearly["PctChange"] = yearly["TotalValue"].pct_change() * 100

    fig = go.Figure(go.Bar(
        x=yearly["Year"], y=yearly["PctChange"],
        marker_color=yearly["PctChange"].apply(
            lambda v: "#22c55e" if v >= 0 else "#ef4444"
        ),
        hovertemplate="Year: %{x}<br>Change: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        title="Appleton St — Year-over-Year Median Assessment Change",
        xaxis_title="Fiscal Year",
    )
    fig.update_yaxes(title_text="% Change", ticksuffix="%")

    save_chart(fig, "28_appleton_yoy_change")


# ── Chart 29: Individual Property Trajectories ─────────────────────────────

def chart_spaghetti(assess):
    """Every property's value trajectory as a line."""
    fig = go.Figure()

    addresses = assess["FullAddress"].unique()
    for addr in addresses:
        prop = assess[assess["FullAddress"] == addr].sort_values("Year")
        fig.add_trace(go.Scatter(
            x=prop["Year"], y=prop["TotalValue"],
            mode="lines", name=addr,
            line=dict(width=1),
            opacity=0.4,
            hovertemplate=f"{addr}<br>Year: %{{x}}<br>Value: $%{{y:,.0f}}<extra></extra>",
            showlegend=False,
        ))

    # Add median overlay
    yearly = assess.groupby("Year")["TotalValue"].median().reset_index()
    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["TotalValue"],
        mode="lines+markers", name="Median",
        line=dict(color="#ef4444", width=4),
        hovertemplate="Median<br>Year: %{x}<br>Value: $%{y:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        title="Appleton St — Every Property's Assessment History (median in red)",
        xaxis_title="Fiscal Year",
    )
    fig.update_yaxes(title_text="Total Assessed Value ($)", tickformat="$,.0f")

    save_chart(fig, "29_appleton_spaghetti", height=700)


# ── Chart 30: Land vs Building Value Shift ─────────────────────────────────

def chart_land_building_shift(assess):
    yearly = assess.groupby("Year").agg(
        MedianTotal=("TotalValue", "median"),
        MedianBuilding=("BuildingValue", "median"),
        MedianLand=("LandValue", "median"),
    ).reset_index()

    yearly["LandPct"] = yearly["MedianLand"] / yearly["MedianTotal"] * 100
    yearly["BuildingPct"] = yearly["MedianBuilding"] / yearly["MedianTotal"] * 100

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["LandPct"],
        name="Land %", fill="tozeroy",
        line=dict(color="#f97316"),
        hovertemplate="Year: %{x}<br>Land: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["BuildingPct"],
        name="Building %", fill="tozeroy",
        line=dict(color="#22c55e"),
        hovertemplate="Year: %{x}<br>Building: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        title="Appleton St — Land vs Building as % of Total Assessment",
        xaxis_title="Fiscal Year",
    )
    fig.update_yaxes(title_text="% of Total Value", ticksuffix="%")

    save_chart(fig, "30_appleton_land_building_pct")


# ── Chart 31: Cumulative Appreciation ──────────────────────────────────────

def chart_cumulative_appreciation(assess):
    """Indexed to 1992 = 100."""
    yearly = assess.groupby("Year").agg(
        MedianTotal=("TotalValue", "median"),
        MedianBuilding=("BuildingValue", "median"),
        MedianLand=("LandValue", "median"),
    ).reset_index().sort_values("Year")

    base_total = yearly.iloc[0]["MedianTotal"]
    base_building = yearly.iloc[0]["MedianBuilding"]
    base_land = yearly.iloc[0]["MedianLand"]

    yearly["TotalIndex"] = yearly["MedianTotal"] / base_total * 100
    yearly["BuildingIndex"] = yearly["MedianBuilding"] / base_building * 100
    yearly["LandIndex"] = yearly["MedianLand"] / base_land * 100

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["TotalIndex"],
        name="Total Value", mode="lines+markers",
        line=dict(color="#2563eb", width=3),
        hovertemplate="Year: %{x}<br>Index: %{y:.0f} (base=100)<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["LandIndex"],
        name="Land Value", mode="lines",
        line=dict(color="#f97316", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=yearly["Year"], y=yearly["BuildingIndex"],
        name="Building Value", mode="lines",
        line=dict(color="#22c55e", width=2),
    ))

    # Reference line at 100
    fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title="Appleton St — Cumulative Appreciation (1992 = 100)",
        xaxis_title="Fiscal Year",
    )
    fig.update_yaxes(title_text="Index (1992 = 100)")

    save_chart(fig, "31_appleton_cumulative")


# ── Chart 32: By Property Type ─────────────────────────────────────────────

def chart_by_type(assess):
    """Median value over time by land use type."""
    # Simplify type labels
    def simplify(code):
        if pd.isna(code):
            return None
        code = str(code).strip()
        if code.startswith("101"):
            return "Single Family"
        elif code.startswith("102"):
            return "Condo"
        elif code.startswith("104"):
            return "Two Family"
        return None

    assess = assess.copy()
    assess["PropType"] = assess["LandUseCode"].apply(simplify)
    assess = assess[assess["PropType"].notna()]

    yearly = assess.groupby(["Year", "PropType"])["TotalValue"].median().reset_index()

    fig = px.line(
        yearly, x="Year", y="TotalValue", color="PropType",
        markers=True,
        title="Appleton St — Assessment by Property Type",
        labels={"Year": "Fiscal Year", "TotalValue": "Median Total Value", "PropType": "Type"},
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "32_appleton_by_type")


# ── Chart 33: Sales History ────────────────────────────────────────────────

def chart_sales_history(sales):
    """All sales on Appleton St over time."""
    valid = sales[
        (sales["SalePrice"] > 100)
        & (sales["SaleDate"].notna())
    ].copy()

    if len(valid) == 0:
        print("  Skipped: no valid sales for chart 33")
        return

    fig = px.scatter(
        valid, x="SaleDate", y="SalePrice",
        hover_data=["FullAddress", "Grantor"],
        title="Appleton St — Property Sales History",
        labels={"SaleDate": "Sale Date", "SalePrice": "Sale Price"},
        color_discrete_sequence=["#2563eb"],
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "33_appleton_sales_scatter")


def main():
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    assess, sales = load_data()
    print(f"  {len(assess):,} assessment records, {len(sales):,} sales\n")

    print("Generating charts...\n")
    chart_median_trend(assess)
    chart_yoy_change(assess)
    chart_spaghetti(assess)
    chart_land_building_shift(assess)
    chart_cumulative_appreciation(assess)
    chart_by_type(assess)
    chart_sales_history(sales)

    print(f"\nDone!")


if __name__ == "__main__":
    main()
