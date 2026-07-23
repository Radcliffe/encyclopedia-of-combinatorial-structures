# `combstruct` 0.1.0a0 release record

Audit date: 2026-07-22

This document records the evidence, confirmed choices, and publication outcome
for the first `combstruct` pre-release.

## Release outcome

Version `0.1.0a0` was published successfully on 2026-07-22:

- [PyPI release](https://pypi.org/project/combstruct/0.1.0a0/)
- [TestPyPI release](https://test.pypi.org/project/combstruct/0.1.0a0/)
- signed source tag `v0.1.0a0`, which identifies merge commit
  `52257132324ee3d091ba40337380d45556077026`
- [successful tag-triggered GitHub Actions run](https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29932518492)

The exact published artifacts were:

| Artifact | SHA-256 |
| --- | --- |
| `combstruct-0.1.0a0-py3-none-any.whl` | `cdf462a4fda4b7bdef92cf11a09d7d31ef66ab1abf0138b4bafceac5ff7b12cf` |
| `combstruct-0.1.0a0.tar.gz` | `229ac0efc687c65f681c7b20610079249134ad5c809aa8052b86e404f2e74c2d` |

Fresh, uncached installations from production PyPI passed all 17 installed
distribution tests, both command-line forms, and `pip check` on Python 3.12,
3.13, and 3.14. PyPI's published hashes match the validated candidate hashes
above.

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
- Package metadata contains live homepage and canonical GitHub links.
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

## Hosting notes

- Publishing used scoped API tokens for the first manual release. A dedicated
  Trusted Publishing workflow remains future release-infrastructure work.
- The test workflow ran successfully on GitHub for both the release branch and
  signed release tag.
- GitHub is the canonical source repository and CI host.

Future releases must follow `docs/releasing.md` against a clean release commit
and must use a new version because PyPI artifacts are immutable. The released
public API subsequently became the integration boundary for every read-only
`python-tools` consumer. The source-data serializers and mutators intentionally
retain raw JSON access because they create the records exposed by that API.
