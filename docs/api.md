# `combstruct` API reference

This reference describes the public API of the initial `combstruct`
pre-release. The package is still pre-alpha, so names may evolve between
pre-releases, but changes to the top-level API should be deliberate,
documented in `CHANGELOG.md`, and covered by distribution tests.

For ordinary application code, import names from `combstruct`. The
`combstruct.specification`, `combstruct.derivation`, and
`combstruct.generating_function` modules are also public for code that works
directly with syntax trees. `combstruct.terms`
preserves the import surface of the repository's historical `compute_terms.py`
script during migration; it should not be the starting point for new
integrations.

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

## Generating-function derivation

### `derive_generating_function(specification, *, labelled, symbol="S")`

Translate a supported ECS specification into a finite `GFExpression`.
`specification` may be source text or a mapping returned by
`parse_specification`. `labelled=True` applies EGF constructor rules and
`False` applies OGF rules. `symbol` selects the named equation to derive.

```python
from combstruct import derive_generating_function, generating_function_coefficients

expression = derive_generating_function(
    "{B = Sequence(Z), S = Prod(Z,B)}",
    labelled=False,
)

assert generating_function_coefficients(expression, 6) == (0, 1, 1, 1, 1, 1)
```

The supported finite rules are:

- `Union` becomes addition and `Prod` becomes multiplication;
- bounded or unrestricted `Sequence` becomes a finite geometric sum or a
  rational expression;
- labelled `Set` and `Cycle` become exponential and logarithmic expressions,
  with exact finite corrections for cardinality bounds; and
- bounded unlabelled `Set` and `Cycle` use exact finite cycle-index formulas and
  substitutions `_x -> _x^k`.

Named acyclic equations are expanded and memoized. A directly self-recursive
equation that is linear or quadratic under `Union` and `Prod` is solved as a
rational or square-root closed form. The least nonnegative constant solution is
selected when the quadratic equation has two branches, and the formal implicit
function condition must determine that branch uniquely.

A mutually recursive dependency, recursion of degree greater than two,
recursion nested inside another constructor, unrestricted unlabelled `Set` or
`Cycle`, or `PowerSet` raises `UnsupportedGeneratingFunctionDerivation`; those
cases need more general equation solving or an infinite cycle-index AST.
Malformed specifications, missing roots, undefined symbols, and invalid
constructor arity raise `SpecificationError`.

The catalogue-wide contract covers 845 records—367 labelled and 478
unlabelled—including all seven single-equation quadratic `Union`/`Prod`
recursions. It verifies their full stored term prefixes against both the derived
expression and the independent specification term evaluator. The 230 remaining
records partition into 188 recursive systems, 21 unrestricted unlabelled sets,
14 unrestricted unlabelled cycles, and seven power sets.

## Stored generating functions

### `parse_generating_function(source)`

Parse one finite elementary ECS generating-function expression into an
immutable `GFExpression` syntax tree.

```python
from combstruct import GFBinary, parse_generating_function

expression = parse_generating_function("exp(_x)/(1-_x)^2")

assert isinstance(expression, GFBinary)
assert expression.operator == "/"
assert isinstance(expression.right, GFBinary)
assert expression.right.operator == "^"
```

The supported grammar consists of:

- nonnegative integer literals and the Maple variable `_x`;
- parentheses and unary `+` or `-`;
- binary `+`, `-`, `*`, `/`, and right-associative `^`; and
- `exp(expression)` and `ln(expression)`.

The parser covers 913 of the 1,028 nonempty generating-function fields in the
bundled catalogue. It explicitly rejects the other 115 current records: 11
equations, 45 infinite-sum forms, 39 `RootOf` forms, 19 `LambertW` forms, and
one explicit `Complex` form.

`GeneratingFunctionParser(source)` is the stateful parser used by the function
API. Malformed input raises `GeneratingFunctionError`. Valid ECS forms outside
this first grammar raise its subclass `UnsupportedGeneratingFunction`.

### Generating-function syntax-tree types

`GFInteger(value)` stores an integer literal. `GFVariable()` represents `_x`.
`GFUnary(operator, operand)` stores unary `+` or `-`.
`GFBinary(operator, left, right)` stores an arithmetic operation.
`GFFunction(name, argument)` stores an `exp` or `ln` call. `GFExpression` is the
union of these five immutable node types.

### `generating_function_coefficients(source, coefficient_count)`

Expand generating-function text or a parsed `GFExpression` and return an exact
tuple of `fractions.Fraction` coefficients from degree zero through
`coefficient_count - 1`.

```python
from fractions import Fraction

from combstruct import generating_function_coefficients

coefficients = generating_function_coefficients("ln(1/(1-_x))", 5)

assert coefficients == (
    Fraction(0),
    Fraction(1),
    Fraction(1, 2),
    Fraction(1, 3),
    Fraction(1, 4),
)
```

The values are raw formal-series coefficients. They equal counting terms for an
ordinary generating function. For an exponential generating function,
coefficient `n` must be multiplied by `n!`. The function does not silently
choose an interpretation.

The evaluator handles every expression accepted from the current catalogue. It
uses exact recurrences for arithmetic, integer and rational powers, `exp`, and
`ln`; intermediate Laurent series allow removable singularities to cancel.
Nonintegral powers currently require constant coefficient one, `exp` requires
constant coefficient zero, and `ln` requires constant coefficient one. A
parsed expression that violates those exact formal-series conditions raises
`GeneratingFunctionEvaluationError`. A negative `coefficient_count` raises
`ValueError`; a non-integer count or invalid source object raises `TypeError`.

Catalogue-wide tests establish that all 913 parsed functions match their full
stored term prefixes and their `Structure.labeled` flags: 503 are OGFs and 410
are EGFs, with no ambiguous or inconsistent result in this subset. In
particular, ECS 265's coefficients are `1, 6, 21, 56, ...`; applying EGF
normalization produces its stored terms `1, 6, 42, 336, ...`. The 115 special
forms rejected by the parser are not covered by this result.

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
