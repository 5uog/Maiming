# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/shared/presentation/opengl/runtime/render_metrics.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PassFrameMetrics:
    cpu_ms: float = 0.0
    draw_calls: int = 0
    instances: int = 0
    rendered: bool = False


@dataclass(frozen=True)
class RendererFrameMetrics:
    world: PassFrameMetrics = field(default_factory=PassFrameMetrics)
    shadow: PassFrameMetrics = field(default_factory=PassFrameMetrics)
