# FILE: src/maiming/presentation/widgets/viewport/viewport_runtime_state.py
from __future__ import annotations
from dataclasses import dataclass, field

from ....domain.config.render_distance import clamp_render_distance_chunks
from ....domain.inventory.hotbar import HOTBAR_SIZE, cycle_hotbar_index, normalize_hotbar_index, normalize_hotbar_slots, with_hotbar_assignment
from ....domain.inventory.special_items import OTHELLO_SETTINGS_ITEM_ID, OTHELLO_START_ITEM_ID, is_special_item_id
from ....domain.othello.types import OthelloSettings
from ....domain.play_space import PLAY_SPACE_MY_WORLD, is_othello_space, normalize_play_space_id
from ....infrastructure.rendering.opengl.facade.cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION, normalize_cloud_flow_direction
from .view_model_visibility import view_model_visible

def _default_hotbar_slots() -> list[str]:
    return list(normalize_hotbar_slots(None, size=HOTBAR_SIZE))

def _default_othello_hotbar_slots() -> list[str]:
    return list(
        normalize_hotbar_slots(
            (
                OTHELLO_START_ITEM_ID,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                OTHELLO_SETTINGS_ITEM_ID,
            ),
            size=HOTBAR_SIZE,
        )
    )

@dataclass
class ViewportRuntimeState:
    current_space_id: str = PLAY_SPACE_MY_WORLD

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

    creative_mode: bool = False
    creative_hotbar_slots: list[str] = field(default_factory=_default_hotbar_slots)
    creative_selected_hotbar_index: int = 0
    survival_hotbar_slots: list[str] = field(default_factory=_default_hotbar_slots)
    survival_selected_hotbar_index: int = 0
    othello_hotbar_slots: list[str] = field(default_factory=_default_othello_hotbar_slots)
    othello_selected_hotbar_index: int = 0
    othello_settings: OthelloSettings = field(default_factory=OthelloSettings)
    reach: float = 5.0
    auto_jump_enabled: bool = False
    auto_sprint_enabled: bool = False
    hide_hud: bool = False
    hide_hand: bool = False
    fullscreen: bool = False
    view_bobbing_enabled: bool = True
    camera_shake_enabled: bool = True
    view_bobbing_strength: float = 0.35
    camera_shake_strength: float = 0.20

    render_distance_chunks: int = 6

    sun_az_deg: float = 45.0
    sun_el_deg: float = 60.0

    debug_shadow: bool = False
    vsync_on: bool = False

    hud_visible: bool = False

    def normalize(self) -> None:
        self.current_space_id = normalize_play_space_id(self.current_space_id)

        self.cloud_density = int(max(0, min(4, int(self.cloud_density))))
        self.cloud_seed = int(max(0, min(9999, int(self.cloud_seed))))
        self.cloud_flow_direction = normalize_cloud_flow_direction(str(self.cloud_flow_direction))

        self.render_distance_chunks = clamp_render_distance_chunks(int(self.render_distance_chunks))
        self.view_bobbing_strength = max(0.0, min(1.0, float(self.view_bobbing_strength)))
        self.camera_shake_strength = max(0.0, min(1.0, float(self.camera_shake_strength)))

        reach = float(self.reach)
        self.reach = 0.0 if reach < 0.0 else reach

        az = float(self.sun_az_deg) % 360.0
        if az < 0.0:
            az += 360.0
        self.sun_az_deg = az

        el = float(self.sun_el_deg)
        self.sun_el_deg = max(0.0, min(90.0, el))

        self.creative_hotbar_slots = list(normalize_hotbar_slots(self.creative_hotbar_slots, size=HOTBAR_SIZE))
        self.creative_selected_hotbar_index = normalize_hotbar_index(self.creative_selected_hotbar_index, size=HOTBAR_SIZE)
        self.survival_hotbar_slots = list(normalize_hotbar_slots(self.survival_hotbar_slots, size=HOTBAR_SIZE))
        self.survival_selected_hotbar_index = normalize_hotbar_index(self.survival_selected_hotbar_index, size=HOTBAR_SIZE)
        self.othello_hotbar_slots = list(normalize_hotbar_slots(self.othello_hotbar_slots, size=HOTBAR_SIZE))
        self.othello_selected_hotbar_index = normalize_hotbar_index(self.othello_selected_hotbar_index, size=HOTBAR_SIZE)
        self.othello_settings = self.othello_settings.normalized()

    def is_othello_space(self) -> bool:
        self.normalize()
        return is_othello_space(self.current_space_id)

    def view_model_visible(self) -> bool:
        self.normalize()
        return view_model_visible(hide_hand=bool(self.hide_hand))

    def _active_hotbar_slots(self) -> list[str]:
        self.normalize()
        if self.is_othello_space():
            return self.othello_hotbar_slots
        if bool(self.creative_mode):
            return self.creative_hotbar_slots
        return self.survival_hotbar_slots

    def _active_hotbar_index(self) -> int:
        self.normalize()
        if self.is_othello_space():
            return int(self.othello_selected_hotbar_index)
        if bool(self.creative_mode):
            return int(self.creative_selected_hotbar_index)
        return int(self.survival_selected_hotbar_index)

    def hotbar_snapshot(self) -> tuple[str, ...]:
        self.normalize()
        return normalize_hotbar_slots(self._active_hotbar_slots(), size=HOTBAR_SIZE)

    def current_item_id(self) -> str | None:
        self.normalize()
        slots = self._active_hotbar_slots()
        idx = self._active_hotbar_index()
        value = str(slots[idx]).strip()
        return value if value else None

    def current_block_id(self) -> str | None:
        self.normalize()
        item_id = self.current_item_id()
        if item_id is None or is_special_item_id(item_id):
            return None
        return item_id

    def current_special_item_id(self) -> str | None:
        self.normalize()
        item_id = self.current_item_id()
        if item_id is None or not is_special_item_id(item_id):
            return None
        return item_id

    def set_hotbar_slot(self, index: int, item_id: str | None) -> None:
        self.normalize()
        if self.is_othello_space():
            self.othello_hotbar_slots = list(with_hotbar_assignment(self.othello_hotbar_slots, index, item_id, size=HOTBAR_SIZE))
            return
        if bool(self.creative_mode):
            self.creative_hotbar_slots = list(with_hotbar_assignment(self.creative_hotbar_slots, index, item_id, size=HOTBAR_SIZE))
            return
        self.survival_hotbar_slots = list(with_hotbar_assignment(self.survival_hotbar_slots, index, item_id, size=HOTBAR_SIZE))

    def select_hotbar_index(self, index: int) -> None:
        self.normalize()
        if self.is_othello_space():
            self.othello_selected_hotbar_index = normalize_hotbar_index(index, size=HOTBAR_SIZE)
            return
        if bool(self.creative_mode):
            self.creative_selected_hotbar_index = normalize_hotbar_index(index, size=HOTBAR_SIZE)
            return
        self.survival_selected_hotbar_index = normalize_hotbar_index(index, size=HOTBAR_SIZE)

    def cycle_hotbar(self, delta_steps: int) -> None:
        self.normalize()
        if self.is_othello_space():
            self.othello_selected_hotbar_index = cycle_hotbar_index(self.othello_selected_hotbar_index, delta_steps, size=HOTBAR_SIZE)
            return
        if bool(self.creative_mode):
            self.creative_selected_hotbar_index = cycle_hotbar_index(self.creative_selected_hotbar_index, delta_steps, size=HOTBAR_SIZE)
            return
        self.survival_selected_hotbar_index = cycle_hotbar_index(self.survival_selected_hotbar_index, delta_steps, size=HOTBAR_SIZE)