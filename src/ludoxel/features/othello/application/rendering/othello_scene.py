# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math
import numpy as np

from ...domain.game.board import BOARD_SIZE as OTHELLO_BOARD_SIZE, OTHELLO_BOARD_SURFACE_Y as OTHELLO_WORLD_BOARD_TOP_Y, OTHELLO_GRASS_TOP_Y as OTHELLO_WORLD_GRASS_TOP_Y, square_center
from ...domain.game.types import BOARD_CELL_COUNT, SIDE_BLACK, SIDE_WHITE, OthelloAnimationState, normalize_side
from .othello_render_state import OthelloRenderState
from .....shared.math.transform_matrices import compose_matrices, rotate_x_deg_matrix, scale_matrix, translate_matrix

OTHELLO_SQUARE_SIZE: float = 1.0
OTHELLO_HALF_SPAN: float = (OTHELLO_BOARD_SIZE * OTHELLO_SQUARE_SIZE) * 0.5
OTHELLO_GRASS_TOP_Y: float = float(OTHELLO_WORLD_GRASS_TOP_Y)
OTHELLO_BOARD_BOTTOM_Y: float = float(OTHELLO_GRASS_TOP_Y)
OTHELLO_BOARD_TOP_Y: float = float(OTHELLO_WORLD_BOARD_TOP_Y)
OTHELLO_HIGHLIGHT_THICKNESS: float = 0.018
OTHELLO_HIGHLIGHT_LIFT: float = 0.006
OTHELLO_HIGHLIGHT_CENTER_Y: float = OTHELLO_BOARD_TOP_Y + OTHELLO_HIGHLIGHT_LIFT + OTHELLO_HIGHLIGHT_THICKNESS * 0.5
OTHELLO_PIECE_RADIUS: float = 0.38
OTHELLO_PIECE_THICKNESS: float = 0.12
OTHELLO_PIECE_GAP_Y: float = 0.004
OTHELLO_PIECE_BASE_Y: float = OTHELLO_BOARD_TOP_Y + OTHELLO_PIECE_THICKNESS * 0.5 + OTHELLO_PIECE_GAP_Y
OTHELLO_PIECE_BOTTOM_Y: float = OTHELLO_PIECE_BASE_Y - OTHELLO_PIECE_THICKNESS * 0.5

_TINT_WHITE = (1.0, 1.0, 1.0, 1.0)
_BOARD_DARK = (0.20, 0.42, 0.20, 1.0)
_BOARD_LIGHT = (0.27, 0.50, 0.27, 1.0)
_BOARD_FRAME = (0.42, 0.25, 0.10, 1.0)
_LEGAL_HINT = (0.44, 0.86, 0.95, 0.34)
_HOVER_HINT = (0.96, 0.90, 0.44, 0.55)
_LAST_MOVE_HINT = (0.96, 0.70, 0.18, 0.38)

def _as_rows(matrix: np.ndarray) -> np.ndarray:
    return np.asarray(matrix, dtype=np.float32).reshape(16)

def _instance_row(matrix: np.ndarray, tint: tuple[float, float, float, float]) -> np.ndarray:
    return np.asarray([*_as_rows(matrix), float(tint[0]), float(tint[1]), float(tint[2]), float(tint[3])], dtype=np.float32)

def _cube_vertices_with_color(color: tuple[float, float, float]) -> np.ndarray:
    r, g, b = (float(color[0]), float(color[1]), float(color[2]))
    p = 0.5

    def face(nx, ny, nz, corners):
        (a, c0, c1, d0) = corners
        return [(*a, nx, ny, nz, r, g, b),(*c0, nx, ny, nz, r, g, b),(*c1, nx, ny, nz, r, g, b),(*a, nx, ny, nz, r, g, b),(*c1, nx, ny, nz, r, g, b),(*d0, nx, ny, nz, r, g, b)]

    faces: list[tuple[float, ...]] = []
    faces.extend(face(1, 0, 0,[(p, -p, -p),(p, -p, p),(p, p, p),(p, p, -p)]))
    faces.extend(face(-1, 0, 0,[(-p, -p, p),(-p, -p, -p),(-p, p, -p),(-p, p, p)]))
    faces.extend(face(0, 1, 0,[(-p, p, -p),(p, p, -p),(p, p, p),(-p, p, p)]))
    faces.extend(face(0, -1, 0,[(-p, -p, p),(p, -p, p),(p, -p, -p),(-p, -p, -p)]))
    faces.extend(face(0, 0, 1,[(p, -p, p),(-p, -p, p),(-p, p, p),(p, p, p)]))
    faces.extend(face(0, 0, -1,[(-p, -p, -p),(p, -p, -p),(p, p, -p),(-p, p, -p)]))
    return np.asarray(faces, dtype=np.float32)

def build_othello_board_vertices() -> np.ndarray:
    return _cube_vertices_with_color((1.0, 1.0, 1.0))

