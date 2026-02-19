# ArcGIS + arcpy — Domain Knowledge

Domain-specific knowledge for working with Esri's ArcGIS platform and the
arcpy Python library. Claude Code should reference this when helping with
geospatial analysis, mapping, geodatabase operations, or ArcGIS Pro automation.

## Overview

ArcGIS is Esri's geographic information system platform. `arcpy` is the Python
site package that ships with ArcGIS Pro, providing access to geoprocessing tools,
spatial analysis, map automation, and data management.

Key concepts: feature classes, rasters, geodatabases, spatial references,
map documents (`.aprx`), layouts, and geoprocessing tools.

## Key Libraries & APIs

- `arcpy` — core Python package for ArcGIS Pro geoprocessing
- `arcpy.mp` — map document and layout automation
- `arcpy.da` — data access cursors (SearchCursor, UpdateCursor, InsertCursor)
- `arcpy.sa` — Spatial Analyst (raster analysis, map algebra)
- `arcpy.na` — Network Analyst (routing, service areas)
- `arcpy.management` — data management tools
- `arcpy.analysis` — analysis tools (buffer, clip, intersect)
- `arcpy.conversion` — format conversion tools
- `arcpy.cartography` — cartographic tools
- `arcpy.geocoding` — address geocoding
- `arcpy.stats` — Spatial Statistics (hot spots, clustering)
- `arcgis` (ArcGIS API for Python) — web GIS, hosted feature layers, Portal/AGOL

## Common Patterns

### Setting up the workspace
```python
import arcpy
import os

arcpy.env.workspace = r"C:\Projects\MyProject\data.gdb"
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)  # WGS84

# Temporary environment override
with arcpy.EnvManager(workspace=r"C:\Temp\scratch.gdb"):
    # work in temporary workspace
    pass
```

### Data access cursors (fast read/write)
```python
# Read features
with arcpy.da.SearchCursor("parcels", ["SHAPE@", "PARCEL_ID", "AREA"]) as cursor:
    for shape, pid, area in cursor:
        print(f"{pid}: {area:.2f} sq m, centroid: {shape.centroid}")

# Read with SQL filter and spatial reference
sr = arcpy.SpatialReference(4326)
with arcpy.da.SearchCursor("parcels", ["SHAPE@", "AREA"],
                            where_clause="AREA > 1000",
                            spatial_reference=sr) as cursor:
    for shape, area in cursor:
        print(f"Large parcel: {area}")

# Update features
with arcpy.da.UpdateCursor("parcels", ["AREA", "STATUS"]) as cursor:
    for row in cursor:
        if row[0] < 100:
            row[1] = "SMALL"
            cursor.updateRow(row)
        elif row[0] > 10000:
            cursor.deleteRow()  # can also delete

# Insert features
with arcpy.da.InsertCursor("points", ["SHAPE@XY", "NAME"]) as cursor:
    cursor.insertRow([(lng, lat), "New Point"])

# Bulk insert from list
records = [((174.7, -36.8), "Auckland"), ((172.6, -43.5), "Christchurch")]
with arcpy.da.InsertCursor("cities", ["SHAPE@XY", "NAME"]) as cursor:
    for rec in records:
        cursor.insertRow(rec)
```

### Cursor field tokens
```
SHAPE@      — full geometry object (Polygon, Polyline, Point, etc.)
SHAPE@XY    — tuple of (x, y) coordinates (centroid for polygons)
SHAPE@X     — x coordinate
SHAPE@Y     — y coordinate
SHAPE@Z     — z coordinate
SHAPE@M     — m value
SHAPE@AREA  — area of feature (in units of spatial reference)
SHAPE@LENGTH — length of feature
SHAPE@JSON  — JSON representation
SHAPE@WKB   — well-known binary
SHAPE@WKT   — well-known text
OID@        — object ID field
```

