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

### 技术边界校准：CIM-TileIR 作为唯一前后端接口
- **状态：**已校准并更新规划
- **背景：**
  - 用户进一步明确：所有前端语言都应解析到 `CIM-TileIR`，再由 `CIM-TileIR` 落实到硬件加载环境。
  - 因此路线不能写成 TileLang 与 Golem SST 直连。TileLang 只是第一个 frontend，Golem SST 只是第一个 backend。
- 已执行的操作：
  - 更新 `docs/golem-runtime-codegen-roadmap.md`，把目标改为 `All frontends -> CIM-TileIR -> Golem SST backend exporter`。
  - 更新 `task_plan.md`，将当前阶段改为 `CIM-TileIR-to-Golem SST backend exporter`。
  - 更新 `README.md`，明确 `CIM-TileIR` 是所有前端与所有后端之间的唯一接口契约。
  - 更新 `findings.md`，记录新决策：不能让 TileLang 和 Golem SST 直接耦合。
- 新的下一步：
  - 先检查并补齐 `CIM-TileIR` 的 layout / transpose 表达。
  - 再实现以 `CIM-TileIR dict` 为核心输入的 Golem SST backend exporter。

### 5 问恢复检查

| 问题 | 答案 |
|------|------|
| 我现在在哪？ | 阶段 4：CIM-TileIR-to-Golem SST backend exporter |
| 我要去哪里？ | 先补齐统一 IR 字段，再做 Golem SST backend artifacts 导出 |
| 目标是什么？ | 所有前端统一生成 `CIM-TileIR`，Golem SST backend 只消费 `CIM-TileIR` |
| 我学到了什么？ | `CIM-TileIR` 是唯一前后端边界，TileLang 与 Golem SST 不应直接耦合 |
| 我已经做了什么？ | 修正文档和规划，使其对齐“所有前端 -> CIM-TileIR -> 硬件后端”的架构 |

### 阶段 4 实现：CIM-TileIR-to-Golem SST backend exporter
- **状态：**完成
- 已执行的操作：
  - 补齐 `CIM-TileIR`：A/B/C tensor 增加 `layout=row_major`，顶层增加 `attrs.transpose_a` / `attrs.transpose_b`。
  - 扩展 `validate_cim_tile_ir`，校验 tensor layout 和 transpose attrs。
  - 新增 `tilelang_cim/golem_constraints.py`：
    - 定义 `GolemBackendConfig`。
    - 校验 Golem 支持的 dtype、layout、transpose 和 tile/backend shape 约束。
  - 新增 `tilelang_cim/golem_exporter.py`：
    - 从 `CIM-TileIR dict` 构造 Golem matmul op desc。
    - 生成 `golem_sst.env`。
    - 生成 `contracts/matmul_op_desc_resolved.json`。
    - 生成 `contracts/matmul_env_mapping_v1.json`。
  - 新增 `examples/export_golem_sst.py`，支持 `cim-tileir-json` 和 `tilelang-source` 两种 CLI 输入，但内部统一走 `CIM-TileIR`。
  - 扩展 `examples/gemm_ir.py`，支持 `--a-dtype`、`--b-dtype`、`--c-dtype`，便于生成 Golem-compatible fp32 IR。
  - 新增 pytest：
    - `tests/test_golem_constraints.py`
    - `tests/test_golem_exporter.py`
  - 更新既有 IR/CLI 测试以覆盖 layout、attrs 和 dtype 参数。
- 已创建/修改的文件：
  - `tilelang_cim/golem_constraints.py`
  - `tilelang_cim/golem_exporter.py`
  - `examples/export_golem_sst.py`
  - `examples/gemm_ir.py`
  - `tilelang_cim/builder.py`
  - `tilelang_cim/checker.py`
  - `tilelang_cim/__init__.py`
  - `tests/test_cim_tile_ir.py`
  - `tests/test_gemm_ir_example.py`
  - `tests/test_golem_constraints.py`
  - `tests/test_golem_exporter.py`
  - `task_plan.md`
  - `progress.md`
- CLI smoke：
  - 输入：`/tmp/gemm.golem.cimtile.json`
  - 输出：
    - `/tmp/golem_codegen_artifacts/golem_sst.env`
    - `/tmp/golem_codegen_artifacts/contracts/matmul_op_desc_resolved.json`
    - `/tmp/golem_codegen_artifacts/contracts/matmul_env_mapping_v1.json`
  - resolved contract 内容为 `m=4096, n=128, k=4096, block_m=64, block_n=64, block_k=64, dtype=fp32, layout=row_major, transpose_a=0, transpose_b=0`。

### 5 问恢复检查

| 问题 | 答案 |
|------|------|
| 我现在在哪？ | 阶段 4 已完成，当前进入阶段 5：SST 脚本参数注入 smoke path |
| 我要去哪里？ | 用 exporter 产物驱动 `run_noc_dma_pipeline.sh`，验证 SST 侧可消费 |
| 目标是什么？ | 让 `CIM-TileIR` 生成的 Golem artifacts 真正进入硬件运行链路 |
| 我学到了什么？ | exporter 核心输入已保持为 `CIM-TileIR dict`，TileLang source 只是 CLI 便利入口 |
| 我已经做了什么？ | 完成 `CIM-TileIR -> golem_sst.env + contract JSON` 的实现、测试和 CLI smoke |

