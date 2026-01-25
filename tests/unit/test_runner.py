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


class TestPrepareWorkingDirectories:
    """Tests for prepare_working_directories function."""

    def test_prepare_from_directory(self, temp_dir: Path) -> None:
        """Test preparing directories from a robot directory."""
        from purjo.runner import prepare_working_directories

        # Setup source directory
        robot_source = temp_dir / "robot_source"
        robot_source.mkdir()
        (robot_source / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Hello"
        )
        (robot_source / "pyproject.toml").write_text("[project]\nname = 'test'")

        robot_dir = temp_dir / "robot_dir"
        robot_dir.mkdir()
        working_dir = temp_dir / "working_dir"
        working_dir.mkdir()

        prepare_working_directories(robot_source, working_dir, robot_dir)

        assert (robot_dir / "test.robot").exists()
        assert (robot_dir / "pyproject.toml").exists()

    def test_prepare_from_zip(self, temp_dir: Path) -> None:
        """Test preparing directories from a zip file."""
        from purjo.runner import prepare_working_directories

        # Create a zip file
        zip_path = temp_dir / "robot.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("test.robot", "*** Test Cases ***\nTest\n    Log    Hello")
            zf.writestr("pyproject.toml", "[project]\nname = 'test'")

        robot_dir = temp_dir / "robot_dir"
        robot_dir.mkdir()
        working_dir = temp_dir / "working_dir"
        working_dir.mkdir()

        prepare_working_directories(zip_path, working_dir, robot_dir)

        assert (robot_dir / "test.robot").exists()
        assert (robot_dir / "pyproject.toml").exists()

    def test_prepare_from_zip_with_cache(self, temp_dir: Path) -> None:
        """Test preparing directories from zip with cache directory."""
        from purjo.runner import prepare_working_directories

        # Create a zip file with .cache directory
        zip_path = temp_dir / "robot.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("test.robot", "*** Test Cases ***")
            zf.writestr(".cache/some_cache", "cached data")

        robot_dir = temp_dir / "robot_dir"
        robot_dir.mkdir()
        working_dir = temp_dir / "working_dir"
        working_dir.mkdir()

        prepare_working_directories(zip_path, working_dir, robot_dir)

        # Cache should be moved to working_dir
        assert (working_dir / ".cache").exists()
        assert not (robot_dir / ".cache").exists()


class TestPrepareVariablesFiles:
    """Tests for prepare_variables_files function."""

    def test_prepare_with_no_secrets(self, temp_dir: Path) -> None:
        """Test preparing variable files without secrets."""
        from purjo.runner import prepare_variables_files

        variables = {"key": "value", "count": 42}
        working_dir = temp_dir / "working"
        working_dir.mkdir()

        task_file, process_file = prepare_variables_files(
            variables, None, working_dir, "# RobotParser content"
        )

        assert (working_dir / "variables.json").exists()
        assert (working_dir / "secrets.json").exists()
        assert (working_dir / "RobotParser.py").exists()
        assert task_file.exists()
        assert process_file.exists()

        # Verify variables content
        vars_content = json.loads((working_dir / "variables.json").read_text())
        assert vars_content["key"] == "value"
        assert vars_content["count"] == 42

        # Secrets should be empty
        secrets_content = json.loads((working_dir / "secrets.json").read_text())
        assert secrets_content == {}

    def test_prepare_with_secrets_provider(self, temp_dir: Path) -> None:
        """Test preparing variable files with secrets provider."""
        from purjo.runner import prepare_variables_files
        from unittest.mock import MagicMock

        mock_provider = MagicMock()
        mock_provider.read.return_value = {"secret_key": "secret_value"}

        variables = {"key": "value"}
        working_dir = temp_dir / "working"
        working_dir.mkdir()

        prepare_variables_files(variables, mock_provider, working_dir, "# RobotParser")

        secrets_content = json.loads((working_dir / "secrets.json").read_text())
        assert secrets_content["secret_key"] == "secret_value"


class TestBuildFileAttachment:
    """Tests for build_file_attachment function."""

    def test_build_html_attachment(self, temp_dir: Path) -> None:
        """Test building HTML file attachment."""
        from operaton.tasks.types import VariableValueType
        from purjo.runner import build_file_attachment

        html_file = temp_dir / "log.html"
        html_file.write_text("<html><body>Test</body></html>")

        result = build_file_attachment(html_file, "log.html", "text/html")

        assert result.type == VariableValueType.File
        assert result.valueInfo is not None
        assert result.valueInfo["filename"] == "log.html"
        assert result.valueInfo["mimetype"] == "text/html"

    def test_build_xml_attachment(self, temp_dir: Path) -> None:
        """Test building XML file attachment."""
        from operaton.tasks.types import VariableValueType
        from purjo.runner import build_file_attachment

        xml_file = temp_dir / "output.xml"
        xml_file.write_text("<robot><test/></robot>")

        result = build_file_attachment(xml_file, "output.xml", "text/xml")

        assert result.type == VariableValueType.File
        assert result.valueInfo is not None
        assert result.valueInfo["filename"] == "output.xml"


class TestBuildErrorVariables:
    """Tests for build_error_variables function."""

    def test_single_line_error(self) -> None:
        """Test building error variables from single line."""
        from purjo.runner import build_error_variables

        result = build_error_variables("Simple error message")

        assert result["errorCode"].value == "Simple error message"
        assert result["errorMessage"].value == "Simple error message"

    def test_multiline_error(self) -> None:
        """Test building error variables from multiline text."""
        from purjo.runner import build_error_variables

        result = build_error_variables("Error code\nDetailed error message")

        assert result["errorCode"].value == "Error code"
        assert result["errorMessage"].value == "Detailed error message"

    def test_empty_error(self) -> None:
        """Test building error variables from empty string."""
        from purjo.runner import build_error_variables

        result = build_error_variables("")

        assert result["errorCode"].value == ""
        assert result["errorMessage"].value == ""


class TestHandleSuccessResult:
    """Tests for handle_success_result function."""

    @pytest.mark.asyncio
    async def test_success_with_return_code_zero(self, temp_dir: Path) -> None:
        """Test handling successful result with return code 0."""
        from operaton.tasks.types import ExternalTaskComplete
        from operaton.tasks.types import LockedExternalTaskDto
        from purjo.runner import handle_success_result

        task = LockedExternalTaskDto(
            id="task-1",
            workerId="worker-1",
            topicName="test-topic",
            activityId="activity-1",
            processInstanceId="process-1",
            processDefinitionId="def-1",
            executionId="exec-1",
        )

        result = await handle_success_result(
            task=task,
            task_variables={},
            process_variables={},
            return_code=0,
            output_xml_path=temp_dir / "output.xml",
            on_fail=OnFail.FAIL,
        )

        assert isinstance(result, ExternalTaskComplete)
        assert result.response.workerId == "worker-1"

    @pytest.mark.asyncio
    async def test_success_with_on_fail_complete(self, temp_dir: Path) -> None:
        """Test handling result with on_fail=COMPLETE adds null error fields."""
        from operaton.tasks.types import CompleteExternalTaskDto
        from operaton.tasks.types import LockedExternalTaskDto
        from operaton.tasks.types import VariableValueType
        from purjo.runner import handle_success_result

        task = LockedExternalTaskDto(
            id="task-1",
            workerId="worker-1",
            topicName="test-topic",
            activityId="activity-1",
            processInstanceId="process-1",
            processDefinitionId="def-1",
            executionId="exec-1",
        )

        result = await handle_success_result(
            task=task,
            task_variables={},
            process_variables={},
            return_code=0,
            output_xml_path=temp_dir / "output.xml",
            on_fail=OnFail.COMPLETE,
        )

        assert isinstance(result.response, CompleteExternalTaskDto)
        assert result.response.localVariables is not None
        assert "errorCode" in result.response.localVariables
        assert (
            result.response.localVariables["errorCode"].type == VariableValueType.Null
        )

    @pytest.mark.asyncio
    async def test_nonzero_return_code_adds_error_vars(self, temp_dir: Path) -> None:
        """Test that non-zero return code adds error variables."""
        from operaton.tasks.types import CompleteExternalTaskDto
        from operaton.tasks.types import LockedExternalTaskDto
        from purjo.runner import handle_success_result

        task = LockedExternalTaskDto(
            id="task-1",
            workerId="worker-1",
            topicName="test-topic",
            activityId="activity-1",
            processInstanceId="process-1",
            processDefinitionId="def-1",
            executionId="exec-1",
        )

        # Create output.xml with failure
        output_xml = temp_dir / "output.xml"
        output_xml.write_text(
            '<robot><status status="FAIL">Test failed</status></robot>'
        )

        result = await handle_success_result(
            task=task,
            task_variables={},
            process_variables={},
            return_code=1,
            output_xml_path=output_xml,
            on_fail=OnFail.COMPLETE,  # Complete mode still processes
        )

        assert isinstance(result.response, CompleteExternalTaskDto)
        assert result.response.localVariables is not None
        assert "errorCode" in result.response.localVariables


