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


def build_golem_env_text(
    desc: dict[str, Any],
    backend_config: GolemBackendConfig = GolemBackendConfig(),
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
    return "\n".join(lines) + "\n"


def export_golem_sst_artifacts(
    ir: dict[str, Any],
    artifact_root: str | Path,
    backend_config: GolemBackendConfig = GolemBackendConfig(),
) -> dict[str, Path]:
    root = Path(artifact_root)
    contracts_dir = root / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    desc = build_golem_matmul_op_desc(ir, backend_config)
    env_path = root / "golem_sst.env"
    resolved_path = contracts_dir / "matmul_op_desc_resolved.json"
    mapping_path = contracts_dir / "matmul_env_mapping_v1.json"

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
