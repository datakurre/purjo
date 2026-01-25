"""Unit tests for CLI commands in main.py.

Related User Stories:
- US-012: Wrap project into robot.zip
- US-013: Include cached dependencies offline
- US-018: Create BPMN/DMN/Form files with unique IDs

Related ADRs:
- ADR-001: Use uv for environment management
- ADR-003: Architecture overview
"""

from pathlib import Path
from purjo.main import cli_wrap
from purjo.main import operaton_create
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
from zipfile import ZipFile
import os
import pytest


class TestCliWrap:
    """Tests for cli_wrap command.

    Related: US-012, US-013
    """

    def test_wrap_creates_zip_file(self, temp_dir: Path, monkeypatch: Any) -> None:
        """Test that cli_wrap creates a robot.zip file."""
        # Change to temp directory
        monkeypatch.chdir(temp_dir)

        # Create a minimal pyproject.toml
        (temp_dir / "pyproject.toml").write_text(
            """
[tool.purjo.topics."test"]
name = "Test"
"""
        )

        # Create a simple robot file
        (temp_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        # Run cli_wrap
        cli_wrap(offline=False, log_level="INFO")

        # Check that robot.zip was created
        assert (temp_dir / "robot.zip").exists()

        # Verify zip contents
        with ZipFile(temp_dir / "robot.zip", "r") as zf:
            names = zf.namelist()
            assert "pyproject.toml" in names
            assert "test.robot" in names

    def test_wrap_respects_wrapignore(self, temp_dir: Path, monkeypatch: Any) -> None:
        """Test that cli_wrap respects .wrapignore file."""
        monkeypatch.chdir(temp_dir)

        # Create files
        (temp_dir / "pyproject.toml").write_text(
            '[tool.purjo.topics.test]\nname = "Test"'
        )
        (temp_dir / "include.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )
        (temp_dir / "exclude.txt").write_text("Should be excluded")

        # Create .wrapignore to exclude .txt files
        (temp_dir / ".wrapignore").write_text("*.txt")

        # Run cli_wrap
        cli_wrap(offline=False, log_level="INFO")

        # Check zip contents
        with ZipFile(temp_dir / "robot.zip", "r") as zf:
            names = zf.namelist()
            assert "include.robot" in names
            # exclude.txt should not be in the zip
            assert "exclude.txt" not in names

    def test_wrap_offline_mode_with_cache(
        self, temp_dir: Path, monkeypatch: Any
    ) -> None:
        """Test that cli_wrap in offline mode includes .cache directory."""
        monkeypatch.chdir(temp_dir)

        # Create files
        (temp_dir / "pyproject.toml").write_text(
            '[tool.purjo.topics.test]\nname = "Test"'
        )
        (temp_dir / "test.robot").write_text(
            "*** Test Cases ***\nTest\n    Log    Test"
        )

        # Create a fake .cache directory
        cache_dir = temp_dir / ".cache"
        cache_dir.mkdir()
        (cache_dir / "cached_file.txt").write_text("Cached content")

        # Mock the uv run command
        with patch("purjo.main.asyncio.run") as mock_asyncio_run:
            # Run cli_wrap in offline mode
            cli_wrap(offline=True, log_level="INFO")

            # Verify asyncio.run was called (for uv cache command)
            assert mock_asyncio_run.called

        # Check zip contents include cache
        with ZipFile(temp_dir / "robot.zip", "r") as zf:
            names = zf.namelist()
            # Cache should be included
            cache_files = [n for n in names if ".cache" in n]
            assert len(cache_files) > 0


class TestOperatonCreate:
    """Tests for operaton_create command.

    Related: US-018
    """

    def test_create_bpmn_file(self, temp_dir: Path) -> None:
        """Test creating a new BPMN file."""
        bpmn_file = temp_dir / "test.bpmn"

        with patch("purjo.main.importlib.resources.files") as mock_resources:
            # Mock the template file
            mock_template = Mock()
            mock_template.read_text.return_value = "<bpmn>template</bpmn>"
            mock_resources.return_value.__truediv__.return_value = mock_template

            operaton_create(bpmn_file, log_level="INFO")

        # Verify file was created
        assert bpmn_file.exists()

    def test_create_dmn_file(self, temp_dir: Path) -> None:
        """Test creating a new DMN file."""
        dmn_file = temp_dir / "test.dmn"

        with patch("purjo.main.importlib.resources.files") as mock_resources:
            # Mock the template file
            mock_template = Mock()
            mock_template.read_text.return_value = "<dmn>template</dmn>"
            mock_resources.return_value.__truediv__.return_value = mock_template

            operaton_create(dmn_file, log_level="INFO")

        # Verify file was created
        assert dmn_file.exists()

    def test_create_form_file(self, temp_dir: Path) -> None:
        """Test creating a new form file."""
        form_file = temp_dir / "test.form"

        with patch("purjo.main.importlib.resources.files") as mock_resources:
            # Mock the template file
            mock_template = Mock()
            mock_template.read_text.return_value = '{"form":"template"}'
            mock_resources.return_value.__truediv__.return_value = mock_template

            operaton_create(form_file, log_level="INFO")

        # Verify file was created
        assert form_file.exists()

    def test_create_adds_bpmn_extension_if_missing(self, temp_dir: Path) -> None:
        """Test that operaton_create adds .bpmn extension if missing."""
        file_path = temp_dir / "test_file"

        with patch("purjo.main.importlib.resources.files") as mock_resources:
            # Mock the template file
            mock_template = Mock()
            mock_template.read_text.return_value = "<bpmn>template</bpmn>"
            mock_resources.return_value.__truediv__.return_value = mock_template

            operaton_create(file_path, log_level="INFO")

        # Verify .bpmn file was created
        assert (temp_dir / "test_file.bpmn").exists()

    def test_create_fails_if_file_exists(self, temp_dir: Path) -> None:
        """Test that operaton_create fails if file already exists."""
        bpmn_file = temp_dir / "existing.bpmn"
        bpmn_file.write_text("<bpmn>existing</bpmn>")

        with pytest.raises(AssertionError):
            operaton_create(bpmn_file, log_level="INFO")
