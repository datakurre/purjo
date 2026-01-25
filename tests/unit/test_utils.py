"""Unit tests for utils.py module.

Related User Stories:
- US-001: Serve robot packages (variable handling)
- US-015: Provide variables (serialization utilities)

Related ADRs:
- ADR-003: Architecture overview
"""

from javaobj.v2.beans import JavaString  # type: ignore[import-untyped]  # type: ignore[import-untyped]
from javaobj.v2.transformers import JavaBool  # type: ignore[import-untyped]  # type: ignore[import-untyped]
from javaobj.v2.transformers import JavaInt
from javaobj.v2.transformers import JavaList
from javaobj.v2.transformers import JavaMap
from operaton.tasks.types import VariableValueDto
from operaton.tasks.types import VariableValueType
from pathlib import Path
from purjo.utils import data_uri
from purjo.utils import deserialize
from purjo.utils import dt_from_operaton
from purjo.utils import dt_to_operaton
from purjo.utils import from_iso_to_dt
from purjo.utils import get_wrap_pathspec
from purjo.utils import inline_screenshots
from purjo.utils import json_serializer
from purjo.utils import lazydecode
from purjo.utils import lazypprint
from purjo.utils import operaton_from_py
from purjo.utils import operaton_value_from_py
from purjo.utils import py_from_javaobj
from purjo.utils import ValueInfo
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
import asyncio
import base64
import datetime
import json
import pytest
import tzlocal


class TestGetWrapPathspec:
    """Tests for get_wrap_pathspec function."""

    def test_with_existing_wrapignore(self, temp_dir: Path) -> None:
        """Test pathspec with existing .wrapignore file."""
        wrapignore = temp_dir / ".wrapignore"
        wrapignore.write_text("*.log\n*.tmp\n")

        spec = get_wrap_pathspec(temp_dir)

        assert spec.match_file("test.log")
        assert spec.match_file("test.tmp")
        assert spec.match_file(".git/config")
        assert not spec.match_file("test.robot")

    def test_without_wrapignore(self, temp_dir: Path) -> None:
        """Test pathspec without .wrapignore file."""
        spec = get_wrap_pathspec(temp_dir)

        # Should match default excludes
        assert spec.match_file(".git/config")
        assert spec.match_file("log.html")
        assert spec.match_file("output.xml")
        assert spec.match_file("report.html")
        assert spec.match_file("__pycache__/test.pyc")
        assert not spec.match_file("test.robot")

    def test_default_excludes(self, temp_dir: Path) -> None:
        """Test that default excludes are applied."""
        spec = get_wrap_pathspec(temp_dir)

        default_excludes = [
            ".git",
            ".devenv",
            ".gitignore",
            "log.html",
            "output.xml",
            "__pycache__/",
            "report.html",
            "robot.zip",
            ".venv/",
            ".wrapignore",
            ".cache",
        ]

        for exclude in default_excludes:
            assert spec.match_file(exclude)


