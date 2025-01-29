from operaton.tasks.config import logger
from operaton.tasks.types import CompleteExternalTaskDto
from operaton.tasks.types import ExternalTaskComplete
from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from pathlib import Path
from purjo.config import settings
from purjo.utils import json_serializer
from purjo.utils import lazydecode
from purjo.utils import py_from_operaton
from pydantic import FilePath
from tempfile import TemporaryDirectory
from typing import Callable
from typing import Coroutine
from typing import Dict
from typing import List
from typing import Tuple
from zipfile import ZipFile
import asyncio
import importlib.resources
import json
import os
import re


async def run(
    program: str, args: List[str], cwd: Path, env: Dict[str, str]
) -> Tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        program,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=os.environ | env | {"PYTHONPATH": ""},
    )

    stdout, stderr = await proc.communicate()
    stdout = stdout.strip() or b""
    stderr = stderr.strip() or b""

    if stderr:
        logger.debug("%s", lazydecode(stderr))
    if stdout:
        logger.debug("%s", lazydecode(stdout))

    logger.debug(f"exit code {proc.returncode}")

    return proc.returncode or 0, stdout, stderr


def fail_reason(robot_dir: str) -> str:
    reason = ""
    for file_path in Path(robot_dir).glob("*/**/output.xml"):
        xml = file_path.read_text()
        for match in re.findall(r'status="FAIL"[^>]*.([^<]*)', xml, re.M):
            match = match.strip()
            reason = match if match else reason
    return reason


def create_task(
    name: str,
    robot: FilePath,
    semaphore: asyncio.Semaphore,
) -> Callable[[LockedExternalTaskDto], Coroutine[None, None, ExternalTaskComplete]]:
    async def execute_task(task: LockedExternalTaskDto) -> ExternalTaskComplete:
        async with semaphore:
            variables = py_from_operaton(task.variables) | {
                "BPMN": "BPMN",
                "BPMN_SCOPE": "BPMN",
                "BPMN_TASK": "BPMN:TASK",
                "BPMN_TASK_SCOPE": "BPMN:TASK",
                "BPMN_PROCESS": "BPMN:PROCESS",
                "BPMN_PROCESS_SCOPE": "BPMN:PROCESS",
            }
            robot_parser = (
                importlib.resources.files("purjo.data") / "RobotParser.py"
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
                process_variables_file = Path(working_dir) / "process_variables.json"
                process_variables_file.write_text("{}")
                return_code, stdout, stderr = await run(
                    settings.UV_EXECUTABLE,
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
                        "--variablefile",
                        "variables.json",
                        "--outputdir",
                        working_dir,
                        robot_dir,
                    ],
                    Path(working_dir),
                    {
                        "BPMN_TASK_SCOPE": str(task_variables_file),
                        "BPMN_PROCESS_SCOPE": str(process_variables_file),
                        "UV_NO_SYNC": "0",
                    },
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
