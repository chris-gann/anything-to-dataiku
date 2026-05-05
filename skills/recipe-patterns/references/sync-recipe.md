# Sync Recipe

Use for: Copying data between connections (e.g., to a data warehouse).

## Pitfalls

**Column case for SQL:** SQL connections (PostgreSQL, Redshift, etc.) may require UPPERCASE column names. If you get "invalid identifier" errors after syncing, force uppercase on the target dataset schema before building.

**Use `with_new_output` for new datasets:** `with_output()` requires the dataset to already exist. Use `with_new_output("name", "connection")` to create it as part of recipe creation (see preferred example below).

## Creating with a new output dataset (preferred)

Use `with_new_output` to create the output dataset automatically as part of recipe creation — no need to create the dataset separately first.

```python
builder = project.new_recipe("sync", "sync_to_warehouse")
builder.with_input("source_dataset")
builder.with_new_output("target_dataset", "connection_name")
recipe = builder.create()

settings = recipe.get_settings()
settings.save()

job = recipe.run(no_fail=True)
```

## Using an existing output dataset

Use `with_output` when the output dataset already exists.

```python
builder = project.new_recipe("sync", "sync_to_warehouse")
builder.with_input("source_dataset")
builder.with_output("existing_target_dataset")
recipe = builder.create()

settings = recipe.get_settings()
settings.save()

job = recipe.run(no_fail=True)
```
