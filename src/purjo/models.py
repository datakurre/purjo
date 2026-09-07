"""Data models for purjo.

This module contains Pydantic models used across the application.
"""

from purjo.config import OnFail
from pydantic import BaseModel
from pydantic import Field
from typing import List
from typing import Optional


class Task(BaseModel):
    """Configuration model for a Robot Framework task.

    This model defines the configuration for executing a Robot Framework
    task or Python callable as an external task in Operaton.

    Attributes:
        name: The name of the test/task to run, or a Python FQFN.
        include: Tag pattern to include tests.
        exclude: Tag pattern to exclude tests.
        on_fail: How to handle task failures (FAIL, COMPLETE, ERROR).
        process_variables: Whether to pass variables at process scope.
        pythonpath: Additional paths to add to PYTHONPATH.
    """

    name: Optional[str] = None
    include: Optional[str] = None
    exclude: Optional[str] = None
    on_fail: Optional[OnFail] = Field(default=None, alias="on-fail")
    process_variables: bool = Field(default=False, alias="process-variables")
    pythonpath: Optional[List[str]] = None
