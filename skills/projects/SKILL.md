---
name: projects
description: "Use when creating, configuring, duplicating, exporting, or deleting Dataiku projects including variables, permissions, and metadata"
---

# Project Management Patterns

Reference patterns for creating and managing Dataiku projects via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Project Key** | Unique identifier for a project (e.g., `"MYPROJECT"`) | Instance-level |
| **Project Variables** | Key-value pairs available to recipes and scenarios | Per project |
| **Project Metadata** | Label, description, tags, checklists, custom key-value pairs | Per project |
| **Permissions** | Group-based access control for project content | Per project |

## List and Access Projects

```python
# List all project keys
project_keys = client.list_project_keys()

# Get a project handle
project = client.get_project("MYPROJECT")

# Get current project (inside DSS)
project = client.get_default_project()
```

## Create a Project

```python
project = client.create_project(
    project_key="MYPROJECT",
    name="My Project",
    owner="alice"
)
```

> **Note:** `project_key` must be unique across the instance. Use UPPERCASE alphanumeric characters and underscores.

## Project Variables

Project variables are accessible in recipes, scenarios, and GREL formulas.

```python
# Get variables
variables = project.get_variables()
# Returns: {"standard": {...}, "local": {...}}

# Set standard variables (shared across environments)
variables["standard"]["input_table"] = "RAW_ORDERS"
variables["standard"]["target_schema"] = "ANALYTICS"
project.set_variables(variables)

# Set local variables (environment-specific, not exported)
variables["local"]["db_connection"] = "my_snowflake_dev"
project.set_variables(variables)
```

> Standard variables are included in project exports. Local variables are not — use them for environment-specific config like connection names.

## Project Metadata and Tags

```python
# Get and update metadata
metadata = project.get_metadata()
metadata["label"] = "Customer Churn Analysis"
metadata["description"] = "End-to-end churn prediction pipeline"
project.set_metadata(metadata)

# Get and set tags
tags = project.get_tags()
tags["tags"] = {"production": {}, "ml-pipeline": {}}
project.set_tags(tags)
```

## Project Settings

```python
settings = project.get_settings()

# Access raw settings dict
raw = settings.settings
raw["projectStatus"] = "Draft"  # or "InProgress", "Done"

# Save changes
settings.save()
```

## Permissions

```python
# Get current permissions
permissions = project.get_permissions()

# Add a group permission
permissions["permissions"].append({
    "group": "data-team",
    "admin": False,
    "readProjectContent": True,
    "readDashboards": True,
    "writeProjectContent": True,
    "writeDashboards": False
})
project.set_permissions(permissions)
```

## Duplicate a Project

```python
result = project.duplicate(
    target_project_key="MYPROJECT_COPY",
    target_project_name="My Project (Copy)",
    duplication_mode="MINIMAL"  # MINIMAL, SHARING, FULL, NONE
)
```

| Mode | Behavior |
|------|----------|
| `MINIMAL` | Structure only, no data |
| `SHARING` | Share datasets from original |
| `FULL` | Copy everything including data |
| `NONE` | Empty project with same settings |

## Export and Import

### Export a Project

```python
# Export to file
project.export_to_file("my_project_export.zip")

# Export with options
project.export_to_file("my_project_export.zip", options={
    "exportUploads": True,
    "exportManagedFS": True,
    "exportAnalysisModels": False,
    "exportSavedModels": True,
    "exportAllDatasets": False
})

# Export as stream
with project.get_export_stream() as stream:
    with open("export.zip", "wb") as f:
        for chunk in stream.stream(512):
            f.write(chunk)
```

### Import a Project

```python
with open("archive.zip", "rb") as f:
    import_result = client.prepare_project_import(f).execute()
```

## Delete a Project

```python
# Delete project (keeps underlying data by default)
project.delete()

# Delete with data cleanup
project.delete(
    clear_managed_datasets=True,
    clear_output_managed_folders=True,
    clear_job_and_scenario_logs=True
)
```

## List Project Contents

```python
# List all items in a project
datasets = project.list_datasets()
recipes = project.list_recipes()
scenarios = project.list_scenarios()
managed_folders = project.list_managed_folders()
saved_models = project.list_saved_models()
```

## Detailed References

- [references/project-variables.md](references/project-variables.md) — Variable types, resolution order, usage in recipes and GREL
- [references/project-permissions.md](references/project-permissions.md) — Full permission matrix, group management, owner transfer

## Related Skills

- [skills/dataset-management/](../dataset-management/) — Creating and managing datasets within projects
- [skills/flow-management/](../flow-management/) — Building and orchestrating project flows
- [skills/scenarios/](../scenarios/) — Automating project workflows
