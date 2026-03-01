# FILE: src/maiming/presentation/widgets/viewport/viewport_overlays.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtWidgets import QWidget

from maiming.application.session.fixed_step_runner import FixedStepRunner
from maiming.presentation.widgets.viewport.viewport_input import ViewportInput

@dataclass
class OverlayRefs:
    pause: QWidget
    inventory: QWidget
    death: QWidget
    crosshair: QWidget
    hud_getter: Callable[[], QWidget | None]

class ViewportOverlays:
    """
    This controller centralizes pause, inventory, and death overlay state transitions.
    The goal is to keep the viewport widget focused on orchestration while ensuring the
    visibility, input reset, capture toggling, and Z-order behavior remain identical.
    """
    def __init__(self, *, refs: OverlayRefs, runner: FixedStepRunner, inp: ViewportInput) -> None:
        self._r = refs
        self._runner = runner
        self._inp = inp

        self._paused: bool = False
        self._dead: bool = False
        self._inventory_open: bool = False

    def paused(self) -> bool:
        return bool(self._paused)

    def dead(self) -> bool:
        return bool(self._dead)

    def inventory_open(self) -> bool:
        return bool(self._inventory_open)

    def set_dead(self, on: bool) -> None:
        on = bool(on)
        if on == self._dead:
            return
        self._dead = on

        self._inp.reset()

        if self._dead:
            self._paused = False
            self._r.pause.setVisible(False)
            self.set_inventory_open(False)
            self._inp.set_mouse_capture(False)

            self._r.death.setVisible(True)
            self._r.death.raise_()
            return

        self._r.death.setVisible(False)
        self._runner.start()
        if (not self._paused) and (not self._inventory_open):
            self._inp.set_mouse_capture(True)
        self._r.crosshair.raise_()
        hud = self._r.hud_getter()
        if hud is not None:
            hud.raise_()

    def set_paused(self, on: bool) -> None:
        on = bool(on)
        if on == self._paused:
            return
        if self._dead:
            return

        self._paused = on
        self._inp.reset()

        if self._paused:
            self.set_inventory_open(False)
            self._inp.set_mouse_capture(False)
            self._r.pause.setVisible(True)
            self._r.pause.raise_()
            return

        self._r.pause.setVisible(False)
        self._runner.start()
        if not self._inventory_open:
            self._inp.set_mouse_capture(True)
        self._r.crosshair.raise_()
        hud = self._r.hud_getter()
        if hud is not None:
            hud.raise_()

    def set_inventory_open(self, on: bool) -> None:
        on = bool(on)
        if on == self._inventory_open:
            return

        self._inventory_open = on
        self._inp.reset()

        if self._inventory_open:
            self._inp.set_mouse_capture(False)
            self._r.inventory.setVisible(True)
            self._r.inventory.raise_()
            self._r.inventory.setFocus()
            return

        self._r.inventory.setVisible(False)
        if (not self._paused) and (not self._dead):
            self._runner.start()
            self._inp.set_mouse_capture(True)
            self._r.crosshair.raise_()
            hud = self._r.hud_getter()
            if hud is not None:
                hud.raise_()