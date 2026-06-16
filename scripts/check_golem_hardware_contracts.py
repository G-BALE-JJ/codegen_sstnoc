#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    args = _parse_args()
    tests_dir = args.hardware_tests_dir
    checks = _build_checks(tests_dir)
    failures: list[str] = []

    for label, path, needles in checks:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            failures.append(f"{label}: cannot read {path}: {exc}")
            continue

        missing = [needle for needle in needles if needle not in text]
        if missing:
            failures.append(f"{label}: {path} missing {', '.join(missing)}")
        else:
            print(f"[OK] {label}: {path}")

    if failures:
        print("[FAIL] Golem hardware contract audit failed:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("[OK] Golem hardware contracts are decoupled enough for CIM-TileIR exporter integration.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Statically audit Golem SST hardware-side env/contract decoupling points."
    )
    parser.add_argument(
        "--hardware-tests-dir",
        type=Path,
        required=True,
        help="Path to RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests.",
    )
    return parser.parse_args()


def _build_checks(tests_dir: Path) -> list[tuple[str, Path, list[str]]]:
    pipeline = tests_dir / "run_noc_dma_pipeline.sh"
    hbm = tests_dir / "tools" / "gen_hbm_init.py"
    runtime = tests_dir / "small" / "mvm_noc_int_array" / "test_noc_dma.cpp"
    config = tests_dir / "small" / "mvm_noc_int_array" / "pipeline_config.h"

    return [
        (
            "GOLEM_ARTIFACT_ROOT external artifact root",
            pipeline,
            [
                'ARTIFACT_ROOT="${GOLEM_ARTIFACT_ROOT:-$SCRIPT_DIR/artifacts}"',
                'export GOLEM_ARTIFACT_ROOT="$ARTIFACT_ROOT"',
                'CONTRACT_RESOLVED_FILE="$ARTIFACT_ROOT/contracts/matmul_op_desc_resolved.json"',
            ],
        ),
        (
            "pipeline exports GOLEM_MATMUL_* compatibility env",
            pipeline,
            [
                'export GOLEM_MATMUL_M="$GOLEM_GEMM_M"',
                'export GOLEM_MATMUL_BLOCK_M="$GOLEM_GEMM_BLOCK_M"',
                'export GOLEM_MATMUL_DTYPE',
                'export GOLEM_MATMUL_LAYOUT="row_major"',
                'export GOLEM_MATMUL_TRANSPOSE_A="0"',
                'export GOLEM_MATMUL_TRANSPOSE_B="0"',
            ],
        ),
        (
            "pipeline validates reusable HBM contract",
            pipeline,
            [
                "validate_hbm_contract_fallback",
                'validate_hbm_contract_fallback "$CONTRACT_RESOLVED_FILE"',
            ],
        ),
        (
            "GOLEM_MATMUL_* environment contract",
            hbm,
            [
                '"m": "GOLEM_MATMUL_M"',
                '"block_m": "GOLEM_MATMUL_BLOCK_M"',
                '"dtype": "GOLEM_MATMUL_DTYPE"',
                '"layout": "GOLEM_MATMUL_LAYOUT"',
                '"transpose_a": "GOLEM_MATMUL_TRANSPOSE_A"',
                '"transpose_b": "GOLEM_MATMUL_TRANSPOSE_B"',
            ],
        ),
        (
            "HBM generator writes mapping and resolved contracts",
            hbm,
            [
                'CONTRACT_MAPPING_FILE = os.path.join(CONTRACT_DIR, "matmul_env_mapping_v1.json")',
                'CONTRACT_RESOLVED_FILE = os.path.join(CONTRACT_DIR, "matmul_op_desc_resolved.json")',
                "json.dump(MATMUL_ENV_MAP",
                "json.dump(MATMUL_OP_DESC",
            ],
        ),
        (
            "HBM generator enforces backend contract constraints",
            hbm,
            [
                'Phase-1 requires GOLEM_MATMUL_LAYOUT=row_major',
                "Phase-1 requires transpose_a=0 and transpose_b=0",
                "GOLEM_GEMM_M/N/K must be divisible by block_M/N/K",
            ],
        ),
        (
            "golem runtime reads matmul env at runtime",
            runtime,
            [
                'read_i64_env_or_default("GOLEM_MATMUL_M"',
                'read_i64_env_or_default("GOLEM_MATMUL_BLOCK_M"',
                'read_dtype_env_or_default("GOLEM_MATMUL_DTYPE"',
                ".layout = GOLEM_LAYOUT_ROW_MAJOR",
                ".transpose_a = 0",
                ".transpose_b = 0",
            ],
        ),
        (
            "pipeline_config exposes compile-time GEMM fallback macros",
            config,
            [
                "#ifndef GOLEM_GEMM_M",
                "#define GOLEM_GEMM_M GOLEM_ARRAY_OUTPUT_SIZE",
                "constexpr int GEMM_M = GOLEM_GEMM_M;",
                "constexpr int GEMM_BLOCK_M = GOLEM_GEMM_BLOCK_M;",
            ],
        ),
    ]


if __name__ == "__main__":
    main()
