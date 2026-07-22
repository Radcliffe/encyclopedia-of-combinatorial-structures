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

Mutually recursive equations use the same API. Here removing `A` leaves the
acyclic definition of `B`; substituting it back produces the quadratic equation
`A = x + A^2`:

```python
from combstruct import derive_generating_function, generating_function_coefficients

expression = derive_generating_function(
    "{A = Union(B,Z), B = Prod(A,A), S = A}",
    labelled=False,
)

assert generating_function_coefficients(expression, 8) == (
    0,
    1,
    1,
    2,
    5,
    14,
    42,
    132,
)
```

The supported finite rules are:

- `Union` becomes addition and `Prod` becomes multiplication;
- bounded or unrestricted `Sequence` becomes a finite geometric sum or a
  rational expression;
- labelled `Set` and `Cycle` become exponential and logarithmic expressions,
  with exact finite corrections for cardinality bounds; and
- bounded unlabelled `Set` and `Cycle` use exact finite cycle-index formulas and
  substitutions `_x -> _x^k`.

Named acyclic equations are expanded and memoized. A recursive component under
`Union` and `Prod` is solved when removing one feedback symbol makes its other
equations acyclic and their substitution is linear or quadratic in that symbol.
The least nonnegative constant solution is selected when the quadratic equation
has two branches, and the formal implicit-function condition must determine
that branch uniquely.

A component requiring multiple feedback symbols, recursion of degree greater
than two, recursion nested inside another constructor, unrestricted unlabelled
`Set` or `Cycle`, or `PowerSet` raises
`UnsupportedGeneratingFunctionDerivation`; those cases need more general
equation solving or an infinite cycle-index AST. Malformed specifications,
missing roots, undefined symbols, and invalid constructor arity raise
`SpecificationError`.

The catalogue-wide contract covers 888 records—367 labelled and 521
unlabelled—including 50 recursive `Union`/`Prod` records. It verifies their full
stored term prefixes against both the derived expression and the independent
specification term evaluator. The 187 remaining records partition into 145
recursive systems, 21 unrestricted unlabelled sets, 14 unrestricted unlabelled
cycles, and seven power sets.

## Stored generating functions

### `parse_generating_function(source)`

Parse one supported ECS generating-function expression, implicit equation, or
equation system into an immutable `GFParseResult` syntax tree.

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
- binary `+`, `-`, `*`, `/`, and right-associative `^`;
- `exp(expression)`, `ln(expression)`, and `LambertW(expression)`;
- unselected `RootOf(expression)` equations, with the Maple-local variable
  `_Z` scoped to that equation;
- indexed `Sum(expression,j[k]=1..infinity)` forms, including
  `numtheory:-phi(j[k])`;
- alternate `Sum_{j=m..inf} expression` and `Sum_{j>m} expression` forms,
  including `phi(j)`;
- alternate `Product_{k>m} expression` forms and lexically bound indexed
  coefficients such as `a_k`;
- the exact positive and alternating four-term ellipsis patterns used by ECS 56
  and 57, normalized to `GFInfiniteSum`;
- the one-argument `Complex(expression)` form used by the catalogue;
- the variable spelling `x`, the function alias `log`, and named formal-series
  calls such as `A(x^2)` inside implicit equations, including comma-separated
  systems; and
- one optional final Maple statement period.

The parser covers all 1,028 nonempty generating-function fields in the bundled
catalogue: all 913 finite elementary forms, all 19 `LambertW` forms, all 39
unselected `RootOf` forms, all 45 Maple-form indexed infinite sums, and the one
`Complex` form, plus ten individual implicit equations in ECS 1, 43, 44, 45,
56, 57, 79, 89, 91, and 95 and the three-equation system in ECS 118. ECS 44 is
the symbolic infinite-product equation. Arbitrary ellipses that do not match
either fully determined catalogue pattern remain unsupported.

`GeneratingFunctionParser(source)` is the stateful parser used by the function
API. Malformed input raises `GeneratingFunctionError`. Valid ECS forms outside
the supported grammar raise its subclass `UnsupportedGeneratingFunction`.

### Generating-function syntax-tree types

