# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

_EQUIP_RATE_PER_SECOND = 8.0
_SWAP_THRESHOLD = 0.05
_SWING_DURATION_S = 6.0 / 20.0


def _normalize_item_id(item_id: str | None) -> str | None:
    """I define N(id) = strip(id) when the stripped string is non-empty and N(id) = None otherwise. I use this normalization so that animation state is not polluted by empty-string sentinels that are semantically equivalent to item absence."""
    if item_id is None:
        return None
    text = str(item_id).strip()
    return text if text else None


@dataclass(frozen=True)
class FirstPersonMotionSample:
    """I define this record as the sampled animation state sigma = (visible, target, equip, swing, arm flags, view-model flags). I use sigma as the immutable boundary between the mutable controller and the later render-state composer."""
    visible_item_id: str | None
    target_item_id: str | None
    equip_progress: float
    prev_equip_progress: float
    swing_progress: float
    prev_swing_progress: float
    show_arm: bool
    show_view_model: bool
    slim_arm: bool


class FirstPersonMotionController:
    """I define this controller as the finite-state machine that evolves equip and swing channels over frame time dt. I keep the mutable animation integrator isolated here so that render-state construction remains a pure readout over a sampled snapshot."""

    def __init__(self, *, slim_arm: bool = True) -> None:
        """I initialize the controller at the quiescent state in which no item is visible, equip is fully raised, and swing is inactive. I also bind the arm-width mode so that later samples can be consumed without consulting external configuration."""
        self.visible_item_id: str | None = None
        self.target_item_id: str | None = None

        self.equip_progress: float = 1.0
        self.prev_equip_progress: float = 1.0

        self.swing_progress: float = 0.0
        self.prev_swing_progress: float = 0.0

        self.show_arm: bool = True
        self.show_view_model: bool = True
        self.slim_arm: bool = bool(slim_arm)

        self._equip_lowering: bool = False
        self._equip_raising: bool = False
        self._swing_active: bool = False

    def prime(self, item_id: str | None) -> None:
        """I define prime(id) as the hard reset that makes visible_item_id and target_item_id coincide with N(id), sets equip to 1, and clears every transient transition flag. I use this reset when the controller must synchronize itself instantly to an authoritative inventory state."""
        normalized = _normalize_item_id(item_id)
        self.visible_item_id = normalized
        self.target_item_id = normalized
        self.equip_progress = 1.0
        self.prev_equip_progress = 1.0
        self.swing_progress = 0.0
        self.prev_swing_progress = 0.0
        self.show_arm = normalized is None
        self._equip_lowering = False
        self._equip_raising = False
        self._swing_active = False

    def set_target_item_id(self, item_id: str | None) -> None:
        """I define target := N(id), and when visible != target I enter the lowering phase of the equip state machine. I use this deferred transition rather than an immediate swap so that visual item replacement remains temporally legible."""
        normalized = _normalize_item_id(item_id)
        if normalized == self.target_item_id:
            return

        self.target_item_id = normalized
        if self.visible_item_id != self.target_item_id:
            self._equip_lowering = True
            self._equip_raising = False

    def set_view_model_visible(self, visible: bool) -> None:
        """I define show_view_model := bool(visible). I keep this assignment separate from item targeting because view-model suppression is an orthogonal presentation policy rather than an inventory transition."""
        self.show_view_model = bool(visible)

    def trigger_left_swing(self) -> None:
        """I define the left-hand trigger as the canonical swing activation event. I route it through the shared swing starter so that all attack-entry paths reset the same temporal channels."""
        self._start_swing()

    def trigger_right_swing(self, *, success: bool) -> None:
        """I define the right-hand trigger as a conditional swing activation that fires only on successful interaction. I use this gate because failed right-click interactions should not consume the same visible swing budget as successful ones."""
        if bool(success):
            self._start_swing()

    def _start_swing(self) -> None:
        """I define the swing reset as (swing_progress, prev_swing_progress, active) := (0, 0, True). I use this hard restart so that consecutive swing requests always begin from the initial animation phase rather than blending unpredictably with any partial prior swing."""
        self.swing_progress = 0.0
        self.prev_swing_progress = 0.0
        self._swing_active = True

    def update(self, dt: float) -> None:
        """I integrate the equip and swing state machine over dt by advancing the lowering, swap, raising, and swing phases under their respective rate laws and thresholds. I keep this update deterministic and side-effect local so that the later render pipeline may treat the sampled output as immutable frame data."""
        step = max(0.0, float(dt))

        self.prev_equip_progress = float(self.equip_progress)
        self.prev_swing_progress = float(self.swing_progress)

        if (not self._equip_lowering) and (not self._equip_raising) and self.visible_item_id != self.target_item_id:
            self._equip_lowering = True

        if self._equip_lowering:
            next_progress = max(0.0, float(self.equip_progress) - float(_EQUIP_RATE_PER_SECOND) * step)
            crossed_swap = float(self.equip_progress) > float(_SWAP_THRESHOLD) and float(next_progress) <= float(_SWAP_THRESHOLD)
            self.equip_progress = float(next_progress)

            if (bool(crossed_swap) or float(self.equip_progress) <= float(_SWAP_THRESHOLD)) and self.visible_item_id != self.target_item_id:
                self.visible_item_id = self.target_item_id
                self.show_arm = self.visible_item_id is None
                self._equip_lowering = False
                self._equip_raising = True
            elif float(self.equip_progress) <= 0.0 and self.visible_item_id == self.target_item_id:
                self._equip_lowering = False
                self._equip_raising = True
        elif self._equip_raising:
            self.equip_progress = min(1.0, float(self.equip_progress) + float(_EQUIP_RATE_PER_SECOND) * step)
            if float(self.equip_progress) >= 1.0:
                self._equip_raising = False
                self._equip_lowering = False
        else:
            self.equip_progress = 1.0

        if self._swing_active:
            duration = max(1e-6, float(_SWING_DURATION_S))
            self.swing_progress = min(1.0, float(self.swing_progress) + step / duration)
            if float(self.swing_progress) >= 1.0:
                self.swing_progress = 0.0
                self._swing_active = False

    def sample(self) -> FirstPersonMotionSample:
        """I define sample() as the immutable projection of the controller's mutable fields onto the FirstPersonMotionSample record. I use this readout so that downstream render-state composition cannot accidentally mutate live controller state."""
        return FirstPersonMotionSample(visible_item_id=self.visible_item_id, target_item_id=self.target_item_id, equip_progress=float(self.equip_progress), prev_equip_progress=float(self.prev_equip_progress), swing_progress=float(self.swing_progress), prev_swing_progress=float(self.prev_swing_progress), show_arm=bool(self.show_arm), show_view_model=bool(self.show_view_model), slim_arm=bool(self.slim_arm))
