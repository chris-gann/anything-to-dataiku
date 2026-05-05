# Pattern: Data cleaning pipeline with multiple prepare steps
# Common cleaning operations: trim, lowercase, fill nulls, filter, rename

project = client.get_project("PROJECT_KEY")

builder = project.new_recipe("prepare", "compute_dataset_cleaned")
builder.with_input("raw_dataset")
builder.with_new_output("dataset_cleaned", "dataiku-managed-storage")
recipe = builder.create()

settings = recipe.get_settings()

# 1. Trim whitespace from text columns
settings.add_processor_step("ColumnTrimmer", {
    "columns": ["name", "email", "address"]
})

# 2. Lowercase for consistency
settings.add_processor_step("ColumnLowercaser", {
    "columns": ["email"]
})

# 3. Fill nulls with default values
settings.add_processor_step("FillEmptyWithValue", {
    "appliesTo": "SINGLE_COLUMN",
    "columns": ["status"],
    "value": "unknown"
})

# 4. Filter rows by formula (keep valid records)
settings.add_processor_step("FilterOnFormula", {
    "formula": "isNotBlank(customer_id) && toNumber(amount) > 0",
    "action": "KEEP"
})

# 5. Filter rows by value (keep specific statuses)
settings.add_processor_step("FilterOnValue", {
    "column": "status",
    "values": ["active", "pending"],
    "action": "KEEP"
})

# 6. Rename columns
settings.add_processor_step("ColumnRenamer", {
    "renamings": [
        {"from": "cust_id", "to": "customer_id"},
        {"from": "amt", "to": "amount"}
    ]
})

# 7. Keep only needed columns
settings.add_processor_step("ColumnsSelector", {
    "columns": ["customer_id", "name", "email", "amount", "status"],
    "keep": True
})

settings.save()

schema_updates = recipe.compute_schema_updates()
if schema_updates.any_action_required():
    schema_updates.apply()

job = recipe.run(no_fail=True)
state = job.get_status()["baseStatus"]["state"]
print("Job state:", state)

# ALWAYS verify output
from helpers.export import sample
rows = sample(client, "PROJECT_KEY", "dataset_cleaned", 5)
for r in rows:
    print(r)
