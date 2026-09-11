---
layout: default
title: Managing Secrets
---

# Managing secrets

`purjo` provides a flexible system for managing sensitive information (secrets) using different providers (e.g., local files, HashiCorp Vault). Secrets are injected into your tasks as variables, but handled securely to prevent accidental exposure.

## Configuration

Secrets are configured in `pyproject.toml` under `[tool.purjo.secrets]`. You can define multiple profiles.

### File provider

The `file` provider loads secrets from a JSON file.

```toml
[tool.purjo.secrets.default]
provider = "file"
path = "secrets.json"
```

In this example, the `default` profile uses a file named `secrets.json` in the project root. A relative path is resolved against the package directory, so `pur serve` finds it no matter which directory you run it from. (A zipped package is not extracted until a task runs, so a relative path in one is resolved against the working directory instead.)

**`secrets.json` Example:**
```json
{
  "api_key": "my-secret-key"
}
```

`pur wrap` never packages a `secrets.json` from the project root, and `pur serve` does not copy it into the sandbox a task runs in — secrets reach tasks as variables, not as a file. Note that this covers the documented name in the project root only: a secrets file kept under another name, or in a subdirectory, is packaged like any other file.

### Vault provider

The `vault` provider loads secrets from HashiCorp Vault.

```toml
[tool.purjo.secrets.prod]
provider = "vault"
path = "secret/my-app"
mount-point = "secret"
```

This requires `VAULT_ADDR` and `VAULT_TOKEN` environment variables to be set.

## Usage

### Selecting a profile

When running `pur serve`, `purjo` uses the `default` profile if one exists. You can specify a different profile or a direct file path using the `--secrets` option.

```console
# Use the 'prod' profile from pyproject.toml
$ pur serve --secrets prod .

# Use a specific secrets file directly (bypassing pyproject.toml)
$ pur serve --secrets ./my-secrets.json .
```

### Accessing secrets in tasks

Secrets are injected as variables into your Robot Framework or Python tasks.

#### Robot Framework

In Robot Framework, secrets are available as standard variables. If `robotframework` >= 7.4b2 is used, they are automatically converted to `Secret` objects, which mask their values in logs.

```robotframework
*** Tasks ***
Use API Key
    Log To Console    The API Key is: ${api_key}
```

#### Python

In Python tasks, you can access them via `BuiltIn().get_variables()`.

```python
from robot.libraries.BuiltIn import BuiltIn

def my_task():
    api_key = BuiltIn().get_variable_value("${api_key}")
```

## Security best practices

*   **Never commit secrets files to version control.** Add `secrets.json` (and any other secret files) to your `.gitignore`.
*   Use the `vault` provider for production environments to avoid storing secrets on disk.
*   `purjo` attempts to mask secrets in logs, but always be cautious when logging variables.
