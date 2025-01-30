from operaton.tasks import external_task_worker
from operaton.tasks import handlers
from operaton.tasks import operaton_session
from operaton.tasks import settings
from operaton.tasks import task
from pathlib import Path
from purjo.config import OnFail
from purjo.runner import create_task
from purjo.runner import run
from pydantic import FilePath
from typing import List
from typing import Optional
from zipfile import ZipFile
import aiohttp
import asyncio
import importlib.resources
import json
import os
import pathspec
import shutil
import tomllib
import typer


cli = typer.Typer()


@cli.command(name="serve")
def cli_serve(
    robots: List[FilePath],
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
    Serve robot.zip packages as BPMN service tasks.
    """
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    settings.ENGINE_REST_TIMEOUT_SECONDS = timeout
    settings.ENGINE_REST_POLL_TTL_SECONDS = poll_ttl
    settings.ENGINE_REST_LOCK_TTL_SECONDS = lock_ttl
    settings.LOG_LEVEL = log_level
    settings.TASKS_WORKER_ID = worker_id
    settings.TASKS_MODULE = None

    semaphore = asyncio.Semaphore(max_jobs)

    if not shutil.which("uv"):
        raise FileNotFoundError("The 'uv' executable is not found in the system PATH.")

    for robot in robots:
        with ZipFile(robot, "r") as fp:
            robot_toml = tomllib.loads(fp.read("pyproject.toml").decode("utf-8"))
            for topic, config in (robot_toml.get("bpmn:serviceTask") or {}).items():
                task(topic)(create_task(config["name"], robot, on_fail, semaphore))

    asyncio.get_event_loop().run_until_complete(external_task_worker(handlers=handlers))


@cli.command(name="init")
def cli_init() -> None:
    """Initialize a new robot package."""
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
            },
        )
        (cwd_path / "hello.py").unlink()
        (cwd_path / "pyproject.toml").write_text(
            (cwd_path / "pyproject.toml").read_text()
            + """
["bpmn:serviceTask"]
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

    asyncio.run(init())


@cli.command(name="wrap")
def cli_wrap() -> None:
    """Wrap the current directory into a robot.zip package."""
    cwd_path = Path(os.getcwd())
    spec_path = cwd_path / ".wrapignore"
    spec_text = spec_path.read_text() if spec_path.exists() else ""
    spec = pathspec.GitIgnoreSpec.from_lines(
        spec_text.splitlines()
        + [
            ".gitignore",
            ".python-version",
            "log.html",
            "output.xml",
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


bpmn = typer.Typer(help="BPMN operations.")


@bpmn.command(name="deploy")
def bpmn_deploy(
    resources: List[FilePath],
    base_url: str = "http://localhost:8080/engine-rest",
    authorization: Optional[str] = None,
) -> None:
    """Deploy resources to the BPMN engine."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization

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
                print(json.dumps(await response.json(), indent=2))

    asyncio.run(deploy())


@bpmn.command(name="start")
def bpmn_start(
    key: str,
    base_url: str = "http://localhost:8080/engine-rest",
    authorization: Optional[str] = None,
) -> None:
    """Start a process instance by key."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization

    async def start() -> None:
        async with operaton_session() as session:
            async with session.post(
                f"{base_url}/process-definition/key/{key}/start",
                json={},
            ) as response:
                print(json.dumps(await response.json(), indent=2))

    asyncio.run(start())


cli.add_typer(bpmn, name="bpmn")


def main() -> None:
    cli()
