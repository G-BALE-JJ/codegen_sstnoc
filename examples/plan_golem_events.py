from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tilelang_cim import GolemBackendConfig, build_golem_event_plan
from tilelang_cim.json_export import to_json_text


def main() -> None:
    args = _parse_args()
    ir = json.loads(args.input.read_text(encoding="utf-8"))
    config = GolemBackendConfig(
        array_input_size=args.array_input_size,
        array_output_size=args.array_output_size,
        num_arrays=args.num_arrays,
        total_groups=args.total_groups,
        total_gemm_cores=args.total_gemm_cores,
        num_memory_nodes=args.num_memory_nodes,
        mem_node_size_bytes=args.mem_node_size_bytes,
        a_reuse_n_tiles=args.a_reuse_n_tiles,
        b_reuse_m_tiles=args.b_reuse_m_tiles,
        dma_slot_count=args.dma_slot_count,
    )
    plan = build_golem_event_plan(ir, config)
    args.output.write_text(to_json_text(plan), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Golem-aware event plan from CIM-TileIR JSON.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--array-input-size", type=int, default=64)
    parser.add_argument("--array-output-size", type=int, default=64)
    parser.add_argument("--num-arrays", type=int, default=64)
    parser.add_argument("--total-groups", type=int, default=4)
    parser.add_argument("--total-gemm-cores", type=int, default=20)
    parser.add_argument("--num-memory-nodes", type=int, default=5)
    parser.add_argument("--mem-node-size-bytes", type=int, default=128 * 1024 * 1024)
    parser.add_argument("--a-reuse-n-tiles", type=int, default=1)
    parser.add_argument("--b-reuse-m-tiles", type=int, default=1)
    parser.add_argument("--dma-slot-count", type=int, default=16)
    return parser.parse_args()


if __name__ == "__main__":
    main()
