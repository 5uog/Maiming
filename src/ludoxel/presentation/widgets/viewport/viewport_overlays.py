# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/presentation/widgets/viewport/viewport_overlays.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtWidgets import QWidget

from ....application.session.fixed_step_runner import FixedStepRunner
from .viewport_input import ViewportInput


@dataclass
class OverlayRefs:
    pause: QWidget
    settings: QWidget
    othello_settings: QWidget
    inventory: QWidget
    death: QWidget
    crosshair: QWidget
    hotbar: QWidget
    hud_getter: Callable[[], QWidget | None]
    othello_hud_getter: Callable[[], QWidget | None]


class ViewportOverlays:

    def __init__(self, *, refs: OverlayRefs, runner: FixedStepRunner, inp: ViewportInput) -> None:
        self._r = refs
        self._runner = runner
        self._inp = inp

        self._paused: bool = False
        self._dead: bool = False
        self._inventory_open: bool = False
        self._settings_open: bool = False
        self._othello_settings_open: bool = False
        self._othello_settings_return_to_pause: bool = False

    def paused(self) -> bool:
        return bool(self._paused)

    def dead(self) -> bool:
        return bool(self._dead)

    def inventory_open(self) -> bool:
        return bool(self._inventory_open)

    def settings_open(self) -> bool:
        return bool(self._settings_open)

    def othello_settings_open(self) -> bool:
        return bool(self._othello_settings_open)

    def any_modal_open(self) -> bool:
        return bool(self._paused or self._inventory_open or self._settings_open or self._othello_settings_open or self._dead)

    def _raise_game_hud(self) -> None:
        self._r.hotbar.setVisible(True)
        self._r.hotbar.raise_()
        self._r.crosshair.raise_()

        hud = self._r.hud_getter()
        if hud is not None:
            hud.raise_()

        othello_hud = self._r.othello_hud_getter()
        if othello_hud is not None:
            othello_hud.raise_()

    def set_dead(self, on: bool) -> None:
        on = bool(on)
        if on == self._dead:
            return
        self._dead = on

        self._inp.reset()

        if self._dead:
            self._paused = False
            self._settings_open = False
            self._othello_settings_open = False
            self._othello_settings_return_to_pause = False

            self._r.pause.setVisible(False)
            self._r.settings.setVisible(False)
            self._r.othello_settings.setVisible(False)
            self._r.hotbar.setVisible(False)
            self.set_inventory_open(False)
            self._inp.set_mouse_capture(False)

            self._r.death.setVisible(True)
            self._r.death.raise_()
            return

        self._r.death.setVisible(False)
        self._runner.start()

        if (not self._paused) and (not self._inventory_open) and (not self._settings_open) and (not self._othello_settings_open):
            self._inp.set_mouse_capture(True)
            self._r.hotbar.setVisible(True)

        self._raise_game_hud()

    def set_paused(self, on: bool) -> None:
        on = bool(on)

        if self._dead:
            return

        if on:
            self._paused = True
            self._settings_open = False
            self._othello_settings_open = False
            self._othello_settings_return_to_pause = False
            self._inp.reset()

            self.set_inventory_open(False)
            self._inp.set_mouse_capture(False)
            self._r.hotbar.setVisible(False)

            self._r.settings.setVisible(False)
            self._r.othello_settings.setVisible(False)
            self._r.pause.setVisible(True)
            self._r.pause.raise_()
            self._r.pause.setFocus()
            return

        if (not self._paused) and (not self._settings_open) and (not self._othello_settings_open):
            return

        self._paused = False
        self._settings_open = False
        self._othello_settings_open = False
        self._othello_settings_return_to_pause = False
        self._inp.reset()

        self._r.pause.setVisible(False)
        self._r.settings.setVisible(False)
        self._r.othello_settings.setVisible(False)

        if not self._inventory_open:
            self._runner.start()
            self._inp.set_mouse_capture(True)
            self._r.hotbar.setVisible(True)

        self._raise_game_hud()

    def set_settings_open(self, on: bool) -> None:
        on = bool(on)

        if self._dead:
            return

        if on == self._settings_open:
            return

        self._settings_open = on
        self._inp.reset()

        if self._settings_open:
            self._paused = True
            self._othello_settings_open = False
            self._othello_settings_return_to_pause = False
            self.set_inventory_open(False)
            self._inp.set_mouse_capture(False)
            self._r.hotbar.setVisible(False)

            self._r.pause.setVisible(False)
            self._r.othello_settings.setVisible(False)
            self._r.settings.setVisible(True)
            self._r.settings.raise_()
            self._r.settings.setFocus()
            return

        self._r.settings.setVisible(False)

        if self._paused:
            self._r.pause.setVisible(True)
            self._r.pause.raise_()
            self._r.pause.setFocus()
            return

        if not self._inventory_open:
            self._runner.start()
            self._inp.set_mouse_capture(True)
            self._r.hotbar.setVisible(True)

        self._raise_game_hud()

    def set_othello_settings_open(self, on: bool) -> None:
        on = bool(on)

        if self._dead:
            return

        if on == self._othello_settings_open:
            return

        self._othello_settings_open = on
        self._inp.reset()

        if self._othello_settings_open:
            self._othello_settings_return_to_pause = bool(self._paused)
            self._settings_open = False
            self.set_inventory_open(False)
            self._inp.set_mouse_capture(False)
            self._r.hotbar.setVisible(False)

            self._r.pause.setVisible(False)
            self._r.settings.setVisible(False)
            self._r.othello_settings.setVisible(True)
            self._r.othello_settings.raise_()
            self._r.othello_settings.setFocus()
            return

        self._r.othello_settings.setVisible(False)

        if self._othello_settings_return_to_pause and self._paused:
            self._r.pause.setVisible(True)
            self._r.pause.raise_()
            self._r.pause.setFocus()
            return

        self._paused = False
        self._othello_settings_return_to_pause = False

        if not self._inventory_open:
            self._runner.start()
            self._inp.set_mouse_capture(True)
            self._r.hotbar.setVisible(True)

        self._raise_game_hud()

    def set_inventory_open(self, on: bool) -> None:
        on = bool(on)

        if self._dead or self._paused or self._settings_open or self._othello_settings_open:
            if on:
                return

        if on == self._inventory_open:
            return

        self._inventory_open = on
        self._inp.reset()

        if self._inventory_open:
            self._inp.set_mouse_capture(False)
            self._r.hotbar.setVisible(False)
            self._r.inventory.setVisible(True)
            self._r.inventory.raise_()
            self._r.inventory.setFocus()
            return

        self._r.inventory.setVisible(False)

        if (not self._paused) and (not self._dead) and (not self._settings_open) and (not self._othello_settings_open):
            self._runner.start()
            self._inp.set_mouse_capture(True)
            self._r.hotbar.setVisible(True)
            self._raise_game_hud()
