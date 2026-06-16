# 进度日志

## 会话：2026-05-18

### 阶段 1：项目初始化
- **状态：**完成
- **开始时间：**2026-05-18
- 已执行的操作：
  - 确认 `tilelang` 和 `TileOPs` 是两个独立仓库。
  - 决定使用 `codegen_sstnoc` 作为协调中枢。
  - 创建了初始规划和文档文件。
  - 将文档统一改为中文。
  - 为 `tilelang` 新增了中文协作规范 `AGENTS.md`。
- 已创建/修改的文件：
  - `README.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
  - `WORKFLOW.md`
  - `docs/adr/0001-项目中枢与源码分离.md`
  - `docs/adr/README.md`
  - `docs/README.md`
  - `scripts/bootstrap.sh`
  - `scripts/check_docs.sh`
  - `.gitignore`
  - `tilelang/AGENTS.md`

### 阶段 2：技术调研
- **状态：**进行中
- 已执行的操作：
  - 梳理了 `tilelang` 的 target、lowering 和 C backend 路径。
  - 确认 `tilelang` 已经有现成的 C 后端入口。
  - 确认首版不修改 `TileOPs`。
  - 确认 SST 目标采用“`c` + SST 标记”方案，不引入新的 target kind。
  - 将 `TileOPs` 中 GEMM 相关文件记为后续联调参考，而不是首版实现改动点。
  - 补充了首版范围、当前约定和后续联调方向到项目文档。
  - 输出了首版 SST codegen 技术设计文档，明确 target 标准化、C backend 落点和测试策略。
  - 生成了一页中文技术路线汇报 PPT，并保留可编辑源文件。
- 已创建/修改的文件：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
  - `README.md`
  - `docs/README.md`
  - `docs/sst-codegen-first-design.md`
  - `docs/sst-codegen-tech-route.fodp`
  - `docs/sst-codegen-tech-route.pptx`
  - `scripts/build_sst_pptx.py`
  - `scripts/export_sst_ppt.sh`

## 测试结果

| 测试 | 输入 | 预期 | 实际 | 状态 |
|------|------|------|------|------|
| 目录创建 | `codegen_sstnoc` 骨架 | 文件存在 | 创建成功 | ✓ |
| 文档语言统一 | 中文化处理 | 全部为中文 | 已完成 | ✓ |
| 源码协作规范 | `tilelang/AGENTS.md` | 仓库内可读 | 已创建 | ✓ |
| C 后端入口确认 | `tilelang` 源码检索 | 存在 C backend 路径 | 已确认 | ✓ |
| 项目文档补全 | 新增首版范围与约定 | 文档同步最新上下文 | 已完成 | ✓ |
| 技术设计输出 | 首版实现方案文档 | 形成可执行设计 | 已完成 | ✓ |
| 组会汇报页 | 一页技术路线 PPT | 可打开的 `.pptx` 文件 | 已生成 | ✓ |

## 错误日志

| 时间 | 错误 | 尝试次数 | 解决方式 |
|------|------|----------|----------|
| 无 | 无 | 1 | N/A |

## 5 问恢复检查

| 问题 | 答案 |
|------|------|
| 我现在在哪？ | 阶段 2：技术调研与方案确定 |
| 我要去哪里？ | 架构规划、实现、验证 |
| 目标是什么？ | 以 `codegen_sstnoc` 为中枢，在 `tilelang` 中实现 SST 首版 C codegen |
| 我学到了什么？ | `tilelang` 和 `TileOPs` 是独立仓库；工作区根目录不是 git 仓库 |
| 我已经做了什么？ | 梳理了现有 codegen 入口并确定首版聚焦 `tilelang` |

## 会话：2026-06-03

### CIM 路线可行性校准
- **状态：**文档已更新，待后续实现阶段启动
- **背景：**
  - 用户新增了 `tilelang_riscv_cim_backend_plan.md`，希望评估 TileLang 衔接 RISC-V CIM 2D-mesh 后端的可行性。
  - 用户确认当前项目只有 `tilelang` 和 `TileOPs` 相关源码，尚无 CIM 架构、simulator、OS loader、runtime ABI、RISC-V ELF 工具链集成或真实 CIM primitive 源码。
- 已执行的操作：
  - 将 CIM 方案从“直接复用已有 simulator/OS loader/ELF 链路”调整为长期路线图。
  - 将近期目标收敛为 `TileLang GEMM -> CIM-TileIR JSON` 的编译器侧原型。
  - 明确 `sim mode` 第一版应先做 abstract event planner / JSON interpreter，不承诺真实 cycle-accurate simulator。
  - 明确 `elf mode` 归入长期目标，需要后续补 runtime ABI、RISC-V toolchain 和 OS loader。
  - 保留首版 SST C codegen 的当前阶段定位，不把 CIM 路线混入阶段 4 实现准备。
  - 将后续 CIM 工作拆为阶段 6：CIM-TileIR 原型、阶段 7：抽象架构与 event planner、阶段 8：runtime ABI 与 ELF 长期闭环。
- 已创建/修改的文件：
  - `tilelang_riscv_cim_backend_plan.md`
  - `README.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### CIM 当前决策摘要

