# FILE: src/maiming/presentation/widgets/viewport/viewport_runtime_state.py
from __future__ import annotations

from dataclasses import dataclass, field

from ....infrastructure.rendering.opengl.facade.cloud_flow_direction import normalize_cloud_flow_direction

def _default_hotbar_slots() -> list[str]:
    return ["", "", "", "", "", "", "", "", ""]

@dataclass
class ViewportRuntimeState:
    invert_x: bool = False
    invert_y: bool = False

    outline_selection: bool = True

    cloud_wire: bool = False
    cloud_enabled: bool = True
    cloud_density: int = 1
    cloud_seed: int = 1337
    cloud_flow_direction: str = "west_to_east"

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

        slots_in = list(self.hotbar_slots) if isinstance(self.hotbar_slots, list) else list(self.hotbar_slots or [])
        slots_out: list[str] = []
        for raw in slots_in[:9]:
            if raw is None:
                slots_out.append("")
            else:
                slots_out.append(str(raw).strip())

        while len(slots_out) < 9:
            slots_out.append("")

        self.hotbar_slots = slots_out[:9]
        self.selected_hotbar_index = int(max(0, min(8, int(self.selected_hotbar_index))))

    def hotbar_snapshot(self) -> tuple[str, ...]:
        self.normalize()
        return tuple(str(v) for v in self.hotbar_slots[:9])

    def current_block_id(self) -> str | None:
        self.normalize()
        bid = str(self.hotbar_slots[self.selected_hotbar_index]).strip()
        return bid if bid else None

    def set_hotbar_slot(self, index: int, block_id: str | None) -> None:
        self.normalize()
        idx = int(index)
        if idx < 0 or idx >= 9:
            return

        bid = "" if block_id is None else str(block_id).strip()
        self.hotbar_slots[idx] = bid

    def select_hotbar_index(self, index: int) -> None:
        self.normalize()
        self.selected_hotbar_index = int(max(0, min(8, int(index))))

    def cycle_hotbar(self, delta_steps: int) -> None:
        self.normalize()
        step = int(delta_steps)
        if step == 0:
            return
        self.selected_hotbar_index = int((int(self.selected_hotbar_index) + step) % 9)