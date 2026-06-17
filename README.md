# codegen_sstnoc

这是 CIM-TileIR codegen 项目的协调中枢与原型目录。

## 作用

- 跟踪项目目标、范围和里程碑。
- 记录技术决策和调研结论。
- 将开发进度与源码修改分开管理。
- 为 agent 驱动的开发提供稳定的工作空间。

## 当前范围

- 当前分支以 RISC-V CIM 2D-mesh 的 `CIM-TileIR` 技术路线为主线。
- 近期目标是完成 `All frontends -> CIM-TileIR -> Golem SST env/contract` 的后端导出闭环。
- 当前已经支持静态 GEMM 的 `CIM-TileIR JSON` 构造、窄模板 TileLang GEMM 提取，以及 `CIM-TileIR -> Golem SST env/contract` 导出。
- toy `CIMArchitectureSpec`、`serial_formula_v0` 和 abstract event planner 已从当前主线移除；真实硬件对接以本地 `RISC-V-CIM-Manycore-SST` 的 Golem runtime contract 为准。
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
- `examples/export_golem_sst.py`：从 `CIM-TileIR JSON` 或 TileLang 源码导出 Golem SST env/contract artifacts。
- `examples/plan_golem_events.py`：从 `CIM-TileIR JSON` 生成 Golem task mapping/debug plan。
- `examples/run_golem_sst_smoke.sh`：将 exporter 生成的 artifacts 注入硬件侧 `run_noc_dma_pipeline.sh`，默认 dry-run。
- `examples/run_tilelang_golem_e2e.sh`：一条命令串起 TileLang 源码、`CIM-TileIR`、Golem artifacts、离线校验、SST smoke 和可选 single-run report。
- `scripts/check_golem_hardware_contracts.py`：静态审计硬件侧是否已经提供 env/contract 解耦入口。
- `tests/`：CIM-TileIR 原型的 pytest 测试。
- `docs/golem-runtime-codegen-roadmap.md`：对接 `RISC-V-CIM-Manycore-SST` Golem runtime 的当前路线。
- `docs/cim-tileir-prototype-summary.md`：当前 CIM-TileIR 原型能力汇总。
- `docs/reference/golem-sst-hardware-summary.md`：硬件侧参考总结。
- `docs/legacy/`：历史路线归档，不作为当前实现依据。

## 工作原则

- 当前 CIM-TileIR 原型代码维护在本目录的 `tilelang_cim/` 中。
- `tilelang/` 暂作为 TileLang 前端和后续 pass 集成参考，不作为当前阶段的直接改动位置。
- `TileOPs/` 在当前阶段只作为上层使用案例和需求来源，不作为实现改动位置。

## 当前约定

- `CIM-TileIR` 是所有前端语言与后续 runtime / hardware backend 之间的唯一接口契约。
- 项目级临时产物默认放在 `/data4/jjgong/tmp/codegen_sstnoc`，避免把 HBM mmap backing files 写入根分区 `/tmp`。
- 当前 target 字段仍写作 `riscv_cim_mesh`，但不会在 TileLang/TVM 中注册真正的新 target kind。
- Golem 后端约束由 `golem_constraints.py` 承担，输出由 `golem_exporter.py` 承担。
- `golem_event_planner.py` 只作为 Golem runtime 映射解释、调试和后续 stats 校准辅助，不作为 SST 必需输入。
- `docs/legacy/tilelang_riscv_cim_backend_plan.md` 仅作历史路线参考；runtime ABI 和 ELF mode 是后续长期目标。

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
TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q
```

从 TileLang GEMM 源码文件提取 `CIM-TileIR JSON`：

```bash
python examples/extract_tilelang_gemm.py \
  tests/fixtures/tilelang_gemm_fixture.py \
  --output tilelang_gemm.cimtile.json \
  --mesh-w 8 --mesh-h 8
```

当前 extractor 是第一版 MVP，只支持标准静态 GEMM 模板。它可以识别源码里的 `T.Tensor`、`T.alloc_shared`、`T.alloc_fragment`、`T.Pipelined`、`T.gemm`，也可以从 TileLang `PrimFunc.script()` 的 `T.match_buffer`、`T.alloc_buffer`、`T.serial`、`T.gemm` 形态中提取同类信息；暂不支持任意动态 shape、复杂 fusion、转置 GEMM、复杂调度或完整 TileLang pass pipeline。

当前 CIM 原型阶段的完整整理见 `docs/cim-tileir-prototype-summary.md`。Golem SST 硬件对齐后的下一步路线见 `docs/golem-runtime-codegen-roadmap.md`。新路线的重点是所有前端先落到 `CIM-TileIR`，再由 Golem SST backend exporter 生成 runtime contract：`golem_sst.env`、resolved matmul contract、env mapping 和 SST smoke 验证。Golem 硬件参数首版作为 backend exporter 的约束校验，不作为第一阶段主产物。

推荐的 TileLang 到 Golem SST 端到端入口：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py
```

默认是 dry-run：它会生成 `CIM-TileIR JSON`、`golem_sst.env`、contracts、Golem mapping/debug plan，并运行 artifact validator、mapping consistency checker 和硬件 wrapper dry-run。默认 `run_root` 位于 `/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_<timestamp>`。

确认当前 shell 已具备硬件脚本所需环境后，显式加 `--execute` 才运行真实 SST：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py \
  --execute
```

如果从 Codex、CI 或其他非交互 shell 启动，当前进程没有加载用户 `~/.bashrc`，可加：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py \
  --use-user-shell-env \
  --execute
```

