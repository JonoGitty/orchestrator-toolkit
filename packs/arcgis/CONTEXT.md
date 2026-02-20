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

## Environment Detection & Setup

How to find ArcGIS Pro on the user's machine, locate their data, and set up
a project from scratch. Run this FIRST when a user says "set up my project"
or "where's my data?"

### Detect ArcGIS Pro installation
```python
import os
import sys

def find_arcgis_pro():
    """Detect ArcGIS Pro installation on Windows."""
    info = {"installed": False, "path": None, "python": None, "version": None}

    # Method 1: Windows Registry (most reliable)
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\ESRI\ArcGISPro",
        )
        info["path"] = winreg.QueryValueEx(key, "InstallDir")[0]
        info["version"] = winreg.QueryValueEx(key, "Version")[0]
        info["installed"] = True
        winreg.CloseKey(key)
    except (ImportError, OSError):
        pass

    # Method 2: Check default install locations
    if not info["installed"]:
        default_paths = [
            r"C:\Program Files\ArcGIS\Pro",
            r"C:\ArcGIS\Pro",
            r"D:\ArcGIS\Pro",
            r"D:\Program Files\ArcGIS\Pro",
        ]
        for p in default_paths:
            if os.path.isdir(p):
                info["path"] = p
                info["installed"] = True
                break

    # Find the Python environment with arcpy
    if info["path"]:
        conda_env = os.path.join(
            info["path"], "bin", "Python", "envs", "arcgispro-py3"
        )
        if os.path.isdir(conda_env):
            info["python"] = os.path.join(conda_env, "python.exe")

    # Try importing arcpy to confirm
    try:
        import arcpy
        info["installed"] = True
        info["version"] = arcpy.GetInstallInfo()["Version"]
        print(f"ArcGIS Pro {info['version']} found")
        print(f"Install: {info['path']}")
        print(f"Product: {arcpy.ProductInfo()}")

        # Check licensed extensions
        extensions = ["Spatial", "3D", "Network", "GeoStats", "DataReviewer"]
        for ext in extensions:
            status = arcpy.CheckExtension(ext)
            marker = "+" if status == "Available" else "-"
            print(f"  [{marker}] {ext}: {status}")
    except ImportError:
        if info["installed"]:
            print(f"ArcGIS Pro found at {info['path']} but arcpy not in current Python path")
            print(f"Run scripts using: {info.get('python', 'ArcGIS Pro Python')}")
        else:
            print("ArcGIS Pro NOT found on this machine")

    return info

find_arcgis_pro()
```

### Scan a directory for GIS data
```python
import os

def scan_for_gis_data(root_path):
    """Walk a directory and catalogue every GIS-relevant file.

    Use this when the user says 'my data is on E:\\' or 'look in Downloads'.
    """
    GIS_EXTENSIONS = {
        # Vectors
        ".shp": ("vector", "Shapefile"),
        ".gpkg": ("vector", "GeoPackage"),
        ".geojson": ("vector", "GeoJSON"),
        ".json": ("vector", "GeoJSON"),
        ".kml": ("vector", "KML"),
        ".kmz": ("vector", "KMZ"),
        ".gml": ("vector", "GML"),
        ".tab": ("vector", "MapInfo TAB"),
        ".mif": ("vector", "MapInfo MIF"),
        # Rasters
        ".tif": ("raster", "GeoTIFF"),
        ".tiff": ("raster", "GeoTIFF"),
        ".img": ("raster", "ERDAS Imagine"),
        ".asc": ("raster", "ASCII Grid"),
        ".ecw": ("raster", "ECW"),
        ".jp2": ("raster", "JPEG2000"),
        ".sid": ("raster", "MrSID"),
        # Point clouds
        ".las": ("pointcloud", "LiDAR LAS"),
        ".laz": ("pointcloud", "LiDAR LAZ"),
        # Tabular
        ".csv": ("tabular", "CSV"),
        ".xlsx": ("tabular", "Excel"),
        ".xls": ("tabular", "Excel (legacy)"),
        # Projects
        ".aprx": ("project", "ArcGIS Pro Project"),
        ".mxd": ("project", "ArcMap Project (legacy)"),
        # Symbology
        ".lyrx": ("symbology", "Layer File"),
        ".lyr": ("symbology", "Layer File (legacy)"),
        ".stylx": ("symbology", "Style File"),
        # Documents
        ".pdf": ("document", "PDF"),
    }

    found = {}
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Detect file geodatabases (folders ending in .gdb)
        for d in dirnames[:]:
            if d.lower().endswith(".gdb"):
                found.setdefault("geodatabase", []).append({
                    "path": os.path.join(dirpath, d),
                    "type": "File Geodatabase",
                    "name": d,
                })

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in GIS_EXTENSIONS:
                continue
            category, fmt = GIS_EXTENSIONS[ext]
            full_path = os.path.join(dirpath, filename)
            try:
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
            except OSError:
                size_mb = 0
            found.setdefault(category, []).append({
                "path": full_path,
                "type": fmt,
                "name": filename,
                "size_mb": round(size_mb, 1),
            })

    # Print report
    total = sum(len(v) for v in found.values())
    print(f"\n=== DATA SCAN: {root_path} ({total} GIS files found) ===\n")
    for category, items in sorted(found.items()):
        print(f"{category.upper()} ({len(items)} files):")
        for item in items:
            size = f"({item['size_mb']:.1f} MB)" if item.get("size_mb") else ""
            print(f"  {item['name']}  {item['type']}  {size}")
            print(f"    {item['path']}")
        print()

    return found

# Example: scan a USB drive
# scan_for_gis_data(r"E:\\")
# scan_for_gis_data(os.path.expanduser("~\\Downloads"))
```

### Identify UK data from filenames
```python
def identify_uk_dataset(filename, fields=None):
    """Guess what a UK GIS dataset is from its filename and fields.

    OS VectorMap Local, Digimap DTM, EA Flood, MAGIC data all have
    recognizable naming patterns.
    """
    name = filename.lower()
    guesses = []

    # OS Grid reference pattern (2 letters + 2 digits, e.g., SU34, TQ38)
    import re
    grid_ref = re.search(r'[a-z]{2}\d{2}', name)

    # Digimap DTM tiles
    if "dtm" in name and (".asc" in name or ".tif" in name):
        res = "5m" if "5m" in name or "dtm5" in name else "50m" if "50m" in name else "unknown"
        guesses.append(f"Edina Digimap DTM ({res} resolution)")
        if grid_ref:
            guesses.append(f"Grid tile: {grid_ref.group().upper()}")

    # OS VectorMap Local / Strategi
    if "road" in name:
        guesses.append("OS road network (VectorMap Local or Strategi)")
    if "rail" in name:
        guesses.append("OS rail network")
    if "surfacewater" in name or "river" in name or "watercourse" in name:
        guesses.append("OS rivers / watercourses")
    if "building" in name or "glasshouse" in name:
        guesses.append("OS buildings (VectorMap Local)")
    if "woodland" in name:
        guesses.append("OS / Natural England woodland")

    # EA Flood data
    if "flood" in name:
        if "zone_2" in name or "zone2" in name:
            guesses.append("EA Flood Zone 2 (medium probability)")
        elif "zone_3" in name or "zone3" in name:
            guesses.append("EA Flood Zone 3 (high probability)")
        elif "warning" in name:
            guesses.append("EA Flood Warning Areas")
        elif "alert" in name:
            guesses.append("EA Flood Alert Areas")
        else:
            guesses.append("EA Flood data (check TYPE or PROB_4BAND field)")

    # Natural England / MAGIC
    if "alc" in name or "agri" in name and "land" in name:
        guesses.append("Agricultural Land Classification (Natural England)")
    if "habitat" in name or "priority" in name:
        guesses.append("Priority Habitats Inventory (Natural England)")
    if "sssi" in name:
        guesses.append("SSSI — Site of Special Scientific Interest")
    if "nnr" in name:
        guesses.append("NNR — National Nature Reserve")
    if "sac" in name:
        guesses.append("SAC — Special Area of Conservation")
    if "spa" in name:
        guesses.append("SPA — Special Protection Area")
    if "ancient" in name and "woodland" in name:
        guesses.append("Ancient Woodland (irreplaceable habitat)")
    if "ramsar" in name:
        guesses.append("Ramsar wetland site")
    if "greenbelt" in name or "green_belt" in name:
        guesses.append("Green Belt designation")

    # Basemap / aerial
    if "25k" in name or "25000" in name:
        guesses.append("OS 1:25,000 basemap (Explorer scale)")
    if "50k" in name or "50000" in name:
        guesses.append("OS 1:50,000 basemap (Landranger scale)")
    if "aerial" in name or "ortho" in name:
        guesses.append("Aerial imagery / orthophoto")

    # Field-based identification
    if fields:
        field_names = [f.lower() for f in fields]
        if "alc_grade" in field_names:
            guesses.append("Confirmed: Agricultural Land Classification")
        if "main_habit" in field_names:
            guesses.append("Confirmed: Priority Habitats Inventory")
        if "prob_4band" in field_names:
            guesses.append("Confirmed: EA Flood Map for Planning")
        if "classifica" in field_names or "roadnumber" in field_names:
            guesses.append("Confirmed: OS road network")

    return guesses if guesses else ["Unknown dataset — inspect fields manually"]
```

### Match scanned data to a project brief
```python
def match_data_to_brief(brief_requirements, scanned_data):
    """Compare what the brief needs against what was found on disk.

    brief_requirements: list of dicts with 'name' and 'keywords'
    scanned_data: output from scan_for_gis_data()
    """
    all_files = []
    for category in scanned_data.values():
        all_files.extend(category)

    matches = []
    missing = []

    for req in brief_requirements:
        # Search by keyword matching against filenames
        found = None
        for f in all_files:
            fname = f["name"].lower()
            if any(kw.lower() in fname for kw in req["keywords"]):
                found = f
                break

        if found:
            matches.append({"requirement": req["name"], "file": found})
        else:
            missing.append(req)

    # Print report
    print("\n=== BRIEF vs DATA MATCH ===\n")
    print(f"{'Requirement':<35} {'Found?':<25} {'Status'}")
    print("-" * 80)
    for m in matches:
        print(f"{m['requirement']:<35} {m['file']['name']:<25} FOUND")
    for m in missing:
        print(f"{m['name']:<35} {'---':<25} MISSING")

    if missing:
        print(f"\n{len(missing)} datasets still needed:")
        for m in missing:
            source = m.get("source", "Check brief for source")
            print(f"  - {m['name']}: download from {source}")

    return {"matches": matches, "missing": missing}

# Example usage for a typical UK suitability brief:
UK_SUITABILITY_REQUIREMENTS = [
    {"name": "Study area boundary", "keywords": ["study_area", "boundary", "site"],
     "source": "Create in ArcGIS Pro or define coordinates"},
    {"name": "OS Basemap (1:25k)", "keywords": ["25k", "25000", "basemap", "raster"],
     "source": "Edina Digimap (digimap.edina.ac.uk)"},
    {"name": "Roads", "keywords": ["road", "highway", "street"],
     "source": "Edina Digimap — OS VectorMap Local"},
    {"name": "Rail", "keywords": ["rail", "railway", "train"],
     "source": "Edina Digimap — OS VectorMap Local"},
    {"name": "Rivers / watercourses", "keywords": ["river", "water", "stream", "surfacewater"],
     "source": "Edina Digimap — OS VectorMap Local"},
    {"name": "Urban areas / buildings", "keywords": ["urban", "building", "builtup", "settlement"],
     "source": "Edina Digimap — OS VectorMap Local"},
    {"name": "Woodland", "keywords": ["woodland", "forest", "wood"],
     "source": "Edina Digimap — OS VectorMap Local or Natural England"},
    {"name": "DTM (elevation)", "keywords": ["dtm", "dem", "elevation", "terrain"],
     "source": "Edina Digimap — DTM5"},
    {"name": "Flood Zone 2", "keywords": ["flood_zone_2", "floodzone2", "fz2"],
     "source": "data.gov.uk — EA Flood Map for Planning"},
    {"name": "Flood Zone 3", "keywords": ["flood_zone_3", "floodzone3", "fz3", "flood"],
     "source": "data.gov.uk — EA Flood Map for Planning"},
    {"name": "Agricultural Land Classification", "keywords": ["alc", "agricultural", "agri_land"],
     "source": "magic.defra.gov.uk — Natural England"},
    {"name": "Priority Habitats", "keywords": ["habitat", "priority_habitat", "phi"],
     "source": "magic.defra.gov.uk — Natural England"},
    {"name": "SSSI", "keywords": ["sssi"],
     "source": "magic.defra.gov.uk — Natural England"},
    {"name": "SAC", "keywords": ["sac"],
     "source": "magic.defra.gov.uk — Natural England"},
    {"name": "SPA", "keywords": ["spa"],
     "source": "magic.defra.gov.uk — Natural England"},
    {"name": "Aerial imagery", "keywords": ["aerial", "ortho", "satellite"],
     "source": "Edina Digimap — Aerial"},
]
```

