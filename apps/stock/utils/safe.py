# apps/stock/utils/safe.py
import math
from datetime import datetime, date, time as dtime
from typing import Any, Optional

def _is_nan(v: Any) -> bool:
    return isinstance(v, float) and math.isnan(v)

def safe_decimal(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        if value is None or _is_nan(value):
            return default
        return float(value)
    except Exception:
        return default

def safe_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
    try:
        if value is None or _is_nan(value):
            return default
        return int(value)
    except Exception:
        return default

def safe_str(value: Any, default: str = "") -> str:
    try:
        if value is None or _is_nan(value):
            return default
        return str(value)
    except Exception:
        return default

def safe_date_passthrough(value: Any):
    try:
        if value is None or _is_nan(value):
            return None
        return value
    except Exception:
        return None

def to_epoch_seconds(value: Any) -> Optional[int]:
    try:
        if value is None or _is_nan(value):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, datetime):
            return int(value.timestamp())
        if isinstance(value, date):
            return int(datetime.combine(value, dtime.min).timestamp())
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except Exception:
                try:
                    return int(float(value))
                except Exception:
                    return None
    except Exception:
        return None
    return None

def to_datetime(value: Any) -> Optional[datetime]:
    try:
        if value is None or _is_nan(value):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value))
        if isinstance(value, date):
            return datetime.combine(value, dtime.min)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                try:
                    return datetime.fromtimestamp(float(value))
                except Exception:
                    return None
    except Exception:
        return None
    return None

def iso_str_or_none(value: Any) -> Optional[str]:
    """Trả về ISO string (dùng cho SymbolOut.update_time)."""
    dt = to_datetime(value)
    return dt.isoformat() if dt else None
