# US-020: Start Process by Key

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/cli/test_async_functions.py

---

## Story

As a developer,
I want to start a process by key,
So that I can trigger specific process definitions.

---

## Acceptance Criteria

### AC-1: Start by Process Definition Key
**Given** a process definition is deployed
**When** I run `pur operaton start <key>`
**Then** a new instance of that process is started

### AC-2: Start with Variables
**Given** I want to start with initial variables
**When** I run `pur operaton start <key> --variable key=value`
**Then** the process starts with the specified variables

### AC-3: Display Instance ID
**Given** a process is started successfully
**When** the command completes
**Then** the process instance ID is displayed

---

## Notes

- Uses the latest version of the process definition
- Can specify a specific version if needed
