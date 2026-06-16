# RISC-V CIM Manycore SST — 项目综合分析

## 一、项目概述

本项目基于 **Sandia 国家实验室** 的 **SST (Structural Simulation Toolkit)** v15.0.0 框架，构建了一个 **RISC-V 多核处理器 + 模拟存算一体 (CIM/Processing-Using-Memory) 加速器** 的周期精确全系统仿真平台。项目核心目标是探索 **大规模 GEMM（矩阵乘法）** 在模拟 MVM (Matrix-Vector Multiplication) 阵列上的执行效率，重点研究数据移动瓶颈（data-movement bottleneck）、计算与通信的 overlap、以及 micro-tiling 调度策略对系统吞吐量的影响。

**项目分支**: `wt-huti-v0-full`（多 worktree 并行本地构建与安装）

---

## 二、硬件架构

### 2.1 顶层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    RISC-V Manycore System                        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐       ┌──────────┐  ┌──────────┐  │
│  │ Vanadis  │  │ Vanadis  │  ...  │ Vanadis  │  │ Vanadis  │  │
│  │ RV64 CPU │  │ RV64 CPU │       │ RV64 CPU │  │ RV64 CPU │  │
│  │  Core 0  │  │  Core 1  │       │Core N-1  │  │ Core N   │  │
│  │          │  │          │       │(Manager) │  │(Worker)  │  │
│  │  + RoCC  │  │  + RoCC  │       │  + RoCC  │  │  + RoCC  │  │
│  └────┬─────┘  └────┬─────┘       └────┬─────┘  └────┬─────┘  │
│       │             │                  │             │         │
│  ┌────┴─────┐  ┌────┴─────┐       ┌────┴─────┐  ┌────┴─────┐  │
│  │   L1     │  │   L1     │       │   L1     │  │   L1     │  │
│  │ I$/D$    │  │ I$/D$    │       │ I$/D$    │  │ I$/D$    │  │
│  └────┬─────┘  └────┬─────┘       └────┬─────┘  └────┬─────┘  │
│       │             │                  │             │         │
│  ┌────┴─────────────┴──────────────────┴─────────────┴────┐   │
│  │              Merlin Mesh NoC (4x4 typical)              │   │
│  │          路由器: hr_router, flit 128B, 3 VN            │   │
│  └──┬──────────┬──────────┬──────────┬──────────┬────────┘   │
│     │          │          │          │          │              │
│  ┌──┴──┐   ┌──┴──┐   ┌──┴──┐   ┌──┴──┐   ┌──┴──┐           │
│  │ HBM │   │ HBM │   │ HBM │   │ HBM │   │ OS  │           │
│  │Node1│   │Node2│   │Node3│   │Node4│   │Node0│           │
│  │DRAM │   │DRAM │   │DRAM │   │DRAM │   │DRAM │           │
│  │Sim3 │   │Sim3 │   │Sim3 │   │Sim3 │   │Sim3 │           │
│  └─────┘   └─────┘   └─────┘   └─────┘   └─────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────┐                   │
│  │    Golem CIM Accelerator Subsystem        │                   │
│  │    ┌─────────────┐  ┌─────────────────┐  │                   │
│  │    │ MVM Compute  │  │  Global Memory   │  │                   │
│  │    │   Array(s)   │  │  (DMA Engine)    │  │                   │
│  │    │ (int32/fp32) │  │  + Request Sched │  │                   │
│  │    └──────┬──────┘  └────────┬────────┘  │                   │
│  │           └──────────────────┘            │                   │
│  └──────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件详解

#### (1) Vanadis — RISC-V RV64 乱序 CPU
- **文件**: `src/sst/elements/vanadis/`
- **功能**: 周期精确的 RISC-V 64 位乱序执行处理器模型
- **微架构特性**:
  - 乱序执行（ROB, Reorder Buffer, 默认 64 个 slot）
  - 分支预测器（32 条目）
  - 每周期最多 4 条指令发射/退休/解码
  - 物理寄存器：整数 180×N_threads, 浮点 168×N_threads
  - 功能单元：整数 ALU（2 单元, 2 周期）、浮点（2 单元, 8 周期）、分支（1 单元）
  - TLB、L1 I$/D$、LSQ（Load-Store Queue）
  - **RoCC (Rocket Custom Coprocessor) 接口**：RISC-V 自定义协处理器接口，用于连接 CIM 加速器

