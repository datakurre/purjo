# US-006: Set Lock TTL

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/unit/test_config.py

---

## Story

As an operator,
I want to set lock TTL,
So that tasks are properly reserved during execution.

---

## Acceptance Criteria

### AC-1: Specify Lock Duration via CLI
**Given** I want to control how long a task is locked
**When** I run `pur serve --lock-ttl <ms>`
**Then** locked tasks are reserved for the specified duration

### AC-2: Lock Extension for Long Tasks
**Given** a task takes longer than the lock TTL
**When** the task is still executing
**Then** the lock is extended before expiration

### AC-3: Default Lock TTL
**Given** no lock TTL is specified
**When** I run `pur serve`
**Then** the worker uses a sensible default (e.g., 300000ms)

---

## Notes

- If a worker crashes without releasing a lock, the task becomes available after TTL expires
- Lock TTL should be longer than typical task execution time
