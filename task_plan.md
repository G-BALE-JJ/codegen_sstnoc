# SST Codegen 项目计划：tilelang 首版

## 目标

在 `tilelang` 中实现 SST 后端首版 codegen：识别到 SST 目标后，生成包含 RISC-V 自定义指令痕迹的 C 代码。首版只要求能生成 C 代码，不要求先完成可执行闭环；本目录继续作为项目控制中心，统一管理计划、决策和进度。

后续 RISC-V CIM 2D-mesh 路线以 `TileLang GEMM -> CIM-TileIR JSON -> abstract event skeleton` 为下一阶段编译器侧目标。当前项目尚无 CIM simulator、OS loader、runtime ABI、RISC-V ELF 工具链集成或真实 CIM primitive 源码，因此当前 event planner 只作为 IR 消费侧骨架，不代表真实架构模拟；architecture-aware planner、runtime ABI 和 ELF mode 均为后续建设目标。

## 当前阶段

阶段 4：实现准备

## 阶段划分

### 阶段 1：项目初始化
- [x] 确定项目协调结构
- [x] 创建规划文件
- [x] 确认仓库边界和工作规则
- [x] 补齐目录与脚本骨架
- **状态：**完成

### 阶段 2：技术调研
- [x] 梳理 `tilelang` 中相关代码路径
- [x] 找出 C codegen 的入口和可扩展点
- [x] 确认首版只修改 `tilelang`
- [x] 确认 SST target 采用“`c` + SST 标记”方案
- [x] 将结论记录到 `findings.md`
- **状态：**完成

### 阶段 3：架构规划
- [x] 设计 SST target 在 `tilelang` 中的标准化表示
- [x] 设计 SST target 判断辅助函数
- [x] 设计 C 代码生成承载方式
- [x] 设计 RISC-V 自定义指令的 C 侧表达方式
- [x] 明确 `TileOPs` 在本阶段的参考边界
- [x] 记录设计决策
- **状态：**完成

### 阶段 4：实现
- [ ] 修改 `tilelang` 的 target 识别逻辑
- [ ] 修改 `tilelang` 的 C codegen 路径
- [ ] 新增 SST 目标的最小 C 代码输出
- [ ] 新增或更新测试
- [ ] 逐步验证改动
- **状态：**进行中

### 阶段 5：验证与交接
- [ ] 验证能正确输出 SST 相关 C 代码
- [ ] 验证生成结果包含预期的自定义指令痕迹
- [ ] 记录测试结果
- [ ] 为后续支持真实执行做铺垫
- **状态：**未开始

### 阶段 6：CIM-TileIR 编译器侧原型
- [x] 定义 `CIM-TileIR` GEMM 子集 schema
- [x] 设计 `TileLang/TIR -> CIM-TileIR JSON` extractor MVP
- [x] 支持 static shape GEMM、2D output tile grid 和 output-stationary dataflow
- [x] 支持标准模板中 `T.Kernel`、`T.copy`、`T.gemm`、`T.alloc_shared`、`T.alloc_fragment`、`T.Pipelined(num_stages=1/2)` 的语义提取
- [x] 支持 TileLang `PrimFunc.script()` 中 `T.match_buffer`、`T.alloc_buffer`、`T.serial`、`T.gemm` 的 MVP 提取
- [x] 新增 JSON checker，验证 tile size、buffer scope、mapping 和 program op 顺序
- [x] 新增静态 GEMM JSON 生成示例
- [ ] 扩展支持转置 GEMM、非标准临时 buffer copy 和更多 TileOPs GEMM 变体
- **状态：**进行中

### 阶段 7：CIM event expander 与架构规格准备
- [x] 定义 mesh/core/CIM GEMM/DMA 的最小抽象事件字段
- [x] 实现 `CIM-TileIR JSON` loader / event expander MVP
- [x] 生成 per-core tile task 和 event list
- [x] 输出 DMA bytes、CIM op count、MACs、core utilization 等粗略统计
- [x] 明确当前 event planner 不是真实 simulator，`estimated_cycles=0` 不代表硬件周期
- [ ] 定义 `CIMArchitectureSpec` schema 和 checker
- [ ] 用 architecture spec 校验 local SRAM、accumulator、dtype、CIM tile shape、DMA 等约束
- [ ] 在 architecture spec 明确提供参数后，再增加 NoC、barrier、pipeline overlap 和非 0 cycle model
- **状态：**进行中

