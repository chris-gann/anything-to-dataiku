---
name: sql-queries
description: "Use when running SQL queries against Dataiku connections, reading query results, or executing SQL in recipes"
---

# SQL Query Patterns

Reference patterns for executing SQL queries via the Dataiku Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **SQLExecutor2** | Runs SQL against a connection (inside DSS recipes/notebooks) | Inside DSS |
| **DSSSQLQuery** | Runs SQL via the API client (external scripts) | API client |
| **SQL Recipe** | A recipe that executes SQL and writes to an output dataset | Per project |

## Run SQL via API Client (External)

```python
query = client.sql_query(
    query="SELECT * FROM my_schema.my_table LIMIT 10",
    connection="my_postgres"
)

# Get column schema
schema = query.get_schema()
for col in schema["columns"]:
    print(f"{col['name']}: {col['type']}")

# Iterate over rows
for row in query.iter_rows():
    print(row)

# Verify no errors occurred
query.verify()
```

## Run SQL Inside DSS (Recipes/Notebooks)

### Query to DataFrame

```python
from dataiku.core.sql import SQLExecutor2

executor = SQLExecutor2(connection="my_postgres")
df = executor.query_to_df("SELECT * FROM public.customers LIMIT 100")
print(df.head())
```

### Query to Iterator (Large Results)

```python
executor = SQLExecutor2(connection="my_postgres")
reader = executor.query_to_iter("SELECT * FROM public.orders")

for row in reader.iter_rows():
    print(row)
```

### Query via Dataset Connection

```python
# Use the connection of an existing dataset
executor = SQLExecutor2(dataset="MY_DATASET")
df = executor.query_to_df("SELECT COUNT(*) as cnt FROM ${DKU_DST_MY_DATASET}")
```

## Execute SQL in a Recipe

```python
from dataiku.core.sql import SQLExecutor2

# Write query results to an output dataset
SQLExecutor2.exec_recipe_fragment(
    output_dataset=dataiku.Dataset("MY_OUTPUT"),
    query="SELECT id, name, amount FROM raw_orders WHERE amount > 100",
    pre_queries=["SET search_path TO analytics"],
    post_queries=[],
    overwrite_output_schema=True
)
```

## Pre and Post Queries

Use `pre_queries` for session setup (setting schema, variables) and `post_queries` for cleanup:

```python
df = executor.query_to_df(
    query="SELECT * FROM orders",
    pre_queries=[
        "SET search_path TO analytics",
        "SET statement_timeout = '30s'"
    ],
    post_queries=[
        "RESET search_path"
    ]
)
```

## Type Handling

```python
df = executor.query_to_df(
    query="SELECT * FROM my_table",
    infer_from_schema=True,   # Use database schema for type inference
    parse_dates=True,          # Parse date columns automatically
    bool_as_str=False          # Keep booleans as bool (True) or convert to str (False)
)
```

## Hive and Impala Queries

```python
from dataiku.core.sql import HiveExecutor, ImpalaExecutor

# Hive
hive = HiveExecutor(database="my_hive_db")
df = hive.query_to_df("SELECT * FROM my_table LIMIT 100")

# Impala
impala = ImpalaExecutor(database="my_impala_db")
df = impala.query_to_df("SELECT * FROM my_table LIMIT 100")
```

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `invalid identifier` | Lowercase column names in Snowflake | Use UPPERCASE column names |
| `relation does not exist` | Wrong schema or table name | Check `search_path` or fully qualify table names |
| Timeout | Large query without limits | Add `LIMIT` or increase timeout via `pre_queries` |
| Type mismatch in DataFrame | Wrong type inference | Use `infer_from_schema=True` or set `dtypes` parameter |

## Detailed References

- [references/sql-patterns.md](references/sql-patterns.md) — Common SQL patterns, parameterized queries, database-specific syntax

## Related Skills

- [skills/connections/](../connections/) — Managing SQL connections
- [skills/importing-tables/](../importing-tables/) — Creating datasets from SQL tables
- [skills/troubleshooting/](../troubleshooting/) — SQL error diagnosis
