# ADR-000: Agent-Oriented Repository Context and Autonomous Guidance

**Status:** Accepted
**Date:** 2025-12-18
**Location:** `./agents/adrs/ADR-000-agent-guidance.md`

---

## 1. Purpose

This ADR defines how LLM coding agents should understand, navigate, and safely modify this repository. It provides an **explicit self-guidance model** to reduce hallucination, ensure architectural compliance, and maintain product intent.

---

## 2. Problem Statement

LLM agents struggle when:

- Intent is implicit or scattered
- Tests define implementation mechanics but not business meaning
- ADRs or documentation lack explicit constraints
- There are unclear rules for autonomous decision-making

This ADR creates a structured, self-reinforcing system for agent reasoning.

---

## 3. Key Principles for LLM Agents

1. **Tests = Truth**: Tests encode observable, verifiable behavior.
2. **ADRs = Constraints**: Architectural rules define limits.
3. **User Stories = Intent**: Stories explain why behavior exists.
4. **AGENTS.md = Navigation & Rules**: Guides reading, priorities, and decision protocols.
5. **Vocabulary Canon**: Standard terminology reduces semantic drift.
6. **Invariants & Sentinel Tests**: Identify unbreakable rules.
7. **Escalation Protocols**: Explicit guidance for ambiguity or conflicts.

---

## 4. Repository Structure (Canonical)

```
./AGENTS.md                # Entry point for LLM agents
./agents/
  /adrs/                   # Architectural Decision Records
    ADR-000-agent-guidance.md
  /stories/                # User stories (product intent)
    US-001-...
  index.md                 # Agent documentation index
  GLOSSARY.md              # Canonical terminology
/tests/                    # Behavioral truth
/src/                      # Implementation
```

---

## 5. Artifact Roles & Cross-Linking

- **Tests:** Reference US and ADR IDs in headers/docstrings. Named to reflect behavior.
- **User Stories:** Reference tests and ADRs. Acceptance criteria must be executable.
- **ADRs:** Define constraints, reference affected modules, tests, and stories. Prescriptive.
- **AGENTS.md:** Defines reading order, work loop, precedence, and escalation rules.
- **index.md:** Agent documentation index and orientation guide.
- **GLOSSARY.md:** Canonical vocabulary to reduce semantic drift.

**Precedence:** Tests > ADRs > User Stories > Inline Comments > Assumptions

---

## 6. BDD Guidance (Future Consideration)

BDD scenarios are not currently implemented. If the project adopts a BDD framework
(e.g. `pytest-bdd`), the following guidelines apply:

- **Use:** User-visible workflows, cross-module behavior, API-level rules.
- **Avoid:** Algorithms, parsing, data transformations, performance-critical logic.
- **Rules:**
  - Steps must be concrete and self-contained.
  - Avoid abstract steps; redundancy is acceptable.
  - Step definitions must contain minimal logic.

**Example Gherkin Scenario:**

```gherkin
# Covers US-014
# Constrained by ADR-003, ADR-000
Scenario: Creating a user with existing email
  Given a user exists with email "a@example.com"
  When another user is created with email "a@example.com"
  Then the request fails with a conflict error
```

---

## 7. Agent Self-Guidance Work Loop

Before making changes, agents MUST:

1. State the perceived goal.
2. Identify relevant tests, user stories, ADRs.
3. Identify architectural and behavioral constraints.
4. Propose minimal change strategy.
5. Add or update tests for new behavior.
6. Implement change.
7. Re-evaluate changes against stories, ADRs, and tests.

**If any step fails, escalate rather than guessing.**

---

## 8. Agent Documentation Index (`index.md`)

- Purpose: Fast understanding of repo scope and invariants.
- Location: `./agents/index.md`
- Sections:
  - What the system does / does not
  - Core invariants
  - Starting points: AGENTS.md → ADRs → User Stories → Tests → Implementation

---

## 9. Vocabulary Canon (`GLOSSARY.md`)

- Define domain terms, standard phrasing, and deprecated synonyms.
- Example:
  - "User" = persisted account entity
  - "Conflict error" = HTTP 409
  - "Deactivate" ≠ "Delete"

---

## 10. Invariants & Sentinel Tests

- Define unbreakable rules that must never fail unless a new ADR is created.
- Example test marker or naming convention: `test_invariants_*`

---

## 11. Decision Escalation Rules

Agents MUST escalate when:

- Tests conflict with user stories.
- ADR constraints are violated.
- Behavior is unclear or ambiguous.
- Multiple interpretations are plausible.

Escalation actions:

- Add failing tests to clarify intent.
- Propose new or updated ADRs.
- Document uncertainties in a TODO list.

---

## 12. Commit Message Guidelines

All commits MUST follow the [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) specification.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Standard Types

- `feat:` - New feature (correlates with MINOR in SemVer)
- `fix:` - Bug fix (correlates with PATCH in SemVer)
- `docs:` - Documentation only changes
- `style:` - Code style changes (formatting, missing semi-colons, etc.)
- `refactor:` - Code refactoring without changing behavior
- `perf:` - Performance improvements
- `test:` - Adding or modifying tests
- `build:` - Build system or dependency changes
- `ci:` - CI/CD configuration changes
- `chore:` - Other changes that don't modify src or test files
- `revert:` - Reverts a previous commit

### Breaking Changes

- Append `!` after type/scope: `feat!:` or `feat(api)!:`
- Or add `BREAKING CHANGE:` footer

### Examples

```bash
# Feature with scope
feat(auth): add OAuth2 authentication support

# Bug fix
fix: prevent race condition in request handler

# Breaking change with !
feat!: drop support for Node 14

# Breaking change with footer
feat: rename config command to setup

BREAKING CHANGE: The `config` command is now `setup`.
Update all scripts accordingly.

# Multiple paragraphs and footers
fix: prevent racing of concurrent requests

Introduce a request id and reference to latest request.
Dismiss incoming responses other than from latest request.

Refs: #123
Reviewed-by: John Doe
```

### Agent Requirements

When creating commits, agents MUST:
1. Use lowercase for type and scope
2. Use imperative mood in description ("add" not "added")
3. Keep description under 72 characters
4. Reference related ADRs, user stories, or issues in footer when applicable
5. Add `BREAKING CHANGE:` footer when changing public APIs
6. Use project-specific scopes consistently (define in project documentation)

---

## 13. Agent TODO List Format

Agents must use this format for review and compliance tasks:

```
* [ ] Identify missing or outdated user stories under ./agents/stories
* [ ] Map existing tests to user stories and ADRs
* [ ] Add references in test headers to US and ADR IDs
* [ ] Review ADRs for missing constraints or outdated decisions
* [ ] Convert suitable high-level tests to BDD scenarios
* [ ] Simplify or refactor over-abstracted BDD steps
* [ ] Add tests where acceptance criteria are not executable
* [ ] Flag conflicts between tests, stories, and ADRs
* [ ] Propose new ADRs where architectural intent is implicit
```

---

## 14. Reference

The canonical `AGENTS.md` is maintained at the repository root (`./AGENTS.md`).
Refer to it directly rather than duplicating its content here.

---

## 15. Consequences

- Safer autonomous agent work.
- Reduced hallucination and misinterpretation.
- Explicit artifact precedence and cross-linking.
- Slight redundancy and increased maintenance overhead are accepted.

This ADR establishes the **foundation for agent-first repository governance** and self-guided LLM contributions.

