# US-013: Include Cached Dependencies Offline

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000, ADR-001
**Related Tests:** tests/cli/test_cli_basic.py, tests/unit/test_file_utils.py

---

## Story

As a developer,
I want to include cached dependencies offline,
So that I can deploy to air-gapped environments.

---

## Acceptance Criteria

### AC-1: Specify Offline Mode
**Given** I need to deploy without internet access
**When** I run `pur wrap --offline`
**Then** the robot.zip includes all cached dependencies

### AC-2: Dependencies Bundled
**Given** I run `pur wrap --offline`
**When** the zip is created
**Then** all Python package wheels are included

### AC-3: Install Without Network
**Given** a robot.zip with offline dependencies
**When** it is executed in an air-gapped environment
**Then** dependencies are installed from the bundled cache

---

## Notes

- Increases package size significantly
- Dependencies must be pre-cached using `uv`
- Useful for secure or isolated environments
