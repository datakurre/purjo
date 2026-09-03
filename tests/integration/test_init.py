"""Integration tests for pur init command."""

from pathlib import Path
from purjo.main import initialize_robot_package
import pytest
import shutil
import unittest.mock as mock


class TestInitIntegration:
    """Integration tests for initialize_robot_package function.

    Related: US-010, US-021
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

    @pytest.mark.asyncio
    async def test_init_with_agents_flag_creates_agents_md(
        self, temp_dir: Path
    ) -> None:
        """Test that --agents creates an AGENTS.md matching the test template."""
        if not shutil.which("uv"):
            pytest.skip("uv not available")

        with mock.patch("purjo.main.cli_wrap"):
            await initialize_robot_package(temp_dir, python=False, agents=True)

        agents_content = (temp_dir / "AGENTS.md").read_text()
        assert "*** Test Cases ***" in agents_content
        assert "My Test in Robot" in agents_content
        assert "Run Robot Test" in agents_content
        assert "[tool.purjo.topics." in agents_content
        assert "Run Robot Task" not in agents_content

        # AGENTS.md is developer-facing and excluded from the robot package
        assert "AGENTS.md" in (temp_dir / ".wrapignore").read_text()

    @pytest.mark.asyncio
    async def test_init_with_agents_and_task_flags(self, temp_dir: Path) -> None:
        """Test that --agents --task creates an AGENTS.md for the task template."""
        if not shutil.which("uv"):
            pytest.skip("uv not available")

        with mock.patch("purjo.main.cli_wrap"):
            await initialize_robot_package(
                temp_dir, python=False, task=True, agents=True
            )

        agents_content = (temp_dir / "AGENTS.md").read_text()
        assert "*** Tasks ***" in agents_content
        assert "My Task in Robot" in agents_content
        assert "Run Robot Task" in agents_content
        assert "*** Test Cases ***" not in agents_content
        assert "Run Robot Test" not in agents_content

    @pytest.mark.asyncio
    async def test_init_without_agents_flag_creates_no_agents_md(
        self, temp_dir: Path
    ) -> None:
        """Test that AGENTS.md is opt-in and .wrapignore stays empty without it."""
        if not shutil.which("uv"):
            pytest.skip("uv not available")

        with mock.patch("purjo.main.cli_wrap"):
            await initialize_robot_package(temp_dir, python=False)

        assert not (temp_dir / "AGENTS.md").exists()
        assert (temp_dir / ".wrapignore").read_text() == ""