### Find .aprx projects on disk
```python
import glob

def find_arcgis_projects(search_paths=None):
    """Find all ArcGIS Pro projects (.aprx) on accessible drives."""
    if search_paths is None:
        search_paths = [
            os.path.expanduser(r"~\Documents\ArcGIS\Projects"),
            os.path.expanduser(r"~\Documents"),
            os.path.expanduser(r"~\Desktop"),
            os.path.expanduser(r"~\Downloads"),
        ]
        # Add removable drives (D: through H:)
        for letter in "DEFGH":
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                search_paths.append(drive)

    projects = []
    for base in search_paths:
        if not os.path.exists(base):
            continue
        for aprx in glob.glob(os.path.join(base, "**", "*.aprx"), recursive=True):
            size_mb = os.path.getsize(aprx) / (1024 * 1024)
            projects.append({"path": aprx, "size_mb": round(size_mb, 1)})

    print(f"Found {len(projects)} ArcGIS Pro projects:")
    for p in projects:
        print(f"  {p['path']}  ({p['size_mb']} MB)")
    return projects
```

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

### Map Production — Layouts, Elements, Symbology, Labels, Export

Full layout automation for professional map production. This covers creating
layouts from scratch, adding map frames, map elements, symbology, labels,
and exporting to JPEG/PDF at print quality.

#### Create a layout from scratch
```python
aprx = arcpy.mp.ArcGISProject(r"C:\Projects\MyProject.aprx")

# Create a new A4 layout (portrait: 21cm x 29.7cm)
layout = aprx.createLayout(29.7, 21, "CENTIMETER", "A4 Landscape")
# Portrait: aprx.createLayout(21, 29.7, "CENTIMETER", "A4 Portrait")

# Add a map frame — this is the main map view
map_obj = aprx.listMaps("Map")[0]
map_frame = layout.createMapFrame(
    arcpy.Extent(1, 3, 27, 19),  # position on layout (left, bottom, right, top) in cm
    map_obj,
    "Main Map Frame",
)
# Set the map extent to the study area
study_extent = arcpy.Describe("study_area").extent
map_frame.camera.setExtent(study_extent)

# Add an inset / locator map (smaller frame, different map or same map zoomed out)
inset_map = aprx.listMaps("Locator")[0]  # or same map with different extent
inset_frame = layout.createMapFrame(
    arcpy.Extent(22, 14, 28, 19),  # top-right corner of layout
    inset_map,
    "Inset Map",
)
# Set inset extent to wider area
inset_frame.camera.setExtent(
    arcpy.Extent(300000, 100000, 600000, 400000)  # wider UK extent in BNG
)
```

#### Multiple map frames on one layout (side-by-side detail maps)
```python
# Two detail maps side by side (e.g., "before" and "after", or two study areas)
layout = aprx.createLayout(29.7, 21, "CENTIMETER", "Dual Map Layout")

# Left map frame
left_frame = layout.createMapFrame(
    arcpy.Extent(1, 3, 14, 19),
    aprx.listMaps("Detail A")[0],
    "Left Detail",
)
# Right map frame
right_frame = layout.createMapFrame(
    arcpy.Extent(15, 3, 28, 19),
    aprx.listMaps("Detail B")[0],
    "Right Detail",
)
```

#### Add map elements (title, scale bar, north arrow, legend, text)
```python
# Title
title = layout.createMapSurroundElement(
    arcpy.Point(14.85, 20.5),  # center-top of layout
    "TEXT",
    "Main Title",
)
# Access CIM for full text control
cim = title.getDefinition("V3")
cim.textString = "Site Suitability Analysis: Study Area"
cim.textSymbol.symbol.height = 16
cim.textSymbol.symbol.font.family = "Arial"
cim.textSymbol.symbol.font.style = "Bold"
title.setDefinition(cim)

# Scale bar
scale_bar = layout.createMapSurroundElement(
    arcpy.Point(5, 1.5),
    "SCALE_BAR",
    "Scale Bar",
    map_frame,  # linked to this map frame
)

# North arrow
north_arrow = layout.createMapSurroundElement(
    arcpy.Point(2, 17),
    "NORTH_ARROW",
    "North Arrow",
    map_frame,
)

# Legend
legend = layout.createMapSurroundElement(
    arcpy.Point(23, 8),
    "LEGEND",
    "Legend",
    map_frame,
)

# Copyright / data source text
copyright_text = layout.createGraphicElement(
    arcpy.Point(14.85, 0.8),
    "TEXT",
    "Copyright Text",
)
cim = copyright_text.getDefinition("V3")
cim.textString = (
    "Contains OS data © Crown copyright and database right 2024. "
    "Flood data © Environment Agency. DTM © Edina Digimap."
)
cim.textSymbol.symbol.height = 6
copyright_text.setDefinition(cim)

# Author / creator text
author_text = layout.createGraphicElement(
    arcpy.Point(26, 0.8), "TEXT", "Author",
)
cim = author_text.getDefinition("V3")
cim.textString = "Created by: [Your Name]"
cim.textSymbol.symbol.height = 7
author_text.setDefinition(cim)
```

#### Update existing layout text elements
```python
layout = aprx.listLayouts("A4 Landscape")[0]
for elm in layout.listElements("TEXT_ELEMENT"):
    print(f"  {elm.name}: '{elm.text}'")
    if elm.name == "Title":
        elm.text = "Updated Map Title"
    if elm.name == "Date":
        import datetime
        elm.text = datetime.date.today().strftime("%d %B %Y")
```

#### Symbology — Unique Values
```python
map_obj = aprx.listMaps("Map")[0]
lyr = map_obj.listLayers("land_use")[0]

sym = lyr.symbology
sym.updateRenderer("UniqueValueRenderer")
sym.renderer.fields = ["LU_CODE"]

# Add values manually
sym.renderer.addValues({
    sym.renderer.fields[0]: [
        ["Urban", {"color": {"RGB": [255, 0, 0, 100]}, "label": "Urban"}],
        ["Forest", {"color": {"RGB": [0, 128, 0, 100]}, "label": "Forest"}],
        ["Agriculture", {"color": {"RGB": [255, 255, 0, 100]}, "label": "Agriculture"}],
        ["Water", {"color": {"RGB": [0, 0, 255, 100]}, "label": "Water"}],
    ]
})
lyr.symbology = sym

# Alternative: use a layer file (.lyrx) for complex symbology
lyr.updateConnectionProperties(lyr.connectionProperties, lyr.connectionProperties)
arcpy.management.ApplySymbologyFromLayer(
    in_layer=lyr,
    in_symbology_layer=r"C:\Templates\land_use_symbology.lyrx",
    symbology_fields=[["VALUE_FIELD", "LU_CODE", "LU_CODE"]],
)
```

#### Symbology — Graduated Colors (classified values)
```python
lyr = map_obj.listLayers("elevation")[0]
sym = lyr.symbology
sym.updateRenderer("GraduatedColorsRenderer")
sym.renderer.classificationField = "ELEVATION"
sym.renderer.breakCount = 5
sym.renderer.classificationMethod = "NaturalBreaks"
sym.renderer.colorRamp = aprx.listColorRamps("Elevation #1")[0]
lyr.symbology = sym
```

#### Symbology — Stretched (continuous raster: elevation, slope)
```python
# For raster layers (DEM, slope, etc.)
raster_lyr = map_obj.listLayers("dem_clipped")[0]
sym = raster_lyr.symbology
sym.updateColorizer("RasterStretchColorizer")
sym.colorizer.stretchType = "MinimumMaximum"
sym.colorizer.colorRamp = aprx.listColorRamps("Elevation #1")[0]
raster_lyr.symbology = sym
```

#### Symbology — Binary raster (suitable / unsuitable)
```python
# Two-colour symbology for binary suitability rasters (values 0 and 1)
binary_lyr = map_obj.listLayers("suitable_areas")[0]
sym = binary_lyr.symbology
sym.updateColorizer("RasterUniqueValueColorizer")
# Access via CIM for precise color control
cim = binary_lyr.getDefinition("V3")
colorizer = cim.colorizer
# Set colors: 0 = red (unsuitable), 1 = green (suitable)
for group in colorizer.groups:
    for cls in group.classes:
        if cls.values[0] == "0":
            cls.symbol.symbol.color = {"RGB": [255, 0, 0, 100]}
            cls.label = "Unsuitable"
        elif cls.values[0] == "1":
            cls.symbol.symbol.color = {"RGB": [0, 200, 0, 100]}
            cls.label = "Suitable"
binary_lyr.setDefinition(cim)
```

#### Labels — enable and configure
```python
lyr = map_obj.listLayers("towns")[0]
lyr.showLabels = True

# Configure label class
label_class = lyr.listLabelClasses()[0]
label_class.expression = "$feature.NAME"  # Arcade expression
label_class.visible = True

# Font styling via CIM
cim = lyr.getDefinition("V3")
for lc in cim.labelClasses:
    ts = lc.textSymbol.symbol
    ts.height = 8
    ts.font.family = "Arial"
    ts.font.style = "Bold"
    ts.color = {"RGB": [0, 0, 0, 100]}
    # Halo (text outline for readability)
    ts.haloSize = 1
    ts.haloSymbol = {"type": "CIMPolygonSymbol", "symbolLayers": [
        {"type": "CIMSolidFill", "color": {"RGB": [255, 255, 255, 100]}}
    ]}
lyr.setDefinition(cim)
```

#### Export to JPEG at 300 dpi
```python
layout = aprx.listLayouts("A4 Landscape")[0]

# JPEG export at 300 dpi (print quality)
layout.exportToJPEG(
    r"C:\Output\Map1_SuitabilityAnalysis.jpg",
    resolution=300,
    jpeg_quality=95,              # 1-100, higher = better quality
    clip_to_elements=False,       # export full page
)

# Also export to PDF (vector quality, recommended for print)
layout.exportToPDF(
    r"C:\Output\Map1_SuitabilityAnalysis.pdf",
    resolution=300,
    image_quality="BEST",
    layers_attributes="LAYERS_AND_ATTRIBUTES",
)

# Export to PNG (lossless, good for reports)
layout.exportToPNG(
    r"C:\Output\Map1_SuitabilityAnalysis.png",
    resolution=300,
)

# Batch export all layouts in the project
for layout in aprx.listLayouts():
    safe_name = layout.name.replace(" ", "_")
    layout.exportToJPEG(
        rf"C:\Output\{safe_name}.jpg",
        resolution=300, jpeg_quality=95,
    )
    print(f"Exported: {safe_name}")
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

# Polygon to Raster — CRITICAL for suitability analysis
# Converts vector polygons to raster grid cells
arcpy.conversion.PolygonToRaster(
    in_features="land_use",
    value_field="LU_CODE",           # attribute to burn into raster cells
    out_rasterdataset="land_use_raster.tif",
    cell_assignment="CELL_CENTER",   # or MAXIMUM_AREA, MAXIMUM_COMBINED_AREA
    priority_field="NONE",
    cellsize=5,                      # cell size in map units
)
# ⚠ CRITICAL: Set the environment extent BEFORE running PolygonToRaster
# If extent isn't set, the output raster may not align with other rasters
# and Raster Calculator will fail with misaligned grid errors.
with arcpy.EnvManager(
    extent="study_area",              # or "MINOF" / explicit coordinates
    cellSize=5,                       # must match other rasters
    snapRaster="reference_raster",    # ensures grid alignment
):
    arcpy.conversion.PolygonToRaster(
        in_features="flood_zones",
        value_field="FLOOD_RISK",
        out_rasterdataset="flood_raster.tif",
        cellsize=5,
    )

# Feature to Raster — alternative (simpler but less control)
arcpy.conversion.FeatureToRaster(
    in_features="land_use",
    field="LU_CODE",
    out_raster="land_use_raster.tif",
    cell_size=5,
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

### ArcGIS API for Python (web GIS) — `arcgis` package

The `arcgis` package is separate from `arcpy`. It talks to ArcGIS Online (AGOL)
and Portal via REST. Works anywhere (no ArcGIS Pro install needed).

```python
from arcgis.gis import GIS

