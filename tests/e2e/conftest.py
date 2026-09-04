"""Shared fixtures for end-to-end tests against live devenv services.

Unlike the rest of ``tests/``, these tests drive the real ``pur`` CLI as a
subprocess against a live Operaton engine (plus Vault, Keycloak, Mockoon)
started by ``devenv up`` / ``devenv test``. They automate the manual
"End-to-end testing" checklist from ``docs/development_environment.md``:
deploy a process, start an instance, run ``pur serve``, then verify the
result through the engine REST API.

Every test here is marked ``e2e`` (see the ``pytestmark`` below) and is
excluded from the default ``pytest`` run via ``-m "not e2e"`` in
``pyproject.toml``, so the 100%-coverage-gated unit suite is unaffected.
``require_live_services`` skips the whole session with a clear message
instead of hanging or failing when the services aren't up.

All engine interaction is exposed as fixtures (rather than plain importable
helpers) so test modules need no cross-file imports beyond normal pytest
fixture injection.
"""

from collections.abc import AsyncIterator
from collections.abc import Callable
from collections.abc import Iterator
from contextlib import AbstractContextManager
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryFile
from typing import Any
from typing import Optional
from urllib.parse import urlparse
import aiohttp
import asyncio
import os
import pytest
import re
import shutil
import socket
import subprocess
import sys
import time

ENGINE_BASE_URL = os.environ.get(
    "ENGINE_REST_BASE_URL", "http://localhost:8080/engine-rest"
)
BASIC_AUTHORIZATION = os.environ.get("ENGINE_REST_AUTHORIZATION", "Basic ZGVtbzpkZW1v")
OAUTH2_TOKEN_URL = os.environ.get(
    "OAUTH2_TOKEN_URL",
    "http://localhost:8081/realms/operaton/protocol/openid-connect/token",
)
OAUTH2_CLIENT_ID = os.environ.get("OAUTH2_CLIENT_ID", "operaton")
OAUTH2_CLIENT_SECRET = os.environ.get("OAUTH2_CLIENT_SECRET", "")

STARTED_INSTANCE_RE = re.compile(
    r"Started: .*/process-instance/([0-9a-f-]{36})/runtime"
)

PUR_EXECUTABLE = shutil.which("pur") or str(Path(sys.executable).with_name("pur"))


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test collected from this directory as `e2e`.

    A bare module-level `pytestmark` in conftest.py does NOT propagate to
    sibling test modules -- only to code within conftest.py itself -- so
    this hook is what actually makes `-m "not e2e"` (see pyproject.toml)
    exclude these tests from the default suite.
    """
    here = Path(__file__).parent
    for item in items:
        if here in item.path.parents:
            item.add_marker(pytest.mark.e2e)


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session", autouse=True)
def require_live_services() -> None:
    """Skip the e2e session outright when devenv's services aren't running."""
    engine_host = urlparse(ENGINE_BASE_URL).hostname or "localhost"
    keycloak_host = urlparse(OAUTH2_TOKEN_URL).hostname or "localhost"
    missing = [
        name
        for name, host, port in (
            ("Operaton", engine_host, 8080),
            ("Vault", "localhost", 8200),
            ("Keycloak", keycloak_host, 8081),
        )
        if not _port_open(host, port)
    ]
    if missing:
        pytest.skip(
            f"live services not reachable ({', '.join(missing)}); "
            "run `devenv up` (or `devenv test`) before `make test-e2e`"
        )


@pytest.fixture
def oauth2_env() -> dict[str, str]:
    """Env overrides that make `pur` authenticate via Keycloak OAuth2."""
    assert OAUTH2_CLIENT_SECRET, "OAUTH2_CLIENT_SECRET must be set (see .env.example)"
    return {
        "ENGINE_REST_AUTHORIZATION": "",
        "OAUTH2_TOKEN_URL": OAUTH2_TOKEN_URL,
        "OAUTH2_CLIENT_ID": OAUTH2_CLIENT_ID,
        "OAUTH2_CLIENT_SECRET": OAUTH2_CLIENT_SECRET,
    }


@pytest.fixture
def basic_auth_env() -> dict[str, str]:
    """Env overrides that make `pur` authenticate via the legacy Basic credential."""
    return {
        "ENGINE_REST_AUTHORIZATION": BASIC_AUTHORIZATION,
        "OAUTH2_TOKEN_URL": "",
        "OAUTH2_CLIENT_ID": "",
        "OAUTH2_CLIENT_SECRET": "",
    }


@pytest.fixture
async def oauth2_bearer_authorization(
    engine_session: aiohttp.ClientSession,
) -> str:
    """A real Keycloak-issued bearer Authorization header, for test-side history
    queries -- separate from `oauth2_env`, which drives `pur`'s own (fully
    independent) OAuth2 client-credentials flow via `operaton.tasks.oauth2`.
    """
    assert OAUTH2_CLIENT_SECRET, "OAUTH2_CLIENT_SECRET must be set (see .env.example)"
    async with engine_session.post(
        OAUTH2_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": OAUTH2_CLIENT_ID,
            "client_secret": OAUTH2_CLIENT_SECRET,
        },
    ) as response:
        assert response.status == 200, await response.text()
        payload = await response.json()
    return f"Bearer {payload['access_token']}"


def _run_pur(
    *args: str, env: dict[str, str], timeout: float = 60
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PUR_EXECUTABLE, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, **env},
    )


@pytest.fixture
def run_pur() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run a one-shot `pur` subcommand (e.g. `run`, `operaton deploy`)."""
    return _run_pur


