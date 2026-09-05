"""Tests for extracted async functions in main.py.

These tests cover the refactored async functions that were extracted
for better testability.

Related User Stories:
- US-014: Deploy and start
- US-015: Provide variables
- US-016: Migrate instances
- US-017: Force deployment
- US-019: Deploy resources
- US-020: Start process

Related ADRs:
- ADR-003: Architecture overview
"""

from contextlib import asynccontextmanager
from purjo.main import deploy_and_start
from purjo.main import deploy_resources
from purjo.main import start_process
from typing import Any
from typing import AsyncIterator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
import pytest


@asynccontextmanager
async def mock_session_context(
    mock_session_instance: MagicMock,
) -> AsyncIterator[MagicMock]:
    """Helper to create async context manager for session mocking."""
    yield mock_session_instance


async def _delegate_to_session(
    http: Any, method: str, url: str, authorization: Any = None, **kwargs: Any
) -> Any:
    """Stand in for request_with_auth_retry, delegating to the mocked session.

    request_with_auth_retry moved authorization from session construction to
    a per-request middleware in operaton-tasks>=1.0b3, so purjo's code now
    calls it instead of session.post/get directly. Tests still mock
    session.post/get for readability; this delegate bridges the two so those
    mocks keep working without duplicating response wiring per test.
    """
    return await getattr(http, method.lower())(url, **kwargs)


class TestDeployResources:
    """Tests for deploy_resources async function.

    Related: US-017, US-019
    """

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_successful(self, mock_session: Any, temp_dir: Any) -> None:
        """Test successful deployment."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "deployment-123",
                "deployedProcessDefinitions": {
                    "def-1": {
                        "id": "def-1",
                        "key": "process-key",
                        "version": 1,
                        "name": "Test Process",
                        "resource": "test.bpmn",
                        "deploymentId": "deployment-123",
                    }
                },
            }
        )

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_resources(
            resources=[bpmn_file],
            name="Test Deployment",
            force=False,
            migrate=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_error_status(self, mock_session: Any, temp_dir: Any) -> None:
        """Test deployment with error response status."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={"error": "Bad request"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_resources(
            resources=[bpmn_file],
            name="Test",
            force=False,
            migrate=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_validation_error(
        self, mock_session: Any, temp_dir: Any
    ) -> None:
        """Test deployment with invalid response that causes validation error."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"invalid": "response"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_resources(
            resources=[bpmn_file],
            name="Test",
            force=False,
            migrate=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.migrate_all")
    @patch("purjo.main.operaton_session")
    async def test_deploy_with_migration(
        self, mock_session: Any, mock_migrate: Any, temp_dir: Any
    ) -> None:
        """Test deployment with migration enabled."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "deployment-123",
                "deployedProcessDefinitions": {
                    "def-1": {
                        "id": "def-1",
                        "key": "process-key",
                        "version": 1,
                        "name": "Test Process",
                        "resource": "test.bpmn",
                        "deploymentId": "deployment-123",
                    }
                },
            }
        )

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)
        mock_migrate.return_value = None

        await deploy_resources(
            resources=[bpmn_file],
            name="Test Deployment",
            force=False,
            migrate=True,
            base_url="http://localhost:8080/engine-rest",
        )

        assert mock_migrate.called


class TestStartProcess:
    """Tests for start_process async function.

    Related: US-015, US-020
    """

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_start_successful(self, mock_session: Any) -> None:
        """Test successful process start."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "test-key",
            }
        )

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await start_process(
            key="test-process",
            variables=None,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_start_with_variables(self, mock_session: Any) -> None:
        """Test process start with inline JSON variables."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "custom-key",
            }
        )

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await start_process(
            key="test-process",
            variables='{"name": "test", "businessKey": "custom-key"}',
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_start_error_status(self, mock_session: Any) -> None:
        """Test process start with error response."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={"error": "Process not found"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await start_process(
            key="nonexistent-process",
            variables=None,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_start_validation_error(self, mock_session: Any) -> None:
        """Test process start with invalid response that causes validation error."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"invalid": "response"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await start_process(
            key="test-process",
            variables=None,
            base_url="http://localhost:8080/engine-rest",
        )


