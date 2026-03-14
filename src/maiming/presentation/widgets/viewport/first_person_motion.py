# FILE: src/maiming/presentation/widgets/viewport/first_person_motion.py
from __future__ import annotations
from dataclasses import dataclass

_EQUIP_RATE_PER_SECOND = 8.0
_SWAP_THRESHOLD = 0.05
_SWING_DURATION_S = 6.0 / 20.0

def _normalize_block_id(block_id: str | None) -> str | None:
    if block_id is None:
        return None
    text = str(block_id).strip()
    return text if text else None

@dataclass(frozen=True)
class FirstPersonMotionSample:
    visible_block_id: str | None
    target_block_id: str | None
    equip_progress: float
    prev_equip_progress: float
    swing_progress: float
    prev_swing_progress: float
    show_arm: bool
    show_view_model: bool
    slim_arm: bool

class FirstPersonMotionController:
    def __init__(self, *, slim_arm: bool = True) -> None:
        self.visible_block_id: str | None = None
        self.target_block_id: str | None = None

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

    def prime(self, block_id: str | None) -> None:
        normalized = _normalize_block_id(block_id)
        self.visible_block_id = normalized
        self.target_block_id = normalized
        self.equip_progress = 1.0
        self.prev_equip_progress = 1.0
        self.swing_progress = 0.0
        self.prev_swing_progress = 0.0
        self.show_arm = normalized is None
        self._equip_lowering = False
        self._equip_raising = False
        self._swing_active = False

    def set_target_block_id(self, block_id: str | None) -> None:
        normalized = _normalize_block_id(block_id)
        if normalized == self.target_block_id:
            return

        self.target_block_id = normalized
        if self.visible_block_id != self.target_block_id:
            self._equip_lowering = True
            self._equip_raising = False

    def set_view_model_visible(self, visible: bool) -> None:
        self.show_view_model = bool(visible)

    def trigger_left_swing(self) -> None:
        self._start_swing()

    def trigger_right_swing(self, *, success: bool) -> None:
        if bool(success):
            self._start_swing()

    def _start_swing(self) -> None:
        self.swing_progress = 0.0
        self.prev_swing_progress = 0.0
        self._swing_active = True

    def update(self, dt: float) -> None:
        step = max(0.0, float(dt))

        self.prev_equip_progress = float(self.equip_progress)
        self.prev_swing_progress = float(self.swing_progress)

        if (not self._equip_lowering) and (not self._equip_raising) and self.visible_block_id != self.target_block_id:
            self._equip_lowering = True

        if self._equip_lowering:
            next_progress = max(0.0, float(self.equip_progress) - float(_EQUIP_RATE_PER_SECOND) * step)
            crossed_swap = float(self.equip_progress) > float(_SWAP_THRESHOLD) and float(next_progress) <= float(_SWAP_THRESHOLD)
            self.equip_progress = float(next_progress)

            if (bool(crossed_swap) or float(self.equip_progress) <= float(_SWAP_THRESHOLD)) and self.visible_block_id != self.target_block_id:
                self.visible_block_id = self.target_block_id
                self.show_arm = self.visible_block_id is None
                self._equip_lowering = False
                self._equip_raising = True
            elif float(self.equip_progress) <= 0.0 and self.visible_block_id == self.target_block_id:
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
        return FirstPersonMotionSample(visible_block_id=self.visible_block_id, target_block_id=self.target_block_id, equip_progress=float(self.equip_progress), prev_equip_progress=float(self.prev_equip_progress), swing_progress=float(self.swing_progress), prev_swing_progress=float(self.prev_swing_progress), show_arm=bool(self.show_arm), show_view_model=bool(self.show_view_model), slim_arm=bool(self.slim_arm))