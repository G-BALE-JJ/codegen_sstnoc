import pytest
import json
import subprocess

from tests.fixtures.tileops_like_gemm_fixture import TILEOPS_LIKE_GEMM_SOURCE
from tests.fixtures.tilelang_gemm_fixture import tilelang_gemm_fixture
from tilelang_cim import (
    extract_gemm_ir_from_source,
    extract_gemm_ir_from_tilelang,
    extract_gemm_ir_from_tir,
    validate_cim_tile_ir,
)
from tilelang_cim.extractor import _tir_op_name
from tilelang_cim.golem_exporter import export_golem_sst_artifacts


TILELANG_GEMM_SOURCE = """
import tilelang.language as T

@T.prim_func
def gemm(
    a: T.Tensor((256, 64), "int8"),
    b: T.Tensor((64, 128), "int8"),
    c: T.Tensor((256, 128), "int32"),
) -> None:
    with T.Kernel(T.ceildiv(128, 64), T.ceildiv(256, 64), threads=128) as (bx, by):
        a_shared = T.alloc_shared((64, 32), "int8")
        b_shared = T.alloc_shared((32, 64), "int8")
        c_local = T.alloc_fragment((64, 64), "int32")

        T.clear(c_local)

        for ko in T.Pipelined(T.ceildiv(64, 32), num_stages=2):
            T.copy(a[by * 64, ko * 32], a_shared)
            T.copy(b[ko * 32, bx * 64], b_shared)
            T.gemm(a_shared, b_shared, c_local)

        T.copy(c_local, c[by * 64, bx * 64])
"""


def test_extract_gemm_ir_from_tilelang_source():
    ir = extract_gemm_ir_from_source(TILELANG_GEMM_SOURCE, mesh_w=4, mesh_h=2)

    assert ir["kernel"] == "gemm"
    assert ir["mesh"] == {"w": 4, "h": 2}
    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 32}
    assert ir["tensors"]["A"]["shape"] == [256, 64]
    assert ir["tensors"]["B"]["shape"] == [64, 128]
    assert ir["tensors"]["C"]["shape"] == [256, 128]
    assert ir["tensors"]["A"]["dtype"] == "int8"
    assert ir["tensors"]["B"]["dtype"] == "int8"
    assert ir["tensors"]["C"]["dtype"] == "int32"
    assert ir["program"][1]["count"] == 2
    assert ir["program"][1]["pipeline_stages"] == 2


def test_extract_gemm_ir_does_not_depend_on_abc_argument_names():
    ir = extract_gemm_ir_from_source(
        """
import tilelang.language as T

@T.prim_func
def gemm(
    lhs: T.Tensor((256, 64), "int8"),
    rhs: T.Tensor((64, 128), "int8"),
    out: T.Tensor((256, 128), "int32"),
) -> None:
    with T.Kernel(T.ceildiv(128, 64), T.ceildiv(256, 64), threads=128) as (bx, by):
        lhs_shared = T.alloc_shared((64, 32), "int8")
        rhs_shared = T.alloc_shared((32, 64), "int8")
        out_local = T.alloc_fragment((64, 64), "int32")

        T.clear(out_local)

        for ko in T.Pipelined(T.ceildiv(64, 32), num_stages=2):
            T.copy(lhs[by * 64, ko * 32], lhs_shared)
            T.copy(rhs[ko * 32, bx * 64], rhs_shared)
            T.gemm(lhs_shared, rhs_shared, out_local)

        T.copy(out_local, out[by * 64, bx * 64])
"""
    )

    assert ir["tensors"]["A"]["shape"] == [256, 64]
    assert ir["tensors"]["B"]["shape"] == [64, 128]
    assert ir["tensors"]["C"]["shape"] == [256, 128]
    assert ir["tensors"]["A"]["dtype"] == "int8"
    assert ir["tensors"]["B"]["dtype"] == "int8"
    assert ir["tensors"]["C"]["dtype"] == "int32"


