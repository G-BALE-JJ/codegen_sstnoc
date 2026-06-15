# CIMArchitectureSpec schema

`CIMArchitectureSpec` 是 architecture-aware event planner 的输入。它描述 toy CIM mesh 的最小架构参数，用来校验 `CIM-TileIR` 是否能放入目标架构，并为 `serial_formula_v0` 提供 cycle estimate 参数。

当前 spec 不是真实硬件配置，也不是 simulator 配置全集。第一版目标是建立可检查、可测试、可解释的编译器侧约束。

## 示例

当前示例位于：

```text
examples/architecture/toy_cim_mesh_v0.json
```

## 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 架构规格名称 |
| `mesh` | object | mesh 拓扑 |
| `core` | object | 单 core 本地资源 |
| `dma` | object | DMA 粗略模型 |
| `cim` | object | CIM primitive 约束 |
| `noc` | object | NoC 占位字段 |
| `sync` | object | synchronization 占位字段 |
| `cycle_model` | object | cycle model 选择 |

## mesh

| 字段 | 类型 | 说明 |
|------|------|------|
| `w` | positive int | mesh 宽度 |
| `h` | positive int | mesh 高度 |
| `core_id` | string | 当前只支持 `row_major` |

`row_major` 的 core id 公式为：

```text
core_id = y * mesh_w + x
```

## core

| 字段 | 类型 | 说明 |
|------|------|------|
| `local_sram_bytes` | positive int | 每 core local SRAM / scratchpad 容量 |
| `accumulator_bytes` | positive int | 每 core accumulator 容量 |
| `max_resident_output_tiles` | positive int | 每 core 同时驻留 output tile 数，当前只作为 schema 字段 |

当前联合校验会检查：

```text
pipeline_stages * (A_tile_bytes + B_tile_bytes) <= local_sram_bytes
C_tile_bytes <= accumulator_bytes
```

## dma

| 字段 | 类型 | 说明 |
|------|------|------|
| `bytes_per_cycle` | positive int | toy DMA 带宽 |
| `startup_cycles` | non-negative int | 每次 DMA 启动开销 |
| `alignment_bytes` | positive int | DMA bytes 对齐要求 |
| `supports_2d` | bool | 当前只记录，不建模 2D DMA |
| `overlap_with_compute` | bool | 当前只记录，`serial_formula_v0` 不做 overlap |

DMA cycle 公式：

```text
dma_cycles = startup_cycles + ceil(bytes / bytes_per_cycle)
```

## cim

| 字段 | 类型 | 说明 |
|------|------|------|
| `input_dtypes` | string list | 支持的 A/B 输入 dtype |
| `acc_dtype` | string | accumulator / C dtype |
| `tile_m` | positive int | 支持的 GEMM M tile |
| `tile_n` | positive int | 支持的 GEMM N tile |
| `tile_k` | positive int | 支持的 GEMM K tile |
| `cycles_per_cim_gemm` | positive int | 单次 `cim_gemm` toy cycle |
| `supports_transpose_a` | bool | 当前必须为 false |
| `supports_transpose_b` | bool | 当前必须为 false |

当前联合校验要求：

```text
BM == tile_m
BN == tile_n
BK == tile_k
A.dtype and B.dtype in input_dtypes
C.dtype == acc_dtype
```

## noc / sync

当前 `noc.enabled` 和 `sync.barrier_supported` 只是占位字段。第一版 architecture-aware planner 不建模 NoC routing、contention、barrier 或 producer-consumer dependency。

## cycle_model

当前只支持：

```text
serial_formula_v0
```

该模型串行累加每个 output tile 的事件：

```text
clear_acc
for each K tile:
  dma_load A
  dma_load B
  cim_gemm
dma_store C
```

全局 `estimated_cycles` 取所有 core 累计 cycles 的最大值。

## 当前边界

- 不代表真实 CIM mesh 性能。
- 不建模 DMA / compute overlap。
- 不建模 NoC。
- 不建模 SRAM bank conflict。
- 不建模 barrier。
- 不支持 micro-tiling 或 tile shape 自动拆分。
