# 发现与决策

## 需求

- 以当前 `feat/cim-tileir-json` 分支为准，推进 RISC-V CIM 2D-mesh 的 `CIM-TileIR` 技术路线。
- 为 CIM-TileIR 原型维护统一的规划、文档、示例和测试区域。
- 将当前 CIM 编译器侧原型维护在 `codegen_sstnoc/tilelang_cim` 中。
- 让整个工作流适合 agent 驱动开发。
- 支持 WSL 和服务器两端的长期维护。

## 调研结论

- `tilelang` 和 `TileOPs` 是 `/data4/jjgong` 下的两个独立 Git 仓库。
- `/data4/jjgong` 本身是工作区根目录，不是 Git 仓库。
- 因此需要一个协调目录来跨仓库管理计划和记录。
- 当前 `codegen_sstnoc` 分支已经包含 `tilelang_cim` 原型包、examples 和 tests。
- 当前主线已经从 SST C codegen 切换为 `TileLang GEMM -> CIM-TileIR JSON -> architecture-aware event plan`。
- SST C codegen 方案保留为历史背景和长期旁支，不作为当前分支近期实现主线。
- `TileOPs` 主要是算子层和 manifest 层，当前阶段不修改它。
- `TileOPs/tests/ops/test_gemm.py` 和相关 `gemm` 实现可以作为后续 smoke path 参考，但当前先使用 TileOPs-like fixture 控制复杂度。
- 当前工作区只有 `tilelang` 和 `TileOPs` 相关源码，尚无 RISC-V CIM 架构源码、simulator、OS loader、runtime ABI、RISC-V ELF 工具链集成或真实 CIM primitive 实现。
- RISC-V CIM 2D-mesh 方向仍然可行，但近期应收敛为编译器侧原型，而不是直接承诺 sim/ELF 可执行闭环。
- TileLang 内部保留 `tl.tileop.copy`、`tl.tileop.gemm` 等 high-level tile op 语义，适合在 `LowerTileOp` 之前通过 TIR visitor/pass 提取。
- CIM 方案第一阶段建议继续复用 `c` target + key/tag 的目标标记策略，待 IR schema、extractor 和 abstract event planner 稳定后再包装 `riscv_cim_mesh` 用户接口。
- 当前 `build_event_plan` 更准确的定位是 abstract event expander / IR sanity consumer。它可以展开 per-output-tile task 和 load/compute/store 事件，但由于缺少真实 architecture spec，不能作为性能模拟器或真实 mesh 执行模型。
- 后续若要让 planner 具备架构意义，需要先定义 `CIMArchitectureSpec`，至少覆盖 mesh/core、local SRAM、accumulator、DMA、CIM primitive、NoC、synchronization、mapping/dataflow 和 cycle model。
- `CIMArchitectureSpec` 第一版适合采用 JSON + Python checker，先保证可读、可测试、可由 CLI 加载。
- `serial_formula_v0` 可以作为第一版 toy cycle model：串行累加 DMA load、CIM compute、DMA store，不建模 overlap、NoC contention、barrier 或 bank conflict。

## 技术决策

| 决策 | 原因 |
|------|------|
| 使用 `codegen_sstnoc` 作为项目中枢 | 将流程集中管理，同时不污染源码仓库 |
| 规划文件采用纯 Markdown | 方便人和 agent 直接读取、编辑和版本管理 |
| 当前 CIM 原型代码放在 `tilelang_cim` 中 | 当前分支已经形成 out-of-tree 原型，便于快速迭代 |
| 统一使用中文文档 | 降低后续维护和沟通成本 |
| 当前分支以 CIM-TileIR 为主线 | 用户明确要求以当前分支和 CIM-TileIR 技术路线为准 |
| SST C codegen 降为历史背景/长期旁支 | 避免当前阶段目标混乱 |
| 当前不修改 `TileOPs` | 先把 CIM IR、architecture spec 和 planner 打稳，避免把问题拆得太散 |
| `TileOPs` 中 GEMM 用例作为后续联调参考 | 便于后续从真实上层调用验证 codegen 行为 |
| CIM 近期目标设为 `CIM-TileIR JSON` 生成 | 当前没有 CIM 执行侧源码，先完成编译器侧可检查闭环更稳 |
| CIM sim mode 先定义为 abstract event expander | 在没有真实 simulator 和 architecture spec 的情况下，先输出事件骨架和粗略统计，不输出真实性能结论 |
| CIM ELF mode 归入长期目标 | runtime ABI、RISC-V toolchain、OS loader 均需要后续建设 |
| CIM target 第一阶段不新增真正 target kind | 复用 `c` target + key/tag 可以降低主链路改造风险 |
| 下一阶段优先定义 `CIMArchitectureSpec` | 没有架构参数时继续扩展 cycle model 或 mapping policy 容易产生误导 |
| 有 architecture spec 时才输出非 0 cycle estimate | cycle estimate 必须有明确参数来源 |
| 第一版 cycle model 使用 `serial_formula_v0` | 建立可解释、可测试的 toy 模型，不提前承诺真实硬件性能 |

## 遇到的问题

| 问题 | 解决方式 |
|------|----------|
| 还没有现成的项目中枢目录 | 新建 `codegen_sstnoc` 并创建基础协调文件 |
| 缺少 CIM 架构、simulator、runtime 和 ELF 侧源码 | 将 `tilelang_riscv_cim_backend_plan.md` 调整为长期路线，并把第一阶段限定为 `ir_only` / JSON 生成 |

## 待确认事项

- CIM-TileIR extractor 先做 out-of-tree 包，还是直接注册为 TileLang pass。
- CIM 内部 target 标记采用 `c -keys=cim`、`c -keys=sst` 还是复用 `noc` key。
- `CIMArchitectureSpec` 第一版使用 JSON/YAML 还是 Python dataclass。
- 真实 mesh/core/local SRAM/accumulator/DMA/CIM primitive/NoC/synchronization 参数是什么。
- architecture spec 缺失时是否坚持 `estimated_cycles=0`，避免输出误导性性能数据。
- `serial_formula_v0` 后续是否应扩展为 overlap model、NoC model 或表驱动 model。
- TileOPs-like smoke path 应优先覆盖普通 GEMM 还是 grouped GEMM。

## 资源

- `/data4/jjgong/tilelang`
- `/data4/jjgong/TileOPs`
- `/data4/jjgong/codegen_sstnoc/tilelang_cim`
- `/data4/jjgong/codegen_sstnoc/docs/cim-tileir-prototype-summary.md`
- `/data4/jjgong/codegen_sstnoc/tilelang_riscv_cim_backend_plan.md`

## 可视化/浏览器结论

- 暂无。
