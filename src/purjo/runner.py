"""Robot Framework task runner module.

This module handles the execution of Robot Framework tasks and Python callables
as external tasks for the Operaton BPM engine. It manages task lifecycle including:
- Building and executing robot commands
- Handling task variables and secrets
- Managing file attachments and results
- Error handling and failure reporting
"""

from operaton.tasks import operaton_session
from operaton.tasks import settings as operaton_settings
from operaton.tasks import stream_handler
from operaton.tasks.types import CompleteExternalTaskDto
from operaton.tasks.types import ExternalTaskBpmnError
from operaton.tasks.types import ExternalTaskComplete
from operaton.tasks.types import ExternalTaskFailure
from operaton.tasks.types import ExternalTaskFailureDto
from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import PatchVariablesDto
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from pathlib import Path
from purjo.config import OnFail
from purjo.config import settings
from purjo.models import Task
from purjo.secrets import SecretsProvider
from purjo.utils import get_wrap_pathspec
from purjo.utils import inline_screenshots
from purjo.utils import json_serializer
from purjo.utils import lazydecode
from purjo.utils import operaton_from_py
from purjo.utils import py_from_operaton
from pydantic import DirectoryPath
from pydantic import FilePath
from tempfile import TemporaryDirectory
from typing import Any
from typing import Callable
from typing import Coroutine
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from zipfile import ZipFile
import asyncio
import base64
import importlib.resources
import json
import logging
import os
import re
import shutil

logger = logging.getLogger(__name__)
logger.addHandler(stream_handler)
logger.setLevel(operaton_settings.LOG_LEVEL)

# Re-export Task for backward compatibility
__all__ = ["Task"]


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


def fail_reason(path: Path) -> str:
    """Extract the reason for the failure from the output.xml file."""
    xml = path.read_text()
    reason = ""
    for match in re.findall(r'status="FAIL"[^>]*.([^<]*)', xml, re.M):
        match = match.strip()
        reason = match if match else reason
    return reason


def _get_default_robot_parser_content() -> str:
    """Get the default RobotParser.py content from package resources."""
    return (importlib.resources.files("purjo.data") / "RobotParser.py").read_text()


def is_python_fqfn(value: str) -> bool:
    """Check if a string looks like a fully qualified function name (fqfn)."""
    # Check basic pattern and ensure no double dots, no leading/trailing dots
    if not re.match(r"^[a-zA-Z_][\w\.]*\.[a-zA-Z_][\w]*$", value):
        return False
    # Check for double dots
    if ".." in value:
        return False
    # Check for leading or trailing dots (redundant, caught by regex above)
    if value.startswith(".") or value.endswith("."):  # pragma: no cover
        return False  # pragma: no cover
    return True


def _build_uv_base_args(robot_dir: str) -> List[str]:
    """Build base uv run arguments."""
    return [
        "run",
        "--link-mode",
        "copy",
        "--project",
        robot_dir,
    ]


def _build_cache_args(working_dir: str) -> List[str]:
    """Build cache arguments if cache directory exists."""
    cache_path = Path(working_dir) / ".cache"
    if cache_path.is_dir():
        return ["--offline", "--cache-dir", str(cache_path)]
    return []


def _build_robot_filter_args(config: Task) -> List[str]:
    """Build robot test filtering arguments from config."""
    args: List[str] = []
    if config.name:
        args.extend(["-t", config.name])
    if config.include:
        args.extend(["-i", config.include])
    if config.exclude:
        args.extend(["-e", config.exclude])
    return args


def _build_pythonpath_args(config: Task, working_dir: str, robot_dir: str) -> List[str]:
    """Build pythonpath arguments."""
    args: List[str] = []
    for path in config.pythonpath or []:
        args.extend(["--pythonpath", path])
    args.extend(["--pythonpath", working_dir, "--pythonpath", robot_dir])
    return args


def _build_parser_arg(config: Task, is_python: bool) -> str:
    """Build parser argument based on task type."""
    if is_python:
        return f"RobotParser.PythonParser:{config.name}"
    return "RobotParser"


def build_run(
    config: Task,
    robot_dir: str,
    working_dir: str,
    task_variables_file: Path,
    process_variables_file: Path,
) -> Coroutine[None, None, Tuple[int, bytes, bytes]]:
    """Build and execute a robot run command.

    Constructs the uv run command with all necessary arguments for executing
    a Robot Framework task or Python callable.

    Args:
        config: Task configuration containing filters and settings.
        robot_dir: Path to the robot package directory.
        working_dir: Path to the working directory for execution.
        task_variables_file: Path to write task-scoped variables.
        process_variables_file: Path to write process-scoped variables.

    Returns:
        A coroutine that executes the command and returns (exit_code, stdout, stderr).
    """
    is_python = bool(config.name and is_python_fqfn(config.name))

    args = (
        _build_uv_base_args(robot_dir)
        + _build_cache_args(working_dir)
        + ["--", "robot"]
        + _build_robot_filter_args(config)
        + _build_pythonpath_args(config, working_dir, robot_dir)
        + [
            "--parser",
            _build_parser_arg(config, is_python),
            "--variablefile",
            "RobotParser.Variables:variables.json:secrets.json",
            "--outputdir",
            working_dir,
            robot_dir,
        ]
    )

    env = {
        "BPMN_PROCESS_SCOPE": str(process_variables_file),
        "BPMN_TASK_SCOPE": str(task_variables_file),
        "UV_NO_SYNC": "0",
        "VIRTUAL_ENV": "",
    }

    return run(settings.UV_EXECUTABLE, args, Path(working_dir), env)


