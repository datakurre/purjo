# US-003: Provide Authorization Credentials

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py

---

## Story

As an operator,
I want to provide authorization credentials,
So that I can authenticate with secured BPM engines.

---

## Acceptance Criteria

### AC-1: Specify Authorization Header via CLI
**Given** the BPM engine requires authentication
**When** I run `pur serve --authorization <credentials>`
**Then** the worker includes the authorization header in requests

### AC-2: Environment Variable for Authorization
**Given** I want to avoid exposing credentials in CLI history
**When** I set the `OPERATON_AUTHORIZATION` environment variable
**Then** the worker uses the authorization from the environment variable

### AC-3: Basic Auth Format Support
**Given** I need to use Basic authentication
**When** I provide credentials in `Basic <base64>` format
**Then** the worker authenticates successfully

---

## Notes

- Credentials should never be logged
- CLI arguments take precedence over environment variables
- Supports Bearer tokens and Basic authentication
