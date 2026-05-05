# Folder Operations

## Metrics

```python
# Compute folder metrics
folder.compute_metrics()

# Get last computed metrics
metrics = folder.get_last_metric_values()
values = metrics.get_global_value("records")
print(f"File count: {values}")
```

## Flow Zone Management

```python
# Get current flow zone
zone = folder.get_zone()

# Move to a different zone
folder.move_to_zone(target_zone)

# Share to another zone (makes it visible without moving)
folder.share_to_zone(other_zone)

# Unshare from a zone
folder.unshare_from_zone(other_zone)
```

## Check Folder Usages

```python
# Find which recipes reference this folder
usages = folder.get_usages()
for usage in usages:
    print(f"Used by: {usage}")
```

## Path Details (Inside DSS)

```python
import dataiku
folder = dataiku.Folder("my_folder")

# Get details about a specific path
details = folder.get_path_details("/subfolder")
# Returns: {"exists": True, "directory": True, "size": ..., "children": [...]}

# Get the local filesystem path (only for local folders)
path = folder.get_path()
```

## Partition Operations (Inside DSS)

```python
import dataiku
folder = dataiku.Folder("my_folder")

# List partitions
partitions = folder.list_partitions()

# List files in a specific partition
files = folder.list_paths_in_partition("2024/01/15")

# Get partition metadata
info = folder.get_partition_info("2024/01/15")

# Clear a partition
folder.clear_partition("2024/01/15")

# Clear all files
folder.clear()
```

## Pitfalls

**Folder ID vs. name:** `project.get_managed_folder()` requires the internal 8-character ID, not the display name. Use `project.list_managed_folders()` to find the ID.

**`get_file()` returns a Response:** The return value of `DSSManagedFolder.get_file()` is a `requests.Response` object, not raw bytes. Use `.iter_content()` or `.content` to access the data.

**`dataiku.Folder` vs `DSSManagedFolder`:** Use `dataiku.Folder` inside DSS recipes and notebooks. Use `DSSManagedFolder` (from `dataikuapi`) for external scripts connecting via the API client.
