"""Main CLI module for purjo.

This module provides the command-line interface for managing Robot Framework
packages and interacting with the Operaton BPM engine. It includes commands for:
- Serving robot packages as external tasks
- Initializing new robot packages
- Wrapping packages into robot.zip files
- Deploying and managing BPMN resources
"""

from operaton.tasks import external_task_worker
from operaton.tasks import handlers
from operaton.tasks import operaton_session
from operaton.tasks import set_log_level
from operaton.tasks import settings
from operaton.tasks import task
from operaton.tasks.types import DeploymentDto
from operaton.tasks.types import DeploymentWithDefinitionsDto
from operaton.tasks.types import ProcessDefinitionDto
from operaton.tasks.types import ProcessInstanceDto
from operaton.tasks.types import StartProcessInstanceDto
from pathlib import Path
from purjo.config import DEFAULT_DEPLOYMENT_NAME
from purjo.config import DEFAULT_ENGINE_BASE_URL
from purjo.config import DEFAULT_LOCK_TTL_SECONDS
from purjo.config import DEFAULT_POLL_TTL_SECONDS
from purjo.config import DEFAULT_TIMEOUT_SECONDS
from purjo.config import DEFAULT_WORKER_ID
from purjo.config import OnFail
from purjo.deployment import build_cockpit_url
from purjo.deployment import build_deployment_form
from purjo.deployment import parse_variables_input
from purjo.file_utils import get_wrap_pathspec
from purjo.migration import migrate as migrate_all
from purjo.runner import create_task
from purjo.runner import logger
from purjo.runner import run
from purjo.runner import Task
from purjo.secrets import get_secrets_provider
from purjo.serialization import operaton_from_py
from pydantic import DirectoryPath
from pydantic import FilePath
from pydantic import ValidationError
from typing import Annotated
from typing import List
from typing import Optional
from typing import Union
from zipfile import ZipFile
import asyncio
import importlib.resources
import json
import os
import random
import shutil
import string
import tomllib
import typer
import uuid

cli = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="pur(jo) is a tool for managing and serving robot packages.",
)


# Extracted async functions for testability
async def deploy_resources(
    resources: List[Path],
    name: str,
    force: bool,
    migrate: bool,
    base_url: str,
) -> None:
    """Deploy resources to BPM engine (extracted for testability)."""
    async with operaton_session(headers={"Content-Type": None}) as session:
        form = build_deployment_form(resources, name, not force)
        response = await session.post(
            f"{base_url}/deployment/create",
            data=form,
        )
        if response.status >= 400:  # pragma: no cover
            print(json.dumps(await response.json(), indent=2))  # pragma: no cover
            return  # pragma: no cover
        try:
            deployment = DeploymentWithDefinitionsDto(**await response.json())
        except ValidationError:  # pragma: no cover
            print(json.dumps(await response.json(), indent=2))  # pragma: no cover
            return  # pragma: no cover
        url = build_cockpit_url(base_url, "/process-definition")
        for definition in (deployment.deployedProcessDefinitions or {}).values():
            if migrate:
                await migrate_all(definition, settings.LOG_LEVEL == "DEBUG")
            print(f"Deployed: {url}/{definition.id}/runtime")
            print(f"With key: {definition.key}")


async def start_process(
    key: str,
    variables: Optional[str],
    base_url: str,
) -> None:
    """Start a process instance (extracted for testability)."""
    variables_data = parse_variables_input(variables)
    business_key = variables_data.pop("businessKey", None) or f"{uuid.uuid4()}"
    async with operaton_session() as session:
        response = await session.post(
            f"{base_url}/process-definition/key/{key}/start",
            json=StartProcessInstanceDto(
                businessKey=business_key,
                variables=operaton_from_py(variables_data, [Path(os.getcwd())]),
            ).model_dump(),
            headers={"Content-Type": "application/json"},
        )
        if response.status >= 400:  # pragma: no cover
            print(json.dumps(await response.json(), indent=2))  # pragma: no cover
            return  # pragma: no cover
        try:
            instance = ProcessInstanceDto(**await response.json())
        except ValidationError:  # pragma: no cover
            print(json.dumps(await response.json(), indent=2))  # pragma: no cover
            return  # pragma: no cover
        url = build_cockpit_url(base_url, "/process-instance")
        print(f"Started: {url}/{instance.id}/runtime")


