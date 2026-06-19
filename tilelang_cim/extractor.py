from __future__ import annotations

import ast
import inspect
import textwrap
from dataclasses import dataclass
from typing import Any

from .builder import build_gemm_ir
from .checker import validate_cim_tile_ir


def extract_gemm_ir_from_tilelang(
    func: Any,
    *,
    mesh_w: int = 8,
    mesh_h: int = 8,
) -> dict[str, Any]:
    """Extract MVP GEMM CIM-TileIR from a TileLang function's Python source."""
    if _looks_like_tir_prim_func(func):
        return extract_gemm_ir_from_tir(func, mesh_w=mesh_w, mesh_h=mesh_h)
    source = _get_source_or_script(func)
    return extract_gemm_ir_from_source(source, mesh_w=mesh_w, mesh_h=mesh_h)


def extract_gemm_ir_from_tir(
    func_or_mod: Any,
    *,
    mesh_w: int = 8,
    mesh_h: int = 8,
) -> dict[str, Any]:
    """Extract MVP GEMM CIM-TileIR directly from TileLang-generated TIR."""
    funcs = _iter_tir_prim_funcs(func_or_mod)
    if not funcs:
        raise ValueError("No TIR PrimFunc was found")
    if len(funcs) > 1:
        raise ValueError("Expected one TIR PrimFunc for GEMM extraction")

    func = funcs[0]
    tensors = _collect_tir_buffer_tensors(func)
    a_shape, b_shape, c_shape = _infer_gemm_tensor_roles(tensors)
    alloc_buffers = _collect_tir_alloc_buffers(func)
    gemm_call = _find_tir_gemm_call(func)
    pipeline = _find_tir_pipeline(func)

    bm = _int_imm(gemm_call.args[5], "T.gemm M tile")
    bn = _int_imm(gemm_call.args[6], "T.gemm N tile")
    bk = _int_imm(gemm_call.args[7], "T.gemm K tile")
    transpose_a = bool(_int_imm(gemm_call.args[3], "T.gemm transpose_A"))
    transpose_b = bool(_int_imm(gemm_call.args[4], "T.gemm transpose_B"))
    if transpose_a or transpose_b:
        raise ValueError("transpose GEMM is not supported by the first TIR extractor MVP")

    _require_tir_buffer_scope(alloc_buffers, "shared", "shared buffer")
    _require_tir_buffer_scope(alloc_buffers, "local.fragment", "fragment buffer")

    ir = build_gemm_ir(
        m=a_shape.shape[0],
        n=b_shape.shape[1],
        k=a_shape.shape[1],
        bm=bm,
        bn=bn,
        bk=bk,
        mesh_w=mesh_w,
        mesh_h=mesh_h,
        pipeline_stages=pipeline.num_stages,
        a_dtype=a_shape.dtype,
        b_dtype=b_shape.dtype,
        c_dtype=c_shape.dtype,
    )
    errors = validate_cim_tile_ir(ir)
    if errors:
        raise ValueError("Extracted invalid CIM-TileIR:\n" + "\n".join(f"- {error}" for error in errors))
    return ir


def _looks_like_tir_prim_func(value: Any) -> bool:
    return hasattr(value, "body") and hasattr(value, "buffer_map")


