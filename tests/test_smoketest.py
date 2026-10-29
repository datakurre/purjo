"""Test project successful import.

Related ADRs:
- ADR-003: Architecture overview
"""

from importlib import reload
from typing import Any
from unittest.mock import patch
import builtins
import purjo
import pytest


def test_import() -> None:
    """Test project successful import."""
    from purjo import main

    assert main


def test_import_main_without_robot_framework() -> None:
    """The CLI package import must not load the Robot Framework library."""
    real_import = builtins.__import__

    def import_without_robot(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "purjo.Purjo" or name == "robot" or name.startswith("robot."):
            raise ModuleNotFoundError("No module named 'robot'", name="robot")
        return real_import(name, *args, **kwargs)

    try:
        with patch("builtins.__import__", side_effect=import_without_robot):
            reload(purjo)
            from purjo import main

            assert main
            assert purjo.purjo is None

        def import_without_another_dependency(
            name: str, *args: Any, **kwargs: Any
        ) -> Any:
            if name == "purjo.Purjo":
                raise ModuleNotFoundError(
                    "No module named 'another_dependency'",
                    name="another_dependency",
                )
            return real_import(name, *args, **kwargs)

        with patch(
            "builtins.__import__", side_effect=import_without_another_dependency
        ):
            with pytest.raises(ModuleNotFoundError, match="another_dependency"):
                reload(purjo)
    finally:
        reload(purjo)