| 决策 | 原因 |
|------|------|
| 第一阶段只做 `CIM-TileIR JSON` | 当前没有 CIM 执行侧源码，先完成编译器侧可检查闭环 |
| sim mode 先做 abstract event planner | 先验证 IR、mapping 和粗略统计模型 |
| ELF mode 作为长期目标 | runtime ABI、RISC-V toolchain、OS loader 均未具备 |
| 内部 target 标记优先复用 `c` target + key/tag | 降低新增 TVM target kind 和主链路改造风险 |
| `TileOPs` 继续作为参考，不纳入第一阶段修改 | 先聚焦 TileLang/TIR 语义提取和 IR schema |

### CIM-TileIR 原型第一步
- **状态：**已完成第一版 schema/checker/example 闭环
- 已执行的操作：
  - 新增 `tilelang_cim` 原型包。
  - 新增 `build_gemm_ir`，可生成静态 GEMM 的 `CIM-TileIR` Python dict。
  - 新增 `validate_cim_tile_ir`，检查 mesh、tile、A/B/C tensor、output-stationary mapping、program op 顺序和 `loop_k` body。
  - 新增 `to_json_text` / `write_json`，支持稳定 JSON 导出。
  - 新增 `examples/gemm_ir.py`，可通过命令行生成 `gemm.cimtile.json`。
  - 新增 pytest 测试覆盖 IR 构造、JSON 导出、checker 错误路径和示例 CLI。
- 已创建/修改的文件：
  - `tilelang_cim/__init__.py`
  - `tilelang_cim/builder.py`
  - `tilelang_cim/checker.py`
  - `tilelang_cim/json_export.py`
  - `examples/gemm_ir.py`
  - `tests/test_cim_tile_ir.py`
  - `tests/test_gemm_ir_example.py`
  - `README.md`
  - `task_plan.md`
  - `progress.md`

### TileLang GEMM extractor MVP
- **状态：**已完成窄模板识别
- 已执行的操作：
  - 新增 `extract_gemm_ir_from_source`，可从标准 TileLang GEMM 源码中提取 A/B/C shape、dtype、BM/BN/BK、pipeline stages，并生成 `CIM-TileIR`。
  - 新增 `extract_gemm_ir_from_tilelang`，当输入是 TileLang `PrimFunc` 时，优先读取 `script()` 结果并识别 lowering 后的 `T.match_buffer`、`T.alloc_buffer`、`T.serial`、`T.gemm` 形态。
  - 新增 `examples/extract_tilelang_gemm.py`，支持从 `.py` 源码文件提取并导出 JSON。
  - 新增 `tests/fixtures/tilelang_gemm_fixture.py`，作为标准 TileLang GEMM 测试样例。
  - 新增 pytest 测试覆盖源码字符串、真实 TileLang `PrimFunc` 和 CLI 提取路径。
- 当前边界：
  - 支持 static shape、标准 GEMM 模板、output-stationary mapping、`num_stages=1/2`。
  - 暂不支持转置 GEMM、动态 shape、复杂 fusion、NoC 通信、真实 simulator 或完整 TileLang pass pipeline。
- 已创建/修改的文件：
  - `tilelang_cim/extractor.py`
  - `tilelang_cim/__init__.py`
  - `examples/extract_tilelang_gemm.py`
  - `tests/fixtures/tilelang_gemm_fixture.py`
  - `tests/test_tilelang_gemm_extractor.py`
  - `tests/test_extract_tilelang_gemm_example.py`
  - `README.md`
  - `task_plan.md`
  - `progress.md`