### 阶段 5 实现：SST 脚本参数注入 dry-run smoke
- **状态：**进行中，dry-run 注入路径已完成，完整 SST execute 验收待跑
- 已执行的操作：
  - 阅读硬件侧 `run_noc_dma_pipeline.sh`，确认其支持 `GOLEM_ARTIFACT_ROOT`、`--dry-run`、`GOLEM_VERIFY_C` 和 contracts 目录。
  - 确认硬件脚本在 HBM metadata 缺失时会使用 `contracts/matmul_op_desc_resolved.json` 做兼容性兜底检查。
  - 扩展 `golem_sst.env` 输出，加入 `GOLEM_ARRAY_INPUT_SIZE`、`GOLEM_ARRAY_OUTPUT_SIZE`、`GOLEM_NUM_ARRAYS`，避免硬件脚本回落到与 exporter 不一致的默认阵列参数。
  - 新增 `examples/run_golem_sst_smoke.sh`：
    - source exporter 生成的 `golem_sst.env`。
    - 导出 `GOLEM_ARTIFACT_ROOT`。
    - 校验 `contracts/matmul_op_desc_resolved.json` 存在。
    - 默认调用硬件脚本 `--dry-run`。
    - 只有显式传 `--execute` 时才运行完整 SST。
  - 新增 `tests/test_run_golem_sst_smoke.py`，使用 stub 硬件脚本验证 env 注入、artifact root 注入和 dry-run 参数传递。
  - 更新 `README.md`、`docs/golem-runtime-codegen-roadmap.md`、`task_plan.md` 和 `findings.md`。
- 已创建/修改的文件：
  - `examples/run_golem_sst_smoke.sh`
  - `tests/test_run_golem_sst_smoke.py`
  - `tilelang_cim/golem_exporter.py`
  - `tests/test_golem_exporter.py`
  - `README.md`
  - `docs/golem-runtime-codegen-roadmap.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
- dry-run smoke：
  - 输入：`/tmp/gemm.golem.cimtile.json`
  - artifact root：`/tmp/golem_codegen_artifacts_phase5`
  - 命令：`bash examples/run_golem_sst_smoke.sh --artifact-root /tmp/golem_codegen_artifacts_phase5 -- --log codegen_phase5_smoke.log`
  - 结果：硬件脚本打印 dry-run 配置，确认 `GOLEM_ARRAY_INPUT_SIZE=64`、`GOLEM_ARRAY_OUTPUT_SIZE=64`、`GOLEM_NUM_ARRAYS=64`、`GOLEM_GEMM_M=4096`、`GOLEM_GEMM_N=128`、`GOLEM_GEMM_K=4096`、`GOLEM_ARTIFACT_ROOT=/tmp/golem_codegen_artifacts_phase5`。

### 阶段 5 测试结果

| 测试 | 命令 | 结果 |
|------|------|------|
| wrapper/exporter 目标测试 | `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests/test_golem_exporter.py tests/test_run_golem_sst_smoke.py -q` | 6 passed |
| Golem-compatible IR 生成 | `python examples/gemm_ir.py --output /tmp/gemm.golem.cimtile.json --m 4096 --n 128 --k 4096 --bm 64 --bn 64 --bk 64 --mesh-w 4 --mesh-h 5 --pipeline-stages 1 --a-dtype fp32 --b-dtype fp32 --c-dtype fp32` | 成功 |
| Golem artifacts 导出 | `python examples/export_golem_sst.py /tmp/gemm.golem.cimtile.json --input-format cim-tileir-json --artifact-root /tmp/golem_codegen_artifacts_phase5` | 成功 |
| 硬件脚本 dry-run smoke | `bash examples/run_golem_sst_smoke.sh --artifact-root /tmp/golem_codegen_artifacts_phase5 -- --log codegen_phase5_smoke.log` | 成功，硬件脚本收到 exporter 参数 |
| 小规模 full execute 尝试 | `bash examples/run_golem_sst_smoke.sh --artifact-root /tmp/golem_codegen_artifacts_small_phase5 --execute -- --log codegen_small_phase5_execute.log` | HBM 生成成功，构建阶段因 `riscv64-linux-musl-g++: Permission denied` 停止 |

### 阶段 5 错误日志

| 时间 | 错误 | 尝试次数 | 解决方式 |
|------|------|----------|----------|
| 2026-06-16 | wrapper 测试最初缺少 `contracts/matmul_op_desc_resolved.json`，触发 contract 缺失错误 | 1 | 在测试 fixture 中补齐 contracts 文件 |
| 2026-06-16 | artifact root 不存在时 wrapper 在 `cd` 阶段提前退出，未输出预期错误信息 | 1 | 改为仅在目录存在时规范化路径，让缺失 env 走显式错误分支 |
| 2026-06-16 | 小规模 full execute 在硬件构建阶段失败：`make: riscv64-linux-musl-g++: Permission denied` | 1 | 确认 exporter/env/contract 已进入 HBM 生成阶段；后续需先修复硬件侧 RISC-V musl toolchain/PATH，再继续 `Simulation is complete` 和 `VERIFY-C = PASS` 验收 |

### 5 问恢复检查

| 问题 | 答案 |
|------|------|
| 我现在在哪？ | 阶段 5：SST 脚本参数注入 smoke path，dry-run 注入已完成 |
| 我要去哪里？ | 跑小规模 full SST execute，验证 `Simulation is complete` 和 `VERIFY-C = PASS` |
| 目标是什么？ | 让 `CIM-TileIR` exporter 的 artifacts 真正驱动硬件侧 Golem SST 脚本 |
| 我学到了什么？ | `GOLEM_ARTIFACT_ROOT` + contracts 已足够完成首版注入，不需要先改硬件脚本 |
| 我已经做了什么？ | 新增 wrapper、补齐 env 后端阵列配置、完成 stub 测试和真实硬件 dry-run smoke |

### 阶段 5 调整：硬件侧 env/contract 解耦静态审计
- **状态：**完成
- 背景：
  - 用户明确调整要求：当前不需要直接跑 `run_noc_dma_pipeline.sh`，只需要检查硬件内容有没有解耦出来。
- 已执行的操作：
  - 将阶段 5 验收从完整 SST execute 调整为硬件侧 env/contract 解耦静态审计。
  - 新增 `scripts/check_golem_hardware_contracts.py`，只读硬件仓库文件，不运行 SST。
  - 新增 `tests/test_check_golem_hardware_contracts.py`，把硬件解耦点检查纳入 pytest。
  - 静态确认硬件侧已经具备：
    - `GOLEM_ARTIFACT_ROOT` 外部 artifact root。
    - `GOLEM_MATMUL_*` env contract。
    - `GOLEM_GEMM_*` legacy alias。
    - `contracts/matmul_env_mapping_v1.json` 和 `contracts/matmul_op_desc_resolved.json`。
    - `tools/gen_hbm_init.py` 的 contract reader/writer 和 Golem 后端约束检查。
    - `test_noc_dma.cpp` runtime env reader。
    - `pipeline_config.h` compile-time fallback macros。
  - 更新 `README.md`、`docs/golem-runtime-codegen-roadmap.md`、`task_plan.md` 和 `findings.md`。
- 已创建/修改的文件：
  - `scripts/check_golem_hardware_contracts.py`
  - `tests/test_check_golem_hardware_contracts.py`
  - `README.md`
  - `docs/golem-runtime-codegen-roadmap.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
