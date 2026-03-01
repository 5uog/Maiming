# FILE: src/maiming/infrastructure/persistence/json_file_store.py
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class JsonFileStore:
    path: Path

    def read(self) -> dict[str, Any] | None:
        p = Path(self.path)
        if not p.exists():
            return None

        try:
            raw = p.read_text(encoding="utf-8")
        except OSError:
            return None

        try:
            v = json.loads(raw)
        except json.JSONDecodeError:
            return None

        if isinstance(v, dict):
            return v
        return None

    def write(self, obj: dict[str, Any]) -> None:
        p = Path(self.path)
        p.parent.mkdir(parents=True, exist_ok=True)

        tmp = p.with_suffix(p.suffix + ".tmp")

        data = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)

        f = None
        try:
            f = open(tmp, "w", encoding="utf-8", newline="\n")
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        finally:
            if f is not None:
                try:
                    f.close()
                except OSError:
                    pass

        try:
            os.replace(str(tmp), str(p))
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass