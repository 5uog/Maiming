# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from importlib import import_module

__all__ = ["PlaySpaceContext"]

def __getattr__(name: str):
    if name == "PlaySpaceContext":
        module = import_module(".play_space_context", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))