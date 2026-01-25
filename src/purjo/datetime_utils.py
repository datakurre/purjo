"""Date and time conversion utilities for Operaton."""

import datetime
import tzlocal


def from_iso_to_dt(iso_str: str) -> datetime.datetime:
    """Convert ISO string to datetime with local timezone if naive."""
    dt = datetime.datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:  # If naive, assign local timezone
        local_tz = tzlocal.get_localzone()
        dt = dt.replace(tzinfo=local_tz)
    return dt


def dt_from_operaton(date_str: str) -> datetime.datetime:
    """Convert Operaton ISO format to Python datetime."""
    if (date_str[-5] == "+" or date_str[-5] == "-") and date_str[-3] != ":":
        date_str = date_str[:-2] + ":" + date_str[-2:]
    return datetime.datetime.fromisoformat(date_str)


def dt_to_operaton(dt: datetime.datetime) -> str:
    """Convert Python datetime to Operaton ISO format."""
    date_str = dt.isoformat(timespec="milliseconds")
    if dt.utcoffset() is None:
        return f"{date_str}+0000"
    if date_str[-3] == ":":
        return f"{date_str[:-3]}{date_str[-2:]}"
    return date_str  # pragma: no cover
