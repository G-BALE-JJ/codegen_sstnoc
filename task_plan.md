# CIM-TileIR 项目计划：TileLang 到 Golem SST 参数导出

## 目标

当前分支以 RISC-V CIM 2D-mesh 的 `CIM-TileIR` 技术路线为准。当前最终产物是从 TileLang 语言或 TileLang 生成的 `CIM-TileIR` 中解析 GEMM 参数，解耦前端编程语言与后端 SST 脚本配置，并把所有必要参数落到 Golem SST 的 env、contract JSON 和运行脚本输入中。

当前阶段仍然是编译器侧原型，不承诺 OS loader、runtime ABI 或 RISC-V ELF 工具链闭环。`GolemArchitectureSpec` 不作为第一阶段主产物；硬件参数首版只作为 Golem exporter 的后端约束校验。

## 当前阶段

阶段 4：TileLang-to-Golem SST env/contract exporter

## 阶段划分

### 阶段 1：CIM-TileIR JSON 原型
- [x] 定义 `CIM-TileIR` GEMM 子集 schema
- [x] 实现 `build_gemm_ir`
- [x] 实现 `validate_cim_tile_ir`
- [x] 实现稳定 JSON 导出
- [x] 新增静态 GEMM JSON 生成示例
- [x] 新增 pytest 覆盖 IR 构造、checker 和 CLI
- **状态：**完成

### 阶段 2：TileLang GEMM extractor 与 abstract event expander
- [x] 实现窄模板 TileLang GEMM 源码 extractor
- [x] 支持 TileLang `PrimFunc.script()` 中 `T.match_buffer`、`T.alloc_buffer`、`T.serial`、`T.gemm` 的 MVP 提取
- [x] 实现 `build_event_plan`
- [x] 展开 per-output-tile task 和 `clear_acc` / `dma_load` / `cim_gemm` / `dma_store` 事件
- [x] 输出 DMA bytes、CIM op count、MACs、core utilization 等粗略统计
- [x] 明确无 architecture spec 时 `estimated_cycles=0`
- **状态：**完成

### 阶段 3：architecture-aware event planning v0
- [x] 定义 `CIMArchitectureSpec` JSON schema 和 checker
- [x] 新增 toy architecture spec 示例
- [x] 实现 `CIM-TileIR + architecture spec` 联合校验
- [x] 校验 local SRAM、accumulator、dtype、CIM tile shape、DMA alignment 等约束
- [x] 新增 `build_arch_event_plan`
- [x] 在 `serial_formula_v0` 下输出每个事件、每个 task、每个 core 的粗略 cycle estimate
- [x] 扩展 `examples/plan_events.py --arch`
- [x] 新增 architecture spec、arch checker、arch event planner 和 CLI 测试
- [x] 补充 schema 文档
- **状态：**完成

### 阶段 4：TileLang-to-Golem SST env/contract exporter
- [ ] 新增 `tilelang_cim/golem_exporter.py`
- [ ] 新增 `tilelang_cim/golem_constraints.py`
- [ ] 新增 `examples/export_golem_sst.py`
- [ ] 支持从 TileLang 源码 fixture 导出 Golem SST artifacts
- [ ] 支持从已有 `CIM-TileIR JSON` 导出 Golem SST artifacts
- [ ] 输出 `golem_sst.env`
- [ ] 输出 `contracts/matmul_op_desc_resolved.json`
- [ ] 输出 `contracts/matmul_env_mapping_v1.json`
- [ ] 后端约束校验覆盖 dtype、layout、transpose、M/N/K 整除、`block_k == GOLEM_ARRAY_INPUT_SIZE`、`block_m == GOLEM_ARRAY_OUTPUT_SIZE`、`block_n <= GOLEM_NUM_ARRAYS`
- [ ] 新增 exporter 和 constraints 的 pytest 覆盖
- **状态：**未开始

### 阶段 5：SST 脚本参数注入 smoke path
- [ ] 设计从 `golem_sst.env` 注入 `run_noc_dma_pipeline.sh` 的最小流程
- [ ] 确认 `GOLEM_ARTIFACT_ROOT` 下 contracts 的生成/复用边界
- [ ] 可选新增 wrapper：`examples/run_golem_sst_smoke.sh`
- [ ] 硬件侧 smoke 验收 `Simulation is complete`
- [ ] 硬件侧 smoke 验收 `VERIFY-C = PASS`
- [ ] 校验硬件侧生成的 `matmul_op_desc_resolved.json` 与 exporter 输出一致
- **状态：**未开始

### 阶段 6：Golem-aware task/event plan
- [ ] 新增 `build_golem_event_plan(ir, golem_backend_config)`
- [ ] 按 `pipeline_config.h` 实现 macro-task、m/n group、A/B reuse window、worker slot、worker core、group、data node 映射
- [ ] 在 event plan 中加入 `a_base_mm`、`b_pack_base_mm`、`c_base_mm`、`task_slot_in_node`、`reuse_offset`
- [ ] 将 toy `dma_load A/B + cim_gemm` 事件升级为 Golem 语义：remote load、GM2IMAT、GM2IVEC batch、MVM batch、wait、OVEC2GM、remote store
- [ ] 新增测试与 `pipeline_config.h` / `gen_hbm_init.py` 的公式对齐
- **状态：**未开始

