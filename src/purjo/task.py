from operaton.tasks import task
from operaton.tasks.types import CompleteExternalTaskDto
from operaton.tasks.types import ExternalTaskComplete
from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from pathlib import Path
from purjo.config import settings
from purjo.runner import run
from purjo.utils import json_serializer
from purjo.utils import lazydecode
from purjo.utils import py_from_operaton
from tempfile import TemporaryDirectory
import asyncio
import importlib.resources
import json


SEMAPHORE = asyncio.Semaphore(settings.TASKS_MAX_JOBS)


@task(settings.TASKS_TOPIC, localVariables=True)
async def robot_runner(task: LockedExternalTaskDto) -> ExternalTaskComplete:
    variables = await py_from_operaton(task.variables)
    suite = variables.pop("suite")
    robot_parser = (
        importlib.resources.files("purjo.data") / "RobotParser.py"
    ).read_text()
    with TemporaryDirectory() as robot_dir, TemporaryDirectory() as working_dir:
        (Path(robot_dir) / "__init__.robot").write_text("")
        (Path(robot_dir) / "task.robot").write_text(suite)
        (Path(working_dir) / "variables.json").write_text(
            json.dumps(variables, default=json_serializer)
        )
        (Path(working_dir) / "RobotParser.py").write_text(robot_parser)
        task_variables_file = Path(working_dir) / "task_variables.json"
        return_code, stdout, stderr = await run(
            settings.UV_EXECUTABLE,
            [
                "run",
                "--with",
                "robotframework",
                "--",
                settings.ROBOT_EXECUTABLE,
                "--pythonpath",
                working_dir,
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
            Path(working_dir),
            {"BPMN_TASK_SCOPE": str(task_variables_file)},
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
                            if task_variables_file.exists()
                            else "{}"
                        ),
                        type=VariableValueType.Json,
                    )
                },
            ),
        )
