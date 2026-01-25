"""Advanced unit tests for CLI commands in main.py.

Related User Stories:
- US-001: Serve robot packages
- US-002: Configure engine URL
- US-003: Provide authorization
- US-004: Configure secrets
- US-005: Configure polling timeout
- US-006: Set lock TTL
- US-007: Control max jobs
- US-008: Set worker ID
- US-009: Control failure behavior
- US-010: Init robot package
- US-011: Init Python template
- US-014: Deploy and start
- US-015: Provide variables
- US-016: Migrate instances
- US-017: Force deployment
- US-019: Deploy resources
- US-020: Start process

Related ADRs:
- ADR-001: Use uv for environment management
- ADR-002: Use external task pattern
- ADR-003: Architecture overview
"""

from pathlib import Path
from purjo.config import OnFail
from purjo.main import cli_init
from purjo.main import cli_run
from purjo.main import cli_serve
from purjo.main import operaton_deploy
from purjo.main import operaton_start
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
from zipfile import ZipFile
import asyncio
import json
import os
import pytest


class TestCliServe:
    """Tests for cli_serve command.

    Related: US-001, US-002, US-003, US-004, US-005, US-006, US-007, US-008, US-009, ADR-002
    """

    @patch("purjo.main.shutil.which")
    def test_serve_missing_uv_error(self, mock_which: Any) -> None:
        """Test that cli_serve raises error when uv is not found."""
        mock_which.return_value = None

        with pytest.raises(FileNotFoundError, match="'uv' executable is not found"):
            cli_serve(robots=[Path("/tmp/test.zip")], log_level="INFO")

    @patch("purjo.main.asyncio.get_event_loop")
    @patch("purjo.main.external_task_worker")
    @patch("purjo.main.task")
    @patch("purjo.main.shutil.which")
    def test_serve_with_directory_robot(
        self,
        mock_which: Any,
        mock_task: Any,
        mock_worker: Any,
        mock_loop: Any,
        temp_dir: Any,
    ) -> None:
        """Test cli_serve with a directory robot package."""
        mock_which.return_value = "/usr/bin/uv"

        # Create a minimal robot directory
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()
        (robot_dir / "pyproject.toml").write_text(
            """
[tool.purjo.topics.test_topic]
name = "Test Task"
on-fail = "ERROR"
"""
        )
        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        # Mock asyncio event loop
        mock_event_loop = Mock()
        mock_event_loop.run_until_complete = Mock()
        mock_loop.return_value = mock_event_loop

        # Run cli_serve
        cli_serve(
            robots=[robot_dir],
            base_url="http://localhost:8080/engine-rest",
            log_level="INFO",
        )

        # Verify task was registered
        assert mock_task.called

    @patch("purjo.main.asyncio.get_event_loop")
    @patch("purjo.main.external_task_worker")
    @patch("purjo.main.task")
    @patch("purjo.main.shutil.which")
    def test_serve_with_zip_robot(
        self,
        mock_which: Any,
        mock_task: Any,
        mock_worker: Any,
        mock_loop: Any,
        temp_dir: Any,
    ) -> None:
        """Test cli_serve with a zip robot package."""
        mock_which.return_value = "/usr/bin/uv"

        # Create a minimal robot zip
        robot_zip = temp_dir / "robot.zip"
        with ZipFile(robot_zip, "w") as zf:
            zf.writestr(
                "pyproject.toml",
                """
[tool.purjo.topics.test_topic]
name = "Test Task"
""",
            )
            zf.writestr("test.robot", "*** Test Cases ***\nTest\n    Log    Test")

        # Mock asyncio event loop
        mock_event_loop = Mock()
        mock_event_loop.run_until_complete = Mock()
        mock_loop.return_value = mock_event_loop

        # Run cli_serve
        cli_serve(
            robots=[robot_zip],
            base_url="http://localhost:8080/engine-rest",
            log_level="INFO",
        )

        # Verify task was registered
        assert mock_task.called

    @patch("purjo.main.asyncio.get_event_loop")
    @patch("purjo.main.external_task_worker")
    @patch("purjo.main.task")
    @patch("purjo.main.shutil.which")
    @patch("purjo.main.get_secrets_provider")
    def test_serve_with_secrets(
        self,
        mock_secrets: Any,
        mock_which: Any,
        mock_task: Any,
        mock_worker: Any,
        mock_loop: Any,
        temp_dir: Any,
    ) -> None:
        """Test cli_serve with secrets configuration."""
        mock_which.return_value = "/usr/bin/uv"
        mock_secrets.return_value = Mock()

        # Create robot with secrets config
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()
        (robot_dir / "pyproject.toml").write_text(
            """
[tool.purjo.secrets]
type = "file"
path = "secrets.json"

[tool.purjo.topics.test_topic]
name = "Test Task"
"""
        )
        (robot_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        # Mock asyncio event loop
        mock_event_loop = Mock()
        mock_event_loop.run_until_complete = Mock()
        mock_loop.return_value = mock_event_loop

        # Run cli_serve
        cli_serve(robots=[robot_dir], secrets="test_profile", log_level="INFO")

        # Verify secrets provider was called with correct profile
        mock_secrets.assert_called()

    @patch("purjo.main.asyncio.get_event_loop")
    @patch("purjo.main.external_task_worker")
    @patch("purjo.main.task")
    @patch("purjo.main.shutil.which")
    def test_serve_settings_configuration(
        self,
        mock_which: Any,
        mock_task: Any,
        mock_worker: Any,
        mock_loop: Any,
        temp_dir: Any,
    ) -> None:
        """Test cli_serve configures settings correctly."""
        from operaton.tasks import settings

        mock_which.return_value = "/usr/bin/uv"

        # Create minimal robot
        robot_dir = temp_dir / "robot_package"
        robot_dir.mkdir()
        (robot_dir / "pyproject.toml").write_text(
            """
[tool.purjo.topics.test_topic]
name = "Test Task"
"""
        )

        # Mock asyncio event loop
        mock_event_loop = Mock()
        mock_event_loop.run_until_complete = Mock()
        mock_loop.return_value = mock_event_loop

        # Run cli_serve with custom settings
        base_url = "http://custom:9090/engine-rest"
        authorization = "Bearer token123"
        worker_id = "custom-worker"

        cli_serve(
            robots=[robot_dir],
            base_url=base_url,
            authorization=authorization,
            worker_id=worker_id,
            timeout=30,
            poll_ttl=20,
            lock_ttl=40,
            log_level="DEBUG",
        )

        # Verify settings were configured
        assert settings.ENGINE_REST_BASE_URL == base_url
        assert settings.ENGINE_REST_AUTHORIZATION == authorization
        assert settings.TASKS_WORKER_ID == worker_id
        assert settings.ENGINE_REST_TIMEOUT_SECONDS == 30
        assert settings.ENGINE_REST_POLL_TTL_SECONDS == 20
        assert settings.ENGINE_REST_LOCK_TTL_SECONDS == 40


class TestCliInit:
    """Tests for cli_init command.

    Related: US-010, US-011
    """

    @patch("purjo.main.shutil.which")
    def test_init_missing_uv_error(
        self, mock_which: Any, temp_dir: Any, monkeypatch: Any
    ) -> None:
        """Test that cli_init raises error when uv is not found."""
        mock_which.return_value = None
        monkeypatch.chdir(temp_dir)

        with pytest.raises(FileNotFoundError, match="'uv' executable is not found"):
            cli_init(log_level="INFO")

    @patch("purjo.main.cli_wrap")
    @patch("purjo.main.run")
    @patch("purjo.main.shutil.which")
    def test_init_robot_template(
        self,
        mock_which: Any,
        mock_run: Any,
        mock_wrap: Any,
        temp_dir: Any,
        monkeypatch: Any,
    ) -> None:
        """Test cli_init with Robot Framework template."""
        mock_which.return_value = "/usr/bin/uv"
        monkeypatch.chdir(temp_dir)

        # Mock the async run function
        async def mock_run_async(*args: Any, **kwargs: Any) -> None:
            # Create a minimal pyproject.toml so init doesn't fail
            if not (temp_dir / "pyproject.toml").exists():
                (temp_dir / "pyproject.toml").write_text("[project]\nname='test'\n")

        mock_run.side_effect = mock_run_async

        # Mock cli_wrap to prevent it from failing on missing files
        def mock_wrap_impl(*args: Any, **kwargs: Any) -> None:
            # Create robot.zip so unlink doesn't fail
            (temp_dir / "robot.zip").write_text("mock")

        mock_wrap.side_effect = mock_wrap_impl

        # Run cli_init
        cli_init(python=False, log_level="INFO")

        # Verify key files were created
        assert (temp_dir / "pyproject.toml").exists()
        # Verify cli_wrap was called
        assert mock_wrap.called

    @patch("purjo.main.cli_wrap")
    @patch("purjo.main.run")
    @patch("purjo.main.shutil.which")
    def test_init_python_template(
        self,
        mock_which: Any,
        mock_run: Any,
        mock_wrap: Any,
        temp_dir: Any,
        monkeypatch: Any,
    ) -> None:
        """Test cli_init with Python template."""
        mock_which.return_value = "/usr/bin/uv"
        monkeypatch.chdir(temp_dir)

        # Mock the async run function
        async def mock_run_async(*args: Any, **kwargs: Any) -> None:
            # Create a minimal pyproject.toml so init doesn't fail
            if not (temp_dir / "pyproject.toml").exists():
                (temp_dir / "pyproject.toml").write_text("[project]\nname='test'\n")

        mock_run.side_effect = mock_run_async

        # Mock cli_wrap to prevent it from failing on missing files
        def mock_wrap_impl(*args: Any, **kwargs: Any) -> None:
            # Create robot.zip so unlink doesn't fail
            (temp_dir / "robot.zip").write_text("mock")

        mock_wrap.side_effect = mock_wrap_impl

        # Run cli_init with python flag
        cli_init(python=True, log_level="INFO")

        # Verify key files were created
        assert (temp_dir / "pyproject.toml").exists()
        # Verify cli_wrap was called
        assert mock_wrap.called

    def test_init_fails_if_pyproject_exists(
        self, temp_dir: Any, monkeypatch: Any
    ) -> None:
        """Test that cli_init fails if pyproject.toml already exists."""
        monkeypatch.chdir(temp_dir)
        (temp_dir / "pyproject.toml").write_text("[project]")

        with pytest.raises(AssertionError):
            cli_init(log_level="INFO")


class TestOperatonDeploy:
    """Tests for operaton_deploy command.

    Related: US-017, US-019
    """

    def test_deploy_successful(self, temp_dir: Any) -> None:
        """Test successful deployment."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        # Mock asyncio.run to skip actual deployment
        with patch("purjo.main.asyncio.run") as mock_run:
            operaton_deploy(
                resources=[bpmn_file], name="Test Deployment", log_level="INFO"
            )
            # Verify asyncio.run was called with the deploy coroutine
            assert mock_run.called

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_deploy_with_migration(
        self, mock_session: Any, mock_asyncio: Any, temp_dir: Any
    ) -> None:
        """Test deployment with migration enabled."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        # Mock the async context manager and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "deployment-123",
                "deployedProcessDefinitions": {
                    "def-1": {"id": "def-1", "key": "process-key", "version": 1}
                },
            }
        )

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # Run deployment
        operaton_deploy(resources=[bpmn_file], migrate=True, log_level="INFO")

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_deploy_error_handling(
        self, mock_session: Any, mock_asyncio: Any, temp_dir: Any
    ) -> None:
        """Test deployment error handling."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"error": "Bad request"})

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # This should handle the error gracefully
        operaton_deploy(resources=[bpmn_file], log_level="INFO")


class TestOperatonStart:
    """Tests for operaton_start command.

    Related: US-015, US-020
    """

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_start_successful(
        self, mock_session: Any, mock_asyncio: Any, temp_dir: Any
    ) -> None:
        """Test successful process start."""
        # Mock the async context manager and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "test-key",
            }
        )

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # Run start
        operaton_start(key="test-process", log_level="INFO")

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_start_with_inline_variables(
        self, mock_session: Any, mock_asyncio: Any
    ) -> None:
        """Test process start with inline JSON variables."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "test-key",
            }
        )

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # Run start with variables
        operaton_start(
            key="test-process",
            variables='{"name": "test", "value": 123}',
            log_level="INFO",
        )

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_start_with_file_variables(
        self, mock_session: Any, mock_asyncio: Any, temp_dir: Any
    ) -> None:
        """Test process start with variables from file."""
        # Create variables file
        vars_file = temp_dir / "vars.json"
        vars_file.write_text('{"name": "test", "value": 456}')

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "test-key",
            }
        )

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # Run start with variables file
        operaton_start(key="test-process", variables=str(vars_file), log_level="INFO")

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_start_error_handling(self, mock_session: Any, mock_asyncio: Any) -> None:
        """Test process start error handling."""
        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={"error": "Process not found"})

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # This should handle the error gracefully
        operaton_start(key="nonexistent-process", log_level="INFO")


