# Workspace Objects

## Supported Object Types

| Type | Description | How to Add |
|------|-------------|-----------|
| **Dataset** | Any dataset from any project | Pass `DSSDataset` handle or raw dict |
| **Dashboard** | Published dashboards | Pass raw dict with `objectType: "DASHBOARD"` |
| **Wiki Article** | Project wiki articles | Pass `DSSWikiArticle` handle or raw dict |
| **App** | Dataiku applications | Pass raw dict with `objectType: "APP"` |

## Adding Objects from Different Projects

```python
ws = client.get_workspace("SHARED_HUB")

# Add objects from multiple projects
projects_and_datasets = [
    ("PROJECT_A", "CUSTOMERS"),
    ("PROJECT_A", "ORDERS"),
    ("PROJECT_B", "PRODUCT_CATALOG"),
]

for project_key, dataset_name in projects_and_datasets:
    ws.add_object({
        "objectType": "DATASET",
        "projectKey": project_key,
        "objectId": dataset_name
    })
```

## Adding a Dashboard

```python
ws.add_object({
    "objectType": "DASHBOARD",
    "projectKey": "MY_PROJECT",
    "objectId": "my_dashboard_id"
})
```

## Raw Object Structure

Each workspace object's `get_raw()` returns:

```python
{
    "objectType": "DATASET",     # DATASET, DASHBOARD, WIKI_ARTICLE, APP
    "projectKey": "MY_PROJECT",
    "objectId": "MY_DATASET",
    "displayName": "...",        # May be present
    "description": "..."         # May be present
}
```

## Pitfalls

**Objects are references, not copies:** Adding a dataset to a workspace creates a reference. If the dataset is deleted from its project, the workspace link breaks.

**Permissions are additive:** A user who has member access to a workspace can view all objects in it, regardless of whether they have access to the underlying project. Ensure sensitive datasets are not added to broadly-shared workspaces.

**Admin rights required for delete:** Only workspace admins can delete the workspace or modify its settings. Contributors can add/remove objects.
