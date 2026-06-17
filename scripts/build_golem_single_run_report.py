#!/usr/bin/env python3
"""Build a structured report from one Golem SST run."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


METRIC_CSVS = {
    "execution": "execution_summary.csv",
    "noc": "noc_summary.csv",
    "memory": "memory_summary.csv",
    "memory_queue": "memory_queue_summary.csv",
    "submit_ready_causal": "submit_ready_causal_summary.csv",
}

SUMMARY_CSVS = {
    "dma": "dma_summary.csv",
}


def _coerce_scalar(value: str) -> Any:
    text = value.strip()
    if text == "":
        return ""
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if re.fullmatch(r"[-+]?\d+", text):
            return int(text)
        if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", text) or re.fullmatch(
            r"[-+]?\d+[eE][-+]?\d+", text
        ):
            return float(text)
    except ValueError:
        return text
    return text


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_metric_csv(path: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "metric" not in reader.fieldnames or "value" not in reader.fieldnames:
            raise ValueError(f"{path} must contain metric,value columns")
        for row in reader:
            metric = (row.get("metric") or "").strip()
            if metric:
                rows[metric] = _coerce_scalar(row.get("value") or "")
    return rows


def _read_summary_csv(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "metric" not in reader.fieldnames:
            raise ValueError(f"{path} must contain a metric column")
        for row in reader:
            metric = (row.get("metric") or "").strip()
            if not metric:
                continue
            rows[metric] = {
                key: _coerce_scalar(value)
                for key, value in row.items()
                if key != "metric" and value is not None
            }
    return rows


def _read_optional_csvs(
    stats_dir: Path,
    specs: dict[str, str],
    reader,
    warnings: list[str],
) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, filename in specs.items():
        path = stats_dir / filename
        if not path.exists():
            warnings.append(f"missing stats file: {path}")
            parsed[key] = {}
            continue
        try:
            parsed[key] = reader(path)
        except Exception as exc:  # pragma: no cover - message path is the behavior.
            warnings.append(f"failed to parse {path}: {exc}")
            parsed[key] = {}
    return parsed


def _read_log_observed(log_path: Path | None, warnings: list[str]) -> dict[str, Any]:
    observed: dict[str, Any] = {
        "simulation_complete": False,
        "simulated_time": None,
        "log_path": str(log_path) if log_path else None,
    }
    if log_path is None:
        warnings.append("missing log path")
        return observed
    if not log_path.exists():
        warnings.append(f"missing log file: {log_path}")
        return observed

    text = log_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Simulation is complete, simulated time:\s*([^\n\r]+)", text)
    if match:
        observed["simulation_complete"] = True
        observed["simulated_time"] = match.group(1).strip()
    if "Bus error" in text:
        warnings.append("log contains Bus error")
    if "MPI_INIT failed" in text:
        warnings.append("log contains MPI_INIT failed")
    if "ERROR" in text or "FAILED" in text:
        warnings.append("log contains ERROR/FAILED marker")
    return observed


def _event_summary(event_plan: dict[str, Any]) -> dict[str, Any]:
    for key in ("summary", "stats", "event_plan_summary"):
        summary = event_plan.get(key)
        if isinstance(summary, dict):
            return dict(summary)
    return {
        "m_tiles": event_plan.get("m_tiles"),
        "n_tiles": event_plan.get("n_tiles"),
        "k_tiles": event_plan.get("k_tiles"),
        "total_gemm_tasks": event_plan.get("total_gemm_tasks"),
    }


def _safe_div(numerator: Any, denominator: Any) -> float | None:
    try:
        den = float(denominator)
        if den == 0:
            return None
        return float(numerator) / den
    except (TypeError, ValueError):
        return None


def _derived_metrics(stats: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    execution = stats.get("execution", {})
    total_cycles = execution.get("total_cycles")
    total_tasks = mapping.get("total_gemm_tasks") or mapping.get("task_count")
    total_macro_tasks = mapping.get("total_macro_tasks") or total_tasks

    def first_metric(*names: str) -> Any:
        for name in names:
            if name in execution:
                return execution[name]
        return None

    compute = first_metric("compute_active_time", "exec_breakdown_compute_active_time")
    prefetch = first_metric("prefetch_wait_time", "exec_breakdown_prefetch_wait_time")
    writeback = first_metric("writeback_wait_time", "exec_breakdown_writeback_wait_time")
    control = first_metric("control_other_time", "exec_breakdown_control_other_time")
    denominator = None
    try:
        denominator = sum(float(x or 0) for x in [compute, prefetch, writeback, control])
    except (TypeError, ValueError):
        denominator = None

    def pct(value: Any) -> float | None:
        if denominator in (None, 0):
            return None
        try:
            return float(value or 0) / denominator * 100.0
        except (TypeError, ValueError):
            return None

    system_util = first_metric("system_array_utilization_pct", "exec_system_array_utilization_pct")
    worker_util = first_metric("array_utilization_pct", "exec_array_utilization_pct")
    util_gap = None
    try:
        util_gap = float(worker_util) - float(system_util)
    except (TypeError, ValueError):
        pass

    return {
        "cycles_per_gemm_task": _safe_div(total_cycles, total_tasks),
        "cycles_per_macro_task": _safe_div(total_cycles, total_macro_tasks),
        "compute_active_pct": pct(compute),
        "prefetch_wait_pct": pct(prefetch),
        "writeback_wait_pct": pct(writeback),
        "control_other_pct": pct(control),
        "system_vs_worker_utilization_gap_pct": util_gap,
    }


def build_golem_single_run_report(
    *,
    artifact_root: str | Path,
    event_plan_path: str | Path,
    stats_dir: str | Path,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    artifact_root = Path(artifact_root)
    event_plan_path = Path(event_plan_path)
    stats_dir = Path(stats_dir)
    log_path_obj = Path(log_path) if log_path is not None else None

    warnings: list[str] = []
    contract_path = artifact_root / "contracts" / "matmul_op_desc_resolved.json"
    env_mapping_path = artifact_root / "contracts" / "matmul_env_mapping_v1.json"

    contract = _read_json(contract_path)
    env_mapping = _read_json(env_mapping_path) if env_mapping_path.exists() else {}
    if not env_mapping_path.exists():
        warnings.append(f"missing env mapping file: {env_mapping_path}")

    event_plan = _read_json(event_plan_path)
    mapping = _event_summary(event_plan)
    stats = {}
    stats.update(_read_optional_csvs(stats_dir, METRIC_CSVS, _read_metric_csv, warnings))
    stats.update(_read_optional_csvs(stats_dir, SUMMARY_CSVS, _read_summary_csv, warnings))

    observed = _read_log_observed(log_path_obj, warnings)
    if not observed["simulation_complete"]:
        warnings.append("simulation completion marker not found")

    status = "ok" if not warnings else "ok_with_warnings"
    report = {
        "mode": "golem_single_run_stats_report",
        "status": status,
        "artifact_root": str(artifact_root),
        "stats_dir": str(stats_dir),
        "contract": contract,
        "env_mapping": env_mapping,
        "mapping": mapping,
        "observed": observed,
        "stats": stats,
        "derived": _derived_metrics(stats, mapping),
        "model": {
            "status": "not_calibrated",
            "reason": "single-run descriptive report only; no sweep or fitted model",
        },
        "warnings": warnings,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a structured report from one Golem SST run.")
    parser.add_argument("--artifact-root", required=True, help="Golem artifact root containing contracts/.")
    parser.add_argument("--event-plan", required=True, help="Golem event/mapping plan JSON.")
    parser.add_argument("--stats-dir", required=True, help="Stats directory for one run.")
    parser.add_argument("--log", required=True, help="SST log path for the same run.")
    parser.add_argument("--output", required=True, help="Output report JSON path.")
    args = parser.parse_args()

    report = build_golem_single_run_report(
        artifact_root=args.artifact_root,
        event_plan_path=args.event_plan,
        stats_dir=args.stats_dir,
        log_path=args.log,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"report: {output}")
    print(f"status: {report['status']}")
    if report["warnings"]:
        print(f"warnings: {len(report['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
