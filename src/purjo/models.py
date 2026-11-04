"""Data models for purjo.

This module contains Pydantic models used across the application.
"""

from operaton.tasks.types import LockedExternalTaskDto
from purjo.config import OnFail
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import StrictStr
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
        task_metadata: External task DTO fields to expose to Robot Framework.
    """

    name: Optional[str] = None
    include: Optional[str] = None
    exclude: Optional[str] = None
    on_fail: Optional[OnFail] = Field(default=None, alias="on-fail")
    process_variables: bool = Field(default=False, alias="process-variables")
    pythonpath: Optional[List[str]] = None
    task_metadata: List[StrictStr] = Field(default_factory=list, alias="task-metadata")

    @field_validator("task_metadata")
    @classmethod
    def validate_task_metadata(cls, value: List[str]) -> List[str]:
        """Validate selected external task DTO fields."""
        if len(value) != len(set(value)):
            raise ValueError("task-metadata field names must be unique")

        invalid = [
            field
            for field in value
            if field == "variables" or field not in LockedExternalTaskDto.model_fields
        ]
        if invalid:
            raise ValueError(
                "task-metadata fields must be LockedExternalTaskDto fields "
                f"other than 'variables'; invalid fields: {invalid}"
            )

        return value
