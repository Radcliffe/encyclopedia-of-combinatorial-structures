# `combstruct` 0.1.0a1 release-candidate audit

Audit date: 2026-07-22

This document records the evidence for preparing the second `combstruct`
pre-release. The maintainer confirmed version `0.1.0a1`; the exact artifacts
for publication must be built and validated once from the merged release
commit.

## Scope completed since 0.1.0a0

- All 1,028 stored ECS generating-function fields have a dedicated immutable
  syntax-tree representation and parser.
- Exact coefficients are available for 986 stored generating functions,
  including supported indexed sums and conservative implicit-equation cases.
- Finite generating functions are derived for 888 specifications, including
  50 recursive systems with rational or square-root closed forms.
- Every read-only `python-tools` consumer uses the public package API. The
  three source-data serializers and mutators intentionally retain raw JSON
  access because they create the catalogue consumed by the package.
- The canonical equations and sequence data for ECS 79 and ECS 91 have been
  corrected and covered by catalogue-wide regression tests.

The remaining unsupported generating-function and derivation forms are
documented explicitly in `PYTHON_PACKAGE.md` and `docs/api.md`; they are
capability boundaries rather than release blockers for this alpha.

## Local validation evidence

The following checks passed from the audited worktree on Python 3.12, 3.13,
and 3.14:

- 98 package tests on each version, with one expected skip;
- 25 maintenance-tool tests on each version;
- 28 tests against a freshly installed wheel on each version;
- both `combstruct` and `python -m combstruct` command forms, each returning
  `0, 1, 1, 1, 2, 3, 6, 12` for the ECS 56 smoke test; and
- `pip check` with no broken requirements on each version.

Ruff formatting and lint checks and strict mypy checks also passed. A Python
3.12 pre-merge candidate build produced both `0.1.0a1` distributions, and the
artifact contract checker, `twine check`, and `check-wheel-contents` all
passed. The wheel contained all 1,075 catalogue records and the required
licensing files.

Those pre-merge artifacts are disposable. Their hashes must not be reused as
release evidence; the upload candidates must be built once from the merged
release commit.

## Gates before publication

1. Confirm a successful GitHub Actions run on the release pull request and
   merge it without additional source changes.
2. Build once from the clean merged release commit and validate the exact wheel
   and source distribution according to `docs/releasing.md`.
3. Because packaging metadata and public capabilities have changed
   substantially since 0.1.0a0, upload those exact artifacts to TestPyPI and
   repeat the clean-install tests before production publication.
4. After maintainer confirmation, upload the unchanged candidate artifacts to
   PyPI, verify fresh installs, create the matching signed tag, and record the
   published hashes and CI evidence here.
