#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_TILELANG_SOURCE="$REPO_ROOT/tests/fixtures/tilelang_gemm_fixture.py"
DEFAULT_RUN_ROOT_BASE="/data4/jjgong/tmp/codegen_sstnoc"
DEFAULT_HARDWARE_TESTS_DIR="/data4/jjgong/RISC-V-CIM-Manycore-SST/build/sst-elements/src/sst/elements/golem/tests"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TILELANG_SOURCE="$DEFAULT_TILELANG_SOURCE"
RUN_ROOT="$DEFAULT_RUN_ROOT_BASE/tilelang_golem_e2e_$TIMESTAMP"
HARDWARE_TESTS_DIR="$DEFAULT_HARDWARE_TESTS_DIR"
EXECUTE=0
USE_USER_SHELL_ENV=0
LOG_NAME="tilelang_golem_smoke.log"
MESH_W=4
MESH_H=5
PYTHON_BIN="${PYTHON:-python3}"

show_help() {
	cat <<EOF
Usage:
  examples/run_tilelang_golem_e2e.sh [options]

Options:
  --tilelang-source FILE   TileLang Python source file.
                            Default: $DEFAULT_TILELANG_SOURCE
  --run-root DIR           Per-run output directory.
                            Default: $DEFAULT_RUN_ROOT_BASE/tilelang_golem_e2e_<timestamp>
  --hardware-tests-dir DIR Directory containing run_noc_dma_pipeline.sh.
                            Default: $DEFAULT_HARDWARE_TESTS_DIR
  --execute                Run real SST through run_noc_dma_pipeline.sh.
                            Default is dry-run only.
  --use-user-shell-env     Forward to run_golem_sst_smoke.sh so ~/.bashrc can
                            populate SST/toolchain runtime environment.
  --log NAME               Hardware pipeline log name. Default: tilelang_golem_smoke.log
  --mesh-w N               CIM-TileIR mesh width. Default: 4
  --mesh-h N               CIM-TileIR mesh height. Default: 5
  -h, --help               Show this help.

Pipeline:
  TileLang source -> CIM-TileIR -> Golem SST artifacts -> validators
  -> Golem mapping plan -> run_golem_sst_smoke.sh -> optional single-run report.
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

if [[ ! -f "$TILELANG_SOURCE" ]]; then
	echo "[ERROR] Missing TileLang source: $TILELANG_SOURCE" >&2
	exit 1
fi

mkdir -p "$RUN_ROOT"
RUN_ROOT="$(cd "$RUN_ROOT" && pwd)"
ARTIFACT_ROOT="$RUN_ROOT/golem_codegen_artifacts"
CIM_TILEIR="$RUN_ROOT/tilelang_gemm.cimtile.json"
EVENT_PLAN="$RUN_ROOT/gemm.golem_event_plan.json"
VALIDATION_REPORT="$RUN_ROOT/golem_artifact_validation.json"
MAPPING_REPORT="$RUN_ROOT/golem_mapping_consistency.json"
SINGLE_RUN_REPORT="$RUN_ROOT/golem_single_run_report.json"

echo "[1/6] Extracting TileLang source to CIM-TileIR..."
"$PYTHON_BIN" "$REPO_ROOT/examples/extract_tilelang_gemm.py" \
	"$TILELANG_SOURCE" \
	--output "$CIM_TILEIR" \
	--mesh-w "$MESH_W" \
	--mesh-h "$MESH_H"

echo "[2/6] Exporting CIM-TileIR to Golem SST artifacts..."
"$PYTHON_BIN" "$REPO_ROOT/examples/export_golem_sst.py" \
	"$CIM_TILEIR" \
	--input-format cim-tileir-json \
	--artifact-root "$ARTIFACT_ROOT"

echo "[3/6] Validating Golem SST artifacts..."
"$PYTHON_BIN" "$REPO_ROOT/scripts/validate_golem_artifacts.py" \
	--artifact-root "$ARTIFACT_ROOT" \
	--hardware-tests-dir "$HARDWARE_TESTS_DIR" \
	--output "$VALIDATION_REPORT"

echo "[4/6] Building and checking Golem mapping plan..."
"$PYTHON_BIN" "$REPO_ROOT/examples/plan_golem_events.py" \
	"$CIM_TILEIR" \
	--output "$EVENT_PLAN"
"$PYTHON_BIN" "$REPO_ROOT/scripts/check_golem_mapping_consistency.py" \
	--artifact-root "$ARTIFACT_ROOT" \
	--event-plan "$EVENT_PLAN" \
	--output "$MAPPING_REPORT"

SMOKE_ARGS=(
	"$REPO_ROOT/examples/run_golem_sst_smoke.sh"
	--artifact-root "$ARTIFACT_ROOT"
	--hardware-tests-dir "$HARDWARE_TESTS_DIR"
)
if [[ "$USE_USER_SHELL_ENV" -eq 1 ]]; then
	SMOKE_ARGS+=(--use-user-shell-env)
fi
if [[ "$EXECUTE" -eq 1 ]]; then
	SMOKE_ARGS+=(--execute)
fi

echo "[5/6] Running Golem SST smoke wrapper..."
bash "${SMOKE_ARGS[@]}" -- --log "$LOG_NAME"

if [[ "$EXECUTE" -eq 1 ]]; then
	STATS_DIR="$(find "$ARTIFACT_ROOT/stats" -name execution_summary.csv -printf '%T@ %h\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)"
	LOG_PATH="$(find "$ARTIFACT_ROOT/logs" -type f -name '*.log' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)"
	if [[ -z "$STATS_DIR" ]]; then
		echo "[ERROR] Cannot find execution_summary.csv under $ARTIFACT_ROOT/stats" >&2
		exit 1
	fi
	if [[ -z "$LOG_PATH" ]]; then
		echo "[ERROR] Cannot find SST log under $ARTIFACT_ROOT/logs" >&2
		exit 1
	fi

	echo "[6/6] Building single-run report..."
	"$PYTHON_BIN" "$REPO_ROOT/scripts/build_golem_single_run_report.py" \
		--artifact-root "$ARTIFACT_ROOT" \
		--event-plan "$EVENT_PLAN" \
		--stats-dir "$STATS_DIR" \
		--log "$LOG_PATH" \
		--output "$SINGLE_RUN_REPORT"
else
	echo "[6/6] Dry-run complete; single-run report is skipped because --execute was not set."
fi

echo "run_root: $RUN_ROOT"
echo "cim_tileir: $CIM_TILEIR"
echo "artifact_root: $ARTIFACT_ROOT"
echo "event_plan: $EVENT_PLAN"
echo "validation_report: $VALIDATION_REPORT"
echo "mapping_report: $MAPPING_REPORT"
if [[ "$EXECUTE" -eq 1 ]]; then
	echo "single_run_report: $SINGLE_RUN_REPORT"
fi
