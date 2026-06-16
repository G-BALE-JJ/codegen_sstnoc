# TileLang 到 Golem SST 参数导出路线

## 目标

`codegen_noc` 的最终产物不是一个独立硬件建模器，也不是先生成 RISC-V ELF。当前主线是：

```text
TileLang 源码 / TileLang PrimFunc
        ↓
解析 GEMM / tile / dtype / layout 参数
        ↓
形成稳定的 MatmulOpDesc / CIM-TileIR 参数层
        ↓
导出 Golem SST 运行需要的 env、contract JSON 和 artifact 目录
        ↓
驱动 RISC-V-CIM-Manycore-SST 的 run_noc_dma_pipeline.sh
```

核心诉求是把前端编程语言与 SST 脚本参数解耦：用户写 TileLang，codegen 负责把参数落到 Golem SST 后端环境和脚本中。

## 为什么不把 Architecture Spec Adapter 放在第一步

早期规划把下一步写成 `GolemArchitectureSpec adapter`。这个方向适合做 architecture-aware planner、cycle estimate 或多硬件后端建模，但它不是当前最短闭环。

对当前目标而言，硬件参数的第一职责不是成为用户可见的架构模型，而是成为 exporter 的后端约束：

```text
TileLang 解析出的参数能不能填进当前 Golem SST 后端？
如果不能，应该报出什么明确错误？
如果能，应该生成哪些 GOLEM_* 环境变量和 contract 文件？
```

因此，`GolemArchitectureSpec` 如果保留，应降级为 `golem_constraints` 或 `backend_constraints`，服务于参数校验，而不是作为第一阶段主产物。

## 当前已有基础

`codegen_sstnoc` 已有：

- `tilelang_cim/extractor.py`：从窄模板 TileLang GEMM 源码或 `PrimFunc.script()` 提取 GEMM 参数。
- `tilelang_cim/builder.py`：构造 `CIM-TileIR` GEMM 子集。
- `tilelang_cim/checker.py`：校验 `CIM-TileIR`。
- `examples/extract_tilelang_gemm.py`：从 TileLang fixture 导出 `CIM-TileIR JSON`。

`RISC-V-CIM-Manycore-SST` 已有：

- `run_noc_dma_pipeline.sh`：Golem SST 主运行脚本。
- `tools/gen_hbm_init.py`：根据 env/contract 生成 HBM 初始化文件。
- `artifacts/contracts/matmul_env_mapping_v1.json`：env 字段映射样例。
- `artifacts/contracts/matmul_op_desc_resolved.json`：resolved matmul op contract 样例。
- `small/mvm_noc_int_array/golem_matmul_runtime.h`：`golem_matmul_op_desc_t` 定义。
- `small/mvm_noc_int_array/pipeline_config.h`：runtime 编译期参数和布局映射。

## 第一阶段主产物

第一阶段应新增一个 Golem SST 参数导出器，而不是架构 spec adapter。

建议模块：

```text
tilelang_cim/golem_exporter.py
```

建议 CLI：

```text
examples/export_golem_sst.py
```

输入可以支持两类：

1. TileLang 源码文件：先走现有 extractor。
2. `CIM-TileIR JSON`：跳过前端解析，直接导出后端 contract。

输出目录结构：

```text
<artifact-root>/
  golem_sst.env
  contracts/
    matmul_env_mapping_v1.json
    matmul_op_desc_resolved.json
```

`golem_sst.env` 首版输出：

```bash
export GOLEM_MATMUL_M=4096
export GOLEM_MATMUL_N=128
export GOLEM_MATMUL_K=4096
export GOLEM_MATMUL_BLOCK_M=64
export GOLEM_MATMUL_BLOCK_N=64
export GOLEM_MATMUL_BLOCK_K=64
export GOLEM_MATMUL_DTYPE=fp32
export GOLEM_MATMUL_LAYOUT=row_major
export GOLEM_MATMUL_TRANSPOSE_A=0
export GOLEM_MATMUL_TRANSPOSE_B=0

export GOLEM_GEMM_M="$GOLEM_MATMUL_M"
export GOLEM_GEMM_N="$GOLEM_MATMUL_N"
export GOLEM_GEMM_K="$GOLEM_MATMUL_K"
export GOLEM_GEMM_BLOCK_M="$GOLEM_MATMUL_BLOCK_M"
export GOLEM_GEMM_BLOCK_N="$GOLEM_MATMUL_BLOCK_N"
export GOLEM_GEMM_BLOCK_K="$GOLEM_MATMUL_BLOCK_K"
```

`matmul_op_desc_resolved.json` 首版输出：

```json
{
  "m": 4096,
  "n": 128,
  "k": 4096,
  "block_m": 64,
  "block_n": 64,
  "block_k": 64,
  "dtype": "fp32",
  "layout": "row_major",
  "transpose_a": 0,
  "transpose_b": 0
}
```

`matmul_env_mapping_v1.json` 首版输出：

```json
{
  "m": "GOLEM_MATMUL_M",
  "n": "GOLEM_MATMUL_N",
  "k": "GOLEM_MATMUL_K",
  "block_m": "GOLEM_MATMUL_BLOCK_M",
  "block_n": "GOLEM_MATMUL_BLOCK_N",
  "block_k": "GOLEM_MATMUL_BLOCK_K",
  "dtype": "GOLEM_MATMUL_DTYPE",
  "layout": "GOLEM_MATMUL_LAYOUT",
  "transpose_a": "GOLEM_MATMUL_TRANSPOSE_A",
  "transpose_b": "GOLEM_MATMUL_TRANSPOSE_B"
}
```

