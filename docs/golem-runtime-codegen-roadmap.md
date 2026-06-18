# CIM-TileIR 到 Golem SST 后端导出路线

## 目标

`codegen_noc` 的最终产物不是一个独立硬件建模器，也不是先生成 RISC-V ELF。当前主线是把 `CIM-TileIR` 定义为唯一前后端解耦接口：

```text
所有前端语言
  TileLang / TileOPs / 未来其他 DSL / 手写 JSON
        ↓
统一 lowering / extraction
        ↓
CIM-TileIR
        ↓
Golem SST backend exporter
        ↓
Golem SST env、contract JSON 和 artifact 目录
        ↓
驱动 RISC-V-CIM-Manycore-SST 的 run_noc_dma_pipeline.sh
```

核心诉求是把前端编程语言与 SST 脚本参数解耦：所有前端只负责生成 `CIM-TileIR`，所有硬件后端只负责消费 `CIM-TileIR` 并生成自己的加载环境。TileLang 只是第一个前端，Golem SST 只是第一个硬件后端。

## 为什么不把 Architecture Spec Adapter 放在第一步

早期规划把下一步写成 `GolemArchitectureSpec adapter`。这个方向适合做 architecture-aware planner、cycle estimate 或多硬件后端建模，但它不是当前最短闭环。

对当前目标而言，硬件参数的第一职责不是成为用户可见的架构模型，而是成为 exporter 的后端约束：

```text
CIM-TileIR 表达的参数能不能填进当前 Golem SST 后端？
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
- `tilelang_cim/golem_exporter.py`：从 `CIM-TileIR` 导出 Golem SST env/contract artifacts。
- `tilelang_cim/golem_constraints.py`：校验 `CIM-TileIR` 是否能落到当前 Golem SST 后端。
- `tilelang_cim/golem_event_planner.py`：生成 Golem runtime 映射解释/debug plan。
- `examples/run_tilelang_golem_e2e.sh`：一条命令执行 TileLang -> `CIM-TileIR` -> Golem artifacts -> validators -> SST smoke -> optional report。
- `scripts/validate_golem_artifacts.py`：离线校验 exporter 产物自洽性。
- `scripts/check_golem_mapping_consistency.py`：离线校验 resolved contract 与 Golem mapping/debug plan 一致性。

`RISC-V-CIM-Manycore-SST` 已有：

- `run_noc_dma_pipeline.sh`：Golem SST 主运行脚本。
- `tools/gen_hbm_init.py`：根据 env/contract 生成 HBM 初始化文件。
- `artifacts/contracts/matmul_env_mapping_v1.json`：env 字段映射样例。
- `artifacts/contracts/matmul_op_desc_resolved.json`：resolved matmul op contract 样例。
- `small/mvm_noc_int_array/golem_matmul_runtime.h`：`golem_matmul_op_desc_t` 定义。
- `small/mvm_noc_int_array/pipeline_config.h`：runtime 编译期参数和布局映射。

## 当前阶段结论

硬件默认 `run_noc_dma_pipeline.sh` 已经可以运行后，当前项目不应继续停留在 dry-run 或离线检查阶段。下一步是执行并记录一次 codegen-driven hardware integration smoke：

```text
CIM-TileIR JSON
  -> Golem SST exporter artifacts
  -> artifact validator
  -> Golem mapping consistency checker
  -> examples/run_golem_sst_smoke.sh --execute
  -> 真实 RISC-V-CIM-Manycore-SST run_noc_dma_pipeline.sh