`GFInteger(value)` stores an integer literal. `GFVariable()` represents `_x`,
while `GFVariable("_Z")` represents the root-local variable.
`GFUnary(operator, operand)` stores unary `+` or `-`.
`GFBinary(operator, left, right)` stores an arithmetic operation.
`GFFunction(name, argument)` stores an `exp`, `ln`, or `LambertW` call.
`GFSeriesCall(name, argument)` stores a named formal-series call such as
`A(x^2)`; the spellings `x` and `_x` both become `GFVariable()` and `log`
becomes `GFFunction("ln", argument)`.
`GFRootOf(equation)` stores an unselected root equation whose local variable is
`GFVariable("_Z")`. `GFIndex(level)` stores `j[level]`, `GFTotient(index)`
stores either totient spelling, and `GFIndexedCoefficient(name, index)` stores
an indexed symbolic coefficient such as `a_k`.
`GFInfiniteSum(summand, index, lower_bound=1)` stores an indexed sum through
infinity, while `GFInfiniteProduct(factor, index, lower_bound=1)` stores a
symbolic product through infinity. Alternate binder names are normalized to
lexically scoped `GFIndex` levels.
`GFComplex(value)` stores a one-argument Maple complex constructor.
`GFExpression` is the union of these thirteen immutable expression-node types.
`GFEquation(left, right)` stores one implicit equality,
`GFEquationSystem(equations)` stores an ordered tuple of equations, and
`GFParseResult` is the union of `GFExpression`, `GFEquation`, and
`GFEquationSystem`. Sum and product indices are lexically scoped within each
equation: a body may reference its own index and outer indices, while unbound
indices and nested rebinding of the same normalized level are rejected.

```python
from combstruct import GFBinary, GFRootOf, GFVariable, parse_generating_function

root = parse_generating_function("RootOf(_Z-_x)")

assert root == GFRootOf(GFBinary("-", GFVariable("_Z"), GFVariable()))
```

```python
from combstruct import GFInfiniteSum, GFTotient, parse_generating_function

indexed_sum = parse_generating_function(
    "Sum(numtheory:-phi(j[1])*_x^j[1]/j[1],j[1]=1..infinity)"
)

assert isinstance(indexed_sum, GFInfiniteSum)
assert indexed_sum.index.level == 1
assert isinstance(indexed_sum.summand.left.left, GFTotient)

later_sum = parse_generating_function("Sum_{j>2} x^j/j")

assert isinstance(later_sum, GFInfiniteSum)
assert later_sum.lower_bound == 3
```

```python
from combstruct import GFEquation, GFIndexedCoefficient, GFInfiniteProduct

product_equation = parse_generating_function(
    "Product_{k>0} 1/(1-x^k)^a_k = 1+x+2*Sum_{k>1} a_k*x^k."
)

assert isinstance(product_equation, GFEquation)
assert isinstance(product_equation.left, GFInfiniteProduct)
assert isinstance(product_equation.left.factor.right.right, GFIndexedCoefficient)
```

```python
from combstruct import GFComplex, parse_generating_function

complex_value = parse_generating_function("Complex(-1/2)")

assert isinstance(complex_value, GFComplex)
```

```python
from combstruct import GFEquation, GFSeriesCall, GFVariable, parse_generating_function

equation = parse_generating_function("A(x)=x+(A(x)^2+A(x^2))/2")

assert isinstance(equation, GFEquation)
assert equation.left == GFSeriesCall("A", GFVariable())

patterned = parse_generating_function(
    "A(x)=x*exp(A(x)-A(x^2)/2+A(x^3)/3-A(x^4)/4+...)"
)

assert isinstance(patterned, GFEquation)
assert isinstance(patterned.right, GFBinary)
assert isinstance(patterned.right.right.argument, GFInfiniteSum)
```

```python
from combstruct import GFEquationSystem

system = parse_generating_function("A(x)=x,B(x)=A(x)")

assert isinstance(system, GFEquationSystem)
assert len(system.equations) == 2
```

### `generating_function_coefficients(source, coefficient_count, *, symbol=None)`

Expand generating-function text or a parsed `GFParseResult` and return an exact
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

Indexed sums use the same API and return exact rational coefficients:

```python
from fractions import Fraction

from combstruct import generating_function_coefficients

coefficients = generating_function_coefficients(
    "Sum(_x^j[1]/j[1],j[1]=1..infinity)",
    5,
)

assert coefficients == (
    Fraction(0),
    Fraction(1),
    Fraction(1, 2),
    Fraction(1, 3),
    Fraction(1, 4),
)
```

The shifted principal `LambertW` form used by ECS 69 is also exact:

```python
coefficients = generating_function_coefficients(
    "-LambertW(-1/2*exp(-1/2+1/2*_x))-1/2+1/2*_x",
    6,
)

assert coefficients == (
    Fraction(0),
    Fraction(1),
    Fraction(1, 2),
    Fraction(2, 3),
    Fraction(13, 12),
    Fraction(59, 30),
)
```

The values are raw formal-series coefficients. They equal counting terms for an
ordinary generating function. For an exponential generating function,
coefficient `n` must be multiplied by `n!`. The function does not silently
choose an interpretation.

