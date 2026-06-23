from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .checker import validate_cim_tile_ir


@dataclass(frozen=True)
class GolemBackendConfig:
    array_input_size: int = 64
    array_output_size: int = 64
    num_arrays: int = 64
    total_groups: int = 4
    total_gemm_cores: int = 20
    num_memory_nodes: int = 5
    mem_node_size_bytes: int = 128 * 1024 * 1024
    a_reuse_n_tiles: int = 1
    b_reuse_m_tiles: int = 1
    dma_slot_count: int = 16


SUPPORTED_GOLEM_DTYPES = {"int32", "fp32", "float32", "float"}


def validate_cim_tile_ir_for_golem(
    ir: dict[str, Any],
    backend_config: GolemBackendConfig = GolemBackendConfig(),
) -> list[str]:
    errors = validate_cim_tile_ir(ir)

    if ir.get("kernel") == "graph":
        _validate_matmul_softmax_graph_for_golem(ir, backend_config, errors)
        return errors

    if ir.get("kernel") != "gemm":
        errors.append("Golem backend supports only gemm kernels for the first exporter")
        return errors

    tensors = ir.get("tensors")
    if not isinstance(tensors, dict) or not all(isinstance(tensors.get(name), dict) for name in ("A", "B", "C")):
        return errors

    dtypes = {tensors[name]["dtype"] for name in ("A", "B", "C")}
    if len(dtypes) != 1 or not dtypes.issubset(SUPPORTED_GOLEM_DTYPES):
        errors.append("Golem backend supports only int32/fp32 tensors for the first exporter")

    attrs = ir.get("attrs")
    if not isinstance(attrs, dict):
        return errors
    if attrs.get("transpose_a"):
        errors.append("Golem backend does not support transpose_a for the first exporter")
    if attrs.get("transpose_b"):
        errors.append("Golem backend does not support transpose_b for the first exporter")

    tile = ir.get("tile")
    if not isinstance(tile, dict):
        return errors
    if tile["BM"] != backend_config.array_output_size:
        errors.append(f"tile.BM must equal GOLEM_ARRAY_OUTPUT_SIZE ({backend_config.array_output_size})")
    if tile["BK"] != backend_config.array_input_size:
        errors.append(f"tile.BK must equal GOLEM_ARRAY_INPUT_SIZE ({backend_config.array_input_size})")
    if tile["BN"] > backend_config.num_arrays:
        errors.append(f"tile.BN must be <= GOLEM_NUM_ARRAYS ({backend_config.num_arrays})")

    return errors


def normalize_golem_dtype(dtype: str) -> str:
    if dtype in {"float", "float32"}:
        return "fp32"
    return dtype


def _validate_matmul_softmax_graph_for_golem(
    ir: dict[str, Any],
    backend_config: GolemBackendConfig,
    errors: list[str],
) -> None:
    tensors = ir.get("tensors")
    ops = ir.get("ops")
    if not isinstance(tensors, dict) or not isinstance(ops, list) or len(ops) != 2:
        return
    matmul_op, softmax_op = ops
    if not isinstance(matmul_op, dict) or not isinstance(softmax_op, dict):
        return
    if matmul_op.get("op") != "matmul" or softmax_op.get("op") != "softmax":
        return

    tensor_names = ("A", "B", "S", "P")
    if not all(isinstance(tensors.get(name), dict) for name in tensor_names):
        return

    dtypes = {normalize_golem_dtype(tensors[name].get("dtype")) for name in tensor_names}
    if dtypes != {"fp32"}:
        errors.append("Golem matmul->softmax graph supports only fp32 tensors for CPU fallback softmax")

    layouts = {tensors[name].get("layout") for name in tensor_names}
    if layouts != {"row_major"}:
        errors.append("Golem matmul->softmax graph supports only row_major tensors")

    tile = matmul_op.get("tile")
    if not isinstance(tile, dict):
        return

    if tile["BM"] != backend_config.array_output_size:
        errors.append(f"graph matmul tile.BM must equal GOLEM_ARRAY_OUTPUT_SIZE ({backend_config.array_output_size})")
    if tile["BK"] != backend_config.array_input_size:
        errors.append(f"graph matmul tile.BK must equal GOLEM_ARRAY_INPUT_SIZE ({backend_config.array_input_size})")
    if tile["BN"] > backend_config.num_arrays:
        errors.append(f"graph matmul tile.BN must be <= GOLEM_NUM_ARRAYS ({backend_config.num_arrays})")

    softmax_attrs = softmax_op.get("attrs")
    if not isinstance(softmax_attrs, dict):
        return
    if softmax_attrs.get("axis") != 1:
        errors.append("Golem softmax CPU fallback supports only axis=1 / dim=-1")

    s_shape = tensors["S"].get("shape")
    if isinstance(s_shape, list) and len(s_shape) == 2 and isinstance(s_shape[1], int):
        if s_shape[1] != tile["BN"]:
            errors.append(
                "Golem softmax CPU fallback requires graph N == matmul tile.BN; "
                "multi-N-tile row-wise softmax is not supported"
            )
