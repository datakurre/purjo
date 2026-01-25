# ADR-003: Architecture Overview

**Status:** Accepted
**Date:** 2026-01-25
**Location:** `./agents/adrs/ADR-003-architecture-overview.md`

---

## 1. Purpose

This ADR documents the high-level architecture of `purjo`, defining component responsibilities, integration points, and key design decisions.

---

## 2. Context

`purjo` is a bridge between the Operaton BPM engine and Robot Framework, enabling the execution of Robot Framework suites as external service tasks. Understanding the architecture is essential for making informed changes to the codebase.

---

## 3. Architecture Components

### 3.1 CLI (`src/purjo/main.py`)

The Command Line Interface is built using `typer`. It provides the following main commands:

| Command | Description |
|---------|-------------|
| `serve` | Starts the external task worker to poll and execute tasks |
| `init` | Initializes a new Robot Framework or Python project |
| `wrap` | Packages the current directory into a `robot.zip` file |
| `run` | Deploys resources to the BPM engine and starts a process instance |
| `operaton` | Provides direct access to BPM engine operations (create, deploy, start) |

**Responsibilities:**
- Parse command-line arguments
- Load configuration from `pyproject.toml`
- Coordinate between components
- Handle errors and display output

### 3.2 Runner (`src/purjo/runner.py`)

The runner is the core component responsible for executing Robot Framework tasks.

**Responsibilities:**
- **Task Creation**: `create_task` generates a handler function for a specific topic
- **Execution**: `build_run` executes the Robot Framework suite using `uv`
- **Variable Mapping**: Handles bidirectional mapping of variables between Operaton and Robot Framework
- **Result Handling**: Processes execution results including:
  - Reporting success or failure to Operaton
  - Handling BPMN errors
  - Uploading execution artifacts (`log.html`, `output.xml`) as task variables

### 3.3 Task Handling (`src/purjo/task.py`)

Defines the task handling logic and external task worker integration.

**Responsibilities:**
- Configure external task workers for topics
- Lock tasks from the engine
- Manage task lifecycle (lock, execute, complete/fail)
- Handle retries and timeouts

### 3.4 Purjo Library (`src/purjo/Purjo.py`)

A Robot Framework library for interacting with the runner from within test suites.

**Responsibilities:**
- Provide keywords for accessing task variables
- Enable setting output variables
- Support BPMN error throwing from Robot Framework

---

## 4. Execution Flow

When `purjo serve` is executed:

1. Configuration is read from `pyproject.toml`
2. External task workers are set up for configured topics
3. Workers begin long-polling the BPM engine
4. When a task is locked:
   a. `create_task` is invoked with task details
   b. A temporary directory is created for execution
   c. The robot package is extracted
   d. The Robot Framework suite is executed via `uv run`
   e. Results are parsed from `output.xml`
   f. Results are sent back to the engine (complete/fail/error)

---

## 5. Integration Points

### 5.1 Operaton Engine
- Communication via `operaton-tasks` library
- Uses External Task REST API
- Supports authentication via Basic/Bearer tokens

### 5.2 Robot Framework
- Suites executed as subprocesses
- Custom `RobotParser` facilitates variable exchange
- Results parsed from XML output

### 5.3 uv
- Used for dependency management
- Provides environment isolation during execution
- Enables reproducible builds

---

## 6. Key Design Decisions

| Decision | Rationale | Related ADR |
|----------|-----------|-------------|
| Use external task pattern | Enables distributed execution, fault tolerance | ADR-002 |
| Use `uv` for environment management | Fast, reproducible, supports offline mode | ADR-001 |
| Execute Robot Framework via subprocess | Isolation, clean environment per task | - |
| Store results as task variables | Enables access to logs from BPM cockpit | - |

---

## 7. Module Map

```
src/purjo/
├── main.py          # CLI entry point (typer app)
├── runner.py        # Task execution logic
├── task.py          # External task worker integration
├── Purjo.py         # Robot Framework library
├── config.py        # Configuration loading
├── secrets.py       # Secrets management
├── models.py        # Data models
├── deployment.py    # BPMN/DMN deployment
├── migration.py     # Process migration
├── serialization.py # Variable serialization
├── exceptions.py    # Custom exceptions
├── utils.py         # Utility functions
├── file_utils.py    # File operations
└── datetime_utils.py # DateTime handling
```

---

## 8. Consequences

- Clear separation of concerns between components
- Easy to test components in isolation
- External task pattern enables horizontal scaling
- `uv` dependency adds external tool requirement

---

## 9. Related

- **ADR-001**: Use of uv for environment management
- **ADR-002**: Use of external task pattern
- **US-001**: Serve robot packages as BPMN service tasks