class TestFromIsoToDt:
    """Tests for from_iso_to_dt function."""

    def test_naive_datetime(self) -> None:
        """Test naive datetime (no timezone) gets local timezone."""
        iso_str = "2024-01-01T10:00:00"
        result = from_iso_to_dt(iso_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 10
        assert result.tzinfo is not None
        assert result.tzinfo == tzlocal.get_localzone()

    def test_datetime_with_timezone(self) -> None:
        """Test datetime with timezone."""
        iso_str = "2024-01-01T10:00:00+02:00"
        result = from_iso_to_dt(iso_str)

        assert result.year == 2024
        assert result.tzinfo is not None

    def test_various_iso_formats(self) -> None:
        """Test various ISO format strings."""
        test_cases = [
            "2024-01-01T10:00:00",
            "2024-01-01T10:00:00.123456",
            "2024-01-01T10:00:00+00:00",
            "2024-01-01T10:00:00-05:00",
        ]

        for iso_str in test_cases:
            result = from_iso_to_dt(iso_str)
            assert isinstance(result, datetime.datetime)
            assert result.tzinfo is not None


class TestDtFromOperaton:
    """Tests for dt_from_operaton function."""

    def test_standard_operaton_format(self) -> None:
        """Test standard Operaton date format."""
        date_str = "2024-01-01T10:00:00.000+0200"
        result = dt_from_operaton(date_str)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 10

    def test_timezone_offset_without_colon(self) -> None:
        """Test timezone offset without colon."""
        date_str = "2024-01-01T10:00:00.000+0200"
        result = dt_from_operaton(date_str)

        assert isinstance(result, datetime.datetime)

    def test_timezone_offset_with_colon(self) -> None:
        """Test timezone offset with colon."""
        date_str = "2024-01-01T10:00:00.000+02:00"
        result = dt_from_operaton(date_str)

        assert isinstance(result, datetime.datetime)


class TestDtToOperaton:
    """Tests for dt_to_operaton function."""

    def test_datetime_without_timezone(self) -> None:
        """Test datetime without timezone."""
        dt = datetime.datetime(2024, 1, 1, 10, 0, 0)
        result = dt_to_operaton(dt)

        assert result.startswith("2024-01-01T10:00:00")
        assert result.endswith("+0000")

    def test_datetime_with_timezone(self) -> None:
        """Test datetime with timezone."""
        tz = datetime.timezone(datetime.timedelta(hours=2))
        dt = datetime.datetime(2024, 1, 1, 10, 0, 0, tzinfo=tz)
        result = dt_to_operaton(dt)

        assert "2024-01-01T10:00:00" in result
        assert "+0200" in result

    def test_format_matches_operaton(self) -> None:
        """Verify format matches Operaton expectations."""
        dt = datetime.datetime(2024, 1, 1, 10, 0, 0, 123000)
        result = dt_to_operaton(dt)

        # Should have milliseconds
        assert "123" in result
        # Should end with timezone
        assert result.endswith("+0000")


class TestPyFromJavaobj:
    """Tests for py_from_javaobj function."""

    def test_javamap_conversion(self) -> None:
        """Test JavaMap conversion."""
        # Mock JavaString objects
        java_key1 = MagicMock(spec=JavaString)
        java_key1.__str__.return_value = "key1"  # type: ignore[attr-defined]
        java_val1 = MagicMock(spec=JavaString)
        java_val1.__str__.return_value = "value1"  # type: ignore[attr-defined]
        java_key2 = MagicMock(spec=JavaString)
        java_key2.__str__.return_value = "key2"  # type: ignore[attr-defined]
        java_val2 = MagicMock(spec=JavaInt)
        java_val2.__int__.return_value = 42

        java_map = JavaMap()
        java_map[java_key1] = java_val1
        java_map[java_key2] = java_val2

        result = py_from_javaobj(java_map)

        assert isinstance(result, dict)
        assert result["key1"] == "value1"
        assert result["key2"] == 42

    def test_javalist_conversion(self) -> None:
        """Test JavaList conversion."""
        # Mock JavaString and JavaInt objects
        java_str = MagicMock(spec=JavaString)
        java_str.__str__.return_value = "item1"  # type: ignore[attr-defined]
        java_int = MagicMock(spec=JavaInt)
        java_int.__int__.return_value = 42

        java_list = JavaList()
        java_list.append(java_str)
        java_list.append(java_int)

        result = py_from_javaobj(java_list)

        assert isinstance(result, list)
        assert result[0] == "item1"
        assert result[1] == 42

    def test_javastring_conversion(self) -> None:
        """Test JavaString conversion."""
        java_str = MagicMock(spec=JavaString)
        java_str.__str__.return_value = "hello"  # type: ignore[attr-defined]

        result = py_from_javaobj(java_str)

        assert result == "hello"
        assert isinstance(result, str)

    def test_javaint_conversion(self) -> None:
        """Test JavaInt conversion."""
        java_int = MagicMock(spec=JavaInt)
        java_int.__int__.return_value = 42

        result = py_from_javaobj(java_int)

        assert result == 42
        assert isinstance(result, int)

    def test_javabool_conversion(self) -> None:
        """Test JavaBool conversion."""
        java_bool = MagicMock(spec=JavaBool)
        java_bool.__bool__.return_value = True

        result = py_from_javaobj(java_bool)

        assert result is True
        assert isinstance(result, bool)

    def test_unsupported_type_raises_error(self) -> None:
        """Test unsupported type raises TypeError."""
        unsupported = object()

        with pytest.raises(TypeError, match="not serializable"):
            py_from_javaobj(unsupported)


class TestDeserialize:
    """Tests for deserialize function."""

    def test_with_none_value(self) -> None:
        """Test with None value."""
        result = deserialize(None, VariableValueType.String, None)
        assert result is None

    def test_with_none_type(self) -> None:
        """Test with None type."""
        result = deserialize("test", None, None)
        assert result == "test"

    def test_date_type_conversion(self) -> None:
        """Test Date type conversion."""
        date_str = "2024-01-01T10:00:00.000+0200"
        result = deserialize(date_str, VariableValueType.Date, None)

        assert isinstance(result, datetime.datetime)

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization."""
        json_str = '{"key": "value"}'
        info = ValueInfo(serializationDataFormat="application/json")
        result = deserialize(json_str, VariableValueType.Json, info)

        assert isinstance(result, dict)
        assert result["key"] == "value"

    @patch("purjo.serialization.javaobj.load")
    def test_java_serialized_object(self, mock_javaobj_load: Any) -> None:
        """Test Java serialized object deserialization."""
        # Mock JavaString objects
        java_key = MagicMock(spec=JavaString)
        java_key.__str__.return_value = "key"  # type: ignore[attr-defined]
        java_val = MagicMock(spec=JavaString)
        java_val.__str__.return_value = "value"  # type: ignore[attr-defined]

        java_map = JavaMap()
        java_map[java_key] = java_val
        mock_javaobj_load.return_value = java_map

        encoded = base64.b64encode(b"test_data").decode("utf-8")
        info = ValueInfo(serializationDataFormat="application/x-java-serialized-object")
        result = deserialize(encoded, VariableValueType.Object, info)

        assert isinstance(result, dict)
        assert result["key"] == "value"


class TestOperatonValueFromPy:
    """Tests for operaton_value_from_py function."""

    def test_none_to_null(self) -> None:
        """Test None → Null type."""
        result = operaton_value_from_py(None)

        assert result.value is None
        assert result.type == VariableValueType.Null

    def test_dict_to_json(self) -> None:
        """Test dict → Json type."""
        result = operaton_value_from_py({"key": "value"})

        assert result.type == VariableValueType.Json
        assert json.loads(result.value) == {"key": "value"}  # type: ignore[arg-type]  # type: ignore[arg-type]

    def test_list_to_json(self) -> None:
        """Test list → Json type."""
        result = operaton_value_from_py([1, 2, 3])

        assert result.type == VariableValueType.Json
        assert json.loads(result.value) == [1, 2, 3]  # type: ignore[arg-type]  # type: ignore[arg-type]

    def test_bool_to_boolean(self) -> None:
        """Test bool → Boolean type."""
        result = operaton_value_from_py(True)

        assert result.value is True
        assert result.type == VariableValueType.Boolean

    def test_float_to_double(self) -> None:
        """Test float → Double type."""
        result = operaton_value_from_py(3.14)

        assert result.value == 3.14
        assert result.type == VariableValueType.Double

    def test_small_int_to_integer(self) -> None:
        """Test small int → Integer type."""
        result = operaton_value_from_py(42)

        assert result.value == 42
        assert result.type == VariableValueType.Integer

    def test_large_int_to_long(self) -> None:
        """Test large int → Long type."""
        large_int = 2**31  # Beyond INT32
        result = operaton_value_from_py(large_int)

        assert result.value == large_int
        assert result.type == VariableValueType.Long

    def test_file_path_detection(self, temp_dir: Path) -> None:
        """Test file path detection and encoding."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello")

        result = operaton_value_from_py(str(test_file), sandbox=[temp_dir])

        assert result.type == VariableValueType.File
        assert result.valueInfo["filename"] == "test.txt"  # type: ignore[index]  # type: ignore[index]
        # Verify base64 encoding
        decoded = base64.b64decode(result.value)  # type: ignore[arg-type]  # type: ignore[arg-type]
        assert decoded == b"hello"

    def test_str_to_string(self) -> None:
        """Test str → String type."""
        result = operaton_value_from_py("hello")

        assert result.value == "hello"
        assert result.type == VariableValueType.String


