---
name: connections
description: "Use when listing, inspecting, testing, or configuring Dataiku connections (SQL, cloud storage, HDFS, etc.)"
---

# Connection Management Patterns

Reference patterns for managing Dataiku connections via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Connection** | A configured link to an external data store (SQL, S3, GCS, etc.) | Instance-level (`client`) |
| **Connection Type** | The backend (PostgreSQL, Snowflake, S3, HDFS, etc.) | Per connection |
| **Usability** | Which groups can use a connection for datasets/folders | Per connection |

## List Connections

```python
connections = client.list_connections(as_type="listitems")
for c in connections:
    print(f"{c.name} ({c.type})")
```

## Get Connection Details

```python
conn = client.get_connection("my_snowflake")

# Get connection info (includes resolved parameters)
info = conn.get_info()
print(f"Type: {info.get_type()}")
print(f"Params: {info.get_params()}")
```

## Test a Connection

```python
conn = client.get_connection("my_snowflake")
result = conn.test()
print(result)  # Returns test result dict
```

## Connection Settings

```python
conn = client.get_connection("my_snowflake")
settings = conn.get_settings()

# Access raw settings
raw = settings.get_raw()
print(f"Type: {settings.type}")

# Check permissions
print(f"Allow managed datasets: {settings.allow_managed_datasets}")
print(f"Allow managed folders: {settings.allow_managed_folders}")
print(f"Allow write: {settings.allow_write}")

# Save changes
settings.save()
```

## Control Connection Usability

```python
settings = conn.get_settings()

# Make usable by specific groups only
settings.set_usability(False, "data-engineers", "analysts")

# Make usable by all
settings.set_usability(True)

settings.save()
```

## Control Credential Readability

```python
settings = conn.get_settings()
readability = settings.details_readability

# Allow specific groups to read credentials
readability.set_readability(False, "admins")

# Allow all
readability.set_readability(True)

settings.save()
```

## Common Connection Types

| Type | Description | Typical Use |
|------|-------------|-------------|
| `PostgreSQL` | PostgreSQL database | SQL datasets, recipes |
| `Snowflake` | Snowflake data warehouse | SQL datasets, recipes |
| `BigQuery` | Google BigQuery | SQL datasets, recipes |
| `S3` | Amazon S3 | File datasets, managed folders |
| `GCS` | Google Cloud Storage | File datasets, managed folders |
| `Azure` | Azure Blob Storage | File datasets, managed folders |
| `HDFS` | Hadoop filesystem | File datasets, managed folders |
| `Filesystem` | Local/NFS filesystem | Uploaded files, managed folders |

## Delete a Connection

```python
conn = client.get_connection("old_connection")
conn.delete()
```

## Detailed References

- [references/connection-types.md](references/connection-types.md) — Connection type parameters, credential modes, cloud-specific configuration

## Related Skills

- [skills/dataset-management/](../dataset-management/) — Creating datasets on connections
- [skills/importing-tables/](../importing-tables/) — Importing SQL tables from connections
- [skills/troubleshooting/](../troubleshooting/) — Diagnosing connection errors
