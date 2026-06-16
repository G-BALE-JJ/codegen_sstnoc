import subprocess
import sys


def test_check_golem_hardware_contracts_passes_for_local_hardware_repo():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_golem_hardware_contracts.py",
            "--hardware-tests-dir",
            "/data4/jjgong/RISC-V-CIM-Manycore-SST/src/sst/elements/golem/tests",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "GOLEM_ARTIFACT_ROOT external artifact root" in result.stdout
    assert "GOLEM_MATMUL_* environment contract" in result.stdout
    assert "golem runtime reads matmul env at runtime" in result.stdout
