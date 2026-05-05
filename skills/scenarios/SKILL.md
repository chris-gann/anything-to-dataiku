---
name: scenarios
description: "Use when creating, running, or configuring Dataiku scenarios including triggers, steps, reporters, and run monitoring"
---

# Scenario Patterns

Reference patterns for creating and managing Dataiku scenarios via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Scenario** | An automated workflow that runs steps sequentially | Per project |
| **Step** | A single action in a scenario (build, run code, etc.) | Per scenario |
| **Trigger** | A condition that starts a scenario (time, dataset change, etc.) | Per scenario |
| **Reporter** | A notification sent after a scenario runs (email, webhook, etc.) | Per scenario |

## List Scenarios

```python
scenarios = project.list_scenarios(as_type="objects")
for s in scenarios:
    print(f"{s.id} — running: {s.running}")
```

## Run a Scenario

### Synchronous (wait for completion)

```python
scenario = project.get_scenario("MYSCENARIO")
scenario.run_and_wait()
```

### Asynchronous (fire and poll)

```python
scenario = project.get_scenario("MYSCENARIO")
trigger_fire = scenario.run()
scenario_run = trigger_fire.wait_for_scenario_run()

while True:
    scenario_run.refresh()
    if not scenario_run.running:
        break
    time.sleep(5)

print(f"Outcome: {scenario_run.outcome}")
```

## Check Run Results

```python
scenario = project.get_scenario("MYSCENARIO")
last_runs = scenario.get_last_runs(only_finished_runs=True)
last_run = last_runs[0]

print(f"Outcome: {last_run.outcome}")      # SUCCESS, WARNING, FAILED, ABORTED
print(f"Duration: {last_run.duration}s")
print(f"Start: {last_run.start_time}")
```

### Get Error Details

```python
if last_run.outcome == "FAILED":
    details = last_run.get_details()
    error = details.first_error_details
    if error:
        print(f"Error: {error.get('message')}")
        print(f"Type: {error.get('clazz')}")
```

### Get Jobs Started by Scenario

```python
details = last_run.get_details()
all_job_ids = []
for step in details.steps:
    all_job_ids.extend(step.job_ids)
print(f"Jobs: {all_job_ids}")
```

## Scenario Settings

```python
scenario = project.get_scenario("MYSCENARIO")
settings = scenario.get_settings()

# Enable/disable auto-triggers
settings.active = True
settings.save()

# Change run-as user
settings.run_as = "service_account"
settings.save()
```

## Add Triggers

```python
settings = scenario.get_settings()

# Run every 30 minutes
settings.add_periodic_trigger(every_minutes=30)

# Run daily at 2:00 AM
settings.add_daily_trigger(hour=2, minute=0)

# Run hourly at minute 15
settings.add_hourly_trigger(minute_of_hour=15)

# Run monthly on the 1st at 3:00 AM
settings.add_monthly_trigger(day=1, hour=3, minute=0)

settings.save()
```

## Configure Reporters

```python
settings = scenario.get_settings()

# Modify existing reporters
for reporter in settings.raw_reporters:
    if reporter["messaging"]["type"] == "mail-scenario":
        reporter["messaging"]["configuration"]["sender"] = "alerts@company.com"

settings.save()
```

## Abort a Running Scenario

```python
scenario = project.get_scenario("MYSCENARIO")
scenario.abort()
```

## Disable All Scenarios in a Project

```python
previously_active = []
for scenario in project.list_scenarios(as_type="objects"):
    settings = scenario.get_settings()
    if settings.active:
        previously_active.append(scenario.id)
        settings.active = False
        settings.save()
```

## Re-enable Previously Active Scenarios

```python
for scenario_id in previously_active:
    scenario = project.get_scenario(scenario_id)
    settings = scenario.get_settings()
    settings.active = True
    settings.save()
```

## Run Multiple Scenarios in Parallel

```python
import time

scenario_runs = []
for scenario_id in ["SCENARIO_A", "SCENARIO_B", "SCENARIO_C"]:
    scenario = project.get_scenario(scenario_id)
    trigger_fire = scenario.run()
    scenario_run = trigger_fire.wait_for_scenario_run()
    scenario_runs.append(scenario_run)

# Wait for all to complete
while True:
    any_running = False
    for run in scenario_runs:
        run.refresh()
        if run.running:
            any_running = True
    if not any_running:
        break
    time.sleep(30)

# Check outcomes
for run in scenario_runs:
    print(f"{run.id}: {run.outcome}")
```

## Scenario Run Logs

```python
last_run = scenario.get_last_runs(only_finished_runs=True)[0]
log = last_run.get_log()
print(log)
```

## Detailed References

- [references/scenario-steps.md](references/scenario-steps.md) — Step types, step-based scenario configuration, Python script scenarios
- [references/scenario-triggers.md](references/scenario-triggers.md) — All trigger types, timezone handling, trigger parameters

## Related Skills

- [skills/jobs/](../jobs/) — Jobs created by scenario build steps
- [skills/flow-management/](../flow-management/) — Building datasets in pipelines
- [skills/troubleshooting/](../troubleshooting/) — Diagnosing scenario failures
