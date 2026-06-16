#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_HARDWARE_TESTS_DIR="/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests"

ARTIFACT_ROOT=""
HARDWARE_TESTS_DIR="$DEFAULT_HARDWARE_TESTS_DIR"
EXECUTE=0
PIPELINE_ARGS=()

show_help() {
	cat <<'EOF'
Usage:
  examples/run_golem_sst_smoke.sh --artifact-root DIR [options] [-- pipeline args...]

Options:
  --artifact-root DIR       Directory containing golem_sst.env and contracts/.
  --hardware-tests-dir DIR  Directory containing run_noc_dma_pipeline.sh.
  --execute                 Run the full SST pipeline. Default is dry-run.
  -h, --help                Show this help.

By default this wrapper appends --dry-run to the hardware script. Pass --execute
only when you intentionally want to run the long SST simulation.
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--artifact-root)
			ARTIFACT_ROOT="$2"; shift 2 ;;
		--hardware-tests-dir)
			HARDWARE_TESTS_DIR="$2"; shift 2 ;;
		--execute)
			EXECUTE=1; shift ;;
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

if [[ -z "$ARTIFACT_ROOT" ]]; then
	echo "[ERROR] --artifact-root is required" >&2
	exit 1
fi

if [[ -d "$ARTIFACT_ROOT" ]]; then
	ARTIFACT_ROOT="$(cd "$ARTIFACT_ROOT" && pwd)"
fi
ENV_FILE="$ARTIFACT_ROOT/golem_sst.env"
CONTRACT_FILE="$ARTIFACT_ROOT/contracts/matmul_op_desc_resolved.json"
PIPELINE_SCRIPT="$HARDWARE_TESTS_DIR/run_noc_dma_pipeline.sh"

if [[ ! -f "$ENV_FILE" ]]; then
	echo "[ERROR] Missing Golem SST env file: $ENV_FILE" >&2
	echo "        Generate it with examples/export_golem_sst.py first." >&2
	exit 1
fi

if [[ ! -f "$CONTRACT_FILE" ]]; then
	echo "[ERROR] Missing Golem SST resolved contract: $CONTRACT_FILE" >&2
	echo "        Generate it with examples/export_golem_sst.py first." >&2
	exit 1
fi

if [[ ! -x "$PIPELINE_SCRIPT" ]]; then
	echo "[ERROR] Missing executable hardware pipeline script: $PIPELINE_SCRIPT" >&2
	exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"
export GOLEM_ARTIFACT_ROOT="$ARTIFACT_ROOT"

cd "$HARDWARE_TESTS_DIR"
if [[ "$EXECUTE" -eq 0 ]]; then
	exec "$PIPELINE_SCRIPT" --dry-run "${PIPELINE_ARGS[@]}"
fi
exec "$PIPELINE_SCRIPT" "${PIPELINE_ARGS[@]}"
