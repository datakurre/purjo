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
from purjo.config import OnFail
from purjo.runner import create_task
from purjo.runner import logger
from purjo.runner import run
from purjo.runner import Task
from purjo.utils import migrate as migrate_all
from purjo.utils import operaton_from_py
from pydantic import DirectoryPath
from pydantic import FilePath
from pydantic import ValidationError
from typing import Annotated
from typing import List
from typing import Optional
from typing import Union
from zipfile import ZipFile
import aiohttp
import asyncio
import importlib.resources
import json
import os
import pathspec
import random
import shutil
import string
import sys
import tomllib
import typer
import uuid


cli = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="pur(jo) is a tool for managing and serving robot packages.",
)


@cli.command(
    name="serve",
    no_args_is_help=True,
)
def cli_serve(
    robots: List[Union[FilePath, DirectoryPath]],
    base_url: Annotated[
        str, typer.Option(envvar="ENGINE_REST_BASE_URL")
    ] = "http://localhost:8080/engine-rest",
    authorization: Annotated[
        Optional[str], typer.Option(envvar="ENGINE_REST_AUTHORIZATION")
    ] = None,
    timeout: Annotated[int, typer.Option(envvar="ENGINE_REST_TIMEOUT_SECONDS")] = 20,
    poll_ttl: Annotated[int, typer.Option(envvar="ENGINE_REST_POLL_TTL_SECONDS")] = 10,
    lock_ttl: Annotated[int, typer.Option(envvar="ENGINE_REST_LOCK_TTL_SECONDS")] = 30,
    max_jobs: int = 1,
    worker_id: Annotated[
        str, typer.Option(envvar="TASKS_WORKER_ID")
    ] = "operaton-robot-runner",
    log_level: Annotated[str, typer.Option(envvar="LOG_LEVEL")] = "DEBUG",
    on_fail: OnFail = OnFail.FAIL,
) -> None:
    """
    Serve robot.zip packages (or directories) as BPMN service tasks.
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

    semaphore = asyncio.Semaphore(max_jobs)

    if not shutil.which("uv"):
        raise FileNotFoundError("The 'uv' executable is not found in the system PATH.")

    for robot in robots:
        if robot.is_dir():
            robot = robot.resolve()
            robot_toml = tomllib.loads((robot / "pyproject.toml").read_text())
        else:
            with ZipFile(robot, "r") as fp:
                robot_toml = tomllib.loads(fp.read("pyproject.toml").decode("utf-8"))
        purjo_toml = (robot_toml.get("tool") or {}).get("purjo") or {}
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
                )
            )
            logger.info("Topic | %s | %s", topic, config)

    asyncio.get_event_loop().run_until_complete(external_task_worker(handlers=handlers))


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

    async def init() -> None:
        await run(
            "uv",
            [
                "init",
                "--no-workspace",
            ],
            cwd_path,
            {
                "UV_NO_SYNC": "0",
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
                "VIRTUAL_ENV": "",
            },
        )
        for fixture_py in [cwd_path / "hello.py", cwd_path / "main.py"]:
            if fixture_py.exists():
                fixture_py.unlink()
        (cwd_path / "pyproject.toml").write_text(
            (cwd_path / "pyproject.toml").read_text()
            + f"""
