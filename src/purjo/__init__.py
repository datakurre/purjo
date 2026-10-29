"""Purjo - Robot Framework integration with Operaton BPM engine.

This package provides tools for orchestrating Robot Framework test suites
and Python tasks with the Operaton BPM engine through external task workers.
"""

from typing import Any
from typing import Optional
from typing import Tuple
from typing import Type

purjo: Optional[Type[Any]]
# The Robot Framework library export is optional requiring robotframework.
try:
    from purjo.Purjo import Purjo as _Purjo
except ModuleNotFoundError as error:
    if error.name != "robot":
        raise
    purjo = None
else:
    purjo = _Purjo


def _import_parsers() -> Tuple[Optional[Type[Any]], Optional[Type[Any]]]:
    """Lazily import Robot Framework parsers if available.

    Returns tuple of (PythonParser, RobotParser) or (None, None) if unavailable.
    """
    try:
        from purjo.data.RobotParser import PythonParser
        from purjo.data.RobotParser import RobotParser

        return PythonParser, RobotParser
    # Robot Framework parsers are only needed by Robot Framework tests.
    except ModuleNotFoundError:  # pragma: no cover
        # PythonParser depends on robot
        return None, None


PythonParser, RobotParser = _import_parsers()

if PythonParser is not None and RobotParser is not None:
    __all__ = ["purjo", "PythonParser", "RobotParser"]
else:  # pragma: no cover
    __all__ = ["purjo"]