def extract_gemm_ir_from_source(
    source: str,
    *,
    mesh_w: int = 8,
    mesh_h: int = 8,
) -> dict[str, Any]:
    """Extract MVP GEMM CIM-TileIR from a narrow TileLang GEMM source pattern."""
    tree = ast.parse(textwrap.dedent(source))
    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not functions:
        raise ValueError("No function definition was found")

    func = _select_tilelang_function(functions)
    symbols = _collect_static_symbols(tree, func)
    tensors = _collect_tensors(func, symbols)
    tensors.update(_collect_match_buffers(func, symbols))
    _require_gemm_call(func)

    shared_shapes = _collect_alloc_shapes(func, "alloc_shared", symbols)
    shared_shapes.extend(_collect_scoped_alloc_buffers(func, "shared", symbols))
    fragment_shapes = _collect_alloc_shapes(func, "alloc_fragment", symbols)
    fragment_shapes.extend(_collect_scoped_alloc_buffers(func, "local.fragment", symbols))
    pipeline = _find_pipeline(func, symbols)

    a_shape, b_shape, c_shape = _infer_gemm_tensor_roles(tensors)

    bm, bn = _infer_output_tile(fragment_shapes, shared_shapes)
    bk = _infer_k_tile(shared_shapes, pipeline)

    ir = build_gemm_ir(
        m=a_shape.shape[0],
        n=b_shape.shape[1],
        k=a_shape.shape[1],
        bm=bm,
        bn=bn,
        bk=bk,
        mesh_w=mesh_w,
        mesh_h=mesh_h,
        pipeline_stages=pipeline.num_stages,
        a_dtype=a_shape.dtype,
        b_dtype=b_shape.dtype,
        c_dtype=c_shape.dtype,
    )
    errors = validate_cim_tile_ir(ir)
    if errors:
        raise ValueError("Extracted invalid CIM-TileIR:\n" + "\n".join(f"- {error}" for error in errors))
    return ir


@dataclass(frozen=True)
class _TensorSpec:
    shape: tuple[int, int]
    dtype: str


@dataclass(frozen=True)
class _PipelineSpec:
    count: int
    num_stages: int


def _iter_tir_prim_funcs(func_or_mod: Any) -> list[Any]:
    if _looks_like_tir_prim_func(func_or_mod):
        return [func_or_mod]
    functions = getattr(func_or_mod, "functions", None)
    if functions is None:
        return []
    return [func for func in functions.values() if _looks_like_tir_prim_func(func)]


def _collect_tir_buffer_tensors(func: Any) -> dict[str, _TensorSpec]:
    tensors: dict[str, _TensorSpec] = {}
    for _, buffer in getattr(func, "buffer_map", {}).items():
        shape = _shape_from_tir_buffer(buffer)
        dtype = str(getattr(buffer, "dtype"))
        name = str(getattr(buffer, "name", getattr(buffer, "name_hint", "")))
        if shape is not None and name:
            tensors[name] = _TensorSpec(shape=shape, dtype=dtype)
    return tensors


def _shape_from_tir_buffer(buffer: Any) -> tuple[int, int] | None:
    shape = getattr(buffer, "shape", None)
    if shape is None or len(shape) != 2:
        return None
    first = _maybe_int_imm(shape[0])
    second = _maybe_int_imm(shape[1])
    if first is None or second is None:
        raise ValueError("unsupported dynamic shape: TIR buffer shapes must be static integer pairs")
    return first, second


def _collect_tir_alloc_buffers(func: Any) -> list[Any]:
    alloc_buffers: list[Any] = []

    def visit(node: Any) -> None:
        for buffer in getattr(node, "alloc_buffers", []):
            alloc_buffers.append(buffer)

    _post_order_visit(func.body, visit)
    return alloc_buffers


def _find_tir_gemm_call(func: Any) -> Any:
    gemm_calls: list[Any] = []

    def visit(node: Any) -> None:
        op = getattr(node, "op", None)
        if op is not None and str(op) == "Op(tl.tileop.gemm)":
            gemm_calls.append(node)

    _post_order_visit(func.body, visit)
    if not gemm_calls:
        raise ValueError("T.gemm call was not found")
    if len(gemm_calls) > 1:
        raise ValueError("Expected one T.gemm call for the first TIR extractor MVP")
    return gemm_calls[0]


def _find_tir_pipeline(func: Any) -> _PipelineSpec:
    loops: list[_PipelineSpec] = []

    def visit(node: Any) -> None:
        if not hasattr(node, "extent") or not hasattr(node, "annotations"):
            return
        count = _maybe_int_imm(node.extent)
        if count is None or count <= 0:
            return
        num_stages = 1
        annotations = getattr(node, "annotations", {})
        if "num_stages" in annotations:
            value = _maybe_int_imm(annotations["num_stages"])
            if value is not None:
                num_stages = value
        loops.append(_PipelineSpec(count=count, num_stages=num_stages))

    _post_order_visit(func.body, visit)
    if not loops:
        raise ValueError("TIR serial pipeline loop was not found")
    if loops[0].num_stages not in (1, 2):
        raise ValueError("num_stages must be 1 or 2 for the first CIM extractor MVP")
    return loops[0]


