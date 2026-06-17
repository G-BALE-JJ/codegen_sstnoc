# CIM-TileIR 原型阶段汇总

本文档汇总 `codegen_sstnoc` 当前仍在维护的 CIM-TileIR 原型能力。当前主线已经收敛为：

```text
All frontends
    ↓
CIM-TileIR
    ↓
Golem SST backend exporter
    ↓
golem_sst.env / contracts / hardware loading environment
```

TileLang 是第一个前端，Golem SST 是第一个真实硬件后端。toy architecture、abstract event planner 和 `serial_formula_v0` 已从当前主线移除。

## 1. 当前定位

当前项目仍处于编译器侧原型阶段，目标不是模拟抽象 CIM mesh，也不是生成 RISC-V ELF，而是验证以下链路是否能闭合：

```text
TileLang GEMM / static GEMM params
    ↓
CIM-TileIR JSON
    ↓
Golem backend legality checks
    ↓
Golem SST env/contract artifacts
```

`CIM-TileIR` 是前端语言与硬件后端之间的唯一接口契约。前端不直接生成 `GOLEM_*` 环境变量；Golem 后端也不直接依赖 TileLang 语法。

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

### 2.3 Golem backend constraints / exporter

已实现从 `CIM-TileIR` 到 Golem SST artifacts 的导出：

- `validate_cim_tile_ir_for_golem`：校验 dtype、layout、transpose、M/N/K 整除、Golem array tile shape 等后端约束。
- `export_golem_sst_artifacts`：生成硬件侧可消费 artifacts。
- `examples/export_golem_sst.py`：CLI 支持 `CIM-TileIR JSON` 和 TileLang 源码输入，但内部必须先落到 `CIM-TileIR`。

导出产物：

- `golem_sst.env`
- `contracts/matmul_op_desc_resolved.json`
- `contracts/matmul_env_mapping_v1.json`

对应文件：

- `tilelang_cim/golem_constraints.py`
- `tilelang_cim/golem_exporter.py`
- `examples/export_golem_sst.py`
- `tests/test_golem_constraints.py`
- `tests/test_golem_exporter.py`

### 2.4 硬件侧 env/contract 解耦审计

当前阶段不要求直接运行完整 SST。已新增静态审计脚本确认硬件仓库是否具备外部 artifacts 注入入口：

- `GOLEM_ARTIFACT_ROOT`
- `GOLEM_MATMUL_*`
- `GOLEM_ARRAY_INPUT_SIZE`
- `GOLEM_ARRAY_OUTPUT_SIZE`
- `GOLEM_NUM_ARRAYS`
- resolved contract
- env mapping contract
- HBM generator contract 写出
- runtime env reader
- compile-time fallback macros

对应文件：

- `scripts/check_golem_hardware_contracts.py`
- `tests/test_check_golem_hardware_contracts.py`

### 2.5 Golem task mapping/debug plan

`build_golem_event_plan` 保留为 Golem runtime 映射解释和调试产物，而不是 SST 必需输入。它复用硬件 `pipeline_config.h` / `gen_hbm_init.py` 中的映射公式，输出：

- macro-task diagonal banding。
- worker slot / worker core。
- group id / data node。
- task slot in node。
- A packed-once base。
- B vector-pack base。
- C output slot base。
- reuse offset。
- Golem runtime 语义事件。

对应文件：

- `tilelang_cim/golem_event_planner.py`
- `examples/plan_golem_events.py`
- `tests/test_golem_event_planner.py`
- `tests/test_plan_golem_events_example.py`

该 plan 用于解释、调试和后续 stats 校准；当前不输出 cycle estimate。

## 3. 已移除内容

以下内容曾用于早期原型验证，但不再服务当前真实 SST 主线，已经删除：

- toy `CIMArchitectureSpec` schema/checker。
- `examples/architecture/toy_cim_mesh_v0.json`。
- abstract `build_event_plan`。
- toy `build_arch_event_plan`。
- `examples/plan_events.py`。
- `docs/cim-architecture-spec.md`。
- `docs/cim-event-plan-schema.md`。
- 对应 toy/abstract planner 测试。

删除原因：

- 本地已经接入真实 `RISC-V-CIM-Manycore-SST` Golem 架构。
- toy spec 会制造两套架构真相。
- abstract `dma_load A/B + cim_gemm` 事件不等价于 Golem runtime 真实执行语义。
- 当前最终产物是 env/contract/script artifact 填充，而不是 toy cycle estimate。

## 4. 当前可运行链路

生成静态 GEMM 的 `CIM-TileIR JSON`：

```bash
python examples/gemm_ir.py \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --m 1024 --n 1024 --k 128 \
  --bm 64 --bn 64 --bk 64 \
  --mesh-w 4 --mesh-h 5 \
  --pipeline-stages 1 \
  --a-dtype fp32 --b-dtype fp32 --c-dtype fp32
```

从 TileLang GEMM fixture 提取 `CIM-TileIR JSON`：

```bash
python examples/extract_tilelang_gemm.py \
  tests/fixtures/tilelang_gemm_fixture.py \
  --output /data4/jjgong/tmp/codegen_sstnoc/tilelang_gemm.cimtile.json \
  --mesh-w 4 --mesh-h 5
```

导出 Golem SST artifacts：

```bash
python examples/export_golem_sst.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts
```

静态审计硬件侧解耦入口：

```bash
python scripts/check_golem_hardware_contracts.py \
  --hardware-tests-dir /data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests
```

生成 Golem task mapping/debug plan：

```bash
python examples/plan_golem_events.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json
```

运行测试：

```bash
TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q
```

文档检查：

```bash
bash scripts/check_docs.sh
```

## 5. 当前不具备的能力

当前原型不能回答以下问题：

- 完整 SST 运行后的真实性能周期是多少。
- NoC 是否拥塞。
- WCP strict-order consumption 具体造成多少 queue wait。
- runtime ABI / RISC-V ELF 如何生成并加载。
- TileOPs 复杂 grouped GEMM 是否可直接提取。
- 非硬件 tile shape 如何通过 micro-tiling 落到 Golem runtime。

这些问题应在 Golem exporter 稳定后，通过 stats-based calibration、TileOPs-like smoke path 和长期 runtime ABI/ELF 阶段继续推进。

## 6. 下一阶段建议

下一阶段不再恢复 toy architecture 或 abstract event planner。建议优先做：

```text
Golem stats calibration report
```

最小目标：

- 读取 `execution_summary.csv`、`dma_summary.csv`、`noc_summary.csv`、`memory_summary.csv`。
- 允许 stats 文件缺失时输出结构化 warning，而不是直接失败。
- 将 `golem_event_plan` 的 mapping 信息与 SST 观测结果放到同一份 report。
- 首版 report 的模型状态可以是 `not_calibrated`，先建立稳定输入/输出格式。