#### (2) Golem — 模拟 MVM 阵列加速器（核心）
- **文件**: `src/sst/elements/golem/`
- **子模块**:

| 子模块 | 文件 | 功能 |
|--------|------|------|
| **RoCCAnalog** | `rocc/roccAnalog.h` | RoCC 接口实现，连接 RISC-V CPU 与 MVM 阵列。支持同步/异步 MVM 操作、Tile 批量执行、GM↔阵列数据传输 |
| **MVMComputeArray** | `array/mvmComputeArray.h` | MVM 计算阵列抽象。支持 int32 (MVMIntArray) 和 fp32 (MVMFloatArray) 数据类型。每个阵列有 `inputSize` 个输入 × `outputSize` 个输出（CU/计算单元），支持逐元素 Overwrite/Accumulate 输出模式 |
| **CrossSimArray** | `array/crossSimComputeArray.h` | 可选集成 Sandia CrossSim 模拟 MVM 阵列模拟器，引入模拟非理想性（analog non-idealities） |
| **GlobalMemory** | `globalmemory/globalmemory.h` | 分布式全局内存系统。提供 DMA 引擎支持跨 NoC 的远程 Load/Store、DMA Write/Read Complete 事件、完成标志机制、信用（credit）管理 |
| **GroupCtrl** | `groupctrl/groupctrl.h` | 分组控制子系统。实现 Worker/Manager 模式：Manager 核心协调组内 Worker 的资源分配（REQUEST→GRANT→DONE→FINISHED 消息协议） |
| **RequestScheduler** | `requestscheduler/requestscheduler.h` | DMA 请求调度器。管理信用分配、窗口化预取、Chunk 级请求下发、批量提交/完成 |
| **WorkerCmdProc (WCP)** | `workercmdproc/workercmdproc.h` | Worker 命令处理器。管理 Slot 缓冲（Ping-Pong 或 4-Slot）、Tile 的生命周期（submit→mat_done→vec_done→ready→compute_start→compute_done→retire）、DMA 与计算的 overlap 控制 |

#### (3) Merlin — 网状片上网络 (Mesh NoC)
- **文件**: `src/sst/elements/merlin/`
- **功能**: 可配置的 2D Mesh NoC，路由器使用 `hr_router`
- **默认配置**: 4×4 mesh, 128B flit, 3 虚拟网络, 25GB/s 链路带宽, 8KB 输入/输出缓冲

#### (4) MemHierarchy — 存储层次
- **文件**: `src/sst/elements/memHierarchy/`
- 提供 L1 Cache、Memory Controller、DRAMSim3 后端等标准存储层次组件
- HBM 仿真使用 DRAMSim3 模型

#### (5) 其他 SST 标准元素
- **Ember**: MPI 通信模式库（Halogram、Allreduce、Alltoall 等）
- **Mercury (HG)**: 多核应用框架，提供 Compute Library、System Library、OS/Process/Thread 模型
- **Ariel**: Intel Pin-tool 集成的前端仿真
- **Opal**: 页面错误处理
- **Prospero**: 内存 trace 回放
- **Miranda**: 可编程内存流量生成器

---

## 三、软件流程

### 3.1 构建与安装流程

```
scripts/build_and_install_local.sh
├── scripts/prepare_local_build.sh   # 准备 build/sst-elements/ 构建树
├── ./autogen.sh                     # 生成 configure 脚本
├── ./configure                      # 检测依赖（SST-core, DRAMSim3 等）
├── make -jN                         # 编译所有元素库
└── make install                     # 安装到 install/ 目录
```