- 静态审计命令：

```bash
python scripts/check_golem_hardware_contracts.py \
  --hardware-tests-dir /data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests
```

- 静态审计结果：通过。

### 阶段 6 实现：Golem-aware task/event plan
- **状态：**完成 MVP
- 已执行的操作：
  - 扩展 `GolemBackendConfig`，增加 `total_groups`、`total_gemm_cores`、`num_memory_nodes`、`mem_node_size_bytes`、`a_reuse_n_tiles`、`b_reuse_m_tiles`、`dma_slot_count`。
  - 新增 `tilelang_cim/golem_event_planner.py`。
  - 新增 `build_golem_event_plan(ir, golem_backend_config)`。
  - 按硬件 `pipeline_config.h` / `gen_hbm_init.py` 公式实现：
    - macro-task diagonal banding。
    - worker slot / worker core。
    - group id / data node。
    - task slot in node。
    - A packed-once base。
    - B packed-once vector pack base。
    - C output slot base。
    - reuse offset。
  - 输出 Golem 语义事件：
    - `remote_load_a_panel`
    - `gm2imat`
    - `remote_load_b_vector_pack`
    - `gm2ivec_batch`
    - `tile_mvm_batch`
    - `tile_wait_batch`
    - `ovec2gm`
    - `remote_store_c_tile`
  - 新增 `examples/plan_golem_events.py`。
  - 新增 pytest 覆盖 planner 和 CLI。
- 当前边界：
  - 这是 Golem 语义映射计划，不是 cycle model。
  - 不读取 SST stats，不估计 ready queue wait、NoC contention 或 memory queue。
  - cycle/stats 校准进入阶段 7。
- 已创建/修改的文件：
  - `tilelang_cim/golem_event_planner.py`
  - `tilelang_cim/golem_constraints.py`
  - `tilelang_cim/__init__.py`
  - `examples/plan_golem_events.py`
  - `tests/test_golem_event_planner.py`
  - `tests/test_plan_golem_events_example.py`
  - `README.md`
  - `docs/golem-runtime-codegen-roadmap.md`
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
- 目标测试：
  - `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests/test_golem_event_planner.py tests/test_plan_golem_events_example.py -q`
  - 结果：`4 passed`

### 清理 toy architecture 与 abstract event planner
- **状态：**完成
- 背景：
  - 用户确认当前已经接入真实 `RISC-V-CIM-Manycore-SST`，不需要继续维护 toy architecture。
  - 用户认为 abstract event planner 对当前 SST 主线无直接价值，要求删除无关内容。
- 已执行的操作：
  - 删除 toy architecture 代码、示例、文档和测试。
  - 删除 abstract event planner 代码、CLI、文档和测试。
  - 从 `tilelang_cim/__init__.py` 移除已删除 API 的导出。
  - 将 README、task plan、findings 和原型汇总文档同步到当前主线：
    - `All frontends -> CIM-TileIR -> Golem SST backend exporter`
    - `golem_event_plan` 保留为 Golem task mapping/debug/calibration 辅助产物，不作为 SST 必需输入。
- 删除的主要文件：
  - `tilelang_cim/architecture.py`
  - `tilelang_cim/event_planner.py`
  - `examples/architecture/toy_cim_mesh_v0.json`
  - `examples/plan_events.py`
  - `docs/cim-architecture-spec.md`
  - `docs/cim-event-plan-schema.md`
  - toy/abstract planner 对应测试文件。
- 验证结果：
  - `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q`
  - 结果：`25 passed`
  - `bash scripts/check_docs.sh`
  - 结果：`基础文档检查通过。`

### 项目整理：legacy/reference 归档
- **状态：**完成
- 背景：
  - 用户要求重新梳理项目，精简或整理多余内容。
  - 当前代码主线已经收敛到 `All frontends -> CIM-TileIR -> Golem SST backend exporter`。
- 已执行的操作：
  - 将旧 SST C codegen 路线文档归档到 `docs/legacy/`。
  - 将早期 TileLang/RISC-V CIM backend 规划归档到 `docs/legacy/`。
  - 将硬件项目总结从根目录移动到 `docs/reference/golem-sst-hardware-summary.md`。
  - 将旧 PPT 源文件移动到 `docs/legacy/`。
  - 将旧 PPT 导出脚本改名为 `scripts/export_legacy_sst_ppt.sh`，并指向 `docs/legacy/`。
  - 更新 `WORKFLOW.md`、`docs/README.md` 和 ADR，明确 `codegen_sstnoc` 是当前原型工作区，`tilelang/` 和硬件仓库默认只读。
  - 更新 `README.md` 和 `findings.md` 中的 legacy/reference 路径。
- 缓存清理：
  - 发现 `.pytest_cache/`、`tests/__pycache__/`、`tests/fixtures/__pycache__/`、`tilelang_cim/__pycache__/`。
  - 删除命令被审批层拒绝，未绕过执行；这些目录已由 `.gitignore` 覆盖，不影响测试和项目逻辑。
- 验证结果：
  - `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q`
  - 结果：`25 passed`
  - `bash scripts/check_docs.sh`
  - 结果：`基础文档检查通过。`

### 阶段 7：No-SST-execute offline artifact validation
- **状态：**完成 MVP
- 背景：
  - 用户反馈当前 `run_noc_dma_pipeline.sh` 存在技术问题，真实硬件测试暂时无法进行。
  - 当前阶段不应被完整 SST execute 阻塞，应先验证 codegen 生成的 env/contract artifacts 是否自洽。
- 已执行的操作：
  - 新增 `scripts/validate_golem_artifacts.py`。
  - 新增 `validate_golem_artifacts(artifact_root, hardware_tests_dir=None)` API。
  - 支持 CLI：

```bash
python scripts/validate_golem_artifacts.py \
  --artifact-root /tmp/golem_codegen_artifacts \
  --output /tmp/golem_artifact_validation.json
```

  - 校验内容：
    - `golem_sst.env` 存在。
    - `contracts/matmul_op_desc_resolved.json` 存在。
    - `contracts/matmul_env_mapping_v1.json` 存在。
    - `GOLEM_MATMUL_*` env 与 resolved contract 一致。
    - `GOLEM_ARRAY_INPUT_SIZE`、`GOLEM_ARRAY_OUTPUT_SIZE`、`GOLEM_NUM_ARRAYS` 与 block shape 一致。
    - legacy `GOLEM_GEMM_*` alias 与 `GOLEM_MATMUL_*` 一致。
  - 新增 `tests/test_validate_golem_artifacts.py`。
  - 更新 `README.md`、`task_plan.md` 和 `docs/golem-runtime-codegen-roadmap.md`。
- TDD 记录：
  - 先运行 `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests/test_validate_golem_artifacts.py -q`。
  - 初始结果：失败，`ModuleNotFoundError: No module named 'scripts.validate_golem_artifacts'`。
  - 实现脚本后目标测试结果：`4 passed`。
- 最终验证：
  - `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q`
  - 结果：`29 passed`
  - `bash scripts/check_docs.sh`
  - 结果：`基础文档检查通过。`
  - CLI 链路：

```bash
python examples/gemm_ir.py \
  --output /tmp/gemm.golem.cimtile.json \
  --m 4096 --n 128 --k 4096 \
  --bm 64 --bn 64 --bk 64 \
  --mesh-w 4 --mesh-h 5 \
  --pipeline-stages 1 \
  --a-dtype fp32 --b-dtype fp32 --c-dtype fp32

python examples/export_golem_sst.py \
  /tmp/gemm.golem.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /tmp/golem_codegen_artifacts

python scripts/validate_golem_artifacts.py \
  --artifact-root /tmp/golem_codegen_artifacts \
  --output /tmp/golem_artifact_validation.json
```

  - 结果：validation report 中 `ok=true`，所有 checks 为 `ok`。

### 阶段 7：Golem mapping consistency check
- **状态：**完成 MVP
- 背景：
  - 在真实 SST execute 不可用时，需要继续强化离线闭环。
  - artifact validator 证明 exporter 产物自洽；mapping consistency check 进一步证明 resolved contract 与 `golem_event_plan` 映射语义一致。
- 已执行的操作：
  - 新增 `scripts/check_golem_mapping_consistency.py`。
  - 新增 `check_golem_mapping_consistency(artifact_root, event_plan)` API。
  - 支持 CLI：

