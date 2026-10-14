"""Install the built wheel with only runtime dependencies and exercise its demo."""

import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from segy_accept import __version__

root = Path(__file__).resolve().parents[1]
wheel = root / "dist" / f"segy_accept-{__version__}-py3-none-any.whl"
if not wheel.is_file():
    raise ValueError(f"build the current release wheel before checking it: {wheel.name}")
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    environment = directory / "runtime"
    venv.EnvBuilder(with_pip=False).create(environment)
    executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [sys.executable, "-m", "pip", "--python", str(executable), "install", str(wheel)],
        check=True,
        cwd=directory,
    )
    subprocess.run(
        [
            str(executable),
            "-I",
            "-c",
            "from importlib.util import find_spec\n"
            "from importlib.metadata import version\n"
            f"if version('segy-accept') != {__version__!r}: raise RuntimeError('wrong installed version')\n"
            "if any(find_spec(p) is not None for p in ['obspy','psutil']): raise RuntimeError('optional dependencies installed')",
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
