# US-004: Configure Secrets Profiles

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/unit/test_secrets.py, tests/unit/test_purjo_lib.py, tests/integration/test_workflows.py

---

## Story

As an operator,
I want to configure secrets profiles,
So that I can securely inject sensitive values into tasks.

---

## Acceptance Criteria

### AC-1: Specify Secrets Profile via CLI
**Given** a secrets profile is defined
**When** I run `pur serve --secrets <profile>`
**Then** the worker loads secrets from the specified profile

### AC-2: Multiple Secrets Profiles
**Given** I need secrets from multiple sources
**When** I specify multiple `--secrets` options
**Then** secrets are merged with later profiles taking precedence

### AC-3: Secrets Available in Robot Framework
**Given** secrets are configured
**When** a Robot Framework suite runs
**Then** secrets are available as variables in the suite

---

## Notes

- Secrets are never logged or included in output artifacts
- Profiles can be YAML or JSON files
- Environment variables can also be used as secret sources
