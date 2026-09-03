# US-021: Create AGENTS.md Guidance For Coding Agents

**Status:** Active
**Date:** 2026-09-03
**Related ADRs:** ADR-000, ADR-001
**Related Tests:** tests/integration/test_init.py

---

## Story

As a developer building automation packages with the help of LLM coding agents,
I want `pur init` to scaffold an `AGENTS.md` describing the generated package,
So that an agent can extend the package correctly without rediscovering the
`purjo` conventions from external documentation.

---

## Acceptance Criteria

### AC-1: Create AGENTS.md
**Given** I am in an empty directory
**When** I run `pur init --agents`
**Then** an `AGENTS.md` describing the generated robot package is created

### AC-2: Match The Task Template
**Given** I want a Robot task package
**When** I run `pur init --agents --task`
**Then** the generated `AGENTS.md` describes the `*** Tasks ***` flavour,
including `Task Template` and the `Run Robot Task` keyword

### AC-3: Opt-In Only
**Given** I run `pur init` without `--agents`
**When** the initialization completes
**Then** no `AGENTS.md` is created

### AC-4: Not Supported With The Python Template
**Given** the pure Python template is still experimental
**When** I run `pur init --agents --python`
**Then** the command fails with an error naming `--agents`, and no package is
created

### AC-5: Excluded From The Robot Package
**Given** I ran `pur init --agents`
**When** the project is wrapped with `pur wrap`
**Then** `AGENTS.md` is excluded from `robot.zip` through `.wrapignore`

---

## Notes

- The guidance is developer-facing only; it must never affect task execution
- Content is distilled from `./docs` and must stay in sync with it
- Two template files under `src/purjo/data/` back the test and task flavours
- Support for `--python` may be added once that template stabilises (US-011)