```

该阶段要证明的是：不是硬件默认配置能跑，而是 `codegen_sstnoc` 生成的 `golem_sst.env` 和 contracts 能真实驱动 SST pipeline，并得到 `Simulation is complete`、`VERIFY-C = PASS` 和 stats CSV。

当前明确不做 sweep、自动调参、多 run 聚合或预测模型。single-run SST stats report 放在 codegen-driven hardware integration smoke 通过之后。

## 临时目录约定

Golem SST smoke 会生成 GB 级 HBM mmap backing files。当前不应再把 artifact root 放在根分区 `/tmp`，否则在空间不足时可能在 `memHierarchy::Backend::BackingMMAP` 初始化阶段触发 `Bus error`。

当前约定：

```text
临时根目录: /data4/jjgong/tmp/codegen_sstnoc
默认 artifact root: /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts
TileLang cache: /data4/jjgong/tmp/tilelang-cache
```

`examples/run_golem_sst_smoke.sh` 不传 `--artifact-root` 时默认使用上述 artifact root。历史文档或日志中出现的 `/tmp/golem_codegen_artifacts` 只代表旧记录，不再作为推荐运行路径。

如果遇到以下栈：

```text
Signal: Bus error (7)
SST::MemHierarchy::Backend::BackingMMAP
```

优先检查 artifact root 所在文件系统可用空间，以及 `hbm_init_node*.bin` / `hbm_out_node*.bin` 是否落在 `/tmp`。

## 前后端边界

`CIM-TileIR` 必须保存后端需要的计算语义，但不能绑定具体 SST 脚本变量名。

`CIM-TileIR` 应表达：

- kernel 类型，例如 `gemm`
- A/B/C tensor shape
- A/B/C dtype
- A/B/C layout
- tile shape：`BM/BN/BK`
- transpose flags：`transpose_a` / `transpose_b`
- 必要的 mapping/dataflow hint

`CIM-TileIR` 不应表达：

- `GOLEM_MATMUL_M`
- `GOLEM_GEMM_BLOCK_M`
- `GOLEM_ARRAY_INPUT_SIZE`
- `run_noc_dma_pipeline.sh`
- HBM artifact 路径

这些都属于 Golem SST backend exporter。

## 已完成：CIM-TileIR 到 Golem SST artifact exporter

已完成一个 `CIM-TileIR -> Golem SST artifacts` 导出器。它不是架构 spec adapter，也不是 TileLang 到 Golem 的直连导出器。

已实现模块：

```text
tilelang_cim/golem_exporter.py
```

已实现 CLI：

```text
examples/export_golem_sst.py
```

核心 API 的输入必须是 `CIM-TileIR dict`。CLI 可以支持两类入口：

1. `CIM-TileIR JSON`：直接导出后端 contract。
2. TileLang 源码文件：先走现有 TileLang frontend 生成 `CIM-TileIR`，再调用同一个 Golem backend exporter。

内部流程必须保持：

```text
TileLang source
  -> extract_gemm_ir_from_source()
  -> CIM-TileIR
  -> export_golem_sst_artifacts()
```

禁止把 TileLang AST/TIR 直接写成 `GOLEM_*` 环境变量。

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
export GOLEM_ARRAY_INPUT_SIZE=64
export GOLEM_ARRAY_OUTPUT_SIZE=64
export GOLEM_NUM_ARRAYS=64

export GOLEM_MATMUL_M=1024
export GOLEM_MATMUL_N=1024
export GOLEM_MATMUL_K=128
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

导出器在写文件前会对 `CIM-TileIR` 做 Golem SST 后端约束校验。这个校验层可以读取一份后端配置，也可以首版使用显式 CLI 参数或默认值。

已实现模块：

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

## 已完成：exporter 验收

基础验收命令：

```bash
# 从 CIM-TileIR JSON 导出，这是后端 exporter 的主入口
python examples/export_golem_sst.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts

# 从 TileLang 源码导出，这是便利入口，内部仍先转 CIM-TileIR
python examples/export_golem_sst.py \
  tests/fixtures/tilelang_gemm_fixture.py \
  --input-format tilelang-source \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --dtype fp32
```

预期输出：

```text
/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts/golem_sst.env
/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts/contracts/matmul_env_mapping_v1.json
/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts/contracts/matmul_op_desc_resolved.json
```

文档和单元测试：

```bash
TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q
bash scripts/check_docs.sh
```

## 已完成：硬件侧解耦静态审计

在硬件脚本暂时不能稳定执行的阶段，验收目标曾经改为：确认硬件仓库已经把前端参数入口解耦成 env/contract 形式，使 `CIM-TileIR -> Golem SST backend exporter` 的输出可以被硬件侧消费。

静态审计命令：

```bash
python scripts/check_golem_hardware_contracts.py \
  --hardware-tests-dir /data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests
