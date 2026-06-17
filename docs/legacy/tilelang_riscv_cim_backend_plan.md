# TileLang 与 RISC-V CIM 2D-Mesh Programming Model 衔接方案

> Legacy note: 本文档记录早期 TileLang/RISC-V CIM 规划，包含已经废弃的 abstract event planner、toy architecture spec 和 architecture-aware planner 路线。当前主线见 `../golem-runtime-codegen-roadmap.md` 和 `../cim-tileir-prototype-summary.md`。

## 1. 目标定位

本方案描述一条从 TileLang tile-level programming model 逐步扩展到 RISC-V CIM 2D-mesh 后端的路线。当前项目只有 `tilelang` 和 `TileOPs` 相关源码，尚无 CIM 架构源码、simulator、OS loader、RISC-V runtime 或 ELF 工具链集成。因此，本方案将近期目标收敛为：

```text
TileLang GEMM 子集
    ↓
TileLang frontend / TIR
    ↓
CIM 语义提取与规划
    ↓
CIM-TileIR JSON
    ↓
可检查的抽象执行计划
```

最终目标仍然可以包装为 TileLang 风格的 device target：

```text
riscv_cim_mesh
```

但第一阶段不建议直接新增真正的 TVM/TileLang `TargetKind`。更稳妥的实现策略是：先沿用现有 `c` target，在 target 上增加 `cim` / `sst` / `noc` 之类的 key 或 tag 进行分流。待 `CIM-TileIR` schema、GEMM 提取流程、architecture spec 和架构感知执行模型稳定后，再把用户接口包装为 `riscv_cim_mesh`。

`CIM-TileIR` 是本项目定义的架构相关中间表示，可以保存为 JSON，也可以在后续实现中用 Python/C++ 对象表示。它不是某个特定文件，而是 TileLang 与未来 architecture-aware planner、simulator、runtime、ELF codegen 之间的接口契约。

## 2. 当前资产与约束

### 2.1 已有资产

- `tilelang` 源码。
- `TileOPs` 源码，可作为上层算子和 GEMM 调用方式参考。
- `codegen_sstnoc` 项目中枢文档。
- TileLang 已有 `c` backend 路径，可作为首版 codegen 和目标分流基础。
- TileLang 内部保留 `T.copy`、`T.gemm`、`T.Pipelined` 等 tile op 语义，适合通过 TIR visitor/pass 提取。

### 2.2 尚未具备的资产

- RISC-V CIM 2D-mesh simulator。
- OS loader 或多核启动框架。
- RISC-V runtime ABI 实现。
- RISC-V ELF 编译、链接和加载闭环。
- 真实 CIM GEMM primitive 或自定义指令实现。
- 精确 NoC、DMA、SRAM、CIM array cycle model。

因此，本文档中的 sim mode 和 elf mode 均为后续扩展目标；第一阶段不承诺已有 simulator/loader/runtime 的复用。

## 3. 功能边界

### 3.1 TileLang 侧负责

TileLang 作为前端，负责表达和承载以下信息：

- 算子级 programming model，例如 GEMM kernel。
- tile 级循环结构，例如 `T.Kernel(grid_x, grid_y)`。
- 显式 buffer 层级，例如 `T.alloc_shared`、`T.alloc_fragment`。
- 显式数据搬运，例如 `T.copy`。
- tile 级计算原语，例如 `T.gemm`。
- pipeline 语义，例如 `T.Pipelined`。

本项目不要求 TileLang 原生理解 RISC-V CIM 架构细节，而是在 backend 或 out-of-tree 工具中解释这些 tile 语义。

### 3.2 近期 CIM backend 负责

近期 backend 的核心目标不是生成可执行程序，而是把 TileLang/TIR 的通用 tile 语义转换为可检查的 `CIM-TileIR`：

