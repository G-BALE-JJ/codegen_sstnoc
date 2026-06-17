import subprocess
from pathlib import Path


DEFAULT_ARTIFACT_ROOT = Path("/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts")


def _write_minimal_artifacts(artifact_root):
    artifact_root.mkdir(parents=True, exist_ok=True)
    contracts_dir = artifact_root / "contracts"
    contracts_dir.mkdir(exist_ok=True)
    (contracts_dir / "matmul_op_desc_resolved.json").write_text("{}\n", encoding="utf-8")
    env_path = artifact_root / "golem_sst.env"
    env_path.write_text(
        "\n".join(
            [
                "export GOLEM_ARRAY_INPUT_SIZE=64",
                "export GOLEM_ARRAY_OUTPUT_SIZE=64",
                "export GOLEM_NUM_ARRAYS=64",
                "export GOLEM_MATMUL_M=1024",
                "export GOLEM_MATMUL_N=1024",
                "export GOLEM_MATMUL_K=128",
                'export GOLEM_GEMM_M="$GOLEM_MATMUL_M"',
                'export GOLEM_GEMM_N="$GOLEM_MATMUL_N"',
                'export GOLEM_GEMM_K="$GOLEM_MATMUL_K"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact_root


def _write_fake_pipeline(tmp_path):
    hardware_tests_dir = tmp_path / "hw" / "tests"
    hardware_tests_dir.mkdir(parents=True)
    pipeline_path = hardware_tests_dir / "run_noc_dma_pipeline.sh"
    capture_path = tmp_path / "captured.env"
    pipeline_path.write_text(
        "\n".join(
            [
                "#!/bin/bash",
                "set -euo pipefail",
                'printf "GOLEM_ARTIFACT_ROOT=%s\\n" "$GOLEM_ARTIFACT_ROOT" > "$CAPTURE_PATH"',
                'printf "GOLEM_ARRAY_INPUT_SIZE=%s\\n" "$GOLEM_ARRAY_INPUT_SIZE" >> "$CAPTURE_PATH"',
                'printf "GOLEM_GEMM_M=%s\\n" "$GOLEM_GEMM_M" >> "$CAPTURE_PATH"',
                'printf "GOLEM_SMOKE_ENV_BOOTSTRAPPED=%s\\n" "${GOLEM_SMOKE_ENV_BOOTSTRAPPED:-0}" >> "$CAPTURE_PATH"',
                'printf "LD_LIBRARY_PATH=%s\\n" "${LD_LIBRARY_PATH:-}" >> "$CAPTURE_PATH"',
                'printf "ARGS=%s\\n" "$*" >> "$CAPTURE_PATH"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pipeline_path.chmod(0o755)
    return hardware_tests_dir, capture_path


def _write_fake_toolchain(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ["sst", "riscv64-linux-musl-g++"]:
        tool_path = bin_dir / name
        tool_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        tool_path.chmod(0o755)
    return bin_dir


def test_run_golem_sst_smoke_sources_env_and_invokes_pipeline(tmp_path):
    artifact_root = tmp_path / "artifacts"
    _write_minimal_artifacts(artifact_root)
    hardware_tests_dir, capture_path = _write_fake_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
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
        env={
            "CAPTURE_PATH": str(capture_path),
            "PATH": f"{_write_fake_toolchain(tmp_path)}:/usr/bin:/bin",
        },
    )

    captured = capture_path.read_text(encoding="utf-8")
    assert f"GOLEM_ARTIFACT_ROOT={artifact_root}" in captured
    assert "GOLEM_ARRAY_INPUT_SIZE=64" in captured
    assert "GOLEM_GEMM_M=1024" in captured
    assert "ARGS=--dry-run --log smoke.log" in captured


def test_run_golem_sst_smoke_defaults_artifact_root_to_data4_tmp(tmp_path):
    _write_minimal_artifacts(DEFAULT_ARTIFACT_ROOT)
    hardware_tests_dir, capture_path = _write_fake_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_golem_sst_smoke.sh",
            "--hardware-tests-dir",
            str(hardware_tests_dir),
            "--",
            "--log",
            "smoke.log",
        ],
        check=True,
        env={
            "CAPTURE_PATH": str(capture_path),
            "PATH": f"{_write_fake_toolchain(tmp_path)}:/usr/bin:/bin",
        },
    )

    captured = capture_path.read_text(encoding="utf-8")
    assert f"GOLEM_ARTIFACT_ROOT={DEFAULT_ARTIFACT_ROOT}" in captured
    assert "ARGS=--dry-run --log smoke.log" in captured


def test_run_golem_sst_smoke_rejects_missing_env(tmp_path):
    missing_root = tmp_path / "missing"
    result = subprocess.run(
        [
            "/bin/bash",
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


def test_run_golem_sst_smoke_can_reexec_with_user_shell_env(tmp_path):
    artifact_root = tmp_path / "artifacts"
    _write_minimal_artifacts(artifact_root)
    hardware_tests_dir, capture_path = _write_fake_pipeline(tmp_path)

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    real_bash = fake_bin / "bash"
    fake_shell_log = tmp_path / "fake-shell.log"
    real_bash.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'printf "argc=%s\\n" "$#" > "$FAKE_SHELL_LOG"',
                'i=1',
                'for arg in "$@"; do',
                '  printf "arg%s=%s\\n" "$i" "$arg" >> "$FAKE_SHELL_LOG"',
                '  i=$((i + 1))',
                'done',
                "export GOLEM_SMOKE_ENV_BOOTSTRAPPED=1",
                'exec /bin/bash "$5" "${@:6}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    real_bash.chmod(0o755)

    env = {
        "CAPTURE_PATH": str(capture_path),
        "FAKE_SHELL_LOG": str(fake_shell_log),
        "GOLEM_SMOKE_BASH": str(real_bash),
        "PATH": f"{_write_fake_toolchain(tmp_path)}:/usr/bin:/bin",
    }
    subprocess.run(
        [
            "/bin/bash",
            "examples/run_golem_sst_smoke.sh",
            "--use-user-shell-env",
            "--artifact-root",
            str(artifact_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
            "--",
            "--log",
            "smoke.log",
        ],
        check=True,
        env=env,
    )

    shell_log = fake_shell_log.read_text(encoding="utf-8")
    assert "arg1=-i" in shell_log
    assert "arg2=-c" in shell_log
    captured = capture_path.read_text(encoding="utf-8")
    assert "GOLEM_SMOKE_ENV_BOOTSTRAPPED=1" in captured
    assert "ARGS=--dry-run --log smoke.log" in captured


def test_run_golem_sst_smoke_reports_missing_runtime_tools(tmp_path):
    artifact_root = tmp_path / "artifacts"
    _write_minimal_artifacts(artifact_root)
    hardware_tests_dir, _ = _write_fake_pipeline(tmp_path)

    result = subprocess.run(
        [
            "/bin/bash",
            "examples/run_golem_sst_smoke.sh",
            "--artifact-root",
            str(artifact_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )

    assert result.returncode != 0
    assert "Missing required runtime tool" in result.stderr
    assert "--use-user-shell-env" in result.stderr


def test_run_golem_sst_smoke_adds_conda_lib_to_library_path(tmp_path):
    artifact_root = tmp_path / "artifacts"
    _write_minimal_artifacts(artifact_root)
    hardware_tests_dir, capture_path = _write_fake_pipeline(tmp_path)
    conda_prefix = tmp_path / "conda"
    (conda_prefix / "lib").mkdir(parents=True)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_golem_sst_smoke.sh",
            "--artifact-root",
            str(artifact_root),
            "--hardware-tests-dir",
            str(hardware_tests_dir),
        ],
        check=True,
        env={
            "CAPTURE_PATH": str(capture_path),
            "CONDA_PREFIX": str(conda_prefix),
            "LD_LIBRARY_PATH": "/existing/lib",
            "PATH": f"{_write_fake_toolchain(tmp_path)}:/usr/bin:/bin",
        },
    )

    captured = capture_path.read_text(encoding="utf-8")
    assert f"LD_LIBRARY_PATH={conda_prefix / 'lib'}:/existing/lib" in captured
