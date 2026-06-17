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
    source = _get_source_or_script(func)
    return extract_gemm_ir_from_source(source, mesh_w=mesh_w, mesh_h=mesh_h)


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
    symbols = _collect_int_symbols(func)
    tensors = _collect_tensors(func, symbols)
    tensors.update(_collect_match_buffers(func, symbols))
    _require_gemm_call(func)

    shared_shapes = _collect_alloc_shapes(func, "alloc_shared", symbols)
    shared_shapes.extend(_collect_scoped_alloc_buffers(func, "shared", symbols))
    fragment_shapes = _collect_alloc_shapes(func, "alloc_fragment", symbols)
    fragment_shapes.extend(_collect_scoped_alloc_buffers(func, "local.fragment", symbols))
    pipeline = _find_pipeline(func, symbols)

    a_shape = tensors.get("a") or tensors.get("A")
    b_shape = tensors.get("b") or tensors.get("B")
    c_shape = tensors.get("c") or tensors.get("C")
    if a_shape is None or b_shape is None or c_shape is None:
        raise ValueError("A/B/C tensor annotations are required")

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


def _collect_int_symbols(func: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, int]:
    symbols: dict[str, int] = {}
    positional_args = func.args.args
    defaults = func.args.defaults
    default_offset = len(positional_args) - len(defaults)
    for index, default in enumerate(defaults):
        arg_name = positional_args[default_offset + index].arg
        if isinstance(default, ast.Constant) and isinstance(default.value, int):
            symbols[arg_name] = default.value

    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = _eval_int(node.value, symbols)
            if value is not None:
                symbols[node.targets[0].id] = value
    return symbols


def _collect_tensors(func: ast.FunctionDef | ast.AsyncFunctionDef, symbols: dict[str, int]) -> dict[str, _TensorSpec]:
    tensors: dict[str, _TensorSpec] = {}
    for arg in func.args.args:
        if arg.annotation is None:
            continue
        spec = _parse_tensor_annotation(arg.annotation, symbols)
        if spec is not None:
            tensors[arg.arg] = spec
    return tensors


def _collect_match_buffers(func: ast.FunctionDef | ast.AsyncFunctionDef, symbols: dict[str, int]) -> dict[str, _TensorSpec]:
    tensors: dict[str, _TensorSpec] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or not _is_t_attr(value.func, "match_buffer") or len(value.args) < 2:
            continue
        shape = _eval_shape2(value.args[1], symbols)
        dtype = _eval_match_buffer_dtype(value)
        if shape is not None and dtype is not None:
            tensors[node.targets[0].id] = _TensorSpec(shape=shape, dtype=dtype)
    return tensors


def _eval_match_buffer_dtype(node: ast.Call) -> str:
    if len(node.args) >= 3:
        dtype = _eval_dtype(node.args[2])
        if dtype is not None:
            return dtype
    for keyword in node.keywords:
        if keyword.arg == "dtype":
            dtype = _eval_dtype(keyword.value)
            if dtype is not None:
                return dtype
    return "float32"


def _parse_tensor_annotation(annotation: ast.AST, symbols: dict[str, int]) -> _TensorSpec | None:
    if not isinstance(annotation, ast.Call):
        return None
    if not _is_t_attr(annotation.func, "Tensor"):
        return None
    if len(annotation.args) < 2:
        return None

    shape = _eval_shape2(annotation.args[0], symbols)
    dtype = _eval_dtype(annotation.args[1])
    if shape is None or dtype is None:
        return None
    return _TensorSpec(shape=shape, dtype=dtype)


def _collect_alloc_shapes(func: ast.FunctionDef | ast.AsyncFunctionDef, op_name: str, symbols: dict[str, int]) -> list[tuple[int, int]]:
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
    symbols: dict[str, int],
) -> list[tuple[int, int]]:
    shapes: list[tuple[int, int]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or not _is_t_attr(node.func, "alloc_buffer") or not node.args:
            continue
        scope = None
        for keyword in node.keywords:
            if keyword.arg == "scope":
                scope = _eval_dtype(keyword.value)
        if scope is None or not scope.startswith(scope_prefix):
            continue
        shape = _eval_shape2(node.args[0], symbols)
        if shape is not None:
            shapes.append(shape)
    return shapes


def _find_pipeline(func: ast.FunctionDef | ast.AsyncFunctionDef, symbols: dict[str, int]) -> _PipelineSpec:
    for node in ast.walk(func):
        if not isinstance(node, ast.Call) or not _is_t_attr(node.func, "Pipelined"):
            continue
        count = _eval_int(node.args[0], symbols) if node.args else None
        num_stages = 1
        for keyword in node.keywords:
            if keyword.arg == "num_stages":
                num_stages = _eval_int(keyword.value, symbols) or 0
        if count is None or count <= 0:
            raise ValueError("T.Pipelined count must be a positive static integer")
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


def _eval_num_stages_annotation(node: ast.Call, symbols: dict[str, int]) -> int | None:
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


def _eval_shape2(node: ast.AST, symbols: dict[str, int]) -> tuple[int, int] | None:
    if isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) == 2:
        first = _eval_int(node.elts[0], symbols)
        second = _eval_int(node.elts[1], symbols)
        if first is not None and second is not None:
            return first, second
    return None


def _eval_dtype(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _eval_int(node: ast.AST, symbols: dict[str, int]) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name):
        return symbols.get(node.id)
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
