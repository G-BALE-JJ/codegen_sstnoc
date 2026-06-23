# 发现与决策摘要

本文档只保留当前仍影响实现的发现、决策和资源路径。完整历史调研记录已归档到：

- `docs/archive/findings-history.md`

## 当前事实

- `/data4/jjgong/codegen_sstnoc` 是项目中枢和编译器侧原型仓库。
- `/data4/jjgong/tilelang`、`/data4/jjgong/TileOPs`、`/data4/jjgong/RISC-V-CIM-Manycore-SST` 是独立仓库。
- 当前主线是 `All frontends -> CIM-TileIR -> Golem SST backend exporter`。
- `CIM-TileIR` 是唯一前后端接口；前端不能直接生成 `GOLEM_*`。
- 当前真实硬件后端是 `RISC-V-CIM-Manycore-SST` 的 Golem runtime。
- 当前 Golem exporter 只支持 GEMM；softmax/graph 目前只在 `CIM-TileIR` 层表达。

## 关键决策

| 决策 | 原因 |
|---|---|
| 以 `CIM-TileIR` 为唯一前后端边界 | 避免 TileLang 与 Golem SST 直接耦合 |
| TileLang 只是第一个前端 | 后续可以接入 TileOPs 或其他 DSL |
| Golem SST 只是第一个后端 | 后续 backend 可以消费同一 IR |
| 当前不修改 `TileOPs` | 先稳定编译器 IR 和 Golem exporter |
| Golem exporter 当前只接受 GEMM | 保护已跑通的 GEMM E2E |
| softmax 阶段一只做 IR 表达 | 真实执行需要硬件侧 runtime/contract |
| softmax 下一阶段先走 RISC-V software path | 风险低，不需要立即新增硬件 primitive |
| 不直接生成 RISC-V ELF | 当前最短闭环是复用 Golem runtime 和脚本 |
| 不在 micro-tiling 未完成前放宽 tile shape | 避免生成硬件 runtime 不能可靠执行的配置 |
| 长日志归档到 `docs/archive/` | 保持日常入口文档简短可读 |

## 待确认事项

1. `matmul -> softmax` graph contract 的文件结构：
   - `graph_sequence_v1.json + softmax_op_desc_resolved.json`
   - 或 `graph_op_desc_resolved.json + ops/*.json`
2. softmax CPU runtime 的数据布局：
   - 直接消费 matmul logits 输出。
   - 是否需要中间 buffer 或 in-place 支持。
3. softmax 校验方式：
   - 绝对/相对误差阈值。
   - 抽样验证还是全量验证。
4. 是否需要把 `golem_event_plan` 改名为 mapping report，避免被误认为 SST 必需输入。
5. 何时恢复真实 TileOPs 复杂模式支持。

## 当前资源

- `tilelang_cim/builder.py`：GEMM、softmax、graph IR 构造。
- `tilelang_cim/checker.py`：IR 校验。
- `tilelang_cim/extractor.py`：TileLang source/TIR GEMM 提取。
- `tilelang_cim/golem_exporter.py`：GEMM Golem artifacts 导出。
- `tilelang_cim/golem_constraints.py`：Golem 后端约束。
- `tilelang_cim/golem_event_planner.py`：Golem mapping/debug plan。
- `examples/run_tilelang_golem_e2e.sh`：TileLang/TIR 到 Golem SST E2E 入口。
- `scripts/validate_golem_artifacts.py`：artifact 自洽检查。
- `scripts/check_golem_mapping_consistency.py`：contract 与 mapping/debug plan 一致性检查。
- `docs/cim-tileir-prototype-summary.md`：当前原型能力说明。
- `docs/golem-runtime-codegen-roadmap.md`：当前 Golem 后端路线图。
- `docs/reference/golem-sst-hardware-summary.md`：硬件参考总结。
- `/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests/small/mvm_noc_softmax_cpu/design.md`：softmax CPU path 相关设计草案。

## 当前验证命令

```bash
bash scripts/check_docs.sh
TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q
```