def _require_tir_buffer_scope(buffers: list[Any], scope_prefix: str, label: str) -> None:
    for buffer in buffers:
        scope = _tir_buffer_scope(buffer)
        if scope.startswith(scope_prefix):
            return
    raise ValueError(f"Unable to infer GEMM tile shape: missing {label}")


def _tir_buffer_scope(buffer: Any) -> str:
    scope = getattr(buffer, "scope", None)
    if callable(scope):
        return str(scope())
    return str(scope or "")


def _post_order_visit(body: Any, visitor) -> None:
    try:
        from tvm.tir.stmt_functor import post_order_visit
    except ModuleNotFoundError:
        import tilelang  # noqa: F401
        from tvm.tir.stmt_functor import post_order_visit

    post_order_visit(body, visitor)


def _int_imm(value: Any, label: str) -> int:
    result = _maybe_int_imm(value)
    if result is None:
        raise ValueError(f"{label} must be a static integer")
    return result


def _maybe_int_imm(value: Any) -> int | None:
    raw = getattr(value, "value", None)
    if isinstance(raw, int):
        return raw
    if isinstance(value, int):
        return value
    return None


def _infer_gemm_tensor_roles(tensors: dict[str, _TensorSpec]) -> tuple[_TensorSpec, _TensorSpec, _TensorSpec]:
    named_roles = (
        tensors.get("a") or tensors.get("A"),
        tensors.get("b") or tensors.get("B"),
        tensors.get("c") or tensors.get("C"),
    )
    if all(role is not None for role in named_roles):
        return named_roles  # type: ignore[return-value]

    candidates: list[tuple[_TensorSpec, _TensorSpec, _TensorSpec]] = []
    tensor_specs = list(tensors.values())
    for a_candidate in tensor_specs:
        m, k = a_candidate.shape
        for b_candidate in tensor_specs:
            if b_candidate is a_candidate:
                continue
            if b_candidate.shape[0] != k:
                continue
            n = b_candidate.shape[1]
            for c_candidate in tensor_specs:
                if c_candidate is a_candidate or c_candidate is b_candidate:
                    continue
                if c_candidate.shape == (m, n):
                    candidates.append((a_candidate, b_candidate, c_candidate))

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError("Unable to infer unique A/B/C tensor roles from GEMM tensor shapes")
    raise ValueError("A/B/C tensor annotations are required or must form A(M,K), B(K,N), C(M,N)")


def _select_tilelang_function(functions: list[ast.FunctionDef | ast.AsyncFunctionDef]) -> ast.FunctionDef | ast.AsyncFunctionDef:
    prim_funcs = [func for func in functions if any(_is_t_attr_call(decorator, "prim_func") for decorator in func.decorator_list)]
    if prim_funcs:
        return prim_funcs[0]
    return functions[-1]


def _get_source_or_script(func: Any) -> str:
    try:
        return inspect.getsource(func)
    except (OSError, TypeError):
        pass

    script = getattr(func, "script", None)
    if callable(script):
        try:
            return str(script())
        except Exception:
            pass

    text = str(func)
    if "def " in text and "T.gemm" in text:
        return text

    raise ValueError("Unable to inspect TileLang function source")


StaticSymbol = int | str | tuple[int, int]


def _collect_static_symbols(tree: ast.Module, func: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, StaticSymbol]:
    symbols: dict[str, StaticSymbol] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_default_symbols(node, symbols)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = _eval_static_symbol(node.value, symbols)
            if value is not None:
                symbols[node.targets[0].id] = value
    _collect_default_symbols(func, symbols)
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = _eval_static_symbol(node.value, symbols)
            if value is not None:
                symbols[node.targets[0].id] = value
    return symbols


def _collect_default_symbols(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    symbols: dict[str, StaticSymbol],
) -> None:
    positional_args = func.args.args
    defaults = func.args.defaults
    default_offset = len(positional_args) - len(defaults)
    for index, default in enumerate(defaults):
        arg_name = positional_args[default_offset + index].arg
        value = _eval_static_symbol(default, symbols)
        if value is not None:
            symbols[arg_name] = value


