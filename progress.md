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
