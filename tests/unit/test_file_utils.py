"""Unit tests for file_utils.py module."""

from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
import pytest


class TestFetch:
    """Tests for fetch function."""

    @pytest.mark.asyncio
    async def test_fetch_file_variable(self, temp_dir: Path) -> None:
        """Test fetching a file variable from Operaton."""
        from purjo.file_utils import fetch

        task = LockedExternalTaskDto(
            id="task-1",
            workerId="worker-1",
            topicName="test-topic",
            activityId="activity-1",
            processInstanceId="process-1",
            processDefinitionId="def-1",
            executionId="exec-1",
        )

        file_content = b"file content"

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=file_content)

        with patch("purjo.file_utils.operaton_session") as mock_session:
            session = AsyncMock()
            session.get = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await fetch(task, "myFile", "document.pdf", temp_dir)

            assert result.exists()
            assert result.read_bytes() == file_content
            assert result.name == "document.pdf"


class TestPyFromOperaton:
    """Tests for py_from_operaton function in file_utils."""

    @pytest.mark.asyncio
    async def test_simple_variables(self) -> None:
        """Test converting simple variables."""
        from purjo.file_utils import py_from_operaton

        variables = {
            "stringVar": VariableValueDto(value="hello", type=VariableValueType.String),
            "intVar": VariableValueDto(value=42, type=VariableValueType.Integer),
            "boolVar": VariableValueDto(value=True, type=VariableValueType.Boolean),
        }

        result = await py_from_operaton(variables)

        assert result["stringVar"] == "hello"
        assert result["intVar"] == 42
        assert result["boolVar"] is True

    @pytest.mark.asyncio
    async def test_none_variables(self) -> None:
        """Test with None variables."""
        from purjo.file_utils import py_from_operaton

        result = await py_from_operaton(None)

        assert result == {}

    @pytest.mark.asyncio
    async def test_skip_file_variables_without_task(self) -> None:
        """Test that file variables are skipped when no task is provided."""
        from purjo.file_utils import py_from_operaton

        variables = {
            "stringVar": VariableValueDto(value="hello", type=VariableValueType.String),
            "fileVar": VariableValueDto(
                value=None,
                type=VariableValueType.File,
                valueInfo={"filename": "doc.pdf"},
            ),
        }

        result = await py_from_operaton(variables)

        assert "stringVar" in result
        assert "fileVar" not in result

    @pytest.mark.asyncio
    async def test_fetch_file_variables_with_task(self, temp_dir: Path) -> None:
        """Test that file variables are fetched when task is provided."""
        from purjo.file_utils import py_from_operaton

        task = LockedExternalTaskDto(
            id="task-1",
            workerId="worker-1",
            topicName="test-topic",
            activityId="activity-1",
            processInstanceId="process-1",
            processDefinitionId="def-1",
            executionId="exec-1",
        )

        variables = {
            "stringVar": VariableValueDto(value="hello", type=VariableValueType.String),
            "fileVar": VariableValueDto(
                value=None,
                type=VariableValueType.File,
                valueInfo={"filename": "doc.pdf"},
            ),
        }

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=b"file content")

        with patch("purjo.file_utils.operaton_session") as mock_session:
            session = AsyncMock()
            session.get = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await py_from_operaton(variables, task, temp_dir)

            assert "stringVar" in result
            assert "fileVar" in result
            assert isinstance(result["fileVar"], Path)


class TestFindImageSources:
    """Tests for find_image_sources function."""

    def test_find_single_image(self) -> None:
        """Test finding a single image source."""
        from purjo.file_utils import find_image_sources

        html = '<html><body><img src="screenshot.png"/></body></html>'
        result = find_image_sources(html)

        assert "screenshot.png" in result

    def test_find_multiple_images(self) -> None:
        """Test finding multiple image sources."""
        from purjo.file_utils import find_image_sources

        html = """
        <html><body>
            <img src="image1.png"/>
            <img src="image2.jpg"/>
            <img src="image3.gif"/>
        </body></html>
        """
        result = find_image_sources(html)

        assert len(result) == 3
        assert "image1.png" in result
        assert "image2.jpg" in result
        assert "image3.gif" in result

    def test_no_images(self) -> None:
        """Test HTML with no images."""
        from purjo.file_utils import find_image_sources

        html = "<html><body><p>No images here</p></body></html>"
        result = find_image_sources(html)

        assert len(result) == 0


class TestResolveImagePath:
    """Tests for resolve_image_path function."""

    def test_existing_image(self, temp_dir: Path) -> None:
        """Test resolving an existing image path."""
        from purjo.file_utils import resolve_image_path

        html_file = temp_dir / "report.html"
        html_file.write_text("<html></html>")
        image_file = temp_dir / "screenshot.png"
        image_file.write_bytes(b"PNG data")

        result = resolve_image_path("screenshot.png", html_file)

        assert result is not None
        assert result == image_file

    def test_nonexistent_image(self, temp_dir: Path) -> None:
        """Test resolving a nonexistent image path."""
        from purjo.file_utils import resolve_image_path

        html_file = temp_dir / "report.html"
        html_file.write_text("<html></html>")

        result = resolve_image_path("nonexistent.png", html_file)

        assert result is None

    def test_data_uri_ignored(self, temp_dir: Path) -> None:
        """Test that data URIs are ignored."""
        from purjo.file_utils import resolve_image_path

        html_file = temp_dir / "report.html"
        html_file.write_text("<html></html>")

        result = resolve_image_path("data:image/png;base64,abc123", html_file)

        assert result is None


class TestReplaceImageSources:
    """Tests for replace_image_sources function."""

    def test_replace_single_image(self) -> None:
        """Test replacing a single image source."""
        from purjo.file_utils import replace_image_sources

        html = '<img src="old.png"/>'
        replacements = {"old.png": "data:image/png;base64,abc123"}

        result = replace_image_sources(html, replacements)

        assert "data:image/png;base64,abc123" in result
        assert "old.png" not in result

    def test_replace_multiple_images(self) -> None:
        """Test replacing multiple image sources."""
        from purjo.file_utils import replace_image_sources

        html = '<img src="img1.png"/><img src="img2.png"/>'
        replacements = {
            "img1.png": "data:image/png;base64,AAA",
            "img2.png": "data:image/png;base64,BBB",
        }

        result = replace_image_sources(html, replacements)

        assert "data:image/png;base64,AAA" in result
        assert "data:image/png;base64,BBB" in result


@pytest.fixture
def temp_dir() -> Any:
    """Provide a temporary directory."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