def _eval_static_symbol(node: ast.AST, symbols: dict[str, StaticSymbol]) -> StaticSymbol | None:
    int_value = _eval_int(node, symbols)
    if int_value is not None:
        return int_value
    dtype = _eval_dtype(node, symbols)
    if dtype is not None:
        return dtype
    return _eval_shape2(node, symbols)


def _collect_tensors(func: ast.FunctionDef | ast.AsyncFunctionDef, symbols: dict[str, StaticSymbol]) -> dict[str, _TensorSpec]:
    tensors: dict[str, _TensorSpec] = {}
    for arg in func.args.args:
        if arg.annotation is None:
            continue
        spec = _parse_tensor_annotation(arg.annotation, symbols)
        if spec is not None:
            tensors[arg.arg] = spec
    return tensors


def _collect_match_buffers(func: ast.FunctionDef | ast.AsyncFunctionDef, symbols: dict[str, StaticSymbol]) -> dict[str, _TensorSpec]:
    tensors: dict[str, _TensorSpec] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or not _is_t_attr(value.func, "match_buffer") or len(value.args) < 2:
            continue
        shape = _eval_shape2(value.args[1], symbols)
        dtype = _eval_match_buffer_dtype(value, symbols)
        if shape is not None and dtype is not None:
            tensors[node.targets[0].id] = _TensorSpec(shape=shape, dtype=dtype)
    return tensors


def _eval_match_buffer_dtype(node: ast.Call, symbols: dict[str, StaticSymbol]) -> str:
    if len(node.args) >= 3:
        dtype = _eval_dtype(node.args[2], symbols)
        if dtype is not None:
            return dtype
    for keyword in node.keywords:
        if keyword.arg == "dtype":
            dtype = _eval_dtype(keyword.value, symbols)
            if dtype is not None:
                return dtype
    return "float32"


def _parse_tensor_annotation(annotation: ast.AST, symbols: dict[str, StaticSymbol]) -> _TensorSpec | None:
    if not isinstance(annotation, ast.Call):
        return None
    if not _is_t_attr(annotation.func, "Tensor"):
        return None
    if len(annotation.args) < 2:
        return None

    shape = _eval_shape2(annotation.args[0], symbols)
    dtype = _eval_dtype(annotation.args[1], symbols)
    if shape is None and _looks_like_shape2(annotation.args[0]):
        raise ValueError("unsupported dynamic shape: tensor shapes must be static integer pairs")
    if shape is None or dtype is None:
        return None
    return _TensorSpec(shape=shape, dtype=dtype)


