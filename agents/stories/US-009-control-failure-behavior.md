# US-009: Control Failure Behavior

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/unit/test_config.py, tests/unit/test_runner.py

---

## Story

As an operator,
I want to control failure behavior (FAIL/ERROR/COMPLETE),
So that I can handle task failures appropriately.

---

## Acceptance Criteria

### AC-1: FAIL Mode (Default)
**Given** failure mode is set to FAIL
**When** a task execution fails
**Then** the failure is reported to the engine with retry information

### AC-2: ERROR Mode
**Given** failure mode is set to ERROR
**When** a task execution fails
**Then** a BPMN error is thrown that can be caught by error boundary events

### AC-3: COMPLETE Mode
**Given** failure mode is set to COMPLETE
**When** a task execution fails
**Then** the task is marked as complete with failure details in output variables

### AC-4: Specify Failure Mode via CLI
**Given** I want to use a specific failure mode
**When** I run `pur serve --on-failure <mode>`
**Then** the worker uses the specified failure handling mode

---

## Notes

- FAIL allows the engine to retry the task based on configuration
- ERROR enables BPMN-level error handling
- COMPLETE is useful for tasks that should always proceed in the workflow
