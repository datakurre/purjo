# US-011: Create Pure Python Template

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000, ADR-001
**Related Tests:** tests/cli/test_cli_advanced.py

---

## Story

As a developer,
I want to create a pure Python template,
So that I can write tasks in Python instead of Robot Framework.

---

## Acceptance Criteria

### AC-1: Specify Python Template
**Given** I want to write tasks in Python
**When** I run `pur init --python`
**Then** a Python-based package structure is created

### AC-2: Generate Python Task File
**Given** I run `pur init --python`
**When** the initialization completes
**Then** a sample Python task file is created

### AC-3: Robot Framework Integration
**Given** a Python template is created
**When** the task is executed
**Then** Python functions are callable from Robot Framework

---

## Notes

- Python templates use Robot Framework's Python library interface
- Allows developers unfamiliar with Robot syntax to contribute
- pyproject.toml configuration is the same as Robot templates
