from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_json_text(ir: dict[str, Any]) -> str:
    return json.dumps(ir, indent=2, sort_keys=False) + "\n"


def write_json(ir: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(to_json_text(ir), encoding="utf-8")
