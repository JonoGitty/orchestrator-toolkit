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

# ──────────────────────────────────────────────────────────────────
# SMART DATASET SELECTION — only load what the brief actually needs
# ──────────────────────────────────────────────────────────────────

def select_datasets_for_brief(brief_text, scanned_data):
    """Analyse a brief and return ONLY the datasets needed — not everything.

    Reads the brief text, identifies which analysis types are required,
    and filters the scanned data down to what's actually relevant.
    Returns a ranked list: essential, optional, and not-needed.

    brief_text:   the actual text of the assignment brief
    scanned_data: output from scan_for_gis_data()
    """
    # --- 1. Detect what analysis the brief is asking for ---
    brief_lower = brief_text.lower()

    analysis_types = {
        "suitability": any(kw in brief_lower for kw in [
            "suitability", "suitable", "site selection", "constraint",
            "exclusion", "criteria", "multi-criteria",
        ]),
        "flood_risk": any(kw in brief_lower for kw in [
            "flood", "inundation", "fluvial", "pluvial", "flood zone",
        ]),
        "slope_terrain": any(kw in brief_lower for kw in [
            "slope", "terrain", "elevation", "gradient", "dtm", "dem",
            "topograph", "steep",
        ]),
        "transport_access": any(kw in brief_lower for kw in [
            "road", "rail", "transport", "access", "highway", "network",
            "route", "travel time",
        ]),
        "ecology": any(kw in brief_lower for kw in [
            "habitat", "sssi", "sac", "spa", "ecology", "biodiversity",
            "wildlife", "protected", "priority habitat", "natura 2000",
        ]),
        "agriculture": any(kw in brief_lower for kw in [
            "agricultural", "alc", "farmland", "grade 1", "grade 2",
            "best and most versatile", "bvm",
        ]),
        "urban_settlement": any(kw in brief_lower for kw in [
            "urban", "built-up", "settlement", "building", "residential",
        ]),
        "hydrology": any(kw in brief_lower for kw in [
            "river", "watercourse", "catchment", "watershed", "stream",
            "drainage", "water body",
        ]),
        "woodland": any(kw in brief_lower for kw in [
            "woodland", "forest", "tree", "ancient woodland",
        ]),
        "heritage": any(kw in brief_lower for kw in [
            "heritage", "listed building", "scheduled monument",
            "conservation area", "historic",
        ]),
    }

    active = {k for k, v in analysis_types.items() if v}
    print(f"Brief analysis types detected: {', '.join(active) if active else 'NONE — ask user'}")

    # --- 2. Map analysis types to required datasets ---
    DATASET_REQUIREMENTS = {
        "suitability":       ["study_area", "roads", "urban_areas"],
        "flood_risk":        ["flood_zone_2", "flood_zone_3"],
        "slope_terrain":     ["dtm"],
        "transport_access":  ["roads", "rail"],
        "ecology":           ["priority_habitats", "sssi", "sac", "spa"],
        "agriculture":       ["alc"],
        "urban_settlement":  ["urban_areas"],
        "hydrology":         ["rivers"],
        "woodland":          ["woodland"],
        "heritage":          ["heritage_sites"],
    }

    essential_names = set()
    for atype in active:
        for ds in DATASET_REQUIREMENTS.get(atype, []):
            essential_names.add(ds)

    # Study area is always essential
    essential_names.add("study_area")

    # --- 3. Match essential datasets to scanned files ---
    all_files = []
    for category in scanned_data.values():
        all_files.extend(category)

    DATASET_KEYWORDS = {
        "study_area":        ["study_area", "boundary", "site_boundary", "aoi"],
        "roads":             ["road", "highway", "street", "motorway"],
        "rail":              ["rail", "railway", "train"],
        "rivers":            ["river", "water", "stream", "surfacewater"],
        "urban_areas":       ["urban", "building", "builtup", "settlement"],
        "woodland":          ["woodland", "forest", "wood"],
        "dtm":               ["dtm", "dem", "elevation", "terrain"],
        "flood_zone_2":      ["flood_zone_2", "floodzone2", "fz2"],
        "flood_zone_3":      ["flood_zone_3", "floodzone3", "fz3"],
        "alc":               ["alc", "agricultural", "agri_land"],
        "priority_habitats": ["habitat", "priority_habitat", "phi"],
        "sssi":              ["sssi"],
        "sac":               ["sac"],
        "spa":               ["spa"],
        "heritage_sites":    ["heritage", "listed", "scheduled"],
    }

    essential = []    # datasets the brief definitely needs
    optional = []     # datasets found but not required by brief
    not_found = []    # datasets needed but not found on disk

    matched_files = set()

    for ds_name in essential_names:
        keywords = DATASET_KEYWORDS.get(ds_name, [ds_name])
        found = None
        for f in all_files:
            fname = f["name"].lower()
            if any(kw in fname for kw in keywords):
                found = f
                matched_files.add(f["name"])
                break
        if found:
            essential.append({"dataset": ds_name, "file": found, "status": "ESSENTIAL"})
        else:
            not_found.append({"dataset": ds_name, "status": "NEEDED BUT MISSING"})

    # Everything else is optional (found but not required by brief)
    for f in all_files:
        if f["name"] not in matched_files:
            optional.append({"dataset": f["name"], "file": f, "status": "OPTIONAL"})

    # --- 4. Print clear report ---
    print(f"\n{'='*70}")
    print(f"DATASET SELECTION FOR BRIEF")
    print(f"{'='*70}\n")

    print(f"ESSENTIAL ({len(essential)} datasets — load these):")
    for item in essential:
        print(f"  ✓ {item['dataset']:<25} → {item['file']['name']}")

    if not_found:
        print(f"\nMISSING ({len(not_found)} — need to download):")
        for item in not_found:
            print(f"  ✗ {item['dataset']:<25} NOT FOUND on disk")

    if optional:
        print(f"\nOPTIONAL ({len(optional)} — found but NOT needed by this brief):")
        for item in optional:
            print(f"  - {item['file']['name']}")

    print(f"\n→ Loading {len(essential)} of {len(all_files)} available datasets")
    if optional:
        print(f"  Skipping {len(optional)} datasets not relevant to this brief")

    return {
        "essential": essential,
        "optional": optional,
        "not_found": not_found,
        "analysis_types": active,
    }

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

#### Consistent colour schemes across multiple maps
```python
# When producing multiple maps (e.g., 3 maps for a suitability report),
# symbology must be consistent — same colours, same classification, same legend.

# Strategy 1: Save symbology as .lyrx, apply to all maps
# Set up symbology once on a layer, then save as a template:
lyr = map_obj.listLayers("land_use")[0]
# ... configure symbology on lyr (UniqueValueRenderer, colors, etc.) ...
lyr.saveACopy(r"C:\Templates\land_use_symbology.lyrx")

# Apply same symbology to the same layer in other maps:
for map_name in ["Map 1 - Overview", "Map 2 - Constraints", "Map 3 - Result"]:
    m = aprx.listMaps(map_name)[0]
    target_lyr = m.listLayers("land_use")[0]
    arcpy.management.ApplySymbologyFromLayer(
        in_layer=target_lyr,
        in_symbology_layer=r"C:\Templates\land_use_symbology.lyrx",
        symbology_fields=[["VALUE_FIELD", "LU_CODE", "LU_CODE"]],
    )

# Strategy 2: Configure symbology programmatically with identical settings
# Define colors once, apply to every map:
SUITABILITY_COLORS = {
    0: {"RGB": [255, 80, 80, 100]},   # red = unsuitable
    1: {"RGB": [80, 200, 80, 100]},   # green = suitable
}

for map_name in ["Map 1 - Overview", "Map 2 - Constraints", "Map 3 - Result"]:
    m = aprx.listMaps(map_name)[0]
    for lyr in m.listLayers():
        if lyr.name == "suitability_result":
            cim = lyr.getDefinition("V3")
            for group in cim.colorizer.groups:
                for cls in group.classes:
                    val = int(cls.values[0])
                    if val in SUITABILITY_COLORS:
                        cls.symbol.symbol.color = SUITABILITY_COLORS[val]
            lyr.setDefinition(cim)

# Strategy 3: Share a single layer across map frames
# If multiple map frames on one layout show the SAME map, they automatically
# share symbology. Only use separate maps when you need different visible layers.
```

#### Automatic Symbology Selection — Choose the Right Look for Each Dataset

Do NOT apply the same renderer to everything. The correct symbology depends on
(a) the geometry type, (b) whether the data is categorical or continuous, and
(c) what the data represents semantically. This engine selects automatically.