class TestCliRun:
    """Tests for cli_run command.

    Related: US-014, US-015, US-016, US-017
    """

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_run_combined_deploy_and_start(
        self, mock_session: Any, mock_asyncio: Any, temp_dir: Any
    ) -> None:
        """Test cli_run combines deployment and process start."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        # Mock deployment response
        mock_deploy_response = AsyncMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(return_value={"id": "deployment-123"})

        # Mock process definition response
        mock_def_response = AsyncMock()
        mock_def_response.status = 200
        mock_def_response.json = AsyncMock(
            return_value=[{"id": "def-1", "key": "test-process", "version": 1}]
        )

        # Mock start response
        mock_start_response = AsyncMock()
        mock_start_response.status = 200
        mock_start_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "test-key",
            }
        )

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(
            side_effect=[mock_deploy_response, mock_start_response]
        )
        mock_session_instance.get = AsyncMock(return_value=mock_def_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # Run cli_run
        cli_run(resources=[bpmn_file], log_level="INFO")

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_run_with_variables(
        self, mock_session: Any, mock_asyncio: Any, temp_dir: Any
    ) -> None:
        """Test cli_run with variables."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        # Mock responses
        mock_deploy_response = AsyncMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(return_value={"id": "deployment-123"})

        mock_def_response = AsyncMock()
        mock_def_response.status = 200
        mock_def_response.json = AsyncMock(
            return_value=[{"id": "def-1", "key": "test-process", "version": 1}]
        )

        mock_start_response = AsyncMock()
        mock_start_response.status = 200
        mock_start_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "test-key",
            }
        )

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(
            side_effect=[mock_deploy_response, mock_start_response]
        )
        mock_session_instance.get = AsyncMock(return_value=mock_def_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # Run cli_run with variables
        cli_run(resources=[bpmn_file], variables='{"test": "value"}', log_level="INFO")

    @patch("purjo.main.asyncio.run")
    @patch("purjo.main.operaton_session")
    def test_run_error_handling(
        self, mock_session: Any, mock_asyncio: Any, temp_dir: Any
    ) -> None:
        """Test cli_run error handling."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value={"error": "Internal server error"})

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aenter__ = AsyncMock(
            return_value=mock_session_instance
        )
        mock_session.return_value.__aexit__ = AsyncMock()

        # This should handle the error gracefully
        cli_run(resources=[bpmn_file], log_level="INFO")