def _collect_alloc_shapes(func: ast.FunctionDef | ast.AsyncFunctionDef, op_name: str, symbols: dict[str, StaticSymbol]) -> list[tuple[int, int]]:
    shapes: list[tuple[int, int]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or not _is_t_attr(node.func, op_name) or not node.args:
            continue
        shape = _eval_shape2(node.args[0], symbols)
        if shape is not None:
            shapes.append(shape)
    return shapes


def _collect_scoped_alloc_buffers(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    scope_prefix: str,
    symbols: dict[str, StaticSymbol],
) -> list[tuple[int, int]]:
    shapes: list[tuple[int, int]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or not _is_t_attr(node.func, "alloc_buffer") or not node.args:
            continue
        scope = None
        for keyword in node.keywords:
            if keyword.arg == "scope":
                scope = _eval_dtype(keyword.value, symbols)
        if scope is None or not scope.startswith(scope_prefix):
            continue
        shape = _eval_shape2(node.args[0], symbols)
        if shape is not None:
            shapes.append(shape)
    return shapes


def _find_pipeline(func: ast.FunctionDef | ast.AsyncFunctionDef, symbols: dict[str, StaticSymbol]) -> _PipelineSpec:
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or not _is_t_attr(node.func, "Pipelined"):
            continue
        count = _eval_int(node.args[0], symbols) if node.args else None
        num_stages = 1
        for keyword in node.keywords:
            if keyword.arg == "num_stages":
                num_stages = _eval_int(keyword.value, symbols) or 0
        if count is None or count <= 0:
            raise ValueError("unsupported dynamic shape: T.Pipelined count must be a positive static integer")
        if num_stages not in (1, 2):
            raise ValueError("num_stages must be 1 or 2 for the first CIM extractor MVP")
        return _PipelineSpec(count=count, num_stages=num_stages)
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or not _is_t_attr(node.func, "serial"):
            continue
        count = _eval_int(node.args[0], symbols) if node.args else None
        num_stages = _eval_num_stages_annotation(node, symbols) or 1
        if count is None or count <= 0:
            continue
        if num_stages not in (1, 2):
            raise ValueError("num_stages must be 1 or 2 for the first CIM extractor MVP")
        return _PipelineSpec(count=count, num_stages=num_stages)
    raise ValueError("T.Pipelined loop was not found")


def _eval_num_stages_annotation(node: ast.Call, symbols: dict[str, StaticSymbol]) -> int | None:
    for keyword in node.keywords:
        if keyword.arg != "annotations" or not isinstance(keyword.value, ast.Dict):
            continue
        for key, value in zip(keyword.value.keys, keyword.value.values):
            if isinstance(key, ast.Constant) and key.value == "num_stages":
                return _eval_int(value, symbols)
    return None


def _require_gemm_call(func: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and _is_t_attr(node.func, "gemm"):
            return
    raise ValueError("T.gemm call was not found")


def _infer_output_tile(fragment_shapes: list[tuple[int, int]], shared_shapes: list[tuple[int, int]]) -> tuple[int, int]:
    if fragment_shapes:
        return fragment_shapes[0]
    if len(shared_shapes) >= 2:
        return shared_shapes[0][0], shared_shapes[1][1]
    raise ValueError("Unable to infer BM/BN from T.alloc_fragment or T.alloc_shared")


def _infer_k_tile(shared_shapes: list[tuple[int, int]], pipeline: _PipelineSpec) -> int:
    if len(shared_shapes) >= 2 and shared_shapes[0][1] == shared_shapes[1][0]:
        return shared_shapes[0][1]
    if len(shared_shapes) >= 2:
        return min(shared_shapes[0][1], shared_shapes[1][0])
    raise ValueError("Unable to infer BK from T.alloc_shared")


def _eval_shape2(node: ast.AST, symbols: dict[str, StaticSymbol]) -> tuple[int, int] | None:
    if isinstance(node, ast.Name):
        value = symbols.get(node.id)
        return value if isinstance(value, tuple) else None
    if isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) == 2:
        first = _eval_int(node.elts[0], symbols)
        second = _eval_int(node.elts[1], symbols)
        if first is not None and second is not None:
            return first, second
    return None


def _looks_like_shape2(node: ast.AST) -> bool:
    return isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) == 2


def _eval_dtype(node: ast.AST, symbols: dict[str, StaticSymbol] | None = None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        if symbols is not None and isinstance(symbols.get(node.id), str):
            return symbols[node.id]  # type: ignore[return-value]
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _eval_int(node: ast.AST, symbols: dict[str, StaticSymbol]) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name):
        value = symbols.get(node.id)
        return value if isinstance(value, int) else None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _eval_int(node.operand, symbols)
        return -value if value is not None else None
    if isinstance(node, ast.BinOp):
        lhs = _eval_int(node.left, symbols)
        rhs = _eval_int(node.right, symbols)
        if lhs is None or rhs is None:
            return None
        if isinstance(node.op, ast.Add):
            return lhs + rhs
        if isinstance(node.op, ast.Sub):
            return lhs - rhs
        if isinstance(node.op, ast.Mult):
            return lhs * rhs
        if isinstance(node.op, ast.FloorDiv) and rhs != 0:
            return lhs // rhs
    if isinstance(node, ast.Call) and _is_t_attr(node.func, "ceildiv") and len(node.args) == 2:
        lhs = _eval_int(node.args[0], symbols)
        rhs = _eval_int(node.args[1], symbols)
        if lhs is not None and rhs is not None and rhs > 0:
            return -(-lhs // rhs)
    return None


def _is_t_attr_call(node: ast.AST, attr_name: str) -> bool:
    return isinstance(node, ast.Call) and _is_t_attr(node.func, attr_name)


def _is_t_attr(node: ast.AST, attr_name: str) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == attr_name
