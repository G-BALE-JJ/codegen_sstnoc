#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_HARDWARE_TESTS_DIR="/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests"
DEFAULT_ARTIFACT_ROOT="/data4/jjgong/tmp/codegen_sstnoc/golem_softmax_artifacts"

ARTIFACT_ROOT="$DEFAULT_ARTIFACT_ROOT"
HARDWARE_TESTS_DIR="$DEFAULT_HARDWARE_TESTS_DIR"
EXECUTE=0
USE_USER_SHELL_ENV=0
SOFTMAX_REFERENCE="probability"
PIPELINE_ARGS=()
ORIGINAL_ARGS=("$@")

show_help() {
	cat <<'EOF'
Usage:
  examples/run_golem_softmax_sst_smoke.sh --artifact-root DIR [options] [-- pipeline args...]

Options:
  --artifact-root DIR       Directory containing golem_sst.env and graph contracts/.
                            Default: /data4/jjgong/tmp/codegen_sstnoc/golem_softmax_artifacts
  --hardware-tests-dir DIR  Directory containing small/mvm_noc_softmax_cpu/.
  --softmax-reference NAME  Softmax checker reference mode passed to the hardware
                            wrapper. Default: probability.
  --execute                 Run the full SST pipeline. Default is dry-run.
  --use-user-shell-env      Re-exec through an interactive bash shell so ~/.bashrc
                            can populate SST runtime environment.
  -h, --help                Show this help.

This wrapper is for Stage 10B graph smoke only. It requires graph artifacts from
the matmul -> softmax(cpu_fallback) exporter and invokes the hardware-side
small/mvm_noc_softmax_cpu/run_noc_dma_softmax_pipeline.sh wrapper with
--verify-softmax enabled.

The default topology is the current single-N-tile smoke configuration:
groups=1, num-cores=1, gemm-cores=1, num-mem-nodes=2, mesh-dim-x=1.
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--artifact-root)
			ARTIFACT_ROOT="$2"; shift 2 ;;
		--hardware-tests-dir)
			HARDWARE_TESTS_DIR="$2"; shift 2 ;;
		--softmax-reference)
			SOFTMAX_REFERENCE="$2"; shift 2 ;;
		--execute)
			EXECUTE=1; shift ;;
		--use-user-shell-env)
			USE_USER_SHELL_ENV=1; shift ;;
		--)
			shift
			PIPELINE_ARGS+=("$@")
			break ;;
		-h|--help)
			show_help; exit 0 ;;
		*)
			echo "[ERROR] Unknown option: $1" >&2
			show_help >&2
			exit 1 ;;
	esac
done

if [[ "$USE_USER_SHELL_ENV" -eq 1 && "${GOLEM_SOFTMAX_SMOKE_ENV_BOOTSTRAPPED:-0}" != "1" ]]; then
	export GOLEM_SOFTMAX_SMOKE_ENV_BOOTSTRAPPED=1
	USER_SHELL_BASH="${GOLEM_SMOKE_BASH:-bash}"
	exec "$USER_SHELL_BASH" -i -c 'exec bash "$@"' bash "$0" "${ORIGINAL_ARGS[@]}"
fi

if [[ -d "$ARTIFACT_ROOT" ]]; then
	ARTIFACT_ROOT="$(cd "$ARTIFACT_ROOT" && pwd)"
fi
if [[ -d "$HARDWARE_TESTS_DIR" ]]; then
	HARDWARE_TESTS_DIR="$(cd "$HARDWARE_TESTS_DIR" && pwd)"
fi

ENV_FILE="$ARTIFACT_ROOT/golem_sst.env"
MATMUL_CONTRACT="$ARTIFACT_ROOT/contracts/matmul_op_desc_resolved.json"
GRAPH_SEQUENCE="$ARTIFACT_ROOT/contracts/graph_sequence_v1.json"
SOFTMAX_CONTRACT="$ARTIFACT_ROOT/contracts/softmax_op_desc_resolved.json"
GRAPH_ENV_MAPPING="$ARTIFACT_ROOT/contracts/graph_env_mapping_v1.json"
PIPELINE_SCRIPT="$HARDWARE_TESTS_DIR/small/mvm_noc_softmax_cpu/run_noc_dma_softmax_pipeline.sh"
VALIDATOR="$REPO_ROOT/scripts/validate_golem_artifacts.py"

