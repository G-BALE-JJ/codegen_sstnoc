#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_TILELANG_SOURCE="$REPO_ROOT/tests/fixtures/tilelang_gemm_fixture.py"
DEFAULT_RUN_ROOT_BASE="/data4/jjgong/tmp/codegen_sstnoc"
DEFAULT_HARDWARE_TESTS_DIR="/data4/jjgong/RISC-V-CIM-Manycore-SST/build/sst-elements/src/sst/elements/golem/tests"
DEFAULT_TILELANG_CACHE_DIR="/data4/jjgong/tmp/tilelang-cache"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TILELANG_SOURCE="$DEFAULT_TILELANG_SOURCE"
RUN_ROOT="$DEFAULT_RUN_ROOT_BASE/tilelang_golem_e2e_$TIMESTAMP"
HARDWARE_TESTS_DIR="$DEFAULT_HARDWARE_TESTS_DIR"
EXECUTE=0
USE_USER_SHELL_ENV=0
GENERATE_TILELANG_SOURCE=0
FRONTEND_MODE="source"
LOG_NAME="tilelang_golem_smoke.log"
MESH_W=4
MESH_H=5
GEMM_M=1024
GEMM_N=1024
GEMM_K=128
GEMM_BM=64
GEMM_BN=64
GEMM_BK=64
GEMM_DTYPE="float32"
GEMM_NUM_STAGES=2
GEMM_THREADS=128
PYTHON_BIN="${PYTHON:-python3}"
export TILELANG_CACHE_DIR="${TILELANG_CACHE_DIR:-$DEFAULT_TILELANG_CACHE_DIR}"

show_help() {
	cat <<EOF
Usage:
  examples/run_tilelang_golem_e2e.sh [options]

Options:
  --tilelang-source FILE   TileLang Python source file.
                            Default: $DEFAULT_TILELANG_SOURCE
  --generate-tilelang-source
                           Generate TileLang GEMM source under run root instead
                           of reading --tilelang-source.
  --frontend-mode MODE     Frontend extraction mode: source or tir.
                            source reads TileLang source text directly.
                            tir loads a TileLang PrimFunc and extracts from TIR.
                            Default: $FRONTEND_MODE
  --m N                    Generated GEMM M. Default: $GEMM_M
  --n N                    Generated GEMM N. Default: $GEMM_N
  --k N                    Generated GEMM K. Default: $GEMM_K
  --bm N                   Generated tile BM. Default: $GEMM_BM
  --bn N                   Generated tile BN. Default: $GEMM_BN
  --bk N                   Generated tile BK. Default: $GEMM_BK
  --dtype DTYPE            Generated tensor dtype. Default: $GEMM_DTYPE
  --num-stages N           Generated T.Pipelined num_stages. Default: $GEMM_NUM_STAGES
  --threads N              Generated T.Kernel threads. Default: $GEMM_THREADS
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
  TileLang source/TIR -> CIM-TileIR -> Golem SST artifacts -> validators
  -> Golem mapping plan -> run_golem_sst_smoke.sh -> optional single-run report.
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--tilelang-source)
			TILELANG_SOURCE="$2"; shift 2 ;;
		--generate-tilelang-source)
			GENERATE_TILELANG_SOURCE=1; shift ;;
		--frontend-mode)
			FRONTEND_MODE="$2"; shift 2 ;;
		--m)
			GEMM_M="$2"; shift 2 ;;
		--n)
			GEMM_N="$2"; shift 2 ;;
		--k)
			GEMM_K="$2"; shift 2 ;;
		--bm)
			GEMM_BM="$2"; shift 2 ;;
		--bn)
			GEMM_BN="$2"; shift 2 ;;
		--bk)
			GEMM_BK="$2"; shift 2 ;;
		--dtype)
			GEMM_DTYPE="$2"; shift 2 ;;
		--num-stages)
			GEMM_NUM_STAGES="$2"; shift 2 ;;
		--threads)
			GEMM_THREADS="$2"; shift 2 ;;
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

case "$FRONTEND_MODE" in
	source|tir) ;;
	*)
		echo "[ERROR] --frontend-mode must be source or tir, got: $FRONTEND_MODE" >&2
		exit 1 ;;
esac

mkdir -p "$RUN_ROOT"
RUN_ROOT="$(cd "$RUN_ROOT" && pwd)"
ARTIFACT_ROOT="$RUN_ROOT/golem_codegen_artifacts"
CIM_TILEIR="$RUN_ROOT/tilelang_gemm.cimtile.json"
EVENT_PLAN="$RUN_ROOT/gemm.golem_event_plan.json"
VALIDATION_REPORT="$RUN_ROOT/golem_artifact_validation.json"
MAPPING_REPORT="$RUN_ROOT/golem_mapping_consistency.json"
SINGLE_RUN_REPORT="$RUN_ROOT/golem_single_run_report.json"

if [[ "$GENERATE_TILELANG_SOURCE" -eq 1 ]]; then
	TILELANG_SOURCE="$RUN_ROOT/generated_tilelang_gemm.py"
	echo "[0/6] Generating TileLang GEMM source..."
	"$PYTHON_BIN" "$REPO_ROOT/examples/make_tilelang_gemm_source.py" \
		--m "$GEMM_M" \
		--n "$GEMM_N" \
		--k "$GEMM_K" \
		--bm "$GEMM_BM" \
		--bn "$GEMM_BN" \
		--bk "$GEMM_BK" \
		--dtype "$GEMM_DTYPE" \
		--num-stages "$GEMM_NUM_STAGES" \
		--threads "$GEMM_THREADS" \
		--output "$TILELANG_SOURCE"
fi

if [[ ! -f "$TILELANG_SOURCE" ]]; then
	echo "[ERROR] Missing TileLang source: $TILELANG_SOURCE" >&2
	exit 1
fi

if [[ "$FRONTEND_MODE" == "tir" ]]; then
	echo "[1/6] Extracting TileLang TIR PrimFunc to CIM-TileIR..."
	"$PYTHON_BIN" "$REPO_ROOT/examples/extract_tilelang_tir_gemm.py" \
		"$TILELANG_SOURCE" \
		--output "$CIM_TILEIR" \
		--mesh-w "$MESH_W" \
		--mesh-h "$MESH_H"
else
	echo "[1/6] Extracting TileLang source to CIM-TileIR..."
	"$PYTHON_BIN" "$REPO_ROOT/examples/extract_tilelang_gemm.py" \
		"$TILELANG_SOURCE" \
		--output "$CIM_TILEIR" \
		--mesh-w "$MESH_W" \
		--mesh-h "$MESH_H"
fi

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
