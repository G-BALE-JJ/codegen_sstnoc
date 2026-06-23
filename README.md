# codegen_sstnoc

`codegen_sstnoc` 是 CIM-TileIR codegen 项目的协调中枢和编译器侧原型目录。当前主线是：

```text
All frontends
  -> CIM-TileIR
  -> Golem SST backend exporter
  -> env/contracts
  -> RISC-V-CIM-Manycore-SST
  -> smoke/stats/report
```

TileLang 是第一个前端，Golem SST 是第一个真实硬件后端。`CIM-TileIR` 是前端和硬件后端之间的唯一接口契约。

## 当前状态

- 已支持静态 GEMM 的 `CIM-TileIR` 构造、校验和 JSON 导出。
- 已支持从窄模板 TileLang GEMM source 以及 TileLang 生成的 TIR `PrimFunc` 提取 GEMM `CIM-TileIR`。
- 已支持 `CIM-TileIR GEMM -> Golem SST env/contracts` 导出。
- 已跑通 GEMM 的真实 SST smoke、`VERIFY-C` 和 single-run stats report。
- 已新增 softmax 阶段一：`CIM-TileIR` 可表达 row-wise softmax 和 `matmul -> softmax` graph IR。
- Golem exporter 当前仍只接受 `kernel=gemm`，softmax/graph IR 不会进入现有 GEMM E2E。

## 快速验证

```bash
bash scripts/check_docs.sh
TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q
```

## 常用入口

从 TileLang source 走默认 GEMM E2E dry-run：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py
```

从 TileLang 生成的 TIR `PrimFunc` 走 Path B dry-run：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --frontend-mode tir \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py \
  --use-user-shell-env
```

确认当前 shell 具备硬件运行环境后，显式加 `--execute` 才运行完整 SST：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --frontend-mode tir \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py \
  --use-user-shell-env \
  --execute
```

生成一个静态 GEMM 的 `CIM-TileIR JSON`：

```bash
python examples/gemm_ir.py --output gemm.cimtile.json
```

导出 Golem SST artifacts：

```bash
python examples/export_golem_sst.py \
  gemm.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts
```

## 目录说明

- `tilelang_cim/`：CIM-TileIR 原型包，包含 builder、checker、extractor、Golem exporter 和 mapping/debug plan。
- `examples/`：可运行入口，包括 GEMM IR 生成、TileLang 提取、TIR 提取、Golem artifact 导出和 E2E wrapper。
- `scripts/`：文档检查、硬件 contract 审计、artifact validation、mapping consistency 和 single-run report 工具。
- `tests/`：pytest 回归测试。
- `docs/`：设计说明、路线图、硬件参考、ADR、legacy 和 archive。
- `task_plan.md`：当前计划、阶段状态和待解决问题。
- `findings.md`：调研结论、关键决策和资源路径。
- `progress.md`：当前进展摘要；完整历史在 `docs/archive/`。
- `WORKFLOW.md`：协作工作流和仓库边界。

## 当前边界

- `CIM-TileIR` 已可表达 GEMM、row-wise softmax、`matmul -> softmax` graph。
- TileLang extractor 当前仍是 GEMM MVP，不支持任意动态 shape、复杂 fusion、转置 GEMM 或完整 TileLang pass pipeline。
- Golem exporter 当前只支持 GEMM，并生成：
  - `golem_sst.env`
  - `contracts/matmul_op_desc_resolved.json`
  - `contracts/matmul_env_mapping_v1.json`
- Softmax 若要进入真实 SST execute，需要在 `RISC-V-CIM-Manycore-SST` 中新增 softmax runtime/contract 或 graph runtime。
- toy `CIMArchitectureSpec`、`serial_formula_v0` 和 abstract event planner 已从当前主线移除。
- 当前不承诺 OS loader、runtime ABI 或 RISC-V ELF 工具链闭环。
- 当前不修改 `/data4/jjgong/TileOPs`；它只作为上层用例来源和后续联调参考。

## 文档入口

- `task_plan.md`：当前计划和阶段状态。
- `progress.md`：当前进展摘要。
- `WORKFLOW.md`：协作规则和仓库边界。
- `docs/cim-tileir-prototype-summary.md`：CIM-TileIR 原型能力和边界。
- `docs/golem-runtime-codegen-roadmap.md`：Golem SST backend exporter 路线。
- `docs/reference/golem-sst-hardware-summary.md`：硬件侧参考总结。
- `docs/legacy/`：历史路线归档，不作为当前实现依据。
- `docs/archive/`：长日志和历史完成记录归档。

## 临时目录

项目级临时产物默认放在：

```text
/data4/jjgong/tmp/codegen_sstnoc
```

TileLang cache 建议放在：

```text
/data4/jjgong/tmp/tilelang-cache
```

这样可以避免 GB 级 HBM mmap backing files 或 TileLang cache 写入空间较小的根分区 `/tmp` / 用户 home。
