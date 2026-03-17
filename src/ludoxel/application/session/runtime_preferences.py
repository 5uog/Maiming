# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/application/session/runtime_preferences.py
from __future__ import annotations

from dataclasses import dataclass, field

from .audio_preferences import AudioPreferences
from .keybinds import KeybindSettings
from ...domain.config.render_distance import clamp_render_distance_chunks
from ...domain.inventory.hotbar import HOTBAR_SIZE, cycle_hotbar_index, normalize_hotbar_index, normalize_hotbar_slots, with_hotbar_assignment
from ...domain.inventory.hotbar_defaults import default_hotbar_slots, default_othello_hotbar_slots
from ...domain.inventory.special_items import is_special_item_id
from ...domain.othello.types import OthelloSettings
from ...domain.play_space import PLAY_SPACE_MY_WORLD, is_othello_space, normalize_play_space_id
from ...infrastructure.rendering.opengl.facade.cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION, normalize_cloud_flow_direction
from ...presentation.widgets.viewport.view_model_visibility import view_model_visible


def _default_hotbar_slots_list() -> list[str]:
    return list(default_hotbar_slots(size=HOTBAR_SIZE))


def _default_othello_hotbar_slots_list() -> list[str]:
    return list(default_othello_hotbar_slots(size=HOTBAR_SIZE))


@dataclass
class RuntimePreferences:
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
    creative_hotbar_slots: list[str] = field(default_factory=_default_hotbar_slots_list)
    creative_selected_hotbar_index: int = 0
    survival_hotbar_slots: list[str] = field(default_factory=_default_hotbar_slots_list)
    survival_selected_hotbar_index: int = 0
    othello_hotbar_slots: list[str] = field(default_factory=_default_othello_hotbar_slots_list)
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
    animated_textures_enabled: bool = True
    render_distance_chunks: int = 6
    sun_az_deg: float = 45.0
    sun_el_deg: float = 60.0
    debug_shadow: bool = False
    vsync_on: bool = False
    hud_visible: bool = False
    keybinds: KeybindSettings = field(default_factory=KeybindSettings)
    audio: AudioPreferences = field(default_factory=AudioPreferences)

    def normalize(self) -> None:
        self.current_space_id = normalize_play_space_id(self.current_space_id)

        self.invert_x = bool(self.invert_x)
        self.invert_y = bool(self.invert_y)
        self.outline_selection = bool(self.outline_selection)
        self.cloud_wire = bool(self.cloud_wire)
        self.cloud_enabled = bool(self.cloud_enabled)
        self.world_wire = bool(self.world_wire)
        self.shadow_enabled = bool(self.shadow_enabled)
        self.creative_mode = bool(self.creative_mode)
        self.auto_jump_enabled = bool(self.auto_jump_enabled)
        self.auto_sprint_enabled = bool(self.auto_sprint_enabled)
        self.hide_hud = bool(self.hide_hud)
        self.hide_hand = bool(self.hide_hand)
        self.fullscreen = bool(self.fullscreen)
        self.view_bobbing_enabled = bool(self.view_bobbing_enabled)
        self.camera_shake_enabled = bool(self.camera_shake_enabled)
        self.animated_textures_enabled = bool(self.animated_textures_enabled)
        self.debug_shadow = bool(self.debug_shadow)
        self.vsync_on = bool(self.vsync_on)
        self.hud_visible = bool(self.hud_visible)

        self.cloud_density = int(max(0, min(4, int(self.cloud_density))))
        self.cloud_seed = int(max(0, min(9999, int(self.cloud_seed))))
        self.cloud_flow_direction = normalize_cloud_flow_direction(str(self.cloud_flow_direction))
        self.render_distance_chunks = clamp_render_distance_chunks(int(self.render_distance_chunks))
        self.view_bobbing_strength = max(0.0, min(1.0, float(self.view_bobbing_strength)))
        self.camera_shake_strength = max(0.0, min(1.0, float(self.camera_shake_strength)))
        self.reach = max(0.0, float(self.reach))

        azimuth = float(self.sun_az_deg) % 360.0
        self.sun_az_deg = azimuth if azimuth >= 0.0 else azimuth + 360.0
        self.sun_el_deg = max(0.0, min(90.0, float(self.sun_el_deg)))

        self.creative_hotbar_slots = list(normalize_hotbar_slots(self.creative_hotbar_slots, size=HOTBAR_SIZE))
        self.creative_selected_hotbar_index = normalize_hotbar_index(self.creative_selected_hotbar_index, size=HOTBAR_SIZE)

        self.survival_hotbar_slots = list(normalize_hotbar_slots(self.survival_hotbar_slots, size=HOTBAR_SIZE))
        self.survival_selected_hotbar_index = normalize_hotbar_index(self.survival_selected_hotbar_index, size=HOTBAR_SIZE)

        self.othello_hotbar_slots = list(normalize_hotbar_slots(self.othello_hotbar_slots, size=HOTBAR_SIZE))
        self.othello_selected_hotbar_index = normalize_hotbar_index(self.othello_selected_hotbar_index, size=HOTBAR_SIZE)

        self.othello_settings = self.othello_settings.normalized()
        self.keybinds = self.keybinds.normalized()
        self.audio = self.audio.normalized()

    def clone(self) -> "RuntimePreferences":
        return coerce_runtime_preferences(runtime=self)

    def is_othello_space(self) -> bool:
        return is_othello_space(self.current_space_id)

    def view_model_visible(self) -> bool:
        return view_model_visible(hide_hand=bool(self.hide_hand))

    def _active_hotbar_slots(self) -> list[str]:
        if self.is_othello_space():
            return self.othello_hotbar_slots
        if bool(self.creative_mode):
            return self.creative_hotbar_slots
        return self.survival_hotbar_slots

    def _active_hotbar_index(self) -> int:
        if self.is_othello_space():
            return int(self.othello_selected_hotbar_index)
        if bool(self.creative_mode):
            return int(self.creative_selected_hotbar_index)
        return int(self.survival_selected_hotbar_index)

    def active_hotbar_index(self) -> int:
        return int(self._active_hotbar_index())

    def hotbar_snapshot(self) -> tuple[str, ...]:
        return tuple(str(value).strip() for value in self._active_hotbar_slots())

    def current_item_id(self) -> str | None:
        slots = self._active_hotbar_slots()
        index = self._active_hotbar_index()
        value = str(slots[index]).strip()
        return value if value else None

    def current_block_id(self) -> str | None:
        item_id = self.current_item_id()
        if item_id is None or is_special_item_id(item_id):
            return None
        return item_id

    def current_special_item_id(self) -> str | None:
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

    def clear_selected_hotbar_slot(self) -> None:
        self.normalize()
        self.set_hotbar_slot(self._active_hotbar_index(), None)


