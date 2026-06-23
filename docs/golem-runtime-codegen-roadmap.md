# CIM-TileIR 到 Golem SST 后端路线图

本文档只记录当前路线和下一步。历史完成细节已归档到：

- `docs/archive/golem-runtime-codegen-history.md`

## 当前目标

当前主线不是独立硬件建模器，也不是直接生成 RISC-V ELF，而是保持以下边界：

```text
All frontends
  -> CIM-TileIR
  -> Golem SST backend exporter
  -> env/contracts
  -> RISC-V-CIM-Manycore-SST runtime
```

`CIM-TileIR` 是唯一前后端接口。前端只负责提取计算语义，后端只负责把统一 IR 落到具体硬件加载环境。

## 当前已稳定链路

已稳定并验证的 GEMM 路径：

```text
TileLang source / generated TileLang source / TIR PrimFunc / hand-written JSON
  -> CIM-TileIR GEMM
  -> Golem backend legality checks
  -> golem_sst.env
  -> contracts/matmul_op_desc_resolved.json
  -> contracts/matmul_env_mapping_v1.json
  -> artifact validator
  -> mapping consistency checker
  -> RISC-V-CIM-Manycore-SST smoke
  -> VERIFY-C / stats / single-run report
```

当前 exporter 只支持 `kernel=gemm`。这是有意边界，用于保护现有 GEMM E2E。

## 前后端边界

`CIM-TileIR` 应表达：

- kernel / graph op 类型。
- tensor shape、dtype、layout。
- GEMM tile shape：`BM/BN/BK`。
- transpose flags。
- pipeline stages。
- 必要的 mapping/dataflow hint。

`CIM-TileIR` 不应表达：

- `GOLEM_MATMUL_*`。
- `GOLEM_GEMM_*`。
- `GOLEM_ARRAY_INPUT_SIZE` / `GOLEM_ARRAY_OUTPUT_SIZE` / `GOLEM_NUM_ARRAYS`。
- `run_noc_dma_pipeline.sh`。
- artifact root、HBM 文件路径或 SST log 路径。

这些属于 Golem SST backend exporter 和硬件运行环境。

## 当前 Golem Contract

Golem exporter 当前输出：

```text
<artifact-root>/
  golem_sst.env
  contracts/
    matmul_op_desc_resolved.json
    matmul_env_mapping_v1.json
```

`matmul_op_desc_resolved.json` 的核心字段：

```json
{
  "m": 1024,
  "n": 1024,
  "k": 128,
  "block_m": 64,
  "block_n": 64,
  "block_k": 64,
  "dtype": "fp32",
  "layout": "row_major",
  "transpose_a": 0,
  "transpose_b": 0
}
```

`golem_sst.env` 会导出：

- Golem array 参数：`GOLEM_ARRAY_INPUT_SIZE`、`GOLEM_ARRAY_OUTPUT_SIZE`、`GOLEM_NUM_ARRAYS`。
- Matmul 参数：`GOLEM_MATMUL_M/N/K`、`GOLEM_MATMUL_BLOCK_M/N/K`、dtype、layout、transpose。
- Legacy alias：`GOLEM_GEMM_*` 指向 `GOLEM_MATMUL_*`，兼容硬件脚本现有路径。

## 后端约束

当前 Golem backend 对 GEMM 做严格约束：

| 规则 | 原因 |
|---|---|
| dtype 只能是 `int32/fp32` | 当前 Golem runtime 只支持这两类路径 |
| layout 必须是 `row_major` | HBM generator 和 runtime phase-1 假设 row-major |
| `transpose_a=false` 且 `transpose_b=false` | 当前 matmul contract 不支持转置 |
| `M/N/K` 必须能被 `BM/BN/BK` 整除 | 当前 HBM layout 和 runtime 假设整 tile |
| `BK == GOLEM_ARRAY_INPUT_SIZE` | 直接映射到 MVM input size |
| `BM == GOLEM_ARRAY_OUTPUT_SIZE` | 直接映射到 MVM output size |
| `BN <= GOLEM_NUM_ARRAYS` | N 列映射到 array id |

在硬件侧 micro-tiling 未完成前，exporter 不应放宽 `BM/BK` 为硬件 tile 的整数倍。

## Softmax / Graph 当前阶段

当前 `CIM-TileIR` 已可表达：

- `kernel=softmax` 的 row-wise softmax。
- `kernel=graph` 的 `matmul -> softmax` 两节点 graph。

当前已支持：

- `kernel=graph` 的 `matmul -> softmax(cpu_fallback)` Golem artifacts。
- `graph_sequence_v1.json`、`softmax_op_desc_resolved.json` 和 `graph_env_mapping_v1.json`。
- TileOps `SoftmaxFwdOp(N=N, dtype=dtype, dim=-1)` 的 single-N-tile 子集：
  `fp32`、二维 row-major、`N == block_n`。
- `examples/run_golem_softmax_sst_smoke.sh` 读取 graph artifacts 并调用硬件侧
  `small/mvm_noc_softmax_cpu/run_noc_dma_softmax_pipeline.sh`。默认 dry-run，`--execute`
  时启用真实 SST 与 `--verify-softmax`。
- `examples/run_tilelang_softmax_golem_e2e.sh` 提供和 GEMM E2E 对齐的 softmax graph 入口：
  TileOps-like `matmul -> SoftmaxFwdOp` source 先提取为 `CIM-TileIR graph`，再导出 artifacts 并进入
  softmax SST wrapper。

当前尚未支持：

- 独立 `kernel=softmax` 导出 Golem artifacts。
- softmax graph 的 single-run stats report 聚合入口。
- TileOps single-tile primitive 形式 `T.reduce_max -> T.exp -> T.reduce_sum -> normalize` 的 extractor。
- TileOps multi-tile online softmax，即 `N > block_n` 的完整 row-wise softmax。

推荐下一步采用低风险执行策略：

```text
matmul on Golem MVM array
  -> write logits
  -> softmax on RISC-V software path
  -> write probability output
```

当前已采用更小版本 contract：

```text
contracts/
  matmul_op_desc_resolved.json
  softmax_op_desc_resolved.json
  graph_sequence_v1.json
  graph_env_mapping_v1.json
```

## 当前不做

- 不直接生成 RISC-V ELF。
- 不把 TileLang 直接写成 `GOLEM_*`。
- 不把 `N > block_n` 的 TileOps multi-tile softmax 误导出为当前 tile-local fallback。
- 不做 sweep、多 run 聚合或自动调参。
- 不在 micro-tiling 未完成前放宽 Golem tile shape。
- 不修改 `TileOPs`。

## 验收命令

日常回归：

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

完整 SST execute 需在硬件环境可用的 shell 中显式加 `--execute`：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --frontend-mode tir \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py \
  --use-user-shell-env \
  --execute
```
