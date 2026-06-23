TILEOPS_LIKE_MATMUL_SOFTMAX_SOURCE = """
import tilelang
import tilelang.language as T
from tileops.softmax import SoftmaxFwdOp

M = 64
N = 64
K = 64
DTYPE = "float32"


@tilelang.jit(out_idx=[-1], compile_flags=["-O3"])
def build_matmul_softmax(
    block_m: int = 64,
    block_n: int = 64,
    block_k: int = 64,
    num_stages: int = 2,
    threads: int = 128,
):
    softmax = SoftmaxFwdOp(N=block_n, dtype=DTYPE, dim=-1)

    @T.prim_func
    def main(
        A: T.Tensor((M, K), DTYPE),
        B: T.Tensor((K, N), DTYPE),
        S: T.Tensor((M, N), DTYPE),
        P: T.Tensor((M, N), DTYPE),
    ) -> None:
        with T.Kernel(T.ceildiv(N, block_n), T.ceildiv(M, block_m), threads=threads) as (bx, by):
            a_shared = T.alloc_shared((block_m, block_k), DTYPE)
            b_shared = T.alloc_shared((block_k, block_n), DTYPE)
            s_local = T.alloc_fragment((block_m, block_n), DTYPE)
            s_shared = T.alloc_shared((block_m, block_n), DTYPE)

            T.clear(s_local)

            for ko in T.Pipelined(T.ceildiv(K, block_k), num_stages=num_stages):
                T.copy(A[by * block_m, ko * block_k], a_shared)
                T.copy(B[ko * block_k, bx * block_n], b_shared)
                T.gemm(a_shared, b_shared, s_local, False, False)

            T.copy(s_local, s_shared)
            T.copy(s_shared, S[by * block_m, bx * block_n])
            softmax(S[by * block_m, bx * block_n], P[by * block_m, bx * block_n])

    return main
"""
