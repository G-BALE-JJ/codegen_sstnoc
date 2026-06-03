# codegen_sstnoc

这是 SST codegen 项目的协调中枢目录。

## 作用

- 跟踪项目目标、范围和里程碑。
- 记录技术决策和调研结论。
- 将开发进度与源码修改分开管理。
- 为 agent 驱动的开发提供稳定的工作空间。

## 当前范围

- 当前目标是完成 `tilelang` 面向 SST 后端的首版 codegen。
- 首版只要求识别 SST 目标后输出 C 代码。
- 生成的 C 代码中需要能够表达 RISC-V 自定义指令。
- 当前阶段不要求生成结果立即可执行。
- 当前阶段不修改 `TileOPs`，但允许把它作为算子和使用方式的参考来源。
- 新增的 RISC-V CIM 2D-mesh 方案属于后续路线图，近期目标收敛为 `TileLang GEMM -> CIM-TileIR JSON` 的编译器侧原型。
- 当前项目尚无 CIM simulator、OS loader、runtime ABI、RISC-V ELF 工具链集成或真实 CIM primitive 源码，因此 sim/ELF 闭环均不属于当前阶段承诺。

## 目录说明

- `task_plan.md`：分阶段计划和当前执行状态。
- `findings.md`：调研记录、技术发现和决策。
- `progress.md`：按时间顺序记录开发过程和验证结果。
- `docs/`：更深入的设计说明和 ADR。
- `scripts/`：初始化、同步和验证的辅助脚本。

## 工作原则

- 源码修改都在 `tilelang/` 中完成。
- 协调、规划和文档维护都在这里完成。
- `TileOPs/` 在当前阶段只作为上层使用案例和需求来源，不作为首版实现改动位置。

## 当前约定

- SST target 采用“`c` + SST 标记”方案。
- 内部继续复用 `tilelang` 现有 `c` backend。
- 后续如需扩展为真实可执行后端，再在首版基础上继续推进。
- CIM 路线第一阶段不新增真正的 `riscv_cim_mesh` target kind，建议先复用 `c` target 并通过 `cim`/`sst`/`noc` key 或 tag 做内部分流。
- `tilelang_riscv_cim_backend_plan.md` 记录 CIM 长期路线；其中 `ir_only` / JSON 生成是近期可落地目标，abstract sim、runtime ABI 和 ELF mode 是后续建设目标。

## 推荐流程

1. 开始新阶段前先更新 `task_plan.md`。
2. 把发现和结论记录到 `findings.md`。
3. 把本次会话进度写入 `progress.md`。
4. 在 `tilelang/` 中修改源码。
5. 把验证结果同步回这个目录。
