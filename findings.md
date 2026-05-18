# 发现与决策

## 需求

- 为 SST codegen 项目维护一个统一的规划和文档区域。
- 将实际代码修改保留在 `tilelang` 中。
- 让整个工作流适合 agent 驱动开发。
- 支持 WSL 和服务器两端的长期维护。

## 调研结论

- `tilelang` 和 `TileOPs` 是 `/data4/jjgong` 下的两个独立 Git 仓库。
- `/data4/jjgong` 本身是工作区根目录，不是 Git 仓库。
- 因此需要一个协调目录来跨仓库管理计划和记录。
- `tilelang` 根目录已经补充了 `AGENTS.md`，可作为源码仓库内的协作规范入口。
- `tilelang` 已经存在可复用的 C 代码生成路径，关键入口是 `target.build.tilelang_c` 和 `target.build.tilelang_c_host`。
- `tilelang` 的 `engine/lower.py` 已经会在 `target.kind.name == "c"` 时走 C 后端，所以首版最适合在这条路径上做 SST 识别和定制输出。
- `TileOPs` 主要是算子层和 manifest 层，首版不需要修改它。
- `TileOPs/tests/ops/test_gemm.py` 和相关 `gemm` 实现可以作为后续联调时的上层调用参考，但当前不作为第一阶段改动点。

## 技术决策

| 决策 | 原因 |
|------|------|
| 使用 `codegen_sstnoc` 作为项目中枢 | 将流程集中管理，同时不污染源码仓库 |
| 规划文件采用纯 Markdown | 方便人和 agent 直接读取、编辑和版本管理 |
| 代码修改只放在 `tilelang` 中 | 避免源码归属混乱 |
| 统一使用中文文档 | 降低后续维护和沟通成本 |
| 首版复用现有 `c` 后端再做 SST 识别 | 可以最快得到 C 代码输出，风险最低 |
| 首版不修改 `TileOPs` | 先把编译链路打通，避免把问题拆得太散 |
| SST target 采用“`c` + SST 标记”而非新 kind | 现有逻辑大量依赖 `target.kind.name == "c"`，复用旧通路更稳 |
| `TileOPs` 中 GEMM 用例作为后续联调参考 | 便于后续从真实上层调用验证 codegen 行为 |

## 遇到的问题

| 问题 | 解决方式 |
|------|----------|
| 还没有现成的项目中枢目录 | 新建 `codegen_sstnoc` 并创建基础协调文件 |
| `tilelang` 侧缺少统一协作说明 | 新增 `tilelang/AGENTS.md` 作为源码仓库协作规范 |

## 待确认事项

- SST 标记最终放在 `target.keys`、`tag` 还是其他自定义属性中。
- 自定义指令在 C 源码里应以宏、内联函数还是 `extern` 函数名承载。
- 首版的测试是只校验源码字符串，还是顺带校验生成流程能跑通。
- 后续联调优先选 `TileOPs` 中哪个 GEMM/算子样例作为 smoke test。

## 资源

- `/data4/jjgong/tilelang`
- `/data4/jjgong/TileOPs`

## 可视化/浏览器结论

- 暂无。
