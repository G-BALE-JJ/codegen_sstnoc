from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tilelang_cim import extract_gemm_ir_from_source, validate_cim_tile_ir, write_json


def main() -> None:
    args = _parse_args()
    source = args.source.read_text(encoding="utf-8")
    ir = extract_gemm_ir_from_source(source, mesh_w=args.mesh_w, mesh_h=args.mesh_h)

    errors = validate_cim_tile_ir(ir)
    if errors:
        raise SystemExit("Invalid CIM-TileIR:\n" + "\n".join(f"- {error}" for error in errors))

    write_json(ir, args.output)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract CIM-TileIR JSON from a narrow TileLang GEMM source pattern.")
    parser.add_argument("source", type=Path, help="Python source file containing a TileLang GEMM prim_func.")
    parser.add_argument("--output", type=Path, default=Path("tilelang_gemm.cimtile.json"))
    parser.add_argument("--mesh-w", type=int, default=8)
    parser.add_argument("--mesh-h", type=int, default=8)
    return parser.parse_args()


if __name__ == "__main__":
    main()