### Abstract event planner MVP
- **状态：**已完成第一版事件展开
- 已执行的操作：
  - 新增 `build_event_plan`，从 `CIM-TileIR` dict 生成 abstract event plan。
  - 新增 per-output-tile task 展开逻辑，按当前 `output_stationary` / `bx % mesh_w` / `by % mesh_h` 规则映射到 core。
  - 每个 task 展开 `clear_acc`、每个 K tile 的 `dma_load A`、`dma_load B`、`cim_gemm`，以及最终 `dma_store C`。
  - 新增粗略统计：`output_tiles`、`total_cores`、`active_cores`、`core_utilization`、`dma_load_bytes`、`dma_store_bytes`、`cim_gemm_ops`、`macs`。
  - 新增 `examples/plan_events.py`，支持从 `CIM-TileIR JSON` 生成 `eventplan JSON`。
  - 新增 pytest 测试覆盖事件展开、core wrap-around、非法 IR 报错和 CLI 生成路径。
- 当前边界：
  - `estimated_cycles` 暂固定为 0。
  - 暂不模拟 NoC、barrier、DMA/compute overlap、SRAM bank conflict 或 CIM array latency。
  - 当前 core 利用率按至少分配到一个 output tile 的 core 数量统计。
- 已创建/修改的文件：
  - `tilelang_cim/event_planner.py`
  - `tilelang_cim/__init__.py`
  - `examples/plan_events.py`
  - `tests/test_event_planner.py`
  - `tests/test_plan_events_example.py`
  - `README.md`
  - `task_plan.md`
  - `progress.md`

### 原型整理与 architecture spec 边界补充
- **状态：**已完成文档整理
- 背景：
  - 用户指出当前项目并不知道真实 CIM mesh 结构，因此 event planner 不能被当作真实 simulator。
- 已执行的操作：
  - 将当前 `build_event_plan` 的定位明确为 abstract event expander / IR sanity consumer。
  - 明确当前 event plan 只验证 `CIM-TileIR` 能否被下游消费，并输出事件骨架和静态统计。
  - 明确 `estimated_cycles=0` 不代表真实硬件周期。
  - 新增 `docs/cim-tileir-prototype-summary.md`，汇总当前已完成能力、可运行链路、边界和后续 architecture spec 需求。
  - 在 `README.md`、`task_plan.md`、`findings.md` 和 `tilelang_riscv_cim_backend_plan.md` 中同步 architecture spec 前置要求。
- 后续需要补齐的 architecture spec 信息：
  - mesh/core 拓扑和 core id 映射。
  - local SRAM 和 accumulator 容量。
  - DMA 粒度、带宽、启动延迟和 overlap 能力。
  - CIM primitive 支持的 dtype、tile shape、latency/throughput。
  - NoC topology、routing、带宽、hop latency 和通信能力。
  - synchronization / barrier 粒度和延迟。
  - mapping/dataflow 策略。
  - cycle model 类型和公式。
- 已创建/修改的文件：
  - `docs/cim-tileir-prototype-summary.md`
  - `README.md`
  - `task_plan.md`
  - `findings.md`
  - `tilelang_riscv_cim_backend_plan.md`
  - `progress.md`

## 会话：2026-06-15

### 当前分支主线确认
- **状态：**已完成
- 背景：
  - 用户明确要求“一切以当前分支为准”，即以 `feat/cim-tileir-json` 上的 CIM-TileIR 技术路线为准。
  - 因此 SST C codegen 降为历史背景和长期旁支，不再作为当前近期主线。
- 已执行的操作：
  - 将 `README.md` 当前范围改为 `TileLang GEMM -> CIM-TileIR JSON -> architecture-aware event plan`。
  - 重写 `task_plan.md`，以 `architecture-aware event planning v0` 作为当前里程碑。
  - 更新 `findings.md`，记录当前分支以 CIM-TileIR 为主线，以及 architecture spec 是后续前置项。
