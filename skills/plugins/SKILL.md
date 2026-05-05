---
name: plugins
description: "Use when installing, configuring, updating, or managing Dataiku plugins and their components"
---

# Plugin Management Patterns

Reference patterns for managing Dataiku plugins via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Plugin** | A package that extends Dataiku with custom recipes, datasets, macros, etc. | Instance-level |
| **Plugin Settings** | Instance-level configuration for a plugin | Instance-level |
| **Project Settings** | Project-specific plugin parameter overrides | Per project |
| **Preset** | A reusable set of plugin parameters | Per plugin |
| **Macro** | An executable action provided by a plugin | Per plugin |

## List Installed Plugins

```python
plugins = client.list_plugins()
for p in plugins:
    print(f"{p['id']} — version {p.get('version', 'unknown')}")
```

## Get a Plugin Handle

```python
plugin = client.get_plugin("my-plugin-id")
```

## Install a Plugin

### From the Dataiku Store

```python
plugin = client.get_plugin("my-plugin-id")
plugin.update_from_store()
```

### From a Zip File

```python
plugin = client.get_plugin("my-plugin-id")
with open("plugin.zip", "rb") as f:
    plugin.update_from_zip(f)
```

### From a Git Repository

```python
plugin = client.get_plugin("my-plugin-id")
plugin.update_from_git(
    repository_url="https://github.com/org/my-plugin.git",
    checkout="main",
    subpath=""
)
```

## Plugin Code Environment

Many plugins require a dedicated code environment:

```python
plugin = client.get_plugin("my-plugin-id")

# Create the plugin's code env
plugin.create_code_env(python_interpreter="PYTHON310", conda=False)

# Update an existing plugin code env
plugin.update_code_env()
```

## Plugin Settings

```python
plugin = client.get_plugin("my-plugin-id")

# Instance-level settings
settings = plugin.get_settings()
raw = settings.get_raw()
# ... modify raw settings ...
settings.save()

# Project-level settings
project_settings = plugin.get_project_settings("MY_PROJECT")
raw = project_settings.get_raw()
# ... modify ...
project_settings.save()
```

## Check Plugin Usages

```python
usages = plugin.list_usages("MY_PROJECT")
# Returns DSSPluginUsages with component usage info
```

## Plugin Files

```python
# List all files in the plugin
files = plugin.list_files()
print(files)

# Read a specific file
content = plugin.get_file("python-lib/my_module.py")

# Update a file
with open("updated_module.py", "rb") as f:
    plugin.put_file("python-lib/my_module.py", f)

# Rename or move files
plugin.rename_file("old_name.py", "new_name.py")
plugin.move_file("python-lib/old_path.py", "python-lib/new_path.py")
```

## Run a Plugin Macro

```python
macro = project.get_macro("my-plugin-id_macro-name")

# Run synchronously
result = macro.run(
    params={"param1": "value1", "param2": 42},
    wait=True
)

# Run asynchronously
run_id = macro.run(params={"param1": "value1"}, wait=False)

# Check status
status = macro.get_status(run_id)

# Get result
result = macro.get_result(run_id, as_type="json")

# Abort
macro.abort(run_id)
```

## Delete a Plugin

```python
plugin = client.get_plugin("my-plugin-id")
plugin.delete(force=False)  # force=True to delete even if in use
```

## Detailed References

- [references/plugin-components.md](references/plugin-components.md) — Plugin structure, component types, preset management

## Related Skills

- [skills/code-envs/](../code-envs/) — Managing plugin code environments
- [skills/recipe-patterns/](../recipe-patterns/) — Custom recipe types from plugins
