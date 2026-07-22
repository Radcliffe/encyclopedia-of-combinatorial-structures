"""Derive finite generating-function expressions from ECS specifications.

This module translates acyclic specifications into the generating-function AST
defined by :mod:`combstruct.generating_function`. Labelled constructions use
exponential-generating-function rules and unlabelled constructions use
ordinary-generating-function rules. Recursive systems and constructions whose
unlabelled cycle-index expansion is inherently infinite remain explicit later
milestones.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from fractions import Fraction
from math import factorial

from .generating_function import (
    GFBinary,
    GFExpression,
    GFFunction,
    GFInteger,
    GFUnary,
    GFVariable,
)
from .specification import (
    Cardinality,
    Constructor,
    Expression,
    Reference,
    SpecificationError,
    parse_specification,
)


class UnsupportedGeneratingFunctionDerivation(SpecificationError):
    """A valid specification has no supported finite GF derivation yet."""


def _integer(value: int) -> GFExpression:
    if value >= 0:
        return GFInteger(value)
    return GFUnary("-", GFInteger(-value))


def _is_integer(expression: GFExpression, value: int) -> bool:
    return isinstance(expression, GFInteger) and expression.value == value


def _sum(expressions: Iterable[GFExpression]) -> GFExpression:
    terms = [expression for expression in expressions if not _is_integer(expression, 0)]
    if not terms:
        return GFInteger(0)
    result = terms[0]
    for term in terms[1:]:
        result = GFBinary("+", result, term)
    return result


def _product(expressions: Iterable[GFExpression]) -> GFExpression:
    factors = list(expressions)
    if any(_is_integer(factor, 0) for factor in factors):
        return GFInteger(0)
    factors = [factor for factor in factors if not _is_integer(factor, 1)]
    if not factors:
        return GFInteger(1)
    result = factors[0]
    for factor in factors[1:]:
        result = GFBinary("*", result, factor)
    return result


def _subtract(left: GFExpression, right: GFExpression) -> GFExpression:
    return left if _is_integer(right, 0) else GFBinary("-", left, right)


def _divide(numerator: GFExpression, denominator: GFExpression) -> GFExpression:
    return numerator if _is_integer(denominator, 1) else GFBinary("/", numerator, denominator)


def _power(base: GFExpression, exponent: int) -> GFExpression:
    if exponent == 0:
        return GFInteger(1)
    if exponent == 1:
        return base
    return GFBinary("^", base, GFInteger(exponent))


def _scale(expression: GFExpression, scalar: Fraction) -> GFExpression:
    if scalar == 0 or _is_integer(expression, 0):
        return GFInteger(0)

    negative = scalar < 0
    magnitude = abs(scalar)
    result = _divide(
        _product((_integer(magnitude.numerator), expression)),
        _integer(magnitude.denominator),
    )
    return GFUnary("-", result) if negative else result


def _substitute_variable(expression: GFExpression, exponent: int) -> GFExpression:
    """Return ``expression(_x**exponent)`` without mutating the source AST."""

    if isinstance(expression, GFInteger):
        return expression
    if isinstance(expression, GFVariable):
        return _power(expression, exponent)
    if isinstance(expression, GFUnary):
        return GFUnary(
            expression.operator,
            _substitute_variable(expression.operand, exponent),
        )
    if isinstance(expression, GFFunction):
        return GFFunction(
            expression.name,
            _substitute_variable(expression.argument, exponent),
        )
    return GFBinary(
        expression.operator,
        _substitute_variable(expression.left, exponent),
        _substitute_variable(expression.right, exponent),
    )


def _euler_totient(value: int) -> int:
    result = value
    remaining = value
    prime = 2
    while prime * prime <= remaining:
        if remaining % prime == 0:
            while remaining % prime == 0:
                remaining //= prime
            result -= result // prime
        prime += 1
    if remaining > 1:
        result -= result // remaining
    return result


def _divisors(value: int) -> Iterable[int]:
    return (divisor for divisor in range(1, value + 1) if value % divisor == 0)


class _GeneratingFunctionDeriver:
    def __init__(self, equations: Mapping[str, Expression], labelled: bool):
        self.equations = dict(equations)
        self.labelled = labelled
        self.memo: dict[str, GFExpression] = {}
        self.active: list[str] = []

    def derive(self, symbol: str) -> GFExpression:
        if symbol not in self.equations:
            raise SpecificationError(f"Specification does not define {symbol!r}")
        return self._reference(symbol)

    def _reference(self, name: str) -> GFExpression:
        if name == "Epsilon":
            return GFInteger(1)
        if name in ("Atom", "Z") and name not in self.equations:
            return GFVariable()
        if name not in self.equations:
            raise SpecificationError(f"Undefined symbol {name!r}")
        if name in self.memo:
            return self.memo[name]
        if name in self.active:
            cycle_start = self.active.index(name)
            cycle = [*self.active[cycle_start:], name]
            raise UnsupportedGeneratingFunctionDerivation(
                "Recursive generating-function derivation is not supported yet: "
                + " -> ".join(cycle),
            )

        self.active.append(name)
        try:
            result = self._expression(self.equations[name])
        finally:
            self.active.pop()
        self.memo[name] = result
        return result

    def _expression(self, expression: Expression) -> GFExpression:
        if isinstance(expression, Reference):
            return self._reference(expression.name)
        if not isinstance(expression, Constructor):
            raise TypeError("Specification values must be Reference or Constructor expressions")

        arguments = [self._expression(argument) for argument in expression.arguments]
        name = expression.name.lower()
        if name == "union":
            if expression.cardinality is not None:
                raise SpecificationError("Union does not accept a cardinality constraint")
            return _sum(arguments)
        if name == "prod":
            if expression.cardinality is not None:
                raise SpecificationError("Prod does not accept a cardinality constraint")
            return _product(arguments)
        if len(arguments) != 1:
            raise SpecificationError(f"{expression.name} requires exactly one component argument")

        component = arguments[0]
        minimum, maximum = self._bounds(
            expression.cardinality,
            default_minimum=1 if name == "cycle" else 0,
        )
        if name == "sequence":
            return self._sequence(component, minimum, maximum)
        if name == "set":
            return (
                self._labelled_set(component, minimum, maximum)
                if self.labelled
                else self._unlabelled_set(component, minimum, maximum)
            )
        if name == "cycle":
            return (
                self._labelled_cycle(component, minimum, maximum)
                if self.labelled
                else self._unlabelled_cycle(component, minimum, maximum)
            )
        if name == "powerset":
            if self.labelled:
                raise UnsupportedGeneratingFunctionDerivation(
                    "PowerSet is only defined for unlabelled structures",
                )
            if expression.cardinality is not None:
                raise UnsupportedGeneratingFunctionDerivation(
                    "PowerSet cardinality constraints are not supported",
                )
            raise UnsupportedGeneratingFunctionDerivation(
                "An unlabelled PowerSet requires an infinite cycle-index expansion",
            )
        raise UnsupportedGeneratingFunctionDerivation(
            f"Unsupported constructor {expression.name!r}",
        )

    @staticmethod
    def _bounds(
        cardinality: Cardinality | None,
        *,
        default_minimum: int,
    ) -> tuple[int, int | None]:
        if cardinality is None:
            return default_minimum, None
        return max(default_minimum, cardinality.minimum), cardinality.maximum

    @staticmethod
    def _sequence(
        component: GFExpression,
        minimum: int,
        maximum: int | None,
    ) -> GFExpression:
        if maximum is not None:
            return _sum(_power(component, count) for count in range(minimum, maximum + 1))
        return _divide(
            _power(component, minimum),
            _subtract(GFInteger(1), component),
        )

    @staticmethod
    def _labelled_set(
        component: GFExpression,
        minimum: int,
        maximum: int | None,
    ) -> GFExpression:
        def fixed(count: int) -> GFExpression:
            return _scale(_power(component, count), Fraction(1, factorial(count)))

        if maximum is not None:
            return _sum(fixed(count) for count in range(minimum, maximum + 1))
        excluded = _sum(fixed(count) for count in range(minimum))
        return _subtract(GFFunction("exp", component), excluded)

    @staticmethod
    def _unlabelled_set(
        component: GFExpression,
        minimum: int,
        maximum: int | None,
    ) -> GFExpression:
        if maximum is None:
            raise UnsupportedGeneratingFunctionDerivation(
                "An unrestricted unlabelled Set requires an infinite cycle-index expansion",
            )

        fixed_values: dict[int, GFExpression] = {0: GFInteger(1)}

        def fixed(count: int) -> GFExpression:
            if count not in fixed_values:
                fixed_values[count] = _scale(
                    _sum(
                        _product(
                            (
                                _substitute_variable(component, part),
                                fixed(count - part),
                            ),
                        )
                        for part in range(1, count + 1)
                    ),
                    Fraction(1, count),
                )
            return fixed_values[count]

        return _sum(fixed(count) for count in range(minimum, maximum + 1))

    @staticmethod
    def _labelled_cycle(
        component: GFExpression,
        minimum: int,
        maximum: int | None,
    ) -> GFExpression:
        def fixed(count: int) -> GFExpression:
            return _scale(_power(component, count), Fraction(1, count))

        if maximum is not None:
            return _sum(fixed(count) for count in range(minimum, maximum + 1))
        unrestricted = GFFunction(
            "ln",
            _divide(
                GFInteger(1),
                _subtract(GFInteger(1), component),
            ),
        )
        excluded = _sum(fixed(count) for count in range(1, minimum))
        return _subtract(unrestricted, excluded)

    @staticmethod
    def _unlabelled_cycle(
        component: GFExpression,
        minimum: int,
        maximum: int | None,
    ) -> GFExpression:
        if maximum is None:
            raise UnsupportedGeneratingFunctionDerivation(
                "An unrestricted unlabelled Cycle requires an infinite cycle-index expansion",
            )

        def fixed(count: int) -> GFExpression:
            return _sum(
                _scale(
                    _power(
                        _substitute_variable(component, divisor),
                        count // divisor,
                    ),
                    Fraction(_euler_totient(divisor), count),
                )
                for divisor in _divisors(count)
            )

        return _sum(fixed(count) for count in range(minimum, maximum + 1))


def derive_generating_function(
    specification: str | Mapping[str, Expression],
    *,
    labelled: bool,
    symbol: str = "S",
) -> GFExpression:
    """Derive a finite OGF or EGF expression from an acyclic specification.

    Source text and the mapping returned by :func:`parse_specification` are both
    accepted. ``labelled=True`` applies exponential-generating-function rules;
    ``False`` applies ordinary-generating-function rules.
    """

    if not isinstance(labelled, bool):
        raise TypeError("labelled must be a boolean")
    if not isinstance(symbol, str):
        raise TypeError("symbol must be a string")
    if not symbol:
        raise ValueError("symbol must not be empty")
    equations: Mapping[str, Expression]
    if isinstance(specification, str):
        equations = parse_specification(specification)
    elif isinstance(specification, Mapping):
        equations = specification
    else:
        raise TypeError("specification must be text or a mapping of equations")
    return _GeneratingFunctionDeriver(equations, labelled).derive(symbol)


__all__ = [
    "UnsupportedGeneratingFunctionDerivation",
    "derive_generating_function",
]