- 已创建/修改的文件：
  - `README.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### Architecture-aware event planner v0
- **状态：**完成
- 已执行的操作：
  - 新增 `tilelang_cim/architecture.py`。
  - 新增 `load_architecture_spec`，支持从 JSON 文件读取 architecture spec。
  - 新增 `validate_architecture_spec`，校验 mesh/core/DMA/CIM/NoC/sync/cycle model 字段。
  - 新增 `validate_cim_tile_ir_for_arch`，联合校验 `CIM-TileIR` 与 architecture spec。
  - 联合校验覆盖：
    - IR mesh 与 architecture mesh 匹配。
    - A/B dtype 属于 `cim.input_dtypes`。
    - C dtype 匹配 `cim.acc_dtype`。
    - `BM/BN/BK` 匹配 `cim.tile_m/tile_n/tile_k`。
    - local SRAM 能容纳 pipeline stages 下的 A/B tile buffer。
    - accumulator 能容纳 C tile。
    - A/B/C tile bytes 满足 DMA alignment。
  - 新增 toy architecture spec：`examples/architecture/toy_cim_mesh_v0.json`。
  - 新增 `build_arch_event_plan`，在 `serial_formula_v0` 下生成 architecture-aware event plan。
  - 扩展 `examples/plan_events.py --arch`，有 architecture spec 时输出 `arch_event_plan`，无 architecture spec 时保持原有 `event_plan` 行为。
  - 新增 schema 文档：
    - `docs/cim-architecture-spec.md`
    - `docs/cim-event-plan-schema.md`
  - 更新 `docs/cim-tileir-prototype-summary.md`，补充 architecture-aware planner v0 的能力与边界。
- 当前 cycle model：
  - `serial_formula_v0` 串行累加 `clear_acc`、DMA load、CIM GEMM、DMA store。
  - DMA cycle 公式为 `startup_cycles + ceil(bytes / bytes_per_cycle)`。
  - 全局 `estimated_cycles` 取所有 core 累计 cycles 的最大值。
  - 不建模 DMA/compute overlap、NoC contention、barrier、SRAM bank conflict 或真实 runtime 调度。
- 已创建/修改的文件：
  - `tilelang_cim/architecture.py`
  - `tilelang_cim/event_planner.py`
  - `tilelang_cim/__init__.py`
  - `examples/architecture/toy_cim_mesh_v0.json`
  - `examples/plan_events.py`
  - `tests/test_architecture_spec.py`
  - `tests/test_arch_event_planner.py`
  - `tests/test_plan_events_example.py`
  - `docs/cim-architecture-spec.md`
  - `docs/cim-event-plan-schema.md`
  - `docs/cim-tileir-prototype-summary.md`
  - `README.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

### 验证结果

| 测试 | 命令 | 结果 |
|------|------|------|
| pytest | `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q` | 22 passed |
| 文档检查 | `bash scripts/check_docs.sh` | 基础文档检查通过 |
| GEMM IR 生成 | `python examples/gemm_ir.py --output /tmp/gemm.cimtile.json` | 成功 |
| architecture-aware event plan CLI | `python examples/plan_events.py /tmp/gemm.cimtile.json --arch examples/architecture/toy_cim_mesh_v0.json --output /tmp/gemm.eventplan.json` | 成功，输出 `mode=arch_event_plan` |

### 错误日志

| 时间 | 错误 | 尝试次数 | 解决方式 |
|------|------|----------|----------|
| 2026-06-15 | 直接运行 `python -m pytest tests -q` 时 TileLang 默认写 `/home/jiajun/.tilelang`，当前环境只读 | 1 | 使用 `TILELANG_CACHE_DIR=/tmp/tilelang-cache` 后测试通过 |
| 2026-06-15 | `test_arch_event_planner_*` 期望值最初把 C store bytes 误算，预期 `1153`，实际按公式应为 `1893` | 1 | 修正测试期望值，保持实现公式不变 |

## 5 问恢复检查

| 问题 | 答案 |
|------|------|
| 我现在在哪？ | 阶段 3 已完成，当前进入阶段 4：extractor 稳健性扩展 |
| 我要去哪里？ | 增强 extractor，随后做 TileOPs-like smoke path |
| 目标是什么？ | 以 `CIM-TileIR` 为主线，推进可检查、可解释的编译器侧 CIM 原型 |
| 我学到了什么？ | architecture-aware planner 必须依赖显式 architecture spec；没有 spec 时保持 `estimated_cycles=0` |
| 我已经做了什么？ | 完成 architecture spec、联合校验、`build_arch_event_plan`、`--arch` CLI、测试和 schema 文档 |

## 会话：2026-06-16

### Golem SST 硬件架构对齐分析
- **状态：**已完成路线分析，待后续实现阶段启动
- **背景：**
  - 用户说明本地已经有真实硬件架构，位于 `/data4/jjgong/RISC-V-CIM-Manycore-SST`。
  - 用户已将硬件项目总结放在 `/data4/jjgong/codegen_sstnoc/summary.md`，希望先分析硬件架构，再规划 `codegen_noc` 下一步。
