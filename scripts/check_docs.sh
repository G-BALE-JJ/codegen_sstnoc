#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for file in \
  "${ROOT_DIR}/README.md" \
  "${ROOT_DIR}/task_plan.md" \
  "${ROOT_DIR}/findings.md" \
  "${ROOT_DIR}/progress.md"
do
  if [[ ! -f "${file}" ]]; then
    echo "缺少文件：${file}"
    exit 1
  fi
done

echo "基础文档检查通过。"