# Connect to ArcGIS Online
gis = GIS("https://www.arcgis.com", "username", "password")

# Connect to Enterprise Portal
gis = GIS("https://portal.company.com/portal", "admin", "pass")

# Anonymous access (public content only)
gis = GIS()

# Connect using Pro's active portal (when running inside ArcGIS Pro)
gis = GIS("pro")
```

#### Content search and management
```python
# Search for items
items = gis.content.search("owner:me AND type:Feature Layer", max_items=100)
for item in items:
    print(f"{item.title} | {item.type} | {item.id}")

# Search with filters
maps = gis.content.search(query="flood", item_type="Web Map", outside_org=False)
layers = gis.content.search("tags:infrastructure", item_type="Feature Layer")

# Get item by ID
item = gis.content.get("abc123def456")
print(item.title, item.type, item.url)

# Create/upload content
csv_item = gis.content.add(
    item_properties={
        "title": "Survey Results",
        "type": "CSV",
        "tags": "survey,2024",
        "description": "Field survey point data",
    },
    data="survey_results.csv",
)
# Publish CSV as hosted feature layer
published = csv_item.publish(overwrite=True)
print(f"Published: {published.url}")

# Upload and publish shapefile
shp_item = gis.content.add({"title": "Parcels", "type": "Shapefile"}, data="parcels.zip")
fl_item = shp_item.publish()

# Upload file geodatabase
gdb_item = gis.content.add(
    {"title": "Analysis Results", "type": "File Geodatabase"},
    data="results.gdb.zip",
)

# Update existing item
item.update(item_properties={"description": "Updated description"})
item.update(data="new_data.csv")

# Delete item
item.delete(permanent=True)

# Move item to folder
gis.content.create_folder("Archive")
item.move("Archive")

# Share item
item.share(org=True)                    # share with organization
item.share(everyone=True)               # share publicly
item.share(groups=["group_id_here"])     # share with specific group
```

#### Feature layer CRUD (create, read, update, delete)
```python
from arcgis.features import FeatureLayer, FeatureSet
import pandas as pd

# Access hosted feature layer
fl = FeatureLayer("https://services.arcgis.com/.../FeatureServer/0")
# Or from an item
item = gis.content.get("abc123")
fl = item.layers[0]       # first layer
tbl = item.tables[0]      # first table (if any)

# Query features
result = fl.query(where="POPULATION > 50000", out_fields="NAME,POPULATION,SHAPE")
print(f"Found {len(result.features)} features")

# Query to Spatially Enabled DataFrame (best for analysis)
sdf = fl.query(where="1=1").sdf
print(sdf.head())
print(sdf.columns.tolist())
print(sdf.spatial.name)  # geometry column

# Query with spatial filter
from arcgis.geometry import Envelope
extent = Envelope({
    "xmin": -118.5, "ymin": 33.7, "xmax": -118.1, "ymax": 34.1,
    "spatialReference": {"wkid": 4326},
})
nearby = fl.query(geometry_filter=extent, return_geometry=True)

# Add new features
new_features = [
    {
        "attributes": {"NAME": "New Park", "TYPE": "Recreation", "AREA_HA": 12.5},
        "geometry": {"x": -118.25, "y": 34.05, "spatialReference": {"wkid": 4326}},
    },
    {
        "attributes": {"NAME": "Lake View", "TYPE": "Conservation", "AREA_HA": 45.0},
        "geometry": {"x": -118.30, "y": 34.10, "spatialReference": {"wkid": 4326}},
    },
]
result = fl.edit_features(adds=new_features)
print(f"Added: {result['addResults']}")

# Update existing features (must include OBJECTID)
updates = [
    {"attributes": {"OBJECTID": 42, "STATUS": "Approved", "REVIEW_DATE": "2024-06-15"}},
]
result = fl.edit_features(updates=updates)

# Delete features
result = fl.edit_features(deletes="42,43,44")  # by OID
# Or delete by query
fl.delete_features(where="STATUS = 'Expired'")

# Append data from DataFrame
import pandas as pd
df = pd.read_csv("new_sites.csv")
sdf = pd.DataFrame.spatial.from_xy(df, "LONGITUDE", "LATITUDE", sr=4326)
fl.edit_features(adds=sdf.spatial.to_featureset())

# Truncate and reload
fl.manager.truncate()
fl.edit_features(adds=new_features)
```

#### Web maps and web apps
```python
from arcgis.mapping import WebMap

# Create a new web map
wm = WebMap()
wm.add_layer(gis.content.get("feature_layer_item_id"))
wm.add_layer(fl, {"title": "Custom Title", "visibility": True})

# Set extent
wm.extent = {
    "xmin": -118.5, "ymin": 33.7, "xmax": -118.1, "ymax": 34.1,
    "spatialReference": {"wkid": 4326},
}

# Set basemap
wm.basemap = "dark-gray-vector"
# Options: streets, satellite, hybrid, topo, gray, dark-gray, oceans,
#   streets-vector, topo-vector, gray-vector, dark-gray-vector

# Save web map
wm_item = wm.save(
    item_properties={
        "title": "Infrastructure Analysis",
        "tags": "infrastructure,analysis",
        "snippet": "Map showing infrastructure analysis results",
    }
)

# Open existing web map
existing_wm = WebMap(gis.content.get("webmap_item_id"))
print(f"Layers: {[l.title for l in existing_wm.layers]}")

# Update layer properties
for layer in existing_wm.layers:
    if layer.title == "Parcels":
        layer.visibility = False
existing_wm.update()
```

#### Portal administration
```python
from arcgis.gis import User, Group

# User management
me = gis.users.me
print(f"Logged in as: {me.username} ({me.role})")

# List all users (admin only)
users = gis.users.search("*", max_users=500)
for u in users:
    print(f"  {u.username}: {u.role} | Last login: {u.lastLogin}")

# Create user (Enterprise only)
new_user = gis.users.create(
    username="jdoe",
    password="TempPass123!",
    firstname="Jane", lastname="Doe",
    email="jdoe@company.com",
    role="org_publisher",
    user_type="creatorUT",
)

# Group management
groups = gis.groups.search("*")
for g in groups:
    print(f"  {g.title} ({len(g.get_members()['users'])} members)")

# Create group
new_group = gis.groups.create(
    title="Field Team",
    tags="field,survey",
    description="Group for field survey team",
    access="org",
)
new_group.add_users(["user1", "user2"])

# Content usage and credits
usage = me.items()
for item in usage:
    print(f"  {item.title}: {item.numViews} views, size={item.size}")
```

#### Geocoding (web-based)
```python
from arcgis.geocoding import geocode, reverse_geocode, batch_geocode

# Single address geocode
results = geocode("1600 Pennsylvania Ave, Washington DC")
if results:
    best = results[0]
    print(f"Score: {best['score']}")
    print(f"Location: {best['location']}")
    print(f"Address: {best['attributes']['Match_addr']}")

# Reverse geocode (coordinates to address)
from arcgis.geometry import Point
location = Point({"x": -77.0365, "y": 38.8977, "spatialReference": {"wkid": 4326}})
address = reverse_geocode(location)
print(address["address"]["Match_addr"])

# Batch geocode (many addresses at once — uses credits on AGOL)
addresses = [
    "380 New York St, Redlands, CA",
    "1 World Trade Center, New York, NY",
    "1600 Amphitheatre Parkway, Mountain View, CA",
]
results = batch_geocode(addresses)
for r in results:
    print(f"  {r['attributes']['ResultID']}: {r['score']} - {r['address']}")

# Geocode from DataFrame (creates point geometry from address column)
import pandas as pd
df = pd.read_csv("customers.csv")
geocoded_sdf = geocode(df, address_field="ADDRESS", as_featureset=False)
```

#### Spatial analysis services (hosted)
```python
from arcgis.features.analysis import create_buffers, overlay_layers
from arcgis.features.analysis import find_hot_spots, interpolate_points

# Buffer analysis (runs on server, no local processing)
buffer_result = create_buffers(
    input_layer=fl,
    distances=[1, 5, 10],
    units="Kilometers",
    dissolve_type="Dissolve",
    output_name="service_areas",
)

# Overlay analysis
overlay_result = overlay_layers(
    input_layer=fl,
    overlay_layer=other_fl,
    overlay_type="Intersect",
    output_name="intersection_result",
)

# Hot spot analysis
hotspots = find_hot_spots(
    analysis_layer=fl,
    analysis_field="INCIDENT_COUNT",
    output_name="crime_hotspots",
)

# Interpolation
surface = interpolate_points(
    input_layer=fl,
    field="TEMPERATURE",
    interpolate_option="5",
    output_name="temp_surface",
)

# Enrich data with demographics (uses credits)
from arcgis.features.enrich_data import enrich_layer
enriched = enrich_layer(
    input_layer=fl,
    data_collections=["KeyGlobalFacts", "Policy"],
    output_name="enriched_sites",
)
```

#### Working with Spatially Enabled DataFrames
```python
import pandas as pd
from arcgis.features import GeoAccessor, GeoSeriesAccessor

# Read from feature layer
sdf = fl.query(where="1=1").sdf

# Create from CSV with coordinates
df = pd.read_csv("sites.csv")
sdf = pd.DataFrame.spatial.from_xy(df, x_column="LON", y_column="LAT", sr=4326)

# Create from shapefile / GDB / GeoJSON
sdf = pd.DataFrame.spatial.from_featureclass("path/to/data.shp")
sdf = pd.DataFrame.spatial.from_featureclass(r"C:\data.gdb\parcels")

# Spatial operations on DataFrames
sdf.spatial.plot(map_widget=my_map)
sdf.spatial.to_featureclass(r"C:\output.gdb\result")
sdf.spatial.to_featurelayer("My Layer Title", gis=gis)

# Buffer, clip, dissolve on SDF
buffered = sdf.spatial.buffer(distance=500)
clipped = sdf.spatial.clip(study_area_sdf)
dissolved = sdf.dissolve(by="ZONE_CODE")

# Spatial join
joined = sdf.spatial.join(other_sdf, how="inner", op="intersects")

# Area / length calculations
sdf["AREA_M2"] = sdf.SHAPE.geom.area
sdf["LENGTH_M"] = sdf.SHAPE.geom.length

# Export to GeoJSON, Shapefile, CSV
sdf.spatial.to_featureclass(r"C:\output\result.shp")
sdf.to_csv("output.csv", index=False)
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

## Dataset Discovery & Inspection

How to inventory what's on the map, understand each dataset, and pick the right
tools. Run these FIRST before starting any analysis.

