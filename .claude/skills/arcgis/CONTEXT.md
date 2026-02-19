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
- `arcgis` (ArcGIS API for Python) — web GIS, hosted feature layers, Portal/AGOL

## Common Patterns

### Setting up the workspace
```python
import arcpy

arcpy.env.workspace = r"C:\Projects\MyProject\data.gdb"
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)  # WGS84
```

### Data access cursors (fast read/write)
```python
# Read features
with arcpy.da.SearchCursor("parcels", ["SHAPE@", "PARCEL_ID", "AREA"]) as cursor:
    for shape, pid, area in cursor:
        print(f"{pid}: {area:.2f} sq m, centroid: {shape.centroid}")

# Update features
with arcpy.da.UpdateCursor("parcels", ["AREA", "STATUS"]) as cursor:
    for row in cursor:
        if row[0] < 100:
            row[1] = "SMALL"
            cursor.updateRow(row)

# Insert features
with arcpy.da.InsertCursor("points", ["SHAPE@XY", "NAME"]) as cursor:
    cursor.insertRow([(lng, lat), "New Point"])
```

### Geoprocessing tool pattern
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
```

### Raster analysis (Spatial Analyst)
```python
from arcpy.sa import Raster, Slope, Aspect, Con

dem = Raster("elevation.tif")
slope = Slope(dem, "DEGREE")
aspect = Aspect(dem)

# Map algebra
suitable = Con((slope < 15) & (dem > 100) & (dem < 500), 1, 0)
suitable.save("suitable_areas.tif")
```

### Map automation
```python
aprx = arcpy.mp.ArcGISProject(r"C:\Projects\MyProject.aprx")
map_obj = aprx.listMaps("Main Map")[0]
lyr = map_obj.listLayers("parcels")[0]

# Apply definition query
lyr.definitionQuery = "STATUS = 'ACTIVE'"

# Export layout to PDF
layout = aprx.listLayouts("Report Layout")[0]
layout.exportToPDF(r"C:\output\report.pdf", resolution=300)

aprx.save()
```

### Creating feature classes
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
```

### ArcGIS API for Python (web GIS)
```python
from arcgis.gis import GIS
from arcgis.features import FeatureLayer

gis = GIS("https://www.arcgis.com", "username", "password")

# Search for content
items = gis.content.search("owner:me AND type:Feature Layer")

# Access a hosted feature layer
fl = FeatureLayer("https://services.arcgis.com/.../FeatureServer/0")
sdf = fl.query(where="POP > 50000").sdf  # Spatially enabled DataFrame

# Publish a shapefile
item = gis.content.add({"type": "Shapefile"}, data="parcels.zip")
published = item.publish()
```

## Best Practices

- Always set `arcpy.env.overwriteOutput = True` to avoid "output exists" errors
- Use `arcpy.da` cursors (not legacy `arcpy.SearchCursor`) — 10x faster
- Use `SHAPE@` token for full geometry, `SHAPE@XY` for point coordinates
- Set `arcpy.env.workspace` early; use raw strings for Windows paths
- Check tool availability with `arcpy.CheckExtension("Spatial")` before SA tools
- Use `arcpy.Describe()` to inspect data properties before processing
- For large datasets, process in chunks or use `arcpy.da.Walk()` for iteration
- Always specify spatial references explicitly — don't rely on defaults
- Use `arcpy.management.GetCount()` to verify results after geoprocessing
- Wrap geoprocessing in try/except to catch `arcpy.ExecuteError`
- Use `with arcpy.EnvManager(workspace=...) as env:` for temporary settings

## Common Gotchas

- Schema locks: close ArcGIS Pro before running scripts that modify open data
- Field name limits: shapefiles truncate field names to 10 characters
- Coordinate systems: mixing projected/geographic CRS causes silent misalignment
- File GDB vs Enterprise GDB: different locking and concurrency behavior
- Memory: large rasters need `arcpy.env.cellSize` set to avoid OOM
- `arcpy.ListFeatureClasses()` requires workspace to be set first
- The `in_memory` workspace is fast but limited in size and feature types

## Example Workflows

### 1. Site suitability analysis
1. Load DEM, land use, and roads layers
2. Generate slope from DEM with `arcpy.sa.Slope`
3. Buffer roads with `arcpy.analysis.Buffer`
4. Use map algebra to combine criteria: flat land + near roads + correct land use
5. Convert raster result to polygons with `arcpy.conversion.RasterToPolygon`
6. Calculate area statistics

### 2. Batch geocoding and analysis
1. Read addresses from CSV
2. Geocode with `arcpy.geocoding.GeocodeAddresses`
3. Create point feature class from results
4. Run `arcpy.analysis.Near` to find closest facility
5. Generate summary statistics with `arcpy.analysis.Statistics`
6. Export to feature layer or report

### 3. Automated map production
1. Open `.aprx` project with `arcpy.mp.ArcGISProject`
2. Iterate over regions using a polygon feature class
3. For each region: set extent, update title text, export PDF
4. Merge PDFs into atlas
