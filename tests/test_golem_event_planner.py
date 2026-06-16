from tilelang_cim import GolemBackendConfig, build_gemm_ir, build_golem_event_plan


def _ir_2x2_tiles():
    return build_gemm_ir(
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


def test_build_golem_event_plan_maps_macro_tasks_like_pipeline_config():
    plan = build_golem_event_plan(
        _ir_2x2_tiles(),
        GolemBackendConfig(
            array_input_size=64,
            array_output_size=64,
            num_arrays=64,
            total_groups=4,
            total_gemm_cores=20,
            num_memory_nodes=5,
            mem_node_size_bytes=128 * 1024 * 1024,
            a_reuse_n_tiles=1,
            b_reuse_m_tiles=1,
            dma_slot_count=16,
        ),
    )

    assert plan["mode"] == "golem_event_plan"
    assert plan["stats"]["m_tiles"] == 2
    assert plan["stats"]["n_tiles"] == 2
    assert plan["stats"]["k_tiles"] == 1
    assert plan["stats"]["total_macro_tasks"] == 4
    assert plan["stats"]["active_worker_cores"] == 16

    task0, task1, task2, task3 = plan["tasks"]
    assert [task["macro_task_id"] for task in plan["tasks"]] == [0, 2, 3, 1]
    assert [task["worker_core"] for task in plan["tasks"]] == [4, 6, 7, 5]
    assert [task["group_id"] for task in plan["tasks"]] == [0, 2, 3, 1]
    assert [task["data_node_idx"] for task in plan["tasks"]] == [1, 3, 4, 2]

    assert task0["m_tile"] == 0
    assert task0["n_tile"] == 0
    assert task1["m_tile"] == 0
    assert task1["n_tile"] == 1
    assert task2["m_tile"] == 1
    assert task2["n_tile"] == 0
    assert task3["m_tile"] == 1
    assert task3["n_tile"] == 1


def test_build_golem_event_plan_emits_hbm_addresses_and_golem_events():
    plan = build_golem_event_plan(_ir_2x2_tiles())
    task0 = plan["tasks"][0]

    assert task0["a_base_mm"] == 128 * 1024 * 1024
    assert task0["b_pack_base_mm"] == 128 * 1024 * 1024 + 0x4000
    assert task0["c_base_mm"] == 128 * 1024 * 1024 + 0x8000
    assert task0["task_slot_in_node"] == 0
    assert task0["reuse_offset"] == 0

    assert [event["op"] for event in task0["events"]] == [
        "remote_load_a_panel",
        "gm2imat",
        "remote_load_b_vector_pack",
        "gm2ivec_batch",
        "tile_mvm_batch",
        "tile_wait_batch",
        "ovec2gm",
        "remote_store_c_tile",
    ]
    assert task0["events"][0]["src_mm"] == task0["a_base_mm"]
    assert task0["events"][2]["src_mm"] == task0["b_pack_base_mm"]
    assert task0["events"][-1]["dst_mm"] == task0["c_base_mm"]


def test_build_golem_event_plan_accounts_for_reuse_offsets():
    plan = build_golem_event_plan(
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
        ),
        GolemBackendConfig(a_reuse_n_tiles=2, b_reuse_m_tiles=2),
    )

    assert plan["stats"]["total_macro_tasks"] == 1
    assert [task["reuse_offset"] for task in plan["tasks"]] == [0, 1, 2, 3]
    assert [task["macro_task_id"] for task in plan["tasks"]] == [0, 0, 0, 0]
