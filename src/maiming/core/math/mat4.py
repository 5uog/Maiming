# FILE: src/maiming/core/math/mat4.py
from __future__ import annotations
import math
import numpy as np

from .vec3 import Vec3


def identity() -> np.ndarray:
    """
    I_4 = [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ].

    I return the exact matrix produced by `np.identity(4, dtype=np.float32)`. The dtype is therefore
    fixed at `float32` at construction time, and no post-processing layer, semantic wrapper, or copied
    variant is interposed.

    I use this matrix as the neutral element of transform composition wherever a no-op 4x4 transform is
    required. In the presently shown code that occurs both as the fallback light-space transform in
    `frame_pipeline.py` when light-space rendering is bypassed and as the construction base inside
    `look_dir()`, where the final row is intentionally inherited from the identity matrix.
    """
    return np.identity(4, dtype=np.float32)


def perspective(fov_y_deg: float, aspect: float, z_near: float, z_far: float) -> np.ndarray:
    """
    f = 1 / tan(radians(fov_y_deg) / 2)
    a = max(aspect, 1e-9)

    M = [
        [f/a,  0,   0,                                  0],
        [0,    f,   0,                                  0],
        [0,    0,   (z_far + z_near)/(z_near - z_far),  (2*z_far*z_near)/(z_near - z_far)],
        [0,    0,  -1,                                  0]
    ].

    I construct exactly the matrix written above. The array is first allocated as zeros with dtype
    `float32`, and I then assign only the five non-zero entries shown in the formula. Every unspecified
    entry therefore remains `0.0` by construction.

    The guard policy is intentionally narrow. I protect only the aspect denominator by replacing the raw
    value with `max(float(aspect), 1e-9)`. I do not protect the field-of-view singularity
    `tan(fov_y/2) = 0`, and I do not protect the clip-plane coincidence singularity `z_near == z_far`.
    Accordingly, finite conventional perspective behavior presupposes that the caller supplies a non-
    singular vertical field of view and distinct near and far distances.

    For a homogeneous point `p_h = (x, y, z, 1)^T`, the pre-divide clip coordinate is exactly `M @ p_h`.
    The projective division step is not performed here. I only materialize the 4x4 coefficient matrix.

    I use this matrix in `frame_pipeline.py` for the world projection transform and, separately, for the
    first-person hand projection transform with a different near plane and a view-model FOV.
    """
    f = 1.0 / math.tan(math.radians(fov_y_deg) * 0.5)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / max(float(aspect), 1e-9)
    m[1, 1] = f
    m[2, 2] = (z_far + z_near) / (z_near - z_far)
    m[2, 3] = (2.0 * z_far * z_near) / (z_near - z_far)
    m[3, 2] = -1.0
    return m


def ortho(left: float, right: float, bottom: float, top: float, z_near: float, z_far: float) -> np.ndarray:
    """
    rl = max(right - left, 1e-9)
    tb = max(top - bottom, 1e-9)
    fn = max(z_far - z_near, 1e-9)

    M = [
        [2/rl,  0,     0,      -(right + left)/rl],
        [0,     2/tb,  0,      -(top + bottom)/tb],
        [0,     0,    -2/fn,   -(z_far + z_near)/fn],
        [0,     0,     0,       1]
    ].

    I construct exactly the coefficient matrix stated above. The array is allocated as zeros with dtype
    `float32`, after which I write the diagonal scale terms, the translation terms, and the homogeneous
    bottom-right entry `1.0`. No other entries are modified.

    The denominator policy is again explicit and must not be overstated. I do not preserve the raw spans
    `right - left`, `top - bottom`, and `z_far - z_near`. I replace each by a positive lower-bounded
    effective span through `max(span, 1e-9)`. This has a concrete consequence: degenerate intervals and
    reversed intervals do not survive algebraically. A mirrored bound configuration such as `right < left`
    is not represented as a negative scale in the output matrix; it is collapsed onto the positive minimum
    denominator instead.

    For a homogeneous point `p_h = (x, y, z, 1)^T`, the transformed coordinate is exactly `M @ p_h`.
    No clipping or viewport mapping is performed here. I only materialize the orthographic 4x4 map.

    I use this matrix in `light_space.py` for the orthographic projection part of the directional-light
    shadow transform.
    """
    m = np.zeros((4, 4), dtype=np.float32)
    rl = max(right - left, 1e-9)
    tb = max(top - bottom, 1e-9)
    fn = max(z_far - z_near, 1e-9)

    m[0, 0] = 2.0 / rl
    m[1, 1] = 2.0 / tb
    m[2, 2] = -2.0 / fn
    m[3, 3] = 1.0

    m[0, 3] = -(right + left) / rl
    m[1, 3] = -(top + bottom) / tb
    m[2, 3] = -(z_far + z_near) / fn
    return m


