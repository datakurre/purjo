# US-010: Initialize New Robot Package

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000, ADR-001
**Related Tests:** tests/cli/test_cli_advanced.py

---

## Story

As a developer,
I want to initialize a new robot package,
So that I can quickly scaffold a new task.

---

## Acceptance Criteria

### AC-1: Create Robot Package Structure
**Given** I am in an empty directory
**When** I run `pur init`
**Then** a Robot Framework package structure is created

### AC-2: Generate pyproject.toml
**Given** I run `pur init`
**When** the initialization completes
**Then** a `pyproject.toml` with purjo configuration is created

### AC-3: Create Sample Robot File
**Given** I run `pur init`
**When** the initialization completes
**Then** a sample `.robot` file is created

### AC-4: Create BPMN Template
**Given** I run `pur init`
**When** the initialization completes
**Then** a sample `.bpmn` file with external task is created

---

## Notes

- The generated files should be immediately usable
- pyproject.toml includes topic configuration
- Uses `uv` for dependency management