def _deploy_and_start(
    resource: Path, name: str, variables: Optional[str], env: dict[str, str]
) -> str:
    result = _run_pur(
        "run",
        str(resource),
        "--name",
        name,
        *(["--variables", variables] if variables else []),
        env=env,
    )
    assert (
        result.returncode == 0
    ), f"`pur run` failed:\n{result.stdout}\n{result.stderr}"
    match = STARTED_INSTANCE_RE.search(result.stdout)
    assert (
        match
    ), f"could not find a started process instance in output:\n{result.stdout}"
    return match.group(1)


@pytest.fixture
def deploy_and_start() -> Callable[[Path, str, Optional[str], dict[str, str]], str]:
    """Deploy a resource and start an instance via `pur run`; return its id."""
    return _deploy_and_start


@contextmanager
def _run_pur_serve(
    *robot_paths: Path, env: dict[str, str]
) -> Iterator["subprocess.Popen[str]"]:
    log_file = TemporaryFile(mode="w+")
    process = subprocess.Popen(
        [
            PUR_EXECUTABLE,
            "serve",
            *[str(path) for path in robot_paths],
            "--max-jobs",
            "1",
            "--poll-ttl",
            "1",
            "--lock-ttl",
            "5",
            "--log-level",
            "DEBUG",
        ],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, **env},
    )
    process.log_file = log_file  # type: ignore[attr-defined]
    try:
        yield process
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        log_file.close()


@pytest.fixture
def run_pur_serve() -> Callable[..., AbstractContextManager["subprocess.Popen[str]"]]:
    """Run `pur serve` in the background for the duration of a `with` block.

    stdout/stderr are captured to a temp file (not a pipe) so a full
    `--log-level DEBUG` worker can't deadlock the test by filling an unread
    pipe buffer; read it back with the `serve_output` fixture for failure
    messages.
    """
    return _run_pur_serve


def _serve_output(process: "subprocess.Popen[str]") -> str:
    log_file: Any = process.log_file  # type: ignore[attr-defined]
    log_file.seek(0)
    return str(log_file.read())


@pytest.fixture
def serve_output() -> Callable[["subprocess.Popen[str]"], str]:
    """Read whatever `pur serve` has printed so far, for failure messages."""
    return _serve_output


async def _wait_for_instance_ended(
    session: aiohttp.ClientSession,
    authorization: str,
    instance_id: str,
    timeout: float = 30,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    headers = {"Authorization": authorization} if authorization else {}
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        async with session.get(
            f"{ENGINE_BASE_URL}/history/process-instance/{instance_id}", headers=headers
        ) as response:
            assert response.status == 200, await response.text()
            last = await response.json()
        if last.get("endTime"):
            return last
        await asyncio.sleep(1)
    raise AssertionError(
        f"process instance {instance_id} did not end within {timeout}s: {last}"
    )


@pytest.fixture
def wait_for_instance_ended() -> Callable[..., Any]:
    """Poll history for a process instance until it has an `endTime`."""
    return _wait_for_instance_ended


async def _ended_activity_ids(
    session: aiohttp.ClientSession, authorization: str, instance_id: str
) -> set[str]:
    headers = {"Authorization": authorization} if authorization else {}
    async with session.get(
        f"{ENGINE_BASE_URL}/history/activity-instance",
        params={"processInstanceId": instance_id, "finished": "true"},
        headers=headers,
    ) as response:
        assert response.status == 200, await response.text()
        activities = await response.json()
    return {activity["activityId"] for activity in activities}


@pytest.fixture
def ended_activity_ids() -> Callable[..., Any]:
    """Return the activityIds of every finished activity instance for a process instance."""
    return _ended_activity_ids


async def _process_variables(
    session: aiohttp.ClientSession, authorization: str, instance_id: str
) -> dict[str, Any]:
    headers = {"Authorization": authorization} if authorization else {}
    async with session.get(
        f"{ENGINE_BASE_URL}/history/variable-instance",
        params={"processInstanceIdIn": instance_id},
        headers=headers,
    ) as response:
        assert response.status == 200, await response.text()
        variables = await response.json()
    return {variable["name"]: variable["value"] for variable in variables}


@pytest.fixture
def process_variables() -> Callable[..., Any]:
    """Return {name: value} for the historic variables of a process instance."""
    return _process_variables


@pytest.fixture
def engine_base_url() -> str:
    """The engine REST API base URL, for tests that build their own requests."""
    return ENGINE_BASE_URL


@pytest.fixture
async def engine_session() -> AsyncIterator[aiohttp.ClientSession]:
    """A plain aiohttp session for direct engine REST calls (history, auth checks)."""
    async with aiohttp.ClientSession() as session:
        yield session
