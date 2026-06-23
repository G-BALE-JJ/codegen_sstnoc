#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_TILELANG_SOURCE="$REPO_ROOT/tests/fixtures/tileops_like_matmul_softmax_fixture.py"
DEFAULT_RUN_ROOT_BASE="/data4/jjgong/tmp/codegen_sstnoc"
DEFAULT_HARDWARE_TESTS_DIR="/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests"
DEFAULT_TILELANG_CACHE_DIR="/data4/jjgong/tmp/tilelang-cache"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TILELANG_SOURCE="$DEFAULT_TILELANG_SOURCE"
RUN_ROOT="$DEFAULT_RUN_ROOT_BASE/tilelang_softmax_golem_e2e_$TIMESTAMP"
HARDWARE_TESTS_DIR="$DEFAULT_HARDWARE_TESTS_DIR"
EXECUTE=0
USE_USER_SHELL_ENV=0
LOG_NAME="tilelang_softmax_golem_smoke.log"
MESH_W=1
MESH_H=1
PYTHON_BIN="${PYTHON:-python3}"
export TILELANG_CACHE_DIR="${TILELANG_CACHE_DIR:-$DEFAULT_TILELANG_CACHE_DIR}"

show_help() {
	cat <<EOF
Usage:
  examples/run_tilelang_softmax_golem_e2e.sh [options]

Options:
  --tilelang-source FILE   TileOps-like matmul->softmax Python source file.
                            Default: $DEFAULT_TILELANG_SOURCE
  --run-root DIR           Per-run output directory.
                            Default: $DEFAULT_RUN_ROOT_BASE/tilelang_softmax_golem_e2e_<timestamp>
  --hardware-tests-dir DIR Directory containing small/mvm_noc_softmax_cpu/.
                            Default: $DEFAULT_HARDWARE_TESTS_DIR
  --execute                Run real SST through run_noc_dma_softmax_pipeline.sh.
                            Default is dry-run only.
  --use-user-shell-env     Forward to run_golem_softmax_sst_smoke.sh so ~/.bashrc
                            can populate SST runtime environment.
  --log NAME               Hardware pipeline log name. Default: tilelang_softmax_golem_smoke.log
  --mesh-w N               CIM-TileIR mesh width. Default: $MESH_W
  --mesh-h N               CIM-TileIR mesh height. Default: $MESH_H
  -h, --help               Show this help.

Pipeline:
  TileOps-like matmul->softmax source -> CIM-TileIR graph -> Golem graph artifacts
  -> graph artifact validator -> run_golem_softmax_sst_smoke.sh.
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--tilelang-source)
			TILELANG_SOURCE="$2"; shift 2 ;;
		--run-root)
			RUN_ROOT="$2"; shift 2 ;;
		--hardware-tests-dir)
			HARDWARE_TESTS_DIR="$2"; shift 2 ;;
		--execute)
			EXECUTE=1; shift ;;
		--use-user-shell-env)
			USE_USER_SHELL_ENV=1; shift ;;
		--log)
			LOG_NAME="$2"; shift 2 ;;
		--mesh-w)
			MESH_W="$2"; shift 2 ;;
		--mesh-h)
			MESH_H="$2"; shift 2 ;;
		-h|--help)
			show_help; exit 0 ;;
		*)
			echo "[ERROR] Unknown option: $1" >&2
			show_help >&2
			exit 1 ;;
	esac
done

mkdir -p "$RUN_ROOT"
RUN_ROOT="$(cd "$RUN_ROOT" && pwd)"
ARTIFACT_ROOT="$RUN_ROOT/golem_softmax_artifacts"
CIM_TILEIR="$RUN_ROOT/tilelang_matmul_softmax.cimtile.json"
VALIDATION_REPORT="$RUN_ROOT/golem_softmax_artifact_validation.json"

if [[ ! -f "$TILELANG_SOURCE" ]]; then
	echo "[ERROR] Missing TileLang softmax source: $TILELANG_SOURCE" >&2
	exit 1
fi

echo "[1/4] Extracting TileOps-like matmul->softmax source to CIM-TileIR graph..."
"$PYTHON_BIN" "$REPO_ROOT/examples/extract_tilelang_matmul_softmax.py" \
	"$TILELANG_SOURCE" \
	--output "$CIM_TILEIR" \
	--mesh-w "$MESH_W" \
	--mesh-h "$MESH_H"

echo "[2/4] Exporting CIM-TileIR graph to Golem SST artifacts..."
"$PYTHON_BIN" "$REPO_ROOT/examples/export_golem_sst.py" \
	"$CIM_TILEIR" \
	--input-format cim-tileir-json \
	--artifact-root "$ARTIFACT_ROOT"

echo "[3/4] Validating Golem graph artifacts..."
"$PYTHON_BIN" "$REPO_ROOT/scripts/validate_golem_artifacts.py" \
	--artifact-root "$ARTIFACT_ROOT" \
	--hardware-tests-dir "$HARDWARE_TESTS_DIR" \
	--output "$VALIDATION_REPORT"

SMOKE_ARGS=(
	"$REPO_ROOT/examples/run_golem_softmax_sst_smoke.sh"
	--artifact-root "$ARTIFACT_ROOT"
	--hardware-tests-dir "$HARDWARE_TESTS_DIR"
)
if [[ "$USE_USER_SHELL_ENV" -eq 1 ]]; then
	SMOKE_ARGS+=(--use-user-shell-env)
fi
if [[ "$EXECUTE" -eq 1 ]]; then
	SMOKE_ARGS+=(--execute)
fi

echo "[4/4] Running Golem softmax SST smoke wrapper..."
bash "${SMOKE_ARGS[@]}" -- --log "$LOG_NAME"

echo "run_root: $RUN_ROOT"
echo "cim_tileir: $CIM_TILEIR"
echo "artifact_root: $ARTIFACT_ROOT"
echo "validation_report: $VALIDATION_REPORT"