```

该检查覆盖以下硬件侧解耦点：

| 解耦点 | 硬件侧位置 | 作用 |
|--------|------------|------|
| 外部 artifact root | `run_noc_dma_pipeline.sh` 的 `GOLEM_ARTIFACT_ROOT` | 允许 codegen 输出目录独立于硬件仓库 |
| matmul env contract | `GOLEM_MATMUL_M/N/K`、`GOLEM_MATMUL_BLOCK_*`、`GOLEM_MATMUL_DTYPE`、layout、transpose | 将矩阵语义从脚本内部默认值中解耦 |
| legacy GEMM env alias | `GOLEM_GEMM_*` 与 `GOLEM_MATMUL_*` 的互通 | 兼容现有脚本和 runtime 编译宏 |
| resolved contract | `contracts/matmul_op_desc_resolved.json` | 保存已经解析后的 matmul 参数 |
| env mapping contract | `contracts/matmul_env_mapping_v1.json` | 固化 contract 字段到 env 变量的映射 |
| HBM generator contract reader/writer | `tools/gen_hbm_init.py` | 根据 env/contract 生成 HBM layout，并写出 contract |
| runtime env reader | `small/mvm_noc_int_array/test_noc_dma.cpp` | runtime 启动时读取 `GOLEM_MATMUL_*` |
| compile-time fallback macros | `pipeline_config.h` | 保留硬件默认宏，同时允许脚本注入覆盖 |

exporter 导出文件仍可用于硬件侧 dry-run 检查：

```bash
python examples/gemm_ir.py \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --m 1024 --n 1024 --k 128 \
  --bm 64 --bn 64 --bk 64 \
  --mesh-w 4 --mesh-h 5 \
  --pipeline-stages 1 \
  --a-dtype fp32 --b-dtype fp32 --c-dtype fp32

python examples/export_golem_sst.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts

bash examples/run_golem_sst_smoke.sh \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  -- \
  --log codegen_smoke.log
```

`examples/run_golem_sst_smoke.sh` 默认追加 `--dry-run`，用于确认 `golem_sst.env`、`GOLEM_ARTIFACT_ROOT` 和 contracts 能被硬件脚本消费。只有显式加 `--execute` 时才运行完整 SST：

```bash
bash examples/run_golem_sst_smoke.sh \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --execute \
  -- \
  --log codegen_smoke.log
```

运行环境边界：

- wrapper 只 source exporter 生成的 `golem_sst.env`，并导出 `GOLEM_ARTIFACT_ROOT`。
- wrapper 不把 `sst`、`riscv64-linux-musl-g++`、`LD_LIBRARY_PATH`、DRAMSim3 或 OpenMPI 路径写死到 codegen artifacts。
- 本地交互终端已经加载用户 `~/.bashrc` 时，直接运行 wrapper 即可。
- Codex、CI 或非交互 shell 不一定继承 `~/.bashrc`；这类场景使用 `--use-user-shell-env` 让 wrapper 通过交互 bash 重入：

```bash
bash examples/run_golem_sst_smoke.sh \
  --use-user-shell-env \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --execute \
  -- \
  --log codegen_smoke.log