### Geoprocessing tool patterns
```python
# Buffer with dissolve
arcpy.analysis.Buffer(
    in_features="roads",
    out_feature_class="roads_buffer_500m",
    buffer_distance_or_field="500 Meters",
    dissolve_option="ALL",
)

# Clip features to study area
arcpy.analysis.Clip(
    in_features="buildings",
    clip_features="study_area",
    out_feature_class="buildings_clipped",
)

# Spatial join
arcpy.analysis.SpatialJoin(
    target_features="parcels",
    join_features="zoning",
    out_feature_class="parcels_with_zoning",
    join_type="KEEP_ALL",
    match_option="WITHIN",
)

# Intersect multiple layers
arcpy.analysis.Intersect(
    in_features=["parcels", "flood_zones", "zoning"],
    out_feature_class="parcels_flood_zoning",
    join_attributes="ALL",
)

# Erase (cookie-cutter: remove overlapping areas)
arcpy.analysis.Erase(
    in_features="parcels",
    erase_features="protected_areas",
    out_feature_class="parcels_developable",
)

# Dissolve (merge features by attribute)
arcpy.management.Dissolve(
    in_features="parcels",
    out_feature_class="parcels_by_zone",
    dissolve_field="ZONE_CODE",
    statistics_fields=[["AREA", "SUM"], ["POP", "SUM"]],
)

# Select by attribute
arcpy.management.SelectLayerByAttribute(
    in_layer_or_view="parcels",
    selection_type="NEW_SELECTION",
    where_clause="ZONE_CODE = 'R1'",
)

# Select by location
arcpy.management.SelectLayerByLocation(
    in_layer="parcels",
    overlap_type="WITHIN_A_DISTANCE",
    select_features="schools",
    search_distance="1 Kilometers",
)

# Summary statistics
arcpy.analysis.Statistics(
    in_table="parcels",
    out_table="parcel_stats",
    statistics_fields=[["AREA", "SUM"], ["AREA", "MEAN"], ["OID@", "COUNT"]],
    case_field="ZONE_CODE",
)

# Add and calculate field
arcpy.management.AddField("parcels", "AREA_HA", "DOUBLE")
arcpy.management.CalculateField(
    in_table="parcels",
    field="AREA_HA",
    expression="!SHAPE.area! / 10000",
    expression_type="PYTHON3",
)

# Calculate geometry attributes
arcpy.management.CalculateGeometryAttributes(
    in_features="parcels",
    geometry_property=[
        ["AREA_SQM", "AREA"],
        ["PERIMETER_M", "PERIMETER_LENGTH"],
        ["CENTROID_X", "CENTROID_X"],
        ["CENTROID_Y", "CENTROID_Y"],
    ],
    area_unit="SQUARE_METERS",
    coordinate_system=arcpy.SpatialReference(2193),
)
```

### Raster analysis (Spatial Analyst)
```python
from arcpy.sa import (
    Raster, Slope, Aspect, Hillshade, Con, SetNull,
    EucDistance, Reclassify, RemapRange, RemapValue,
    ZonalStatisticsAsTable, ExtractByMask, FocalStatistics,
    NbrCircle, Int, Float
)

arcpy.CheckOutExtension("Spatial")

dem = Raster("elevation.tif")
slope = Slope(dem, "DEGREE")
aspect = Aspect(dem)
hillshade = Hillshade(dem, azimuth=315, altitude=45)

# Map algebra
suitable = Con((slope < 15) & (dem > 100) & (dem < 500), 1, 0)
suitable.save("suitable_areas.tif")

# Reclassify
slope_class = Reclassify(slope, "VALUE",
    RemapRange([[0, 5, 1], [5, 15, 2], [15, 30, 3], [30, 90, 4]]))

# Euclidean distance from features
dist_to_roads = EucDistance("roads", cell_size=10)

# Zonal statistics (summarize raster values within polygons)
ZonalStatisticsAsTable(
    in_zone_data="catchments",
    zone_field="CATCH_ID",
    in_value_raster=dem,
    out_table="catchment_elevation_stats",
    statistics_type="ALL",
)

# Extract raster by mask (clip raster to polygon)
clipped_dem = ExtractByMask(dem, "study_area")
clipped_dem.save("dem_clipped.tif")

# Focal statistics (neighborhood analysis)
smoothed = FocalStatistics(dem, NbrCircle(5, "CELL"), "MEAN")

# SetNull (make cells NoData based on condition)
no_flat = SetNull(slope == 0, dem)

arcpy.CheckInExtension("Spatial")
```

### Map automation (arcpy.mp)
```python
aprx = arcpy.mp.ArcGISProject(r"C:\Projects\MyProject.aprx")

# List maps and layers
for m in aprx.listMaps():
    print(f"Map: {m.name}")
    for lyr in m.listLayers():
        print(f"  Layer: {lyr.name} ({lyr.dataSource})")

map_obj = aprx.listMaps("Main Map")[0]
lyr = map_obj.listLayers("parcels")[0]

# Apply definition query
lyr.definitionQuery = "STATUS = 'ACTIVE'"

# Change symbology
sym = lyr.symbology
if hasattr(sym, "renderer"):
    sym.renderer.type = "GraduatedColorsRenderer"
    sym.renderer.classificationField = "POPULATION"
    sym.renderer.breakCount = 5
    lyr.symbology = sym

# Add data to map
map_obj.addDataFromPath(r"C:\Data\new_layer.shp")

# Export layout to PDF
layout = aprx.listLayouts("Report Layout")[0]
layout.exportToPDF(r"C:\output\report.pdf", resolution=300)

# Export map frame to image
mf = layout.listElements("MAPFRAME_ELEMENT", "Main Frame")[0]
mf.exportToPNG(r"C:\output\map.png", resolution=150)

# Update text elements in layout
for elm in layout.listElements("TEXT_ELEMENT"):
    if elm.name == "Title":
        elm.text = "Updated Title"
    if elm.name == "Date":
        import datetime
        elm.text = datetime.date.today().strftime("%d %B %Y")

# Batch export: one PDF per region
regions_cursor = arcpy.da.SearchCursor("regions", ["REGION_NAME", "SHAPE@"])
for region_name, shape in regions_cursor:
    mf.camera.setExtent(shape.extent)
    layout.listElements("TEXT_ELEMENT", "Title")[0].text = region_name
    safe_name = region_name.replace(" ", "_")
    layout.exportToPDF(rf"C:\output\{safe_name}.pdf", resolution=300)

aprx.save()
```

