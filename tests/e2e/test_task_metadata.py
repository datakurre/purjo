"""Live acceptance test for selected Operaton external task metadata.

Related User Stories:
- US-001: Serve robot packages as BPMN service tasks
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
import aiohttp
import pytest

pytestmark = pytest.mark.auth_oauth2

METADATA_DIR = Path(__file__).resolve().parents[2] / "examples" / "task-metadata"
METADATA_BPMN = METADATA_DIR / "metadata.bpmn"


async def test_selected_task_metadata_is_available_to_robot(
    oauth2_env: dict[str, str],
    oauth2_bearer_authorization: str,
    deploy_and_start: Callable[[Path, str, str, dict[str, str]], str],
    run_pur_serve: Callable[..., AbstractContextManager["Any"]],
    wait_for_instance_ended: Callable[..., Any],
    process_variables: Callable[..., Any],
    serve_output: Callable[[Any], str],
    engine_session: aiohttp.ClientSession,
) -> None:
    authorization = oauth2_bearer_authorization
    instance_id = deploy_and_start(
        METADATA_BPMN,
        "e2e-task-metadata",
        '{"businessKey": "invoice-42"}',
        oauth2_env,
    )

    with run_pur_serve(METADATA_DIR, env=oauth2_env) as process:
        await wait_for_instance_ended(engine_session, authorization, instance_id)
        variables = await process_variables(engine_session, authorization, instance_id)
        output = serve_output(process)

    assert (
        variables.get("metadata_activity_id") == "MetadataTask"
    ), f"activity metadata was unavailable; pur serve output:\n{output}"
    assert (
        variables.get("metadata_topic_name") == "Task Metadata"
    ), f"topic metadata was unavailable; pur serve output:\n{output}"
    assert variables.get(
        "metadata_create_time"
    ), f"createTime metadata was unavailable; pur serve output:\n{output}"
    assert (
        variables.get("metadata_business_key") == "invoice-42"
    ), f"businessKey metadata did not round-trip; pur serve output:\n{output}"
