import json
import subprocess
from pathlib import Path

from tilelang_cim import extract_gemm_ir_from_source
from tilelang_cim.golem_exporter import export_golem_sst_artifacts


def test_make_tilelang_gemm_source_generates_parseable_static_gemm(tmp_path):
    output = tmp_path / "generated_tilelang_gemm.py"

    subprocess.run(
        [
            "python",
            "examples/make_tilelang_gemm_source.py",
            "--m",
            "256",
            "--n",
            "128",
            "--k",
            "64",
            "--bm",
            "64",
            "--bn",
            "64",
            "--bk",
            "32",
            "--dtype",
            "float32",
            "--num-stages",
            "2",
            "--threads",
            "128",
            "--output",
            str(output),
        ],
        check=True,
    )

    source = output.read_text(encoding="utf-8")
    ir = extract_gemm_ir_from_source(source, mesh_w=4, mesh_h=2)

    assert ir["tensors"]["A"]["shape"] == [256, 64]
    assert ir["tensors"]["B"]["shape"] == [64, 128]
    assert ir["tensors"]["C"]["shape"] == [256, 128]
    assert ir["tensors"]["A"]["dtype"] == "float32"
    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 32}
    assert ir["program"][1]["count"] == 2
    assert ir["program"][1]["pipeline_stages"] == 2


def test_make_tilelang_gemm_source_default_is_golem_exportable(tmp_path):
    output = tmp_path / "generated_tilelang_gemm.py"

    subprocess.run(
        [
            "python",
            "examples/make_tilelang_gemm_source.py",
            "--output",
            str(output),
        ],
        check=True,
    )

    ir = extract_gemm_ir_from_source(output.read_text(encoding="utf-8"), mesh_w=4, mesh_h=5)
    paths = export_golem_sst_artifacts(ir, tmp_path / "artifacts")

    assert ir["tensors"]["A"]["shape"] == [1024, 128]
    assert ir["tensors"]["B"]["shape"] == [128, 1024]
    assert ir["tensors"]["C"]["shape"] == [1024, 1024]
    assert ir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert paths["env"].exists()
    assert paths["resolved_contract"].exists()


def test_run_tilelang_golem_e2e_can_generate_tilelang_source(tmp_path):
    from tests.test_run_tilelang_golem_e2e import _write_fake_pipeline, _write_fake_toolchain

    run_root = tmp_path / "e2e"
    hardware_tests_dir, capture_path = _write_fake_pipeline(tmp_path)

    subprocess.run(
        [
            "/bin/bash",
            "examples/run_tilelang_golem_e2e.sh",
            "--generate-tilelang-source",
            "--m",
            "512",
            "--n",
            "256",
            "--k",
            "128",
            "--bm",
            "64",
            "--bn",
            "64",
            "--bk",
            "64",
            "--dtype",
            "float32",
            "--num-stages",
            "2",
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

    generated = run_root / "generated_tilelang_gemm.py"
    cim_tileir = json.loads((run_root / "tilelang_gemm.cimtile.json").read_text(encoding="utf-8"))

    assert generated.exists()
    assert cim_tileir["tensors"]["A"]["shape"] == [512, 128]
    assert cim_tileir["tensors"]["B"]["shape"] == [128, 256]
    assert cim_tileir["tensors"]["C"]["shape"] == [512, 256]
    assert cim_tileir["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert cim_tileir["program"][1]["pipeline_stages"] == 2
    assert capture_path.read_text(encoding="utf-8").strip().startswith("--dry-run")
