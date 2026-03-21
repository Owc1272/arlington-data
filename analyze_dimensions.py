"""
Analyze which property dimensions correlate most with value in Arlington, MA.

Correlates physical dimensions (size, rooms, age, features) against four
value targets: ValuePerSqFt, SalePrice, BuildValue, CurrentTotal.

Generates interactive Plotly HTML charts saved to output/charts/.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

INPUT_DIR = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"
CHART_DIR = OUTPUT_DIR / "charts"

# Value targets to correlate against
TARGETS = {
    "ValuePerSqFt": "Assessed Value per Sq Ft",
    "SalePrice": "Last Sale Price",
    "BuildValue": "Building Value",
    "CurrentTotal": "Total Assessed Value",
}

# Property dimensions to test
NUMERIC_DIMS = {
    "GISSqFt": "Lot Size (sq ft)",
    "GrossArea": "Gross Building Area",
    "FinishedArea": "Finished Area",
    "CurrentAcres": "Lot Acres",
    "NumRoom": "Total Rooms",
    "NumBedroom": "Bedrooms",
    "FullBath": "Full Baths",
    "HalfBath": "Half Baths",
    "TotalBaths": "Total Baths",
    "Kitchens": "Kitchens",
    "FirePlaces": "Fireplaces",
    "NumUnits": "Units",
    "PctAC": "% Air Conditioned",
    "YearBuilt": "Year Built",
    "Age": "Building Age",
    "StoryHgt_num": "Stories",
    "BldgFootprint": "Building Footprint (sq ft)",
    "BldgMaxHeight": "Max Building Height (ft)",
    "BldgHeightRange": "Height Range (ft)",
    "BldgCount": "Building Count",
    "FootprintRatio": "Footprint/Lot Ratio",
}


def load_data():
    """Load assessor data, merge aggregated building dimensions, and clean."""
    df = pd.read_csv(INPUT_DIR / "assessor_data.csv", low_memory=False)

    # Parse/clean
    df["SalePrice"] = pd.to_numeric(df["SalePrice"], errors="coerce")
    df["SaleYear"] = pd.to_numeric(df["SaleYear"], errors="coerce")
    df["YearBuilt"] = pd.to_numeric(df["YearBuilt"], errors="coerce")
    df["StoryHgt_num"] = pd.to_numeric(df["StoryHgt"], errors="coerce")

    # Derived columns
    df["TotalBaths"] = df["FullBath"] + df["HalfBath"] * 0.5
    df["Age"] = 2026 - df["YearBuilt"]

    # ── Merge building dimensions (aggregated per parcel) ──
    bldg = pd.read_csv(INPUT_DIR / "buildings_data.csv", low_memory=False)
    bldg["Parcel_id_clean"] = bldg["Parcel_id"].astype(str).str.strip()

    bldg_agg = bldg.groupby("Parcel_id_clean").agg(
        BldgFootprint=("AreaSqFt", "sum"),
        BldgMaxHeight=("TopHeight", "max"),
        BldgMinLowHeight=("LowHeight", "min"),
        BldgMaxTopHeight=("TopHeight", "max"),
        BldgCount=("BldgID", "count"),
        BldgBaseElev=("BaseElev", "median"),
    ).reset_index()
    bldg_agg["BldgHeightRange"] = bldg_agg["BldgMaxTopHeight"] - bldg_agg["BldgMinLowHeight"]

    df["ParcelID_clean"] = df["ParcelID"].astype(str).str.strip()
    df = df.merge(bldg_agg, left_on="ParcelID_clean", right_on="Parcel_id_clean", how="left")
    df.drop(columns=["Parcel_id_clean"], inplace=True)

    # Footprint-to-lot ratio
    df["FootprintRatio"] = df["BldgFootprint"] / df["GISSqFt"]
    df.loc[df["FootprintRatio"] > 1, "FootprintRatio"] = np.nan  # bad data

    matched = df["BldgFootprint"].notna().sum()
    print(f"  Building data merged: {matched:,} / {len(df):,} parcels matched")

    # Filter to residential with positive values
    residential_codes = ["101  - One Family", "102  - Condo", "104  - Two Family",
                         "105  - Three Fam.", "111  - Apts. 4-8"]
    df = df[df["LUC_Desc"].isin(residential_codes)].copy()
    df = df[df["CurrentTotal"] > 0].copy()

    # For SalePrice, only keep valid market sales
    df["ValidSale"] = (df["SalePrice"] > 50000) & (df["SaleYear"] >= 2000)

    return df


def save_chart(fig, name, height=600):
    path = CHART_DIR / f"{name}.html"
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=40, t=80, b=60),
    )
    fig.write_html(str(path), include_plotlyjs="cdn")
    print(f"  Saved: {path}")


# ── Chart 1: Correlation Heatmap ─────────────────────────────────────────────

def chart_correlation_heatmap(df):
    """Heatmap showing Pearson correlation of each dimension with each value target."""
    # For SalePrice, use only valid sales
    targets = list(TARGETS.keys())
    dims = [d for d in NUMERIC_DIMS if d in df.columns]

    corr_rows = []
    for dim in dims:
        row = {}
        for target in targets:
            if target == "SalePrice":
                subset = df[df["ValidSale"]]
            else:
                subset = df
            valid = subset[[dim, target]].dropna()
            valid = valid[(valid[target] > 0) & (valid[dim].notna())]
            if len(valid) > 30:
                row[target] = valid[dim].corr(valid[target])
            else:
                row[target] = np.nan
        row["Dimension"] = NUMERIC_DIMS[dim]
        corr_rows.append(row)

    corr_df = pd.DataFrame(corr_rows).set_index("Dimension")
    corr_df.columns = [TARGETS[t] for t in targets]

    fig = px.imshow(
        corr_df,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-0.6, zmax=0.6,
        title="Arlington, MA — Correlation of Property Dimensions with Value",
        labels=dict(color="Pearson r"),
        aspect="auto",
    )
    fig.update_xaxes(side="bottom")

    save_chart(fig, "dim_01_correlation_heatmap", height=650)

    # Print rankings
    print("\n  Top correlations by target:")
    for col in corr_df.columns:
        ranked = corr_df[col].dropna().abs().sort_values(ascending=False)
        print(f"\n  {col}:")
        for dim, val in ranked.head(5).items():
            sign = "+" if corr_df.loc[dim, col] > 0 else "-"
            print(f"    {sign}{val:.3f}  {dim}")

    return corr_df


# ── Chart 2: Scatter Matrix — Top Dimensions vs Value/SqFt ──────────────────

def chart_scatter_top_dims(df):
    """Scatter plots of top dimension drivers vs ValuePerSqFt."""
    top_dims = ["FinishedArea", "TotalBaths", "BldgFootprint", "BldgMaxHeight", "GISSqFt", "FootprintRatio"]
    available = [d for d in top_dims if d in df.columns]

    subset = df[df["ValuePerSqFt"].between(10, 500)].copy()

    # Property type for color
    type_map = {
        "101  - One Family": "Single Family",
        "102  - Condo": "Condo",
        "104  - Two Family": "Two Family",
        "105  - Three Fam.": "Three Family",
    }
    subset["PropType"] = subset["LUC_Desc"].map(type_map).fillna("Other")

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[NUMERIC_DIMS.get(d, d) for d in available[:6]],
        vertical_spacing=0.12, horizontal_spacing=0.08,
    )

    colors = {"Single Family": "#2563eb", "Condo": "#16a34a",
              "Two Family": "#f97316", "Three Family": "#dc2626", "Other": "#6b7280"}

    for i, dim in enumerate(available[:6]):
        row, col = (i // 3) + 1, (i % 3) + 1
        for ptype, color in colors.items():
            mask = subset["PropType"] == ptype
            s = subset[mask].sample(n=min(500, mask.sum()), random_state=42)
            fig.add_trace(
                go.Scatter(
                    x=s[dim], y=s["ValuePerSqFt"],
                    mode="markers", marker=dict(size=4, color=color, opacity=0.4),
                    name=ptype, legendgroup=ptype,
                    showlegend=(i == 0),
                    hovertemplate=f"{NUMERIC_DIMS.get(dim, dim)}: %{{x}}<br>$/sqft: $%{{y:.0f}}<extra>{ptype}</extra>",
                ),
                row=row, col=col,
            )
        fig.update_xaxes(title_text=NUMERIC_DIMS.get(dim, dim), row=row, col=col)
        fig.update_yaxes(title_text="$/sq ft" if col == 1 else "", tickformat="$,.0f", row=row, col=col)

    fig.update_layout(title="Arlington, MA — Property Dimensions vs Assessed Value per Sq Ft")
    save_chart(fig, "dim_02_scatter_vs_value_sqft", height=700)


# ── Chart 3: Box Plots — Value by Bedroom/Bath Count ────────────────────────

def chart_box_by_rooms(df):
    """Box plots showing how value changes with bedroom and bath counts."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=["By Bedrooms", "By Full Baths"])

    subset = df[(df["CurrentTotal"] > 0) & (df["CurrentTotal"] < 3_000_000)].copy()

    # Bedrooms
    bed_sub = subset[subset["NumBedroom"].between(1, 7)].copy()
    bed_sub["NumBedroom"] = bed_sub["NumBedroom"].astype(int).astype(str)
    for bed in sorted(bed_sub["NumBedroom"].unique()):
        vals = bed_sub[bed_sub["NumBedroom"] == bed]["CurrentTotal"]
        fig.add_trace(
            go.Box(y=vals, name=f"{bed} BR", marker_color="#3b82f6", showlegend=False),
            row=1, col=1,
        )

    # Full Baths
    bath_sub = subset[subset["FullBath"].between(1, 5)].copy()
    bath_sub["FullBath_str"] = bath_sub["FullBath"].astype(int).astype(str)
    for bath in sorted(bath_sub["FullBath_str"].unique()):
        vals = bath_sub[bath_sub["FullBath_str"] == bath]["CurrentTotal"]
        fig.add_trace(
            go.Box(y=vals, name=f"{bath} BA", marker_color="#16a34a", showlegend=False),
            row=1, col=2,
        )

    fig.update_yaxes(tickformat="$,.0f", title_text="Total Assessed Value", row=1, col=1)
    fig.update_yaxes(tickformat="$,.0f", row=1, col=2)
    fig.update_layout(title="Arlington, MA — Assessed Value by Bedroom & Bath Count")

    save_chart(fig, "dim_03_value_by_beds_baths", height=550)