async def deploy_and_start(
    resources: List[Path],
    name: str,
    variables: Optional[str],
    migrate: bool,
    force: bool,
    base_url: str,
) -> None:
    """Deploy resources and start process instance (extracted for testability)."""
    async with operaton_session(headers={"Content-Type": None}) as session:
        form = build_deployment_form(resources, name, not force)
        response = await session.post(
            f"{base_url}/deployment/create",
            data=form,
        )
        if response.status >= 400:  # pragma: no cover
            print(json.dumps(await response.json(), indent=2))  # pragma: no cover
            return  # pragma: no cover
        try:
            deployment = DeploymentDto(**await response.json())
        except ValidationError:  # pragma: no cover
            print(json.dumps(await response.json(), indent=2))  # pragma: no cover
            return  # pragma: no cover
        response = await session.get(
            f"{base_url}/process-definition?deploymentId={deployment.id}"
        )
        if response.status >= 400:  # pragma: no cover
            print(json.dumps(await response.json(), indent=2))  # pragma: no cover
            return  # pragma: no cover
        try:
            definitions = [
                ProcessDefinitionDto(**element) for element in await response.json()
            ]
        except (TypeError, ValidationError):  # pragma: no cover
            print(json.dumps(await response.json(), indent=2))  # pragma: no cover
            return  # pragma: no cover
        for definition in definitions:
            if migrate:
                await migrate_all(definition, settings.LOG_LEVEL == "DEBUG")
            variables_data = parse_variables_input(variables)
            business_key = variables_data.pop("businessKey", None) or f"{uuid.uuid4()}"
            response = await session.post(
                f"{base_url}/process-definition/key/{definition.key}/start",
                json=StartProcessInstanceDto(
                    businessKey=business_key,
                    variables=operaton_from_py(variables_data, [Path(os.getcwd())]),
                ).model_dump(),
                headers={"Content-Type": "application/json"},
            )
            if response.status >= 400:  # pragma: no cover
                print(json.dumps(await response.json(), indent=2))  # pragma: no cover
                return  # pragma: no cover
            try:
                instance = ProcessInstanceDto(**await response.json())
            except ValidationError:  # pragma: no cover
                print(json.dumps(await response.json(), indent=2))  # pragma: no cover
                return  # pragma: no cover
            url = build_cockpit_url(base_url, "/process-instance")
            print(f"Started: {url}/{instance.id}/runtime")


def configure_settings(
    base_url: str,
    authorization: Optional[str],
    timeout: int,
    poll_ttl: int,
    lock_ttl: int,
    worker_id: str,
    log_level: str,
) -> None:
    """Configure the operaton settings for the worker.

    Args:
        base_url: The base URL for the Operaton engine REST API.
        authorization: Optional authorization header value.
        timeout: Request timeout in seconds.
        poll_ttl: Long-polling timeout in seconds.
        lock_ttl: Task lock duration in seconds.
        worker_id: Unique identifier for this worker.
        log_level: Logging level (DEBUG, INFO, etc.).
    """
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    settings.ENGINE_REST_TIMEOUT_SECONDS = timeout
    settings.ENGINE_REST_POLL_TTL_SECONDS = poll_ttl
    settings.ENGINE_REST_LOCK_TTL_SECONDS = lock_ttl
    settings.TASKS_WORKER_ID = worker_id
    settings.TASKS_MODULE = None
    logger.setLevel(log_level)
    set_log_level(log_level)


def validate_environment() -> None:
    """Validate that required executables are available.

    Raises:
        FileNotFoundError: If the 'uv' executable is not found.
    """
    if not shutil.which("uv"):
        raise FileNotFoundError("The 'uv' executable is not found in the system PATH.")


