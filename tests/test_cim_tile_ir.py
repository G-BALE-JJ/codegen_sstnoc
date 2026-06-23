import json

import pytest

from tilelang_cim import build_gemm_ir, build_matmul_softmax_graph_ir, build_softmax_ir, to_json_text, validate_cim_tile_ir


def test_build_gemm_ir_exports_checked_json():
    ir = build_gemm_ir(
        m=1024,
        n=1024,
        k=1024,
        bm=64,
        bn=64,
        bk=32,
        mesh_w=8,
        mesh_h=8,
        pipeline_stages=2,
    )

    assert validate_cim_tile_ir(ir) == []

    payload = json.loads(to_json_text(ir))
    assert payload["kernel"] == "gemm"
    assert payload["mode"] == "ir_only"
    assert payload["target"] == "riscv_cim_mesh"
    assert payload["mesh"] == {"w": 8, "h": 8}
    assert payload["tile"] == {"BM": 64, "BN": 64, "BK": 32}
    assert payload["tensors"]["A"] == {
        "shape": [1024, 1024],
        "dtype": "int8",
        "layout": "row_major",
        "addr": "A_base",
    }
    assert payload["tensors"]["B"] == {
        "shape": [1024, 1024],
        "dtype": "int8",
        "layout": "row_major",
        "addr": "B_base",
    }
    assert payload["tensors"]["C"] == {
        "shape": [1024, 1024],
        "dtype": "int32",
        "layout": "row_major",
        "addr": "C_base",
    }
    assert payload["attrs"] == {"transpose_a": False, "transpose_b": False}
    assert payload["mapping"]["policy"] == "output_stationary"
    assert [op["op"] for op in payload["program"]] == ["clear_acc", "loop_k", "store"]
    assert payload["program"][1]["count"] == 32
    assert payload["program"][1]["pipeline_stages"] == 2
    assert [op["op"] for op in payload["program"][1]["body"]] == [
        "load",
        "load",
        "cim_gemm",
    ]


def test_checker_rejects_invalid_tile_and_program_order():
    ir = build_gemm_ir(
        m=128,
        n=128,
        k=128,
        bm=0,
        bn=64,
        bk=30,
        mesh_w=0,
        mesh_h=4,
    )
    ir["program"] = [{"op": "store", "tensor": "C"}]

    errors = validate_cim_tile_ir(ir)

    assert "mesh.w must be a positive integer" in errors
    assert "tile.BM must be a positive integer" in errors
    assert "K must be divisible by tile.BK for the first MVP" in errors
    assert "program must start with clear_acc" in errors
    assert "program must contain a loop_k op before store" in errors


def test_checker_requires_gemm_tensors_and_output_stationary_mapping():
    ir = build_gemm_ir(m=128, n=128, k=128, bm=64, bn=64, bk=32)
    del ir["tensors"]["B"]
    ir["mapping"]["policy"] = "row_stationary"

    errors = validate_cim_tile_ir(ir)

    assert "tensors.B is required" in errors
    assert "mapping.policy must be output_stationary" in errors


def test_checker_rejects_missing_layout_and_invalid_transpose_flags():
    ir = build_gemm_ir(m=128, n=128, k=128, bm=64, bn=64, bk=32)
    del ir["tensors"]["A"]["layout"]
    ir["tensors"]["B"]["layout"] = "column_major"
    ir["attrs"]["transpose_a"] = 1
    del ir["attrs"]["transpose_b"]

    errors = validate_cim_tile_ir(ir)

    assert "tensors.A.layout must be row_major" in errors
    assert "tensors.B.layout must be row_major" in errors
    assert "attrs.transpose_a must be a boolean" in errors
    assert "attrs.transpose_b must be a boolean" in errors


def test_build_gemm_ir_rejects_invalid_pipeline_stage():
    with pytest.raises(ValueError, match="pipeline_stages must be 1 or 2"):
        build_gemm_ir(m=128, n=128, k=128, bm=64, bn=64, bk=32, pipeline_stages=3)


def test_build_softmax_ir_exports_checked_json():
    ir = build_softmax_ir(
        rows=128,
        cols=256,
        dtype="fp32",
        axis=1,
        input_name="logits",
        output_name="prob",
    )

    assert validate_cim_tile_ir(ir) == []

    payload = json.loads(to_json_text(ir))
    assert payload["kernel"] == "softmax"
    assert payload["mode"] == "ir_only"
    assert payload["target"] == "riscv_cim_mesh"
    assert payload["tensors"]["logits"] == {
        "shape": [128, 256],
        "dtype": "fp32",
        "layout": "row_major",
        "addr": "logits_base",
    }
    assert payload["tensors"]["prob"] == {
        "shape": [128, 256],
        "dtype": "fp32",
        "layout": "row_major",
        "addr": "prob_base",
    }
    assert payload["attrs"] == {"axis": 1}
    assert [op["op"] for op in payload["program"]] == [
        "row_max",
        "subtract",
        "exp",
        "row_sum",
        "divide",
        "store",
    ]


def test_checker_rejects_invalid_softmax_axis_and_shape():
    ir = build_softmax_ir(rows=128, cols=256)
    ir["attrs"]["axis"] = 0
    ir["tensors"]["output"]["shape"] = [128, 128]

    errors = validate_cim_tile_ir(ir)

    assert "softmax attrs.axis must be 1 for the first MVP" in errors
    assert "softmax input and output shapes must match" in errors


def test_build_matmul_softmax_graph_ir_keeps_matmul_and_softmax_as_ir_ops():
    ir = build_matmul_softmax_graph_ir(
        m=1024,
        n=1024,
        k=128,
        bm=64,
        bn=64,
        bk=64,
        mesh_w=4,
        mesh_h=5,
        dtype="fp32",
    )

    assert validate_cim_tile_ir(ir) == []

    payload = json.loads(to_json_text(ir))
    assert payload["kernel"] == "graph"
    assert [op["op"] for op in payload["ops"]] == ["matmul", "softmax"]
    assert payload["ops"][0]["inputs"] == ["A", "B"]
    assert payload["ops"][0]["outputs"] == ["S"]
    assert payload["ops"][1]["inputs"] == ["S"]
    assert payload["ops"][1]["outputs"] == ["P"]
    assert payload["ops"][1]["attrs"] == {"axis": 1}
