# SQL Patterns

## Parameterized Queries with Project Variables

Inside DSS, use `${variable_name}` for project variable substitution:

```python
executor = SQLExecutor2(connection="my_postgres")
df = executor.query_to_df(
    "SELECT * FROM ${target_schema}.${target_table} WHERE date >= '${start_date}'"
)
```

> **Note:** Variable substitution happens at the Dataiku level, not at the database level. This is string interpolation, not parameterized queries — be aware of SQL injection risks if variables come from user input.

## Schema-Qualified Queries

Always fully qualify table names to avoid ambiguity:

```python
# PostgreSQL
df = executor.query_to_df("SELECT * FROM public.customers")

# Snowflake (use UPPERCASE)
df = executor.query_to_df("SELECT * FROM MY_DATABASE.RAW.ORDERS")

# BigQuery
df = executor.query_to_df("SELECT * FROM `my_project.raw_data.orders`")
```

## Aggregation Queries

```python
df = executor.query_to_df("""
    SELECT
        category,
        COUNT(*) as count,
        SUM(amount) as total_amount,
        AVG(amount) as avg_amount
    FROM orders
    GROUP BY category
    ORDER BY total_amount DESC
""")
```

## CREATE TABLE AS SELECT (CTAS)

For creating tables from query results outside of recipes:

```python
executor = SQLExecutor2(connection="my_postgres")
executor.query_to_df(
    "CREATE TABLE analytics.summary AS SELECT category, COUNT(*) as cnt FROM orders GROUP BY category",
    pre_queries=["DROP TABLE IF EXISTS analytics.summary"]
)
```

## Database-Specific Syntax

### Snowflake

```sql
-- Use UPPERCASE identifiers
SELECT CUSTOMER_ID, ORDER_DATE FROM RAW.ORDERS
-- Use :: for type casting
SELECT AMOUNT::NUMBER(10,2) FROM ORDERS
-- Use FLATTEN for semi-structured data
SELECT f.value FROM ORDERS, LATERAL FLATTEN(input => JSON_DATA) f
```

### BigQuery

```sql
-- Use backticks for project-qualified names
SELECT * FROM `my-project.dataset.table`
-- Use SAFE_ prefix for null-safe functions
SELECT SAFE_DIVIDE(a, b) FROM my_table
-- Use STRUCT for nested data
SELECT STRUCT(name, age) as person FROM users
```

## Pitfalls

**`query_to_df()` loads everything into memory:** For large result sets, use `query_to_iter()` instead to process rows one at a time.

**`exec_recipe_fragment()` is static:** Call it as `SQLExecutor2.exec_recipe_fragment(...)`, not on an instance.

**Connection vs dataset parameter:** `SQLExecutor2(connection="name")` uses a named connection. `SQLExecutor2(dataset="name")` uses the connection of an existing dataset. Don't mix them.
