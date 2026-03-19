# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/managers/__init__.py
from __future__ import annotations

from importlib import import_module

__all__ = ["SessionManager", "SessionStepResult"]


def __getattr__(name: str):
    if name in {"SessionManager", "SessionStepResult"}:
        module = import_module(".session_manager", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
