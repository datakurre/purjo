"""Shared pytest fixtures for purjo tests."""

from datetime import datetime
from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import VariableValueDto
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from typing import AsyncGenerator
from typing import Dict
from typing import Generator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
import asyncio
import json
import pytest


@pytest.fixture
def mock_semaphore() -> asyncio.Semaphore:
    """Mock asyncio Semaphore for concurrency tests."""
    return asyncio.Semaphore(1)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Temporary directory context manager."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_http_session() -> AsyncMock:
    """Mock aiohttp ClientSession."""
    session = AsyncMock()
    session.get = AsyncMock()
    session.post = AsyncMock()
    session.put = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_operaton_session() -> AsyncMock:
    """Mock operaton_session context manager."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def sample_locked_task() -> LockedExternalTaskDto:
    """Sample LockedExternalTaskDto fixture."""
    return LockedExternalTaskDto(
        activityId="Activity_test",
        activityInstanceId="test-activity-instance",
        errorMessage=None,
        errorDetails=None,
        executionId="test-execution",
        id="test-task-id",
        lockExpirationTime=datetime.now(),
        processDefinitionId="test-process-def",
        processDefinitionKey="testProcess",
        processInstanceId="test-process-instance",
        retries=3,
        suspended=False,
        workerId="test-worker",
        topicName="test-topic",
        tenantId=None,
        priority=0,
        businessKey=None,
        variables={"input": VariableValueDto(value="test", type="String")},
    )


@pytest.fixture
def sample_variable_value_dto() -> VariableValueDto:
    """Sample VariableValueDto fixture."""
    return VariableValueDto(value="test_value", type="String")


@pytest.fixture
def sample_process_definition() -> Dict[str, Any]:
    """Sample ProcessDefinitionDto data."""
    return {
        "id": "test-process-def",
        "key": "testProcess",
        "category": "http://bpmn.io/schema/bpmn",
        "description": None,
        "name": "Test Process",
        "version": 1,
        "resource": "test.bpmn",
        "deploymentId": "test-deployment",
        "diagram": None,
        "suspended": False,
        "tenantId": None,
        "versionTag": None,
        "historyTimeToLive": None,
        "startableInTasklist": True,
    }


@pytest.fixture
def sample_variables() -> Dict[str, VariableValueDto]:
    """Sample variables dictionary."""
    return {
        "string_var": VariableValueDto(value="hello", type="String"),
        "integer_var": VariableValueDto(value=42, type="Integer"),
        "boolean_var": VariableValueDto(value=True, type="Boolean"),
        "json_var": VariableValueDto(value={"key": "value"}, type="Json"),
    }


@pytest.fixture
def mock_subprocess_run() -> Mock:
    """Mock subprocess.run for command execution tests."""
    mock = Mock()
    mock.return_value = Mock(
        returncode=0,
        stdout="test output",
        stderr="",
    )
    return mock


@pytest.fixture
def sample_robot_output_xml(temp_dir: Path) -> Path:
    """Create a sample Robot Framework output.xml file."""
    output_xml = temp_dir / "output.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 7.1" generated="2024-01-01T10:00:00.000000" rpa="false">
  <suite id="s1" name="Test Suite" source="/tmp/test.robot">
    <status status="PASS" start="2024-01-01T10:00:00.000000" elapsed="1.234"/>
  </suite>
  <statistics>
    <total>
      <stat pass="1" fail="0" skip="0">All Tests</stat>
    </total>
  </statistics>
</robot>"""
    output_xml.write_text(xml_content)
    return output_xml


@pytest.fixture
def sample_robot_failed_xml(temp_dir: Path) -> Path:
    """Create a sample failed Robot Framework output.xml file."""
    output_xml = temp_dir / "output.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<robot generator="Robot 7.1" generated="2024-01-01T10:00:00.000000" rpa="false">
  <suite id="s1" name="Test Suite" source="/tmp/test.robot">
    <test id="s1-t1" name="Test Case">
      <status status="FAIL" start="2024-01-01T10:00:00.000000" elapsed="0.123">
        Test failed: Expected value did not match
      </status>
    </test>
    <status status="FAIL" start="2024-01-01T10:00:00.000000" elapsed="1.234"/>
  </suite>
  <statistics>
    <total>
      <stat pass="0" fail="1" skip="0">All Tests</stat>
    </total>
  </statistics>
</robot>"""
    output_xml.write_text(xml_content)
    return output_xml


@pytest.fixture
def sample_secrets_file(temp_dir: Path) -> Path:
    """Create a sample secrets.json file."""
    secrets_file = temp_dir / "secrets.json"
    secrets = {
        "username": "testuser",
        "password": "testpass",
        "api_key": "test-api-key-123",
    }
    secrets_file.write_text(json.dumps(secrets))
    return secrets_file


@pytest.fixture
def mock_hvac_client() -> Mock:
    """Mock hvac.Client for Vault testing."""
    client = Mock()
    client.secrets.kv.v2.read_secret_version.return_value = {
        "data": {"data": {"username": "vault-user", "password": "vault-pass"}}
    }
    return client


@pytest.fixture
def sample_pyproject_toml(temp_dir: Path) -> Path:
    """Create a sample pyproject.toml file."""
    pyproject = temp_dir / "pyproject.toml"
    content = """[project]
name = "test-project"
version = "0.1.0"
dependencies = ["robotframework"]

[tool.purjo]
tasks = ["test.robot"]
"""
    pyproject.write_text(content)
    return pyproject


@pytest.fixture
def sample_robot_file(temp_dir: Path) -> Path:
    """Create a sample Robot Framework file."""
    robot_file = temp_dir / "test.robot"
    content = """*** Test Cases ***
Test Example
    Log    Hello World
    Set Task Variable    ${result}    success
"""
    robot_file.write_text(content)
    return robot_file
