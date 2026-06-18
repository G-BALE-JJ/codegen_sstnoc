# CIM-TileIR 项目计划：统一前端到 Golem SST 后端导出

## 目标

当前分支以 RISC-V CIM 2D-mesh 的 `CIM-TileIR` 技术路线为准。当前最终产物是让所有前端语言先统一解析到 `CIM-TileIR`，再由硬件后端消费 `CIM-TileIR` 并落实到具体加载环境中。首个前端是 TileLang，首个硬件后端是 Golem SST。

当前阶段仍然是编译器侧原型，不承诺 OS loader、runtime ABI 或 RISC-V ELF 工具链闭环。`CIM-TileIR` 是唯一前后端解耦接口；Golem 硬件参数首版只作为 Golem backend exporter 的后端约束校验。

## 当前阶段

阶段 8：codegen-driven hardware integration smoke

## 临时目录约定

项目级临时产物默认放在 `/data4/jjgong/tmp/codegen_sstnoc`。Golem SST smoke 的默认 artifact root 是 `/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts`，避免 HBM mmap backing files 写入根分区 `/tmp`。

## 阶段划分

### 阶段 1：CIM-TileIR JSON 原型
- [x] 定义 `CIM-TileIR` GEMM 子集 schema
- [x] 实现 `build_gemm_ir`
- [x] 实现 `validate_cim_tile_ir`
- [x] 实现稳定 JSON 导出
- [x] 新增静态 GEMM JSON 生成示例
- [x] 新增 pytest 覆盖 IR 构造、checker 和 CLI
- **状态：**完成

### 阶段 2：TileLang GEMM extractor
- [x] 实现窄模板 TileLang GEMM 源码 extractor
- [x] 支持 TileLang `PrimFunc.script()` 中 `T.match_buffer`、`T.alloc_buffer`、`T.serial`、`T.gemm` 的 MVP 提取
- [x] 明确 TileLang 只是第一个前端，extractor 输出必须先落到 `CIM-TileIR`
- [x] 删除与真实 SST 主线无关的 abstract event planner 产物
- **状态：**完成

### 阶段 3：移除 toy architecture / abstract planner 主线
- [x] 确认本地已有真实 `RISC-V-CIM-Manycore-SST` Golem 硬件/运行时链路
- [x] 确认 toy `CIMArchitectureSpec`、`serial_formula_v0` 和 abstract event planner 不再服务当前主线
- [x] 删除 toy architecture schema、toy 示例、abstract planner CLI 和相关测试
- [x] 将当前主线收敛为 `CIM-TileIR -> Golem SST backend exporter`
- **状态：**完成

### 阶段 4：CIM-TileIR-to-Golem SST backend exporter
- [x] 检查并补齐 `CIM-TileIR` schema：layout 与 transpose flags 必须能表达 Golem 后端需求
- [x] 新增 `tilelang_cim/golem_exporter.py`
- [x] 新增 `tilelang_cim/golem_constraints.py`
- [x] 新增 `examples/export_golem_sst.py`
- [x] 核心 exporter API 以 `CIM-TileIR dict` 为输入
- [x] CLI 支持从已有 `CIM-TileIR JSON` 导出 Golem SST artifacts
- [x] CLI 支持从 TileLang 源码 fixture 导出 Golem SST artifacts，但内部必须先生成 `CIM-TileIR`
- [x] 输出 `golem_sst.env`
- [x] 输出 `contracts/matmul_op_desc_resolved.json`
- [x] 输出 `contracts/matmul_env_mapping_v1.json`
- [x] 后端约束校验覆盖 dtype、layout、transpose、M/N/K 整除、`block_k == GOLEM_ARRAY_INPUT_SIZE`、`block_m == GOLEM_ARRAY_OUTPUT_SIZE`、`block_n <= GOLEM_NUM_ARRAYS`
- [x] 新增 exporter 和 constraints 的 pytest 覆盖
- **状态：**完成

