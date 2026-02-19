---
name: arcgis
description: Help with ArcGIS Pro, arcpy geospatial analysis, mapping, and geodatabase operations
user-invocable: true
argument-hint: "[describe your GIS task]"
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# ArcGIS + arcpy

Geospatial analysis, mapping, and geodatabase automation using ArcGIS Pro and arcpy.

## When to use

Use /arcgis when the user needs help with:
- arcpy scripts (geoprocessing, cursors, spatial analysis)
- ArcGIS Pro map automation (.aprx projects, layouts, exports)
- Geodatabase operations (create, query, manage feature classes)
- Raster analysis (DEM, slope, map algebra via arcpy.sa)
- Network analysis (routing, service areas via arcpy.na)
- ArcGIS API for Python (web GIS, Portal, AGOL)
- Site suitability, geocoding, spatial joins, buffers

## Context

Refer to @CONTEXT.md for arcpy API patterns, best practices, common gotchas,
and example workflows.

## Approach

1. Understand the geospatial task and data sources involved
2. Set up the arcpy environment (workspace, coordinate system, overwrite)
3. Use appropriate arcpy modules (da, sa, na, mp, analysis, management)
4. Follow the patterns in CONTEXT.md for cursors, geoprocessing, and map automation
5. Validate results with GetCount, Describe, or visual inspection

$ARGUMENTS
