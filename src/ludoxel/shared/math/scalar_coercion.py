# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_BOOL_TRUE_TOKENS = frozenset({"1", "true", "yes", "on"})
_BOOL_FALSE_TOKENS = frozenset({"0", "false", "no", "off"})


def coerce_float(value: object, default: float) -> float:
    """I define C_R(value; d) = float(value) when float(value) is admissible and = float(d) otherwise. I keep this total map in shared math because persisted scalar recovery and UI decoding both require the same failure-stable real coercion."""
    try:
        return float(value)
    except Exception:
        return float(default)


def coerce_int(value: object, default: int) -> int:
    """I define C_Z(value; d) = int(value) when integer coercion is admissible and = int(d) otherwise. I use this total integer decoder wherever serialized counters, dimensions, and indices must survive malformed input."""
    try:
        return int(value)
    except Exception:
        return int(default)


def coerce_bool(value: object, default: bool) -> bool:
    """I define C_B(value; d) as a total boolean decoder over {bool,int,float,str}. Numeric inputs follow the predicate x != 0, canonical string tokens are interpreted through two finite truth tables, and every non-decodable residue collapses to d."""
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = str(value).strip().lower()
        if token in _BOOL_TRUE_TOKENS:
            return True
        if token in _BOOL_FALSE_TOKENS:
            return False
    return bool(default)


def coerce_str(value: object, default: str) -> str:
    """I define C_S(value; d) = str(value) for every non-None operand and = str(d) on the null branch. I centralize this coercion because persistence payloads repeatedly admit optional textual fields with the same total-fallback rule."""
    if value is None:
        return str(default)
    return str(value)


def mapping_float(d: Mapping[str, Any], key: str, default: float) -> float:
    """I define M_R(d, k; a) = C_R(d.get(k, a); a). This composition realizes a total real-valued dictionary projection with explicit default preservation."""
    return coerce_float(d.get(str(key), default), float(default))


def mapping_int(d: Mapping[str, Any], key: str, default: int) -> int:
    """I define M_Z(d, k; a) = C_Z(d.get(k, a); a). I use this operator to decode persisted integer branches without duplicating missing-key and malformed-value handling."""
    return coerce_int(d.get(str(key), default), int(default))


def mapping_bool(d: Mapping[str, Any], key: str, default: bool) -> bool:
    """I define M_B(d, k; a) = C_B(d.get(k, a); a). This gives persistence code a total boolean projection with the same lexical token semantics used elsewhere in the codebase."""
    return coerce_bool(d.get(str(key), default), bool(default))


def mapping_str(d: Mapping[str, Any], key: str, default: str) -> str:
    """I define M_S(d, k; a) = C_S(d.get(k, a); a). This keeps textual dictionary extraction total while preserving the declared default branch exactly."""
    return coerce_str(d.get(str(key), default), str(default))