### 阶段 5：硬件侧 env/contract 解耦静态审计
- [x] 设计从 `golem_sst.env` 注入硬件侧 env/contract 的最小流程
- [x] 确认 `GOLEM_ARTIFACT_ROOT` 下 contracts 的生成/复用边界
- [x] 新增 wrapper：`examples/run_golem_sst_smoke.sh`
- [x] wrapper 默认 dry-run，显式 `--execute` 才运行完整 SST
- [x] exporter 生成的 `golem_sst.env` 写入 `GOLEM_ARRAY_INPUT_SIZE`、`GOLEM_ARRAY_OUTPUT_SIZE`、`GOLEM_NUM_ARRAYS`
- [x] dry-run smoke 验证硬件脚本可消费 exporter artifacts
- [x] 新增 `scripts/check_golem_hardware_contracts.py`
- [x] 静态审计硬件侧 `GOLEM_ARTIFACT_ROOT`、`GOLEM_MATMUL_*`、contract JSON、HBM generator、runtime env reader 和 compile-time fallback macros
- [x] 确认当前阶段不要求直接运行 `run_noc_dma_pipeline.sh --execute`
- [ ] 可选后验验证：硬件侧 `Simulation is complete`
- [ ] 可选后验验证：硬件侧 `VERIFY-C = PASS`
- **状态：**完成

### 阶段 6：Golem task mapping/debug plan
- [x] 新增 `build_golem_event_plan(ir, golem_backend_config)`
- [x] 按 `pipeline_config.h` 实现 macro-task、m/n group、A/B reuse window、worker slot、worker core、group、data node 映射
- [x] 在 event plan 中加入 `a_base_mm`、`b_pack_base_mm`、`c_base_mm`、`task_slot_in_node`、`reuse_offset`
- [x] 输出 Golem runtime 语义事件：remote load、GM2IMAT、GM2IVEC batch、MVM batch、wait、OVEC2GM、remote store
- [x] 新增测试与 `pipeline_config.h` / `gen_hbm_init.py` 的公式对齐
- [x] 新增 `examples/plan_golem_events.py`
- [x] 明确该 plan 是 mapping/debug/calibration 辅助产物，不是 SST 必需输入
- **状态：**完成

### 阶段 7：No-SST-execute offline validation
- [x] 新增 `scripts/validate_golem_artifacts.py`
- [x] 离线检查 `golem_sst.env`、`matmul_op_desc_resolved.json`、`matmul_env_mapping_v1.json` 是否齐全
- [x] 校验 `GOLEM_MATMUL_*` env 与 resolved contract 一致
- [x] 校验 `GOLEM_ARRAY_INPUT_SIZE`、`GOLEM_ARRAY_OUTPUT_SIZE`、`GOLEM_NUM_ARRAYS` 与 block shape 一致
- [x] 校验 legacy `GOLEM_GEMM_*` alias 与 `GOLEM_MATMUL_*` 一致
- [x] 支持输出 JSON validation report
- [x] 新增 `tests/test_validate_golem_artifacts.py`
- [x] 新增 `scripts/check_golem_mapping_consistency.py`
- [x] 校验 resolved contract 与 Golem task mapping/debug plan 的 tile counts、task count、worker/data node 范围和 base address 引用一致
- [x] 新增 `tests/test_check_golem_mapping_consistency.py`
- **状态：**完成

### 阶段 8：codegen-driven hardware integration smoke
- [x] 使用 `examples/gemm_ir.py` 生成当前 smoke 规模的 `CIM-TileIR JSON`：`M=1024, N=1024, K=128`
- [x] 使用 `examples/export_golem_sst.py` 导出 `/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts`
- [x] 运行 `scripts/validate_golem_artifacts.py`
- [x] 运行 `examples/plan_golem_events.py`
- [x] 运行 `scripts/check_golem_mapping_consistency.py`
- [x] 使用 `examples/run_golem_sst_smoke.sh --execute` 将 codegen artifacts 注入真实 `run_noc_dma_pipeline.sh`
- [x] 验证硬件 log 中出现 `Simulation is complete`
- [x] 验证 `VERIFY_C=1` 后处理通过；当前 `[VERIFY-C] PASS` 写到终端 stdout，不写入 SST log，若失败则脚本会因 `set -e` 停止且不会生成完整 stats/run_summary
- [x] 记录本次 run 的 log path 和 stats-dir
- [x] 确认生成 `execution_summary.csv`、`dma_summary.csv`、`noc_summary.csv`、`memory_summary.csv`
- [x] 确认生成 `memory_queue_summary.csv`、`submit_ready_causal_summary.csv`
- **状态：**完成