### Creating and managing data
```python
# Create a new geodatabase
arcpy.management.CreateFileGDB(r"C:\Projects", "analysis.gdb")

# Create feature class
arcpy.management.CreateFeatureclass(
    out_path=r"C:\Projects\analysis.gdb",
    out_name="sample_points",
    geometry_type="POINT",
    spatial_reference=arcpy.SpatialReference(4326),
)

# Add fields
arcpy.management.AddField("sample_points", "SITE_NAME", "TEXT", field_length=100)
arcpy.management.AddField("sample_points", "ELEVATION", "DOUBLE")
arcpy.management.AddField("sample_points", "SAMPLE_DATE", "DATE")

# List fields
for field in arcpy.ListFields("sample_points"):
    print(f"{field.name}: {field.type} ({field.length})")

# Describe dataset
desc = arcpy.Describe("sample_points")
print(f"Shape type: {desc.shapeType}")
print(f"Spatial ref: {desc.spatialReference.name}")
print(f"Feature count: {arcpy.management.GetCount('sample_points')}")

# Merge multiple datasets
arcpy.management.Merge(
    inputs=["points_2020", "points_2021", "points_2022"],
    output="points_all_years",
)

# Project (reproject data)
arcpy.management.Project(
    in_dataset="parcels_wgs84",
    out_dataset="parcels_nztm",
    out_coor_system=arcpy.SpatialReference(2193),  # NZGD2000 / NZTM
)
```

### Conversion tools
```python
# CSV to point feature class
arcpy.management.XYTableToPoint(
    in_table=r"C:\Data\locations.csv",
    out_feature_class="locations_points",
    x_field="LONGITUDE",
    y_field="LATITUDE",
    coordinate_system=arcpy.SpatialReference(4326),
)

# Feature class to GeoJSON
arcpy.conversion.FeaturesToJSON(
    in_features="parcels",
    out_json_file=r"C:\Output\parcels.geojson",
    geoJSON="GEOJSON",
)

# Raster to polygon
arcpy.conversion.RasterToPolygon(
    in_raster="classified.tif",
    out_polygon_features="classified_poly",
    simplify="SIMPLIFY",
)

# Excel to table
arcpy.conversion.ExcelToTable(
    Input_Excel_File=r"C:\Data\survey.xlsx",
    Output_Table="survey_table",
    Sheet="Sheet1",
)
```

### ArcGIS API for Python (web GIS)
```python
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis.geocoding import geocode, batch_geocode

gis = GIS("https://www.arcgis.com", "username", "password")

# Search for content
items = gis.content.search("owner:me AND type:Feature Layer")

# Access a hosted feature layer
fl = FeatureLayer("https://services.arcgis.com/.../FeatureServer/0")
sdf = fl.query(where="POP > 50000").sdf  # Spatially enabled DataFrame

# Publish a shapefile
item = gis.content.add({"type": "Shapefile"}, data="parcels.zip")
published = item.publish()

# Geocode
results = geocode("1600 Pennsylvania Ave, Washington DC")
```

## Field Types Reference

| arcpy type | Python type | Description |
|-----------|-------------|-------------|
| `TEXT` | str | Variable-length string (set field_length) |
| `FLOAT` | float | Single-precision floating point |
| `DOUBLE` | float | Double-precision floating point |
| `SHORT` | int | 16-bit integer (-32768 to 32767) |
| `LONG` | int | 32-bit integer |
| `DATE` | datetime | Date and time |
| `BLOB` | bytes | Binary large object |
| `GUID` | str | Globally unique identifier |

## Common Coordinate Systems

| EPSG | Name | Use |
|------|------|-----|
| 4326 | WGS 84 | GPS, global web maps |
| 3857 | Web Mercator | Web tiles (Google, ESRI, OSM) |
| 2193 | NZGD2000 / NZTM | New Zealand |
| 28355 | GDA94 / MGA55 | Australia (zone 55) |
| 27700 | OSGB 1936 | Great Britain |
| 32601-32660 | WGS 84 / UTM zones | UTM (pick zone for area) |
| 4269 | NAD83 | North America |

```python
sr = arcpy.SpatialReference(4326)
desc = arcpy.Describe("my_layer")
print(f"Name: {desc.spatialReference.name}, WKID: {desc.spatialReference.factoryCode}")
```

## Geometry Objects

```python
# Create point
pt = arcpy.Point(174.7633, -36.8485)
pt_geom = arcpy.PointGeometry(pt, arcpy.SpatialReference(4326))

# Create polygon
array = arcpy.Array([
    arcpy.Point(0, 0), arcpy.Point(0, 10),
    arcpy.Point(10, 10), arcpy.Point(10, 0),
    arcpy.Point(0, 0),
])
polygon = arcpy.Polygon(array, arcpy.SpatialReference(4326))

# Geometry operations
buffered = pt_geom.buffer(1000)
projected = polygon.projectAs(arcpy.SpatialReference(2193))
contains = polygon.contains(pt_geom)       # boolean
distance = pt_geom.distanceTo(polygon)
```

## Best Practices

