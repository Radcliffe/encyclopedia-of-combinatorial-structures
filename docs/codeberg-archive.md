# Archived Codeberg project records

This file preserves the issue and pull-request context from the former Codeberg
project immediately before its deletion on 2026-07-22. Git commits, branches,
and tags were copied separately and verified byte-for-byte against the GitHub
repository. The final Codeberg `main` commit was
`c94d9fb19140e72339c951bde3575bc16e39af00`.

## Issues

### Issue #1: Suggested TODO: Identify structures with identical sequence

- State: closed
- Created: 2025-08-28T11:01:25+02:00
- Closed: 2025-08-29T20:17:42+02:00

Some structures, like 34 and 298, have the same sequence. This should be shown on their individual page.

Comments:

> Radcliffe (2025-08-29T20:17:41+02:00): Done.

### Issue #2: Distinguish between ordinary and exponential generating functions

- State: open
- Created: 2025-08-29T04:41:11+02:00

Some entries provide ordinary generating functions (ogf's) while others provide exponential generating functions (egf's). Both of these are labeled as "gf" in the data, without specifying the type of generating function. The word "labelled" seems to imply that the gf is an egf, while "unlabelled" implies that it is an ogf. But I have not confirmed this for all instances.

Sometimes an egf is provided, but the terms are computed as if it were an ogf. An example of this is ECS 265.

Tasks:

1. For each term, determine whether the gf is an ogf or an egf.
2. Verify the correctness of each generating function.
3. Verify that the gf generates the given terms.
4. Verify that each entry links to the correct OEIS sequence.

## Pull requests

### Pull request #3: Package existing evaluator as combstruct 0.1.0a0

- State: closed (merged)
- Created: 2026-07-22T16:46:32+02:00
- Closed: 2026-07-22T16:46:59+02:00
- Merged: 2026-07-22T16:46:59+02:00
- Head: `codex/combstruct-0.1.0a0` at `1351c18ede31ed366714fa74fa7f6ecb4125e879`
- Merge commit: `52257132324ee3d091ba40337380d45556077026`

Successful Github Actions run: https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29921514585

Released combstruct 0.1.0a0 on TestPyPI. All tests are passing.

### Pull request #4: Document combstruct 0.1.0a0 release and start 0.1.0a1 development

- State: closed (merged)
- Created: 2026-07-22T17:51:15+02:00
- Closed: 2026-07-22T17:52:42+02:00
- Merged: 2026-07-22T17:52:42+02:00
- Head: `codex/combstruct-post-release` at `0a83a5e645e78655358d5d6b3e2ad2db32539c96`
- Merge commit: `1b7a593e26edb6af561c58d17d7c4304a4773cb9`

## Summary

- record the successful TestPyPI and production PyPI publication, exact artifact hashes, signed tag, and CI outcome for `combstruct 0.1.0a0`
- replace pre-release installation guidance with the published PyPI command
- start the next development cycle at `0.1.0a1.dev0` so future builds cannot reuse PyPI's immutable `0.1.0a0` version
- read the artifact-checker's expected version from `pyproject.toml` as the single source of truth
- update the changelog and future release checklist

This changes release metadata and documentation only; it adds no package runtime capabilities.

## Verification

- 17 package tests on Python 3.12, 3.13, and 3.14
- 13 historical maintenance-tool tests on Python 3.12, 3.13, and 3.14
- Ruff formatting/lint and strict mypy
- wheel and source-distribution build and content validation
- `twine check` and `check-wheel-contents`
- fresh installed-wheel tests, both CLI entry points, and `pip check`

### Pull request #5: Migrate b-file generation to the public combstruct API

- State: closed (merged)
- Created: 2026-07-22T17:54:08+02:00
- Closed: 2026-07-22T17:55:14+02:00
- Merged: 2026-07-22T17:55:14+02:00
- Head: `codex/combstruct-generate-bfiles-migration` at `4e31c1e8b1c8b3ac04e6a478227ec7eddeb3dd14`
- Merge commit: `ee3519b28357430a65893d067550aa2dae128da1`

