import json
import subprocess
from pathlib import Path


def _write_fake_toolchain(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ["sst", "riscv64-linux-musl-g++"]:
        tool_path = bin_dir / name
        tool_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        tool_path.chmod(0o755)
    return bin_dir


def _write_fake_pipeline(tmp_path):
    hardware_tests_dir = tmp_path / "hw" / "tests"
    hardware_tests_dir.mkdir(parents=True)
    pipeline_path = hardware_tests_dir / "run_noc_dma_pipeline.sh"
    capture_path = tmp_path / "pipeline_args.txt"
    pipeline_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "$*" > "$CAPTURE_PATH"',
                'mkdir -p "$GOLEM_ARTIFACT_ROOT/logs"',
                'mkdir -p "$GOLEM_ARTIFACT_ROOT/stats/overlap0/run_fake"',
                'printf "Simulation is complete, simulated time: 1.0 us\\n" > "$GOLEM_ARTIFACT_ROOT/logs/fake_execute.log"',
                'stats_dir="$GOLEM_ARTIFACT_ROOT/stats/overlap0/run_fake"',
                'printf "metric,value\\ntotal_cycles,10\\narray_utilization_pct,50\\nsystem_array_utilization_pct,40\\ncompute_active_time,8\\nprefetch_wait_time,2\\nwriteback_wait_time,0\\ncontrol_other_time,0\\n" > "$stats_dir/execution_summary.csv"',
                'printf "metric,value\\npackets,1\\n" > "$stats_dir/noc_summary.csv"',
                'printf "metric,value\\nreads,1\\n" > "$stats_dir/memory_summary.csv"',
                'printf "metric,value\\nqueue_depth,0\\n" > "$stats_dir/memory_queue_summary.csv"',
                'printf "metric,value\\nready,1\\n" > "$stats_dir/submit_ready_causal_summary.csv"',
                'printf "metric,total\\nloads,1\\n" > "$stats_dir/dma_summary.csv"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pipeline_path.chmod(0o755)
    return hardware_tests_dir, capture_path


def test_tilelang_golem_e2e_dry_run_generates_checked_artifacts(tmp_path):
    run_root = tmp_path / "e2e"
    hardware_tests_dir, capture_path = _write_fake_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_tilelang_golem_e2e.sh",
            "--tilelang-source",
            "tests/fixtures/tilelang_gemm_fixture.py",
            "--run-root",
            str(run_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
        ],
        check=True,
        env={
            "CAPTURE_PATH": str(capture_path),
            "PATH": f"{_write_fake_toolchain(tmp_path)}:/usr/bin:/bin",
        },
    )

    artifact_root = run_root / "golem_codegen_artifacts"
    cim_tileir = json.loads((run_root / "tilelang_gemm.cimtile.json").read_text(encoding="utf-8"))
    validation = json.loads((run_root / "golem_artifact_validation.json").read_text(encoding="utf-8"))
    consistency = json.loads((run_root / "golem_mapping_consistency.json").read_text(encoding="utf-8"))

    assert cim_tileir["tensors"]["A"]["shape"] == [1024, 128]
    assert cim_tileir["tensors"]["B"]["shape"] == [128, 1024]
    assert cim_tileir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert (artifact_root / "golem_sst.env").exists()
    assert (run_root / "gemm.golem_event_plan.json").exists()
    assert validation["ok"] is True
    assert consistency["ok"] is True
    assert capture_path.read_text(encoding="utf-8").strip().startswith("--dry-run")
    assert not (run_root / "golem_single_run_report.json").exists()


def test_tilelang_golem_e2e_tir_frontend_generates_checked_artifacts(tmp_path):
    run_root = tmp_path / "e2e"
    hardware_tests_dir, capture_path = _write_fake_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_tilelang_golem_e2e.sh",
            "--frontend-mode",
            "tir",
            "--tilelang-source",
            "tests/fixtures/tilelang_gemm_fixture.py",
            "--run-root",
            str(run_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
        ],
        check=True,
        env={
            "CAPTURE_PATH": str(capture_path),
            "PATH": f"{_write_fake_toolchain(tmp_path)}:/usr/bin:/bin",
        },
    )

    artifact_root = run_root / "golem_codegen_artifacts"
    cim_tileir = json.loads((run_root / "tilelang_gemm.cimtile.json").read_text(encoding="utf-8"))
    validation = json.loads((run_root / "golem_artifact_validation.json").read_text(encoding="utf-8"))
    consistency = json.loads((run_root / "golem_mapping_consistency.json").read_text(encoding="utf-8"))

    assert cim_tileir["tensors"]["A"]["shape"] == [1024, 128]
    assert cim_tileir["tensors"]["B"]["shape"] == [128, 1024]
    assert cim_tileir["tensors"]["C"]["shape"] == [1024, 1024]
    assert cim_tileir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert cim_tileir["program"][1]["pipeline_stages"] == 2
    assert (artifact_root / "golem_sst.env").exists()
    assert validation["ok"] is True
    assert consistency["ok"] is True
    assert capture_path.read_text(encoding="utf-8").strip().startswith("--dry-run")


def test_tilelang_golem_e2e_execute_builds_single_run_report(tmp_path):
    run_root = tmp_path / "e2e"
    hardware_tests_dir, capture_path = _write_fake_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_tilelang_golem_e2e.sh",
            "--tilelang-source",
            "tests/fixtures/tilelang_gemm_fixture.py",
            "--run-root",
            str(run_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
            "--execute",
        ],
        check=True,
        env={
            "CAPTURE_PATH": str(capture_path),
            "PATH": f"{_write_fake_toolchain(tmp_path)}:/usr/bin:/bin",
        },
    )

    report = json.loads((run_root / "golem_single_run_report.json").read_text(encoding="utf-8"))
    assert "--dry-run" not in capture_path.read_text(encoding="utf-8")
    assert report["mode"] == "golem_single_run_stats_report"
    assert report["observed"]["simulation_complete"] is True
    assert report["stats_dir"].endswith("stats/overlap0/run_fake")
