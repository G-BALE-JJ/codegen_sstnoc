from __future__ import annotations

from typing import Any

from .golem_constraints import GolemBackendConfig, normalize_golem_dtype, validate_cim_tile_ir_for_golem


MM_ALIGN = 0x100
OFF_GEMM_MAT_BASE = 0x0


def build_golem_event_plan(
    ir: dict[str, Any],
    backend_config: GolemBackendConfig = GolemBackendConfig(),
) -> dict[str, Any]:
    errors = validate_cim_tile_ir_for_golem(ir, backend_config)
    if errors:
        raise ValueError("Invalid CIM-TileIR for Golem event planner:\n" + "\n".join(f"- {error}" for error in errors))

    layout = _build_layout(ir, backend_config)
    tasks = [_build_task(ir, backend_config, layout, task_id) for task_id in range(layout["total_gemm_tasks"])]

    return {
        "kernel": ir["kernel"],
        "source_target": ir.get("target", "riscv_cim_mesh"),
        "mode": "golem_event_plan",
        "backend": "golem_sst",
        "tile": dict(ir["tile"]),
        "tasks": tasks,
        "stats": {
            "m_tiles": layout["m_tiles"],
            "n_tiles": layout["n_tiles"],
            "k_tiles": layout["k_tiles"],
            "m_groups": layout["m_groups"],
            "n_groups": layout["n_groups"],
            "total_gemm_tasks": layout["total_gemm_tasks"],
            "total_macro_tasks": layout["total_macro_tasks"],
            "active_worker_cores": layout["active_worker_cores"],
            "total_gemm_cores": backend_config.total_gemm_cores,
            "total_groups": backend_config.total_groups,
            "num_memory_nodes": backend_config.num_memory_nodes,
            "a_reuse_n_tiles": layout["a_reuse_n_tiles"],
            "b_reuse_m_tiles": layout["b_reuse_m_tiles"],
        },
    }


def _build_layout(ir: dict[str, Any], config: GolemBackendConfig) -> dict[str, Any]:
    bm = ir["tile"]["BM"]
    bn = ir["tile"]["BN"]
    bk = ir["tile"]["BK"]
    m, _ = ir["tensors"]["A"]["shape"]
    _, n = ir["tensors"]["B"]["shape"]
    _, k = ir["tensors"]["A"]["shape"]
    dtype = normalize_golem_dtype(ir["tensors"]["A"]["dtype"])
    elem_bytes = _elem_bytes(dtype)

    m_tiles = m // bm
    n_tiles = n // bn
    k_tiles = k // bk
    a_reuse_n = max(1, config.a_reuse_n_tiles)
    b_reuse_m = max(1, config.b_reuse_m_tiles)
    m_groups = _ceildiv(m_tiles, b_reuse_m)
    n_groups = _ceildiv(n_tiles, a_reuse_n)
    total_macro_tasks = m_groups * n_groups
    dedicated_manager_cores = config.total_groups
    active_worker_cores = config.total_gemm_cores - dedicated_manager_cores
    if active_worker_cores <= 0:
        raise ValueError("Golem event planner requires at least one active worker core")
    if config.num_memory_nodes < 2:
        raise ValueError("Golem event planner requires at least one data memory node")

    mat_stride = _align_up(bm * bk * elem_bytes, MM_ALIGN)
    vec_stride = _align_up(bk * elem_bytes, MM_ALIGN)
    out_stride = _align_up(bm * bn * elem_bytes, MM_ALIGN)
    max_a_m_tiles = _max_count(
        range(m_tiles),
        lambda node_idx, m_tile: _a_data_node_for_m_tile(m_tile, b_reuse_m, config, active_worker_cores) == node_idx,
        config,
    )
    max_b_n_tiles = _max_count(
        range(n_tiles),
        lambda node_idx, n_tile: _b_data_node_for_n_tile(n_tile, a_reuse_n, config, active_worker_cores) == node_idx,
        config,
    )
    off_vec_base = OFF_GEMM_MAT_BASE + max_a_m_tiles * k_tiles * mat_stride
    off_out_base = off_vec_base + max_b_n_tiles * k_tiles * bn * vec_stride

    return {
        "m": m,
        "n": n,
        "k": k,
        "block_m": bm,
        "block_n": bn,
        "block_k": bk,
        "dtype": dtype,
        "elem_bytes": elem_bytes,
        "m_tiles": m_tiles,
        "n_tiles": n_tiles,
        "k_tiles": k_tiles,
        "a_reuse_n_tiles": a_reuse_n,
        "b_reuse_m_tiles": b_reuse_m,
        "m_groups": m_groups,
        "n_groups": n_groups,
        "total_gemm_tasks": m_tiles * n_tiles,
        "total_macro_tasks": total_macro_tasks,
        "dedicated_manager_cores": dedicated_manager_cores,
        "active_worker_cores": active_worker_cores,
        "mat_stride": mat_stride,
        "vec_stride": vec_stride,
        "out_stride": out_stride,
        "off_vec_base": off_vec_base,
        "off_out_base": off_out_base,
    }


