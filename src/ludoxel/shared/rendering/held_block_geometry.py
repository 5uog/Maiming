# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass

from ..blocks.models.common import LocalBox
from ..blocks.models.dimensions import px_box
from ..blocks.models.fence_gate import boxes_for_fence_gate
from ..blocks.models.slab import boxes_for_slab
from ..blocks.models.stairs import boxes_for_stairs
from ..blocks.models.wall import boxes_for_wall
from ..math.voxel.voxel_faces import FACE_NEG_X, FACE_NEG_Y, FACE_NEG_Z, FACE_POS_X, FACE_POS_Y, FACE_POS_Z
from .render_types import DefLookup


@dataclass(frozen=True)
class TexturedBox:
    """I define this record as the pair (B, U), where B is a local cuboid and U is an optional per-face pixel-rectangle family over the six voxel faces. I use the record to transport enough information to synthesize both geometry and atlas-addressing data without binding held-item rendering to any single block-family implementation."""
    box: LocalBox
    face_uv_pixels: dict[int, tuple[float, float, float, float]] | None = None


_FENCE_INVENTORY_BOXES: tuple[TexturedBox, ...] = (TexturedBox(box=px_box(6, 0, 6, 10, 16, 10), face_uv_pixels={FACE_POS_X: (10.0, 0.0, 14.0, 16.0), FACE_NEG_X: (6.0, 0.0, 10.0, 16.0), FACE_POS_Y: (6.0, 6.0, 10.0, 10.0), FACE_NEG_Y: (10.0, 6.0, 14.0, 10.0), FACE_POS_Z: (6.0, 0.0, 10.0, 16.0), FACE_NEG_Z: (14.0, 0.0, 10.0, 16.0)}), TexturedBox(box=px_box(7, 6, -2, 9, 9, 18), face_uv_pixels={FACE_POS_X: (9.0, 6.0, 11.0, 9.0), FACE_NEG_X: (7.0, 6.0, 9.0, 9.0), FACE_POS_Y: (7.0, 0.0, 9.0, 4.0), FACE_NEG_Y: (9.0, 0.0, 11.0, 4.0), FACE_POS_Z: (7.0, 4.0, 9.0, 7.0), FACE_NEG_Z: (11.0, 4.0, 13.0, 7.0)}), TexturedBox(box=px_box(7, 12, -2, 9, 15, 18), face_uv_pixels={FACE_POS_X: (9.0, 12.0, 11.0, 15.0), FACE_NEG_X: (7.0, 12.0, 9.0, 15.0), FACE_POS_Y: (7.0, 7.0, 9.0, 11.0), FACE_NEG_Y: (9.0, 7.0, 11.0, 11.0), FACE_POS_Z: (7.0, 9.0, 9.0, 12.0), FACE_NEG_Z: (11.0, 9.0, 13.0, 12.0)}))

_WALL_INVENTORY_BOXES: tuple[TexturedBox, ...] = tuple(TexturedBox(box=b) for b in boxes_for_wall(props={"north": "low", "south": "low", "east": "none", "west": "none", "up": "true"}, get_state=(lambda _x, _y, _z: None), get_def=(lambda _block_id: None), x=0, y=0, z=0))

_HELD_BLOCK_KIND_SCALE_MULTIPLIERS: dict[str, float] = {"cube": 1.0, "slab": 1.0, "stairs": 1.0, "wall": 1.16, "fence": 1.12, "fence_gate": 1.72}


def _normalize_kind(kind: str | None) -> str:
    """I define k_norm = lower(strip(kind)) when kind is present and k_norm = '' otherwise. I use this normalization to make the held-block geometry catalogue total over nullable and loosely formatted block-kind inputs."""
    return "" if kind is None else str(kind).strip().lower()


def held_block_model_boxes(block_id: str | None, def_lookup: DefLookup) -> tuple[TexturedBox, ...]:
    """I define B(id) = B_kind(kind(id)) whenever the registry resolves the block definition, and B(id) = () otherwise. I use this lookup to bridge inventory identifiers onto the canonical held-item cuboid catalogue."""
    if block_id is None:
        return ()

    block_def = def_lookup(str(block_id))
    if block_def is None:
        return ()

    return held_block_model_boxes_for_kind(block_def.kind_name())


def held_block_model_boxes_for_kind(kind: str | None) -> tuple[TexturedBox, ...]:
    """I define B_kind over the finite family {cube, slab, stairs, wall, fence, fence_gate}, with each element mapped onto the cuboid decomposition used by the held-item renderer. I keep this catalogue factored so that first-person and third-person item rendering consume the same geometric source of truth."""
    normalized = _normalize_kind(kind)
    if normalized == "slab":
        return tuple(TexturedBox(box=b) for b in boxes_for_slab({"type": "bottom"}))
    if normalized == "stairs":
        boxes = boxes_for_stairs(base_id="minecraft:stone_stairs", props={"facing": "east", "half": "bottom", "shape": "straight"}, get_state=(lambda _x, _y, _z: None), get_def=(lambda _block_id: None), x=0, y=0, z=0)
        return tuple(TexturedBox(box=b) for b in boxes)
    if normalized == "wall":
        return _WALL_INVENTORY_BOXES
    if normalized == "fence":
        return _FENCE_INVENTORY_BOXES
    if normalized == "fence_gate":
        return tuple(TexturedBox(box=b) for b in boxes_for_fence_gate({"facing": "south", "open": "false", "in_wall": "false"}))
    return (TexturedBox(box=LocalBox(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)),)


def held_block_kind_scale_multiplier(kind: str | None) -> float:
    """I define s(kind) as the renderer-side scalar correction applied to the held-item camera transform. I use this finite lookup so that narrow or sparse block families occupy approximately stable screen-space mass under one shared first-person composition law."""
    normalized = _normalize_kind(kind)
    return float(_HELD_BLOCK_KIND_SCALE_MULTIPLIERS.get(normalized, 1.0))