```bash
python scripts/check_golem_mapping_consistency.py \
  --artifact-root /tmp/golem_codegen_artifacts \
  --event-plan /tmp/gemm.golem_event_plan.json \
  --output /tmp/golem_mapping_consistency.json
```

  - 校验内容：
    - event plan header 为 `mode=golem_event_plan`、`backend=golem_sst`。
    - `m_tiles/n_tiles/k_tiles` 与 resolved contract 的 `m/n/k` 和 `block_m/block_n/block_k` 一致。
    - `len(tasks)` 等于 `total_gemm_tasks`。
    - `worker_core`、`worker_slot`、`data_node_idx`、`macro_task_id` 等字段在合法范围内。
    - `a_base_mm`、`b_pack_base_mm`、`c_base_mm` 存在且非负。
    - Golem 语义事件中的地址引用与 task base address 一致。
  - 新增 `tests/test_check_golem_mapping_consistency.py`。
  - 更新 `README.md`、`task_plan.md` 和 `docs/golem-runtime-codegen-roadmap.md`。
- TDD 记录：
  - 先运行 `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests/test_check_golem_mapping_consistency.py -q`。
  - 初始结果：失败，`ModuleNotFoundError: No module named 'scripts.check_golem_mapping_consistency'`。
  - 实现脚本后目标测试结果：`4 passed`。
- 最终验证：
  - `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q`
  - 结果：`33 passed`
  - `bash scripts/check_docs.sh`
  - 结果：`基础文档检查通过。`
  - CLI 链路：

```bash
python examples/gemm_ir.py \
  --output /tmp/gemm.golem.cimtile.json \
  --m 4096 --n 128 --k 4096 \
  --bm 64 --bn 64 --bk 64 \
  --mesh-w 4 --mesh-h 5 \
  --pipeline-stages 1 \
  --a-dtype fp32 --b-dtype fp32 --c-dtype fp32

python examples/export_golem_sst.py \
  /tmp/gemm.golem.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /tmp/golem_codegen_artifacts

python examples/plan_golem_events.py \
  /tmp/gemm.golem.cimtile.json \
  --output /tmp/gemm.golem_event_plan.json

python scripts/check_golem_mapping_consistency.py \
  --artifact-root /tmp/golem_codegen_artifacts \
  --event-plan /tmp/gemm.golem_event_plan.json \
  --output /tmp/golem_mapping_consistency.json
```

  - 结果：mapping consistency report 中 `ok=true`，`plan_header`、`tile_counts_match_contract`、`task_count_matches_tiles`、`task_fields_in_range`、`base_addresses_present`、`event_address_refs` 均为 `ok`。

### 规划调整：硬件可运行后的下一阶段
- **状态：**完成文档调整
- 背景：
  - 用户确认硬件侧 `run_noc_dma_pipeline.sh` 现在已经可以运行。
  - 用户指出目前还没有做 codegen-driven 硬件接入测试。
  - 用户明确当前不做 sweep。
- 已执行的文档调整：
  - 将当前阶段改为 `阶段 8：codegen-driven hardware integration smoke`。
  - 将 stats report 顺延为 `阶段 9：single-run SST stats report`。
  - 将 extractor / TileOPs-like smoke path 顺延为阶段 10。
  - 将 runtime ABI / ELF 长期闭环顺延为阶段 11。
  - 在 `task_plan.md` 中增加手动硬件接入 smoke 验收步骤：
    - codegen 生成 `CIM-TileIR JSON`。
    - exporter 生成 `/tmp/golem_codegen_artifacts`。
    - artifact validator 通过。
    - Golem event plan 生成。
    - mapping consistency checker 通过。
    - `examples/run_golem_sst_smoke.sh --execute` 真实运行。
    - 验证 `Simulation is complete`、`VERIFY-C = PASS` 和 stats CSV 生成。
  - 在 `README.md` 和 `docs/golem-runtime-codegen-roadmap.md` 中补充 codegen-driven hardware integration smoke 用法。
  - 明确当前不做 sweep、自动调参、多 run 聚合或预测模型。
- 本次只修改文档，未运行真实硬件接入测试。

### 规划文档整理：当前阶段聚焦 codegen-driven hardware smoke
- **状态：**完成文档调整
- 背景：
  - 用户要求“先修改文档”。
  - 当前硬件默认脚本已经可运行，但 `codegen_sstnoc` 生成 artifacts 驱动真实 SST 的接入测试尚未执行。
- 已执行的文档调整：
  - 更新 `docs/golem-runtime-codegen-roadmap.md`，将旧的“第一阶段/第二阶段”历史口吻整理为“已完成 / 当前阶段 / 下一阶段”。
  - 明确当前阶段是 `codegen-driven hardware integration smoke`。
  - 明确该阶段验收重点是 `CIM-TileIR JSON -> Golem SST artifacts -> validator -> mapping checker -> run_golem_sst_smoke.sh --execute -> 真实 run_noc_dma_pipeline.sh`。
  - 明确需要记录 artifact root、validation report、mapping report、硬件 log、stats-dir、`Simulation is complete` 和 `VERIFY-C = PASS`。
  - 保留 single-run SST stats report 作为 smoke 通过后的下一阶段。
  - 保留“不做 sweep”的决策。
- 本次仍只修改文档，未运行真实硬件接入测试。

### 阶段 8：codegen-driven hardware integration smoke 尝试
- **状态：**部分完成，完整 SST run 被当前执行环境阻塞
- 已执行的操作：
  - 生成与硬件默认配置一致的 `CIM-TileIR JSON`：

