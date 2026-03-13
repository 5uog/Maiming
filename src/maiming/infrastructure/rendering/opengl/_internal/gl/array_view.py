# FILE: src/maiming/infrastructure/rendering/opengl/_internal/gl/array_view.py
from __future__ import annotations
import numpy as np

def _as_c_array(data: np.ndarray, *, dtype: object) -> np.ndarray:
    arr = data
    if arr.dtype != dtype:
        arr = arr.astype(dtype, copy=False)
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr, dtype=dtype)
    return arr

def as_float32_c_array(data: np.ndarray) -> np.ndarray:
    return _as_c_array(data, dtype=np.float32)

def as_uint32_c_array(data: np.ndarray) -> np.ndarray:
    return _as_c_array(data, dtype=np.uint32)

def require_2d_shape(data: np.ndarray, *, cols: int, label: str) -> np.ndarray:
    if data.ndim != 2 or int(data.shape[1]) != int(cols):
        raise ValueError(f"{str(label)} must be a {data.dtype} Nx{int(cols)} array")
    return data

def as_float32_rows(data: np.ndarray, *, cols: int, label: str) -> np.ndarray:
    return require_2d_shape(as_float32_c_array(data), cols=int(cols), label=str(label))

def as_uint32_rows(data: np.ndarray, *, cols: int, label: str) -> np.ndarray:
    return require_2d_shape(as_uint32_c_array(data), cols=int(cols), label=str(label))

def copy_float32_rows(data: np.ndarray, *, cols: int, label: str) -> np.ndarray:
    src = as_float32_rows(data, cols=int(cols), label=str(label))
    return np.array(src, dtype=np.float32, copy=True, order="C")