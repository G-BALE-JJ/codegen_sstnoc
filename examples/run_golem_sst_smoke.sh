#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_HARDWARE_TESTS_DIR="/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests"
DEFAULT_ARTIFACT_ROOT="/data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts"

ARTIFACT_ROOT="$DEFAULT_ARTIFACT_ROOT"
HARDWARE_TESTS_DIR="$DEFAULT_HARDWARE_TESTS_DIR"
EXECUTE=0
USE_USER_SHELL_ENV=0
PIPELINE_ARGS=()
ORIGINAL_ARGS=("$@")

show_help() {
	cat <<'EOF'
Usage:
  examples/run_golem_sst_smoke.sh --artifact-root DIR [options] [-- pipeline args...]

Options:
  --artifact-root DIR       Directory containing golem_sst.env and contracts/.
                            Default: /data4/jjgong/tmp/codegen_sstnoc/golem_codegen_artifacts
  --hardware-tests-dir DIR  Directory containing run_noc_dma_pipeline.sh.
  --execute                 Run the full SST pipeline. Default is dry-run.
  --use-user-shell-env      Re-exec through an interactive bash shell so ~/.bashrc
                            can populate SST/toolchain runtime environment.
  -h, --help                Show this help.

By default this wrapper appends --dry-run to the hardware script. Pass --execute
only when you intentionally want to run the long SST simulation.

This wrapper does not hard-code SST, RISC-V toolchain, or LD_LIBRARY_PATH. Run it
from an environment where the hardware script already works, or pass
--use-user-shell-env for non-interactive launchers that do not inherit ~/.bashrc.
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

if [[ "$USE_USER_SHELL_ENV" -eq 1 && "${GOLEM_SMOKE_ENV_BOOTSTRAPPED:-0}" != "1" ]]; then
	export GOLEM_SMOKE_ENV_BOOTSTRAPPED=1
	USER_SHELL_BASH="${GOLEM_SMOKE_BASH:-bash}"
	exec "$USER_SHELL_BASH" -i -c 'exec bash "$@"' bash "$0" "${ORIGINAL_ARGS[@]}"
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

if [[ -n "${CONDA_PREFIX:-}" && -d "$CONDA_PREFIX/lib" ]]; then
	case ":${LD_LIBRARY_PATH:-}:" in
		*":$CONDA_PREFIX/lib:"*) ;;
		*) export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;;
	esac
fi

missing_tools=()
for required_tool in sst riscv64-linux-musl-g++; do
	if ! command -v "$required_tool" >/dev/null 2>&1; then
		missing_tools+=("$required_tool")
	fi
done

if [[ "${#missing_tools[@]}" -ne 0 ]]; then
	echo "[ERROR] Missing required runtime tool(s): ${missing_tools[*]}" >&2
	echo "        Run this wrapper from the same shell environment where the hardware script works," >&2
	echo "        or pass --use-user-shell-env so an interactive bash can load ~/.bashrc." >&2
	exit 1
fi

cd "$HARDWARE_TESTS_DIR"
if [[ "$EXECUTE" -eq 0 ]]; then
	exec "$PIPELINE_SCRIPT" --dry-run "${PIPELINE_ARGS[@]}"
fi
exec "$PIPELINE_SCRIPT" "${PIPELINE_ARGS[@]}"
