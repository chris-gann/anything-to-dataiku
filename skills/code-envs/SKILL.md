---
name: code-envs
description: "Use when creating, updating, or managing Dataiku code environments for Python or R packages"
---

# Code Environment Patterns

Reference patterns for managing Dataiku code environments via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Code Env** | An isolated Python or R environment with specific packages | Instance-level |
| **Design Node** | Where code envs are created and configured interactively | Design instance |
| **Automation Node** | Where versioned code envs are deployed | Automation instance |
| **Jupyter Support** | Whether the code env is available in Jupyter notebooks | Per code env |

## List Code Environments

```python
code_envs = client.list_code_envs()
for env in code_envs:
    print(f"{env['envName']} ({env['envLang']}) — {env.get('deploymentMode', 'DESIGN')}")
```

## Create a Code Environment

```python
# Create a new Python code env
code_env = client.create_code_env(
    env_lang="PYTHON",
    env_name="my_ml_env",
    deployment_mode="DESIGN_MANAGED",
    params={
        "pythonInterpreter": "PYTHON310",  # or PYTHON39, PYTHON311
        "installCorePackages": True,
        "installJupyterSupport": True
    }
)
```

## Configure Packages

```python
code_env = client.get_code_env("PYTHON", "my_ml_env")
settings = code_env.get_settings()

# Set pip packages
settings.set_required_packages(
    "pandas==2.1.0",
    "scikit-learn==1.3.0",
    "xgboost>=1.7",
    "lightgbm"
)

settings.save()

# Update packages (install/upgrade to match spec)
code_env.update_packages(wait=True)
```

## Set Conda Packages

```python
settings = code_env.get_settings()
settings.set_required_conda_spec(
    "pandas=2.1.0",
    "scikit-learn=1.3.0",
    "numpy"
)
settings.save()
code_env.update_packages(wait=True)
```

## Get Current Packages

```python
settings = code_env.get_settings()

# Get pip packages as a list
packages = settings.get_required_packages(as_list=True)
for pkg in packages:
    print(pkg)

# Get conda spec
conda_spec = settings.get_required_conda_spec(as_list=True)
```

## Enable/Disable Jupyter Support

```python
code_env.set_jupyter_support(active=True, wait=True)
```

## Check Code Env Usages

```python
usages = code_env.list_usages()
for usage in usages:
    print(f"Used in: {usage}")
```

## View Logs

```python
# List available logs
logs = code_env.list_logs()
for log in logs:
    print(log)

# Get a specific log
log_content = code_env.get_log(logs[0])
print(log_content)
```

## Set as Project Default

To make a code env the default for a project, update the project settings:

```python
project_settings = project.get_settings()
raw = project_settings.settings
raw["settings"]["codeEnvs"] = {
    "python": {
        "mode": "EXPLICIT_ENV",
        "envName": "my_ml_env"
    }
}
project_settings.save()
```

## Delete a Code Environment

```python
code_env.delete(wait=True)
```

## Force Rebuild

```python
code_env.update_packages(force_rebuild_env=True, wait=True)
```

## Detailed References

- [references/code-env-config.md](references/code-env-config.md) — Python interpreters, deployment modes, container configuration

## Related Skills

- [skills/projects/](../projects/) — Setting project-level code env defaults
- [skills/recipe-patterns/](../recipe-patterns/) — Python recipes that use code envs
- [skills/troubleshooting/](../troubleshooting/) — Environment-related errors
