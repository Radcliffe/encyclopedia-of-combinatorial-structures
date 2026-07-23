# Changelog

This file records notable changes to the ECS website, data, tools, and
`combstruct` Python distribution.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Python package releases use version headings; website and data deployments that
do not have a corresponding package release are grouped by date.

## Unreleased

- Add the first Maple `combstruct` parity slice: public `count`, `gfseries`,
  and `gfsolve` operations with explicit labeled/EGF versus unlabeled/OGF
  semantics, plus a dependency-ordered parity matrix.
- Add immutable combinatorial object values, exact-size `allstructs`
  enumeration for grammar-defined classes, and the `iterstructs`,
  `nextstruct`, and `finished` iterator family.
- Support exact and bounded cardinality constraints on unlabeled `PowerSet`
  in both counting and exhaustive generation.
- Add predefined `Combination`/`Subset`, `Permutation`, `Partition`, and
  `Composition` families to `count`, `allstructs`, and the iterator command
  family, including Maple-compatible defaults and `allsizes` behavior.
- Add uniform `draw` for grammar-defined and predefined classes with injectable
  seeded randomness and an explicit empty-class error.
- Support Maple's `Subst(A,B)` constructor across counting,
  generating-function derivation, exhaustive iteration, and random drawing by
  cloning outer productions and replacing their atoms at the grammar level.
- Add `gfeqns` for unsolved named OGF/EGF systems, including exact finite
  cycle-index formulas, symbolic infinite Set/Cycle/PowerSet sums, and formal
  `Subst` composition.
- Preserve named Epsilon productions as tags in generated objects and support
  independent or multiplied Epsilon marker variables in symbolic `gfeqns`
  systems.
- Add linear attribute-grammar parsing, symbolic multivariate `agfeqns`, exact
  joint OGF/EGF prefixes through `agfseries`, and truncated mixed factorial
  moments through `agfmomentsolve`.
- Support atomic symbolic constants and linear coefficients in attribute
  equations, with validated integer parameter binding for exact series and
  moment extraction.
- Add exact count-directed `draw` for recursive Union/Prod/Sequence grammars,
  substitution-expanded forms, labeled Set/Cycle, and every predefined family,
  with explicit algorithm selection and a uniform exhaustive fallback for
  remaining symmetries.
- Add grouped component-type unranking for unlabeled Set and PowerSet drawing,
  including recursively defined multiset classes without top-level
  materialization.
- Add exact cycle-index-weighted drawing for unlabeled Cycle, with orbit-size
  rejection correction so periodic and aperiodic necklaces are uniform.

Add production-bound changes here under `Added`, `Changed`, `Fixed`, or `Removed`.
When a package is released or `prod` is deployed, move the entries into a version
or date section and leave this section in place for subsequent work.

### Changed

- Distinguished every stored ordinary and exponential generating function with
  an explicit `gf_type`, exposed that classification through the Python API,
  and added OGF/EGF labels and filtering to the website.
- Recorded the successful `0.1.0a1` publication, updated the maintenance-tools
  lock to that release, and started the `0.1.0a2` development cycle.
- Updated the Python test workflow to `actions/checkout` and
  `actions/setup-python` version 7 after the release run reported their prior
  Node.js 20 runtimes as deprecated.

## 0.1.0a1 - 2026-07-22

### Added

- Added an immutable AST and parser for the finite elementary, `LambertW`,
  unselected `RootOf`, both indexed infinite-`Sum` notations, and one-argument
  `Complex` syntax, plus the two fully determined positive and alternating
  ellipsis patterns, the symbolic infinite product and indexed coefficients in
  ECS 44, ten individual implicit equations, and one three-equation system used
  by all 1,028 stored ECS generating-function fields.
  `RootOf` retains its unspecified-branch meaning, infinite sums retain their
  lexical index binding and lower bound, the product and `a_k` coefficients
  remain explicit, named series calls remain explicit, recognized ellipses
  normalize to infinite sums, and `Complex(x)` retains its purely imaginary
  meaning.
- Added dependency-free exact coefficient expansion for 986 parsed generating
  functions, including rational powers, removable singularities, principal
  `LambertW` compositions at zero and recognized rational centers, and all 47
  coefficientwise-finite indexed sums, plus exact fixed-point solving for five
  contractive named-series equations and the three-series system in ECS 118,
  and exact coefficient-recursive solving for ECS 79, 89, and 91. Catalogue
  tests verify 556 OGFs and 430 EGFs against every stored term. The 39
  unselected `RootOf` expressions, one complex expression, and two equations
  requiring stronger solvers remain explicit exact-evaluation boundaries.
- Added finite generating-function derivation for 888 specifications, including
  labelled constructor rules, bounded unlabelled cycle-index substitutions, and
  rational or square-root closed forms for 50 recursive `Union`/`Prod` records.
  Recursive components are reduced by removing one feedback symbol and
  expanding the remaining acyclic equations, with every result verified against
  the independent term evaluator.

