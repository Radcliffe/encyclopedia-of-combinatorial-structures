# Changelog

This file records notable changes to the ECS website, data, tools, and
`combstruct` Python distribution.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Python package releases use version headings; website and data deployments that
do not have a corresponding package release are grouped by date.

## Unreleased

Add production-bound changes here under `Added`, `Changed`, `Fixed`, or `Removed`.
When a package is released or `prod` is deployed, move the entries into a version
or date section and leave this section in place for subsequent work.

### Changed

- Started the `0.1.0a1` development cycle and updated installation and release
  documentation after the successful `0.1.0a0` publication.
- Read the expected artifact version from `pyproject.toml` so release validation
  has a single version source of truth.

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
