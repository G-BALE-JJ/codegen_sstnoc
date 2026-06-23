from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .golem_constraints import GolemBackendConfig, normalize_golem_dtype, validate_cim_tile_ir_for_golem


MATMUL_ENV_MAPPING = {
    "m": "GOLEM_MATMUL_M",
    "n": "GOLEM_MATMUL_N",
    "k": "GOLEM_MATMUL_K",
    "block_m": "GOLEM_MATMUL_BLOCK_M",
    "block_n": "GOLEM_MATMUL_BLOCK_N",
    "block_k": "GOLEM_MATMUL_BLOCK_K",
    "dtype": "GOLEM_MATMUL_DTYPE",
    "layout": "GOLEM_MATMUL_LAYOUT",
    "transpose_a": "GOLEM_MATMUL_TRANSPOSE_A",
    "transpose_b": "GOLEM_MATMUL_TRANSPOSE_B",
}

GRAPH_ENV_MAPPING = {
    "graph_kind": "GOLEM_GRAPH_KIND",
    "softmax_enable": "GOLEM_SOFTMAX_ENABLE",
    "softmax_axis": "GOLEM_SOFTMAX_AXIS",
    "softmax_backend": "GOLEM_SOFTMAX_BACKEND",
    "softmax_scope": "GOLEM_SOFTMAX_SCOPE",
}


def build_golem_matmul_op_desc(
    ir: dict[str, Any],
    backend_config: GolemBackendConfig = GolemBackendConfig(),
) -> dict[str, Any]:
    errors = validate_cim_tile_ir_for_golem(ir, backend_config)
    if errors:
        raise ValueError("Invalid CIM-TileIR for Golem SST:\n" + "\n".join(f"- {error}" for error in errors))

    m, k = ir["tensors"]["A"]["shape"]
    _, n = ir["tensors"]["B"]["shape"]
    tile = ir["tile"]
    attrs = ir["attrs"]

    return {
        "m": m,
        "n": n,
        "k": k,
        "block_m": tile["BM"],
        "block_n": tile["BN"],
        "block_k": tile["BK"],
        "dtype": normalize_golem_dtype(ir["tensors"]["A"]["dtype"]),
        "layout": ir["tensors"]["A"]["layout"],
        "transpose_a": int(attrs["transpose_a"]),
        "transpose_b": int(attrs["transpose_b"]),
    }


def build_golem_softmax_op_desc_from_graph(
    ir: dict[str, Any],
    backend_config: GolemBackendConfig = GolemBackendConfig(),
) -> dict[str, Any]:
    errors = validate_cim_tile_ir_for_golem(ir, backend_config)
    if errors:
        raise ValueError("Invalid CIM-TileIR graph for Golem SST:\n" + "\n".join(f"- {error}" for error in errors))

    tensors = ir["tensors"]
    softmax_op = ir["ops"][1]
    outer, dim = tensors["S"]["shape"]

    return {
        "op": "softmax",
        "op_name": "SoftmaxFwdOp",
        "semantic_source": "TileOps SoftmaxFwdOp",
        "input": softmax_op["inputs"][0],
        "output": softmax_op["outputs"][0],
        "N": dim,
        "dim": -1,
        "axis": softmax_op["attrs"]["axis"],
        "outer": outer,
        "dtype": normalize_golem_dtype(tensors["S"]["dtype"]),
        "layout": tensors["S"]["layout"],
        "backend": "riscv_cpu_fallback",
        "scope": "tile_local",
        "supported_subset": "single_n_tile_rowwise",
        "requires_single_n_tile": True,
        "tile_local_equivalent_to_rowwise": True,
        "in_place_runtime": True,
    }


