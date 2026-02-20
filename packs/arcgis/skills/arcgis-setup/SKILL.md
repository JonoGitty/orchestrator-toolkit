---
name: arcgis-setup
description: Find ArcGIS Pro, scan a USB/folder for data, match datasets to your brief, and set up everything to start working
user-invocable: true
argument-hint: "[path to USB/folder, or 'scan' to auto-detect]"
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# ArcGIS Setup

One-shot setup: find ArcGIS Pro on the machine, scan the user's data directory
(USB drive, Downloads folder, or any path), identify every GIS dataset,
match what's found to the project brief, and tell the user exactly what they
have and what's missing.

## When to use

Use /arcgis-setup when the user:
- Says "I plugged in my USB" or "my data is on this drive"
- Says "set up my project" or "find my data"
- Wants to know if ArcGIS Pro is installed and where it is
- Wants to point Claude at a folder and have it figure everything out
- Needs to match available data to an assignment brief
- Is starting from scratch and needs the full setup

## First: Load domain knowledge

Read the relevant sections of CONTEXT.md:
```
@CONTEXT.md
```

Pay special attention to:
- "Environment Detection & Setup" section
- "UK Geospatial Data Sources & Patterns" section
- "Dataset Discovery & Inspection" section

## Setup workflow

### Phase 1: Find ArcGIS Pro

Generate and present a Python script that detects where ArcGIS Pro is installed.
The script checks (in order):

1. **Windows Registry** — most reliable:
   ```python
   import winreg
   key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
       r"SOFTWARE\ESRI\ArcGISPro")
   install_dir = winreg.QueryValueEx(key, "InstallDir")[0]
   ```

2. **Default install paths**:
   - `C:\Program Files\ArcGIS\Pro\`
   - `C:\ArcGIS\Pro\`
   - `D:\ArcGIS\Pro\`

3. **Conda environment** (where arcpy lives):
   - `C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\`
   - Check `python.exe` and `arcpy` importability

4. **ArcGIS Pro projects on disk** — search for `.aprx` files:
   ```python
   # Check common locations for .aprx files
   import glob
   search_paths = [
       os.path.expanduser("~\\Documents\\ArcGIS\\Projects\\**\\*.aprx"),
       "D:\\**\\*.aprx",  # secondary drives
   ]
   ```

Tell the user:
- Where ArcGIS Pro is installed (or if it's not found)
- Which Python environment has arcpy
- What version is installed
- What extensions are licensed

### Phase 2: Scan user's data directory

Ask the user: **"Where is your data? Give me the path — USB drive letter,
Downloads folder, or any directory."**

If the user provides a path (e.g., `E:\`, `D:\GIS_Data`, `C:\Users\me\Downloads`),
generate a Python script that walks the entire directory and catalogues every
GIS-relevant file:

**File types to detect:**

| Extension | Type | What it is |
|-----------|------|------------|
| `.shp` (+`.dbf`,`.shx`,`.prj`) | Vector | Shapefile |
| `.gdb` (folder) | Vector/Raster | File Geodatabase |
| `.gpkg` | Vector | GeoPackage |
| `.geojson`, `.json` | Vector | GeoJSON |
| `.kml`, `.kmz` | Vector | Google Earth format |
| `.gml` | Vector | Geography Markup Language |
| `.tab`, `.mif` | Vector | MapInfo format |
| `.tif`, `.tiff` | Raster | GeoTIFF |
| `.img` | Raster | ERDAS Imagine |
| `.asc` | Raster | ASCII Grid (DTM, DEM) |
| `.ecw` | Raster | Enhanced Compressed Wavelet |
| `.jp2` | Raster | JPEG 2000 |
| `.sid` | Raster | MrSID |
| `.las`, `.laz` | Point Cloud | LiDAR |
| `.lasd` | Point Cloud | LAS Dataset |
| `.csv`, `.xlsx` | Tabular | May contain coordinates |
| `.aprx` | Project | ArcGIS Pro project |
| `.mxd` | Project | ArcMap project (legacy) |
| `.lyrx`, `.lyr` | Symbology | Layer files |
| `.stylx` | Symbology | Style files |
| `.pdf` | Document | Possibly a brief or spec |

**The scan script should:**

```python
import os