class TestDeployAndStart:
    """Tests for deploy_and_start async function.

    Related: US-014, US-015, US-016, US-017
    """

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.migrate_all")
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_successful(
        self, mock_session: Any, mock_migrate: Any, temp_dir: Any
    ) -> None:
        """Test successful deploy-and-start."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_deploy_response = MagicMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(
            return_value={"id": "deployment-123", "name": "Test"}
        )

        mock_defs_response = MagicMock()
        mock_defs_response.status = 200
        mock_defs_response.json = AsyncMock(
            return_value=[
                {
                    "id": "def-1",
                    "key": "test-process",
                    "version": 1,
                    "name": "Test Process",
                    "resource": "test.bpmn",
                    "deploymentId": "deployment-123",
                }
            ]
        )

        mock_start_response = MagicMock()
        mock_start_response.status = 200
        mock_start_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "test-key",
            }
        )

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(
            side_effect=[mock_deploy_response, mock_start_response]
        )
        mock_session_instance.get = AsyncMock(return_value=mock_defs_response)
        mock_session.return_value = mock_session_context(mock_session_instance)
        mock_migrate.return_value = None

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables=None,
            migrate=True,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_deployment_error(
        self, mock_session: Any, temp_dir: Any
    ) -> None:
        """Test deploy_and_start with deployment error."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_deploy_response = MagicMock()
        mock_deploy_response.status = 400
        mock_deploy_response.json = AsyncMock(return_value={"error": "Bad request"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_deploy_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables=None,
            migrate=False,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_definitions_error(
        self, mock_session: Any, temp_dir: Any
    ) -> None:
        """Test deploy_and_start with definitions fetch error."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_deploy_response = MagicMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(
            return_value={"id": "deployment-123", "name": "Test"}
        )

        mock_defs_response = MagicMock()
        mock_defs_response.status = 500
        mock_defs_response.json = AsyncMock(return_value={"error": "Server error"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_deploy_response)
        mock_session_instance.get = AsyncMock(return_value=mock_defs_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables=None,
            migrate=False,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_definitions_validation_error(
        self, mock_session: Any, temp_dir: Any
    ) -> None:
        """Test deploy_and_start with definitions validation error."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_deploy_response = MagicMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(
            return_value={"id": "deployment-123", "name": "Test"}
        )

        mock_defs_response = MagicMock()
        mock_defs_response.status = 200
        mock_defs_response.json = AsyncMock(return_value={"invalid": "not a list"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_deploy_response)
        mock_session_instance.get = AsyncMock(return_value=mock_defs_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables=None,
            migrate=False,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.migrate_all")
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_start_error(
        self, mock_session: Any, mock_migrate: Any, temp_dir: Any
    ) -> None:
        """Test deploy_and_start with start process error."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_deploy_response = MagicMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(
            return_value={"id": "deployment-123", "name": "Test"}
        )

        mock_defs_response = MagicMock()
        mock_defs_response.status = 200
        mock_defs_response.json = AsyncMock(
            return_value=[
                {
                    "id": "def-1",
                    "key": "test-process",
                    "version": 1,
                    "name": "Test Process",
                    "resource": "test.bpmn",
                    "deploymentId": "deployment-123",
                }
            ]
        )

        mock_start_response = MagicMock()
        mock_start_response.status = 500
        mock_start_response.json = AsyncMock(return_value={"error": "Start failed"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(
            side_effect=[mock_deploy_response, mock_start_response]
        )
        mock_session_instance.get = AsyncMock(return_value=mock_defs_response)
        mock_session.return_value = mock_session_context(mock_session_instance)
        mock_migrate.return_value = None

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables=None,
            migrate=True,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.migrate_all")
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_start_validation_error(
        self, mock_session: Any, mock_migrate: Any, temp_dir: Any
    ) -> None:
        """Test deploy_and_start with start validation error."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_deploy_response = MagicMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(
            return_value={"id": "deployment-123", "name": "Test"}
        )

        mock_defs_response = MagicMock()
        mock_defs_response.status = 200
        mock_defs_response.json = AsyncMock(
            return_value=[
                {
                    "id": "def-1",
                    "key": "test-process",
                    "version": 1,
                    "name": "Test Process",
                    "resource": "test.bpmn",
                    "deploymentId": "deployment-123",
                }
            ]
        )

        mock_start_response = MagicMock()
        mock_start_response.status = 200
        mock_start_response.json = AsyncMock(return_value={"invalid": "response"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(
            side_effect=[mock_deploy_response, mock_start_response]
        )
        mock_session_instance.get = AsyncMock(return_value=mock_defs_response)
        mock_session.return_value = mock_session_context(mock_session_instance)
        mock_migrate.return_value = None

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables=None,
            migrate=True,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.migrate_all")
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_with_variables(
        self, mock_session: Any, mock_migrate: Any, temp_dir: Any
    ) -> None:
        """Test deploy_and_start with variables."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_deploy_response = MagicMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(
            return_value={"id": "deployment-123", "name": "Test"}
        )

        mock_defs_response = MagicMock()
        mock_defs_response.status = 200
        mock_defs_response.json = AsyncMock(
            return_value=[
                {
                    "id": "def-1",
                    "key": "test-process",
                    "version": 1,
                    "name": "Test Process",
                    "resource": "test.bpmn",
                    "deploymentId": "deployment-123",
                }
            ]
        )

        mock_start_response = MagicMock()
        mock_start_response.status = 200
        mock_start_response.json = AsyncMock(
            return_value={
                "id": "instance-123",
                "definitionId": "def-1",
                "businessKey": "custom-key",
            }
        )

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(
            side_effect=[mock_deploy_response, mock_start_response]
        )
        mock_session_instance.get = AsyncMock(return_value=mock_defs_response)
        mock_session.return_value = mock_session_context(mock_session_instance)
        mock_migrate.return_value = None

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables='{"name": "test", "businessKey": "custom-key"}',
            migrate=True,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )


class TestEngineResponseValidationErrors:
    """Tests for malformed engine responses.

    The engine may answer 2xx with a payload that does not match the expected
    DTO. Each of these paths prints the raw payload and returns instead of
    raising, so the CLI degrades gracefully rather than tracebacking.

    Related: US-014, US-019, US-020
    """

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_resources_invalid_payload(
        self, mock_session: Any, temp_dir: Any, capsys: Any
    ) -> None:
        """Test deploy_resources with a payload failing DTO validation."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"id": 123, "deployedProcessDefinitions": "not-a-dict"}
        )

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_resources(
            resources=[bpmn_file],
            name="Test Deployment",
            force=False,
            migrate=False,
            base_url="http://localhost:8080/engine-rest",
        )

        # The raw payload is printed and no deployment result is reported
        out = capsys.readouterr().out
        assert "not-a-dict" in out
        assert "Deployed:" not in out

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_start_process_invalid_payload(
        self, mock_session: Any, capsys: Any
    ) -> None:
        """Test start_process with a payload failing DTO validation."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"id": 123, "links": "not-a-list"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await start_process(
            key="process-key",
            variables=None,
            base_url="http://localhost:8080/engine-rest",
        )

        out = capsys.readouterr().out
        assert "not-a-list" in out
        assert "Started:" not in out

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_invalid_deployment_payload(
        self, mock_session: Any, temp_dir: Any, capsys: Any
    ) -> None:
        """Test deploy_and_start with a deployment payload failing validation."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"id": 123, "links": "not-a-list"})

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables=None,
            migrate=False,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )

        out = capsys.readouterr().out
        assert "not-a-list" in out
        assert "Started:" not in out

    @pytest.mark.asyncio
    @patch(  # type: ignore[untyped-decorator]
        "purjo.main.request_with_auth_retry", new=_delegate_to_session
    )
    @patch("purjo.main.operaton_session")
    async def test_deploy_and_start_invalid_instance_payload(
        self, mock_session: Any, temp_dir: Any, capsys: Any
    ) -> None:
        """Test deploy_and_start with a start payload failing validation."""
        bpmn_file = temp_dir / "test.bpmn"
        bpmn_file.write_text("<bpmn>content</bpmn>")

        mock_deploy_response = MagicMock()
        mock_deploy_response.status = 200
        mock_deploy_response.json = AsyncMock(return_value={"id": "deployment-123"})

        mock_defs_response = MagicMock()
        mock_defs_response.status = 200
        mock_defs_response.json = AsyncMock(
            return_value=[
                {
                    "id": "def-1",
                    "key": "process-key",
                    "version": 1,
                    "deploymentId": "deployment-123",
                }
            ]
        )

        mock_start_response = MagicMock()
        mock_start_response.status = 200
        mock_start_response.json = AsyncMock(
            return_value={"id": 123, "links": "not-a-list"}
        )

        mock_session_instance = MagicMock()
        mock_session_instance.post = AsyncMock(
            side_effect=[mock_deploy_response, mock_start_response]
        )
        mock_session_instance.get = AsyncMock(return_value=mock_defs_response)
        mock_session.return_value = mock_session_context(mock_session_instance)

        await deploy_and_start(
            resources=[bpmn_file],
            name="Test",
            variables=None,
            migrate=False,
            force=False,
            base_url="http://localhost:8080/engine-rest",
        )

        out = capsys.readouterr().out
        assert "not-a-list" in out
        assert "Started:" not in out
