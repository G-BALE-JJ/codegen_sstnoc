# 文档目录

这里存放项目级说明、设计记录、硬件参考和历史路线归档。

## 建议内容

- 架构决策记录。
- 当前 Golem SST backend exporter 路线。
- CIM-TileIR 原型能力汇总。
- 硬件参考资料。
- 已废弃或降级的历史路线。

## 当前重点

- 当前主线是 `All frontends -> CIM-TileIR -> Golem SST backend exporter`。
- TileLang 是第一个前端，Golem SST 是第一个真实硬件后端。
- toy architecture、abstract event planner 和 SST C codegen 路线已从当前主线移除或降级为 legacy。

## 当前文档

- `golem-runtime-codegen-roadmap.md`：当前 Golem SST backend exporter 路线。
- `cim-tileir-prototype-summary.md`：当前 CIM-TileIR 原型能力、边界和可运行链路。
- `reference/golem-sst-hardware-summary.md`：本地 Golem SST 硬件/运行时项目参考总结。
- `legacy/`：历史路线归档，不作为当前实现依据。
- `adr/`：架构决策记录。
