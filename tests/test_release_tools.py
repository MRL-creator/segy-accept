import subprocess
import sys
from pathlib import Path


def test_field_integrity_checks_remain_active_with_python_optimization():
    script = Path(__file__).resolve().parents[1] / "tools" / "validate_f3.py"
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            f"import runpy; m=runpy.run_path({str(script)!r}); m['inspect_independently'](b'x'*m['SIZE'])",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "fingerprint" in result.stderr