ViewportRuntimeState = RuntimePreferences


def coerce_runtime_preferences(*, runtime: RuntimePreferences | None = None, **overrides) -> RuntimePreferences:
    if runtime is not None:
        out = RuntimePreferences(
            current_space_id=str(runtime.current_space_id),
            invert_x=bool(runtime.invert_x),
            invert_y=bool(runtime.invert_y),
            outline_selection=bool(runtime.outline_selection),
            cloud_wire=bool(runtime.cloud_wire),
            cloud_enabled=bool(runtime.cloud_enabled),
            cloud_density=int(runtime.cloud_density),
            cloud_seed=int(runtime.cloud_seed),
            cloud_flow_direction=str(runtime.cloud_flow_direction),
            world_wire=bool(runtime.world_wire),
            shadow_enabled=bool(runtime.shadow_enabled),
            creative_mode=bool(runtime.creative_mode),
            creative_hotbar_slots=list(runtime.creative_hotbar_slots),
            creative_selected_hotbar_index=int(runtime.creative_selected_hotbar_index),
            survival_hotbar_slots=list(runtime.survival_hotbar_slots),
            survival_selected_hotbar_index=int(runtime.survival_selected_hotbar_index),
            othello_hotbar_slots=list(runtime.othello_hotbar_slots),
            othello_selected_hotbar_index=int(runtime.othello_selected_hotbar_index),
            othello_settings=runtime.othello_settings.normalized(),
            reach=float(runtime.reach),
            auto_jump_enabled=bool(runtime.auto_jump_enabled),
            auto_sprint_enabled=bool(runtime.auto_sprint_enabled),
            hide_hud=bool(runtime.hide_hud),
            hide_hand=bool(runtime.hide_hand),
            fullscreen=bool(runtime.fullscreen),
            view_bobbing_enabled=bool(runtime.view_bobbing_enabled),
            camera_shake_enabled=bool(runtime.camera_shake_enabled),
            view_bobbing_strength=float(runtime.view_bobbing_strength),
            camera_shake_strength=float(runtime.camera_shake_strength),
            animated_textures_enabled=bool(runtime.animated_textures_enabled),
            render_distance_chunks=int(runtime.render_distance_chunks),
            sun_az_deg=float(runtime.sun_az_deg),
            sun_el_deg=float(runtime.sun_el_deg),
            debug_shadow=bool(runtime.debug_shadow),
            vsync_on=bool(runtime.vsync_on),
            hud_visible=bool(runtime.hud_visible),
            keybinds=runtime.keybinds.normalized(),
            audio=runtime.audio.normalized(),
        )
    else:
        out = RuntimePreferences()

    for key, value in overrides.items():
        if value is None or not hasattr(out, key):
            continue
        if key.endswith("_hotbar_slots"):
            setattr(out, key, list(value))
        elif key == "othello_settings":
            setattr(out, key, value.normalized())
        elif key == "keybinds":
            setattr(out, key, value.normalized() if isinstance(value, KeybindSettings) else KeybindSettings.from_dict(value))
        elif key == "audio":
            setattr(out, key, value.normalized() if isinstance(value, AudioPreferences) else AudioPreferences.from_dict(value))
        else:
            setattr(out, key, value)

    out.normalize()
    return out
