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
    layout: str = "row_major",
    transpose_a: bool = False,
    transpose_b: bool = False,
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
            "A": {"shape": [m, k], "dtype": a_dtype, "layout": layout, "addr": "A_base"},
            "B": {"shape": [k, n], "dtype": b_dtype, "layout": layout, "addr": "B_base"},
            "C": {"shape": [m, n], "dtype": c_dtype, "layout": layout, "addr": "C_base"},
        },
        "attrs": {
            "transpose_a": transpose_a,
            "transpose_b": transpose_b,
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


def build_softmax_ir(
    *,
    rows: int,
    cols: int,
    dtype: str = "fp32",
    axis: int = 1,
    input_name: str = "input",
    output_name: str = "output",
    mesh_w: int = 8,
    mesh_h: int = 8,
    layout: str = "row_major",
) -> dict[str, Any]:
    """Build a first MVP CIM-TileIR dictionary for row-wise softmax."""
    return {
        "kernel": "softmax",
        "target": "riscv_cim_mesh",
        "mode": "ir_only",
        "mesh": {"w": mesh_w, "h": mesh_h},
        "tensors": {
            input_name: {
                "shape": [rows, cols],
                "dtype": dtype,
                "layout": layout,
                "addr": f"{input_name}_base",
            },
            output_name: {
                "shape": [rows, cols],
                "dtype": dtype,
                "layout": layout,
                "addr": f"{output_name}_base",
            },
        },
        "attrs": {"axis": axis},
        "program": [
            {"op": "row_max", "input": input_name, "output": "row_max"},
            {"op": "subtract", "lhs": input_name, "rhs": "row_max", "output": "shifted"},
            {"op": "exp", "input": "shifted", "output": "exp"},
            {"op": "row_sum", "input": "exp", "output": "row_sum"},
            {"op": "divide", "lhs": "exp", "rhs": "row_sum", "output": output_name},
            {"op": "store", "src": output_name, "tensor": output_name},
        ],
    }


def build_matmul_softmax_graph_ir(
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
    dtype: str = "fp32",
    layout: str = "row_major",
) -> dict[str, Any]:
    """Build a graph-shaped IR for GEMM followed by row-wise softmax."""
    if pipeline_stages not in (1, 2):
        raise ValueError("pipeline_stages must be 1 or 2")

    return {
        "kernel": "graph",
        "target": "riscv_cim_mesh",
        "mode": "ir_only",
        "mesh": {"w": mesh_w, "h": mesh_h},
        "tensors": {
            "A": {"shape": [m, k], "dtype": dtype, "layout": layout, "addr": "A_base"},
            "B": {"shape": [k, n], "dtype": dtype, "layout": layout, "addr": "B_base"},
            "S": {"shape": [m, n], "dtype": dtype, "layout": layout, "addr": "S_base"},
            "P": {"shape": [m, n], "dtype": dtype, "layout": layout, "addr": "P_base"},
        },
        "ops": [
            {
                "id": "matmul_0",
                "op": "matmul",
                "inputs": ["A", "B"],
                "outputs": ["S"],
                "tile": {"BM": bm, "BN": bn, "BK": bk},
                "attrs": {
                    "transpose_a": False,
                    "transpose_b": False,
                    "pipeline_stages": pipeline_stages,
                },
            },
            {
                "id": "softmax_0",
                "op": "softmax",
                "inputs": ["S"],
                "outputs": ["P"],
                "attrs": {"axis": 1},
            },
        ],
    }


def _ceildiv(lhs: int, rhs: int) -> int:
    return -(-lhs // rhs)
