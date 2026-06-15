from copy import deepcopy

from tilelang_cim import (
    build_gemm_ir,
    load_architecture_spec,
    validate_architecture_spec,
    validate_cim_tile_ir_for_arch,
)


def _toy_spec():
    return load_architecture_spec("examples/architecture/toy_cim_mesh_v0.json")


def test_toy_architecture_spec_is_valid():
    assert validate_architecture_spec(_toy_spec()) == []


def test_architecture_spec_rejects_invalid_required_fields():
    spec = _toy_spec()
    spec["mesh"]["w"] = 0
    spec["core"]["local_sram_bytes"] = -1
    spec["dma"]["alignment_bytes"] = 0
    spec["cim"]["input_dtypes"] = ["int4"]
    spec["cycle_model"]["type"] = "unknown"

    errors = validate_architecture_spec(spec)

    assert "mesh.w must be a positive integer" in errors
    assert "core.local_sram_bytes must be a positive integer" in errors
    assert "dma.alignment_bytes must be a positive integer" in errors
    assert "cim.input_dtypes contains unsupported dtype int4" in errors
    assert "cycle_model.type must be serial_formula_v0 for the first MVP" in errors


def test_architecture_checker_accepts_matching_gemm_ir():
    ir = build_gemm_ir(m=1024, n=1024, k=1024, bm=64, bn=64, bk=32, mesh_w=8, mesh_h=8)

    assert validate_cim_tile_ir_for_arch(ir, _toy_spec()) == []


def test_architecture_checker_reports_resource_and_dtype_mismatches():
    ir = build_gemm_ir(m=1024, n=1024, k=1024, bm=64, bn=64, bk=32, mesh_w=8, mesh_h=8)
    spec = _toy_spec()
    spec["core"]["local_sram_bytes"] = 1024
    spec["core"]["accumulator_bytes"] = 1024
    spec["cim"]["input_dtypes"] = ["float16"]

    errors = validate_cim_tile_ir_for_arch(ir, spec)

    assert "tensors.A.dtype must be supported by cim.input_dtypes" in errors
    assert "tensors.B.dtype must be supported by cim.input_dtypes" in errors
    assert "local SRAM is too small: required 4096 bytes, available 1024 bytes" in errors
    assert "accumulator is too small: required 16384 bytes, available 1024 bytes" in errors


def test_architecture_checker_reports_tile_and_mesh_mismatches():
    ir = build_gemm_ir(m=1024, n=1024, k=1024, bm=64, bn=64, bk=32, mesh_w=8, mesh_h=8)
    spec = deepcopy(_toy_spec())
    spec["mesh"]["w"] = 4
    spec["cim"]["tile_k"] = 16

    errors = validate_cim_tile_ir_for_arch(ir, spec)

    assert "IR mesh must match architecture mesh for the first MVP" in errors
    assert "tile.BK must match cim.tile_k for the first MVP" in errors
