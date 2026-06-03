import json
import subprocess
import sys

from tilelang_cim import validate_cim_tile_ir


def test_gemm_ir_example_writes_valid_json(tmp_path):
    output_path = tmp_path / "gemm.cimtile.json"

    subprocess.run(
        [
            sys.executable,
            "examples/gemm_ir.py",
            "--output",
            str(output_path),
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
            "--mesh-w",
            "4",
            "--mesh-h",
            "2",
        ],
        check=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert validate_cim_tile_ir(payload) == []
    assert payload["mesh"] == {"w": 4, "h": 2}
    assert payload["program"][1]["count"] == 2
