# FILE: src/maiming/domain/blocks/state_values.py
from __future__ import annotations

from collections.abc import Mapping

def bool_str(v: bool) -> str:
    return "true" if bool(v) else "false"

def str_as_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return bool(default)

    s = str(raw).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return bool(default)

def prop_as_bool(props: Mapping[str, str], key: str, default: bool = False) -> bool:
    return str_as_bool(props.get(str(key)), default)