def scan_for_gis_data(root_path):
    """Walk a directory tree and catalogue every GIS file."""
    GIS_EXTENSIONS = {
        # Vectors
        '.shp': 'Shapefile', '.gdb': 'File Geodatabase',
        '.gpkg': 'GeoPackage', '.geojson': 'GeoJSON',
        '.kml': 'KML', '.kmz': 'KMZ', '.gml': 'GML',
        # Rasters
        '.tif': 'GeoTIFF', '.tiff': 'GeoTIFF', '.img': 'ERDAS',
        '.asc': 'ASCII Grid', '.ecw': 'ECW', '.jp2': 'JPEG2000',
        # Point clouds
        '.las': 'LiDAR', '.laz': 'LiDAR Compressed',
        # Tabular
        '.csv': 'CSV', '.xlsx': 'Excel',
        # Projects
        '.aprx': 'ArcGIS Pro Project', '.mxd': 'ArcMap Project',
        # Documents
        '.pdf': 'PDF Document',
    }

    found = {'vector': [], 'raster': [], 'pointcloud': [],
             'tabular': [], 'project': [], 'document': []}

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Check for file geodatabases (they're folders ending in .gdb)
        for dirname in dirnames[:]:
            if dirname.endswith('.gdb'):
                found['vector'].append({
                    'path': os.path.join(dirpath, dirname),
                    'type': 'File Geodatabase',
                    'name': dirname,
                })

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in GIS_EXTENSIONS:
                continue
            full_path = os.path.join(dirpath, filename)
            entry = {
                'path': full_path,
                'type': GIS_EXTENSIONS[ext],
                'name': filename,
                'size_mb': os.path.getsize(full_path) / (1024*1024),
            }
            if ext in ('.shp', '.gpkg', '.geojson', '.kml', '.kmz', '.gml'):
                found['vector'].append(entry)
            elif ext in ('.tif', '.tiff', '.img', '.asc', '.ecw', '.jp2'):
                found['raster'].append(entry)
            elif ext in ('.las', '.laz'):
                found['pointcloud'].append(entry)
            elif ext in ('.csv', '.xlsx'):
                found['tabular'].append(entry)
            elif ext in ('.aprx', '.mxd'):
                found['project'].append(entry)
            elif ext == '.pdf':
                found['document'].append(entry)

    return found
```

### Phase 3: Identify what each dataset IS

For every dataset found, generate an arcpy script to inspect it:

**Vectors:**
```python
import arcpy
desc = arcpy.Describe(path)
print(f"Shape: {desc.shapeType}, CRS: {desc.spatialReference.name}")
print(f"Features: {arcpy.management.GetCount(path)[0]}")
fields = [(f.name, f.type) for f in arcpy.ListFields(path)
          if f.type not in ('OID', 'Geometry')]
```

**Rasters:**
```python
r = arcpy.Raster(path)
print(f"Size: {r.width}x{r.height}, Cell: {r.meanCellWidth}")
print(f"Range: {r.minimum} to {r.maximum}")
```

**CSVs** — check for coordinate columns:
```python
import csv
with open(path) as f:
    headers = csv.reader(f).__next__()
    coord_hints = [h for h in headers if any(
        kw in h.lower() for kw in
        ['lat', 'lon', 'x', 'y', 'east', 'north', 'coord']
    )]
    if coord_hints:
        print(f"Possible coordinate columns: {coord_hints}")
```

Present findings as a clear inventory:

```
=== DATA SCAN: E:\ ===

VECTOR DATA (7 files):
  1. Roads.shp — Polyline, 12,450 features, BNG (EPSG:27700)
     Fields: CLASS, NAME, NUMBER, LENGTH
     Likely: OS VectorMap Local road network
  2. Flood_Zone_3.shp — Polygon, 234 features, BNG
     Fields: TYPE, PROB_4BAND, SOURCE
     Likely: Environment Agency Flood Zone 3

RASTER DATA (4 files):
  3. su34_DTM_5m.asc — 2000x2000, 5m cells, Float32, range 45-312m
     Likely: Edina Digimap DTM5 tile (grid ref SU34)
  4. su35_DTM_5m.asc — 2000x2000, 5m cells, Float32
     Likely: Edina Digimap DTM5 tile (grid ref SU35)

TABULAR (1 file):
  5. survey_data.csv — 450 rows
     Has coordinate columns: EASTING, NORTHING
     -> Can convert to points with XYTableToPoint

PROJECTS (1 file):
  6. Assignment1.aprx — ArcGIS Pro project

DOCUMENTS (2 files):
  7. Assignment_Brief.pdf — 2.3 MB
  8. Marking_Criteria.pdf — 0.5 MB
```

### Phase 4: Match data to the project brief

If a project brief exists (either in BRIEF.md or as a PDF found during scan):

1. Read the brief to understand what analysis is required
2. For each requirement in the brief, check if matching data was found:

```
=== BRIEF vs DATA MATCH ===

Brief requires                    | Data found?         | Status
----------------------------------|---------------------|--------
Study area boundary               | NOT FOUND           | NEED TO CREATE
OS 1:25k basemap                  | basemap_25k.tif     | FOUND
Roads network                     | Roads.shp           | FOUND
Rail network                      | Rail.shp            | FOUND
Rivers                            | NOT FOUND           | MISSING
DTM (elevation)                   | 2x DTM5 tiles       | FOUND (need merge)
Flood zones                       | Flood_Zone_3.shp    | FOUND (Zone 2 MISSING)
Agricultural Land Classification  | NOT FOUND           | NEED TO DOWNLOAD
Priority Habitats                 | NOT FOUND           | NEED TO DOWNLOAD
Designated sites (SSSI, SAC, etc) | NOT FOUND           | NEED TO DOWNLOAD

ACTION ITEMS:
  1. Create study area polygon (digitise or define coordinates)
  2. Download Flood Zone 2 from data.gov.uk
  3. Download ALC from MAGIC (magic.defra.gov.uk)
  4. Download Priority Habitats from MAGIC
  5. Download SSSI/SAC/SPA/NNR from Natural England
  6. Merge the 2 DTM tiles before analysis
```

### Phase 5: Set up the project

If everything looks good, offer to:

1. **Create the project directory** (via /arcgis-project):
   ```
   packs/arcgis/projects/<name>/
   ```

2. **Auto-populate DATASETS.md** with everything found in the scan:
   - Path, format, CRS, field names
   - Which brief requirement each dataset satisfies

3. **Auto-populate PARAMETERS.md** with defaults from the brief:
   - Buffer distances, cell size, classification rules
   - Output format (JPEG 300dpi, A4, etc.)

4. **Copy or link the brief** into MATERIALS.md

5. **Generate a starter script** that:
   - Sets up the workspace and CRS
   - Creates the geodatabase
   - Loads all found datasets
   - Merges multi-tile rasters
   - Clips everything to the study area

## Quick-start examples

User says: "My USB is E:, my data is in E:\GIS, and my brief is E:\brief.pdf"
-> Scan E:\GIS for all data, read the brief PDF, do the match, set up project

User says: "Set up my project, everything is in Downloads"
-> Scan ~/Downloads, find what's there, ask about the brief

User says: "Where's ArcGIS Pro on my computer?"
-> Run detection script, report install location and version

User says: "Can you find my data?"
-> Ask for the path, then scan

## Tips

- USB drives on Windows are typically D:\, E:\, F:\ etc.
- Digimap downloads often land in Downloads as .zip files — remind the user to extract first
- If .shp files are missing .prj (no projection info), check if they're BNG by looking
  at coordinate values (UK BNG eastings are 6 digits starting with 1-6, northings 5-6 digits)
- OS VectorMap Local filenames often contain the grid reference (e.g., SU34, TQ38)
- DTM filenames usually contain grid reference + resolution (e.g., su34_DTM_5m.asc)
- Multiple .asc files with sequential grid references = tiles that need merging
- If a .gdb is found, always inventory its contents — it may contain multiple feature classes

$ARGUMENTS
