# Architecture

`purjo` is designed as a bridge between the Operaton BPM engine and Robot Framework, enabling the execution of Robot Framework suites as external service tasks.

## Core Components

### CLI (`src/purjo/main.py`)

The Command Line Interface (CLI) is built using `typer`. It provides the following main commands:

- `serve`: Starts the external task worker to poll and execute tasks.
- `init`: Initializes a new Robot Framework or Python project with `purjo` configuration.
- `wrap`: Packages the current directory into a `robot.zip` file for deployment.
- `run`: Deploys resources to the BPM engine and starts a process instance.
- `bpm`: Provides direct access to BPM engine operations (create, deploy, start).

### Runner (`src/purjo/runner.py`)

The runner is the core component responsible for executing Robot Framework tasks. Its key responsibilities include:

- **Task Creation**: `create_task` generates a handler function for a specific topic.
- **Execution**: `build_run` executes the Robot Framework suite using `uv`. This ensures that each execution runs in a managed Python environment.
- **Variable Mapping**: It handles the bidirectional mapping of variables between Operaton (BPMN) and Robot Framework.
- **Result Handling**: It processes the execution results, including:
  - Reporting success or failure to Operaton.
  - Handling BPMN errors.
  - Uploading execution artifacts like `log.html` and `output.xml` as task variables.

### Task Handling

When `purjo serve` is executed:
1. It reads the configuration from `pyproject.toml`.
2. It sets up external task workers for the configured topics.
3. When a task is locked, `create_task` is invoked.
4. A temporary directory is created for the execution.
5. The Robot Framework suite is executed within this environment.
6. Results are parsed and sent back to the engine.

## Integration Points

- **Operaton Engine**: Communication is handled via the `operaton-tasks` library, which uses the External Task REST API.
- **Robot Framework**: Suites are executed as subprocesses. A custom `RobotParser` is injected to facilitate variable exchange.
- **uv**: Used for dependency management and environment isolation during task execution.