```

第二阶段已经解决的工程边界：

1. `run_noc_dma_pipeline.sh` 可以通过 `GOLEM_ARTIFACT_ROOT` 消费外部 artifact root。
2. `contracts/matmul_op_desc_resolved.json` 由 exporter 生成，并可作为硬件侧 HBM 复用兼容检查的兜底 contract。
3. wrapper 位于 `examples/run_golem_sst_smoke.sh`，不直接修改硬件仓库主脚本。
4. wrapper 默认 dry-run，降低误触发长仿真的风险。
5. wrapper 会在调用硬件脚本前检查 `sst` 和 `riscv64-linux-musl-g++` 是否在当前环境中可见；缺失时提示使用当前硬件 shell 或 `--use-user-shell-env`。

该阶段验收标准：

- `scripts/check_golem_hardware_contracts.py` 通过。
- `scripts/validate_golem_artifacts.py` 通过。
- `TILELANG_CACHE_DIR=/data4/jjgong/tmp/tilelang-cache python -m pytest tests -q` 通过。
- `bash scripts/check_docs.sh` 通过。

硬件默认脚本可运行之后，完整 SST 运行不再只是可选后验验证；但这里要区分两件事：

- 硬件默认配置能运行：说明硬件环境可用。
- codegen artifacts 能运行：说明 `CIM-TileIR -> Golem SST exporter` 真实接入硬件加载环境。

当前要完成的是第二项。

## 已完成：Golem-aware task mapping/debug plan

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

当前 MVP 已实现：

- `tilelang_cim/golem_event_planner.py`
- `build_golem_event_plan(ir, golem_backend_config)`
- `examples/plan_golem_events.py`

示例命令：

```bash
python examples/plan_golem_events.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json
```

当前输出是 Golem 语义映射计划，不是 cycle model。它对齐 `pipeline_config.h` / `gen_hbm_init.py` 的 macro-task、worker core、data node、A/B packed-once base、C output slot 和 reuse offset 公式。

## 已完成：No-SST-execute offline validation

当 `run_noc_dma_pipeline.sh` 暂时不能稳定执行时，不应把真实 SST execute 作为 codegen 阶段阻塞项。当前应先验证 exporter 产物本身是否完整、自洽，并与硬件 contract 入口一致。

当前 MVP 已实现：

- `scripts/validate_golem_artifacts.py`
- `tests/test_validate_golem_artifacts.py`
- `scripts/check_golem_mapping_consistency.py`
- `tests/test_check_golem_mapping_consistency.py`

示例命令：

```bash
python scripts/validate_golem_artifacts.py \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --output /data4/jjgong/tmp/codegen_sstnoc/golem_artifact_validation.json

python examples/plan_golem_events.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json

python scripts/check_golem_mapping_consistency.py \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --event-plan /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/golem_mapping_consistency.json
```

检查内容：

- `golem_sst.env` 是否存在。
- `contracts/matmul_op_desc_resolved.json` 是否存在。
- `contracts/matmul_env_mapping_v1.json` 是否存在。
- `GOLEM_MATMUL_*` 是否与 resolved contract 一致。
- `GOLEM_ARRAY_INPUT_SIZE`、`GOLEM_ARRAY_OUTPUT_SIZE`、`GOLEM_NUM_ARRAYS` 是否与 block shape 一致。
- legacy `GOLEM_GEMM_*` alias 是否与 `GOLEM_MATMUL_*` 一致。
- resolved contract 与 Golem task mapping/debug plan 的 tile counts 是否一致。
- event plan 的 task count 是否等于 `m_tiles * n_tiles`。
- worker core、worker slot、data node、macro task id 是否在合法范围。
- A/B/C base address 是否存在，事件地址引用是否与 task base address 一致。

## 当前阶段：codegen-driven hardware integration smoke

硬件默认 `run_noc_dma_pipeline.sh` 可以运行后，下一步必须证明 codegen 生成的 artifacts 也能驱动真实 SST pipeline，而不是只验证硬件默认配置。

推荐手动验收流程：

```bash
python examples/gemm_ir.py \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --m 1024 --n 1024 --k 1024 \
  --bm 64 --bn 64 --bk 64 \
  --mesh-w 4 --mesh-h 5 \
  --pipeline-stages 1 \
  --a-dtype fp32 --b-dtype fp32 --c-dtype fp32

python examples/export_golem_sst.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --input-format cim-tileir-json \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts

python scripts/validate_golem_artifacts.py \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --output /data4/jjgong/tmp/codegen_sstnoc/golem_artifact_validation.json

python examples/plan_golem_events.py \
  /data4/jjgong/tmp/codegen_sstnoc/gemm.golem.cimtile.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json

python scripts/check_golem_mapping_consistency.py \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --event-plan /data4/jjgong/tmp/codegen_sstnoc/gemm.golem_event_plan.json \
  --output /data4/jjgong/tmp/codegen_sstnoc/golem_mapping_consistency.json

bash examples/run_golem_sst_smoke.sh \
  --artifact-root /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts \
  --execute \
  -- \
  --log codegen_smoke.log
