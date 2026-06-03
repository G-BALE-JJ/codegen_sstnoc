# CIM-TileIR 原型阶段汇总

本文档汇总当前 `codegen_sstnoc` 中 RISC-V CIM 2D-mesh 方向已经完成的原型、当前边界，以及后续进入 architecture-aware planner / simulator 前必须补齐的架构规格信息。

## 1. 当前定位

当前项目仍处于编译器侧原型阶段，目标不是模拟真实 CIM mesh，也不是生成 RISC-V ELF，而是验证以下链路是否能闭合：

```text
TileLang GEMM
    ↓
CIM-TileIR JSON
    ↓
abstract event expander
    ↓
per-output-tile task / event skeleton
```

其中 `abstract event expander` 只负责把 `CIM-TileIR` 展开成理想化事件骨架，并做基本统计。它不是 cycle-accurate simulator，也不代表真实硬件性能。

## 2. 已完成能力

### 2.1 CIM-TileIR schema / builder / checker

已实现 `tilelang_cim` 原型包，支持：

- `build_gemm_ir`：从静态 GEMM 参数生成 `CIM-TileIR` dict。
- `validate_cim_tile_ir`：检查 mesh、tile、A/B/C tensor、mapping、program op 顺序和 `loop_k` body。
- `to_json_text` / `write_json`：导出稳定 JSON。

对应文件：

- `tilelang_cim/builder.py`
- `tilelang_cim/checker.py`
- `tilelang_cim/json_export.py`
- `examples/gemm_ir.py`
- `tests/test_cim_tile_ir.py`
- `tests/test_gemm_ir_example.py`

### 2.2 TileLang GEMM extractor MVP

已实现窄模板 extractor，支持从标准静态 GEMM 的 TileLang 源码或 TileLang `PrimFunc.script()` 中提取：

- A/B/C tensor shape 和 dtype。
- BM/BN/BK。
- `pipeline_stages`。
- `T.gemm` 是否存在。
- lowering 后的 `T.match_buffer`、`T.alloc_buffer`、`T.serial`、`T.gemm` 形态。

对应文件：

- `tilelang_cim/extractor.py`
- `examples/extract_tilelang_gemm.py`
- `tests/fixtures/tilelang_gemm_fixture.py`
- `tests/test_tilelang_gemm_extractor.py`
- `tests/test_extract_tilelang_gemm_example.py`

当前不支持：

- 转置 GEMM。
- 动态 shape。
- 复杂 fusion。
- 非标准 TileOPs GEMM 变体。
- 完整 TileLang pass pipeline。

### 2.3 Abstract event expander MVP

已实现 `build_event_plan`，可以从 `CIM-TileIR` 生成抽象事件骨架：

- per-output-tile task。
- core 映射。
- `clear_acc`。
- 每个 K tile 的 `dma_load A`、`dma_load B`、`cim_gemm`。
- 最终 `dma_store C`。
- 粗略统计：`output_tiles`、`total_cores`、`active_cores`、`core_utilization`、`dma_load_bytes`、`dma_store_bytes`、`cim_gemm_ops`、`macs`。

对应文件：

- `tilelang_cim/event_planner.py`
- `examples/plan_events.py`
- `tests/test_event_planner.py`
- `tests/test_plan_events_example.py`

当前 `estimated_cycles` 固定为 0，不代表真实硬件周期。

## 3. 当前可运行链路

从 TileLang GEMM fixture 提取 `CIM-TileIR JSON`：

```bash
python examples/extract_tilelang_gemm.py \
  tests/fixtures/tilelang_gemm_fixture.py \
  --output /tmp/tilelang_gemm.cimtile.json \
  --mesh-w 4 --mesh-h 2
```

从 `CIM-TileIR JSON` 生成 event plan：

```bash
python examples/plan_events.py \
  /tmp/tilelang_gemm.cimtile.json \
  --output /tmp/tilelang_gemm.eventplan.json
```

运行测试：

```bash
python -m pytest tests -q
```

文档检查：

```bash
bash scripts/check_docs.sh
```

## 4. 为什么当前 event expander 仍然有意义

在没有真实 mesh 架构细节时，当前 expander 不能评估真实性能，但仍然可以验证 IR 是否具备下游消费所需的最小信息：

- 能否从 tensor shape 和 tile shape 展开 output tile grid。
- 能否从 K/BK 展开 K-loop。
- 每个 output tile 是否能映射到某个抽象 core。
- load / compute / store 事件是否能形成完整顺序。
- DMA bytes 和 MAC 数是否能从 IR 中静态计算。
- 当前 mapping policy 是否导致明显的 core utilization 问题。

因此它当前的定位是：

```text
IR sanity consumer / abstract event skeleton generator
```

而不是：

```text
architecture-aware simulator
```

## 5. 当前不具备的能力

当前原型不能回答以下问题：

- 真实执行周期是多少。
- NoC 是否拥塞。
- DMA 和 CIM 计算能否 overlap。
- local SRAM / accumulator 是否足够。
- CIM array 支持的 tile shape 是否匹配。
- RISC-V 指令序列如何生成。
- OS loader / runtime 如何启动多核执行。
- 真实 dataflow / mapping 是否最优。

