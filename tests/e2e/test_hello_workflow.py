"""End-to-end happy-path test using the `hello_example` fixture package.

Automates the "End-to-end testing" checklist from
docs/development_environment.md: deploy the fixture's `hello.bpmn`, start an
instance, run `pur serve` against the package, and verify through the
engine's history REST API that the instance reached the "Test passed" end
event with the expected output variable.

Related User Stories:
- US-001: Serve robot packages
- US-014: Deploy and start process

Related ADRs:
- ADR-002: Use external task pattern
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
import aiohttp
import asyncio

HELLO_DIR = Path(__file__).parent / "fixtures" / "hello_example"
HELLO_BPMN = HELLO_DIR / "hello.bpmn"

TEST_PASSED_ACTIVITY_ID = "Event_07zpz98"

# hello.robot rolls a die and takes the "Random failure" boundary-error path
# on a 1 or 2 (about a third of the time). Starting several instances and
# requiring at least one to reach "Test passed" keeps the assertion
# deterministic without modifying the fixture package itself.
ATTEMPTS = 6


async def test_hello_workflow_reaches_test_passed(
    basic_auth_env: dict[str, str],
    deploy_and_start: Callable[[Path, str, str, dict[str, str]], str],
    run_pur_serve: Callable[..., AbstractContextManager["Any"]],
    wait_for_instance_ended: Callable[..., Any],
    ended_activity_ids: Callable[..., Any],
    process_variables: Callable[..., Any],
    serve_output: Callable[[Any], str],
    engine_session: aiohttp.ClientSession,
) -> None:
    authorization = basic_auth_env["ENGINE_REST_AUTHORIZATION"]
    instance_ids = [
        deploy_and_start(HELLO_BPMN, "e2e-hello", '{"name": "World"}', basic_auth_env)
        for _ in range(ATTEMPTS)
    ]

    with run_pur_serve(HELLO_DIR, env=basic_auth_env) as process:
        await asyncio.gather(
            *(
                wait_for_instance_ended(engine_session, authorization, instance_id)
                for instance_id in instance_ids
            )
        )
        passed_instance_id = None
        for instance_id in instance_ids:
            activity_ids = await ended_activity_ids(
                engine_session, authorization, instance_id
            )
            if TEST_PASSED_ACTIVITY_ID in activity_ids:
                passed_instance_id = instance_id
                break

        assert passed_instance_id, (
            f'none of {ATTEMPTS} attempts reached "Test passed"; '
            f"pur serve output:\n{serve_output(process)}"
        )
        variables = await process_variables(
            engine_session, authorization, passed_instance_id
        )

    assert variables["message"] == "Hello World!"