## Summary

- replace raw JSON dictionaries in `generate_bfiles.py` with the public `Catalog`, `Structure`, and `compute_terms` APIs
- use the bundled canonical catalogue by default while preserving `--dataset` support for canonical directories and historical consolidated JSON
- declare and lock `combstruct>=0.1.0a0,<0.2` as a maintenance-tools dependency
- install the package before maintenance-tool tests in CI
- document the tools environment and b-file workflow

This is the first incremental migration of `python-tools` after the package release. It does not add package capabilities or change generated b-file contents.

## Verification

- 14 maintenance-tool tests on Python 3.12, 3.13, and 3.14
- isolated `uv --locked` test run using published `combstruct 0.1.0a0`
- Ruff formatting/lint and strict mypy for the migrated script
- single-process and multi-process b-file generation smoke tests
- all five jobs passed in [GitHub Actions](https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29935032569)

### Pull request #6: Migrate Maple and sequence tools to the public combstruct API

- State: closed (merged)
- Created: 2026-07-22T18:07:21+02:00
- Closed: 2026-07-22T18:09:23+02:00
- Merged: 2026-07-22T18:09:23+02:00
- Head: `codex/combstruct-maple-tools-migration` at `93dffa9847e902279a015ca6f5c681cda2415040`
- Merge commit: `1147508194708472ec632102ef71478e1fba2cc6`

## Summary

- replace raw JSON dictionary loading in `write_maple_scripts.py` with the public `Catalog` and typed `Structure` APIs
- preserve historical Maple term-counting and generating-function command text for all 1,075 records
- make catalogue, Maple input/output, and local OEIS paths explicit and independent of the current working directory
- add focused tests for Maple command generation, wrapped output parsing, catalogue validation, EIS references, and OEIS internal-format data
- extend Ruff and strict mypy quality gates to migrated maintenance tools

This is the second incremental `python-tools` migration. It adds no `combstruct` runtime capabilities and does not change generated Maple command content.

## Verification

- 17 package tests and 20 maintenance-tool tests on Python 3.12, 3.13, and 3.14
- isolated `uv --locked` run against published `combstruct 0.1.0a0`
- Ruff formatting/lint and strict mypy
- all 1,075 historical term commands and 1,075 GF commands matched byte-for-byte
- all GitHub Actions jobs passed: https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29936339828

### Pull request #7: Test term evaluator through the public combstruct API

- State: closed (merged)
- Created: 2026-07-22T18:17:56+02:00
- Closed: 2026-07-22T18:18:42+02:00
- Merged: 2026-07-22T18:18:42+02:00
- Head: `codex/combstruct-evaluator-tests-migration` at `ff54a982b52f9d09b6dd7665c40f223b8e0b9b30`
- Merge commit: `cf5a18d698e6972d70401712e10816378e7591a8`

## Summary

- switch the term-evaluator regression suite from raw ECS JSON and the legacy wrapper to the documented top-level `combstruct` API
- read typed records through `Catalog` while retaining exhaustive stored-prefix verification
- keep the historical `compute_terms.py` compatibility entry point and exercise it with a dedicated command-line smoke test
- add the migrated evaluator files to the Ruff quality gate and document the boundary

This is the third incremental `python-tools` migration. It adds no package runtime capabilities and remains compatible with the published `combstruct 0.1.0a0`.

## Verification

- 17 package tests and 21 maintenance-tool tests on Python 3.12, 3.13, and 3.14
- all 1,075 ECS records recomputed and matched against their stored prefixes
- migrated evaluator suite passed against published `combstruct 0.1.0a0` on Python 3.12, 3.13, and 3.14
- Ruff formatting/lint and strict mypy
- all GitHub Actions jobs passed: https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29937139162

### Pull request #8: Migrate the OEIS report to the public combstruct API

