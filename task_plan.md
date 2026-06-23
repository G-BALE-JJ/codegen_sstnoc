# CIM-TileIR 项目计划

本文档只保留当前计划和阶段摘要。完整历史计划已归档到：

- `docs/archive/task-plan-history.md`

## 目标

当前主线：

```text
All frontends
  -> CIM-TileIR
  -> Golem SST backend exporter
  -> env/contracts
  -> RISC-V-CIM-Manycore-SST
```

`CIM-TileIR` 是唯一前后端接口。TileLang 是第一个前端，Golem SST 是第一个真实硬件后端。

## 当前状态

- GEMM E2E 已跑通：
  - TileLang source / generated TileLang source / TIR `PrimFunc`。
  - `CIM-TileIR GEMM -> Golem env/contracts -> SST smoke -> VERIFY-C -> stats/report`。
- Softmax 阶段一已完成：
  - `build_softmax_ir()` 支持 row-wise softmax IR。
  - `build_matmul_softmax_graph_ir()` 支持 `matmul -> softmax` graph IR。
  - Golem exporter 支持 `matmul -> softmax(cpu_fallback)` graph artifacts。
  - Stage 10B wrapper 可读取 graph artifacts 并调用硬件侧 softmax SST wrapper，默认 dry-run。
  - Stage 10C wrapper 可从 TileOps-like `matmul -> SoftmaxFwdOp` source 经 `CIM-TileIR graph`
    进入 Golem graph artifacts 和 softmax SST wrapper。
- 当前短期方向：
  - 用 Stage 10C E2E wrapper 跑真实 SST graph smoke，并保留 `--verify-softmax` checker。
  - 继续保持 `matmul on Golem MVM + softmax on RISC-V software path`，暂不做多核 softmax 或硬件 softmax primitive。
  - softmax 前端语义参考 TileOPs `SoftmaxFwdOp(N=N, dtype=dtype, dim=dim)`；
    当前 Golem 后端只支持其 single-N-tile 子集，要求 `N == block_n`。

## 阶段摘要

| 阶段 | 状态 | 结果 |
|---|---|---|
| 1. CIM-TileIR GEMM JSON 原型 | 完成 | `build_gemm_ir`、checker、JSON 导出、CLI 和测试 |
| 2. TileLang GEMM extractor | 完成 | Source/script/TIR GEMM MVP 提取 |
| 3. 移除 toy architecture / abstract planner 主线 | 完成 | 当前主线收敛到真实 Golem SST |
| 4. Golem SST backend exporter | 完成 | `golem_sst.env`、matmul resolved contract、env mapping |
| 5. 硬件侧 env/contract 解耦审计 | 完成 | 确认硬件脚本可消费外部 artifacts |
| 6. Golem mapping/debug plan | 完成 | macro-task、worker/data node、A/B/C 地址解释 |
| 7. Offline validation | 完成 | artifact validator 和 mapping consistency checker |
| 8. Codegen-driven hardware smoke | 完成 | 真实 SST `Simulation is complete`、`VERIFY-C PASS` |
| 9. Single-run stats report | 完成 | `golem_single_run_report.json` |
| 10. TileLang/TIR E2E 与 softmax IR 阶段一 | 进行中 | GEMM E2E 稳定，softmax/graph 仅 IR 层表达 |
| 10A. matmul -> softmax graph artifacts | 完成 | 导出 Golem graph sequence、matmul contract、softmax CPU fallback contract；只支持 single-N-tile softmax |
| 10B. codegen-driven softmax SST smoke wrapper | 完成 | 读取 graph artifacts，调用硬件 softmax wrapper；dry-run 默认，execute 启用 `--verify-softmax` |
| 10C. TileLang softmax E2E through CIM-TileIR | 完成 | TileOps-like `matmul -> SoftmaxFwdOp` source 经 CIM-TileIR graph 进入 Golem softmax SST wrapper |
| 11. runtime ABI / ELF | 长期 | 暂不承诺 |