def prepare_working_directories(
    robot: Union[FilePath, DirectoryPath],
    working_dir: Path,
    robot_dir: Path,
) -> None:
    """Copy robot files to working directory."""
    if robot.is_dir():
        spec = get_wrap_pathspec(robot.absolute())
        for file_path in spec.match_tree(robot, negate=True, follow_links=False):
            src = robot / file_path
            dst = robot_dir / file_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    else:
        with ZipFile(robot, "r") as fp:
            fp.extractall(robot_dir)
            if (robot_dir / ".cache").is_dir():
                shutil.move(robot_dir / ".cache", working_dir)


def prepare_variables_files(
    variables: Dict[str, Any],
    secrets_provider: Optional[SecretsProvider],
    working_dir: Path,
    robot_parser_content: Optional[str] = None,
) -> Tuple[Path, Path]:
    """Create variables, secrets, and RobotParser files in working directory.

    Args:
        variables: Dictionary of variables to write.
        secrets_provider: Optional provider for secrets.
        working_dir: Working directory path.
        robot_parser_content: Optional RobotParser.py content for testing.
            If None, loads from package resources.

    Returns:
        Tuple of (task_variables_file, process_variables_file) paths.
    """
    robot_parser = robot_parser_content or _get_default_robot_parser_content()

    (working_dir / "variables.json").write_text(
        json.dumps(variables, default=json_serializer)
    )

    secrets_data: dict[str, Any] = secrets_provider.read() if secrets_provider else {}
    (working_dir / "secrets.json").write_text(
        json.dumps(secrets_data, default=json_serializer)
    )

    (working_dir / "RobotParser.py").write_text(robot_parser)

    task_variables_file = working_dir / "task_variables.json"
    task_variables_file.write_text("{}")

    process_variables_file = working_dir / "process_variables.json"
    process_variables_file.write_text("{}")

    return task_variables_file, process_variables_file


def build_file_attachment(
    file_path: Path,
    filename: str,
    mimetype: str,
) -> VariableValueDto:
    """Build a file attachment variable from a file path."""
    inline_screenshots(file_path)
    return VariableValueDto(
        value=base64.b64encode(file_path.read_bytes()),
        type=VariableValueType.File,
        valueInfo={
            "filename": filename,
            "mimetype": mimetype,
            "mimeType": mimetype,
            "encoding": "utf-8",
        },
    )


def build_error_variables(fail_reason_text: str) -> Dict[str, VariableValueDto]:
    """Build errorCode and errorMessage variables from failure reason."""
    return {
        "errorCode": VariableValueDto(
            value=fail_reason_text.split("\n", 1)[0].strip(),
            type=VariableValueType.String,
        ),
        "errorMessage": VariableValueDto(
            value=fail_reason_text.split("\n", 1)[-1].strip(),
            type=VariableValueType.String,
        ),
    }


async def handle_success_result(
    task: LockedExternalTaskDto,
    task_variables: Dict[str, VariableValueDto],
    process_variables: Dict[str, VariableValueDto],
    return_code: int,
    output_xml_path: Path,
    on_fail: OnFail,
) -> ExternalTaskComplete:
    """Handle successful task execution and build the complete response."""
    if return_code != 0:
        fail_reason_ = fail_reason(output_xml_path) if output_xml_path.exists() else ""
        task_variables.update(build_error_variables(fail_reason_))
    elif on_fail == OnFail.COMPLETE:
        task_variables.update(
            {
                "errorCode": VariableValueDto(
                    value=None,
                    type=VariableValueType.Null,
                ),
                "errorMessage": VariableValueDto(
                    value=None,
                    type=VariableValueType.Null,
                ),
            }
        )

    return ExternalTaskComplete(
        task=task,
        response=CompleteExternalTaskDto(
            workerId=task.workerId,
            localVariables=task_variables,
            variables=process_variables,
        ),
    )