def register_topics(
    robots: List[Union[FilePath, DirectoryPath, Path]],
    secrets: Optional[str],
    on_fail: OnFail,
    semaphore: asyncio.Semaphore,
) -> None:
    """Register robot packages as external task handlers.

    Args:
        robots: List of robot package paths (directories or zip files).
        secrets: Optional secrets profile name.
        on_fail: Default failure handling strategy.
        semaphore: Semaphore for limiting concurrent job execution.
    """
    for robot in robots:
        if robot.is_dir():
            robot = robot.resolve()
            robot_toml = tomllib.loads((robot / "pyproject.toml").read_text())
        else:
            with ZipFile(robot, "r") as fp:
                robot_toml = tomllib.loads(fp.read("pyproject.toml").decode("utf-8"))
        purjo_toml = (robot_toml.get("tool") or {}).get("purjo") or {}
        secrets_provider = get_secrets_provider(
            purjo_toml.get("secrets"), profile=secrets
        )
        for topic, config in (purjo_toml.get("topics") or {}).items():
            task_config = Task(**config)
            task(topic, localVariables=not task_config.process_variables)(
                create_task(
                    config=task_config,
                    robot=robot,
                    on_fail=(
                        task_config.on_fail
                        if task_config.on_fail is not None
                        else on_fail
                    ),
                    semaphore=semaphore,
                    secrets_provider=secrets_provider,
                )
            )
            logger.info("Topic | %s | %s", topic, config)


def start_worker() -> None:
    """Start the external task worker event loop."""
    asyncio.get_event_loop().run_until_complete(external_task_worker(handlers=handlers))


@cli.command(
    name="serve",
    no_args_is_help=True,
)
def cli_serve(
    robots: List[Union[FilePath, DirectoryPath]],
    base_url: Annotated[
        str, typer.Option(envvar="ENGINE_REST_BASE_URL")
    ] = DEFAULT_ENGINE_BASE_URL,
    authorization: Annotated[
        Optional[str], typer.Option(envvar="ENGINE_REST_AUTHORIZATION")
    ] = None,
    secrets: Annotated[
        Optional[str], typer.Option(envvar="TASKS_SECRETS_PROFILE")
    ] = None,
    timeout: Annotated[
        int, typer.Option(envvar="ENGINE_REST_TIMEOUT_SECONDS")
    ] = DEFAULT_TIMEOUT_SECONDS,
    poll_ttl: Annotated[
        int, typer.Option(envvar="ENGINE_REST_POLL_TTL_SECONDS")
    ] = DEFAULT_POLL_TTL_SECONDS,
    lock_ttl: Annotated[
        int, typer.Option(envvar="ENGINE_REST_LOCK_TTL_SECONDS")
    ] = DEFAULT_LOCK_TTL_SECONDS,
    max_jobs: int = 1,
    worker_id: Annotated[
        str, typer.Option(envvar="TASKS_WORKER_ID")
    ] = DEFAULT_WORKER_ID,
    log_level: Annotated[str, typer.Option(envvar="LOG_LEVEL")] = "DEBUG",
    on_fail: OnFail = OnFail.FAIL,
) -> None:
    """
    Serve robot.zip packages (or directories) as BPMN service tasks.
    """
    configure_settings(
        base_url=base_url,
        authorization=authorization,
        timeout=timeout,
        poll_ttl=poll_ttl,
        lock_ttl=lock_ttl,
        worker_id=worker_id,
        log_level=log_level,
    )
    validate_environment()
    semaphore = asyncio.Semaphore(max_jobs)
    register_topics(robots, secrets, on_fail, semaphore)
    start_worker()


