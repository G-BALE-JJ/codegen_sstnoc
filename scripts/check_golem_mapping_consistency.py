#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def check_golem_mapping_consistency(
    artifact_root: str | Path,
    event_plan: str | Path,
) -> dict[str, Any]:
    root = Path(artifact_root)
    event_plan_path = Path(event_plan)
    resolved_path = root / "contracts" / "matmul_op_desc_resolved.json"
    report: dict[str, Any] = {
        "mode": "golem_mapping_consistency",
        "artifact_root": str(root),
        "event_plan_path": str(event_plan_path),
        "ok": False,
        "checks": {},
        "resolved_contract": {},
        "event_plan_summary": {},
        "warnings": [],
        "errors": [],
    }

    resolved = _read_json_object(resolved_path, "resolved contract", report)
    plan = _read_json_object(event_plan_path, "event plan", report)
    if report["errors"]:
        return report

    report["resolved_contract"] = resolved
    stats = plan.get("stats") if isinstance(plan.get("stats"), dict) else {}
    tasks = plan.get("tasks") if isinstance(plan.get("tasks"), list) else []
    report["event_plan_summary"] = _summarize_plan(plan, stats, tasks)

    _check_plan_header(plan, report)
    _check_tile_counts(resolved, stats, report)
    _check_task_count(stats, tasks, report)
    _check_task_ranges(stats, tasks, report)
    _check_base_addresses(tasks, report)
    _check_event_address_refs(tasks, report)

    report["ok"] = not report["errors"]
    return report