- State: closed (merged)
- Created: 2026-07-22T18:29:36+02:00
- Closed: 2026-07-22T18:30:42+02:00
- Merged: 2026-07-22T18:30:42+02:00
- Head: `codex/combstruct-oeis-report-migration` at `a27afd1256177e2d9c0ccfc8b2b19476389fb2ee`
- Merge commit: `79cafda1b073f465f5d1e1ab54d639c5a48d48c1`

## Summary

- replace raw web-JSON dictionaries in the historical OEIS report with public `Catalog` and typed `Structure` records
- preserve the existing 58-record missing-generating-function report byte-for-byte
- make catalogue, OEIS-name, CSV, and augmented-JSON defaults independent of the invoking directory
- add focused tests for typed loading, EIS reference selection, legacy report compatibility, and report artifact generation
- extend Ruff and strict mypy coverage to the migrated report
- document why canonical-data serializers, splitters, and mutators intentionally retain raw JSON access

This is the fourth incremental `python-tools` migration. It adds no `combstruct` runtime capabilities and remains compatible with published `combstruct 0.1.0a0`.

## Verification

- 17 package tests and 25 maintenance-tool tests on Python 3.12, 3.13, and 3.14
- migrated OEIS tests passed against published `combstruct 0.1.0a0` on Python 3.12, 3.13, and 3.14
- default missing-GF output matched the legacy script byte-for-byte
- Ruff formatting/lint and strict mypy
- all GitHub Actions jobs passed: https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29937965496

### Pull request #9: Parse finite elementary ECS generating functions

- State: closed (merged)
- Created: 2026-07-22T18:47:59+02:00
- Closed: 2026-07-22T18:49:20+02:00
- Merged: 2026-07-22T18:49:20+02:00
- Head: `codex/combstruct-gf-expression-parser` at `7fa828a98dcef0e4211da9d8a9ab59aa03834837`
- Merge commit: `7bd59283a89b523aa8ff99af375c87188fda9cc0`

## Summary

- add an immutable AST and precedence-aware parser for finite elementary ECS generating-function expressions
- support integers, `_x`, parentheses, unary signs, `+ - * / ^`, and `exp`/`ln`
- match Maple precedence, including right-associative powers and powers binding more tightly than unary signs
- parse all 913 finite elementary `gf` fields in the catalogue
- reject the remaining 115 current forms explicitly: 11 equations, 45 infinite sums, 39 `RootOf` forms, 19 `LambertW` forms, and one `Complex` form
- expose the parser, AST, and specific exceptions through the documented public API

This first GF milestone parses syntax only. It does not evaluate coefficients or infer OGF versus EGF from `Structure.labeled`; issue #2 remains open for exact two-interpretation validation.

## Verification

- 25 package tests and 25 maintenance-tool tests on Python 3.12, 3.13, and 3.14
- exhaustive 913-supported / 115-unsupported catalogue partition
- Ruff formatting/lint and strict mypy
- sdist and wheel content checks, Twine metadata check, and `check-wheel-contents`
- installed-wheel distribution/parser tests and CLI smoke test outside the checkout
- all GitHub Actions jobs passed: https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29939236583

### Pull request #10: Expand finite ECS generating functions exactly

- State: closed (merged)
- Created: 2026-07-22T19:23:42+02:00
- Closed: 2026-07-22T19:24:29+02:00
- Merged: 2026-07-22T19:24:29+02:00
- Head: `codex/combstruct-gf-coefficients` at `8a1a56a5bcbd10bb4b8805935f30665875b4b290`
- Merge commit: `596b8ffe00d29ff3a80d5e31668edd18b88a13eb`

## Summary

- add `generating_function_coefficients` for exact formal-series expansion of parsed ECS expressions
- use dependency-free `fractions.Fraction` arithmetic, including rational powers, `exp`, `ln`, and removable singularities
- expose a specific `GeneratingFunctionEvaluationError` for parsed expressions that cannot be expanded exactly
- document the public API, raw-coefficient semantics, and supported analytic conditions

