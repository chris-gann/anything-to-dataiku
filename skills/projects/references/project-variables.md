# Project Variables

## Variable Types

| Type | Scope | Exported | Use Case |
|------|-------|----------|----------|
| **Standard** | Shared across environments | Yes | Table names, schema names, business parameters |
| **Local** | Environment-specific | No | Connection names, file paths, credentials |

## Get and Set Variables

```python
variables = project.get_variables()

# Structure:
# {
#   "standard": {"key1": "value1", ...},
#   "local": {"key2": "value2", ...}
# }

# Set a standard variable
variables["standard"]["target_table"] = "CUSTOMERS_CLEAN"
project.set_variables(variables)
```

## Using Variables in Recipes

In SQL recipes and GREL formulas, project variables are referenced as `${variable_name}`:

```sql
SELECT * FROM ${target_schema}.${target_table}
```

In Python recipes:
```python
import dataiku
variables = dataiku.get_project_variables()
table_name = variables["standard"]["target_table"]
```

## Variable Resolution Order

When a variable name is used, Dataiku resolves in this order:
1. **Local** variables (highest priority)
2. **Standard** variables
3. **Global** variables (instance-level, set by admin)

> Local variables override standard variables with the same name. Use this for environment-specific overrides (e.g., dev vs. prod connection names).

## Bulk Variable Setup

```python
variables = project.get_variables()
variables["standard"].update({
    "source_connection": "raw_data",
    "target_connection": "analytics",
    "target_schema": "DWH",
    "batch_size": 10000,
})
variables["local"].update({
    "db_host": "dev-server.internal",
})
project.set_variables(variables)
```

## Pitfalls

**Variables are strings in GREL:** When using numeric variables in GREL formulas, cast them explicitly. `${batch_size}` returns the string `"10000"`, not an integer.

**Local variables are not exported:** If you export and re-import a project, local variables will be missing. Document required local variables so they can be re-set after import.
