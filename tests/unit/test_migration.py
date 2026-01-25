"""Unit tests for migration.py module."""

from datetime import datetime
from operaton.tasks.types import ProcessDefinitionDto
from operaton.tasks.types import ProcessInstanceDto
from typing import Any
from typing import Dict
from typing import List
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
import pytest


class TestMigrate:
    """Tests for migrate function."""

    @pytest.mark.asyncio
    async def test_no_instances_to_migrate(self) -> None:
        """Test migration when there are no instances to migrate."""
        from purjo.migration import migrate

        target = ProcessDefinitionDto(
            id="target-def-id",
            key="process-key",
            name="Test Process",
            version=2,
        )

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[])

        with patch("purjo.migration.operaton_session") as mock_session:
            session = AsyncMock()
            session.get = AsyncMock(return_value=mock_response)
            session.post = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            await migrate(target, verbose=False)

            session.get.assert_called_once()
            session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_migrate_single_instance(self) -> None:
        """Test migrating a single process instance."""
        from purjo.migration import migrate

        target = ProcessDefinitionDto(
            id="target-def-id",
            key="process-key",
            name="Test Process",
            version=2,
        )

        instances = [
            {
                "id": "instance-1",
                "definitionId": "old-def-id",
                "businessKey": "bk-1",
            }
        ]

        migration_plan = {
            "sourceProcessDefinitionId": "old-def-id",
            "targetProcessDefinitionId": "target-def-id",
            "instructions": [],
        }

        mock_get_response = AsyncMock()
        mock_get_response.json = AsyncMock(return_value=instances)

        mock_post_response = AsyncMock()
        mock_post_response.json = AsyncMock(return_value=migration_plan)

        mock_execute_response = AsyncMock()
        mock_execute_response.json = AsyncMock(return_value={})

        with patch("purjo.migration.operaton_session") as mock_session:
            session = AsyncMock()
            session.get = AsyncMock(return_value=mock_get_response)
            session.post = AsyncMock(
                side_effect=[mock_post_response, mock_execute_response]
            )
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            await migrate(target, verbose=False)

            assert session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_migrate_with_verbose_output(self, capsys: Any) -> None:
        """Test migration with verbose output enabled."""
        from purjo.migration import migrate

        target = ProcessDefinitionDto(
            id="target-def-id",
            key="process-key",
            name="Test Process",
            version=2,
        )

        instances = [
            {
                "id": "instance-1",
                "definitionId": "old-def-id",
                "businessKey": "bk-1",
            }
        ]

        migration_plan = {
            "sourceProcessDefinitionId": "old-def-id",
            "targetProcessDefinitionId": "target-def-id",
            "instructions": [],
        }

        mock_get_response = AsyncMock()
        mock_get_response.json = AsyncMock(return_value=instances)

        mock_post_response = AsyncMock()
        mock_post_response.json = AsyncMock(return_value=migration_plan)

        mock_execute_response = AsyncMock()
        mock_execute_response.json = AsyncMock(return_value={"migrated": True})

        with patch("purjo.migration.operaton_session") as mock_session:
            session = AsyncMock()
            session.get = AsyncMock(return_value=mock_get_response)
            session.post = AsyncMock(
                side_effect=[mock_post_response, mock_execute_response]
            )
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            await migrate(target, verbose=True)

            captured = capsys.readouterr()
            assert "migrated" in captured.out

    @pytest.mark.asyncio
    async def test_migrate_multiple_definitions(self) -> None:
        """Test migrating instances from multiple source definitions."""
        from purjo.migration import migrate

        target = ProcessDefinitionDto(
            id="target-def-id",
            key="process-key",
            name="Test Process",
            version=3,
        )

        instances = [
            {
                "id": "instance-1",
                "definitionId": "def-v1",
                "businessKey": "bk-1",
            },
            {
                "id": "instance-2",
                "definitionId": "def-v2",
                "businessKey": "bk-2",
            },
        ]

        migration_plan_v1 = {
            "sourceProcessDefinitionId": "def-v1",
            "targetProcessDefinitionId": "target-def-id",
            "instructions": [],
        }

        migration_plan_v2 = {
            "sourceProcessDefinitionId": "def-v2",
            "targetProcessDefinitionId": "target-def-id",
            "instructions": [],
        }

        mock_get_response = AsyncMock()
        mock_get_response.json = AsyncMock(return_value=instances)

        post_responses = [
            AsyncMock(json=AsyncMock(return_value=migration_plan_v1)),
            AsyncMock(json=AsyncMock(return_value=migration_plan_v2)),
            AsyncMock(json=AsyncMock(return_value={})),
            AsyncMock(json=AsyncMock(return_value={})),
        ]

        with patch("purjo.migration.operaton_session") as mock_session:
            session = AsyncMock()
            session.get = AsyncMock(return_value=mock_get_response)
            session.post = AsyncMock(side_effect=post_responses)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            await migrate(target, verbose=False)

            # 2 generate calls + 2 execute calls
            assert session.post.call_count == 4

    @pytest.mark.asyncio
    async def test_skip_instances_with_no_definition(self) -> None:
        """Test that instances without definitionId are skipped."""
        from purjo.migration import migrate

        target = ProcessDefinitionDto(
            id="target-def-id",
            key="process-key",
            name="Test Process",
            version=2,
        )

        # Instance has no definitionId - should be skipped
        instances = [
            {
                "id": "instance-1",
                "definitionId": None,
                "businessKey": "bk-1",
            }
        ]

        mock_get_response = AsyncMock()
        mock_get_response.json = AsyncMock(return_value=instances)

        with patch("purjo.migration.operaton_session") as mock_session:
            session = AsyncMock()
            session.get = AsyncMock(return_value=mock_get_response)
            session.post = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            await migrate(target, verbose=False)

            # No migration posts should be made since definitionId is None
            session.post.assert_not_called()
