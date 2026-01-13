"""File-related utility functions."""

from operaton.tasks import operaton_session
from operaton.tasks import settings as operaton_settings
from operaton.tasks.types import LockedExternalTaskDto
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from pathlib import Path
from purjo.serialization import deserialize
from purjo.serialization import ValueInfo
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import base64
import mimetypes
import os
import pathspec
import re

# Default exclusion patterns for wrapping robot packages
DEFAULT_WRAP_EXCLUDES = [
    "/.git",
    "/.devenv",
    "/.gitignore",
    "/log.html",
    "/output.xml",
    "__pycache__/",
    "/report.html",
    "/robot.zip",
    "/.venv/",
    "/.wrapignore",
    "/.cache",
]


def get_wrap_pathspec(cwd_path: Path) -> pathspec.GitIgnoreSpec:
    """Get pathspec for wrapping robot packages, excluding common build artifacts."""
    spec_path = cwd_path / ".wrapignore"
    spec_text = spec_path.read_text() if spec_path.exists() else ""
    return pathspec.GitIgnoreSpec.from_lines(
        spec_text.splitlines() + DEFAULT_WRAP_EXCLUDES
    )


async def fetch(
    task: LockedExternalTaskDto, name: str, filename: str, sandbox: Path
) -> Path:
    """Fetch file variable from Operaton execution."""
    path = sandbox / "files" / name
    async with operaton_session(
        headers={"Content-Type": None, "Accept": "application/octet-stream"}
    ) as session:
        resp = await session.get(
            f"{operaton_settings.ENGINE_REST_BASE_URL}/execution/{task.executionId}/localVariables/{name}/data",
        )
        resp.raise_for_status()
        path.mkdir(parents=True, exist_ok=True)
        with open((path / filename), "wb") as f:
            f.write(await resp.read())
    return path / filename


async def py_from_operaton(
    variables: Optional[Dict[str, VariableValueDto]],
    task: Optional[LockedExternalTaskDto] = None,
    sandbox: Optional[Path] = None,
) -> Dict[str, Any]:
    """Convert Operaton variables to Python objects, fetching files if needed."""
    return {
        key: deserialize(
            variable.value,
            VariableValueType(variable.type) if variable.type else None,
            ValueInfo(**variable.valueInfo) if variable.valueInfo else None,
        )
        for key, variable in (variables.items() if variables is not None else ())
        if variable.type not in (VariableValueType.File, VariableValueType.Bytes)
    } | (
        {
            key: (
                await fetch(
                    task,
                    key,
                    variable.valueInfo["filename"] if variable.valueInfo else key,
                    sandbox,
                )
            )
            for key, variable in (variables.items() if variables is not None else ())
            if variable.type in (VariableValueType.File,)
        }
        if task is not None and sandbox is not None
        else {}
    )


def find_image_sources(html_content: str) -> List[str]:
    """Find all image source URLs in HTML content.

    Args:
        html_content: The HTML content to search.

    Returns:
        A list of image source URLs found in img tags.
    """
    return re.findall('img src="([^"]+)', html_content)


def resolve_image_path(src: str, file_path: Path) -> Optional[Path]:
    """Resolve an image source to an actual file path.

    Tries to find the image file in the following order:
    1. As an absolute path
    2. Relative to the HTML file's location
    3. Relative to the current working directory

    Args:
        src: The image source URL from the HTML.
        file_path: The path to the HTML file containing the image reference.

    Returns:
        The resolved Path to the image file, or None if not found.
    """
    cwd = os.getcwd()
    candidates = [
        Path(src),
        Path(file_path.parent) / src,
        Path(cwd) / src,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def replace_image_sources(html_content: str, replacements: Dict[str, str]) -> str:
    """Replace image sources in HTML content with data URIs.

    Args:
        html_content: The original HTML content.
        replacements: A dict mapping original source URLs to data URIs.

    Returns:
        The HTML content with image sources replaced.
    """
    for src, uri in replacements.items():
        html_content = html_content.replace(f'a href="{src}"', "a")
        html_content = html_content.replace(
            f'img src="{src}" width="800px"',
            f'img src="{uri}" style="max-width:800px;"',
        )
        html_content = html_content.replace(f'img src="{src}"', f'img src="{uri}"')
    return html_content


def inline_screenshots(file_path: Path) -> None:
    """Inline screenshot images in Robot Framework HTML reports as data URIs.

    This function reads an HTML file, finds all embedded images, converts them
    to base64 data URIs, and writes the modified content back to the file.

    Args:
        file_path: Path to the HTML file to process.
    """
    with open(file_path, encoding="utf-8") as fp:
        html_content = fp.read()

    replacements: Dict[str, str] = {}
    for src in find_image_sources(html_content):
        resolved_path = resolve_image_path(src, file_path)
        if resolved_path is None:
            continue
        mimetype = mimetypes.guess_type(resolved_path)[0] or "image/png"
        with open(resolved_path, "rb") as fp:
            data_bytes = fp.read()
        replacements[src] = data_uri(mimetype, data_bytes)

    html_content = replace_image_sources(html_content, replacements)

    with open(file_path, "w", encoding="utf-8") as fp:
        fp.write(html_content)


def data_uri(mimetype: str, data: bytes) -> str:
    """Create a data URI from mimetype and data bytes."""
    return "data:{};base64,{}".format(  # noqa: C0209
        mimetype, base64.b64encode(data).decode("utf-8")
    )
