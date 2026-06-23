from __future__ import annotations

from typing import Any


def validate_cim_tile_ir(ir: dict[str, Any]) -> list[str]:
    """Return a list of validation errors for the first CIM-TileIR MVP."""
    errors: list[str] = []

    _check_positive_int(ir, ["mesh", "w"], "mesh.w", errors)
    _check_positive_int(ir, ["mesh", "h"], "mesh.h", errors)

    kernel = ir.get("kernel")
    if kernel == "softmax":
        _check_softmax_ir(ir, errors)
        return errors
    if kernel == "graph":
        _check_graph_ir(ir, errors)
        return errors
    if kernel not in (None, "gemm"):
        errors.append("kernel must be gemm, softmax, or graph")
        return errors

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
        _check_tensor_layouts(tensors, errors)

    _check_attrs(ir.get("attrs"), errors)

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


def _check_tensor_layouts(tensors: dict[str, Any], errors: list[str]) -> None:
    for name in ("A", "B", "C"):
        tensor = tensors.get(name)
        if not isinstance(tensor, dict):
            continue
        if tensor.get("layout") != "row_major":
            errors.append(f"tensors.{name}.layout must be row_major")


def _check_attrs(attrs: Any, errors: list[str]) -> None:
    if not isinstance(attrs, dict):
        errors.append("attrs must be an object")
        return
    for name in ("transpose_a", "transpose_b"):
        if not isinstance(attrs.get(name), bool):
            errors.append(f"attrs.{name} must be a boolean")


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


def _check_softmax_ir(ir: dict[str, Any], errors: list[str]) -> None:
    tensors = ir.get("tensors")
    if not isinstance(tensors, dict):
        errors.append("tensors must be an object")
        return

    tensor_names = list(tensors)
    if len(tensor_names) != 2:
        errors.append("softmax must define exactly one input tensor and one output tensor")
        return

    input_tensor = tensors[tensor_names[0]]
    output_tensor = tensors[tensor_names[1]]
    if not isinstance(input_tensor, dict) or not isinstance(output_tensor, dict):
        errors.append("softmax input and output tensors must be objects")
        return

    input_shape = input_tensor.get("shape")
    output_shape = output_tensor.get("shape")
    if not _is_2d_shape(input_shape) or not _is_2d_shape(output_shape):
        errors.append("softmax input and output shapes must be 2D integer lists")
    elif input_shape != output_shape:
        errors.append("softmax input and output shapes must match")

    if input_tensor.get("dtype") != output_tensor.get("dtype"):
        errors.append("softmax input and output dtypes must match")

    for name, tensor in zip(tensor_names, (input_tensor, output_tensor)):
        if tensor.get("layout") != "row_major":
            errors.append(f"tensors.{name}.layout must be row_major")

    attrs = ir.get("attrs")
    if not isinstance(attrs, dict):
        errors.append("attrs must be an object")
    elif attrs.get("axis") != 1:
        errors.append("softmax attrs.axis must be 1 for the first MVP")

    program = ir.get("program")
    if not isinstance(program, list):
        errors.append("program must be a list")
        return
    op_names = [op.get("op") for op in program if isinstance(op, dict)]
    if op_names != ["row_max", "subtract", "exp", "row_sum", "divide", "store"]:
        errors.append("softmax program must contain row_max, subtract, exp, row_sum, divide, store in order")


def _check_graph_ir(ir: dict[str, Any], errors: list[str]) -> None:
    tensors = ir.get("tensors")
    if not isinstance(tensors, dict):
        errors.append("tensors must be an object")
        return

    for name in ("A", "B", "S", "P"):
        tensor = tensors.get(name)
        if not isinstance(tensor, dict):
            errors.append(f"tensors.{name} is required")
            continue
        if not _is_2d_shape(tensor.get("shape")):
            errors.append(f"tensors.{name}.shape must be a 2D integer list")
        if tensor.get("layout") != "row_major":
            errors.append(f"tensors.{name}.layout must be row_major")

    if all(isinstance(tensors.get(name), dict) for name in ("A", "B", "S", "P")):
        a_shape = tensors["A"].get("shape")
        b_shape = tensors["B"].get("shape")
        s_shape = tensors["S"].get("shape")
        p_shape = tensors["P"].get("shape")
        if _is_2d_shape(a_shape) and _is_2d_shape(b_shape) and _is_2d_shape(s_shape) and _is_2d_shape(p_shape):
            m, k = a_shape
            b_k, n = b_shape
            if k != b_k:
                errors.append("A.K must match B.K")
            if s_shape != [m, n]:
                errors.append("S shape must be [A.M, B.N]")
            if p_shape != s_shape:
                errors.append("P shape must match S shape")

    ops = ir.get("ops")
    if not isinstance(ops, list) or len(ops) != 2:
        errors.append("graph must contain exactly matmul and softmax ops for the first MVP")
        return
    op_names = [op.get("op") for op in ops if isinstance(op, dict)]
    if op_names != ["matmul", "softmax"]:
        errors.append("graph ops must be matmul, softmax in order for the first MVP")
        return

    matmul_op, softmax_op = ops
    if matmul_op.get("inputs") != ["A", "B"] or matmul_op.get("outputs") != ["S"]:
        errors.append("graph matmul op must consume A/B and produce S")
    if softmax_op.get("inputs") != ["S"] or softmax_op.get("outputs") != ["P"]:
        errors.append("graph softmax op must consume S and produce P")

    tile = matmul_op.get("tile")
    if not isinstance(tile, dict):
        errors.append("graph matmul op tile must be an object")
    else:
        for key in ("BM", "BN", "BK"):
            value = tile.get(key)
            if not isinstance(value, int) or value <= 0:
                errors.append(f"graph matmul tile.{key} must be a positive integer")
        a_shape = tensors.get("A", {}).get("shape") if isinstance(tensors.get("A"), dict) else None
        b_shape = tensors.get("B", {}).get("shape") if isinstance(tensors.get("B"), dict) else None
        if _is_2d_shape(a_shape) and _is_2d_shape(b_shape):
            if isinstance(tile.get("BM"), int) and tile["BM"] > 0 and a_shape[0] % tile["BM"] != 0:
                errors.append("M must be divisible by graph matmul tile.BM for the first MVP")
            if isinstance(tile.get("BN"), int) and tile["BN"] > 0 and b_shape[1] % tile["BN"] != 0:
                errors.append("N must be divisible by graph matmul tile.BN for the first MVP")
            if isinstance(tile.get("BK"), int) and tile["BK"] > 0 and a_shape[1] % tile["BK"] != 0:
                errors.append("K must be divisible by graph matmul tile.BK for the first MVP")

    matmul_attrs = matmul_op.get("attrs")
    if not isinstance(matmul_attrs, dict):
        errors.append("graph matmul attrs must be an object")
    else:
        if matmul_attrs.get("transpose_a") is not False:
            errors.append("graph matmul attrs.transpose_a must be false for the first MVP")
        if matmul_attrs.get("transpose_b") is not False:
            errors.append("graph matmul attrs.transpose_b must be false for the first MVP")
        if matmul_attrs.get("pipeline_stages") not in (1, 2):
            errors.append("graph matmul attrs.pipeline_stages must be 1 or 2")

    softmax_attrs = softmax_op.get("attrs")
    if not isinstance(softmax_attrs, dict):
        errors.append("graph softmax attrs must be an object")
    elif softmax_attrs.get("axis") != 1:
        errors.append("graph softmax attrs.axis must be 1 for the first MVP")
