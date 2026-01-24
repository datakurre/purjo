"""Unit tests for Purjo.py library module."""

from factories import TaskFactory
from pathlib import Path
from purjo.Purjo import _get_output_variables
from purjo.Purjo import Purjo
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
from zipfile import ZipFile
import json
import pytest


class TestGetOutputVariables:
    """Tests for _get_output_variables function."""

    def test_directory_robot_package_successful(self, temp_dir: Path) -> None:
        """Test _get_output_variables with directory robot package - successful execution."""
        # Create a simple robot package directory
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        # Create pyproject.toml with purjo configuration
        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
on-fail = "ERROR"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)

        # Create a simple robot file
        robot_file_content = """*** Test Cases ***
Test Suite
    Log    Hello from test
    Set Task Variable    result    success
"""
        (robot_dir / "test.robot").write_text(robot_file_content)

        # Mock build_run and asyncio.run to return success
        mock_result = (0, b"Test passed", b"")
        with (
            patch("purjo.Purjo.asyncio.run", return_value=mock_result),
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
        ):

            # Call the function
            result = _get_output_variables(
                robot=robot_dir,
                topic="test-topic",
                variables={"input_var": "test_value"},
                secrets=None,
                log_level="DEBUG",
            )

            # Result should be a dictionary
            assert isinstance(result, dict)

    def test_zip_robot_package_successful(self, temp_dir: Path) -> None:
        """Test _get_output_variables with zip robot package - successful execution."""
        # Create a robot package directory first
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        # Create pyproject.toml
        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
on-fail = "ERROR"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)

        # Create a simple robot file
        robot_file_content = """*** Test Cases ***
Test Suite
    Log    Hello from test
"""
        (robot_dir / "test.robot").write_text(robot_file_content)

        # Create zip file
        zip_path = temp_dir / "robot.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.write(robot_dir / "pyproject.toml", "pyproject.toml")
            zf.write(robot_dir / "test.robot", "test.robot")

        # Mock asyncio.run to return success
        mock_result = (0, b"Test passed", b"")
        with (
            patch("purjo.Purjo.asyncio.run", return_value=mock_result),
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
        ):

            # Call the function
            result = _get_output_variables(
                robot=zip_path,
                topic="test-topic",
                variables={"input_var": "test_value"},
                secrets=None,
                log_level="DEBUG",
            )

            # Result should be a dictionary
            assert isinstance(result, dict)

    def test_failed_execution_with_error_extraction(self, temp_dir: Path) -> None:
        """Test _get_output_variables with failed execution and error extraction."""
        # Create a simple robot package directory
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        # Create pyproject.toml
        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
on-fail = "ERROR"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)

        # Create a robot file that fails
        robot_file_content = """*** Test Cases ***
Test Suite
    Fail    Test failure message
"""
        (robot_dir / "test.robot").write_text(robot_file_content)

        # Mock asyncio.run to return failure
        mock_result = (1, b"Test failed", b"Error output")

        # Create a mock for Path.exists to say output.xml exists
        original_exists = Path.exists

        def mock_exists(path_self: Any) -> bool:
            # Say output.xml exists so fail_reason gets called
            if str(path_self).endswith("output.xml"):
                return True
            return original_exists(path_self)

        with (
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
            patch(
                "purjo.Purjo.build_run",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch("purjo.Purjo.fail_reason") as mock_fail_reason,
            patch.object(Path, "exists", mock_exists),
        ):
            mock_fail_reason.return_value = "FAIL\nTest failure message"

            # Call the function
            result = _get_output_variables(
                robot=robot_dir,
                topic="test-topic",
                variables={"input_var": "test_value"},
                secrets=None,
                log_level="DEBUG",
            )

            # Verify fail_reason was called
            assert mock_fail_reason.called
            # Verify error variables are set
            assert "errorCode" in result
            assert "errorMessage" in result
            assert result["errorCode"] == "FAIL"
            assert "Test failure message" in result["errorMessage"]

    def test_missing_uv_executable(self, temp_dir: Path) -> None:
        """Test _get_output_variables raises error when uv is not found."""
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)

        with patch("purjo.Purjo.shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="uv.*not found"):
                _get_output_variables(
                    robot=robot_dir,
                    topic="test-topic",
                    variables={},
                )

    def test_topic_not_found_in_package(self, temp_dir: Path) -> None:
        """Test _get_output_variables raises assertion error when topic not found."""
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."other-topic"]
name = "Other Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)

        with patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"):
            with pytest.raises(AssertionError, match="Topic.*not found"):
                _get_output_variables(
                    robot=robot_dir,
                    topic="non-existent-topic",
                    variables={},
                )

    def test_variable_handling(self, temp_dir: Path) -> None:
        """Test _get_output_variables properly handles input variables."""
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)

        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        mock_result = (0, b"", b"")
        with (
            patch("purjo.Purjo.asyncio.run", return_value=mock_result),
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
        ):

            input_vars = {
                "string_var": "test",
                "int_var": 42,
                "bool_var": True,
                "list_var": [1, 2, 3],
                "dict_var": {"key": "value"},
            }

            result = _get_output_variables(
                robot=robot_dir,
                topic="test-topic",
                variables=input_vars,
                secrets=None,
            )

            # Result should be a dictionary
            assert isinstance(result, dict)

    def test_secrets_handling(self, temp_dir: Path) -> None:
        """Test _get_output_variables properly handles secrets."""
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)

        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        mock_result = (0, b"", b"")
        with (
            patch("purjo.Purjo.asyncio.run", return_value=mock_result),
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
        ):

            secrets = {
                "api_key": "secret123",
                "password": "pass456",
            }

            result = _get_output_variables(
                robot=robot_dir,
                topic="test-topic",
                variables={},
                secrets=secrets,
            )

            # Result should be a dictionary
            assert isinstance(result, dict)

    def test_log_level_setting(self, temp_dir: Path) -> None:
        """Test _get_output_variables respects log_level parameter."""
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)

        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        mock_result = (0, b"", b"")
        with (
            patch("purjo.Purjo.asyncio.run", return_value=mock_result),
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
            patch("purjo.Purjo.logger") as mock_logger,
        ):

            result = _get_output_variables(
                robot=robot_dir,
                topic="test-topic",
                variables={},
                log_level="INFO",
            )

            # Verify logger.setLevel was called with INFO
            mock_logger.setLevel.assert_called()


