# FILE: src/maiming/core/math/vec3.py
from __future__ import annotations

from dataclasses import dataclass

import math


@dataclass(frozen=True)
class Vec3:
    """
    V = (x, y, z) in R^3.

    This type denotes an immutable ordered triple of real-valued components. Within the presently 
    disclosed codebase, the same algebraic carrier is used, without internal tagging, for Euclidean 
    position vectors, displacement vectors, velocity vectors, unit or non-unit direction vectors, 
    per-axis sizes, colors, and other three-component quantities. The class itself therefore furnishes 
    only the elementary vector-space operations explicitly defined below, and imposes no semantic 
    distinction among such uses.

    The frozen dataclass form is of structural importance. Every operation defined herein is purely 
    functional and returns a fresh Vec3 instance; no in-placemutation path is provided by this module. 
    This is materially consistent with the surrounding usage, wherein values of this type are freely 
    constructed, copied, and replaced across geometry, movement, rendering, and persistence boundaries.
    """
    x: float
    y: float
    z: float

    def __add__(self, o: "Vec3") -> "Vec3":
        """
        (x1, y1, z1) + (x2, y2, z2) = (x1 + x2, y1 + y2, z1 + z2).

        This is the canonical component-wise vector addition in R^3. No geometric reinterpretation is 
        embedded in the implementation; the operation is purely algebraic. In the provided codebase, 
        this operator is used, inter alia, to advance points by scaled directions, to combine basis-
        weighted movement contributions, and to reconstruct hit positions from ray parameters.

        The method performs exactly three floating-point additions and returns the resulting triple 
        as a new immutable Vec3. No normalization, clamping, or tolerance handling is applied.
        """
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        """
        (x1, y1, z1) - (x2, y2, z2) = (x1 - x2, y1 - y2, z1 - z2).

        This is the canonical component-wise vector subtraction in R^3. In the disclosed system, the 
        operation serves both as displacement formation between points and as ordinary vector difference. 
        The implementation does not distinguish these interpretations; it merely computes the algebraic
        difference of corresponding components.

        The method performs exactly three floating-point subtractions and returns a new Vec3. 
        No post-processing is applied.
        """
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, k: float) -> "Vec3":
        """
        k * (x, y, z) = (k*x, k*y, k*z).

        This method implements scalar multiplication by a real factor k. The code is strictly component-
        wise and does not admit matrix multiplication, dot products, Hadamard products, or any other 
        overloaded interpretation. Within the surrounding files, it is used to scale directions by 
        reach, time-step displacement by dt, camera or cloud offsets by amplitudes, and orthonormal 
        basis vectors by projected coordinates.

        The implementation performs exactly three floating-point multiplications and returns a new Vec3. 
        No saturation, finite-value check, or unit-length preservation is attempted.
        """
        return Vec3(self.x * k, self.y * k, self.z * k)

    __rmul__ = __mul__

    def dot(self, o: "Vec3") -> float:
        """
        dot(a, b) = a.x*b.x + a.y*b.y + a.z*b.z.

        This is the standard Euclidean inner product on R^3. The value returned is a scalar and is 
        used throughout the provided code as the primitive from which projection, signed alignment, 
        camera-space coordinate extraction, and orthogonality-related constructions are derived.

        No normalization of either operand is performed. Consequently, the result encodes both angular 
        relation and magnitude. If unit vectors are required for a geometric interpretation such as 
        cos(theta), that precondition must have been established by the caller or by prior normalization 
        in upstream code.
        """
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "Vec3") -> "Vec3":
        """
        cross(a, b) = (a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y*b.x).

        This is the standard vector product in R^3, oriented according to the right-hand rule encoded 
        by the above determinant expansion. In the surrounding code, it is used to construct local 
        orthogonal frames, notably right and up vectors from a forward direction and an up hint.

        The method does not enforce non-collinearity of the operands. If the input vectors are parallel 
        or nearly parallel, the returned vector may be the zero vector or numerically very small; 
        downstream callers therefore sometimes normalize the result and rely on external fallback logic 
        when degeneracy must be avoided.
        """
        return Vec3(self.y * o.z - self.z * o.y, self.z * o.x - self.x * o.z, self.x * o.y - self.y * o.x)

    def length(self) -> float:
        """
        ||v||_2 = sqrt(x^2 + y^2 + z^2).

        This is the Euclidean L2 norm induced by the standard inner product on R^3. The returned scalar 
        is non-negative by construction. In the supplied code, it is used to determine whether a vector 
        is effectively non-zero, to compute horizontal or full 3D magnitudes, and to prepare normalized
        directions for ray casting, view-space construction, and movement logic.

        The implementation is the direct scalar formula and does not call hypot-style staged accumulation. 
        Accordingly, it reflects the ordinary floating-point behavior of squaring and summation in 
        Python's binary64 arithmetic before the final square root.
        """
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> "Vec3":
        """
        normalize(v) =
            v / ||v||_2,         if ||v||_2 > 1e-12
            (0.0, 0.0, 0.0),     otherwise.

        This method attempts Euclidean normalization of the vector. The threshold 1e-12 is a deliberate 
        degeneracy guard: when the computed norm is less than or equal to that bound, reciprocal scaling 
        is suppressed and the zero vector is returned instead. The branch therefore defines total 
        behavior over all finite inputs and avoids division by a numerically tiny denominator.

        In the disclosed code, this convention is operationally significant. Direction-producing functions, 
        such as forward-vector construction, normalize their outputs; ray picking normalizes incoming 
        directions before traversal; camera-frame construction normalizes basis vectors after cross 
        products; sun and cloud passes likewise normalize view or light directions. The zero-vector 
        fallback therefore serves as a local singularity-handling rule for degenerate inputs.

        It must be noted with precision that the returned vector is guaranteed to have unit Euclidean 
        norm only in the branch where ||v||_2 > 1e-12 and ordinary floating-point roundoff is disregarded. 
        In the guarded branch, the output is exactly the zero vector and hence not a unit vector.
        """
        n = self.length()
        if n <= 1e-12:
            return Vec3(0.0, 0.0, 0.0)
        inv = 1.0 / n
        return Vec3(self.x * inv, self.y * inv, self.z * inv)


def clampf(x: float, lo: float, hi: float) -> float:
    """
    clamp(x; lo, hi) =
        lo, if x < lo
        hi, if x > hi
        x,  otherwise.

    This is a scalar saturation map onto the closed interval [lo, hi], assuming that the caller supplies 
    bounds intended to function as a lower and upper limit. The implementation is branch-based and exact 
    with respect to the ordering tests written; it does not reorder the bounds, does not validate 
    lo <= hi, and does not special-case NaN.

    Its role in the disclosed system is concrete and recurrent. It is used to confine movement inputs 
    to [-1, 1], to restrict pitch into a prescribed angular window, to cap visual effect strengths to 
    [0, 1], and to constrain other scalar parameters whose legal domain is interval-bounded at the call site.

    Because the expression is implemented as "lo if x < lo else hi if x > hi else x", the behavior 
    under exceptional floating-point values follows ordinary Python comparison semantics. 
    In particular, no additional sanitization layer is supplied by this function.
    """
    return lo if x < lo else hi if x > hi else x