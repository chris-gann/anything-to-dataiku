# Job Status

## Status Structure

```python
status = job.get_status()

# Top-level structure:
# {
#   "baseStatus": {
#     "state": "DONE" | "FAILED" | "RUNNING" | "ABORTED",
#     "activities": {
#       "activity_name": {
#         "state": "DONE" | "FAILED",
#         "firstFailure": {
#           "message": "Error details...",
#           "clazz": "java.lang.Exception"
#         }
#       }
#     }
#   }
# }
```

## Extract Error Details

```python
status = job.get_status()
state = status.get("baseStatus", {}).get("state")

if state == "FAILED":
    activities = status.get("baseStatus", {}).get("activities", {})
    for name, info in activities.items():
        if info.get("firstFailure"):
            msg = info["firstFailure"].get("message", "No message")
            clazz = info["firstFailure"].get("clazz", "Unknown")
            print(f"Activity: {name}")
            print(f"  Error: {msg}")
            print(f"  Type: {clazz}")
```

## Investigate Most Recent Failed Job

```python
jobs = project.list_jobs()
for j in jobs:
    if j.get("state") == "FAILED":
        job = project.get_job(j['def']['id'])
        print(f"Job: {j['def']['id']}")
        print(job.get_log()[-3000:])
        break
```

## Job States

| State | Meaning |
|-------|---------|
| `RUNNING` | Job is currently executing |
| `DONE` | Job completed successfully |
| `FAILED` | Job failed (check activities for details) |
| `ABORTED` | Job was manually aborted |

## Pitfalls

**`recipe.run()` already waits:** Do not add a separate wait loop after `recipe.run()`. It blocks until the job is complete. Use `no_fail=True` to prevent exceptions on failure.

**`wait_for_completion()` does not exist on DSSJob:** Use `recipe.run()` (which waits) or `job_builder.start_and_wait()`. For manual waiting, use `DSSJobWaiter(job).wait()`.
