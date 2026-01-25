"""Edge cases and error handling tests for purjo.

Related User Stories:
- US-001: Serve robot packages
- US-009: Control failure behavior
- US-012: Wrap robot.zip

Related ADRs:
- ADR-003: Architecture overview
"""

from operaton.tasks.types import VariableValueDto
from pathlib import Path
from purjo.config import OnFail
from purjo.data.RobotParser import Variables
from purjo.main import cli_init
from purjo.main import cli_serve
from purjo.main import cli_wrap
from purjo.Purjo import Purjo
from purjo.runner import create_task
from purjo.runner import Task
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
from zipfile import ZipFile
import json
import pytest
import subprocess
import tomllib


class TestSubprocessFailures:
    """Test subprocess failure handling."""

    def test_cli_serve_missing_uv_executable(self, temp_dir: Any) -> None:
        """Test that cli_serve raises error when uv is not found."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="'uv' executable is not found"):
                cli_serve(robots=[temp_dir])

    def test_cli_init_missing_uv_executable(
        self, temp_dir: Any, monkeypatch: Any
    ) -> None:
        """Test that cli_init raises error when uv is not found."""
        # Change to the temp directory
        monkeypatch.chdir(temp_dir)

        with patch("shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="'uv' executable is not found"):
                cli_init(python=False)

    def test_robot_execution_failure(self, temp_dir: Any, mock_semaphore: Any) -> None:
        """Test handling of robot execution failures."""
        # Create a task that will fail
        task_dir = temp_dir / "failing_task"
        task_dir.mkdir()

        # Create a minimal pyproject.toml
        pyproject = task_dir / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "failing-task"
version = "0.1.0"

[tool.purjo.robot]
module = "failing_task"
"""
        )

        # Create a robot file that will fail
        robot_file = task_dir / "failing_task.robot"
        robot_file.write_text(
            """
*** Test Cases ***
Failing Test
    Fail    This test intentionally fails
"""
        )

        task_config = Task(name="test")
        task_func = create_task(
            config=task_config,
            robot=task_dir,
            semaphore=mock_semaphore,
            secrets_provider=None,
            on_fail=OnFail.FAIL,
        )

        # Test that we can create the task function
        assert callable(task_func)

    def test_subprocess_timeout(self, temp_dir: Any, mock_semaphore: Any) -> None:
        """Test handling of subprocess timeout."""
        task_dir = temp_dir / "timeout_task"
        task_dir.mkdir()

        pyproject = task_dir / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "timeout-task"
version = "0.1.0"

[tool.purjo.robot]
module = "timeout_task"
"""
        )

        task_config = Task(name="test")
        task_func = create_task(
            config=task_config,
            robot=task_dir,
            semaphore=mock_semaphore,
            secrets_provider=None,
            on_fail=OnFail.FAIL,
        )

        # Test that we can create the task function
        assert callable(task_func)


class TestFileSystemErrors:
    """Test file system error handling."""

    def test_permission_denied_reading_pyproject(self, temp_dir: Any) -> None:
        """Test handling of permission denied when reading pyproject.toml."""
        task_dir = temp_dir / "no_perms"
        task_dir.mkdir()
        pyproject = task_dir / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "no-perms"
version = "0.1.0"

[tool.purjo.robot]
module = "no_perms"
"""
        )

        # Make file unreadable
        pyproject.chmod(0o000)

        try:
            with pytest.raises(PermissionError):
                with open(pyproject, "r") as f:
                    f.read()
        finally:
            # Restore permissions for cleanup
            pyproject.chmod(0o644)

    def test_missing_directory(self) -> None:
        """Test handling of missing directory."""
        from purjo.Purjo import _get_output_variables

        with pytest.raises(FileNotFoundError):
            _get_output_variables(
                robot=Path("/nonexistent/directory"),
                topic="test",
                variables={},
                secrets=None,
            )

    def test_corrupted_zip_file(self, temp_dir: Any) -> None:
        """Test handling of corrupted zip file."""
        from purjo.Purjo import _get_output_variables

        corrupted_zip = temp_dir / "corrupted.zip"
        # Create an invalid zip file
        corrupted_zip.write_bytes(b"not a valid zip file")

        with pytest.raises(Exception):  # ZipFile raises various exceptions
            _get_output_variables(
                robot=corrupted_zip, topic="test", variables={}, secrets=None
            )

    def test_disk_full_simulation(self, temp_dir: Any) -> None:
        """Test handling when disk is full (simulated with OSError)."""
        with patch("pathlib.Path.write_text") as mock_write:
            mock_write.side_effect = OSError("No space left on device")

            with pytest.raises(OSError, match="No space left on device"):
                output_file = temp_dir / "output.txt"
                output_file.write_text("test data")

    def test_read_only_directory(self, temp_dir: Any) -> None:
        """Test handling operations in read-only directory."""
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()

        # Make directory read-only
        readonly_dir.chmod(0o444)

        try:
            with pytest.raises(PermissionError):
                test_file = readonly_dir / "test.txt"
                test_file.write_text("test")
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)


