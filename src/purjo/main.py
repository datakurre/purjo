from operaton.tasks import external_task_worker
from operaton.tasks import handlers
from operaton.tasks import operaton_session
from operaton.tasks import settings
from operaton.tasks import task
from pathlib import Path
from purjo.runner import create_task
from pydantic import FilePath
from typing import List
from typing import Optional
from zipfile import ZipFile
import aiohttp
import asyncio
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
                task(topic)(create_task(config["name"], robot, semaphore))

    asyncio.get_event_loop().run_until_complete(external_task_worker(handlers=handlers))


@cli.command(name="wrap")
def cli_wrap():
    """Wrap the current directory into a robot.zip package."""
    cwd_path = Path(os.getcwd())
    spec_path = cwd_path / ".wrapignore"
    spec_text = spec_path.read_text() if spec_path.exists() else ""
    spec = pathspec.GitIgnoreSpec.from_lines(
        spec_text.splitlines()
        + [
            ".venv/",
            "log.html",
            "report.html",
            "output.xml",
            "robot.zip",
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

    async def deploy():
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
                response.raise_for_status()

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

    async def start():
        async with operaton_session() as session:
            async with session.post(
                f"{base_url}/process-definition/key/{key}/start",
                json={},
            ) as response:
                print(json.dumps(await response.json(), indent=2))
                response.raise_for_status

    asyncio.run(start())


cli.add_typer(bpmn, name="bpmn")


def main() -> None:
    cli()