if [[ ! -f "$ENV_FILE" ]]; then
	echo "[ERROR] Missing Golem SST env file: $ENV_FILE" >&2
	echo "        Generate it with examples/matmul_softmax_ir.py and examples/export_golem_sst.py first." >&2
	exit 1
fi

for required_graph_artifact in "$MATMUL_CONTRACT" "$GRAPH_SEQUENCE" "$SOFTMAX_CONTRACT" "$GRAPH_ENV_MAPPING"; do
	if [[ ! -f "$required_graph_artifact" ]]; then
		echo "[ERROR] Missing Golem softmax graph artifact: $required_graph_artifact" >&2
		echo "        Stage 10B requires matmul -> softmax graph artifacts, not GEMM-only artifacts." >&2
		exit 1
	fi
done

if [[ ! -x "$PIPELINE_SCRIPT" ]]; then
	echo "[ERROR] Missing executable hardware softmax pipeline script: $PIPELINE_SCRIPT" >&2
	exit 1
fi

python3 "$VALIDATOR" --artifact-root "$ARTIFACT_ROOT" --hardware-tests-dir "$HARDWARE_TESTS_DIR" >/dev/null

# shellcheck source=/dev/null
source "$ENV_FILE"
export GOLEM_ARTIFACT_ROOT="$ARTIFACT_ROOT"

required_env=(
	GOLEM_ARRAY_INPUT_SIZE
	GOLEM_ARRAY_OUTPUT_SIZE
	GOLEM_NUM_ARRAYS
	GOLEM_GEMM_M
	GOLEM_GEMM_N
	GOLEM_GEMM_K
	GOLEM_GEMM_BLOCK_M
	GOLEM_GEMM_BLOCK_N
	GOLEM_GEMM_BLOCK_K
	GOLEM_SOFTMAX_ENABLE
	GOLEM_SOFTMAX_BACKEND
	GOLEM_SOFTMAX_SCOPE
)
missing_env=()
for env_key in "${required_env[@]}"; do
	if [[ -z "${!env_key:-}" ]]; then
		missing_env+=("$env_key")
	fi
done
if [[ "${#missing_env[@]}" -ne 0 ]]; then
	echo "[ERROR] Missing required Golem softmax env key(s): ${missing_env[*]}" >&2
	exit 1
fi

if [[ "$GOLEM_SOFTMAX_ENABLE" != "1" || "$GOLEM_SOFTMAX_BACKEND" != "riscv_cpu_fallback" ]]; then
	echo "[ERROR] Unsupported softmax graph backend: enable=$GOLEM_SOFTMAX_ENABLE backend=$GOLEM_SOFTMAX_BACKEND" >&2
	echo "        Stage 10B supports only matmul -> softmax(cpu_fallback)." >&2
	exit 1
fi

softmax_args=(
	--groups 1
	--num-cores 1
	--gemm-cores 1
	--num-mem-nodes 2
	--mesh-dim-x 1
	--num-arrays "$GOLEM_NUM_ARRAYS"
	--array-in "$GOLEM_ARRAY_INPUT_SIZE"
	--array-out "$GOLEM_ARRAY_OUTPUT_SIZE"
	--gemm-m "$GOLEM_GEMM_M"
	--gemm-n "$GOLEM_GEMM_N"
	--gemm-k "$GOLEM_GEMM_K"
	--gemm-block-m "$GOLEM_GEMM_BLOCK_M"
	--gemm-block-n "$GOLEM_GEMM_BLOCK_N"
	--gemm-block-k "$GOLEM_GEMM_BLOCK_K"
	--group-manager-enable 0
	--ctrl-link-enable 0
	--verify-softmax
	--softmax-reference "$SOFTMAX_REFERENCE"
)

if [[ "$EXECUTE" -eq 0 ]]; then
	softmax_args+=(--dry-run)
fi

cd "$HARDWARE_TESTS_DIR"
exec "$PIPELINE_SCRIPT" "${softmax_args[@]}" "${PIPELINE_ARGS[@]}"
