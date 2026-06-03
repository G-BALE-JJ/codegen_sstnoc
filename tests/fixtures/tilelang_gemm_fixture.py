def tilelang_gemm_fixture():
    import tilelang.language as T

    @T.prim_func
    def gemm(
        a: T.Tensor((256, 64), "int8"),
        b: T.Tensor((64, 128), "int8"),
        c: T.Tensor((256, 128), "int32"),
    ) -> None:
        with T.Kernel(T.ceildiv(128, 64), T.ceildiv(256, 64), threads=128) as (bx, by):
            a_shared = T.alloc_shared((64, 32), "int8")
            b_shared = T.alloc_shared((32, 64), "int8")
            c_local = T.alloc_fragment((64, 64), "int32")

            T.clear(c_local)

            for ko in T.Pipelined(T.ceildiv(64, 32), num_stages=2):
                T.copy(a[by * 64, ko * 32], a_shared)
                T.copy(b[ko * 32, bx * 64], b_shared)
                T.gemm(a_shared, b_shared, c_local)

            T.copy(c_local, c[by * 64, bx * 64])

    return gemm
