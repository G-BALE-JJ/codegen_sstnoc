# 进度摘要

本文档只保留当前状态和最近进展。完整历史日志已归档到：

- `docs/archive/progress-2026-05-18-to-2026-06-23.md`

## 当前状态

- 当前主线：`All frontends -> CIM-TileIR -> Golem SST backend exporter -> SST smoke/report`。
- 当前分支：`feat/tir-extractor-path-b`。
- 已跑通 GEMM 路径：
  - TileLang source / generated TileLang source / TIR `PrimFunc`。
  - `CIM-TileIR` GEMM。
  - Golem SST `golem_sst.env` 与 matmul contracts。
  - Artifact validation、mapping consistency check、SST smoke、single-run report。
- 已新增 softmax 阶段一：
  - `build_softmax_ir()` 支持 row-wise softmax IR。
  - `build_matmul_softmax_graph_ir()` 支持 `matmul -> softmax` graph IR。
  - Softmax/graph 目前只在 `CIM-TileIR` 层表达和校验，不导出 Golem SST artifacts。
- Golem exporter 当前仍只接受 `kernel=gemm`，用于保护现有 GEMM E2E。

## 最近会话：2026-06-23

### Softmax 阶段一

- 新增 `build_softmax_ir()`。
- 新增 `build_matmul_softmax_graph_ir()`。
- 扩展 `validate_cim_tile_ir()`：
  - 保持原 GEMM 校验路径不变。
  - 新增 `kernel=softmax` 校验。
  - 新增 `kernel=graph` 校验，当前只接受 `matmul -> softmax`。
- 新增测试：
  - softmax IR 可校验、可 JSON 导出。
  - graph IR 可校验、可 JSON 导出。
  - Golem exporter 对 softmax/graph IR 明确拒绝。
  - 原 GEMM exporter 路径仍正常。

### 文档精简

- 将完整历史 `progress.md` 归档到 `docs/archive/progress-2026-05-18-to-2026-06-23.md`。
- 当前 `progress.md` 改为短状态摘要。
- `README.md` 改为项目入口，不再承载完整操作手册。
- `docs/README.md` 更新为文档职责索引。

## 当前边界

- `CIM-TileIR` 已可表达 GEMM、row-wise softmax、`matmul -> softmax` graph。
- TileLang extractor 当前仍只支持标准静态 GEMM 模板和 TIR `tl.tileop.gemm` MVP。
- Golem exporter 当前只支持 GEMM。
- Softmax 若要进入真实 SST execute，需要在 `RISC-V-CIM-Manycore-SST` 中新增 softmax runtime/contract 或 graph runtime。
- 当前不修改 `/data4/jjgong/TileOPs`。
- 当前不承诺 runtime ABI / RISC-V ELF 闭环。

## 当前验收命令

```bash
bash scripts/check_docs.sh
TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q
```

## 下一步

1. 设计 softmax/graph 到硬件侧的执行策略。
2. 推荐先做 `GEMM on Golem MVM + softmax on RISC-V software`。
3. 为 graph/softmax 增加独立 artifact contract，而不是复用 matmul contract。
4. 后续再评估是否需要 softmax 专用硬件 primitive。

## 当前会话：阶段 10A 开始

- 用户确认执行 `matmul -> softmax(cpu_fallback)` 的 Golem graph artifact export。
- 新增边界要求：softmax 前端语言参考 TileOps/TileLang 标准实现。
- 已确认 TileOps 标准接口为 `SoftmaxFwdOp(N=N, dtype=dtype, dim=dim)`。
- 已确认 TileOps single-tile TileLang kernel 形态为
  `T.reduce_max -> T.exp -> T.reduce_sum -> normalize`。
- 当前硬件侧 softmax 只做 tile-local CPU fallback，不对齐 TileOps multi-tile online softmax。
- 阶段 10A 只支持 TileOps softmax 的 single-N-tile 子集，硬性要求 `N == block_n`。

### 阶段 10A 实现

- TDD RED：
  - 新增 graph exporter 测试，要求生成 `graph_sequence_v1.json` 和
    `softmax_op_desc_resolved.json`。
  - 新增 Golem constraints 测试，要求接受 `N == block_n` 的 graph，拒绝 `N > block_n`。
  - 新增 artifact validator 测试，要求识别 graph artifacts。
  - 首次相关测试失败于缺少 `build_golem_softmax_op_desc_from_graph`，属于有效 RED。
