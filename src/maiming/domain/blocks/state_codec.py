# FILE: src/maiming/domain/blocks/state_codec.py
from __future__ import annotations

from typing import Dict, Tuple

def parse_state(s: str) -> Tuple[str, Dict[str, str]]:
    raw = str(s)
    if "|" not in raw:
        return raw, {}

    base, tail = raw.split("|", 1)
    base = str(base)
    props: Dict[str, str] = {}

    tail = str(tail).strip()
    if not tail:
        return base, props

    for frag in tail.split(","):
        frag = frag.strip()
        if not frag:
            continue
        if "=" not in frag:
            continue
        k, v = frag.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        props[str(k)] = str(v)

    return base, props

def format_state(base_id: str, props: Dict[str, str] | None) -> str:
    base = str(base_id)
    if props is None or not props:
        return base

    items = [(str(k), str(v)) for (k, v) in props.items() if str(k)]
    if not items:
        return base

    items.sort(key=lambda kv: kv[0])
    tail = ",".join([f"{k}={v}" for (k, v) in items])
    return f"{base}|{tail}"