# Pattern: Bin a numeric column stored as string into ranges
# Tested: 2026-03-03 on Dataiku Cloud
#
# Key insight: Use toNumber() to cast string columns to numeric.
# DO NOT use numval(), val(), toInt() — they return null silently.

project = client.get_project("PROJECT_KEY")

builder = project.new_recipe("prepare", "compute_dataset_binned")
builder.with_input("source_dataset")
builder.with_new_output("dataset_binned", "dataiku-managed-storage")
recipe = builder.create()

settings = recipe.get_settings()
settings.add_processor_step("CreateColumnWithGREL", {
    "column": "age_bin",
    "expression": (
        "if(toNumber(age) < 18, '<18', "
        "if(toNumber(age) < 35, '18-34', "
        "if(toNumber(age) < 50, '35-49', "
        "if(toNumber(age) < 65, '50-64', '65+'))))"
    )
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
rows = sample(client, "PROJECT_KEY", "dataset_binned", 5)
for r in rows:
    print(r['age'], '->', r['age_bin'])
