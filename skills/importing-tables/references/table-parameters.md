# Table Parameters by Connection Type

## Parameter Keys

Each SQL connection type uses slightly different parameter keys in the dataset's `params` dict:

| Connection Type | Schema Key | Table Key | Extra Keys |
|-----------------|-----------|-----------|------------|
| `PostgreSQL` | `schema` | `table` | — |
| `MySQL` | `schema` | `table` | — |
| `Snowflake` | `schema` | `table` | `catalog` (database name) |
| `BigQuery` | `dataset` | `table` | — |
| `Oracle` | `schema` | `table` | — |
| `SQLServer` | `schema` | `table` | `catalog` (database name) |
| `Redshift` | `schema` | `table` | — |

## Snowflake Naming

Snowflake uses a three-level hierarchy: `database.schema.table`. In Dataiku:

```python
params = {
    "connection": "my_snowflake",
    "catalog": "MY_DATABASE",   # Snowflake database
    "schema": "RAW",            # Snowflake schema
    "table": "ORDERS"           # Snowflake table
}
```

> **Important:** Always use UPPERCASE for Snowflake table and column names. Lowercase names get quoted, causing `"invalid identifier"` errors.

## BigQuery Naming

BigQuery uses `project.dataset.table`. In Dataiku:

```python
params = {
    "connection": "my_bigquery",
    "dataset": "raw_data",      # BigQuery dataset (not Dataiku dataset)
    "table": "orders"           # BigQuery table
}
```

> The BigQuery `dataset` parameter is the BigQuery dataset name, not to be confused with a Dataiku dataset.

## Reading Dataset Parameters

```python
ds = project.get_dataset("MY_DATASET")
settings = ds.get_settings()
raw = settings.get_raw()

connection = raw["params"].get("connection")
schema = raw["params"].get("schema")
table = raw["params"].get("table")
print(f"Connection: {connection}, Schema: {schema}, Table: {table}")
```

## Pitfalls

**`create_dataset` type parameter:** The first `type` argument to `project.create_dataset()` is the connection type string (e.g., `"PostgreSQL"`, `"Snowflake"`), not the connection name. The connection name goes in `params["connection"]`.

**Auto-detect requires connectivity:** `autodetect_settings()` queries the actual database table. If the connection credentials are invalid or the table doesn't exist, it will fail silently and return an empty schema.
