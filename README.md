# codegen_sstnoc

这是 SST codegen 项目的协调中枢目录。

## 作用

- 跟踪项目目标、范围和里程碑。
- 记录技术决策和调研结论。
- 将开发进度与源码修改分开管理。
- 为 agent 驱动的开发提供稳定的工作空间。

## 当前范围

- 当前目标是完成 `tilelang` 面向 SST 后端的首版 codegen。
- 首版只要求识别 SST 目标后输出 C 代码。
- 生成的 C 代码中需要能够表达 RISC-V 自定义指令。
- 当前阶段不要求生成结果立即可执行。
- 当前阶段不修改 `TileOPs`，但允许把它作为算子和使用方式的参考来源。
- 新增的 RISC-V CIM 2D-mesh 方案属于后续路线图，近期目标收敛为 `TileLang GEMM -> CIM-TileIR JSON` 的编译器侧原型。
- 当前项目尚无 CIM simulator、OS loader、runtime ABI、RISC-V ELF 工具链集成或真实 CIM primitive 源码，因此 sim/ELF 闭环均不属于当前阶段承诺。

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

## 工作原则

- 源码修改都在 `tilelang/` 中完成。
- 协调、规划和文档维护都在这里完成。
- `TileOPs/` 在当前阶段只作为上层使用案例和需求来源，不作为首版实现改动位置。

## 当前约定

- SST target 采用“`c` + SST 标记”方案。
- 内部继续复用 `tilelang` 现有 `c` backend。
- 后续如需扩展为真实可执行后端，再在首版基础上继续推进。
- CIM 路线第一阶段不新增真正的 `riscv_cim_mesh` target kind，建议先复用 `c` target 并通过 `cim`/`sst`/`noc` key 或 tag 做内部分流。
- `tilelang_riscv_cim_backend_plan.md` 记录 CIM 长期路线；其中 `ir_only` / JSON 生成是近期可落地目标，abstract sim、runtime ABI 和 ELF mode 是后续建设目标。

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
python -m pytest tests -q
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

当前 CIM 原型阶段的完整整理见 `docs/cim-tileir-prototype-summary.md`。该文档同时列出了后续进入 architecture-aware planner 前需要补齐的 architecture spec 信息，包括 mesh/core、local SRAM、accumulator、DMA、CIM primitive、NoC、synchronization、mapping/dataflow 和 cycle model。

## 推荐流程

1. 开始新阶段前先更新 `task_plan.md`。
2. 把发现和结论记录到 `findings.md`。
3. 把本次会话进度写入 `progress.md`。
4. 在 `tilelang/` 中修改源码。
5. 把验证结果同步回这个目录。
