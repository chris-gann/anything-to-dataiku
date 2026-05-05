---
name: project-libraries
description: "Use when managing shared Python/R code in Dataiku project libraries, uploading library files, or organizing reusable modules"
---

# Project Library Patterns

Reference patterns for managing Dataiku project libraries via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Project Library** | A collection of reusable Python/R modules shared across recipes in a project | Per project |
| **Library File** | A single `.py` or `.R` file in the library | Per project |
| **Library Folder** | A directory for organizing library files | Per project |

## Access the Project Library

```python
library = project.get_library()
```

## List Library Contents

```python
# List root contents
items = library.list("/")
for item in items:
    print(f"{item.path} — {'folder' if hasattr(item, 'list') else 'file'}")

# List contents of a subfolder
items = library.list("/python/")
```

## Read a Library File

```python
lib_file = library.get_file("/python/utils.py")
content = lib_file.read()  # Returns string by default
print(content)

# Read as bytes
binary_content = lib_file.read(as_type="bytes")
```

## Create and Write Library Files

```python
# Create a new file in the root
lib_file = library.add_file("helpers.py")
lib_file.write("""
def clean_column_name(name):
    \"\"\"Normalize column name for SQL compatibility.\"\"\"
    return name.strip().upper().replace(" ", "_")

def safe_divide(a, b, default=0):
    \"\"\"Divide with zero-safe default.\"\"\"
    return a / b if b != 0 else default
""")
```

## Create Folders and Nested Files

```python
# Create a folder
folder = library.add_folder("python")

# Create a subfolder
sub_folder = folder.add_folder("transforms")

# Add a file to the subfolder
lib_file = sub_folder.add_file("__init__.py")
lib_file.write("")

lib_file = sub_folder.add_file("cleaning.py")
lib_file.write("""
import dataiku

def normalize_schema(dataset_name):
    ds = dataiku.Dataset(dataset_name)
    schema = ds.read_schema()
    for col in schema:
        col["name"] = col["name"].upper()
    ds.write_schema(schema)
""")
```

## Navigate Library Structure

```python
# Get a specific folder
folder = library.get_folder("/python/transforms")

# List folder contents
items = folder.list()
for item in items:
    print(item.path)

# Get a child by name
child = folder.get_child("cleaning.py")
```

## Move and Rename Files

```python
# Rename a file
lib_file = library.get_file("/python/old_name.py")
lib_file.rename("new_name.py")

# Move a file to a different folder
lib_file = library.get_file("/python/utils.py")
target_folder = library.get_folder("/python/common")
lib_file.move_to(target_folder)
```

## Delete Library Items

```python
# Delete a file
lib_file = library.get_file("/python/obsolete.py")
lib_file.delete()

# Delete a folder (and all contents)
folder = library.get_folder("/python/old_module")
folder.delete()
```

## Using Library Code in Recipes

Once files are in the project library, import them in Python recipes:

```python
# In a Python recipe, import from the library:
from python.transforms.cleaning import normalize_schema

normalize_schema("MY_DATASET")
```

> Library files under `python/` are importable as Python modules. The `python/` prefix acts as the root package.

## Detailed References

- [references/library-structure.md](references/library-structure.md) — Recommended directory layout, `__init__.py` patterns, Git integration

## Related Skills

- [skills/recipe-patterns/](../recipe-patterns/) — Python recipes that use library code
- [skills/code-envs/](../code-envs/) — Code environments for library dependencies
