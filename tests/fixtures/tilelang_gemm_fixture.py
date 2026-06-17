def tilelang_gemm_fixture():
    import tilelang.language as T

    @T.prim_func
    def gemm(
        a: T.Tensor((1024, 128), "float32"),
        b: T.Tensor((128, 1024), "float32"),
        c: T.Tensor((1024, 1024), "float32"),
    ) -> None:
        with T.Kernel(T.ceildiv(1024, 64), T.ceildiv(1024, 64), threads=128) as (bx, by):
            a_shared = T.alloc_shared((64, 64), "float32")
            b_shared = T.alloc_shared((64, 64), "float32")
            c_local = T.alloc_fragment((64, 64), "float32")

            T.clear(c_local)

            for ko in T.Pipelined(T.ceildiv(128, 64), num_stages=2):
                T.copy(a[by * 64, ko * 64], a_shared)
                T.copy(b[ko * 64, bx * 64], b_shared)
                T.gemm(a_shared, b_shared, c_local)

            T.copy(c_local, c[by * 64, bx * 64])

    return gemm