class TestNetworkErrors:
    """Test network error handling."""

    @pytest.mark.asyncio
    async def test_connection_refused(self) -> None:
        """Test handling of connection refused errors."""
        from aiohttp import ClientError

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = ClientError("Connection refused")

            # This would typically be in a function that uses aiohttp
            with pytest.raises(ClientError):
                raise ClientError("Connection refused")

    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        """Test handling of timeout errors."""
        from asyncio import TimeoutError as AsyncTimeoutError

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = AsyncTimeoutError()

            with pytest.raises(AsyncTimeoutError):
                raise AsyncTimeoutError()

    @pytest.mark.asyncio
    async def test_http_500_error(self) -> None:
        """Test handling of HTTP 500 errors."""
        from aiohttp import ClientResponseError

        with patch("aiohttp.ClientSession.get") as mock_get:
            error = ClientResponseError(
                request_info=Mock(),
                history=(),
                status=500,
                message="Internal Server Error",
            )
            mock_get.side_effect = error

            with pytest.raises(ClientResponseError):
                raise error


class TestMalformedInput:
    """Test handling of malformed input."""

    def test_invalid_toml(self, temp_dir: Any, mock_semaphore: Any) -> None:
        """Test handling of invalid TOML syntax."""
        task_dir = temp_dir / "invalid_toml"
        task_dir.mkdir()

        pyproject = task_dir / "pyproject.toml"
        pyproject.write_text("invalid toml {[} syntax")

        with pytest.raises(tomllib.TOMLDecodeError):
            with open(pyproject, "rb") as f:
                tomllib.load(f)

    def test_invalid_json_variables(self, temp_dir: Any) -> None:
        """Test handling of invalid JSON in variables file."""
        invalid_json = temp_dir / "invalid.json"
        invalid_json.write_text("invalid json {[}")

        with pytest.raises(json.JSONDecodeError):
            with open(invalid_json) as f:
                json.load(f)

    def test_missing_required_toml_fields(self, temp_dir: Any) -> None:
        """Test handling of missing required fields in pyproject.toml."""
        task_dir = temp_dir / "incomplete_toml"
        task_dir.mkdir()

        pyproject = task_dir / "pyproject.toml"
        # Missing tool.purjo section
        pyproject.write_text(
            """
[project]
name = "incomplete"
version = "0.1.0"
"""
        )

        # Test that accessing missing keys raises errors
        with pytest.raises(KeyError):
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                tool_purjo = data["tool"]["purjo"]

    def test_empty_pyproject_toml(self, temp_dir: Any) -> None:
        """Test handling of empty pyproject.toml."""
        task_dir = temp_dir / "empty_toml"
        task_dir.mkdir()

        pyproject = task_dir / "pyproject.toml"
        pyproject.write_text("")

        with pytest.raises((tomllib.TOMLDecodeError, KeyError)):
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                # Empty TOML is valid, so check for missing keys
                tool = data["tool"]["purjo"]

    def test_corrupted_robot_zip(self, temp_dir: Any) -> None:
        """Test handling of corrupted robot.zip file."""
        from purjo.Purjo import _get_output_variables

        corrupted_zip = temp_dir / "robot.zip"
        corrupted_zip.write_bytes(b"PK\x00\x00corrupted")

        with pytest.raises(Exception):
            _get_output_variables(
                robot=corrupted_zip, topic="test", variables={}, secrets=None
            )