## 后端约束校验

导出器必须在写文件前做 Golem SST 后端约束校验。这个校验层可以读取一份后端配置，也可以首版使用显式 CLI 参数或默认值。

建议模块：

```text
tilelang_cim/golem_constraints.py
```

首版校验规则：

| 规则 | 原因 |
|------|------|
| `dtype in {"int32", "fp32"}` | Golem runtime 当前支持 int32/fp32 路径 |
| `layout == "row_major"` | `gen_hbm_init.py` phase-1 仅支持 row-major |
| `transpose_a == 0` 且 `transpose_b == 0` | 当前 Golem matmul contract 不支持转置 |
| `M % block_m == 0` | 当前 HBM layout 和 runtime 假设整 tile |
| `N % block_n == 0` | 当前 HBM layout 和 runtime 假设整 tile |
| `K % block_k == 0` | 当前 K tile 循环假设整除 |
| `block_k == GOLEM_ARRAY_INPUT_SIZE` | 当前 hardware tile 直接执行路径要求 BK 匹配 MVM input size |
| `block_m == GOLEM_ARRAY_OUTPUT_SIZE` | 当前 hardware tile 直接执行路径要求 BM 匹配 MVM output size |
| `block_n <= GOLEM_NUM_ARRAYS` | N 列映射到 array id，不能超过 array 数 |

注意：`block_m` / `block_k` 的整数倍放宽应等硬件侧 WCP micro-tiling 完成后再做。当前 exporter 应拒绝这些 shape，避免生成 SST runtime 不能可靠执行的配置。

## 第一阶段验收

建议命令：

```bash
python examples/export_golem_sst.py \
  tests/fixtures/tilelang_gemm_fixture.py \
  --artifact-root /tmp/golem_codegen_artifacts \
  --dtype fp32
```

预期输出：

```text
/tmp/golem_codegen_artifacts/golem_sst.env
/tmp/golem_codegen_artifacts/contracts/matmul_env_mapping_v1.json
/tmp/golem_codegen_artifacts/contracts/matmul_op_desc_resolved.json
```

文档和单元测试：

```bash
TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q
bash scripts/check_docs.sh
```

## 第二阶段：SST 脚本注入 smoke

第一阶段导出文件可直接用于硬件侧脚本：

```bash
cd /data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests
source /tmp/golem_codegen_artifacts/golem_sst.env
GOLEM_ARTIFACT_ROOT=/tmp/golem_codegen_artifacts \
bash run_noc_dma_pipeline.sh
```

第二阶段需要解决两个工程问题：

1. `run_noc_dma_pipeline.sh` 是否允许外部 artifact root 下已有 contracts 被复用。
2. 是否需要新增一个轻量 wrapper，例如 `examples/run_golem_sst_smoke.sh`，避免直接修改硬件仓库主脚本。

验收标准：

- `Simulation is complete`
- `VERIFY-C = PASS`
- `contracts/matmul_op_desc_resolved.json` 与 exporter 输出一致
- `stats/execution_summary.csv` 可解析

## 第三阶段：Golem-aware task/event plan

只有当 env/contract export 和脚本注入闭环稳定后，才需要做 Golem-aware planner。

这一阶段的目标不是取代 exporter，而是给调试和性能解释提供结构化计划：

- `macro_task_id`
- `m_group/n_group`
- `worker_slot`
- `worker_core`
- `group_id`
- `data_node_idx`
- `task_slot_in_node`
- `a_base_mm`
- `b_pack_base_mm`
- `c_base_mm`
- `reuse_offset`

事件也应从 toy `dma_load A/B + cim_gemm` 改成 Golem runtime 语义：

- `remote_load_a_panel`
- `remote_load_b_vector_pack`
- `gm2imat`
- `gm2ivec_batch`
- `tile_mvm_batch`
- `tile_wait_batch`
- `ovec2gm`
- `remote_store_c_tile`

## 第四阶段：stats-based 校准

当硬件 smoke 能稳定运行后，再用 SST stats 校准 event plan：

- `execution_summary.csv`
- `dma_summary.csv`
- `noc_summary.csv`
- `memory_summary.csv`

当前硬件总结显示主要瓶颈是 `ready -> compute_start` 队列等待，而不是纯 DMA 延迟。因此后续模型应优先解释 WCP slot、prefetch window、strict-order consumption、reuse window 对 compute_active / prefetch_wait / writeback_wait 的影响。

## 不推荐立即做的事情

- 不建议把 `GolemArchitectureSpec` 作为第一阶段主产物。它会把问题带回硬件建模，而不是解决前端到 SST 参数填充。
- 不建议直接生成 RoCC inline assembly 或 RISC-V ELF。当前最短闭环是复用已有 Golem runtime 和 `run_noc_dma_pipeline.sh`。
- 不建议先做复杂 TileLang pass 集成。现有 extractor 足够支撑第一版参数导出器。
- 不建议在 micro-tiling 未完成前放宽 `block_m/block_k` 为硬件 tile 的整数倍。

## 推荐阶段顺序

1. TileLang / CIM-TileIR 到 Golem SST env/contract exporter
2. Golem 后端约束校验
3. `run_noc_dma_pipeline.sh` 参数注入 smoke
4. Golem-aware task/event plan
5. stats-based 性能解释与校准
6. extractor / TileOPs-like 扩展
7. runtime ABI / ELF 长期闭环