### List everything in the map
```python
aprx = arcpy.mp.ArcGISProject("CURRENT")  # or path to .aprx

for m in aprx.listMaps():
    print(f"\n=== Map: {m.name} ===")
    for lyr in m.listLayers():
        if lyr.isFeatureLayer:
            desc = arcpy.Describe(lyr)
            count = int(arcpy.management.GetCount(lyr)[0])
            sr = desc.spatialReference
            print(f"  [Vector] {lyr.name}")
            print(f"    Shape: {desc.shapeType}  |  Features: {count}")
            print(f"    CRS: {sr.name} (EPSG:{sr.factoryCode})")
            print(f"    Source: {lyr.dataSource}")
            print(f"    Fields: {[f.name for f in arcpy.ListFields(lyr) if f.type not in ('OID','Geometry')]}")
        elif lyr.isRasterLayer:
            desc = arcpy.Describe(lyr)
            print(f"  [Raster] {lyr.name}")
            print(f"    Size: {desc.width}x{desc.height}  |  Bands: {desc.bandCount}")
            print(f"    Cell: {desc.meanCellWidth}x{desc.meanCellHeight}")
            print(f"    CRS: {desc.spatialReference.name}")
            print(f"    Pixel type: {desc.pixelType}")
            print(f"    Source: {lyr.dataSource}")
        elif lyr.isGroupLayer:
            print(f"  [Group] {lyr.name} ({len(list(lyr.listLayers()))} sub-layers)")
        else:
            print(f"  [Other] {lyr.name} (table/basemap/etc)")
```

### Detailed field inspection for a specific layer
```python
layer_name = "parcels"  # change to your layer
fields = arcpy.ListFields(layer_name)

print(f"\n{'Field':<25} {'Type':<12} {'Length':<8} {'Nullable':<10} {'Domain'}")
print("-" * 75)
for f in fields:
    domain = f.domain if f.domain else ""
    print(f"{f.name:<25} {f.type:<12} {f.length:<8} {f.isNullable:<10} {domain}")

# Sample first 5 rows to understand the data
print("\nSample data (first 5 rows):")
field_names = [f.name for f in fields if f.type not in ("OID", "Geometry", "Blob")]
with arcpy.da.SearchCursor(layer_name, field_names) as cursor:
    for i, row in enumerate(cursor):
        if i >= 5:
            break
        print(f"  {dict(zip(field_names, row))}")
```

### Unique values and field statistics
```python
# Get unique values for a field (useful for classification / filtering)
def unique_values(table, field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor if row[0] is not None})

print("Land use types:", unique_values("parcels", "LAND_USE"))
print("Zone codes:", unique_values("parcels", "ZONE_CODE"))

# Numeric field statistics
import statistics
def field_stats(table, field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        values = [row[0] for row in cursor if row[0] is not None]
    return {
        "count": len(values),
        "min": min(values), "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0,
    }
print("Elevation stats:", field_stats("sample_points", "ELEVATION"))
```

### Check spatial reference consistency across layers
```python
aprx = arcpy.mp.ArcGISProject("CURRENT")
map_obj = aprx.listMaps()[0]

crs_report = {}
for lyr in map_obj.listLayers():
    if lyr.isFeatureLayer or lyr.isRasterLayer:
        desc = arcpy.Describe(lyr)
        sr = desc.spatialReference
        key = f"{sr.name} (EPSG:{sr.factoryCode})"
        crs_report.setdefault(key, []).append(lyr.name)

print("\n=== CRS Report ===")
for crs, layers in crs_report.items():
    print(f"\n{crs}:")
    for name in layers:
        print(f"  - {name}")

if len(crs_report) > 1:
    print("\n⚠ WARNING: Mixed coordinate systems detected!")
    print("  Use arcpy.management.Project() to reproject before analysis.")
```

### Identify geometry type and pick the right tool
```python
# Quick decision helper: what can I do with this data?
def suggest_tools(layer_name):
    desc = arcpy.Describe(layer_name)
    shape = desc.shapeType
    suggestions = []

    if shape == "Point":
        suggestions = [
            "Buffer → create areas around points",
            "Near → find closest features",
            "SpatialJoin → attach polygon attributes to points",
            "Kernel Density / IDW → interpolate to surface",
            "Hot Spot Analysis → find clusters",
            "XY To Line → connect pairs of points",
        ]
    elif shape == "Polygon":
        suggestions = [
            "Intersect / Union → overlay with other polygons",
            "Clip → cut to study area boundary",
            "Dissolve → merge by attribute",
            "Buffer → expand/shrink boundaries",
            "SpatialJoin → count points inside polygons",
            "Erase → subtract protected areas",
            "CalculateGeometryAttributes → compute area/perimeter",
            "Zonal Statistics → summarize raster values per polygon",
        ]
    elif shape == "Polyline":
        suggestions = [
            "Buffer → create corridors",
            "Intersect → find crossing points",
            "Near → distance from features to lines",
            "Split Line at Point → segment lines",
            "Feature Vertices To Points → extract nodes",
            "Network Analyst → routing (if network dataset)",
            "GeneratePointsAlongLines → sample at intervals",
        ]
    elif shape == "MultiPatch":
        suggestions = [
            "3D Analyst tools (Is3D, Skyline, LineOfSight)",
            "Multipatch footprint → convert to 2D polygons",
        ]

    count = int(arcpy.management.GetCount(layer_name)[0])
    sr = desc.spatialReference
    print(f"\n{layer_name}: {shape} ({count} features, {sr.name})")
    print("Suggested tools:")
    for s in suggestions:
        print(f"  → {s}")

# Run for each layer
for lyr in map_obj.listLayers():
    if lyr.isFeatureLayer:
        suggest_tools(lyr.name)
```

### Raster inspection and tool suggestions
```python
def inspect_raster(raster_name):
    desc = arcpy.Describe(raster_name)
    r = arcpy.Raster(raster_name)
    print(f"\n{raster_name}:")
    print(f"  Dimensions: {desc.width} x {desc.height}")
    print(f"  Cell size: {desc.meanCellWidth} x {desc.meanCellHeight}")
    print(f"  Bands: {desc.bandCount}")
    print(f"  Pixel type: {desc.pixelType}")
    print(f"  NoData: {r.noDataValue}")
    print(f"  Value range: {r.minimum} to {r.maximum}")
    print(f"  Mean: {r.mean:.2f}  |  Std Dev: {r.standardDeviation:.2f}")
    print(f"  CRS: {desc.spatialReference.name}")

    # Suggest tools based on raster characteristics
    suggestions = [
        "Slope / Aspect → terrain derivatives (if DEM)",
        "Hillshade → shaded relief visualization",
        "Reclassify → classify into categories",
        "Con → conditional (if/else) map algebra",
        "ExtractByMask → clip to polygon",
        "ZonalStatisticsAsTable → summarize per zone",
        "FocalStatistics → neighborhood smoothing",
        "Contour → generate isolines",
    ]
    if desc.bandCount > 1:
        suggestions.extend([
            "CompositeBands → combine bands",
            "NDVI → (Band4 - Band3) / (Band4 + Band3) for vegetation",
            "Iso Cluster / Maximum Likelihood → classify imagery",
        ])
    print("  Suggested tools:")
    for s in suggestions:
        print(f"    → {s}")

# Inspect all rasters in workspace
arcpy.env.workspace = r"C:\Projects\data.gdb"
for raster in arcpy.ListRasters():
    inspect_raster(raster)
```

### List everything in a geodatabase (no map needed)
```python
# Inventory an entire geodatabase
def inventory_gdb(gdb_path):
    arcpy.env.workspace = gdb_path
    print(f"\n=== Geodatabase: {gdb_path} ===\n")

    # Feature datasets
    for fds in arcpy.ListDatasets(feature_type="Feature") or []:
        print(f"[Feature Dataset] {fds}")
        arcpy.env.workspace = os.path.join(gdb_path, fds)
        for fc in arcpy.ListFeatureClasses():
            desc = arcpy.Describe(fc)
            count = int(arcpy.management.GetCount(fc)[0])
            print(f"  {fc}: {desc.shapeType} ({count} features)")
        arcpy.env.workspace = gdb_path

    # Standalone feature classes
    print("\n[Standalone Feature Classes]")
    for fc in arcpy.ListFeatureClasses() or []:
        desc = arcpy.Describe(fc)
        count = int(arcpy.management.GetCount(fc)[0])
        print(f"  {fc}: {desc.shapeType} ({count} features)")

    # Tables
    print("\n[Tables]")
    for tbl in arcpy.ListTables() or []:
        count = int(arcpy.management.GetCount(tbl)[0])
        print(f"  {tbl}: {count} rows")

    # Rasters
    print("\n[Rasters]")
    for raster in arcpy.ListRasters() or []:
        desc = arcpy.Describe(raster)
        print(f"  {raster}: {desc.width}x{desc.height}, {desc.bandCount} bands")

inventory_gdb(r"C:\Projects\analysis.gdb")
```

---

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

## Hydrology & Watershed Analysis

Full watershed delineation and hydrological modelling using Spatial Analyst.

### Complete watershed workflow
```python
import arcpy
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

dem = "elevation_dem.tif"

# Step 1: Fill sinks — removes small imperfections in the DEM
# Without this, water gets "stuck" in artificial depressions
filled = Fill(dem)
filled.save("dem_filled.tif")

# Step 2: Flow Direction — which way does water flow from each cell?
# D8 method: assigns one of 8 directions (1,2,4,8,16,32,64,128)
flow_dir = FlowDirection(filled, force_flow="NORMAL")
flow_dir.save("flow_direction.tif")

# Step 3: Flow Accumulation — how many upstream cells drain through each cell?
# High values = streams, low values = ridges
flow_acc = FlowAccumulation(flow_dir, data_type="FLOAT")
flow_acc.save("flow_accumulation.tif")

# Step 4: Define stream network — threshold determines stream density
# Lower threshold = more streams; typical values: 500-5000 cells
stream_threshold = 1000
streams = Con(flow_acc > stream_threshold, 1)
streams.save("streams_raster.tif")

# Step 5: Stream Order (Strahler) — classify stream hierarchy
# 1 = headwater, higher = larger rivers
stream_order = StreamOrder(streams, flow_dir, "STRAHLER")
stream_order.save("stream_order.tif")

# Step 6: Stream to Feature — convert raster streams to polylines
arcpy.sa.StreamToFeature(stream_order, flow_dir, "stream_network", "SIMPLIFY")

# Step 7: Snap Pour Points — snap outlet points to highest flow accumulation
# Distance should be > cell size but not too large
pour_points = "outlet_points"  # your outlet locations
snapped = SnapPourPoint(pour_points, flow_acc, snap_distance=30, pour_point_field="ID")
snapped.save("snapped_pour_points.tif")

# Step 8: Watershed delineation — delineate catchment for each pour point
watersheds = Watershed(flow_dir, snapped)
watersheds.save("watersheds.tif")

# Step 9: Convert to polygon for further analysis
arcpy.conversion.RasterToPolygon(
    in_raster="watersheds.tif",
    out_polygon_features="watershed_polygons",
    simplify="SIMPLIFY",
    raster_field="Value",
)

# Step 10: Calculate area for each watershed
arcpy.management.CalculateGeometryAttributes(
    "watershed_polygons",
    [["AREA_KM2", "AREA"]],
    area_unit="SQUARE_KILOMETERS",
)

arcpy.CheckInExtension("Spatial")
print("Watershed delineation complete")
```

### Stream link and basin delineation
```python
from arcpy.sa import *

# Stream Link — unique ID for each stream segment between junctions
stream_links = StreamLink(streams, flow_dir)
stream_links.save("stream_links.tif")

# Basin — delineate ALL drainage basins (no pour points needed)
basins = Basin(flow_dir)
basins.save("all_basins.tif")

# Convert basins to polygons
arcpy.conversion.RasterToPolygon("all_basins.tif", "basin_polygons", "SIMPLIFY")
```

### Terrain derivatives for hydrology
```python
from arcpy.sa import *
dem = "dem_filled.tif"

# Slope — steepness (affects runoff speed)
slope = Slope(dem, output_measurement="DEGREE")
slope.save("slope_degrees.tif")

# Aspect — direction of downhill face (affects solar radiation, snowmelt)
aspect = Aspect(dem)
aspect.save("aspect.tif")

# Curvature — convex/concave terrain (affects flow convergence)
curvature = Curvature(dem, z_factor=1)
curvature.save("curvature.tif")

# Topographic Wetness Index (TWI) — where water accumulates
# TWI = ln(flow_accumulation / tan(slope_radians))
import math
flow_acc = FlowAccumulation(FlowDirection(Fill(dem)), data_type="FLOAT")
slope_rad = Slope(dem, output_measurement="DEGREE") * (math.pi / 180)
# Avoid division by zero: clamp slope minimum
slope_clamped = Con(slope_rad < 0.001, 0.001, slope_rad)
twi = Ln((flow_acc + 1) / Tan(slope_clamped))
twi.save("twi.tif")
```