- GREEN：
  - `golem_constraints.py` 支持 `kernel=graph` 的 `matmul -> softmax` Golem 约束。
  - `golem_exporter.py` 新增 `build_golem_softmax_op_desc_from_graph` 和
    `build_golem_graph_sequence`。
  - `export_golem_sst_artifacts()` 对 graph IR 额外导出：
    `graph_sequence_v1.json`、`softmax_op_desc_resolved.json`、`graph_env_mapping_v1.json`。
  - `scripts/validate_golem_artifacts.py` 支持 graph mode，检查 graph sequence、softmax contract
    和 graph env mapping。
  - 新增 `examples/matmul_softmax_ir.py`，默认生成 64x64x64 single-N-tile graph IR。
- 相关验证：
  - `TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests/test_golem_constraints.py tests/test_golem_exporter.py tests/test_validate_golem_artifacts.py -q`
    输出 `18 passed`。
  - `python examples/matmul_softmax_ir.py --output /data4/jjgong/tmp/codegen_sstnoc/matmul_softmax_stage10a.cimtile.json`
    通过。
  - `python examples/export_golem_sst.py ... --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_softmax_stage10a_artifacts`
    通过，生成 `graph_sequence_v1.json`、`softmax_op_desc_resolved.json` 和 `graph_env_mapping_v1.json`。
  - `python scripts/validate_golem_artifacts.py --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_softmax_stage10a_artifacts ...`
    通过，validation report 中 `ok=true`，`softmax_contract_schema=ok`。

## 当前会话：阶段 10B

- 目标：在 `codegen_sstnoc` 内新增 wrapper，读取 Stage 10A graph artifacts，并调用硬件侧
  `small/mvm_noc_softmax_cpu/run_noc_dma_softmax_pipeline.sh`。
- 约束：不修改硬件仓库；softmax 仍是 RISC-V CPU fallback；默认 dry-run，显式 `--execute`
  才运行真实 SST。
- TDD RED：
  - 新增 `tests/test_run_golem_softmax_sst_smoke.py`。
  - 首次定向测试失败于缺少 `examples/run_golem_softmax_sst_smoke.sh`，属于有效 RED。
- GREEN：
  - 新增 `examples/run_golem_softmax_sst_smoke.sh`。
  - wrapper 会检查 `golem_sst.env`、`matmul_op_desc_resolved.json`、`graph_sequence_v1.json`、
    `softmax_op_desc_resolved.json` 和 `graph_env_mapping_v1.json`。
  - wrapper 先运行 `scripts/validate_golem_artifacts.py`，再 source `golem_sst.env`。
  - 默认映射到当前已验证的 1 group / 1 core / 1 GEMM core / 2 memory nodes / 1x mesh softmax smoke。
  - 硬件侧调用始终附带 `--verify-softmax --softmax-reference probability`；非 `--execute` 时额外附带
    `--dry-run`。
- 定向验证：
  - `python -m pytest tests/test_run_golem_softmax_sst_smoke.py -q`
    输出 `3 passed`。

## 当前会话：阶段 10C

- 目标：把 softmax 做成和现有 GEMM 一样的端到端，并且必须经过 `CIM-TileIR`。
- 采用路径：
  `TileOps-like matmul->SoftmaxFwdOp source -> CIM-TileIR graph -> Golem graph artifacts -> Stage 10B softmax SST wrapper`。
- 范围约束：
  - 只支持 `SoftmaxFwdOp(N=block_n, dtype=DTYPE, dim=-1)`。
  - 只支持 `fp32/float32`、二维 row-major、single-N-tile，即 `N == block_n`。
  - 不做 standalone softmax SST、不做 multi-tile online softmax、不做多核 softmax 或硬件 softmax primitive。
- TDD RED：
  - 新增 `tests/test_tilelang_matmul_softmax_extractor.py`。
  - 新增 `tests/test_run_tilelang_softmax_golem_e2e.py`。
  - 首次失败于缺少 `extract_matmul_softmax_graph_ir_from_source`，属于有效 RED。
- GREEN：
  - `tilelang_cim/extractor.py` 新增 `extract_matmul_softmax_graph_ir_from_source()`。
  - `tilelang_cim/__init__.py` 导出该 API。
  - 新增 `examples/extract_tilelang_matmul_softmax.py`。
  - 新增 `examples/run_tilelang_softmax_golem_e2e.sh`。
  - 新增 TileOps-like fixture：
    `tests/fixtures/tileops_like_matmul_softmax_source.py` 和可 import 的源码字符串 fixture。
  - E2E wrapper 会生成：
    `tilelang_matmul_softmax.cimtile.json`、`golem_softmax_artifacts/`、
    `golem_softmax_artifact_validation.json`，再调用 Stage 10B softmax smoke wrapper。
- 定向验证：
  - `python -m pytest tests/test_tilelang_matmul_softmax_extractor.py tests/test_run_tilelang_softmax_golem_e2e.py -q`
    输出 `3 passed`。