- 将 `T.Kernel` 的 tile grid 映射为 2D mesh 上的抽象 core/task。
- 将 `T.copy` 描述为抽象 load/store 事件。
- 将 `T.gemm` 描述为抽象 `cim_gemm` 事件。
- 将 `T.alloc_shared` 映射为 per-core local SRAM / scratchpad 描述。
- 将 `T.alloc_fragment` 映射为 accumulator / register / partial-sum buffer 描述。
- 将 `T.Pipelined` 的 `num_stages=1/2` 提取为 pipeline metadata。
- 生成 `CIM-TileIR JSON`，作为后续 abstract sim 和 ELF codegen 的共同输入。

### 3.3 抽象 event expander / 后续 simulator 侧负责

当前尚无现成 simulator，也尚无真实 mesh architecture spec。MVP 中已经实现的 `build_event_plan` 更准确地说是 abstract event expander / IR sanity consumer，而不是完整 cycle-accurate simulator：

- 读取 `CIM-TileIR JSON`。
- 根据 mesh 配置创建抽象 core 列表。
- 根据 tile mapping 给每个 core 分配 tile task。
- 展开 load / store / cim_gemm 等抽象事件。
- 输出 per-core event list。
- 统计 DMA bytes、store bytes、CIM op count、MACs、core utilization 等指标。

该阶段用于验证 IR 结构和 tile mapping 是否能被下游消费，不代表真实硬件执行。当前 `estimated_cycles` 应保持为 0 或缺省值，直到 architecture spec 明确给出 DMA、CIM primitive、NoC、synchronization 等参数。

后续真正的 architecture-aware planner / simulator 需要先定义 `CIMArchitectureSpec`，至少包含 mesh/core、local SRAM、accumulator、DMA、CIM primitive、NoC、barrier、mapping/dataflow 和 cycle model。

### 3.4 OS/ELF 侧负责

ELF mode 是长期扩展目标。当前项目尚未具备 OS loader、多核 runtime、RISC-V toolchain 集成和 CIM primitive 实现，因此第一阶段只定义接口草案，不承诺 ELF 闭环。

未来 ELF mode 的目标链路为：

```text
CIM-TileIR
    ↓
C++ SPMD kernel
    ↓
riscv-g++ / clang
    ↓
kernel.elf
    ↓
OS loader
```

推荐边界仍然是：

```text
TileLang/TIR -> CIM-TileIR
```

之后的：

```text
CIM-TileIR -> C++ -> ELF -> OS loader
```

需要在后续阶段另行建设。

## 4. CIM-TileIR 设计

`CIM-TileIR` 是 TileLang backend 输出的架构相关中间表示。第一阶段 schema 应尽量小，只覆盖 GEMM 子集和可检查的事件计划。

### 4.1 Kernel 与 Tensor 描述

- kernel name。
- M/N/K 等 shape。
- tensor shape / stride / dtype。
- tensor role，例如 A、B、C。
- output layout。
- 可选 base address；第一阶段可用符号地址，不要求真实物理地址。

### 4.2 Tiling 描述

- BM / BN / BK。
- K 维 loop count。
- edge tile 处理策略。
- accumulator dtype。

### 4.3 Mesh Mapping 描述

- mesh width / height。
- tile id 到 core id 或 `(core_x, core_y)` 的映射。
- 初期只支持 output-stationary dataflow。
- 一个 core 是否处理多个 output tile。

### 4.4 Memory 与 Communication 描述

- global memory 抽象。
- local SRAM / scratchpad 抽象。
- accumulator buffer 抽象。
- DMA load/store 抽象事件。
- NoC send/recv/broadcast/multicast 先作为可选字段，不作为第一阶段必需能力。
- barrier/synchronization 先作为可选字段，不作为第一阶段必需能力。

### 4.5 Compute 描述

- `clear_acc`。
- `load`。
- `store`。
- `cim_gemm`。
- `loop_k`。
- 可选 `barrier`。
- 可选 elementwise/fusion op；第一阶段不支持复杂 fusion。

示例 JSON：

