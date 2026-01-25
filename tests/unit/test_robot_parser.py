"""Unit tests for data/RobotParser.py module.

Related User Stories:
- US-001: Serve robot packages

Related ADRs:
- ADR-001: Use uv for environment management
- ADR-003: Architecture overview
"""

from pathlib import Path
from purjo.data.RobotParser import BPMN_PROCESS_SCOPE
from purjo.data.RobotParser import BPMN_TASK_SCOPE
from purjo.data.RobotParser import json_serializer
from purjo.data.RobotParser import PythonParser
from purjo.data.RobotParser import RobotParser
from purjo.data.RobotParser import set_bpmn_process
from purjo.data.RobotParser import set_bpmn_task
from purjo.data.RobotParser import Variables
from robot.running import TestDefaults  # type: ignore[import-untyped]  # type: ignore[import-untyped]
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
import json
import os
import pytest


class TestJsonSerializer:
    """Tests for json_serializer function."""

    def test_serialize_datetime(self) -> None:
        """Test serializing datetime objects."""
        import datetime

        dt = datetime.datetime(2024, 1, 15, 10, 30, 45)
        result = json_serializer(dt)
        assert result == "2024-01-15T10:30:45"

    def test_serialize_path(self) -> None:
        """Test serializing Path objects."""
        path = Path("/tmp/test")
        result = json_serializer(path)
        assert "/tmp/test" in result or "\\tmp\\test" in result

    def test_serialize_unsupported_type(self) -> None:
        """Test that unsupported types raise TypeError."""
        with pytest.raises(TypeError, match="not serializable"):
            json_serializer(object())


class TestSetBpmnTask:
    """Tests for set_bpmn_task function."""

    def test_set_bpmn_task_writes_to_file(self, temp_dir: Path) -> None:
        """Test that set_bpmn_task writes to the correct file."""
        task_file = temp_dir / "task_variables.json"
        task_file.write_text("{}")

        os.environ[BPMN_TASK_SCOPE] = str(task_file)

        try:
            mock_variable_scopes = Mock()
            set_bpmn_task(mock_variable_scopes, "${myVar}", "test_value")

            # Verify the file was written
            data = json.loads(task_file.read_text())
            assert "myVar" in data
            assert data["myVar"] == "test_value"
        finally:
            if BPMN_TASK_SCOPE in os.environ:
                del os.environ[BPMN_TASK_SCOPE]

    def test_set_bpmn_task_creates_new_file(self, temp_dir: Path) -> None:
        """Test that set_bpmn_task creates a new file if it doesn't exist."""
        task_file = temp_dir / "new_task_variables.json"

        os.environ[BPMN_TASK_SCOPE] = str(task_file)

        try:
            mock_variable_scopes = Mock()
            set_bpmn_task(mock_variable_scopes, "${newVar}", "new_value")

            # Verify the file was created and written
            assert task_file.exists()
            data = json.loads(task_file.read_text())
            assert "newVar" in data
            assert data["newVar"] == "new_value"
        finally:
            if BPMN_TASK_SCOPE in os.environ:
                del os.environ[BPMN_TASK_SCOPE]

    def test_set_bpmn_task_updates_existing_data(self, temp_dir: Path) -> None:
        """Test that set_bpmn_task updates existing data in the file."""
        task_file = temp_dir / "task_variables.json"
        task_file.write_text('{"existing": "value"}')

        os.environ[BPMN_TASK_SCOPE] = str(task_file)

        try:
            mock_variable_scopes = Mock()
            set_bpmn_task(mock_variable_scopes, "${newVar}", "new_value")

            # Verify both old and new data exist
            data = json.loads(task_file.read_text())
            assert "existing" in data
            assert data["existing"] == "value"
            assert "newVar" in data
            assert data["newVar"] == "new_value"
        finally:
            if BPMN_TASK_SCOPE in os.environ:
                del os.environ[BPMN_TASK_SCOPE]

    def test_set_bpmn_task_missing_environment_variable(self) -> None:
        """Test that set_bpmn_task raises AssertionError when env var is missing."""
        # Ensure env var is not set
        if BPMN_TASK_SCOPE in os.environ:
            del os.environ[BPMN_TASK_SCOPE]

        mock_variable_scopes = Mock()

        with pytest.raises(AssertionError, match=BPMN_TASK_SCOPE):
            set_bpmn_task(mock_variable_scopes, "${myVar}", "test_value")


class TestSetBpmnProcess:
    """Tests for set_bpmn_process function."""

    def test_set_bpmn_process_writes_to_file(self, temp_dir: Path) -> None:
        """Test that set_bpmn_process writes to the correct file."""
        process_file = temp_dir / "process_variables.json"
        process_file.write_text("{}")

        os.environ[BPMN_PROCESS_SCOPE] = str(process_file)

        try:
            mock_variable_scopes = Mock()
            set_bpmn_process(mock_variable_scopes, "${processVar}", "process_value")

            # Verify the file was written
            data = json.loads(process_file.read_text())
            assert "processVar" in data
            assert data["processVar"] == "process_value"
        finally:
            if BPMN_PROCESS_SCOPE in os.environ:
                del os.environ[BPMN_PROCESS_SCOPE]

    def test_set_bpmn_process_creates_new_file(self, temp_dir: Path) -> None:
        """Test that set_bpmn_process creates a new file if it doesn't exist."""
        process_file = temp_dir / "new_process_variables.json"

        os.environ[BPMN_PROCESS_SCOPE] = str(process_file)

        try:
            mock_variable_scopes = Mock()
            set_bpmn_process(mock_variable_scopes, "${newVar}", "new_value")

            # Verify the file was created and written
            assert process_file.exists()
            data = json.loads(process_file.read_text())
            assert "newVar" in data
            assert data["newVar"] == "new_value"
        finally:
            if BPMN_PROCESS_SCOPE in os.environ:
                del os.environ[BPMN_PROCESS_SCOPE]

    def test_set_bpmn_process_missing_environment_variable(self) -> None:
        """Test that set_bpmn_process raises AssertionError when env var is missing."""
        # Ensure env var is not set
        if BPMN_PROCESS_SCOPE in os.environ:
            del os.environ[BPMN_PROCESS_SCOPE]

        mock_variable_scopes = Mock()

        with pytest.raises(AssertionError, match=BPMN_PROCESS_SCOPE):
            set_bpmn_process(mock_variable_scopes, "${processVar}", "process_value")


class TestRobotParser:
    """Tests for RobotParser class."""

    def test_parse_valid_robot_file(self, temp_dir: Path) -> None:
        """Test parsing a valid .robot file."""
        robot_file = temp_dir / "test.robot"
        robot_file.write_text(
            """*** Test Cases ***
My Test Case
    Log    Hello World
"""
        )

        parser = RobotParser()
        defaults = TestDefaults()
        suite = parser.parse(robot_file, defaults)

        assert suite is not None
        # Robot Framework capitalizes the suite name from the file name
        assert suite.name == "Test"
        assert len(suite.tests) == 1
        assert suite.tests[0].name == "My Test Case"

    def test_parse_init_robot_file(self, temp_dir: Path) -> None:
        """Test parsing __init__.robot file."""
        robot_dir = temp_dir / "robot_suite"
        robot_dir.mkdir()
        init_file = robot_dir / "__init__.robot"
        init_file.write_text(
            """*** Settings ***
Documentation    Suite initialization
"""
        )

        parser = RobotParser()
        defaults = TestDefaults()
        suite = parser.parse_init(init_file, defaults)

        assert suite is not None

    def test_extension_attribute(self) -> None:
        """Test that RobotParser has the correct extension."""
        parser = RobotParser()
        assert parser.extension == ".robot"


class TestPythonParser:
    """Tests for PythonParser class."""

    def test_parse_with_valid_fqfn(self, temp_dir: Path) -> None:
        """Test parsing with valid fully qualified function name."""
        python_file = temp_dir / "tasks.py"
        python_file.write_text(
            """
def main():
    print("Hello from Python")
"""
        )

        parser = PythonParser(fqfn="tasks.main")
        defaults = TestDefaults()
        suite = parser.parse(python_file, defaults)

        assert suite is not None
        assert suite.name == "tasks"
        assert len(suite.tests) == 1
        assert suite.tests[0].name == "tasks.main"

    def test_parse_with_invalid_fqfn(self, temp_dir: Path) -> None:
        """Test parsing with invalid fqfn returns empty suite."""
        python_file = temp_dir / "tasks.py"
        python_file.write_text("# Empty")

        parser = PythonParser(fqfn="invalid")
        defaults = TestDefaults()
        suite = parser.parse(python_file, defaults)

        assert suite is not None
        assert len(suite.tests) == 0

    def test_parse_with_empty_fqfn(self, temp_dir: Path) -> None:
        """Test parsing with empty fqfn returns empty suite."""
        python_file = temp_dir / "tasks.py"
        python_file.write_text("# Empty")

        parser = PythonParser(fqfn="")
        defaults = TestDefaults()
        suite = parser.parse(python_file, defaults)

        assert suite is not None
        assert len(suite.tests) == 0

    def test_parse_with_mismatched_source(self, temp_dir: Path) -> None:
        """Test parsing with mismatched source file returns empty suite."""
        python_file = temp_dir / "other.py"
        python_file.write_text("# Empty")

        parser = PythonParser(fqfn="tasks.main")
        defaults = TestDefaults()
        suite = parser.parse(python_file, defaults)

        # Should return empty suite because 'other' doesn't match 'tasks'
        assert suite is not None
        assert len(suite.tests) == 0

    def test_parse_init_returns_empty_suite(self, temp_dir: Path) -> None:
        """Test that parse_init always returns empty suite."""
        python_file = temp_dir / "__init__.py"
        python_file.write_text("# Empty")

        parser = PythonParser(fqfn="tasks.main")
        defaults = TestDefaults()
        suite = parser.parse_init(python_file, defaults)

        assert suite is not None
        assert len(suite.tests) == 0

    def test_extension_attribute(self) -> None:
        """Test that PythonParser has the correct extension."""
        parser = PythonParser()
        assert parser.extension == ".py"


class TestVariables:
    """Tests for Variables class."""

    def test_load_variables_from_file(self, temp_dir: Path) -> None:
        """Test loading variables from JSON file."""
        variables_file = temp_dir / "variables.json"
        variables_file.write_text('{"var1": "value1", "var2": 42}')

        secrets_file = temp_dir / "secrets.json"
        secrets_file.write_text("{}")

        variables = Variables()
        result = variables.get_variables(str(variables_file), str(secrets_file))

        assert "var1" in result
        assert result["var1"] == "value1"
        assert "var2" in result
        assert result["var2"] == 42

    def test_load_secrets_with_secret_type(self, temp_dir: Path) -> None:
        """Test loading secrets with Secret type."""
        variables_file = temp_dir / "variables.json"
        variables_file.write_text("{}")

        secrets_file = temp_dir / "secrets.json"
        secrets_file.write_text('{"api_key": "secret123", "password": "pass456"}')

        variables = Variables()
        result = variables.get_variables(str(variables_file), str(secrets_file))

        assert "api_key" in result
        assert "password" in result
        # Secret objects have special __str__ representation that shows "<secret>"
        # But internally they store the actual value
        # Check that the secret object is present (not checking its string representation)
        assert result["api_key"] is not None
        assert result["password"] is not None

    def test_missing_variables_file(self, temp_dir: Path) -> None:
        """Test that missing variables file returns empty dict."""
        non_existent_variables = temp_dir / "non_existent_variables.json"
        non_existent_secrets = temp_dir / "non_existent_secrets.json"

        variables = Variables()
        result = variables.get_variables(
            str(non_existent_variables), str(non_existent_secrets)
        )

        assert result == {}

    def test_missing_secrets_file(self, temp_dir: Path) -> None:
        """Test that missing secrets file doesn't affect variables loading."""
        variables_file = temp_dir / "variables.json"
        variables_file.write_text('{"var1": "value1"}')

        non_existent_secrets = temp_dir / "non_existent_secrets.json"

        variables = Variables()
        result = variables.get_variables(str(variables_file), str(non_existent_secrets))

        assert "var1" in result
        assert result["var1"] == "value1"

    def test_merge_variables_and_secrets(self, temp_dir: Path) -> None:
        """Test that variables and secrets are merged correctly."""
        variables_file = temp_dir / "variables.json"
        variables_file.write_text('{"var1": "value1", "var2": 42}')

        secrets_file = temp_dir / "secrets.json"
        secrets_file.write_text('{"api_key": "secret123"}')

        variables = Variables()
        result = variables.get_variables(str(variables_file), str(secrets_file))

        # Should have both variables and secrets
        assert "var1" in result
        assert "var2" in result
        assert "api_key" in result
