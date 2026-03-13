# FILE: src/maiming/infrastructure/rendering/opengl/_internal/scene/chunk_visibility.py
from __future__ import annotations
import numpy as np

from ......domain.world.chunking import ChunkKey, chunk_bounds

def chunk_corners_homogeneous(chunk_key: ChunkKey) -> np.ndarray:
    x0, x1, y0, y1, z0, z1 = chunk_bounds(chunk_key)
    return np.asarray([[float(x0), float(y0), float(z0), 1.0], [float(x1), float(y0), float(z0), 1.0], [float(x0), float(y1), float(z0), 1.0], [float(x1), float(y1), float(z0), 1.0], [float(x0), float(y0), float(z1), 1.0], [float(x1), float(y0), float(z1), 1.0], [float(x0), float(y1), float(z1), 1.0], [float(x1), float(y1), float(z1), 1.0]], dtype=np.float32)

def chunk_intersects_clip_volume(chunk_key: ChunkKey, matrix: np.ndarray) -> bool:
    corners = chunk_corners_homogeneous(chunk_key)
    clip = (matrix.astype(np.float32, copy=False) @ corners.T).T

    xs = clip[:, 0]
    ys = clip[:, 1]
    zs = clip[:, 2]
    ws = clip[:, 3]

    if bool(np.all(xs < (-ws))):
        return False
    if bool(np.all(xs > ws)):
        return False
    if bool(np.all(ys < (-ws))):
        return False
    if bool(np.all(ys > ws)):
        return False
    if bool(np.all(zs < (-ws))):
        return False
    if bool(np.all(zs > ws)):
        return False

    return True