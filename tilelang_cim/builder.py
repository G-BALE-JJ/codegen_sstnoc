from __future__ import annotations

from typing import Any


def build_gemm_ir(
    *,
    m: int,
    n: int,
    k: int,
    bm: int,
    bn: int,
    bk: int,
    mesh_w: int = 8,
    mesh_h: int = 8,
    pipeline_stages: int = 1,
    a_dtype: str = "int8",
    b_dtype: str = "int8",
    c_dtype: str = "int32",
) -> dict[str, Any]:
    """Build the first MVP CIM-TileIR dictionary for static GEMM."""
    if pipeline_stages not in (1, 2):
        raise ValueError("pipeline_stages must be 1 or 2")

    loop_k_count = _ceildiv(k, bk) if bk > 0 else 0

    return {
        "kernel": "gemm",
        "target": "riscv_cim_mesh",
        "mode": "ir_only",
        "mesh": {"w": mesh_w, "h": mesh_h},
        "tile": {"BM": bm, "BN": bn, "BK": bk},
        "tensors": {
            "A": {"shape": [m, k], "dtype": a_dtype, "addr": "A_base"},
            "B": {"shape": [k, n], "dtype": b_dtype, "addr": "B_base"},
            "C": {"shape": [m, n], "dtype": c_dtype, "addr": "C_base"},
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
                "count": loop_k_count,
                "pipeline_stages": pipeline_stages,
                "body": [
                    {
                        "op": "load",
                        "tensor": "A",
                        "tile": ["by*BM", "ko*BK", "BM", "BK"],
                        "dst": "A_s",
                    },
                    {
                        "op": "load",
                        "tensor": "B",
                        "tile": ["ko*BK", "bx*BN", "BK", "BN"],
                        "dst": "B_s",
                    },
                    {"op": "cim_gemm", "A": "A_s", "B": "B_s", "C": "C_acc"},
                ],
            },
            {"op": "store", "src": "C_acc", "tensor": "C", "tile": ["by*BM", "bx*BN", "BM", "BN"]},
        ],
    }


def _ceildiv(lhs: int, rhs: int) -> int:
    return -(-lhs // rhs)
