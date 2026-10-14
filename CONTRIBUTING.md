# Contributing

Install a source checkout using Python 3.10+:

```sh
git clone https://github.com/MRL-creator/segy-accept.git
cd segy-accept
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install --upgrade "setuptools>=83"
python -m pip install -e ".[dev]" pip-audit
python -m pytest --cov=segy_accept --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m build
python tools/check_wheel.py
python -m pip_audit --skip-editable
```

Read [SPEC.md](SPEC.md) and [CONSTRAINTS.md](CONSTRAINTS.md). Keep patches small;
write a regression that fails before fixing a bug, and preserve explicit unknown
states, source immutability, and bounded evidence. Do not skip checks or widen the
profile to make a file pass. Include the commands and environment used to verify
your change. Public APIs and output-schema changes need corresponding docs.

For a bug report, include the tool/Python/segyio versions, expected and observed
outcome, rule IDs, and a minimal synthetic reproduction when possible. Never
upload confidential seismic data. Link a publicly licensed source rather than
attaching third-party data; identify its licence and provide a fingerprint.
The [practitioner packet](docs/practitioner-review.md) describes domain feedback
that would help evaluate usefulness. Feature proposals should explain the intended
receiving workflow and how acceptance can be independently tested.
