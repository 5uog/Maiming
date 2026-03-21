# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

__all__ = ["HudPayload", "HudController", "PlayerMetricsSnapshot", "PlayerMetricsTracker"]

def __getattr__(name: str):
    if str(name) == "HudPayload":
        from .hud_payload import HudPayload

        return HudPayload
    if str(name) == "HudController":
        from .hud_controller import HudController

        return HudController
    if str(name) == "PlayerMetricsSnapshot":
        from .player_metrics import PlayerMetricsSnapshot

        return PlayerMetricsSnapshot
    if str(name) == "PlayerMetricsTracker":
        from .player_metrics import PlayerMetricsTracker

        return PlayerMetricsTracker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")