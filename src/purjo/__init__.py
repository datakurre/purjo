"""Purjo - Robot Framework integration with Operaton BPM engine.

This package provides tools for orchestrating Robot Framework test suites
and Python tasks with the Operaton BPM engine through external task workers.
"""

from purjo.Purjo import Purjo as purjo
from typing import Any
from typing import Optional
from typing import Tuple
from typing import Type


def _import_parsers() -> Tuple[Optional[Type[Any]], Optional[Type[Any]]]:
    """Lazily import Robot Framework parsers if available.

    Returns tuple of (PythonParser, RobotParser) or (None, None) if unavailable.
    """
    try:
        from purjo.data.RobotParser import PythonParser
        from purjo.data.RobotParser import RobotParser

        return PythonParser, RobotParser
    except ModuleNotFoundError:  # pragma: no cover
        # PythonParser depends on robot
        return None, None


PythonParser, RobotParser = _import_parsers()

if PythonParser is not None and RobotParser is not None:
    __all__ = ["purjo", "PythonParser", "RobotParser"]
else:  # pragma: no cover
    __all__ = ["purjo"]
