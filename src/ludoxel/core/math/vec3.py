# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/core/math/vec3.py
from __future__ import annotations

from dataclasses import dataclass

import math


@dataclass(frozen=True)
class Vec3:
    """
    V = (x, y, z) in R^3.

    I define `Vec3` as the immutable three-scalar carrier for the lowest mathematical layer of my codebase. 
    At this layer I do not encode any type-level distinction among Euclidean positions, displacements, 
    velocities, directions, extents, colors, or any other quantity whose stored data is merely an ordered 
    triple of scalars. The structure I admit is limited to ordered storage and to the algebraic operations 
    that I declare on this type itself. Any stronger semantic reading is imposed by the caller.

    I make the class a frozen dataclass because adjacent systems replace whole vector values rather than 
    mutate components in place. Movement updates, collision integration, ray construction, block-shape 
    translation, cloud and sun placement, and camera or light-frame construction all exchange `Vec3` 
    values by value semantics. Every vector-valued operation in this module therefore returns a fresh 
    `Vec3`, and I admit no in-place mutation path in this mathematical layer.

    I do not validate finiteness, ordering, normalization, or physical admissibility at construction 
    time. The class is a carrier of three numbers, not a policy gate.
    """
    x: float
    y: float
    z: float

    def __add__(self, o: "Vec3") -> "Vec3":
        """
        (x1, y1, z1) + (x2, y2, z2) = (x1 + x2, y1 + y2, z1 + z2).

        I implement ordinary component-wise addition on R^3 and nothing more. The method does not
        distinguish point-plus-displacement from vector-plus-vector or any other geometric reading.
        It adds corresponding stored components and returns the resulting triple as a new immutable
        value.

        I rely on this primitive wherever a translated point or an accumulated offset must be formed
        from existing vectors. Direct instances include hit-point reconstruction in `intersection.py`, 
        ray-origin biasing in `build_system.py`, basis-weighted wish-direction accumulation in 
        `movement_system.py`, stabilization-anchor construction in `light_space.py`, and sun-center 
        placement in `sun_pass.py`.
        """
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        """
        (x1, y1, z1) - (x2, y2, z2) = (x1 - x2, y1 - y2, z1 - z2).

        I implement ordinary component-wise subtraction on R^3. The result may be read by callers as
        a displacement, a relative coordinate, or merely the algebraic difference of two stored
        triples, but the method itself encodes only subtraction of corresponding components.

        I rely on this operation where one location must be re-expressed relative to another before
        subsequent scalar tests are applied. A direct instance appears in `cloud_field.py`, where I
        form `c_world - eye` and then resolve the relative vector against `forward`, `right`, and
        `up` by inner products.
        """
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, k: float) -> "Vec3":
        """
        (x, y, z) * k = (x*k, y*k, z*k).

        I reserve this operator family for multiplication by a single scalar factor `k`. I do not
        overload it for matrix products, Hadamard products, or inner products. The algebraic content
        is therefore uniform scaling of each stored component by the same factor.

        The relation to `__rmul__ = __mul__` is literal and narrow. This method realizes the
        `Vec3 * scalar` spelling directly, and the alias admits the reflected `scalar * Vec3`
        spelling through the same computation path. I do not impose a law deeper than that explicit
        implementation fact.

        I rely on this primitive wherever a stored triple must be scaled by an external coefficient,
        including time-step displacement formation in movement and collision code, ray-origin biasing
        in `build_system.py`, sun-center placement in `sun_pass.py`, and light-position or
        stabilization-anchor construction in `light_space.py`. The method preserves neither unit
        length nor finiteness and applies no clamping.
        """
        return Vec3(self.x * k, self.y * k, self.z * k)

    __rmul__ = __mul__

    def dot(self, o: "Vec3") -> float:
        """
        dot(a, b) = a.x*b.x + a.y*b.y + a.z*b.z.

        I implement the standard Euclidean inner product on R^3. No normalization is performed for
        either operand. The returned scalar therefore carries both magnitude information and angular
        information. Any interpretation as `cos(angle(a, b))` presupposes that the caller has
        already supplied unit-length inputs elsewhere.

        I rely on this scalar primitive wherever a basis coordinate, directional support value, or
        projection onto an axis is required. That includes the translation terms of `mat4.look_dir()`, 
        the non-parallel up-hint test and stabilization-anchor construction in `light_space.py`, 
        and the frustum-style cloud culling tests in `cloud_field.py`.

        I attach no semantic tag beyond the inner product itself. The method computes only the scalar
        contraction of the two stored triples.
        """
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "Vec3") -> "Vec3":
        """
        cross(a, b) = (
            a.y*b.z - a.z*b.y,
            a.z*b.x - a.x*b.z,
            a.x*b.y - a.y*b.x
        ).

        I implement the standard vector product in R^3 with the orientation fixed by this
        determinant-expansion formula and thus by the right-hand rule. In exact arithmetic the result 
        is orthogonal to the two operands. I do not normalize the result and I do not repair degeneracy.

        That omission is deliberate. I use this method as the raw oriented-basis primitive in view-frame 
        and billboard construction, notably in `mat4.look_dir()`, `cloud_field.py`, and `sun_pass.py`. 
        When the operands are parallel or nearly parallel, the result may collapse to the zero vector 
        or to a numerically tiny vector, and any fallback policy remains outside this method.
        """
        return Vec3(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )

    def length(self) -> float:
        """
        norm2(v) = sqrt(x*x + y*y + z*z).

        I implement the Euclidean L2 norm directly as
        `math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z)`. I do not interpose staged
        `hypot` accumulation, compensated summation, scale-and-rescale stabilization, or any repair
        for exceptional values.

        For ordinary finite real inputs the returned scalar is non-negative and agrees with the norm
        induced by the standard inner product. I do not state a stronger implementation-level
        guarantee than that. If intermediate products overflow, or if any component is non-finite,
        Python's ordinary floating-point semantics govern the realized result.

        I use this norm directly wherever the code must perform an explicit smallness test on a
        vector magnitude, including zero-wish detection in `movement_system.py`, the post-
        normalization guard in `build_system.py`, and the billboard-basis fallback in `sun_pass.py`.
        """
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> "Vec3":
        """
        normalize(v) =
            v / norm2(v),   if norm2(v) > 1e-12,
            (0, 0, 0),      otherwise.

        I implement this branch law exactly. I first evaluate `n = self.length()`. If the computed
        norm satisfies `n <= 1e-12`, I return the exact zero vector and perform no reciprocal
        scaling. Otherwise I compute `inv = 1.0 / n` and return `(x*inv, y*inv, z*inv)` as a fresh
        `Vec3`.

        This guarded branch is the singularity convention of my mathematical layer. It is
        operationally material because `build_system.py` normalizes the incoming direction before DDA
        traversal, `mat4.look_dir()` normalizes frame vectors after cross products,
        `view_angles.py` normalizes direction constructors before publication, `light_space.py`
        normalizes the light direction, `cloud_field.py` normalizes billboard-frame axes, and
        `sun_pass.py` normalizes intermediate billboard axes before later use.

        I do not impose any broader totality or finiteness claim than the literal branch structure
        above. If `self.length()` yields a non-finite value, the guard `n <= 1e-12` follows
        Python's ordinary float comparison semantics, and the returned components are whatever the
        explicit multiplications by `1.0 / n` realize. For finite non-degenerate inputs, the
        positive branch yields the usual unit direction up to ordinary floating-point roundoff.
        """
        n = self.length()
        if n <= 1e-12:
            return Vec3(0.0, 0.0, 0.0)
        inv = 1.0 / n
        return Vec3(self.x * inv, self.y * inv, self.z * inv)


def clampf(x: float, lo: float, hi: float) -> float:
    """
    clamp(x; lo, hi) =
        lo,  if x < lo,
        hi,  if x > hi,
        x,   otherwise.

    I implement the exact branch expression `lo if x < lo else hi if x > hi else x`. I do not
    reorder the bounds, validate `lo <= hi`, or add any exceptional-value policy beyond the
    semantics of the written comparisons themselves. The function is therefore a scalar saturation
    map only to the extent that the caller supplies a coherent interval.

    I rely on this helper where the code must enforce explicit scalar admissibility windows, most
    visibly for movement-input confinement to `[-1, 1]` in `movement_system.py` and for player pitch
    confinement to `[-89.5, 89.5]` in `player_entity.py` before view-direction reconstruction.

    Because the implementation is comparison-defined and nothing more, Python's ordinary float
    comparison semantics govern edge cases. In particular, if `x` is NaN, both ordered comparisons
    are false and the function returns `x` unchanged.
    """
    return lo if x < lo else hi if x > hi else x
