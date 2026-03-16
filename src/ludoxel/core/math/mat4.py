# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0

# FILE: src/ludoxel/core/math/mat4.py
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
    fixed at `float32` at construction time, and I interpose no wrapper, semantic decoration, or
    post-processing layer. I use this matrix as the neutral element of transform composition wherever
    a no-op 4x4 transform is required. In `frame_pipeline.py` I use it as the fallback light-space
    transform when light-space rendering is bypassed. I also use it as the construction base inside
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

    I construct exactly this coefficient matrix. I first allocate a zero matrix of shape `(4, 4)`
    with dtype `float32`, and then I write only the five non-zero entries that appear in the
    formula. Every unwritten entry therefore remains `0.0` by construction.

    The guard policy is narrow and literal. I protect only the aspect denominator by replacing the
    raw value with `max(float(aspect), 1e-9)`. I do not protect the field-of-view singularity
    `tan(fov_y/2) = 0`, and I do not protect the clip-plane coincidence singularity
    `z_near == z_far`. I also do not preserve a negative aspect ratio as a mirrored projection,
    because any `aspect <= 1e-9` is collapsed onto `1e-9`. Conventional finite perspective behavior
    therefore presupposes a non-singular vertical field of view and distinct near and far distances.

    For a homogeneous point `p_h = (x, y, z, 1)^T`, the pre-divide clip coordinate is exactly
    `M @ p_h`. I do not perform the projective division step. I materialize only the 4x4
    coefficient matrix.

    I use this matrix in `frame_pipeline.py` both for the world projection transform and for the first-
    person hand projection transform with a different near plane and a view-model field of view.
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

    I construct exactly this orthographic coefficient matrix. The array is allocated as zeros with
    dtype `float32`, after which I write the diagonal scale terms, the translation terms, and the
    homogeneous bottom-right entry `1.0`. No other entries are modified.

    The denominator policy is explicit and must not be overstated. I do not preserve the raw spans
    `right - left`, `top - bottom`, and `z_far - z_near`. I replace each by a positive lower-
    bounded effective span through `max(span, 1e-9)`. A degenerate interval and a reversed interval
    therefore do not survive algebraically. A mirrored bound configuration such as `right < left`
    is not represented as a negative scale in the output matrix; it is collapsed onto the positive
    minimum denominator instead.

    For a homogeneous point `p_h = (x, y, z, 1)^T`, the transformed coordinate is exactly `M @ p_h`.
    I do not perform clipping or viewport mapping. I materialize only the orthographic 4x4 map.

    I use this matrix in `light_space.py` for the orthographic projection part of the
    directional-light shadow transform.
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


def look_dir(eye: Vec3, forward: Vec3, up_hint: Vec3=Vec3(0.0, 1.0, 0.0)) -> np.ndarray:
    """
    f = normalize(forward)
    r = normalize(cross(up_hint, f))
    u = normalize(cross(f, r))

    M = [
        [ r.x,   r.y,   r.z,  -dot(r, eye)],
        [ u.x,   u.y,   u.z,  -dot(u, eye)],
        [-f.x,  -f.y,  -f.z,   dot(f, eye)],
        [ 0.0,   0.0,   0.0,   1.0]
    ].

    I build exactly this 4x4 view matrix. The matrix is initialized from `identity()`, so its dtype
    is `float32` from the outset and its last row remains `[0.0, 0.0, 0.0, 1.0]` after I populate
    the first three rows and translation entries.

    The basis construction is fixed by code and must be read literally. I first normalize the
    supplied forward vector, then compute the right vector as `normalize(cross(up_hint, f))`, and
    finally compute the corrected up vector as `normalize(cross(f, r))`. I do not use
    `cross(f, up_hint)` for the right axis. The handedness of the resulting frame is therefore
    exactly the one encoded by these two cross products.

    For a homogeneous point `p_h = (p.x, p.y, p.z, 1)^T`, the first three coordinates of `M @ p_h` are

        dot(r, p - eye),
        dot(u, p - eye),
        -dot(f, p - eye),

    provided the basis vectors are non-degenerate. This is the direct algebra of the populated rows
    and translation terms.

    I do not add any degeneracy repair beyond the branch behavior inherited from
    `Vec3.normalized()`. If `forward` is zero or effectively zero, then `f` becomes the zero
    vector. If `up_hint` is parallel or nearly parallel to `f`, then `cross(up_hint, f)` may
    collapse, and both `r` and the subsequently derived `u` may collapse as well. Where a fallback
    up hint is required, I supply it outside this function, as in `light_space.py`.

    I use this matrix for the camera view transform in `frame_pipeline.py` and for directional-light
    view construction in `light_space.py`.
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
    C_ij = sum_k A_ik * B_kj.

    I delegate the product to NumPy's `@` operator and then cast the realized result to `float32`.
    The cast is explicit and unconditional at the return site, so the returned array is materialized
    in `float32` even if NumPy employed a wider dtype during evaluation of the matrix product.

    I do not add shape validation, rank restriction, or semantic interpretation beyond whatever
    NumPy itself enforces for the supplied operands. I use this helper on transform arrays, notably
    for products such as `proj @ view`, `rotate_z_deg_matrix(...) @ view`, `proj @ light_view`, and
    `proj @ view` inside renderer construction.

    The function therefore serves as a narrow dtype-normalizing wrapper around NumPy multiplication,
    not as an independent linear-algebra policy layer.
    """
    return (a @ b).astype(np.float32)