### Changed

- Moved the canonical source repository and issue tracker from Codeberg to
  GitHub, updated package and website links, and archived the former Codeberg
  issue and pull-request records under `docs/codeberg-archive.md`.
- Started the `0.1.0a1` development cycle and updated installation and release
  documentation after the successful `0.1.0a0` publication.
- Read the expected artifact version from `pyproject.toml` so release validation
  has a single version source of truth.
- Migrated b-file generation to the public `combstruct` catalogue and term
  evaluator APIs, with an explicit package dependency for maintenance tools.
- Migrated Maple script generation and sequence validation to the typed public
  catalogue API and extended static quality checks to migrated tools.
- Migrated the term-evaluator regression suite to the public top-level API and
  added an explicit smoke test for the historical script entry point.
- Migrated the legacy OEIS report to typed catalogue records and documented why
  source-data serializers and mutators intentionally retain raw JSON access.
- Completed migration of every read-only `python-tools` consumer to the public
  package API; source-data serializers and mutators retain raw JSON access as
  the intentional producer boundary.
- Ignored the conventional local PyPI and TestPyPI token filenames and
  documented their safe handling during manual releases.

### Fixed

- Required a structural affine proof before coefficient recursion accepts
  nonzero constant terms, preventing its degree-zero Jacobian from selecting an
  arbitrary root of a nonlinear implicit system.
- Solved non-stabilizing affine constant-term equations through the exact
  coefficient Jacobian, allowing nonsingular implicit systems to select nonzero
  constant terms.
- Preserved exact additive cancellations while constructing the zero-delay
  dependency graph, avoiding false recursion cycles in contractive equations.
- Replaced the named-series solver's empirical second starting-value check with
  a structural proof that its same-coefficient dependency graph is acyclic, and
  rejected equation solutions containing negative powers instead of silently
  dropping their Laurent terms.
- Corrected indexed-sum coefficient bounds when an index occurs in a power's
  exponent, and recognized constant-minus perturbations in shifted principal
  `LambertW` expressions.
- Corrected the canonical generating-function equations for ECS 79 and 91.
  ECS 79 now designates `B = S + Z` as the counted class and includes its
  size-one object, agreeing with OEIS A032203's offset and terms. ECS 91 now
  includes the full unlabelled-cycle Pólya sum and removes both length-one and
  length-two cycles. Both equations reproduce all 21 stored OGF terms.
- Regenerated the consolidated web catalogue with all canonical implicit
  generating-function fields and regenerated ECS 79's b-file for its corrected
  counted class.

## 0.1.0a0 - 2026-07-22

### Added

- Added this changelog and documented how it is maintained for the `prod` branch.
- Added the pre-alpha `combstruct` Python package, including the existing ECS
  specification parser, exact term evaluator, command-line interface, documentation,
  all 1,075 canonical structure records, and a typed read-only catalogue API.
- Added Python 3.12–3.14 test automation and installed-distribution verification for
  the package.
- Added explicit public and legacy compatibility export contracts, a detailed API
  reference, strict Ruff/mypy quality gates, and component-level ECS/OEIS licensing.

## 2026-07-22

### Fixed

- Scroll to the top after selecting a structure so its details are immediately visible.

## 2026-07-21

### Added

- Added an alphabetical index for browsing all ECS structures by name.
- Added exact combinatorial-specification evaluation and OEIS-style b-file generation tools.
- Added b-files containing terms through `a(1000)`, subject to the 1,000-digit limit.
- Added a dedicated sequence page with a compact table, pin plot, and automatically
  logarithmic scatter plot.
- Added links from structure records to their sequence tables, plots, and b-files.

### Changed

- Store sequence integers as decimal strings so values larger than JavaScript's safe
  integer range remain exact.
- Replaced missing, vague, and duplicate structure names where reliable alternatives
  were available.
- Split the main React application into focused ECS components and shared utilities.
- Limited sequence tables to `a(0)` through `a(50)` and plots to `a(0)` through `a(100)`.

## 2025-08-30

### Changed

- Refreshed the structure data and updated the application's displayed data date.

## 2025-08-29

### Added

- Added a report identifying structures with identical initial sequence terms.

## 2025-08-28

### Removed

- Removed the temporary Maple code and generated Maple files from the repository.

## 2025-08-27

### Added

- Added temporary Maple computation support for structure data processing.

### Changed

- Updated the application footer.

## 2025-08-26

### Changed

- Updated the ECS branding, logo, icons, and project documentation.

## 2025-08-25

### Added

- Added deep links to individual structure records.
- Added missing names, descriptions, and OEIS references.
- Split the ECS data into individual JSON files for maintainable structure-level edits.
- Added the page title, favicon, and initial ECS logo.

### Changed

- Cleaned up and reformatted the initial application code.

## 2025-08-24

### Added

- Created the initial ECS prototype.
- Added the project README and license.