## Catalogue verification

All 913 finite elementary generating functions now expand through their complete stored term prefixes:

- 503 unlabelled records match OGF semantics
- 410 labelled records match EGF semantics
- no record is ambiguous or inconsistent in this subset
- ECS 265 correctly matches EGF semantics; its raw coefficients begin 1, 6, 21, 56 and normalization by n! gives 1, 6, 42, 336

The remaining 115 equation, infinite-sum, RootOf, LambertW, and Complex forms remain explicitly unsupported. Issue #2 therefore stays open for those forms and OEIS-link verification.

## Verification

- 35 package tests and 25 maintenance-tool tests on Python 3.12, 3.13, and 3.14
- exhaustive 913-record coefficient and OGF/EGF validation
- Ruff formatting/lint and strict mypy
- documentation examples executed successfully
- sdist and wheel content checks, Twine metadata check, and `check-wheel-contents`
- installed-wheel public API and full generating-function tests outside the checkout
- all GitHub Actions jobs passed: https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29941749021

### Pull request #11: Derive finite generating functions from ECS specifications

- State: closed (merged)
- Created: 2026-07-22T19:52:53+02:00
- Closed: 2026-07-22T19:54:54+02:00
- Merged: 2026-07-22T19:54:54+02:00
- Head: `codex/combstruct-gf-derivation` at `a2c50de61be7adb76b556f467e371e3dea2f045b`
- Merge commit: `b693b49ad9041b4eb65fb7ec0c83448252b5a925`

## Summary

- add `derive_generating_function` as a documented public API
- translate acyclic ECS specifications into the existing immutable `GFExpression` AST
- apply exact OGF or EGF rules according to the labelled universe
- support `Union`, `Prod`, `Sequence`, labelled `Set` and `Cycle`, and bounded unlabelled `Set` and `Cycle`
- implement finite unlabelled cycle-index substitutions and totient weights without runtime dependencies
- report recursive and inherently infinite cycle-index cases through `UnsupportedGeneratingFunctionDerivation`

## Catalogue verification

The current catalogue partitions into 838 supported finite derivations and 237 explicit later cases:

- 365 labelled specifications derive EGFs
- 473 unlabelled specifications derive OGFs
- 195 recursive specifications require equation solving
- 21 unrestricted unlabelled sets and 14 unrestricted unlabelled cycles require infinite cycle-index expressions
- 7 power sets require infinite cycle-index expressions

For every supported record, the complete derived coefficient prefix agrees with both the stored ECS terms and an independent `compute_terms` evaluation.

## Verification

- 46 package tests and 25 maintenance-tool tests on Python 3.12, 3.13, and 3.14
- exhaustive 838-record derivation, expansion, normalization, and independent term comparison
- Ruff formatting/lint and strict mypy
- all Python examples in the package guide and API reference executed successfully
- sdist and wheel content checks, Twine metadata check, and `check-wheel-contents`
- installed-wheel distribution, derivation, and generating-function tests outside the checkout
- all GitHub Actions jobs passed: https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29943712380

### Pull request #12: Solve quadratic recursive ECS specifications

- State: closed
- Created: 2026-07-22T20:13:23+02:00
- Closed: 2026-07-22T21:07:34+02:00
- Head: `codex/combstruct-quadratic-recursion` at `9c07d7ad3a1c893aed5fe04fc2c162f94d41dd9b`

## Summary

- solve directly self-recursive equations that are linear or quadratic in their own symbol under `Union` and `Prod`
- return rational or square-root `GFExpression` closed forms through the existing public derivation API
- select the least nonnegative formal-series branch using exact rational constant arithmetic and require the implicit-function condition to make it unique
- handle removable singularities such as `(1-sqrt(1-4*x))/(2*x)` without approximation
- support quadratic named equations reached through aliases
- keep mutually recursive, higher-degree, and constructor-nested recursion explicitly unsupported

