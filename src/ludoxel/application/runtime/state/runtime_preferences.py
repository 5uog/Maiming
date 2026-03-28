# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from ....shared.math.scalars import clampf, clampi
from ....shared.world.config.render_distance import clamp_render_distance_chunks
from ....shared.world.inventory.hotbar import HOTBAR_SIZE, cycle_hotbar_index, normalize_hotbar_index, normalize_hotbar_slots, with_hotbar_assignment
from ....shared.world.inventory.hotbar_defaults import default_hotbar_slots
from ....features.othello.domain.inventory.hotbar_defaults import default_othello_hotbar_slots
from ....features.othello.domain.inventory.special_items import is_special_item_id
from ....features.othello.domain.game.types import OthelloSettings
from ....shared.world.play_space import PLAY_SPACE_MY_WORLD, is_othello_space, normalize_play_space_id
from ....shared.opengl.runtime.cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION, normalize_cloud_flow_direction
from ....shared.rendering.player_skin import PLAYER_SKIN_KIND_ALEX, normalize_player_skin_kind
from ....shared.ui.hud.crosshair_art import CROSSHAIR_MODE_DEFAULT, EMPTY_CROSSHAIR_PIXELS, normalize_crosshair_mode, normalize_crosshair_pixels
from .camera_perspective import CAMERA_PERSPECTIVE_FIRST_PERSON, cycle_camera_perspective, is_first_person_camera_perspective, normalize_camera_perspective
from ..keybinds import KeybindSettings
from .audio_preferences import AudioPreferences


