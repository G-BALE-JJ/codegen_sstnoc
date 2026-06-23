import json
import subprocess
from pathlib import Path


def _write_fake_softmax_pipeline(tmp_path: Path) -> tuple[Path, Path]:
    hardware_tests_dir = tmp_path / "hw" / "tests"
    pipeline_dir = hardware_tests_dir / "small" / "mvm_noc_softmax_cpu"
    pipeline_dir.mkdir(parents=True)
    pipeline_path = pipeline_dir / "run_noc_dma_softmax_pipeline.sh"
    capture_path = tmp_path / "softmax_pipeline_args.txt"
    pipeline_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "%s\\n" "$*" > "$CAPTURE_PATH"',
                'printf "GOLEM_ARTIFACT_ROOT=%s\\n" "$GOLEM_ARTIFACT_ROOT" >> "$CAPTURE_PATH"',
                'printf "GOLEM_GRAPH_KIND=%s\\n" "${GOLEM_GRAPH_KIND:-}" >> "$CAPTURE_PATH"',
                'printf "GOLEM_SOFTMAX_ENABLE=%s\\n" "${GOLEM_SOFTMAX_ENABLE:-}" >> "$CAPTURE_PATH"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pipeline_path.chmod(0o755)
    return hardware_tests_dir, capture_path


def test_tilelang_softmax_golem_e2e_dry_run_generates_graph_artifacts(tmp_path):
    run_root = tmp_path / "softmax_e2e"
    hardware_tests_dir, capture_path = _write_fake_softmax_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_tilelang_softmax_golem_e2e.sh",
            "--tilelang-source",
            "tests/fixtures/tileops_like_matmul_softmax_source.py",
            "--run-root",
            str(run_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
        ],
        check=True,
        env={
            "CAPTURE_PATH": str(capture_path),
            "PATH": "/usr/bin:/bin",
        },
    )

    artifact_root = run_root / "golem_softmax_artifacts"
    cim_tileir = json.loads((run_root / "tilelang_matmul_softmax.cimtile.json").read_text(encoding="utf-8"))
    validation = json.loads((run_root / "golem_softmax_artifact_validation.json").read_text(encoding="utf-8"))
    captured = capture_path.read_text(encoding="utf-8")

    assert cim_tileir["kernel"] == "graph"
    assert [op["op"] for op in cim_tileir["ops"]] == ["matmul", "softmax"]
    assert (artifact_root / "contracts" / "graph_sequence_v1.json").exists()
    assert (artifact_root / "contracts" / "softmax_op_desc_resolved.json").exists()
    assert validation["ok"] is True
    assert captured.startswith("--groups 1 --num-cores 1 --gemm-cores 1")
    assert "--verify-softmax --softmax-reference probability --dry-run --log tilelang_softmax_golem_smoke.log" in captured
    assert "GOLEM_GRAPH_KIND=matmul_softmax" in captured
    assert "GOLEM_SOFTMAX_ENABLE=1" in captured
