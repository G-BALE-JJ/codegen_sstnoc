from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tilelang_cim import build_matmul_softmax_graph_ir, validate_cim_tile_ir, write_json


def main() -> None:
    args = _parse_args()
    ir = build_matmul_softmax_graph_ir(
        m=args.m,
        n=args.n,
        k=args.k,
        bm=args.bm,
        bn=args.bn,
        bk=args.bk,
        mesh_w=args.mesh_w,
        mesh_h=args.mesh_h,
        pipeline_stages=args.pipeline_stages,
        dtype=args.dtype,
        layout=args.layout,
    )
    errors = validate_cim_tile_ir(ir)
    if errors:
        raise SystemExit("Invalid matmul->softmax graph IR:\n" + "\n".join(f"- {error}" for error in errors))
    write_json(ir, args.output)
    print(f"wrote {args.output}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a CIM-TileIR matmul->softmax graph JSON.")
    parser.add_argument("--output", type=Path, default=Path("matmul_softmax.cimtile.json"))
    parser.add_argument("--m", type=int, default=64)
    parser.add_argument("--n", type=int, default=64)
    parser.add_argument("--k", type=int, default=64)
    parser.add_argument("--bm", type=int, default=64)
    parser.add_argument("--bn", type=int, default=64)
    parser.add_argument("--bk", type=int, default=64)
    parser.add_argument("--mesh-w", type=int, default=1)
    parser.add_argument("--mesh-h", type=int, default=1)
    parser.add_argument("--pipeline-stages", type=int, choices=(1, 2), default=1)
    parser.add_argument("--dtype", choices=("fp32", "float32", "float"), default="fp32")
    parser.add_argument("--layout", choices=("row_major",), default="row_major")
    return parser.parse_args()


if __name__ == "__main__":
    main()