### 阶段 9：single-run SST stats report
- [x] 新增 `scripts/build_golem_single_run_report.py`
- [x] 读取 `execution_summary.csv`、`dma_summary.csv`、`noc_summary.csv`、`memory_summary.csv`
- [x] 读取 `memory_queue_summary.csv`、`submit_ready_causal_summary.csv`
- [x] stats 文件缺失时输出 structured warnings，不阻塞 report 生成
- [x] 对比 Golem task mapping/debug plan 与 SST 观测结果
- [x] 输出 `mode=golem_single_run_stats_report` 的首版 JSON report
- [x] 输出 `model.status=not_calibrated`
- [x] 计算 `compute_active_pct`、`prefetch_wait_pct`、`writeback_wait_pct`、`control_other_pct`
- [x] 计算 `cycles_per_gemm_task`、`cycles_per_macro_task`、`system_vs_worker_utilization_gap_pct`
- [x] 使用真实成功 run 生成 `/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346/golem_single_run_report.json`
- [x] 明确该 JSON report 是当前性能报告 MVP：只解释单次真实 SST 运行，不做 sweep、预测模型或多 run 对比
- **状态：**完成首版

### 阶段 10：TileLang 到 Golem SST E2E 与 extractor 扩展
- [x] 新增 `examples/run_tilelang_golem_e2e.sh`
- [x] 一条命令串起 `TileLang source -> CIM-TileIR -> Golem SST artifacts -> validators -> mapping checker -> run_golem_sst_smoke.sh`
- [x] dry-run 默认只校验 artifacts 和硬件脚本参数注入，不运行完整 SST
- [x] `--execute` 时自动查找最新 stats run 和 SST log，并生成 `golem_single_run_report.json`
- [x] 默认 run root 放在 `/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_<timestamp>`
- [x] 默认 TileLang fixture 调整为 Golem SST smoke 规格：`M=1024, N=1024, K=128, BM=64, BN=64, BK=64`
- [x] extractor 支持 `T.match_buffer` 缺省 dtype 时按 `float32` 解析，兼容 TileLang `PrimFunc.script()` 输出
- [x] 使用真实 SST 完成 `TileLang -> CIM-TileIR -> Golem SST -> VERIFY-C -> stats -> report` E2E run
- [x] 记录成功 run：`/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_20260617_193443`
- [x] 减少 extractor 对 A/B/C 参数命名的依赖：支持从 `A(M,K), B(K,N), C(M,N)` shape 关系推断角色
- [x] 增加更多 dtype、默认 pipeline stages、不同变量命名的 fixture 覆盖
- [x] 对动态 shape 输出明确 unsupported reason
- [ ] 改进缺失 shared buffer、fragment buffer、`T.gemm`、静态 shape 的错误信息
- [ ] 保持对转置 GEMM、复杂 fusion 的明确拒绝
- [x] 新增 TileOPs-like GEMM fixture
- [x] 验证 extractor 对简化 TileOPs GEMM 形态的支持边界：普通非转置 GEMM 可提取并导出 Golem artifacts
- [x] 新增 `examples/make_tilelang_gemm_source.py`，支持从 CLI 参数生成静态 TileLang GEMM 源码
- [x] `examples/run_tilelang_golem_e2e.sh` 支持 `--generate-tilelang-source`、`--m/--n/--k`、`--bm/--bn/--bk`、`--dtype`、`--num-stages`、`--threads`
- [x] 生成源码默认落在 `$RUN_ROOT/generated_tilelang_gemm.py`，再进入 `TileLang source -> CIM-TileIR -> Golem SST exporter`
- [ ] 对真实 TileOPs 复杂模式输出明确 unsupported reason（当前暂缓，不作为近期必要步骤）
- [ ] 不修改 `/data4/jjgong/TileOPs`
- **状态：**E2E smoke 与参数化 TileLang GEMM 入口完成，真实 TileOPs 复杂模式暂缓

### 阶段 11：runtime ABI 与 ELF 长期闭环
- [ ] 定义 runtime ABI，例如 `tl_core_id`、`tl_dma_load`、`tl_dma_store`、`tl_cim_gemm`
- [ ] 设计 C++ SPMD kernel codegen
- [ ] 集成 RISC-V 编译、链接、加载工具链
- [ ] 打通 GEMM ELF 闭环
- **状态：**长期目标

## 关键问题

1. TileLang extractor 下一步应继续 out-of-tree AST MVP，还是开始接入 TileLang pass pipeline？
2. 真实 TileOPs 复杂模式何时恢复推进，以及优先覆盖普通 GEMM 还是 grouped GEMM？
3. exporter 首版 CLI 是否同时支持 TileLang 源码和 `CIM-TileIR JSON`，还是先只支持 JSON？
4. `BM/BK` 整数倍 micro-tiling 尚未在硬件侧完成时，codegen 是否应严格拒绝非硬件 tile shape？
5. 后续是否需要新增显式 `--contract-dir` / `--env-file` 参数，还是继续通过 `source golem_sst.env` 和 `GOLEM_ARTIFACT_ROOT` 注入？
6. Golem task mapping/debug plan 是否需要改名为 mapping report，避免被误认为 SST 必需输入？