- 已执行的操作：
  - 阅读 `codegen_sstnoc` 当前规划、发现、进度和 CIM-TileIR 文档。
  - 阅读 `summary.md` 中的 Golem SST 架构总结。
  - 阅读硬件侧 Golem 配置文件、runtime header、RoCC 指令封装、`pipeline_config.h`、HBM 初始化脚本和 contract 示例。
  - 确认当前 toy `arch_event_plan` 与硬件 runtime 在 task 映射、A/B reuse、memory node、B vector packing、local GM layout 和 cycle model 上存在语义差异。
  - 新增路线文档 `docs/golem-runtime-codegen-roadmap.md`。
  - 更新 `task_plan.md`，将阶段 4 调整为 Golem SST architecture spec adapter，并新增 Golem-aware planner、contract export、硬件 smoke integration 和 stats-based cycle 校准阶段。
  - 更新 `findings.md`，记录硬件对齐结论和待确认事项。
- 核心结论：
  - `codegen_noc` 下一步不应直接生成 RISC-V ELF 或 RoCC inline assembly。
  - 最短路径是把 `CIM-TileIR` 对接到 Golem runtime contract：先生成 Golem architecture spec、macro-task event plan、resolved matmul contract 和 env 片段，再驱动 `run_noc_dma_pipeline.sh` 验证。
  - 在硬件 WCP micro-tiling 未完成前，codegen 首版应严格要求 `BM == GOLEM_ARRAY_OUTPUT_SIZE`、`BK == GOLEM_ARRAY_INPUT_SIZE`、`BN <= GOLEM_NUM_ARRAYS`。
- 已创建/修改的文件：
  - `docs/golem-runtime-codegen-roadmap.md`
  - `task_plan.md`
  - `findings.md`
  - `README.md`
  - `progress.md`

### 5 问恢复检查

| 问题 | 答案 |
|------|------|
| 我现在在哪？ | 阶段 4：Golem SST architecture spec adapter |
| 我要去哪里？ | Golem-aware task planner、contract export、SST smoke integration |
| 目标是什么？ | 让 `CIM-TileIR` 生成的计划能对齐并驱动现有 Golem SST runtime |
| 我学到了什么？ | Golem runtime 的真实映射是 macro-task/worker/group/data-node，而不是 toy mesh `bx/by` 映射 |
| 我已经做了什么？ | 完成硬件架构对齐分析，并把下一步路线固化到项目文档 |

### 技术方向校准：前端参数到 SST env/contract
- **状态：**已校准并更新规划
- **背景：**
  - 用户明确指出最终产物是“从 TileLang 语言解析参数，把编程语言解耦，把所有参数落到 SST 的环境以及脚本中去”。
  - 因此原路线中把 `GolemArchitectureSpec adapter` 放在第一阶段会偏向硬件建模，不符合当前最短闭环。
- 已执行的操作：
  - 重写 `docs/golem-runtime-codegen-roadmap.md`，将主线改为 `TileLang/CIM-TileIR -> Golem SST env/contract exporter`。
  - 更新 `task_plan.md`，把当前阶段改为 `TileLang-to-Golem SST env/contract exporter`。
  - 更新 `README.md`，明确下一阶段产物是 `golem_sst.env`、`matmul_op_desc_resolved.json`、`matmul_env_mapping_v1.json`。
  - 更新 `findings.md`，记录新决策：Golem 硬件参数首版作为 exporter 的后端约束校验，而不是第一阶段主模型。
- 新的下一步：
  - 新增 `tilelang_cim/golem_exporter.py`。
  - 新增 `tilelang_cim/golem_constraints.py`。
  - 新增 `examples/export_golem_sst.py`。
  - 输出可被 `run_noc_dma_pipeline.sh` 使用的 env 和 contract artifacts。

### 5 问恢复检查

| 问题 | 答案 |
|------|------|
| 我现在在哪？ | 阶段 4：TileLang-to-Golem SST env/contract exporter |
| 我要去哪里？ | 先完成参数导出器，再做 SST 脚本注入 smoke path |
| 目标是什么？ | 从 TileLang/CIM-TileIR 抽取 GEMM 参数，并生成 Golem SST 可消费的 env/contract |
| 我学到了什么？ | Golem architecture spec 不应作为第一阶段主产物，硬件参数应先服务 exporter 合法性校验 |
| 我已经做了什么？ | 修正技术路线和项目规划，使其对齐用户确认的最终产物 |
