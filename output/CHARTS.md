# Arlington, MA GIS Analysis — Chart Guide

All charts are interactive Plotly HTML files. Open any in a browser to hover, zoom, pan, and filter.

---

## Assessor Analysis (`analyze_assessor.py`)

General property value trends across all Arlington parcels.

| # | File | Description |
|---|---|---|
| 01 | `01_price_trends.html` | Median and mean sale price by year (1980–2025) with transaction volume overlay |
| 02 | `02_price_by_type.html` | Median sale price over time broken out by property type (single family, condo, two-family, apartments) |
| 03 | `03_value_by_zoning.html` | Box plot of current assessed values by zoning district (top 8 zones) |
| 04 | `04_assessed_vs_sale.html` | Scatter of last sale price vs current assessed value, colored by sale year (2000+) with 1:1 reference line |
| 05 | `05_appreciation_by_sale_year.html` | Median property appreciation (current assessed value / sale price) by year of last sale |
| 06 | `06_year_built_distribution.html` | Housing stock age: property count by decade built with median assessed value overlay |
| 07 | `07_land_vs_building_ratio.html` | Land value as % of total assessed value by decade built and property type |
| 08 | `08_price_sqft_by_zip.html` | Median sale price per sq ft by zip code over time (2000–2025) |
| 09 | `09_zoning_landuse_heatmap.html` | Heatmap of median assessed value by zoning district x land use category |
| 10 | `10_recent_sales_scatter.html` | Individual property sales since 2015, sized by lot area, colored by land use |

## Buildings Analysis (`analyze_buildings.py`)

Analysis of the Arlington Structures GIS layer (18,500 building footprints) joined with assessor data.

| # | File | Description |
|---|---|---|
| 11 | `11_footprint_distribution.html` | Distribution of building footprint sizes |
| 12 | `12_height_distribution.html` | Distribution of building heights |
| 13 | `13_value_per_sqft_by_zone.html` | Value per sq ft by zoning district |
| 14 | `14_size_vs_value.html` | Building footprint size vs assessed value |
| 15 | `15_height_vs_value.html` | Building height vs assessed value |
| 16 | `16_footprint_by_decade.html` | Building footprint size by decade built |
| 17 | `17_value_density.html` | Value density ($/sq ft of footprint) |
| 18 | `18_structure_type_comparison.html` | Comparison across structure types |
| 19 | `19_top_50_buildings.html` | Top 50 buildings by footprint area |
| 20 | `20_appreciation_by_building_size.html` | Appreciation rates by building size |

## Trees Analysis (`analyze_trees.py`)

Public shade trees (10,900+) and their relationship with property values.

| # | File | Description |
|---|---|---|
| 21 | `21_top_species.html` | Most common tree species |
| 22 | `22_size_by_species.html` | Tree canopy size by species |
| 23 | `23_planting_history.html` | Tree planting trends over time |
| 24 | `24_environmental_value.html` | Estimated environmental value (stormwater, carbon) |
| 25 | `25_trees_vs_property_value.html` | Tree proximity vs property assessed value |
| 26 | `26_canopy_size_vs_value.html` | Canopy size vs nearby property values |

## Historical Analysis (`analyze_history.py`)

Year-over-year assessment history for Appleton St properties (scraped from Patriot Properties).

| # | File | Description |
|---|---|---|
| 27 | `27_appleton_median_trend.html` | Median assessment trend over time |
| 28 | `28_appleton_yoy_change.html` | Year-over-year % change in assessments |
| 29 | `29_appleton_spaghetti.html` | Individual property assessment trajectories |
| 30 | `30_appleton_land_building_pct.html` | Land vs building value split over time |
| 31 | `31_appleton_cumulative.html` | Cumulative assessment growth |
| 32 | `32_appleton_by_type.html` | Assessment trends by property type |
| 33 | `33_appleton_sales_scatter.html` | Actual sales vs assessed values |

---

## Dimensions Analysis (`analyze_dimensions.py`)

Which property dimensions give the most "bang for buck" in assessed value? Uses multivariate OLS regression to isolate the marginal value of each feature, controlling for all others.

### Correlation & Overview

| # | File | Description |
|---|---|---|
| dim_01 | `dim_01_correlation_heatmap.html` | Pearson correlation of 16 property dimensions against 4 value targets (ValuePerSqFt, SalePrice, BuildValue, CurrentTotal). Strongest driver of total value: Finished Area (r=0.846). |
| dim_02 | `dim_02_scatter_vs_value_sqft.html` | Scatter plots of top 6 dimensions vs assessed value per sq ft, colored by property type. Shows raw relationships before controlling for confounders. |
| dim_03 | `dim_03_value_by_beds_baths.html` | Box plots of total assessed value by bedroom count and full bath count. Illustrates the raw (unadjusted) value spread at each level. |

### Regression — Isolated Marginal Values

| # | File | Description |
|---|---|---|
| dim_04 | `dim_04_marginal_value_regression.html` | OLS regression coefficients for all 15 features across 4 value targets. Each bar shows the per-unit marginal value controlling for everything else. Blue = significant positive, red = significant negative, gray = not significant. |
| dim_05 | `dim_05_size_vs_value_trendline.html` | Finished area vs total assessed value with linear trendlines by property type. Slopes: Single Family $348/sqft, Condo $357/sqft, Two Family $229/sqft. |
| dim_06 | `dim_06_age_vs_value.html` | Median total value and median value/sqft by decade built, split by property type. Two panels showing how age affects value in absolute and per-sqft terms. |
| dim_07 | `dim_07_feature_premiums.html` | Side-by-side comparison of median assessed value for homes with vs without AC, fireplace, renovation, and 2+ stories. Caution: these are raw comparisons, not regression-controlled. |
| dim_08 | `dim_08_bubble_multi.html` | Multivariate bubble chart: finished area vs value/sqft, sized by lot, colored by year built. Single family homes only. Reveals clustering patterns. |

