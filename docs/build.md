# Isolated wheel build

Running from the source checkout needs no build step. To build a wheel on macOS,
use Python 3.10+ and a separate virtual environment. `requirements-build.txt`
pins pip and setuptools and records the SHA-256 hashes of their PyPI wheels.
The setuptools version matches `pyproject.toml`.

From the repository root (choose a fresh scratch directory outside the checkout):

```bash
build_root=/tmp/trainer2875-build
python3 -m venv "$build_root/venv"
"$build_root/venv/bin/python" -m pip install --require-hashes --only-binary=:all: -r requirements-build.txt
SOURCE_DATE_EPOCH=1704067200 "$build_root/venv/bin/python" -m pip wheel --no-index --no-deps --no-build-isolation --no-cache-dir --wheel-dir "$build_root/dist" .
```

The virtual environment isolates the tooling. Hash checking rejects substituted
tool distributions; `--no-build-isolation` prevents pip from creating a second
environment with independently resolved tooling. The wheel step is offline.
`SOURCE_DATE_EPOCH` fixes ZIP entry timestamps; reproduce with the same source,
Python version, build-tool lock and epoch. The interpreter itself is not supplied
or locked by this repository.

The output is in the selected scratch directory. Setuptools may also create
ignored `build/` and `*.egg-info/` intermediates in the checkout. A normal isolated
PEP 517 build uses the exact backend version from `pyproject.toml`, but only the
workflow above enforces the committed distribution hashes.
