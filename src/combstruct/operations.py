"""High-level operations corresponding to Maple ``combstruct`` commands."""

from __future__ import annotations

import math
from collections.abc import Mapping
from fractions import Fraction
from random import Random, SystemRandom
from typing import cast

from .derivation import derive_generating_function
from .enumeration import StructureValue, allstructs
from .generating_function import GFExpression
from .predefined import (
    PredefinedStructure,
    StructureSize,
    count_predefined,
    is_predefined,
    sample_predefined,
)
from .sampling import (
    CountDirectedSampler,
    DrawAlgorithm,
    UnsupportedCountDirectedSampling,
)
from .specification import Expression, parse_specification
from .terms import CoefficientCompiler, UnsupportedConstruction, integer_value


class EmptyStructureClassError(LookupError):
    """No object exists for the requested structure and size."""


def _equations(
    specification: str | Mapping[str, Expression],
) -> dict[str, Expression]:
    if isinstance(specification, str):
        return parse_specification(specification)
    if not isinstance(specification, Mapping):
        raise TypeError("specification must be text or a mapping of equations")
    return dict(specification)


def _validate_universe(labelled: bool) -> None:
    if not isinstance(labelled, bool):
        raise TypeError("labelled must be a boolean")


def _validate_term_count(term_count: int) -> None:
    if isinstance(term_count, bool) or not isinstance(term_count, int):
        raise TypeError("term_count must be an integer")
    if term_count <= 0:
        raise ValueError("term_count must be positive")


def _validate_size(size: int) -> None:
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be an integer")
    if size < 0:
        raise ValueError("size must be nonnegative")


def count(
    specification: str | Mapping[str, Expression] | PredefinedStructure,
    *,
    size: StructureSize = None,
    labelled: bool | None = None,
    symbol: str = "S",
) -> int:
    """Count objects in a grammar-defined or predefined combinatorial class.

    ``labelled=True`` selects labeled/EGF semantics and ``False`` selects
    unlabeled/OGF semantics. The return value is the integer object count, not
    the normalized generating-function coefficient. Predefined structures do
    not use ``labelled`` and support Maple's default and ``"allsizes"`` sizes.
    """

    if is_predefined(specification):
        if labelled is not None:
            raise TypeError("labelled does not apply to predefined structures")
        if symbol != "S":
            raise ValueError("symbol does not apply to predefined structures")
        return count_predefined(specification, size=size)
    if size is None or isinstance(size, str):
        raise TypeError("grammar-defined structures require an integer size")
    _validate_size(size)
    if labelled is None:
        raise TypeError("grammar-defined structures require labelled=True or labelled=False")
    _validate_universe(labelled)
    grammar = cast(str | Mapping[str, Expression], specification)
    coefficients = CoefficientCompiler(_equations(grammar), size, labelled).compute(symbol)
    result = coefficients[size]
    if isinstance(result, Fraction) and result.denominator != 1:
        raise UnsupportedConstruction(
            f"Coefficient of size {size} does not yield an integer count: {result}",
        )
    return integer_value(result)


def gfseries(
    specification: str | Mapping[str, Expression],
    *,
    labelled: bool,
    term_count: int,
) -> dict[str, tuple[Fraction, ...]]:
    """Return truncated generating-function series for every grammar symbol.

    Labeled specifications return EGF coefficients ``a(n) / n!``. Unlabeled
    specifications return OGF coefficients ``a(n)``.
    """

    _validate_universe(labelled)
    _validate_term_count(term_count)
    equations = _equations(specification)
    result: dict[str, tuple[Fraction, ...]] = {}
    for symbol in equations:
        counts = CoefficientCompiler(equations, term_count - 1, labelled).compute(symbol)
        if labelled:
            result[symbol] = tuple(
                Fraction(coefficient, math.factorial(degree))
                for degree, coefficient in enumerate(counts)
            )
        else:
            result[symbol] = tuple(Fraction(coefficient) for coefficient in counts)
    return result


def gfsolve(
    specification: str | Mapping[str, Expression],
    *,
    labelled: bool,
    symbol: str = "S",
) -> GFExpression:
    """Solve for one supported grammar generating function.

    This Maple-compatible command name delegates to
    :func:`derive_generating_function`, which documents the currently
    supported finite and recursive systems.
    """

    return derive_generating_function(
        specification,
        labelled=labelled,
        symbol=symbol,
    )


def draw(
    specification: str | Mapping[str, Expression] | PredefinedStructure,
    *,
    size: StructureSize = None,
    labelled: bool | None = None,
    symbol: str = "S",
    rng: Random | None = None,
    algorithm: DrawAlgorithm = "auto",
) -> StructureValue:
    """Draw one object uniformly from the requested finite class.

    Passing a seeded :class:`random.Random` instance makes the result
    reproducible. ``algorithm="auto"`` uses count-directed recursive sampling
    when the grammar has a supported symmetry profile and otherwise falls back
    to exhaustive rank selection. ``"counted"`` requires the recursive path;
    ``"enumerate"`` always selects an exhaustive rank.
    """

    if rng is not None and not isinstance(rng, Random):
        raise TypeError("rng must be an instance of random.Random")
    if algorithm not in {"auto", "counted", "enumerate"}:
        raise ValueError("algorithm must be 'auto', 'counted', or 'enumerate'")
    source = rng if rng is not None else SystemRandom()
    if is_predefined(specification):
        if labelled is not None:
            raise TypeError("labelled does not apply to predefined structures")
        if symbol != "S":
            raise ValueError("symbol does not apply to predefined structures")
        if algorithm != "enumerate":
            try:
                return sample_predefined(specification, size=size, rng=source)
            except LookupError as error:
                raise EmptyStructureClassError(
                    "No objects exist for the requested structure and size",
                ) from error
    elif algorithm != "enumerate":
        if size is None or isinstance(size, str):
            raise TypeError("grammar-defined structures require an integer size")
        _validate_size(size)
        if labelled is None:
            raise TypeError(
                "grammar-defined structures require labelled=True or labelled=False",
            )
        _validate_universe(labelled)
        equations = _equations(cast(str | Mapping[str, Expression], specification))
        try:
            return CountDirectedSampler(
                equations,
                labelled=labelled,
                size=size,
                rng=source,
            ).sample(symbol)
        except UnsupportedCountDirectedSampling:
            if algorithm == "counted":
                raise
        except LookupError as error:
            raise EmptyStructureClassError(
                "No objects exist for the requested structure and size",
            ) from error

    objects = allstructs(
        specification,
        size=size,
        labelled=labelled,
        symbol=symbol,
    )
    if not objects:
        raise EmptyStructureClassError("No objects exist for the requested structure and size")
    return objects[source.randrange(len(objects))]


__all__ = ["EmptyStructureClassError", "count", "draw", "gfseries", "gfsolve"]
