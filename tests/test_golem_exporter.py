import json
import subprocess
import sys

from tilelang_cim import build_gemm_ir
from tilelang_cim.golem_exporter import (
    build_golem_env_text,
    build_golem_matmul_op_desc,
    export_golem_sst_artifacts,
)
from tilelang_cim.golem_constraints import GolemBackendConfig


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


def test_build_golem_matmul_op_desc_from_cim_tile_ir():
    desc = build_golem_matmul_op_desc(_valid_golem_ir())

    assert desc == {
        "m": 4096,
        "n": 128,
        "k": 4096,
        "block_m": 64,
        "block_n": 64,
        "block_k": 64,
        "dtype": "fp32",
        "layout": "row_major",
        "transpose_a": 0,
        "transpose_b": 0,
    }


def test_build_golem_env_text_exports_matmul_and_legacy_gemm_vars():
    backend_config = GolemBackendConfig(array_input_size=64, array_output_size=64, num_arrays=64)
    env_text = build_golem_env_text(build_golem_matmul_op_desc(_valid_golem_ir()), backend_config)

    assert "export GOLEM_ARRAY_INPUT_SIZE=64" in env_text
    assert "export GOLEM_ARRAY_OUTPUT_SIZE=64" in env_text
    assert "export GOLEM_NUM_ARRAYS=64" in env_text
    assert "export GOLEM_MATMUL_M=4096" in env_text
    assert "export GOLEM_MATMUL_DTYPE=fp32" in env_text
    assert 'export GOLEM_GEMM_M="$GOLEM_MATMUL_M"' in env_text
    assert env_text.endswith("\n")


def test_export_golem_sst_artifacts_writes_env_and_contracts(tmp_path):
    export_golem_sst_artifacts(_valid_golem_ir(), tmp_path)

    env_path = tmp_path / "golem_sst.env"
    resolved_path = tmp_path / "contracts" / "matmul_op_desc_resolved.json"
    mapping_path = tmp_path / "contracts" / "matmul_env_mapping_v1.json"

    assert env_path.exists()
    assert resolved_path.exists()
    assert mapping_path.exists()

    resolved = json.loads(resolved_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

    assert resolved["m"] == 4096
    assert resolved["dtype"] == "fp32"
    assert mapping["m"] == "GOLEM_MATMUL_M"
    assert mapping["transpose_b"] == "GOLEM_MATMUL_TRANSPOSE_B"


def test_export_golem_sst_cli_accepts_cim_tileir_json(tmp_path):
    ir_path = tmp_path / "gemm.cimtile.json"
    artifact_root = tmp_path / "artifacts"
    ir_path.write_text(json.dumps(_valid_golem_ir()), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            "examples/export_golem_sst.py",
            str(ir_path),
            "--input-format",
            "cim-tileir-json",
            "--artifact-root",
            str(artifact_root),
        ],
        check=True,
    )

    resolved = json.loads((artifact_root / "contracts" / "matmul_op_desc_resolved.json").read_text(encoding="utf-8"))
    assert resolved["block_k"] == 64
    assert (artifact_root / "golem_sst.env").exists()
