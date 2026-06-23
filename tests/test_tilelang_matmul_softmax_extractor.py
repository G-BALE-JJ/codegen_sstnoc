import json
import subprocess

from tests.fixtures.tileops_like_matmul_softmax_fixture import TILEOPS_LIKE_MATMUL_SOFTMAX_SOURCE
from tilelang_cim import extract_matmul_softmax_graph_ir_from_source, validate_cim_tile_ir


def test_extract_tileops_like_matmul_softmax_source_to_graph_ir():
    ir = extract_matmul_softmax_graph_ir_from_source(TILEOPS_LIKE_MATMUL_SOFTMAX_SOURCE, mesh_w=1, mesh_h=1)

    assert validate_cim_tile_ir(ir) == []
    assert ir["kernel"] == "graph"
    assert ir["mesh"] == {"w": 1, "h": 1}
    assert ir["tensors"]["A"]["shape"] == [64, 64]
    assert ir["tensors"]["B"]["shape"] == [64, 64]
    assert ir["tensors"]["S"]["shape"] == [64, 64]
    assert ir["tensors"]["P"]["shape"] == [64, 64]
    assert ir["ops"][0]["op"] == "matmul"
    assert ir["ops"][0]["tile"] == {"BM": 64, "BN": 64, "BK": 64}
    assert ir["ops"][0]["attrs"]["pipeline_stages"] == 2
    assert ir["ops"][1]["op"] == "softmax"
    assert ir["ops"][1]["attrs"]["axis"] == 1


def test_extract_tilelang_matmul_softmax_example_writes_valid_json(tmp_path):
    source = tmp_path / "matmul_softmax.py"
    output = tmp_path / "matmul_softmax.cimtile.json"
    source.write_text(TILEOPS_LIKE_MATMUL_SOFTMAX_SOURCE, encoding="utf-8")

    subprocess.run(
        [
            "python",
            "examples/extract_tilelang_matmul_softmax.py",
            str(source),
            "--output",
            str(output),
            "--mesh-w",
            "1",
            "--mesh-h",
            "1",
        ],
        check=True,
    )

    ir = json.loads(output.read_text(encoding="utf-8"))
    assert validate_cim_tile_ir(ir) == []
    assert ir["kernel"] == "graph"
    assert [op["op"] for op in ir["ops"]] == ["matmul", "softmax"]
