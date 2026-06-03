from tilelang_cim import build_event_plan, build_gemm_ir


def test_event_planner_expands_gemm_tiles_to_core_tasks():
    ir = build_gemm_ir(
        m=256,
        n=128,
        k=64,
        bm=64,
        bn=64,
        bk=32,
        mesh_w=4,
        mesh_h=2,
        pipeline_stages=2,
    )

    plan = build_event_plan(ir)

    assert plan["kernel"] == "gemm"
    assert plan["mesh"] == {"w": 4, "h": 2}
    assert len(plan["tasks"]) == 8

    first_task = plan["tasks"][0]
    assert first_task["task_id"] == "tile_by0_bx0"
    assert first_task["output_tile"] == {"bx": 0, "by": 0}
    assert first_task["core"] == {"x": 0, "y": 0, "id": 0}
    assert [event["op"] for event in first_task["events"]] == [
        "clear_acc",
        "dma_load",
        "dma_load",
        "cim_gemm",
        "dma_load",
        "dma_load",
        "cim_gemm",
        "dma_store",
    ]
    assert first_task["events"][1] == {
        "op": "dma_load",
        "tensor": "A",
        "ko": 0,
        "bytes": 2048,
        "tile": [0, 0, 64, 32],
        "dst": "A_s",
    }
    assert first_task["events"][2] == {
        "op": "dma_load",
        "tensor": "B",
        "ko": 0,
        "bytes": 2048,
        "tile": [0, 0, 32, 64],
        "dst": "B_s",
    }
    assert first_task["events"][-1] == {
        "op": "dma_store",
        "tensor": "C",
        "bytes": 16384,
        "tile": [0, 0, 64, 64],
        "src": "C_acc",
    }

    assert plan["stats"] == {
        "output_tiles": 8,
        "total_cores": 8,
        "active_cores": 4,
        "core_utilization": 0.5,
        "dma_load_bytes": 65536,
        "dma_store_bytes": 131072,
        "cim_gemm_ops": 16,
        "macs": 2097152,
        "estimated_cycles": 0,
    }


def test_event_planner_wraps_more_tiles_than_cores():
    ir = build_gemm_ir(
        m=256,
        n=256,
        k=64,
        bm=64,
        bn=64,
        bk=32,
        mesh_w=2,
        mesh_h=2,
    )

    plan = build_event_plan(ir)

    assert len(plan["tasks"]) == 16
    assert plan["stats"]["total_cores"] == 4
    assert plan["stats"]["active_cores"] == 4
    assert plan["stats"]["core_utilization"] == 1.0
    assert plan["tasks"][0]["core"] == {"x": 0, "y": 0, "id": 0}
    assert plan["tasks"][8]["core"] == {"x": 0, "y": 0, "id": 0}


def test_event_planner_reports_validation_errors():
    ir = build_gemm_ir(m=128, n=128, k=128, bm=64, bn=64, bk=32)
    ir["mesh"]["w"] = 0

    try:
        build_event_plan(ir)
    except ValueError as exc:
        assert "mesh.w must be a positive integer" in str(exc)
    else:
        raise AssertionError("build_event_plan should reject invalid CIM-TileIR")
