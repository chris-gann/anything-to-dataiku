---
name: workspaces
description: "Use when creating or managing Dataiku workspaces, adding objects to workspaces, or configuring workspace permissions"
---

# Workspace Patterns

Reference patterns for managing Dataiku workspaces via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Workspace** | A curated collection of objects (datasets, dashboards, apps, wiki articles) for a specific audience | Instance-level (`client`) |
| **Workspace Object** | An item added to a workspace (dataset, dashboard, wiki article, app) | Per workspace |
| **Permissions** | Member, contributor, and admin roles on the workspace | Per workspace |

## List Workspaces

```python
workspaces = client.list_workspaces()
for ws in workspaces:
    print(ws)
```

## Create a Workspace

```python
ws = client.create_workspace(
    workspace_key="ANALYTICS_HUB",
    name="Analytics Hub",
    description="Central workspace for the analytics team",
    color="#2196F3"
)
```

## Get a Workspace Handle

```python
ws = client.get_workspace("ANALYTICS_HUB")
```

## Add Objects to a Workspace

```python
ws = client.get_workspace("ANALYTICS_HUB")

# Add a dataset
ds = project.get_dataset("CUSTOMER_SUMMARY")
ws.add_object(ds)

# Add a wiki article
wiki = project.get_wiki()
article = wiki.get_article("getting-started")
ws.add_object(article)

# Add by raw dict (for cross-project objects)
ws.add_object({
    "objectType": "DATASET",
    "projectKey": "OTHER_PROJECT",
    "objectId": "THEIR_DATASET"
})
```

## List Workspace Objects

```python
objects = ws.list_objects()
for obj in objects:
    raw = obj.get_raw()
    print(f"{raw.get('objectType')}: {raw.get('projectKey')}.{raw.get('objectId')}")
```

## Remove Objects

```python
objects = ws.list_objects()
for obj in objects:
    raw = obj.get_raw()
    if raw.get("objectId") == "OLD_DATASET":
        obj.remove()
```

## Workspace Settings

```python
ws = client.get_workspace("ANALYTICS_HUB")
settings = ws.get_settings()

# Read properties
print(settings.display_name)
print(settings.description)
print(settings.color)

# Update properties
settings.display_name = "Analytics Hub v2"
settings.description = "Updated workspace for the analytics team"
settings.color = "#4CAF50"
settings.save()
```

## Workspace Permissions

```python
from dataikuapi.dss.workspace import DSSWorkspacePermissionItem

settings = ws.get_settings()

# Set permissions using helper class
settings.permissions = [
    DSSWorkspacePermissionItem.admin_user("alice@example.com"),
    DSSWorkspacePermissionItem.contributor_group("data-team"),
    DSSWorkspacePermissionItem.member_group("analysts"),
    DSSWorkspacePermissionItem.member_user("bob@example.com"),
]
settings.save()
```

### Permission Roles

| Role | Can View | Can Add/Remove Objects | Can Manage Settings |
|------|---------|----------------------|-------------------|
| **Member** | Yes | No | No |
| **Contributor** | Yes | Yes | No |
| **Admin** | Yes | Yes | Yes |

## Delete a Workspace

```python
ws = client.get_workspace("OLD_WORKSPACE")
ws.delete()  # Requires admin rights
```

## Detailed References

- [references/workspace-objects.md](references/workspace-objects.md) — Supported object types, cross-project sharing patterns

## Related Skills

- [skills/data-catalog/](../data-catalog/) — Data collections (similar concept, dataset-focused)
- [skills/wikis/](../wikis/) — Wiki articles that can be added to workspaces
