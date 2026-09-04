"""End-to-end failure-path test using the `fail_example` fixture package.

Its `hello.robot` fails unconditionally (a plain `Fail` before anything else
runs), so unlike `hello_example` it deterministically exercises the BPMN
error boundary event. This proves Invariant 2 ("Task
results must ALWAYS be reported to the BPM engine",
`tests/test_invariants.py::TestInvariant2_TaskResultsReporting`) against a
live engine, not just in the mocked unit suite.

Related User Stories:
- US-001: Serve robot packages
- US-009: Control failure behavior

Related ADRs:
- ADR-002: Use external task pattern
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
import aiohttp

FAIL_EXAMPLE_DIR = Path(__file__).parent / "fixtures" / "fail_example"
FAIL_EXAMPLE_BPMN = FAIL_EXAMPLE_DIR / "hello.bpmn"

TEST_FAILED_ACTIVITY_ID = "Event_0p6xzhn"


async def test_failure_workflow_reaches_test_failed(
    basic_auth_env: dict[str, str],
    deploy_and_start: Callable[[Path, str, str, dict[str, str]], str],
    run_pur_serve: Callable[..., AbstractContextManager["Any"]],
    wait_for_instance_ended: Callable[..., Any],
    ended_activity_ids: Callable[..., Any],
    serve_output: Callable[[Any], str],
    engine_session: aiohttp.ClientSession,
) -> None:
    authorization = basic_auth_env["ENGINE_REST_AUTHORIZATION"]
    instance_id = deploy_and_start(
        FAIL_EXAMPLE_BPMN, "e2e-fail-example", "", basic_auth_env
    )

    with run_pur_serve(FAIL_EXAMPLE_DIR, env=basic_auth_env) as process:
        await wait_for_instance_ended(engine_session, authorization, instance_id)
        activity_ids = await ended_activity_ids(
            engine_session, authorization, instance_id
        )
        assert TEST_FAILED_ACTIVITY_ID in activity_ids, (
            f'instance {instance_id} did not reach "Test failed" '
            f"({activity_ids}); pur serve output:\n{serve_output(process)}"
        )