## Catalogue verification

This increases exact generating-function derivation from 838 to 845 ECS records:

- 367 labelled specifications derive EGFs
- 478 unlabelled specifications derive OGFs
- all seven directly self-recursive quadratic `Union`/`Prod` records now derive closed forms
- 188 more general recursive records remain explicit later cases

For every supported record, the complete derived coefficient prefix agrees with both the stored ECS terms and an independent `compute_terms` evaluation.

## Verification

- 52 package tests and 25 maintenance-tool tests on Python 3.12, 3.13, and 3.14
- exhaustive 845-record derivation, expansion, normalization, and independent term comparison
- Ruff formatting/lint and strict mypy
- all eight Python examples in the package guide and all five examples in the API reference executed successfully
- sdist and wheel content checks, Twine metadata check, and `check-wheel-contents`
- installed-wheel distribution, derivation, and generating-function tests outside the checkout
- all GitHub Actions jobs passed: https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures/actions/runs/29945298282

### Pull request #13: Solve reducible mutual recursive specifications

- State: closed (merged)
- Created: 2026-07-22T20:32:26+02:00
- Closed: 2026-07-22T20:35:58+02:00
- Merged: 2026-07-22T20:36:00+02:00
- Head: `codex/combstruct-mutual-quadratic-recursion` at `eee2d6bc43c7fb4bddd05187c965e3c73f7c56a0`
- Merge commit: `4319debfcc150b3f3f569af0e99a0bcc6a322f7a`

Extends exact generating-function derivation from direct self recursion to reducible mutual recursive components. Removing one feedback symbol must leave acyclic Union/Prod equations whose substitution is linear or quadratic. This raises exact catalogue coverage from 845 to 888 specifications, including 50 recursive records, while retaining explicit unsupported boundaries for higher-degree and multiple-feedback systems. Adds focused solver tests, exhaustive catalogue verification, and updated API and release documentation. Verified on Python 3.12, 3.13, and 3.14; fresh wheel and source artifacts pass project validation, Twine, wheel-content inspection, all 57 installed-package tests, and all 25 maintenance-tool tests. GitHub CI run 29946579089 passed.

### Pull request #14: Expand principal Lambert W generating functions

- State: closed (merged)
- Created: 2026-07-22T20:47:50+02:00
- Closed: 2026-07-22T20:48:37+02:00
- Merged: 2026-07-22T20:48:37+02:00
- Head: `codex/combstruct-lambertw` at `4f16f2fe34ad697d3b83ad99e36d49f750abcfd3`
- Merge commit: `3bc117e0f2f955e757f5dd9438bd63cf029589f2`

Adds LambertW to the immutable stored generating-function AST and parser. The parser now covers 932 of 1,028 nonempty ECS generating-function fields. Exact dependency-free formal-series expansion supports the 18 principal LambertW compositions whose arguments have constant term zero, raising fully verified coefficient coverage to 931 records: 503 OGFs and 428 EGFs. ECS 69 is parsed but remains an explicit evaluation boundary because its shifted nonzero transcendental branch requires a separate exact representation. Adds focused series tests, exhaustive catalogue verification, and updated API and project documentation. Verified from source and from the exact built wheel on Python 3.12, 3.13, and 3.14; all 59 package tests, 25 maintenance-tool tests, artifact checks, strict typing, lint, documentation examples, pip checks, and GitHub CI run 29948013789 pass.

### Pull request #15: Parse unselected RootOf generating functions

- State: closed (merged)
- Created: 2026-07-22T21:00:28+02:00
- Closed: 2026-07-22T21:02:01+02:00
- Merged: 2026-07-22T21:02:01+02:00
- Head: `codex/combstruct-rootof-syntax` at `c432a52180da59eac8d446687584fe08a3312942`
- Merge commit: `8dba3cd2d6e639abebc11f8a44b336340dc2567a`

