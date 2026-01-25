# US-017: Force Deployment

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/cli/test_async_functions.py, tests/unit/test_deployment.py

---

## Story

As a developer,
I want to force deployment,
So that I can redeploy unchanged resources.

---

## Acceptance Criteria

### AC-1: Enable Force Deployment via CLI
**Given** resources have not changed since last deployment
**When** I run `pur run --force`
**Then** resources are redeployed anyway

### AC-2: Default Behavior (Skip Unchanged)
**Given** resources have not changed
**When** I run `pur run` without `--force`
**Then** deployment is skipped and existing deployment is used

### AC-3: Force Creates New Version
**Given** I run with `--force`
**When** deployment completes
**Then** a new version of the process definition is created

---

## Notes

- Useful for testing deployment scripts
- May create multiple identical versions
