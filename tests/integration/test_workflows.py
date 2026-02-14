"""Integration tests for purjo end-to-end workflows.

Related User Stories:
- US-001: Serve robot packages
- US-004: Configure secrets
- US-012: Wrap robot.zip

Related ADRs:
- ADR-001: Use uv for environment management
- ADR-002: Use external task pattern
- ADR-003: Architecture overview
"""

from pathlib import Path
from purjo.main import cli_wrap
from purjo.Purjo import Purjo
from typing import Any
from unittest.mock import patch
from zipfile import ZipFile
import pytest


class TestHelloExampleIntegration:
    """Integration test using the hello example."""

    def test_hello_example_workflow(self, temp_dir: Path) -> None:
        """Test complete workflow: create robot package, wrap it, and test it."""
        # Create a minimal hello robot package
        package_dir = temp_dir / "hello_package"
        package_dir.mkdir()

        # Create pyproject.toml
        pyproject_content = """
[project]
name = "hello-package"
version = "0.1.0"
dependencies = ["robotframework"]

[tool.purjo.topics."hello"]
name = "Hello Test"
on-fail = "ERROR"
"""
        (package_dir / "pyproject.toml").write_text(pyproject_content)

        # Create a simple robot test
        robot_content = """*** Test Cases ***
Hello Test
    Log    Hello World
    Set Task Variable    greeting    Hello from Robot
"""
        (package_dir / "hello.robot").write_text(robot_content)

        # Test get_output_variables with the directory
        purjo = Purjo()

        with (
            patch("purjo.Purjo.asyncio.run") as mock_asyncio_run,
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
        ):
            # Mock successful execution
            mock_asyncio_run.return_value = (0, b"Success", b"")

            result = purjo.get_output_variables(
                path=str(package_dir),
                topic="hello",
                variables={"name": "World"},
                log_level="INFO",
            )

            # Should get back a dictionary
            assert isinstance(result, dict)


class TestSecretsExampleIntegration:
    """Integration test for secrets handling."""

    def test_secrets_workflow(self, temp_dir: Path) -> None:
        """Test workflow with secrets."""
        # Create a package with secrets
        package_dir = temp_dir / "secrets_package"
        package_dir.mkdir()

        # Create pyproject.toml with secrets configuration
        pyproject_content = """
[project]
name = "secrets-package"
version = "0.1.0"
dependencies = ["robotframework"]

[tool.purjo]
secrets = "file"

[tool.purjo.topics."secure"]
name = "Secure Test"
on-fail = "ERROR"
"""
        (package_dir / "pyproject.toml").write_text(pyproject_content)

        # Create robot test that uses secrets
        robot_content = """*** Test Cases ***
Secure Test
    Log    Using secrets
    Set Task Variable    result    success
"""
        (package_dir / "secure.robot").write_text(robot_content)

        # Test with secrets
        purjo = Purjo()

        with (
            patch("purjo.Purjo.asyncio.run") as mock_asyncio_run,
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
        ):
            # Mock successful execution
            mock_asyncio_run.return_value = (0, b"Success", b"")

            result = purjo.get_output_variables(
                path=str(package_dir),
                topic="secure",
                variables={"input": "data"},
                secrets={"api_key": "secret123"},
                log_level="INFO",
            )

            # Should get back a dictionary
            assert isinstance(result, dict)


class TestWrapAndExecuteIntegration:
    """Integration test for wrapping and executing packages."""

    def test_wrap_then_execute(self, temp_dir: Path, monkeypatch: Any) -> None:
        """Test wrapping a package into zip and then executing it."""
        # Create a package
        package_dir = temp_dir / "test_package"
        package_dir.mkdir()

        # Create pyproject.toml
        pyproject_content = """
[project]
name = "test-package"
version = "0.1.0"
dependencies = ["robotframework"]

[tool.purjo.topics."test"]
name = "Test Case"
"""
        (package_dir / "pyproject.toml").write_text(pyproject_content)

        # Create robot file
        (package_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest Case\n    Log    Test"
        )

        # Change to package directory and wrap it
        monkeypatch.chdir(package_dir)
        cli_wrap(offline=False, log_level="INFO")

        # Verify zip was created
        zip_path = package_dir / "robot.zip"
        assert zip_path.exists()

        # Verify zip contents
        with ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "pyproject.toml" in names
            assert "test.robot" in names

        # Now test executing the zip
        purjo = Purjo()

        with (
            patch("purjo.Purjo.asyncio.run") as mock_asyncio_run,
            patch("purjo.Purjo.shutil.which", return_value="/usr/bin/uv"),
        ):
            # Mock successful execution
            mock_asyncio_run.return_value = (0, b"Success", b"")

            result = purjo.get_output_variables(
                path=str(zip_path),
                topic="test",
                variables={},
                log_level="INFO",
            )

            # Should get back a dictionary
            assert isinstance(result, dict)
