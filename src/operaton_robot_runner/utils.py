from io import BytesIO
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from PIL import Image
from pydantic import BaseModel
from typing import Any
from typing import Dict
from typing import Optional
from urllib.parse import unquote
import base64
import binascii
import datetime
import javaobj.v2 as javaobj  # type: ignore
import json
import os
import pprint
import re


class ValueInfo(BaseModel):
    objectTypeName: Optional[str] = None
    serializationDataFormat: Optional[str] = None


def dt_from_operaton(date_str: str) -> datetime.datetime:
    """Convert Operaton ISO format to Python ISO format."""
    if (date_str[-5] == "+" or date_str[-5] == "-") and date_str[-3] != ":":
        date_str = date_str[:-2] + ":" + date_str[-2:]
    return datetime.datetime.fromisoformat(date_str)


def dt_to_operaton(dt: datetime.datetime) -> str:
    """Convert Python ISO format to Operaton ISO format."""
    date_str = dt.isoformat(timespec="milliseconds")
    if dt.utcoffset() is None:
        return f"{date_str}+0000"
    if date_str[-3] == ":":
        return f"{date_str[:-3]}{date_str[-2:]}"
    return date_str


def deserialize(
    value: Any,
    type_: Optional[VariableValueType] = None,
    info: Optional[ValueInfo] = None,
) -> Any:
    if (
        value is None
        or type_ is None
        or info is None
        or info.serializationDataFormat is None
    ):
        return value
    elif type_ == VariableValueType.Date:
        return dt_from_operaton(value)
    elif info.serializationDataFormat is None:
        return value
    elif info.serializationDataFormat == "application/json":
        return json.loads(value)
    elif info.serializationDataFormat == "application/x-java-serialized-object":
        return javaobj.load(BytesIO(base64.b64decode(value)))
    raise NotImplementedError(info.serializationDataFormat)


def py_from_operaton(
    variables: Optional[Dict[str, VariableValueDto]]
) -> Dict[str, Any]:
    return {
        key: deserialize(
            variable.value,
            VariableValueType(variable.type) if variable.type else None,
            ValueInfo(**variable.valueInfo) if variable.valueInfo else None,
        )
        for key, variable in (variables.items() if variables is not None else ())
        if variable.type not in (VariableValueType.File, VariableValueType.Bytes)
    }


def json_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class lazypprint:
    def __init__(self, data: Any) -> None:
        self.data = data

    def __str__(self) -> str:
        return pprint.pformat(self.data)


class lazydecode:
    def __init__(self, *data: bytes) -> None:
        self.data = data

    def __str__(self) -> str:
        return "\n".join([b.decode() for b in self.data])


def inline_screenshots(file_path: str) -> None:
    data_str = ""
    data_bytes = b""
    mimetype = None
    cwd = os.getcwd()
    with open(file_path, encoding="utf-8") as fp:
        data_str = fp.read()
    for src in re.findall('img src="([^"]+)', data_str):
        if os.path.exists(src):
            filename = src
        elif os.path.exists(os.path.join(file_path, src)):
            filename = os.path.join(file_path, src)
        elif os.path.exists(os.path.join(cwd, src)):
            filename = os.path.join(cwd, src)
        elif src.startswith("data:"):
            filename = None
            try:
                spec, uri = src.split(",", 1)
                spec, encoding = spec.split(";", 1)
                spec, mimetype = spec.split(":", 1)
                if not (encoding == "base64" and mimetype.startswith("image/")):
                    continue
                data_ = base64.b64decode(unquote(uri).encode("utf-8"))
                Image.open(BytesIO(data_))
            except (binascii.Error, IndexError, ValueError):
                continue
        else:
            continue
        if filename:
            im = Image.open(filename)
            mimetype = (Image.MIME.get(im.format) if im and im.format else None) or ""
            # Fix issue where Pillow on Windows returns APNG for PNG
            if mimetype == "image/apng":
                mimetype = "image/png"
            with open(filename, "rb") as fp:
                data_bytes = fp.read()
        if data_bytes and mimetype:
            uri = data_uri(mimetype, data_bytes)
            data_str = data_str.replace(f'a href="{src}"', "a")
            data_str = data_str.replace(
                f'img src="{src}" width="800px"',
                f'img src="{uri}" style="max-width:800px;"',
            )  # noqa: E501
            data_str = data_str.replace(f'img src="{src}"', f'img src="{uri}"')
    with open(file_path, "w", encoding="utf-8") as fp:
        fp.write(data_str)


def data_uri(mimetype: str, data: bytes) -> str:
    return "data:{};base64,{}".format(  # noqa: C0209
        mimetype, base64.b64encode(data).decode("utf-8")
    )