- Always set `arcpy.env.overwriteOutput = True`
- Use `arcpy.da` cursors (not legacy `arcpy.SearchCursor`) — 10x faster
- Use `SHAPE@` token for full geometry, `SHAPE@XY` for point coordinates
- Set `arcpy.env.workspace` early; use raw strings for Windows paths
- Check extension: `arcpy.CheckOutExtension("Spatial")` before SA tools
- Use `arcpy.Describe()` to inspect data before processing
- Always specify spatial references explicitly
- Use `arcpy.management.GetCount()` to verify results
- Wrap geoprocessing in try/except for `arcpy.ExecuteError`
- Print `arcpy.GetMessages()` after tools for debugging
- Use `with arcpy.EnvManager(workspace=...) as env:` for temp settings

## Common Gotchas

- **Schema locks**: close ArcGIS Pro before running scripts that modify open data
- **Field name limits**: shapefiles truncate field names to 10 characters
- **Coordinate systems**: mixing projected/geographic CRS causes silent misalignment
- **File GDB vs Enterprise GDB**: different locking and concurrency behavior
- **Memory**: large rasters need `arcpy.env.cellSize` set to avoid OOM
- **ListFeatureClasses**: requires `arcpy.env.workspace` to be set first
- **in_memory workspace**: fast but limited; no rasters, no topology
- **Feature layers vs feature classes**: some tools need layers (use `MakeFeatureLayer`)
- **Expression types**: CalculateField needs `expression_type="PYTHON3"` not "PYTHON"
- **Date queries**: SQL date syntax differs by GDB type

## Script Template

```python
#!/usr/bin/env python3
"""[Project] — [Description]"""
import arcpy
import os, sys, traceback

WORKSPACE = r"C:\Projects\data.gdb"
OUTPUT_GDB = r"C:\Projects\output.gdb"
COORD_SYS = arcpy.SpatialReference(4326)

arcpy.env.workspace = WORKSPACE
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = COORD_SYS

def main():
    print("Starting analysis...")
    for ds in ["dataset_a", "dataset_b"]:
        if not arcpy.Exists(ds):
            raise FileNotFoundError(f"Missing: {ds}")
        print(f"  {ds}: {arcpy.management.GetCount(ds)} features")

    if not arcpy.Exists(OUTPUT_GDB):
        arcpy.management.CreateFileGDB(*os.path.split(OUTPUT_GDB))

    # ... analysis steps ...
    print("Done.")

if __name__ == "__main__":
    try:
        main()
    except arcpy.ExecuteError:
        print(f"Geoprocessing error:\n{arcpy.GetMessages(2)}")
        sys.exit(1)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
```

## Example Workflows

### 1. Site suitability analysis
1. Load DEM, land use, and roads layers
2. Generate slope from DEM with `arcpy.sa.Slope`
3. Buffer roads with `arcpy.analysis.Buffer`
4. Map algebra to combine criteria
5. Convert raster to polygons with `arcpy.conversion.RasterToPolygon`
6. Calculate area statistics

### 2. Batch geocoding and spatial analysis
1. Read addresses from CSV with `XYTableToPoint` or `batch_geocode`
2. `arcpy.analysis.Near` to find closest facility
3. `arcpy.analysis.SpatialJoin` to attach zone attributes
4. `arcpy.analysis.Statistics` for summary
5. Export to CSV or hosted feature layer

### 3. Automated map production
1. Open `.aprx` with `arcpy.mp.ArcGISProject`
2. Iterate regions with `SearchCursor`
3. Set extent, update text elements, export PDF per region

### 4. Change detection
1. Intersect Time 1 and Time 2 datasets
2. CalculateField to classify change type
3. Dissolve by change type, summarize area

### 5. Network analysis (service areas)
1. `arcpy.CheckOutExtension("Network")`
2. `arcpy.na.MakeServiceAreaAnalysisLayer`
3. Add facilities, solve, export drive-time polygons
4. SpatialJoin to count population within each zone

---

## Network Analyst Deep Dive (arcpy.na)

Network Analyst solves routing, service area, closest facility, and OD cost
matrix problems. Requires `arcpy.CheckOutExtension("Network")`.

### Building a network dataset
```python
# From a road feature class with travel time/distance attributes
arcpy.na.CreateNetworkDataset(
    feature_dataset=r"C:\Data\Transport.gdb\Roads",
    out_name="Roads_ND",
)
arcpy.na.BuildNetwork(r"C:\Data\Transport.gdb\Roads\Roads_ND")
```

### Route analysis (point-to-point shortest path)
```python
arcpy.CheckOutExtension("Network")

# Create route layer
route_lyr = arcpy.na.MakeRouteAnalysisLayer(
    network_data_source=r"C:\Data\Transport.gdb\Roads\Roads_ND",
    layer_name="Route",
    travel_mode="Driving Time",
).getOutput(0)

# Add stops
arcpy.na.AddLocations(route_lyr, "Stops", "my_stops_fc",
    field_mappings="Name Name #")

# Solve
arcpy.na.Solve(route_lyr)

# Export route lines
route_sublayer = route_lyr.listLayers("Routes")[0]
arcpy.management.CopyFeatures(route_sublayer, "solved_route")
arcpy.CheckInExtension("Network")
```

