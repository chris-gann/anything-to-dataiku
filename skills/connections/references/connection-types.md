# Connection Types

## SQL Connections

SQL connections store datasets as tables. Common parameters in `get_raw()["params"]`:

| Parameter | Description |
|-----------|-------------|
| `host` | Database server hostname |
| `port` | Database server port |
| `db` | Database name |
| `user` | Username (if basic auth) |
| `password` | Password (if basic auth) |
| `properties` | Additional JDBC properties |

### Snowflake-Specific

```python
raw = settings.get_raw()
params = raw["params"]
# params["account"] — Snowflake account identifier
# params["warehouse"] — Default warehouse
# params["db"] — Database name
# params["schema"] — Default schema
```

### BigQuery-Specific

```python
raw = settings.get_raw()
params = raw["params"]
# params["projectId"] — GCP project ID
# params["defaultDataset"] — Default dataset name
```

## Cloud Storage Connections

### S3

```python
raw = settings.get_raw()
params = raw["params"]
# params["bucket"] — S3 bucket name
# params["pathPrefix"] — Optional path prefix
# params["region"] — AWS region
```

### GCS

```python
raw = settings.get_raw()
params = raw["params"]
# params["bucket"] — GCS bucket name
# params["pathPrefix"] — Optional path prefix
```

## Credential Modes

| Mode | Description |
|------|-------------|
| `PARAMS` | Credentials stored in connection parameters |
| `GLOBAL_USER_REMAPPING` | Per-user credentials configured by admin |
| `PER_USER` | Each user provides their own credentials |

```python
info = conn.get_info()
print(f"Credential mode: {info.get_credential_mode()}")

# For basic auth connections
user, password = info.get_basic_credential()

# For AWS connections
aws_creds = info.get_aws_credential()
```

## Filesystem Connection

Used for local files, NFS mounts, and uploaded files:

```python
raw = settings.get_raw()
params = raw["params"]
# params["root"] — Root directory path
```

> **Note:** The built-in `filesystem_managed` connection is used for uploaded datasets. It cannot be deleted.
