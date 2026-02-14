# US-005: Configure Polling Timeouts

**Status:** Active
**Date:** 2026-01-25
**Related ADRs:** ADR-000
**Related Tests:** tests/cli/test_cli_advanced.py, tests/unit/test_config.py

---

## Story

As an operator,
I want to configure polling timeouts,
So that I can tune performance for my environment.

---

## Acceptance Criteria

### AC-1: Specify Async Response Timeout
**Given** I want to control how long the worker waits for tasks
**When** I run `pur serve --async-response-timeout <ms>`
**Then** the worker uses the specified timeout for long-polling

### AC-2: Default Timeout Value
**Given** no timeout is specified
**When** I run `pur serve`
**Then** the worker uses a sensible default timeout

### AC-3: Timeout Affects Responsiveness
**Given** a short timeout is configured
**When** tasks are infrequent
**Then** the worker reconnects more frequently

---

## Notes

- Longer timeouts reduce network overhead but delay shutdown
- The timeout should be less than any load balancer timeouts
