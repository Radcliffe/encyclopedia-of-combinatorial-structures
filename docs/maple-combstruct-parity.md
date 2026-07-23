# Maple `combstruct` parity

This document defines feature parity with Maple's `combstruct` package as a
testable compatibility target for the Python package. It tracks mathematical
capabilities and command behavior; it does not require reproducing Maple's
worksheet UI or its exact expression display format.

The primary source is Maplesoft's
[`combstruct` overview](https://www.maplesoft.com/support/help/Maple/view.aspx?path=combstruct).
Maple documents twelve package commands:

`agfeqns`, `agfmomentsolve`, `agfseries`, `allstructs`, `count`, `draw`,
`finished`, `gfeqns`, `gfseries`, `gfsolve`, `iterstructs`, and `nextstruct`.

The package overview also treats
[grammar specifications](https://www.maplesoft.com/support/help/Maple/view.aspx?path=combstruct%2Fspecification),
[predefined structures](https://www.maplesoft.com/support/help/Maple/view.aspx?path=combstruct%2Fstructures),
and algorithm options as part of the package surface.

## Compatibility rules

- Every operation must make the universe explicit: `labelled=True` means
  labeled classes and exponential generating functions; `labelled=False`
  means unlabeled classes and ordinary generating functions.
- Counting operations return object counts. Series operations return
  generating-function coefficients, so labeled coefficient `n` is
  `count(n) / n!` while an unlabeled coefficient is `count(n)`.
- Uniform random generation means every object of the requested size has the
  same probability. Seeded random sources must produce reproducible results.
- Unsupported classes must raise a specific exception. They must not silently
  use the wrong labeled/unlabeled rule, truncate an infinite construction, or
  choose an arbitrary generating-function branch.
- A feature is complete only when its public API, mathematical behavior,
  documentation, and tests are all present.

## Current parity matrix

| Maple surface | Python status | Remaining compatibility work |
| --- | --- | --- |
| Grammar specifications | Partial | All documented constructors and cardinality bounds parse, count, and enumerate; named Epsilon markers and linear attribute grammars with atomic symbolic costs are supported. Expand attribute rules through `Subst`. |
| `count` | Complete | Grammar-defined and predefined classes, defaults, `Subst`, and `allsizes` are supported with explicit labeled/unlabeled semantics. |
| `gfseries` | Partial | All grammar symbols return truncated OGF/EGF coefficients; add marker tags and multivariate series. |
| `gfsolve` | Partial | Finite acyclic and selected linear/quadratic recursive systems are supported; add general equation output and broader formal-series solving. |
| `gfeqns` | Partial | Unsolved named OGF/EGF equations cover every constructor and all 1,075 catalog grammars, including infinite cycle-index forms and products of Epsilon marker variables; support arbitrary nonmonomial tag values and multivariate evaluation. |
| `allstructs` | Complete | Grammar-defined and predefined classes have exhaustive generation, including `Subst`, Epsilon marker preservation, defaults, and `allsizes`. |
| `iterstructs`, `nextstruct`, `finished` | Complete | Both kinds of class use shared explicit iterator state and preserve named Epsilon markers. |
| `draw` | Partial | Exact count-directed sampling covers recursive Union/Prod/Sequence grammars, Set/PowerSet, labeled Cycle, top-level and product-nested unlabeled Cycle, substitution-expanded forms, and every predefined family. Add component-type ranking for an unlabeled Cycle nested inside Set/PowerSet. |
| Predefined structures | Complete | `Combination`/`Subset`, `Permutation`, `Partition`, and `Composition` count, enumerate, iterate, and draw with documented defaults and `allsizes`. |
| `agfeqns`, `agfseries` | Partial | Linear attribute grammars, atomic constants and coefficients, recursive defaults, multiple markers, acyclic cross-attribute dependencies, symbolic equations, and exact joint OGF/EGF prefixes are supported. Add `Subst` and recurrence-based scaling. |
| `agfmomentsolve` | Partial | Exact truncated univariate factorial and mixed-moment series are supported. Add Maple-style closed-form solving and recoverable differentiated equation output. |
| Algorithm options | Partial | `draw` exposes validated `auto`, `counted`, and `enumerate` selection. Add resource limits and options for series/solver algorithms where useful. |

## Dependency-ordered implementation plan

1. **Command-level counting and generating functions.** Provide `count`,
   `gfseries`, and `gfsolve` names over the existing exact engines, with tests
   that distinguish OGF from EGF coefficients.
2. **Combinatorial object model and exhaustive grammar generation.** Define
   immutable values for atoms and constructor nodes, then implement
   `allstructs` and the iterator command family for finite sizes.
3. **Predefined finite structures.** Implement combinations/subsets,
   permutations, integer partitions, and compositions across count,
   enumeration, and iteration, including `allsizes`.
4. **Uniform random generation.** Implement `draw` using exact constructor
   counts and injected random sources for grammars and predefined structures.
   Verify distribution on small classes and reproducibility under a seed.
5. **Generating-function equations.** Add `gfeqns`, including symbolic
   infinite cycle-index forms, and extend `gfsolve` from the equation layer.
6. **Tags and attribute grammars.** Add tagged epsilon atoms, multivariate
   `gfseries`, `agfeqns`, `agfseries`, and moment solving in that order.
7. **Options, performance, and conformance.** Add algorithm/resource options,
   Maple example conformance tests, complexity benchmarks, and documentation
   for intentional Python-interface differences.

## First completed slice

The package now exposes:

- `count(specification, *, size, labelled, symbol="S")`, which returns the
  integer number of objects of one size;
- `gfseries(specification, *, labelled, term_count)`, which returns a mapping
  from every grammar symbol to truncated `Fraction` coefficients; and
- `gfsolve(specification, *, labelled, symbol="S")`, the command-level name
  for the existing supported generating-function solver.

These are intentionally keyword-explicit about labeled versus unlabeled
semantics. The behavior corresponds to Maplesoft's
[`count`/`draw` documentation](https://www.maplesoft.com/support/help/Maple/view.aspx?path=combstruct%2Fdraw)
and
[`gfseries` documentation](https://www.maplesoft.com/support/help/Maple/view.aspx?path=combstruct%2Fgfseries).

## Second completed slice

Grammar-defined classes now expose exact-size exhaustive generation:

- immutable `AtomObject`, `EpsilonObject`, and `ConstructionObject` values;
- `allstructs(specification, *, size, labelled, symbol="S")`;
- `iterstructs(...)`, which returns a Python iterator with explicit mutable
  position state; and
- `nextstruct(iterator)` and `finished(iterator)`.

Union alternatives carry a branch number so the union remains disjoint even
when two alternatives produce structurally equal values. Unordered Set and
PowerSet children and rotations of Cycle children are canonicalized, while
Prod and Sequence preserve order. Labeled objects carry the labels `1..n` on
their atoms.

The enumeration tests compare the number of distinct generated objects with
`count` across recursive trees, labeled products/sequences/sets/cycles, and
unlabeled multisets/power sets/cycles. PowerSet cardinality constraints are
now supported by the counting engine as well as enumeration.

Maple also documents `Subst(A,B)` as a grammar constructor. Its implementation
is described in the fifth completed slice below.

## Third completed slice

The four predefined structure families now share the same command surface:

- `Combination(elements)` and its alias `Subset`;
- `Permutation(elements)`;
- `Partition(total)`; and
- `Composition(total)`.

Combination and Permutation accept a finite iterable or a nonnegative integer
`n`, which expands to `1..n`. Their `size` is the selected sequence length.
For Partition and Composition, `size` is the number of positive summands.

The default is `"allsizes"` for Combination, Partition, and Composition.
Permutation defaults to the full input length. Passing `size="allsizes"`
explicitly enumerates partial permutations beginning with the empty
permutation, matching Maplesoft's documented example. Repeated input elements
are handled as multiset elements, so duplicate-looking outputs are not counted
twice.

## Fourth completed slice

`draw(...)` now selects an exact uniform rank from `allstructs`. It supports
grammar-defined classes, all four predefined structure families, their
defaults, and `"allsizes"`. Callers can inject a seeded `random.Random`
instance for reproducible output; the default uses `SystemRandom`.

This establishes correct uniform behavior, but the implementation currently
materializes every object. Count-directed recursive unranking remains a
performance requirement so large Maple examples can be sampled without
exhaustive generation.

## Fifth completed slice

`Subst(A,B)` is supported across counting, `gfseries`, `gfsolve`,
`allstructs`, the iterator family, and `draw`. Maple defines this as B-objects
whose atoms are replaced by A-objects.

The implementation expands substitution at the grammar level by cloning any
referenced B productions and replacing their terminal atoms. This preserves
the constructor that carries unlabeled symmetry: substituting into `Set`
remains a multiset construction, substituting into `Cycle` remains cyclic, and
recursive outer grammars remain recursive after cloning. It avoids the
incorrect shortcut of treating every unlabeled substitution as ordinary
generating-function composition.

As required by Maple's grammar rules, either argument producing a size-zero
object is rejected. Nested substitutions, named recursive outer grammars,
labeled partitional label distribution, and OGF/EGF derivation are covered by
conformance tests.

## Sixth completed slice

`gfeqns(specification, *, labelled)` returns a `GFEquationSystem` containing
one unsolved equation for every named production. References remain
`GFSeriesCall` nodes rather than being expanded or solved.

The builder covers:

- distinct labeled EGF and unlabeled OGF constructor rules;
- finite cardinality corrections;
- unrestricted unlabeled Set as an exponential of a cycle-index sum;
- unrestricted unlabeled Cycle as a totient-weighted logarithmic sum;
- unrestricted unlabeled PowerSet as an alternating cycle-index sum; and
- `Subst(A,B)` as formal-series composition `B(A(x))`.

All 1,075 catalog specifications build equation systems. A coefficient audit
independently expanded 1,050 systems through their complete stored prefixes
with no mismatches. The remaining 25 systems have nonlinear nonzero constant
branches that the equation-system coefficient evaluator intentionally refuses
without an explicit branch selector; their grammar counts remain available
through `count` and `gfseries`.

## Seventh completed slice

Named productions defined directly as `Epsilon` now remain visible in
generated object values as `EpsilonObject(tag=production_name)`. This preserves
size-zero derivation markers across `allstructs`, the iterator family, and
`draw` without changing object size.

`gfeqns(..., tags={"u": "leaf"})` can replace one or more named Epsilon
productions with independent symbolic variables. Tag names and marker
productions are validated and reserved size-variable names are rejected.
Assigning one marker under multiple variables multiplies their weights,
covering Maple tags such as `u*v`.

These systems are currently symbolic: the coefficient engine remains
univariate. Multivariate coefficient extraction and arbitrary nonmonomial tag
values remain beyond this symbolic marker layer.

## Eighth completed slice

The package now parses and validates Maple-style linear attribute grammars.
Rules mirror `Union`, `Prod`, `Set`, `PowerSet`, `Sequence`, and `Cycle`;
substructure attributes and the predefined `size` can appear with integer
linear coefficients. Missing rules receive the documented recursive default,
and multiple attributes each have a unique marker variable.

`agfeqns` produces symbolic multivariate equations with argument
transformations such as `T(x*u,u)` for size-dependent recursive attributes.
The labeled path uses EGF constructor rules, while the unlabeled path applies
cycle-index substitutions to the size variable and every marker variable.

`agfseries` returns exact finite joint distributions as OGF or EGF
coefficients. `agfmomentsolve` derives every mixed factorial-moment series
through a requested order by differentiating those distributions and setting
marker variables to one.

The current series and moment baseline uses exhaustive object generation.
Direct multivariate coefficient recurrences, attribute expansion through
`Subst`, and closed-form moment solving remain before these commands reach
full parity.

## Ninth completed slice

Attribute rules now accept Maple's documented atomic constants and
coefficients. For example, `sq+mul` remains symbolic in `agfeqns`, while
`mul*cost(T)` becomes the marker substitution `u^mul` in a recursive series
argument.

Exact `agfseries` and `agfmomentsolve` calls bind those names through an
explicit integer `parameters` mapping. Missing, unknown, conflicting, Boolean,
or otherwise noninteger parameter values are rejected rather than producing
ambiguous exponent keys. Symbolic equation systems expose their required
parameter names for inspection.

## Tenth completed slice

`draw(..., algorithm="auto")` now uses exact constructor counts to sample
without exhaustive generation for terminals, recursive named productions,
Union, Prod, Sequence, substitution-expanded grammars, and labeled Set and
Cycle. Branches and size compositions are chosen in proportion to their exact
object counts; labeled products also choose ordered label partitions
uniformly.

Combination/Subset, Permutation, Partition, and Composition now use direct
count-weighted samplers as well. Multiset inputs, default sizes, and
`"allsizes"` choose among distinct objects uniformly without constructing
their full tuples.

`algorithm="counted"` requires this path, while `"enumerate"` retains explicit
uniform rank selection. The automatic mode falls back to enumeration at
unsupported nested symmetry boundaries, keeping every result uniform while
the remaining component-ranking cases are developed.

Unlabeled Set and PowerSet subsequently gained grouped component-type
unranking. Exact binomial weights select multiplicities by component size,
then recursive ranks select the component objects without enumerating the
resulting multiset or subset class. This also handles recursively defined
unlabeled Set grammars when component sizes decrease.

Unlabeled Cycle uses totient-weighted cycle-index counts to choose its
cardinality, then samples ordered component tuples with an orbit-size
acceptance correction. The correction gives periodic and aperiodic necklaces
the same probability without materializing the cycle class. A Set or PowerSet
whose component type contains an unlabeled Cycle is the remaining draw
boundary because grouped selection needs deterministic ranks for those nested
cycle types.