### Flood inundation mapping
```python
from arcpy.sa import *

dem = "dem_filled.tif"
flood_level = 105.5  # water surface elevation in same units as DEM

# Areas below flood level = inundated
flooded = Con(Raster(dem) <= flood_level, 1, 0)
flooded.save("flood_extent.tif")

# Convert to polygon
arcpy.conversion.RasterToPolygon("flood_extent.tif", "flood_polygon", "SIMPLIFY")

# Calculate flood depth
flood_depth = Con(Raster(dem) <= flood_level, flood_level - Raster(dem))
flood_depth.save("flood_depth.tif")

# Zonal stats: what's affected?
arcpy.sa.ZonalStatisticsAsTable(
    "flood_polygon", "GRIDCODE", "buildings", "flood_building_stats", "DATA", "ALL"
)
```

### Curve Number rainfall-runoff (SCS method)
```python
from arcpy.sa import *

# Inputs: CN grid (from soil + land use), rainfall depth
cn_grid = Raster("curve_number.tif")
rainfall_inches = 4.0  # storm event depth

# S = potential maximum retention
s = (1000.0 / cn_grid) - 10.0
# Ia = initial abstraction (0.2S)
ia = 0.2 * s
# Runoff Q (inches) — only where rainfall > Ia
q = Con(
    rainfall_inches > ia,
    ((rainfall_inches - ia) ** 2) / (rainfall_inches - ia + s),
    0,
)
q.save("runoff_depth.tif")
```

---

## 3D Analyst & LAS / Point Cloud Processing

Working with LiDAR data, TINs, 3D features, and point clouds.

### LAS dataset setup and inspection
```python
import arcpy
arcpy.CheckOutExtension("3D")

# Create a LAS dataset (index for .las/.laz files)
arcpy.management.CreateLasDataset(
    input=r"C:\LiDAR\tiles",              # folder of .las files
    out_las_dataset="lidar_index.lasd",
    folder_recursion="RECURSION",
    compute_stats="COMPUTE_STATS",
    relative_paths="RELATIVE_PATHS",
)

# Get LAS dataset properties
desc = arcpy.Describe("lidar_index.lasd")
print(f"Point count: {desc.pointCount:,}")
print(f"Files: {desc.fileCount}")
print(f"Z range: {desc.ZMin:.2f} to {desc.ZMax:.2f}")
print(f"CRS: {desc.spatialReference.name}")

# LAS dataset statistics
arcpy.management.LasDatasetStatistics(
    in_las_dataset="lidar_index.lasd",
    calculation_type="DATASET_STATS",
    out_file="las_stats.csv",
)
```

### LAS classification and filtering
```python
# LAS point classifications (ASPRS standard):
#   1 = Unassigned     2 = Ground          3 = Low vegetation
#   4 = Medium veg     5 = High veg        6 = Building
#   7 = Low point      9 = Water          17 = Bridge deck

# Classify ground points automatically
arcpy.ddd.ClassifyLasGround(
    in_las_dataset="lidar_index.lasd",
    method="AGGRESSIVE",  # CONSERVATIVE, STANDARD, or AGGRESSIVE
)

# Classify buildings
arcpy.ddd.ClassifyLasBuilding(
    in_las_dataset="lidar_index.lasd",
    min_height="2 Meters",
    min_area="10 SquareMeters",
)

# Classify noise (outliers)
arcpy.ddd.ClassifyLasNoise(
    in_las_dataset="lidar_index.lasd",
    method="RELATIVE_HEIGHT",
    edit_las="CLASSIFY",
    withheld="WITHHELD",
    ground="GROUND",
    low_z="-5 Meters",
    high_z="100 Meters",
    max_neighbors=6,
    step_width="5 Meters",
    step_height="2.5 Meters",
)

# Make layer with specific class filter (ground only)
arcpy.management.MakeLasDatasetLayer(
    in_las_dataset="lidar_index.lasd",
    out_layer="ground_points",
    class_code=[2],  # ground
)
```

### LAS to raster surfaces (DEM / DSM)
```python
# DEM (bare earth) — ground points only (class 2)
arcpy.management.MakeLasDatasetLayer("lidar_index.lasd", "ground_lyr", class_code=[2])
arcpy.conversion.LasDatasetToRaster(
    in_las_dataset="ground_lyr",
    out_raster="dem_lidar.tif",
    value_field="ELEVATION",
    interpolation_type="BINNING AVERAGE LINEAR",
    data_type="FLOAT",
    sampling_type="CELLSIZE",
    sampling_value=1,  # 1m resolution
)

# DSM (includes buildings + vegetation) — first returns
arcpy.management.MakeLasDatasetLayer(
    "lidar_index.lasd", "first_return_lyr",
    class_code=[1, 2, 3, 4, 5, 6],
    return_values=["Last Return"],
)
arcpy.conversion.LasDatasetToRaster(
    in_las_dataset="lidar_index.lasd",
    out_raster="dsm_lidar.tif",
    value_field="ELEVATION",
    interpolation_type="BINNING MAXIMUM LINEAR",
    data_type="FLOAT",
    sampling_type="CELLSIZE",
    sampling_value=1,
)

# CHM (Canopy Height Model) = DSM - DEM
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
chm = Raster("dsm_lidar.tif") - Raster("dem_lidar.tif")
chm = Con(chm < 0, 0, chm)  # no negative heights
chm.save("canopy_height_model.tif")
arcpy.CheckInExtension("Spatial")
```

### TIN (Triangulated Irregular Network)
```python
# Create TIN from points
arcpy.ddd.CreateTin(
    out_tin="terrain_tin",
    spatial_reference=arcpy.SpatialReference(2193),
)
arcpy.ddd.EditTin(
    in_tin="terrain_tin",
    in_features=[
        ["elevation_points", "ELEVATION", "Mass_Points", "<None>"],
        ["boundary_polygon", "<None>", "Hard_Clip", "<None>"],
        ["breaklines", "ELEVATION", "Hard_Line", "<None>"],
    ],
)

# TIN to raster
arcpy.ddd.TinRaster(
    in_tin="terrain_tin",
    out_raster="tin_surface.tif",
    data_type="FLOAT",
    method="LINEAR",
    sample_distance="CELLSIZE 5",
)

# TIN domain (extract boundary polygon)
arcpy.ddd.TinDomain("terrain_tin", "tin_boundary", "POLYGON")

# TIN contours
arcpy.ddd.TinContour("terrain_tin", "tin_contours", interval=10)

# TIN edges and nodes
arcpy.ddd.TinEdge("terrain_tin", "tin_edges", edge_type="DATA")
arcpy.ddd.TinNode("terrain_tin", "tin_nodes")
```

### Visibility analysis
```python
# Viewshed — what's visible from observer points
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension("3D")

viewshed = Viewshed2(
    in_raster="dem.tif",
    in_observer_features="lookout_points",
    out_agl_raster="above_ground_level.tif",
    analysis_type="FREQUENCY",
    observer_height=1.7,  # eye height meters
    target_height=0,
    refractivity_coefficient=0.13,
)
viewshed.save("viewshed_result.tif")

# Line of Sight
arcpy.ddd.LineOfSight(
    in_surface="dem.tif",
    in_line_feature_class="sight_lines",
    out_los_feature_class="los_result",
    out_obstruction_feature_class="los_obstructions",
)

# Skyline — silhouette from an observer
arcpy.ddd.Skyline(
    in_observer_point_features="observer_point",
    out_feature_class="skyline_result",
    in_surface="dem.tif",
    surface_radius="5000 Meters",
)

arcpy.CheckInExtension("3D")
arcpy.CheckInExtension("Spatial")
```

### 3D feature operations
```python
arcpy.CheckOutExtension("3D")

# Interpolate shape — drape 2D features onto a surface
arcpy.ddd.InterpolateShape(
    in_surface="dem.tif",
    in_feature_class="roads_2d",
    out_feature_class="roads_3d",
)

# Add Z information (min/max/mean Z to attributes)
arcpy.ddd.AddZInformation(
    in_feature_class="roads_3d",
    out_property=["Z_MIN", "Z_MAX", "Z_MEAN", "LENGTH_3D"],
)

# Difference 3D — compare two surfaces
arcpy.ddd.Difference3D(
    in_features_minuend="dsm_features",
    in_features_subtrahend="dem_features",
    out_feature_class="volume_diff",
)

# Surface volume — cut/fill between surface and reference plane
arcpy.ddd.SurfaceVolume(
    in_surface="dem.tif",
    out_text_file="volume_report.txt",
    reference_plane="ABOVE",
    base_z=100,
)

# Cut Fill — compare two DEMs (before vs after)
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")
cut_fill = CutFill("dem_before.tif", "dem_after.tif")
cut_fill.save("cut_fill_result.tif")
arcpy.CheckInExtension("Spatial")

arcpy.CheckInExtension("3D")
```

---

## Time-Series & Temporal Analysis

Working with time-enabled data, multidimensional rasters, and temporal patterns.

### Enable time on feature layers
```python
import arcpy
import datetime

# Add a datetime field if not present
arcpy.management.AddField("incidents", "EVENT_DATE", "DATE")

# Parse dates from string field
with arcpy.da.UpdateCursor("incidents", ["DATE_STRING", "EVENT_DATE"]) as cursor:
    for row in cursor:
        try:
            row[1] = datetime.datetime.strptime(row[0], "%m/%d/%Y %H:%M")
        except (ValueError, TypeError):
            row[1] = None
        cursor.updateRow(row)

# Enable time on a layer via CIM
aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.listMaps()[0]
lyr = m.listLayers("incidents")[0]

cim = lyr.getDefinition("V3")
cim.featureTable.timeFields = arcpy.cim.CIMTimeTableDefinition()
cim.featureTable.timeFields.startTimeField = "EVENT_DATE"
cim.featureTable.timeFields.timeValueFormat = "yyyy-MM-dd HH:mm:ss"
lyr.setDefinition(cim)
```

### Temporal aggregation and binning
```python
import arcpy
import datetime
from collections import defaultdict

# Aggregate events by time period (day / week / month / year)
def aggregate_by_period(table, date_field, period="MONTH"):
    counts = defaultdict(int)
    with arcpy.da.SearchCursor(table, [date_field]) as cursor:
        for row in cursor:
            if row[0] is None:
                continue
            dt = row[0]
            if period == "HOUR":
                key = dt.strftime("%Y-%m-%d %H:00")
            elif period == "DAY":
                key = dt.strftime("%Y-%m-%d")
            elif period == "WEEK":
                key = dt.strftime("%Y-W%W")
            elif period == "MONTH":
                key = dt.strftime("%Y-%m")
            elif period == "YEAR":
                key = str(dt.year)
            counts[key] += 1

    for period_key in sorted(counts):
        print(f"  {period_key}: {counts[period_key]} events")
    return dict(counts)

print("Monthly incident counts:")
monthly = aggregate_by_period("incidents", "EVENT_DATE", "MONTH")
```

