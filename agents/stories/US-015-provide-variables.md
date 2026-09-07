# US-015: Provide Initial Process Variables

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/cli/test_async_functions.py

---

## Story

As a developer,
I want to provide initial process variables,
So that I can test different scenarios.

---

## Acceptance Criteria

### AC-1: Specify Variables via CLI
**Given** I want to start a process with specific variables
**When** I run `pur run --variable key=value`
**Then** the process starts with the specified variables

### AC-2: Multiple Variables
**Given** I need multiple variables
**When** I specify multiple `--variable` options
**Then** all variables are passed to the process

### AC-3: Variable Types
**Given** I specify a variable value
**When** the process starts
**Then** the value is properly typed (string, number, boolean, JSON)

---

## Notes

- Variables can also be read from a file using `--variables-file`
- JSON values are parsed automatically