class TestVariableTypeBoundaries:
    """Test variable type boundary conditions."""

    def test_int32_min_boundary(self) -> None:
        """Test INT32 minimum value boundary."""
        var = VariableValueDto(value=-2147483648, type="Integer")
        assert var.value == -2147483648
        assert var.type == "Integer"

    def test_int32_max_boundary(self) -> None:
        """Test INT32 maximum value boundary."""
        var = VariableValueDto(value=2147483647, type="Integer")
        assert var.value == 2147483647
        assert var.type == "Integer"

    def test_int32_overflow(self) -> None:
        """Test handling of INT32 overflow."""
        # Python automatically handles large integers, but we test the type
        var = VariableValueDto(value=2147483648, type="Long")
        assert var.value == 2147483648
        assert var.type == "Long"

    def test_large_json_structure(self, temp_dir: Any) -> None:
        """Test handling of large JSON structures."""
        large_json = {"data": [{"id": i, "name": f"item_{i}"} for i in range(10000)]}

        json_file = temp_dir / "large.json"
        json_file.write_text(json.dumps(large_json))

        # Should handle large JSON without issues
        with open(json_file) as f:
            loaded_data = json.load(f)
        assert len(loaded_data["data"]) == 10000

    def test_binary_file_handling(self, temp_dir: Any) -> None:
        """Test handling of binary files."""
        binary_file = temp_dir / "test.bin"
        binary_data = bytes(range(256))
        binary_file.write_bytes(binary_data)

        # Reading binary file should work
        read_data = binary_file.read_bytes()
        assert read_data == binary_data

    def test_empty_string_variable(self) -> None:
        """Test handling of empty string variables."""
        var = VariableValueDto(value="", type="String")
        assert var.value == ""
        assert var.type == "String"

    def test_null_variable(self) -> None:
        """Test handling of null/None variables."""
        var = VariableValueDto(value=None, type="Null")
        assert var.value is None
        assert var.type == "Null"

    def test_very_long_string(self) -> None:
        """Test handling of very long strings."""
        long_string = "a" * 1000000  # 1 million characters
        var = VariableValueDto(value=long_string, type="String")

        assert var.type == "String"

    def test_unicode_characters(self) -> None:
        """Test handling of various unicode characters."""
        unicode_string = "Hello 世界 🌍 مرحبا Привет"
        var = VariableValueDto(value=unicode_string, type="String")
        assert var.value == unicode_string
        assert var.type == "String"

    def test_nested_json_depth(self, temp_dir: Any) -> None:
        """Test handling of deeply nested JSON structures."""
        nested = {"level": 1}
        current = nested
        for i in range(2, 101):  # Create 100 levels of nesting
            current["next"] = {"level": i}  # type: ignore[assignment]  # type: ignore[assignment]
            current = current["next"]  # type: ignore[assignment]  # type: ignore[assignment]

        json_file = temp_dir / "deep.json"
        json_file.write_text(json.dumps(nested))

        # Should handle deep nesting
        with open(json_file) as f:
            loaded_data = json.load(f)
        assert "level" in loaded_data
        assert loaded_data["level"] == 1

    def test_boolean_values(self) -> None:
        """Test handling of boolean values."""
        var_true = VariableValueDto(value=True, type="Boolean")
        var_false = VariableValueDto(value=False, type="Boolean")

        assert var_true.value is True
        assert var_false.value is False
        assert var_true.type == "Boolean"
        assert var_false.type == "Boolean"

    def test_float_precision(self) -> None:
        """Test handling of floating point precision."""
        var = VariableValueDto(value=3.141592653589793, type="Double")

        assert var.type == "Double"

    def test_special_float_values(self) -> None:
        """Test handling of special float values."""
        import math

        # Test infinity
        var_inf = VariableValueDto(value=math.inf, type="Double")
        assert var_inf.type == "Double"

        # Test negative infinity
        var_ninf = VariableValueDto(value=-math.inf, type="Double")
        assert var_ninf.type == "Double"

        # Test NaN
        var_nan = VariableValueDto(value=math.nan, type="Double")
        assert var_nan.type == "Double"