### 阶段 7：stats-based cycle model 校准
- [ ] 读取 `execution_summary.csv`、`dma_summary.csv`、`noc_summary.csv`
- [ ] 对比 `golem_event_plan` 估计与 SST 观测结果
- [ ] 优先建模 WCP slot、prefetch window、strict-order consumption 和 ready-to-compute queue wait
- [ ] 输出 compute_active / prefetch_wait / writeback_wait 对齐报告
- **状态：**未开始

### 阶段 8：extractor 与 TileOPs-like smoke path
- [ ] 减少 extractor 对 A/B/C 参数命名的依赖
- [ ] 增加不同 dtype、默认 pipeline stages、不同变量命名的 fixture
- [ ] 改进缺失 shared buffer、fragment buffer、`T.gemm`、静态 shape 的错误信息
- [ ] 保持对动态 shape、转置 GEMM、复杂 fusion 的明确拒绝
- [ ] 新增 TileOPs-like GEMM fixture
- [ ] 验证 extractor 对简化 TileOPs GEMM 形态的支持边界
- [ ] 对真实 TileOPs 复杂模式输出明确 unsupported reason
- [ ] 不修改 `/data4/jjgong/TileOPs`
- **状态：**未开始

### 阶段 9：runtime ABI 与 ELF 长期闭环
- [ ] 定义 runtime ABI，例如 `tl_core_id`、`tl_dma_load`、`tl_dma_store`、`tl_cim_gemm`
- [ ] 设计 C++ SPMD kernel codegen
- [ ] 集成 RISC-V 编译、链接、加载工具链
- [ ] 打通 GEMM ELF 闭环
- **状态：**长期目标

## 关键问题

1. `CIMArchitectureSpec` 第一版是否长期保持 JSON，还是后续升级为 Python dataclass / pydantic-like schema？
2. `serial_formula_v0` 是否足够作为 architecture-aware planner v0 的 cycle model？
3. toy spec 的 SRAM、accumulator、DMA、CIM primitive 参数应如何与未来真实架构参数对齐？
4. output tile 大于 core 数时，第一版是否继续按 row-major core wrap-around 累加 core cycles？
5. output tile 小于 core 数时，后续是否需要 split-K / split-M / split-N 来提升 utilization？
6. TileLang extractor 下一步应继续 out-of-tree AST MVP，还是开始接入 TileLang pass pipeline？
7. TileOPs-like smoke path 应优先覆盖普通 GEMM 还是 grouped GEMM？
8. exporter 首版输入是否同时支持 TileLang 源码和 `CIM-TileIR JSON`，还是先只支持 JSON？
9. `BM/BK` 整数倍 micro-tiling 尚未在硬件侧完成时，codegen 是否应严格拒绝非硬件 tile shape？
10. `run_noc_dma_pipeline.sh` 是否需要新增显式 `--contract-dir` / `--env-file` 参数，还是首版只通过 `source golem_sst.env` 和 `GOLEM_ARTIFACT_ROOT` 注入？

## 已做决策

| 决策 | 原因 |
|------|------|
| 当前分支以 CIM-TileIR 为主线 | 分支已包含 `tilelang_cim`、examples 和 tests，近期工作应围绕已有原型推进 |
| SST C codegen 降为历史背景/长期旁支 | 当前用户明确要求以 CIM-TileIR 技术路线为准 |
| toy architecture spec 已作为阶段 3 前置项完成 | 它服务于 `serial_formula_v0` toy planner，不再作为 Golem 对接的第一阶段主线 |
| 无 `--arch` 时保持 abstract event expander 行为 | 兼容已有原型和测试，避免把无架构参数的事件骨架伪装成 simulator |
| 有 `--arch` 时才输出非 0 cycle estimate | 让 cycle estimate 有明确参数来源 |
| 第一版 cycle model 使用 `serial_formula_v0` | 先建立可测试、可解释的 toy 模型，不提前承诺 overlap / NoC contention |
| 当前不修改 `TileOPs` | TileOPs 先作为上层用例来源，避免把问题面扩大 |
| 下一阶段优先做 TileLang-to-Golem SST exporter | 用户最终产物是从 TileLang 解析参数并填充 SST env/script，而不是先做硬件建模 |
| Golem path 先生成 env/contract，不直接生成 RoCC 指令 | 硬件 runtime 已有 header-only API/WCP descriptor，先对齐可消费接口风险更低 |
| 非硬件 tile shape 首版严格拒绝 | 硬件总结显示 micro-tiling 尚未完成，不能让 codegen 生成 runtime 不能正确执行的任务 |
| Architecture spec 降级为后端约束校验 | 当前主线是前端参数到 SST 脚本填充，硬件参数只需服务 exporter 的合法性检查 |

## 当前验收命令

```bash
TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q
bash scripts/check_docs.sh
python examples/gemm_ir.py --output /tmp/gemm.cimtile.json
python examples/plan_events.py \
  /tmp/gemm.cimtile.json \
  --arch examples/architecture/toy_cim_mesh_v0.json \
  --output /tmp/gemm.eventplan.json
# 阶段 4 完成后的新增目标命令：
# python examples/export_golem_sst.py \
#   tests/fixtures/tilelang_gemm_fixture.py \
#   --artifact-root /tmp/golem_codegen_artifacts
```

## 备注

- 涉及 TileLang 导入的测试需要设置 `TILELANG_CACHE_DIR=/tmp/tilelang-cache`，避免默认写 `/home/jiajun/.tilelang`。
- 每完成一个阶段后更新本文件。
- 规划文件应始终作为流程和决策的权威记录。
