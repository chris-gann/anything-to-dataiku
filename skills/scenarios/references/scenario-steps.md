# Scenario Steps

## Step-Based vs Python Script Scenarios

Dataiku supports two scenario types:

| Type | Configuration | Use When |
|------|--------------|----------|
| **Step-based** | Configured via `raw_steps` list | Simple build/check workflows |
| **Python script** | Full Python code | Complex logic, conditional execution |

## Step-Based Scenario Steps

Access steps via `settings.raw_steps`:

```python
settings = scenario.get_settings()
# settings is a StepBasedScenarioSettings instance

steps = settings.raw_steps
for step in steps:
    print(f"{step['name']} ({step['type']})")
```

### Common Step Types

| Step Type | Purpose |
|-----------|---------|
| `build_flowitem` | Build a dataset or managed folder |
| `run_scenario` | Run another scenario |
| `exec_sql` | Execute SQL queries |
| `python` | Run Python code |
| `set_project_vars` | Set project variables |
| `clear_items` | Clear dataset or folder contents |
| `check_dataset` | Run data quality checks |
| `compute_metrics` | Compute dataset metrics |

### Step Structure

Each step is a dict with these fields:

```python
{
    "id": "step_unique_id",
    "name": "Human-readable name",
    "type": "build_flowitem",
    "params": {
        # Type-specific parameters
    }
}
```

## Python Script Scenarios

Access the script code directly:

```python
settings = scenario.get_settings()
# settings is a PythonScriptBasedScenarioSettings instance

# Read the code
print(settings.code)

# Update the code
settings.code = """
import dataiku
from dataiku.scenario import Scenario

scenario = Scenario()

# Build a dataset
scenario.build("MY_DATASET")

# Check outcome
step = scenario.get_previous_steps_outcomes()
if step[-1]["outcome"] == "FAILED":
    scenario.set_scenario_variables(error="Build failed")
"""
settings.save()
```

## Pitfalls

**`raw_steps` is a live reference:** Modifying the list returned by `settings.raw_steps` modifies the settings directly. Always call `settings.save()` after changes.

**Step IDs must be unique:** When adding steps programmatically, ensure each step has a unique `id` field. Duplicate IDs cause undefined behavior.