### Time-sliced analysis (compare periods)
```python
import arcpy
import datetime

# Filter features by time range and run analysis on each slice
def time_slice_analysis(fc, date_field, start, end, interval_days=30):
    results = []
    current = start
    while current < end:
        next_date = current + datetime.timedelta(days=interval_days)
        where = (
            f"{date_field} >= timestamp '{current.strftime('%Y-%m-%d')}' "
            f"AND {date_field} < timestamp '{next_date.strftime('%Y-%m-%d')}'"
        )
        # Select features in this time window
        arcpy.management.MakeFeatureLayer(fc, "time_slice", where)
        count = int(arcpy.management.GetCount("time_slice")[0])

        if count > 0:
            period_name = current.strftime("%Y_%m")
            arcpy.sa.KernelDensity(
                "time_slice", "NONE", cell_size=100, search_radius=500
            ).save(f"density_{period_name}.tif")
            results.append({"period": period_name, "count": count})
            print(f"  {period_name}: {count} events -> density created")

        arcpy.management.Delete("time_slice")
        current = next_date
    return results

time_slice_analysis(
    "crime_incidents", "DATE_OCC",
    datetime.datetime(2024, 1, 1),
    datetime.datetime(2025, 1, 1),
    interval_days=30,
)
```

### Space-Time Cube for pattern mining
```python
import arcpy

# Create Space Time Cube from points
# Aggregates point data into space-time bins for trend analysis
arcpy.stpm.CreateSpaceTimeCube(
    in_features="incidents",
    output_cube="incidents_cube.nc",
    time_field="EVENT_DATE",
    time_step_interval="1 Months",
    distance_interval="500 Meters",
)

# Emerging Hot Spot Analysis — find new, intensifying, or diminishing clusters
arcpy.stpm.EmergingHotSpotAnalysis(
    in_cube="incidents_cube.nc",
    analysis_variable="COUNT",
    output_features="emerging_hotspots",
    neighborhood_distance="1000 Meters",
    neighborhood_time_step=3,
)
# Result categories: New, Consecutive, Intensifying, Persistent,
#   Diminishing, Sporadic, Oscillating, Historical

# Local Outlier Analysis — space-time outliers
arcpy.stpm.LocalOutlierAnalysis(
    in_cube="incidents_cube.nc",
    analysis_variable="COUNT",
    output_features="space_time_outliers",
    neighborhood_distance="1000 Meters",
    neighborhood_time_step=1,
)

# Time Series Clustering — group locations with similar temporal patterns
arcpy.stpm.TimeSeriesClustering(
    in_cube="incidents_cube.nc",
    analysis_variable="COUNT",
    output_features="time_clusters",
    characteristics_of_interest="PROFILES",
    cluster_count=5,
)

# Visualize cube as 2D map
arcpy.stpm.VisualizeSpaceTimeCube2D(
    in_cube="incidents_cube.nc",
    cube_variable="COUNT",
    display_theme="TRENDS",
    output_features="trend_map",
)
```

### Multidimensional raster analysis (NetCDF, HDF, GRIB)
```python
import arcpy
from arcpy.sa import *
from arcpy.ia import *
arcpy.CheckOutExtension("Spatial")

# Create multidimensional raster from NetCDF (climate, ocean, weather data)
arcpy.management.MakeMultidimensionalRasterLayer(
    in_multidimensional_raster="temperature.nc",
    out_multidimensional_raster_layer="temp_layer",
    variables=["air_temperature"],
    dimension_def="BY_RANGES",
    dimension_ranges=[["StdTime", "2020-01-01", "2024-12-31"]],
)

# Aggregate across time dimension (mean temperature per pixel)
arcpy.ia.AggregateMultidimensionalRaster(
    in_multidimensional_raster="temp_layer",
    dimension="StdTime",
    aggregation_method="MEAN",
    aggregation_def="INTERVAL_KEYWORD",
    interval_keyword="YEARLY",
).save("yearly_mean_temp.crf")

# Trend analysis per pixel over time
arcpy.ia.GenerateTrendRaster(
    in_multidimensional_raster="temp_layer",
    dimension="StdTime",
    variables=["air_temperature"],
    trend_line_type="LINEAR",
).save("temperature_trend.crf")

# Anomaly detection (deviation from long-term mean)
arcpy.ia.GenerateMultidimensionalAnomaly(
    in_multidimensional_raster="temp_layer",
    variables=["air_temperature"],
    method="DIFFERENCE_FROM_MEAN",
    calculation_interval="RECURRING_MONTHLY",
).save("temp_anomalies.crf")

arcpy.CheckInExtension("Spatial")
```

### Change detection between two time periods
```python
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")

# Raster change detection (land cover at two dates)
before = Raster("landcover_2020.tif")
after = Raster("landcover_2024.tif")

# Simple difference
change = after - before
change.save("change_raw.tif")

# Classify change types
# Example: land cover codes 1=urban, 2=agriculture, 3=forest, 4=water
change_type = Con(
    (before == 3) & (after == 1), 1,  # forest to urban (deforestation)
    Con(
        (before == 2) & (after == 1), 2,  # agriculture to urban (urbanization)
        Con(
            (before == 1) & (after == 3), 3,  # urban to forest (reforestation)
            0  # no change or other
        )
    )
)
change_type.save("change_classified.tif")

# Vector change detection (compare two polygon layers)
arcpy.analysis.SymDiff(
    "buildings_2020", "buildings_2024", "building_changes"
)
arcpy.management.CalculateField(
    "building_changes", "CHANGE_TYPE",
    "classify(!FID_buildings_2020!, !FID_buildings_2024!)",
    expression_type="PYTHON3",
    code_block="""
def classify(fid_old, fid_new):
    if fid_old == -1: return 'NEW'
    elif fid_new == -1: return 'DEMOLISHED'
    else: return 'MODIFIED'
""",
)

arcpy.CheckInExtension("Spatial")
```

---

## UK Geospatial Data Sources & Patterns

Common UK data sources, coordinate systems, and loading patterns for
environmental, planning, and infrastructure analysis.

### British National Grid (EPSG:27700)

The standard CRS for all UK mapping work. All OS, EA, and Natural England
data uses BNG. Always set this as your project CRS for UK work.

```python
BNG = arcpy.SpatialReference(27700)  # OSGB 1936 / British National Grid
arcpy.env.outputCoordinateSystem = BNG

# If data comes in WGS84 (e.g., from GPS), reproject to BNG
arcpy.management.Project("gps_points", "gps_points_bng", BNG)
```

### UK data source reference

| Data Type | Source | Format | Notes |
|-----------|--------|--------|-------|
| OS Basemaps (1:25k, 1:50k) | Edina Digimap | Raster (TIFF/ECW) | BNG, may need merge if multi-tile |
| OS VectorMap Local | Edina Digimap | Vector (SHP/GML) | Roads, rail, rivers, buildings, woodland |
| OS VectorMap District/Strategi | Edina Digimap | Vector | Coarser scale, wider coverage |
| DTM (elevation) | Edina Digimap (DTM5) | Raster (ASC/TIFF) | 5m cell size, BNG, multi-tile |
| Aerial imagery | Edina Digimap | Raster (TIFF/ECW) | BNG, often multi-tile |
| Flood Warning Areas | data.gov.uk / EA | Vector (SHP/GeoJSON) | EA Flood Map for Planning |
| Flood Alert Areas | data.gov.uk / EA | Vector (SHP/GeoJSON) | Wider flood risk zones |
| Flood Zone 2 & 3 | data.gov.uk / EA | Vector (SHP) | Statutory planning zones |
| Agricultural Land Classification (ALC) | Natural England / MAGIC | Vector (SHP) | Grades 1-5, field = "ALC_GRADE" |
| Priority Habitats Inventory | Natural England / MAGIC | Vector (SHP) | Field = "Main_Habit" |
| SSSI | Natural England / MAGIC | Vector (SHP) | Sites of Special Scientific Interest |
| NNR | Natural England / MAGIC | Vector (SHP) | National Nature Reserves |
| SAC | Natural England / MAGIC | Vector (SHP) | Special Areas of Conservation |
| SPA | Natural England / MAGIC | Vector (SHP) | Special Protection Areas |
| Ancient Woodland | Natural England / MAGIC | Vector (SHP) | Irreplaceable habitat |
| Green Belt | Local authority / data.gov.uk | Vector (SHP) | Varies by council |

### Loading multi-tile Digimap data
```python
import arcpy, os

# Digimap downloads often come as multiple tiles
# Merge them into a single layer before analysis

# Raster tiles (DTM, basemap)
tile_folder = r"C:\Data\Digimap\DTM5"
arcpy.env.workspace = tile_folder
tiles = arcpy.ListRasters("*.asc")  # or *.tif
print(f"Found {len(tiles)} DTM tiles")

# Mosaic all tiles into one raster
arcpy.management.MosaicToNewRaster(
    input_rasters=tiles,
    output_location=r"C:\Projects\analysis.gdb",
    raster_dataset_name_with_extension="dtm_merged",
    coordinate_system_for_the_raster=arcpy.SpatialReference(27700),
    pixel_type="32_BIT_FLOAT",
    number_of_bands=1,
    mosaic_method="MEAN",             # MEAN for elevation overlap areas
)

# Vector tiles (OS VectorMap Local comes as multiple tiles)
vector_folder = r"C:\Data\Digimap\VML"
arcpy.env.workspace = vector_folder

# Merge all road tiles
road_tiles = arcpy.ListFeatureClasses("*Road*")
if road_tiles:
    arcpy.management.Merge(road_tiles, r"C:\Projects\analysis.gdb\roads_all")

# Merge all building tiles
building_tiles = arcpy.ListFeatureClasses("*Building*")
if building_tiles:
    arcpy.management.Merge(building_tiles, r"C:\Projects\analysis.gdb\buildings_all")
```

### Loading EA flood data
```python
# EA Flood Map for Planning — download from data.gov.uk
# Typically comes as shapefile with fields like PROB_4BAND, TYPE, etc.

# Load and inspect
arcpy.env.workspace = r"C:\Data\EA_Flood"
for fc in arcpy.ListFeatureClasses("*flood*"):
    desc = arcpy.Describe(fc)
    count = int(arcpy.management.GetCount(fc)[0])
    fields = [f.name for f in arcpy.ListFields(fc) if f.type not in ("OID", "Geometry")]
    print(f"{fc}: {desc.shapeType} ({count}), fields: {fields}")

# Common EA flood zone field values:
# Flood Zone 2 — "Medium Probability" (0.1-1% annual chance from rivers)
# Flood Zone 3 — "High Probability" (>1% annual chance)
```

### Loading Natural England / MAGIC data
```python
# MAGIC (magic.defra.gov.uk) data — statutory environmental designations
# Download as shapefiles, all in BNG (EPSG:27700)

# Agricultural Land Classification
alc = r"C:\Data\MAGIC\ALC.shp"
print("ALC Grades:", sorted({row[0] for row in
    arcpy.da.SearchCursor(alc, ["ALC_GRADE"]) if row[0]}))
# Typical values: "Grade 1", "Grade 2", "Grade 3a", "Grade 3b", "Grade 4", "Grade 5",
#                 "Non Agricultural", "Urban"

# Priority Habitats
habitats = r"C:\Data\MAGIC\Priority_Habitats.shp"
print("Habitat types:", sorted({row[0] for row in
    arcpy.da.SearchCursor(habitats, ["Main_Habit"]) if row[0]}))

# Designated sites — load and merge all into one constraints layer
designations = ["SSSI.shp", "NNR.shp", "SAC.shp", "SPA.shp", "Ancient_Woodland.shp"]
for shp in designations:
    path = os.path.join(r"C:\Data\MAGIC", shp)
    if arcpy.Exists(path):
        count = int(arcpy.management.GetCount(path)[0])
        print(f"  {shp}: {count} features")
```

---

## Multi-Criteria Site Suitability Analysis (UK) — Complete Workflow

End-to-end workflow for binary suitability analysis using UK data.
Follows the 12-step process: setup → create study area → add data →
merge → clip → buffer → slope → polygon-to-raster → reclassify →
raster calculator → identify patches → map production.

### Step 1: Setup project, CRS, geodatabase
```python
import arcpy
import os
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

# British National Grid for all UK work
BNG = arcpy.SpatialReference(27700)
arcpy.env.outputCoordinateSystem = BNG

# Create project geodatabase
PROJECT_DIR = r"C:\Projects\SiteSuitability"
GDB = os.path.join(PROJECT_DIR, "analysis.gdb")

if not os.path.exists(PROJECT_DIR):
    os.makedirs(PROJECT_DIR)
if not arcpy.Exists(GDB):
    arcpy.management.CreateFileGDB(PROJECT_DIR, "analysis.gdb")

arcpy.env.workspace = GDB

# Cell size for all raster operations (5m matches DTM5)
CELL_SIZE = 5
arcpy.env.cellSize = CELL_SIZE

print(f"Project: {PROJECT_DIR}")
print(f"GDB: {GDB}")
print(f"CRS: {BNG.name}")
print(f"Cell size: {CELL_SIZE}m")
```

