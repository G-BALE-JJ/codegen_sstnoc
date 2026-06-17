# 协作工作流

## 基本原则

- 规划、原型实现、示例和测试优先写在 `codegen_sstnoc`。
- 当前实现主线是 `All frontends -> CIM-TileIR -> Golem SST backend exporter`。
- `tilelang/` 只在需要正式接入 TileLang pass pipeline 时修改。
- `RISC-V-CIM-Manycore-SST/` 默认只读，除非明确要求修改硬件仓库。
- 任何重要设计变化都要写入 `task_plan.md` / `findings.md`，长期边界变化再补 ADR。
- 每次会话结束前更新 `progress.md`。

## 推荐顺序

1. 先看 `task_plan.md`。
2. 再看 `findings.md`。
3. 当前 Golem 后端路线看 `docs/golem-runtime-codegen-roadmap.md`。
4. 当前 CIM-TileIR 原型能力看 `docs/cim-tileir-prototype-summary.md`。
5. 历史路线只看 `docs/legacy/`，不要按 legacy 文档安排当前实现。
6. 在 `tilelang_cim/`、`examples/`、`scripts/` 和 `tests/` 中修改当前原型。
7. 跑 `TILELANG_CACHE_DIR=/tmp/tilelang-cache python -m pytest tests -q` 和 `bash scripts/check_docs.sh`。
8. 回来更新 `progress.md`。
