# US-014: Deploy and Start Process

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/cli/test_async_functions.py

---

## Story

As a developer,
I want to deploy and start a process in one command,
So that I can quickly test my workflows.

---

## Acceptance Criteria

### AC-1: Deploy Resources
**Given** BPMN/DMN/Form resources exist in the project
**When** I run `pur run`
**Then** resources are deployed to the BPM engine

### AC-2: Start Process Instance
**Given** resources are deployed
**When** `pur run` completes deployment
**Then** a new process instance is started

### AC-3: Wait for Completion (Optional)
**Given** I want to wait for the process to complete
**When** I run `pur run --wait`
**Then** the command blocks until the process finishes

---

## Notes

- Combines `pur operaton deploy` and `pur operaton start`
- Ideal for development and testing workflows
