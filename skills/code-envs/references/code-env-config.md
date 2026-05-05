# Code Environment Configuration

## Python Interpreters

| Interpreter | Value |
|-------------|-------|
| Python 3.9 | `PYTHON39` |
| Python 3.10 | `PYTHON310` |
| Python 3.11 | `PYTHON311` |
| Python 3.12 | `PYTHON312` |

## Deployment Modes

| Mode | Description |
|------|-------------|
| `DESIGN_MANAGED` | Managed by DSS on a design node |
| `AUTOMATION_SINGLE` | Single-version env on automation node |
| `AUTOMATION_VERSIONED` | Multi-version env on automation node |
| `PLUGIN_MANAGED` | Created and managed by a plugin |

## Container Configuration (Kubernetes)

For containerized execution environments:

```python
settings = code_env.get_settings()

# Set container configurations to build images for
settings.set_built_container_confs("default-container", "gpu-container")

# Add GPU/CUDA support
settings.add_container_runtime_addition("CUDA_12_2_CUDNN_8_9_7")

# Set a Dockerfile fragment
settings.set_dockerfile_fragment(
    "RUN pip install my-private-package",
    location="AFTER_INSTALL"
)

settings.save()
```

## Available Container Runtime Additions

| Addition | Description |
|----------|-------------|
| `CUDA_11_2_CUDNN_8_1_1` | CUDA 11.2 with cuDNN 8.1.1 |
| `CUDA_12_2_CUDNN_8_9_7` | CUDA 12.2 with cuDNN 8.9.7 |
| `PYTORCH_2_NVIDIA` | PyTorch 2.x NVIDIA packages |
| `BASIC_GPU` | Basic GPU enabling |

## Raw Settings Access

```python
settings = code_env.get_settings()
raw = settings.get_raw()

# Common raw fields:
# raw["envName"] — Environment name
# raw["envLang"] — "PYTHON" or "R"
# raw["deploymentMode"] — Deployment mode string
# raw["pythonInterpreter"] — Python version
# raw["specPackageList"] — Pip packages string (newline-separated)
# raw["condaPackageList"] — Conda packages string (newline-separated)
# raw["installCorePackages"] — Boolean
# raw["installJupyterSupport"] — Boolean
```

## Pitfalls

**`update_packages()` is required:** After changing the package spec with `set_required_packages()` and `save()`, you must call `update_packages()` to actually install. Saving only updates the spec, it does not trigger installation.

**`wait=True` is important:** Code env operations (create, update, delete) can take minutes. Always use `wait=True` unless you need asynchronous behavior.