def look_dir(eye: Vec3, forward: Vec3, up_hint: Vec3 = Vec3(0.0, 1.0, 0.0)) -> np.ndarray:
    """
    f = normalize(forward)
    r = normalize(up_hint x f)
    u = normalize(f x r)

    M = [
        [ r.x,   r.y,   r.z,  -dot(r, eye)],
        [ u.x,   u.y,   u.z,  -dot(u, eye)],
        [-f.x,  -f.y,  -f.z,   dot(f, eye)],
        [ 0.0,   0.0,   0.0,   1.0]
    ].

    I build the exact 4x4 view matrix written above. The matrix is initialized from `identity()`, so its
    dtype is `float32` from the outset and its last row remains `[0.0, 0.0, 0.0, 1.0]` after I populate
    the first three rows and translation entries.

    The basis construction is fixed by the code and should be read literally. I first normalize the
    supplied forward vector, then compute the right vector as `normalize(up_hint x f)`, and finally
    compute the corrected up vector as `normalize(f x r)`. I do not use `f x up_hint` for the right axis;
    the handedness of the resulting frame is therefore exactly the one encoded by the two displayed cross
    products.

    For a homogeneous point `p_h = (p.x, p.y, p.z, 1)^T`, the first three coordinates of `M @ p_h` are

        r · (p - eye),
        u · (p - eye),
        -f · (p - eye),

    provided the basis vectors are non-degenerate. This is not an external geometric gloss layered over
    the function. It is the direct algebra of the populated rows and translation terms.

    I do not add any degeneracy repair beyond the branch behavior inherited from `Vec3.normalized()`. If
    `forward` is zero or effectively zero, then `f` becomes the zero vector. If `up_hint` is parallel or
    nearly parallel to `f`, then `up_hint x f` may collapse, and both `r` and the subsequently derived `u`
    may collapse as well. Where a fallback up hint is required, I supply it outside this function, as in
    `light_space.py`.

    I use this matrix for the camera view transform in `frame_pipeline.py` and for directional-light view
    construction in `light_space.py`.
    """
    f = forward.normalized()
    r = up_hint.cross(f).normalized()
    u = f.cross(r).normalized()

    m = identity()
    m[0, 0], m[0, 1], m[0, 2] = r.x, r.y, r.z
    m[1, 0], m[1, 1], m[1, 2] = u.x, u.y, u.z
    m[2, 0], m[2, 1], m[2, 2] = -f.x, -f.y, -f.z

    m[0, 3] = -r.dot(eye)
    m[1, 3] = -u.dot(eye)
    m[2, 3] = f.dot(eye)
    return m


def mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    C = A @ B
    C_ij = sum_k A_ik * B_kj, when A and B are interpreted as matrices of compatible shape.

    I delegate the product to NumPy's `@` operator and then cast the realized result to `float32`.
    The cast is explicit and unconditional at the return site below, so the returned array is materialized 
    in `float32` even if NumPy employed a wider intermediate dtype while evaluating the product.

    I do not add shape validation, rank restriction, or semantic interpretation beyond whatever NumPy
    itself enforces for the supplied operands. In the presently shown code I invoke this helper only 
    on 4x4 transform arrays, notably for products such as `proj @ view`, 
    `rotate_z_deg_matrix(...) @ view`, and `proj @ light_view`.

    The function therefore serves as a narrow dtype-normalizing wrapper around NumPy multiplication, 
    not as an independent linear-algebra policy layer.
    """
    return (a @ b).astype(np.float32)