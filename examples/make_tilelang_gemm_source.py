from __future__ import annotations

import argparse
import sys
from pathlib import Path


SUPPORTED_DTYPES = ("float32",)


def main() -> None:
    args = _parse_args()
    _validate_args(args)
    source = build_tilelang_gemm_source(
        m=args.m,
        n=args.n,
        k=args.k,
        bm=args.bm,
        bn=args.bn,
        bk=args.bk,
        dtype=args.dtype,
        num_stages=args.num_stages,
        threads=args.threads,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source, encoding="utf-8")
    print(f"tilelang_source: {args.output}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a static TileLang GEMM source file for the CIM-TileIR frontend."
    )
    parser.add_argument("--m", type=int, default=1024, help="GEMM M dimension. Default: 1024")
    parser.add_argument("--n", type=int, default=1024, help="GEMM N dimension. Default: 1024")
    parser.add_argument("--k", type=int, default=128, help="GEMM K dimension. Default: 128")
    parser.add_argument("--bm", type=int, default=64, help="Tile M dimension. Default: 64")
    parser.add_argument("--bn", type=int, default=64, help="Tile N dimension. Default: 64")
    parser.add_argument("--bk", type=int, default=64, help="Tile K dimension. Default: 64")
    parser.add_argument("--dtype", choices=SUPPORTED_DTYPES, default="float32")
    parser.add_argument("--num-stages", type=int, default=2, help="T.Pipelined num_stages. Default: 2")
    parser.add_argument("--threads", type=int, default=128, help="T.Kernel thread count. Default: 128")
    parser.add_argument("--output", type=Path, required=True, help="Output Python source path.")
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    positive_fields = ("m", "n", "k", "bm", "bn", "bk", "num_stages", "threads")
    for field in positive_fields:
        if getattr(args, field) <= 0:
            raise SystemExit(f"[ERROR] --{field.replace('_', '-')} must be positive")

    divisibility = (("m", "bm"), ("n", "bn"), ("k", "bk"))
    for dim_field, tile_field in divisibility:
        dim_value = getattr(args, dim_field)
        tile_value = getattr(args, tile_field)
        if dim_value % tile_value != 0:
            raise SystemExit(
                f"[ERROR] --{dim_field}={dim_value} must be divisible by --{tile_field}={tile_value}"
            )


def build_tilelang_gemm_source(
    *,
    m: int,
    n: int,
    k: int,
    bm: int,
    bn: int,
    bk: int,
    dtype: str,
    num_stages: int,
    threads: int,
) -> str:
    return f'''"""Generated TileLang GEMM source.

This file is an input fixture for codegen_sstnoc:
TileLang source -> CIM-TileIR -> Golem SST artifacts.
"""


def tilelang_gemm_fixture():
    import tilelang.language as T

    @T.prim_func
    def gemm(
        a: T.Tensor(({m}, {k}), "{dtype}"),
        b: T.Tensor(({k}, {n}), "{dtype}"),
        c: T.Tensor(({m}, {n}), "{dtype}"),
    ) -> None:
        with T.Kernel(T.ceildiv({n}, {bn}), T.ceildiv({m}, {bm}), threads={threads}) as (bx, by):
            a_shared = T.alloc_shared(({bm}, {bk}), "{dtype}")
            b_shared = T.alloc_shared(({bk}, {bn}), "{dtype}")
            c_local = T.alloc_fragment(({bm}, {bn}), "{dtype}")

            T.clear(c_local)

            for ko in T.Pipelined(T.ceildiv({k}, {bk}), num_stages={num_stages}):
                T.copy(a[by * {bm}, ko * {bk}], a_shared)
                T.copy(b[ko * {bk}, bx * {bn}], b_shared)
                T.gemm(a_shared, b_shared, c_local)

            T.copy(c_local, c[by * {bm}, bx * {bn}])

    return gemm
'''


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
