# FILE: src/maiming/domain/world/chunking.py
from __future__ import annotations
from typing import Tuple, Set

CHUNK_SIZE: int = 16
ChunkKey = Tuple[int, int, int]

def normalize_chunk_key(k: ChunkKey) -> ChunkKey:
    return (int(k[0]), int(k[1]), int(k[2]))

def chunk_key(x: int, y: int, z: int) -> ChunkKey:
    return (int(x) // CHUNK_SIZE, int(y) // CHUNK_SIZE, int(z) // CHUNK_SIZE)

def chunk_bounds(k: ChunkKey) -> tuple[int, int, int, int, int, int]:
    cx, cy, cz = normalize_chunk_key(k)
    x0 = cx * CHUNK_SIZE
    y0 = cy * CHUNK_SIZE
    z0 = cz * CHUNK_SIZE
    return (x0, x0 + CHUNK_SIZE, y0, y0 + CHUNK_SIZE, z0, z0 + CHUNK_SIZE)

def neighbor_chunk_keys_for_cell(x: int, y: int, z: int) -> Set[ChunkKey]:
    keys: Set[ChunkKey] = {chunk_key(int(x), int(y), int(z))}
    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        keys.add(chunk_key(int(x + dx), int(y + dy), int(z + dz)))
    return keys