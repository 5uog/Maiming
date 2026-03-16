# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/domain/blocks/state_values.py
from __future__ import annotations

from collections.abc import Mapping


def bool_str(v: bool) -> str:
    return "true" if bool(v) else "false"


def str_as_bool(raw: str | None, default: bool=False) -> bool:
    if raw is None:
        return bool(default)

    s = str(raw).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return bool(default)


def prop_as_bool(props: Mapping[str, str], key: str, default: bool=False) -> bool:
    return str_as_bool(props.get(str(key)), default)


def prop_as_str(props: Mapping[str, str], key: str, default: str="") -> str:
    raw = props.get(str(key))
    if raw is None:
        return str(default)
    return str(raw)


def slab_type_value(props: Mapping[str, str], default: str="bottom") -> str:
    t = prop_as_str(props, "type", default).strip()
    if t in ("bottom", "top", "double"):
        return t

    d = str(default).strip()
    if d in ("bottom", "top", "double"):
        return d

    return "bottom"
