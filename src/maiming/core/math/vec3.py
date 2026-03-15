# FILE: src/maiming/core/math/vec3.py
from __future__ import annotations

from dataclasses import dataclass

import math


@dataclass(frozen=True)
class Vec3:
    """
    V = (x, y, z) in R^3.

    I define `Vec3` as the immutable three-scalar carrier for the lowest mathematical layer of this
    codebase. At this layer I do not impose a type-level distinction between Euclidean positions,
    displacements, velocities, directions, extents, colors, or any other quantity that is merely an
    ordered triple of scalars. The only structure established here is the ordered storage of three
    components together with the operations explicitly declared below. Any stronger semantic reading
    is imposed by the caller, not by this class.

    I make the class a frozen dataclass because the surrounding code replaces whole values rather than
    mutating vector components in place. Movement updates, collision correction, ray construction, 
    block-shape translation, cloud placement, and camera or light-frame construction all pass `Vec3` 
    values across subsystem boundaries as value objects. Every vector-valued operation below therefore 
    returns a fresh `Vec3`, and no in-place mutation path is admitted in this module.
    """
    x: float
    y: float
    z: float

    def __add__(self, o: "Vec3") -> "Vec3":
        """
        (x1, y1, z1) + (x2, y2, z2) = (x1 + x2, y1 + y2, z1 + z2).

        I implement ordinary component-wise addition on R^3 and nothing more. The method does not
        distinguish point-plus-displacement from vector-plus-vector or any other geometric reading.
        It simply adds corresponding stored components and returns the resulting triple as a new
        immutable value.

        I rely on this primitive wherever a translated position or an accumulated offset must be
        formed directly from existing vectors, including ray hit-point reconstruction, positional
        correction in collision resolution, cloud-shift application, sun-center placement, and the
        accumulation of basis-weighted movement contributions.
        """
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        """
        (x1, y1, z1) - (x2, y2, z2) = (x1 - x2, y1 - y2, z1 - z2).

        I implement ordinary component-wise subtraction on R^3. The result may be read by callers as
        a displacement, a relative coordinate, or merely the algebraic difference of two stored triples,
        but this method itself encodes only the subtraction of corresponding components.

        Within the presently shown code I rely on this operation where one location or center must be
        re-expressed relative to another before subsequent scalar tests are applied, most visibly in the
        camera-relative cloud culling path of `cloud_field.py`, where `c_world - eye` is formed and then
        resolved against `forward`, `right`, and `up` by dot products.
        """
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, k: float) -> "Vec3":
        """
        (x, y, z) * k = k * (x, y, z) = (x*k, y*k, z*k).

        I reserve this operator family for multiplication by a single scalar factor `k`. I do not
        overload it for matrix products, Hadamard products, or inner products. The algebraic content
        encoded here is therefore nothing other than uniform scaling of each stored component by the
        same scalar. The relation between this method and the immediately following alias must be stated
        exactly. The implementation below realizes the `Vec3 * scalar` spelling directly, and
        `__rmul__ = __mul__` thereafter admits the reflected `scalar * Vec3` spelling through the same
        computation path. I do not prove or impose any deeper law than that literal implementation fact.

        I use this primitive wherever a stored triple must be scaled by an external coefficient,
        including time-step displacement formation in movement and collision code, ray-origin biasing in
        interaction code, sun-center placement in `sun_pass.py`, and light-position or stabilization-
        anchor construction in `light_space.py`. The method preserves neither unit length nor finiteness
        and applies no clamping.
        """
        return Vec3(self.x * k, self.y * k, self.z * k)

    __rmul__ = __mul__

    def dot(self, o: "Vec3") -> float:
        """
        dot(a, b) = a.x*b.x + a.y*b.y + a.z*b.z.

        I implement the standard Euclidean inner product on R^3. 
        No normalization is performed for either operand. The returned scalar therefore carries both 
        magnitude information and angular information. Any interpretation as cos(theta) presupposes 
        that the caller has already supplied unit-length inputs elsewhere.

        This scalar primitive is used in the presently shown code wherever a basis coordinate, 
        directional support value, or projection onto an axis is required. That includes the translation 
        terms of `mat4.look_dir()`, the non-parallel up-hint test and stabilized anchor construction 
        in `light_space.py`, and the camera-relative cloud culling tests in `cloud_field.py`.

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

        I implement the standard vector product in R^3 with the orientation fixed by the displayed
        determinant expansion and thus by the right-hand rule. The result is orthogonal to the ideal
        input operands in exact arithmetic, but this method does not itself normalize the result or
        repair degeneracy.

        That omission is deliberate. I use this method as the raw oriented-basis primitive in view-frame
        and billboard construction, notably in `mat4.look_dir`, `cloud_field.py`, and `sun_pass.py`.
        When the operands are parallel or nearly parallel, the result may collapse to the zero vector or
        a numerically tiny vector, and any fallback policy remains outside this method.
        """
        return Vec3(self.y * o.z - self.z * o.y, self.z * o.x - self.x * o.z, self.x * o.y - self.y * o.x)

    def length(self) -> float:
        """
        ||v||_2 = sqrt(x^2 + y^2 + z^2).

        I implement the Euclidean L2 norm formula directly as `math.sqrt(self.x * self.x + self.y * 
        self.y + self.z * self.z)`. No staged `hypot` accumulation, compensated summation, scaling 
        transform, or exceptional-value repair is interposed.

        For ordinary finite real inputs the returned scalar agrees with the Euclidean norm induced by
        the standard inner product and is non-negative. I do not state a stronger implementation-level
        guarantee than that. If intermediate products overflow or if any component is non-finite,
        Python's ordinary floating-point semantics govern the realized result.

        I use this norm as the local magnitude test wherever the code must distinguish a usable
        direction from an effectively zero vector, including wish-direction synthesis in movement,
        sun-billboard basis fallback, cloud-frame construction, and the degeneracy guard inside
        `normalized()`.
        """
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> "Vec3":
        """
        normalize(v) =
            v / ||v||_2,      if ||v||_2 > 1e-12,
            (0, 0, 0),        otherwise.

        I implement the exact branch law written above after first evaluating `n = self.length()`. 
        If the computed norm satisfies `n <= 1e-12`, I return the exact zero vector and perform no
        reciprocal scaling. Otherwise I compute `inv = 1.0 / n` and return `(x*inv, y*inv, z*inv)` 
        as a fresh `Vec3`.

        The guarded branch is the singularity convention of this mathematical layer. 
        It is operationally material because ray picking normalizes the incoming direction before 
        DDA traversal, view and light matrix construction normalize basis vectors after cross products, 
        camera and sun direction helpers normalize their outputs before publication, and billboard 
        construction normalizes intermediate axes before later dot-product use.

        I do not impose any broader totality or finiteness claim than the literal branch structure
        above. When `self.length()` yields a non-finite value, the guard `n <= 1e-12` follows Python's
        ordinary float comparison semantics, and the returned components are whatever the explicit
        multiplications by `1.0 / n` realize. For finite non-degenerate inputs, the positive branch
        yields the usual unit direction up to ordinary floating-point roundoff.
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

    I implement the exact branch expression `lo if x < lo else hi if x > hi else x`. I do not reorder
    the bounds, validate `lo <= hi`, or add any exceptional-value policy beyond the semantics of the
    written comparisons themselves. The function is therefore a scalar saturation map only to the extent
    that the caller supplies a coherent interval.

    I use this helper where the code must enforce explicit scalar admissibility windows, most visibly for
    movement-input confinement to `[-1, 1]` and for player pitch confinement to `[-89.5, 89.5]` before
    view-direction reconstruction.

    Because the implementation is comparison-defined and nothing more, Python's ordinary float comparison
    semantics govern edge cases. In particular, if `x` is NaN, both ordered comparisons are false and the
    function returns `x` unchanged.
    """
    return lo if x < lo else hi if x > hi else x