```bash
python examples/gemm_ir.py \
  --output /tmp/gemm.golem.cimtile.json \
  --m 1024 --n 1024 --k 1024 \
  --bm 64 --bn 64 --bk 64 \
  --mesh-w 4 --mesh-h 5 \
  --pipeline-stages 1 \
  --a-dtype fp32 --b-dtype fp32 --c-dtype fp32
```

  - 导出 Golem SST artifacts：

```bash
python examples/export_golem_sst.py \
  /tmp/gemm.golem.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /tmp/golem_codegen_artifacts
```

  - 生成文件：
    - `/tmp/golem_codegen_artifacts/golem_sst.env`
    - `/tmp/golem_codegen_artifacts/contracts/matmul_op_desc_resolved.json`
    - `/tmp/golem_codegen_artifacts/contracts/matmul_env_mapping_v1.json`
  - 运行 artifact validator：

```bash
python scripts/validate_golem_artifacts.py \
  --artifact-root /tmp/golem_codegen_artifacts \
  --output /tmp/golem_artifact_validation.json
```

    - 结果：`ok=true`
  - 生成 Golem task mapping/debug plan：

```bash
python examples/plan_golem_events.py \
  /tmp/gemm.golem.cimtile.json \
  --output /tmp/gemm.golem_event_plan.json
```

  - 运行 mapping consistency checker：

```bash
python scripts/check_golem_mapping_consistency.py \
  --artifact-root /tmp/golem_codegen_artifacts \
  --event-plan /tmp/gemm.golem_event_plan.json \
  --output /tmp/golem_mapping_consistency.json
```

    - 结果：`ok=true`
- 硬件 smoke 尝试记录：
  - 首次直接运行时，`riscv64-linux-musl-g++` 解析不到用户 `.bashrc` 中的工具链路径，编译阶段失败。
  - 改用 `/data4/jjgong/local/packages/riscv64_musl_toolchain/bin` 后，编译器可执行，但 assembler 不认识 Golem 自定义指令，例如 `mvm.ovec2gm`、`remote.st`。
  - 改用用户 `.bashrc` 中的工具链路径 `/data/lzq/packages/install/riscv64_musl_toolchain/bin` 后，RISC-V test binary 编译通过。
  - 使用完整环境：

```bash
PATH=/data4/jjgong/local/sstcore/bin:/data/lzq/packages/install/riscv64_musl_toolchain/bin:$PATH
LD_LIBRARY_PATH=/data4/jjgong/miniconda3/lib:/data4/jjgong/local/sstcore/lib:$LD_LIBRARY_PATH
```

    - HBM 初始化通过。
    - RISC-V test binary 编译通过。
    - SST 启动阶段失败，日志路径：
      `/tmp/golem_codegen_artifacts/logs/codegen_smoke_fullenv_run_20260617_162641_2.log`
    - 失败原因：

```text
opal_ifinit: socket() failed with errno=1
No network interfaces were found for out-of-band communications.
MPI_INIT failed
```

  - 该错误发生在 OpenMPI/SST 启动阶段，当前证据显示不是 codegen artifact、contract、HBM layout 或 RISC-V 编译问题。
  - 用户已允许非沙箱重跑，但 `require_escalated` 请求被审批层 503 拒绝，无法在本轮由 Codex 继续完成真实 SST run。
- 当前产物路径：
  - `CIM-TileIR JSON`：`/tmp/gemm.golem.cimtile.json`
  - artifact root：`/tmp/golem_codegen_artifacts`
  - artifact validation report：`/tmp/golem_artifact_validation.json`
  - Golem mapping/debug plan：`/tmp/gemm.golem_event_plan.json`
  - mapping consistency report：`/tmp/golem_mapping_consistency.json`
  - 最近失败 log：`/tmp/golem_codegen_artifacts/logs/codegen_smoke_fullenv_run_20260617_162641_2.log`

### 临时目录迁移：避免 `/tmp` HBM mmap backing file 触发 Bus error
- **状态：**完成实现与文档调整
- 背景：
  - 用户在终端手动运行 codegen-driven hardware smoke 后，SST 进入架构初始化阶段，但在 `memHierarchy::Backend::BackingMMAP` 处触发 `Bus error`。
  - 现场检查显示 `/tmp` 所在根分区可用空间仅约 49MB，而 codegen smoke 的 HBM backing files 至少包含 4 个 `hbm_init_node*.bin` 和 4 个 `hbm_out_node*.bin`，每个约 128MB。
  - 因此 `/tmp/golem_codegen_artifacts` 不适合作为真实 SST smoke 的 artifact root。
- 已执行的修改：
  - 修改 `examples/run_golem_sst_smoke.sh`，不传 `--artifact-root` 时默认使用 `/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts`。
  - 新增 `tests/test_run_golem_sst_smoke.py` 覆盖默认 artifact root。
  - 将 README、task plan、Golem roadmap 和 CIM-TileIR prototype summary 中的当前运行示例迁移到 `/data4/jjgong/tmp/codegen_sstnoc`。
  - 将测试命令中的 `TILELANG_CACHE_DIR` 示例改为 `/data4/jjgong/tmp/tilelang-cache`。