def _build_task(
    ir: dict[str, Any],
    config: GolemBackendConfig,
    layout: dict[str, Any],
    task_id: int,
) -> dict[str, Any]:
    n_tiles = layout["n_tiles"]
    m_tile = task_id // n_tiles
    n_tile = task_id % n_tiles
    macro_task_id = _macro_task_for_tile(m_tile, n_tile, layout)
    worker_slot = macro_task_id % layout["active_worker_cores"]
    worker_core = config.total_groups + worker_slot
    group_id = worker_core % config.total_groups if config.total_groups > 0 else 0
    data_node_idx = _data_node_for_task(macro_task_id, config, layout["active_worker_cores"])
    task_slot = _task_slot_in_node(macro_task_id, data_node_idx, config, layout["active_worker_cores"])
    a_node_idx = _a_data_node_for_m_tile(m_tile, layout["b_reuse_m_tiles"], config, layout["active_worker_cores"])
    b_node_idx = _b_data_node_for_n_tile(n_tile, layout["a_reuse_n_tiles"], config, layout["active_worker_cores"])
    a_slot = _a_slot_for_m_tile(m_tile, a_node_idx, layout["b_reuse_m_tiles"], config, layout["active_worker_cores"])
    b_slot = _b_slot_for_n_tile(n_tile, b_node_idx, layout["a_reuse_n_tiles"], config, layout["active_worker_cores"])
    mat_slots = layout["b_reuse_m_tiles"] if layout["b_reuse_m_tiles"] > 1 else 1
    vec_slots = layout["a_reuse_n_tiles"] if layout["a_reuse_n_tiles"] > 1 else 1
    reuse_offset = (m_tile % mat_slots) * vec_slots + (n_tile % vec_slots)

    a_base_mm = (
        _node_base(a_node_idx, config)
        + OFF_GEMM_MAT_BASE
        + a_slot * layout["k_tiles"] * layout["mat_stride"]
    )
    b_pack_base_mm = (
        _node_base(b_node_idx, config)
        + layout["off_vec_base"]
        + b_slot * layout["k_tiles"] * layout["block_n"] * layout["vec_stride"]
    )
    c_base_mm = (
        _node_base(data_node_idx, config)
        + layout["off_out_base"]
        + (task_slot * mat_slots * vec_slots + reuse_offset) * layout["out_stride"]
    )

    return {
        "task_id": task_id,
        "macro_task_id": macro_task_id,
        "m_tile": m_tile,
        "n_tile": n_tile,
        "m_group": m_tile // layout["b_reuse_m_tiles"],
        "n_group": n_tile // layout["a_reuse_n_tiles"],
        "worker_slot": worker_slot,
        "worker_core": worker_core,
        "group_id": group_id,
        "data_node_idx": data_node_idx,
        "task_slot_in_node": task_slot,
        "reuse_offset": reuse_offset,
        "a_base_mm": a_base_mm,
        "b_pack_base_mm": b_pack_base_mm,
        "c_base_mm": c_base_mm,
        "events": _build_events(layout, a_base_mm, b_pack_base_mm, c_base_mm),
    }