class TestHandleFailureResult:
    """Tests for handle_failure_result function."""

    @pytest.mark.asyncio
    async def test_failure_with_on_fail_error(self, temp_dir: Path) -> None:
        """Test failure handling with on_fail=ERROR returns BPMN error."""
        from operaton.tasks.types import ExternalTaskComplete
        from operaton.tasks.types import LockedExternalTaskDto
        from operaton.tasks.types import VariableValueDto
        from operaton.tasks.types import VariableValueType
        from purjo.runner import handle_failure_result

        task = LockedExternalTaskDto(
            id="task-1",
            workerId="worker-1",
            topicName="test-topic",
            activityId="activity-1",
            processInstanceId="process-1",
            processDefinitionId="def-1",
            executionId="exec-1",
        )

        output_xml = temp_dir / "output.xml"
        output_xml.write_text(
            '<robot><status status="FAIL">Test failed</status></robot>'
        )

        log_html = VariableValueDto(value=b"html", type=VariableValueType.File)
        output_var = VariableValueDto(value=b"xml", type=VariableValueType.File)

        with patch("purjo.runner.operaton_session") as mock_session:
            session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            session.post = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await handle_failure_result(
                task=task,
                on_fail=OnFail.ERROR,
                output_xml_path=output_xml,
                stdout=b"stdout",
                stderr=b"stderr",
                task_variables={"log.html": log_html, "output.xml": output_var},
                process_variables={},
            )

        assert isinstance(result, ExternalTaskComplete)

    @pytest.mark.asyncio
    async def test_failure_with_on_fail_fail(self, temp_dir: Path) -> None:
        """Test failure handling with on_fail=FAIL returns failure response."""
        from operaton.tasks.types import ExternalTaskFailure
        from operaton.tasks.types import LockedExternalTaskDto
        from operaton.tasks.types import VariableValueDto
        from operaton.tasks.types import VariableValueType
        from purjo.runner import handle_failure_result

        task = LockedExternalTaskDto(
            id="task-1",
            workerId="worker-1",
            topicName="test-topic",
            activityId="activity-1",
            processInstanceId="process-1",
            processDefinitionId="def-1",
            executionId="exec-1",
        )

        output_xml = temp_dir / "output.xml"
        output_xml.write_text(
            '<robot><status status="FAIL">Test failed</status></robot>'
        )

        log_html = VariableValueDto(value=b"html", type=VariableValueType.File)
        output_var = VariableValueDto(value=b"xml", type=VariableValueType.File)

        with patch("purjo.runner.operaton_session") as mock_session:
            session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            session.post = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await handle_failure_result(
                task=task,
                on_fail=OnFail.FAIL,
                output_xml_path=output_xml,
                stdout=b"stdout output",
                stderr=b"stderr output",
                task_variables={"log.html": log_html, "output.xml": output_var},
                process_variables={},
            )

        assert isinstance(result, ExternalTaskFailure)
        assert result.response.retries == 0


