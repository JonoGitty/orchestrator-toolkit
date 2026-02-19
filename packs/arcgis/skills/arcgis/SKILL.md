---
name: arcgis
description: Help with ArcGIS Pro, arcpy scripting, geospatial analysis — reads project context if available
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

## First: Load context

1. Read the arcpy domain knowledge:
```
@CONTEXT.md
```

2. Check if there are any active projects with stored context:
```bash
ls packs/arcgis/projects/ 2>/dev/null
```

3. If a project exists, read ALL its context files to understand the user's
   specific datasets, parameters, and materials:
```
packs/arcgis/projects/<name>/BRIEF.md
packs/arcgis/projects/<name>/DATASETS.md
packs/arcgis/projects/<name>/PARAMETERS.md
packs/arcgis/projects/<name>/MATERIALS.md
packs/arcgis/projects/<name>/NOTES.md
```

4. If no project exists and the user seems to be working on something specific,
   suggest: "Want me to set up a project so I can keep track of your datasets
   and parameters? Use /arcgis-project"

## Approach

1. Understand the geospatial task — read project context if available
2. Use the EXACT field names, dataset paths, and CRS from DATASETS.md
3. Apply the EXACT thresholds and parameters from PARAMETERS.md
4. Follow arcpy patterns from CONTEXT.md
5. Write complete, runnable scripts (not fragments)
6. Validate results with GetCount, Describe, or print statements
7. Update NOTES.md with what was done

## Writing scripts

When writing arcpy scripts, always:
- Start with `import arcpy` and environment setup
- Use the user's actual workspace path and dataset names
- Apply their coordinate system (from BRIEF.md or DATASETS.md)
- Use `arcpy.env.overwriteOutput = True`
- Include error handling with `arcpy.ExecuteError`
- Print progress messages so the user can track execution
- End with a summary of what was created/modified

$ARGUMENTS