class TestPurjoClass:
    """Tests for Purjo class."""

    def test_get_output_variables_with_file_path(self, temp_dir: Path) -> None:
        """Test Purjo.get_output_variables with file path."""
        # Create a zip file
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)
        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        zip_path = temp_dir / "robot.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.write(robot_dir / "pyproject.toml", "pyproject.toml")
            zf.write(robot_dir / "test.robot", "test.robot")

        purjo = Purjo()

        with patch("purjo.Purjo._get_output_variables") as mock_get_output:
            mock_get_output.return_value = {"result": "success"}

            result = purjo.get_output_variables(
                path=str(zip_path),
                topic="test-topic",
                variables={"input": "value"},
            )

            assert mock_get_output.called
            assert result == {"result": "success"}

    def test_get_output_variables_with_directory_path(self, temp_dir: Path) -> None:
        """Test Purjo.get_output_variables with directory path."""
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)
        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        purjo = Purjo()

        with patch("purjo.Purjo._get_output_variables") as mock_get_output:
            mock_get_output.return_value = {"result": "success"}

            result = purjo.get_output_variables(
                path=str(robot_dir),
                topic="test-topic",
                variables={"input": "value"},
            )

            assert mock_get_output.called
            assert result == {"result": "success"}

    def test_get_output_variables_path_validation(self, temp_dir: Path) -> None:
        """Test Purjo.get_output_variables validates path exists."""
        purjo = Purjo()

        non_existent_path = temp_dir / "non_existent"

        with pytest.raises(AssertionError):
            purjo.get_output_variables(
                path=str(non_existent_path),
                topic="test-topic",
                variables={},
            )

    def test_get_output_variables_with_secrets(self, temp_dir: Path) -> None:
        """Test Purjo.get_output_variables passes secrets correctly."""
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)
        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        purjo = Purjo()

        with patch("purjo.Purjo._get_output_variables") as mock_get_output:
            mock_get_output.return_value = {"result": "success"}

            secrets = {"api_key": "secret123"}

            result = purjo.get_output_variables(
                path=str(robot_dir),
                topic="test-topic",
                variables={"input": "value"},
                secrets=secrets,
            )

            # Verify secrets were passed
            call_args = mock_get_output.call_args
            # call_args is a tuple (args, kwargs), we check positional arg 4 (secrets)
            assert call_args[0][3] == secrets

    def test_get_output_variables_with_custom_log_level(self, temp_dir: Path) -> None:
        """Test Purjo.get_output_variables passes custom log level."""
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()

        pyproject_content = """
[tool.purjo.topics."test-topic"]
name = "Test Suite"
"""
        (robot_dir / "pyproject.toml").write_text(pyproject_content)
        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        purjo = Purjo()

        with patch("purjo.Purjo._get_output_variables") as mock_get_output:
            mock_get_output.return_value = {"result": "success"}

            result = purjo.get_output_variables(
                path=str(robot_dir),
                topic="test-topic",
                variables={},
                log_level="ERROR",
            )

            # Verify log level was passed
            call_args = mock_get_output.call_args
            # call_args is a tuple (args, kwargs), we check positional arg 4 (log_level)
            assert call_args[0][4] == "ERROR"
