# Pattern: Common GREL calculated column formulas
# Reference for CreateColumnWithGREL processor expressions
#
# IMPORTANT: Always verify function names against references/grel-functions.md
# Dataiku GREL is NOT the same as OpenRefine GREL.

project = client.get_project("PROJECT_KEY")

builder = project.new_recipe("prepare", "compute_dataset_enriched")
builder.with_input("source_dataset")
builder.with_new_output("dataset_enriched", "dataiku-managed-storage")
recipe = builder.create()

settings = recipe.get_settings()

# --- Math ---
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "revenue",
    "expression": "price * quantity"
})

# --- Conditional / Binning ---
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "size_category",
    "expression": "if(toNumber(amount) > 1000, 'large', if(toNumber(amount) > 100, 'medium', 'small'))"
})

# --- String concatenation ---
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "full_name",
    "expression": "first_name + ' ' + last_name"
})

# --- Date extraction (requires parsed date column) ---
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "order_month",
    "expression": "datePart(order_date, 'month')"
})

# --- Null handling ---
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "display_name",
    "expression": "coalesce(preferred_name, first_name)"
})

# --- Boolean flag ---
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "is_high_value",
    "expression": "if(toNumber(amount) > 500, 'true', 'false')"
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
rows = sample(client, "PROJECT_KEY", "dataset_enriched", 5)
for r in rows:
    print(r)