def _read_json_object(path: Path, label: str, report: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report["errors"].append(f"cannot read {label} {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        report["errors"].append(f"{label} must be a JSON object")
        return {}
    return payload


def _summarize_plan(plan: dict[str, Any], stats: dict[str, Any], tasks: list[Any]) -> dict[str, Any]:
    keys = [
        "m_tiles",
        "n_tiles",
        "k_tiles",
        "m_groups",
        "n_groups",
        "total_gemm_tasks",
        "total_macro_tasks",
        "active_worker_cores",
        "total_gemm_cores",
        "total_groups",
        "num_memory_nodes",
        "a_reuse_n_tiles",
        "b_reuse_m_tiles",
    ]
    summary = {key: stats.get(key) for key in keys if key in stats}
    summary["mode"] = plan.get("mode")
    summary["backend"] = plan.get("backend")
    summary["task_count"] = len(tasks)
    return summary


def _check_plan_header(plan: dict[str, Any], report: dict[str, Any]) -> None:
    errors: list[str] = []
    if plan.get("mode") != "golem_event_plan":
        errors.append(f"event plan mode must be golem_event_plan, got {plan.get('mode')!r}")
    if plan.get("backend") != "golem_sst":
        errors.append(f"event plan backend must be golem_sst, got {plan.get('backend')!r}")
    if errors:
        report["checks"]["plan_header"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["plan_header"] = "ok"


def _check_tile_counts(resolved: dict[str, Any], stats: dict[str, Any], report: dict[str, Any]) -> None:
    errors: list[str] = []
    for dim, count_key, size_key, block_key in (
        ("m", "m_tiles", "m", "block_m"),
        ("n", "n_tiles", "n", "block_n"),
        ("k", "k_tiles", "k", "block_k"),
    ):
        size = resolved.get(size_key)
        block = resolved.get(block_key)
        actual = stats.get(count_key)
        if not isinstance(size, int) or not isinstance(block, int) or not isinstance(actual, int):
            errors.append(f"cannot compare {count_key}: contract {size_key}/{block_key} or plan stat is missing")
            continue
        expected = size // block if block else None
        if actual != expected:
            errors.append(f"event plan {count_key}={actual} does not match contract {dim}/{block_key}={expected}")
    if errors:
        report["checks"]["tile_counts_match_contract"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["tile_counts_match_contract"] = "ok"


def _check_task_count(stats: dict[str, Any], tasks: list[Any], report: dict[str, Any]) -> None:
    expected = stats.get("total_gemm_tasks")
    if isinstance(expected, int) and len(tasks) == expected:
        report["checks"]["task_count_matches_tiles"] = "ok"
        return
    report["checks"]["task_count_matches_tiles"] = "fail"
    report["errors"].append(f"event plan has {len(tasks)} tasks, expected total_gemm_tasks={expected}")


def _check_task_ranges(stats: dict[str, Any], tasks: list[Any], report: dict[str, Any]) -> None:
    errors: list[str] = []
    total_gemm_cores = stats.get("total_gemm_cores")
    num_memory_nodes = stats.get("num_memory_nodes")
    total_macro_tasks = stats.get("total_macro_tasks")
    active_worker_cores = stats.get("active_worker_cores")

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"task {index} must be an object")
            continue
        task_id = task.get("task_id", index)
        _check_int_range(task, "worker_core", 0, total_gemm_cores, f"task {task_id}", errors)
        _check_int_range(task, "worker_slot", 0, active_worker_cores, f"task {task_id}", errors)
        _check_int_range(task, "data_node_idx", 1, num_memory_nodes, f"task {task_id}", errors)
        _check_int_range(task, "macro_task_id", 0, total_macro_tasks, f"task {task_id}", errors)
        _check_int_range(task, "task_slot_in_node", 0, None, f"task {task_id}", errors)
        _check_int_range(task, "reuse_offset", 0, None, f"task {task_id}", errors)

    if errors:
        report["checks"]["task_fields_in_range"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["task_fields_in_range"] = "ok"


def _check_int_range(
    payload: dict[str, Any],
    field: str,
    lower: int,
    upper: Any,
    prefix: str,
    errors: list[str],
) -> None:
    value = payload.get(field)
    if not isinstance(value, int):
        errors.append(f"{prefix} {field} must be an integer")
        return
    if value < lower or (isinstance(upper, int) and value >= upper):
        if isinstance(upper, int):
            errors.append(f"{prefix} {field}={value} is outside [{lower}, {upper})")
        else:
            errors.append(f"{prefix} {field}={value} is less than {lower}")


def _check_base_addresses(tasks: list[Any], report: dict[str, Any]) -> None:
    errors: list[str] = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id", index)
        for field in ("a_base_mm", "b_pack_base_mm", "c_base_mm"):
            value = task.get(field)
            if not isinstance(value, int):
                errors.append(f"task {task_id} {field} must be an integer")
            elif value < 0:
                errors.append(f"task {task_id} {field} must be non-negative")
    if errors:
        report["checks"]["base_addresses_present"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["base_addresses_present"] = "ok"


def _check_event_address_refs(tasks: list[Any], report: dict[str, Any]) -> None:
    errors: list[str] = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id", index)
        events = task.get("events")
        if not isinstance(events, list):
            errors.append(f"task {task_id} events must be a list")
            continue
        if not _event_matches(events, "remote_load_a_panel", "src_mm", task.get("a_base_mm")):
            errors.append(f"task {task_id} remote_load_a_panel src_mm does not match a_base_mm")
        if not _event_matches(events, "remote_load_b_vector_pack", "src_mm", task.get("b_pack_base_mm")):
            errors.append(f"task {task_id} remote_load_b_vector_pack src_mm does not match b_pack_base_mm")
        if not _event_matches(events, "remote_store_c_tile", "dst_mm", task.get("c_base_mm")):
            errors.append(f"task {task_id} remote_store_c_tile dst_mm does not match c_base_mm")
    if errors:
        report["checks"]["event_address_refs"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["event_address_refs"] = "ok"


def _event_matches(events: list[Any], op: str, field: str, expected: Any) -> bool:
    return any(isinstance(event, dict) and event.get("op") == op and event.get(field) == expected for event in events)


def main() -> None:
    args = _parse_args()
    report = check_golem_mapping_consistency(args.artifact_root, args.event_plan)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if not report["ok"]:
        raise SystemExit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check consistency between Golem SST resolved contract and Golem task mapping plan."
    )
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--event-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    main()