class TestOperatonFromPy:
    """Tests for operaton_from_py function."""

    def test_dict_conversion_with_mixed_types(self) -> None:
        """Test dict conversion with mixed types."""
        variables = {
            "string": "hello",
            "number": 42,
            "bool": True,
            "data": {"key": "value"},
        }

        result = operaton_from_py(variables)

        assert len(result) == 4
        assert result["string"].type == VariableValueType.String
        assert result["number"].type == VariableValueType.Integer
        assert result["bool"].type == VariableValueType.Boolean
        assert result["data"].type == VariableValueType.Json


class TestJsonSerializer:
    """Tests for json_serializer function."""

    def test_datetime_serialization(self) -> None:
        """Test datetime serialization."""
        dt = datetime.datetime(2024, 1, 1, 10, 0, 0, 123000)
        result = json_serializer(dt)

        assert isinstance(result, str)
        assert "2024-01-01 10:00:00" in result
        assert "123" in result  # milliseconds

    def test_path_serialization(self) -> None:
        """Test Path serialization."""
        path = Path("/tmp/test.txt")
        result = json_serializer(path)

        assert isinstance(result, str)
        assert "test.txt" in result

    def test_unsupported_type_raises_error(self) -> None:
        """Test unsupported type raises TypeError."""
        unsupported = object()

        with pytest.raises(TypeError, match="not serializable"):
            json_serializer(unsupported)


class TestLazypprint:
    """Tests for lazypprint class."""

    def test_str_method(self) -> None:
        """Test __str__ method."""
        data = {"key": "value", "nested": {"a": 1, "b": 2}}
        lazy = lazypprint(data)

        result = str(lazy)

        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result
        assert "nested" in result


