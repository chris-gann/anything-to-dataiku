# Library Structure

## Recommended Directory Layout

```
python/
├── __init__.py
├── transforms/
│   ├── __init__.py
│   ├── cleaning.py
│   ├── enrichment.py
│   └── validation.py
├── connectors/
│   ├── __init__.py
│   └── api_client.py
└── utils/
    ├── __init__.py
    ├── logging.py
    └── schema_helpers.py
```

## Import Patterns

From a Python recipe or notebook:

```python
# Import a module
from python.transforms.cleaning import clean_data

# Import a specific function
from python.utils.schema_helpers import normalize_column_names

# Import the whole package
import python.transforms as transforms
```

## `__init__.py` Files

Every directory that should be importable as a Python package needs an `__init__.py` file. It can be empty:

```python
lib_file = folder.add_file("__init__.py")
lib_file.write("")
```

Or it can re-export commonly used functions:

```python
lib_file = folder.add_file("__init__.py")
lib_file.write("""
from .cleaning import clean_data
from .enrichment import enrich_with_lookup
""")
```

## Git Integration

Project libraries can be backed by a Git repository. This is configured in the DSS UI under Project Settings > Libraries. The API does not directly manage Git settings for libraries, but you can:

1. Push library changes via the DSS UI Git integration
2. Use `DSSProject.get_project_git()` for project-level Git operations

## Pitfalls

**Library changes require recipe restart:** If you update a library file, running Python recipes may still use the cached version. Clear the cache or restart the recipe kernel.

**`python/` prefix is mandatory:** Only files under the `python/` directory are importable in Python recipes. Files at the library root are not importable.

**No automatic dependency resolution:** Library code runs in the project's code environment. Ensure all imports used by library code are available in the active code env.
