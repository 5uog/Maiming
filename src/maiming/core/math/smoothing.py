# FILE: src/maiming/core/math/smoothing.py
from __future__ import annotations

import math


def exp_alpha(rate: float, dt: float) -> float:
    """
    alpha = 1 - exp(-r*t)
    r = max(0, rate)
    t = max(0, dt)

    This function returns the exponential blending gain used by a first-order relaxation step of the 
    form "x_next = x_cur + (x_target - x_cur) * alpha". For strictly positive, non-negligible arguments, 
    namely after the internal sanitization "r = max(0, rate), t = max(0, dt)", and under the branch 
    condition "r > 1e-9 and t > 1e-9", the returned value is exactly "alpha = 1 - exp(-r*t)".

    The foregoing expression is the closed-form discrete gain associated with the scalar linear decay 
    law "d/dtau e(tau) = -r * e(tau)", where e denotes the deviation from a constant target over the 
    interval of duration t. Consequently, substituting the returned alpha into 

        x_next = x_cur + (x_target - x_cur) * alpha 

        yields     x_next = x_target + (x_cur - x_target) * exp(-r*t), 

    which preserves the exponential approach factor exp(-r*t) exactly at the sampling boundary, 
    subject only to the explicit threshold rules implemented below.

    The implementation does not admit negative effective parameters. Any negative input rate or negative 
    input time step is clamped to zero prior to further evaluation. Thereafter, if either sanitized 
    quantity satisfies "r <= 1e-9 or t <= 1e-9", the function returns 0.0 by construction, rather than 
    evaluating the exponential formula. This is not an approximation stated outside the code; it is 
    the literal branch behavior of the implementation. Accordingly, the function defines a piecewise 
    mapping

        exp_alpha(rate, dt) = 0.0,
            if max(0, rate) <= 1e-9 or max(0, dt) <= 1e-9,

        exp_alpha(rate, dt) = 1 - exp(-max(0, rate) * max(0, dt)),
            otherwise.

    Under the positive branch, the result satisfies "0.0 < alpha < 1.0", because exp(-r*t) lies strictly 
    between 0 and 1 for r*t > 0. Under the threshold branch, the result is exactly 0.0. Therefore the 
    total codomain realized by this implementation is the half-open interval "0.0 <= alpha < 1.0".

    This property is operationally significant in the importing code. In `session_manager.py`, the 
    returned gain is used in assignments such as "nxt = cur + (target - cur) * a", for crouch-eye and 
    step-eye offset relaxation. In `movement_system.py`, it is used in velocity relaxation updates 
    such as "vx = vx + (target_x - vx) * a, vy = vy + (target_y - vy) * a, vz = vz + (target_z - vz) * a", 
    for flight motion, and similarly for horizontal ground or air acceleration in Bedrock-style movement. 
    In each such use, the mathematical role of this function is identical: it furnishes the per-step 
    interpolation factor that converts a continuous exponential approach rate into a frame-duration-
    aware discrete update coefficient.

    No further semantics should be imputed here. This function does not itself update state, does not 
    retain history, does not clamp the output to 1.0, and does not encode any target value. Its sole 
    responsibility is the computation of the scalar gain alpha from a nonnegative effective rate and 
    a nonnegative effective time increment, with a zero-return convention for negligibly small arguments.
    
    Peace out brudda.
    """
    r = float(max(0.0, rate))
    t = float(max(0.0, dt))

    if r <= 1e-9 or t <= 1e-9:
        return 0.0

    return 1.0 - math.exp(-r * t)