[tool.purjo.topics."My Topic in BPMN"]
name = "{'tasks.main' if python else 'My Test in Robot'}"
on-fail = "ERROR"
process-variables = true
"""
        )
        (cwd_path / "hello.bpmn").write_text(
            (importlib.resources.files("purjo.data") / "hello.bpmn").read_text()
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
        (cwd_path / ".wrapignore").write_text("")
        cli_wrap()
        (cwd_path / "robot.zip").unlink()

    asyncio.run(init())


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
        if cwd_path.joinpath(".venv").exists():
            shutil.rmtree(cwd_path / ".venv")
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
    spec_path = cwd_path / ".wrapignore"
    spec_text = spec_path.read_text() if spec_path.exists() else ""
    spec = pathspec.GitIgnoreSpec.from_lines(
        spec_text.splitlines()
        + [
            "/.git",
            "/.gitignore",
            "/log.html",
            "/output.xml",
            "__pycache__/",
            "/report.html",
            "/robot.zip",
            "/.venv/",
            "/.wrapignore",
            "/.cache",
        ]
    )
    zip_path = cwd_path / "robot.zip"
    with ZipFile(zip_path, "w") as zipf:
        for file_path in spec.match_tree(cwd_path, negate=True):
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

    if not (filename.name.endswith(".bpmn") or filename.name.endswith(".dmn")):
        filename = filename.with_suffix(".bpmn")
    assert not Path(filename).exists()
    (
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


@operaton.command(name="deploy")
def operaton_deploy(
    resources: List[FilePath],
    name: Annotated[str, typer.Option(envvar="DEPLOYMENT_NAME")] = "pur(jo) deployment",
    migrate: bool = True,
    force: bool = False,
    base_url: Annotated[
        str, typer.Option(envvar="ENGINE_REST_BASE_URL")
    ] = "http://localhost:8080/engine-rest",
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

    async def deploy() -> None:
        async with operaton_session(headers={"Content-Type": None}) as session:
            form = aiohttp.FormData()
            for resource in resources:
                form.add_field(
                    "deployment-name",
                    name,
                    content_type="text/plain",
                )
                form.add_field(
                    "deployment-source",
                    "pur(jo)",
                    content_type="text/plain",
                )
                form.add_field(
                    "deploy-changed-only",
                    "true" if not force else "false",
                    content_type="text/plain",
                )
                form.add_field(
                    resource.name,
                    resource.read_text(),
                    filename=resource.name,
                    content_type="application/octet-stream",
                )
            response = await session.post(
                f"{base_url}/deployment/create",
                data=form,
            )
            if response.status >= 400:
                print(json.dumps(await response.json(), indent=2))
                return
            try:
                deployment = DeploymentWithDefinitionsDto(**await response.json())
            except ValidationError:
                print(json.dumps(await response.json(), indent=2))
                return
            url = (
                base_url.replace("/engine-rest", "").rstrip("/")
                if "CODESPACE_NAME" not in os.environ
                else f"https://{os.environ['CODESPACE_NAME']}-8080.app.github.dev"
            ) + "/operaton/app/cockpit/default/#/process-definition"
            for definition in (deployment.deployedProcessDefinitions or {}).values():
                if migrate:
                    await migrate_all(definition, settings.LOG_LEVEL == "DEBUG")
                print(f"Deployed: {url}/{definition.id}/runtime")
                print(f"With key: {definition.key}")

    asyncio.run(deploy())


@operaton.command(name="start")
def operaton_start(
    key: str,
    variables: Optional[str] = None,
    base_url: Annotated[
        str, typer.Option(envvar="ENGINE_REST_BASE_URL")
    ] = "http://localhost:8080/engine-rest",
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

    async def start() -> None:
        variables_data = (
            json.load(sys.stdin)
            if variables == "-"
            else (
                json.loads(Path(variables).read_text())
                if variables and os.path.isfile(variables)
                else (json.loads(variables) if variables else {})
            )
        )
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
            if response.status >= 400:
                print(json.dumps(await response.json(), indent=2))
                return
            try:
                instance = ProcessInstanceDto(**await response.json())
            except ValidationError:
                print(json.dumps(await response.json(), indent=2))
                return
            url = (
                base_url.replace("/engine-rest", "").rstrip("/")
                if "CODESPACE_NAME" not in os.environ
                else f"https://{os.environ['CODESPACE_NAME']}-8080.app.github.dev"
            ) + "/operaton/app/cockpit/default/#/process-instance"
            print(f"Started: {url}/{instance.id}/runtime")

    asyncio.run(start())


cli.add_typer(operaton, name="operaton")
cli.add_typer(operaton, name="bpm", hidden=True)


@cli.command(
    name="run",
    no_args_is_help=True,
)
def cli_run(
    resources: List[FilePath],
    name: Annotated[str, typer.Option(envvar="DEPLOYMENT_NAME")] = "pur(jo) deployment",
    variables: Optional[str] = None,
    migrate: bool = True,
    force: bool = False,
    base_url: Annotated[
        str, typer.Option(envvar="ENGINE_REST_BASE_URL")
    ] = "http://localhost:8080/engine-rest",
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

    async def start() -> None:
        async with operaton_session(headers={"Content-Type": None}) as session:
            form = aiohttp.FormData()
            for resource in resources:
                form.add_field(
                    "deployment-name",
                    name,
                    content_type="text/plain",
                )
                form.add_field(
                    "deployment-source",
                    "pur(jo)",
                    content_type="text/plain",
                )
                form.add_field(
                    "deploy-changed-only",
                    "true" if not force else "false",
                    content_type="text/plain",
                )
                form.add_field(
                    resource.name,
                    resource.read_text(),
                    filename=resource.name,
                    content_type="application/octet-stream",
                )
            response = await session.post(
                f"{base_url}/deployment/create",
                data=form,
            )
            if response.status >= 400:
                print(json.dumps(await response.json(), indent=2))
                return
            try:
                deployment = DeploymentDto(**await response.json())
            except ValidationError:
                print(json.dumps(await response.json(), indent=2))
                return
            response = await session.get(
                f"{base_url}/process-definition?deploymentId={deployment.id}"
            )
            if response.status >= 400:
                print(json.dumps(await response.json(), indent=2))
                return
            try:
                definitions = [
                    ProcessDefinitionDto(**element) for element in await response.json()
                ]
            except (TypeError, ValidationError):
                print(json.dumps(await response.json(), indent=2))
                return
            for definition in definitions:
                if migrate:
                    await migrate_all(definition, settings.LOG_LEVEL == "DEBUG")
                variables_data = (
                    json.load(sys.stdin)
                    if variables == "-"
                    else (
                        json.loads(Path(variables).read_text())
                        if variables and os.path.isfile(variables)
                        else (json.loads(variables) if variables else {})
                    )
                )
                business_key = (
                    variables_data.pop("businessKey", None) or f"{uuid.uuid4()}"
                )
                response = await session.post(
                    f"{base_url}/process-definition/key/{definition.key}/start",
                    json=StartProcessInstanceDto(
                        businessKey=business_key,
                        variables=operaton_from_py(variables_data, [Path(os.getcwd())]),
                    ).model_dump(),
                    headers={"Content-Type": "application/json"},
                )
                if response.status >= 400:
                    print(json.dumps(await response.json(), indent=2))
                    return
                try:
                    instance = ProcessInstanceDto(**await response.json())
                except ValidationError:
                    print(json.dumps(await response.json(), indent=2))
                    return
                url = (
                    base_url.replace("/engine-rest", "").rstrip("/")
                    if "CODESPACE_NAME" not in os.environ
                    else f"https://{os.environ['CODESPACE_NAME']}-8080.app.github.dev"
                ) + "/operaton/app/cockpit/default/#/process-instance"
                print(f"Started: {url}/{instance.id}/runtime")

    asyncio.run(start())


def main() -> None:
    cli()
