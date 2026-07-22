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
development version parses and exactly expands the finite elementary subset of
stored generating functions. Extending that work to the remaining special
forms, deriving a generating function from a specification, and finding closed
forms remain later milestones.

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

## Parsing and expanding a stored generating function

`parse_generating_function` parses the finite elementary Maple expressions
found in 913 ECS records:

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

The first grammar supports integers, `_x`, parentheses, unary signs, the five
arithmetic operators `+`, `-`, `*`, `/`, and `^`, plus `exp` and `ln` calls.
Power is right-associative and binds more tightly than unary signs, matching
the stored Maple expressions. The immutable AST uses `GFInteger`,
`GFVariable`, `GFUnary`, `GFBinary`, and `GFFunction`.

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
constant term zero, and `ln` arguments with constant term one.

The catalogue currently has 1,028 nonempty `gf` fields. In addition to the 913
finite elementary expressions, it contains 11 equations and 104 expressions
using infinite sums, `RootOf`, `LambertW`, or explicit complex values. Those
forms raise `UnsupportedGeneratingFunction`; malformed input raises
`GeneratingFunctionError`.

The evaluator deliberately returns coefficients rather than silently deciding
whether an expression is an OGF or EGF. Exhaustive tests compare every stored
term for the 913 parsed records under both interpretations: 503 unlabelled
records match as OGFs and 410 labelled records match as EGFs, with no ambiguous
or inconsistent record in this subset. ECS 265, cited in
[ECS issue #2](https://codeberg.org/ECS/encyclopedia-of-combinatorial-structures/issues/2),
does match EGF semantics: its raw coefficients begin `1, 6, 21, 56`, and
multiplication by `n!` gives the stored terms `1, 6, 42, 336`. The remaining 115
special forms still require separate verification.

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
`python python-tools/compute_terms.py` remains available in this repository
until the maintenance scripts are deliberately migrated to the package.

## Project status and scope

The package API should be considered unstable until the first mature release.
The packaging and first maintenance-tool adoption foundations are now in place:

- the existing exact term evaluator is packaged and documented;
- all canonical ECS records ship with a typed, immutable catalogue API;
- the specification syntax tree and parser have a dedicated public module;
- finite elementary stored generating functions have a dedicated immutable AST,
  parser, and exact coefficient evaluator;
- read-only `python-tools` consumers use the public package, while source-data
  serializers and mutators retain their stricter raw-JSON boundary;
- source and installed-wheel tests cover Python 3.12, 3.13, and 3.14; and
- CI builds and metadata-checks both source and wheel distributions.

Version `0.1.0a0` was published to
[PyPI](https://pypi.org/project/combstruct/0.1.0a0/) on 2026-07-22. The next
milestones remain deliberately incremental:

1. extend parsing and evaluation to additional ECS generating-function forms
   where exact semantics can be specified;
2. derive generating functions from specifications where supported; and
3. add conservative closed-form solving for favorable cases.

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
