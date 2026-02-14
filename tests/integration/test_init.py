"""Integration tests for pur init command."""

from pathlib import Path
from purjo.main import initialize_robot_package
import pytest
import shutil
import unittest.mock as mock


class TestInitIntegration:
    """Integration tests for initialize_robot_package function.

    Related: US-010
    """

    @pytest.mark.asyncio
    async def test_init_with_task_flag_creates_task_files(self, temp_dir: Path) -> None:
        """Test that --task flag creates robot files with Tasks section."""
        if not shutil.which("uv"):
            pytest.skip("uv not available")

        # Mock cli_wrap to prevent ZIP timestamp issues
        with mock.patch("purjo.main.cli_wrap"):
            # Initialize with task flag
            await initialize_robot_package(temp_dir, python=False, task=True)

        # Verify hello.robot contains "*** Tasks ***"
        hello_content = (temp_dir / "hello.robot").read_text()
        assert "*** Tasks ***" in hello_content
        assert "*** Test Cases ***" not in hello_content
        assert "My Task in Robot" in hello_content

        # Verify test_hello.robot contains "*** Tasks ***" and "Task Template"
        test_hello_content = (temp_dir / "test_hello.robot").read_text()
        assert "*** Tasks ***" in test_hello_content
        assert "*** Test Cases ***" not in test_hello_content
        assert "Task Template" in test_hello_content
        assert "Test Template" not in test_hello_content
        assert "Run Robot Task" in test_hello_content

        # Verify pyproject.toml has correct topic name
        pyproject_content = (temp_dir / "pyproject.toml").read_text()
        assert "My Task in Robot" in pyproject_content

    @pytest.mark.asyncio
    async def test_init_without_task_flag_creates_test_files(
        self, temp_dir: Path
    ) -> None:
        """Test that default behavior creates robot files with Test Cases section."""
        if not shutil.which("uv"):
            pytest.skip("uv not available")

        # Mock cli_wrap to prevent ZIP timestamp issues
        with mock.patch("purjo.main.cli_wrap"):
            # Initialize without task flag
            await initialize_robot_package(temp_dir, python=False, task=False)

        # Verify hello.robot contains "*** Test Cases ***"
        hello_content = (temp_dir / "hello.robot").read_text()
        assert "*** Test Cases ***" in hello_content
        assert "*** Tasks ***" not in hello_content
        assert "My Test in Robot" in hello_content

        # Verify test_hello.robot contains "*** Test Cases ***" and "Test Template"
        test_hello_content = (temp_dir / "test_hello.robot").read_text()
        assert "*** Test Cases ***" in test_hello_content
        assert "*** Tasks ***" not in test_hello_content
        assert "Test Template" in test_hello_content
        assert "Task Template" not in test_hello_content
        assert "Run Robot Test" in test_hello_content

        # Verify pyproject.toml has correct topic name
        pyproject_content = (temp_dir / "pyproject.toml").read_text()
        assert "My Test in Robot" in pyproject_content
