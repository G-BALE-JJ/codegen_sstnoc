import json
import subprocess
import sys

from tilelang_cim import build_gemm_ir, build_matmul_softmax_graph_ir
from tilelang_cim.golem_exporter import export_golem_sst_artifacts
from scripts.validate_golem_artifacts import validate_golem_artifacts


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


def test_validate_golem_artifacts_accepts_exporter_output(tmp_path):
    export_golem_sst_artifacts(_valid_golem_ir(), tmp_path)

    report = validate_golem_artifacts(tmp_path)

    assert report["ok"] is True
    assert report["mode"] == "golem_artifact_validation"
    assert report["artifact_root"] == str(tmp_path)
    assert report["env"]["GOLEM_MATMUL_M"] == "4096"
    assert report["resolved_contract"]["block_k"] == 64
    assert report["checks"]["required_files"] == "ok"
    assert report["checks"]["env_matches_resolved_contract"] == "ok"
    assert report["errors"] == []


def test_validate_golem_artifacts_reports_missing_contract_file(tmp_path):
    export_golem_sst_artifacts(_valid_golem_ir(), tmp_path)
    (tmp_path / "contracts" / "matmul_op_desc_resolved.json").unlink()

    report = validate_golem_artifacts(tmp_path)

    assert report["ok"] is False
    assert any("matmul_op_desc_resolved.json is missing" in error for error in report["errors"])


def test_validate_golem_artifacts_reports_env_resolved_mismatch(tmp_path):
    export_golem_sst_artifacts(_valid_golem_ir(), tmp_path)
    env_path = tmp_path / "golem_sst.env"
    env_text = env_path.read_text(encoding="utf-8").replace("GOLEM_MATMUL_M=4096", "GOLEM_MATMUL_M=2048")
    env_path.write_text(env_text, encoding="utf-8")

    report = validate_golem_artifacts(tmp_path)

    assert report["ok"] is False
    assert any("GOLEM_MATMUL_M=2048 does not match resolved m=4096" in error for error in report["errors"])


def test_validate_golem_artifacts_cli_writes_report_json(tmp_path):
    artifact_root = tmp_path / "artifacts"
    report_path = tmp_path / "validation.json"
    export_golem_sst_artifacts(_valid_golem_ir(), artifact_root)

    subprocess.run(
        [
            sys.executable,
            "scripts/validate_golem_artifacts.py",
            "--artifact-root",
            str(artifact_root),
            "--output",
            str(report_path),
        ],
        check=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["checks"]["env_mapping_contract"] == "ok"


def test_validate_golem_artifacts_accepts_matmul_softmax_graph_output(tmp_path):
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
    export_golem_sst_artifacts(ir, tmp_path)

    report = validate_golem_artifacts(tmp_path)

    assert report["ok"] is True
    assert report["graph_sequence"]["kind"] == "matmul_softmax"
    assert report["softmax_contract"]["op_name"] == "SoftmaxFwdOp"
    assert report["checks"]["graph_required_files"] == "ok"
    assert report["checks"]["softmax_contract_schema"] == "ok"
