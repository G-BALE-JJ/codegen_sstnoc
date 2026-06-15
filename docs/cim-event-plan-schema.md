# CIM event plan schema

`event plan` 是 `CIM-TileIR` 的下游消费形态。当前有两种模式：

| mode | 入口 | 说明 |
|------|------|------|
| `event_plan` | `build_event_plan(ir)` | 无 architecture spec 的 abstract event skeleton，`estimated_cycles=0` |
| `arch_event_plan` | `build_arch_event_plan(ir, arch_spec)` | 有 architecture spec 的 toy architecture-aware event plan |

## abstract event plan

无 `--arch` 时 CLI 输出 abstract event plan：

```bash
python examples/plan_events.py gemm.cimtile.json --output gemm.eventplan.json
```

顶层字段：

| 字段 | 说明 |
|------|------|
| `kernel` | 当前只支持 `gemm` |
| `source_target` | 来源 IR 的 target |
| `mode` | `event_plan` |
| `mesh` | mesh 宽高 |
| `tile` | `BM/BN/BK` |
| `tasks` | per-output-tile task 列表 |
| `stats` | 静态统计 |

`stats.estimated_cycles` 固定为 0，不代表真实硬件周期。

## architecture-aware event plan

提供 `--arch` 时 CLI 输出 architecture-aware event plan：

```bash
python examples/plan_events.py \
  gemm.cimtile.json \
  --arch examples/architecture/toy_cim_mesh_v0.json \
  --output gemm.eventplan.json
```

新增顶层字段：

| 字段 | 说明 |
|------|------|
| `architecture` | architecture spec 名称 |
| `cycle_model` | 当前为 `serial_formula_v0` |
| `core_cycles` | 每个 active core 的累计 cycles |

`stats` 新增字段：

| 字段 | 说明 |
|------|------|
| `cycle_model` | cycle model 名称 |
| `estimated_task_cycles_sum` | 所有 task cycles 之和 |
| `estimated_max_core_cycles` | 最忙 core 的 cycles |
| `estimated_cycles` | 当前等于 `estimated_max_core_cycles` |

## task

每个 task 表示一个 output tile：

| 字段 | 说明 |
|------|------|
| `task_id` | 例如 `tile_by0_bx0` |
| `output_tile` | `{bx, by}` |
| `core` | `{x, y, id}` |
| `cycles` | 仅 `arch_event_plan` 中存在 |
| `events` | 事件列表 |

## events

当前事件顺序固定为：

```text
clear_acc
for each ko:
  dma_load A
  dma_load B
  cim_gemm
dma_store C
```

`arch_event_plan` 中每个事件带 `cycles` 字段。`event_plan` 中事件不带 cycle。

## serial_formula_v0

单次 DMA：

```text
dma_cycles = startup_cycles + ceil(bytes / bytes_per_cycle)
```

单次 CIM GEMM：

```text
cim_gemm_cycles = cycles_per_cim_gemm
```

单 task：

```text
task_cycles =
  clear_acc_cycles
  + sum_k(dma_load_A_cycles + dma_load_B_cycles + cim_gemm_cycles)
  + dma_store_C_cycles
```

全局：

```text
estimated_cycles = max(sum(task_cycles assigned to each core))
```

## 当前边界

- `serial_formula_v0` 是 toy 模型。
- 不建模 overlap、NoC contention、barrier、bank conflict 或真实 runtime 调度。
- 当 output tile 数大于 core 数时，当前按 row-major wrap-around 把多个 task 累加到同一个 core。
