# Scenario Triggers

## Trigger Types

| Method | Schedule |
|--------|----------|
| `add_periodic_trigger(every_minutes=5)` | Every N minutes |
| `add_hourly_trigger(minute_of_hour=0)` | At a specific minute each hour |
| `add_daily_trigger(hour=2, minute=0)` | Daily at a specific time |
| `add_monthly_trigger(day=1, hour=2)` | Monthly on a specific day |

## Periodic Trigger

```python
settings = scenario.get_settings()
settings.add_periodic_trigger(every_minutes=15)
settings.save()
```

## Daily Trigger with Day Selection

```python
settings.add_daily_trigger(
    hour=6,
    minute=30,
    days=[0, 1, 2, 3, 4],   # Monday through Friday (0=Monday)
    repeat_every=1,
    timezone="SERVER"         # or "UTC", "America/New_York", etc.
)
settings.save()
```

## Monthly Trigger

```python
settings.add_monthly_trigger(
    day=15,
    hour=3,
    minute=0,
    run_on="ON_THE_DAY",     # or "ON_CLOSEST_WEEKDAY"
    repeat_every=1,
    timezone="SERVER"
)
settings.save()
```

## Access Raw Triggers

For advanced trigger types not covered by helper methods:

```python
settings = scenario.get_settings()
triggers = settings.raw_triggers

for trigger in triggers:
    print(f"Type: {trigger['type']}")
    print(f"Params: {trigger.get('params', {})}")
```

## Remove All Triggers

```python
settings = scenario.get_settings()
settings.raw_triggers.clear()
settings.save()
```

## Check Next Scheduled Run

```python
status = scenario.get_status()
print(f"Next run: {status.next_run}")  # Approximate datetime
print(f"Currently running: {status.running}")
```

## Timezone Handling

| Value | Behavior |
|-------|----------|
| `"SERVER"` | Uses the DSS server's timezone |
| `"UTC"` | UTC timezone |
| `"America/New_York"` | IANA timezone string |

> **Note:** `timezone` defaults to `"SERVER"` for all trigger types. Always specify explicitly if your team spans time zones.
