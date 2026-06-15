# CIM-TileIR 项目计划：architecture-aware event planning v0

## 目标

当前分支以 RISC-V CIM 2D-mesh 的 `CIM-TileIR` 技术路线为准。近期目标是在已有 `TileLang GEMM -> CIM-TileIR JSON -> abstract event skeleton` 原型基础上，补齐 `CIMArchitectureSpec`，实现带架构约束校验和 toy cycle estimate 的 architecture-aware event planner v0。

当前阶段仍然是编译器侧原型，不承诺真实 simulator、OS loader、runtime ABI、RISC-V ELF 工具链集成或真实 CIM primitive。SST C codegen 保留为历史背景和长期旁支，不作为当前分支近期主线。

## 当前阶段

阶段 4：extractor 稳健性扩展

## 阶段划分

### 阶段 1：CIM-TileIR JSON 原型
- [x] 定义 `CIM-TileIR` GEMM 子集 schema
- [x] 实现 `build_gemm_ir`
- [x] 实现 `validate_cim_tile_ir`
- [x] 实现稳定 JSON 导出
- [x] 新增静态 GEMM JSON 生成示例
- [x] 新增 pytest 覆盖 IR 构造、checker 和 CLI
- **状态：**完成

### 阶段 2：TileLang GEMM extractor 与 abstract event expander
- [x] 实现窄模板 TileLang GEMM 源码 extractor
- [x] 支持 TileLang `PrimFunc.script()` 中 `T.match_buffer`、`T.alloc_buffer`、`T.serial`、`T.gemm` 的 MVP 提取
- [x] 实现 `build_event_plan`
- [x] 展开 per-output-tile task 和 `clear_acc` / `dma_load` / `cim_gemm` / `dma_store` 事件
- [x] 输出 DMA bytes、CIM op count、MACs、core utilization 等粗略统计
- [x] 明确无 architecture spec 时 `estimated_cycles=0`
- **状态：**完成

### 阶段 3：architecture-aware event planning v0
- [x] 定义 `CIMArchitectureSpec` JSON schema 和 checker
- [x] 新增 toy architecture spec 示例
- [x] 实现 `CIM-TileIR + architecture spec` 联合校验
- [x] 校验 local SRAM、accumulator、dtype、CIM tile shape、DMA alignment 等约束
- [x] 新增 `build_arch_event_plan`
- [x] 在 `serial_formula_v0` 下输出每个事件、每个 task、每个 core 的粗略 cycle estimate
- [x] 扩展 `examples/plan_events.py --arch`
- [x] 新增 architecture spec、arch checker、arch event planner 和 CLI 测试
- [x] 补充 schema 文档
- **状态：**完成

### 阶段 4：extractor 稳健性扩展
- [ ] 减少对 A/B/C 参数命名的依赖
- [ ] 增加不同 dtype、默认 pipeline stages、不同变量命名的 fixture
- [ ] 改进缺失 shared buffer、fragment buffer、`T.gemm`、静态 shape 的错误信息
- [ ] 保持对动态 shape、转置 GEMM、复杂 fusion 的明确拒绝
- **状态：**未开始

### 阶段 5：TileOPs-like smoke path
- [ ] 新增 TileOPs-like GEMM fixture
- [ ] 验证 extractor 对简化 TileOPs GEMM 形态的支持边界
- [ ] 对真实 TileOPs 复杂模式输出明确 unsupported reason
- [ ] 不修改 `/data4/jjgong/TileOPs`
- **状态：**未开始

### 阶段 6：runtime ABI 与 ELF 长期闭环
- [ ] 定义 runtime ABI，例如 `tl_core_id`、`tl_dma_load`、`tl_dma_store`、`tl_cim_gemm`
- [ ] 设计 C++ SPMD kernel codegen
- [ ] 集成 RISC-V 编译、链接、加载工具链
- [ ] 打通 GEMM ELF 闭环
- **状态：**长期目标

## 关键问题

1. `CIMArchitectureSpec` 第一版是否长期保持 JSON，还是后续升级为 Python dataclass / pydantic-like schema？
2. `serial_formula_v0` 是否足够作为 architecture-aware planner v0 的 cycle model？
3. toy spec 的 SRAM、accumulator、DMA、CIM primitive 参数应如何与未来真实架构参数对齐？
4. output tile 大于 core 数时，第一版是否继续按 row-major core wrap-around 累加 core cycles？
5. output tile 小于 core 数时，后续是否需要 split-K / split-M / split-N 来提升 utilization？
6. TileLang extractor 下一步应继续 out-of-tree AST MVP，还是开始接入 TileLang pass pipeline？
7. TileOPs-like smoke path 应优先覆盖普通 GEMM 还是 grouped GEMM？

## 已做决策

| 决策 | 原因 |
|------|------|
| 当前分支以 CIM-TileIR 为主线 | 分支已包含 `tilelang_cim`、examples 和 tests，近期工作应围绕已有原型推进 |
| SST C codegen 降为历史背景/长期旁支 | 当前用户明确要求以 CIM-TileIR 技术路线为准 |
| architecture spec 是下一阶段前置项 | 没有架构参数时继续扩展 cycle model 或 mapping policy 容易产生误导 |
| 无 `--arch` 时保持 abstract event expander 行为 | 兼容已有原型和测试，避免把无架构参数的事件骨架伪装成 simulator |
| 有 `--arch` 时才输出非 0 cycle estimate | 让 cycle estimate 有明确参数来源 |
| 第一版 cycle model 使用 `serial_formula_v0` | 先建立可测试、可解释的 toy 模型，不提前承诺 overlap / NoC contention |
| 当前不修改 `TileOPs` | TileOPs 先作为上层用例来源，避免把问题面扩大 |

## 当前验收命令

```bash
TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q
bash scripts/check_docs.sh
python examples/gemm_ir.py --output /tmp/gemm.cimtile.json
python examples/plan_events.py \
  /tmp/gemm.cimtile.json \
  --arch examples/architecture/toy_cim_mesh_v0.json \
  --output /tmp/gemm.eventplan.json
```

## 备注

- 涉及 TileLang 导入的测试需要设置 `TILELANG_CACHE_DIR=/tmp/tilelang-cache`，避免默认写 `/home/jiajun/.tilelang`。
- 每完成一个阶段后更新本文件。
- 规划文件应始终作为流程和决策的权威记录。