这些问题需要后续 architecture spec 和执行侧实现。

## 6. 后续 architecture spec 需要补齐的信息

进入 architecture-aware planner 前，建议先定义 `CIMArchitectureSpec`。第一版可以是 JSON/YAML，也可以是 Python dict/dataclass。建议至少包含以下字段。

### 6.1 Mesh / Core

- `mesh.w` / `mesh.h`。
- `core_id` 与 `(core_x, core_y)` 的映射。
- 是否有 cluster / tile group 层级。
- 每个 core 是否能独立执行一个 output tile。
- 一个 core 是否允许同时保留多个 tile 的 partial sum。

### 6.2 Memory

- 每个 core 的 local SRAM / scratchpad 容量。
- accumulator buffer 容量。
- A/B shared buffer 是否与 C accumulator 分离。
- SRAM bank 数、bank width、访问冲突模型是否需要建模。
- global memory 地址空间和 alignment 约束。

### 6.3 DMA

- DMA load/store 的最小粒度。
- DMA bandwidth，例如 bytes/cycle。
- DMA startup latency。
- 是否支持 2D DMA / strided DMA。
- DMA 与 CIM compute 是否能 overlap。
- 是否有 in-flight DMA 数量限制。

### 6.4 CIM Primitive

- 支持的 input dtype，例如 int8 / int4 / fp16。
- accumulator dtype，例如 int32。
- `cim_gemm` 支持的 BM/BN/BK 或 micro-tile shape。
- 单次 `cim_gemm` latency 或 throughput。
- 是否支持 transpose A/B。
- 是否支持 accumulate / clear / saturation / quantization。
- CIM array 数量及每个 core 可并行执行的 primitive 数。

### 6.5 NoC / Communication

- NoC topology，例如 2D mesh。
- routing policy，例如 XY routing。
- link bandwidth。
- hop latency。
- 是否支持 unicast / broadcast / multicast。
- 是否需要建模 NoC contention。
- core 间通信是否出现在第一版 GEMM dataflow 中。

### 6.6 Synchronization

- barrier 粒度：core、row、column、cluster、global。
- barrier latency。
- 是否需要 producer-consumer dependency。
- 是否支持 async event / fence。

### 6.7 Mapping / Dataflow

- 第一版 dataflow 是否固定为 output-stationary。
- output tile 到 core 的映射策略。
- 当 output tile 数大于 core 数时如何排队。
- 当 output tile 数小于 core 数时是否允许 split-K / split-N / split-M 提升利用率。
- 是否允许一个 output tile 跨多个 core 协作。

### 6.8 Cycle Model

- 第一版 cycle model 类型：无、常数、公式、表驱动。
- DMA cycle 公式。
- CIM compute cycle 公式。
- store cycle 公式。
- overlap 策略：串行、load/compute overlap、double-buffer。
- NoC cycle 是否纳入。

## 7. 建议的 architecture spec 草案

第一版可以从如下 JSON 开始：

```json
{
  "name": "toy_cim_mesh_v0",
  "mesh": {
    "w": 4,
    "h": 2,
    "core_id": "row_major"
  },
  "core": {
    "local_sram_bytes": 65536,
    "accumulator_bytes": 16384,
    "max_resident_output_tiles": 1
  },
  "dma": {
    "bytes_per_cycle": 16,
    "startup_cycles": 20,
    "supports_2d": false,
    "overlap_with_compute": false
  },
  "cim": {
    "input_dtypes": ["int8"],
    "acc_dtype": "int32",
    "tile_m": 64,
    "tile_n": 64,
    "tile_k": 32,
    "cycles_per_cim_gemm": 128,
    "supports_transpose_a": false,
    "supports_transpose_b": false
  },
  "noc": {
    "enabled": false,
    "topology": "2d_mesh",
    "routing": "xy",
    "link_bytes_per_cycle": 16,
    "hop_latency": 1
  },
  "sync": {
    "barrier_cycles": 0
  },
  "mapping": {
    "dataflow": "output_stationary",
    "policy": "tile_by_bx_mod_mesh"
  },
  "cycle_model": {
    "type": "none"
  }
}
```

在没有真实架构参数前，这个 spec 应命名为 `toy_*` 或 `abstract_*`，避免误认为是硬件承诺。

## 8. 下一阶段建议

建议下一阶段不要继续扩大性能模型，而是先做：

```text
CIMArchitectureSpec schema + checker
```

最小目标：

- 能读取 architecture spec JSON。
- 校验 `CIM-TileIR` 的 tile/dtype/buffer 需求是否满足 spec。
- 将当前 `estimated_cycles=0` 保持为默认。
- 只有当 spec 明确提供 DMA/CIM cycle 参数时，才输出粗略 cycle estimate。

这样可以把当前原型从：

```text
TileLang GEMM -> IR -> event skeleton
```

推进到：

```text
TileLang GEMM -> IR -> architecture-aware legality check
```

再之后才适合继续做 mapping policy、NoC、pipeline overlap 或 runtime/ELF。
