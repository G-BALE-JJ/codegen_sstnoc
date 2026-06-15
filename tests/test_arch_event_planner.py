from tilelang_cim import build_arch_event_plan, build_gemm_ir, load_architecture_spec


def _toy_spec():
    return load_architecture_spec("examples/architecture/toy_cim_mesh_v0.json")


def test_arch_event_planner_adds_serial_formula_cycles():
    ir = build_gemm_ir(m=128, n=128, k=64, bm=64, bn=64, bk=32, mesh_w=8, mesh_h=8, pipeline_stages=2)

    plan = build_arch_event_plan(ir, _toy_spec())

    assert plan["mode"] == "arch_event_plan"
    assert plan["architecture"] == "toy_cim_mesh_v0"
    assert plan["cycle_model"] == "serial_formula_v0"
    assert len(plan["tasks"]) == 4

    first_task = plan["tasks"][0]
    assert first_task["cycles"] == 1893
    assert [event["cycles"] for event in first_task["events"]] == [
        1,
        148,
        148,
        128,
        148,
        148,
        128,
        1044,
    ]
    assert plan["core_cycles"] == {
        "0": 1893,
        "1": 1893,
        "8": 1893,
        "9": 1893,
    }
    assert plan["stats"]["estimated_task_cycles_sum"] == 7572
    assert plan["stats"]["estimated_max_core_cycles"] == 1893
    assert plan["stats"]["estimated_cycles"] == 1893
    assert plan["stats"]["cycle_model"] == "serial_formula_v0"


def test_arch_event_planner_accumulates_cycles_for_wrapped_cores():
    ir = build_gemm_ir(m=256, n=256, k=64, bm=64, bn=64, bk=32, mesh_w=8, mesh_h=8)
    spec = _toy_spec()
    spec["mesh"]["w"] = 2
    spec["mesh"]["h"] = 2
    ir["mesh"] = {"w": 2, "h": 2}

    plan = build_arch_event_plan(ir, spec)

    assert len(plan["tasks"]) == 16
    assert plan["stats"]["active_cores"] == 4
    assert plan["stats"]["estimated_max_core_cycles"] == 7572
    assert plan["stats"]["estimated_cycles"] == 7572
    assert plan["core_cycles"] == {
        "0": 7572,
        "1": 7572,
        "2": 7572,
        "3": 7572,
    }


def test_arch_event_planner_rejects_invalid_arch_match():
    ir = build_gemm_ir(m=128, n=128, k=64, bm=64, bn=64, bk=32, mesh_w=8, mesh_h=8)
    spec = _toy_spec()
    spec["core"]["accumulator_bytes"] = 1024

    try:
        build_arch_event_plan(ir, spec)
    except ValueError as exc:
        assert "accumulator is too small" in str(exc)
    else:
        raise AssertionError("build_arch_event_plan should reject IR that does not fit the architecture")