### Service area (drive-time / walk-time polygons)
```python
arcpy.CheckOutExtension("Network")

sa_lyr = arcpy.na.MakeServiceAreaAnalysisLayer(
    network_data_source=r"C:\Data\Transport.gdb\Roads\Roads_ND",
    layer_name="ServiceArea",
    travel_mode="Driving Time",
    travel_direction="FROM_FACILITIES",
    cutoffs=[5, 10, 15],          # 5, 10, 15 minute drive times
    output_type="POLYGONS",
    geometry_at_overlaps="DISSOLVE",
).getOutput(0)

arcpy.na.AddLocations(sa_lyr, "Facilities", "fire_stations")
arcpy.na.Solve(sa_lyr)

sa_polygons = sa_lyr.listLayers("Polygons")[0]
arcpy.management.CopyFeatures(sa_polygons, "fire_station_service_areas")
arcpy.CheckInExtension("Network")
```

### Closest facility
```python
arcpy.CheckOutExtension("Network")

cf_lyr = arcpy.na.MakeClosestFacilityAnalysisLayer(
    network_data_source=r"C:\Data\Transport.gdb\Roads\Roads_ND",
    layer_name="ClosestFacility",
    travel_mode="Driving Distance",
    travel_direction="TO_FACILITIES",
    number_of_facilities_to_find=3,
).getOutput(0)

arcpy.na.AddLocations(cf_lyr, "Facilities", "hospitals")
arcpy.na.AddLocations(cf_lyr, "Incidents", "accident_locations")
arcpy.na.Solve(cf_lyr)

routes = cf_lyr.listLayers("Routes")[0]
arcpy.management.CopyFeatures(routes, "closest_hospital_routes")
arcpy.CheckInExtension("Network")
```

### OD Cost Matrix (origin-destination distances)
```python
arcpy.CheckOutExtension("Network")

od_lyr = arcpy.na.MakeODCostMatrixAnalysisLayer(
    network_data_source=r"C:\Data\Transport.gdb\Roads\Roads_ND",
    layer_name="ODMatrix",
    travel_mode="Driving Time",
    number_of_destinations_to_find=5,
).getOutput(0)

arcpy.na.AddLocations(od_lyr, "Origins", "warehouses")
arcpy.na.AddLocations(od_lyr, "Destinations", "retail_stores")
arcpy.na.Solve(od_lyr)

od_lines = od_lyr.listLayers("Lines")[0]
arcpy.management.CopyFeatures(od_lines, "od_cost_matrix")
arcpy.CheckInExtension("Network")
```

---

## Spatial Statistics (arcpy.stats)

Hot spot analysis, clustering, spatial autocorrelation, and regression.

```python
# Hot Spot Analysis (Getis-Ord Gi*)
arcpy.stats.HotSpots(
    Input_Feature_Class="crime_incidents",
    Input_Field="INCIDENT_COUNT",
    Output_Feature_Class="crime_hotspots",
    Conceptualization_of_Spatial_Relationships="FIXED_DISTANCE_BAND",
    Distance_Band_or_Threshold_Distance=1000,
)

# Optimized Hot Spot Analysis (auto-aggregates point data)
arcpy.stats.OptimizedHotSpotAnalysis(
    Input_Features="crime_points",
    Output_Features="crime_hotspots_optimized",
    Analysis_Field=None,  # uses point density
)

# Cluster and Outlier Analysis (Anselin Local Moran's I)
arcpy.stats.ClustersOutliers(
    Input_Feature_Class="income_data",
    Input_Field="MEDIAN_INCOME",
    Output_Feature_Class="income_clusters",
    Conceptualization_of_Spatial_Relationships="K_NEAREST_NEIGHBORS",
    Number_of_Neighbors=8,
)

# Spatial Autocorrelation (Global Moran's I)
arcpy.stats.SpatialAutocorrelation(
    Input_Feature_Class="housing_prices",
    Input_Field="PRICE",
    Generate_Report="GENERATE_REPORT",
    Conceptualization_of_Spatial_Relationships="INVERSE_DISTANCE",
)

# Grouping Analysis (multivariate clustering)
arcpy.stats.GroupingAnalysis(
    Input_Features="census_tracts",
    Unique_ID_Field="TRACT_ID",
    Output_Feature_Class="census_grouped",
    Number_of_Groups=5,
    Analysis_Fields=["MEDIAN_INCOME", "POP_DENSITY", "PCT_COLLEGE"],
    Spatial_Constraints="CONTIGUITY_EDGES_ONLY",
)

# Ordinary Least Squares regression (OLS)
arcpy.stats.OrdinaryLeastSquares(
    Input_Feature_Class="housing",
    Unique_ID_Field="OID@",
    Output_Feature_Class="housing_ols",
    Dependent_Variable="PRICE",
    Explanatory_Variables=["SQFT", "BEDROOMS", "DIST_CBD"],
    Output_Report_File=r"C:\Output\ols_report.pdf",
)

# Geographically Weighted Regression (GWR)
arcpy.stats.GeographicallyWeightedRegression(
    in_features="housing",
    dependent_field="PRICE",
    explanatory_field=["SQFT", "BEDROOMS", "DIST_CBD"],
    out_featureclass="housing_gwr",
    kernel_type="ADAPTIVE",
    bandwidth_method="AICc",
)
```

