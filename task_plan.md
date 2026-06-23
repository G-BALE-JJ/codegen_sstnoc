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
  - Golem exporter 仍只接受 GEMM，softmax/graph 不进入当前硬件 E2E。
- 当前短期方向：
  - 设计 softmax/graph 到硬件侧的 execution contract。
  - 推荐先做 `matmul on Golem MVM + softmax on RISC-V software path`。

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
| 11. runtime ABI / ELF | 长期 | 暂不承诺 |

## 近期计划

1. 保持 GEMM E2E 稳定。
2. 为 softmax/graph 设计硬件侧最小 contract：
   - graph sequence。
   - matmul op desc。
   - softmax op desc。
   - input/output memory layout。
3. 在 `RISC-V-CIM-Manycore-SST` 中先实现 CPU software softmax runtime path。
4. 扩展 `codegen_sstnoc` exporter，让 `matmul -> softmax` graph 可导出新 contract。
5. 增加 graph artifact validator 和 fake/dry-run 测试。
6. 完成真实 SST graph smoke 后，再考虑是否需要 softmax 硬件 primitive。

## 当前边界

- Golem exporter 只支持 `kernel=gemm`。
- Softmax/graph IR 当前不导出 Golem artifacts。
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
