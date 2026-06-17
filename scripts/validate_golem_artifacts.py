#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any


REQUIRED_ENV_KEYS = [
    "GOLEM_ARRAY_INPUT_SIZE",
    "GOLEM_ARRAY_OUTPUT_SIZE",
    "GOLEM_NUM_ARRAYS",
    "GOLEM_MATMUL_M",
    "GOLEM_MATMUL_N",
    "GOLEM_MATMUL_K",
    "GOLEM_MATMUL_BLOCK_M",
    "GOLEM_MATMUL_BLOCK_N",
    "GOLEM_MATMUL_BLOCK_K",
    "GOLEM_MATMUL_DTYPE",
    "GOLEM_MATMUL_LAYOUT",
    "GOLEM_MATMUL_TRANSPOSE_A",
    "GOLEM_MATMUL_TRANSPOSE_B",
    "GOLEM_GEMM_M",
    "GOLEM_GEMM_N",
    "GOLEM_GEMM_K",
    "GOLEM_GEMM_BLOCK_M",
    "GOLEM_GEMM_BLOCK_N",
    "GOLEM_GEMM_BLOCK_K",
]


EXPECTED_MAPPING = {
    "m": "GOLEM_MATMUL_M",
    "n": "GOLEM_MATMUL_N",
    "k": "GOLEM_MATMUL_K",
    "block_m": "GOLEM_MATMUL_BLOCK_M",
    "block_n": "GOLEM_MATMUL_BLOCK_N",
    "block_k": "GOLEM_MATMUL_BLOCK_K",
    "dtype": "GOLEM_MATMUL_DTYPE",
    "layout": "GOLEM_MATMUL_LAYOUT",
    "transpose_a": "GOLEM_MATMUL_TRANSPOSE_A",
    "transpose_b": "GOLEM_MATMUL_TRANSPOSE_B",
}


FIELD_TYPES = {
    "m": int,
    "n": int,
    "k": int,
    "block_m": int,
    "block_n": int,
    "block_k": int,
    "dtype": str,
    "layout": str,
    "transpose_a": int,
    "transpose_b": int,
}


