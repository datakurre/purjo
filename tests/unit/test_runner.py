"""Unit tests for runner.py module."""

from factories import FileFactory
from factories import TaskFactory
from pathlib import Path
from purjo.config import OnFail
from purjo.runner import build_run
from purjo.runner import fail_reason
from purjo.runner import is_python_fqfn
from purjo.runner import run
from purjo.runner import Task
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
from zipfile import ZipFile
import asyncio
import json
import pytest


class TestRun:
    """Tests for run function."""

    @pytest.mark.asyncio
    async def test_successful_command_execution(self, temp_dir: Path) -> None:
        """Test successful command execution."""
        returncode, stdout, stderr = await run("echo", ["hello"], temp_dir, {})

        assert returncode == 0
        assert b"hello" in stdout
        assert stderr == b""

    @pytest.mark.asyncio
    async def test_command_with_stderr(self, temp_dir: Path) -> None:
        """Test command with stderr output."""
        # Use sh to redirect to stderr
        returncode, stdout, stderr = await run(
            "sh", ["-c", "echo error >&2"], temp_dir, {}
        )

        assert returncode == 0
        assert b"error" in stderr

    @pytest.mark.asyncio
    async def test_command_with_env_vars(self, temp_dir: Path) -> None:
        """Test command with environment variables."""
        returncode, stdout, stderr = await run(
            "sh", ["-c", "echo $TEST_VAR"], temp_dir, {"TEST_VAR": "test_value"}
        )

        assert returncode == 0
        assert b"test_value" in stdout

    @pytest.mark.asyncio
    async def test_pythonpath_cleared(self, temp_dir: Path) -> None:
        """Test that PYTHONPATH is cleared."""
        returncode, stdout, stderr = await run(
            "sh", ["-c", "echo $PYTHONPATH"], temp_dir, {}
        )

        assert returncode == 0
        # PYTHONPATH should be empty
        assert stdout == b""

    @pytest.mark.asyncio
    async def test_command_failure(self, temp_dir: Path) -> None:
        """Test command failure."""
        returncode, stdout, stderr = await run("sh", ["-c", "exit 1"], temp_dir, {})

        assert returncode == 1


class TestFailReason:
    """Tests for fail_reason function."""

    def test_extract_failure_reason(self, sample_robot_failed_xml: Path) -> None:
        """Test extracting failure reason from output.xml."""
        reason = fail_reason(sample_robot_failed_xml)

        assert "Test failed" in reason
        assert "Expected value did not match" in reason

    def test_multiple_fail_statuses(self, temp_dir: Path) -> None:
        """Test with multiple FAIL statuses."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<robot>
  <test status="FAIL">First failure</test>
  <test status="FAIL">Second failure</test>
  <status status="FAIL">Third failure</status>
</robot>"""
        xml_file = temp_dir / "output.xml"
        xml_file.write_text(xml_content)

        reason = fail_reason(xml_file)

        # Should extract the last non-empty failure reason
        assert "failure" in reason.lower()

    def test_empty_reason(self, temp_dir: Path) -> None:
        """Test with empty reason."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<robot>
  <status status="FAIL"></status>
</robot>"""
        xml_file = temp_dir / "output.xml"
        xml_file.write_text(xml_content)

        reason = fail_reason(xml_file)

        assert reason == ""

    def test_malformed_xml(self, temp_dir: Path) -> None:
        """Test with malformed XML (robust handling)."""
        xml_file = temp_dir / "output.xml"
        xml_file.write_text("not valid xml")

        # Should not crash, just return empty or partial match
        reason = fail_reason(xml_file)
        assert isinstance(reason, str)