Adds a public immutable GFRootOf syntax node and scopes Maple local variable _Z to RootOf equations. The parser now faithfully accepts all 39 ECS RootOf fields, raising total stored generating-function parser coverage from 932 to 971 of 1,028 nonempty fields. Because the ECS strings contain no root selectors and Maple defines unselected RootOf as unspecified roots, exact coefficient evaluation raises a branch-specific error instead of guessing from stored terms. Derivation substitution preserves _Z while substituting _x. Adds focused public-API tests, exhaustive catalogue parsing and boundary verification, and documented Maple selector semantics. Verified from source and from the exact built wheel on Python 3.12, 3.13, and 3.14; all 62 package tests, 25 maintenance-tool tests, artifact checks, strict typing, lint, documentation examples, pip checks, and GitHub CI run 29948917603 pass.

### Pull request #16: Parse indexed infinite generating-function sums

- State: closed (merged)
- Created: 2026-07-22T21:15:23+02:00
- Closed: 2026-07-22T21:16:34+02:00
- Merged: 2026-07-22T21:16:34+02:00
- Head: `codex/combstruct-indexed-sum-syntax` at `59f90cf680e2ed7a4f783b6cb1aeaeb9a65acd28`
- Merge commit: `d522fa8b23f14e8bb83e0ad6522b37a533dd87c1`

Adds public immutable GFIndex, GFTotient, and GFInfiniteSum syntax nodes and parses the exact indexed Sum(...,j[k]=1..infinity) and numtheory:-phi forms used by the ECS catalogue. Indices are validated with lexical scope: nested sums may reference outer indices, while unbound indices and rebinding are rejected.

This raises generating-function parser coverage from 971 to 1,016 of 1,028 nonempty fields, covering all 45 indexed infinite-sum records. Exact coefficient expansion remains deliberately at 931 records: infinite sums raise a targeted error until a finite formal truncation bound is proved, rather than silently truncating.

Updates derivation substitution, public exports, catalogue-wide tests, the changelog, package guide, and API documentation.

Verified from source and from the exact built wheel on Python 3.12, 3.13, and 3.14. All 65 package tests, 25 maintenance-tool tests, 17 executable documentation examples, artifact checks, strict typing, lint, formatting, and GitHub Actions run 29949881781 pass.

### Pull request #17: Parse one-argument Complex generating functions

- State: closed (merged)
- Created: 2026-07-22T21:27:27+02:00
- Closed: 2026-07-22T21:28:02+02:00
- Merged: 2026-07-22T21:28:02+02:00
- Head: `codex/combstruct-complex-syntax` at `66189644cdd035cb0e8d135099f9da207725003c`
- Merge commit: `c94d9fb19140e72339c951bde3575bc16e39af00`

Adds a public immutable GFComplex node for the one-argument Maple Complex(value) constructor used by ECS 47. Maple defines this form as the purely imaginary value I*value. The parser preserves that meaning without attempting complex coefficient arithmetic.

This raises generating-function parser coverage from 1,016 to 1,017 of 1,028 nonempty fields. The remaining 11 fields are heterogeneous equations or prose and stay explicit parser boundaries. Exact expansion remains 931 records; ECS 47 now raises a targeted complex-formal-series error.

Evaluation now preflights semantic boundary nodes across the complete syntax tree, so nested RootOf, infinite Sum, and Complex forms report their actual missing capability before unrelated local series restrictions. Public exports, derivation substitution, catalogue-wide tests, the changelog, package guide, and API documentation are updated.

Maple Complex documentation: https://www.maplesoft.com/support/help/Maple/view.aspx?path=complex

Verified from source and the exact built wheel on Python 3.12, 3.13, and 3.14. All 68 package tests, 25 maintenance-tool tests, 19 executable documentation examples, artifact checks, strict typing, lint, formatting, and GitHub Actions run 29950932829 pass.

