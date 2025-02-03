from operaton.tasks import external_task_worker
from operaton.tasks import handlers
from operaton.tasks import operaton_session
from operaton.tasks import set_log_level
from operaton.tasks import settings
from operaton.tasks import task
from pathlib import Path
from purjo.config import OnFail
from purjo.runner import create_task
from purjo.runner import logger
from purjo.runner import run
from pydantic import DirectoryPath
from pydantic import FilePath
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
import tomllib
import typer


cli = typer.Typer()


@cli.command(name="serve")
def cli_serve(
    robots: List[Union[FilePath, DirectoryPath]],
    base_url: str = "http://localhost:8080/engine-rest",
    authorization: Optional[str] = None,
    timeout: int = 20,
    poll_ttl: int = 10,
    lock_ttl: int = 30,
    max_jobs: int = 1,
    worker_id: str = "operaton-robot-runner",
    log_level: str = "DEBUG",
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
            task(topic)(create_task(config["name"], robot, on_fail, semaphore))

    asyncio.get_event_loop().run_until_complete(external_task_worker(handlers=handlers))


@cli.command(name="init")
def cli_init(
    log_level: str = "INFO",
) -> None:
    """Initialize a new robot package."""
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
                "--no-sources",
            ],
            cwd_path,
            {
                "UV_NO_SYNC": "0",
                "VIRTUAL_ENV": "",
            },
        )
        (cwd_path / "hello.py").unlink()
        (cwd_path / "pyproject.toml").write_text(
            (cwd_path / "pyproject.toml").read_text()
            + """
[tool.purjo.topics]
"My Topic" = { name = "My Task" }
"""
        )
        (cwd_path / "hello.bpmn").write_text(
            (importlib.resources.files("purjo.data") / "hello.bpmn").read_text()
        )
        (cwd_path / "hello.robot").write_text(
            (importlib.resources.files("purjo.data") / "hello.robot").read_text()
        )
        (cwd_path / "Hello.py").write_text(
            (importlib.resources.files("purjo.data") / "Hello.py").read_text()
        )
        (cwd_path / ".wrapignore").write_text("*.bpmn\n")
        cli_wrap()
        (cwd_path / "robot.zip").unlink()

    asyncio.run(init())


@cli.command(name="wrap")
def cli_wrap(
    log_level: str = "INFO",
) -> None:
    """Wrap the current directory into a robot.zip package."""
    logger.setLevel(log_level)
    set_log_level(log_level)
    cwd_path = Path(os.getcwd())
    spec_path = cwd_path / ".wrapignore"
    spec_text = spec_path.read_text() if spec_path.exists() else ""
    spec = pathspec.GitIgnoreSpec.from_lines(
        spec_text.splitlines()
        + [
            ".gitignore",
            "log.html",
            "output.xml",
            "__pycache__/",
            "report.html",
            "robot.zip",
            ".venv/",
            ".wrapignore",
        ]
    )
    zip_path = cwd_path / "robot.zip"
    with ZipFile(zip_path, "w") as zipf:
        for file_path in spec.match_tree(cwd_path, negate=True):
            print(f"Adding {file_path}")
            zipf.write(file_path)


bpm = typer.Typer(help="BPM engine operation as distinct sub commands.")


def generate_random_string(length: int = 7) -> str:
    characters = string.ascii_lowercase + string.digits
    return "".join(random.choice(characters) for _ in range(length))


@bpm.command(name="create")
def bpm_create(
    filename: Path,
    log_level: str = "INFO",
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


@bpm.command(name="deploy")
def bpm_deploy(
    resources: List[FilePath],
    base_url: str = "http://localhost:8080/engine-rest",
    authorization: Optional[str] = None,
    log_level: str = "INFO",
) -> None:
    """Deploy resources to the BPM engine."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    logger.setLevel(log_level)
    set_log_level(log_level)

    async def deploy() -> None:
        async with operaton_session(headers={"Content-Type": None}) as session:
            form = aiohttp.FormData()
            for resource in resources:
                form.add_field(
                    "data",
                    resource.read_text(),
                    filename=resource.name,
                    content_type="application/octet-stream",
                )
            async with session.post(
                f"{base_url}/deployment/create",
                data=form,
            ) as response:
                results = await response.json()
                if "deployedProcessDefinitions" not in results:
                    print(json.dumps(results, indent=2))
                    return
                url = (
                    base_url.replace("/engine-rest", "").rstrip("/")
                    + "/operaton/app/cockpit/default/#/process-definition"
                )
                for result in results.get("deployedProcessDefinitions").values():
                    print(f"Deployed: {url}/{result['id']}/runtime")
                    print(f"With key: {result['key']}")

    asyncio.run(deploy())


@bpm.command(name="start")
def bpm_start(
    key: str,
    base_url: str = "http://localhost:8080/engine-rest",
    authorization: Optional[str] = None,
    log_level: str = "INFO",
) -> None:
    """Start a process instance by key."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    logger.setLevel(log_level)
    set_log_level(log_level)

    async def start() -> None:
        async with operaton_session() as session:
            async with session.post(
                f"{base_url}/process-definition/key/{key}/start",
                json={},
            ) as response:
                results = await response.json()
                if "links" not in results:
                    print(json.dumps(results, indent=2))
                    return
                url = (
                    base_url.replace("/engine-rest", "").rstrip("/")
                    + "/operaton/app/cockpit/default/#/process-instance"
                )
                print(f"Started: {url}/{results['id']}/runtime")

    asyncio.run(start())


cli.add_typer(bpm, name="bpm")


@cli.command(name="run")
def cli_run(
    resources: List[FilePath],
    base_url: str = "http://localhost:8080/engine-rest",
    authorization: Optional[str] = None,
    log_level: str = "INFO",
) -> None:
    """Deploy and start resources to the BPMN engine."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    logger.setLevel(log_level)
    set_log_level(log_level)

    async def start() -> None:
        async with operaton_session(headers={"Content-Type": None}) as session:
            form = aiohttp.FormData()
            for resource in resources:
                form.add_field(
                    "data",
                    resource.read_text(),
                    filename=resource.name,
                    content_type="application/octet-stream",
                )
            response = await session.post(
                f"{base_url}/deployment/create",
                data=form,
            )
            results = await response.json()
            if "deployedProcessDefinitions" not in results:
                print(json.dumps(results, indent=2))
                return
            for result in results.get("deployedProcessDefinitions").values():
                async with session.post(
                    f"{base_url}/process-definition/key/{result['key']}/start",
                    json={},
                ) as response:
                    results = await response.json()
                    if "links" not in results:
                        print(json.dumps(results, indent=2))
                        return
                    url = (
                        base_url.replace("/engine-rest", "").rstrip("/")
                        + "/operaton/app/cockpit/default/#/process-instance"
                    )
                    print(f"Started: {url}/{results['id']}/runtime")

    asyncio.run(start())


def main() -> None:
    cli()