- 依赖：SST Core（`/data4/lishun/pkg/sst_install`）、DRAMSim3（`/data4/lishun/pkg/DRAMsim3`）
- 产物：`install/lib/sst-elements-library/` 下的各 `.so` 库
- 运行前需 `source scripts/env_local_install.sh` 设置 SST 元素路径

### 3.2 测试运行流程（主路径）

**入口脚本**: `src/sst/elements/golem/tests/run_noc_dma_pipeline.sh`

```
┌─────────────────────────────────────────────────────────────────┐
│  Stage 0: 配置加载                                              │
│  ├── configs/default.env → 10_core_gemm.env → 20_dma.env        │
│  ├── → 25_latency.env → 30_network.env → 40_debug_io.env        │
│  └── → 50_tensor_verify.env → 60_run.env                        │
├─────────────────────────────────────────────────────────────────┤
│  Stage 1: 生成 Tensor 测试数据 (A, B)                            │
│  └── fronted/gemm_demo.py 生成 A (M×K) / B (K×N) 的二进制数据    │
│        支持 synthetic（合成）或 ONNX 模型权重                     │
├─────────────────────────────────────────────────────────────────┤
│  Stage 2: 生成 HBM 初始化文件                                    │
│  └── tools/gen_hbm_init.py 将 A/B/C 按数据布局写入 HBM 镜像       │
├─────────────────────────────────────────────────────────────────┤
│  Stage 3: 编译 RISC-V 应用程序                                   │
│  └── small/mvm_noc_int_array/ 下的 RISC-V 测试程序               │
│       使用 RISC-V 交叉编译器 (riscv64-unknown-elf-g++)            │
├─────────────────────────────────────────────────────────────────┤
│  Stage 4: 运行 SST 仿真                                          │
│  ├── architecture/ncores_selfcom_dma_ctrl.py 构建完整架构         │
│  │   ├── cpu_builder.py: 实例化 Vanadis CPU + L1 Cache           │
│  │   ├── noc_builder.py: 构建 Merlin Mesh NoC                    │
│  │   └── 连接 CPU ↔ NoC ↔ HBM (DRAMSim3)                        │
│  ├── 启动 sst 命令行（setsid 独立进程组）                         │
│  └── 监控日志输出，检测 "Simulation is complete"                  │
├─────────────────────────────────────────────────────────────────┤
│  Stage 4 (后处理):                                               │
│  ├── tools/extract_latency_csv.py: 提取执行摘要                  │
│  ├── 生成 execution_summary.csv / dma_summary.csv                 │
│  ├── 生成 noc_summary.csv / memory_summary.csv                    │
│  ├── tools/unpack_c_from_hbm.py: 提取 C 矩阵验证正确性            │
│  └── VERIFY-C = PASS/FAIL                                        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 配置系统

分层配置文件（env 格式），优先级：**CLI 参数 > 环境变量 > 预设文件**

| 配置文件 | 职责 |
|----------|------|
| `default.env` | 聚合器，按顺序 source 以下所有配置 |
| `10_core_gemm.env` | **核心 GEMM 参数**: M/N/K 维度、Block 尺寸、阵列数、Core 数、Group 数 |
| `20_dma.env` | **DMA 参数**: 信用管理、Slot 配置、预取窗口、窗口 K-Tile 数 |
| `25_latency.env` | **延迟参数**: MVM 计算延迟、GM↔阵列传输延迟 |
| `30_network.env` | **网络参数**: NoC 维度、缓冲大小、带宽 |
| `40_debug_io.env` | **调试参数**: 各级 Verbose 开关、日志输出 |
| `50_tensor_verify.env` | **张量验证参数**: 验证开关、参考数据路径 |
| `60_run.env` | **运行控制参数**: 控制链路开关、调度器/管理器/WCP 开关 |

### 3.4 运行时架构（软件栈）

```
┌──────────────────────────────────────────────┐
│  RISC-V Application (test_noc_dma)            │
│  ├── gemm_matmul_op_ctrl.h  ← 控制流算子     │
│  ├── gemm_matmul_op.h       ← GEMM 数据流算子│
│  └── golem_matmul_runtime.cpp ← 主函数       │
├──────────────────────────────────────────────┤
│  RoCC Custom Instructions                     │
│  ├── TILE_MVM_BATCH        (func7=0x11)       │
│  ├── TILE_WAIT_BATCH       (func7=0x12)       │
│  ├── TILE_GM2IMAT_BCAST    (func7=0x13)       │
│  ├── TILE_GM2IVEC_BATCH    (func7=0x14)       │
│  ├── WCP_START             (func7=0x15)       │
│  └── WCP_WAIT              (func7=0x16)       │
├──────────────────────────────────────────────┤
│  GroupCtrl Runtime (group_ctrl_runtime.h)     │
│  ├── WCP: Window-Buffer Slot 管理             │
│  ├── DMA Slot 分配与释放                       │
│  └── Tile 生命周期追踪                         │
├──────────────────────────────────────────────┤
│  RequestScheduler Runtime                     │
│  ├── 信用分配与回收                            │
│  ├── 窗口化预取请求下发                        │
│  └── 完成批量汇报                              │
└──────────────────────────────────────────────┘
```

### 3.5 典型配置与当前性能基线

**默认配置** (来自 `10_core_gemm.env` 等):
- `GOLEM_ARRAY_INPUT_SIZE=64`, `GOLEM_ARRAY_OUTPUT_SIZE=64`, `GOLEM_NUM_ARRAYS=64`
- `GOLEM_GEMM_M=4096`, `GOLEM_GEMM_N=128`, `GOLEM_GEMM_K=4096`
- `GOLEM_GEMM_BLOCK_M=64`, `GOLEM_GEMM_BLOCK_N=64`, `GOLEM_GEMM_BLOCK_K=64`
- `GOLEM_TOTAL_CORES=20`, `GOLEM_TOTAL_GROUPS=4`
- DMA: 32 信用/节点, 预取窗口=2, 4-Slot 缓冲

**当前性能瓶颈** (来自 `tests/cmd.md`):
- `compute_active ≈ 8.5%` — 计算时间占比极低
- `prefetch_wait ≈ 78.8%` — **Tile 等待计算的最主要瓶颈**
- `writeback_wait ≈ 12.7%` — 写回等待占次要位置
- 瓶颈本质：**不是纯 DMA 延迟，而是 Tile 虽然早早 Ready，但严格顺序消费导致长期排队等待** (`ready → compute_start` 的巨大队列延迟)

---

## 四、测试脚本体系

### 4.1 主运行脚本

| 脚本 | 功能 |
|------|------|
| `run_noc_dma_pipeline.sh` | **主入口**。4 阶段流水线：生成张量→生成 HBM→编译→仿真+验证 |
| `run_dim_sweep.sh` | M/N/K 维度参数扫描 |
| `run_flow_control_sweep.sh` | 流控参数扫描 |
| `run_numarrays_sweep.sh` | 阵列数量扫描 |
| `run_reuse_window_sweep.sh` | A/B 复用窗口策略扫描 (1×1, 1×4, 4×1, 2×2, 4×4) |
| `run_latest_comparison.sh` | 多 run 对比分析 |

### 4.2 工具脚本

| 工具 | 功能 |
|------|------|
| `tools/extract_latency_csv.py` | 提取互斥 breakdown：`compute_active_time`、`prefetch_wait_time`、`writeback_wait_time`、`control_other_time` |
| `tools/gen_hbm_init.py` | 生成 HBM 初始化镜像 |
| `tools/unpack_c_from_hbm.py` | 提取仿真后的 C 矩阵用于验证 |
| `stats/` | 各类统计文件模板 |

### 4.3 测试应用 (`small/`)

| 目录 | 说明 |
|------|------|
| `mvm_noc_int_array/` | **主测试应用**：基于 NoC 的 int32 MVM 阵列 GEMM |
| `mvm_int_array/` | 无 NoC 的本机 int32 MVM 阵列 |
| `mvm_float_array/` | fp32 MVM 阵列 |
| `gemm_int_array/` | int32 GEMM 直接阵列 |
| `crosssim_int_array/`, `crosssim_float_array/` | 集成 CrossSim 模拟非理想性 |
| `lenet5/` | LeNet-5 卷积神经网络推理 demo |

---

## 五、关键技术特点

### 5.1 模拟 MVM 阵列抽象
- 支持 **int32 和 fp32** 两种数据类型
- 阵列结构：`inputSize × outputSize` 的模拟 MVM 单元
- 计算模型：`computeCycles = ceil(inputSize / MAC_per_CU_per_cycle) + pipelineDepth`
- 可选集成 **CrossSim** 引入模拟非理想性（噪声、变化、IR drop 等）

### 5.2 分布式存储与 DMA
- HBM 节点按 **Group/Worker 亲和性** 分布数据
- DMA 引擎支持异步读写，完成标志机制
- **Credit-based 流控**：节点信用、Chunk 信用
- **窗口化预取**：提前将 K 维度的 Tile 数据搬入阵列

### 5.3 分组管理 (Group Management)
- 核心分为 **Manager（每组 1 个）** 和 **Worker（每组 GROUP_SIZE-1 个）**
- Manager 负责资源分配和同步协调
- 支持 A/B 矩阵的跨 Tile 复用（reuse）以降低 DMA 流量
- **Ctrl Link**：Manager↔Worker 之间的控制消息通道

### 5.4 Worker Command Processor (WCP)
- 管理 2 或 4 个 Slot 缓冲（Ping-Pong 或扩展）
- 每个 Slot 可以同时进行：DMA 加载矩阵、DMA 加载向量、MVM 计算
- **当前制约**：WCP 运行时仍把逻辑 Block 当作 Hardware Tile 直接执行，尚未实现真正的 micro-tiling（`m_step/k_step` 循环）

---

## 六、代码组织

```
RISC-V-CIM-Manycore-SST/
├── README.md                          # SST 项目说明
├── BUILD_LOCAL.md                     # 本地构建指南
├── configure.ac                       # Autoconf 配置（SST Elements 15.0.0）
├── Makefile.am                        # 顶层 Makefile
├── scripts/
│   ├── build_and_install_local.sh     # 一键构建安装
│   ├── env_local_install.sh           # 运行环境配置
│   └── prepare_local_build.sh         # 构建树准备
├── build/sst-elements/                # 本地构建树（gitignore）
├── install/                           # 本地安装前缀（gitignore）
│   ├── bin/                           # 可执行工具
│   ├── include/sst/elements/          # 头文件
│   └── lib/sst-elements-library/      # 共享库（.so）
└── src/
    ├── libltdl/                       # libtool 动态加载库
    └── sst/elements/
        ├── vanadis/        # RISC-V CPU (18 子目录, ~50 源文件)
        ├── golem/          # CIM 阵列 (8 子模块, ~15 源文件)
        │   ├── rocc/       #     RoCC 接口
        │   ├── array/      #     MVM 阵列
        │   ├── globalmemory/ #  全局内存+DMA
        │   ├── groupctrl/  #     分组控制
        │   ├── requestscheduler/ # 请求调度
        │   ├── workercmdproc/  #   命令处理器
        │   └── tests/      #     **核心测试区** (大量 Python/Bash/C++ 脚本)
        │       ├── configs/        # 配置文件
        │       ├── architecture/   # 架构构建器
        │       ├── fronted/        # 张量生成
        │       ├── small/          # RISC-V 测试应用
        │       ├── tools/          # 分析工具
        │       ├── stats/          # 统计模板
        │       └── verify/         # 验证脚本
        ├── merlin/         # Mesh NoC
        ├── memHierarchy/   # 存储层次
        ├── mercury/        # 多核应用框架 (hg)
        ├── ember/          # MPI 通信模式
        ├── ariel/          # Pin-tool 前端
        ├── mirror/         # 可编程流量生成器
        ├── prospero/       # Memory trace 回放
        ├── firefly/        # MPI 仿真
        └── ... (其他 20+ 元素)
