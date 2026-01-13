"""
Utility functions for purjo.

This module re-exports utilities from focused submodules for backward compatibility.
"""

from purjo.datetime_utils import dt_from_operaton
from purjo.datetime_utils import dt_to_operaton
from purjo.datetime_utils import from_iso_to_dt
from purjo.file_utils import data_uri
from purjo.file_utils import fetch
from purjo.file_utils import get_wrap_pathspec
from purjo.file_utils import inline_screenshots
from purjo.file_utils import py_from_operaton
from purjo.migration import migrate
from purjo.serialization import deserialize
from purjo.serialization import json_serializer
from purjo.serialization import operaton_from_py
from purjo.serialization import operaton_value_from_py
from purjo.serialization import py_from_javaobj
from purjo.serialization import ValueInfo
from typing import Any
import pprint

__all__ = [
    "dt_from_operaton",
    "dt_to_operaton",
    "from_iso_to_dt",
    "data_uri",
    "fetch",
    "get_wrap_pathspec",
    "inline_screenshots",
    "py_from_operaton",
    "migrate",
    "deserialize",
    "json_serializer",
    "operaton_from_py",
    "operaton_value_from_py",
    "py_from_javaobj",
    "ValueInfo",
    "lazypprint",
    "lazydecode",
]


# Utility classes for lazy logging
class lazypprint:
    """Lazy pretty-print formatter for logging."""

    def __init__(self, data: Any) -> None:
        self.data = data

    def __str__(self) -> str:
        return pprint.pformat(self.data)


class lazydecode:
    """Lazy byte string decoder for logging."""

    def __init__(self, *data: bytes) -> None:
        self.data = data

    def __str__(self) -> str:
        return "\n".join([b.decode() for b in self.data])
