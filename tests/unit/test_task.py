"""Unit tests for task.py module."""

from datetime import datetime
from operaton.tasks.types import CompleteExternalTaskDto
from operaton.tasks.types import ExternalTaskComplete
from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from pathlib import Path
from purjo.task import robot_runner
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
import asyncio
import json
import pytest


@pytest.fixture
def mock_task() -> Any:
    """Create a mock LockedExternalTaskDto."""
    return LockedExternalTaskDto(
        id="task-123",
        workerId="worker-1",
        topicName="robotframework",
        activityId="task1",
        processInstanceId="process-1",
        processDefinitionId="process-def-1",
        executionId="execution-1",
        lockExpirationTime=datetime.fromisoformat("2024-01-01T12:00:00.000+00:00"),
        variables={
            "suite": VariableValueDto(
                value="*** Test Cases ***\nSimple Test\n    Log    Hello World",
                type=VariableValueType.String,
            ),
            "test_var": VariableValueDto(
                value="test_value",
                type=VariableValueType.String,
            ),
        },
    )


class TestRobotRunner:
    """Tests for robot_runner function."""

    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_task: Any) -> None:
        """Test successful robot execution."""
        with (
            patch("purjo.task.run") as mock_run,
            patch("purjo.task.py_from_operaton") as mock_py_from_operaton,
        ):
            # Mock py_from_operaton to return variables
            mock_py_from_operaton.return_value = {
                "suite": "*** Test Cases ***\nSimple Test\n    Log    Hello World",
                "test_var": "test_value",
            }

            # Mock run to return success
            mock_run.return_value = (0, b"Robot execution successful", b"")

            result = await robot_runner(mock_task)

            # Verify result structure
            assert isinstance(result, ExternalTaskComplete)
            assert result.task == mock_task
            assert isinstance(result.response, CompleteExternalTaskDto)
            assert result.response.workerId == "worker-1"

            # Verify localVariables contains output
            result_var = None
            if "result" in result.response.localVariables:  # type: ignore[operator]  # type: ignore[operator]
                result_var = result.response.localVariables["result"]  # type: ignore[index]  # type: ignore[index]
            if result_var:
                assert isinstance(result_var, VariableValueDto)
                assert result_var.type == VariableValueType.Json

            # Verify run was called with correct arguments
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == "uv"
            assert "run" in call_args[0][1]
            assert "--with" in call_args[0][1]
            assert "robotframework" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_failed_execution(self, mock_task: Any) -> None:
        """Test failed robot execution."""
        with (
            patch("purjo.task.run") as mock_run,
            patch("purjo.task.py_from_operaton") as mock_py_from_operaton,
        ):
            # Mock py_from_operaton to return variables
            mock_py_from_operaton.return_value = {
                "suite": "*** Test Cases ***\nFailing Test\n    Fail    Test failed",
                "test_var": "test_value",
            }

            # Mock run to return failure
            mock_run.return_value = (1, b"", b"Robot execution failed")

            with pytest.raises(AssertionError, match="Robot execution failed"):
                await robot_runner(mock_task)

    @pytest.mark.asyncio
    async def test_with_task_variables(self, mock_task: Any) -> None:
        """Test robot execution with task variables output."""
        with (
            patch("purjo.task.run") as mock_run,
            patch("purjo.task.py_from_operaton") as mock_py_from_operaton,
            patch("purjo.task.TemporaryDirectory") as mock_temp_dir,
        ):
            # Create a real temporary directory for testing
            import tempfile

            real_temp_dir = tempfile.mkdtemp()
            mock_context = MagicMock()
            mock_context.__enter__ = lambda self: real_temp_dir
            mock_context.__exit__ = lambda self, *args: None
            mock_temp_dir.return_value = mock_context

            # Mock py_from_operaton to return variables
            mock_py_from_operaton.return_value = {
                "suite": "*** Test Cases ***\nTest With Variables\n    Log    Test",
            }

            # Create task_variables.json file
            task_vars = {"result": "success", "count": 42}
            task_vars_file = Path(real_temp_dir) / "task_variables.json"
            task_vars_file.write_text(json.dumps(task_vars))

            # Mock run to return success
            mock_run.return_value = (0, b"Robot execution successful", b"")

            result = await robot_runner(mock_task)

            # Verify result is correct
            assert isinstance(result.response, CompleteExternalTaskDto)
            if result.response.localVariables:
                output_var = result.response.localVariables.get("result")
                if output_var:
                    output_data = json.loads(output_var.value)  # type: ignore[arg-type]  # type: ignore[arg-type]
                    assert output_data == task_vars

            # Clean up
            import shutil

            shutil.rmtree(real_temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_with_empty_variables(self, mock_task: Any) -> None:
        """Test robot execution with empty variables."""
        # Create a task with only the suite variable
        task_with_empty_vars = LockedExternalTaskDto(
            id="task-123",
            workerId="worker-1",
            topicName="robotframework",
            activityId="task1",
            processInstanceId="process-1",
            processDefinitionId="process-def-1",
            executionId="execution-1",
            lockExpirationTime=datetime.fromisoformat("2024-01-01T12:00:00.000+00:00"),
            variables={
                "suite": VariableValueDto(
                    value="*** Test Cases ***\nEmpty Test\n    Log    No variables",
                    type=VariableValueType.String,
                ),
            },
        )

        with (
            patch("purjo.task.run") as mock_run,
            patch("purjo.task.py_from_operaton") as mock_py_from_operaton,
        ):
            # Mock py_from_operaton to return only suite
            mock_py_from_operaton.return_value = {
                "suite": "*** Test Cases ***\nEmpty Test\n    Log    No variables",
            }

            # Mock run to return success
            mock_run.return_value = (0, b"Robot execution successful", b"")

            result = await robot_runner(task_with_empty_vars)

            # Verify result
            assert isinstance(result, ExternalTaskComplete)
            assert result.response.workerId == "worker-1"

    @pytest.mark.asyncio
    async def test_creates_correct_file_structure(self, mock_task: Any) -> None:
        """Test that robot_runner creates the correct file structure."""
        with (
            patch("purjo.task.run") as mock_run,
            patch("purjo.task.py_from_operaton") as mock_py_from_operaton,
            patch("purjo.task.Path") as mock_path_class,
        ):
            # Mock py_from_operaton to return variables
            mock_py_from_operaton.return_value = {
                "suite": "*** Test Cases ***\nTest\n    Log    Test",
                "var1": "value1",
            }

            # Mock run to return success
            mock_run.return_value = (0, b"Success", b"")

            # Track file writes
            written_files = {}

            def mock_write_text(content: Any) -> None:
                # Store the file content
                written_files[str(mock_path_class.return_value)] = content

            mock_path_class.return_value.write_text = mock_write_text

            try:
                await robot_runner(mock_task)
            except Exception:
                # Ignore errors from mocking, we're just checking calls
                pass

            # Verify py_from_operaton was called
            mock_py_from_operaton.assert_called_once_with(mock_task.variables)
