TILEOPS_LIKE_GEMM_SOURCE = """
import tilelang
import tilelang.language as T

M = 1024
N = 1024
K = 128
DTYPE = "float32"
ACCUM_DTYPE = "float32"


@tilelang.jit(out_idx=[-1], compile_flags=["-O3"])
def build_gemm(block_m: int = 64, block_n: int = 64, block_k: int = 64, num_stages: int = 2, threads: int = 128):
    a_shape = (M, K)
    b_shape = (K, N)
    a_shared_shape = (block_m, block_k)
    b_shared_shape = (block_k, block_n)

    @T.prim_func
    def main(
        lhs: T.Tensor(a_shape, DTYPE),
        rhs: T.Tensor(b_shape, DTYPE),
        out: T.Tensor((M, N), DTYPE),
    ) -> None:
        with T.Kernel(T.ceildiv(N, block_n), T.ceildiv(M, block_m), threads=threads) as (bx, by):
            lhs_shared = T.alloc_shared(a_shared_shape, DTYPE)
            rhs_shared = T.alloc_shared(b_shared_shape, DTYPE)
            out_local = T.alloc_fragment((block_m, block_n), ACCUM_DTYPE)
            out_shared = T.alloc_shared((block_m, block_n), DTYPE)

            T.annotate_layout({})
            T.use_swizzle(10, enable=True)
            T.clear(out_local)

            for ko in T.Pipelined(T.ceildiv(K, block_k), num_stages=num_stages):
                T.copy(lhs[by * block_m, ko * block_k], lhs_shared)
                T.copy(rhs[ko * block_k, bx * block_n], rhs_shared)
                T.gemm(lhs_shared, rhs_shared, out_local, False, False)

            T.copy(out_local, out_shared)
            T.copy(out_shared, out[by * block_m, bx * block_n])

    return main
"""
