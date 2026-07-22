"""Derive finite generating-function expressions from ECS specifications.

This module translates finite specifications into the generating-function AST
defined by :mod:`combstruct.generating_function`. Labelled constructions use
exponential-generating-function rules and unlabelled constructions use
ordinary-generating-function rules. A recursive component is solved in closed
form when removing one feedback symbol leaves an acyclic system whose expansion
is linear or quadratic in that symbol. More general recursive systems and
constructions whose unlabelled cycle-index expansion is inherently infinite
remain explicit later milestones.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from fractions import Fraction
from math import factorial, isqrt

from .generating_function import (
    GFBinary,
    GFComplex,
    GFExpression,
    GFFunction,
    GFIndex,
    GFIndexedCoefficient,
    GFInfiniteProduct,
    GFInfiniteSum,
    GFInteger,
    GFRootOf,
    GFSeriesCall,
    GFTotient,
    GFUnary,
    GFVariable,
    generating_function_coefficients,
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


def _square_root(expression: GFExpression) -> GFExpression:
    return GFBinary(
        "^",
        expression,
        GFBinary("/", GFInteger(1), GFInteger(2)),
    )


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
    if isinstance(expression, (GFIndex, GFIndexedCoefficient, GFTotient)):
        return expression
    if isinstance(expression, GFVariable):
        return expression if expression.name == "_Z" else _power(expression, exponent)
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
    if isinstance(expression, GFSeriesCall):
        return GFSeriesCall(
            expression.name,
            _substitute_variable(expression.argument, exponent),
        )
    if isinstance(expression, GFRootOf):
        return GFRootOf(_substitute_variable(expression.equation, exponent))
    if isinstance(expression, GFComplex):
        return GFComplex(_substitute_variable(expression.value, exponent))
    if isinstance(expression, GFInfiniteSum):
        return GFInfiniteSum(
            _substitute_variable(expression.summand, exponent),
            expression.index,
            expression.lower_bound,
        )
    if isinstance(expression, GFInfiniteProduct):
        return GFInfiniteProduct(
            _substitute_variable(expression.factor, exponent),
            expression.index,
            expression.lower_bound,
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


def _rational_square_root(value: Fraction) -> Fraction | None:
    if value < 0:
        return None
    numerator = isqrt(value.numerator)
    denominator = isqrt(value.denominator)
    if numerator * numerator != value.numerator:
        return None
    if denominator * denominator != value.denominator:
        return None
    return Fraction(numerator, denominator)


type _QuadraticPolynomial = tuple[GFExpression, GFExpression, GFExpression]


def _expression_references(expression: Expression) -> set[str]:
    if isinstance(expression, Reference):
        return {expression.name}
    references: set[str] = set()
    for argument in expression.arguments:
        references.update(_expression_references(argument))
    return references


def _recursive_component_map(
    equations: Mapping[str, Expression],
) -> dict[str, tuple[str, ...]]:
    """Return every symbol in a recursive SCC mapped to that ordered SCC."""

    graph = {
        name: _expression_references(expression) & equations.keys()
        for name, expression in equations.items()
    }

    def reachable(start: str) -> set[str]:
        visited: set[str] = set()
        pending = [start]
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            visited.add(name)
            pending.extend(graph[name] - visited)
        return visited

    reachability = {name: reachable(name) for name in equations}
    result: dict[str, tuple[str, ...]] = {}
    assigned: set[str] = set()
    for name in equations:
        if name in assigned:
            continue
        component = tuple(
            candidate
            for candidate in equations
            if candidate in reachability[name] and name in reachability[candidate]
        )
        if len(component) > 1 or name in graph[name]:
            result.update((candidate, component) for candidate in component)
        assigned.update(component)
    return result


class _GeneratingFunctionDeriver:
    def __init__(self, equations: Mapping[str, Expression], labelled: bool):
        self.equations = dict(equations)
        self.labelled = labelled
        self.memo: dict[str, GFExpression] = {}
        self.active: list[str] = []
        self.recursive_components = _recursive_component_map(self.equations)
        self.solving_components: set[tuple[str, ...]] = set()

    def derive(self, symbol: str) -> GFExpression:
        if symbol not in self.equations:
            raise SpecificationError(f"Specification does not define {symbol!r}")
        return self._reference(symbol)

    @staticmethod
    def _contains_reference(expression: Expression, name: str) -> bool:
        if isinstance(expression, Reference):
            return expression.name == name
        return any(
            _GeneratingFunctionDeriver._contains_reference(argument, name)
            for argument in expression.arguments
        )

    def _reference(self, name: str) -> GFExpression:
        if name == "Epsilon":
            return GFInteger(1)
        if name in ("Atom", "Z") and name not in self.equations:
            return GFVariable()
        if name not in self.equations:
            raise SpecificationError(f"Undefined symbol {name!r}")
        if name in self.memo:
            return self.memo[name]
        component = self.recursive_components.get(name)
        if component is not None and len(component) > 1:
            self._solve_mutual_recursive(component)
            return self.memo[name]
        if name in self.active:
            cycle_start = self.active.index(name)
            cycle = [*self.active[cycle_start:], name]
            raise UnsupportedGeneratingFunctionDerivation(
                "Recursive generating-function derivation is not supported yet: "
                + " -> ".join(cycle),
            )
        if self._contains_reference(self.equations[name], name):
            result = self._solve_self_recursive(name)
            self.memo[name] = result
            return result

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
        return self._construction(expression, arguments)

    def _construction(
        self,
        expression: Constructor,
        arguments: list[GFExpression],
    ) -> GFExpression:
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

    def _solve_self_recursive(self, symbol: str) -> GFExpression:
        self.active.append(symbol)
        try:
            constant, linear, quadratic = self._quadratic_expression(
                self.equations[symbol],
                symbol,
            )
        finally:
            self.active.pop()

        return self._solve_quadratic_polynomial(
            symbol,
            constant,
            linear,
            quadratic,
        )

    def _solve_mutual_recursive(self, component: tuple[str, ...]) -> None:
        if all(name in self.memo for name in component):
            return
        if component in self.solving_components:
            cycle = " -> ".join((*component, component[0]))
            raise UnsupportedGeneratingFunctionDerivation(
                f"Recursive component cannot be reduced safely: {cycle}",
            )

        self.solving_components.add(component)
        try:
            candidates: list[
                tuple[
                    int,
                    int,
                    str,
                    dict[str, _QuadraticPolynomial],
                    _QuadraticPolynomial,
                ]
            ] = []
            first_error: UnsupportedGeneratingFunctionDerivation | None = None
            component_set = set(component)
            for root_index, root in enumerate(component):
                expansions: dict[str, _QuadraticPolynomial] = {}
                remaining = component_set - {root}
                dependencies = {
                    name: _expression_references(self.equations[name]) & remaining
                    for name in remaining
                }
                while dependencies:
                    ready = [
                        name
                        for name in component
                        if name in dependencies and dependencies[name] <= expansions.keys()
                    ]
                    if not ready:
                        break
                    for name in ready:
                        try:
                            expansions[name] = self._quadratic_expression(
                                self.equations[name],
                                root,
                                component=component_set,
                                expansions=expansions,
                            )
                        except UnsupportedGeneratingFunctionDerivation as error:
                            first_error = first_error or error
                            dependencies.clear()
                            break
                        del dependencies[name]
                if dependencies or len(expansions) != len(remaining):
                    continue
                try:
                    polynomial = self._quadratic_expression(
                        self.equations[root],
                        root,
                        component=component_set,
                        expansions=expansions,
                    )
                except UnsupportedGeneratingFunctionDerivation as error:
                    first_error = first_error or error
                    continue
                degree = 2 if not _is_integer(polynomial[2], 0) else 1
                candidates.append((degree, root_index, root, expansions, polynomial))

            for _, _, root, expansions, polynomial in sorted(candidates):
                try:
                    root_expression = self._solve_quadratic_polynomial(
                        root,
                        *polynomial,
                    )
                except UnsupportedGeneratingFunctionDerivation as error:
                    first_error = first_error or error
                    continue
                self.memo[root] = root_expression
                for name, expansion in expansions.items():
                    self.memo[name] = self._evaluate_quadratic(
                        expansion,
                        root_expression,
                    )
                return

            if first_error is not None:
                raise first_error
            cycle = " -> ".join((*component, component[0]))
            raise UnsupportedGeneratingFunctionDerivation(
                "Recursive component cannot be reduced by removing one feedback symbol: " + cycle,
            )
        finally:
            self.solving_components.remove(component)

    def _solve_quadratic_polynomial(
        self,
        symbol: str,
        constant: GFExpression,
        linear: GFExpression,
        quadratic: GFExpression,
    ) -> GFExpression:
        one_minus_linear = _subtract(GFInteger(1), linear)
        if _is_integer(quadratic, 0):
            if _is_integer(linear, 1):
                raise UnsupportedGeneratingFunctionDerivation(
                    f"Recursive equation for {symbol!r} is not well founded",
                )
            return _divide(constant, one_minus_linear)

        discriminant = _subtract(
            _power(one_minus_linear, 2),
            _scale(_product((quadratic, constant)), Fraction(4)),
        )
        square_root = _square_root(discriminant)
        denominator = _scale(quadratic, Fraction(2))
        minus_root = _divide(_subtract(one_minus_linear, square_root), denominator)
        plus_root = _divide(_sum((one_minus_linear, square_root)), denominator)
        return self._select_quadratic_root(
            constant,
            linear,
            quadratic,
            minus_root,
            plus_root,
            symbol,
        )

    def _quadratic_expression(
        self,
        expression: Expression,
        symbol: str,
        *,
        component: set[str] | None = None,
        expansions: Mapping[str, _QuadraticPolynomial] | None = None,
    ) -> _QuadraticPolynomial:
        component = {symbol} if component is None else component
        expansions = {} if expansions is None else expansions
        zero = GFInteger(0)
        if isinstance(expression, Reference):
            if expression.name == symbol:
                return zero, GFInteger(1), zero
            if expression.name in component:
                try:
                    return expansions[expression.name]
                except KeyError as error:
                    raise RuntimeError(
                        f"Recursive symbol {expression.name!r} was expanded out of order",
                    ) from error
            return self._reference(expression.name), zero, zero

        arguments = [
            self._quadratic_expression(
                argument,
                symbol,
                component=component,
                expansions=expansions,
            )
            for argument in expression.arguments
        ]
        name = expression.name.lower()
        if name == "union":
            if expression.cardinality is not None:
                raise SpecificationError("Union does not accept a cardinality constraint")
            return (
                _sum(argument[0] for argument in arguments),
                _sum(argument[1] for argument in arguments),
                _sum(argument[2] for argument in arguments),
            )
        if name == "prod":
            if expression.cardinality is not None:
                raise SpecificationError("Prod does not accept a cardinality constraint")
            result: _QuadraticPolynomial = (GFInteger(1), zero, zero)
            for argument in arguments:
                result = self._multiply_quadratic(result, argument, symbol)
            return result

        if len(arguments) != 1:
            raise SpecificationError(f"{expression.name} requires exactly one component argument")
        if any(
            not _is_integer(coefficient, 0)
            for argument in arguments
            for coefficient in argument[1:]
        ):
            raise UnsupportedGeneratingFunctionDerivation(
                f"Recursive symbol {symbol!r} occurs inside {expression.name}; "
                "only Union and Prod recursion is supported",
            )
        return (
            self._construction(
                expression,
                [argument[0] for argument in arguments],
            ),
            zero,
            zero,
        )

    @staticmethod
    def _evaluate_quadratic(
        polynomial: _QuadraticPolynomial,
        value: GFExpression,
    ) -> GFExpression:
        return _sum(
            (
                polynomial[0],
                _product((polynomial[1], value)),
                _product((polynomial[2], _power(value, 2))),
            ),
        )

    @staticmethod
    def _multiply_quadratic(
        left: _QuadraticPolynomial,
        right: _QuadraticPolynomial,
        symbol: str,
    ) -> _QuadraticPolynomial:
        coefficients: list[list[GFExpression]] = [[], [], []]
        for left_degree, left_coefficient in enumerate(left):
            if _is_integer(left_coefficient, 0):
                continue
            for right_degree, right_coefficient in enumerate(right):
                if _is_integer(right_coefficient, 0):
                    continue
                degree = left_degree + right_degree
                if degree > 2:
                    raise UnsupportedGeneratingFunctionDerivation(
                        f"Recursive equation for {symbol!r} has degree greater than two",
                    )
                coefficients[degree].append(
                    _product((left_coefficient, right_coefficient)),
                )
        return (
            _sum(coefficients[0]),
            _sum(coefficients[1]),
            _sum(coefficients[2]),
        )

    @staticmethod
    def _select_quadratic_root(
        constant: GFExpression,
        linear: GFExpression,
        quadratic: GFExpression,
        minus_root: GFExpression,
        plus_root: GFExpression,
        symbol: str,
    ) -> GFExpression:
        constant_term = generating_function_coefficients(constant, 1)[0]
        linear_term = generating_function_coefficients(linear, 1)[0]
        quadratic_term = generating_function_coefficients(quadratic, 1)[0]
        one_minus_linear = Fraction(1) - linear_term
        discriminant = one_minus_linear**2 - 4 * quadratic_term * constant_term
        square_root = _rational_square_root(discriminant)
        if square_root is None:
            raise UnsupportedGeneratingFunctionDerivation(
                f"Recursive equation for {symbol!r} has no rational formal-series branch",
            )

        if quadratic_term == 0:
            if one_minus_linear == 0:
                raise UnsupportedGeneratingFunctionDerivation(
                    f"Recursive equation for {symbol!r} has an indeterminate constant term",
                )
            return minus_root if one_minus_linear > 0 else plus_root

        minus_constant = (one_minus_linear - square_root) / (2 * quadratic_term)
        plus_constant = (one_minus_linear + square_root) / (2 * quadratic_term)
        nonnegative = [
            (value, root)
            for value, root in (
                (minus_constant, minus_root),
                (plus_constant, plus_root),
            )
            if value >= 0
        ]
        if not nonnegative:
            raise UnsupportedGeneratingFunctionDerivation(
                f"Recursive equation for {symbol!r} has no nonnegative constant solution",
            )
        selected_constant, selected_root = min(nonnegative, key=lambda item: item[0])
        derivative = 2 * quadratic_term * selected_constant + linear_term - 1
        if derivative == 0:
            raise UnsupportedGeneratingFunctionDerivation(
                f"Recursive equation for {symbol!r} does not determine a unique formal-series branch",
            )
        return selected_root

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
    """Derive a finite OGF or EGF expression from a supported specification.

    Source text and the mapping returned by :func:`parse_specification` are both
    accepted. ``labelled=True`` applies exponential-generating-function rules;
    ``False`` applies ordinary-generating-function rules. A recursive
    ``Union``/``Prod`` component reducible to one linear or quadratic equation
    is returned as a rational or square-root closed form.
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