## 近期计划

1. 保持 GEMM E2E 稳定。
2. 用 `examples/run_tilelang_softmax_golem_e2e.sh` 对 TileOps-like source 做 dry-run 和真实 SST smoke。
3. 真实 SST smoke 成功后，再补充 softmax graph 的运行报告入口。
4. 再评估 TileOps single-tile primitive 形式 `T.reduce_max -> T.exp -> T.reduce_sum -> normalize`
   的 extractor 入口。
5. 暂不做 multi-tile online softmax、多核 softmax 或 softmax 硬件 primitive。

## 阶段 10C 结果

1. 新增 `extract_matmul_softmax_graph_ir_from_source()`，识别窄模板 TileOps-like
   `matmul -> SoftmaxFwdOp(N=block_n, dtype=DTYPE, dim=-1)`。
2. 新增 `examples/extract_tilelang_matmul_softmax.py`，输出 `kernel=graph` 的
   `CIM-TileIR` JSON。
3. 新增 `examples/run_tilelang_softmax_golem_e2e.sh`，流程为：
   `TileOps-like source -> CIM-TileIR graph -> Golem graph artifacts -> validator -> run_golem_softmax_sst_smoke.sh`。
4. 第一版只支持 single-N-tile softmax，要求 `SoftmaxFwdOp.N == block_n`，不支持
   TileOps multi-tile online softmax。

## 阶段 10B 计划

1. 新增 codegen wrapper，读取 graph artifacts 并调用硬件侧
   `mvm_noc_softmax_cpu/run_noc_dma_softmax_pipeline.sh`。
2. dry-run 模式先对齐 1-core / 1-tile softmax smoke 命令。
3. execute 模式复用用户 shell 环境运行真实 SST，并启用 `--verify-softmax`。
4. 再评估 TileOps-like softmax source / TileLang single-tile softmax fixture 的 extractor 入口。

## 阶段 10A 约束

- 目标：导出 `matmul -> softmax(cpu_fallback)` 的 Golem graph artifacts。
- softmax 语义参考 TileOps `SoftmaxFwdOp(N=N, dtype=dtype, dim=dim)`。
- 当前仅支持二维 `fp32`、`row_major`、`dim=-1` / `axis=1`。
- 当前硬件 softmax 是 tile-local CPU fallback；因此 exporter 必须要求 `N == block_n`，
  使 tile-local softmax 与完整 row-wise softmax 等价。
- 暂不支持 TileOps multi-tile / online softmax 语义，即不支持 `N > block_n`。
- 暂不支持 `fp16`、`bf16`、`dim=0`、standalone softmax SST execute 或 softmax 硬件 primitive。

## 当前边界

- Golem exporter 支持 `kernel=gemm` 和 `kernel=graph` 的 `matmul -> softmax(cpu_fallback)` single-N-tile 子集。
- 独立 `kernel=softmax` 当前不导出 Golem artifacts。
- 不把 TileLang 直接转换为 `GOLEM_*`。
- 不修改 `/data4/jjgong/TileOPs`。
- 不在 micro-tiling 未完成前放宽 Golem tile shape。
- 不做 sweep、多 run 聚合或自动调参。
- 不承诺 OS loader、runtime ABI 或 RISC-V ELF 闭环。

## 验收命令

```bash
bash scripts/check_docs.sh
TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q
```

TIR frontend dry-run：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --frontend-mode tir \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py \
  --use-user-shell-env
```

完整 SST execute 需要硬件环境可用，并显式加 `--execute`。

## 备注

- 项目级临时产物默认放在 `/data4/jjgong/tmp/codegen_sstnoc`。
- TileLang cache 建议设置为 `/data4/jjgong/tmp/tilelang-cache`。
- 每次实现阶段结束后更新 `progress.md`；长历史放入 `docs/archive/`。
