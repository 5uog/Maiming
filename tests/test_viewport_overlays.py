# FILE: tests/test_viewport_overlays.py
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from maiming.application.session.fixed_step_runner import FixedStepRunner
from maiming.presentation.widgets.viewport.viewport_overlays import OverlayRefs, ViewportOverlays


class _StubWidget:
    def __init__(self) -> None:
        self.visible = False
        self.focused = False

    def setVisible(self, on: bool) -> None:
        self.visible = bool(on)

    def raise_(self) -> None:
        return

    def setFocus(self) -> None:
        self.focused = True


class _StubInput:
    def __init__(self) -> None:
        self.captured = False
        self.reset_calls = 0

    def reset(self) -> None:
        self.reset_calls += 1

    def set_mouse_capture(self, on: bool) -> None:
        self.captured = bool(on)


class ViewportOverlaysTests(unittest.TestCase):
    def test_othello_settings_close_resumes_gameplay_without_opening_pause(self) -> None:
        pause = _StubWidget()
        settings = _StubWidget()
        othello_settings = _StubWidget()
        inventory = _StubWidget()
        death = _StubWidget()
        crosshair = _StubWidget()
        hotbar = _StubWidget()
        hud = _StubWidget()
        othello_hud = _StubWidget()
        inp = _StubInput()
        runner = FixedStepRunner(step_dt=1.0 / 60.0, on_step=lambda _dt: None)

        overlays = ViewportOverlays(
            refs=OverlayRefs(
                pause=pause,
                settings=settings,
                othello_settings=othello_settings,
                inventory=inventory,
                death=death,
                crosshair=crosshair,
                hotbar=hotbar,
                hud_getter=lambda: hud,
                othello_hud_getter=lambda: othello_hud,
            ),
            runner=runner,
            inp=inp,
        )

        overlays.set_othello_settings_open(True)
        self.assertTrue(overlays.othello_settings_open())
        self.assertFalse(overlays.paused())
        self.assertTrue(othello_settings.visible)

        overlays.set_othello_settings_open(False)
        self.assertFalse(overlays.othello_settings_open())
        self.assertFalse(overlays.paused())
        self.assertFalse(pause.visible)
        self.assertTrue(hotbar.visible)
        self.assertTrue(inp.captured)


if __name__ == "__main__":
    unittest.main()