```

验收标准：

- `Simulation is complete`
- `VERIFY-C = PASS`
- 生成 `execution_summary.csv`
- 生成 `dma_summary.csv`
- 生成 `noc_summary.csv`
- 生成 `memory_summary.csv`
- 记录本次 run 的 log path 和 stats-dir

该阶段不放入 pytest，因为完整 SST run 时间长且依赖硬件环境。

完成该阶段后，需要把以下信息记录到 `progress.md`：

- `CIM-TileIR JSON` 路径。
- `artifact-root` 路径。
- artifact validation report 路径和 `ok` 状态。
- mapping consistency report 路径和 `ok` 状态。
- 硬件 log 路径。
- stats-dir 路径。
- `Simulation is complete` / `VERIFY-C = PASS` 的验证结果。

## 已完成首版：single-run SST stats report

当 codegen-driven hardware integration smoke 通过后，读取单次 SST stats 并生成结构化 report：

- `execution_summary.csv`
- `dma_summary.csv`
- `noc_summary.csv`
- `memory_summary.csv`
- `memory_queue_summary.csv`
- `submit_ready_causal_summary.csv`

首版 report 输出 `mode=golem_single_run_stats_report` 和 `model.status=not_calibrated`，只做单次运行的观测值汇总与派生指标，不做预测模型。它是当前项目的性能报告 MVP：输入来自真实 SST run 的 stats CSV 和 log，输出结构化 JSON，用于回答一次 codegen 生成配置在 SST 上跑出来的延迟、利用率、等待占比和主要瓶颈。

当前 MVP 已实现：

- `scripts/build_golem_single_run_report.py`
- `tests/test_build_golem_single_run_report.py`

示例命令：

```bash
RUN_ROOT=/data4/jjgong/tmp/codegen_sstnoc/full_smoke_20260617_173346

python scripts/build_golem_single_run_report.py \
  --artifact-root "$RUN_ROOT/golem_codegen_artifacts" \
  --event-plan "$RUN_ROOT/gemm.golem_event_plan.json" \
  --stats-dir "$RUN_ROOT/golem_codegen_artifacts/stats/overlap0/run_20260617_174010_1201356" \
  --log "$RUN_ROOT/golem_codegen_artifacts/logs/full_smoke_execute_terminal_run_20260617_174010_1201356.log" \
  --output "$RUN_ROOT/golem_single_run_report.json"
```

优先派生指标：

- `compute_active_pct`
- `prefetch_wait_pct`
- `writeback_wait_pct`
- `control_other_pct`
- `cycles_per_gemm_task`
- `cycles_per_macro_task`
- `system_vs_worker_utilization_gap_pct`

当前不做 sweep、自动调参、多 run 聚合或图表生成。sweep 需要稳定的 single-run report 作为基础，在没有明确参数优化目标前会提前放大运行成本和维护复杂度。

## 性能报告定位

项目最终会有性能报告，但分阶段实现：

1. 当前已完成：`golem_single_run_report.json`，面向单次真实 SST run，记录 correctness、mapping、stats、派生指标和 warning。
2. 下一步可做：从 JSON 生成 Markdown/HTML 可读报告，突出关键结论，例如仿真时间、总 cycles、array utilization、system utilization、compute/prefetch/writeback/control 占比、cycles per task 和 artifact 路径。
3. 当前不做：sweep、多 run 聚合、自动调参和性能预测模型。

因此当前性能报告不是“调参平台”，而是一次端到端编译/运行结果的结构化解释报告。

## 已完成首版：TileLang 到 Golem SST 一键端到端入口

当前已经有分步命令可以验证 `CIM-TileIR -> Golem SST`，但用户最终需要的是从 TileLang 前端语言到 SST 执行的端到端流程。新增入口：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py
```

默认 dry-run，会在 `/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_<timestamp>` 下生成：

- `tilelang_gemm.cimtile.json`
- `golem_codegen_artifacts/golem_sst.env`
- `golem_codegen_artifacts/contracts/matmul_op_desc_resolved.json`
- `golem_codegen_artifacts/contracts/matmul_env_mapping_v1.json`
- `gemm.golem_event_plan.json`
- `golem_artifact_validation.json`
- `golem_mapping_consistency.json`

真实执行时：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --tilelang-source tests/fixtures/tilelang_gemm_fixture.py \
  --use-user-shell-env \
  --execute