def test_extract_gemm_ir_from_python_function_source():
    ir = extract_gemm_ir_from_tilelang(tilelang_gemm_fixture(), mesh_w=4, mesh_h=2)

    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert ir["program"][1]["count"] == 2
    assert ir["tensors"]["A"]["shape"] == [1024, 128]
    assert ir["tensors"]["B"]["shape"] == [128, 1024]
    assert ir["tensors"]["C"]["shape"] == [1024, 1024]


def test_extract_gemm_ir_from_tir_prim_func_without_script_text():
    prim_func = tilelang_gemm_fixture()

    ir = extract_gemm_ir_from_tir(prim_func, mesh_w=4, mesh_h=2)

    assert ir["mesh"] == {"w": 4, "h": 2}
    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert ir["program"][1]["count"] == 2
    assert ir["program"][1]["pipeline_stages"] == 2
    assert ir["tensors"]["A"]["shape"] == [1024, 128]
    assert ir["tensors"]["B"]["shape"] == [128, 1024]
    assert ir["tensors"]["C"]["shape"] == [1024, 1024]
    assert ir["tensors"]["A"]["dtype"] == "float32"
    assert validate_cim_tile_ir(ir) == []


def test_extract_tilelang_tir_gemm_example_writes_valid_json(tmp_path):
    output = tmp_path / "tilelang_tir_gemm.cimtile.json"

    subprocess.run(
        [
            "python",
            "examples/extract_tilelang_tir_gemm.py",
            "tests/fixtures/tilelang_gemm_fixture.py",
            "--output",
            str(output),
            "--mesh-w",
            "4",
            "--mesh-h",
            "5",
        ],
        check=True,
    )

    ir = json.loads(output.read_text(encoding="utf-8"))
    assert ir["mesh"] == {"w": 4, "h": 5}
    assert ir["tensors"]["A"]["shape"] == [1024, 128]
    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert validate_cim_tile_ir(ir) == []


def test_tir_op_name_accepts_tvm_op_string_variants():
    class OpWithName:
        name = "tl.tileop.gemm"

    class LegacyStringOp:
        def __str__(self):
            return "Op(tl.tileop.gemm)"

    class FfiStringOp:
        def __str__(self):
            return 'ir.Op(span=None, name="tl.tileop.gemm", num_inputs=5)'

    assert _tir_op_name(OpWithName()) == "tl.tileop.gemm"
    assert _tir_op_name(LegacyStringOp()) == "tl.tileop.gemm"
    assert _tir_op_name(FfiStringOp()) == "tl.tileop.gemm"


def test_extract_tilelang_prefers_tir_visitor_when_script_is_unavailable():
    class PrimFuncWithoutScriptText:
        def __init__(self, prim_func):
            self.body = prim_func.body
            self.buffer_map = prim_func.buffer_map

        def script(self):
            raise AssertionError("script() should not be used for TIR-like inputs")

    ir = extract_gemm_ir_from_tilelang(PrimFuncWithoutScriptText(tilelang_gemm_fixture()), mesh_w=4, mesh_h=2)

    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert ir["program"][1]["pipeline_stages"] == 2
    assert ir["tensors"]["C"]["shape"] == [1024, 1024]


def test_extract_tileops_like_gemm_fixture_exports_golem_artifacts(tmp_path):
    ir = extract_gemm_ir_from_source(TILEOPS_LIKE_GEMM_SOURCE, mesh_w=4, mesh_h=5)

    assert validate_cim_tile_ir(ir) == []
    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert ir["tensors"]["A"]["shape"] == [1024, 128]
    assert ir["tensors"]["B"]["shape"] == [128, 1024]
    assert ir["tensors"]["C"]["shape"] == [1024, 1024]
    assert ir["tensors"]["A"]["dtype"] == "float32"
    assert ir["program"][1]["pipeline_stages"] == 2

    paths = export_golem_sst_artifacts(ir, tmp_path)

    assert paths["env"].exists()
    assert paths["resolved_contract"].exists()
    assert paths["env_mapping"].exists()


