# US-001: Serve Robot Packages as BPMN Service Tasks

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000, ADR-002
**Related Tests:** tests/cli/test_cli_advanced.py, tests/unit/test_runner.py, tests/unit/test_purjo_lib.py, tests/unit/test_robot_parser.py, tests/integration/test_workflows.py

---

## Story

As an operator,
I want to serve robot packages as BPMN service tasks,
So that I can execute automated tasks from the BPM engine.

---

## Acceptance Criteria

### AC-1: Start External Task Worker
**Given** a valid `pyproject.toml` with topic configurations
**When** I run `pur serve`
**Then** the worker starts polling the BPM engine for tasks

### AC-2: Execute Robot Suite on Task Receipt
**Given** the worker is running and a task is published on a configured topic
**When** the worker locks the task
**Then** the corresponding Robot Framework suite is executed

### AC-3: Report Results to Engine
**Given** a Robot Framework suite has completed execution
**When** the execution finishes
**Then** the results are reported back to the BPM engine

---

## Notes

- The worker uses long-polling to efficiently wait for tasks
- Each topic maps to a specific robot package
- Execution happens in an isolated environment managed by `uv`
