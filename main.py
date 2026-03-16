# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: main.py
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"

if _SRC.exists():
    sys.path.insert(0, str(_SRC))

from ludoxel.api import run_app  # noqa: E402

if __name__ == "__main__":
    run_app()
