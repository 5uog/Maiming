# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/viewport/view_model_visibility.py
from __future__ import annotations


def view_model_visible(*, hide_hand: bool) -> bool:
    return not bool(hide_hand)