def build_golem_graph_sequence(
    ir: dict[str, Any],
    backend_config: GolemBackendConfig = GolemBackendConfig(),
) -> dict[str, Any]:
    errors = validate_cim_tile_ir_for_golem(ir, backend_config)
    if errors:
        raise ValueError("Invalid CIM-TileIR graph for Golem SST:\n" + "\n".join(f"- {error}" for error in errors))

    return {
        "version": 1,
        "kind": "matmul_softmax",
        "backend": "golem_sst",
        "source_kernel": "graph",
        "execution": [
            {
                "id": ir["ops"][0]["id"],
                "op": "matmul",
                "backend": "golem_mvm",
                "contract": "contracts/matmul_op_desc_resolved.json",
            },
            {
                "id": ir["ops"][1]["id"],
                "op": "softmax",
                "backend": "riscv_cpu_fallback",
                "contract": "contracts/softmax_op_desc_resolved.json",
            },
        ],
    }


def build_golem_env_text(
    desc: dict[str, Any],
    backend_config: GolemBackendConfig = GolemBackendConfig(),
    graph_sequence: dict[str, Any] | None = None,
    softmax_desc: dict[str, Any] | None = None,
) -> str:
    lines = [
        f"export GOLEM_ARRAY_INPUT_SIZE={backend_config.array_input_size}",
        f"export GOLEM_ARRAY_OUTPUT_SIZE={backend_config.array_output_size}",
        f"export GOLEM_NUM_ARRAYS={backend_config.num_arrays}",
        "",
        f"export GOLEM_MATMUL_M={desc['m']}",
        f"export GOLEM_MATMUL_N={desc['n']}",
        f"export GOLEM_MATMUL_K={desc['k']}",
        f"export GOLEM_MATMUL_BLOCK_M={desc['block_m']}",
        f"export GOLEM_MATMUL_BLOCK_N={desc['block_n']}",
        f"export GOLEM_MATMUL_BLOCK_K={desc['block_k']}",
        f"export GOLEM_MATMUL_DTYPE={desc['dtype']}",
        f"export GOLEM_MATMUL_LAYOUT={desc['layout']}",
        f"export GOLEM_MATMUL_TRANSPOSE_A={desc['transpose_a']}",
        f"export GOLEM_MATMUL_TRANSPOSE_B={desc['transpose_b']}",
        "",
        'export GOLEM_GEMM_M="$GOLEM_MATMUL_M"',
        'export GOLEM_GEMM_N="$GOLEM_MATMUL_N"',
        'export GOLEM_GEMM_K="$GOLEM_MATMUL_K"',
        'export GOLEM_GEMM_BLOCK_M="$GOLEM_MATMUL_BLOCK_M"',
        'export GOLEM_GEMM_BLOCK_N="$GOLEM_MATMUL_BLOCK_N"',
        'export GOLEM_GEMM_BLOCK_K="$GOLEM_MATMUL_BLOCK_K"',
    ]
    if graph_sequence is not None and softmax_desc is not None:
        lines.extend(
            [
                "",
                f"export GOLEM_GRAPH_KIND={graph_sequence['kind']}",
                "export GOLEM_SOFTMAX_ENABLE=1",
                f"export GOLEM_SOFTMAX_AXIS={softmax_desc['axis']}",
                f"export GOLEM_SOFTMAX_BACKEND={softmax_desc['backend']}",
                f"export GOLEM_SOFTMAX_SCOPE={softmax_desc['scope']}",
            ]
        )
    return "\n".join(lines) + "\n"


