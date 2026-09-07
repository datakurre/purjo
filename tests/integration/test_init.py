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

        # Mock wrap_package to prevent ZIP timestamp issues
        with mock.patch("purjo.main.wrap_package"):
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

        # Mock wrap_package to prevent ZIP timestamp issues
        with mock.patch("purjo.main.wrap_package"):
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

        with mock.patch("purjo.main.wrap_package"):
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

        with mock.patch("purjo.main.wrap_package"):
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

        with mock.patch("purjo.main.wrap_package"):
            await initialize_robot_package(temp_dir, python=False)

        assert not (temp_dir / "AGENTS.md").exists()
        assert (temp_dir / ".wrapignore").read_text() == ""

    @pytest.mark.asyncio
    async def test_init_rejects_agents_with_python(self, temp_dir: Path) -> None:
        """Test that agents combined with python is rejected by the function.

        The CLI raises typer.BadParameter for the same combination, but the
        invariant belongs to initialize_robot_package itself, which is also
        called directly.
        """
        with pytest.raises(ValueError, match="not supported with python"):
            await initialize_robot_package(temp_dir, python=True, agents=True)

        # Nothing was scaffolded before the guard tripped
        assert not (temp_dir / "AGENTS.md").exists()
        assert not (temp_dir / ".wrapignore").exists()

    @pytest.mark.asyncio
    async def test_init_reports_failing_uv_step(self, temp_dir: Path) -> None:
        """Test that a failing uv command aborts init with a clear error.

        `run` returns the exit code rather than raising, so without an
        explicit check a failed `uv init` surfaced much later as a
        FileNotFoundError on a pyproject.toml that was never written.
        """
        from purjo.exceptions import PurjoEnvironmentError

        async def failing_run(*args: object, **kwargs: object) -> object:
            return (1, b"", b"network unreachable")

        with mock.patch("purjo.main.run", side_effect=failing_run):
            with pytest.raises(PurjoEnvironmentError, match="uv init failed"):
                await initialize_robot_package(temp_dir, python=False)

        # Nothing was scaffolded after the failed step
        assert not (temp_dir / "pyproject.toml").exists()

    @pytest.mark.asyncio
    async def test_init_works_in_directory_with_invalid_package_name(
        self, temp_dir: Path
    ) -> None:
        """Test that init succeeds where the directory is not a package name.

        `uv init` derives the package name from the directory and rejects
        names like "2024.report_", so purjo passes an explicit sanitised
        --name instead.
        """
        if not shutil.which("uv"):
            pytest.skip("uv not available")

        awkward = temp_dir / "2024.report_"
        awkward.mkdir()

        with mock.patch("purjo.main.wrap_package"):
            await initialize_robot_package(awkward, python=False)

        assert (awkward / "pyproject.toml").exists()
        assert (awkward / "hello.robot").exists()