## 已做决策

| 决策 | 原因 |
|------|------|
| 当前分支以 CIM-TileIR 为主线 | 分支已包含 `tilelang_cim`、examples 和 tests，近期工作应围绕已有原型推进 |
| SST C codegen 降为历史背景/长期旁支 | 当前用户明确要求以 CIM-TileIR 技术路线为准 |
| 当前不修改 `TileOPs` | TileOPs 先作为上层用例来源，避免把问题面扩大 |
| 所有前端必须先落到 `CIM-TileIR` | `CIM-TileIR` 是唯一前后端接口，避免 TileLang 与 Golem SST 直接耦合 |
| 下一阶段优先做 `CIM-TileIR-to-Golem SST backend exporter` | 用户最终产物是从统一 IR 填充 SST env/script，而不是先做硬件建模 |
| Golem path 先生成 env/contract，不直接生成 RoCC 指令 | 硬件 runtime 已有 header-only API/WCP descriptor，先对齐可消费接口风险更低 |
| 非硬件 tile shape 首版严格拒绝 | 硬件总结显示 micro-tiling 尚未完成，不能让 codegen 生成 runtime 不能正确执行的任务 |
| Architecture spec 降级为后端约束校验 | 当前主线是前端参数到 SST 脚本填充，硬件参数只需服务 exporter 的合法性检查 |
| SST smoke wrapper 默认 dry-run | 避免误触发长时间 SST 仿真，完整运行必须显式传 `--execute` |
| exporter env 必须写入 Golem 阵列配置 | 确保硬件脚本不会回落到默认 array size，与 exporter 约束保持一致 |
| 当前阶段不要求直接跑完整 SST | 用户要求改为检查硬件内容是否已经解耦出来，完整运行作为后续可选后验验证 |
| 删除 toy architecture 与 abstract event planner | 本地已接入真实 Golem SST 架构，继续维护 toy 路径会制造两套架构真相 |
| 保留 Golem task mapping/debug plan | 它对齐真实 Golem runtime 映射，可用于解释、调试和后续 stats 校准 |
| 当前不做 sweep | 当前优先证明 codegen artifacts 能驱动单次真实 SST，并建立 single-run stats report；多 run 参数扫描会提前放大运行成本和维护复杂度 |
| Golem smoke 默认 artifact root 使用 `/data4/jjgong/tmp/codegen_sstnoc` | HBM mmap backing files 约 GB 级，根分区 `/tmp` 空间不足时会在 memHierarchy `BackingMMAP` 阶段触发 `Bus error` |

## 当前验收命令

```bash
TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q
bash scripts/check_docs.sh
python examples/gemm_ir.py --output /data4/jjgong/tmp/codegen_sstnoc/gemm.cimtile.json
# 阶段 4 完成后的新增目标命令：
# python examples/export_golem_sst.py \
#   /data4/jjgong/tmp/codegen_sstnoc/gemm.cimtile.json \
#   --input-format cim-tileir-json \
#   --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts
# python examples/export_golem_sst.py \
#   tests/fixtures/tilelang_gemm_fixture.py \
#   --input-format tilelang-source \
#   --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts
# bash examples/run_tilelang_golem_e2e.sh \
#   --tilelang-source tests/fixtures/tilelang_gemm_fixture.py
# bash examples/run_tilelang_golem_e2e.sh \
#   --generate-tilelang-source \
#   --m 1024 --n 1024 --k 128 \
#   --bm 64 --bn 64 --bk 64 \
#   --dtype float32 \
#   --num-stages 2
# bash examples/run_golem_sst_smoke.sh \
#   --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
#   -- \
#   --log codegen_smoke.log
python scripts/check_golem_hardware_contracts.py \
  --hardware-tests-dir /data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests
python scripts/validate_golem_artifacts.py \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --output /data4/jjgong/tmp/codegen_sstnoc/golem_artifact_validation.json
python examples/plan_golem_events.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json
python scripts/check_golem_mapping_consistency.py \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --event-plan /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/golem_mapping_consistency.json
bash examples/run_golem_sst_smoke.sh \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --execute \
  -- \
  --log codegen_smoke.log
```

## 备注

- 涉及 TileLang 导入的测试需要设置 `TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache`，避免默认写 `/home/jiajun/.tilelang`。
- 每完成一个阶段后更新本文件。
- 规划文件应始终作为流程和决策的权威记录。
