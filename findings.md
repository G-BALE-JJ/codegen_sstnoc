# 发现与决策

## 需求

- 为 SST codegen 项目维护一个统一的规划和文档区域。
- 将实际代码修改保留在 `tilelang` 中。
- 让整个工作流适合 agent 驱动开发。
- 支持 WSL 和服务器两端的长期维护。

## 调研结论

- `tilelang` 和 `TileOPs` 是 `/data4/jjgong` 下的两个独立 Git 仓库。
- `/data4/jjgong` 本身是工作区根目录，不是 Git 仓库。
- 因此需要一个协调目录来跨仓库管理计划和记录。
- `tilelang` 根目录已经补充了 `AGENTS.md`，可作为源码仓库内的协作规范入口。
- `tilelang` 已经存在可复用的 C 代码生成路径，关键入口是 `target.build.tilelang_c` 和 `target.build.tilelang_c_host`。
- `tilelang` 的 `engine/lower.py` 已经会在 `target.kind.name == "c"` 时走 C 后端，所以首版最适合在这条路径上做 SST 识别和定制输出。
- `TileOPs` 主要是算子层和 manifest 层，首版不需要修改它。
- `TileOPs/tests/ops/test_gemm.py` 和相关 `gemm` 实现可以作为后续联调时的上层调用参考，但当前不作为第一阶段改动点。
- 当前工作区只有 `tilelang` 和 `TileOPs` 相关源码，尚无 RISC-V CIM 架构源码、simulator、OS loader、runtime ABI、RISC-V ELF 工具链集成或真实 CIM primitive 实现。
- RISC-V CIM 2D-mesh 方向仍然可行，但近期应收敛为 `TileLang GEMM -> CIM-TileIR JSON` 的编译器侧原型，而不是直接承诺 sim/ELF 可执行闭环。
- TileLang 内部保留 `tl.tileop.copy`、`tl.tileop.gemm` 等 high-level tile op 语义，适合在 `LowerTileOp` 之前通过 TIR visitor/pass 提取。
- CIM 方案第一阶段建议继续复用 `c` target + key/tag 的目标标记策略，待 IR schema、extractor 和 abstract event planner 稳定后再包装 `riscv_cim_mesh` 用户接口。

## 技术决策

| 决策 | 原因 |
|------|------|
| 使用 `codegen_sstnoc` 作为项目中枢 | 将流程集中管理，同时不污染源码仓库 |
| 规划文件采用纯 Markdown | 方便人和 agent 直接读取、编辑和版本管理 |
| 代码修改只放在 `tilelang` 中 | 避免源码归属混乱 |
| 统一使用中文文档 | 降低后续维护和沟通成本 |
| 首版复用现有 `c` 后端再做 SST 识别 | 可以最快得到 C 代码输出，风险最低 |
| 首版不修改 `TileOPs` | 先把编译链路打通，避免把问题拆得太散 |
| SST target 采用“`c` + SST 标记”而非新 kind | 现有逻辑大量依赖 `target.kind.name == "c"`，复用旧通路更稳 |
| `TileOPs` 中 GEMM 用例作为后续联调参考 | 便于后续从真实上层调用验证 codegen 行为 |
| CIM 近期目标设为 `CIM-TileIR JSON` 生成 | 当前没有 CIM 执行侧源码，先完成编译器侧可检查闭环更稳 |
| CIM sim mode 先定义为 abstract event planner | 在没有真实 simulator 的情况下，先输出 per-core event list 和粗略统计 |
| CIM ELF mode 归入长期目标 | runtime ABI、RISC-V toolchain、OS loader 均需要后续建设 |
| CIM target 第一阶段不新增真正 target kind | 复用 `c` target + key/tag 可以降低主链路改造风险 |

## 遇到的问题

| 问题 | 解决方式 |
|------|----------|
| 还没有现成的项目中枢目录 | 新建 `codegen_sstnoc` 并创建基础协调文件 |
| `tilelang` 侧缺少统一协作说明 | 新增 `tilelang/AGENTS.md` 作为源码仓库协作规范 |
| 缺少 CIM 架构、simulator、runtime 和 ELF 侧源码 | 将 `tilelang_riscv_cim_backend_plan.md` 调整为长期路线，并把第一阶段限定为 `ir_only` / JSON 生成 |

## 待确认事项

- SST 标记最终放在 `target.keys`、`tag` 还是其他自定义属性中。
- 自定义指令在 C 源码里应以宏、内联函数还是 `extern` 函数名承载。
- 首版的测试是只校验源码字符串，还是顺带校验生成流程能跑通。
- 后续联调优先选 `TileOPs` 中哪个 GEMM/算子样例作为 smoke test。
- CIM-TileIR extractor 先做 out-of-tree 包，还是直接注册为 TileLang pass。
- CIM 内部 target 标记采用 `c -keys=cim`、`c -keys=sst` 还是复用 `noc` key。
- abstract event planner 的统计模型第一版采用常数估算、公式估算还是表驱动估算。

## 资源

- `/data4/jjgong/tilelang`
- `/data4/jjgong/TileOPs`
- `/data4/jjgong/codegen_sstnoc/docs/sst-codegen-first-design.md`
- `/home/jiajun/codegen_sstnoc/tilelang_riscv_cim_backend_plan.md`

## 可视化/浏览器结论

- 暂无。