---

## Cartography Tools (arcpy.cartography)

Simplification, smoothing, aggregation, and label placement.

```python
# Simplify polygons (reduce vertices while preserving shape)
arcpy.cartography.SimplifyPolygon(
    in_features="detailed_parcels",
    out_feature_class="parcels_simplified",
    algorithm="POINT_REMOVE",
    tolerance="10 Meters",
)

# Simplify lines
arcpy.cartography.SimplifyLine(
    in_features="contours",
    out_feature_class="contours_simplified",
    algorithm="BEND_SIMPLIFY",
    tolerance="50 Meters",
)

# Smooth lines (generalize curves)
arcpy.cartography.SmoothLine(
    in_features="rivers",
    out_feature_class="rivers_smoothed",
    algorithm="PAEK",
    tolerance="100 Meters",
)

# Aggregate polygons (merge nearby polygons)
arcpy.cartography.AggregatePolygons(
    in_features="buildings",
    out_feature_class="building_blocks",
    aggregation_distance="20 Meters",
    minimum_area="500 SquareMeters",
)

# Collapse dual-line roads to centerlines
arcpy.cartography.CollapseDualLinesToCenterline(
    in_features="road_casings",
    out_feature_class="road_centerlines",
    maximum_width="30 Meters",
)

# Create map grid / graticule
arcpy.cartography.GridIndexFeatures(
    out_feature_class="map_grid",
    in_features="study_area",
    number_rows=10,
    number_columns=10,
)
```

---

## Geocoding (arcpy.geocoding)

Address matching and reverse geocoding.

```python
# Geocode addresses using a locator
arcpy.geocoding.GeocodeAddresses(
    in_table=r"C:\Data\addresses.csv",
    address_locator=r"C:\Locators\NZ_Address_Locator",
    in_address_fields="Street Address; City City; Postcode ZIP",
    out_feature_class="geocoded_addresses",
    out_relationship_type="STATIC",
)

# Reverse geocode (points to addresses)
arcpy.geocoding.ReverseGeocode(
    in_features="sample_points",
    address_locator=r"C:\Locators\NZ_Address_Locator",
    out_feature_class="reverse_geocoded",
)

# Create a composite address locator
arcpy.geocoding.CreateCompositeAddressLocator(
    in_address_locators=[
        ["StreetLocator", "Street"],
        ["CityLocator", "City"],
    ],
    in_field_map="Street Street; City City",
    out_composite_address_locator=r"C:\Locators\Composite_Locator",
)

# Using ArcGIS API for Python geocoding (web)
from arcgis.geocoding import geocode, batch_geocode, reverse_geocode

result = geocode("380 New York Street, Redlands, CA")
location = result[0]["location"]  # {'x': -117.19, 'y': 34.05}

# Batch geocode a list
addresses = [
    {"Address": "380 New York St", "City": "Redlands", "Region": "CA"},
    {"Address": "1 Market St", "City": "San Francisco", "Region": "CA"},
]
results = batch_geocode(addresses)
```

---

## Editing and Topology

### Feature editing in scripts
```python
# Create topology
arcpy.management.CreateTopology(
    in_dataset=r"C:\Data\parcels.gdb\Land",
    out_name="Land_Topology",
    in_cluster_tolerance=0.001,
)
arcpy.management.AddFeatureClassToTopology(
    in_topology=r"C:\Data\parcels.gdb\Land\Land_Topology",
    in_featureclass="parcels",
    xy_rank=1,
)
arcpy.management.AddRuleToTopology(
    in_topology=r"C:\Data\parcels.gdb\Land\Land_Topology",
    rule_type="Must Not Overlap (Area)",
    in_featureclass="parcels",
)
arcpy.management.ValidateTopology(r"C:\Data\parcels.gdb\Land\Land_Topology")

# Export topology errors for review
arcpy.management.ExportTopologyErrors(
    in_topology=r"C:\Data\parcels.gdb\Land\Land_Topology",
    out_path=r"C:\Data\parcels.gdb",
    out_basename="topology_errors",
)
```

### Feature datasets
```python
# Create feature dataset (container for related feature classes + topology)
arcpy.management.CreateFeatureDataset(
    out_dataset_path=r"C:\Data\project.gdb",
    out_name="Transportation",
    spatial_reference=arcpy.SpatialReference(2193),
)
```

---

## Image / Raster Management