# ── Chart 4: Regression-Based Marginal Value of Each Feature ────────────────

def chart_marginal_value(df):
    """OLS regression isolating the marginal dollar value of each property feature,
    controlling for all other dimensions simultaneously."""
    sfh = df[df["LUC_Desc"] == "101  - One Family"].copy()

    # Features to include in the regression
    feature_cols = {
        "FinishedArea": "Finished Area (per sq ft)",
        "GISSqFt": "Lot Size (per sq ft)",
        "NumBedroom": "Bedroom",
        "FullBath": "Full Bath",
        "HalfBath": "Half Bath",
        "FirePlaces": "Fireplace",
        "NumRoom": "Total Room",
        "StoryHgt_num": "Story",
        "Age": "Year of Age",
        "PctAC": "% AC (per point)",
        "BldgFootprint": "Bldg Footprint (per sq ft)",
        "BldgMaxHeight": "Max Bldg Height (per ft)",
        "BldgHeightRange": "Bldg Height Range (per ft)",
        "BldgCount": "Additional Building",
        "FootprintRatio": "Footprint/Lot Ratio (per %)",
    }

    available = [c for c in feature_cols if c in sfh.columns]

    # Build regression matrix — drop rows with any NaN in features or target
    targets = {
        "CurrentTotal": "Total Assessed Value",
        "BuildValue": "Building Value",
        "ValuePerSqFt": "Value per Sq Ft",
        "SalePrice": "Sale Price",
    }

    all_results = {}

    for target_col, target_label in targets.items():
        if target_col == "SalePrice":
            subset = sfh[sfh["ValidSale"]].copy()
        else:
            subset = sfh.copy()

        cols_needed = available + [target_col]
        clean = subset[cols_needed].dropna()
        clean = clean[clean[target_col] > 0]

        if len(clean) < 100:
            continue

        X = clean[available].values.astype(float)
        y = clean[target_col].values.astype(float)

        # Add intercept column
        X_with_intercept = np.column_stack([np.ones(len(X)), X])

        # OLS via numpy least squares
        coeffs, residuals, rank, sv = np.linalg.lstsq(X_with_intercept, y, rcond=None)

        # R-squared
        y_pred = X_with_intercept @ coeffs
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot

        # Standard errors for significance
        n, p = X_with_intercept.shape
        mse = ss_res / (n - p)
        cov = mse * np.linalg.inv(X_with_intercept.T @ X_with_intercept)
        se = np.sqrt(np.diag(cov))
        t_stats = coeffs / se

        results = []
        for j, col in enumerate(available):
            results.append({
                "Feature": feature_cols[col],
                "Coefficient": coeffs[j + 1],  # +1 to skip intercept
                "StdError": se[j + 1],
                "t_stat": t_stats[j + 1],
                "Significant": abs(t_stats[j + 1]) > 1.96,
            })

        all_results[target_col] = {
            "label": target_label,
            "results": pd.DataFrame(results),
            "r2": r2,
            "n": n,
            "intercept": coeffs[0],
        }

    # ── Main chart: coefficient bar chart for all 4 targets ──
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[v["label"] + f" (R²={v['r2']:.3f}, n={v['n']:,})"
                        for v in all_results.values()],
        vertical_spacing=0.18, horizontal_spacing=0.15,
    )

    colors_pos = "#2563eb"
    colors_neg = "#dc2626"
    colors_insig = "#d1d5db"

    for idx, (target_col, info) in enumerate(all_results.items()):
        row, col = (idx // 2) + 1, (idx % 2) + 1
        res = info["results"].sort_values("Coefficient", ascending=True)

        bar_colors = [
            colors_insig if not r["Significant"]
            else (colors_pos if r["Coefficient"] > 0 else colors_neg)
            for _, r in res.iterrows()
        ]

        fig.add_trace(
            go.Bar(
                y=res["Feature"], x=res["Coefficient"],
                orientation="h",
                marker_color=bar_colors,
                showlegend=False,
                hovertemplate="%{y}<br>$%{x:,.0f}<br><extra></extra>",
                error_x=dict(type="data", array=res["StdError"].tolist() , visible=True,
                             thickness=1.5, width=3),
            ),
            row=row, col=col,
        )
        fig.update_xaxes(tickformat="$,.0f", title_text="Marginal $ Value", row=row, col=col)

    fig.update_layout(
        title="Arlington, MA — Isolated Marginal Value of Each Feature (OLS Regression, Single Family)",
        annotations=[dict(
            text="Blue = positive & significant | Red = negative & significant | Gray = not significant (p>0.05) | Error bars = 1 SE",
            xref="paper", yref="paper", x=0.5, y=-0.08,
            showarrow=False, font=dict(size=11, color="#6b7280"),
        )] + list(fig.layout.annotations),  # preserve subplot titles
    )

    save_chart(fig, "dim_04_marginal_value_regression", height=750)

    # Print summary
    print("\n  Regression coefficients (controlling for all other features):")
    for target_col, info in all_results.items():
        print(f"\n  {info['label']} (R²={info['r2']:.3f}, n={info['n']:,}):")
        res = info["results"].sort_values("Coefficient", key=abs, ascending=False)
        for _, r in res.iterrows():
            sig = "*" if r["Significant"] else " "
            print(f"   {sig} {r['Feature']:<25} ${r['Coefficient']:>+12,.0f}  (±${r['StdError']:,.0f})")
    print("\n  * = statistically significant (p < 0.05)")


# ── Chart 5: Size vs Value with Trendlines ──────────────────────────────────

def chart_size_vs_value(df):
    """FinishedArea vs CurrentTotal with OLS trendline, by property type."""
    subset = df[
        (df["FinishedArea"] > 200) & (df["FinishedArea"] < 6000)
        & (df["CurrentTotal"] > 50000) & (df["CurrentTotal"] < 3_000_000)
    ].copy()

    type_map = {
        "101  - One Family": "Single Family",
        "102  - Condo": "Condo",
        "104  - Two Family": "Two Family",
    }
    subset["PropType"] = subset["LUC_Desc"].map(type_map)
    subset = subset[subset["PropType"].notna()]

    fig = go.Figure()
    colors = {"Single Family": "#2563eb", "Condo": "#16a34a", "Two Family": "#f97316"}

    print("\n  Value per additional sq ft of finished area (linear fit):")
    for ptype, color in colors.items():
        s = subset[subset["PropType"] == ptype]
        fig.add_trace(go.Scatter(
            x=s["FinishedArea"], y=s["CurrentTotal"],
            mode="markers", marker=dict(size=4, color=color, opacity=0.3),
            name=ptype,
            hovertemplate=f"%{{customdata[0]}}<br>%{{x:,.0f}} sqft<br>${{y:,.0f}}<extra>{ptype}</extra>",
            customdata=s[["FullAddress"]].values,
        ))
        # Manual linear fit
        valid = s[["FinishedArea", "CurrentTotal"]].dropna()
        if len(valid) > 10:
            coeffs = np.polyfit(valid["FinishedArea"], valid["CurrentTotal"], 1)
            x_range = np.array([valid["FinishedArea"].min(), valid["FinishedArea"].max()])
            fig.add_trace(go.Scatter(
                x=x_range, y=np.polyval(coeffs, x_range),
                mode="lines", line=dict(color=color, width=2, dash="dash"),
                name=f"{ptype} trend", showlegend=False,
            ))
            print(f"    {ptype}: ${coeffs[0]:,.0f}/sqft  (intercept: ${coeffs[1]:,.0f})")

    fig.update_layout(
        title="Arlington, MA — Finished Area vs Total Assessed Value",
        xaxis_title="Finished Area (sq ft)",
        yaxis_title="Total Assessed Value",
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "dim_05_size_vs_value_trendline", height=650)


# ── Chart 6: Age vs Value ───────────────────────────────────────────────────

def chart_age_vs_value(df):
    """Building age (binned by decade) vs median value, split by property type."""
    subset = df[
        (df["YearBuilt"] > 1850) & (df["YearBuilt"] <= 2025)
        & (df["CurrentTotal"] > 0)
    ].copy()

    type_map = {
        "101  - One Family": "Single Family",
        "102  - Condo": "Condo",
        "104  - Two Family": "Two Family",
    }
    subset["PropType"] = subset["LUC_Desc"].map(type_map)
    subset = subset[subset["PropType"].notna()]
    subset["Decade"] = (subset["YearBuilt"] // 10) * 10

    agg = subset.groupby(["Decade", "PropType"]).agg(
        MedianValue=("CurrentTotal", "median"),
        MedianPerSqFt=("ValuePerSqFt", "median"),
        Count=("CurrentTotal", "count"),
    ).reset_index()
    agg = agg[agg["Count"] >= 5]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Median Total Value by Decade Built", "Median Value/SqFt by Decade Built"],
    )

    colors = {"Single Family": "#2563eb", "Condo": "#16a34a", "Two Family": "#f97316"}

    for ptype, color in colors.items():
        data = agg[agg["PropType"] == ptype]
        fig.add_trace(
            go.Scatter(
                x=data["Decade"], y=data["MedianValue"],
                name=ptype, mode="lines+markers",
                line=dict(color=color, width=2),
                legendgroup=ptype,
                hovertemplate="Decade: %{x}s<br>Median: $%{y:,.0f}<extra>" + ptype + "</extra>",
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=data["Decade"], y=data["MedianPerSqFt"],
                name=ptype, mode="lines+markers",
                line=dict(color=color, width=2),
                legendgroup=ptype, showlegend=False,
                hovertemplate="Decade: %{x}s<br>$/sqft: $%{y:,.0f}<extra>" + ptype + "</extra>",
            ),
            row=1, col=2,
        )

    fig.update_yaxes(tickformat="$,.0f", title_text="Median Value", row=1, col=1)
    fig.update_yaxes(tickformat="$,.0f", title_text="Median $/sq ft", row=1, col=2)
    fig.update_xaxes(title_text="Decade Built", row=1, col=1)
    fig.update_xaxes(title_text="Decade Built", row=1, col=2)
    fig.update_layout(title="Arlington, MA — Building Age vs Value by Property Type")

    save_chart(fig, "dim_06_age_vs_value", height=550)


# ── Chart 7: Feature Premiums — AC, Fireplace, Renovation ──────────────────

def chart_feature_premiums(df):
    """Compare median values for properties with vs without key features."""
    sfh = df[df["LUC_Desc"] == "101  - One Family"].copy()

    features = []

    # AC
    sfh["HasAC"] = sfh["PctAC"].fillna(0) > 0
    for has, label in [(True, "Has AC"), (False, "No AC")]:
        vals = sfh[sfh["HasAC"] == has]["CurrentTotal"]
        features.append({"Feature": "Air Conditioning", "Category": label,
                        "MedianValue": vals.median(), "Count": len(vals)})

    # Fireplace
    sfh["HasFP"] = sfh["FirePlaces"].fillna(0) > 0
    for has, label in [(True, "Has Fireplace"), (False, "No Fireplace")]:
        vals = sfh[sfh["HasFP"] == has]["CurrentTotal"]
        features.append({"Feature": "Fireplace", "Category": label,
                        "MedianValue": vals.median(), "Count": len(vals)})

    # Renovation
    sfh["Renovated"] = sfh["RenoYear"].notna()
    for has, label in [(True, "Renovated"), (False, "Not Renovated")]:
        vals = sfh[sfh["Renovated"] == has]["CurrentTotal"]
        features.append({"Feature": "Renovation", "Category": label,
                        "MedianValue": vals.median(), "Count": len(vals)})

    # 2+ stories vs 1
    sfh["MultiStory"] = pd.to_numeric(sfh["StoryHgt"], errors="coerce") >= 2
    for has, label in [(True, "2+ Stories"), (False, "1 Story")]:
        vals = sfh[sfh["MultiStory"] == has]["CurrentTotal"]
        if len(vals) > 0:
            features.append({"Feature": "Stories", "Category": label,
                            "MedianValue": vals.median(), "Count": len(vals)})

    feat_df = pd.DataFrame(features)

    fig = px.bar(
        feat_df, x="Feature", y="MedianValue", color="Category",
        barmode="group", text="Count",
        title="Arlington, MA — Feature Premiums: Median Assessed Value (Single Family)",
        labels={"MedianValue": "Median Assessed Value", "Feature": "", "Count": "Properties"},
    )
    fig.update_yaxes(tickformat="$,.0f")
    fig.update_traces(texttemplate="n=%{text:,}", textposition="outside", textfont_size=10)

    # Add premium annotations
    for feat in feat_df["Feature"].unique():
        vals = feat_df[feat_df["Feature"] == feat]["MedianValue"].tolist()
        if len(vals) == 2:
            premium = vals[0] - vals[1]
            pct = (premium / vals[1]) * 100
            print(f"    {feat}: ${premium:+,.0f} ({pct:+.1f}%)")

    save_chart(fig, "dim_07_feature_premiums", height=550)


# ── Chart 8: Multivariate — Bubble Chart ────────────────────────────────────

def chart_bubble_multi(df):
    """Bubble: FinishedArea vs ValuePerSqFt, sized by lot, colored by age."""
    subset = df[
        (df["FinishedArea"] > 200) & (df["FinishedArea"] < 5000)
        & (df["ValuePerSqFt"] > 10) & (df["ValuePerSqFt"] < 500)
        & (df["GISSqFt"] > 500)
        & (df["YearBuilt"] > 1850)
        & (df["LUC_Desc"] == "101  - One Family")
    ].copy()

    # Sample for performance
    if len(subset) > 2000:
        subset = subset.sample(2000, random_state=42)

    fig = px.scatter(
        subset, x="FinishedArea", y="ValuePerSqFt",
        size="GISSqFt", color="YearBuilt",
        color_continuous_scale="Viridis",
        size_max=20, opacity=0.6,
        title="Arlington, MA — Finished Area vs Value/SqFt (size=lot, color=year built)",
        labels={
            "FinishedArea": "Finished Area (sq ft)",
            "ValuePerSqFt": "Assessed Value per Sq Ft (lot)",
            "GISSqFt": "Lot Size (sq ft)",
            "YearBuilt": "Year Built",
        },
        hover_data=["FullAddress", "NumBedroom", "FullBath", "CurrentTotal"],
    )
    fig.update_yaxes(tickformat="$,.0f")

    save_chart(fig, "dim_08_bubble_multi", height=700)


# ── Chart 9: Bang for Buck — Practical Impact Visualization ─────────────────

def chart_bang_for_buck(df):
    """Single flagship chart: what does a realistic improvement of each
    dimension actually add to property value, controlling for everything else?

    Runs OLS on single-family homes, then multiplies each coefficient by a
    practical increment (e.g., +1 bath, +200 sqft finished area) to show
    the dollar impact in comparable, intuitive terms.
    """
    sfh = df[df["LUC_Desc"] == "101  - One Family"].copy()

    # Regression features (raw column → per-unit label)
    raw_features = [
        "FinishedArea", "GISSqFt", "NumBedroom", "FullBath", "HalfBath",
        "FirePlaces", "NumRoom", "StoryHgt_num", "Age", "PctAC",
        "BldgFootprint", "BldgMaxHeight", "BldgHeightRange", "BldgCount",
        "FootprintRatio",
    ]
    available = [c for c in raw_features if c in sfh.columns]

    # ── Fit OLS on CurrentTotal ──
    cols_needed = available + ["CurrentTotal"]
    clean = sfh[cols_needed].dropna()
    clean = clean[clean["CurrentTotal"] > 0]

    X = clean[available].values.astype(float)
    y = clean["CurrentTotal"].values.astype(float)
    X_int = np.column_stack([np.ones(len(X)), X])

    coeffs, _, _, _ = np.linalg.lstsq(X_int, y, rcond=None)
    y_pred = X_int @ coeffs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot
    n = len(clean)

    # Standard errors
    mse = ss_res / (n - X_int.shape[1])
    cov = mse * np.linalg.inv(X_int.T @ X_int)
    se = np.sqrt(np.diag(cov))
    t_stats = coeffs / se

    coeff_map = {feat: coeffs[i + 1] for i, feat in enumerate(available)}
    se_map = {feat: se[i + 1] for i, feat in enumerate(available)}
    sig_map = {feat: abs(t_stats[i + 1]) > 1.96 for i, feat in enumerate(available)}

    # ── Define practical increments ──
    # Each entry: (raw_col, increment, human label, category)
    increments = [
        ("FinishedArea",    200,  "+200 sq ft finished area",    "Size"),
        ("GISSqFt",         2000, "+2,000 sq ft lot",            "Size"),
        ("BldgFootprint",   200,  "+200 sq ft building footprint", "Size"),
        ("FootprintRatio",  0.05, "+5% footprint/lot coverage",  "Size"),
        ("FullBath",        1,    "+1 full bath",                "Rooms"),
        ("HalfBath",        1,    "+1 half bath",                "Rooms"),
        ("NumBedroom",      1,    "+1 bedroom",                  "Rooms"),
        ("NumRoom",         1,    "+1 room (any type)",          "Rooms"),
        ("StoryHgt_num",    1,    "+1 story",                    "Structure"),
        ("BldgMaxHeight",   5,    "+5 ft max building height",   "Structure"),
        ("BldgHeightRange", 5,    "+5 ft height range",          "Structure"),
        ("BldgCount",       1,    "+1 building on parcel",       "Structure"),
        ("FirePlaces",      1,    "+1 fireplace",                "Features"),
        ("PctAC",           100,  "Add central AC (0 to 100%)",  "Features"),
        ("Age",             -10,  "10 years newer",              "Features"),
    ]

    rows = []
    for raw_col, incr, label, cat in increments:
        if raw_col not in coeff_map:
            continue
        impact = coeff_map[raw_col] * incr
        impact_se = se_map[raw_col] * abs(incr)
        sig = sig_map[raw_col]
        rows.append({
            "Label": label,
            "Category": cat,
            "Impact": impact,
            "SE": impact_se,
            "Significant": sig,
            "AbsImpact": abs(impact),
        })

    impact_df = pd.DataFrame(rows).sort_values("Impact", ascending=True)

    # ── Build the chart ──
    cat_colors = {
        "Size": "#2563eb",
        "Rooms": "#16a34a",
        "Structure": "#f97316",
        "Features": "#8b5cf6",
    }

    fig = go.Figure()

    # Bars
    bar_colors = []
    for _, r in impact_df.iterrows():
        if not r["Significant"]:
            bar_colors.append("#d1d5db")
        else:
            bar_colors.append(cat_colors.get(r["Category"], "#6b7280"))

    fig.add_trace(go.Bar(
        y=impact_df["Label"],
        x=impact_df["Impact"],
        orientation="h",
        marker_color=bar_colors,
        error_x=dict(
            type="data",
            array=impact_df["SE"].tolist(),
            visible=True, thickness=1.5, width=4, color="#9ca3af",
        ),
        hovertemplate="%{y}<br>Impact: $%{x:,.0f}<extra></extra>",
    ))

    # Dollar annotations on each bar
    for _, r in impact_df.iterrows():
        sign = "+" if r["Impact"] >= 0 else ""
        sig_marker = "" if r["Significant"] else "  (n.s.)"
        fig.add_annotation(
            y=r["Label"],
            x=r["Impact"],
            text=f"  {sign}${r['Impact']:,.0f}{sig_marker}",
            showarrow=False,
            xanchor="left" if r["Impact"] >= 0 else "right",
            font=dict(size=11, color="#374151" if r["Significant"] else "#9ca3af"),
        )

    # Zero line
    fig.add_vline(x=0, line_width=1.5, line_color="#374151")

    # Category legend as colored squares in annotation
    legend_text = "  ".join(
        f'<span style="color:{c}">■</span> {cat}'
        for cat, c in cat_colors.items()
    ) + '  <span style="color:#d1d5db">■</span> Not significant'

    fig.update_layout(
        title=dict(
            text=(
                "Arlington, MA — Bang for Buck: Value Impact of Practical Improvements<br>"
                f"<sub>OLS regression on single-family homes (R²={r2:.3f}, n={n:,}) — "
                "each bar controls for all other features simultaneously</sub>"
            ),
        ),
        xaxis_title="Impact on Total Assessed Value ($)",
        xaxis=dict(tickformat="$,.0f", zeroline=True),
        yaxis_title="",
        template="plotly_white",
        height=700,
        margin=dict(l=250, r=120, t=100, b=80),
        annotations=list(fig.layout.annotations) + [
            dict(
                text=legend_text,
                xref="paper", yref="paper", x=0.5, y=-0.1,
                showarrow=False, font=dict(size=12),
            ),
            dict(
                text="Error bars = 1 standard error  |  n.s. = not statistically significant (p > 0.05)",
                xref="paper", yref="paper", x=0.5, y=-0.14,
                showarrow=False, font=dict(size=10, color="#9ca3af"),
            ),
        ],
    )

    save_chart(fig, "dim_09_bang_for_buck", height=700)

    # Print ranked summary
    print("\n  Practical impact on Total Assessed Value (ranked):")
    ranked = impact_df.sort_values("AbsImpact", ascending=False)
    for _, r in ranked.iterrows():
        sig = "*" if r["Significant"] else " "
        sign = "+" if r["Impact"] >= 0 else ""
        print(f"   {sig} {sign}${r['Impact']:>9,.0f}  {r['Label']}")

    return impact_df


# ── Chart 10: Marginal Value Curve — +200 sqft across house sizes ───────────

def chart_marginal_curve(df):
    """How does the value of +200 sq ft change as house size increases?

    Fits a polynomial (cubic) on FinishedArea while keeping all other controls
    linear.  The derivative of the cubic at each point × 200 gives the local
    marginal value of adding 200 sq ft at that house size.
    """
    sfh = df[df["LUC_Desc"] == "101  - One Family"].copy()

    # Control features (everything except FinishedArea — we handle that specially)
    controls = [
        "GISSqFt", "NumBedroom", "FullBath", "HalfBath", "FirePlaces",
        "NumRoom", "StoryHgt_num", "Age", "PctAC",
        "BldgFootprint", "BldgMaxHeight", "BldgHeightRange", "BldgCount",
        "FootprintRatio",
    ]
    controls = [c for c in controls if c in sfh.columns]

    # Need FinishedArea in a reasonable range
    cols_needed = ["FinishedArea", "CurrentTotal"] + controls
    clean = sfh[cols_needed].dropna()
    clean = clean[(clean["CurrentTotal"] > 0)
                  & (clean["FinishedArea"] >= 500)
                  & (clean["FinishedArea"] <= 6000)]

    fa = clean["FinishedArea"].values.astype(float)
    y = clean["CurrentTotal"].values.astype(float)

    # Build design matrix: intercept, FA, FA², FA³, then linear controls
    fa_centered = fa - fa.mean()  # center to reduce collinearity
    fa_mean = fa.mean()

    X = np.column_stack([
        np.ones(len(fa)),
        fa_centered,
        fa_centered ** 2,
        fa_centered ** 3,
        clean[controls].values.astype(float),
    ])

    coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    b1, b2, b3 = coeffs[1], coeffs[2], coeffs[3]

    # R² of the full model
    y_pred = X @ coeffs
    r2 = 1 - np.sum((y - y_pred) ** 2) / np.sum((y - y.mean()) ** 2)

    # Derivative of cubic w.r.t. FinishedArea at any point:
    #   dV/dFA = b1 + 2*b2*(FA - mean) + 3*b3*(FA - mean)²
    # Marginal value of +200 sqft ≈ derivative × 200
    fa_range = np.arange(1000, 5001, 50)
    fa_range_c = fa_range - fa_mean
    marginal_200 = (b1 + 2 * b2 * fa_range_c + 3 * b3 * fa_range_c ** 2) * 200

    # Bootstrap confidence interval
    rng = np.random.default_rng(42)
    n_boot = 500
    boot_curves = np.zeros((n_boot, len(fa_range)))

    for b in range(n_boot):
        idx = rng.choice(len(y), size=len(y), replace=True)
        X_b, y_b = X[idx], y[idx]
        try:
            c_b, _, _, _ = np.linalg.lstsq(X_b, y_b, rcond=None)
            boot_curves[b] = (c_b[1] + 2 * c_b[2] * fa_range_c + 3 * c_b[3] * fa_range_c ** 2) * 200
        except Exception:
            boot_curves[b] = np.nan

    ci_lo = np.nanpercentile(boot_curves, 5, axis=0)
    ci_hi = np.nanpercentile(boot_curves, 95, axis=0)

    # ── Distribution of actual homes by size (background histogram) ──
    hist_counts, hist_edges = np.histogram(fa, bins=np.arange(1000, 5200, 200))
    hist_centers = (hist_edges[:-1] + hist_edges[1:]) / 2

    # ── Build chart ──
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Confidence band
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([fa_range, fa_range[::-1]]),
            y=np.concatenate([ci_hi, ci_lo[::-1]]),
            fill="toself", fillcolor="rgba(37, 99, 235, 0.12)",
            line=dict(width=0), name="90% CI",
            hoverinfo="skip",
        ),
        secondary_y=False,
    )

    # Main curve
    fig.add_trace(
        go.Scatter(
            x=fa_range, y=marginal_200,
            mode="lines", name="Marginal value of +200 sq ft",
            line=dict(color="#2563eb", width=3),
            hovertemplate="At %{x:,.0f} sq ft: +200 sq ft adds $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Background histogram of home sizes
    fig.add_trace(
        go.Bar(
            x=hist_centers, y=hist_counts,
            name="Number of homes", opacity=0.15,
            marker_color="#94a3b8", width=180,
            hovertemplate="%{x:,.0f} sq ft: %{y} homes<extra></extra>",
        ),
        secondary_y=True,
    )

    # Reference line at the linear estimate ($37K from chart 9)
    linear_est = b1 * 200
    fig.add_hline(
        y=linear_est, line_dash="dash", line_color="#dc2626", line_width=1.5,
        annotation_text=f"Linear model: ${linear_est:,.0f}",
        annotation_position="top right",
        annotation_font_color="#dc2626",
        secondary_y=False,
    )

    # Annotations at key points
    for sqft in [1500, 2500, 3500, 4500]:
        idx = np.argmin(np.abs(fa_range - sqft))
        val = marginal_200[idx]
        fig.add_annotation(
            x=sqft, y=val,
            text=f"${val:,.0f}",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
            arrowcolor="#374151", ay=-35, font=dict(size=12, color="#374151"),
            secondary_y=False,
        )

    fig.update_layout(
        title=dict(text=(
            "Arlington, MA — Diminishing Returns: Marginal Value of +200 Sq Ft by House Size<br>"
            f"<sub>Cubic polynomial + linear controls on single-family homes "
            f"(R²={r2:.3f}, n={len(clean):,}) — shaded band = 90% bootstrap CI</sub>"
        )),
        xaxis_title="Current Finished Area (sq ft)",
        template="plotly_white",
        height=600,
        margin=dict(l=80, r=60, t=100, b=60),
        legend=dict(x=0.65, y=0.95),
    )
    fig.update_yaxes(
        title_text="Value Added by +200 Sq Ft ($)",
        tickformat="$,.0f", secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Number of Homes", secondary_y=True,
        showgrid=False,
    )

    save_chart(fig, "dim_10_marginal_sqft_curve", height=600)

    # Print key points
    print("\n  Marginal value of +200 sq ft at different house sizes:")
    for sqft in [1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]:
        idx = np.argmin(np.abs(fa_range - sqft))
        lo, hi = ci_lo[idx], ci_hi[idx]
        print(f"    At {sqft:,} sq ft:  ${marginal_200[idx]:>+9,.0f}   (90% CI: ${lo:,.0f} to ${hi:,.0f})")


# ── Chart 11: Marginal Value Curve — +5% Footprint/Lot Coverage ─────────────

def chart_marginal_footprint_curve(df):
    """How does the value of +5% footprint/lot coverage change across the
    distribution?  Same approach as chart 10: cubic polynomial on
    FootprintRatio with linear controls, derivative × 0.05.
    """
    sfh = df[df["LUC_Desc"] == "101  - One Family"].copy()

    controls = [
        "FinishedArea", "GISSqFt", "NumBedroom", "FullBath", "HalfBath",
        "FirePlaces", "NumRoom", "StoryHgt_num", "Age", "PctAC",
        "BldgFootprint", "BldgMaxHeight", "BldgHeightRange", "BldgCount",
    ]
    controls = [c for c in controls if c in sfh.columns]

    cols_needed = ["FootprintRatio", "CurrentTotal"] + controls
    clean = sfh[cols_needed].dropna()
    clean = clean[(clean["CurrentTotal"] > 0)
                  & (clean["FootprintRatio"] > 0)
                  & (clean["FootprintRatio"] < 1)]

    fr = clean["FootprintRatio"].values.astype(float)
    y = clean["CurrentTotal"].values.astype(float)

    fr_mean = fr.mean()
    fr_std = fr.std()
    fr_centered = fr - fr_mean

    # Design matrix: intercept, FR, FR², FR³, then linear controls
    X = np.column_stack([
        np.ones(len(fr)),
        fr_centered,
        fr_centered ** 2,
        fr_centered ** 3,
        clean[controls].values.astype(float),
    ])

    coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    b1, b2, b3 = coeffs[1], coeffs[2], coeffs[3]

    y_pred = X @ coeffs
    r2 = 1 - np.sum((y - y_pred) ** 2) / np.sum((y - y.mean()) ** 2)

    # Curve from -3sd to +3sd
    lo_bound = max(fr_mean - 3 * fr_std, 0.01)
    hi_bound = min(fr_mean + 3 * fr_std, 0.95)
    fr_range = np.linspace(lo_bound, hi_bound, 200)
    fr_range_c = fr_range - fr_mean

    # Marginal value of +5% (0.05) at each point
    increment = 0.05
    marginal = (b1 + 2 * b2 * fr_range_c + 3 * b3 * fr_range_c ** 2) * increment

    # Bootstrap CI
    rng = np.random.default_rng(42)
    n_boot = 500
    boot_curves = np.zeros((n_boot, len(fr_range)))

    for bx in range(n_boot):
        idx = rng.choice(len(y), size=len(y), replace=True)
        try:
            c_b, _, _, _ = np.linalg.lstsq(X[idx], y[idx], rcond=None)
            boot_curves[bx] = (c_b[1] + 2 * c_b[2] * fr_range_c + 3 * c_b[3] * fr_range_c ** 2) * increment
        except Exception:
            boot_curves[bx] = np.nan

    ci_lo = np.nanpercentile(boot_curves, 5, axis=0)
    ci_hi = np.nanpercentile(boot_curves, 95, axis=0)

    # Histogram of actual footprint ratios
    hist_counts, hist_edges = np.histogram(fr, bins=np.linspace(lo_bound, hi_bound, 40))
    hist_centers = (hist_edges[:-1] + hist_edges[1:]) / 2

    # Linear estimate for reference
    linear_est = b1 * increment

    # ── Build chart ──
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # CI band
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([fr_range, fr_range[::-1]]) * 100,
            y=np.concatenate([ci_hi, ci_lo[::-1]]),
            fill="toself", fillcolor="rgba(139, 92, 246, 0.12)",
            line=dict(width=0), name="90% CI",
            hoverinfo="skip",
        ),
        secondary_y=False,
    )

    # Main curve
    fig.add_trace(
        go.Scatter(
            x=fr_range * 100, y=marginal,
            mode="lines", name="Marginal value of +5% coverage",
            line=dict(color="#8b5cf6", width=3),
            hovertemplate="At %{x:.1f}% coverage: +5% adds $%{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Background histogram
    fig.add_trace(
        go.Bar(
            x=hist_centers * 100, y=hist_counts,
            name="Number of homes", opacity=0.15,
            marker_color="#94a3b8",
            width=(hist_edges[1] - hist_edges[0]) * 100 * 0.9,
            hovertemplate="%{x:.1f}% coverage: %{y} homes<extra></extra>",
        ),
        secondary_y=True,
    )

    # Linear reference
    fig.add_hline(
        y=linear_est, line_dash="dash", line_color="#dc2626", line_width=1.5,
        annotation_text=f"Linear model: ${linear_est:,.0f}",
        annotation_position="top right",
        annotation_font_color="#dc2626",
        secondary_y=False,
    )

    # Mean and +/-1sd markers
    for offset, label in [(0, "mean"), (-1, "-1 SD"), (1, "+1 SD"), (-2, "-2 SD"), (2, "+2 SD")]:
        val = (fr_mean + offset * fr_std) * 100
        if lo_bound * 100 <= val <= hi_bound * 100:
            fig.add_vline(
                x=val, line_dash="dot", line_color="#9ca3af", line_width=1,
                annotation_text=label, annotation_position="top",
                annotation_font_size=10, annotation_font_color="#9ca3af",
            )

    # Annotations at key points
    for pct in [0.10, 0.15, 0.22, 0.30, 0.40]:
        if lo_bound <= pct <= hi_bound:
            idx = np.argmin(np.abs(fr_range - pct))
            val = marginal[idx]
            fig.add_annotation(
                x=pct * 100, y=val,
                text=f"${val:,.0f}",
                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
                arrowcolor="#374151", ay=-35,
                font=dict(size=12, color="#374151"),
                secondary_y=False,
            )

    fig.update_layout(
        title=dict(text=(
            "Arlington, MA — Marginal Value of +5% Building Footprint/Lot Coverage<br>"
            f"<sub>Cubic polynomial + linear controls on single-family homes "
            f"(R\u00b2={r2:.3f}, n={len(clean):,}) | "
            f"mean={fr_mean*100:.1f}%, sd={fr_std*100:.1f}% | "
            f"range shown: {lo_bound*100:.1f}% to {hi_bound*100:.1f}% (-3sd to +3sd)</sub>"
        )),
        xaxis_title="Current Footprint/Lot Coverage (%)",
        template="plotly_white",
        height=600,
        margin=dict(l=80, r=60, t=100, b=60),
        legend=dict(x=0.65, y=0.95),
    )
    fig.update_yaxes(
        title_text="Value Added by +5% Coverage ($)",
        tickformat="$,.0f", secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Number of Homes", secondary_y=True,
        showgrid=False,
    )

    save_chart(fig, "dim_11_marginal_footprint_curve", height=600)

    # Print key points
    print(f"\n  FootprintRatio: mean={fr_mean*100:.1f}%, sd={fr_std*100:.1f}%")
    print("  Marginal value of +5% coverage at different levels:")
    for pct in np.arange(lo_bound, hi_bound + 0.01, 0.03):
        idx = np.argmin(np.abs(fr_range - pct))
        lo_ci, hi_ci = ci_lo[idx], ci_hi[idx]
        sds = (pct - fr_mean) / fr_std
        print(f"    At {pct*100:5.1f}% ({sds:+.1f} sd):  ${marginal[idx]:>+9,.0f}   "
              f"(90% CI: ${lo_ci:,.0f} to ${hi_ci:,.0f})")


# ── Chart 12: Marginal Value of +1 Full Bath by Current Bath Count ──────────

def chart_marginal_bath(df):
    """What is the marginal value of adding 1 full bath when you already
    have 1, 2, 3, ... baths?

    Uses dummy variables for each bath count (instead of a linear term)
    so the regression captures the actual value at each level.  The marginal
    value of going from N to N+1 baths is the difference in coefficients.
    """
    sfh = df[df["LUC_Desc"] == "101  - One Family"].copy()

    # Controls — everything except FullBath (we handle that as dummies)
    controls = [
        "FinishedArea", "GISSqFt", "NumBedroom", "HalfBath", "FirePlaces",
        "NumRoom", "StoryHgt_num", "Age", "PctAC",
        "BldgFootprint", "BldgMaxHeight", "BldgHeightRange", "BldgCount",
        "FootprintRatio",
    ]
    controls = [c for c in controls if c in sfh.columns]

    # Only keep bath counts with enough data
    bath_counts = sfh["FullBath"].value_counts()
    valid_baths = sorted(bath_counts[bath_counts >= 20].index.tolist())
    valid_baths = [b for b in valid_baths if b >= 1]

    cols_needed = ["FullBath", "CurrentTotal"] + controls
    clean = sfh[cols_needed].dropna()
    clean = clean[(clean["CurrentTotal"] > 0) & (clean["FullBath"].isin(valid_baths))]

    # Create dummy columns for each bath count (drop bath=1 as reference)
    for b in valid_baths:
        clean[f"Bath_{b}"] = (clean["FullBath"] == b).astype(float)
    dummy_cols = [f"Bath_{b}" for b in valid_baths if b != valid_baths[0]]
    ref_bath = valid_baths[0]

    # Design matrix: intercept + bath dummies + controls
    X = np.column_stack([
        np.ones(len(clean)),
        clean[dummy_cols].values.astype(float),
        clean[controls].values.astype(float),
    ])
    y_val = clean["CurrentTotal"].values.astype(float)

    coeffs, _, _, _ = np.linalg.lstsq(X, y_val, rcond=None)

    y_pred = X @ coeffs
    ss_res = np.sum((y_val - y_pred) ** 2)
    ss_tot = np.sum((y_val - y_val.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot
    n = len(clean)

    # Standard errors
    mse = ss_res / (n - X.shape[1])
    cov_mat = mse * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov_mat))

    # Extract bath coefficients (relative to reference bath count)
    # Index 0 = intercept, then dummy_cols, then controls
    bath_effect = {ref_bath: 0.0}
    bath_se = {ref_bath: 0.0}
    for i, b in enumerate(valid_baths):
        if b == ref_bath:
            continue
        coeff_idx = 1 + dummy_cols.index(f"Bath_{b}")
        bath_effect[b] = coeffs[coeff_idx]
        bath_se[b] = se[coeff_idx]

    # Marginal value: going from N to N+1
    marginal_rows = []
    for i in range(len(valid_baths) - 1):
        b_from = valid_baths[i]
        b_to = valid_baths[i + 1]
        if b_to - b_from != 1:
            continue
        marg = bath_effect[b_to] - bath_effect[b_from]

        # SE of the difference (for non-reference, use delta method)
        if b_from == ref_bath:
            marg_se = bath_se[b_to]
        elif b_to == ref_bath:
            marg_se = bath_se[b_from]
        else:
            # Covariance between two dummy coefficients
            idx_from = 1 + dummy_cols.index(f"Bath_{b_from}")
            idx_to = 1 + dummy_cols.index(f"Bath_{b_to}")
            var_diff = cov_mat[idx_from, idx_from] + cov_mat[idx_to, idx_to] - 2 * cov_mat[idx_from, idx_to]
            marg_se = np.sqrt(max(var_diff, 0))

        count_from = int(bath_counts.get(b_from, 0))
        count_to = int(bath_counts.get(b_to, 0))

        marginal_rows.append({
            "Transition": f"{b_from} -> {b_to}",
            "From": b_from,
            "To": b_to,
            "Marginal": marg,
            "SE": marg_se,
            "Significant": abs(marg / marg_se) > 1.96 if marg_se > 0 else False,
            "CountFrom": count_from,
            "CountTo": count_to,
        })

    marg_df = pd.DataFrame(marginal_rows)

    # ── Also compute cumulative level values for a secondary panel ──
    level_rows = []
    for b in valid_baths:
        count = int(bath_counts.get(b, 0))
        level_rows.append({
            "Baths": b,
            "Effect": bath_effect[b],
            "SE": bath_se[b],
            "Count": count,
        })
    level_df = pd.DataFrame(level_rows)

    # ── Build chart ──
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            "Marginal Value: Adding the Nth Bath",
            "Cumulative Effect vs 1 Bath (reference)",
        ],
        horizontal_spacing=0.12,
    )

    # Left panel: marginal value bars
    bar_colors = [
        "#2563eb" if r["Significant"] else "#d1d5db"
        for _, r in marg_df.iterrows()
    ]
    fig.add_trace(
        go.Bar(
            x=marg_df["Transition"],
            y=marg_df["Marginal"],
            marker_color=bar_colors,
            error_y=dict(type="data", array=marg_df["SE"].tolist(),
                         visible=True, thickness=1.5, width=4, color="#9ca3af"),
            hovertemplate="%{x}<br>Marginal value: $%{y:,.0f}<extra></extra>",
            showlegend=False,
        ),
        row=1, col=1,
    )

    # Annotations with dollar values and sample sizes
    for _, r in marg_df.iterrows():
        sig_mark = "" if r["Significant"] else " (n.s.)"
        fig.add_annotation(
            x=r["Transition"], y=r["Marginal"],
            text=f"${r['Marginal']:+,.0f}{sig_mark}<br><sub>n: {r['CountFrom']:,} -> {r['CountTo']:,}</sub>",
            showarrow=False, yshift=25 if r["Marginal"] >= 0 else -30,
            font=dict(size=11, color="#374151" if r["Significant"] else "#9ca3af"),
            row=1, col=1,
        )

    fig.update_yaxes(tickformat="$,.0f", title_text="Marginal Value ($)", row=1, col=1)
    fig.update_xaxes(title_text="Bath Transition", row=1, col=1)

    # Right panel: cumulative effect (step chart)
    fig.add_trace(
        go.Scatter(
            x=level_df["Baths"], y=level_df["Effect"],
            mode="lines+markers",
            line=dict(color="#8b5cf6", width=3),
            marker=dict(size=10, color="#8b5cf6"),
            error_y=dict(type="data", array=level_df["SE"].tolist(),
                         visible=True, thickness=1.5, width=4, color="#c4b5fd"),
            hovertemplate="%{x} baths<br>Effect vs 1-bath: $%{y:+,.0f}<extra></extra>",
            showlegend=False,
        ),
        row=1, col=2,
    )

    # Count annotations on right panel
    for _, r in level_df.iterrows():
        fig.add_annotation(
            x=r["Baths"], y=r["Effect"],
            text=f"n={r['Count']:,}",
            showarrow=False, yshift=-22,
            font=dict(size=10, color="#6b7280"),
            row=1, col=2,
        )

    fig.update_yaxes(tickformat="$,.0f", title_text="Value vs 1-Bath Reference ($)", row=1, col=2)
    fig.update_xaxes(title_text="Number of Full Baths", dtick=1, row=1, col=2)

    fig.update_layout(
        title=dict(text=(
            "Arlington, MA — Marginal Value of Each Additional Full Bath<br>"
            f"<sub>Dummy-variable regression on single-family homes "
            f"(R\u00b2={r2:.3f}, n={n:,}) — controls for size, lot, rooms, age, "
            f"building dims | Blue = significant, gray = not (p>0.05)</sub>"
        )),
        template="plotly_white",
        height=550,
        margin=dict(l=80, r=60, t=100, b=60),
    )

    save_chart(fig, "dim_12_marginal_bath", height=550)

    # Print summary
    print(f"\n  Marginal value of each additional full bath (R2={r2:.3f}, n={n:,}):")
    print(f"  Reference: {ref_bath} bath(s)")
    for _, r in marg_df.iterrows():
        sig = "*" if r["Significant"] else " "
        print(f"   {sig} {r['Transition']:>6}:  ${r['Marginal']:>+9,.0f}  "
              f"(+/-${r['SE']:,.0f})  "
              f"homes: {r['CountFrom']:,} -> {r['CountTo']:,}")


