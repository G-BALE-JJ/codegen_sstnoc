from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tilelang_cim import extract_gemm_ir_from_source, export_golem_sst_artifacts
from tilelang_cim.golem_constraints import GolemBackendConfig


def main() -> None:
    args = _parse_args()
    ir = _load_ir(args)
    if args.dtype is not None:
        _override_tensor_dtype(ir, args.dtype)

    backend_config = GolemBackendConfig(
        array_input_size=args.array_input_size,
        array_output_size=args.array_output_size,
        num_arrays=args.num_arrays,
    )
    paths = export_golem_sst_artifacts(ir, args.artifact_root, backend_config)
    for label, path in paths.items():
        print(f"{label}: {path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Golem SST env and contract artifacts from CIM-TileIR.")
    parser.add_argument("input", type=Path, help="CIM-TileIR JSON or TileLang source file.")
    parser.add_argument(
        "--input-format",
        choices=("cim-tileir-json", "tilelang-source"),
        default="cim-tileir-json",
    )
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--mesh-w", type=int, default=4)
    parser.add_argument("--mesh-h", type=int, default=5)
    parser.add_argument("--dtype", choices=("int32", "fp32"), default=None)
    parser.add_argument("--array-input-size", type=int, default=64)
    parser.add_argument("--array-output-size", type=int, default=64)
    parser.add_argument("--num-arrays", type=int, default=64)
    return parser.parse_args()


def _load_ir(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_format == "cim-tileir-json":
        return json.loads(args.input.read_text(encoding="utf-8"))
    source = args.input.read_text(encoding="utf-8")
    return extract_gemm_ir_from_source(source, mesh_w=args.mesh_w, mesh_h=args.mesh_h)


def _override_tensor_dtype(ir: dict[str, Any], dtype: str) -> None:
    for name in ("A", "B", "C"):
        ir["tensors"][name]["dtype"] = dtype


if __name__ == "__main__":
    main()
