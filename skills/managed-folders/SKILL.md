---
name: managed-folders
description: "Use when creating managed folders, uploading/downloading files, listing folder contents, or managing file-based data"
---

# Managed Folder Patterns

Reference patterns for creating and managing Dataiku managed folders via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Managed Folder** | A folder in the flow for storing arbitrary files (CSV, images, models, etc.) | Per project |
| **DSSManagedFolder** | External API handle (`dataikuapi`) for remote operations | API client |
| **dataiku.Folder** | Internal API handle for use inside DSS recipes/notebooks | Inside DSS |

## Create a Managed Folder

```python
folder = project.create_managed_folder("my_folder")

# Configure storage location
settings = folder.get_settings()
settings.set_connection_and_path("filesystem_managed", "/data/my_folder")
settings.save()
```

## List Managed Folders

```python
folders = project.list_managed_folders()
for f in folders:
    print(f"{f['name']} (id: {f['id']})")
```

## Get a Managed Folder Handle

```python
# By ID (the 8-character internal ID)
folder = project.get_managed_folder("abcd1234")
```

## Upload Files

```python
# Upload from a local file
with open("data/report.csv", "rb") as f:
    folder.put_file("report.csv", f)

# Upload to a subdirectory
with open("data/image.png", "rb") as f:
    folder.put_file("images/image.png", f)

# Upload an entire local directory
folder.upload_folder("uploads/", "/path/to/local/folder")
```

## Download Files

```python
# Download a file (returns a Response object)
response = folder.get_file("report.csv")
with open("downloaded_report.csv", "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

## List Folder Contents

```python
contents = folder.list_contents()
for item in contents["items"]:
    print(f"{item['path']} ({item['size']} bytes, modified: {item['lastModified']})")
```

## Delete Files

```python
# Delete a specific file (no error if file doesn't exist)
folder.delete_file("report.csv")
```

## Copy to Another Folder

```python
target_folder = project.get_managed_folder("target_id")
folder.copy_to(target_folder, write_mode="OVERWRITE")
```

## Create a Dataset from Folder Files

```python
# Create a FilesInFolder dataset from the managed folder
folder.create_dataset_from_files("my_files_dataset")
```

## Folder Settings

```python
settings = folder.get_settings()

# Access raw settings
raw = settings.get_raw()
raw_params = settings.get_raw_params()  # Connection-specific params

# Change storage
settings.set_connection_and_path("s3_connection", "my-bucket/prefix")
settings.save()
```

## Partitioning

```python
settings = folder.get_settings()

# Add a discrete partition dimension
settings.add_discrete_partitioning_dimension("region")

# Add a time partition dimension
settings.add_time_partitioning_dimension("date", period="DAY")

# Set the file pattern for partitioning
settings.set_partitioning_file_pattern("%{region}/%Y/%M/%D/")

settings.save()
```

## Using Folders Inside DSS Recipes

Inside DSS Python recipes and notebooks, use `dataiku.Folder`:

```python
import dataiku

folder = dataiku.Folder("my_folder")

# Read a JSON file
data = folder.read_json("config.json")

# Write a JSON file
folder.write_json("output.json", {"result": "success"})

# Upload binary data
folder.upload_data("file.bin", b"binary content")

# Get download stream
with folder.get_download_stream("report.csv") as stream:
    content = stream.read()

# List files
for path in folder.list_paths_in_partition():
    print(path)
```

## Rename and Delete

```python
# Rename a folder
folder.rename("new_folder_name")

# Delete the folder from the flow
folder.delete()
```

## Detailed References

- [references/folder-operations.md](references/folder-operations.md) — Partitioning patterns, metrics, flow zone management

## Related Skills

- [skills/dataset-management/](../dataset-management/) — Creating datasets from folder files
- [skills/flow-management/](../flow-management/) — Building managed folders in pipelines
- [skills/jobs/](../jobs/) — Building managed folder outputs
