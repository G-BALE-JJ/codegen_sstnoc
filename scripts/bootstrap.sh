#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "项目中枢目录：${ROOT_DIR}"
echo "建议检查以下文件："
echo "  - ${ROOT_DIR}/task_plan.md"
echo "  - ${ROOT_DIR}/findings.md"
echo "  - ${ROOT_DIR}/progress.md"
echo "  - ${ROOT_DIR}/docs/adr/"
