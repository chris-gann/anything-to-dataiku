# Prepare Recipe Processors

Complete reference for all processor types used in Dataiku prepare recipes.

## Pitfalls

**Prefer `add_processor_step()`** over `raw_steps.append()`. Both work, but `add_processor_step()` is the official API method. With `add_processor_step()`, pass params directly (no wrapping `"params"` key). With `raw_steps.append()`, wrap under `"params"`.

**GREL functions:** Before writing any GREL expression, read [grel-functions.md](grel-functions.md). Do not guess function names — Dataiku GREL differs from OpenRefine.

## Common Cleaning Processors

```python
project = client.get_project("PROJECT_KEY")

builder = project.new_recipe("prepare", "clean_data")
builder.with_input("raw_data")
builder.with_new_output("clean_data", "dataiku-managed-storage")
recipe = builder.create()

settings = recipe.get_settings()

# Trim whitespace from text columns
settings.add_processor_step("ColumnTrimmer", {
    "columns": ["name", "address"]
})

# Lowercase for consistency
settings.add_processor_step("ColumnLowercaser", {
    "columns": ["email"]
})

# Remove duplicates
settings.add_processor_step("RemoveDuplicates", {
    "columns": ["id"]
})

# Fill nulls with default
settings.add_processor_step("FillEmptyWithValue", {
    "appliesTo": "SINGLE_COLUMN",
    "columns": ["status"],
    "value": "unknown"
})

settings.save()
```

## CreateColumnWithGREL

Add calculated or derived columns using GREL expressions.

```python
# Add revenue column
{
    "type": "CreateColumnWithGREL",
    "params": {
        "column": "revenue",
        "expression": "price * quantity"
    }
}

# String concatenation
{
    "type": "CreateColumnWithGREL",
    "params": {
        "column": "full_name",
        "expression": "first_name + ' ' + last_name"
    }
}

# Conditional logic
{
    "type": "CreateColumnWithGREL",
    "params": {
        "column": "size_category",
        "expression": "if(amount > 1000, 'large', if(amount > 100, 'medium', 'small'))"
    }
}

# Date extraction
{
    "type": "CreateColumnWithGREL",
    "params": {
        "column": "year",
        "expression": "datePart(order_date, 'year')"
    }
}

# Merge columns
{
    "type": "CreateColumnWithGREL",
    "params": {
        "column": "address_full",
        "expression": "street + ', ' + city + ', ' + state + ' ' + zip"
    }
}
```

## FilterOnValue

Keep or remove rows matching specific column values.

```python
{
    "type": "FilterOnValue",
    "params": {
        "column": "status",
        "values": ["active", "pending"],
        "action": "KEEP"  # or "REMOVE"
    }
}
```

## FilterOnFormula

Keep or remove rows using a GREL boolean expression.

```python
# Filter by formula
{
    "type": "FilterOnFormula",
    "params": {
        "formula": "amount > 0 && isNotBlank(customer_id)",
        "action": "KEEP"
    }
}

# Filter by date range
{
    "type": "FilterOnFormula",
    "params": {
        "formula": "order_date >= '2024-01-01' && order_date < '2025-01-01'",
        "action": "KEEP"
    }
}
```

## ColumnRenamer

Rename one or more columns.

```python
{
    "type": "ColumnRenamer",
    "params": {
        "renamings": [
            {"from": "old_name", "to": "new_name"}
        ]
    }
}
```

## ColumnsSelector

Keep or remove a set of columns.

```python
# Keep only specific columns (in order)
{
    "type": "ColumnsSelector",
    "params": {
        "columns": ["id", "name", "amount", "date"],
        "keep": True
    }
}

# Remove columns
{
    "type": "ColumnsSelector",
    "params": {
        "columns": ["temp_col", "debug_col"],
        "keep": False
    }
}
```

## ColumnSplitter

Split a column by delimiter into new columns.

```python
{
    "type": "ColumnSplitter",
    "params": {
        "column": "full_name",
        "separator": " ",
        "outColumns": ["first_name", "last_name"]
    }
}
```

## Complete Example: Sales Data Prep

End-to-end example creating a prepare recipe that cleans, enriches, filters, and selects columns from a raw sales dataset.

```python
project = client.get_project("PROJECT_KEY")

builder = project.new_recipe("prepare", "prepare_sales")
builder.with_input("raw_sales")
builder.with_new_output("clean_sales", "dataiku-managed-storage")
recipe = builder.create()

settings = recipe.get_settings()

# Clean text fields
settings.add_processor_step("ColumnTrimmer", {
    "columns": ["customer_name", "product"]
})

# Standardize case
settings.add_processor_step("ColumnLowercaser", {
    "columns": ["email"]
})

# Add calculated fields
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "revenue",
    "expression": "price * quantity"
})
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "month",
    "expression": "datePart(order_date, 'month')"
})

# Filter valid records
settings.add_processor_step("FilterOnFormula", {
    "formula": "quantity > 0 && isNotBlank(customer_id)",
    "action": "KEEP"
})

# Keep only needed columns
settings.add_processor_step("ColumnsSelector", {
    "columns": ["order_id", "customer_id", "product", "revenue", "month", "order_date"],
    "keep": True
})

settings.save()

# Apply schema and run
schema_updates = recipe.compute_schema_updates()
if schema_updates.any_action_required():
    schema_updates.apply()

job = recipe.run(no_fail=True)
state = job.get_status()["baseStatus"]["state"]
print(f"Job completed with status: {state}")
```