class TestLazydecode:
    """Tests for lazydecode class."""

    def test_single_bytes(self) -> None:
        """Test with single bytes object."""
        data = b"hello"
        lazy = lazydecode(data)

        result = str(lazy)

        assert result == "hello"

    def test_multiple_bytes(self) -> None:
        """Test with multiple bytes objects."""
        data1 = b"hello"
        data2 = b"world"
        lazy = lazydecode(data1, data2)

        result = str(lazy)

        assert result == "hello\nworld"


class TestInlineScreenshots:
    """Tests for inline_screenshots function."""

    def test_with_matching_image_files(self, temp_dir: Path) -> None:
        """Test with matching image files."""
        # Create test image
        img_file = temp_dir / "screenshot.png"
        img_file.write_bytes(b"fake image data")

        # Create HTML with image reference
        html_file = temp_dir / "report.html"
        html_content = (
            f'<html><body><img src="screenshot.png" width="800px"></body></html>'
        )
        html_file.write_text(html_content)

        # Change to temp directory so inline_screenshots can find the image
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            inline_screenshots(html_file)
        finally:
            os.chdir(old_cwd)

        result = html_file.read_text()
        assert "data:image/png;base64," in result
        assert "screenshot.png" not in result

    def test_with_missing_image_files(self, temp_dir: Path) -> None:
        """Test with missing image files."""
        html_file = temp_dir / "report.html"
        html_content = '<html><body><img src="missing.png"></body></html>'
        html_file.write_text(html_content)

        inline_screenshots(html_file)

        result = html_file.read_text()
        # Should not change if file doesn't exist
        assert "missing.png" in result


class TestDataUri:
    """Tests for data_uri function."""

    def test_various_mimetypes(self) -> None:
        """Test various mimetypes."""
        data = b"test data"

        result_png = data_uri("image/png", data)
        assert result_png.startswith("data:image/png;base64,")

        result_txt = data_uri("text/plain", data)
        assert result_txt.startswith("data:text/plain;base64,")

    def test_base64_encoding(self) -> None:
        """Verify base64 encoding."""
        data = b"hello world"
        result = data_uri("text/plain", data)

        # Extract base64 part
        base64_part = result.split(",")[1]
        decoded = base64.b64decode(base64_part)
        assert decoded == data


class TestDeserializeEdgeCases:
    """Edge case tests for deserialize function."""

    def test_unknown_serialization_format(self) -> None:
        """Test unknown serialization format raises NotImplementedError."""
        info = ValueInfo(serializationDataFormat="application/unknown")

        with pytest.raises(NotImplementedError):
            deserialize("value", VariableValueType.String, info)

    def test_none_serialization_format_with_info(self) -> None:
        """Test with info object but None serializationDataFormat."""
        info = ValueInfo(serializationDataFormat=None)
        result = deserialize("test", VariableValueType.String, info)

        assert result == "test"


class TestOperatonValueFromPyEdgeCases:
    """Edge case tests for operaton_value_from_py function."""

    def test_fallback_to_string(self) -> None:
        """Test fallback conversion for unsupported types."""

        # Create a custom class to trigger fallback
        class CustomObject:
            def __str__(self) -> str:
                return "custom_string"

        result = operaton_value_from_py(CustomObject())

        assert result.type == VariableValueType.String
        assert result.value == "custom_string"

    def test_file_resolution_in_sandbox(self, temp_dir: Path) -> None:
        """Test file resolution with sandbox directories."""
        # Create a test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # Use relative path with sandbox
        result = operaton_value_from_py("test.txt", [temp_dir])

        assert result.type == VariableValueType.File
        assert result.valueInfo is not None
        assert result.valueInfo.get("filename") == "test.txt"

    def test_file_resolution_absolute_path(self, temp_dir: Path) -> None:
        """Test file resolution with absolute path in sandbox."""
        # Create a test file
        test_file = temp_dir / "absolute.txt"
        test_file.write_text("absolute content")

        # Use absolute path with sandbox
        result = operaton_value_from_py(str(test_file), [temp_dir])

        assert result.type == VariableValueType.File
        assert result.valueInfo is not None
        assert result.valueInfo.get("filename") == "absolute.txt"

    def test_file_outside_sandbox(self, temp_dir: Path) -> None:
        """Test file outside sandbox is not resolved."""
        # Create a file in a sibling directory
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"content")
            outside_file = Path(f.name)

        try:
            # File exists but is outside sandbox
            result = operaton_value_from_py(str(outside_file), [temp_dir])

            # Should be treated as string, not file
            assert result.type == VariableValueType.String
        finally:
            outside_file.unlink()
