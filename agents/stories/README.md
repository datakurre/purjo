# User Stories

This directory contains user stories that define the product intent for `purjo`.

## Naming Convention

Stories follow the naming convention: `US-XXX-short-description.md`

Where:
- `US` = User Story prefix
- `XXX` = 3-digit sequential number (e.g., 001, 002)
- `short-description` = Kebab-case summary of the story

## Story Template

Each user story should follow this format:

```markdown
# US-XXXX: Title

**Status:** Draft | Active | Deprecated
**Date:** YYYY-MM-DD
**Related ADRs:** ADR-XXXX, ADR-YYYY
**Related Tests:** test_file.py::test_name

---

## Story

As a [role],
I want [feature/capability],
So that [benefit/value].

---

## Acceptance Criteria

### AC-1: [Criterion Title]
**Given** [precondition]
**When** [action]
**Then** [expected outcome]

### AC-2: [Criterion Title]
**Given** [precondition]
**When** [action]
**Then** [expected outcome]

---

## Notes

Additional context, edge cases, or implementation hints.
```

## Story Index

### `pur serve` Command
- [US-001](./US-001-serve-robot-packages.md): Serve robot packages as BPMN service tasks
- [US-002](./US-002-configure-engine-url.md): Configure BPM engine base URL
- [US-003](./US-003-provide-authorization.md): Provide authorization credentials
- [US-004](./US-004-configure-secrets.md): Configure secrets profiles
- [US-005](./US-005-configure-polling-timeout.md): Configure polling timeouts
- [US-006](./US-006-set-lock-ttl.md): Set lock TTL
- [US-007](./US-007-control-max-jobs.md): Control max concurrent jobs
- [US-008](./US-008-set-worker-id.md): Set worker ID
- [US-009](./US-009-control-failure-behavior.md): Control failure behavior

### `pur init` Command
- [US-010](./US-010-init-robot-package.md): Initialize new robot package
- [US-011](./US-011-init-python-template.md): Create pure Python template

### `pur wrap` Command
- [US-012](./US-012-wrap-robot-zip.md): Wrap project into robot.zip
- [US-013](./US-013-include-offline-deps.md): Include cached dependencies offline

### `pur run` Command
- [US-014](./US-014-deploy-and-start.md): Deploy and start process
- [US-015](./US-015-provide-variables.md): Provide initial process variables
- [US-016](./US-016-migrate-instances.md): Migrate existing instances
- [US-017](./US-017-force-deployment.md): Force deployment

### `pur operaton` Command
- [US-018](./US-018-create-resources.md): Create BPMN/DMN/Form files
- [US-019](./US-019-deploy-resources.md): Deploy resources separately
- [US-020](./US-020-start-process.md): Start process by key
