"""Install the built wheel with only runtime dependencies and exercise its demo."""

import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

root = Path(__file__).resolve().parents[1]
wheels = list((root / "dist").glob("segy_accept-*.whl"))
if len(wheels) != 1:
    raise ValueError("build exactly one release wheel before checking it")
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    environment = directory / "runtime"
    venv.EnvBuilder(with_pip=False).create(environment)
    executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [sys.executable, "-m", "pip", "--python", str(executable), "install", str(wheels[0])],
        check=True,
        cwd=directory,
    )
    subprocess.run(
        [
            str(executable),
            "-I",
            "-c",
            "from importlib.util import find_spec; assert find_spec('obspy') is None; assert find_spec('psutil') is None",
        ],
        check=True,
        cwd=directory,
    )
    subprocess.run(
        [str(executable), "-I", "-m", "segy_accept", "demo", str(directory / "demo")],
        check=True,
        cwd=directory,
    )
print("Built wheel verified outside the source tree with runtime dependencies only")
