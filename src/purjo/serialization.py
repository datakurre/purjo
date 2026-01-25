"""Serialization utilities for Operaton variable conversion."""

from io import BytesIO
from javaobj.v2.beans import JavaString  # type: ignore
from javaobj.v2.transformers import JavaBool  # type: ignore
from javaobj.v2.transformers import JavaInt
from javaobj.v2.transformers import JavaList
from javaobj.v2.transformers import JavaMap
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from pathlib import Path
from purjo.datetime_utils import dt_from_operaton
from purjo.datetime_utils import dt_to_operaton
from purjo.datetime_utils import from_iso_to_dt
from pydantic import BaseModel
from typing import Any
from typing import cast
from typing import Dict
from typing import List
from typing import Optional
import base64
import datetime
import javaobj.v2 as javaobj  # type: ignore
import json
import mimetypes
import tzlocal


class ValueInfo(BaseModel):
    """Value information for Operaton variables."""

    objectTypeName: Optional[str] = None
    serializationDataFormat: Optional[str] = None


# Type alias for deserialized Python values
DeserializedValue = Optional[
    str | int | float | bool | list[Any] | dict[str, Any] | datetime.datetime
]

# Type alias for Java-to-Python converted values
JavaConvertedValue = str | int | bool | list[Any] | dict[Any, Any]