### Step 2: Create study area polygon
```python
# Option A: Create from coordinates (BNG easting/northing)
study_coords = arcpy.Array([
    arcpy.Point(400000, 300000),
    arcpy.Point(400000, 310000),
    arcpy.Point(410000, 310000),
    arcpy.Point(410000, 300000),
    arcpy.Point(400000, 300000),  # close the polygon
])
study_polygon = arcpy.Polygon(study_coords, BNG)
arcpy.management.CreateFeatureclass(GDB, "study_area", "POLYGON", spatial_reference=BNG)
with arcpy.da.InsertCursor("study_area", ["SHAPE@"]) as cursor:
    cursor.insertRow([study_polygon])

# Option B: If you have an existing boundary shapefile
# arcpy.management.CopyFeatures(r"C:\Data\my_boundary.shp", "study_area")

# Set the study area as the processing extent for ALL subsequent operations
arcpy.env.extent = "study_area"
arcpy.env.mask = "study_area"

print(f"Study area created: {int(arcpy.management.GetCount('study_area')[0])} feature(s)")
desc = arcpy.Describe("study_area")
ext = desc.extent
print(f"Extent: {ext.XMin:.0f}, {ext.YMin:.0f} to {ext.XMax:.0f}, {ext.YMax:.0f}")
```

### Step 3: Add all required datasets
```python
# Load all datasets into the geodatabase
datasets = {
    # Vector data
    "roads": r"C:\Data\Digimap\VML\Roads.shp",
    "rail": r"C:\Data\Digimap\VML\Rail.shp",
    "rivers": r"C:\Data\Digimap\VML\Rivers.shp",
    "urban_areas": r"C:\Data\Digimap\VML\Urban.shp",
    "woodland": r"C:\Data\Digimap\VML\Woodland.shp",
    "flood_zone_2": r"C:\Data\EA\Flood_Zone_2.shp",
    "flood_zone_3": r"C:\Data\EA\Flood_Zone_3.shp",
    "flood_warning": r"C:\Data\EA\Flood_Warning_Areas.shp",
    "alc": r"C:\Data\MAGIC\ALC.shp",
    "priority_habitats": r"C:\Data\MAGIC\Priority_Habitats.shp",
    "sssi": r"C:\Data\MAGIC\SSSI.shp",
    "nnr": r"C:\Data\MAGIC\NNR.shp",
    "sac": r"C:\Data\MAGIC\SAC.shp",
    "spa": r"C:\Data\MAGIC\SPA.shp",
}

for name, path in datasets.items():
    if arcpy.Exists(path):
        arcpy.management.CopyFeatures(path, os.path.join(GDB, name))
        count = int(arcpy.management.GetCount(name)[0])
        print(f"  Loaded {name}: {count} features")
    else:
        print(f"  WARNING: {name} not found at {path}")

# Raster data
raster_datasets = {
    "dtm": r"C:\Data\Digimap\DTM5",  # folder of tiles
    "basemap_25k": r"C:\Data\Digimap\Raster\25k",
    "aerial": r"C:\Data\Digimap\Aerial",
}
# DTM tiles — mosaic into one
arcpy.env.workspace = raster_datasets["dtm"]
dtm_tiles = arcpy.ListRasters("*.asc") or arcpy.ListRasters("*.tif")
if dtm_tiles:
    arcpy.management.MosaicToNewRaster(
        dtm_tiles, GDB, "dtm_raw",
        coordinate_system_for_the_raster=BNG,
        pixel_type="32_BIT_FLOAT", number_of_bands=1,
    )
    print(f"  DTM mosaic: {len(dtm_tiles)} tiles merged")
arcpy.env.workspace = GDB
```

### Step 4: Merge multi-tile datasets (same type)
```python
# If vector data came as multiple tiles, merge them
# Example: OS VectorMap Local delivers roads as separate tiles per grid square
arcpy.env.workspace = r"C:\Data\Digimap\VML"
road_tiles = arcpy.ListFeatureClasses("*Road*")
if len(road_tiles) > 1:
    arcpy.management.Merge(road_tiles, os.path.join(GDB, "roads"))
    print(f"Merged {len(road_tiles)} road tiles")

# Merge all designated sites into one constraints layer
arcpy.env.workspace = GDB
designated = [ds for ds in ["sssi", "nnr", "sac", "spa"] if arcpy.Exists(ds)]
if designated:
    arcpy.management.Merge(designated, "designated_sites")
    print(f"Merged {len(designated)} designation layers into 'designated_sites'")
```

### Step 5: Clip all layers to study area
```python
arcpy.env.workspace = GDB

# Clip all vector layers
vector_layers = [
    "roads", "rail", "rivers", "urban_areas", "woodland",
    "flood_zone_2", "flood_zone_3", "flood_warning",
    "alc", "priority_habitats", "designated_sites",
]
for layer in vector_layers:
    if arcpy.Exists(layer):
        out_name = f"{layer}_clip"
        arcpy.analysis.Clip(layer, "study_area", out_name)
        count = int(arcpy.management.GetCount(out_name)[0])
        print(f"  Clipped {layer}: {count} features")

# Clip raster (DTM) to study area
arcpy.management.Clip(
    in_raster="dtm_raw",
    out_raster="dtm_clip",
    in_template_dataset="study_area",
    clipping_geometry="ClippingGeometry",
)
print("  Clipped DTM to study area")
```

### Step 6: Buffer relevant layers (with different distances)
```python
# ⚠ CRITICAL: Different buffer distances for different road classes
# Need to SELECT by attribute FIRST, then buffer separately

# Split roads by class — motorways get 50m, other roads get 25m
arcpy.management.MakeFeatureLayer("roads_clip", "motorways_lyr",
    "CLASSIFICA = 'Motorway' OR CLASSIFICA = 'A Road'")
arcpy.management.MakeFeatureLayer("roads_clip", "other_roads_lyr",
    "CLASSIFICA <> 'Motorway' AND CLASSIFICA <> 'A Road'")

arcpy.analysis.Buffer("motorways_lyr", "motorways_buffer",
    "50 Meters", dissolve_option="ALL")
arcpy.analysis.Buffer("other_roads_lyr", "other_roads_buffer",
    "25 Meters", dissolve_option="ALL")

# Merge all road buffers
arcpy.management.Merge(
    ["motorways_buffer", "other_roads_buffer"], "roads_buffer_all"
)

# Other buffers — all with dissolve ALL
buffer_config = {
    "rail_clip": ("rail_buffer", "25 Meters"),
    "rivers_clip": ("rivers_buffer", "50 Meters"),
    "woodland_clip": ("woodland_buffer", "50 Meters"),
}
for input_layer, (output, distance) in buffer_config.items():
    if arcpy.Exists(input_layer):
        arcpy.analysis.Buffer(input_layer, output, distance, dissolve_option="ALL")
        print(f"  Buffered {input_layer} -> {output} ({distance})")

# Clean up temporary layers
for lyr in ["motorways_lyr", "other_roads_lyr"]:
    arcpy.management.Delete(lyr)
```

### Step 7: Generate slope from DTM
```python
# Slope in degrees (for suitability: steep slopes = unsuitable)
slope = Slope("dtm_clip", output_measurement="DEGREE")
slope.save("slope_degrees")
print(f"Slope range: {slope.minimum:.1f} to {slope.maximum:.1f} degrees")
```

### Step 8: Convert all vector layers to raster (cell size 5m)
```python
# ⚠ CRITICAL GOTCHA: Set extent AND snap raster for EVERY PolygonToRaster call
# If extent is not set to the study area, rasters won't align and
# Raster Calculator will fail with "ERROR 000864: Extent does not match"

# Use the DTM as snap raster to ensure perfect grid alignment
arcpy.env.snapRaster = "dtm_clip"
arcpy.env.extent = "study_area"
arcpy.env.cellSize = CELL_SIZE  # 5m

# Layers to rasterize — each needs a value field
# For presence/absence layers (buffer outputs), add a constant field first
presence_layers = [
    "roads_buffer_all", "rail_buffer", "rivers_buffer", "woodland_buffer",
    "flood_zone_2_clip", "flood_zone_3_clip", "designated_sites_clip",
    "priority_habitats_clip", "urban_areas_clip",
]

for layer in presence_layers:
    if not arcpy.Exists(layer):
        print(f"  SKIP (not found): {layer}")
        continue

    # Add a constant value field = 1 (presence)
    if not any(f.name == "PRESENCE" for f in arcpy.ListFields(layer)):
        arcpy.management.AddField(layer, "PRESENCE", "SHORT")
    arcpy.management.CalculateField(layer, "PRESENCE", "1", "PYTHON3")

    out_raster = f"{layer}_raster"
    with arcpy.EnvManager(extent="study_area", cellSize=CELL_SIZE, snapRaster="dtm_clip"):
        arcpy.conversion.PolygonToRaster(
            in_features=layer,
            value_field="PRESENCE",
            out_rasterdataset=out_raster,
            cell_assignment="CELL_CENTER",
            cellsize=CELL_SIZE,
        )
    print(f"  Rasterized {layer} -> {out_raster}")

# ALC needs its grade field, not a constant
if arcpy.Exists("alc_clip"):
    with arcpy.EnvManager(extent="study_area", cellSize=CELL_SIZE, snapRaster="dtm_clip"):
        arcpy.conversion.PolygonToRaster(
            "alc_clip", "ALC_GRADE", "alc_raster",
            cell_assignment="CELL_CENTER", cellsize=CELL_SIZE,
        )
    print("  Rasterized ALC by grade")
```

### Step 9: Reclassify each raster to binary (1 = suitable, 0 = unsuitable)
```python
# ⚠ CRITICAL GOTCHA: NODATA handling
# Where a constraint dataset has NO features (e.g., no flood zone in an area),
# PolygonToRaster produces ALL NODATA. This must be reclassified to 1 (suitable)
# because absence of a constraint = suitable.

# Helper: reclassify presence raster to exclusion raster
# presence=1 → 0 (unsuitable), NODATA → 1 (suitable, no constraint present)
def reclassify_exclusion(in_raster, out_raster, label):
    """Where feature IS present = unsuitable (0), elsewhere = suitable (1)."""
    if not arcpy.Exists(in_raster):
        print(f"  SKIP {label}: {in_raster} not found")
        return None
    r = Raster(in_raster)
    # Con(condition, true_value, false_value)
    # IsNull checks for NODATA cells — these are SUITABLE (no constraint)
    result = Con(IsNull(r), 1, 0)
    result.save(out_raster)
    print(f"  Reclassified {label}: presence=0, absence=1")
    return out_raster

# Exclusion criteria — where features exist = UNSUITABLE
exclusion_rasters = {}
exclusion_rasters["roads"] = reclassify_exclusion(
    "roads_buffer_all_raster", "reclass_roads", "Road buffers")
exclusion_rasters["rail"] = reclassify_exclusion(
    "rail_buffer_raster", "reclass_rail", "Rail buffers")
exclusion_rasters["rivers"] = reclassify_exclusion(
    "rivers_buffer_raster", "reclass_rivers", "River buffers")
exclusion_rasters["flood_z3"] = reclassify_exclusion(
    "flood_zone_3_clip_raster", "reclass_flood3", "Flood Zone 3")
exclusion_rasters["designated"] = reclassify_exclusion(
    "designated_sites_clip_raster", "reclass_designated", "Designated sites")
exclusion_rasters["urban"] = reclassify_exclusion(
    "urban_areas_clip_raster", "reclass_urban", "Urban areas")
exclusion_rasters["habitats"] = reclassify_exclusion(
    "priority_habitats_clip_raster", "reclass_habitats", "Priority habitats")

# Slope reclassification — suitable if slope < 15 degrees
slope_reclass = Con(Raster("slope_degrees") <= 15, 1, 0)
slope_reclass.save("reclass_slope")
exclusion_rasters["slope"] = "reclass_slope"
print("  Reclassified slope: <=15deg=1, >15deg=0")

# ALC reclassification — protect best agricultural land (Grades 1, 2, 3a)
# Grade 1/2/3a = unsuitable (protected), Grade 3b/4/5/Non-Ag = suitable
if arcpy.Exists("alc_raster"):
    alc_r = Raster("alc_raster")
    alc_reclass = Reclassify(alc_r, "VALUE", RemapValue([
        ["Grade 1", 0], ["Grade 2", 0], ["Grade 3a", 0],   # protected
        ["Grade 3b", 1], ["Grade 4", 1], ["Grade 5", 1],    # suitable
        ["Non Agricultural", 1], ["Urban", 1],
    ]), missing_values="DATA")
    # Handle NODATA — if no ALC data, assume suitable
    alc_final = Con(IsNull(alc_reclass), 1, alc_reclass)
    alc_final.save("reclass_alc")
    exclusion_rasters["alc"] = "reclass_alc"
    print("  Reclassified ALC: Grade 1/2/3a=0, others=1")

# Remove None entries (layers that were skipped)
exclusion_rasters = {k: v for k, v in exclusion_rasters.items() if v is not None}
print(f"\n{len(exclusion_rasters)} reclassified layers ready for combination")
```

