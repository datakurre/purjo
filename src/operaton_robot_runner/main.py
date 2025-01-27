from collections.abc import Coroutine
from operaton.tasks import task
from operaton.tasks.config import handlers
from operaton.tasks.config import settings
from operaton.tasks.types import CompleteExternalTaskDto
from operaton.tasks.types import ExternalTaskComplete
from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from operaton.tasks.worker import external_task_worker
from operaton_robot_runner.config import settings as robot_settings
from operaton_robot_runner.runner import run
from operaton_robot_runner.utils import json_serializer
from operaton_robot_runner.utils import lazydecode
from operaton_robot_runner.utils import py_from_operaton
from pathlib import Path
from pydantic import FilePath
from tempfile import TemporaryDirectory
from typing import Callable
from typing import List
from typing import Optional
from zipfile import ZipFile
import asyncio
import importlib.resources
import json
import tomllib
import typer


def create_task(
    name: str,
    robot: FilePath,
    semaphore: asyncio.Semaphore,
) -> Callable[[LockedExternalTaskDto], Coroutine[None, None, ExternalTaskComplete]]:
    async def execute_task(task: LockedExternalTaskDto) -> ExternalTaskComplete:
        variables = py_from_operaton(task.variables)
        robot_parser = (
            importlib.resources.files("operaton_robot_runner.data") / "RobotParser.py"
        ).read_text()
        with TemporaryDirectory() as robot_dir, TemporaryDirectory() as working_dir:
            with ZipFile(robot, "r") as fp:
                fp.extractall(robot_dir)
            (Path(working_dir) / "variables.json").write_text(
                json.dumps(variables, default=json_serializer)
            )
            (Path(working_dir) / "RobotParser.py").write_text(robot_parser)
            task_variables_file = Path(working_dir) / "task_variables.json"
            task_variables_file.write_text("{}")
            return_code, stdout, stderr = await run(
                robot_settings.UV_EXECUTABLE,
                [
                    "run",
                    "--link-mode",
                    "copy",
                    "--project",
                    robot_dir,
                    "--",
                    "robot",
                    "-t",
                    name,
                    "--pythonpath",
                    working_dir,
                    "--pythonpath",
                    robot_dir,
                    "--parser",
                    "RobotParser",
                    "--variable",
                    "BPMN_SCOPE:BPMN",
                    "--variablefile",
                    "variables.json",
                    "--outputdir",
                    working_dir,
                    robot_dir,
                ],
                working_dir,
                {"BPMN_TASK_SCOPE": str(task_variables_file), "UV_NO_SYNC": "0"},
            )
            print(
                tuple(
                    p for p in Path(working_dir).glob("**/*") if ".venv" not in str(p)
                )
            )
            print(
                tuple(p for p in Path(robot_dir).glob("**/*") if ".venv" not in str(p))
            )
            assert return_code == 0, lazydecode(stdout + stderr)
            return ExternalTaskComplete(
                task=task,
                response=CompleteExternalTaskDto(
                    workerId=task.workerId,
                    localVariables={
                        "output": VariableValueDto(
                            value=(
                                task_variables_file.read_text()
                                if task_variables_file.exists
                                else "{}"
                            ),
                            type=VariableValueType.Json,
                        )
                    },
                ),
            )

    return execute_task


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
    """CLI."""
    settings.ENGINE_REST_BASE_URL = base_url
    settings.ENGINE_REST_AUTHORIZATION = authorization
    settings.ENGINE_REST_TIMEOUT_SECONDS = timeout
    settings.ENGINE_REST_POLL_TTL_SECONDS = poll_ttl
    settings.ENGINE_REST_LOCK_TTL_SECONDS = lock_ttl
    settings.LOG_LEVEL = log_level
    settings.TASKS_WORKER_ID = worker_id
    settings.TASKS_MODULE = None

    semaphore = asyncio.Semaphore(max_jobs)

    for robot in robots:
        with ZipFile(robot, "r") as fp:
            robot_toml = tomllib.loads(fp.read("pyproject.toml").decode("utf-8"))
            for topic, config in (robot_toml.get("bpmn:serviceTask") or {}).items():
                task(topic)(create_task(config["name"], robot, semaphore))

    asyncio.get_event_loop().run_until_complete(external_task_worker(handlers))


def main() -> None:
    cli()
