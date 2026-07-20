"""Utilities for the Birthday Card Helper"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, cast


def pretty_print(value: object) -> None:
    print(json.dumps(_json_safe_value(value), indent=2))


def _json_safe_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        dataclass_value = cast(Any, value)
        return _json_safe_value(asdict(dataclass_value))

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}

    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]

    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]

    return value
