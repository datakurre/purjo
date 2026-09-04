"""End-to-end secrets and OAuth2 tests.

Secrets: proves Invariant 3 ("Secrets must NEVER be logged or included in
output artifacts", `tests/test_invariants.py::TestInvariant3_SecretsSafety`)
against a live `pur serve` process, not just the mocked unit suite.

OAuth2: `purjo` itself has no OAuth2 logic of its own -- authentication is
handled entirely by its `operaton-tasks` dependency
(`operaton.tasks.oauth2.token_manager`), which is driven purely by the
`OAUTH2_CLIENT_ID` / `OAUTH2_CLIENT_SECRET` / `OAUTH2_TOKEN_URL` environment
variables already present in `.env.example`. There is no other coverage of
this anywhere in the repo, so this is the only test proving the Keycloak
realm (`fixture/keycloak/operaton-realm.json`) and
`services.operaton.oauth2` wiring actually work together.

Both scenarios below deploy the same deterministic
`fixtures/secrets_example` package (a single service task, no dice-rolled
failure branch like `hello_example`), so the assertions aren't a coin flip.

Related User Stories:
- US-003: Provide authorization
- US-004: Configure secrets

Note: there is no dedicated OAuth2 user story or ADR yet -- the
`services.operaton.oauth2` / Keycloak wiring landed via the `oauth2` merge
without one. US-003 (the closest existing story) only covers the
`--authorization`/`ENGINE_REST_AUTHORIZATION` string, not OAuth2 client
credentials.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
import aiohttp

SECRETS_EXAMPLE_DIR = Path(__file__).resolve().parent / "fixtures" / "secrets_example"
SECRETS_EXAMPLE_BPMN = SECRETS_EXAMPLE_DIR / "hello.bpmn"
RAW_SECRET_VALUE = "e2e-secret-should-never-appear-in-logs"

TEST_PASSED_ACTIVITY_ID = "Event_TestPassed"


async def test_secret_is_used_but_never_logged(
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
        SECRETS_EXAMPLE_BPMN, "e2e-secrets-example", "", basic_auth_env
    )

    with run_pur_serve(SECRETS_EXAMPLE_DIR, env=basic_auth_env) as process:
        await wait_for_instance_ended(engine_session, authorization, instance_id)
        activity_ids = await ended_activity_ids(
            engine_session, authorization, instance_id
        )
        output = serve_output(process)

    assert (
        TEST_PASSED_ACTIVITY_ID in activity_ids
    ), f"instance {instance_id} did not complete; pur serve output:\n{output}"
    assert RAW_SECRET_VALUE not in output, (
        "the raw secret value leaked into `pur serve` output:\n" + output
    )


async def test_unauthenticated_request_is_rejected(
    engine_base_url: str,
    engine_session: aiohttp.ClientSession,
) -> None:
    async with engine_session.get(f"{engine_base_url}/deployment") as response:
        assert response.status == 401, (
            "an unauthenticated request to the engine succeeded "
            f"(status {response.status}); services.operaton.oauth2 may not "
            "be enabled"
        )


async def test_oauth2_bearer_token_authenticates_the_workflow(
    oauth2_env: dict[str, str],
    oauth2_bearer_authorization: str,
    deploy_and_start: Callable[[Path, str, str, dict[str, str]], str],
    run_pur_serve: Callable[..., AbstractContextManager["Any"]],
    wait_for_instance_ended: Callable[..., Any],
    ended_activity_ids: Callable[..., Any],
    serve_output: Callable[[Any], str],
    engine_session: aiohttp.ClientSession,
) -> None:
    # deploy/start/serve authenticate via the Keycloak client-credentials
    # grant (operaton.tasks.oauth2.token_manager), configured purely through
    # env vars -- `pur` never sees a raw Authorization header here.
    # Verification below uses its own, independently-fetched bearer token.
    instance_id = deploy_and_start(
        SECRETS_EXAMPLE_BPMN, "e2e-secrets-example-oauth2", "", oauth2_env
    )

    with run_pur_serve(SECRETS_EXAMPLE_DIR, env=oauth2_env) as process:
        await wait_for_instance_ended(
            engine_session, oauth2_bearer_authorization, instance_id
        )
        activity_ids = await ended_activity_ids(
            engine_session, oauth2_bearer_authorization, instance_id
        )
        output = serve_output(process)

    assert TEST_PASSED_ACTIVITY_ID in activity_ids, (
        f"OAuth2-authenticated workflow did not complete ({activity_ids}); "
        f"pur serve output:\n{output}"
    )