def _build_events(
    layout: dict[str, Any],
    a_base_mm: int,
    b_pack_base_mm: int,
    c_base_mm: int,
) -> list[dict[str, Any]]:
    block_m = layout["block_m"]
    block_n = layout["block_n"]
    block_k = layout["block_k"]
    elem_bytes = layout["elem_bytes"]
    return [
        {"op": "remote_load_a_panel", "src_mm": a_base_mm, "bytes": block_m * block_k * elem_bytes},
        {"op": "gm2imat", "src": "local_mat", "block_m": block_m, "block_k": block_k},
        {
            "op": "remote_load_b_vector_pack",
            "src_mm": b_pack_base_mm,
            "bytes": block_n * block_k * elem_bytes,
        },
        {"op": "gm2ivec_batch", "vectors": block_n, "block_k": block_k},
        {"op": "tile_mvm_batch", "vectors": block_n, "macs": block_m * block_n * block_k},
        {"op": "tile_wait_batch", "vectors": block_n},
        {"op": "ovec2gm", "vectors": block_n, "block_m": block_m},
        {"op": "remote_store_c_tile", "dst_mm": c_base_mm, "bytes": block_m * block_n * elem_bytes},
    ]


def _macro_task_for_tile(m_tile: int, n_tile: int, layout: dict[str, Any]) -> int:
    m_group = m_tile // layout["b_reuse_m_tiles"]
    n_group = n_tile // layout["a_reuse_n_tiles"]
    n_band = (n_group - m_group + layout["n_groups"]) % layout["n_groups"]
    return n_band * layout["m_groups"] + m_group


def _data_node_for_task(task_id: int, config: GolemBackendConfig, active_worker_cores: int) -> int:
    owner_core = _owner_core_for_task(task_id, config, active_worker_cores)
    group_id = owner_core % config.total_groups if config.total_groups > 0 else 0
    data_node_count = config.num_memory_nodes - 1
    return 1 + (group_id % data_node_count) if data_node_count > 0 else 1


def _owner_core_for_task(task_id: int, config: GolemBackendConfig, active_worker_cores: int) -> int:
    return config.total_groups + (task_id % active_worker_cores)


def _task_slot_in_node(
    task_id: int,
    node_idx: int,
    config: GolemBackendConfig,
    active_worker_cores: int,
) -> int:
    return sum(1 for prev in range(task_id) if _data_node_for_task(prev, config, active_worker_cores) == node_idx)


def _a_data_node_for_m_tile(
    m_tile: int,
    b_reuse_m_tiles: int,
    config: GolemBackendConfig,
    active_worker_cores: int,
) -> int:
    return _data_node_for_task(m_tile // b_reuse_m_tiles, config, active_worker_cores)


def _b_data_node_for_n_tile(
    n_tile: int,
    a_reuse_n_tiles: int,
    config: GolemBackendConfig,
    active_worker_cores: int,
) -> int:
    return _data_node_for_task(n_tile // a_reuse_n_tiles, config, active_worker_cores)


def _a_slot_for_m_tile(
    m_tile: int,
    node_idx: int,
    b_reuse_m_tiles: int,
    config: GolemBackendConfig,
    active_worker_cores: int,
) -> int:
    return sum(
        1
        for prev in range(m_tile)
        if _a_data_node_for_m_tile(prev, b_reuse_m_tiles, config, active_worker_cores) == node_idx
    )


def _b_slot_for_n_tile(
    n_tile: int,
    node_idx: int,
    a_reuse_n_tiles: int,
    config: GolemBackendConfig,
    active_worker_cores: int,
) -> int:
    return sum(
        1
        for prev in range(n_tile)
        if _b_data_node_for_n_tile(prev, a_reuse_n_tiles, config, active_worker_cores) == node_idx
    )


def _max_count(items: range, predicate, config: GolemBackendConfig) -> int:
    best = 0
    for node_idx in range(1, config.num_memory_nodes):
        best = max(best, sum(1 for item in items if predicate(node_idx, item)))
    return best or 1


def _node_base(node_idx: int, config: GolemBackendConfig) -> int:
    return node_idx * config.mem_node_size_bytes


def _elem_bytes(dtype: str) -> int:
    if dtype in {"int32", "fp32"}:
        return 4
    raise ValueError(f"Unsupported Golem dtype: {dtype}")


def _align_up(value: int, align: int) -> int:
    return ((value + align - 1) // align) * align


def _ceildiv(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor
