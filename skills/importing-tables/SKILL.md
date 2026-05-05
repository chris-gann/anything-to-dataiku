---
name: importing-tables
description: "Use when importing existing database tables as Dataiku datasets, pointing datasets at SQL tables, or syncing table schemas"
---

# Importing Tables as Datasets

Reference patterns for importing existing database tables into Dataiku projects as datasets via the Python API.

## When to Use This Skill

- Pointing a Dataiku dataset at an existing SQL table
- Importing tables from a database connection into a project
- Auto-detecting schema from an existing table
- Creating datasets that reference external tables without copying data

## Import a SQL Table as a Dataset

The most common pattern: create a dataset that points to an existing table in a SQL connection.

```python
# Create a dataset pointing to an existing SQL table
ds = project.create_dataset(
    "MY_DATASET",
    "PostgreSQL",  # Connection type
    params={
        "connection": "my_postgres",
        "table": "customers",
        "schema": "public"
    }
)

# Auto-detect the schema from the table
settings = ds.autodetect_settings(infer_storage_types=True)
settings.save()
```

## Connection-Specific Table Import

### Snowflake

```python
ds = project.create_dataset(
    "SNOWFLAKE_TABLE",
    "Snowflake",
    params={
        "connection": "my_snowflake",
        "schema": "RAW",
        "table": "ORDERS",
        "catalog": "MY_DATABASE"
    }
)
settings = ds.autodetect_settings(infer_storage_types=True)
settings.save()
```

### BigQuery

```python
ds = project.create_dataset(
    "BIGQUERY_TABLE",
    "BigQuery",
    params={
        "connection": "my_bigquery",
        "table": "orders",
        "dataset": "raw_data"  # BigQuery dataset (not Dataiku dataset)
    }
)
settings = ds.autodetect_settings(infer_storage_types=True)
settings.save()
```

## Import Multiple Tables

```python
tables_to_import = [
    {"name": "CUSTOMERS", "table": "customers", "schema": "public"},
    {"name": "ORDERS", "table": "orders", "schema": "public"},
    {"name": "PRODUCTS", "table": "products", "schema": "public"},
]

connection_name = "my_postgres"

for t in tables_to_import:
    # Check if dataset already exists
    existing = [d["name"] for d in project.list_datasets()]
    if t["name"] in existing:
        print(f"Skipping {t['name']} — already exists")
        continue

    ds = project.create_dataset(
        t["name"],
        "PostgreSQL",
        params={
            "connection": connection_name,
            "table": t["table"],
            "schema": t["schema"]
        }
    )
    settings = ds.autodetect_settings(infer_storage_types=True)
    settings.save()
    print(f"Imported {t['name']}")
```

## Import via Managed Dataset Builder

An alternative approach using the managed dataset builder:

```python
builder = project.new_managed_dataset("MY_TABLE")
builder.with_store_into("my_postgres")
ds = builder.create()

# Configure the table reference
settings = ds.get_settings()
raw = settings.get_raw()
raw["params"]["schema"] = "public"
raw["params"]["table"] = "customers"
settings.save()

# Detect schema
settings = ds.autodetect_settings(infer_storage_types=True)
settings.save()
```

## Verify the Import

```python
ds = project.get_dataset("MY_DATASET")

# Check the schema
schema = ds.get_settings().get_schema()
print(f"Columns: {len(schema['columns'])}")
for col in schema["columns"]:
    print(f"  {col['name']}: {col['type']}")

# Sample data to confirm connectivity
from helpers.export import sample
rows = sample(client, "PROJECT_KEY", "MY_DATASET", 5)
for r in rows:
    print(r)
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty schema | Table doesn't exist or wrong name | Verify table name and schema in the database |
| `invalid identifier` | Lowercase column names in Snowflake | Use UPPERCASE column names |
| Connection error | Wrong connection name or credentials | Test connection with `client.get_connection(name).test()` |
| Type mismatch | Auto-detect chose wrong types | Manually set schema with `settings.set_schema()` |

## Detailed References

- [references/table-parameters.md](references/table-parameters.md) — Connection-specific parameter keys, catalog vs schema vs dataset naming

## Related Skills

- [skills/connections/](../connections/) — Managing and testing connections
- [skills/dataset-management/](../dataset-management/) — Schema operations and dataset configuration
- [skills/troubleshooting/](../troubleshooting/) — SQL and connection error diagnosis