# ── Charts 13–22: Distribution Curves ───────────────────────────────────────

def _fit_normal_curve(data, bins):
    """Return x, y for a normal curve fitted to data, scaled to match histogram."""
    from scipy.stats import norm
    mu, sigma = data.mean(), data.std()
    bin_width = bins[1] - bins[0]
    x = np.linspace(bins[0], bins[-1], 300)
    y = norm.pdf(x, mu, sigma) * len(data) * bin_width
    return x, y, mu, sigma


def chart_distributions(df):
    """Generate 10 distribution charts with histograms by property type
    and fitted normal curves overlaid."""

    type_map = {
        "101  - One Family": "Single Family",
        "102  - Condo": "Condo",
        "104  - Two Family": "Two Family",
    }
    df = df[df["LUC_Desc"].isin(type_map)].copy()
    df["PropType"] = df["LUC_Desc"].map(type_map)

    colors = {
        "Single Family": ("#2563eb", "rgba(37, 99, 235, 0.25)"),
        "Condo":         ("#16a34a", "rgba(22, 163, 74, 0.25)"),
        "Two Family":    ("#f97316", "rgba(249, 115, 22, 0.25)"),
    }

    # ── Define each distribution chart ──
    dist_specs = [
        {
            "col": "FinishedArea", "label": "Finished Area (sq ft)",
            "filter": lambda s: s.between(200, 5000),
            "bins": np.arange(200, 5200, 200),
            "fmt": ",.0f", "prefix": "", "suffix": " sqft",
            "title": "Finished Living Area",
        },
        {
            "col": "GISSqFt", "label": "Lot Size (sq ft)",
            "filter": lambda s: s.between(500, 30000),
            "bins": np.arange(500, 30500, 1000),
            "fmt": ",.0f", "prefix": "", "suffix": " sqft",
            "title": "Lot Size",
        },
        {
            "col": "BldgFootprint", "label": "Building Footprint (sq ft)",
            "filter": lambda s: s.between(100, 5000),
            "bins": np.arange(100, 5200, 200),
            "fmt": ",.0f", "prefix": "", "suffix": " sqft",
            "title": "Building Footprint",
        },
        {
            "col": "FootprintRatio", "label": "Footprint / Lot Ratio",
            "filter": lambda s: s.between(0.01, 0.60),
            "bins": np.arange(0.01, 0.62, 0.02),
            "fmt": ".0%", "prefix": "", "suffix": "",
            "title": "Footprint / Lot Coverage",
            "pct": True,
        },
        {
            "col": "BldgMaxHeight", "label": "Max Building Height (ft)",
            "filter": lambda s: s.between(10, 80),
            "bins": np.arange(10, 82, 2),
            "fmt": ",.0f", "prefix": "", "suffix": " ft",
            "title": "Max Building Height",
        },
        {
            "col": "CurrentTotal", "label": "Total Assessed Value ($)",
            "filter": lambda s: s.between(50000, 3000000),
            "bins": np.arange(50000, 3050000, 100000),
            "fmt": "$,.0f", "prefix": "$", "suffix": "",
            "title": "Total Assessed Value",
        },
        {
            "col": "ValuePerSqFt", "label": "Value per Sq Ft ($/sqft)",
            "filter": lambda s: s.between(10, 400),
            "bins": np.arange(10, 410, 15),
            "fmt": "$,.0f", "prefix": "$", "suffix": "/sqft",
            "title": "Assessed Value per Sq Ft",
        },
        {
            "col": "NumBedroom", "label": "Bedrooms",
            "filter": lambda s: s.between(0, 8),
            "bins": np.arange(-0.5, 9.5, 1),
            "fmt": ".0f", "prefix": "", "suffix": " BR",
            "title": "Number of Bedrooms",
            "discrete": True,
        },
        {
            "col": "FullBath", "label": "Full Baths",
            "filter": lambda s: s.between(0, 6),
            "bins": np.arange(-0.5, 7.5, 1),
            "fmt": ".0f", "prefix": "", "suffix": " BA",
            "title": "Number of Full Baths",
            "discrete": True,
        },
        {
            "col": "YearBuilt", "label": "Year Built",
            "filter": lambda s: s.between(1800, 2025),
            "bins": np.arange(1800, 2030, 10),
            "fmt": ".0f", "prefix": "", "suffix": "",
            "title": "Year Built",
        },
    ]

    for i, spec in enumerate(dist_specs):
        chart_num = 13 + i
        col = spec["col"]
        is_pct = spec.get("pct", False)
        is_discrete = spec.get("discrete", False)

        fig = go.Figure()

        stats_text = []

        for ptype in ["Single Family", "Condo", "Two Family"]:
            sub = df[df["PropType"] == ptype].copy()
            data = sub[col].dropna()
            data = data[spec["filter"](data)]

            if len(data) < 20:
                continue

            line_color, fill_color = colors[ptype]
            bins = spec["bins"]

            if is_pct:
                hist_x = data * 100
                hist_bins = bins * 100
            else:
                hist_x = data
                hist_bins = bins

            # Histogram
            counts, edges = np.histogram(hist_x, bins=hist_bins)
            centers = (edges[:-1] + edges[1:]) / 2

            fig.add_trace(go.Bar(
                x=centers, y=counts,
                name=ptype,
                marker_color=fill_color,
                marker_line_color=line_color,
                marker_line_width=0.5,
                width=(edges[1] - edges[0]) * 0.9,
                hovertemplate=f"{ptype}<br>{spec['label']}: %{{x:{spec['fmt']}}}<br>Count: %{{y}}<extra></extra>",
            ))

            # Fitted normal curve (skip for discrete)
            if not is_discrete:
                mu, sigma = hist_x.mean(), hist_x.std()
                bin_width = hist_bins[1] - hist_bins[0]
                from scipy.stats import norm
                x_curve = np.linspace(hist_bins[0], hist_bins[-1], 300)
                y_curve = norm.pdf(x_curve, mu, sigma) * len(hist_x) * bin_width

                fig.add_trace(go.Scatter(
                    x=x_curve, y=y_curve,
                    mode="lines",
                    line=dict(color=line_color, width=2.5, dash="dash"),
                    name=f"{ptype} normal fit",
                    showlegend=False,
                    hoverinfo="skip",
                ))

            # Stats summary
            med = hist_x.median()
            mu_val = hist_x.mean()
            sd_val = hist_x.std()
            if is_pct:
                stats_text.append(
                    f"{ptype} (n={len(data):,}): "
                    f"mean={mu_val:.1f}%, median={med:.1f}%, sd={sd_val:.1f}%"
                )
            elif spec["fmt"].startswith("$"):
                stats_text.append(
                    f"{ptype} (n={len(data):,}): "
                    f"mean=${mu_val:,.0f}, median=${med:,.0f}, sd=${sd_val:,.0f}"
                )
            else:
                stats_text.append(
                    f"{ptype} (n={len(data):,}): "
                    f"mean={mu_val:{spec['fmt']}}, median={med:{spec['fmt']}}, sd={sd_val:{spec['fmt']}}"
                )

        x_title = spec["label"]
        if is_pct:
            x_title += " (%)"

        fig.update_layout(
            title=dict(text=(
                f"Arlington, MA — Distribution of {spec['title']} by Property Type<br>"
                f"<sub>{'  |  '.join(stats_text)}</sub>"
            )),
            xaxis_title=x_title,
            yaxis_title="Number of Properties",
            barmode="overlay",
            template="plotly_white",
            height=500,
            margin=dict(l=60, r=40, t=100, b=60),
            legend=dict(x=0.75, y=0.95),
        )

        save_chart(fig, f"dim_{chart_num:02d}_dist_{col.lower()}", height=500)
        print(f"  {chart_num}. {spec['title']}")
        for s in stats_text:
            print(f"     {s}")


