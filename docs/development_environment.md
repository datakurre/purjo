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
*   **Authentication:** OAuth2-protected by default (via the Keycloak service below), rather than the plain HTTP Basic credential used in older setups. Requests need either a valid OAuth2 bearer token or `ENGINE_REST_AUTHORIZATION` -- never both (see [CLI Reference](cli_reference.md)).

### Keycloak
*   **Port:** `8081`
*   **URL:** `http://localhost:8081`
*   **Description:** An identity provider supplying OAuth2 client-credentials tokens for the Operaton engine above.
*   **Configuration:** The environment imports the `operaton` realm from `fixture/keycloak/operaton-realm.json`, including the `operaton` service-account client that `pur` authenticates as.

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

```console
$ devenv test
```

This command waits for all services (Operaton, Vault, Keycloak) to be ready, then runs the unit test suite (`make test`) followed by the end-to-end suite against those live services (`make test-e2e`; see [End-to-end testing](#end-to-end-testing) below). It covers the default (OAuth2) profile only; CI does not use it.

## Testing strategies

### Integration and functional testing

You can test your Robot Framework tasks locally without running a BPM engine using either:

1. **Integration tests** with `robotframework-robotlibrary` (`Run Robot Test` / `Run Robot Task`) to execute a task/test from another `.robot` file and assert results via variable overrides.
2. **Functional tests** with the `purjo` Robot Framework library (`Get Output Variables`) to execute a configured topic and validate the returned output variable dictionary.

See [Testing Tasks](testing_tasks.md) for the full guide and examples.

### End-to-end testing

`purjo`'s own end-to-end suite (`tests/e2e/`) automates exactly this flow
against live services -- deploy, start an instance, run `pur serve`, then
verify the result through the engine's history REST API.

The engine authenticates one way at a time, so the two authentication
scenarios are two devenv profiles rather than two fixtures, and every e2e
test is marked with the one it needs:

| Profile | Engine | Marker |
| --- | --- | --- |
| `shell` (the default) | OAuth2-protected, with Keycloak | `auth_oauth2` |
| `basic` | HTTP Basic on `/engine-rest`, no Keycloak | `auth_basic` |

`services.operaton` asserts that its `oauth2` and `basicAuth` options are
mutually exclusive, which is why these are separate profiles. Each profile
proves its own engine is actually protected rather than merely reachable:
`test_unauthenticated_request_is_rejected` carries both markers and runs in
either, and a scheme-specific test either side of it checks that the Basic
credential is accepted under `basic` and rejected under `shell`.

```console
$ devenv up                                     # OAuth2 engine (default profile)
$ cp .env.example .env                          # client credentials it needs
$ devenv shell -- make test-e2e E2E_MARKERS="e2e and auth_oauth2"

$ devenv --profile basic up                     # Basic-auth engine
$ devenv --profile basic shell -- make test-e2e E2E_MARKERS="e2e and auth_basic"
```

Only the OAuth2 profile needs credentials on the environment; the Basic tests
pass `ENGINE_REST_AUTHORIZATION` to `pur` themselves. Never set both -- see
[CLI Reference](cli_reference.md).

CI runs the two as separate matrix jobs, via `make test-e2e-ci`, which also
waits for that profile's ports and fails if a service never appears (rather
than letting the suite skip itself green).

You can also drive the same flow by hand, which is what `tests/e2e/`
automates:
1.  Start the services with `devenv up`.
2.  Deploy your process using `pur run` or `pur operaton deploy`.
3.  Start a process instance.
4.  Run `pur serve` to execute the tasks.
5.  Verify the results in the Operaton Cockpit or by querying the engine API.
