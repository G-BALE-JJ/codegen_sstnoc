from __future__ import annotations

from typing import Any


def validate_cim_tile_ir(ir: dict[str, Any]) -> list[str]:
    """Return a list of validation errors for the first CIM-TileIR MVP."""
    errors: list[str] = []

    _check_positive_int(ir, ["mesh", "w"], "mesh.w", errors)
    _check_positive_int(ir, ["mesh", "h"], "mesh.h", errors)
    _check_positive_int(ir, ["tile", "BM"], "tile.BM", errors)
    _check_positive_int(ir, ["tile", "BN"], "tile.BN", errors)
    _check_positive_int(ir, ["tile", "BK"], "tile.BK", errors)

    tensors = ir.get("tensors")
    if not isinstance(tensors, dict):
        errors.append("tensors must be an object")
        tensors = {}

    for name in ("A", "B", "C"):
        if name not in tensors:
            errors.append(f"tensors.{name} is required")

    if isinstance(tensors.get("A"), dict) and isinstance(tensors.get("B"), dict) and isinstance(tensors.get("C"), dict):
        _check_gemm_shapes(tensors["A"], tensors["B"], tensors["C"], ir.get("tile", {}), errors)

    mapping = ir.get("mapping")
    if not isinstance(mapping, dict):
        errors.append("mapping must be an object")
    elif mapping.get("policy") != "output_stationary":
        errors.append("mapping.policy must be output_stationary")

    _check_program(ir.get("program"), errors)

    return errors


def _check_positive_int(ir: dict[str, Any], path: list[str], label: str, errors: list[str]) -> None:
    value: Any = ir
    for key in path:
        if not isinstance(value, dict) or key not in value:
            errors.append(f"{label} must be a positive integer")
            return
        value = value[key]

    if not isinstance(value, int) or value <= 0:
        errors.append(f"{label} must be a positive integer")


def _check_gemm_shapes(
    tensor_a: dict[str, Any],
    tensor_b: dict[str, Any],
    tensor_c: dict[str, Any],
    tile: Any,
    errors: list[str],
) -> None:
    a_shape = tensor_a.get("shape")
    b_shape = tensor_b.get("shape")
    c_shape = tensor_c.get("shape")
    if not (_is_2d_shape(a_shape) and _is_2d_shape(b_shape) and _is_2d_shape(c_shape)):
        errors.append("A, B, and C tensor shapes must be 2D integer lists")
        return

    m, k = a_shape
    b_k, n = b_shape
    c_m, c_n = c_shape
    if k != b_k:
        errors.append("A.K must match B.K")
    if (m, n) != (c_m, c_n):
        errors.append("C shape must be [A.M, B.N]")

    if not isinstance(tile, dict):
        return
    bm = tile.get("BM")
    bn = tile.get("BN")
    bk = tile.get("BK")

    if isinstance(bm, int) and bm > 0 and m % bm != 0:
        errors.append("M must be divisible by tile.BM for the first MVP")
    if isinstance(bn, int) and bn > 0 and n % bn != 0:
        errors.append("N must be divisible by tile.BN for the first MVP")
    if isinstance(bk, int) and bk > 0 and k % bk != 0:
        errors.append("K must be divisible by tile.BK for the first MVP")


def _check_program(program: Any, errors: list[str]) -> None:
    if not isinstance(program, list) or not program:
        errors.append("program must be a non-empty list")
        return

    op_names = [op.get("op") for op in program if isinstance(op, dict)]
    if not op_names or op_names[0] != "clear_acc":
        errors.append("program must start with clear_acc")
    if "loop_k" not in op_names:
        errors.append("program must contain a loop_k op before store")
        return
    if "store" not in op_names:
        errors.append("program must contain store")
        return
    if op_names.index("loop_k") > op_names.index("store"):
        errors.append("program must contain a loop_k op before store")

    loop_ops = [op for op in program if isinstance(op, dict) and op.get("op") == "loop_k"]
    for loop_op in loop_ops:
        _check_loop_k(loop_op, errors)


def _check_loop_k(loop_op: dict[str, Any], errors: list[str]) -> None:
    if not isinstance(loop_op.get("count"), int) or loop_op["count"] <= 0:
        errors.append("loop_k.count must be a positive integer")
    if loop_op.get("pipeline_stages") not in (1, 2):
        errors.append("loop_k.pipeline_stages must be 1 or 2")

    body = loop_op.get("body")
    if not isinstance(body, list):
        errors.append("loop_k.body must be a list")
        return

    body_ops = [op.get("op") for op in body if isinstance(op, dict)]
    if body_ops != ["load", "load", "cim_gemm"]:
        errors.append("loop_k.body must contain load, load, cim_gemm in order")


def _is_2d_shape(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(dim, int) and dim > 0 for dim in value)
