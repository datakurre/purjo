---
layout: default
title: CLI Reference
---

# CLI reference

This page provides a comprehensive reference for the `purjo` (or `pur`) command-line interface.

## `pur serve`

Serve robot packages (or directories) as BPMN service tasks. This command starts a worker that long-polls the BPM engine for tasks and executes them.

```console
$ pur serve [OPTIONS] ROBOTS...
```

### Arguments

*   `ROBOTS`: One or more paths to robot packages (`.zip` files) or directories containing `pyproject.toml`.

### Options

*   `--base-url TEXT`: Base URL of the BPM engine REST API. Default: `http://localhost:8080/engine-rest`. (Env: `ENGINE_REST_BASE_URL`)
*   `--authorization TEXT`: Authorization header value for the BPM engine. (Env: `ENGINE_REST_AUTHORIZATION`)
*   `--secrets TEXT`: Secrets profile to use from `pyproject.toml` or path to a secrets file. (Env: `TASKS_SECRETS_PROFILE`)
*   `--timeout INTEGER`: Long-polling timeout in seconds. Default: `20`. (Env: `ENGINE_REST_TIMEOUT_SECONDS`)
*   `--poll-ttl INTEGER`: Fetch and lock duration in seconds. Default: `10`. (Env: `ENGINE_REST_POLL_TTL_SECONDS`)
*   `--lock-ttl INTEGER`: Lock duration for executing tasks in seconds. Default: `30`. (Env: `ENGINE_REST_LOCK_TTL_SECONDS`)
*   `--max-jobs INTEGER`: Maximum number of concurrent jobs. Default: `1`.
*   `--worker-id TEXT`: Worker ID to identify this client. Default: `operaton-robot-runner`. (Env: `TASKS_WORKER_ID`)
*   `--log-level TEXT`: Logging level (DEBUG, INFO, WARNING, ERROR). Default: `DEBUG`. (Env: `LOG_LEVEL`)
*   `--on-fail [FAIL|ERROR|COMPLETE]`: Default behavior when a task fails. Default: `FAIL`.

## `pur init`

Initialize a new robot package in the current directory.

```console
$ pur init [OPTIONS]
```

### Options

*   `--python`: Create a pure Python template instead of a Robot Framework template.
*   `--log-level TEXT`: Logging level. Default: `INFO`. (Env: `LOG_LEVEL`)

## `pur wrap`

Wrap the current directory into a `robot.zip` package for distribution.

```console
$ pur wrap [OPTIONS]
```

### Options

*   `--offline`: Include cached dependencies in the package (requires `uv` cache).
*   `--log-level TEXT`: Logging level. Default: `INFO`. (Env: `LOG_LEVEL`)

## `pur run`

Deploy process resources to the BPM engine and immediately start a new process instance.

```console
$ pur run [OPTIONS] RESOURCES...
```

### Arguments

*   `RESOURCES`: One or more paths to BPMN, DMN, or Form files.

### Options

*   `--name TEXT`: Name for the deployment. Default: `pur(jo) deployment`. (Env: `DEPLOYMENT_NAME`)
*   `--variables TEXT`: Initial process variables as a JSON string or path to a JSON file.
*   `--migrate / --no-migrate`: Whether to migrate existing instances to the new version. Default: `True`.
*   `--force`: Force deployment even if resources haven't changed. Default: `False`.
*   `--base-url TEXT`: Base URL of the BPM engine. Default: `http://localhost:8080/engine-rest`. (Env: `ENGINE_REST_BASE_URL`)
*   `--authorization TEXT`: Authorization header. (Env: `ENGINE_REST_AUTHORIZATION`)
*   `--log-level TEXT`: Logging level. Default: `INFO`. (Env: `LOG_LEVEL`)

## `pur operaton`

BPM engine operations. Also available as `pur bpm`.

### `pur operaton create`

Create a new BPMN, DMN, or Form file with unique IDs.

```console
$ pur operaton create [OPTIONS] FILENAME
```

*   `FILENAME`: Path to the file to create (must end in `.bpmn`, `.dmn`, or `.form`).

### `pur operaton deploy`

Deploy resources to the BPM engine.

```console
$ pur operaton deploy [OPTIONS] RESOURCES...
```

*   `RESOURCES`: Paths to files to deploy.
*   `--name TEXT`: Deployment name.
*   `--migrate / --no-migrate`: Migrate instances.
*   `--force`: Force deployment.
*   `--base-url TEXT`: Engine URL.
*   `--authorization TEXT`: Auth header.

### `pur operaton start`

Start a process instance by process definition key.

```console
$ pur operaton start [OPTIONS] KEY
```

*   `KEY`: The Process Definition Key (ID) of the process to start.
*   `--variables TEXT`: JSON string or file path for variables.
*   `--base-url TEXT`: Engine URL.
*   `--authorization TEXT`: Auth header.