class TestTask:
    """Tests for Task model."""

    def test_default_values(self) -> None:
        """Test default values."""
        task = Task()

        assert task.name is None
        assert task.include is None
        assert task.exclude is None
        assert task.on_fail is None
        assert task.process_variables is False
        assert task.pythonpath is None

    def test_alias_parsing_on_fail(self) -> None:
        """Test alias parsing for on-fail."""
        task = Task(**{"name": "test", "on-fail": "FAIL"})  # type: ignore[arg-type]

        assert task.on_fail == OnFail.FAIL

    def test_alias_parsing_process_variables(self) -> None:
        """Test alias parsing for process-variables."""
        task = Task(**{"name": "test", "process-variables": True})  # type: ignore[arg-type]

        assert task.process_variables is True

    def test_full_task_config(self) -> None:
        """Test full task configuration."""
        task = Task(
            **{  # type: ignore[arg-type]
                "name": "test.robot",
                "include": "tag1",
                "exclude": "tag2",
                "on-fail": "FAIL",
                "process-variables": True,
                "pythonpath": ["/path1", "/path2"],
            }
        )

        assert task.name == "test.robot"
        assert task.include == "tag1"
        assert task.exclude == "tag2"
        assert task.on_fail == OnFail.FAIL
        assert task.process_variables is True
        assert task.pythonpath == ["/path1", "/path2"]


class TestIsPythonFqfn:
    """Tests for is_python_fqfn function."""

    def test_valid_fqfn(self) -> None:
        """Test valid fully qualified function names."""
        valid_fqfns = [
            "module.function",
            "package.module.function",
            "my_package.my_module.my_function",
            "a.b.c.d.e.function_name",
        ]

        for fqfn in valid_fqfns:
            assert is_python_fqfn(fqfn), f"Should be valid: {fqfn}"

    def test_invalid_patterns(self) -> None:
        """Test invalid patterns."""
        invalid_patterns = [
            "function",  # No module
            ".function",  # Starts with dot
            "module.",  # Ends with dot
            "module..function",  # Double dot
            "123module.function",  # Starts with number
            "module.123function",  # Function starts with number
            "",  # Empty string
        ]

        for pattern in invalid_patterns:
            assert not is_python_fqfn(pattern), f"Should be invalid: {pattern}"

    def test_edge_cases(self) -> None:
        """Test edge cases."""
        assert is_python_fqfn("_private._function")
        assert is_python_fqfn("Module.Function")
        assert is_python_fqfn("a.b")
        # Note: test.robot might match if it has exactly one dot
        # Let's verify the actual behavior
        assert not is_python_fqfn("test")


