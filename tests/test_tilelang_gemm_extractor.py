import pytest

from tests.fixtures.tilelang_gemm_fixture import tilelang_gemm_fixture
from tilelang_cim import extract_gemm_ir_from_source, extract_gemm_ir_from_tilelang


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


def test_extract_gemm_ir_from_python_function_source():
    ir = extract_gemm_ir_from_tilelang(tilelang_gemm_fixture(), mesh_w=4, mesh_h=2)

    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert ir["program"][1]["count"] == 2
    assert ir["tensors"]["A"]["shape"] == [1024, 128]
    assert ir["tensors"]["B"]["shape"] == [128, 1024]
    assert ir["tensors"]["C"]["shape"] == [1024, 1024]


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