### Step 10: Raster Calculator — multiply all reclassified layers
```python
# Multiply all binary layers: 1 * 1 * 1 = 1 (suitable everywhere)
# Any 0 makes the cell 0 (unsuitable)
raster_list = list(exclusion_rasters.values())

# Start with the first raster, multiply each subsequent one
combined = Raster(raster_list[0])
for raster_path in raster_list[1:]:
    combined = combined * Raster(raster_path)

combined.save("suitability_result")
print("Suitability combination complete")

# Verify: count suitable vs unsuitable cells
suitable_count = 0
unsuitable_count = 0
with arcpy.da.SearchCursor("suitability_result", ["VALUE", "COUNT"]) as cursor:
    for value, count in cursor:
        if value == 1:
            suitable_count = count
        else:
            unsuitable_count = count
total = suitable_count + unsuitable_count
if total > 0:
    pct = (suitable_count / total) * 100
    print(f"Suitable: {suitable_count:,} cells ({pct:.1f}%)")
    print(f"Unsuitable: {unsuitable_count:,} cells ({100-pct:.1f}%)")
    area_ha = suitable_count * CELL_SIZE * CELL_SIZE / 10000
    print(f"Suitable area: {area_ha:.1f} hectares")
```

### Step 11: Identify suitable patches of sufficient area
```python
# Convert binary suitability raster to polygons
arcpy.conversion.RasterToPolygon(
    "suitability_result", "suitability_polygons", "SIMPLIFY", "VALUE"
)

# Keep only suitable polygons (gridcode = 1)
arcpy.management.MakeFeatureLayer(
    "suitability_polygons", "suitable_lyr", "gridcode = 1"
)
arcpy.management.CopyFeatures("suitable_lyr", "suitable_patches")

# Calculate area for each patch
arcpy.management.CalculateGeometryAttributes(
    "suitable_patches",
    [["AREA_HA", "AREA"], ["PERIMETER_M", "PERIMETER_LENGTH"]],
    area_unit="HECTARES",
    length_unit="METERS",
)

# Filter by minimum area (e.g., patches > 1 hectare)
MIN_AREA_HA = 1.0
arcpy.management.MakeFeatureLayer(
    "suitable_patches", "large_patches_lyr", f"AREA_HA >= {MIN_AREA_HA}"
)
arcpy.management.CopyFeatures("large_patches_lyr", "suitable_patches_final")

count = int(arcpy.management.GetCount("suitable_patches_final")[0])
print(f"Suitable patches >= {MIN_AREA_HA} ha: {count}")

# Summary statistics
with arcpy.da.SearchCursor("suitable_patches_final", ["AREA_HA"]) as cursor:
    areas = sorted([row[0] for row in cursor], reverse=True)
print(f"Largest: {areas[0]:.2f} ha")
print(f"Smallest: {areas[-1]:.2f} ha")
print(f"Total suitable area: {sum(areas):.2f} ha")

# Clean up temporary layers
for lyr in ["suitable_lyr", "large_patches_lyr"]:
    arcpy.management.Delete(lyr)
```

### Step 12: Design and export 3 maps at 300dpi JPEG
```python
aprx = arcpy.mp.ArcGISProject("CURRENT")  # or path to .aprx

# === MAP 1: Overview with study area + basemap ===
layout1 = aprx.createLayout(29.7, 21, "CENTIMETER", "Map 1 - Overview")
map1 = aprx.listMaps("Map")[0]

# Add basemap and study area layers
mf1 = layout1.createMapFrame(
    arcpy.Extent(1, 3, 27, 19), map1, "Overview Frame"
)
mf1.camera.setExtent(arcpy.Describe("study_area").extent)

# Add map elements
layout1.createMapSurroundElement(arcpy.Point(14.85, 20.5), "TEXT", "Title1")
layout1.createMapSurroundElement(arcpy.Point(5, 1.5), "SCALE_BAR", "SB1", mf1)
layout1.createMapSurroundElement(arcpy.Point(2, 17), "NORTH_ARROW", "NA1", mf1)
layout1.createMapSurroundElement(arcpy.Point(23, 10), "LEGEND", "Leg1", mf1)

layout1.exportToJPEG(
    os.path.join(PROJECT_DIR, "Map1_Overview.jpg"),
    resolution=300, jpeg_quality=95,
)

# === MAP 2: Constraint layers + reclassification ===
layout2 = aprx.createLayout(29.7, 21, "CENTIMETER", "Map 2 - Constraints")
# ... similar setup with constraint layers visible ...
layout2.exportToJPEG(
    os.path.join(PROJECT_DIR, "Map2_Constraints.jpg"),
    resolution=300, jpeg_quality=95,
)

# === MAP 3: Final suitability result (two detail maps side-by-side) ===
layout3 = aprx.createLayout(29.7, 21, "CENTIMETER", "Map 3 - Suitability")

# Left: full suitability raster with binary symbology
left_frame = layout3.createMapFrame(
    arcpy.Extent(1, 3, 14, 19), map1, "Suitability Full"
)

# Right: zoomed detail of best patches
right_frame = layout3.createMapFrame(
    arcpy.Extent(15, 3, 28, 19), map1, "Suitability Detail"
)
# Zoom to the largest suitable patch
with arcpy.da.SearchCursor(
    "suitable_patches_final", ["SHAPE@"], sql_clause=(None, "ORDER BY AREA_HA DESC")
) as cursor:
    largest = next(cursor)[0]
    right_frame.camera.setExtent(largest.extent)
    right_frame.camera.scale *= 1.2  # add 20% padding

layout3.exportToJPEG(
    os.path.join(PROJECT_DIR, "Map3_Suitability.jpg"),
    resolution=300, jpeg_quality=95,
)

print("All 3 maps exported at 300 dpi")
arcpy.CheckInExtension("Spatial")
```

---

## Suitability Analysis — Critical Gotchas

These mistakes cause the most failures in multi-criteria suitability analysis.
Build these checks into EVERY suitability workflow.

### 1. Extent must be set on EVERY PolygonToRaster conversion
```python
# ❌ WRONG — rasters will have different extents, Raster Calculator fails
arcpy.conversion.PolygonToRaster("flood_zones", "RISK", "flood_raster", cellsize=5)
arcpy.conversion.PolygonToRaster("woodland", "PRESENCE", "wood_raster", cellsize=5)
# ERROR: "The extent of the rasters do not match"

# ✅ CORRECT — always set extent, cellSize, and snapRaster
with arcpy.EnvManager(extent="study_area", cellSize=5, snapRaster="dtm_clip"):
    arcpy.conversion.PolygonToRaster("flood_zones", "RISK", "flood_raster", cellsize=5)
    arcpy.conversion.PolygonToRaster("woodland", "PRESENCE", "wood_raster", cellsize=5)
```

### 2. NODATA handling in Reclassify — the silent killer
```python
# ❌ WRONG — areas with no flood zone become NODATA, which propagates
# through multiplication and makes the ENTIRE area unsuitable
flood_reclass = Reclassify(flood_raster, "VALUE", RemapValue([[1, 0]]))
# Cells where there are NO flood zones → NODATA → kills the result

# ✅ CORRECT — explicitly set NODATA to 1 (suitable = no constraint present)
flood_reclass = Con(IsNull(flood_raster), 1, 0)  # NODATA→1, presence→0
# OR use Con(IsNull(Reclassify(...)), 1, Reclassify(...))
```

### 3. Cell size consistency — all rasters must match
```python
# ❌ WRONG — mixing cell sizes causes silent resampling or errors
arcpy.conversion.PolygonToRaster("roads", "PRESENCE", "roads_r", cellsize=5)
arcpy.conversion.PolygonToRaster("flood", "PRESENCE", "flood_r", cellsize=10)
# Raster Calculator will resample one → inaccurate results

# ✅ CORRECT — set cell size globally and use snap raster
CELL_SIZE = 5
arcpy.env.cellSize = CELL_SIZE
arcpy.env.snapRaster = "dtm_clip"  # ensures grid cells align perfectly
```

### 4. Selective buffering — different distances for different feature types
```python
# ❌ WRONG — buffering all roads the same distance
arcpy.analysis.Buffer("roads", "roads_buffer", "25 Meters")
# Motorways should be 50m, minor roads 25m

# ✅ CORRECT — select by attribute first, buffer separately, then merge
arcpy.management.MakeFeatureLayer("roads", "motorways",
    "ROAD_CLASS IN ('Motorway', 'A Road')")
arcpy.management.MakeFeatureLayer("roads", "minor_roads",
    "ROAD_CLASS NOT IN ('Motorway', 'A Road')")
arcpy.analysis.Buffer("motorways", "motorway_buffer", "50 Meters", dissolve_option="ALL")
arcpy.analysis.Buffer("minor_roads", "minor_buffer", "25 Meters", dissolve_option="ALL")
arcpy.management.Merge(["motorway_buffer", "minor_buffer"], "roads_buffer_combined")
```

### 5. Buffer dissolve option — always dissolve
```python
# ❌ WRONG — individual buffer rings overlap, counts as separate features
arcpy.analysis.Buffer("rivers", "river_buffer", "50 Meters")
# Result: overlapping buffer polygons that double-count in rasterization

# ✅ CORRECT — dissolve all into single feature
arcpy.analysis.Buffer("rivers", "river_buffer", "50 Meters", dissolve_option="ALL")
# Result: single merged polygon, no overlaps
```

### 6. Verify raster alignment before combining
```python
# Always check that all rasters share the same properties before Raster Calculator
def check_raster_alignment(raster_names):
    """Verify all rasters have matching extent, cell size, and CRS."""
    issues = []
    ref = arcpy.Describe(raster_names[0])
    ref_ext = ref.extent
    ref_cell = round(ref.meanCellWidth, 4)
    ref_crs = ref.spatialReference.factoryCode

    for name in raster_names[1:]:
        desc = arcpy.Describe(name)
        cell = round(desc.meanCellWidth, 4)
        crs = desc.spatialReference.factoryCode
        ext = desc.extent

        if cell != ref_cell:
            issues.append(f"{name}: cell size {cell} != {ref_cell}")
        if crs != ref_crs:
            issues.append(f"{name}: CRS {crs} != {ref_crs}")
        if abs(ext.XMin - ref_ext.XMin) > ref_cell:
            issues.append(f"{name}: extent mismatch (XMin off by {ext.XMin - ref_ext.XMin:.1f})")

    if issues:
        print("⚠ ALIGNMENT ISSUES:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✓ All rasters aligned")
        return True

check_raster_alignment(list(exclusion_rasters.values()))
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