def _coerce_optional_int(value: object) -> int | None:
    """I define C?(x) = int(x) when coercion succeeds and None otherwise. I use this partial integer decoder for optional window geometry fields whose absence is semantically meaningful."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _default_hotbar_slots_list() -> list[str]:
    """I materialize the canonical mutable default hotbar for ordinary world play."""
    return list(default_hotbar_slots(size=HOTBAR_SIZE))


def _default_othello_hotbar_slots_list() -> list[str]:
    """I materialize the canonical mutable default hotbar for the Othello space."""
    return list(default_othello_hotbar_slots(size=HOTBAR_SIZE))


def _normalize_hotbar_state(slots: object, index: object, *, size: int=HOTBAR_SIZE) -> tuple[list[str], int]:
    """I define H(slots, index) = (normalized_slots, normalized_index) with the slot vector constrained to the active hotbar size. This keeps selection and assignment code total under malformed persisted state."""
    normalized_slots = list(normalize_hotbar_slots(slots, size=int(size)))
    normalized_index = normalize_hotbar_index(index, size=int(size))
    return normalized_slots, int(normalized_index)


@dataclass
class RuntimePreferences:
    """I model the mutable runtime preference manifold as P, which aggregates view, audio, cloud, hotbar, skin, space-selection, and Othello-default state. I normalize this object in place because it serves as the shared mutable bridge between persistence, Qt controls, renderer state, and active session logic."""
    DEFAULT_BLOCK_BREAK_REPEAT_INTERVAL_S: ClassVar[float] = 0.30
    DEFAULT_BLOCK_PLACE_REPEAT_INTERVAL_S: ClassVar[float] = 0.20
    BLOCK_BREAK_REPEAT_INTERVAL_MIN: ClassVar[float] = 0.0
    BLOCK_BREAK_REPEAT_INTERVAL_MAX: ClassVar[float] = 1.0
    BLOCK_PLACE_REPEAT_INTERVAL_MIN: ClassVar[float] = 0.0
    BLOCK_PLACE_REPEAT_INTERVAL_MAX: ClassVar[float] = 1.0
    DEFAULT_BLOCK_BREAK_PARTICLE_SPAWN_RATE: ClassVar[float] = 1.0
    DEFAULT_BLOCK_BREAK_PARTICLE_SPEED_SCALE: ClassVar[float] = 1.0
    BLOCK_BREAK_PARTICLE_SPAWN_RATE_MIN: ClassVar[float] = 0.0
    BLOCK_BREAK_PARTICLE_SPAWN_RATE_MAX: ClassVar[float] = 2.0
    BLOCK_BREAK_PARTICLE_SPEED_SCALE_MIN: ClassVar[float] = 0.1
    BLOCK_BREAK_PARTICLE_SPEED_SCALE_MAX: ClassVar[float] = 3.0

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
    block_break_repeat_interval_s: float = DEFAULT_BLOCK_BREAK_REPEAT_INTERVAL_S
    block_place_repeat_interval_s: float = DEFAULT_BLOCK_PLACE_REPEAT_INTERVAL_S
    block_break_particle_spawn_rate: float = DEFAULT_BLOCK_BREAK_PARTICLE_SPAWN_RATE
    block_break_particle_speed_scale: float = DEFAULT_BLOCK_BREAK_PARTICLE_SPEED_SCALE
    auto_jump_enabled: bool = False
    auto_sprint_enabled: bool = False
    hide_hud: bool = False
    hide_hand: bool = False
    crosshair_mode: str = CROSSHAIR_MODE_DEFAULT
    crosshair_pixels: tuple[str, ...] = field(default_factory=lambda: EMPTY_CROSSHAIR_PIXELS)
    player_skin_kind: str = PLAYER_SKIN_KIND_ALEX
    camera_perspective: str = CAMERA_PERSPECTIVE_FIRST_PERSON
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
    window_left: int | None = None
    window_top: int | None = None
    window_width: int = 1280
    window_height: int = 720
    window_screen_name: str = ""
    keybinds: KeybindSettings = field(default_factory=KeybindSettings)
    audio: AudioPreferences = field(default_factory=AudioPreferences)

    def normalize(self) -> None:
        """I project every component of P onto its admissible domain. This includes Boolean coercion, bounded scalar clamps, hotbar normalization, canonical play-space identifiers, and nested normalization of Othello, keybind, and audio subrecords."""
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
        self.crosshair_mode = normalize_crosshair_mode(self.crosshair_mode)
        self.crosshair_pixels = normalize_crosshair_pixels(self.crosshair_pixels)
        self.player_skin_kind = normalize_player_skin_kind(self.player_skin_kind)
        self.camera_perspective = normalize_camera_perspective(self.camera_perspective)
        self.fullscreen = bool(self.fullscreen)
        self.view_bobbing_enabled = bool(self.view_bobbing_enabled)
        self.camera_shake_enabled = bool(self.camera_shake_enabled)
        self.animated_textures_enabled = bool(self.animated_textures_enabled)
        self.debug_shadow = bool(self.debug_shadow)
        self.vsync_on = bool(self.vsync_on)
        self.hud_visible = bool(self.hud_visible)

        self.cloud_density = clampi(int(self.cloud_density), 0, 4)
        self.cloud_seed = clampi(int(self.cloud_seed), 0, 9999)
        self.cloud_flow_direction = normalize_cloud_flow_direction(str(self.cloud_flow_direction))
        self.render_distance_chunks = clamp_render_distance_chunks(int(self.render_distance_chunks))
        self.view_bobbing_strength = clampf(float(self.view_bobbing_strength), 0.0, 1.0)
        self.camera_shake_strength = clampf(float(self.camera_shake_strength), 0.0, 1.0)
        self.reach = max(0.0, float(self.reach))
        self.block_break_repeat_interval_s = clampf(float(self.block_break_repeat_interval_s), float(self.BLOCK_BREAK_REPEAT_INTERVAL_MIN), float(self.BLOCK_BREAK_REPEAT_INTERVAL_MAX))
        self.block_place_repeat_interval_s = clampf(float(self.block_place_repeat_interval_s), float(self.BLOCK_PLACE_REPEAT_INTERVAL_MIN), float(self.BLOCK_PLACE_REPEAT_INTERVAL_MAX))
        self.block_break_particle_spawn_rate = clampf(float(self.block_break_particle_spawn_rate), float(self.BLOCK_BREAK_PARTICLE_SPAWN_RATE_MIN), float(self.BLOCK_BREAK_PARTICLE_SPAWN_RATE_MAX))
        self.block_break_particle_speed_scale = clampf(float(self.block_break_particle_speed_scale), float(self.BLOCK_BREAK_PARTICLE_SPEED_SCALE_MIN), float(self.BLOCK_BREAK_PARTICLE_SPEED_SCALE_MAX))
        self.window_left = _coerce_optional_int(self.window_left)
        self.window_top = _coerce_optional_int(self.window_top)
        self.window_width = max(320, int(self.window_width))
        self.window_height = max(240, int(self.window_height))
        self.window_screen_name = str(self.window_screen_name or "").strip()

        azimuth = float(self.sun_az_deg) % 360.0
        self.sun_az_deg = azimuth if azimuth >= 0.0 else azimuth + 360.0
        self.sun_el_deg = clampf(float(self.sun_el_deg), 0.0, 90.0)

        self.creative_hotbar_slots, self.creative_selected_hotbar_index = _normalize_hotbar_state(self.creative_hotbar_slots, self.creative_selected_hotbar_index, size=HOTBAR_SIZE)
        self.survival_hotbar_slots, self.survival_selected_hotbar_index = _normalize_hotbar_state(self.survival_hotbar_slots, self.survival_selected_hotbar_index, size=HOTBAR_SIZE)
        self.othello_hotbar_slots, self.othello_selected_hotbar_index = _normalize_hotbar_state(self.othello_hotbar_slots, self.othello_selected_hotbar_index, size=HOTBAR_SIZE)

        self.othello_settings = self.othello_settings.normalized()
        self.keybinds = self.keybinds.normalized()
        self.audio = self.audio.normalized()

    def clone(self) -> "RuntimePreferences":
        """I return a normalized structural copy of P."""
        return coerce_runtime_preferences(runtime=self)

    def is_othello_space(self) -> bool:
        """I evaluate the predicate chi_othello(P.current_space_id)."""
        return is_othello_space(self.current_space_id)

    def is_first_person_view(self) -> bool:
        """I evaluate the predicate chi_fp(P.camera_perspective)."""
        return is_first_person_camera_perspective(self.camera_perspective)

    def view_model_visible(self) -> bool:
        """I define V_model = chi_fp and not hide_hand. This predicate governs whether the first-person held-item model is rendered."""
        return bool(self.is_first_person_view()) and (not bool(self.hide_hand))

    def cycle_camera_perspective(self, step: int=1) -> None:
        """I advance the camera perspective along the finite cyclic order induced by the configured perspective set."""
        self.camera_perspective = cycle_camera_perspective(self.camera_perspective, step=int(step))

    def _active_hotbar_state_attrs(self) -> tuple[str, str]:
        """I choose the active hotbar state projection as a function of play space and creative-mode state."""
        if self.is_othello_space():
            return ("othello_hotbar_slots", "othello_selected_hotbar_index")
        if bool(self.creative_mode):
            return ("creative_hotbar_slots", "creative_selected_hotbar_index")
        return ("survival_hotbar_slots", "survival_selected_hotbar_index")

    def _active_hotbar_slots(self) -> list[str]:
        """I return the mutable slot vector of the currently active hotbar branch."""
        slots_attr, _index_attr = self._active_hotbar_state_attrs()
        return getattr(self, slots_attr)

    def _active_hotbar_index(self) -> int:
        """I return the currently active hotbar index after branch selection."""
        _slots_attr, index_attr = self._active_hotbar_state_attrs()
        return int(getattr(self, index_attr))

    def active_hotbar_index(self) -> int:
        """I expose the active hotbar index as a public projection."""
        return int(self._active_hotbar_index())

    def hotbar_snapshot(self) -> tuple[str, ...]:
        """I return the active hotbar as an immutable tuple snapshot."""
        return tuple(str(value).strip() for value in self._active_hotbar_slots())

    def current_item_id(self) -> str | None:
        """I define item(P) as the normalized item identifier stored at the active hotbar index, or None when the slot is empty."""
        slots = self._active_hotbar_slots()
        index = self._active_hotbar_index()
        value = str(slots[index]).strip()
        return value if value else None

    def current_block_id(self) -> str | None:
        """I project item(P) onto the block-id subset by excluding special-item identifiers."""
        item_id = self.current_item_id()
        if item_id is None or is_special_item_id(item_id):
            return None
        return item_id

    def current_special_item_id(self) -> str | None:
        """I project item(P) onto the special-item subset by excluding ordinary block identifiers."""
        item_id = self.current_item_id()
        if item_id is None or not is_special_item_id(item_id):
            return None
        return item_id

    def set_hotbar_slot(self, index: int, item_id: str | None) -> None:
        """I assign one slot of the active hotbar branch after normalizing the full preference state. The branch selection is dynamic, so the same operation can target creative, survival, or Othello control slots."""
        self.normalize()
        slots_attr, _index_attr = self._active_hotbar_state_attrs()
        active_slots = getattr(self, slots_attr)
        setattr(self, slots_attr, list(with_hotbar_assignment(active_slots, index, item_id, size=HOTBAR_SIZE)))

    def select_hotbar_index(self, index: int) -> None:
        """I assign the active hotbar index through the bounded hotbar-index normalizer."""
        self.normalize()
        _slots_attr, index_attr = self._active_hotbar_state_attrs()
        setattr(self, index_attr, normalize_hotbar_index(index, size=HOTBAR_SIZE))

    def cycle_hotbar(self, delta_steps: int) -> None:
        """I apply cyclic index motion i := i (+) delta over the active hotbar branch."""
        self.normalize()
        _slots_attr, index_attr = self._active_hotbar_state_attrs()
        current_index = int(getattr(self, index_attr))
        setattr(self, index_attr, cycle_hotbar_index(current_index, delta_steps, size=HOTBAR_SIZE))

    def clear_selected_hotbar_slot(self) -> None:
        """I clear the active slot of the currently selected hotbar branch."""
        self.normalize()
        self.set_hotbar_slot(self._active_hotbar_index(), None)


def coerce_runtime_preferences(*, runtime: RuntimePreferences | None=None, **overrides) -> RuntimePreferences:
    """I define C_P(runtime, overrides) as total cloning plus fieldwise override over the runtime preference manifold. I use this constructor whenever I need a normalized copy that may selectively replace one or more projections."""
    if runtime is not None:
        out = RuntimePreferences(current_space_id=str(runtime.current_space_id), invert_x=bool(runtime.invert_x), invert_y=bool(runtime.invert_y), outline_selection=bool(runtime.outline_selection), cloud_wire=bool(runtime.cloud_wire), cloud_enabled=bool(runtime.cloud_enabled), cloud_density=int(runtime.cloud_density), cloud_seed=int(runtime.cloud_seed), cloud_flow_direction=str(runtime.cloud_flow_direction), world_wire=bool(runtime.world_wire), shadow_enabled=bool(runtime.shadow_enabled), creative_mode=bool(runtime.creative_mode), creative_hotbar_slots=list(runtime.creative_hotbar_slots), creative_selected_hotbar_index=int(runtime.creative_selected_hotbar_index), survival_hotbar_slots=list(runtime.survival_hotbar_slots), survival_selected_hotbar_index=int(runtime.survival_selected_hotbar_index), othello_hotbar_slots=list(runtime.othello_hotbar_slots), othello_selected_hotbar_index=int(runtime.othello_selected_hotbar_index), othello_settings=runtime.othello_settings.normalized(), reach=float(runtime.reach), block_break_repeat_interval_s=float(runtime.block_break_repeat_interval_s), block_place_repeat_interval_s=float(runtime.block_place_repeat_interval_s), block_break_particle_spawn_rate=float(runtime.block_break_particle_spawn_rate), block_break_particle_speed_scale=float(runtime.block_break_particle_speed_scale), auto_jump_enabled=bool(runtime.auto_jump_enabled), auto_sprint_enabled=bool(runtime.auto_sprint_enabled), hide_hud=bool(runtime.hide_hud), hide_hand=bool(runtime.hide_hand), crosshair_mode=str(runtime.crosshair_mode), crosshair_pixels=tuple(runtime.crosshair_pixels), player_skin_kind=str(runtime.player_skin_kind), camera_perspective=str(runtime.camera_perspective), fullscreen=bool(runtime.fullscreen), view_bobbing_enabled=bool(runtime.view_bobbing_enabled), camera_shake_enabled=bool(runtime.camera_shake_enabled), view_bobbing_strength=float(runtime.view_bobbing_strength), camera_shake_strength=float(runtime.camera_shake_strength), animated_textures_enabled=bool(runtime.animated_textures_enabled), render_distance_chunks=int(runtime.render_distance_chunks), sun_az_deg=float(runtime.sun_az_deg), sun_el_deg=float(runtime.sun_el_deg), debug_shadow=bool(runtime.debug_shadow), vsync_on=bool(runtime.vsync_on), hud_visible=bool(runtime.hud_visible), window_left=_coerce_optional_int(runtime.window_left), window_top=_coerce_optional_int(runtime.window_top), window_width=int(runtime.window_width), window_height=int(runtime.window_height), window_screen_name=str(runtime.window_screen_name), keybinds=runtime.keybinds.normalized(), audio=runtime.audio.normalized())
    else:
        out = RuntimePreferences()

    for key, value in overrides.items():
        if value is None or not hasattr(out, key):
            continue
        if key.endswith("_hotbar_slots"):
            setattr(out, key, list(value))
        elif key == "crosshair_pixels":
            setattr(out, key, normalize_crosshair_pixels(value))
        elif key == "othello_settings":
            setattr(out, key, value.normalized())
        elif key == "keybinds":
            if isinstance(value, KeybindSettings):
                setattr(out, key, value.normalized())
            else:
                setattr(out, key, KeybindSettings.from_dict(value))
        elif key == "audio":
            if isinstance(value, AudioPreferences):
                setattr(out, key, value.normalized())
            else:
                setattr(out, key, AudioPreferences.from_dict(value))
        else:
            setattr(out, key, value)

    out.normalize()
    return out
