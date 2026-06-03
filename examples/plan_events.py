from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tilelang_cim import build_event_plan, write_json


def main() -> None:
    args = _parse_args()
    ir = json.loads(args.input.read_text(encoding="utf-8"))
    plan = build_event_plan(ir)
    write_json(plan, args.output)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an abstract event plan from CIM-TileIR JSON.")
    parser.add_argument("input", type=Path, help="Input CIM-TileIR JSON file.")
    parser.add_argument("--output", type=Path, default=Path("gemm.eventplan.json"))
    return parser.parse_args()


if __name__ == "__main__":
    main()
