# US-007: Control Max Concurrent Jobs

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/unit/test_config.py

---

## Story

As an operator,
I want to control max concurrent jobs,
So that I can limit resource usage.

---

## Acceptance Criteria

### AC-1: Specify Max Jobs via CLI
**Given** I want to limit concurrent task execution
**When** I run `pur serve --max-jobs <n>`
**Then** the worker executes at most n tasks concurrently

### AC-2: Queue Behavior at Limit
**Given** max jobs limit is reached
**When** new tasks are available
**Then** the worker waits until a slot is free before locking new tasks

### AC-3: Default Max Jobs
**Given** no max jobs is specified
**When** I run `pur serve`
**Then** the worker uses a default value (e.g., 1)

---

## Notes

- Each concurrent job consumes memory and CPU
- Set based on available resources and task resource requirements