```python
# Mosaic rasters
arcpy.management.MosaicToNewRaster(
    input_rasters=["tile1.tif", "tile2.tif", "tile3.tif"],
    output_location=r"C:\Output",
    raster_dataset_name_with_extension="merged_dem.tif",
    number_of_bands=1,
    pixel_type="32_BIT_FLOAT",
)

# Clip raster to polygon
arcpy.management.Clip(
    in_raster="dem.tif",
    out_raster="dem_clipped.tif",
    in_template_dataset="study_area",
    clipping_geometry="ClippingGeometry",
)

# Resample raster
arcpy.management.Resample(
    in_raster="dem.tif",
    out_raster="dem_10m.tif",
    cell_size="10 10",
    resampling_type="BILINEAR",
)

# Create raster from points (IDW interpolation)
from arcpy.sa import Idw
arcpy.CheckOutExtension("Spatial")
idw_surface = Idw("sample_points", "ELEVATION", cell_size=10, power=2)
idw_surface.save("elevation_idw.tif")
arcpy.CheckInExtension("Spatial")

# Kriging
from arcpy.sa import Kriging, KrigingModelOrdinary
arcpy.CheckOutExtension("Spatial")
kriging_surface = Kriging(
    "sample_points", "ELEVATION",
    KrigingModelOrdinary("Spherical"),
    cell_size=10,
)
kriging_surface.save("elevation_kriging.tif")
arcpy.CheckInExtension("Spatial")

# Contour generation
arcpy.sa.Contour("dem.tif", "contours", contour_interval=10, base_contour=0)
arcpy.sa.ContourList("dem.tif", "contours_specific", [100, 200, 500, 1000])
```

---

## Multipart / Geometry Utilities

```python
# Multipart to singlepart
arcpy.management.MultipartToSinglepart("parcels_multi", "parcels_single")

# Feature vertices to points
arcpy.management.FeatureVerticesToPoints(
    in_features="roads",
    out_feature_class="road_vertices",
    point_location="ALL",
)

# Feature to polygon (lines to polygons)
arcpy.management.FeatureToPolygon(
    in_features="boundary_lines",
    out_feature_class="enclosed_polygons",
)

# Points along line (generate points at intervals)
arcpy.management.GeneratePointsAlongLines(
    Input_Features="transect_lines",
    Output_Feature_Class="sample_points",
    Point_Placement="DISTANCE",
    Distance="100 Meters",
)

# Bearing distance to line (create lines from point + angle + distance)
arcpy.management.BearingDistanceToLine(
    in_table="survey_shots",
    out_featureclass="survey_lines",
    x_field="X", y_field="Y",
    distance_field="DISTANCE",
    bearing_field="BEARING",
    spatial_reference=arcpy.SpatialReference(2193),
)

# Feature envelope to polygon (bounding boxes)
arcpy.management.FeatureEnvelopeToPolygon("parcels", "parcel_envelopes")

# Minimum bounding geometry
arcpy.management.MinimumBoundingGeometry(
    in_features="tree_points",
    out_feature_class="tree_clusters_convex",
    geometry_type="CONVEX_HULL",
    group_option="LIST",
    group_field="CLUSTER_ID",
)
```

---

## Joins and Relates

```python
# Add join (in-memory join for layer)
arcpy.management.MakeFeatureLayer("parcels", "parcels_lyr")
arcpy.management.AddJoin(
    in_layer_or_view="parcels_lyr",
    in_field="PARCEL_ID",
    join_table="ownership_table",
    join_field="PARCEL_ID",
    join_type="KEEP_ALL",
)
# Export joined result to permanent feature class
arcpy.management.CopyFeatures("parcels_lyr", "parcels_with_owners")
arcpy.management.RemoveJoin("parcels_lyr")

# Join field (permanently copy field values from one table to another)
arcpy.management.JoinField(
    in_data="parcels",
    in_field="PARCEL_ID",
    join_table="valuations",
    join_field="PARCEL_ID",
    fields=["LAND_VALUE", "CAPITAL_VALUE"],
)

# Table to table (convert CSV/Excel to GDB table)
arcpy.conversion.TableToTable(
    in_rows=r"C:\Data\records.csv",
    out_path=r"C:\Data\project.gdb",
    out_name="records_table",
)
```

---

## Batch Processing Patterns

```python
# Process all feature classes in a geodatabase
arcpy.env.workspace = r"C:\Data\input.gdb"
for fc in arcpy.ListFeatureClasses():
    desc = arcpy.Describe(fc)
    if desc.shapeType == "Polygon":
        out_name = f"{fc}_buffered"
        arcpy.analysis.Buffer(fc, out_name, "100 Meters")
        print(f"  Buffered {fc} -> {out_name}")

# Process all rasters in a folder
arcpy.env.workspace = r"C:\Data\rasters"
for raster in arcpy.ListRasters("*.tif"):
    slope = arcpy.sa.Slope(raster, "DEGREE")
    slope.save(os.path.join(r"C:\Output", f"slope_{raster}"))

# Walk through nested geodatabases
for dirpath, dirnames, filenames in arcpy.da.Walk(
    r"C:\Data", datatype="FeatureClass", type="Polygon"
):
    for filename in filenames:
        full_path = os.path.join(dirpath, filename)
        count = int(arcpy.management.GetCount(full_path)[0])
        print(f"{full_path}: {count} features")

# Parallel processing with multiprocessing (CPU-bound tasks)
import multiprocessing

def process_tile(tile_path):
    arcpy.sa.Slope(tile_path, "DEGREE").save(
        tile_path.replace("dem_", "slope_"))

tiles = [os.path.join(r"C:\Tiles", f) for f in os.listdir(r"C:\Tiles")]
with multiprocessing.Pool(4) as pool:
    pool.map(process_tile, tiles)
```

