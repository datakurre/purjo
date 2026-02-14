# US-008: Set Worker ID

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/unit/test_config.py

---

## Story

As an operator,
I want to set a worker ID,
So that I can identify task workers in logs.

---

## Acceptance Criteria

### AC-1: Specify Worker ID via CLI
**Given** I want to identify this worker instance
**When** I run `pur serve --worker-id <id>`
**Then** the worker uses the specified ID in communications

### AC-2: Auto-Generated Worker ID
**Given** no worker ID is specified
**When** I run `pur serve`
**Then** the worker generates a unique ID (e.g., hostname-based)

### AC-3: Worker ID in Logs
**Given** a worker ID is set
**When** tasks are executed
**Then** the worker ID appears in log messages

---

## Notes

- Worker IDs help trace task execution across distributed workers
- Should be unique across all workers in a deployment
