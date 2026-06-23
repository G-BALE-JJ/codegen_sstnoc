# 文档索引

本文档只维护 `docs/` 下的文档职责。项目入口见仓库根目录 `README.md`，当前计划见 `task_plan.md`，当前进展见 `progress.md`。

## 当前主线文档

- `cim-tileir-prototype-summary.md`：当前 CIM-TileIR 原型能力、边界和可运行链路。
- `golem-runtime-codegen-roadmap.md`：`CIM-TileIR -> Golem SST backend exporter` 路线、contract 设计和后续方向。

## 参考资料

- `reference/golem-sst-hardware-summary.md`：本地 `RISC-V-CIM-Manycore-SST` 硬件/运行时项目参考总结。

## 决策记录

- `adr/`：架构决策记录。长期有效、会影响后续维护的边界变化应补 ADR。

## 历史与归档

- `legacy/`：历史路线归档，例如 SST C codegen 和早期 TileLang-RISC-V-CIM 规划。不作为当前实现依据。
- `archive/`：长日志和历史完成记录归档。日常恢复优先看根目录 `progress.md`。
  - `progress-2026-05-18-to-2026-06-23.md`：完整旧进度日志。
  - `golem-runtime-codegen-history.md`：旧版 Golem 路线长文档。
  - `task-plan-history.md`：旧版阶段计划。
  - `findings-history.md`：旧版调研发现与决策。

## 维护原则

- `README.md` 只做项目入口，不放长命令手册。
- `task_plan.md` 只做计划和当前阶段状态。
- `progress.md` 只做当前进展摘要，长流水账放入 `docs/archive/`。
- `findings.md` 只保留当前仍影响实现的发现、决策和资源路径。
- 稳定设计放在 `docs/`，历史方案放在 `docs/legacy/`。
