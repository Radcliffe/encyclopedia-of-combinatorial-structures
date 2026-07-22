# Developing `combstruct`

The first package milestone extracts and stabilizes behavior already present
in `python-tools/compute_terms.py`. New symbolic capabilities belong in later,
separately designed milestones. Keeping that boundary explicit makes package
regressions distinguishable from future mathematics work.

## Environment

The package supports Python 3.12, 3.13, and 3.14 and has no runtime
dependencies outside the standard library. From the repository root, create
an isolated environment and install the quality and release tools:

```console
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[quality,release]'
```

The `quality` extra supplies Ruff and mypy. The `release` extra supplies the
standard build frontend, Twine metadata validation, and wheel-content
validation. Neither extra becomes a runtime dependency for users.

## Local checks

Run these commands before proposing a package change:

```console
.venv/bin/ruff check src/combstruct tests
.venv/bin/ruff format --check src/combstruct tests
.venv/bin/mypy
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
(cd python-tools && ../.venv/bin/python -m unittest discover -v)
```

The package test suite validates the recommended API, parser coverage for all
1,075 canonical specifications, catalogue conversion, and term computation.
The historical suite remains mandatory until the maintenance scripts are
migrated because it detects changes to the extracted evaluator's behavior.

The repository workflow repeats both suites on all supported Python versions.
A separate quality job runs strict static typing, lint, and formatting checks.
The distribution job runs only after both jobs succeed. The workflow is stored
under `.github/workflows`, so it runs on the GitHub mirror and is also a
Forgejo fallback workflow. Running it on Codeberg requires repository Actions
and a compatible runner to be configured by a maintainer.

## Public API discipline

The recommended public surface is `combstruct.__all__`, documented in
`docs/api.md`. Adding, removing, or changing a top-level name requires:

1. an intentional API decision;
2. documentation and a changelog entry;
3. source and installed-wheel tests; and
4. consideration of the pre-release version number.

The wider `combstruct.terms.__all__` surface mirrors the original term script
for the repository's transition. Do not promote its evaluator nodes or series
helpers to top-level imports merely because they remain available for
compatibility.

## Data changes

Canonical records live under `structures/`. Package builds map them into
`combstruct/data` without duplicating the 1,075 JSON files in the source tree.
If a record changes, run both the package catalogue tests and the existing
`python-tools` validation tests. Regenerate consolidated web data and b-files
only through their existing maintenance scripts; do not hand-edit generated
copies independently.

Data provenance and licensing are release concerns, not just documentation
details. Update `NOTICE.md` when a new source is introduced and preserve the
component boundaries and attribution recorded there.

## Distribution checks

Follow `docs/releasing.md` for the complete process. At minimum, build into a
clean output directory and validate the exact artifacts:

```console
.venv/bin/python -m build
.venv/bin/python tests/check_artifacts.py \
  dist/combstruct-*.whl dist/combstruct-*.tar.gz
.venv/bin/python -m twine check dist/*
.venv/bin/check-wheel-contents dist/combstruct-*.whl
```

Install the wheel into another empty environment and run
`tests/test_distribution.py` from a directory outside the checkout. This is
essential: source-tree tests alone can hide omitted package data, incorrect
entry points, or imports that accidentally resolve to local files.

Build artifacts, virtual environments, caches, and generated package metadata
must remain untracked. Publishing is a separate maintainer-approved action;
the test workflow is deliberately read-only.