def main():
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    df = load_data()
    print(f"  {len(df):,} residential parcels loaded\n")

    print("1. Correlation heatmap...")
    chart_correlation_heatmap(df)

    print("\n2. Scatter plots — top dimensions vs value/sqft...")
    chart_scatter_top_dims(df)

    print("\n3. Value by bedroom & bath count...")
    chart_box_by_rooms(df)

    print("\n4. Marginal value per additional feature...")
    chart_marginal_value(df)

    print("\n5. Finished area vs value with trendlines...")
    chart_size_vs_value(df)

    print("\n6. Building age vs value...")
    chart_age_vs_value(df)

    print("\n7. Feature premiums (AC, fireplace, renovation, stories)...")
    chart_feature_premiums(df)

    print("\n8. Multivariate bubble chart...")
    chart_bubble_multi(df)

    print("\n9. Bang for Buck — practical impact summary...")
    chart_bang_for_buck(df)

    print("\n10. Marginal value curve — +200 sqft across house sizes...")
    chart_marginal_curve(df)

    print("\n11. Marginal value curve — +5% footprint/lot coverage...")
    chart_marginal_footprint_curve(df)

    print("\n12. Marginal value of +1 full bath by current count...")
    chart_marginal_bath(df)

    print("\n13-22. Distribution curves...")
    chart_distributions(df)

    print(f"\nDone! 22 charts saved to output/charts/.")
    print("All filenames start with 'dim_' — open any in a browser.")


if __name__ == "__main__":
    main()
