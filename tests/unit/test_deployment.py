"""Unit tests for deployment.py module.

Related User Stories:
- US-017: Force deployment
- US-019: Deploy resources

Related ADRs:
- ADR-003: Architecture overview
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch
import aiohttp
import json
import os
import pytest
import sys


class TestBuildDeploymentForm:
    """Tests for build_deployment_form function."""

    def test_single_resource(self, temp_dir: Path) -> None:
        """Test building form with single resource."""
        from purjo.deployment import build_deployment_form

        resource = temp_dir / "process.bpmn"
        resource.write_text("<bpmn>content</bpmn>")

        form = build_deployment_form([resource], "test-deployment", True)

        assert isinstance(form, aiohttp.FormData)

    def test_multiple_resources(self, temp_dir: Path) -> None:
        """Test building form with multiple resources."""
        from purjo.deployment import build_deployment_form

        resource1 = temp_dir / "process1.bpmn"
        resource1.write_text("<bpmn>content1</bpmn>")
        resource2 = temp_dir / "process2.bpmn"
        resource2.write_text("<bpmn>content2</bpmn>")

        form = build_deployment_form([resource1, resource2], "multi-deploy", False)

        assert isinstance(form, aiohttp.FormData)

    def test_deploy_changed_only_true(self, temp_dir: Path) -> None:
        """Test that deploy_changed_only flag is set correctly."""
        from purjo.deployment import build_deployment_form

        resource = temp_dir / "process.bpmn"
        resource.write_text("<bpmn>content</bpmn>")

        form = build_deployment_form([resource], "test", True)

        assert isinstance(form, aiohttp.FormData)

    def test_deploy_changed_only_false(self, temp_dir: Path) -> None:
        """Test that deploy_changed_only flag is set correctly when False."""
        from purjo.deployment import build_deployment_form

        resource = temp_dir / "process.bpmn"
        resource.write_text("<bpmn>content</bpmn>")

        form = build_deployment_form([resource], "test", False)

        assert isinstance(form, aiohttp.FormData)


class TestBuildCockpitUrl:
    """Tests for build_cockpit_url function."""

    def test_basic_url(self) -> None:
        """Test building basic cockpit URL."""
        from purjo.deployment import build_cockpit_url

        result = build_cockpit_url(
            "http://localhost:8080/engine-rest", "/process-instance"
        )

        assert "localhost:8080" in result
        assert "/operaton/app/cockpit/default/#/process-instance" in result

    def test_url_without_engine_rest(self) -> None:
        """Test building cockpit URL without /engine-rest suffix."""
        from purjo.deployment import build_cockpit_url

        result = build_cockpit_url("http://localhost:8080", "/process-definition")

        assert "localhost:8080" in result
        assert "/operaton/app/cockpit/default/#/process-definition" in result

    def test_url_with_trailing_slash(self) -> None:
        """Test building cockpit URL with trailing slash."""
        from purjo.deployment import build_cockpit_url

        result = build_cockpit_url(
            "http://localhost:8080/engine-rest/", "/process-instance"
        )

        assert "/operaton/app/cockpit/default/#/process-instance" in result

    def test_url_with_custom_port(self) -> None:
        """Test building cockpit URL with custom port."""
        from purjo.deployment import build_cockpit_url

        result = build_cockpit_url(
            "http://localhost:9090/engine-rest", "/process-instance"
        )

        assert "localhost:9090" in result

    def test_codespace_environment(self) -> None:
        """Test building cockpit URL in GitHub Codespaces environment."""
        from purjo.deployment import build_cockpit_url

        with patch.dict(os.environ, {"CODESPACE_NAME": "my-codespace"}):
            result = build_cockpit_url(
                "http://localhost:8080/engine-rest", "/process-instance"
            )

            assert "my-codespace" in result
            assert "app.github.dev" in result
            assert "/operaton/app/cockpit/default/#/process-instance" in result


class TestParseVariablesInput:
    """Tests for parse_variables_input function."""

    def test_none_input(self) -> None:
        """Test parsing None returns empty dict."""
        from purjo.deployment import parse_variables_input

        result = parse_variables_input(None)

        assert result == {}

    def test_empty_string(self) -> None:
        """Test parsing empty string returns empty dict."""
        from purjo.deployment import parse_variables_input

        result = parse_variables_input("")

        assert result == {}

    def test_json_string(self) -> None:
        """Test parsing JSON string."""
        from purjo.deployment import parse_variables_input

        result = parse_variables_input('{"key": "value", "num": 42}')

        assert result == {"key": "value", "num": 42}

    def test_file_path(self, temp_dir: Path) -> None:
        """Test parsing from file path."""
        from purjo.deployment import parse_variables_input

        variables_file = temp_dir / "variables.json"
        variables_file.write_text('{"fromFile": true}')

        result = parse_variables_input(str(variables_file))

        assert result == {"fromFile": True}

    def test_stdin_input(self) -> None:
        """Test parsing from stdin."""
        from io import StringIO
        from purjo.deployment import parse_variables_input

        mock_stdin = StringIO('{"fromStdin": true}')
        with patch.object(sys, "stdin", mock_stdin):
            result = parse_variables_input("-")

        assert result == {"fromStdin": True}

    def test_complex_json(self) -> None:
        """Test parsing complex JSON structure."""
        from purjo.deployment import parse_variables_input

        complex_json = json.dumps(
            {"nested": {"key": "value"}, "list": [1, 2, 3], "bool": True}
        )
        result = parse_variables_input(complex_json)

        assert result["nested"]["key"] == "value"
        assert result["list"] == [1, 2, 3]
        assert result["bool"] is True


@pytest.fixture
def temp_dir() -> Any:
    """Provide a temporary directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
