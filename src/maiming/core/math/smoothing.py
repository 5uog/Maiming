# FILE: src/maiming/core/math/smoothing.py
from __future__ import annotations

import math


def exp_alpha(rate: float, dt: float) -> float:
    """
    alpha(rate, dt) =
        0.0,                                if max(0, rate) <= 1e-9 or max(0, dt) <= 1e-9,
        1 - exp(-max(0, rate)*max(0, dt)),  otherwise.

    I use this function to convert a continuous first-order relaxation rate into the discrete gain of
    an affine update of the form `x_next = x_cur + (x_target - x_cur) * alpha`.

    Writing `r = float(max(0.0, rate))` and `t = float(max(0.0, dt))`, the positive branch
    implemented below is exactly `alpha = 1.0 - exp(-r*t)`. Substituting that coefficient into the
    affine update yields `x_next = x_target + (x_cur - x_target) * exp(-r*t)`, so the residual error
    factor at the sample boundary is the same exponential decay factor that solves the scalar ODE
    `de/dtau = -r*e` over an interval of duration `t` under a constant target.

    The sanitization and threshold policy must be read literally. I first clamp both arguments below
    at zero through `max(0.0, ...)`, then I test the effective values against `1e-9`. If either
    effective argument is at or below that threshold, I return the exact scalar `0.0` and do not
    evaluate the exponential expression at all. Otherwise I evaluate the displayed exponential
    expression once and return its complement.

    For ordinary finite inputs the realized value satisfies `0.0 <= alpha <= 1.0`. I intentionally
    do not state the stronger bound `alpha < 1.0` at the implementation level, because in floating-
    point arithmetic the exponential term may underflow to `0.0` for sufficiently large positive
    `r*t`, in which case the returned value is exactly `1.0`.

    I use this scalar precisely in `movement_system.py`, where it governs velocity relaxation in
    `step_flying()` and horizontal acceleration smoothing in `step_bedrock()`. The function itself
    neither updates state nor stores history. It computes only the frame-duration-aware scalar gain.
    """
    r = float(max(0.0, rate))
    t = float(max(0.0, dt))

    if r <= 1e-9 or t <= 1e-9:
        return 0.0

    return 1.0 - math.exp(-r * t)