```python
# ──────────────────────────────────────────────────────────────────
# COLOUR PALETTE LIBRARY — semantically correct colours for GIS data
# ──────────────────────────────────────────────────────────────────

GIS_COLOUR_PALETTES = {
    # --- Suitability / binary ---
    "suitable_unsuitable": {
        1: {"RGB": [56, 168, 0, 100],   "label": "Suitable"},       # dark green
        0: {"RGB": [255, 85, 85, 100],  "label": "Unsuitable"},     # red
    },

    # --- Constraint layers (single-colour fills with meaning) ---
    "flood_zone":       {"fill": [100, 150, 255, 60],  "outline": [40, 80, 200, 100]},   # translucent blue
    "flood_zone_3":     {"fill": [0, 77, 168, 70],     "outline": [0, 38, 115, 100]},    # darker blue
    "rivers":           {"line": [0, 112, 255, 100],    "width": 1.5},                    # bright blue line
    "roads_major":      {"line": [168, 0, 0, 100],      "width": 2.0},                    # dark red line
    "roads_minor":      {"line": [168, 112, 0, 100],    "width": 1.0},                    # brown line
    "rail":             {"line": [78, 78, 78, 100],      "width": 1.5, "dash": True},     # grey dashed
    "urban":            {"fill": [204, 204, 204, 80],   "outline": [130, 130, 130, 100]}, # grey
    "woodland":         {"fill": [56, 168, 0, 60],      "outline": [38, 115, 0, 100]},    # green
    "habitat":          {"fill": [76, 230, 0, 50],      "outline": [56, 168, 0, 100]},    # bright green
    "sssi":             {"fill": [255, 170, 0, 50],     "outline": [230, 152, 0, 100]},   # orange
    "sac":              {"fill": [170, 102, 205, 50],   "outline": [132, 0, 168, 100]},   # purple
    "spa":              {"fill": [255, 0, 197, 40],     "outline": [168, 0, 132, 100]},   # pink
    "alc_grade1":       {"fill": [168, 112, 0, 100],    "label": "Grade 1 (Excellent)"},  # dark brown
    "alc_grade2":       {"fill": [205, 170, 102, 100],  "label": "Grade 2 (Very Good)"},  # light brown
    "alc_grade3a":      {"fill": [255, 211, 127, 100],  "label": "Grade 3a (Good)"},      # gold
    "alc_grade3b":      {"fill": [255, 255, 190, 100],  "label": "Grade 3b (Moderate)"},  # pale yellow
    "alc_grade4":       {"fill": [233, 255, 190, 100],  "label": "Grade 4 (Poor)"},       # pale green
    "alc_grade5":       {"fill": [204, 204, 204, 100],  "label": "Grade 5 (Very Poor)"},  # grey

    # --- Buffers (always show as hatched or semi-transparent) ---
    "buffer":           {"fill": [255, 170, 0, 30],     "outline": [255, 85, 0, 100]},    # orange translucent

    # --- Study area boundary (no fill, just outline) ---
    "study_area":       {"fill": None,                   "outline": [0, 0, 0, 100], "width": 2.5},

    # --- Raster continuous colour ramps ---
    "elevation":        "Elevation #1",            # brown-to-white
    "slope":            "Slope",                   # green-yellow-red
    "aspect":           "Aspect",                  # circular colour wheel
    "temperature":      "Temperature",             # blue-white-red
    "precipitation":    "Precipitation",           # light-to-dark blue

    # --- Patch ranking (graduated) ---
    "patch_rank": {
        "ramp": "Green-Blue (Continuous)",
        "field": "AREA_HA",
        "breaks": 5,
        "method": "NaturalBreaks",
    },
}
```

```python
# ──────────────────────────────────────────────────────────────────
# SYMBOLOGY ENGINE — automatically choose renderer for each dataset
# ──────────────────────────────────────────────────────────────────

def choose_symbology(layer_name, lyr, aprx):
    """Automatically pick the right renderer and colours for a layer.

    Inspects the layer's geometry, data type, and name to decide:
    - Which renderer (UniqueValue, GraduatedColors, Stretch, etc.)
    - Which colour palette
    - Line width, fill transparency, outline colour

    Returns a description of what was applied (for logging).
    """
    desc = arcpy.Describe(lyr.dataSource if hasattr(lyr, 'dataSource') else lyr)
    name_lower = layer_name.lower()
    applied = []

    # --- RASTER layers ---
    if lyr.isRasterLayer:
        r = arcpy.Raster(lyr.dataSource)

        # Binary raster (0/1) — suitability result
        if r.minimum is not None and r.maximum is not None:
            if int(r.minimum) == 0 and int(r.maximum) == 1:
                sym = lyr.symbology
                sym.updateColorizer("RasterUniqueValueColorizer")
                cim = lyr.getDefinition("V3")
                pal = GIS_COLOUR_PALETTES["suitable_unsuitable"]
                for group in cim.colorizer.groups:
                    for cls in group.classes:
                        val = int(cls.values[0])
                        if val in pal:
                            cls.symbol.symbol.color = pal[val]
                            cls.label = pal[val]["label"]
                lyr.setDefinition(cim)
                applied.append("Binary: green/red (suitable/unsuitable)")

            # Continuous raster — elevation, slope, etc.
            else:
                sym = lyr.symbology
                sym.updateColorizer("RasterStretchColorizer")
                sym.colorizer.stretchType = "MinimumMaximum"

                # Choose colour ramp by name
                if any(kw in name_lower for kw in ["slope", "gradient"]):
                    ramp_name = GIS_COLOUR_PALETTES["slope"]
                elif any(kw in name_lower for kw in ["aspect"]):
                    ramp_name = GIS_COLOUR_PALETTES["aspect"]
                elif any(kw in name_lower for kw in ["dtm", "dem", "elevation"]):
                    ramp_name = GIS_COLOUR_PALETTES["elevation"]
                else:
                    ramp_name = "Elevation #1"

                ramps = aprx.listColorRamps(ramp_name)
                if ramps:
                    sym.colorizer.colorRamp = ramps[0]
                lyr.symbology = sym
                applied.append(f"Stretch: {ramp_name}")

        return applied

    # --- VECTOR layers ---
    geom_type = desc.shapeType  # Point, Polyline, Polygon, MultiPatch

    # Determine the semantic category from the layer name
    LAYER_CATEGORIES = {
        "study_area":   "study_area",
        "boundary":     "study_area",
        "flood_zone_2": "flood_zone",
        "flood_zone_3": "flood_zone_3",
        "flood":        "flood_zone",
        "river":        "rivers",
        "watercourse":  "rivers",
        "stream":       "rivers",
        "road":         "roads_major",     # default; split by class below
        "highway":      "roads_major",
        "motorway":     "roads_major",
        "rail":         "rail",
        "railway":      "rail",
        "urban":        "urban",
        "building":     "urban",
        "settlement":   "urban",
        "builtup":      "urban",
        "woodland":     "woodland",
        "forest":       "woodland",
        "habitat":      "habitat",
        "phi":          "habitat",
        "sssi":         "sssi",
        "sac":          "sac",
        "spa":          "spa",
        "alc":          "alc",              # special handling below
        "buffer":       "buffer",
    }

    category = None
    for keyword, cat in LAYER_CATEGORIES.items():
        if keyword in name_lower:
            category = cat
            break

    if not category:
        # Unknown layer — apply a simple single-symbol grey fill/line
        applied.append(f"Unknown layer type — default grey symbol")
        return applied

    # --- ALC requires UniqueValueRenderer (multiple grades) ---
    if category == "alc":
        sym = lyr.symbology
        sym.updateRenderer("UniqueValueRenderer")
        sym.renderer.fields = ["ALC_GRADE"]  # common field name

        # Build value list from palette
        alc_colors = {
            "Grade 1": GIS_COLOUR_PALETTES["alc_grade1"],
            "Grade 2": GIS_COLOUR_PALETTES["alc_grade2"],
            "Grade 3a": GIS_COLOUR_PALETTES["alc_grade3a"],
            "Grade 3b": GIS_COLOUR_PALETTES["alc_grade3b"],
            "Grade 4": GIS_COLOUR_PALETTES["alc_grade4"],
            "Grade 5": GIS_COLOUR_PALETTES["alc_grade5"],
        }
        for grade, colors in alc_colors.items():
            applied.append(f"ALC {grade}: {colors.get('label', grade)}")
        lyr.symbology = sym
        return applied

    # --- All other categories: apply from palette ---
    pal = GIS_COLOUR_PALETTES.get(category, {})
    cim = lyr.getDefinition("V3")

    if geom_type == "Polygon":
        symbol = cim.renderer.symbol.symbol
        # Fill
        for sl in symbol.symbolLayers:
            if sl.__class__.__name__ == "CIMSolidFill":
                if pal.get("fill") is not None:
                    sl.color = {"values": pal["fill"][:3], "type": "CIMRGBColor"}
                    sl.color["values"].append(pal["fill"][3])  # alpha
                else:
                    # No fill (study area boundary)
                    sl.enable = False
            elif sl.__class__.__name__ == "CIMSolidStroke":
                if pal.get("outline"):
                    sl.color = {"values": pal["outline"][:3], "type": "CIMRGBColor"}
                    sl.width = pal.get("width", 1.0)
        applied.append(f"Polygon: {category} style")

    elif geom_type == "Polyline":
        symbol = cim.renderer.symbol.symbol
        for sl in symbol.symbolLayers:
            if sl.__class__.__name__ == "CIMSolidStroke":
                if pal.get("line"):
                    sl.color = {"values": pal["line"][:3], "type": "CIMRGBColor"}
                    sl.width = pal.get("width", 1.0)
                if pal.get("dash"):
                    sl.effects = [{"type": "CIMGeometricEffectDashes",
                                   "dashTemplate": [6, 3]}]
        applied.append(f"Line: {category} style (width {pal.get('width', 1.0)})")

    elif geom_type == "Point":
        # Points — use circle marker with colour from palette
        applied.append(f"Point: {category} marker")

    lyr.setDefinition(cim)
    return applied


def apply_symbology_to_all_layers(map_obj, aprx):
    """Walk through every layer in a map and apply appropriate symbology.

    Prints a report of what was applied so the user can review.
    """
    print(f"\nApplying symbology to map: '{map_obj.name}'")
    print("-" * 60)

    for lyr in map_obj.listLayers():
        if not lyr.isFeatureLayer and not lyr.isRasterLayer:
            continue
        result = choose_symbology(lyr.name, lyr, aprx)
        print(f"  {lyr.name:<30} → {', '.join(result) if result else 'unchanged'}")

    print(f"\n✓ Symbology applied. Export a preview to check the colours.")
    print(f"  If anything looks wrong, tell me which layer needs different colours.")
```

#### Brief-Driven Layer Visibility — Only Show What's Relevant per Map

Different maps in a report need different visible layers. Don't show everything
on every map — that makes the map unreadable.

