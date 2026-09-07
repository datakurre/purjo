# US-012: Wrap Project into robot.zip

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_basic.py, tests/unit/test_file_utils.py, tests/integration/test_workflows.py

---

## Story

As a developer,
I want to wrap my project into a robot.zip,
So that I can distribute my task package.

---

## Acceptance Criteria

### AC-1: Create robot.zip
**Given** I am in a project directory with `pyproject.toml`
**When** I run `pur wrap`
**Then** a `robot.zip` file is created

### AC-2: Include Project Files
**Given** I run `pur wrap`
**When** the zip is created
**Then** it includes all necessary project files

### AC-3: Exclude Unnecessary Files
**Given** I run `pur wrap`
**When** the zip is created
**Then** it excludes `.git`, `__pycache__`, and other build artifacts

---

## Notes

- The robot.zip is self-contained and portable
- Can be deployed to any environment with `uv` installed
