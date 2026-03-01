# FILE: tools/acceptance/bedrock_movement_acceptance.py
from __future__ import annotations

import math
from dataclasses import dataclass

from src.maiming.application.session.session_manager import SessionManager

@dataclass(frozen=True)
class CaseResult:
    name: str
    avg_speed: float

def _avg(xs: list[float]) -> float:
    if not xs:
        return 0.0
    return float(sum(xs) / float(len(xs)))

def _run_case(name: str, *, dt: float, seconds: float, sprint: bool, hold_jump: bool) -> CaseResult:
    sm = SessionManager.create_default(seed=0)

    warm = 1.0
    total_steps = int(max(1, round(seconds / dt)))
    warm_steps = int(max(0, round(warm / dt)))

    speeds: list[float] = []

    jump_held = bool(hold_jump)
    jump_pressed_once = True

    for i in range(total_steps):
        p = sm.player
        hs = math.sqrt(float(p.velocity.x) * float(p.velocity.x) + float(p.velocity.z) * float(p.velocity.z))

        if i >= warm_steps:
            speeds.append(float(hs))

        jp = False
        if bool(jump_pressed_once):
            jp = True
            jump_pressed_once = False

        sm.step(
            dt=float(dt),
            move_f=1.0,
            move_s=0.0,
            jump_held=bool(jump_held),
            jump_pressed=bool(jp),
            sprint=bool(sprint),
            crouch=False,
            mdx=0.0,
            mdy=0.0,
            auto_jump_enabled=False,
        )

    return CaseResult(name=str(name), avg_speed=_avg(speeds))

def main() -> None:
    secs = 10.0

    for dt in (1.0 / 120.0, 1.0 / 60.0, 1.0 / 20.0):
        r_walk = _run_case("walk", dt=dt, seconds=secs, sprint=False, hold_jump=False)
        r_sprint = _run_case("sprint", dt=dt, seconds=secs, sprint=True, hold_jump=False)
        r_sj = _run_case("sprint_jump", dt=dt, seconds=secs, sprint=True, hold_jump=True)

        print(f"dt={dt:.6f} walk_avg={r_walk.avg_speed:.3f} sprint_avg={r_sprint.avg_speed:.3f} sprint_jump_avg={r_sj.avg_speed:.3f}")

if __name__ == "__main__":
    main()