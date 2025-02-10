from operaton.tasks import set_log_level
from pathlib import Path
from purjo.runner import build_run
from purjo.runner import fail_reason
from purjo.runner import logger
from purjo.runner import Task
from purjo.utils import json_serializer
from pydantic import DirectoryPath
from pydantic import FilePath
from tempfile import TemporaryDirectory
from typing import Any
from typing import Dict
from typing import Union
from zipfile import ZipFile
import asyncio
import importlib.resources
import json
import os
import shutil
import tomllib


def _get_output_variables(
    robot: Union[FilePath, DirectoryPath],
    topic: str,
    variables: Dict[str, Any],
    log_level: str = "DEBUG",
) -> Dict[str, Any]:
    """
    Test a specific topic in a robot package with input for expected output.
    """
    logger.setLevel(os.environ.get("LOG_LEVEL") or log_level)
    set_log_level(os.environ.get("LOG_LEVEL") or log_level)

    if not shutil.which("uv"):
        raise FileNotFoundError("The 'uv' executable is not found in the system PATH.")

    if robot.is_dir():
        robot = robot.resolve()
        robot_toml = tomllib.loads((robot / "pyproject.toml").read_text())
    else:
        with ZipFile(robot, "r") as fp:
            robot_toml = tomllib.loads(fp.read("pyproject.toml").decode("utf-8"))
    purjo_toml = (robot_toml.get("tool") or {}).get("purjo") or {}

    assert topic in purjo_toml.get(
        "topics", {}
    ), f"Topic {topic} not found in robot package."

    config = Task(**purjo_toml["topics"][topic])

    robot_parser = (
        importlib.resources.files("purjo.data") / "RobotParser.py"
    ).read_text()
    with TemporaryDirectory() as robot_dir, TemporaryDirectory() as working_dir:
        variables = variables | {
            "BPMN:PROCESS": "BPMN:BPMN:TASK",
            "BPMN:TASK": "BPMN:TASK",
        }
        if robot.is_dir():
            shutil.copytree(robot, robot_dir, dirs_exist_ok=True)
        else:
            with ZipFile(robot, "r") as fp:
                fp.extractall(robot_dir)
                if (Path(robot_dir) / ".cache").is_dir():
                    shutil.move(Path(robot_dir) / ".cache", working_dir)
        (Path(working_dir) / "variables.json").write_text(
            json.dumps(variables, default=json_serializer)
        )
        (Path(working_dir) / "RobotParser.py").write_text(robot_parser)
        task_variables_file = Path(working_dir) / "task_variables.json"
        task_variables_file.write_text("{}")
        return_code, stdout, stderr = asyncio.run(
            build_run(
                config, robot_dir, working_dir, task_variables_file, task_variables_file
            )
        )
        variables = json.loads(task_variables_file.read_text())
        if return_code != 0:
            output_xml_path = Path(working_dir) / "output.xml"
            fail_reason_ = (
                fail_reason(output_xml_path) if output_xml_path.exists() else ""
            )
            variables.update(
                {
                    "errorCode": fail_reason_.split("\n", 1)[0].strip(),
                    "errorMessage": fail_reason_.split("\n", 1)[-1].strip(),
                }
            )
        return variables


class Purjo:
    """Robot Framework keyword library for `pur`(jo)."""

    def get_output_variables(
        self, path: str, topic: str, variables: Dict[str, Any], log_level: str = "DEBUG"
    ) -> Dict[str, Any]:
        """
        Executes test or task package at given path with given input variables and
        returns the output variables.
        """
        assert Path(path).is_file() or Path(path).is_dir()
        return _get_output_variables(
            FilePath(path) if Path(path).is_file() else DirectoryPath(path),
            topic,
            variables,
            log_level,
        )
