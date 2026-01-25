# 1. Use uv for Environment Management

Date: 2024-12-28

## Status

Accepted

## Context

Executing Robot Framework tasks requires a Python environment with the necessary dependencies. Managing these environments consistently across different machines and deployments is challenging. We needed a fast and reliable way to manage Python dependencies and environments.

## Decision

We decided to use [uv](https://docs.astral.sh/uv/) for Python environment management.

## Consequences

### Positive

- **Speed**: `uv` is significantly faster than other tools like `pip` or `poetry` for resolving and installing dependencies.
- **Reliability**: It provides a lockfile mechanism (`uv.lock`) ensuring reproducible environments.
- **Simplicity**: It simplifies the process of setting up the environment for each task execution.

### Negative

- **Dependency**: The tool introduces a dependency on `uv` being installed on the system.