The evaluator uses exact recurrences for arithmetic, integer and rational
powers, `exp`, `ln`, principal `LambertW`, and coefficientwise-finite indexed
sums; intermediate Laurent series allow removable singularities to cancel.
Nonintegral powers currently require constant coefficient one, `exp` requires
constant coefficient zero, and `ln` requires constant coefficient one.
`LambertW` uses its exact formal series
`sum((-k)^(k-1) * z^k / k!, k >= 1)` at zero. It also recognizes
`LambertW(c*exp(c+h))` for a rational principal-branch center `c > -1`, `c != 0`,
and a zero-constant formal series `h`. If `W=c+u`, the equation becomes
`ln(1+u/c)+u=h`, providing an exact rational recurrence without representing
the transcendental constant `exp(c)`. The branch point `c=-1` and lower centers
are rejected. All 19 parsed catalogue `LambertW` fields meet the zero-centered
or recognized-shift contract. A parsed expression that violates these exact
formal-series conditions raises
`GeneratingFunctionEvaluationError`. A negative `coefficient_count` raises
`ValueError`; a non-integer count or invalid source object raises `TypeError`.
Named-series assignments of the form `A(x)=expression` are expanded by exact,
simultaneous fixed-point iteration. The solver selects the combinatorial branch
reached from zero series and returns only after every requested coefficient
stabilizes exactly. It then constructs the graph of dependencies that can
affect the same positive-degree coefficient. The graph must be acyclic, proving
that every recursive cycle introduces a positive degree delay; one or several
sample starting values are not treated as a proof. Equation results receive the
same negative-power check as standalone expressions. Named-series composition
requires a zero-constant argument. In a multi-equation system, `symbol` is
required to select the returned series:

```python
from combstruct import generating_function_coefficients

coefficients = generating_function_coefficients(
    "A(x)=x+(A(x)^2+A(x^2))/2",
    10,
)

assert coefficients == (0, 1, 1, 1, 2, 3, 6, 11, 23, 46)
```

This contract solves ECS 1, 43, 45, 56, and 57, as well as the simultaneous
`B`, `C`, and `S` assignments in ECS 118. It includes indexed infinite sums
whose coefficientwise finiteness follows after substituting the current named
series approximants. ECS 79 and 91 have same-degree feedback and do not
stabilize under this iteration; ECS 89 is not an assignment, ECS 44 is a
symbolic-product coefficient equation, and ECS 95 does not provide a
coefficientwise-finite sum at its implied constant term. Those forms raise
`GeneratingFunctionEvaluationError` rather than selecting an unjustified
solution. Standalone `GFSeriesCall`, `GFInfiniteProduct`, and
`GFIndexedCoefficient` values likewise remain explicit boundaries.

Catalogue-wide tests establish that 983 parsed functions match their full
stored term prefixes and their `Structure.labeled` flags: 554 are OGFs and 429
are EGFs, with no ambiguous or inconsistent result in this subset. In
particular, ECS 265's coefficients are `1, 6, 21, 56, ...`; applying EGF
normalization produces its stored terms `1, 6, 42, 336, ...`. ECS 69 uses the
recognized center `c=-1/2`; exact expansion reproduces all 21 of its stored EGF
terms. The 45 non-evaluable fields consist of 39 parsed `RootOf` fields without
a branch selector, the one `Complex` field requiring complex formal-series
arithmetic, and five individual equations requiring stronger solvers (ECS 44,
79, 89, 91, and 95). There are no remaining catalogue fields outside the parser
grammar.

Maple documents unselected `RootOf` as representing unspecified roots and uses
explicit selectors to identify one root. Because the ECS strings do not contain
selectors, coefficient evaluation raises `GeneratingFunctionEvaluationError`
with a branch-specific message rather than inferring a root from catalogue
terms. See Maple's
[`RootOf` documentation](https://www.maplesoft.com/support/help/Maple/view.aspx?path=RootOf)
and
[`indexed RootOf` rules](https://www.maplesoft.com/support/help/Maple/view.aspx?path=RootOf%2Findexed).

Coefficient evaluation of `GFInfiniteSum` requires a proof that its summand has
constant coefficient zero and every occurrence of `_x` is scaled by the bound
index. Coefficient `n` can then receive contributions only from indices at or
above `lower_bound` that divide `n`, so the infinite range reduces to a finite
exact sum. Nested sums also account for the proven product of their outer index
scales. All 45 exactly evaluable catalogue indexed-sum records meet this
contract. A sum that does not meet it raises `GeneratingFunctionEvaluationError`
rather than being silently truncated.

`GFInfiniteProduct` and `GFIndexedCoefficient` faithfully retain ECS 44's
symbolic coefficient equation. Their coefficient evaluation raises
`GeneratingFunctionEvaluationError` until a symbolic-product equation solver is
available.

`GFComplex` coefficient evaluation also raises
`GeneratingFunctionEvaluationError` until exact complex formal-series
arithmetic is available. Maple defines one-argument `Complex(x)` as the purely
imaginary value `I*x`; see the official
[`Complex` constructor documentation](https://www.maplesoft.com/support/help/Maple/view.aspx?path=complex).

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
