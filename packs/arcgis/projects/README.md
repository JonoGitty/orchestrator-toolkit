# ArcGIS Projects

Each subdirectory is a project with its own context files that Claude Code reads.

## Quick start

```bash
# Create a new project (copies the template)
python orchestrator.py new-skill arcgis  # if pack not yet created
# Or just copy the template:
cp -r .template my-flood-analysis
```

Or use `/arcgis-project` in Claude Code:
```
/arcgis-project flood risk analysis for Canterbury region
```

## Project structure

```
my-project/
    BRIEF.md        — What you're building, study area, deliverables
    DATASETS.md     — Every dataset: source, format, fields, CRS
    PARAMETERS.md   — Thresholds, buffer distances, classification rules
    MATERIALS.md    — Pasted content from PDFs, briefs, specs
    NOTES.md        — Running notes and decisions
```

## How Claude Code uses these files

When you use `/arcgis` or `/arcgis-project`, Claude reads:
1. `CONTEXT.md` (arcpy domain knowledge)
2. Your project's `BRIEF.md`, `DATASETS.md`, `PARAMETERS.md`, `MATERIALS.md`
3. And combines them to write scripts that match YOUR specific data and requirements
