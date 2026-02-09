---
layout: default
title: Development Environment
---

# Development environment

`purjo` utilizes [`devenv`](https://devenv.sh/) to provide a reproducible and feature-rich development environment. This setup includes not only the necessary Python tools but also a suite of services to simulate a production-like ecosystem.

## Prerequisites

*   [Install `devenv`](https://devenv.sh/getting-started/)
*   [Install `direnv`](https://direnv.net/) (optional, but recommended for automatic environment activation)

## Services

When you run `devenv up`, the following services are started automatically:

### Operaton BPM Engine
*   **Port:** `8080`
*   **URL:** `http://localhost:8080/operaton`
*   **Description:** A lightweight, open-source BPM engine. It serves as the orchestration core for your `purjo` tasks.

### HashiCorp Vault
*   **Port:** `8200`
*   **UI:** `http://localhost:8200/ui`
*   **Description:** A secrets management service.
*   **Configuration:** The environment automatically initializes Vault and enables the `secret/` Key-Value (v2) engine. This allows you to test `purjo`'s Vault integration out of the box.

### Mockoon
*   **Port:** `3080`
*   **Description:** A mock API server.
*   **Data:** Configured with `./fixture/mockoon/data.json`.
*   **Usage:** Useful for simulating external APIs that your Robot Framework tasks might need to interact with during development.

## Dev containers

The project is configured to support [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers). This allows you to open the project in a fully configured container environment without installing dependencies on your host machine.

### Recommended extensions

When working with `purjo` in VS Code, the following extensions are recommended:

*   **Robot Code** (`d-biehl.robotcode`): For Robot Framework syntax highlighting and language server features.
*   **BPMN Editor** (`miragon-gmbh.vs-code-bpmn-modeler`): For visual editing of `.bpmn` files.
*   **Ruff** (`charliermarsh.ruff`): For Python linting and formatting.
*   **Nix IDE** (`bbenoist.Nix`): If you are editing `devenv.nix` files.

## Running tests

The development environment includes a test suite that verifies the integration between `purjo` and the services.

```console
$ devenv test
```

This command waits for the services (Operaton, Vault) to be ready and then runs the project's test suite.

## Testing strategies

### Integration and functional testing

You can test your Robot Framework tasks locally without running a BPM engine using either:

1. **Integration tests** with `robotframework-robotlibrary` (`Run Robot Test` / `Run Robot Task`) to execute a task/test from another `.robot` file and assert results via variable overrides.
2. **Functional tests** with the `purjo` Robot Framework library (`Get Output Variables`) to execute a configured topic and validate the returned output variable dictionary.

See [Testing Tasks](testing_tasks.md) for the full guide and examples.

### End-to-end testing

For full end-to-end testing, you can:
1.  Start the services with `devenv up`.
2.  Deploy your process using `pur run` or `pur operaton deploy`.
3.  Start a process instance.
4.  Run `pur serve` to execute the tasks.
5.  Verify the results in the Operaton Cockpit or by querying the engine API.