---

## Licensing and Extensions

```python
# Check product level
print(arcpy.ProductInfo())  # 'ArcGISPro', 'Advanced', etc.

# Available and in-use extensions
extensions = [
    "Spatial", "3D", "Network", "Schematics", "Tracking",
    "GeoStats", "DataReviewer", "Airports", "Maritime",
    "Production", "Defense", "Bathymetry", "LocationReferencing",
]
for ext in extensions:
    status = arcpy.CheckExtension(ext)
    print(f"  {ext}: {status}")  # Available, Unavailable, NotLicensed, etc.

# Check out / check in
arcpy.CheckOutExtension("Spatial")
# ... do spatial analyst work ...
arcpy.CheckInExtension("Spatial")

# Check out multiple
for ext in ["Spatial", "3D", "Network"]:
    if arcpy.CheckExtension(ext) == "Available":
        arcpy.CheckOutExtension(ext)
```

---

## Debugging and Error Handling

```python
# Full error handling pattern
import arcpy
import sys
import traceback

try:
    arcpy.analysis.Buffer("input", "output", "500 Meters")
except arcpy.ExecuteError:
    # Geoprocessing-specific errors
    severity = arcpy.GetMaxSeverity()
    print(f"GP Error (severity {severity}):")
    for i in range(arcpy.GetMessageCount()):
        print(f"  [{arcpy.GetSeverity(i)}] {arcpy.GetMessage(i)}")
except Exception:
    traceback.print_exc()

# Get tool messages after execution
result = arcpy.analysis.Buffer("input", "output", "500 Meters")
print(f"Messages: {result.getMessages()}")
print(f"Status: {result.status}")  # 4 = succeeded

# Validate dataset existence before processing
datasets = ["parcels", "roads", "zoning"]
missing = [ds for ds in datasets if not arcpy.Exists(ds)]
if missing:
    raise FileNotFoundError(f"Missing datasets: {', '.join(missing)}")

# List all geoprocessing tool names
for toolbox in arcpy.ListToolboxes():
    print(f"\n{toolbox}")
    for tool in arcpy.ListTools(f"*_{toolbox.split(';')[0]}"):
        print(f"  {tool}")
```

---

## Automation vs Manual — What Can Be Scripted

Understanding what CAN and CANNOT be automated with arcpy is critical.

### Fully scriptable (do this in Python)
| Task | Module |
|------|--------|
| All geoprocessing tools | `arcpy.analysis`, `arcpy.management`, etc. |
| Data access (read/write/insert/delete) | `arcpy.da` cursors |
| Creating geodatabases, feature classes, tables, fields | `arcpy.management` |
| Raster analysis and map algebra | `arcpy.sa` |
| Network analysis (route, service area, OD matrix) | `arcpy.na` |
| Spatial statistics (hot spots, clustering, regression) | `arcpy.stats` |
| Geocoding | `arcpy.geocoding` |
| Projecting / reprojecting data | `arcpy.management.Project` |
| Map automation (layers, symbology, definition queries) | `arcpy.mp` |
| Layout automation (text elements, export to PDF/PNG) | `arcpy.mp` |
| Publishing to ArcGIS Online / Portal | `arcgis` API |
| Batch processing (loop over datasets, tiles, regions) | Python + `arcpy.da.Walk` |
| Interpolation (IDW, Kriging, Spline) | `arcpy.sa` |
| Topology creation and validation | `arcpy.management` |

### Requires ArcGIS Pro UI (cannot script)
| Task | Why |
|------|-----|
| Interactive digitizing (drawing features by hand) | Needs map click events |
| Visual symbology design (color ramps, manual breaks) | Use `arcpy.mp` for basic symbology, but complex styling needs the UI |
| Map navigation and exploration | Interactive by nature |
| Labeling engine configuration (Maplex fine-tuning) | Some properties scriptable, but full config needs UI |
| 3D scene setup and navigation | `arcpy.mp` supports some, but interactive 3D needs Pro |
| Editing feature geometry by dragging vertices | Needs interactive edit session |
| Configuring pop-ups and HTML pop-up expressions | Portal/AGOL web map config |

### Partially scriptable (script what you can, finish in Pro)
| Task | Script part | Manual part |
|------|-------------|-------------|
| Symbology | Set renderer type, field, break count | Fine-tune colors, labels, legend appearance |
| Layouts | Create text, set extent, export | Precise element positioning, visual polish |
| Topology | Create rules, validate, export errors | Inspect and fix individual errors interactively |
| Feature editing | Bulk insert/update/delete via cursors | Manual vertex editing, snapping |
| Labels | Enable labels, set expression, font size | Maplex placement weights, conflict resolution |

### Practical implication for Claude Code
When a user asks for help:
1. **Script everything possible** — write complete arcpy scripts for all analysis
2. **Flag manual steps** — clearly note what must be done in ArcGIS Pro UI
3. **Provide instructions for manual steps** — describe exactly what to click/configure
4. **Suggest workarounds** — e.g., export to lyrx/stylx for symbology templates