def validate_golem_artifacts(
    artifact_root: str | Path,
    hardware_tests_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(artifact_root)
    paths = {
        "env": root / "golem_sst.env",
        "resolved_contract": root / "contracts" / "matmul_op_desc_resolved.json",
        "env_mapping": root / "contracts" / "matmul_env_mapping_v1.json",
    }
    report: dict[str, Any] = {
        "mode": "golem_artifact_validation",
        "artifact_root": str(root),
        "hardware_tests_dir": str(hardware_tests_dir) if hardware_tests_dir is not None else None,
        "ok": False,
        "checks": {},
        "paths": {name: str(path) for name, path in paths.items()},
        "env": {},
        "resolved_contract": {},
        "env_mapping": {},
        "warnings": [],
        "errors": [],
    }

    _check_required_files(paths, report)
    if report["errors"]:
        return report

    env = _read_env(paths["env"], report)
    resolved = _read_json_object(paths["resolved_contract"], "resolved_contract", report)
    mapping = _read_json_object(paths["env_mapping"], "env_mapping", report)
    report["env"] = env
    report["resolved_contract"] = resolved
    report["env_mapping"] = mapping
    if report["errors"]:
        return report

    _check_required_env(env, report)
    _check_mapping(mapping, report)
    _check_resolved_contract(resolved, report)
    _check_env_matches_resolved(env, resolved, report)
    _check_backend_shape_constraints(env, resolved, report)
    _check_legacy_aliases(env, report)

    report["ok"] = not report["errors"]
    return report


def _check_required_files(paths: dict[str, Path], report: dict[str, Any]) -> None:
    missing = [f"{path.name} is missing at {path}" for path in paths.values() if not path.is_file()]
    if missing:
        report["checks"]["required_files"] = "fail"
        report["errors"].extend(missing)
    else:
        report["checks"]["required_files"] = "ok"


def _read_env(path: Path, report: dict[str, Any]) -> dict[str, str]:
    env: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        report["errors"].append(f"cannot read {path}: {exc}")
        return env

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not stripped.startswith("export "):
            report["warnings"].append(f"{path}:{line_no}: ignored non-export line")
            continue
        assignment = stripped[len("export ") :]
        if "=" not in assignment:
            report["warnings"].append(f"{path}:{line_no}: ignored export without assignment")
            continue
        key, raw_value = assignment.split("=", 1)
        env[key] = _resolve_env_value(raw_value, env)
    return env


def _resolve_env_value(raw_value: str, env: dict[str, str]) -> str:
    tokens = shlex.split(raw_value)
    value = tokens[0] if tokens else ""
    if value.startswith("$"):
        return env.get(value[1:], value)
    return value


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


def _check_required_env(env: dict[str, str], report: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_ENV_KEYS if key not in env]
    if missing:
        report["checks"]["required_env"] = "fail"
        report["errors"].append("golem_sst.env missing " + ", ".join(missing))
    else:
        report["checks"]["required_env"] = "ok"


def _check_mapping(mapping: dict[str, Any], report: dict[str, Any]) -> None:
    mismatches = [
        f"{field} maps to {mapping.get(field)!r}, expected {env_key!r}"
        for field, env_key in EXPECTED_MAPPING.items()
        if mapping.get(field) != env_key
    ]
    if mismatches:
        report["checks"]["env_mapping_contract"] = "fail"
        report["errors"].extend(mismatches)
    else:
        report["checks"]["env_mapping_contract"] = "ok"


def _check_resolved_contract(resolved: dict[str, Any], report: dict[str, Any]) -> None:
    errors: list[str] = []
    for field, field_type in FIELD_TYPES.items():
        if field not in resolved:
            errors.append(f"resolved contract missing {field}")
            continue
        if not isinstance(resolved[field], field_type):
            errors.append(f"resolved {field} must be {field_type.__name__}")
    if errors:
        report["checks"]["resolved_contract_schema"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["resolved_contract_schema"] = "ok"


def _check_env_matches_resolved(env: dict[str, str], resolved: dict[str, Any], report: dict[str, Any]) -> None:
    errors: list[str] = []
    for field, env_key in EXPECTED_MAPPING.items():
        if field not in resolved or env_key not in env:
            continue
        expected = resolved[field]
        actual = _coerce_env_value(env[env_key], type(expected))
        if actual != expected:
            errors.append(f"{env_key}={env[env_key]} does not match resolved {field}={expected}")
    if errors:
        report["checks"]["env_matches_resolved_contract"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["env_matches_resolved_contract"] = "ok"


def _check_backend_shape_constraints(env: dict[str, str], resolved: dict[str, Any], report: dict[str, Any]) -> None:
    errors: list[str] = []
    array_input = _optional_int(env.get("GOLEM_ARRAY_INPUT_SIZE"))
    array_output = _optional_int(env.get("GOLEM_ARRAY_OUTPUT_SIZE"))
    num_arrays = _optional_int(env.get("GOLEM_NUM_ARRAYS"))

    if array_input is not None and resolved.get("block_k") != array_input:
        errors.append(f"block_k={resolved.get('block_k')} does not match GOLEM_ARRAY_INPUT_SIZE={array_input}")
    if array_output is not None and resolved.get("block_m") != array_output:
        errors.append(f"block_m={resolved.get('block_m')} does not match GOLEM_ARRAY_OUTPUT_SIZE={array_output}")
    if num_arrays is not None and isinstance(resolved.get("block_n"), int) and resolved["block_n"] > num_arrays:
        errors.append(f"block_n={resolved['block_n']} exceeds GOLEM_NUM_ARRAYS={num_arrays}")

    if errors:
        report["checks"]["backend_shape_constraints"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["backend_shape_constraints"] = "ok"


def _check_legacy_aliases(env: dict[str, str], report: dict[str, Any]) -> None:
    aliases = {
        "GOLEM_GEMM_M": "GOLEM_MATMUL_M",
        "GOLEM_GEMM_N": "GOLEM_MATMUL_N",
        "GOLEM_GEMM_K": "GOLEM_MATMUL_K",
        "GOLEM_GEMM_BLOCK_M": "GOLEM_MATMUL_BLOCK_M",
        "GOLEM_GEMM_BLOCK_N": "GOLEM_MATMUL_BLOCK_N",
        "GOLEM_GEMM_BLOCK_K": "GOLEM_MATMUL_BLOCK_K",
    }
    errors = [
        f"{alias}={env.get(alias)} does not match {target}={env.get(target)}"
        for alias, target in aliases.items()
        if alias in env and target in env and env[alias] != env[target]
    ]
    if errors:
        report["checks"]["legacy_aliases"] = "fail"
        report["errors"].extend(errors)
    else:
        report["checks"]["legacy_aliases"] = "ok"


def _coerce_env_value(value: str, target_type: type) -> Any:
    if target_type is int:
        return int(value)
    return value


def _optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def main() -> None:
    args = _parse_args()
    report = validate_golem_artifacts(args.artifact_root, args.hardware_tests_dir)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if not report["ok"]:
        raise SystemExit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated Golem SST env/contract artifacts offline.")
    parser.add_argument("--artifact-root", type=Path, required=True, help="Artifact root generated by export_golem_sst.py.")
    parser.add_argument(
        "--hardware-tests-dir",
        type=Path,
        default=None,
        help="Optional path to RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests for report context.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report output path.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
