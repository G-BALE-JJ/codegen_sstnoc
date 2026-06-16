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
