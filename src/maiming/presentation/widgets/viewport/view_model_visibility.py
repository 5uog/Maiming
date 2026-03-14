# FILE: src/maiming/presentation/widgets/viewport/view_model_visibility.py
from __future__ import annotations

def view_model_visible(*, hide_hand: bool) -> bool:
    return not bool(hide_hand)