### Bang for Buck — Practical Impact

| # | File | Description |
|---|---|---|
| dim_09 | `dim_09_bang_for_buck.html` | **Flagship chart.** Translates regression coefficients into dollar impact of realistic improvements (e.g., +1 bath, +200 sqft, +1 story). Bars sorted by impact, color-coded by category (size/rooms/structure/features), with error bars. Top value-adds: +1 story (+$123K), +2,000 sqft lot (+$79K), +1 full bath (+$75K). |

### Non-Linear Marginal Value Curves

| # | File | Description |
|---|---|---|
| dim_10 | `dim_10_marginal_sqft_curve.html` | How the marginal value of +200 sq ft changes from 1,000 to 5,000 sq ft houses. Uses cubic polynomial regression. Finding: **increasing returns** — the value of +200 sqft grows from ~$13K at 1,000 sqft to ~$66K at 5,000 sqft. 90% bootstrap CI shown. |
| dim_11 | `dim_11_marginal_footprint_curve.html` | How the marginal value of +5% footprint/lot coverage changes across the distribution (-3sd to +3sd). Finding: **diminishing returns** — from ~$35K at low coverage down to ~$15K at high coverage. |
| dim_12 | `dim_12_marginal_bath.html` | Marginal value of each additional full bath (1->2, 2->3, etc.) using dummy-variable regression. Finding: **accelerating returns** — 1->2 adds $43K, 2->3 adds $75K, 3->4 adds $161K, 4->5 adds $264K. Both marginal bar chart and cumulative effect curve. |

### Distribution Curves

Histograms by property type (single family, condo, two-family) with fitted normal curves overlaid.

| # | File | Description |
|---|---|---|
| dim_13 | `dim_13_dist_finishedarea.html` | Finished living area. SFH median 1,926 sqft, condo 1,181, two-family 2,647. |
| dim_14 | `dim_14_dist_gissqft.html` | Lot size. SFH median 6,410 sqft. Condos have wide spread (shared lots). |
| dim_15 | `dim_15_dist_bldgfootprint.html` | Building footprint. Condos and two-family have larger footprints than SFH. |
| dim_16 | `dim_16_dist_footprintratio.html` | Footprint/lot coverage. SFH ~21%, condo ~31%, two-family ~35%. |
| dim_17 | `dim_17_dist_bldgmaxheight.html` | Max building height. SFH shorter (median 47 ft) than condos/two-family (~54-55 ft). |
| dim_18 | `dim_18_dist_currenttotal.html` | Total assessed value. SFH and two-family overlap (~$1M+), condos lower ($621K). |
| dim_19 | `dim_19_dist_valuepersqft.html` | Value per sq ft. Two-family highest ($219/sqft), SFH $163, condo $118. |
| dim_20 | `dim_20_dist_numbedroom.html` | Bedrooms. SFH peaks at 3, condo at 2, two-family at 4-5. |
| dim_21 | `dim_21_dist_fullbath.html` | Full baths. SFH peaks at 2, condo at 1. |
| dim_22 | `dim_22_dist_yearbuilt.html` | Year built. Two-family is oldest stock (median 1923), SFH 1940, condo 1946. |

---

## Maps (`map_properties.py`, `analyze_trees.py`)

Interactive Folium maps saved in `output/maps/`.

| File | Description |
|---|---|
| `map_property_values.html` | Choropleth of property assessed values across Arlington |
| `map_recent_sales.html` | Recent property sales plotted on map |
| `map_tree_canopy.html` | Public shade tree locations with canopy info |
| `map_tree_stormwater_heatmap.html` | Heatmap of tree stormwater value |
| `map_trees_and_values.html` | Trees overlaid with property values |
| `map_value_heatmap.html` | Heatmap of property values |
| `map_value_per_sqft.html` | Value per sq ft across Arlington |
| `map_year_built.html` | Building age map |

---

## Data Sources

- **Assessor data**: Arlington, MA GIS Open Data Hub — Parcels with Assessor Info (15,662 parcels)
- **Buildings data**: Arlington Structures (view) FeatureServer (18,500 building footprints)
- **Address points**: Current Arlington Address Points with coordinates
- **Trees data**: Public Shade Trees layer (10,900+ active trees)
- **ACS data**: American Community Survey 5-Year Estimates
- **Historical assessments**: Scraped from Patriot Properties for Appleton St properties

## Methodology Notes

- **Regression models** use OLS (ordinary least squares) on single-family homes, controlling for finished area, lot size, bedrooms, baths, rooms, stories, age, AC, building footprint, max height, height range, building count, and footprint/lot ratio simultaneously.
- **Non-linear curves** (charts 10-11) use cubic polynomial terms with bootstrap confidence intervals (500 iterations).
- **Bath analysis** (chart 12) uses dummy variables for each bath count rather than a linear term, allowing the regression to capture non-constant marginal effects.
- All significance tests use t-statistics with p < 0.05 threshold.
