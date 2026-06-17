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

当前 CIM 原型阶段的完整整理见 `docs/cim-tileir-prototype-summary.md`。Golem SST 硬件对齐后的下一步路线见 `docs/golem-runtime-codegen-roadmap.md`。新路线的重点是所有前端先落到 `CIM-TileIR`，再由 Golem SST backend exporter 生成 runtime contract：`golem_sst.env`、resolved matmul contract、env mapping 和 SST smoke 验证。Golem 硬件参数首版作为 backend exporter 的约束校验，不作为第一阶段主产物。

导出 Golem SST artifacts：

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
```

将 artifacts 注入硬件侧 SST 脚本做 dry-run smoke：

```bash
bash examples/run_golem_sst_smoke.sh \
  --artifact-root /tmp/golem_codegen_artifacts \
  -- \
  --log codegen_smoke.log
```

wrapper 默认追加 `--dry-run`。确认配置无误后，显式加 `--execute` 才会运行完整 SST 仿真。

当前阶段不要求直接运行完整 SST。检查硬件侧是否已经把参数入口解耦出来：

```bash
python scripts/check_golem_hardware_contracts.py \
  --hardware-tests-dir /data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests
```

该检查会确认硬件侧存在 `GOLEM_ARTIFACT_ROOT`、`GOLEM_MATMUL_*`、`matmul_env_mapping_v1.json`、`matmul_op_desc_resolved.json`、HBM generator contract 写出、runtime env 读取和 compile-time fallback macros。完整 SST 运行只作为后续可选后验验证。

生成 Golem task mapping/debug plan：

```bash
python examples/plan_golem_events.py \
  /tmp/gemm.golem.cimtile.json \
  --output /tmp/gemm.golem_event_plan.json
```

该 plan 对齐 Golem runtime 的 macro-task / worker core / data node / A/B packed-once / C slot 映射，用于解释和调试硬件侧行为；当前不作为 SST 必需输入，也不输出 cycle estimate。

## 推荐流程

1. 开始新阶段前先更新 `task_plan.md`。
2. 把发现和结论记录到 `findings.md`。
3. 把本次会话进度写入 `progress.md`。
4. 在 `tilelang_cim/` 中修改当前 CIM 原型。
5. 把验证结果同步回这个目录。
