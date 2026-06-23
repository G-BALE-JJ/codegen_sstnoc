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
- 当前主线已经从 SST C codegen 切换为 `All frontends -> CIM-TileIR -> Golem SST backend exporter`。
- SST C codegen 方案保留为历史背景和长期旁支，不作为当前分支近期实现主线。
- `TileOPs` 主要是算子层和 manifest 层，当前阶段不修改它。
- `TileOPs/tests/ops/test_gemm.py` 和相关 `gemm` 实现可以作为后续 smoke path 参考，但当前先使用 TileOPs-like fixture 控制复杂度。
- 早期调研时当前工作区只有 `tilelang` 和 `TileOPs` 相关源码，尚无 RISC-V CIM 架构源码、simulator、OS loader、runtime ABI、RISC-V ELF 工具链集成或真实 CIM primitive 实现；截至 2026-06-16，本地已新增 `/data4/jjgong/RISC-V-CIM-Manycore-SST`，可作为真实 Golem SST 硬件/运行时对接目标。
- RISC-V CIM 2D-mesh 方向仍然可行，但近期应收敛为编译器侧原型，而不是直接承诺 sim/ELF 可执行闭环。
- TileLang 内部保留 `tl.tileop.copy`、`tl.tileop.gemm` 等 high-level tile op 语义，适合在 `LowerTileOp` 之前通过 TIR visitor/pass 提取。
- CIM 方案第一阶段建议继续复用 `c` target + key/tag 的目标标记策略，待 IR schema、extractor 和 Golem backend exporter 稳定后再包装 `riscv_cim_mesh` 用户接口。
- 早期的 `build_event_plan`、toy `CIMArchitectureSpec` 和 `serial_formula_v0` 已不再服务当前主线；本地已有真实 Golem SST 架构后，继续维护 toy 路径会制造两套架构真相。
- Golem runtime 的关键抽象不是 toy mesh 上的 `by/bx -> core`，而是 `macro_task -> worker_slot -> worker_core -> group -> data_node`。
- Golem GEMM 数据布局由 `pipeline_config.h` 与 `tools/gen_hbm_init.py` 共同定义：A 按 m tile/k tile 存储，B 按 n tile/k tile/n_col vector pack 存储，C 按 macro-task slot 和 reuse offset 存储。
- 当前 Golem 路径支持 `int32` / `fp32`，而不是 toy spec 默认的 `int8 -> int32`。
- 当前硬件约束下 `BK` 应等于 `GOLEM_ARRAY_INPUT_SIZE`，`BM` 应等于 `GOLEM_ARRAY_OUTPUT_SIZE`，`BN` 不应超过 `GOLEM_NUM_ARRAYS`；硬件 micro-tiling 完成前不应由 codegen 放宽这些约束。
- `WorkerTaskListHeaderRuntime` 是 WCP 路径的关键 descriptor，包含 worker slot、active worker cores、memory node、block shape、stride、local GM 地址、slot count 和 A/B reuse 参数。
- 硬件侧已有 `matmul_op_desc_resolved.json` 与 `matmul_env_mapping_v1.json` contract 文件，适合作为 `codegen_noc` 首版输出目标。
- 当前性能瓶颈来自 WCP/调度侧 strict-order consumption 导致的 ready-to-compute queue wait；因此后续 cycle model 应优先建模 WCP slot、prefetch window、reuse window 和队列等待，而不是只微调 DMA bandwidth 公式。
- 2026-06-16 用户进一步明确最终产物：所有前端语言都解析到 `CIM-TileIR`，再由 `CIM-TileIR` 落实到具体硬件加载环境中。
- 因此下一阶段主线应调整为 `All frontends -> CIM-TileIR -> Golem SST backend exporter`，而不是 `TileLang -> Golem` 直连，也不是 `GolemArchitectureSpec adapter`。
- Golem 硬件参数首版应作为 exporter 的后端约束校验，例如 dtype、layout、transpose、tile shape 与 array input/output/num arrays 的匹配，不应作为用户可见的第一阶段主模型。
- `run_noc_dma_pipeline.sh` 已支持通过 `GOLEM_ARTIFACT_ROOT` 定位外部 artifacts，并会在 HBM metadata 缺失时使用 `contracts/matmul_op_desc_resolved.json` 做兼容性兜底检查。
- 因此 codegen 侧无需第一步修改硬件脚本；新增 wrapper 负责 source `golem_sst.env`、导出 `GOLEM_ARTIFACT_ROOT` 并调用硬件脚本即可。
- exporter 生成的 `golem_sst.env` 必须包含 `GOLEM_ARRAY_INPUT_SIZE`、`GOLEM_ARRAY_OUTPUT_SIZE`、`GOLEM_NUM_ARRAYS`，否则硬件脚本可能回落到默认阵列参数，和 exporter 校验用的后端配置不一致。
- 用户最新要求将当前验收从“直接跑 `run_noc_dma_pipeline.sh`”调整为“检查硬件内容是否已经解耦出来”。
- 静态审计确认硬件侧已经具备：外部 `GOLEM_ARTIFACT_ROOT`、`GOLEM_MATMUL_*` env contract、resolved contract、env mapping contract、HBM generator contract 写出、runtime env 读取和 compile-time fallback macros。
- `Golem-aware event plan` 的核心不是 toy mesh 映射，而是复用硬件 `pipeline_config.h` / `gen_hbm_init.py` 公式：macro-task diagonal banding、worker slot/core、group、data node、A/B packed-once base、C output slot 和 reuse offset。
- 2026-06-17 用户确认删除无关内容：toy architecture、abstract event planner、toy event plan schema、toy 示例和相关测试从当前代码路径移除。
- `golem_event_plan` 保留为 Golem task mapping/debug/calibration 辅助产物，不作为 SST 必需输入。
- 2026-06-18 用户确认真实 TileOPs 复杂模式和 Markdown/HTML 报告暂时不用做，当前改为补齐参数化 TileLang GEMM 源码生成入口。
- 参数化入口仍必须遵守边界：命令行参数先生成 TileLang 源码，源码再被 extractor 转成 `CIM-TileIR`，最后由 Golem exporter 生成 `GOLEM_*` env 和 contracts。