- TDD 记录：
  - 先运行 `TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests/test_run_golem_sst_smoke.py -q`。
  - 初始结果：失败，`[ERROR] --artifact-root is required`。
  - 实现 wrapper 默认 artifact root 后，目标测试结果：`3 passed`。

### 阶段 8 shape 调整与 sample tensor 来源确认
- **状态：**完成
- 背景：
  - 用户认为原先 `M=4096, N=128, K=4096` 对当前 smoke 太大，要求改为 `M=1024, N=1024, K=128`。
  - 用户询问硬件脚本中 `Using external tensor files: A=.../data/a.bin, B=.../data/b.bin` 的 tensor 来源。
- 已执行的修改：
  - 将当前 README、Golem roadmap、CIM-TileIR summary 和 wrapper smoke 测试中的推荐 Golem smoke shape 改为 `M=1024, N=1024, K=128`。
  - 保留部分单元测试中的 `4096/128/4096` 形状作为公式和 validator 测试夹具，不把历史测试全部改成当前 smoke 规模。
  - 重新生成 `/data4/jjgong/tmp/codegen_sstnoc` 下的 codegen artifacts。
- dry-run 验证：

```text
GOLEM_GEMM_M=1024
GOLEM_GEMM_N=1024
GOLEM_GEMM_K=128
GOLEM_GEMM_K_TILES(derived)=2
GOLEM_TENSOR_SOURCE=sample
python3 tools/gen_sample_tensors.py --m 1024 --n 1024 --k 128 --dtype fp32 --a-out .../data/a.bin --b-out .../data/b.bin
```

- tensor 来源结论：
  - 当前硬件默认 `50_tensor_verify.env` 设置 `GOLEM_TENSOR_SOURCE=sample`。
  - `run_noc_dma_pipeline.sh` 在 sample 模式下调用 `tools/gen_sample_tensors.py`，生成 `data/a.bin` 和 `data/b.bin`。
  - `gen_sample_tensors.py` 生成确定性样例矩阵：
    - `A[i,j] = ((i * 3 + j * 5) % 17) - 8`
    - `B[i,j] = ((i * 7 + j * 2) % 19) - 9`
  - 当前 dtype 为 `fp32` 时，脚本把这些整数样例值转换为 float32 二进制写入文件。

### Golem smoke wrapper 运行环境边界修正
- **状态：**完成
- 背景：
  - 用户指出硬件测试环境变量已经存在于硬件脚本和用户 `~/.bashrc` 中，codegen wrapper 不应该要求额外复制 PATH/LD_LIBRARY_PATH。
  - 根因确认：用户 `~/.bashrc` 开头有交互 shell 判断，非交互 shell 会提前 `return`，因此 Codex/CI 这类启动方式可能没有加载后续 SST/toolchain 环境。
- 已执行的修改：
  - `examples/run_golem_sst_smoke.sh` 新增 `--use-user-shell-env`，在非交互场景下通过交互 bash 重入，让 `~/.bashrc` 中的用户环境生效。
  - wrapper 调用硬件脚本前检查 `sst` 和 `riscv64-linux-musl-g++` 是否可见；缺失时给出明确提示，而不是让硬件脚本在后续阶段隐式失败。
  - wrapper 仍然不硬编码 SST、RISC-V toolchain、DRAMSim3 或 `LD_LIBRARY_PATH`；它只负责 source codegen 生成的 `golem_sst.env` 并导出 `GOLEM_ARTIFACT_ROOT`。
  - 更新 README、WORKFLOW 和 Golem roadmap，明确本地交互终端可直接运行 wrapper，Codex/CI/非交互 shell 可加 `--use-user-shell-env`。
- TDD 记录：
  - 先新增 `tests/test_run_golem_sst_smoke.py` 用例覆盖 `--use-user-shell-env` 重入和缺失 runtime tools 的错误提示。
  - 初始结果：新增用例失败，wrapper 不认识 `--use-user-shell-env`，且未检查 `sst/riscv64-linux-musl-g++`。
  - 实现后 targeted 验证：`TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests/test_run_golem_sst_smoke.py -q`，结果 `5 passed`。

### 重新执行 codegen-driven smoke 测试
- **状态：**离线链路与硬件前置阶段通过，SST execute 仍受当前 Codex 沙箱 OpenMPI 限制
- 本次 run root：
  - `/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346`
- 已执行并通过：
  - 生成 `gemm.golem.cimtile.json`
  - 导出 `golem_codegen_artifacts/golem_sst.env`
  - 导出 `contracts/matmul_op_desc_resolved.json`
  - 导出 `contracts/matmul_env_mapping_v1.json`
  - `scripts/validate_golem_artifacts.py`：`ok=true, errors=0, warnings=0`
  - `examples/plan_golem_events.py`
  - `scripts/check_golem_mapping_consistency.py`：`ok=true, errors=0, warnings=0`
  - wrapper dry-run：确认 `GOLEM_GEMM_M=1024, GOLEM_GEMM_N=1024, GOLEM_GEMM_K=128`
  - HBM 初始化：生成 4 个 `hbm_init_node*.bin` 和 4 个 `hbm_out_node*.bin`，每个 128MB
  - RISC-V test binary 编译：生成静态链接 RISC-V ELF
