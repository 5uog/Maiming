# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Dict, List

from .common import LocalBox

def boxes_for_slab(props: Dict[str, str]) -> List[LocalBox]:
    t = str(props.get("type", "bottom"))
    if t == "top":
        return [LocalBox(0.0, 0.5, 0.0, 1.0, 1.0, 1.0)]
    if t == "double":
        return [LocalBox(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)]
    return [LocalBox(0.0, 0.0, 0.0, 1.0, 0.5, 1.0)]