```

`--execute` 成功后，脚本会自动选择 artifact root 下最新 stats run 和最新 SST log，输出 `golem_single_run_report.json`。该入口仍遵守前后端边界：TileLang 只负责被解析到 `CIM-TileIR`，Golem SST backend exporter 才负责填充 `GOLEM_*` 和 contracts。

## 已完成：参数化 TileLang GEMM 源码入口

为了避免每次实验都手写或修改 TileLang fixture，新增源码生成器：

```bash
python examples/make_tilelang_gemm_source.py \
  --m 1024 --n 1024 --k 128 \
  --bm 64 --bn 64 --bk 64 \
  --dtype float32 \
  --num-stages 2 \
  --threads 128 \
  --output /data4/jjgong/tmp/codegen_sstnoc/generated_tilelang_gemm.py
```

默认参数与当前已通过真实 SST 的 smoke 规格一致：

```text
M=1024, N=1024, K=128
BM=64, BN=64, BK=64
dtype=float32
num_stages=2
threads=128
```

更推荐通过一键 E2E 入口直接生成并执行后续流程：

```bash
bash examples/run_tilelang_golem_e2e.sh \
  --generate-tilelang-source \
  --m 1024 --n 1024 --k 128 \
  --bm 64 --bn 64 --bk 64 \
  --dtype float32 \
  --num-stages 2
```

`--generate-tilelang-source` 会把源码写入 `$RUN_ROOT/generated_tilelang_gemm.py`。后续流程仍然是：

```text
generated TileLang source
  -> extract_tilelang_gemm.py
  -> CIM-TileIR JSON
  -> export_golem_sst.py
  -> Golem SST artifacts
  -> validators / mapping checker / smoke wrapper
```

这一步的意义是补齐“前端语言参数化输入”的最小实验入口，而不是把参数直接写入 Golem env。`GOLEM_*` 仍只由 Golem SST backend exporter 生成。

真实执行成功记录：

```text
run_root=/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_20260617_193443
single_run_report=/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_20260617_193443/golem_single_run_report.json
SST log=/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_20260617_193443/golem_codegen_artifacts/logs/tilelang_golem_smoke_run_20260617_193443_1637879.log
stats_dir=/data4/jjgong/tmp/codegen_sstnoc/tilelang_golem_e2e_20260617_193443/golem_codegen_artifacts/stats/overlap0/run_20260617_193443_1637879
Simulation is complete, simulated time: 234.589 us
[VERIFY-C] PASS dtype=fp32 sampled=1024 mismatches=0
report.status=ok
```

## 不推荐立即做的事情

- 不建议把 `GolemArchitectureSpec` 作为第一阶段主产物。它会把问题带回硬件建模，而不是解决前端到 SST 参数填充。
- 不建议直接生成 RoCC inline assembly 或 RISC-V ELF。当前最短闭环是复用已有 Golem runtime 和 `run_noc_dma_pipeline.sh`。
- 不建议先做复杂 TileLang pass 集成。现有 extractor 足够支撑第一版参数导出器。
- 不建议在 micro-tiling 未完成前放宽 `block_m/block_k` 为硬件 tile 的整数倍。
- 不建议当前做 sweep。先完成 codegen-driven hardware smoke 和 single-run stats report。

## 当前执行顺序

1. 已完成：补齐 `CIM-TileIR` 作为统一前后端接口所需的 layout / transpose 字段。
2. 已完成：`CIM-TileIR -> Golem SST env/contract exporter`。
3. 已完成：Golem 后端约束校验。
4. 已完成：`run_noc_dma_pipeline.sh` 参数注入 dry-run smoke。
5. 已完成：Golem-aware task mapping/debug plan。
6. 已完成：No-SST-execute offline validation。
7. 已完成：codegen-driven hardware integration smoke。
8. 已完成首版：single-run SST stats report。
9. 已完成首版：TileLang 到 Golem SST 一键端到端入口。
10. 已完成：参数化 TileLang GEMM 源码生成与 E2E 参数入口。
11. 当前暂缓：真实 TileOPs 复杂模式、Markdown/HTML 报告和 sweep。
12. 长期目标：runtime ABI / ELF 闭环。