@pytest.fixture
def temp_dir() -> Any:
    """Provide a temporary directory."""
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_robot_failed_xml(temp_dir: Path) -> Path:
    """Create a sample failed robot output.xml."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<robot>
  <test name="Test Case" id="s1-t1">
    <status status="FAIL">Test failed
Expected value did not match</status>
  </test>
</robot>"""
    xml_file = temp_dir / "output.xml"
    xml_file.write_text(xml_content)
    return xml_file


class TestGetDefaultRobotParserContent:
    """Tests for _get_default_robot_parser_content function."""

    def test_returns_robot_parser_content(self) -> None:
        """Test that the function returns RobotParser content."""
        from purjo.runner import _get_default_robot_parser_content

        content = _get_default_robot_parser_content()

        assert isinstance(content, str)
        assert len(content) > 0
        # The RobotParser.py should contain class definitions
        assert "class" in content or "def" in content


class TestCreateTask:
    """Tests for create_task function."""

    @pytest.mark.asyncio
    async def test_create_task_returns_callable(self, temp_dir: Path) -> None:
        """Test that create_task returns a callable."""
        from purjo.runner import create_task

        robot_dir = temp_dir / "robot"
        robot_dir.mkdir()
        (robot_dir / "pyproject.toml").write_text("[project]\nname='test'")
        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Hello"
        )

        config = Task()
        semaphore = asyncio.Semaphore(1)

        task_handler = create_task(
            config=config,
            robot=robot_dir,
            on_fail=OnFail.FAIL,
            semaphore=semaphore,
            secrets_provider=None,
            robot_parser_content="# Mock RobotParser",
        )

        # Verify it returns a callable
        assert callable(task_handler)

    @pytest.mark.asyncio
    async def test_create_task_execution_success(self, temp_dir: Path) -> None:
        """Test task execution with success."""
        from operaton.tasks.types import ExternalTaskComplete
        from operaton.tasks.types import LockedExternalTaskDto
        from purjo.runner import create_task

        robot_dir = temp_dir / "robot"
        robot_dir.mkdir()
        (robot_dir / "pyproject.toml").write_text("[project]\nname='test'")
        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Hello"
        )

        config = Task()
        semaphore = asyncio.Semaphore(1)

        task_handler = create_task(
            config=config,
            robot=robot_dir,
            on_fail=OnFail.COMPLETE,
            semaphore=semaphore,
            secrets_provider=None,
            robot_parser_content="# Mock RobotParser",
        )

        task = LockedExternalTaskDto(
            id="task-1",
            workerId="worker-1",
            topicName="test-topic",
            activityId="activity-1",
            processInstanceId="process-1",
            processDefinitionId="def-1",
            executionId="exec-1",
            variables={},
        )

        # Create a coroutine that returns the expected tuple
        async def mock_build_run_coro(*args: Any, **kwargs: Any) -> Any:
            return (0, b"success", b"")

        with (
            patch("purjo.runner.build_run", side_effect=mock_build_run_coro),
            patch("purjo.runner.py_from_operaton") as mock_py_from,
        ):
            mock_py_from.return_value = {}

            result = await task_handler(task)

            # On success, should return ExternalTaskComplete
            assert isinstance(result, ExternalTaskComplete)

    @pytest.mark.asyncio
    async def test_create_task_from_zip(self, temp_dir: Path) -> None:
        """Test task creation from zip file."""
        from purjo.runner import create_task

        # Create a zip file
        zip_path = temp_dir / "robot.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("pyproject.toml", "[project]\nname='test'")
            zf.writestr("test.robot", "*** Test Cases ***\nTest\n    Log    Hello")

        config = Task()
        semaphore = asyncio.Semaphore(1)

        task_handler = create_task(
            config=config,
            robot=zip_path,
            on_fail=OnFail.FAIL,
            semaphore=semaphore,
            secrets_provider=None,
            robot_parser_content="# Mock RobotParser",
        )

        assert callable(task_handler)
