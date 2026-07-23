# `combstruct` 0.1.0a1 release record

Audit date: 2026-07-22

This document records the evidence and publication outcome for the second
`combstruct` pre-release. Version `0.1.0a1` was built once from the merged
release commit, validated through both package indexes, and published without
rebuilding.

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

## Exact merged-commit candidate

The publication candidate was built once from clean merge commit
`5343c694a806b496a220e734e7c242529c547f64`. Its fixed artifacts are:

| Artifact | SHA-256 |
| --- | --- |
| `combstruct-0.1.0a1-py3-none-any.whl` | `109510509417b801e1bd0075bcb3370abc8d99afdbe769ebc142c21acdbf325b` |
| `combstruct-0.1.0a1.tar.gz` | `b00ca0cbf468170727d287d42ff338a47958efa00ad7f39ac0848025c0ef2803` |

The artifact contract checker, `twine check`, and `check-wheel-contents`
passed these exact files. Fresh installations of the exact wheel passed all
28 installed-distribution tests, both command forms, and `pip check` on Python
3.12, 3.13, and 3.14.

## TestPyPI outcome

The exact candidate artifacts were uploaded successfully to
[TestPyPI](https://test.pypi.org/project/combstruct/0.1.0a1/). TestPyPI's JSON
API and simple index reported the same filenames and SHA-256 hashes recorded
above. Fresh, uncached installations from TestPyPI passed all 28 installed-
distribution tests, both command forms, and `pip check` on Python 3.12, 3.13,
and 3.14.

## Production outcome

The unchanged candidate artifacts were published successfully to
[PyPI](https://pypi.org/project/combstruct/0.1.0a1/). PyPI's JSON API and
simple index report the same filenames and SHA-256 hashes recorded above.
Fresh, uncached production-index installations passed all 28 installed-
distribution tests, both command forms, and `pip check` on Python 3.12, 3.13,
and 3.14.

Signed source tag `v0.1.0a1` identifies merge commit
`5343c694a806b496a220e734e7c242529c547f64`. Its SSH signature was verified
against the maintainer's RSA public key, and the
[tag-triggered GitHub Actions run](https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29973171402)
passed static checks, all three source and maintenance-tool test jobs, artifact
validation, installed-wheel tests, and both command-line smoke tests.

The [GitHub prerelease](https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/releases/tag/v0.1.0a1)
attaches the exact published wheel and source distribution plus `SHA256SUMS`.
GitHub's recorded asset digests match the PyPI and local hashes above.
