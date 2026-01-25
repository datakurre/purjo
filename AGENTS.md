# AGENTS.md

## Purpose

Defines how LLM coding agents read, navigate, and safely modify this repository.

`purjo` is an experimental command line tool for orchestrating [Robot Framework](https://robotframework.org/) test or task suites with the [Operaton](https://operaton.org/) BPM engine.

---

## Source of Truth

- **Tests** define correct behavior (executable truth)
- **ADRs** define architectural constraints
- **User Stories** define product intent
- **Precedence:** Tests > ADRs > User Stories > Inline comments > Assumptions

---

## Agent Work Loop

Before making changes, agents MUST:

1. **Identify** the task goal
2. **Locate** relevant tests, stories, ADRs
3. **Identify** constraints from ADRs
4. **Propose** minimal change strategy
5. **Add or update** tests for new behavior
6. **Implement** code changes
7. **Re-evaluate** against stories, ADRs, and tests

**If any step is unclear, escalate rather than guessing.**

---

## Repository Map

| Path | Description |
|------|-------------|
| `./AGENTS.md` | Entry point for LLM agents (this file) |
| `./agents/` | Agent-oriented documentation |
| `./agents/adrs/` | Architectural Decision Records |
| `./agents/stories/` | User stories (product intent) |
| `./agents/GLOSSARY.md` | Canonical terminology |
| `./agents/index.md` | Documentation index |
| `./tests/` | Behavioral truth (test suite) |
| `./src/purjo/` | Implementation |
| `./docs/` | User documentation |
| `./examples/` | Example projects |

### Key Source Files

| File | Responsibility |
|------|----------------|
| `src/purjo/main.py` | CLI entry point (typer app) |
| `src/purjo/runner.py` | Task execution logic |
| `src/purjo/task.py` | External task worker integration |
| `src/purjo/Purjo.py` | Robot Framework library |
| `src/purjo/config.py` | Configuration loading |
| `src/purjo/secrets.py` | Secrets management |

---

## Change Rules

- Do not change public APIs without updating tests and stories
- Do not violate ADRs without creating a new ADR
- When uncertain, add a failing test demonstrating expected behavior
- All commits must follow [Conventional Commits](https://www.conventionalcommits.org/)

---

## Escalation Rules

Stop and escalate if:

- Tests conflict with user stories
- ADRs would be violated
- Behavior is unclear or ambiguous
- Multiple interpretations are plausible

Escalation actions:

- Add failing tests to clarify intent
- Propose new or updated ADRs
- Document uncertainties in a TODO list

---

## Core Invariants

These invariants are enforced by sentinel tests in `tests/test_invariants.py`. 
Violations indicate fundamental architectural problems that must be fixed immediately.

### 1. Isolated Execution Environments

**Requirement:** Robot packages must execute in isolated environments using `uv`.

**Rationale:** Prevents dependency conflicts and ensures reproducible execution across different deployment environments.

**Enforced by:** ADR-001

**Tests:** `tests/test_invariants.py::TestInvariant1_IsolatedEnvironments`

### 2. Complete Task Result Reporting

**Requirement:** Task results must ALWAYS be reported to the BPM engine, regardless of outcome (success, failure, or error).

**Rationale:** The BPM engine must track process state accurately. Unreported task outcomes cause process instances to hang indefinitely.

**Enforced by:** ADR-002

**Tests:** `tests/test_invariants.py::TestInvariant2_TaskResultsReporting`

### 3. Secrets Safety

**Requirement:** Secrets must NEVER be logged or included in output artifacts (logs, reports, variables).

**Rationale:** Prevents credential leaks and maintains security compliance.

**Enforced by:** US-004, ADR-003

**Tests:** `tests/test_invariants.py::TestInvariant3_SecretsSafety`

### 4. Single CLI Entry Point

**Requirement:** The CLI (`pur` command via `main.py`) must be the only entry point for all user operations.

**Rationale:** Ensures consistent behavior, proper initialization, and centralized configuration handling.

**Enforced by:** ADR-003

**Tests:** `tests/test_invariants.py::TestInvariant4_CLIEntryPoint`

---

## Documentation

For comprehensive agent documentation, see:

- [agents/index.md](./agents/index.md) - Documentation index
- [agents/GLOSSARY.md](./agents/GLOSSARY.md) - Domain terminology
- [agents/adrs/](./agents/adrs/) - Architectural decisions
- [agents/stories/](./agents/stories/) - User stories
