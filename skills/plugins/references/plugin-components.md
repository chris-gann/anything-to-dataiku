# Plugin Components

## Plugin Structure

A typical Dataiku plugin contains:

```
my-plugin/
├── plugin.json              # Plugin metadata and version
├── python-lib/              # Shared Python code
│   └── my_module.py
├── python-connectors/       # Custom dataset connectors
│   └── my-connector/
│       └── connector.py
├── python-recipes/          # Custom recipes
│   └── my-recipe/
│       ├── recipe.json
│       └── recipe.py
├── python-runnables/        # Macros
│   └── my-macro/
│       ├── runnable.json
│       └── runnable.py
├── resource/                # Static resources (JS, CSS)
└── code-env/
    └── python/
        └── spec/
            └── requirements.txt
```

## Component Types

| Component | Directory | Purpose |
|-----------|-----------|---------|
| **Connector** | `python-connectors/` | Custom dataset types |
| **Recipe** | `python-recipes/` | Custom recipe types |
| **Macro** | `python-runnables/` | One-click actions |
| **Webapp** | `webapps/` | Custom web applications |
| **Custom Check** | `python-checks/` | Data quality checks |
| **Custom Metric** | `python-probes/` | Dataset metrics |

## Presets

Presets are reusable parameter configurations for plugin components:

```python
plugin = client.get_plugin("my-plugin-id")
settings = plugin.get_settings()

# Access parameter sets (preset definitions)
raw = settings.get_raw()
parameter_sets = raw.get("parameterSets", [])
```

## Plugin Usages

```python
usages = plugin.list_usages("MY_PROJECT")

# The usages object contains info about which components are in use
# and any missing types (components that were removed from the plugin)
```

## Pitfalls

**Admin permissions required:** Most plugin management operations (install, update, delete) require admin or developer permissions on the DSS instance.

**Code env must match plugin requirements:** After updating a plugin, always call `plugin.update_code_env()` to ensure the code environment has the correct packages.

**`force=True` on delete:** If a plugin is referenced by recipes or datasets, `delete()` will fail unless `force=True` is passed. This removes the plugin but leaves orphaned references.
