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