```python
# ──────────────────────────────────────────────────────────────────
# LAYER VISIBILITY — show only relevant layers per map
# ──────────────────────────────────────────────────────────────────

# Define what layers belong on each map type
MAP_LAYER_PROFILES = {
    # Map 1: Overview — basemap, study area, key features
    "overview": {
        "visible": [
            "study_area", "roads", "rail", "rivers", "urban_areas",
            "woodland", "towns",
        ],
        "hidden": [
            "flood_zone_2", "flood_zone_3", "alc", "priority_habitats",
            "sssi", "sac", "spa", "slope", "dtm", "suitability_result",
            "suitable_patches",
        ],
    },

    # Map 2: Constraints — show all constraint layers
    "constraints": {
        "visible": [
            "study_area", "flood_zone_2", "flood_zone_3", "alc",
            "priority_habitats", "sssi", "sac", "spa", "roads_buffer",
            "rail_buffer", "rivers_buffer", "urban_buffer", "woodland",
            "slope_unsuitable",
        ],
        "hidden": [
            "roads", "rail", "rivers", "urban_areas", "towns",
            "suitability_result", "suitable_patches", "dtm",
        ],
    },

    # Map 3: Result — suitability result + patches + study area
    "result": {
        "visible": [
            "study_area", "suitability_result", "suitable_patches",
            "roads", "towns",
        ],
        "hidden": [
            "flood_zone_2", "flood_zone_3", "alc", "priority_habitats",
            "sssi", "sac", "spa", "urban_areas", "woodland",
            "roads_buffer", "rail_buffer", "rivers_buffer", "urban_buffer",
            "slope", "dtm", "slope_unsuitable",
        ],
    },
}


def set_layer_visibility(map_obj, profile_name):
    """Turn layers on/off according to a map profile.

    profile_name: one of 'overview', 'constraints', 'result',
                  or a custom dict with 'visible' and 'hidden' lists.
    """
    if isinstance(profile_name, str):
        profile = MAP_LAYER_PROFILES.get(profile_name)
        if not profile:
            print(f"Unknown profile: {profile_name}")
            print(f"Available: {', '.join(MAP_LAYER_PROFILES.keys())}")
            return
    else:
        profile = profile_name

    visible_kw = [v.lower() for v in profile["visible"]]
    hidden_kw = [h.lower() for h in profile["hidden"]]

    shown = []
    hidden_list = []
    unmatched = []

    for lyr in map_obj.listLayers():
        name_lower = lyr.name.lower()

        # Check if layer matches any visible keyword
        if any(kw in name_lower for kw in visible_kw):
            lyr.visible = True
            shown.append(lyr.name)
        elif any(kw in name_lower for kw in hidden_kw):
            lyr.visible = False
            hidden_list.append(lyr.name)
        else:
            # Unmatched layers — hide by default, warn user
            lyr.visible = False
            unmatched.append(lyr.name)

    print(f"\nLayer visibility for '{profile_name}' map:")
    print(f"  VISIBLE ({len(shown)}): {', '.join(shown)}")
    print(f"  HIDDEN  ({len(hidden_list)}): {', '.join(hidden_list)}")
    if unmatched:
        print(f"  UNMATCHED ({len(unmatched)}): {', '.join(unmatched)}")
        print(f"  → These layers were hidden. Tell me if any should be visible.")


def setup_maps_for_report(aprx, map_configs):
    """Configure visibility for all maps in a multi-map report.

    map_configs: list of {"map_name": "...", "profile": "overview"/"constraints"/"result"}
    """
    for config in map_configs:
        m = aprx.listMaps(config["map_name"])[0]
        set_layer_visibility(m, config["profile"])

    print(f"\n✓ All {len(map_configs)} maps configured.")
    print(f"  Export previews to check each one.")

# Usage:
# setup_maps_for_report(aprx, [
#     {"map_name": "Map 1 - Overview",    "profile": "overview"},
#     {"map_name": "Map 2 - Constraints", "profile": "constraints"},
#     {"map_name": "Map 3 - Result",      "profile": "result"},
# ])
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
exclusion_rasters["woodland"] = reclassify_exclusion(
    "woodland_buffer_raster", "reclass_woodland", "Woodland buffers")
exclusion_rasters["flood_z2"] = reclassify_exclusion(
    "flood_zone_2_clip_raster", "reclass_flood2", "Flood Zone 2")
exclusion_rasters["flood_z3"] = reclassify_exclusion(
    "flood_zone_3_clip_raster", "reclass_flood3", "Flood Zone 3")
exclusion_rasters["flood_warning"] = reclassify_exclusion(
    "flood_warning_clip_raster", "reclass_flood_warning", "Flood Warning Areas")
exclusion_rasters["designated"] = reclassify_exclusion(
    "designated_sites_clip_raster", "reclass_designated", "Designated sites")
exclusion_rasters["urban"] = reclassify_exclusion(
    "urban_areas_clip_raster", "reclass_urban", "Urban areas")
exclusion_rasters["habitats"] = reclassify_exclusion(
    "priority_habitats_clip_raster", "reclass_habitats", "Priority habitats")

# Slope reclassification — threshold depends on brief (ask the user!)
# Common values: 10° for agriculture, 15° for renewables, 30° for housing
SLOPE_THRESHOLD = 30  # ← UPDATE this to match the brief
slope_reclass = Con(Raster("slope_degrees") <= SLOPE_THRESHOLD, 1, 0)
slope_reclass.save("reclass_slope")
exclusion_rasters["slope"] = "reclass_slope"
print(f"  Reclassified slope: <={SLOPE_THRESHOLD}deg=1, >{SLOPE_THRESHOLD}deg=0")

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

# Filter by area range — brief may specify min AND max
# Housing brief: 30-100 houses with gardens = approximately 1-4 ha
MIN_AREA_HA = 1.0   # ← minimum from brief (ask user if not specified)
MAX_AREA_HA = None   # ← set to None for no upper limit, or e.g. 4.0

if MAX_AREA_HA:
    where = f"AREA_HA >= {MIN_AREA_HA} AND AREA_HA <= {MAX_AREA_HA}"
    label = f"{MIN_AREA_HA}-{MAX_AREA_HA} ha"
else:
    where = f"AREA_HA >= {MIN_AREA_HA}"
    label = f">= {MIN_AREA_HA} ha"

arcpy.management.MakeFeatureLayer("suitable_patches", "filtered_lyr", where)
arcpy.management.CopyFeatures("filtered_lyr", "suitable_patches_final")

count = int(arcpy.management.GetCount("suitable_patches_final")[0])
print(f"Suitable patches ({label}): {count}")

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

# === MAP 3: Two site detail views with desirable criteria + aerial imagery ===
# Map 3 shows ONE view per selected site, side-by-side on A4.
# Each view has: aerial background, site outline, desirable criteria layers.
layout3 = aprx.createLayout(29.7, 21, "CENTIMETER", "Map 3 - Site Details")

# Create two separate maps for independent layer control per site
site1_map = aprx.createMap("Site 1 Detail", "MAP")
site2_map = aprx.createMap("Site 2 Detail", "MAP")

# Add aerial imagery as basemap for both detail maps
for m in [site1_map, site2_map]:
    # Add aerial raster or tile layer as background
    if arcpy.Exists(r"C:\Data\Digimap\Aerial"):
        m.addDataFromPath(r"C:\Data\Digimap\Aerial")
    # Add site outline and desirable criteria layers
    m.addDataFromPath(os.path.join(GDB, "selected_sites"))
    # Desirable criteria layers — these are NOT in the model,
    # they're shown on Map 3 to support site comparison
    for desirable_lyr in [
        "greenspace", "bus_stops", "train_stations",
        "schools", "shops_services", "gp_surgeries",
        "flood_alert_areas", "urban_areas_clip",
    ]:
        if arcpy.Exists(os.path.join(GDB, desirable_lyr)):
            m.addDataFromPath(os.path.join(GDB, desirable_lyr))

# Left frame: Site 1 detail
left_frame = layout3.createMapFrame(
    arcpy.Extent(1, 3, 14, 19), site1_map, "Site 1 Detail"
)
# Right frame: Site 2 detail
right_frame = layout3.createMapFrame(
    arcpy.Extent(15, 3, 28, 19), site2_map, "Site 2 Detail"
)

# Zoom each frame to its site with padding
with arcpy.da.SearchCursor("selected_sites", ["SHAPE@", "SITE_NAME"]) as cursor:
    sites = [(row[0], row[1]) for row in cursor]

if len(sites) >= 2:
    left_frame.camera.setExtent(sites[0][0].extent)
    left_frame.camera.scale *= 1.5   # 50% padding for context
    right_frame.camera.setExtent(sites[1][0].extent)
    right_frame.camera.scale *= 1.5

    # Add site labels
    title_left = layout3.createGraphicElement(
        arcpy.Point(7.5, 19.5), "TEXT", "Site 1 Label"
    )
    cim = title_left.getDefinition("V3")
    cim.textString = f"Site 1: {sites[0][1]}"
    cim.textSymbol.symbol.height = 10
    title_left.setDefinition(cim)

    title_right = layout3.createGraphicElement(
        arcpy.Point(21.5, 19.5), "TEXT", "Site 2 Label"
    )
    cim = title_right.getDefinition("V3")
    cim.textString = f"Site 2: {sites[1][1]}"
    cim.textSymbol.symbol.height = 10
    title_right.setDefinition(cim)

# Add map elements (scale bar, north arrow, legend, copyright)
layout3.createMapSurroundElement(arcpy.Point(14.85, 20.5), "TEXT", "Map3Title")
layout3.createMapSurroundElement(arcpy.Point(5, 1.5), "SCALE_BAR", "SB3", left_frame)
layout3.createMapSurroundElement(arcpy.Point(19, 1.5), "SCALE_BAR", "SB3R", right_frame)
layout3.createMapSurroundElement(arcpy.Point(2, 17), "NORTH_ARROW", "NA3", left_frame)
layout3.createMapSurroundElement(arcpy.Point(23, 10), "LEGEND", "Leg3", left_frame)

layout3.exportToJPEG(
    os.path.join(PROJECT_DIR, "Map3_SiteDetails.jpg"),
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

---

## Validation Checkpoints — How to Know the Output Is Right

After every major operation, run validation checks to catch errors early.
Do NOT proceed to the next step until the current step passes validation.

### After loading data (Step 3)
```python
def validate_data_loaded(expected_datasets, gdb_path):
    """Check that all required datasets exist and have features."""
    arcpy.env.workspace = gdb_path
    issues = []

    for name in expected_datasets:
        if not arcpy.Exists(name):
            issues.append(f"MISSING: {name} does not exist in the geodatabase")
            continue
        count = int(arcpy.management.GetCount(name)[0])
        if count == 0:
            issues.append(f"EMPTY: {name} has 0 features — check the source data")
        else:
            desc = arcpy.Describe(name)
            sr = desc.spatialReference
            print(f"  OK: {name} — {count} features, CRS: {sr.name} (EPSG:{sr.factoryCode})")
            # Warn if not in expected CRS
            if sr.factoryCode != 27700:  # BNG
                issues.append(
                    f"CRS WARNING: {name} is in {sr.name} (EPSG:{sr.factoryCode}), "
                    f"expected British National Grid (EPSG:27700). Reproject before analysis."
                )

    if issues:
        print(f"\n⚠ {len(issues)} ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    print("\n✓ All datasets loaded and valid")
    return True

# Call after loading
validate_data_loaded([
    "roads", "rail", "rivers", "urban_areas", "woodland",
    "flood_zone_2", "flood_zone_3", "alc", "priority_habitats",
    "designated_sites", "dtm_raw", "study_area",
], GDB)
```

### After clipping (Step 5)
```python
def validate_clip_results(clipped_layers, study_area):
    """Verify clipped layers have features and fall within study area extent."""
    study_ext = arcpy.Describe(study_area).extent
    issues = []

    for layer in clipped_layers:
        if not arcpy.Exists(layer):
            issues.append(f"MISSING: {layer} not created by clip")
            continue
        count = int(arcpy.management.GetCount(layer)[0])
        if count == 0:
            issues.append(
                f"EMPTY: {layer} has 0 features after clip — "
                f"the dataset may not overlap with the study area"
            )
        else:
            ext = arcpy.Describe(layer).extent
            # Check if clipped extent is within study area extent (with tolerance)
            tol = 10  # meters
            if (ext.XMin < study_ext.XMin - tol or ext.YMin < study_ext.YMin - tol
                    or ext.XMax > study_ext.XMax + tol or ext.YMax > study_ext.YMax + tol):
                issues.append(f"EXTENT: {layer} extends beyond study area — clip may have failed")
            else:
                print(f"  OK: {layer} — {count} features, within study area")

    if issues:
        print(f"\n⚠ {len(issues)} ISSUES:")
        for i in issues:
            print(f"  - {i}")
        return False
    print("\n✓ All clipped layers valid")
    return True
```

### After reclassification (Step 9)
```python
def validate_reclassified(raster_name, expected_values={0, 1}):
    """Verify a reclassified raster contains only expected values (0 and 1)."""
    r = arcpy.Raster(raster_name)
    issues = []

    # Check value range
    if r.minimum is not None and r.maximum is not None:
        actual_min = int(r.minimum)
        actual_max = int(r.maximum)
        actual_values = set(range(actual_min, actual_max + 1))
        unexpected = actual_values - expected_values
        if unexpected:
            issues.append(
                f"UNEXPECTED VALUES: {raster_name} contains values {unexpected}, "
                f"expected only {expected_values}"
            )
    else:
        issues.append(f"ALL NODATA: {raster_name} has no valid values — reclassification failed")

    # Check for excessive NODATA
    desc = arcpy.Describe(raster_name)
    total_cells = desc.width * desc.height
    if r.noDataValue is not None:
        # Count NODATA cells
        from arcpy.sa import IsNull
        nodata_count = arcpy.Raster(IsNull(r))
        # If >50% is NODATA, something is probably wrong
        pass  # difficult to count exactly without stats; flag as warning

    if not issues:
        print(f"  OK: {raster_name} — values: {r.minimum} to {r.maximum}")
    else:
        for i in issues:
            print(f"  ⚠ {i}")
    return len(issues) == 0

# Validate all reclassified layers
for name, path in exclusion_rasters.items():
    validate_reclassified(path)
```

### After final suitability result (Step 10)
```python
def validate_suitability_result(result_raster, study_area, cell_size):
    """Final validation of the suitability output."""
    r = arcpy.Raster(result_raster)
    issues = []

    # 1. Check it's binary (0 and 1 only)
    if r.minimum < 0 or r.maximum > 1:
        issues.append(f"NOT BINARY: values range from {r.minimum} to {r.maximum}")

    # 2. Check extent matches study area
    study_ext = arcpy.Describe(study_area).extent
    raster_ext = arcpy.Describe(result_raster).extent
    tol = cell_size * 2
    if abs(raster_ext.XMin - study_ext.XMin) > tol:
        issues.append(f"EXTENT MISMATCH: raster XMin={raster_ext.XMin:.0f}, study={study_ext.XMin:.0f}")

    # 3. Check cell size
    desc = arcpy.Describe(result_raster)
    actual_cell = round(desc.meanCellWidth, 2)
    if actual_cell != cell_size:
        issues.append(f"CELL SIZE: expected {cell_size}m, got {actual_cell}m")

    # 4. Check CRS
    sr = desc.spatialReference
    if sr.factoryCode != 27700:
        issues.append(f"CRS: expected BNG (27700), got {sr.name} ({sr.factoryCode})")

    # 5. Report statistics
    with arcpy.da.SearchCursor(result_raster, ["VALUE", "COUNT"]) as cursor:
        stats = {row[0]: row[1] for row in cursor}
    suitable = stats.get(1, 0)
    unsuitable = stats.get(0, 0)
    total = suitable + unsuitable
    pct = (suitable / total * 100) if total > 0 else 0
    area_ha = suitable * cell_size * cell_size / 10000

    if suitable == 0:
        issues.append("NO SUITABLE LAND FOUND — check reclassification criteria")
    if pct > 95:
        issues.append(f"SUSPICIOUS: {pct:.0f}% suitable — constraints may not be applied correctly")

    print(f"\nSuitability Result: {result_raster}")
    print(f"  Suitable:   {suitable:>10,} cells  ({pct:.1f}%)  = {area_ha:.1f} ha")
    print(f"  Unsuitable: {unsuitable:>10,} cells  ({100-pct:.1f}%)")
    print(f"  Cell size: {actual_cell}m  |  CRS: {sr.name}")

    if issues:
        print(f"\n  ⚠ {len(issues)} ISSUES:")
        for i in issues:
            print(f"    - {i}")
    else:
        print(f"\n  ✓ Result looks good")

    return len(issues) == 0
```

---

## Decision Points — When to Stop and Ask the User

Claude Code should NOT make every decision automatically. At these critical
points, STOP and ASK the user before proceeding.

### When to ask

| Decision Point | What to Ask | Why |
|----------------|-------------|-----|
| **Study area definition** | "How should I define the study area? Do you have a boundary shapefile, coordinates, or should I create one from a place name?" | The entire analysis depends on this boundary |
| **Buffer distances** | "The brief says buffer roads. What distances? e.g., 25m for minor roads, 50m for motorways?" | Wrong distances = wrong results |
| **Road classification split** | "I found these road classes in your data: [list]. Which should get the larger buffer?" | Field names vary between datasets |
| **Reclassification thresholds** | "What slope is too steep? (common: 10°, 15°, 20°)" | Depends on the land use being assessed |
| **ALC grades to exclude** | "Which Agricultural Land grades should be protected? (typical: Grades 1, 2, 3a)" | Policy decision, not technical |
| **NODATA interpretation** | "Areas with no flood zone data — should I treat those as suitable (no flood risk) or flag them for manual review?" | Absence of data ≠ absence of risk |
| **Minimum patch size** | "What's the minimum area for a suitable patch? (e.g., 0.5 ha, 1 ha, 5 ha)" | Depends on what's being sited |
| **Map layout** | "I'll create 3 maps. Map 1: overview, Map 2: constraints, Map 3: result. Does this match your brief?" | Brief may specify different maps |
| **Symbology colours** | "For the suitability result: green = suitable, red = unsuitable. Are these the right colours for your brief?" | Some briefs specify colour schemes |
| **Output format** | "Export as JPEG at 300dpi on A4 landscape? Or does the brief specify something different?" | Don't assume |

### How to ask (patterns for Claude Code)

When you hit a decision point, present it clearly:

```
I need your input before proceeding:

**Buffer distances for roads**
I found these road classes in your data:
  - Motorway (234 features)
  - A Road (1,205 features)
  - B Road (892 features)
  - Minor Road (3,456 features)

Common approaches:
  1. Motorway: 50m, A Road: 50m, B Road: 25m, Minor: 25m
  2. All roads: 25m (simpler)
  3. Custom distances — tell me what you need

Which approach, or what distances do you want?
```

### How to present choices from the data

When a decision depends on the actual data content, show the user what's there:

```python
# Before asking about ALC reclassification, show them the grades present:
grades = sorted({row[0] for row in
    arcpy.da.SearchCursor("alc_clip", ["ALC_GRADE"]) if row[0]})
counts = {}
with arcpy.da.SearchCursor("alc_clip", ["ALC_GRADE"]) as cursor:
    for row in cursor:
        counts[row[0]] = counts.get(row[0], 0) + 1

print("ALC Grades in your study area:")
for grade in grades:
    print(f"  {grade}: {counts[grade]} features")
# Then ask: "Which grades should be protected (unsuitable)?"
```

### Decision log — record what was decided

After each decision, write it to the project notes:

```python
def log_decision(project_dir, decision, choice, reason=""):
    """Append a decision to the project NOTES.md file."""
    import datetime
    notes_path = os.path.join(project_dir, "NOTES.md")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n### Decision: {decision} ({timestamp})\n"
    entry += f"**Choice:** {choice}\n"
    if reason:
        entry += f"**Reason:** {reason}\n"
    with open(notes_path, "a") as f:
        f.write(entry)
    print(f"Decision logged: {decision} → {choice}")

# Example usage after user decides buffer distances:
log_decision(
    PROJECT_DIR,
    "Road buffer distances",
    "Motorway: 50m, A Road: 50m, B Road: 25m, Minor Road: 25m",
    "Per assignment brief Section 3.2"
)
```

---

## Visual Review & Feedback Loop

Claude Code runs in a terminal and cannot display maps directly. But there
are effective ways to let the user see and review map outputs, then make
adjustments based on their feedback.

### Export quick previews for user review
```python
def export_preview(aprx_or_layout, output_path, resolution=72):
    """Export a quick low-res preview for the user to check.

    72 dpi = small file, fast export, good enough to spot layout issues.
    Final export uses 300 dpi.
    """
    if isinstance(aprx_or_layout, str):
        # It's a layout name — find it
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        layout = aprx.listLayouts(aprx_or_layout)[0]
    else:
        layout = aprx_or_layout

    layout.exportToJPEG(output_path, resolution=resolution, jpeg_quality=80)
    size_kb = os.path.getsize(output_path) / 1024
    print(f"Preview exported: {output_path} ({size_kb:.0f} KB)")
    print(f"Open this file and tell me what needs changing.")
    return output_path

# After setting up a layout, export preview and ask user to review:
preview = export_preview(layout, r"C:\Projects\preview_map1.jpg")
```

### Report what's on the layout (so user can direct changes)
```python
def describe_layout(layout):
    """Describe every element on the layout with positions and sizes.

    Present this to the user so they can say things like
    'move the legend to the bottom-right' or 'make the title bigger'.
    """
    print(f"\nLayout: '{layout.name}' ({layout.pageWidth}x{layout.pageHeight} {layout.pageUnits})")
    print("-" * 70)

    for elm in layout.listElements():
        elm_type = elm.type
        name = elm.name

        # Position and size
        x = round(elm.elementPositionX, 1)
        y = round(elm.elementPositionY, 1)
        w = round(elm.elementWidth, 1)
        h = round(elm.elementHeight, 1)

        print(f"  [{elm_type}] '{name}'")
        print(f"    Position: ({x}, {y})  Size: {w} x {h} cm")

        if elm_type == "TEXT_ELEMENT":
            print(f"    Text: '{elm.text}'")
            print(f"    Font size: {elm.textSize} pt")
        elif elm_type == "MAPFRAME_ELEMENT":
            print(f"    Map: {elm.map.name if elm.map else 'None'}")
            print(f"    Scale: 1:{elm.camera.scale:,.0f}")
            ext = elm.camera.getExtent()
            print(f"    Extent: ({ext.XMin:.0f}, {ext.YMin:.0f}) to ({ext.XMax:.0f}, {ext.YMax:.0f})")
        elif elm_type == "LEGEND_ELEMENT":
            print(f"    Items: {len(elm.items)}")

    print(f"\nTell me what to change — e.g.:")
    print(f"  'Move the legend to bottom-right'")
    print(f"  'Make the title bigger'")
    print(f"  'The scale bar is overlapping the map'")
    print(f"  'Change the north arrow to a different style'")

describe_layout(layout)
```

### Handle user feedback about layout

When the user says things like "move the legend", "make the title bigger",
"this doesn't look right", translate their feedback into arcpy.mp calls:

```python
# Common user feedback and how to handle it:

# "Move the legend to the bottom-right"
legend = layout.listElements("LEGEND_ELEMENT", "Legend")[0]
legend.elementPositionX = 22.0  # right side of A4 landscape
legend.elementPositionY = 3.0   # near bottom

# "Make the title bigger"
title = layout.listElements("TEXT_ELEMENT", "Title")[0]
cim = title.getDefinition("V3")
cim.textSymbol.symbol.height = 20  # increase from e.g. 14 to 20
title.setDefinition(cim)

# "The scale bar overlaps the map frame"
scale_bar = layout.listElements("SCALE_BAR_ELEMENT")[0]
map_frame = layout.listElements("MAPFRAME_ELEMENT")[0]
# Move scale bar below the map frame
scale_bar.elementPositionY = map_frame.elementPositionY - 1.5

# "Add more space between the two map frames"
left_frame = layout.listElements("MAPFRAME_ELEMENT", "Left Detail")[0]
right_frame = layout.listElements("MAPFRAME_ELEMENT", "Right Detail")[0]
left_frame.elementWidth = 12.0  # shrink left
right_frame.elementPositionX = 15.5  # move right further over

# "Change the map extent to show more area"
mf = layout.listElements("MAPFRAME_ELEMENT", "Main Map Frame")[0]
ext = mf.camera.getExtent()
# Expand by 20%
buffer_x = (ext.XMax - ext.XMin) * 0.1
buffer_y = (ext.YMax - ext.YMin) * 0.1
new_ext = arcpy.Extent(
    ext.XMin - buffer_x, ext.YMin - buffer_y,
    ext.XMax + buffer_x, ext.YMax + buffer_y,
)
mf.camera.setExtent(new_ext)

# "The colours are wrong / I want different colours"
# → Re-run the symbology section with new colours

# "This layer shouldn't be visible"
lyr = mf.map.listLayers("urban_areas")[0]
lyr.visible = False

# After ANY change: re-export preview and show to user
export_preview(layout, r"C:\Projects\preview_updated.jpg")
```

### Handle user feedback about analysis results

When the user says "the results don't look right" or "too much/too little
is marked as suitable":

```python
# Common analysis feedback and responses:

# "Too much area is suitable — something's missing"
# → Check which constraint layers are active:
print("Active constraint layers:")
for name, path in exclusion_rasters.items():
    r = arcpy.Raster(path)
    zeros = sum(1 for row in arcpy.da.SearchCursor(path, ["VALUE"])
                if row[0] == 0)
    print(f"  {name}: {zeros} cells excluded")
# Show which layer excludes the most / least

# "Nothing is suitable"
# → One reclassified layer is probably all-zero. Check each:
print("Checking each layer for all-zero issues:")
for name, path in exclusion_rasters.items():
    r = arcpy.Raster(path)
    if r.maximum == 0:
        print(f"  ⚠ {name}: ALL UNSUITABLE (max=0) — this kills the entire result!")
        print(f"    Check the reclassification criteria for this layer")

# "The suitable areas are in the wrong place"
# → Export each individual reclassified layer as a separate preview
# so the user can see which constraint is causing the issue

# "The buffer distance is wrong, change it to 100m"
# → Re-run just the buffer step with new distance, then re-run
# PolygonToRaster, Reclassify, and Raster Calculator from that point
```

### Screenshot review — user sends a picture

Claude Code is multimodal. If the user takes a screenshot of their map in
ArcGIS Pro and sends it, Claude can SEE the image and give specific feedback:

```
User: [pastes screenshot of their map layout]
Claude: I can see your Map 1 layout. A few observations:
  1. The legend is overlapping the map frame on the right side — I'll move
     it to position (23, 8) to give it more space
  2. The title text looks too small — I'll increase it from 12pt to 16pt
  3. The north arrow is in the bottom-left which is unconventional — most
     maps put it in the top-left or top-right
  4. I can see the study area boundary but the basemap isn't visible —
     the basemap layer might be turned off

Want me to fix all of these, or just specific ones?
```

### The review loop workflow

For map production, always follow this loop:

```
1. Generate layout with script
2. Export low-res preview (72 dpi)
3. Tell user: "Preview saved to [path]. Please open it and tell me
   what needs changing."
4. Wait for user feedback
5. Make adjustments based on feedback
6. Export new preview
7. Repeat until user says it looks good
8. Export final version at 300 dpi
```

For analysis results:

```
1. Run analysis step
2. Run validation checkpoint
3. Present results with statistics
4. Ask: "Does this look right? [X] cells suitable ([Y]%). Expected?"
5. If user says no: ask what's wrong, diagnose, re-run
6. If user says yes: proceed to next step
```

---

## Putting It All Together — The Interactive Workflow

When helping a user through a complete suitability analysis, the interaction
should follow this pattern. Claude Code should NOT silently run all 12 steps.
Instead, pause at checkpoints and decision points.

```
PHASE 1: SETUP
  [1] Find ArcGIS Pro, scan USB/folder for data
  [2] Match data to brief → show FOUND/MISSING table
  ● ASK: "I found 8 of 12 datasets. You're missing [X, Y, Z].
    Should I proceed with what we have, or do you need to download
    the missing ones first?"

PHASE 2: DATA PREPARATION
  [3] Load data into geodatabase
  → VALIDATE: all datasets loaded, CRS correct
  [4] Merge multi-tile data
  [5] Clip to study area
  → VALIDATE: all clips have features
  ● ASK if any clips are empty: "The flood zone clip is empty —
    there may be no flood zones in your study area. Is that expected?"

PHASE 3: ANALYSIS (decision-heavy)
  [6] Buffer
  ● ASK: "What buffer distances? Here are the road classes I found: [...]"
  → VALIDATE: buffer features created
  [7] Slope
  ● ASK: "What slope threshold? 10°? 15°? 20°?"
  [8] Polygon to Raster
  → VALIDATE: all rasters aligned (check_raster_alignment)
  [9] Reclassify
  ● ASK: "For ALC, which grades to protect? I found these in your data: [...]"
  ● ASK: "How should I handle NODATA in flood zones?"
  → VALIDATE: all binary (0/1), no unexpected values
  [10] Raster Calculator
  → VALIDATE: result is binary, suitable % is reasonable
  ● REPORT: "Result: X% suitable (Y hectares). Does this seem right?"

PHASE 4: RESULTS
  [11] Identify patches
  ● ASK: "What minimum patch size? 0.5 ha? 1 ha?"
  → REPORT: "Found N suitable patches, largest is X ha, smallest Y ha"

PHASE 5: MAP PRODUCTION (iterative)
  [12] Create maps
  → EXPORT preview (72 dpi)
  ● ASK: "Preview saved. Open it and tell me what to change."
  → Adjust based on feedback
  → EXPORT new preview
  → Repeat until approved
  → EXPORT final (300 dpi)
```

---

## Desirable Criteria — Proximity Analysis for Site Selection

Desirable criteria are NOT part of the suitability model. They are used AFTER
the model produces suitable patches to help the user pick the best site(s).
These are spatial proximity calculations: how close is each patch to amenities,
services, transport, and greenspace?

### Load desirable criteria data
```python
# These datasets are NOT exclusion layers — they go on Map 3 only
DESIRABLE_DATASETS = {
    # Name in GDB          Source file path
    "greenspace":          r"C:\Data\OS\GreenspaceSite.shp",
    "bus_stops":           r"C:\Data\NaPTAN\Stops.csv",        # National Public Transport
    "train_stations":      r"C:\Data\NaPTAN\RailReferences.csv",
    "schools":             r"C:\Data\OS\important_building.shp",  # filter type=school
    "shops_services":      r"C:\Data\OS\important_building.shp",  # filter type=retail
    "gp_surgeries":        r"C:\Data\NHS\gp_practices.csv",
    "flood_alert_areas":   r"C:\Data\EA\Flood_Alert_Areas.shp",
}

# Load and clip to study area (with buffer for context)
for name, source in DESIRABLE_DATASETS.items():
    if not os.path.exists(source):
        print(f"  SKIP {name}: source file not found at {source}")
        continue

    # Import to geodatabase
    if source.endswith(".csv"):
        # CSV with coordinates → point feature class
        arcpy.management.XYTableToPoint(
            source, os.path.join(GDB, name),
            x_field="Easting", y_field="Northing",
            coordinate_system=arcpy.SpatialReference(27700),
        )
    else:
        arcpy.conversion.FeatureClassToFeatureClass(
            source, GDB, name,
        )

    # Clip to study area (with 2km buffer for context beyond site boundary)
    arcpy.analysis.Buffer("study_area", "study_area_2km", "2000 Meters")
    arcpy.analysis.Clip(name, "study_area_2km", f"{name}_clip")
    count = int(arcpy.management.GetCount(f"{name}_clip")[0])
    print(f"  {name}: {count} features loaded")
```

### Calculate proximity scores for each suitable patch
```python
def calculate_proximity_scores(patches_fc, desirable_layers):
    """For each suitable patch, calculate distance to nearest amenity.

    Adds fields to the patches feature class:
      DIST_GREENSPACE, DIST_BUS, DIST_TRAIN, DIST_SCHOOL, etc.

    Lower distance = better site for that criterion.
    """
    results = {}

    for layer_name, field_name in desirable_layers.items():
        target = f"{layer_name}_clip"
        if not arcpy.Exists(target) or int(arcpy.management.GetCount(target)[0]) == 0:
            print(f"  SKIP {layer_name}: no features in study area")
            continue

        # Near tool calculates distance from each patch centroid
        # to nearest feature in the desirable layer
        arcpy.analysis.Near(patches_fc, target, search_radius="10000 Meters")

        # Rename NEAR_DIST to descriptive field name
        if not field_name in [f.name for f in arcpy.ListFields(patches_fc)]:
            arcpy.management.AddField(patches_fc, field_name, "DOUBLE")
        arcpy.management.CalculateField(
            patches_fc, field_name, "!NEAR_DIST!", "PYTHON3"
        )

        # Clean up Near tool fields
        arcpy.management.DeleteField(patches_fc, ["NEAR_FID", "NEAR_DIST"])

        # Report
        with arcpy.da.SearchCursor(patches_fc, [field_name]) as cursor:
            distances = [row[0] for row in cursor if row[0] is not None]
        if distances:
            print(f"  {field_name}: min={min(distances):.0f}m, "
                  f"max={max(distances):.0f}m, mean={sum(distances)/len(distances):.0f}m")
            results[field_name] = distances

    return results


# Define what to measure
DESIRABLE_PROXIMITY = {
    "greenspace":       "DIST_GREENSPACE",
    "bus_stops":        "DIST_BUS",
    "train_stations":   "DIST_TRAIN",
    "schools":          "DIST_SCHOOL",
    "shops_services":   "DIST_SHOPS",
    "gp_surgeries":     "DIST_GP",
    "flood_alert_areas":"DIST_FLOOD_ALERT",
}

calculate_proximity_scores("suitable_patches_final", DESIRABLE_PROXIMITY)
```

### Check adjacency to existing urban areas
```python
def check_urban_adjacency(patches_fc, urban_fc, max_distance=200):
    """Flag patches that are adjacent to existing urban areas.

    'Adjacent' = within max_distance metres of urban boundary.
    This is DESIRABLE for housing (natural extension of settlement).
    """
    arcpy.analysis.Near(patches_fc, urban_fc, search_radius=f"{max_distance} Meters")

    # Add boolean field
    arcpy.management.AddField(patches_fc, "ADJACENT_URBAN", "SHORT")
    arcpy.management.CalculateField(
        patches_fc, "ADJACENT_URBAN",
        f"1 if !NEAR_DIST! >= 0 and !NEAR_DIST! <= {max_distance} else 0",
        "PYTHON3",
    )

    # Report
    with arcpy.da.SearchCursor(patches_fc, ["ADJACENT_URBAN"]) as cursor:
        adjacent = sum(1 for row in cursor if row[0] == 1)
    total = int(arcpy.management.GetCount(patches_fc)[0])
    print(f"  {adjacent} of {total} patches are within {max_distance}m of urban areas")

    arcpy.management.DeleteField(patches_fc, ["NEAR_FID", "NEAR_DIST"])

check_urban_adjacency("suitable_patches_final", "urban_areas_clip")
```

### Present desirable criteria summary table
```python
def print_site_comparison_table(patches_fc, top_n=10):
    """Print a ranked comparison table of the best patches.

    Shows area, all proximity distances, and urban adjacency.
    Helps the user pick their final 2 sites.
    """
    fields = ["OID@", "AREA_HA", "ADJACENT_URBAN"]
    # Add all DIST_ fields
    dist_fields = [f.name for f in arcpy.ListFields(patches_fc) if f.name.startswith("DIST_")]
    fields.extend(dist_fields)

    rows = []
    with arcpy.da.SearchCursor(patches_fc, fields) as cursor:
        for row in cursor:
            rows.append(dict(zip(fields, row)))

    # Sort by area (largest first)
    rows.sort(key=lambda r: r["AREA_HA"], reverse=True)
    top = rows[:top_n]

    # Print table
    print(f"\n{'='*90}")
    print(f"TOP {len(top)} SUITABLE PATCHES — DESIRABLE CRITERIA COMPARISON")
    print(f"{'='*90}")

    header = f"{'ID':>4}  {'Area(ha)':>8}  {'Urban?':>6}"
    for df in dist_fields:
        short = df.replace("DIST_", "")[:8]
        header += f"  {short:>8}"
    print(header)
    print("-" * len(header))

    for r in top:
        line = f"{r['OID@']:>4}  {r['AREA_HA']:>8.2f}  {'Yes' if r.get('ADJACENT_URBAN') else 'No':>6}"
        for df in dist_fields:
            val = r.get(df)
            if val is not None:
                line += f"  {val:>7.0f}m"
            else:
                line += f"  {'N/A':>8}"
        print(line)

    print(f"\nLower distances = better. 'Urban?' = adjacent to existing settlement.")
    print(f"\nWhich 2 patches do you want as your final sites?")
    print(f"Tell me the IDs and I'll create the site outline polygons.")

print_site_comparison_table("suitable_patches_final")
```

---

## Site Selection & Digitising — Creating Final Site Polygons

After the user picks their 2 best patches from the comparison table,
create proper site outline polygons with attributes.

### Create selected sites from patch IDs
```python
def create_selected_sites(patches_fc, selected_ids, output_fc, site_names=None):
    """Extract user-selected patches into a new feature class.

    selected_ids: list of OID values the user chose (e.g. [42, 17])
    site_names:   optional names (e.g. ["North Field", "River Meadow"])
    """
    # Select the chosen patches
    oid_field = arcpy.Describe(patches_fc).OIDFieldName
    where = f"{oid_field} IN ({', '.join(str(i) for i in selected_ids)})"
    arcpy.management.MakeFeatureLayer(patches_fc, "selected_lyr", where)
    arcpy.management.CopyFeatures("selected_lyr", output_fc)

    # Add site metadata fields
    arcpy.management.AddField(output_fc, "SITE_NAME", "TEXT", field_length=100)
    arcpy.management.AddField(output_fc, "SITE_ID", "SHORT")
    arcpy.management.AddField(output_fc, "DWELLINGS_EST", "SHORT")

    # Estimate dwelling capacity: ~25 dwellings per hectare (typical UK density)
    DWELLINGS_PER_HA = 25

    with arcpy.da.UpdateCursor(
        output_fc, ["SITE_ID", "SITE_NAME", "AREA_HA", "DWELLINGS_EST"]
    ) as cursor:
        for i, row in enumerate(cursor):
            row[0] = i + 1  # SITE_ID
            if site_names and i < len(site_names):
                row[1] = site_names[i]
            else:
                row[1] = f"Site {i + 1}"
            row[3] = int(row[2] * DWELLINGS_PER_HA)  # estimated dwellings
            cursor.updateRow(row)

    # Report
    with arcpy.da.SearchCursor(
        output_fc, ["SITE_ID", "SITE_NAME", "AREA_HA", "DWELLINGS_EST"]
    ) as cursor:
        for row in cursor:
            print(f"  Site {row[0]}: {row[1]}")
            print(f"    Area: {row[2]:.2f} ha")
            print(f"    Estimated dwellings: {row[3]} (at {DWELLINGS_PER_HA}/ha)")

    arcpy.management.Delete("selected_lyr")
    return output_fc

# Usage after user picks their sites:
# create_selected_sites(
#     "suitable_patches_final",
#     selected_ids=[42, 17],
#     output_fc="selected_sites",
#     site_names=["North of Oakwood", "River Meadow East"],
# )
```

### Manual digitising guidance (when patch shapes need refinement)
```
Sometimes the raster-derived patch boundary is too jagged or includes
unwanted areas. The user may need to manually digitise a cleaner outline.

Claude Code CANNOT do interactive digitising — this requires ArcGIS Pro UI.
Give the user these instructions:

1. Open the "selected_sites" feature class in ArcGIS Pro
2. Start an Edit session (Edit tab → Create)
3. Select the site polygon you want to refine
4. Right-click → Edit Vertices
5. Drag vertices to clean up the boundary
6. Or: delete the feature and draw a new polygon using the
   Polygon construction tool, snapping to the original shape
7. Save Edits when done

After manual edits, recalculate geometry:
```
```python
arcpy.management.CalculateGeometryAttributes(
    "selected_sites",
    [["AREA_HA", "AREA"], ["PERIMETER_M", "PERIMETER_LENGTH"]],
    area_unit="HECTARES", length_unit="METERS",
)
```

### Workspace cleanup — remove intermediate layers
```python
def cleanup_intermediate_layers(gdb_path, keep_patterns=None):
    """Delete intermediate datasets, keep only final outputs.

    keep_patterns: list of name patterns to preserve.
    Default keeps: study_area, selected_sites, suitable_patches_final,
                   suitability_result, all *_clip layers, all desirable layers.
    """
    if keep_patterns is None:
        keep_patterns = [
            "study_area", "selected_sites", "suitable_patches_final",
            "suitability_result", "reclass_", "_clip",
            "greenspace", "bus_stops", "train_stations",
            "schools", "shops_services", "gp_surgeries",
            "flood_alert",
        ]

    arcpy.env.workspace = gdb_path
    all_datasets = (
        arcpy.ListFeatureClasses() +
        arcpy.ListRasters() +
        arcpy.ListTables()
    )

    to_delete = []
    to_keep = []

    for ds in all_datasets:
        if any(pat in ds.lower() for pat in [p.lower() for p in keep_patterns]):
            to_keep.append(ds)
        else:
            to_delete.append(ds)

    print(f"KEEPING {len(to_keep)} datasets:")
    for ds in sorted(to_keep):
        print(f"  ✓ {ds}")

    print(f"\nDELETING {len(to_delete)} intermediate datasets:")
    for ds in sorted(to_delete):
        print(f"  ✗ {ds}")

    # ASK user before deleting
    print(f"\nDelete these {len(to_delete)} intermediate datasets? (confirm before proceeding)")
    # Only delete after user confirms
    # for ds in to_delete:
    #     arcpy.management.Delete(ds)
```

---

## Custom Criteria — Adding Extra Constraints Beyond the Standard Set

Many briefs require 2+ additional criteria chosen by the student with
literature-backed justification. This section provides a framework for
selecting, implementing, and justifying custom criteria.

### Common additional criteria for UK housing suitability

| Criterion | Buffer / Rule | Data Source | Justification |
|-----------|---------------|-------------|---------------|
| Heritage / listed buildings | ≥100m buffer | Historic England | NPPF (2024) para 200-208: protect heritage assets and their settings |
| AONB / National Landscapes | Exclude entirely | Natural England (MAGIC) | NPPF (2024) para 182: major development should not occur in AONBs |
| Green Belt | Exclude entirely | Local authority GIS / MAGIC | NPPF (2024) para 142-156: strong presumption against development |
| Power lines / pipelines | ≥50m buffer | National Grid / HSE | Health & Safety Executive guidance on development near high-voltage lines |
| Peat / bog soils | Exclude entirely | BGS / Natural England | NPPF (2024) para 180: protect irreplaceable habitats; peat is carbon store |
| Local Nature Reserves (LNR) | Exclude entirely | Natural England (MAGIC) | NPPF (2024) para 185: protect local wildlife-rich habitats |
| Ancient woodland | ≥15m buffer | Natural England | Natural England standing advice: 15m buffer minimum |
| Noise contours (roads/airports) | Exclude >70dB | Local authority | WHO Environmental Noise Guidelines (2018): health impacts |
| Contaminated land | Exclude | Local authority register | Environmental Protection Act 1990, Part IIA |
| Public Rights of Way | ≥5m buffer | OS / local authority | Countryside and Rights of Way Act 2000: maintain access |

### Implementing a custom criterion
```python
# Example: Heritage / Listed Buildings with 100m buffer

# 1. Load the data
heritage_source = r"C:\Data\HistoricEngland\ListedBuildings.shp"
arcpy.conversion.FeatureClassToFeatureClass(heritage_source, GDB, "listed_buildings")
arcpy.analysis.Clip("listed_buildings", "study_area", "listed_buildings_clip")

# 2. Buffer
arcpy.analysis.Buffer(
    "listed_buildings_clip", "listed_buildings_buffer",
    "100 Meters", dissolve_option="ALL",
)

# 3. Convert to raster
arcpy.env.extent = "study_area"
arcpy.conversion.PolygonToRaster(
    "listed_buildings_buffer", "OBJECTID", "listed_buildings_raster",
    cell_assignment="CELL_CENTER", cellsize=CELL_SIZE,
)

# 4. Reclassify (same as other exclusion layers)
exclusion_rasters["heritage"] = reclassify_exclusion(
    "listed_buildings_raster", "reclass_heritage", "Heritage buffer 100m"
)

# 5. Include in raster calculator (it's already in the exclusion_rasters dict)
```

```python
# Example: AONB / National Landscapes — full exclusion

aonb_source = r"C:\Data\NaturalEngland\Areas_of_Outstanding_Natural_Beauty.shp"
arcpy.conversion.FeatureClassToFeatureClass(aonb_source, GDB, "aonb")
arcpy.analysis.Clip("aonb", "study_area", "aonb_clip")

count = int(arcpy.management.GetCount("aonb_clip")[0])
if count == 0:
    print("  No AONB in study area — criterion does not apply")
    print("  → Note this in report section C (missing criteria)")
else:
    arcpy.env.extent = "study_area"
    arcpy.conversion.PolygonToRaster(
        "aonb_clip", "OBJECTID", "aonb_raster",
        cell_assignment="CELL_CENTER", cellsize=CELL_SIZE,
    )
    exclusion_rasters["aonb"] = reclassify_exclusion(
        "aonb_raster", "reclass_aonb", "AONB (National Landscape)"
    )
```

### Literature justification template
```
When adding a custom criterion, justify it with this structure:

CRITERION: [Name]
RULE: [Buffer distance / exclusion rule]
JUSTIFICATION:
  [One sentence on WHY this criterion matters for housing suitability]
  [Reference to national planning policy — e.g. NPPF 2024 paragraph X]
  [Reference to academic/practitioner source — e.g. Malczewski, 2004]
DATA SOURCE: [Exact dataset name and download URL]
IMPLEMENTATION: [Buffer distance, reclassification rule]

Example:
  CRITERION: Heritage assets (listed buildings)
  RULE: 100m buffer — classify as unsuitable
  JUSTIFICATION:
    New housing development near listed buildings can harm their
    historic setting and character. The NPPF (2024, para 200) states
    that "great weight should be given to the asset's conservation"
    and that "any harm to, or loss of, the significance of a
    designated heritage asset... should require clear and convincing
    justification" (para 206). A 100m buffer provides a minimum
    protective zone consistent with Historic England's guidance on
    setting assessment (Historic England, 2017).
  DATA SOURCE: Historic England — National Heritage List
    (https://historicengland.org.uk/listing/the-list/)
  IMPLEMENTATION: Buffer 100m, dissolve, PolygonToRaster, reclassify
    to binary (present=0, absent=1).
```

---

## Report Writing Support — Pro-Forma Sections A–G

This section helps Claude Code generate content for the report pro-forma.
Claude should draft the text; the user reviews and edits.

### Section A: Dataset Reference Table (Harvard style)
```python
def generate_dataset_table(datasets_used):
    """Generate a Harvard-referenced dataset table for the report.

    datasets_used: list of dicts with keys:
        name, source_org, year, url, what_for
    """
    print("| Dataset | Source | Used For |")
    print("|---------|--------|----------|")
    for ds in datasets_used:
        ref = f"{ds['source_org']} ({ds['year']})"
        print(f"| {ds['name']} | {ref} | {ds['what_for']} |")

    print("\n--- Harvard References ---\n")
    # Sort alphabetically by source org for reference list
    for ds in sorted(datasets_used, key=lambda d: d["source_org"]):
        print(f"{ds['source_org']} ({ds['year']}) {ds['name']}. "
              f"Available at: {ds['url']} (Accessed: [DATE]).")

# Standard UK suitability datasets
DATASETS_USED = [
    {
        "name": "OS VectorMap Local (Roads, Rail, Urban, Watercourses)",
        "source_org": "Ordnance Survey",
        "year": "2024",
        "url": "https://digimap.edina.ac.uk",
        "what_for": "Buffer analysis (roads, rail, watercourses), urban exclusion",
    },
    {
        "name": "OS Terrain 5 DTM",
        "source_org": "Ordnance Survey",
        "year": "2024",
        "url": "https://digimap.edina.ac.uk",
        "what_for": "Slope generation for terrain constraint",
    },
    {
        "name": "Flood Map for Planning (Flood Zones 2 & 3)",
        "source_org": "Environment Agency",
        "year": "2024",
        "url": "https://www.data.gov.uk/dataset/flood-map-for-planning",
        "what_for": "Flood zone exclusion",
    },
    {
        "name": "Flood Warning Areas",
        "source_org": "Environment Agency",
        "year": "2024",
        "url": "https://www.data.gov.uk/dataset/flood-warning-areas",
        "what_for": "Essential flood exclusion criterion",
    },
    {
        "name": "Flood Alert Areas",
        "source_org": "Environment Agency",
        "year": "2024",
        "url": "https://www.data.gov.uk/dataset/flood-alert-areas",
        "what_for": "Desirable criterion (Map 3)",
    },
    {
        "name": "Agricultural Land Classification",
        "source_org": "Natural England",
        "year": "2024",
        "url": "https://magic.defra.gov.uk",
        "what_for": "Grade 1/2 agricultural land exclusion",
    },
    {
        "name": "Priority Habitat Inventory",
        "source_org": "Natural England",
        "year": "2024",
        "url": "https://magic.defra.gov.uk",
        "what_for": "Habitat exclusion",
    },
    {
        "name": "Sites of Special Scientific Interest",
        "source_org": "Natural England",
        "year": "2024",
        "url": "https://magic.defra.gov.uk",
        "what_for": "Designated site exclusion",
    },
    {
        "name": "National Woodland Inventory",
        "source_org": "Forestry Commission",
        "year": "2024",
        "url": "https://magic.defra.gov.uk",
        "what_for": "Woodland buffer exclusion",
    },
    {
        "name": "OS MasterMap 1:25,000 Raster",
        "source_org": "Ordnance Survey",
        "year": "2024",
        "url": "https://digimap.edina.ac.uk",
        "what_for": "Basemap for all maps",
    },
]
```

### Section B: Custom Criteria Justification
```
Draft structure for the user's 2 custom criteria:

Criterion 1: [NAME]
  This criterion was included because [1 sentence reason].
  The NPPF (2024, para X) states that "[relevant quote]".
  [Academic source] found that [relevant finding].
  A buffer of [X]m was applied based on [source guidance].

Criterion 2: [NAME]
  [Same structure as above]

Claude should draft this text based on:
- Which criterion the user chose
- The literature justification from the custom criteria table above
- The actual data found in the study area
```

### Section C: Absent Criteria
```python
def identify_absent_criteria(exclusion_rasters, study_area):
    """Identify criteria from the brief that have no data in the study area.

    Some constraints may be absent — e.g., no flood zones, no SSSI.
    This is normal and should be documented in section C.
    """
    absent = []
    for name, path in exclusion_rasters.items():
        if path is None:
            absent.append({"criterion": name, "reason": "Dataset not available"})
            continue
        r = arcpy.Raster(path)
        # If reclassified raster is ALL 1 (all suitable), the constraint
        # has no effect — it's absent from the study area
        if r.minimum == 1 and r.maximum == 1:
            absent.append({
                "criterion": name,
                "reason": "No features in study area (all cells suitable)",
            })

    if absent:
        print(f"\nCriteria with NO EFFECT in this study area:")
        for a in absent:
            print(f"  - {a['criterion']}: {a['reason']}")
        print(f"\n→ Document these in report section C.")
        print(f"  Explain WHY they're absent (e.g., 'The study area in")
        print(f"  [town] does not contain any SSSIs, so this criterion")
        print(f"  had no effect on the suitability output.')")
    else:
        print("All criteria are active in the study area.")

    return absent
```

### Section D: Site Comparison and Recommendation
```python
def generate_site_comparison(sites_fc):
    """Generate a structured comparison of the 2 selected sites.

    Reads all proximity fields and produces a comparative summary
    that the user can adapt for section D of the report.
    """
    fields = [f.name for f in arcpy.ListFields(sites_fc)]
    dist_fields = [f for f in fields if f.startswith("DIST_")]

    sites = []
    with arcpy.da.SearchCursor(sites_fc, ["SITE_ID", "SITE_NAME", "AREA_HA",
                                           "DWELLINGS_EST", "ADJACENT_URBAN"]
                                           + dist_fields) as cursor:
        for row in cursor:
            site = dict(zip(["SITE_ID", "SITE_NAME", "AREA_HA",
                            "DWELLINGS_EST", "ADJACENT_URBAN"] + dist_fields, row))
            sites.append(site)

    if len(sites) < 2:
        print("Need at least 2 sites for comparison")
        return

    s1, s2 = sites[0], sites[1]

    print(f"\n{'='*70}")
    print(f"SITE COMPARISON — Section D Draft")
    print(f"{'='*70}\n")

    print(f"{'Criterion':<25} {'Site 1':>15} {'Site 2':>15} {'Better':>10}")
    print("-" * 65)

    # Area
    better = "Site 1" if s1["AREA_HA"] > s2["AREA_HA"] else "Site 2"
    print(f"{'Area (ha)':<25} {s1['AREA_HA']:>14.2f} {s2['AREA_HA']:>14.2f} {better:>10}")

    # Dwellings
    better = "Site 1" if s1["DWELLINGS_EST"] > s2["DWELLINGS_EST"] else "Site 2"
    print(f"{'Est. dwellings':<25} {s1['DWELLINGS_EST']:>15} {s2['DWELLINGS_EST']:>15} {better:>10}")

    # Urban adjacency
    adj1 = "Yes" if s1.get("ADJACENT_URBAN") else "No"
    adj2 = "Yes" if s2.get("ADJACENT_URBAN") else "No"
    print(f"{'Adjacent to urban':<25} {adj1:>15} {adj2:>15}")

    # Proximity fields (lower = better)
    for df in dist_fields:
        v1 = s1.get(df)
        v2 = s2.get(df)
        if v1 is not None and v2 is not None:
            better = "Site 1" if v1 < v2 else "Site 2"
            label = df.replace("DIST_", "Dist to ")
            print(f"{label:<25} {v1:>14.0f}m {v2:>14.0f}m {better:>10}")

    print(f"\n--- Draft recommendation ---")
    print(f"Based on the comparison above, Claude should draft:")
    print(f"  'Site [X] is recommended because [reasons from table].'")
    print(f"  'While Site [Y] scores better on [criterion], Site [X]'")
    print(f"  'offers [key advantages] which align with NPPF (2024)'")
    print(f"  'objectives for sustainable development (para 8).'")
    print(f"\nThe user should review and personalise this text.")

generate_site_comparison("selected_sites")
```

### Section E: Suggested Additional Criteria
```
Claude should suggest criteria that COULD improve the model but were
not included. Draft structure:

"The model could be improved by incorporating the following criteria:

1. [Criterion name]: [Why it matters]. [Academic/policy reference].
   This was not included due to [data availability / scope].

2. [Criterion name]: [Why it matters]. [Academic/policy reference].
   This was not included due to [data availability / scope]."

Good suggestions to draw from:
- Noise pollution contours (WHO, 2018)
- Air quality zones (DEFRA, local authority data)
- Soil percolation / drainage (BGS data)
- Landscape character assessment (local authority)
- Archaeological potential (Historic Environment Record)
- Climate change flood projections (EA)
- Walking distance to public transport (CIHT, 2015)
```

### Section F: Reference List (Harvard format)
```
Standard references for UK housing suitability analysis:

Department for Levelling Up, Housing and Communities (2024) National
  Planning Policy Framework. London: HMSO. Available at:
  https://www.gov.uk/government/publications/national-planning-policy-framework
  (Accessed: [DATE]).

Environment Agency (2024) Flood Map for Planning. Available at:
  https://www.data.gov.uk/dataset/flood-map-for-planning (Accessed: [DATE]).

Historic England (2017) The Setting of Heritage Assets: Historic Environment
  Good Practice Advice in Planning Note 3. 2nd edn. Available at:
  https://historicengland.org.uk/images-books/publications/gpa3-setting-of-heritage-assets/
  (Accessed: [DATE]).

Homes England (2024) Strategic Plan 2023–2028. Available at:
  https://www.gov.uk/government/publications/homes-england-strategic-plan-2023-to-2028
  (Accessed: [DATE]).

Malczewski, J. (2004) 'GIS-based land-use suitability analysis: a critical
  overview', Progress in Planning, 62(1), pp. 3–65.
  doi:10.1016/j.progress.2003.09.002.

Natural England (2024) Agricultural Land Classification: Protecting the Best
  and Most Versatile Agricultural Land. Available at:
  https://magic.defra.gov.uk (Accessed: [DATE]).

Natural England (2024) Priority Habitat Inventory. Available at:
  https://magic.defra.gov.uk (Accessed: [DATE]).

Ordnance Survey (2024) OS VectorMap Local. Available at:
  https://digimap.edina.ac.uk (Accessed: [DATE]).

Watson, J.J.W. and Hudson, M.D. (2015) 'Regional Scale wind farm and solar
  farm suitability assessment using GIS-assisted multi-criteria evaluation',
  Landscape and Urban Planning, 138, pp. 20–31.
  doi:10.1016/j.landurbplan.2015.02.001.

World Health Organization (2018) Environmental Noise Guidelines for the
  European Region. Copenhagen: WHO Regional Office for Europe.
```

### Flood Warning vs Flood Alert — Important Distinction

The brief may reference both. They are DIFFERENT EA datasets:

| Dataset | What It Means | Use In Analysis |
|---------|---------------|-----------------|
| **Flood Zones 2 & 3** | Planning zones based on probability | Common exclusion layer (Zones 2/3 = unsuitable) |
| **Flood Warning Areas** | Operational: EA can issue flood warnings here | Stronger exclusion — these areas have KNOWN flood risk |
| **Flood Alert Areas** | Operational: EA can issue flood alerts (wider) | Desirable criterion only — show on Map 3, don't exclude |

```python
# Load BOTH flood datasets — they serve different purposes
# Flood Warning Areas → EXCLUSION (essential criterion)
arcpy.conversion.FeatureClassToFeatureClass(
    r"C:\Data\EA\Flood_Warning_Areas.shp", GDB, "flood_warning"
)
arcpy.analysis.Clip("flood_warning", "study_area", "flood_warning_clip")

# Flood Alert Areas → DESIRABLE only (Map 3 layer, NOT in model)
arcpy.conversion.FeatureClassToFeatureClass(
    r"C:\Data\EA\Flood_Alert_Areas.shp", GDB, "flood_alert"
)
arcpy.analysis.Clip("flood_alert", "study_area_2km", "flood_alert_clip")
# Clipped to 2km buffer because it's context for Map 3, not exclusion
```