def build_othello_piece_vertices(*, segments: int=48) -> np.ndarray:
    segs = max(12, int(segments))
    top_color = (0.08, 0.08, 0.08)
    bottom_color = (0.94, 0.94, 0.94)
    rim_color = (0.22, 0.22, 0.22)
    half_h = 0.5

    vertices: list[tuple[float, ...]] = []

    def add_triangle(p0, p1, p2, normal, color):
        r, g, b = color
        nx, ny, nz = normal
        vertices.append((*p0, nx, ny, nz, r, g, b))
        vertices.append((*p1, nx, ny, nz, r, g, b))
        vertices.append((*p2, nx, ny, nz, r, g, b))

    center_top = (0.0, half_h, 0.0)
    center_bottom = (0.0, -half_h, 0.0)

    for segment_index in range(segs):
        a0 = (float(segment_index) / float(segs)) * (2.0 * math.pi)
        a1 = (float(segment_index + 1) / float(segs)) * (2.0 * math.pi)

        x0 = math.cos(a0) * 0.5
        z0 = math.sin(a0) * 0.5
        x1 = math.cos(a1) * 0.5
        z1 = math.sin(a1) * 0.5

        p0_top = (x0, half_h, z0)
        p1_top = (x1, half_h, z1)
        p0_bottom = (x0, -half_h, z0)
        p1_bottom = (x1, -half_h, z1)

        add_triangle(center_top, p0_top, p1_top,(0.0, 1.0, 0.0), top_color)
        add_triangle(center_bottom, p1_bottom, p0_bottom,(0.0, -1.0, 0.0), bottom_color)

        nx0 = math.cos((a0 + a1) * 0.5)
        nz0 = math.sin((a0 + a1) * 0.5)
        add_triangle(p0_top, p0_bottom, p1_bottom,(nx0, 0.0, nz0), rim_color)
        add_triangle(p0_top, p1_bottom, p1_top,(nx0, 0.0, nz0), rim_color)

    return np.asarray(vertices, dtype=np.float32)

def _piece_angle_deg_for_side(side: int) -> float:
    return 0.0 if int(normalize_side(side)) == int(SIDE_BLACK) else 180.0

def _animation_progress(animation: OthelloAnimationState) -> tuple[float, float]:
    duration = max(1e-6, float(animation.duration_s))
    t = max(0.0, min(1.0, float(animation.elapsed_s) / duration))
    eased = 3.0 * t * t - 2.0 * t * t * t
    lift = math.sin(t * math.pi) * float(animation.lift_height)
    return (float(eased), float(lift))

def build_othello_instance_rows(render_state: OthelloRenderState) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not bool(render_state.enabled):
        empty = np.zeros((0, 20), dtype=np.float32)
        return (empty, empty, empty)

    board_rows: list[np.ndarray] = []
    highlight_rows: list[np.ndarray] = []
    piece_rows: list[np.ndarray] = []

    legal_indices = {int(index) for index in tuple(render_state.legal_move_indices) if 0 <= int(index) < BOARD_CELL_COUNT}
    animation_map = {int(animation.square_index): animation.normalized() for animation in tuple(render_state.animations)}

    if render_state.last_move_index is not None and 0 <= int(render_state.last_move_index) < BOARD_CELL_COUNT:
        x, z = square_center(int(render_state.last_move_index))
        matrix = compose_matrices(translate_matrix(float(x), float(OTHELLO_HIGHLIGHT_CENTER_Y), float(z)), scale_matrix(0.86, float(OTHELLO_HIGHLIGHT_THICKNESS), 0.86))
        highlight_rows.append(_instance_row(matrix, _LAST_MOVE_HINT))

    for square_index in legal_indices:
        x, z = square_center(square_index)
        tint = _HOVER_HINT if render_state.hover_square_index == square_index else _LEGAL_HINT
        scale = 0.74 if render_state.hover_square_index == square_index else 0.56
        matrix = compose_matrices(translate_matrix(float(x), float(OTHELLO_HIGHLIGHT_CENTER_Y), float(z)), scale_matrix(float(scale), float(OTHELLO_HIGHLIGHT_THICKNESS), float(scale)))
        highlight_rows.append(_instance_row(matrix, tint))

    materialized_board = tuple(render_state.board[:BOARD_CELL_COUNT])
    for square_index, side in enumerate(materialized_board):
        norm_side = normalize_side(side)
        if norm_side not in (int(SIDE_BLACK), int(SIDE_WHITE)):
            continue
        x, z = square_center(square_index)
        angle_deg = _piece_angle_deg_for_side(norm_side)
        lift = 0.0
        animation = animation_map.get(square_index)
        if animation is not None:
            progress, lift = _animation_progress(animation)
            start_angle = _piece_angle_deg_for_side(animation.from_side)
            end_angle = _piece_angle_deg_for_side(animation.to_side)
            if end_angle <= start_angle:
                end_angle += 360.0
            angle_deg = float(start_angle) + (float(end_angle) - float(start_angle)) * float(progress)
        matrix = compose_matrices(translate_matrix(float(x), float(OTHELLO_PIECE_BASE_Y) + float(lift), float(z)), rotate_x_deg_matrix(float(angle_deg)), scale_matrix(float(OTHELLO_PIECE_RADIUS) * 2.0, float(OTHELLO_PIECE_THICKNESS), float(OTHELLO_PIECE_RADIUS) * 2.0))
        piece_rows.append(_instance_row(matrix, _TINT_WHITE))

    return (np.ascontiguousarray(np.vstack(board_rows), dtype=np.float32) if board_rows else np.zeros((0, 20), dtype=np.float32), np.ascontiguousarray(np.vstack(highlight_rows), dtype=np.float32) if highlight_rows else np.zeros((0, 20), dtype=np.float32), np.ascontiguousarray(np.vstack(piece_rows), dtype=np.float32) if piece_rows else np.zeros((0, 20), dtype=np.float32))