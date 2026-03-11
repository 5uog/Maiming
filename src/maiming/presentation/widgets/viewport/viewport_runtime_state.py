# FILE: src/maiming/presentation/widgets/viewport/viewport_runtime_state.py
from __future__ import annotations

from dataclasses import dataclass, field

from ....domain.inventory.hotbar import HOTBAR_SIZE, current_hotbar_block_id, cycle_hotbar_index, normalize_hotbar_index, normalize_hotbar_slots, with_hotbar_assignment
from ....infrastructure.rendering.opengl.facade.cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION, normalize_cloud_flow_direction

def _default_hotbar_slots() -> list[str]:
    return list(normalize_hotbar_slots(None, size=HOTBAR_SIZE))

@dataclass
class ViewportRuntimeState:
    invert_x: bool = False
    invert_y: bool = False

    outline_selection: bool = True

    cloud_wire: bool = False
    cloud_enabled: bool = True
    cloud_density: int = 1
    cloud_seed: int = 1337
    cloud_flow_direction: str = DEFAULT_CLOUD_FLOW_DIRECTION

    world_wire: bool = False
    shadow_enabled: bool = True

    build_mode: bool = False
    hotbar_slots: list[str] = field(default_factory=_default_hotbar_slots)
    selected_hotbar_index: int = 0
    reach: float = 5.0
    auto_jump_enabled: bool = False
    auto_sprint_enabled: bool = False

    render_distance_chunks: int = 6

    sun_az_deg: float = 45.0
    sun_el_deg: float = 60.0

    debug_shadow: bool = False
    vsync_on: bool = False

    hud_visible: bool = False

    def normalize(self) -> None:
        self.cloud_density = int(max(0, min(4, int(self.cloud_density))))
        self.cloud_seed = int(max(0, min(9999, int(self.cloud_seed))))
        self.cloud_flow_direction = normalize_cloud_flow_direction(str(self.cloud_flow_direction))

        self.render_distance_chunks = int(max(2, min(16, int(self.render_distance_chunks))))

        reach = float(self.reach)
        self.reach = 0.0 if reach < 0.0 else reach

        az = float(self.sun_az_deg) % 360.0
        if az < 0.0:
            az += 360.0
        self.sun_az_deg = az

        el = float(self.sun_el_deg)
        self.sun_el_deg = max(0.0, min(90.0, el))

        self.hotbar_slots = list(normalize_hotbar_slots(self.hotbar_slots, size=HOTBAR_SIZE))
        self.selected_hotbar_index = normalize_hotbar_index(self.selected_hotbar_index, size=HOTBAR_SIZE)

    def hotbar_snapshot(self) -> tuple[str, ...]:
        self.normalize()
        return normalize_hotbar_slots(self.hotbar_slots, size=HOTBAR_SIZE)

    def current_block_id(self) -> str | None:
        self.normalize()
        return current_hotbar_block_id(self.hotbar_slots, self.selected_hotbar_index, size=HOTBAR_SIZE)

    def set_hotbar_slot(self, index: int, block_id: str | None) -> None:
        self.normalize()
        self.hotbar_slots = list(with_hotbar_assignment(self.hotbar_slots, index, block_id, size=HOTBAR_SIZE))

    def select_hotbar_index(self, index: int) -> None:
        self.normalize()
        self.selected_hotbar_index = normalize_hotbar_index(index, size=HOTBAR_SIZE)

    def cycle_hotbar(self, delta_steps: int) -> None:
        self.normalize()
        self.selected_hotbar_index = cycle_hotbar_index(self.selected_hotbar_index, delta_steps, size=HOTBAR_SIZE)