## 技术决策

| 决策 | 原因 |
|------|------|
| 使用 `codegen_sstnoc` 作为项目中枢 | 将流程集中管理，同时不污染源码仓库 |
| 规划文件采用纯 Markdown | 方便人和 agent 直接读取、编辑和版本管理 |
| 当前 CIM 原型代码放在 `tilelang_cim` 中 | 当前分支已经形成 out-of-tree 原型，便于快速迭代 |
| 统一使用中文文档 | 降低后续维护和沟通成本 |
| 当前分支以 CIM-TileIR 为主线 | 用户明确要求以当前分支和 CIM-TileIR 技术路线为准 |
| SST C codegen 降为历史背景/长期旁支 | 避免当前阶段目标混乱 |
| 当前不修改 `TileOPs` | 先把 CIM IR、Golem exporter 和硬件 contract 路径打稳，避免把问题拆得太散 |
| `TileOPs` 中 GEMM 用例作为后续联调参考 | 便于后续从真实上层调用验证 codegen 行为 |
| CIM 近期目标设为 `CIM-TileIR JSON` 生成 | 当前没有 CIM 执行侧源码，先完成编译器侧可检查闭环更稳 |
| CIM ELF mode 归入长期目标 | runtime ABI、RISC-V toolchain、OS loader 均需要后续建设 |
| CIM target 第一阶段不新增真正 target kind | 复用 `c` target + key/tag 可以降低主链路改造风险 |
| Golem 对接优先走 contract/env export | 现有硬件脚本已经能消费 env 和 resolved contract，先打通 smoke path 比直接生成 ELF 更稳 |
| Golem 首版严格拒绝非硬件 tile shape | WCP micro-tiling 尚未完成，放宽 shape 会生成硬件 runtime 不能正确执行的 plan |
| Golem exporter 优先于 Golem architecture spec adapter | 用户最终产物是前端参数到 SST env/script 填充；硬件参数只作为 exporter 的合法性约束 |
| `CIM-TileIR` 是唯一前后端边界 | TileLang 只是第一个前端，Golem SST 只是第一个硬件后端；两者不能直接耦合 |
| 新增 codegen 侧 SST smoke wrapper | 保持硬件仓库主脚本不变，通过 env/artifact root 完成参数注入 |
| wrapper 默认 dry-run | 防止日常检查误触发完整 SST 仿真，完整仿真需显式 `--execute` |
| 当前阶段验收改为静态审计硬件解耦点 | 用户明确不需要直接跑 `run_noc_dma_pipeline.sh`，只需确认硬件内容已经解耦 |
| Golem-aware plan 不输出 cycle estimate | 当前阶段先对齐硬件映射语义，cycle/stats 校准进入下一阶段 |
| 删除 toy architecture 与 abstract event planner | 真实 Golem SST 已经接入，toy 路径不再是有效产品路径 |
| 保留 Golem-aware plan 作为 debug artifact | 它能解释 macro-task、worker core、data node、buffer slot 和 reuse offset，利于后续对齐 SST stats |
| 参数化实验入口先生成 TileLang 源码而不是直接生成 env | 保持 `TileLang -> CIM-TileIR -> Golem exporter` 的前后端解耦边界 |

