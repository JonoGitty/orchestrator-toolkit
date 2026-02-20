---
name: arcgis-discover
description: Scan your ArcGIS map/geodatabase — list all datasets, inspect fields, check CRS, and get tool recommendations
user-invocable: true
argument-hint: "[map name, .aprx path, or .gdb path]"
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# ArcGIS Discover

Inventory and inspect everything in the user's map or geodatabase. Shows what
datasets are available, what fields they have, whether coordinate systems match,
and recommends the right geoprocessing tools for each dataset type.

## When to use

Use /arcgis-discover when the user:
- Wants to know what layers/data are in their map or geodatabase
- Says "what data do I have?" or "what's on my map?"
- Needs to understand their datasets before starting analysis
- Wants tool recommendations based on their data types
- Needs to check if coordinate systems are consistent
- Is starting a new project and wants to audit available data

## First: Load domain knowledge

Read the Dataset Discovery & Inspection section of CONTEXT.md:
```
@CONTEXT.md
```

## Discovery workflow

### Step 1: Determine the data source

Ask the user or infer from context:
- **ArcGIS Pro project (.aprx)**: scan all maps and layers
- **Geodatabase (.gdb)**: inventory all feature classes, tables, rasters
- **Folder of shapefiles**: list and describe each .shp
- **Active map in Pro**: use `arcpy.mp.ArcGISProject("CURRENT")`

### Step 2: Generate and run the inventory script

Write a complete arcpy script that:

1. **Lists every dataset** with name, type (vector/raster/table), and source path
2. **For each vector layer**: shape type, feature count, CRS, all field names + types
3. **For each raster layer**: dimensions, cell size, band count, pixel type, value range
4. **For tables**: row count, field names + types
5. **CRS consistency check**: flag if layers use different coordinate systems

Use the patterns from CONTEXT.md's "Dataset Discovery & Inspection" section.

### Step 3: Present findings as a structured report

Format the output clearly:

```
=== Map: [name] ===

VECTOR LAYERS:
  1. parcels (Polygon, 12,450 features, NZGD2000/NZTM)
     Fields: PARCEL_ID (Long), LAND_USE (Text), AREA_M2 (Double), ZONE (Text)
     Unique LAND_USE values: Residential, Commercial, Industrial, Rural

  2. roads (Polyline, 8,230 features, NZGD2000/NZTM)
     Fields: ROAD_ID (Long), NAME (Text), CLASS (Short), SPEED_LIM (Short)

RASTER LAYERS:
  3. dem (1200x900, 5m cells, Float32, range: 0.0 to 1847.3)

TABLES:
  4. survey_responses (2,100 rows)
     Fields: RESP_ID, DATE, SCORE, COMMENTS

CRS CHECK: All layers use NZGD2000/NZTM (EPSG:2193) ✓
```

### Step 4: Recommend tools for each dataset

Based on geometry type, suggest what the user can DO with each dataset.
Use the `suggest_tools()` pattern from CONTEXT.md:

- **Points** -> Buffer, Near, SpatialJoin, Kernel Density, Hot Spots, IDW
- **Polygons** -> Intersect, Union, Clip, Dissolve, SpatialJoin, Zonal Stats, Erase
- **Polylines** -> Buffer, Intersect, Near, Network Analyst, Split Line
- **Rasters** -> Slope, Aspect, Reclassify, Map Algebra, Contour, Zonal Stats
- **Tables** -> Join to spatial data, XY Table to Point (if has coordinates)

### Step 5: Update project context (if project exists)

Check for an active project:
```bash
ls packs/arcgis/projects/ 2>/dev/null
```

If a project exists, offer to update DATASETS.md with the discovered datasets:
- Dataset name and source path
- Geometry type and feature count
- Field names and types
- Coordinate system
- Any notable characteristics (mixed CRS, large feature counts, etc.)

## Tips

- If the user just says "discover" with no arguments, ask them for the path to
  their .aprx or .gdb, or suggest using `"CURRENT"` if they're in ArcGIS Pro
- Always run the CRS check — mixed coordinate systems is the #1 source of
  spatial analysis bugs
- Sample a few rows of data (5-10) so the user can verify field contents
- Flag any empty datasets (0 features) or datasets with all NULL values in key fields
- If a field has a domain, list the domain values
- Mention feature counts — some tools behave differently with very large datasets

$ARGUMENTS
