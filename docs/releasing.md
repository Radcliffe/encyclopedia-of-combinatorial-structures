# Releasing `combstruct`

This checklist describes the intended release process for the `combstruct`
Python distribution. Publishing is deliberately separate from test CI:
the test workflow builds and validates artifacts but never uploads them.
The confirmed first-release choices and outcome are recorded in
[`release-readiness.md`](release-readiness.md). The current second-alpha
baseline audit is recorded in
[`release-readiness-0.1.0a1.md`](release-readiness-0.1.0a1.md).

## Established release choices

The maintainers confirmed these project-level choices for the first release on
2026-07-22:

- The PyPI distribution name is `combstruct`.
- The first pre-release version is `0.1.0a0`.
- The complete canonical catalogue remains bundled. Python code and the base
  ECS data are LGPL-2.1-only; OEIS-derived text and its adaptations are CC
  BY-SA 4.0. The package uses the SPDX expression
  `LGPL-2.1-only AND CC-BY-SA-4.0` and ships both license texts plus
  `NOTICE.md`.
- The `Radcliffe/encyclopedia-of-combinatorial-structures` GitHub repository is
  the canonical source repository.

The test workflow is stored in `.github/workflows` and runs in the canonical
GitHub repository. Confirm a successful remote run on the release commit rather
than assuming that local syntax validation is enough.

The `combstruct` project now exists on PyPI. PyPI release files are immutable,
so choose a new version, verify it in the exact artifacts, and do not rebuild
after validation.

Use a separate TestPyPI account when testing uploads. TestPyPI and PyPI have
separate user and project databases.

## Prepare the release

1. Start from a clean checkout of the intended release commit.
2. Update `project.version` in `pyproject.toml` and record the release in
   `CHANGELOG.md`.
3. Run the Python package and legacy test jobs on every supported Python
   version. The `Python package` workflow currently covers 3.12, 3.13, and
   3.14. Confirm that its Ruff formatting/lint and strict mypy checks pass as
   well, and that the remote runner completed successfully.
4. Create an isolated release environment and install the documented tools:

   ```console
   python3.12 -m venv .venv-release
   .venv-release/bin/python -m pip install --upgrade pip
   .venv-release/bin/python -m pip install ".[release]"
   ```

5. Build and validate both distributions:

   ```console
   .venv-release/bin/python -m build
   .venv-release/bin/python tests/check_artifacts.py \
     dist/combstruct-*.whl dist/combstruct-*.tar.gz
   .venv-release/bin/python -m twine check dist/*
   .venv-release/bin/check-wheel-contents dist/combstruct-*.whl
   ```

6. Install the wheel in another empty environment and run
   `tests/test_distribution.py` from outside the checkout. Also run
   `combstruct --id 56 --terms 8 --plain` and confirm the output is:

   ```text
   0, 1, 1, 1, 2, 3, 6, 12
   ```

Inspect the final filenames, metadata, and hashes. Upload exactly the files
that passed these checks; do not rebuild between validation and publication.

## TestPyPI

Test the publishing path before a production release when release tooling or
metadata has changed:

```console
.venv-release/bin/python -m twine upload --repository testpypi dist/*
```

Install that version into a fresh environment using TestPyPI and repeat the
installed-distribution and command-line smoke tests. TestPyPI may periodically
remove projects and accounts, so it is a process check rather than permanent
release storage.

## PyPI

For regular releases, prefer a dedicated Trusted Publishing workflow with a
protected `pypi` environment and manual approval. Configure it only after the
PyPI project, GitHub repository owner, workflow filename, and environment name
are confirmed. Keep publishing permissions in that dedicated workflow; the
existing test workflow must remain read-only.

For a manual upload, use a project-scoped API token and never store it in the
repository or shell history:

```console
.venv-release/bin/python -m twine upload dist/*
```

After publication, install from PyPI in a clean environment, rerun the smoke
tests, create the matching signed version-control tag, and attach the validated
artifacts and checksums to the release notes.

Official references:

- [Python Packaging User Guide: Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [Python Packaging User Guide: Using TestPyPI](https://packaging.python.org/en/latest/guides/using-testpypi/)
- [PyPI: Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
