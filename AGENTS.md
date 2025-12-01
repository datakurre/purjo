# Agents

`purjo` is an experimental command line tool for orchestrating [Robot Framework](https://robotframework.org/) test or task suites with the [Operaton](https://operaton.org/) BPM engine.

## Purpose

The main purpose of `purjo` is to act as a bridge between Operaton BPM engine and Robot Framework. It allows:
- Long-polling external service tasks from Operaton.
- Executing mapped Robot Framework suites using `uv` for environment management.
- Reporting results back to the engine.

## Structure

The project is structured as follows:
- `src/purjo`: Contains the source code of the CLI tool.
  - `main.py`: Entry point for the CLI.
  - `runner.py`: Handles the execution of Robot Framework tasks.
  - `task.py`: Defines the task handling logic.
  - `Purjo.py`: Robot Framework library for interacting with the runner.
- `docs/`: Documentation files.
- `examples/`: Example projects and configurations.

## Documentation

For more comprehensive documentation for agents, please refer to the [agents](./agents/index.md) directory.
