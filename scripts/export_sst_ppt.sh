#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC_DIR="${ROOT_DIR}/docs"

soffice --headless --convert-to pptx --outdir "${DOC_DIR}" "${DOC_DIR}/sst-codegen-tech-route.fodp"

echo "已导出：${DOC_DIR}/sst-codegen-tech-route.pptx"