def export_golem_sst_artifacts(
    ir: dict[str, Any],
    artifact_root: str | Path,
    backend_config: GolemBackendConfig = GolemBackendConfig(),
) -> dict[str, Path]:
    root = Path(artifact_root)
    contracts_dir = root / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    env_path = root / "golem_sst.env"
    resolved_path = contracts_dir / "matmul_op_desc_resolved.json"
    mapping_path = contracts_dir / "matmul_env_mapping_v1.json"

    if ir.get("kernel") == "graph":
        matmul_ir = _matmul_ir_from_graph(ir)
        desc = build_golem_matmul_op_desc(matmul_ir, backend_config)
        softmax_desc = build_golem_softmax_op_desc_from_graph(ir, backend_config)
        graph_sequence = build_golem_graph_sequence(ir, backend_config)
        graph_path = contracts_dir / "graph_sequence_v1.json"
        softmax_path = contracts_dir / "softmax_op_desc_resolved.json"
        graph_mapping_path = contracts_dir / "graph_env_mapping_v1.json"

        env_path.write_text(build_golem_env_text(desc, backend_config, graph_sequence, softmax_desc), encoding="utf-8")
        resolved_path.write_text(_json_text(desc), encoding="utf-8")
        mapping_path.write_text(_json_text(MATMUL_ENV_MAPPING), encoding="utf-8")
        graph_path.write_text(_json_text(graph_sequence), encoding="utf-8")
        softmax_path.write_text(_json_text(softmax_desc), encoding="utf-8")
        graph_mapping_path.write_text(_json_text(GRAPH_ENV_MAPPING), encoding="utf-8")

        return {
            "env": env_path,
            "resolved_contract": resolved_path,
            "env_mapping": mapping_path,
            "graph_sequence": graph_path,
            "softmax_contract": softmax_path,
            "graph_env_mapping": graph_mapping_path,
        }

    desc = build_golem_matmul_op_desc(ir, backend_config)
    env_path.write_text(build_golem_env_text(desc, backend_config), encoding="utf-8")
    resolved_path.write_text(_json_text(desc), encoding="utf-8")
    mapping_path.write_text(_json_text(MATMUL_ENV_MAPPING), encoding="utf-8")

    return {
        "env": env_path,
        "resolved_contract": resolved_path,
        "env_mapping": mapping_path,
    }


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _matmul_ir_from_graph(ir: dict[str, Any]) -> dict[str, Any]:
    tensors = ir["tensors"]
    matmul_op = ir["ops"][0]
    return {
        "kernel": "gemm",
        "target": ir.get("target", "riscv_cim_mesh"),
        "mode": ir.get("mode", "ir_only"),
        "mesh": dict(ir["mesh"]),
        "tile": {
            "BM": matmul_op["tile"]["BM"],
            "BN": matmul_op["tile"]["BN"],
            "BK": matmul_op["tile"]["BK"],
        },
        "tensors": {
            "A": dict(tensors["A"]),
            "B": dict(tensors["B"]),
            "C": {
                "shape": list(tensors["S"]["shape"]),
                "dtype": tensors["S"]["dtype"],
                "layout": tensors["S"]["layout"],
                "addr": tensors["S"].get("addr", "S_base"),
            },
        },
        "attrs": {
            "transpose_a": matmul_op["attrs"]["transpose_a"],
            "transpose_b": matmul_op["attrs"]["transpose_b"],
        },
        "mapping": {
            "policy": "output_stationary",
            "core_x": "bx % mesh_w",
            "core_y": "by % mesh_h",
        },
        "program": [
            {"op": "clear_acc", "buffer": "C_acc"},
            {
                "op": "loop_k",
                "var": "ko",
                "count": _ceildiv(tensors["A"]["shape"][1], matmul_op["tile"]["BK"]),
                "pipeline_stages": matmul_op["attrs"]["pipeline_stages"],
                "body": [
                    {"op": "load", "tensor": "A", "tile": ["by*BM", "ko*BK", "BM", "BK"], "dst": "A_s"},
                    {"op": "load", "tensor": "B", "tile": ["ko*BK", "bx*BN", "BK", "BN"], "dst": "B_s"},
                    {"op": "cim_gemm", "A": "A_s", "B": "B_s", "C": "C_acc"},
                ],
            },
            {"op": "store", "src": "C_acc", "tensor": "C", "tile": ["by*BM", "bx*BN", "BM", "BN"]},
        ],
    }


def _ceildiv(lhs: int, rhs: int) -> int:
    return -(-lhs // rhs)
