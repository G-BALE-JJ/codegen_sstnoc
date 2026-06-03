from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tilelang_cim import build_gemm_ir, validate_cim_tile_ir, write_json


def main() -> None:
    args = _parse_args()
    ir = build_gemm_ir(
        m=args.m,
        n=args.n,
        k=args.k,
        bm=args.bm,
        bn=args.bn,
        bk=args.bk,
        mesh_w=args.mesh_w,
        mesh_h=args.mesh_h,
        pipeline_stages=args.pipeline_stages,
    )
    errors = validate_cim_tile_ir(ir)
    if errors:
        raise SystemExit("Invalid CIM-TileIR:\n" + "\n".join(f"- {error}" for error in errors))

    write_json(ir, args.output)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a static GEMM CIM-TileIR JSON file.")
    parser.add_argument("--output", type=Path, default=Path("gemm.cimtile.json"))
    parser.add_argument("--m", type=int, default=1024)
    parser.add_argument("--n", type=int, default=1024)
    parser.add_argument("--k", type=int, default=1024)
    parser.add_argument("--bm", type=int, default=64)
    parser.add_argument("--bn", type=int, default=64)
    parser.add_argument("--bk", type=int, default=32)
    parser.add_argument("--mesh-w", type=int, default=8)
    parser.add_argument("--mesh-h", type=int, default=8)
    parser.add_argument("--pipeline-stages", type=int, default=1)
    return parser.parse_args()


if __name__ == "__main__":
    main()
