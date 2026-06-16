import subprocess
from pathlib import Path


def test_run_golem_sst_smoke_sources_env_and_invokes_pipeline(tmp_path):
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    contracts_dir = artifact_root / "contracts"
    contracts_dir.mkdir()
    (contracts_dir / "matmul_op_desc_resolved.json").write_text("{}\n", encoding="utf-8")
    env_path = artifact_root / "golem_sst.env"
    env_path.write_text(
        "\n".join(
            [
                "export GOLEM_ARRAY_INPUT_SIZE=64",
                "export GOLEM_ARRAY_OUTPUT_SIZE=64",
                "export GOLEM_NUM_ARRAYS=64",
                "export GOLEM_MATMUL_M=4096",
                "export GOLEM_MATMUL_N=128",
                "export GOLEM_MATMUL_K=4096",
                'export GOLEM_GEMM_M="$GOLEM_MATMUL_M"',
                'export GOLEM_GEMM_N="$GOLEM_MATMUL_N"',
                'export GOLEM_GEMM_K="$GOLEM_MATMUL_K"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    hardware_tests_dir = tmp_path / "hw" / "tests"
    hardware_tests_dir.mkdir(parents=True)
    pipeline_path = hardware_tests_dir / "run_noc_dma_pipeline.sh"
    capture_path = tmp_path / "captured.env"
    pipeline_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'printf "GOLEM_ARTIFACT_ROOT=%s\\n" "$GOLEM_ARTIFACT_ROOT" > "$CAPTURE_PATH"',
                'printf "GOLEM_ARRAY_INPUT_SIZE=%s\\n" "$GOLEM_ARRAY_INPUT_SIZE" >> "$CAPTURE_PATH"',
                'printf "GOLEM_GEMM_M=%s\\n" "$GOLEM_GEMM_M" >> "$CAPTURE_PATH"',
                'printf "ARGS=%s\\n" "$*" >> "$CAPTURE_PATH"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pipeline_path.chmod(0o755)

    subprocess.run(
        [
            "bash",
            "examples/run_golem_sst_smoke.sh",
            "--artifact-root",
            str(artifact_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
            "--",
            "--log",
            "smoke.log",
        ],
        check=True,
        env={"CAPTURE_PATH": str(capture_path)},
    )

    captured = capture_path.read_text(encoding="utf-8")
    assert f"GOLEM_ARTIFACT_ROOT={artifact_root}" in captured
    assert "GOLEM_ARRAY_INPUT_SIZE=64" in captured
    assert "GOLEM_GEMM_M=4096" in captured
    assert "ARGS=--dry-run --log smoke.log" in captured


def test_run_golem_sst_smoke_rejects_missing_env(tmp_path):
    missing_root = tmp_path / "missing"
    result = subprocess.run(
        [
            "bash",
            "examples/run_golem_sst_smoke.sh",
            "--artifact-root",
            str(missing_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Missing Golem SST env file" in result.stderr
