from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .checker import validate_cim_tile_ir


DTYPE_BYTES = {
    "int8": 1,
    "uint8": 1,
    "float16": 2,
    "float32": 4,
    "float": 4,
    "int32": 4,
}


def load_architecture_spec(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_architecture_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not isinstance(spec.get("name"), str) or not spec["name"]:
        errors.append("name must be a non-empty string")

    _check_positive_int(spec, ["mesh", "w"], "mesh.w", errors)
    _check_positive_int(spec, ["mesh", "h"], "mesh.h", errors)
    if _get(spec, ["mesh", "core_id"]) != "row_major":
        errors.append("mesh.core_id must be row_major for the first MVP")

    _check_positive_int(spec, ["core", "local_sram_bytes"], "core.local_sram_bytes", errors)
    _check_positive_int(spec, ["core", "accumulator_bytes"], "core.accumulator_bytes", errors)
    _check_positive_int(spec, ["core", "max_resident_output_tiles"], "core.max_resident_output_tiles", errors)

    _check_positive_int(spec, ["dma", "bytes_per_cycle"], "dma.bytes_per_cycle", errors)
    _check_non_negative_int(spec, ["dma", "startup_cycles"], "dma.startup_cycles", errors)
    _check_positive_int(spec, ["dma", "alignment_bytes"], "dma.alignment_bytes", errors)
    _check_bool(spec, ["dma", "supports_2d"], "dma.supports_2d", errors)
    _check_bool(spec, ["dma", "overlap_with_compute"], "dma.overlap_with_compute", errors)

    input_dtypes = _get(spec, ["cim", "input_dtypes"])
    if not isinstance(input_dtypes, list) or not input_dtypes or not all(isinstance(dtype, str) for dtype in input_dtypes):
        errors.append("cim.input_dtypes must be a non-empty string list")
    else:
        for dtype in input_dtypes:
            if dtype not in DTYPE_BYTES:
                errors.append(f"cim.input_dtypes contains unsupported dtype {dtype}")

    acc_dtype = _get(spec, ["cim", "acc_dtype"])
    if not isinstance(acc_dtype, str) or acc_dtype not in DTYPE_BYTES:
        errors.append("cim.acc_dtype must be a supported dtype string")

    _check_positive_int(spec, ["cim", "tile_m"], "cim.tile_m", errors)
    _check_positive_int(spec, ["cim", "tile_n"], "cim.tile_n", errors)
    _check_positive_int(spec, ["cim", "tile_k"], "cim.tile_k", errors)
    _check_positive_int(spec, ["cim", "cycles_per_cim_gemm"], "cim.cycles_per_cim_gemm", errors)
    _check_bool(spec, ["cim", "supports_transpose_a"], "cim.supports_transpose_a", errors)
    _check_bool(spec, ["cim", "supports_transpose_b"], "cim.supports_transpose_b", errors)

    _check_bool(spec, ["noc", "enabled"], "noc.enabled", errors)
    _check_bool(spec, ["sync", "barrier_supported"], "sync.barrier_supported", errors)

    if _get(spec, ["cycle_model", "type"]) != "serial_formula_v0":
        errors.append("cycle_model.type must be serial_formula_v0 for the first MVP")

    return errors


def validate_cim_tile_ir_for_arch(ir: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    errors = validate_cim_tile_ir(ir)
    errors.extend(validate_architecture_spec(spec))
    if errors:
        return errors

    mesh = ir["mesh"]
    arch_mesh = spec["mesh"]
    if mesh["w"] != arch_mesh["w"] or mesh["h"] != arch_mesh["h"]:
        errors.append("IR mesh must match architecture mesh for the first MVP")

    tensors = ir["tensors"]
    tile = ir["tile"]
    cim = spec["cim"]
    core = spec["core"]
    dma = spec["dma"]

    for tensor_name in ("A", "B"):
        dtype = tensors[tensor_name]["dtype"]
        if dtype not in cim["input_dtypes"]:
            errors.append(f"tensors.{tensor_name}.dtype must be supported by cim.input_dtypes")
    if tensors["C"]["dtype"] != cim["acc_dtype"]:
        errors.append("tensors.C.dtype must match cim.acc_dtype")

    if tile["BM"] != cim["tile_m"]:
        errors.append("tile.BM must match cim.tile_m for the first MVP")
    if tile["BN"] != cim["tile_n"]:
        errors.append("tile.BN must match cim.tile_n for the first MVP")
    if tile["BK"] != cim["tile_k"]:
        errors.append("tile.BK must match cim.tile_k for the first MVP")

    pipeline_stages = _loop_k(ir).get("pipeline_stages", 1)
    a_tile_bytes, b_tile_bytes, c_tile_bytes = tile_byte_sizes(ir)
    local_sram_required = pipeline_stages * (a_tile_bytes + b_tile_bytes)
    if local_sram_required > core["local_sram_bytes"]:
        errors.append(
            "local SRAM is too small: "
            f"required {local_sram_required} bytes, available {core['local_sram_bytes']} bytes"
        )
    if c_tile_bytes > core["accumulator_bytes"]:
        errors.append(
            "accumulator is too small: "
            f"required {c_tile_bytes} bytes, available {core['accumulator_bytes']} bytes"
        )

    alignment = dma["alignment_bytes"]
    for label, byte_count in (("A tile", a_tile_bytes), ("B tile", b_tile_bytes), ("C tile", c_tile_bytes)):
        if byte_count % alignment != 0:
            errors.append(f"{label} DMA bytes must be aligned to dma.alignment_bytes")

    return errors


def tile_byte_sizes(ir: dict[str, Any]) -> tuple[int, int, int]:
    bm = ir["tile"]["BM"]
    bn = ir["tile"]["BN"]
    bk = ir["tile"]["BK"]
    a_bytes = bm * bk * dtype_bytes(ir["tensors"]["A"]["dtype"])
    b_bytes = bk * bn * dtype_bytes(ir["tensors"]["B"]["dtype"])
    c_bytes = bm * bn * dtype_bytes(ir["tensors"]["C"]["dtype"])
    return a_bytes, b_bytes, c_bytes


def dtype_bytes(dtype: str) -> int:
    if dtype not in DTYPE_BYTES:
        raise ValueError(f"Unsupported dtype: {dtype}")
    return DTYPE_BYTES[dtype]


def ceildiv(lhs: int, rhs: int) -> int:
    return -(-lhs // rhs)


def _loop_k(ir: dict[str, Any]) -> dict[str, Any]:
    for op in ir["program"]:
        if op.get("op") == "loop_k":
            return op
    raise ValueError("program must contain loop_k")


def _check_positive_int(spec: dict[str, Any], path: list[str], label: str, errors: list[str]) -> None:
    value = _get(spec, path)
    if not isinstance(value, int) or value <= 0:
        errors.append(f"{label} must be a positive integer")


def _check_non_negative_int(spec: dict[str, Any], path: list[str], label: str, errors: list[str]) -> None:
    value = _get(spec, path)
    if not isinstance(value, int) or value < 0:
        errors.append(f"{label} must be a non-negative integer")


def _check_bool(spec: dict[str, Any], path: list[str], label: str, errors: list[str]) -> None:
    value = _get(spec, path)
    if not isinstance(value, bool):
        errors.append(f"{label} must be a boolean")


def _get(spec: dict[str, Any], path: list[str]) -> Any:
    value: Any = spec
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value
