import json
import subprocess
import sys

from tilelang_cim import GolemBackendConfig, build_gemm_ir, build_golem_event_plan
from tilelang_cim.golem_exporter import export_golem_sst_artifacts
from scripts.check_golem_mapping_consistency import check_golem_mapping_consistency


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


def _write_event_plan(path, ir=None, config=GolemBackendConfig()):
    plan = build_golem_event_plan(ir or _valid_golem_ir(), config)
    path.write_text(json.dumps(plan), encoding="utf-8")
    return plan


def test_check_golem_mapping_consistency_accepts_exporter_and_plan(tmp_path):
    artifact_root = tmp_path / "artifacts"
    event_plan_path = tmp_path / "golem_event_plan.json"
    export_golem_sst_artifacts(_valid_golem_ir(), artifact_root)
    _write_event_plan(event_plan_path)

    report = check_golem_mapping_consistency(artifact_root, event_plan_path)

    assert report["ok"] is True
    assert report["mode"] == "golem_mapping_consistency"
    assert report["resolved_contract"]["m"] == 4096
    assert report["event_plan_summary"]["m_tiles"] == 64
    assert report["event_plan_summary"]["n_tiles"] == 2
    assert report["event_plan_summary"]["k_tiles"] == 64
    assert report["checks"]["tile_counts_match_contract"] == "ok"
    assert report["checks"]["task_count_matches_tiles"] == "ok"
    assert report["checks"]["task_fields_in_range"] == "ok"
    assert report["errors"] == []


def test_check_golem_mapping_consistency_reports_contract_plan_tile_mismatch(tmp_path):
    artifact_root = tmp_path / "artifacts"
    event_plan_path = tmp_path / "golem_event_plan.json"
    export_golem_sst_artifacts(_valid_golem_ir(), artifact_root)
    wrong_ir = build_gemm_ir(
        m=2048,
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
    _write_event_plan(event_plan_path, wrong_ir)

    report = check_golem_mapping_consistency(artifact_root, event_plan_path)

    assert report["ok"] is False
    assert any("event plan m_tiles=32 does not match contract m/block_m=64" in error for error in report["errors"])


def test_check_golem_mapping_consistency_reports_out_of_range_task_fields(tmp_path):
    artifact_root = tmp_path / "artifacts"
    event_plan_path = tmp_path / "golem_event_plan.json"
    export_golem_sst_artifacts(_valid_golem_ir(), artifact_root)
    plan = _write_event_plan(event_plan_path)
    plan["tasks"][0]["worker_core"] = 999
    plan["tasks"][0]["data_node_idx"] = 999
    event_plan_path.write_text(json.dumps(plan), encoding="utf-8")

    report = check_golem_mapping_consistency(artifact_root, event_plan_path)

    assert report["ok"] is False
    assert any("task 0 worker_core=999 is outside [0, 20)" in error for error in report["errors"])
    assert any("task 0 data_node_idx=999 is outside [1, 5)" in error for error in report["errors"])


def test_check_golem_mapping_consistency_cli_writes_report_json(tmp_path):
    artifact_root = tmp_path / "artifacts"
    event_plan_path = tmp_path / "golem_event_plan.json"
    report_path = tmp_path / "mapping_report.json"
    export_golem_sst_artifacts(_valid_golem_ir(), artifact_root)
    _write_event_plan(event_plan_path)

    subprocess.run(
        [
            sys.executable,
            "scripts/check_golem_mapping_consistency.py",
            "--artifact-root",
            str(artifact_root),
            "--event-plan",
            str(event_plan_path),
            "--output",
            str(report_path),
        ],
        check=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["checks"]["base_addresses_present"] == "ok"
