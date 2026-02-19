---
name: arcgis-project
description: Start or load an ArcGIS project — sets up context files for datasets, parameters, and materials from PDFs/briefs
user-invocable: true
argument-hint: "[project name or description]"
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# ArcGIS Project

Start a new ArcGIS project or load an existing one. This sets up a structured
context directory where you store your datasets, parameters, materials from
PDFs, and project brief. Claude Code reads all of these when helping you write
arcpy scripts.

## When to use

Use /arcgis-project when:
- Starting a new ArcGIS analysis from scratch
- Loading an existing project so Claude Code has full context
- The user mentions a new assignment, brief, or analysis task

## Starting a new project

1. Create the project directory from the template:

```bash
cp -r packs/arcgis/projects/.template packs/arcgis/projects/$ARGUMENTS
```

Replace spaces in the project name with hyphens. Use kebab-case.

2. Tell the user their project is set up and explain the files:

   - **BRIEF.md** — Describe what you're building: objective, study area, deliverables, coordinate system
   - **DATASETS.md** — List every dataset with source path, format, geometry type, key fields, CRS
   - **PARAMETERS.md** — Analysis thresholds, buffer distances, classification rules, output specs
   - **MATERIALS.md** — Paste content from PDFs, assignment briefs, emails, specifications here
   - **NOTES.md** — Running notes and decisions across sessions

3. Ask the user: "What do you have to start with? You can paste your assignment brief,
   list your datasets, or describe what you need to analyze and I'll help fill these in."

## Loading an existing project

1. Look in `packs/arcgis/projects/` for existing projects:

```bash
ls packs/arcgis/projects/
```

2. Read ALL the context files for the project:

```
packs/arcgis/projects/<name>/BRIEF.md
packs/arcgis/projects/<name>/DATASETS.md
packs/arcgis/projects/<name>/PARAMETERS.md
packs/arcgis/projects/<name>/MATERIALS.md
packs/arcgis/projects/<name>/NOTES.md
```

3. Also read the general ArcGIS domain knowledge:
```
packs/arcgis/CONTEXT.md
```

4. Summarize what you know about the project and ask what the user wants to work on next.

## Working on a project

Once context is loaded, you have everything needed to:
- Write arcpy scripts tailored to their specific datasets and field names
- Use the correct coordinate system and spatial references
- Apply the exact buffer distances, thresholds, and classification rules
- Produce outputs matching their deliverable requirements
- Reference their pasted materials for assignment-specific requirements

Always update NOTES.md with decisions and progress at the end of significant work.

$ARGUMENTS