```json
{
  "kernel": "gemm",
  "target": "riscv_cim_mesh",
  "mode": "ir_only",
  "mesh": { "w": 8, "h": 8 },
  "tile": { "BM": 64, "BN": 64, "BK": 32 },
  "tensors": {
    "A": { "shape": [1024, 1024], "dtype": "int8", "addr": "A_base" },
    "B": { "shape": [1024, 1024], "dtype": "int8", "addr": "B_base" },
    "C": { "shape": [1024, 1024], "dtype": "int32", "addr": "C_base" }
  },
  "mapping": {
    "policy": "output_stationary",
    "core_x": "bx % mesh_w",
    "core_y": "by % mesh_h"
  },
  "program": [
    { "op": "clear_acc", "buffer": "C_acc" },
    {
      "op": "loop_k",
      "var": "ko",
      "count": "ceildiv(K, BK)",
      "pipeline_stages": 2,
      "body": [
        { "op": "load", "tensor": "A", "tile": ["by*BM", "ko*BK", "BM", "BK"], "dst": "A_s" },
        { "op": "load", "tensor": "B", "tile": ["ko*BK", "bx*BN", "BK", "BN"], "dst": "B_s" },
        { "op": "cim_gemm", "A": "A_s", "B": "B_s", "C": "C_acc" }
      ]
    },
    { "op": "store", "src": "C_acc", "tensor": "C", "tile": ["by*BM", "bx*BN", "BM", "BN"] }
  ]
}
```

## 5. Backend 实现技术路线

### 5.1 第 0 阶段：范围校准

本阶段只修改项目文档，不修改源码：

- 明确当前没有 CIM simulator、OS loader、runtime 和 ELF 工具链资产。
- 明确第一阶段目标是 `TileLang GEMM -> CIM-TileIR JSON`。
- 将 sim mode 改为后续 abstract simulator / event planner。
- 将 elf mode 改为长期目标。
- 保留 `TileOPs` 作为上层参考，不把它纳入第一阶段修改范围。

### 5.2 第 1 阶段：out-of-tree CIM-TileIR 原型

先不修改 TileLang 主干，独立实现一个外部 backend 包：

```text
tilelang_cim/
  ir/
    cim_tile_ir.py
    schema.py
  passes/
    tir_extract.py
    mesh_mapping.py
    buffer_planning.py
  backends/
    json_export.py
  tests/
    test_gemm_ir.py
```

建议接口：

```python
import tilelang_cim as tlcim

ir = tlcim.compile(
    tilelang_func,
    target={
        "kind": "riscv_cim_mesh",
        "mesh": [8, 8],
        "mode": "ir_only"
    }
)

tlcim.export_json(ir, "gemm.cimtile.json")
```

内部可以先把 `kind="riscv_cim_mesh"` 转成 `Target({"kind": "c", "keys": ["cim"]})` 或等价标记，以复用 TileLang 现有 `c` backend / CPU-style lowering 能力。该阶段目标是将现有 parser 思路升级为 TIR visitor/pass，即从 TileLang/TIR 节点中提取语义，而不是解析 Python 源码文本。

### 5.3 第 2 阶段：CIM architecture spec 草案

在将当前 event expander 升级为 architecture-aware planner 前，需要先定义最小架构规格：

- mesh 宽高。
- `core_id` 与 `(core_x, core_y)` 的映射。
- per-core local SRAM 容量。
- accumulator buffer 容量。
- `cim_gemm` 支持的 dtype、BM/BN/BK 约束。
- DMA load/store 的抽象语义和带宽模型。
- NoC 通信是否支持；若支持，先支持单播还是广播。
- barrier 粒度；第一阶段可先不支持。
- cycle model 是常数估算、公式估算还是表驱动估算。

没有这份规格，event planner 只能输出事件骨架，不能输出可信的 legality / cycle / performance 结论。当前阶段汇总见 `../cim-tileir-prototype-summary.md`。

### 5.4 第 3 阶段：abstract event expander / architecture-aware planner

sim mode 初期不是完整 simulator，而是两层逐步推进。

