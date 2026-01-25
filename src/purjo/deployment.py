"""Deployment utilities for Operaton BPM engine."""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import aiohttp
import json
import os
import sys


def build_deployment_form(
    resources: list[Path], name: str, deploy_changed_only: bool
) -> aiohttp.FormData:
    """Build a FormData object for deployment to Operaton.

    Args:
        resources: List of resource file paths to deploy.
        name: Name of the deployment.
        deploy_changed_only: If True, only deploy changed resources.

    Returns:
        FormData object ready for deployment.
    """
    from purjo.config import CONTENT_TYPE_OCTET_STREAM
    from purjo.config import DEPLOYMENT_SOURCE
    from purjo.config import FIELD_DEPLOY_CHANGED_ONLY
    from purjo.config import FIELD_DEPLOYMENT_NAME
    from purjo.config import FIELD_DEPLOYMENT_SOURCE

    form = aiohttp.FormData()
    for resource in resources:
        form.add_field(
            FIELD_DEPLOYMENT_NAME,
            name,
            content_type="text/plain",
        )
        form.add_field(
            FIELD_DEPLOYMENT_SOURCE,
            DEPLOYMENT_SOURCE,
            content_type="text/plain",
        )
        form.add_field(
            FIELD_DEPLOY_CHANGED_ONLY,
            "true" if deploy_changed_only else "false",
            content_type="text/plain",
        )
        form.add_field(
            resource.name,
            resource.read_text(),
            filename=resource.name,
            content_type=CONTENT_TYPE_OCTET_STREAM,
        )
    return form


def build_cockpit_url(base_url: str, path_suffix: str) -> str:
    """Build a Cockpit URL with support for GitHub Codespaces.

    Args:
        base_url: The base URL of the engine REST API.
        path_suffix: The path suffix to append (e.g., '/process-instance').

    Returns:
        Complete Cockpit URL.
    """
    port = urlparse(base_url).port or 8080
    cockpit_base = (
        base_url.replace("/engine-rest", "").rstrip("/")
        if "CODESPACE_NAME" not in os.environ
        else f"https://{os.environ['CODESPACE_NAME']}-{port}.app.github.dev"
    )
    return cockpit_base + "/operaton/app/cockpit/default/#" + path_suffix


def parse_variables_input(variables: str | None) -> dict[str, Any]:
    """Parse variables from stdin, file, or JSON string.

    Args:
        variables: Either '-' for stdin, a file path, or a JSON string.

    Returns:
        Dictionary of parsed variables.
    """
    if variables == "-":
        return json.load(sys.stdin)  # type: ignore[no-any-return]
    elif variables and os.path.isfile(variables):
        return json.loads(Path(variables).read_text())  # type: ignore[no-any-return]
    elif variables:
        return json.loads(variables)  # type: ignore[no-any-return]
    else:
        return {}
