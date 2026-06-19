from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tilelang_cim import extract_gemm_ir_from_tir, validate_cim_tile_ir, write_json


def main() -> None:
    args = _parse_args()
    prim_func = _load_prim_func(args.source, args.factory)
    ir = extract_gemm_ir_from_tir(prim_func, mesh_w=args.mesh_w, mesh_h=args.mesh_h)

    errors = validate_cim_tile_ir(ir)
    if errors:
        raise SystemExit("Invalid CIM-TileIR:\n" + "\n".join(f"- {error}" for error in errors))

    write_json(ir, args.output)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract CIM-TileIR JSON from a TileLang-generated TIR PrimFunc.")
    parser.add_argument("source", type=Path, help="Python source file containing a TileLang PrimFunc factory.")
    parser.add_argument("--output", type=Path, default=Path("tilelang_gemm.cimtile.json"))
    parser.add_argument("--mesh-w", type=int, default=8)
    parser.add_argument("--mesh-h", type=int, default=8)
    parser.add_argument(
        "--factory",
        default=None,
        help="Callable name returning a PrimFunc. If omitted, the first zero-argument callable returning a TIR-like object is used.",
    )
    return parser.parse_args()


def _load_prim_func(source: Path, factory: str | None) -> Any:
    module = _load_module(source)
    if factory is not None:
        candidate = getattr(module, factory, None)
        if candidate is None or not callable(candidate):
            raise ValueError(f"Factory {factory!r} was not found or is not callable in {source}")
        return _call_factory(candidate, factory)

    candidates: list[str] = []
    for name, value in vars(module).items():
        if name.startswith("_") or not callable(value):
            continue
        candidates.append(name)
        try:
            prim_func = value()
        except TypeError:
            continue
        if _looks_like_tir_prim_func(prim_func):
            return prim_func

    raise ValueError(
        "Unable to find a zero-argument callable that returns a TIR PrimFunc. "
        f"Checked callables: {', '.join(candidates) if candidates else '<none>'}"
    )


def _load_module(source: Path) -> Any:
    module_name = f"_tilelang_tir_source_{abs(hash(source.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise ValueError(f"Unable to load Python source: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _call_factory(factory, name: str) -> Any:
    try:
        prim_func = factory()
    except TypeError as exc:
        raise ValueError(f"Factory {name!r} must be callable without arguments") from exc
    if not _looks_like_tir_prim_func(prim_func):
        raise ValueError(f"Factory {name!r} did not return a TIR PrimFunc-like object")
    return prim_func


def _looks_like_tir_prim_func(value: Any) -> bool:
    return hasattr(value, "body") and hasattr(value, "buffer_map")


if __name__ == "__main__":
    main()