async def handle_failure_result(
    task: LockedExternalTaskDto,
    on_fail: OnFail,
    output_xml_path: Path,
    stdout: bytes,
    stderr: bytes,
    task_variables: Dict[str, VariableValueDto],
    process_variables: Dict[str, VariableValueDto],
) -> Union[ExternalTaskComplete, ExternalTaskFailure]:
    """Handle failed task execution and build the appropriate response."""
    # Only post output file attachments if they were actually produced
    modifications: Dict[str, VariableValueDto] = {}
    if "log.html" in task_variables:
        modifications["log.html"] = task_variables["log.html"]
    if "output.xml" in task_variables:
        modifications["output.xml"] = task_variables["output.xml"]

    if modifications:
        async with operaton_session() as session:
            resp = await session.post(
                f"{operaton_settings.ENGINE_REST_BASE_URL}/execution/{task.executionId}/localVariables",
                data=PatchVariablesDto(
                    modifications=modifications,
                ).model_dump_json(),
            )
            resp.raise_for_status()

    fail_reason_ = fail_reason(output_xml_path) if output_xml_path.exists() else ""
    if not fail_reason_:
        fail_reason_ = (stderr or stdout or b"Unknown execution error").decode(
            "utf-8", errors="replace"
        )

    if on_fail == OnFail.ERROR:
        return ExternalTaskComplete(
            task=task,
            response=ExternalTaskBpmnError(
                workerId=task.workerId,
                errorCode=fail_reason_.split("\n", 1)[0].strip(),
                errorMessage=fail_reason_.split("\n", 1)[-1].strip(),
                variables=process_variables,
            ),
        )
    else:
        return ExternalTaskFailure(
            task=task,
            response=ExternalTaskFailureDto(
                workerId=task.workerId,
                errorMessage=fail_reason_,
                errorDetails=(stdout + stderr).decode("utf-8"),
                retries=0,
                retryTimeout=0,
            ),
        )


def create_task(
    config: Task,
    robot: Union[FilePath, DirectoryPath],
    on_fail: OnFail,
    semaphore: asyncio.Semaphore,
    secrets_provider: Optional[SecretsProvider],
    robot_parser_content: Optional[str] = None,
) -> Callable[
    [LockedExternalTaskDto],
    Coroutine[None, None, Union[ExternalTaskComplete, ExternalTaskFailure]],
]:
    """Create an external task handler for Robot Framework execution.

    Creates a closure that executes Robot Framework tasks in isolated temporary
    directories, handling variable conversion, file attachments, and result
    processing.

    Args:
        config: Task configuration containing filters and settings.
        robot: Path to the robot package (directory or zip file).
        on_fail: How to handle task failures (FAIL, COMPLETE, ERROR).
        semaphore: Semaphore for limiting concurrent task execution.
        secrets_provider: Optional provider for secrets injection.
        robot_parser_content: Optional RobotParser.py content for testing.
            If None, loads from package resources.

    Returns:
        An async function that executes the task and returns the result.
    """

    async def execute_task(
        task: LockedExternalTaskDto,
    ) -> Union[ExternalTaskComplete, ExternalTaskFailure]:
        async with semaphore:
            with (
                TemporaryDirectory() as robot_dir_str,
                TemporaryDirectory() as working_dir_str,
            ):
                robot_dir = Path(robot_dir_str)
                working_dir = Path(working_dir_str)

                # Prepare variables
                variables = await py_from_operaton(
                    task.variables, task, working_dir
                ) | {
                    "BPMN:PROCESS": "BPMN:PROCESS",
                    "BPMN:TASK": "BPMN:TASK",
                }

                # Prepare working directories
                prepare_working_directories(robot, working_dir, robot_dir)

                # Prepare variables and secrets files
                task_variables_file, process_variables_file = prepare_variables_files(
                    variables, secrets_provider, working_dir, robot_parser_content
                )

                # Execute robot run
                return_code, stdout, stderr = await build_run(
                    config,
                    str(robot_dir),
                    str(working_dir),
                    task_variables_file,
                    process_variables_file,
                )

                # Process results
                task_variables = operaton_from_py(
                    json.loads(task_variables_file.read_text()),
                    [robot_dir, working_dir],
                )
                process_variables = operaton_from_py(
                    json.loads(process_variables_file.read_text()),
                    [robot_dir, working_dir],
                )

                # Preserve variable types from original task
                for name_, variable in (
                    task.variables or {}
                ).items():  # pragma: no cover
                    if (
                        name_ in task_variables and task_variables[name_].value is None
                    ):  # pragma: no cover
                        task_variables[name_].type = variable.type  # pragma: no cover
                    if name_ in process_variables:  # pragma: no cover
                        process_variables[name_].type = (
                            variable.type
                        )  # pragma: no cover

                # Attach output files
                log_html_path = working_dir / "log.html"
                if log_html_path.exists():  # pragma: no cover
                    task_variables["log.html"] = build_file_attachment(
                        log_html_path, "log.html", "text/html"
                    )  # pragma: no cover

                output_xml_path = working_dir / "output.xml"
                if output_xml_path.exists():  # pragma: no cover
                    task_variables["output.xml"] = build_file_attachment(
                        output_xml_path, "output.xml", "text/xml"
                    )  # pragma: no cover

                # Handle success or failure
                if return_code == 0 or on_fail == OnFail.COMPLETE:
                    return await handle_success_result(
                        task,
                        task_variables,
                        process_variables,
                        return_code,
                        output_xml_path,
                        on_fail,
                    )
                else:  # pragma: no cover
                    return await handle_failure_result(
                        task,
                        on_fail,
                        output_xml_path,
                        stdout,
                        stderr,
                        task_variables,
                        process_variables,
                    )

    return execute_task
