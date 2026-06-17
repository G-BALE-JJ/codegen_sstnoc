# SST 首版 Codegen 技术设计

> Legacy note: 本文档记录早期 TileLang C backend / SST target / RISC-V custom instruction 路线，不是当前实现主线。当前主线见 `../golem-runtime-codegen-roadmap.md`。

## 设计目标

在 `tilelang` 中增加首版 SST 后端支持，使编译链能够：

1. 识别 SST 目标。
2. 继续复用现有 `c` backend。
3. 在生成的 C 源码中输出可表示 RISC-V 自定义指令的代码片段。
4. 首版只保证“能生成正确形态的 C 代码”，不要求立即可执行。

## 非目标

- 当前阶段不修改 `TileOPs` 的实现代码。
- 当前阶段不新增真正独立的 target kind，例如 `c_SST`。
- 当前阶段不打通完整运行时、工具链和硬件执行链路。
- 当前阶段不要求自动从 `TileOPs` 直接触发 SST 代码生成。

## 现有架构理解

### Python 侧

- `tilelang/tilelang/utils/target.py`
  - 负责 target 字符串标准化和 `Target` 构造。
  - 适合加入 SST target 的别名解析与标准化逻辑。
- `tilelang/tilelang/engine/lower.py`
  - 负责 lowering 以及 host/device IR 分离。
  - 当 `target.kind.name == "c"` 时，设备侧已经走 `target.build.tilelang_c`。
- `tilelang/tilelang/jit/adapter/utils.py`
  - 有 `is_cpu_target()` 这类辅助判断。
  - 适合补一个 SST target 判断辅助函数。

### C++ 侧

- `tilelang/src/target/rt_mod_c.cc`
  - 注册 `target.build.tilelang_c`。
  - 负责创建 `CodeGenTileLangC` 并产出 C 源码模块。
- `tilelang/src/target/codegen_c.h`
  - `CodeGenTileLangC` 的声明。
- `tilelang/src/target/codegen_c.cc`
  - `CodeGenTileLangC` 的实现。
  - 其中 `VisitExpr_(const CallNode* op, std::ostream& os)` 是处理 extern 调用和特殊表达式输出的关键位置。
- `tilelang/src/target/codegen_c_host.cc`
  - host 侧 C 源码生成。
  - 首版重点不在 host 侧逻辑改造，但可以补注释或目标标识。

## 总体方案

### 核心思路

SST target 不作为新的 `target.kind` 引入，而是采用：

- `kind = "c"`
- 外加 SST 标记

这样可以保持以下现有逻辑不变：

- `target.kind.name == "c"` 的判断仍成立
- `lower.py` 仍然自动走现有 C backend
- `jit` 和辅助工具里的 CPU/C target 识别路径大部分不用重写

## SST target 表示方案

### 用户侧表示

用户传入的 target 保持为“`c` + SST”的形式。具体字符串格式建议有两种备选：

1. `c -keys=sst`
2. `c -tag=sst`

首版建议优先采用“标准化后写入自定义 key/attr”的方式，而不是依赖用户手写复杂 Target 字符串。

### 内部标准化表示

Python 侧标准化后，内部目标应满足：

- `target.kind.name == "c"`
- 同时能通过统一辅助函数判断这是 SST 目标

建议内部实现提供：

- `normalize_sst_target(target: str | Target) -> Target | None`
- `is_sst_target(target: Target) -> bool`

### 推荐实现方式

优先尝试以下内部表示：

- `Target({"kind": "c", "keys": ["sst"]})`

如果 TVM 对 `keys` 的行为不稳定或不适合，也可以退回到：

- `Target({"kind": "c", "tag": "sst"})`

最终原则是：

- Python 侧统一构造
- 下游判断逻辑统一使用 `is_sst_target()`
- 不把具体属性细节散落在各处 `if` 语句里

## 代码修改点设计

### 1. target 标准化层

文件：

- `tilelang/tilelang/utils/target.py`

新增内容：

- `normalize_sst_target()`
- `target_is_sst()` 或 `is_sst_target()` 风格的辅助函数
- 在 `determine_target()` 中插入 SST target 识别逻辑

职责：

- 识别用户传入的 SST 目标表示
- 构造标准化的 `Target`
- 保证后续 `Target(...).kind.name == "c"`

### 2. Python 辅助判断层

文件：

- `tilelang/tilelang/jit/adapter/utils.py`

新增内容：

- `is_sst_target(target: Target) -> bool`

职责：

- 给上层工具、测试和后续调试统一判断入口

注意：

- `is_cpu_target()` 不需要替换
- SST 目标本质仍属于 CPU/C target 的一类

### 3. device codegen 分支层

文件：

- `tilelang/tilelang/engine/lower.py`

当前逻辑中，`target.kind.name == "c"` 已经走：

- `target.build.tilelang_c`

首版建议：

