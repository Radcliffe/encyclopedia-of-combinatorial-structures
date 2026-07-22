# `combstruct` API reference

This reference describes the public API of the initial `combstruct`
pre-release. The package is still pre-alpha, so names may evolve between
pre-releases, but changes to the top-level API should be deliberate,
documented in `CHANGELOG.md`, and covered by distribution tests.

For ordinary application code, import names from `combstruct`. The
`combstruct.specification` module is also public for code that works directly
with syntax trees. `combstruct.terms` preserves the import surface of the
repository's historical `compute_terms.py` script during migration; it should
not be the starting point for new integrations.

## Package metadata

### `combstruct.__version__`

The installed distribution version as a string. It is read from Python
package metadata, so it stays consistent with the wheel or source
distribution. A source checkout that has not been installed reports
`"0+unknown"`.

## Specifications

### `parse_specification(source)`

Parse an ECS specification string and return a `Specification`, which is a
dictionary mapping each equation symbol to an `Expression` syntax tree.

```python
from combstruct import Constructor, Reference, parse_specification

equations = parse_specification("{S = Sequence(Z,card <= 3)}")
root = equations["S"]

assert root == Constructor(
    name="Sequence",
    arguments=(Reference("Z"),),
    cardinality=root.cardinality,
)
assert root.cardinality is not None
assert root.cardinality.minimum == 0
assert root.cardinality.maximum == 3
```

The parser accepts the syntax used by every specification in the bundled ECS
catalogue:

- a specification is a brace-delimited, comma-separated set of equations;
- symbols are identifiers, optionally followed by a numeric index such as
  `A[1]`;
- expressions are symbol references or constructor calls;
- the term evaluator recognizes `Union`, `Prod`, `Sequence`, `Set`, `Cycle`,
  and `PowerSet`; and
- cardinality constraints use `card = n`, `card <= n`, `card < n`,
  `n <= card`, or `n < card`.

Parsing recognizes constructor syntax independently of whether the term
evaluator supports a particular mathematical use of that constructor.
Malformed text raises `SpecificationError`.

### Syntax-tree types

`Reference(name)` is an immutable reference to another equation or to an atom
such as `Z`.

`Constructor(name, arguments, cardinality=None)` is an immutable constructor
call. `arguments` is a tuple of `Reference` or nested `Constructor` values.

`Cardinality(minimum=0, maximum=None)` stores inclusive component-count
bounds. `None` means that there is no upper bound. The parser creates bounds
from valid ECS syntax; callers constructing syntax trees directly are
responsible for providing meaningful bounds.

`Expression` is the type alias `Reference | Constructor`, and `Specification`
is the alias `dict[str, Expression]`.

`Parser(source)` exposes the stateful parser object used by
`parse_specification`. Most callers should prefer the function API.

## Computing terms

### `compute_terms(specification, *, labelled, term_count, symbol="S", max_digits=None)`

Compute exact counting terms beginning at size zero.

```python
from combstruct import compute_terms

terms = compute_terms(
    "{S = Union(Epsilon,Prod(Z,S,S))}",
    labelled=False,
    term_count=8,
)

assert terms == [1, 1, 2, 5, 14, 42, 132, 429]
```

Parameters:

- `specification` is ECS specification text.
- `labelled` selects labelled/exponential-generating-function semantics when
  true and unlabelled/ordinary-generating-function semantics when false.
- `term_count` is the requested number of terms, including the size-zero
  term. It must be positive.
- `symbol` selects the equation to enumerate. ECS records provide their own
  root symbol; literal examples conventionally use `S`.
- `max_digits`, when provided, stops before returning an integer whose decimal
  representation exceeds the limit. This supports the historical b-file
  generation workflow.

The return value is a list of Python integers. Intermediate arithmetic uses
`fractions.Fraction`; a nonintegral final coefficient raises
`UnsupportedConstruction` instead of being rounded.

`SpecificationError` reports malformed input, missing equations, undefined
symbols, or invalid constructor arguments. `UnsupportedConstruction`, a
subclass of `SpecificationError`, reports a valid specification that the
current finite-series evaluator cannot expand safely. `ValueError` reports a
nonpositive `term_count`.

## ECS catalogue

### `Structure`

An immutable dataclass representing one canonical ECS record. Its attributes
are:

| Attribute | Type | Meaning |
| --- | --- | --- |
| `id` | `int` | Positive ECS identifier |
| `name` | `str` | Display name |
| `description` | `str` | Structure description |
| `specification` | `str` | Original ECS specification text |
| `labeled` | `bool` | Whether labelled semantics apply |
| `symbol` | `str` | Root equation symbol |
| `terms` | `tuple[int, ...]` | Stored counting terms |
| `references` | `tuple[str, ...]` | ECS bibliography and sequence references |
| `generating_function` | `str | None` | Stored ECS `gf` text |
| `recurrence` | `str | None` | Stored ECS `rec` text |
| `closed_form` | `str | None` | Stored ECS `closedform` text |
| `asymptotic_equivalent` | `str | None` | Stored ECS `equiv` text |

`Structure.from_record(mapping)` validates and converts a canonical or
web-encoded record. `structure.as_record()` returns a mutable dictionary using
the original ECS field names.

### `Catalog(dataset=None)`

A lazy, read-only collection of structures. With no argument it reads the
canonical records in the repository or the data bundled in an installed
wheel. A supplied path may identify either a canonical record directory or
the historical consolidated ECS JSON mapping.

`catalog.ids` is the ordered tuple of identifiers. `len(catalog)`, membership
tests, and iteration are supported. `catalog.get(structure_id)` validates the
identifier, loads one record, and caches the resulting immutable object for
the lifetime of that catalogue.

Invalid datasets raise `CatalogError`. A missing identifier raises
`StructureNotFoundError`. A boolean is not accepted as an identifier even
though `bool` is a subclass of `int` in Python.

### Catalogue convenience functions

`get_structure(structure_id)` reads from the process-wide default catalogue.

`iter_structures()` iterates over that catalogue in identifier order.

`default_dataset()` and `load_record(dataset, structure_id)` retain the
low-level behavior expected by repository maintenance scripts. New code
should prefer `Catalog`, `get_structure`, and the typed `Structure` model.

## Command line

Installing the distribution provides both `combstruct` and
`python -m combstruct` entry points. They use the same implementation.

```console
combstruct --spec '{S = Sequence(Z)}' --unlabelled --terms 10 --plain
python -m combstruct --id 56 --terms 8 --plain
```

Literal specifications require either `--labelled` or `--unlabelled`. An ECS
identifier obtains that choice and the root symbol from its stored record.
Without `--plain`, output is JSON and includes whether computed terms match
the stored prefix.

## Compatibility policy for the first milestone

The historical `python-tools/compute_terms.py` file is now a thin wrapper over
`combstruct.terms`. Its original declared classes, functions, type aliases,
and token expression are listed explicitly in `combstruct.terms.__all__` and
covered by installed-distribution tests. This compatibility surface exists so
the other maintenance scripts can be migrated after a package release; it is
not a promise that every evaluator implementation detail will become a
long-term top-level API.
