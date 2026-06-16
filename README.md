# codegen_sstnoc

这是 CIM-TileIR codegen 项目的协调中枢与原型目录。

## 作用

- 跟踪项目目标、范围和里程碑。
- 记录技术决策和调研结论。
- 将开发进度与源码修改分开管理。
- 为 agent 驱动的开发提供稳定的工作空间。

## 当前范围

- 当前分支以 RISC-V CIM 2D-mesh 的 `CIM-TileIR` 技术路线为主线。
- 近期目标是完成 `TileLang GEMM -> CIM-TileIR JSON/MatmulOpDesc -> Golem SST env/contract` 的参数导出闭环。
- 当前已经支持静态 GEMM 的 `CIM-TileIR JSON` 构造、窄模板 TileLang GEMM 提取，以及 abstract event skeleton 展开。
- 已完成 toy `CIMArchitectureSpec` 与 `serial_formula_v0` planner。由于本地已经有 `RISC-V-CIM-Manycore-SST` 的 Golem 硬件/运行时链路，下一阶段重点转为 Golem SST env/contract exporter。
- 当前不承诺 OS loader、runtime ABI 或 RISC-V ELF 工具链闭环；首版硬件对接以生成 `golem_sst.env`、`matmul_op_desc_resolved.json`、`matmul_env_mapping_v1.json` 并驱动既有 `run_noc_dma_pipeline.sh` smoke path 为目标。
- SST C codegen 方案保留为历史背景和长期旁支，不再作为当前分支的近期主线。

## 目录说明

- `task_plan.md`：分阶段计划和当前执行状态。
- `findings.md`：调研记录、技术发现和决策。
- `progress.md`：按时间顺序记录开发过程和验证结果。
- `docs/`：更深入的设计说明和 ADR。
- `scripts/`：初始化、同步和验证的辅助脚本。
- `tilelang_cim/`：CIM-TileIR 编译器侧原型包。
- `examples/gemm_ir.py`：生成静态 GEMM 的 `CIM-TileIR JSON` 示例。
- `examples/extract_tilelang_gemm.py`：从窄模板 TileLang GEMM 源码提取 `CIM-TileIR JSON` 的示例。
- `examples/plan_events.py`：将 `CIM-TileIR JSON` 展开为 abstract event plan 的示例。
- `tests/`：CIM-TileIR 原型的 pytest 测试。
- `docs/golem-runtime-codegen-roadmap.md`：对接 `RISC-V-CIM-Manycore-SST` Golem runtime 的下一步路线。

## 工作原则

- 当前 CIM-TileIR 原型代码维护在本目录的 `tilelang_cim/` 中。
- `tilelang/` 暂作为 TileLang 前端和后续 pass 集成参考，不作为当前 architecture-aware planner v0 的直接改动位置。
- `TileOPs/` 在当前阶段只作为上层使用案例和需求来源，不作为实现改动位置。

## 当前约定

- `CIM-TileIR` 是当前 TileLang 与后续 event planner / simulator / runtime 之间的接口契约。
- 当前 target 字段仍写作 `riscv_cim_mesh`，但不会在 TileLang/TVM 中注册真正的新 target kind。
- architecture-aware planner 只有在显式提供 architecture spec 时才输出非 0 cycle estimate。
- 未提供 architecture spec 时，event planner 继续作为 abstract event expander，`estimated_cycles=0`，不代表真实硬件周期。
- `tilelang_riscv_cim_backend_plan.md` 记录 CIM 长期路线；runtime ABI 和 ELF mode 是后续建设目标。

## CIM-TileIR 原型用法

生成一个静态 GEMM 的 `CIM-TileIR JSON`：

```bash
python examples/gemm_ir.py --output gemm.cimtile.json
```

自定义矩阵、tile 和 mesh 参数：

```bash
python examples/gemm_ir.py \
  --output gemm.cimtile.json \
  --m 1024 --n 1024 --k 1024 \
  --bm 64 --bn 64 --bk 32 \
  --mesh-w 8 --mesh-h 8 \
  --pipeline-stages 2
```

运行原型测试：

```bash
TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q
```

从 TileLang GEMM 源码文件提取 `CIM-TileIR JSON`：

```bash
python examples/extract_tilelang_gemm.py \
  tests/fixtures/tilelang_gemm_fixture.py \
  --output tilelang_gemm.cimtile.json \
  --mesh-w 8 --mesh-h 8
```

当前 extractor 是第一版 MVP，只支持标准静态 GEMM 模板。它可以识别源码里的 `T.Tensor`、`T.alloc_shared`、`T.alloc_fragment`、`T.Pipelined`、`T.gemm`，也可以从 TileLang `PrimFunc.script()` 的 `T.match_buffer`、`T.alloc_buffer`、`T.serial`、`T.gemm` 形态中提取同类信息；暂不支持任意动态 shape、复杂 fusion、转置 GEMM、复杂调度或完整 TileLang pass pipeline。

将 `CIM-TileIR JSON` 展开成 abstract event plan：

```bash
python examples/plan_events.py \
  tilelang_gemm.cimtile.json \
  --output tilelang_gemm.eventplan.json
```

第一版 event planner 更准确地说是 abstract event expander / IR sanity consumer，只做抽象事件展开和粗略统计。输出包括 per-output-tile task、core 映射、`clear_acc`、`dma_load`、`cim_gemm`、`dma_store` 事件，以及 `dma_load_bytes`、`dma_store_bytes`、`cim_gemm_ops`、`macs`、`core_utilization` 等统计；`estimated_cycles` 暂固定为 0，不代表真实硬件周期。

使用 toy architecture spec 生成 architecture-aware event plan：

```bash
python examples/plan_events.py \
  tilelang_gemm.cimtile.json \
  --arch examples/architecture/toy_cim_mesh_v0.json \
  --output tilelang_gemm.eventplan.json
```

提供 `--arch` 后，planner 会先校验 `CIM-TileIR` 是否满足架构约束，再按 `serial_formula_v0` 生成每个事件和每个 core 的粗略 cycle estimate。该估计只适用于 toy spec 和串行公式，不代表真实硬件性能。

当前 CIM 原型阶段的完整整理见 `docs/cim-tileir-prototype-summary.md`。Golem SST 硬件对齐后的下一步路线见 `docs/golem-runtime-codegen-roadmap.md`。新路线的重点是从 TileLang/CIM-TileIR 参数导出到 Golem SST runtime contract：`golem_sst.env`、resolved matmul contract、env mapping 和 SST smoke 验证。Golem 硬件参数首版作为 exporter 的后端约束校验，不作为第一阶段主产物。

## 推荐流程

1. 开始新阶段前先更新 `task_plan.md`。
2. 把发现和结论记录到 `findings.md`。
3. 把本次会话进度写入 `progress.md`。
4. 在 `tilelang_cim/` 中修改当前 CIM 原型。
5. 把验证结果同步回这个目录。