def py_from_javaobj(obj: Any) -> JavaConvertedValue:
    """Convert Java object to Python object.

    Converts Java serialized objects to their Python equivalents:
    - JavaMap -> dict
    - JavaList -> list
    - JavaString -> str
    - JavaInt -> int
    - JavaBool -> bool

    Args:
        obj: A Java object from javaobj library.

    Returns:
        The equivalent Python value.

    Raises:
        TypeError: If the object type is not supported.
    """
    if isinstance(obj, JavaMap):
        return {py_from_javaobj(k): py_from_javaobj(v) for k, v in obj.items()}
    elif isinstance(obj, JavaList):
        return [py_from_javaobj(v) for v in obj]
    elif isinstance(obj, JavaString):
        return str(obj)
    elif isinstance(obj, JavaInt):
        return int(obj)
    elif isinstance(obj, JavaBool):
        return bool(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def deserialize(
    value: Any,
    type_: Optional[VariableValueType] = None,
    info: Optional[ValueInfo] = None,
) -> DeserializedValue:
    """Deserialize Operaton variable value to Python object.

    Converts Operaton variable values to their Python equivalents based on
    the variable type and serialization format.

    Args:
        value: The raw value from Operaton.
        type_: The Operaton variable type.
        info: Value info containing serialization format.

    Returns:
        The deserialized Python value, which can be:
        - str, int, float, bool for primitive types
        - dict or list for JSON/Object types
        - datetime for Date types
        - None for null values

    Raises:
        NotImplementedError: If the serialization format is not supported.
    """
    if (
        value is None
        or type_ is None
        or info is None
        or info.serializationDataFormat is None
    ):
        if type_ == VariableValueType.Date:
            return dt_from_operaton(value)
        return cast(DeserializedValue, value)
    elif info.serializationDataFormat is None:  # pragma: no cover
        return cast(DeserializedValue, value)
    elif info.serializationDataFormat == "application/json":
        result: DeserializedValue = json.loads(value)
        return result
    elif info.serializationDataFormat == "application/x-java-serialized-object":
        return py_from_javaobj(javaobj.load(BytesIO(base64.b64decode(value))))
    raise NotImplementedError(info.serializationDataFormat)


def _create_file_value_dto(file_path: Path) -> VariableValueDto:
    """Create a VariableValueDto for a file."""
    mime = mimetypes.guess_type(file_path)[0] or "text/plain"
    return VariableValueDto(
        value=base64.b64encode(file_path.read_bytes()).decode("utf-8"),
        type=VariableValueType.File,
        valueInfo={
            "filename": file_path.name,
            "mimetype": mime,
            "mimeType": mime,
            "encoding": "utf-8",
        },
    )


def _try_parse_datetime(value: str) -> Optional[VariableValueDto]:
    """Try to parse a string as a datetime and return a VariableValueDto."""
    try:
        return VariableValueDto(
            value=dt_to_operaton(from_iso_to_dt(value)),
            type=VariableValueType.Date,
        )
    except ValueError:
        return None


def _try_resolve_file(
    value: str, sandbox: Optional[List[Path]]
) -> Optional[VariableValueDto]:
    """Try to resolve a string as a file path within the sandbox."""
    for path in sandbox or []:
        # Check if value is an absolute path within sandbox
        if Path(value).is_file() and value.startswith(f"{path}"):
            return _create_file_value_dto(Path(value))
        # Check if value is a relative path within sandbox
        resolved = path / value
        if resolved.is_file() and f"{resolved}".startswith(f"{path}"):
            return _create_file_value_dto(resolved)
    return None


def _convert_string(value: str, sandbox: Optional[List[Path]]) -> VariableValueDto:
    """Convert a string value to VariableValueDto, checking for datetime and file."""
    # Try parsing as datetime first
    datetime_result = _try_parse_datetime(value)
    if datetime_result is not None:  # pragma: no cover
        return datetime_result  # pragma: no cover

    # Try resolving as file
    file_result = _try_resolve_file(value, sandbox)
    if file_result is not None:  # pragma: no cover
        return file_result  # pragma: no cover

    # Default to string
    return VariableValueDto(value=value, type=VariableValueType.String)


def _convert_int(value: int) -> VariableValueDto:
    """Convert an integer to VariableValueDto, choosing Integer or Long type."""
    INT32_MIN = -(2**31)
    INT32_MAX = 2**31 - 1
    if INT32_MIN <= value <= INT32_MAX:
        return VariableValueDto(value=value, type=VariableValueType.Integer)
    return VariableValueDto(value=value, type=VariableValueType.Long)


def operaton_value_from_py(
    value: Any,
    sandbox: Optional[List[Path]] = None,
) -> VariableValueDto:
    """Convert Python value to Operaton variable value.

    Converts Python values to their corresponding Operaton variable types:
    - None -> Null
    - dict, list, tuple, set -> Json
    - bool -> Boolean
    - float -> Double
    - int -> Integer (32-bit) or Long (64-bit)
    - str -> Date (if ISO format), File (if path in sandbox), or String

    Args:
        value: The Python value to convert.
        sandbox: Optional list of paths to check for file resolution.

    Returns:
        A VariableValueDto with the appropriate type and value.
    """
    if value is None:
        return VariableValueDto(value=None, type=VariableValueType.Null)

    if isinstance(value, (dict, list, tuple, set)):
        return VariableValueDto(
            value=json.dumps(value, default=json_serializer),
            type=VariableValueType.Json,
        )

    if isinstance(value, bool):
        return VariableValueDto(value=value, type=VariableValueType.Boolean)

    if isinstance(value, float):
        return VariableValueDto(value=value, type=VariableValueType.Double)

    if isinstance(value, int):
        return _convert_int(value)

    if isinstance(value, str):
        return _convert_string(value, sandbox)

    # Fallback: convert to string
    return VariableValueDto(value=f"{value}", type=VariableValueType.String)


def operaton_from_py(
    variables: Dict[str, Any],
    sandbox: Optional[List[Path]] = None,
) -> Dict[str, VariableValueDto]:
    """Convert Python variables dict to Operaton variables dict."""
    return {
        key: operaton_value_from_py(value, sandbox) for key, value in variables.items()
    }


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for datetime and Path objects."""
    if isinstance(obj, datetime.datetime):
        local_tz = tzlocal.get_localzone()
        return (
            obj.astimezone(local_tz)
            .replace(tzinfo=None)
            .isoformat(timespec="milliseconds")
            .replace("T", " ")
        )
    elif isinstance(obj, Path):
        return f"{obj.absolute()}"
    raise TypeError(f"Type {type(obj)} not serializable")
