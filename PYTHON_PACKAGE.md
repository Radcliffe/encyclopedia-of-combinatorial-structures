# combstruct

`combstruct` is the developing Python interface to the
[Encyclopedia of Combinatorial Structures](https://combstruct.netlify.app/)
(ECS). It is intended to make the ECS data and its Maple
`combstruct`-style specifications useful from ordinary Python programs.

This is a pre-alpha package extraction. The first release does
two things that the repository's existing Python tools already do:

- parse ECS specifications containing `Union`, `Prod`, `Sequence`, `Set`,
  `Cycle`, and `PowerSet`, including ECS cardinality constraints; and
- compute exact integer terms from a specification, using exponential
  generating-function semantics for labelled structures and ordinary
  generating-function semantics for unlabelled structures.

The distribution also contains the canonical ECS records. The current
development version parses the finite elementary and `LambertW` subset of
stored generating functions and exactly expands principal `LambertW`
compositions at zero. It also derives finite generating-function
expressions from acyclic specifications and closed rational or square-root
expressions for a first class of recursive systems. Extending that work to more
general recursive systems and infinite cycle-index forms, parsing the remaining
special forms, and finding further closed forms remain later milestones.

## Installation

Install the released pre-alpha from PyPI:

```console
python -m pip install "combstruct==0.1.0a0"
```

The initial package requires Python 3.12 or newer and has no runtime
dependencies outside the Python standard library.

Contributors who need an editable source checkout should follow
[`docs/development.md`](https://codeberg.org/ECS/encyclopedia-of-combinatorial-structures/src/branch/main/docs/development.md).

The installed version is available as `combstruct.__version__`.

## Computing terms

Use `compute_terms` with an ECS specification, the labelled/unlabelled
universe, and the number of terms beginning at size zero:

```python
from combstruct import compute_terms

catalan = compute_terms(
    "{S = Union(Epsilon,Prod(Z,S,S))}",
    labelled=False,
    term_count=12,
)

assert catalan == [1, 1, 2, 5, 14, 42, 132, 429, 1430, 4862, 16796, 58786]
```

All internal arithmetic is exact. A specification that is malformed,
undefined, or outside the evaluator's supported constructions raises
`SpecificationError` or its subclass `UnsupportedConstruction`.

## Parsing a specification

`parse_specification` produces a mapping of equation names to small immutable
syntax trees. References are represented by `Reference`, constructor calls by
`Constructor`, and constructor cardinality bounds by `Cardinality`:

```python
from combstruct import Constructor, parse_specification

equations = parse_specification("{S = Sequence(Z,card <= 3)}")
root = equations["S"]

assert isinstance(root, Constructor)
assert root.name == "Sequence"
assert root.cardinality.maximum == 3
```

The parser accepts the syntax found in the current ECS catalogue, including
multiple mutually recursive equations and indexed symbols such as `A[1]`.
`Parser` remains available for callers that need to construct a parser object
explicitly. The AST and parser are defined in `combstruct.specification`; their
top-level imports are the recommended stable API.

## Deriving a generating function

`derive_generating_function` translates a supported specification into the same
immutable `GFExpression` tree used by the stored-function parser:

```python
from fractions import Fraction

from combstruct import derive_generating_function, generating_function_coefficients

expression = derive_generating_function(
    "{A = Sequence(Z), S = Prod(Z,A)}",
    labelled=False,
)
coefficients = generating_function_coefficients(expression, 6)

assert coefficients == (
    Fraction(0),
    Fraction(1),
    Fraction(1),
    Fraction(1),
    Fraction(1),
    Fraction(1),
)
```

The `labelled` argument selects exponential- or ordinary-generating-function
constructor rules. The finite derivation supports `Union`, `Prod`, and
`Sequence`; labelled `Set` and `Cycle`; and bounded unlabelled `Set` and
`Cycle`, including the required cycle-index substitutions. It follows named
acyclic equations and accepts either source text or a mapping returned by
`parse_specification`. A recursive component built from `Union` and `Prod` is
also solved when removing one feedback symbol leaves acyclic equations whose
expansion is linear or quadratic in that symbol. This produces a rational or
square-root closed form for both direct and mutually recursive specifications.
For example, the Catalan specification derives its algebraic generating
function directly:

```python
from combstruct import derive_generating_function, generating_function_coefficients

catalan_gf = derive_generating_function(
    "{S = Union(Z,Prod(S,S))}",
    labelled=False,
)

assert generating_function_coefficients(catalan_gf, 8) == (
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

Higher-degree systems, components requiring more than one feedback symbol,
recursion nested inside another constructor, unrestricted unlabelled `Set` and
`Cycle`, and `PowerSet` raise `UnsupportedGeneratingFunctionDerivation` because
their next derivation step requires more general equation solving or an infinite
cycle-index representation. In the current catalogue, 888 specifications have
a supported finite derivation: 367 labelled EGFs and 521 unlabelled OGFs.
Exhaustive tests compare every derived coefficient with both the independent
term evaluator and the complete stored term prefix. The remaining partition is
145 recursive specifications, 21 unrestricted unlabelled sets, 14 unrestricted
unlabelled cycles, and seven power sets.

## Parsing and expanding a stored generating function

`parse_generating_function` parses the supported finite Maple expressions found
in 932 ECS records:

```python
from combstruct import GFBinary, GFInteger, GFVariable, parse_generating_function

expression = parse_generating_function("1/(1-_x)^2")

assert isinstance(expression, GFBinary)
assert expression.operator == "/"
assert expression.left == GFInteger(1)
assert expression.right == GFBinary(
    "^",
    GFBinary("-", GFInteger(1), GFVariable()),
    GFInteger(2),
)
```

The grammar supports integers, `_x`, parentheses, unary signs, the five
arithmetic operators `+`, `-`, `*`, `/`, and `^`, plus `exp`, `ln`, and
`LambertW` calls. Power is right-associative and binds more tightly than unary
signs, matching the stored Maple expressions. The immutable AST uses
`GFInteger`, `GFVariable`, `GFUnary`, `GFBinary`, and `GFFunction`.

`generating_function_coefficients` expands either source text or an already
parsed expression using exact `fractions.Fraction` arithmetic:

```python
from fractions import Fraction

from combstruct import generating_function_coefficients

coefficients = generating_function_coefficients("exp(_x)", 6)

assert coefficients == (
    Fraction(1),
    Fraction(1),
    Fraction(1, 2),
    Fraction(1, 6),
    Fraction(1, 24),
    Fraction(1, 120),
)
```

These are raw series coefficients. For an ordinary generating function,
coefficient `n` is the counting term. For an exponential generating function,
multiply coefficient `n` by `n!`. The evaluator supports the exact analytic
conditions used by the finite catalogue expressions, including removable
singularities, square roots with constant term one, `exp` arguments with
constant term zero, `ln` arguments with constant term one, and the principal
formal `LambertW` series when its argument has constant term zero. Its exact
coefficients use
`W(z) = sum((-k)^(k-1) * z^k / k!, k >= 1)` without a numerical dependency.

The catalogue currently has 1,028 nonempty `gf` fields. The parser accepts all
913 finite elementary expressions and all 19 `LambertW` expressions. It rejects
the remaining 96 fields: 11 equations, 45 infinite-sum forms, 39 `RootOf`
forms, and one explicit complex expression. Those forms raise
`UnsupportedGeneratingFunction`; malformed input raises
`GeneratingFunctionError`.

The evaluator deliberately returns coefficients rather than silently deciding
whether an expression is an OGF or EGF. Exhaustive tests compare every stored
term for 931 exactly evaluable records under both interpretations: 503
unlabelled records match as OGFs and 428 labelled records match as EGFs, with no
ambiguous or inconsistent record in this subset. ECS 265, cited in
[ECS issue #2](https://codeberg.org/ECS/encyclopedia-of-combinatorial-structures/issues/2),
does match EGF semantics: its raw coefficients begin `1, 6, 21, 56`, and
multiplication by `n!` gives the stored terms `1, 6, 42, 336`. ECS 69 is parsed
but its `LambertW` argument has a nonzero transcendental constant; exact
expansion therefore raises `GeneratingFunctionEvaluationError` until a shifted
branch representation is defined. Together with the 96 parser exclusions, it
is one of 97 fields still requiring separate exact verification.

## Using the ECS catalogue

`get_structure` loads an immutable, typed `Structure` from the canonical ECS
catalogue:

```python
from combstruct import compute_terms, get_structure

structure = get_structure(56)
terms = compute_terms(
    structure.specification,
    labelled=structure.labeled,
    term_count=20,
    symbol=structure.symbol,
)
```

The model contains the ECS identifier, name, description, specification,
labelled flag, root symbol, stored terms, references, and whichever symbolic
results are available. Terms and references are tuples, and absent symbolic
results are `None`. The ECS source fields have descriptive Python names:

| ECS field | `Structure` attribute |
| --- | --- |
| `gf` | `generating_function` |
| `rec` | `recurrence` |
| `closedform` | `closed_form` |
| `equiv` | `asymptotic_equivalent` |

Use `iter_structures()` to traverse the catalogue in ECS identifier order, or
construct `Catalog(path)` to read either canonical per-record JSON files or a
historical consolidated ECS JSON mapping:

```python
from itertools import islice

from combstruct import Catalog, iter_structures

assert len(Catalog()) == 1075
first_three = [structure.id for structure in islice(iter_structures(), 3)]
assert first_three == [1, 2, 3]
```

`Structure.as_record()` returns a mutable dictionary with the original ECS
field names. The low-level `default_dataset()` and `load_record()` functions
remain available for compatibility with the repository's existing scripts.

## Command line

Installation provides a `combstruct` command. It can evaluate a literal
specification:

```console
combstruct --spec '{S = Sequence(Z)}' --unlabelled --terms 10 --plain
```

or load a bundled ECS record by identifier:

```console
combstruct --id 56 --terms 30
```

Run `combstruct --help` for all current options. The historical command
`python python-tools/compute_terms.py` remains available as a compatibility
wrapper around the package entry point.

## Project status and scope

The package API should be considered unstable until the first mature release.
The packaging and first maintenance-tool adoption foundations are now in place:

- the existing exact term evaluator is packaged and documented;
- all canonical ECS records ship with a typed, immutable catalogue API;
- the specification syntax tree and parser have a dedicated public module;
- 888 specifications derive finite exact generating-function expressions,
  including 50 recursive rational or square-root closed forms, whose
  coefficients agree with the independent term evaluator;
- finite elementary and `LambertW` generating functions have a dedicated
  immutable AST, parser, and exact coefficient evaluator for principal
  compositions at zero;
- read-only `python-tools` consumers use the public package, while source-data
  serializers and mutators retain their stricter raw-JSON boundary;
- source and installed-wheel tests cover Python 3.12, 3.13, and 3.14; and
- CI builds and metadata-checks both source and wheel distributions.

Version `0.1.0a0` was published to
[PyPI](https://pypi.org/project/combstruct/0.1.0a0/) on 2026-07-22. The next
milestones remain deliberately incremental:

1. extend equation solving beyond recursive components reducible through one
   linear or quadratic feedback symbol and represent infinite unlabelled
   cycle-index forms;
2. extend parsing and evaluation to additional stored generating-function
   forms where exact semantics can be specified; and
3. add further conservative closed-form solving where branch semantics can be
   proved.

The Python code and underlying ECS catalogue are distributed under the GNU
Lesser General Public License, version 2.1 only. OEIS-derived names,
descriptions, and their later adaptations are distributed under Creative
Commons Attribution-ShareAlike 4.0. The distribution metadata uses
`LGPL-2.1-only AND CC-BY-SA-4.0`; see `LICENSE.md`,
`LICENSES/CC-BY-SA-4.0.txt`, and `NOTICE.md` for component boundaries and
attribution.

## Data provenance

The bundled catalogue derives from Jérémie Lumbroso's LGPL-2.1-licensed
[`encyclopedia-of-combinatorial-structures-data`](https://github.com/jlumbroso/encyclopedia-of-combinatorial-structures-data)
repository and ultimately from the INRIA Algorithms Project's ECS data. The
original ECS was started by Stéphanie Petit-Halajda in 1998 and incorporated
work by many Algorithms Project contributors.

Structure names and descriptions were enriched from corresponding
[OEIS](https://oeis.org/) entries. OEIS makes its content available under CC
BY-SA 4.0 and requests attribution to The On-Line Encyclopedia of Integer
Sequences. See `NOTICE.md` for the exact historical counts, provenance, and
attribution.

Contributor build and release instructions are in
[`docs/releasing.md`](https://codeberg.org/ECS/encyclopedia-of-combinatorial-structures/src/branch/main/docs/releasing.md).
The complete public API is described in
[`docs/api.md`](https://codeberg.org/ECS/encyclopedia-of-combinatorial-structures/src/branch/main/docs/api.md).
Contributor setup and quality checks are in
[`docs/development.md`](https://codeberg.org/ECS/encyclopedia-of-combinatorial-structures/src/branch/main/docs/development.md).
The first release record is in
[`docs/release-readiness.md`](https://codeberg.org/ECS/encyclopedia-of-combinatorial-structures/src/branch/main/docs/release-readiness.md).