- 本次执行中发现并修复：
  - `--use-user-shell-env` 重入时直接 exec 脚本文件，若脚本没有 executable bit 会失败；已改为通过 `bash "$0" ...` 重入。
  - 当前用户 shell 中 `CONDA_PREFIX=/data4/jjgong/miniconda3`，但 `LD_LIBRARY_PATH` 未包含 `$CONDA_PREFIX/lib`，导致 `sst` 缺 `libpython3.13.so.1.0`；wrapper 已在存在 `CONDA_PREFIX/lib` 时自动补入 `LD_LIBRARY_PATH`。
  - 新增对应单测后，`tests/test_run_golem_sst_smoke.py` 结果为 `6 passed`。
- 当前剩余 execute 失败点：
  - 最新日志：`/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/golem_codegen_artifacts/logs/full_smoke_execute_after_conda_lib_run_20260617_173739_2.log`
  - 失败内容：

```text
opal_ifinit: socket() failed with errno=1
No network interfaces were found for out-of-band communications.
MPI_INIT failed
```

  - 结论：当前失败点是 Codex 沙箱对 OpenMPI/socket 的限制；codegen artifact、env/contract、HBM 初始化和 RISC-V 编译均已通过。
- 验证：
  - `TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q`：`37 passed`
  - `bash scripts/check_docs.sh`：通过

### 阶段 8：codegen-driven hardware integration smoke 成功收口
- **状态：**完成
- 用户在正常终端中完成真实 SST run。
- run root：
  - `/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346`
- 成功日志：
  - `/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/golem_codegen_artifacts/logs/full_smoke_execute_terminal_run_20260617_174010_1201356.log`
- stats 目录：
  - `/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/golem_codegen_artifacts/stats/overlap0/run_20260617_174010_1201356`
- 关键结果：

```text
Simulation is complete, simulated time: 234.589 us
total_cycles=2889.187500
worker_avg_total_cycles=2889.187500
gemm_system_latency_cycles=5911.000000
exec_array_utilization_pct=70.884981
exec_system_array_utilization_pct=34.647268
```

- 已生成 stats：
  - `execution_summary.csv`
  - `dma_summary.csv`
  - `noc_summary.csv`
  - `memory_summary.csv`
  - `memory_queue_summary.csv`
  - `submit_ready_causal_summary.csv`
  - 额外生成：`execution_debug_summary.csv`、`noc_latency_summary.csv`、`noc_hotspot_summary.csv`、`sched_pressure_summary.csv` 等。
- 关于 `VERIFY-C`：
  - 硬件脚本在 `VERIFY_C=1` 时调用 `verify/verify_c_against_golden.py`。
  - `[VERIFY-C] PASS` 输出到终端 stdout，不写入 SST log 文件。
  - 当前 run 能继续导出完整 stats 和 `run_summary.csv`，说明 verify 后处理没有失败；若 verify 失败，脚本会因 `set -e` 中止。
- 阶段结论：
  - `CIM-TileIR -> Golem SST exporter -> env/contract artifacts -> run_golem_sst_smoke.sh -> 真实 run_noc_dma_pipeline.sh -> SST complete -> stats CSV` 已打通。
  - 下一阶段进入 `single-run SST stats report`，不做 sweep。

### 阶段 9：single-run SST stats report MVP
- **状态：**完成首版
- 已执行的修改：
  - 新增 `scripts/build_golem_single_run_report.py`。
  - 新增 `tests/test_build_golem_single_run_report.py`。
  - 更新 `task_plan.md`、`README.md`、`docs/golem-runtime-codegen-roadmap.md`。
- report 输入：
  - artifact root：`/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/golem_codegen_artifacts`
  - event plan：`/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/gemm.golem_event_plan.json`
  - stats dir：`/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/golem_codegen_artifacts/stats/overlap0/run_20260617_174010_1201356`
  - log：`/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/golem_codegen_artifacts/logs/full_smoke_execute_terminal_run_20260617_174010_1201356.log`
- report 输出：
  - `/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/golem_single_run_report.json`
- report 关键结果：

```text
mode=golem_single_run_stats_report
status=ok
model.status=not_calibrated
m_tiles=16
n_tiles=16
k_tiles=2
total_gemm_tasks=256
active_worker_cores=16
simulation_complete=true
simulated_time=234.589 us
total_cycles=2889.1875
gemm_system_latency_cycles=5911.0
array_utilization_pct=70.884981
system_array_utilization_pct=34.647268
cycles_per_gemm_task=11.285888671875
cycles_per_macro_task=11.285888671875
compute_active_pct=73.10013628398988
prefetch_wait_pct=26.276851190862484
writeback_wait_pct=0.5537889112423475
control_other_pct=0.06922361390529344
system_vs_worker_utilization_gap_pct=36.237713
warnings=[]
```

- 实现边界：
  - 只做单次真实运行的结构化观测和派生指标。
  - stats CSV 缺失时输出 structured warnings，不直接崩溃。
  - 输出 `model.status=not_calibrated`，不声称已有预测模型。
  - 当前不做 sweep、自动调参、多 run 聚合或图表生成。
- TDD 记录：
  - 初始运行 `TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests/test_build_golem_single_run_report.py -q` 失败，原因是 `scripts.build_golem_single_run_report` 模块不存在。
  - 实现脚本后 targeted 测试通过。
  - 使用真实 run 生成 report 后，发现真实 event plan 使用 `stats` 字段、真实 execution CSV 无 `exec_` 前缀；已补兼容并重新验证。