第一层是当前已完成的 event expander：

```text
CIM-TileIR JSON
    ↓
IR loader
    ↓
per-core tile task
    ↓
per-core event list
    ↓
粗略统计指标
```

该层只输出事件骨架和静态统计，不代表真实执行。

第二层需要在 architecture spec 之后再做：

```text
CIM-TileIR JSON + CIMArchitectureSpec
    ↓
legality check
    ↓
architecture-aware event plan
    ↓
optional rough cycle estimate
```

建议后续新增：

- `CimTileIrLoader`
- `KernelDesc`
- `TileTask`
- `CimOp`
- `MeshMapper`
- `BufferPlanner`
- `EventPlanner`
- `CIMArchitectureSpec`
- `ArchitectureChecker`

执行流程：

```text
读取 JSON
    ↓
构建 kernel/tensor/tile/mapping 描述
    ↓
读取或选择 architecture spec
    ↓
校验 dtype / tile shape / local SRAM / accumulator / DMA 约束
    ↓
按 core_id 分配 tile task
    ↓
展开 load / cim_gemm / store event
    ↓
输出 per-core event list 和统计指标
```

### 5.5 第 4 阶段：ELF/runtime ABI 草案与实现

ELF mode 在 simulator/event planner 稳定后再启动。该阶段以 `CIM-TileIR` 为输入生成 C++ SPMD kernel：

```text
CIM-TileIR
    ↓
kernel.cpp
    ↓
riscv-g++ / clang
    ↓
kernel.elf
    ↓
OS loader
```

建议定义最小 runtime ABI 草案：

```cpp
int tl_core_id();
int tl_mesh_x();
int tl_mesh_y();

void tl_dma_load(void* local, uint64_t global, size_t bytes);
void tl_dma_store(uint64_t global, const void* local, size_t bytes);

void tl_noc_send(int dst_x, int dst_y, const void* buf, size_t bytes);
void tl_noc_recv(int src_x, int src_y, void* buf, size_t bytes);
void tl_barrier();

void tl_cim_gemm(
    const void* A_s,
    const void* B_s,
    void* C_acc,
    int BM,
    int BN,
    int BK
);
```

该 ABI 当前只是接口草案，不代表已有实现。

### 5.6 第 5 阶段：TileLang target 包装

在前面流程稳定后，再把接口包装成 TileLang 风格：

```python
tilelang.compile(
    func,
    target={
        "kind": "riscv_cim_mesh",
        "mesh": [8, 8],
        "mode": "ir_only"
    }
)
```

或者：

```python
tilelang.compile(
    func,
    target={
        "kind": "riscv_cim_mesh",
        "mesh": [8, 8],
        "mode": "sim"
    }
)
```

内部仍可继续复用 `c + cim key` 的实现策略，直到确实需要新增真正 target kind。

## 6. MVP 支持范围

第一版 MVP 名称建议为：

```text
TileLang GEMM 到 CIM-TileIR 的编译器侧原型
```

MVP 支持：

- static shape 或 compile-time known shape。
- 2D output tile grid。
- output-stationary dataflow。
- `T.Kernel` 二维 grid；建议先使用 CPU-style kernel 或 `c` target 兼容路径。
- `T.copy` global to local / local to global。
- `T.alloc_shared` / `T.alloc_fragment`。
- `T.gemm`。
- `T.Pipelined` 的 `num_stages=1` 或 `num_stages=2`。
- 输出 `CIM-TileIR JSON`。
- JSON checker 验证 tile size、buffer scope、program op 顺序、mapping 合法性。

暂不支持：

- 任意 Python 控制流。
- 动态 shape。
- 复杂 fusion。
- 任意 TVM schedule primitive。
- 完整 CUDA thread/warp 语义。
- NoC multicast/broadcast 的真实执行。
- 精确 cycle simulator。
- 由 TVM 直接生成最终 RISC-V ELF。

## 7. 与 GPU Backend 的区别