def test_extract_gemm_ir_from_match_buffer_without_dtype_defaults_to_float32():
    ir = extract_gemm_ir_from_source(
        """
from tvm.script import tir as T

@T.prim_func
def gemm(a_handle: T.handle, b_handle: T.handle, c_handle: T.handle):
    a = T.match_buffer(a_handle, (1024, 128), strides=(128, 1))
    b = T.match_buffer(b_handle, (128, 1024), strides=(1024, 1))
    c = T.match_buffer(c_handle, (1024, 1024), strides=(1024, 1))
    a_shared = T.alloc_buffer((64, 64), scope="shared.dyn")
    b_shared = T.alloc_buffer((64, 64), scope="shared.dyn")
    c_local = T.alloc_buffer((64, 64), scope="local.fragment")
    for ko in T.serial(2, annotations={"num_stages": 2}):
        T.gemm(a_shared, b_shared, c_local)
"""
    )

    assert ir["tensors"]["A"]["shape"] == [1024, 128]
    assert ir["tensors"]["A"]["dtype"] == "float32"


def test_extract_gemm_ir_defaults_pipeline_stages_to_one():
    ir = extract_gemm_ir_from_source(
        """
import tilelang.language as T

@T.prim_func
def gemm(
    lhs: T.Tensor((128, 64), "float32"),
    rhs: T.Tensor((64, 128), "float32"),
    out: T.Tensor((128, 128), "float32"),
) -> None:
    with T.Kernel(T.ceildiv(128, 64), T.ceildiv(128, 64), threads=128) as (bx, by):
        lhs_shared = T.alloc_shared((64, 64), "float32")
        rhs_shared = T.alloc_shared((64, 64), "float32")
        out_local = T.alloc_fragment((64, 64), "float32")

        T.clear(out_local)

        for ko in T.Pipelined(T.ceildiv(64, 64)):
            T.copy(lhs[by * 64, ko * 64], lhs_shared)
            T.copy(rhs[ko * 64, bx * 64], rhs_shared)
            T.gemm(lhs_shared, rhs_shared, out_local)

        T.copy(out_local, out[by * 64, bx * 64])
"""
    )

    assert ir["program"][1]["pipeline_stages"] == 1
    assert ir["tensors"]["A"]["dtype"] == "float32"
    assert ir["tensors"]["B"]["dtype"] == "float32"
    assert ir["tensors"]["C"]["dtype"] == "float32"


def test_extract_gemm_ir_rejects_dynamic_tensor_shapes_with_clear_error():
    with pytest.raises(ValueError, match="unsupported dynamic shape"):
        extract_gemm_ir_from_source(
            """
import tilelang.language as T

@T.prim_func
def gemm(
    lhs: T.Tensor((M, K), "float32"),
    rhs: T.Tensor((K, N), "float32"),
    out: T.Tensor((M, N), "float32"),
) -> None:
    with T.Kernel(T.ceildiv(N, 64), T.ceildiv(M, 64), threads=128) as (bx, by):
        lhs_shared = T.alloc_shared((64, 64), "float32")
        rhs_shared = T.alloc_shared((64, 64), "float32")
        out_local = T.alloc_fragment((64, 64), "float32")

        T.clear(out_local)

        for ko in T.Pipelined(T.ceildiv(K, 64)):
            T.gemm(lhs_shared, rhs_shared, out_local)
"""
        )


def test_extract_gemm_ir_rejects_missing_tilelang_gemm():
    with pytest.raises(ValueError, match="T.gemm call was not found"):
        extract_gemm_ir_from_source(
            """
import tilelang.language as T

@T.prim_func
def copy_only(a: T.Tensor((16, 16), "int8")) -> None:
    with T.Kernel(1, threads=32) as bx:
        T.copy(a, a)
"""
        )
