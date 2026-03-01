# FILE: src/maiming/domain/world/world_state.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Iterable, Any

BlockKey = Tuple[int, int, int]

@dataclass
class WorldState:
    blocks: Dict[BlockKey, str]
    revision: int = 0

    def set_block(self, x: int, y: int, z: int, block_id: str) -> None:
        self.blocks[(x, y, z)] = block_id
        self.revision += 1

    def remove_block(self, x: int, y: int, z: int) -> None:
        if (x, y, z) in self.blocks:
            del self.blocks[(x, y, z)]
            self.revision += 1

    def iter_blocks(self) -> Iterable[tuple[int, int, int, str]]:
        for (x, y, z), bid in self.blocks.items():
            yield x, y, z, bid

    def to_persisted_dict(self) -> dict[str, Any]:
        items: list[list[Any]] = []
        for (x, y, z), s in self.blocks.items():
            items.append([int(x), int(y), int(z), str(s)])
        return {"revision": int(self.revision), "blocks": items}

    @staticmethod
    def from_persisted_dict(d: dict[str, Any]) -> "WorldState":
        rev = d.get("revision", 0)
        try:
            revision = int(rev)
        except Exception:
            revision = 0

        out: Dict[BlockKey, str] = {}
        raw = d.get("blocks", [])
        if isinstance(raw, list):
            for it in raw:
                if not isinstance(it, list) or len(it) != 4:
                    continue
                try:
                    x = int(it[0])
                    y = int(it[1])
                    z = int(it[2])
                    s = str(it[3])
                except Exception:
                    continue
                out[(x, y, z)] = s

        return WorldState(blocks=out, revision=int(max(0, revision)))