- 不新增新的 build 入口
- 不新增新的 `target.build.tilelang_sst`
- 继续走 `target.build.tilelang_c`

也就是说，这一层只依赖 SST target 已经被标准化为 `kind == "c"`。

### 4. C 代码生成层

文件：

- `tilelang/src/target/codegen_c.h`
- `tilelang/src/target/codegen_c.cc`
- 如有必要，`tilelang/src/target/rt_mod_c.cc`

新增内容建议：

- 在 `CodeGenTileLangC` 中新增 SST 目标状态位，例如 `is_sst_target_`
- 在 `Init(...)` 或构造阶段解析 `target_str` / `Target` 信息，设置该状态
- 在 `VisitExpr_(const CallNode* op, std::ostream& os)` 中对 SST 相关调用进行定制输出

## RISC-V 自定义指令承载方案

### 首版建议

首版不要直接生成复杂内联汇编，建议先生成以下两类之一：

1. 宏调用
2. 内联函数调用

例如：

```c
SST_RISCV_CUSTOM_OP(dst, src0, src1);
```

或：

```c
sst_riscv_custom_op(dst, src0, src1);
```

这样做的优点：

- 生成结果更容易验证
- 不需要首版就绑定具体汇编模板
- 后续可以把宏/内联函数的实现替换成真正的 inline asm

### 暂不推荐首版直接做的方式

- 直接在 codegen 里拼完整 `asm volatile(...)`
- 在第一版就耦合完整 RISC-V 编译器约束字符串

原因：

- 调试成本高
- 一旦操作数类型和寄存器约束未完全明确，很容易在早期陷入编译细节

## IR 到 C 的映射建议

首版最好显式引入一个“专用于 SST codegen 的 extern 调用命名约定”。

建议形式：

- 在 TileLang/TIR 层使用 `call_extern("tl.sst.xxx", ...)`
- C backend 在 `VisitExpr_(CallNode)` 中识别这个命名空间

例如：

- `tl.sst.custom0`
- `tl.sst.mma`
- `tl.sst.ld`
- `tl.sst.st`

这样做的优点：

- 不需要大改现有 lowering 主链
- 便于在 codegen 层集中识别
- 后续可以平滑扩展更多 SST 原语

## 建议的第一阶段最小闭环

第一阶段不追求通用性，建议先打通一个最小路径：

1. Python 侧能识别 SST target。
2. `lower.py` 正常走到 `tilelang_c` backend。
3. 构造一个最小 TIR/extern 调用样例。
4. `CodeGenTileLangC` 在 SST target 下把该调用输出成 SST 自定义宏/函数调用。
5. 测试断言生成源码中包含预期字符串。

## 测试设计

### 测试目标

验证的核心不是执行结果，而是源码生成行为：

- 普通 `c` target 不应走 SST 特化输出
- SST target 应输出预期的自定义指令表达
- 输出源码应包含目标标识或特征片段

### 建议测试类型

1. target 标准化测试
   - 输入 SST target 字符串
   - 断言输出 target 仍是 `kind == "c"`
   - 断言 `is_sst_target(target)` 为真

2. codegen 字符串测试
   - 给定最小 `PrimFunc`
   - 使用 SST target 编译
   - 断言 `kernel_source` 包含：
     - SST 标记
     - 宏名或函数名

3. 回归测试
   - 普通 `c` target 下，相同路径不应输出 SST 专用代码

## 与 TileOPs 的关系

当前阶段：

- `TileOPs` 不参与实现改动
- `TileOPs` 只作为需求来源和联调样例来源

后续阶段：

- 可选择 `TileOPs/tests/ops/test_gemm.py`
- 或 `TileOPs/tileops/kernels/gemm.py`

作为上层入口，验证 SST target 接入后真实调用链是否能触发新 codegen。

## 风险与规避

### 风险 1：Target 属性方案不稳定

风险：

- `keys` / `tag` 在 TVM 的行为可能和预期不完全一致

规避：

- 先在 Python 侧集中标准化
- 只暴露 `is_sst_target()` 给其他模块

### 风险 2：首版过早耦合真实汇编

风险：

- 会把调试重点从“编译链打通”转移到“汇编模板细节”

规避：

- 首版先用宏或内联函数占位

### 风险 3：改动面扩散到 TileOPs

风险：

- 问题边界失控，难以定位错误来源

规避：

- 首版只改 `tilelang`
- `TileOPs` 只做后续 smoke test

## 推荐实施顺序

1. 在 `target.py` 中加入 SST target 标准化。
2. 增加 `is_sst_target()` 辅助函数。
3. 在 C backend 中加入 SST 状态识别。
4. 在 `VisitExpr_(CallNode)` 中加入一个最小 SST extern 调用输出分支。
5. 补 target 标准化测试和 codegen 字符串测试。
6. 最后再考虑从 `TileOPs` 的 GEMM 用例联调。
