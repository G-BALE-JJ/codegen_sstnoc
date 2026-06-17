import json
import subprocess
import sys

from tilelang_cim import validate_cim_tile_ir


def test_extract_tilelang_gemm_example_writes_valid_json(tmp_path):
    output_path = tmp_path / "tilelang_gemm.cimtile.json"

    subprocess.run(
        [
            sys.executable,
            "examples/extract_tilelang_gemm.py",
            "tests/fixtures/tilelang_gemm_fixture.py",
            "--output",
            str(output_path),
            "--mesh-w",
            "4",
            "--mesh-h",
            "2",
        ],
        check=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert validate_cim_tile_ir(payload) == []
    assert payload["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert payload["tensors"]["A"]["shape"] == [1024, 128]
    assert payload["tensors"]["B"]["shape"] == [128, 1024]
    assert payload["tensors"]["C"]["shape"] == [1024, 1024]
    assert payload["tensors"]["A"]["dtype"] == "float32"
    assert payload["program"][1]["pipeline_stages"] == 2
