import subprocess
from pathlib import Path

from tilelang_cim import GolemBackendConfig, build_matmul_softmax_graph_ir, export_golem_sst_artifacts


def _write_graph_artifacts(artifact_root: Path) -> None:
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
    export_golem_sst_artifacts(
        ir,
        artifact_root,
        GolemBackendConfig(
            array_input_size=64,
            array_output_size=64,
            num_arrays=64,
        ),
    )


def _write_fake_softmax_pipeline(tmp_path: Path) -> tuple[Path, Path]:
    hardware_tests_dir = tmp_path / "hw" / "tests"
    pipeline_dir = hardware_tests_dir / "small" / "mvm_noc_softmax_cpu"
    pipeline_dir.mkdir(parents=True)
    pipeline_path = pipeline_dir / "run_noc_dma_softmax_pipeline.sh"
    capture_path = tmp_path / "softmax_pipeline_capture.txt"
    pipeline_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "GOLEM_ARTIFACT_ROOT=%s\\n" "$GOLEM_ARTIFACT_ROOT" > "$CAPTURE_PATH"',
                'printf "GOLEM_SOFTMAX_ENABLE=%s\\n" "${GOLEM_SOFTMAX_ENABLE:-}" >> "$CAPTURE_PATH"',
                'printf "GOLEM_GRAPH_KIND=%s\\n" "${GOLEM_GRAPH_KIND:-}" >> "$CAPTURE_PATH"',
                'printf "GOLEM_GEMM_M=%s\\n" "$GOLEM_GEMM_M" >> "$CAPTURE_PATH"',
                'printf "GOLEM_GEMM_BLOCK_N=%s\\n" "$GOLEM_GEMM_BLOCK_N" >> "$CAPTURE_PATH"',
                'printf "ARGS=%s\\n" "$*" >> "$CAPTURE_PATH"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pipeline_path.chmod(0o755)
    return hardware_tests_dir, capture_path


def test_run_golem_softmax_sst_smoke_invokes_softmax_pipeline_with_contract_args(tmp_path):
    artifact_root = tmp_path / "artifacts"
    _write_graph_artifacts(artifact_root)
    hardware_tests_dir, capture_path = _write_fake_softmax_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_golem_softmax_sst_smoke.sh",
            "--artifact-root",
            str(artifact_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
            "--",
            "--log",
            "softmax_smoke.log",
        ],
        check=True,
        env={
            "CAPTURE_PATH": str(capture_path),
            "PATH": "/usr/bin:/bin",
        },
    )

    captured = capture_path.read_text(encoding="utf-8")
    assert f"GOLEM_ARTIFACT_ROOT={artifact_root}" in captured
    assert "GOLEM_SOFTMAX_ENABLE=1" in captured
    assert "GOLEM_GRAPH_KIND=matmul_softmax" in captured
    assert "GOLEM_GEMM_M=64" in captured
    assert "GOLEM_GEMM_BLOCK_N=64" in captured
    assert (
        "ARGS=--groups 1 --num-cores 1 --gemm-cores 1 "
        "--num-mem-nodes 2 --mesh-dim-x 1 "
        "--num-arrays 64 --array-in 64 --array-out 64 "
        "--gemm-m 64 --gemm-n 64 --gemm-k 64 "
        "--gemm-block-m 64 --gemm-block-n 64 --gemm-block-k 64 "
        "--group-manager-enable 0 --ctrl-link-enable 0 "
        "--verify-softmax --softmax-reference probability "
        "--dry-run --log softmax_smoke.log"
    ) in captured


def test_run_golem_softmax_sst_smoke_execute_omits_dry_run(tmp_path):
    artifact_root = tmp_path / "artifacts"
    _write_graph_artifacts(artifact_root)
    hardware_tests_dir, capture_path = _write_fake_softmax_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_golem_softmax_sst_smoke.sh",
            "--artifact-root",
            str(artifact_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
            "--execute",
        ],
        check=True,
        env={
            "CAPTURE_PATH": str(capture_path),
            "PATH": "/usr/bin:/bin",
        },
    )

    captured = capture_path.read_text(encoding="utf-8")
    assert "--verify-softmax" in captured
    assert "--softmax-reference probability" in captured
    assert "--dry-run" not in captured


def test_run_golem_softmax_sst_smoke_rejects_missing_graph_artifacts(tmp_path):
    artifact_root = tmp_path / "artifacts"
    _write_graph_artifacts(artifact_root)
    (artifact_root / "contracts" / "graph_sequence_v1.json").unlink()

    result = subprocess.run(
        [
            "/bin/bash",
            "examples/run_golem_softmax_sst_smoke.sh",
            "--artifact-root",
            str(artifact_root),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )

    assert result.returncode != 0
    assert "Missing Golem softmax graph artifact" in result.stderr
    assert "graph_sequence_v1.json" in result.stderr
