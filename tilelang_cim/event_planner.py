from __future__ import annotations

from typing import Any

from .checker import validate_cim_tile_ir


_DTYPE_BYTES = {
    "int8": 1,
    "uint8": 1,
    "float16": 2,
    "float32": 4,
    "float": 4,
    "int32": 4,
}


def build_event_plan(ir: dict[str, Any]) -> dict[str, Any]:
    """Expand a GEMM CIM-TileIR dictionary into per-core abstract events."""
    errors = validate_cim_tile_ir(ir)
    if errors:
        raise ValueError("Invalid CIM-TileIR:\n" + "\n".join(f"- {error}" for error in errors))
    if ir.get("kernel") != "gemm":
        raise ValueError("Only gemm kernels are supported by the first event planner MVP")

    mesh_w = ir["mesh"]["w"]
    mesh_h = ir["mesh"]["h"]
    bm = ir["tile"]["BM"]
    bn = ir["tile"]["BN"]
    bk = ir["tile"]["BK"]
    m, _ = ir["tensors"]["A"]["shape"]
    _, n = ir["tensors"]["B"]["shape"]
    _, k_tiles = _find_loop_k(ir)

    m_tiles = m // bm
    n_tiles = n // bn

    tasks: list[dict[str, Any]] = []
    stats = _new_stats(output_tiles=m_tiles * n_tiles, total_cores=mesh_w * mesh_h)
    active_core_ids: set[int] = set()

    for by in range(m_tiles):
        for bx in range(n_tiles):
            core = _map_output_tile_to_core(bx=bx, by=by, mesh_w=mesh_w, mesh_h=mesh_h)
            active_core_ids.add(core["id"])
            events = _build_task_events(ir=ir, bx=bx, by=by, k_tiles=k_tiles)
            _accumulate_stats(stats, events)
            tasks.append(
                {
                    "task_id": f"tile_by{by}_bx{bx}",
                    "output_tile": {"bx": bx, "by": by},
                    "core": core,
                    "events": events,
                }
            )

    stats["active_cores"] = len(active_core_ids)
    stats["core_utilization"] = round(stats["active_cores"] / stats["total_cores"], 6)

    return {
        "kernel": ir["kernel"],
        "source_target": ir.get("target", "riscv_cim_mesh"),
        "mode": "event_plan",
        "mesh": {"w": mesh_w, "h": mesh_h},
        "tile": dict(ir["tile"]),
        "tasks": tasks,
        "stats": stats,
    }


def _new_stats(*, output_tiles: int, total_cores: int) -> dict[str, Any]:
    return {
        "output_tiles": output_tiles,
        "total_cores": total_cores,
        "active_cores": 0,
        "core_utilization": 0.0,
        "dma_load_bytes": 0,
        "dma_store_bytes": 0,
        "cim_gemm_ops": 0,
        "macs": 0,
        "estimated_cycles": 0,
    }


def _find_loop_k(ir: dict[str, Any]) -> tuple[dict[str, Any], int]:
    for op in ir["program"]:
        if op.get("op") == "loop_k":
            return op, op["count"]
    raise ValueError("program must contain loop_k")


def _map_output_tile_to_core(*, bx: int, by: int, mesh_w: int, mesh_h: int) -> dict[str, int]:
    x = bx % mesh_w
    y = by % mesh_h
    return {"x": x, "y": y, "id": y * mesh_w + x}


def _build_task_events(*, ir: dict[str, Any], bx: int, by: int, k_tiles: int) -> list[dict[str, Any]]:
    bm = ir["tile"]["BM"]
    bn = ir["tile"]["BN"]
    bk = ir["tile"]["BK"]
    a_bytes = bm * bk * _dtype_bytes(ir["tensors"]["A"]["dtype"])
    b_bytes = bk * bn * _dtype_bytes(ir["tensors"]["B"]["dtype"])
    c_bytes = bm * bn * _dtype_bytes(ir["tensors"]["C"]["dtype"])

    events: list[dict[str, Any]] = [{"op": "clear_acc", "buffer": "C_acc"}]
    for ko in range(k_tiles):
        events.append(
            {
                "op": "dma_load",
                "tensor": "A",
                "ko": ko,
                "bytes": a_bytes,
                "tile": [by * bm, ko * bk, bm, bk],
                "dst": "A_s",
            }
        )
        events.append(
            {
                "op": "dma_load",
                "tensor": "B",
                "ko": ko,
                "bytes": b_bytes,
                "tile": [ko * bk, bx * bn, bk, bn],
                "dst": "B_s",
            }
        )
        events.append({"op": "cim_gemm", "ko": ko, "BM": bm, "BN": bn, "BK": bk, "macs": bm * bn * bk})

    events.append(
        {
            "op": "dma_store",
            "tensor": "C",
            "bytes": c_bytes,
            "tile": [by * bm, bx * bn, bm, bn],
            "src": "C_acc",
        }
    )
    return events


def _accumulate_stats(stats: dict[str, Any], events: list[dict[str, Any]]) -> None:
    for event in events:
        if event["op"] == "dma_load":
            stats["dma_load_bytes"] += event["bytes"]
        elif event["op"] == "dma_store":
            stats["dma_store_bytes"] += event["bytes"]
        elif event["op"] == "cim_gemm":
            stats["cim_gemm_ops"] += 1
            stats["macs"] += event["macs"]


def _dtype_bytes(dtype: str) -> int:
    if dtype not in _DTYPE_BYTES:
        raise ValueError(f"Unsupported dtype for event planning: {dtype}")
    return _DTYPE_BYTES[dtype]
