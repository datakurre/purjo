"""Test data factories for purjo tests."""

from datetime import datetime
from datetime import timedelta
from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import ProcessDefinitionDto
from operaton.tasks.types import VariableValueDto
from pathlib import Path
from purjo.runner import Task
from typing import Any
from typing import Dict
from typing import Optional


class VariableValueDtoFactory:
    """Factory for creating VariableValueDto test objects."""

    @staticmethod
    def create(
        value: Any = "test_value",
        type: str = "String",
        value_info: Optional[Dict[str, Any]] = None,
    ) -> VariableValueDto:
        """Create a VariableValueDto."""
        return VariableValueDto(value=value, type=type, valueInfo=value_info)

    @staticmethod
    def create_string(value: str = "test") -> VariableValueDto:
        """Create a String type variable."""
        return VariableValueDto(value=value, type="String")

    @staticmethod
    def create_integer(value: int = 42) -> VariableValueDto:
        """Create an Integer type variable."""
        return VariableValueDto(value=value, type="Integer")

    @staticmethod
    def create_long(value: int = 9223372036854775807) -> VariableValueDto:
        """Create a Long type variable."""
        return VariableValueDto(value=value, type="Long")

    @staticmethod
    def create_double(value: float = 3.14) -> VariableValueDto:
        """Create a Double type variable."""
        return VariableValueDto(value=value, type="Double")

    @staticmethod
    def create_boolean(value: bool = True) -> VariableValueDto:
        """Create a Boolean type variable."""
        return VariableValueDto(value=value, type="Boolean")

    @staticmethod
    def create_json(value: Optional[Dict[str, Any]] = None) -> VariableValueDto:
        """Create a Json type variable."""
        if value is None:
            value = {"key": "value"}
        return VariableValueDto(value=value, type="Json")

    @staticmethod
    def create_date(value: Optional[str] = None) -> VariableValueDto:
        """Create a Date type variable."""
        if value is None:
            value = datetime.now().isoformat()
        return VariableValueDto(value=value, type="Date")

    @staticmethod
    def create_file(
        value: str = "base64content", filename: str = "test.txt"
    ) -> VariableValueDto:
        """Create a File type variable."""
        return VariableValueDto(
            value=value,
            type="File",
            valueInfo={"filename": filename, "mimeType": "text/plain"},
        )


class LockedExternalTaskDtoFactory:
    """Factory for creating LockedExternalTaskDto test objects."""

    @staticmethod
    def create(
        id: str = "test-task-id",
        topic_name: str = "test-topic",
        worker_id: str = "test-worker",
        activity_id: str = "Activity_test",
        process_definition_key: str = "testProcess",
        process_instance_id: str = "test-process-instance",
        variables: Optional[Dict[str, VariableValueDto]] = None,
        **kwargs: Any,
    ) -> LockedExternalTaskDto:
        """Create a LockedExternalTaskDto."""
        now = datetime.now()
        lock_expiration = now + timedelta(hours=1)

        defaults = {
            "activityId": activity_id,
            "activityInstanceId": f"{activity_id}-instance",
            "errorMessage": None,
            "errorDetails": None,
            "executionId": "test-execution",
            "id": id,
            "lockExpirationTime": lock_expiration,
            "processDefinitionId": f"{process_definition_key}:1:test-def-id",
            "processDefinitionKey": process_definition_key,
            "processInstanceId": process_instance_id,
            "retries": 3,
            "suspended": False,
            "workerId": worker_id,
            "topicName": topic_name,
            "tenantId": None,
            "priority": 0,
            "businessKey": None,
            "variables": variables or {},
        }
        defaults.update(kwargs)
        return LockedExternalTaskDto(**defaults)  # type: ignore[arg-type]

    @staticmethod
    def create_with_variables(
        variables: Dict[str, VariableValueDto], **kwargs: Any
    ) -> LockedExternalTaskDto:
        """Create a LockedExternalTaskDto with specific variables."""
        return LockedExternalTaskDtoFactory.create(variables=variables, **kwargs)

    @staticmethod
    def create_failed(
        error_message: str = "Task failed",
        retries: int = 0,
        **kwargs: Any,
    ) -> LockedExternalTaskDto:
        """Create a failed LockedExternalTaskDto."""
        return LockedExternalTaskDtoFactory.create(
            errorMessage=error_message,
            retries=retries,
            **kwargs,
        )


class ProcessDefinitionDtoFactory:
    """Factory for creating ProcessDefinitionDto test objects."""

    @staticmethod
    def create(
        id: str = "test-process-def",
        key: str = "testProcess",
        version: int = 1,
        **kwargs: Any,
    ) -> ProcessDefinitionDto:
        """Create a ProcessDefinitionDto."""
        defaults = {
            "id": id,
            "key": key,
            "category": "http://bpmn.io/schema/bpmn",
            "description": None,
            "name": "Test Process",
            "version": version,
            "resource": f"{key}.bpmn",
            "deploymentId": "test-deployment",
            "diagram": None,
            "suspended": False,
            "tenantId": None,
            "versionTag": None,
            "historyTimeToLive": None,
            "startableInTasklist": True,
        }
        defaults.update(kwargs)
        return ProcessDefinitionDto(**defaults)  # type: ignore[arg-type]


class TaskFactory:
    """Factory for creating Task test objects."""

    @staticmethod
    def create(
        id: str = "test.robot",
        on_fail: str = "fail",
        process_variables: bool = True,
        secrets_profile: Optional[str] = None,
        **kwargs: Any,
    ) -> Task:
        """Create a Task object."""
        defaults = {
            "name": id,  # Task model uses 'name' not 'id'
            "on_fail": on_fail,
            "process_variables": process_variables,
        }
        defaults.update(kwargs)
        return Task(**defaults)  # type: ignore[arg-type]

    @staticmethod
    def create_robot(id: str = "test.robot", **kwargs: Any) -> Task:
        """Create a Robot Framework task."""
        return TaskFactory.create(id=id, **kwargs)

    @staticmethod
    def create_python(id: str = "module.function", **kwargs: Any) -> Task:
        """Create a Python task."""
        return TaskFactory.create(id=id, **kwargs)


class FileFactory:
    """Factory for creating test files and directories."""

    @staticmethod
    def create_robot_file(path: Path, content: Optional[str] = None) -> Path:
        """Create a Robot Framework file."""
        if content is None:
            content = """*** Test Cases ***
Example Test
    Log    Hello World
    Set Task Variable    ${result}    success
"""
        path.write_text(content)
        return path

    @staticmethod
    def create_pyproject_toml(
        path: Path,
        name: str = "test-project",
        tasks: Optional[list[str]] = None,
    ) -> Path:
        """Create a pyproject.toml file."""
        if tasks is None:
            tasks = ["test.robot"]

        content = f"""[project]
name = "{name}"
version = "0.1.0"
dependencies = ["robotframework"]

[tool.purjo]
tasks = {tasks}
"""
        path.write_text(content)
        return path

    @staticmethod
    def create_secrets_json(
        path: Path, secrets: Optional[Dict[str, str]] = None
    ) -> Path:
        """Create a secrets.json file."""
        import json

        if secrets is None:
            secrets = {
                "username": "testuser",
                "password": "testpass",
            }
        path.write_text(json.dumps(secrets, indent=2))
        return path

    @staticmethod
    def create_robot_output(path: Path, passed: bool = True, message: str = "") -> Path:
        """Create a Robot Framework output.xml file."""
        status = "PASS" if passed else "FAIL"
        message_tag = f"        {message}\n" if message and not passed else ""

        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 7.1" generated="2024-01-01T10:00:00.000000" rpa="false">
  <suite id="s1" name="Test Suite" source="/tmp/test.robot">
    <test id="s1-t1" name="Test Case">
      <status status="{status}" start="2024-01-01T10:00:00.000000" elapsed="0.123">
{message_tag}      </status>
    </test>
    <status status="{status}" start="2024-01-01T10:00:00.000000" elapsed="1.234"/>
  </suite>
  <statistics>
    <total>
      <stat pass="{'1' if passed else '0'}" fail="{'0' if passed else '1'}" skip="0">All Tests</stat>
    </total>
  </statistics>
</robot>"""
        path.write_text(content)
        return path
