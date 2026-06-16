import json
import subprocess
import sys

from tilelang_cim import build_gemm_ir


def test_plan_golem_events_cli_writes_golem_event_plan(tmp_path):
    ir_path = tmp_path / "gemm.cimtile.json"
    out_path = tmp_path / "gemm.golem_event_plan.json"
    ir_path.write_text(
        json.dumps(
            build_gemm_ir(
                m=128,
                n=128,
                k=64,
                bm=64,
                bn=64,
                bk=64,
                mesh_w=4,
                mesh_h=5,
                a_dtype="fp32",
                b_dtype="fp32",
                c_dtype="fp32",
            )
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            "examples/plan_golem_events.py",
            str(ir_path),
            "--output",
            str(out_path),
        ],
        check=True,
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "golem_event_plan"
    assert payload["stats"]["total_macro_tasks"] == 4
