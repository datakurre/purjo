# Agent Documentation Index

This directory contains comprehensive documentation for agents working with `purjo`.

## Overview

`purjo` is an experimental command line tool for orchestrating [Robot Framework](https://robotframework.org/) test or task suites with the [Operaton](https://operaton.org/) BPM engine.

## Contents

### Architecture Decision Records (ADRs)
- [ADR-000: Agent-Oriented Repository Context and Autonomous Guidance](./adrs/ADR-000-agent-guidance.md)
- [ADR-001: Use uv for Environment Management](./adrs/ADR-001-use-uv-for-environment-management.md)
- [ADR-002: Use External Task Pattern](./adrs/ADR-002-use-external-task-pattern.md)
- [ADR-003: Architecture Overview](./adrs/ADR-003-architecture-overview.md)

### Reference Documentation
- [GLOSSARY.md](./GLOSSARY.md): Canonical terminology and domain definitions

### User Stories
- [stories/](./stories/): User stories defining product intent

## Quick Links

| Resource | Description |
|----------|-------------|
| [AGENTS.md](../AGENTS.md) | Entry point for LLM agents |
| [tests/](../tests/) | Behavioral truth (test suite) |
| [src/purjo/](../src/purjo/) | Implementation |
| [docs/](../docs/) | User documentation |

## Navigation

For agents, the recommended reading order is:

1. **AGENTS.md** - Navigation and rules
2. **ADRs** - Architectural constraints
3. **User Stories** - Product intent
4. **Tests** - Behavioral truth
5. **Implementation** - Source code
