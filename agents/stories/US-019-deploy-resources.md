# US-019: Deploy Resources Separately

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/cli/test_async_functions.py, tests/unit/test_deployment.py

---

## Story

As a developer,
I want to deploy resources separately,
So that I can manage deployments independently.

---

## Acceptance Criteria

### AC-1: Deploy Specific Resources
**Given** I want to deploy only specific files
**When** I run `pur operaton deploy <file>`
**Then** only the specified resource is deployed

### AC-2: Deploy Directory
**Given** I want to deploy all resources in a directory
**When** I run `pur operaton deploy <directory>`
**Then** all BPMN/DMN/Form files in the directory are deployed

### AC-3: Deployment Name
**Given** I want to identify the deployment
**When** I run `pur operaton deploy --name <name>`
**Then** the deployment is created with the specified name

---

## Notes

- Separate from `pur run` which combines deploy and start
- Useful for deploying shared resources like DMN tables
