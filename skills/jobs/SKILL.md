---
name: jobs
description: "Use when building datasets, running jobs, checking job status, reading job logs, or aborting jobs"
---

# Job Management Patterns

Reference patterns for running and managing Dataiku jobs via the Python API.

## When to Use This Skill

- Building one or more datasets
- Checking whether a job succeeded or failed
- Reading job logs for error details
- Aborting a running job
- Running builds with specific strategies (recursive, forced, etc.)

## Build a Single Dataset via Recipe

The simplest way to build a dataset is through its recipe:

```python
recipe = project.get_recipe("my_recipe")
job = recipe.run(no_fail=True)
state = job.get_status()["baseStatus"]["state"]  # "DONE" or "FAILED"
```

> `recipe.run()` already waits for completion. Use `no_fail=True` to prevent exceptions on failure.

## Build via Job Builder

For more control, use the project-level job builder:

```python
job_builder = project.new_job('NON_RECURSIVE_FORCED_BUILD')
job_builder.with_output('MY_DATASET', object_type='DATASET')
job = job_builder.start_and_wait(no_fail=True)
```

### Build Multiple Outputs in One Job

```python
job_builder = project.new_job('RECURSIVE_BUILD')
job_builder.with_output('DATASET_A', object_type='DATASET')
job_builder.with_output('DATASET_B', object_type='DATASET')
job = job_builder.start_and_wait(no_fail=True)
```

### Build a Managed Folder

```python
job_builder = project.new_job('NON_RECURSIVE_FORCED_BUILD')
job_builder.with_output('my_folder_id', object_type='MANAGED_FOLDER')
job = job_builder.start_and_wait(no_fail=True)
```

## Build Types

| Build Type | Behavior |
|------------|----------|
| `NON_RECURSIVE_FORCED_BUILD` | Build only the specified outputs, even if up-to-date |
| `RECURSIVE_BUILD` | Build outputs and any out-of-date upstream dependencies |
| `RECURSIVE_FORCED_BUILD` | Rebuild everything upstream, regardless of state |
| `RECURSIVE_MISSING_ONLY_BUILD` | Build only missing upstream datasets |

## Check Job Status

```python
status = job.get_status()
state = status.get("baseStatus", {}).get("state")  # "DONE" or "FAILED"

if state == "FAILED":
    activities = status.get("baseStatus", {}).get("activities", {})
    for name, info in activities.items():
        if info.get("firstFailure"):
            print(f"Error in {name}: {info['firstFailure'].get('message')}")
```

## Read Job Logs

```python
# Full log
log = job.get_log()
print(log[-2000:])  # Last 2000 chars

# Log for a specific activity
log = job.get_log(activity="my_activity")
```

## List Recent Jobs

```python
jobs = project.list_jobs()
for j in jobs[:5]:
    job_id = j['def']['id']
    state = j.get('state', 'unknown')
    print(f"Job {job_id}: {state}")
```

## Abort a Running Job

```python
job.abort()
```

## Auto-Update Schema Before Build

```python
job_builder = project.new_job('NON_RECURSIVE_FORCED_BUILD')
job_builder.with_output('MY_DATASET', object_type='DATASET')
job_builder.with_auto_update_schema_before_each_recipe_run(True)
job = job_builder.start_and_wait(no_fail=True)
```

## Detailed References

- [references/job-status.md](references/job-status.md) — Full status structure, activity details, failure extraction patterns

## Related Skills

- [skills/flow-management/](../flow-management/) — Building datasets in dependency order
- [skills/troubleshooting/](../troubleshooting/) — Diagnosing job failures
- [skills/scenarios/](../scenarios/) — Running jobs as part of automated workflows