async def initialize_robot_package(cwd_path: Path, python: bool = False) -> None:
    """Initialize a new robot package in the specified directory.

    This function creates a new robot package with all necessary files:
    - Initializes a uv project
    - Adds robotframework and optional dependencies
    - Creates template files (BPMN, Robot/Python)
    - Configures pyproject.toml with purjo topics

    Args:
        cwd_path: The directory to initialize the package in.
        python: If True, create a Python template instead of a Robot template.
    """
    await run(
        "uv",
        [
            "init",
            "--no-workspace",
        ],
        cwd_path,
        {
            "UV_NO_SYNC": "0",
            "UV_NO_CONFIG": "1",
            "UV_NO_WORKSPACE": "1",
            "VIRTUAL_ENV": "",
        },
    )
    await run(
        "uv",
        [
            "add",
            "robotframework",
        ]
        + (["pydantic"] if python else [])
        + [
            "--no-sources",
        ],
        cwd_path,
        {
            "UV_NO_SYNC": "0",
            "UV_NO_CONFIG": "1",
            "UV_NO_WORKSPACE": "1",
            "VIRTUAL_ENV": "",
        },
    )
    await run(
        "uv",
        [
            "add",
            "--dev",
        ]
        + (["purjo"] if python else ["robotframework-robotlibrary>=1.0a3"])
        + [
            "--no-sources",
        ],
        cwd_path,
        {
            "UV_NO_SYNC": "0",
            "UV_NO_CONFIG": "1",
            "UV_NO_WORKSPACE": "1",
            "VIRTUAL_ENV": "",
        },
    )
    for fixture_py in [
        cwd_path / "hello.py",
        cwd_path / "main.py",
        cwd_path / ".python-version",
    ]:
        if fixture_py.exists():  # pragma: no cover
            fixture_py.unlink()  # pragma: no cover
    (cwd_path / "pyproject.toml").write_text(
        (cwd_path / "pyproject.toml").read_text() + f"""
[tool.purjo.topics."My Topic in BPMN"]
name = "{'tasks.main' if python else 'My Test in Robot'}"
on-fail = "{'FAIL' if python else 'ERROR'}"
process-variables = true
"""
    )
    (cwd_path / "hello.bpmn").write_text(
        (importlib.resources.files("purjo.data") / "hello.bpmn").read_text()
    )
    (cwd_path / "Makefile").write_text(
        (importlib.resources.files("purjo.data") / "Makefile").read_text()
    )
    if python:
        (cwd_path / "tasks.py").write_text(
            (importlib.resources.files("purjo.data") / "tasks.py").read_text()
        )
    else:
        (cwd_path / "hello.robot").write_text(
            (importlib.resources.files("purjo.data") / "hello.robot").read_text()
        )
        (cwd_path / "Hello.py").write_text(
            (importlib.resources.files("purjo.data") / "Hello.py").read_text()
        )
        (cwd_path / "test_hello.robot").write_text(
            (importlib.resources.files("purjo.data") / "test_hello.robot").read_text()
        )
    (cwd_path / ".wrapignore").write_text("")
    cli_wrap()
    (cwd_path / "robot.zip").unlink()
    if (cwd_path / ".venv").exists():  # pragma: no cover
        shutil.rmtree(cwd_path / ".venv")  # pragma: no cover


@cli.command(name="init")
def cli_init(
    python: Annotated[
        bool,
        typer.Option(
            "--python", help="Create a Python template instead of a Robot template"
        ),
    ] = False,
    log_level: Annotated[str, typer.Option(envvar="LOG_LEVEL")] = "INFO",
) -> None:
    """Initialize a new robot package into the current directory."""
    logger.setLevel(log_level)
    set_log_level(log_level)
    cwd_path = Path(os.getcwd())
    pyproject_path = cwd_path / "pyproject.toml"
    assert not pyproject_path.exists()

    if not shutil.which("uv"):
        raise FileNotFoundError("The 'uv' executable is not found in the system PATH.")

    asyncio.run(initialize_robot_package(cwd_path, python))


@cli.command(name="wrap")
def cli_wrap(
    offline: bool = False,
    log_level: Annotated[str, typer.Option(envvar="LOG_LEVEL")] = "INFO",
) -> None:
    """Wrap the current directory into a robot.zip package."""
    logger.setLevel(log_level)
    set_log_level(log_level)
    cwd_path = Path(os.getcwd())
    if offline:
        # Cache dependencies
        if cwd_path.joinpath(".venv").exists():  # pragma: no cover
            shutil.rmtree(cwd_path / ".venv")  # pragma: no cover
        asyncio.run(
            run(
                "uv",
                [
                    "run",
                    "--refresh",
                    "--cache-dir",
                    str(cwd_path / ".cache"),
                    "--",
                    "echo",
                    "Cached.",
                ],
                cwd_path,
                {"UV_NO_SYNC": "0", "VIRTUAL_ENV": ""},
            )
        )
    spec = get_wrap_pathspec(cwd_path)
    zip_path = cwd_path / "robot.zip"
    with ZipFile(zip_path, "w") as zipf:
        for file_path in spec.match_tree(cwd_path, negate=True, follow_links=False):
            print(f"Adding {file_path}")
            zipf.write(file_path)
        if offline:
            print("Adding .cache")
            for file_path_ in (cwd_path / ".cache").rglob("*"):
                if file_path_.is_file():
                    zipf.write(file_path_, file_path_.relative_to(cwd_path))