## 遇到的问题

| 问题 | 解决方式 |
|------|----------|
| 还没有现成的项目中枢目录 | 新建 `codegen_sstnoc` 并创建基础协调文件 |
| 早期缺少 CIM 架构、simulator、runtime 和 ELF 侧源码 | 相关旧规划已归档到 `docs/legacy/`，当前主线改为 Golem SST env/contract exporter |

## 待确认事项

- CIM-TileIR extractor 先做 out-of-tree 包，还是直接注册为 TileLang pass。
- CIM 内部 target 标记采用 `c -keys=cim`、`c -keys=sst` 还是复用 `noc` key。
- 真实 TileOPs 复杂模式何时恢复推进，以及优先覆盖普通 GEMM 还是 grouped GEMM。
- exporter 核心 API 必须以 `CIM-TileIR dict` 为输入；CLI 是否首版同时支持 TileLang 源码和 `CIM-TileIR JSON` 仍待确认。
- Golem 后端约束首版参数来自 CLI 默认值、配置 JSON，还是读取硬件侧 env。
- 不同参数化 GEMM 规模是否都能在真实 SST 上稳定通过 `Simulation is complete` 和 `VERIFY-C = PASS`。
- `golem_event_plan` 是否应改名为 Golem mapping report，避免被误认为执行必需输入。

## 资源

- `/data4/jjgong/tilelang`
- `/data4/jjgong/TileOPs`
- `/data4/jjgong/codegen_sstnoc/tilelang_cim`
- `/data4/jjgong/codegen_sstnoc/docs/cim-tileir-prototype-summary.md`
- `/data4/jjgong/codegen_sstnoc/docs/legacy/tilelang_riscv_cim_backend_plan.md`
- `/data4/jjgong/codegen_sstnoc/docs/reference/golem-sst-hardware-summary.md`
- `/data4/jjgong/codegen_sstnoc/docs/golem-runtime-codegen-roadmap.md`
- `/data4/jjgong/RISC-V-CIM-Manycore-SST`
- `/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests/configs/`
- `/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests/small/mvm_noc_int_array/pipeline_config.h`
- `/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests/small/mvm_noc_int_array/gemm_matmul_op.h`
- `/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests/tools/gen_hbm_init.py`

## 可视化/浏览器结论

- 暂无。