```

---

## 七、当前研发状态与方向

### 7.1 当前状态（来自 `tests/cmd.md`）

**已完成的工程修复**:
- 参数解耦：`ARRAY_INPUT_SIZE` / `ARRAY_OUTPUT_SIZE` / `NUM_ARRAYS` 已从旧 `DIM` 参数独立
- Builder 语义统一：`num_cu = array_output_size`, `runtime input size = block_k`
- WCP 2-slot 残留 bug 修复（`buffers_[2] → buffers_[4]`）
- 脚本可靠性改进（trap 杀掉 sst 进程树、NoC heatmap 可选）

**已知未完成的关键任务**:
- WCP 内部 **micro-tiling** 尚未实现——仍将逻辑 Block 当作 Hardware Tile 直接执行
- `block_m / block_k` 的整数倍自由化尚未落地
- 数据布局依赖编译期 `constexpr`，运行时参数化受限于编译边界

### 7.2 推荐推进方向
1. 在 WCP 中实现真正的 micro-tiling：`for m_step` × `for k_step` 循环
2. 放宽整数倍检查（`block_m % hw_output_size == 0`）
3. 每步小改动并回归验证（`Simulation is complete` + `VERIFY-C = PASS`）

### 7.3 已知不推荐的方向
- 直接实现乱序计算（已试过，导致 `VERIFY-C = FAIL`，根因是 overwrite/accumulate 语义与逻辑 k 顺序未正确绑定）
- 大规模修改 `globalmemory`（改动成本高，不是当前瓶颈）
- 盲目扫描 credit 参数（不是当前主要瓶颈）

---

## 八、依赖关系

| 依赖 | 说明 |
|------|------|
| SST Core v15.x | 仿真框架核心（`/data4/lishun/pkg/sst_install`） |
| DRAMSim3 | HBM 周期精确 DRAM 模型（`/data4/lishun/pkg/DRAMsim3`） |
| RISC-V GNU 工具链 | riscv64-unknown-elf-g++ 交叉编译器 |
| Python 3 | 配置生成、工具脚本、张量生成 |
| CrossSim (可选) | Sandia 模拟 MVM 阵列模拟器 |
| NumPy (可选) | CrossSim 集成所需的 Python 依赖 |
| MPI (可选) | Ariel MPI 前端仿真支持 |

---

## 九、总结

本项目是一个**面向 RISC-V 多核 + 模拟存算一体 (CIM) 阵列的周期精确全系统仿真平台**，基于 Sandia SST 框架构建。它的核心贡献在于：

1. **硬件建模**：通过 Golem 元素精确建模了模拟 MVM 阵列加速器，包括 RoCC 协处理器接口、DMA 数据搬运引擎、分组资源管理和 MVM 计算调度
2. **全系统仿真**：将 RISC-V 乱序 CPU (Vanadis)、Mesh NoC (Merlin)、HBM 内存 (DRAMSim3) 与 CIM 阵列集成，实现端到端的 GEMM 工作负载仿真
3. **性能分析**：提供精细的互斥 breakdown 分析（计算活跃 / 预取等待 / 写回等待 / 控制开销），揭示数据移动瓶颈是当前系统的主要限制因素
4. **研究平台**：为探索 GEMM 在 CIM 架构上的 micro-tiling 调度策略、数据布局优化、信用流控策略等提供了可配置、可扩展的实验环境

**当前最核心技术结论**：系统瓶颈不在控制面或事务边界，而在于 **Tile 虽然数据已就绪（ready），但由于严格的顺序消费策略，长期在队列中等待计算**。解决这个问题的关键是实现真正的 micro-tiling，将逻辑 Block 分解为多个 Hardware Tile 逐步累积计算。
