---
name: arcgis-ingest
description: Organize pasted content from PDFs, briefs, or specs into the right ArcGIS project context files
user-invocable: true
argument-hint: "[project name]"
allowed-tools: Read, Edit, Write, Glob
---

# ArcGIS Ingest

Help the user organize pasted content (from PDFs, assignment briefs, emails,
specifications) into the correct project context files.

## When to use

Use /arcgis-ingest when the user:
- Pastes a wall of text from a PDF or document
- Shares an assignment brief or project specification
- Has dataset descriptions, parameter tables, or requirements to organize
- Says something like "here's my brief" or "I got this from the assignment PDF"

## How to process pasted content

1. First, find or confirm the project:

```bash
ls packs/arcgis/projects/
```

If no project exists yet, create one first (see /arcgis-project).

2. Read the pasted content carefully and extract:

   **Project info** -> write to `BRIEF.md`:
   - Objective / purpose / research question
   - Study area / geographic extent
   - Expected deliverables (maps, reports, layers)
   - Coordinate system requirements
   - Timeline or milestones

   **Dataset descriptions** -> write to `DATASETS.md`:
   - Dataset names and sources (file paths, URLs, service endpoints)
   - Format (shapefile, GDB, CSV, raster, WFS)
   - Geometry type (point, line, polygon, raster, table)
   - Field names and types
   - Coordinate system
   - Feature counts

   **Analysis parameters** -> write to `PARAMETERS.md`:
   - Buffer distances
   - Classification thresholds and criteria
   - Spatial relationship rules
   - Output format and symbology requirements
   - Map export specifications (DPI, size, layout)

   **Everything else** -> append to `MATERIALS.md`:
   - The raw pasted text (preserved for reference)
   - Marking instructions or rubric criteria
   - Specific tool/method requirements
   - Example outputs or reference images mentioned

3. After organizing, summarize what was extracted:
   - "I've added X datasets to DATASETS.md"
   - "I've set up Y analysis parameters in PARAMETERS.md"
   - "The full brief is in MATERIALS.md for reference"

4. Ask if anything is missing or if they have more materials to add.

## Tips for extraction

- Look for tables — they often contain field definitions or parameter values
- Numbered lists often describe steps/methodology -> those are parameters
- "Using the data provided..." -> dataset descriptions follow
- "Your map should show..." -> deliverables and symbology requirements
- "Submit..." -> deliverables and export format
- Percentages, distances, counts -> analysis parameters
- File names ending in .shp, .gdb, .tif, .csv -> dataset references

$ARGUMENTS
