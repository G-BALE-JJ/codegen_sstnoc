from tilelang_cim import build_gemm_ir, build_matmul_softmax_graph_ir
from tilelang_cim.golem_constraints import GolemBackendConfig, validate_cim_tile_ir_for_golem


def _valid_golem_ir():
    return build_gemm_ir(
        m=4096,
        n=128,
        k=4096,
        bm=64,
        bn=64,
        bk=64,
        mesh_w=4,
        mesh_h=5,
        a_dtype="fp32",
        b_dtype="fp32",
        c_dtype="fp32",
    )


def test_validate_cim_tile_ir_for_golem_accepts_default_fp32_gemm():
    errors = validate_cim_tile_ir_for_golem(_valid_golem_ir())

    assert errors == []


def test_validate_cim_tile_ir_for_golem_rejects_unsupported_dtype_layout_and_transpose():
    ir = _valid_golem_ir()
    ir["tensors"]["A"]["dtype"] = "int8"
    ir["tensors"]["B"]["layout"] = "column_major"
    ir["attrs"]["transpose_b"] = True

    errors = validate_cim_tile_ir_for_golem(ir)

    assert "Golem backend supports only int32/fp32 tensors for the first exporter" in errors
    assert "tensors.B.layout must be row_major" in errors
    assert "Golem backend does not support transpose_b for the first exporter" in errors


def test_validate_cim_tile_ir_for_golem_rejects_tile_shape_not_matching_backend():
    ir = _valid_golem_ir()
    ir["tile"]["BM"] = 128
    ir["tile"]["BK"] = 32
    ir["tile"]["BN"] = 128

    errors = validate_cim_tile_ir_for_golem(ir)

    assert "tile.BM must equal GOLEM_ARRAY_OUTPUT_SIZE (64)" in errors
    assert "tile.BK must equal GOLEM_ARRAY_INPUT_SIZE (64)" in errors
    assert "tile.BN must be <= GOLEM_NUM_ARRAYS (64)" in errors


def test_validate_cim_tile_ir_for_golem_accepts_custom_backend_config():
    ir = _valid_golem_ir()
    ir["tile"] = {"BM": 32, "BN": 16, "BK": 128}
    ir["tensors"]["A"]["shape"] = [4096, 4096]
    ir["tensors"]["B"]["shape"] = [4096, 128]
    ir["tensors"]["C"]["shape"] = [4096, 128]

    errors = validate_cim_tile_ir_for_golem(
        ir,
        GolemBackendConfig(array_input_size=128, array_output_size=32, num_arrays=16),
    )

    assert errors == []


def test_validate_cim_tile_ir_for_golem_accepts_single_n_tile_matmul_softmax_graph():
    ir = build_matmul_softmax_graph_ir(
        m=64,
        n=64,
        k=64,
        bm=64,
        bn=64,
        bk=64,
        mesh_w=1,
        mesh_h=1,
        dtype="fp32",
    )

    errors = validate_cim_tile_ir_for_golem(ir, GolemBackendConfig(total_groups=1, total_gemm_cores=1))

    assert errors == []


def test_validate_cim_tile_ir_for_golem_rejects_multi_n_tile_softmax_graph():
    ir = build_matmul_softmax_graph_ir(
        m=64,
        n=128,
        k=64,
        bm=64,
        bn=64,
        bk=64,
        mesh_w=1,
        mesh_h=2,
        dtype="fp32",
    )

    errors = validate_cim_tile_ir_for_golem(ir)

    assert (
        "Golem softmax CPU fallback requires graph N == matmul tile.BN; "
        "multi-N-tile row-wise softmax is not supported"
    ) in errors