### 阶段 8：CIM runtime ABI 与 ELF 长期闭环
- [ ] 定义 runtime ABI，例如 `tl_core_id`、`tl_dma_load`、`tl_dma_store`、`tl_cim_gemm`
- [ ] 设计 C++ SPMD kernel codegen
- [ ] 集成 RISC-V 编译、链接、加载工具链
- [ ] 打通 GEMM ELF 闭环
- **状态：**长期目标

## 关键问题

1. SST 标记最终放在 `target.keys`、`tag`，还是其他自定义属性中？
2. 生成的 RISC-V 自定义指令应该先以宏、内联函数还是 `extern` 声明落到 C 中？
3. 首版是否只需要生成 C 源码，不要求立即可执行？
4. 哪些现有 `tilelang` 入口最适合挂接 SST 目标识别逻辑？
5. 用哪些最小测试可以稳定验证“识别到 SST 后能生成对应 C 代码”？
6. `TileOPs` 侧需要保留哪些最小案例作为后续联调样本？
7. CIM-TileIR 第一版是否先作为 out-of-tree 包实现，还是直接挂到 `tilelang` pass pipeline？
8. CIM 内部 target 标记使用 `c -keys=cim`、`c -keys=sst` 还是复用既有 `noc` key？
9. `CIMArchitectureSpec` 的第一版应采用 JSON/YAML 还是 Python dataclass？
10. 架构参数未知时，cycle model 是否应继续保持 `estimated_cycles=0`？
11. 真实 mesh 的 local SRAM、accumulator、DMA、CIM primitive、NoC 和 synchronization 参数分别是什么？

## 已做决策

| 决策 | 原因 |
|------|------|
| 使用 `codegen_sstnoc` 作为协调中枢 | 将计划和决策与源码修改分离，避免混乱 |
| 实现改动只放在 `tilelang` 中 | 保持源码归属清晰，便于审查和维护 |
| 规划文档统一使用中文 | 方便日常维护和长期协作 |
| 首版只做 C 代码生成，不做执行闭环 | 先把目标识别和代码输出打通，降低首版复杂度 |
| 优先复用 `tilelang` 现有 C 后端 | 现成的 `target.build.tilelang_c` 和 `tilelang_c_host` 是最稳的落点 |
| SST 目标采用“`c` + SST 标记”方案 | 保持 `target.kind.name == "c"`，最大化复用现有 C backend，避免引入新的 target kind |
| `TileOPs` 当前只作为参考，不作为首版修改目标 | 先聚焦编译链路本身，避免问题面扩散 |
| CIM 路线第一阶段只做 `CIM-TileIR JSON`，不承诺 simulator/ELF | 当前尚无 CIM simulator、OS loader、runtime ABI 和 RISC-V ELF 工具链集成源码 |
| CIM target 第一阶段不新增真正 `riscv_cim_mesh` target kind | 继续复用 `c` target + key/tag 可降低 TVM target 注册和主链路改造风险 |
| CIM sim mode 先降级为 abstract event expander | 在没有真实 architecture spec 和 simulator 的情况下，只验证 IR 能否被下游消费 |
| 下一阶段优先定义 `CIMArchitectureSpec` | 没有架构参数时继续扩展 cycle model 或 mapping policy 容易产生误导 |

## 遇到的问题

| 问题 | 解决方式 |
|------|----------|
| 目前没有现成的项目中枢目录 | 新建 `codegen_sstnoc` 并初始化基础文档 |
| SST 目标的精确定义还未固定 | 首版先按“识别 SST 目标并输出 C 代码”推进，后续再细化 target 表达 |
| 当前没有 CIM 架构、simulator、OS loader、runtime ABI 和 ELF 工具链源码 | 将 CIM 近期目标收敛为编译器侧 `CIM-TileIR JSON` 原型，sim/ELF 作为后续阶段 |

## 备注

- 每完成一个阶段后更新本文件。
- 规划文件应始终作为流程和决策的权威记录。