两者在 TileLang 前端上相似，都是 tile-based programming model；区别在 backend lowering 和当前项目资产成熟度。

```text
GPU backend:
TileLang tile program
    ↓
block/thread/warp/tensor-core lowering
    ↓
CUDA/HIP/LLVM executable

RISC-V CIM mesh backend:
TileLang tile program
    ↓
tile/core/CIM/NoC 语义提取
    ↓
CIM-TileIR JSON
    ↓
abstract sim / future RISC-V ELF
```

对应关系：

| GPU | RISC-V CIM 2D-mesh |
|---|---|
| GPU device | RISC-V CIM mesh device |
| SM | mesh core / core cluster |
| CUDA block | output tile task |
| thread/warp | core 内 lane / CIM subarray / micro-op |
| tensor core | CIM array |
| shared memory | local SRAM / scratchpad |
| CUDA runtime | future OS loader / simulator runtime |
| PTX/cubin | CIM-TileIR / future RISC-V ELF |

因此，本项目不是简单复用 GPU backend，而是将同一套 TileLang tile programming model 逐步 lowering 到新的架构抽象。

## 8. 预期产出

### 8.1 近期产出

- `CIM-TileIR` schema 与 JSON 示例。
- TileLang/TIR 到 `CIM-TileIR` 的 GEMM 子集 extractor。
- GEMM `ir_only` 闭环。
- JSON checker。
- 面向 mesh size、tile size、pipeline stage 的静态合法性检查。

### 8.2 中期产出

- 抽象 CIM 架构规格。
- abstract event expander。
- architecture-aware planner。
- per-core task graph。
- load/store/cim_gemm event list。
- 粗略 DMA bytes、CIM op count、MACs、core utilization 统计。
- 在 architecture spec 明确后，再输出 estimated cycles。

### 8.3 长期产出

- runtime ABI 实现。
- C++ SPMD kernel codegen。
- RISC-V toolchain 集成。
- OS loader / 多核执行框架。
- GEMM ELF 闭环。
- 更丰富的 dataflow、pipeline 和 schedule search。

## 9. Pre 汇报简短版

我们计划将 TileLang 的 tile programming model 逐步衔接到 RISC-V CIM 2D-mesh 架构。当前项目只有 `tilelang` 和 `TileOPs` 相关源码，尚无 CIM simulator、OS loader、runtime ABI 或 RISC-V ELF 工具链集成，因此近期目标不会直接承诺可执行闭环，而是先做编译器侧原型。

第一阶段目标是支持 GEMM 子集，把 TileLang/TIR 中的 `T.Kernel`、`T.copy`、`T.gemm`、`T.alloc_shared`、`T.alloc_fragment` 和 `T.Pipelined` 语义提取为 `CIM-TileIR JSON`。该 IR 描述 output tile 如何映射到 2D mesh core，A/B/C tensor 如何切 tile，load/store/cim_gemm 事件如何组织，以及 pipeline stage 等 metadata。

实现上，第一阶段不建议直接新增真正的 `riscv_cim_mesh` target kind，而是先复用 TileLang 现有 `c` target 路径，通过 `c + cim key/tag` 做内部标记。对外可以保留 `riscv_cim_mesh` 的包装接口，内部先转成兼容现有 C/CPU-style lowering 的形式，降低改动风险。

中期先实现一个 abstract event expander，读取 `CIM-TileIR JSON` 后生成 per-core task 和 event list，输出 DMA bytes、CIM op count、MACs、core utilization 等静态统计。它不代表真实 simulator，也不输出可信硬件周期。之后需要先定义 `CIMArchitectureSpec`，再升级为 architecture-aware planner，并在架构参数明确后才输出 estimated cycles。长期才进入 C++ SPMD、runtime ABI、RISC-V ELF 和 OS loader 闭环。

这样项目会从现有资产出发，先证明 TileLang GEMM 到 CIM-TileIR 的编译器侧路径可行，再逐步补齐 CIM 架构、模拟器和执行链路。
