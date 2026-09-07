# US-002: Configure BPM Engine Base URL

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/unit/test_config.py

---

## Story

As an operator,
I want to configure the BPM engine base URL,
So that I can connect to different environments (dev, staging, production).

---

## Acceptance Criteria

### AC-1: Specify Engine URL via CLI
**Given** I want to connect to a specific BPM engine
**When** I run `pur serve --engine-url <url>`
**Then** the worker connects to the specified engine

### AC-2: Default Engine URL
**Given** no engine URL is specified
**When** I run `pur serve`
**Then** the worker uses the default URL (http://localhost:8080/engine-rest)

### AC-3: Environment Variable Override
**Given** the `OPERATON_ENGINE_URL` environment variable is set
**When** I run `pur serve` without `--engine-url`
**Then** the worker uses the URL from the environment variable

---

## Notes

- CLI arguments take precedence over environment variables
- The URL should not include a trailing slash
