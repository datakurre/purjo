# US-016: Migrate Existing Instances

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/cli/test_async_functions.py, tests/unit/test_migration.py

---

## Story

As a developer,
I want to migrate existing instances,
So that running processes use the new version.

---

## Acceptance Criteria

### AC-1: Enable Migration via CLI
**Given** existing process instances are running
**When** I run `pur run --migrate`
**Then** running instances are migrated to the new version

### AC-2: Safe Migration
**Given** I run with migration enabled
**When** migration fails for some instances
**Then** errors are reported without affecting other instances

### AC-3: Migration Summary
**Given** migration completes
**When** results are displayed
**Then** the number of migrated instances is shown

---

## Notes

- Migration uses Operaton's process instance migration API
- Not all process changes are compatible with migration