operaton = typer.Typer(
    pretty_exceptions_enable=False,
    no_args_is_help=True,
    help='BPM engine operations as distinct sub commands (also as "bpm").',
)


def generate_random_string(length: int = 7) -> str:
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))


@operaton.command(name="create")
def operaton_create(
    filename: Path,
    log_level: Annotated[str, typer.Option(envvar="LOG_LEVEL")] = "INFO",
) -> None:
    """Create a new BPMN (or DMN) file."""
    logger.setLevel(log_level)
    set_log_level(log_level)

    if not (
        filename.name.endswith(".bpmn")
        or filename.name.endswith(".dmn")
        or filename.name.endswith(".form")
    ):
        filename = filename.with_suffix(".bpmn")
    assert not Path(filename).exists()
    (
        filename.write_text(
            (importlib.resources.files("purjo.data") / "template.form")
            .read_text()
            .replace("FORM_ID", generate_random_string())
        )
        if filename.name.endswith(".form")
        else (
            filename.write_text(
                (importlib.resources.files("purjo.data") / "template.bpmn")
                .read_text()
                .replace("DEFINITION_ID", generate_random_string())
                .replace("PROCESS_ID", generate_random_string())
            )
            if filename.name.endswith(".bpmn")
            else filename.write_text(
                (importlib.resources.files("purjo.data") / "template.dmn")
                .read_text()
                .replace("DEFINITIONS_ID", generate_random_string())
                .replace("DEFINITIONS_TABLE_ID", generate_random_string())
                .replace("DECISION_ID", generate_random_string())
            )
        )
    )


@operaton.command(name="deploy")
def operaton_deploy(
    resources: List[FilePath],
    name: Annotated[
        str, typer.Option(envvar="DEPLOYMENT_NAME")
    ] = DEFAULT_DEPLOYMENT_NAME,
    migrate: bool = True,
    force: bool = False,
    base_url: Annotated[
        str, typer.Option(envvar="ENGINE_REST_BASE_URL")
    ] = DEFAULT_ENGINE_BASE_URL,
    authorization: Annotated[
        Optional[str], typer.Option(envvar="ENGINE_REST_AUTHORIZATION")
    ] = None,
    log_level: Annotated[str, typer.Option(envvar="LOG_LEVEL")] = "INFO",
) -> None:
    """Deploy resources to BPM engine."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    logger.setLevel(log_level)
    set_log_level(log_level)

    asyncio.run(deploy_resources(resources, name, force, migrate, base_url))


@operaton.command(name="start")
def operaton_start(
    key: str,
    variables: Optional[str] = None,
    base_url: Annotated[
        str, typer.Option(envvar="ENGINE_REST_BASE_URL")
    ] = DEFAULT_ENGINE_BASE_URL,
    authorization: Annotated[
        Optional[str], typer.Option(envvar="ENGINE_REST_AUTHORIZATION")
    ] = None,
    log_level: Annotated[str, typer.Option(envvar="LOG_LEVEL")] = "INFO",
) -> None:
    """Start a process instance by process definition key."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    logger.setLevel(log_level)
    set_log_level(log_level)

    asyncio.run(start_process(key, variables, base_url))


cli.add_typer(operaton, name="operaton")
cli.add_typer(operaton, name="bpm", hidden=True)


@cli.command(
    name="run",
    no_args_is_help=True,
)
def cli_run(
    resources: List[FilePath],
    name: Annotated[
        str, typer.Option(envvar="DEPLOYMENT_NAME")
    ] = DEFAULT_DEPLOYMENT_NAME,
    variables: Optional[str] = None,
    migrate: bool = True,
    force: bool = False,
    base_url: Annotated[
        str, typer.Option(envvar="ENGINE_REST_BASE_URL")
    ] = DEFAULT_ENGINE_BASE_URL,
    authorization: Annotated[
        Optional[str], typer.Option(envvar="ENGINE_REST_AUTHORIZATION")
    ] = None,
    log_level: Annotated[str, typer.Option(envvar="LOG_LEVEL")] = "INFO",
) -> None:
    """Deploy process resources to BPM engine and start a new instance."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    settings.LOG_LEVEL = log_level
    logger.setLevel(log_level)
    set_log_level(log_level)

    asyncio.run(deploy_and_start(resources, name, variables, migrate, force, base_url))


def main() -> None:  # pragma: no cover
    cli()
