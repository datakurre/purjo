# US-018: Create BPMN/DMN/Form Files

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_basic.py

---

## Story

As a developer,
I want to create BPMN/DMN/Form files with unique IDs,
So that I can avoid ID conflicts.

---

## Acceptance Criteria

### AC-1: Create BPMN File
**Given** I want to create a new process
**When** I run `pur operaton create bpmn <name>`
**Then** a new BPMN file is created with a unique process ID

### AC-2: Create DMN File
**Given** I want to create a decision table
**When** I run `pur operaton create dmn <name>`
**Then** a new DMN file is created with a unique decision ID

### AC-3: Create Form File
**Given** I want to create a form
**When** I run `pur operaton create form <name>`
**Then** a new form file is created with a unique form ID

### AC-4: Unique ID Generation
**Given** I create multiple resources
**When** IDs are generated
**Then** each ID is unique and follows naming conventions

---

## Notes

- IDs are based on the file name plus a unique suffix
- Helps avoid conflicts when merging processes from different developers
