# Project Permissions

## Permission Structure

```python
permissions = project.get_permissions()
# Returns:
# {
#   "owner": "alice",
#   "permissions": [
#     {
#       "group": "data-team",
#       "admin": False,
#       "readProjectContent": True,
#       "readDashboards": True,
#       "writeProjectContent": True,
#       "writeDashboards": False,
#       "runScenarios": True,
#       "manageDashboardAuthorizations": False,
#       "manageExposedElements": False,
#       "executeApp": False
#     }
#   ]
# }
```

## Permission Flags

| Flag | Controls |
|------|----------|
| `admin` | Full project admin (overrides all other flags) |
| `readProjectContent` | View datasets, recipes, notebooks, code |
| `writeProjectContent` | Create/edit datasets, recipes, notebooks |
| `readDashboards` | View dashboards and insights |
| `writeDashboards` | Create/edit dashboards and insights |
| `runScenarios` | Execute scenarios manually |
| `manageDashboardAuthorizations` | Control dashboard sharing |
| `manageExposedElements` | Control which items are exposed to other projects |
| `executeApp` | Run Dataiku applications |

## Add a Group Permission

```python
permissions = project.get_permissions()
permissions["permissions"].append({
    "group": "analysts",
    "admin": False,
    "readProjectContent": True,
    "readDashboards": True,
    "writeProjectContent": False,
    "writeDashboards": False,
    "runScenarios": False
})
project.set_permissions(permissions)
```

## Remove a Group Permission

```python
permissions = project.get_permissions()
permissions["permissions"] = [
    p for p in permissions["permissions"]
    if p.get("group") != "old-team"
]
project.set_permissions(permissions)
```

## Transfer Ownership

```python
# Ownership is in the permissions dict
permissions = project.get_permissions()
permissions["owner"] = "bob"
project.set_permissions(permissions)
```

> **Important:** Only instance admins or the current owner can transfer ownership.
