# `combstruct` pre-release readiness

Audit date: 2026-07-22

This document records the evidence and confirmed choices for the first
`combstruct` pre-release. It is not a substitute for rerunning
`docs/releasing.md` against the exact release commit.

## Technically ready

- The source distribution and universal wheel build successfully with Python
  3.12.
- `twine check` passes both artifacts.
- `check-wheel-contents` reports the wheel is valid.
- The installed wheel passes all 17 package and catalogue tests on Python
  3.12, 3.13, and 3.14 from outside the source checkout.
- All 13 historical `python-tools` tests pass on the same three versions.
- Ruff formatting/lint and strict mypy checks pass for the packaged source.
- `pip check` reports no broken requirements after wheel installation.
- The installed command produces the expected ECS #56 prefix.
- The wheel contains all 1,075 canonical ECS records, `py.typed`, both license
  texts, and the provenance notice.
- The source distribution contains the changelog, API/development/release
  documentation, tests, both license texts, and all canonical records.
- Package metadata contains live homepage and canonical Codeberg links.
- The test CI workflow is read-only and checks source, legacy tools,
  artifact metadata and contents, installation, and both command-line entry
  points.

## Confirmed first-release choices

### Distribution name

The maintainer confirmed `combstruct` as the distribution name. It was
unregistered on both PyPI and TestPyPI when checked on 2026-07-22, but
availability does not reserve the name. Check again immediately before
creating a pending trusted publisher or uploading the first artifact.

### Version

The maintainer confirmed `0.1.0a0` as the first pre-release version. PyPI does
not allow files for an existing release to be replaced and does not allow an
uploaded version number to be reused.

### Combined data licensing

The base `ecs-original.json` came from
`jlumbroso/encyclopedia-of-combinatorial-structures-data`. Its `LICENSE.md` is
byte-for-byte identical to this repository's LGPL-2.1 license file (Git blob
ID `3a3af496f876c2c31fbe560da4bd635d96179c4e`).

The canonical records have subsequently been curated. Relative to the
upstream JSON, the current records contain:

- 999 changed names;
- 714 changed descriptions;
- 54 changed reference lists;
- 5 changed term lists;
- 5 changed labelled flags; and
- 11 changed generating-function fields.

Repository history makes the OEIS contribution more precise. Commit
`aa28cd1` replaced 696 names and 703 descriptions with exact OEIS entry
titles. All 703 prior descriptions and 158 of the prior names were missing;
the remaining names were generic ECS labels. Later commits curated names
further. OEIS currently licenses its content under CC BY-SA 4.0.

The maintainer chose to retain the complete catalogue and document both
component licenses. Package metadata now declares
`LGPL-2.1-only AND CC-BY-SA-4.0`; `LICENSE.md` contains the LGPL text,
`LICENSES/CC-BY-SA-4.0.txt` contains the official Creative Commons legal text,
and `NOTICE.md` identifies component boundaries, attribution, source links,
and later modifications. Artifact checks validate the metadata format and
file inclusion; they do not constitute legal review.

## Deliberately not performed

- Nothing has been uploaded to TestPyPI or PyPI.
- No PyPI project or trusted publisher has been created.
- No credentials, API tokens, tags, commits, or releases have been created.
- The local CI workflow has been syntax-checked, but it cannot run remotely
  until these changes are committed and pushed. The GitHub mirror can run it
  from `.github/workflows`; Codeberg's Forgejo fallback additionally requires
  repository Actions and a compatible runner to be configured.

Follow `docs/releasing.md` against a clean release commit. Migrate the
remaining `python-tools` scripts only after the resulting package pre-release
is available and its public API is confirmed.
