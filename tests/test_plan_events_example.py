import json
import subprocess
import sys

from tilelang_cim import build_gemm_ir, write_json


def test_plan_events_example_writes_event_plan_json(tmp_path):
    ir_path = tmp_path / "gemm.cimtile.json"
    plan_path = tmp_path / "gemm.eventplan.json"
    write_json(
        build_gemm_ir(m=256, n=128, k=64, bm=64, bn=64, bk=32, mesh_w=4, mesh_h=2),
        ir_path,
    )

    subprocess.run(
        [
            sys.executable,
            "examples/plan_events.py",
            str(ir_path),
            "--output",
            str(plan_path),
        ],
        check=True,
    )

    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "event_plan"
    assert len(payload["tasks"]) == 8
    assert payload["stats"]["dma_load_bytes"] == 65536