class TestBuildRun:
    """Tests for build_run function."""

    @pytest.mark.asyncio
    async def test_robot_mode_basic(self, temp_dir: Path) -> None:
        """Test correct arguments for basic Robot mode."""
        config = Task(name="test.robot")
        robot_dir = str(temp_dir / "robot")
        working_dir = str(temp_dir / "work")
        task_vars = temp_dir / "task_vars.json"
        process_vars = temp_dir / "process_vars.json"

        with patch("purjo.runner.run") as mock_run:
            mock_run.return_value = (0, b"", b"")
            coroutine = build_run(
                config, robot_dir, working_dir, task_vars, process_vars
            )

            # Check it returns a coroutine
            assert asyncio.iscoroutine(coroutine)

            # Execute it to verify
            await coroutine

            # Verify run was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0]

            # Verify UV executable
            assert call_args[0] == "uv"

            # Verify arguments contain expected parts
            args = call_args[1]
            assert "run" in args
            assert "--project" in args
            assert robot_dir in args
            assert "--" in args
            assert "robot" in args
            assert "-t" in args
            assert "test.robot" in args

    @pytest.mark.asyncio
    async def test_robot_mode_with_tags(self, temp_dir: Path) -> None:
        """Test with include and exclude tags."""
        config = Task(include="smoke", exclude="slow")
        robot_dir = str(temp_dir / "robot")
        working_dir = str(temp_dir / "work")
        task_vars = temp_dir / "task_vars.json"
        process_vars = temp_dir / "process_vars.json"

        with patch("purjo.runner.run") as mock_run:
            mock_run.return_value = (0, b"", b"")
            await build_run(config, robot_dir, working_dir, task_vars, process_vars)

            args = mock_run.call_args[0][1]
            assert "-i" in args
            assert "smoke" in args
            assert "-e" in args
            assert "slow" in args

    @pytest.mark.asyncio
    async def test_python_mode(self, temp_dir: Path) -> None:
        """Test Python mode with FQFN."""
        config = Task(name="mymodule.myfunction")
        robot_dir = str(temp_dir / "robot")
        working_dir = str(temp_dir / "work")
        task_vars = temp_dir / "task_vars.json"
        process_vars = temp_dir / "process_vars.json"

        with patch("purjo.runner.run") as mock_run:
            mock_run.return_value = (0, b"", b"")
            await build_run(config, robot_dir, working_dir, task_vars, process_vars)

            args = mock_run.call_args[0][1]
            assert "--parser" in args
            # Find parser argument
            parser_idx = args.index("--parser") + 1
            assert "PythonParser" in args[parser_idx]
            assert "mymodule.myfunction" in args[parser_idx]

    @pytest.mark.asyncio
    async def test_offline_mode_with_cache(self, temp_dir: Path) -> None:
        """Test offline mode when cache directory exists."""
        config = Task()
        robot_dir = str(temp_dir / "robot")
        working_dir = str(temp_dir / "work")
        (temp_dir / "work").mkdir()
        (temp_dir / "work" / ".cache").mkdir()
        task_vars = temp_dir / "task_vars.json"
        process_vars = temp_dir / "process_vars.json"

        with patch("purjo.runner.run") as mock_run:
            mock_run.return_value = (0, b"", b"")
            await build_run(config, robot_dir, working_dir, task_vars, process_vars)

            args = mock_run.call_args[0][1]
            assert "--offline" in args
            assert "--cache-dir" in args

    @pytest.mark.asyncio
    async def test_pythonpath_arguments(self, temp_dir: Path) -> None:
        """Test pythonpath arguments."""
        config = Task(pythonpath=["/path1", "/path2"])
        robot_dir = str(temp_dir / "robot")
        working_dir = str(temp_dir / "work")
        task_vars = temp_dir / "task_vars.json"
        process_vars = temp_dir / "process_vars.json"

        with patch("purjo.runner.run") as mock_run:
            mock_run.return_value = (0, b"", b"")
            await build_run(config, robot_dir, working_dir, task_vars, process_vars)

            args = mock_run.call_args[0][1]
            # Count pythonpath occurrences
            pythonpath_count = args.count("--pythonpath")
            # Should have 2 from config + 2 defaults (working_dir, robot_dir)
            assert pythonpath_count == 4

    @pytest.mark.asyncio
    async def test_environment_variables(self, temp_dir: Path) -> None:
        """Test environment variables passed to run."""
        config = Task()
        robot_dir = str(temp_dir / "robot")
        working_dir = str(temp_dir / "work")
        task_vars = temp_dir / "task_vars.json"
        process_vars = temp_dir / "process_vars.json"

        with patch("purjo.runner.run") as mock_run:
            mock_run.return_value = (0, b"", b"")
            await build_run(config, robot_dir, working_dir, task_vars, process_vars)

            # Check environment variables
            env = mock_run.call_args[0][3]
            assert "BPMN_PROCESS_SCOPE" in env
            assert "BPMN_TASK_SCOPE" in env
            assert "UV_NO_SYNC" in env
            assert env["UV_NO_SYNC"] == "0"
            assert env["VIRTUAL_ENV"] == ""


class TestTaskFactory:
    """Tests for TaskFactory helper."""

    def test_create_robot_task(self) -> None:
        """Test creating a Robot task."""
        task = TaskFactory.create_robot(id="test.robot")

        assert task.name == "test.robot"

    def test_create_python_task(self) -> None:
        """Test creating a Python task."""
        task = TaskFactory.create_python(id="module.function")

        assert task.name == "module.function"

    def test_task_with_custom_config(self) -> None:
        """Test task with custom configuration."""
        task = TaskFactory.create(
            **{  # type: ignore[arg-type]
                "id": "test.robot",
                "on-fail": "FAIL",
                "process-variables": True,
                "secrets_profile": "production",
            }
        )

        # TaskFactory creates Task objects with these attributes
        assert isinstance(task, Task)
