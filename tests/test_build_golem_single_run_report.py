import json
import subprocess
from pathlib import Path

from scripts.build_golem_single_run_report import build_golem_single_run_report


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _write_metric_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "metric,value\n" + "\n".join(f"{key},{value}" for key, value in rows) + "\n",
        encoding="utf-8",
    )


def _write_summary_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "metric,mean,median,p95,min,max,sum\n"
        + "\n".join(
            f"{key},{mean},{median},{p95},{min_},{max_},{sum_}"
            for key, mean, median, p95, min_, max_, sum_ in rows
        )
        + "\n",
        encoding="utf-8",
    )


def _write_artifacts(tmp_path):
    artifact_root = tmp_path / "artifacts"
    _write_json(
        artifact_root / "contracts" / "matmul_op_desc_resolved.json",
        {
            "m": 1024,
            "n": 1024,
            "k": 128,
            "block_m": 64,
            "block_n": 64,
            "block_k": 64,
            "dtype": "fp32",
            "layout": "row_major",
            "transpose_a": 0,
            "transpose_b": 0,
        },
    )
    _write_json(
        artifact_root / "contracts" / "matmul_env_mapping_v1.json",
        {"m": "GOLEM_MATMUL_M"},
    )
    event_plan = tmp_path / "gemm.golem_event_plan.json"
    _write_json(
        event_plan,
        {
            "mode": "golem_event_plan",
            "backend": "golem_sst",
            "stats": {
                "m_tiles": 16,
                "n_tiles": 16,
                "k_tiles": 2,
                "total_gemm_tasks": 256,
                "total_macro_tasks": 256,
                "active_worker_cores": 16,
                "total_gemm_cores": 20,
                "num_memory_nodes": 5,
            },
            "tasks": [],
        },
    )
    stats_dir = artifact_root / "stats" / "overlap0" / "run_1"
    _write_metric_csv(
        stats_dir / "execution_summary.csv",
        [
            ("total_cycles", "2889.187500"),
            ("worker_avg_total_cycles", "2889.187500"),
            ("worker_p95_total_cycles", "3191.000000"),
            ("worker_max_total_cycles", "3318.000000"),
            ("gemm_system_latency_cycles", "5911.000000"),
            ("array_utilization_pct", "70.884981"),
            ("system_array_utilization_pct", "34.647268"),
            ("compute_active_time", "2112.000000"),
            ("prefetch_wait_time", "759.187500"),
            ("writeback_wait_time", "16.000000"),
            ("control_other_time", "2.000000"),
        ],
    )
    _write_summary_csv(
        stats_dir / "dma_summary.csv",
        [("write_issue_count", "12", "16", "16", "0", "16", "256")],
    )
    _write_metric_csv(
        stats_dir / "noc_summary.csv",
        [
            ("router_count", "28"),
            ("simulated_time_ps", "234589000"),
            ("total_send_packets", "211506"),
            ("total_xbar_stalls", "27416"),
        ],
    )
    _write_metric_csv(
        stats_dir / "memory_summary.csv",
        [
            ("channel_count", "16"),
            ("total_reads_done", "23037"),
            ("mem_avg_read_latency_cycles", "19.265616"),
        ],
    )
    _write_metric_csv(
        stats_dir / "memory_queue_summary.csv",
        [
            ("queue_sample_count", "39703"),
            ("memory_queue_delay_avg_cycles", "1"),
            ("memory_queue_delay_p99_cycles", "1"),
        ],
    )
    _write_metric_csv(
        stats_dir / "submit_ready_causal_summary.csv",
        [
            ("causal_model_source", "residual"),
            ("trace_found", "1"),
            ("trace_samples_mat", "128"),
            ("trace_samples_vec", "128"),
        ],
    )
    log_path = artifact_root / "logs" / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "Simulation is complete, simulated time: 234.589 us\n",
        encoding="utf-8",
    )
    return artifact_root, event_plan, stats_dir, log_path


def test_build_golem_single_run_report_from_stats(tmp_path):
    artifact_root, event_plan, stats_dir, log_path = _write_artifacts(tmp_path)

    report = build_golem_single_run_report(
        artifact_root=artifact_root,
        event_plan_path=event_plan,
        stats_dir=stats_dir,
        log_path=log_path,
    )

    assert report["mode"] == "golem_single_run_stats_report"
    assert report["status"] == "ok"
    assert report["contract"]["m"] == 1024
    assert report["mapping"]["total_gemm_tasks"] == 256
    assert report["observed"]["simulation_complete"] is True
    assert report["observed"]["simulated_time"] == "234.589 us"
    assert report["stats"]["execution"]["total_cycles"] == 2889.1875
    assert report["stats"]["dma"]["write_issue_count"]["sum"] == 256
    assert report["derived"]["cycles_per_gemm_task"] == 2889.1875 / 256
    assert report["derived"]["cycles_per_macro_task"] == 2889.1875 / 256
    assert report["derived"]["compute_active_pct"] > 0
    assert report["model"]["status"] == "not_calibrated"
    assert report["warnings"] == []


def test_build_golem_single_run_report_warns_for_missing_optional_stats(tmp_path):
    artifact_root, event_plan, stats_dir, log_path = _write_artifacts(tmp_path)
    (stats_dir / "memory_queue_summary.csv").unlink()

    report = build_golem_single_run_report(
        artifact_root=artifact_root,
        event_plan_path=event_plan,
        stats_dir=stats_dir,
        log_path=log_path,
    )

    assert report["status"] == "ok_with_warnings"
    assert any("memory_queue_summary.csv" in warning for warning in report["warnings"])


def test_build_golem_single_run_report_cli_writes_json(tmp_path):
    artifact_root, event_plan, stats_dir, log_path = _write_artifacts(tmp_path)
    output = tmp_path / "report.json"

    subprocess.run(
        [
            "python",
            "scripts/build_golem_single_run_report.py",
            "--artifact-root",
            str(artifact_root),
            "--event-plan",
            str(event_plan),
            "--stats-dir",
            str(stats_dir),
            "--log",
            str(log_path),
            "--output",
            str(output),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["mode"] == "golem_single_run_stats_report"
    assert data["status"] == "ok"