`--execute` 成功后，脚本会自动从 artifact root 下找到最新 `execution_summary.csv` 和最新 SST log，生成 `$RUN_ROOT/golem_single_run_report.json`。这个入口仍然不把 TileLang 直接耦合到 `GOLEM_*`：流程内部先落到 `CIM-TileIR`，再由 Golem backend exporter 生成 SST 运行环境。

当前已有一次真实端到端成功记录：

```text
run_root=/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_20260617_193443
single_run_report=/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_20260617_193443/golem_single_run_report.json
Simulation is complete, simulated time: 234.589 us
[VERIFY-C] PASS dtype=fp32 sampled=1024 mismatches=0
```

`golem_single_run_report.json` 是当前性能报告 MVP。它不是 sweep 或调参报告，而是单次真实 SST 运行的结构化性能解释：包含 mapping、stats CSV 观测值、仿真完成状态、array utilization、system utilization、cycles per task、compute/prefetch/writeback/control 占比和 warning。后续可以在此基础上生成 Markdown/HTML 可读报告。

导出 Golem SST artifacts：

```bash
python examples/gemm_ir.py \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --m 1024 --n 1024 --k 128 \
  --bm 64 --bn 64 --bk 64 \
  --mesh-w 4 --mesh-h 5 \
  --pipeline-stages 1 \
  --a-dtype fp32 --b-dtype fp32 --c-dtype fp32

python examples/export_golem_sst.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts
```

将 artifacts 注入硬件侧 SST 脚本做 dry-run smoke：

```bash
bash examples/run_golem_sst_smoke.sh \
  -- \
  --log codegen_smoke.log
```

wrapper 默认 artifact root 是 `/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts`，并默认追加 `--dry-run`。确认配置无误后，显式加 `--execute` 才会运行完整 SST 仿真。

检查硬件侧是否已经把参数入口解耦出来：

```bash
python scripts/check_golem_hardware_contracts.py \
  --hardware-tests-dir /data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests
```

该检查会确认硬件侧存在 `GOLEM_ARTIFACT_ROOT`、`GOLEM_MATMUL_*`、`matmul_env_mapping_v1.json`、`matmul_op_desc_resolved.json`、HBM generator contract 写出、runtime env 读取和 compile-time fallback macros。

离线检查 exporter 生成的具体 artifacts 是否自洽：

```bash
python scripts/validate_golem_artifacts.py \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --output /data4/jjgong/tmp/codegen_sstnoc/golem_artifact_validation.json
```

该检查不运行 SST，会确认 `golem_sst.env`、resolved contract 和 env mapping contract 齐全，并校验 env、contract、Golem array shape 与 legacy alias 是否一致。

生成 Golem task mapping/debug plan：

```bash
python examples/plan_golem_events.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json
```

该 plan 对齐 Golem runtime 的 macro-task / worker core / data node / A/B packed-once / C slot 映射，用于解释和调试硬件侧行为；当前不作为 SST 必需输入，也不输出 cycle estimate。

离线检查 exporter contract 和 Golem task mapping/debug plan 是否一致：

```bash
python scripts/check_golem_mapping_consistency.py \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --event-plan /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/golem_mapping_consistency.json
```

该检查不运行 SST，会确认 resolved contract 中的 M/N/K/block shape 与 event plan 的 tile counts、task count、worker/data node 范围、A/B/C base address 和事件地址引用一致。

当前硬件默认脚本已经可以运行后，下一阶段需要执行 codegen-driven hardware integration smoke，证明 codegen artifacts 可以真实驱动 SST：

```bash
bash examples/run_golem_sst_smoke.sh \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --execute \
  -- \
  --log codegen_smoke.log
```

`examples/run_golem_sst_smoke.sh` 只注入 codegen 生成的 `GOLEM_*` env、contracts 和 `GOLEM_ARTIFACT_ROOT`。`sst`、`riscv64-linux-musl-g++`、`LD_LIBRARY_PATH`、DRAMSim3 等运行环境仍来自硬件脚本和当前用户 shell；wrapper 不复制也不硬编码这些路径。若从 Codex、CI 或其他非交互 shell 启动，当前进程可能没有加载用户 `~/.bashrc`，可显式加：

```bash
bash examples/run_golem_sst_smoke.sh \
  --use-user-shell-env \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --execute \
  -- \
  --log codegen_smoke.log
```

验收标准：

- 硬件 log 中出现 `Simulation is complete`。
- `VERIFY_C=1` 后处理通过。当前 `[VERIFY-C] PASS` 输出到终端 stdout，不写入 SST log；若 verify 失败，硬件脚本会中止。
- 本次 run 生成 `execution_summary.csv`、`dma_summary.csv`、`noc_summary.csv`、`memory_summary.csv`。

通过该 smoke 后，生成 single-run SST stats report：

```bash
RUN_ROOT=/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346

python scripts/build_golem_single_run_report.py \
  --artifact-root "$RUN_ROOT/golem_codegen_artifacts" \
  --event-plan "$RUN_ROOT/gemm.golem_event_plan.json" \
  --stats-dir "$RUN_ROOT/golem_codegen_artifacts/stats/overlap0/run_20260617_174010_1201356" \
  --log "$RUN_ROOT/golem_codegen_artifacts/logs/full_smoke_execute_terminal_run_20260617_174010_1201356.log" \
  --output "$RUN_ROOT/golem_single_run_report.json"
```

该 report 输出 `mode=golem_single_run_stats_report` 和 `model.status=not_calibrated`，只解释单次真实运行。当前不做 sweep、自动调参、多 run 聚合或性能预测模型。

## 推荐流程

1. 开始新阶段前先更新 `task_plan.md`。
2. 把发现和结论记录到 `findings.md`。
3. 把本次会话进度写入 `progress.md`。
4. 在 `tilelang_cim/` 中修改当前 CIM 原型。
5. 把验证结果同步回这个目录。
