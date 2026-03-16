# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/infrastructure/persistence/scalar_coercion.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def coerce_float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def coerce_int(value: object, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, (bool, int)):
        return bool(value)
    return bool(default)


def coerce_str(value: object, default: str) -> str:
    if value is None:
        return str(default)
    return str(value)


def mapping_float(d: Mapping[str, Any], key: str, default: float) -> float:
    return coerce_float(d.get(str(key), default), float(default))


def mapping_int(d: Mapping[str, Any], key: str, default: int) -> int:
    return coerce_int(d.get(str(key), default), int(default))


def mapping_bool(d: Mapping[str, Any], key: str, default: bool) -> bool:
    return coerce_bool(d.get(str(key), default), bool(default))


def mapping_str(d: Mapping[str, Any], key: str, default: str) -> str:
    return coerce_str(d.get(str(key), default), str(default))
