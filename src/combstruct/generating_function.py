"""Parse ECS generating functions and expand supported forms exactly.

The parser recognizes every stored ECS generating-function field: the finite
elementary grammar, principal ``LambertW`` calls, unselected ``RootOf``
equations, indexed infinite sums, the symbolic infinite product and indexed
coefficients, two fully determined patterned ellipses, and the one-argument
``Complex`` constructor, plus bounded implicit-equation and equation-system
syntax. The series evaluator uses exact rational arithmetic and expands
principal ``LambertW`` compositions at zero or recognized rational centers,
plus indexed sums whose requested coefficients have a provable bound and
coefficientwise-convergent named-series assignments. Unselected roots and
complex series remain explicit evaluation boundaries; the evaluator never
guesses a branch or truncation.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from math import factorial, prod
from typing import Literal, cast

type UnaryOperator = Literal["+", "-"]
type BinaryOperator = Literal["+", "-", "*", "/", "^"]
type FunctionName = Literal["exp", "ln", "LambertW"]


class GeneratingFunctionError(ValueError):
    """A stored generating-function expression is malformed."""


class UnsupportedGeneratingFunction(GeneratingFunctionError):
    """A valid ECS generating-function form is outside the current grammar."""


class GeneratingFunctionEvaluationError(GeneratingFunctionError):
    """A parsed expression cannot be expanded as an exact formal series."""


@dataclass(frozen=True, slots=True)
class GFInteger:
    """An integer literal in a generating-function expression."""

    value: int


@dataclass(frozen=True, slots=True)
class GFVariable:
    """The generating variable or Maple-local ``RootOf`` variable."""

    name: Literal["_x", "_Z"] = "_x"


@dataclass(frozen=True, slots=True)
class GFUnary:
    """A unary plus or minus expression."""

    operator: UnaryOperator
    operand: GFExpression


@dataclass(frozen=True, slots=True)
class GFBinary:
    """A binary arithmetic expression."""

    operator: BinaryOperator
    left: GFExpression
    right: GFExpression


@dataclass(frozen=True, slots=True)
class GFFunction:
    """A function call recognized in the finite ECS corpus."""

    name: FunctionName
    argument: GFExpression


@dataclass(frozen=True, slots=True)
class GFSeriesCall:
    """A named formal series evaluated at an expression, such as ``A(x^2)``."""

    name: str
    argument: GFExpression


@dataclass(frozen=True, slots=True)
class GFRootOf:
    """An unselected Maple ``RootOf`` equation in its local ``_Z`` variable."""

    equation: GFExpression


@dataclass(frozen=True, slots=True)
class GFComplex:
    """A one-argument Maple ``Complex`` constructor representing ``I * value``."""

    value: GFExpression


@dataclass(frozen=True, slots=True)
class GFIndex:
    """A normalized bound variable represented as ``j[level]``."""

    level: int


@dataclass(frozen=True, slots=True)
class GFTotient:
    """Euler's totient applied to an indexed summation variable."""

    index: GFIndex


@dataclass(frozen=True, slots=True)
class GFIndexedCoefficient:
    """A symbolic indexed coefficient such as ``a_k``."""

    name: str
    index: GFIndex


@dataclass(frozen=True, slots=True)
class GFInfiniteSum:
    """A sum over one indexed variable from a positive bound through infinity."""

    summand: GFExpression
    index: GFIndex
    lower_bound: int = 1


@dataclass(frozen=True, slots=True)
class GFInfiniteProduct:
    """A product over one indexed variable from a positive bound through infinity."""

    factor: GFExpression
    index: GFIndex
    lower_bound: int = 1


@dataclass(frozen=True, slots=True)
class GFEquation:
    """One implicit generating-function equation."""

    left: GFExpression
    right: GFExpression


@dataclass(frozen=True, slots=True)
class GFEquationSystem:
    """An ordered system of implicit generating-function equations."""

    equations: tuple[GFEquation, ...]


type GFExpression = (
    GFInteger
    | GFVariable
    | GFUnary
    | GFBinary
    | GFFunction
    | GFSeriesCall
    | GFRootOf
    | GFComplex
    | GFIndex
    | GFTotient
    | GFIndexedCoefficient
    | GFInfiniteSum
    | GFInfiniteProduct
)
type GFParseResult = GFExpression | GFEquation | GFEquationSystem


TOKEN_RE = re.compile(
    r"\s*(numtheory:-phi|\d+|[A-Za-z_][A-Za-z0-9_]*|[()+\-*/^]|\S)",
)
IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
INFIX_BINDING_POWER: dict[str, tuple[int, int]] = {
    "+": (10, 11),
    "-": (10, 11),
    "*": (20, 21),
    "/": (20, 21),
    "^": (40, 40),
}
UNARY_BINDING_POWER = 30


def _normalize_patterned_ellipsis(source: str) -> str:
    """Rewrite the two fully determined ellipsis patterns stored by the ECS."""

    compact = re.sub(r"\s+", "", source)
    match = re.fullmatch(
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\(x\)=x\*exp\((?P<body>.*)\)",
        compact,
    )
    if match is None:
        return source
    name = match.group("name")
    body = match.group("body")
    positive_prefix = f"{name}(x)+{name}(x^2)/2+{name}(x^3)/3+{name}(x^4)/4+..."
    alternating_prefix = f"{name}(x)-{name}(x^2)/2+{name}(x^3)/3-{name}(x^4)/4+..."
    if body == positive_prefix:
        summand = f"{name}(x^j[1])/j[1]"
    elif body == alternating_prefix:
        summand = f"(-1)^(j[1]+1)*{name}(x^j[1])/j[1]"
    else:
        return source
    return f"{name}(x)=x*exp(Sum({summand},j[1]=1..infinity))"


class GeneratingFunctionParser:
    """Parse supported expressions and implicit equations used by the ECS."""

    def __init__(self, source: str):
        self.source = source
        self.tokens = self._tokenize(source)
        self.position = 0
        self.root_depth = 0
        self.explicit_index_ceiling = max(
            (
                int(self.tokens[position + 2])
                for position in range(len(self.tokens) - 3)
                if self.tokens[position] == "j"
                and self.tokens[position + 1] == "["
                and self.tokens[position + 2].isdigit()
                and self.tokens[position + 3] == "]"
            ),
            default=0,
        )
        self.unindexed_bindings: list[tuple[str, GFIndex]] = []

    @staticmethod
    def _tokenize(source: str) -> list[str]:
        if source.strip() == "":
            raise GeneratingFunctionError("Generating-function source must not be empty")
        source = _normalize_patterned_ellipsis(source)
        if "..." in source:
            raise UnsupportedGeneratingFunction(
                "Unrecognized ellipsis-based generating functions are not supported",
            )

        tokens: list[str] = []
        position = 0
        while position < len(source):
            match = TOKEN_RE.match(source, position)
            if not match:
                if source[position:].strip() == "":
                    break
                excerpt = source[position : position + 20]
                raise GeneratingFunctionError(f"Unexpected input near {excerpt!r}")
            tokens.append(match.group(1))
            position = match.end()
        return tokens

    def parse(self) -> GFParseResult:
        """Parse and return one immutable expression, equation, or system."""

        result: GFParseResult = self._parse_equation_or_expression()
        if self._peek() == ",":
            if not isinstance(result, GFEquation):
                raise self._error("An equation system must contain equations")
            equations = [result]
            while self._peek() == ",":
                self.position += 1
                equation = self._parse_equation_or_expression()
                if not isinstance(equation, GFEquation):
                    raise self._error("An equation system must contain equations")
                equations.append(equation)
            result = GFEquationSystem(tuple(equations))
        if self._peek() == "." and self.position == len(self.tokens) - 1:
            self.position += 1
        if self.position != len(self.tokens):
            raise self._error(f"Unexpected token {self._peek()!r} after expression")
        if isinstance(result, GFEquationSystem):
            for equation in result.equations:
                self._validate_equation(equation)
        elif isinstance(result, GFEquation):
            self._validate_equation(result)
        else:
            self._validate_indices(result, frozenset())
        return result

    def _parse_equation_or_expression(self) -> GFExpression | GFEquation:
        left = self._parse_expression()
        if self._peek() != "=":
            return left
        self.position += 1
        return GFEquation(left, self._parse_expression())

    def _validate_equation(self, equation: GFEquation) -> None:
        self._validate_indices(equation.left, frozenset())
        self._validate_indices(equation.right, frozenset())

    def _parse_expression(self, minimum_binding_power: int = 0) -> GFExpression:
        left = self._parse_prefix()
        while (operator := self._peek()) in INFIX_BINDING_POWER:
            assert operator is not None
            left_binding_power, right_binding_power = INFIX_BINDING_POWER[operator]
            if left_binding_power < minimum_binding_power:
                break
            self.position += 1
            right = self._parse_expression(right_binding_power)
            left = GFBinary(cast(BinaryOperator, operator), left, right)
        return left

    def _parse_prefix(self) -> GFExpression:
        token = self._take()
        if token.isdigit():
            return GFInteger(int(token))
        if token in {"_x", "x"}:
            return GFVariable()
        if token == "_Z":
            if self.root_depth == 0:
                raise self._error("Root variable '_Z' is only valid inside RootOf")
            return GFVariable("_Z")
        if token == "j":
            return self._parse_index_reference("j")
        if token in {"+", "-"}:
            return GFUnary(
                cast(UnaryOperator, token),
                self._parse_expression(UNARY_BINDING_POWER),
            )
        if token == "(":
            expression = self._parse_expression()
            self._expect(")")
            return expression
        if token in {"exp", "ln", "log", "LambertW"}:
            self._expect("(")
            argument = self._parse_expression()
            self._expect(")")
            name = "ln" if token == "log" else token
            return GFFunction(cast(FunctionName, name), argument)
        if token == "RootOf":
            self._expect("(")
            self.root_depth += 1
            try:
                equation = self._parse_expression()
            finally:
                self.root_depth -= 1
            self._expect(")")
            return GFRootOf(equation)
        if token == "Complex":
            self._expect("(")
            value = self._parse_expression()
            if self._peek() == ",":
                raise UnsupportedGeneratingFunction(
                    "Only the one-argument Complex form used by the ECS catalogue is supported",
                )
            self._expect(")")
            return GFComplex(value)
        if token == "numtheory:-phi":
            self._expect("(")
            self._expect("j")
            index = self._parse_index_reference("j")
            self._expect(")")
            return GFTotient(index)
        if token == "phi":
            self._expect("(")
            self._expect("j")
            index = self._parse_index_reference("j")
            self._expect(")")
            return GFTotient(index)
        if token == "Sum":
            self._expect("(")
            summand = self._parse_expression()
            self._expect(",")
            self._expect("j")
            index = self._parse_index_suffix()
            self._expect("=")
            self._expect("1")
            self._expect(".")
            self._expect(".")
            self._expect("infinity")
            self._expect(")")
            return GFInfiniteSum(summand, index)
        if token == "Sum_":
            return self._parse_alternate_aggregate("Sum")
        if token == "Product_":
            return self._parse_alternate_aggregate("Product")
        if IDENTIFIER_RE.fullmatch(token):
            if active_index := self._active_unindexed_index(token):
                return active_index
            coefficient_name, separator, index_name = token.rpartition("_")
            if (
                separator
                and coefficient_name
                and (coefficient_index := self._active_unindexed_index(index_name))
            ):
                return GFIndexedCoefficient(coefficient_name, coefficient_index)
            if self._peek() == "(":
                self.position += 1
                argument = self._parse_expression()
                self._expect(")")
                return GFSeriesCall(token, argument)
            raise UnsupportedGeneratingFunction(
                f"Generating-function identifier {token!r} is not supported",
            )
        raise self._error(f"Expected an expression, found {token!r}")

    def _parse_index_suffix(self) -> GFIndex:
        self._expect("[")
        token = self._take()
        if not token.isdigit() or int(token) < 1:
            raise self._error(f"Expected a positive summation-index level, found {token!r}")
        self._expect("]")
        return GFIndex(int(token))

    def _active_unindexed_index(self, name: str) -> GFIndex | None:
        for bound_name, index in reversed(self.unindexed_bindings):
            if bound_name == name:
                return index
        return None

    def _parse_index_reference(self, name: str) -> GFIndex:
        if self._peek() == "[":
            return self._parse_index_suffix()
        if index := self._active_unindexed_index(name):
            return index
        raise self._error(f"Unindexed variable {name!r} is not bound by a Sum or Product")

    def _parse_alternate_aggregate(
        self,
        kind: Literal["Sum", "Product"],
    ) -> GFInfiniteSum | GFInfiniteProduct:
        self._expect("{")
        index_name = self._take()
        if not IDENTIFIER_RE.fullmatch(index_name):
            raise self._error(f"Expected an index name, found {index_name!r}")
        relation = self._take()
        bound_token = self._take()
        if not bound_token.isdigit():
            raise self._error(
                f"Expected an integer {kind} bound, found {bound_token!r}",
            )
        bound = int(bound_token)
        if relation == "=":
            if bound < 1:
                raise self._error(f"An infinite {kind} lower bound must be positive")
            self._expect(".")
            self._expect(".")
            infinity = self._take()
            if infinity not in {"inf", "infinity"}:
                raise self._error(f"Expected infinity, found {infinity!r}")
            lower_bound = bound
        elif relation == ">":
            lower_bound = bound + 1
        else:
            raise self._error(
                f"Expected '=' or '>' in a {kind} bound, found {relation!r}",
            )
        self._expect("}")
        next_level = (
            max(
                (index.level for _, index in self.unindexed_bindings),
                default=self.explicit_index_ceiling,
            )
            + 1
        )
        index = GFIndex(next_level)
        self.unindexed_bindings.append((index_name, index))
        try:
            body = self._parse_expression(11)
        finally:
            self.unindexed_bindings.pop()
        if kind == "Sum":
            return GFInfiniteSum(body, index, lower_bound)
        return GFInfiniteProduct(body, index, lower_bound)

    def _validate_indices(
        self,
        expression: GFExpression,
        bound: frozenset[int],
    ) -> None:
        if isinstance(expression, (GFInteger, GFVariable)):
            return
        if isinstance(expression, GFIndex):
            if expression.level not in bound:
                raise GeneratingFunctionError(
                    f"Index j[{expression.level}] is not bound by a Sum or Product",
                )
            return
        if isinstance(expression, GFUnary):
            self._validate_indices(expression.operand, bound)
            return
        if isinstance(expression, GFBinary):
            self._validate_indices(expression.left, bound)
            self._validate_indices(expression.right, bound)
            return
        if isinstance(expression, GFFunction):
            self._validate_indices(expression.argument, bound)
            return
        if isinstance(expression, GFSeriesCall):
            self._validate_indices(expression.argument, bound)
            return
        if isinstance(expression, GFRootOf):
            self._validate_indices(expression.equation, bound)
            return
        if isinstance(expression, GFComplex):
            self._validate_indices(expression.value, bound)
            return
        if isinstance(expression, GFTotient):
            self._validate_indices(expression.index, bound)
            return
        if isinstance(expression, GFIndexedCoefficient):
            self._validate_indices(expression.index, bound)
            return
        if expression.index.level in bound:
            raise GeneratingFunctionError(
                f"Nested Sum or Product cannot rebind j[{expression.index.level}]",
            )
        body = expression.summand if isinstance(expression, GFInfiniteSum) else expression.factor
        self._validate_indices(body, bound | {expression.index.level})

    def _expect(self, expected: str) -> None:
        token = self._take()
        if token != expected:
            raise self._error(f"Expected {expected!r}, found {token!r}")

    def _take(self) -> str:
        if self.position >= len(self.tokens):
            raise self._error("Unexpected end of generating function")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def _peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _error(self, message: str) -> GeneratingFunctionError:
        nearby = " ".join(self.tokens[max(0, self.position - 2) : self.position + 3])
        return GeneratingFunctionError(f"{message} near {nearby!r}")


def parse_generating_function(source: str) -> GFParseResult:
    """Parse a supported ECS generating-function expression or equation system."""

    return GeneratingFunctionParser(source).parse()


_VALUATION_SEARCH_LIMIT = 10_000


class _FormalSeries:
    """A lazily evaluated exact Laurent series used by the public expander."""

    def __init__(
        self,
        lower_bound: int,
        coefficient: Callable[[int], Fraction],
        *,
        exact_constant: Fraction | None = None,
        is_constant: bool = False,
    ):
        self.lower_bound = lower_bound
        self._coefficient = coefficient
        self._cache: dict[int, Fraction] = {}
        self.exact_constant = exact_constant
        self.is_constant = is_constant
        self._valuation: int | None = None

    @property
    def is_zero(self) -> bool:
        return self.is_constant and self.exact_constant == 0

    def coefficient(self, degree: int) -> Fraction:
        if degree < self.lower_bound:
            return Fraction()
        if degree not in self._cache:
            self._cache[degree] = self._coefficient(degree)
        return self._cache[degree]

    def valuation(self) -> int:
        if self.is_zero:
            raise GeneratingFunctionEvaluationError("The zero series has no valuation")
        if self._valuation is None:
            degree = self.lower_bound
            while self.coefficient(degree) == 0:
                degree += 1
                if degree - self.lower_bound > _VALUATION_SEARCH_LIMIT:
                    raise GeneratingFunctionEvaluationError(
                        "Could not determine a series valuation after "
                        f"{_VALUATION_SEARCH_LIMIT} exact coefficients",
                    )
            self._valuation = degree
        return self._valuation


def _constant_series(value: int | Fraction) -> _FormalSeries:
    constant = Fraction(value)
    return _FormalSeries(
        0,
        lambda degree: constant if degree == 0 else Fraction(),
        exact_constant=constant,
        is_constant=True,
    )


def _negate(series: _FormalSeries) -> _FormalSeries:
    if series.is_constant:
        assert series.exact_constant is not None
        return _constant_series(-series.exact_constant)
    return _FormalSeries(
        series.lower_bound,
        lambda degree: -series.coefficient(degree),
    )


def _add(
    left: _FormalSeries,
    right: _FormalSeries,
    *,
    right_sign: Literal[-1, 1] = 1,
) -> _FormalSeries:
    if left.is_constant and right.is_constant:
        assert left.exact_constant is not None
        assert right.exact_constant is not None
        return _constant_series(left.exact_constant + right_sign * right.exact_constant)
    if left.is_zero:
        return right if right_sign == 1 else _negate(right)
    if right.is_zero:
        return left
    return _FormalSeries(
        min(left.lower_bound, right.lower_bound),
        lambda degree: left.coefficient(degree) + right_sign * right.coefficient(degree),
    )


def _scale(series: _FormalSeries, scalar: Fraction) -> _FormalSeries:
    if scalar == 0 or series.is_zero:
        return _constant_series(0)
    if series.is_constant:
        assert series.exact_constant is not None
        return _constant_series(scalar * series.exact_constant)
    return _FormalSeries(
        series.lower_bound,
        lambda degree: scalar * series.coefficient(degree),
    )


def _multiply(left: _FormalSeries, right: _FormalSeries) -> _FormalSeries:
    if left.is_zero or right.is_zero:
        return _constant_series(0)
    if left.is_constant:
        assert left.exact_constant is not None
        return _scale(right, left.exact_constant)
    if right.is_constant:
        assert right.exact_constant is not None
        return _scale(left, right.exact_constant)

    left_valuation = left.valuation()
    right_valuation = right.valuation()
    return _FormalSeries(
        left_valuation + right_valuation,
        lambda degree: sum(
            (
                left.coefficient(index) * right.coefficient(degree - index)
                for index in range(
                    left_valuation,
                    degree - right_valuation + 1,
                )
            ),
            Fraction(),
        ),
    )


def _divide(numerator: _FormalSeries, denominator: _FormalSeries) -> _FormalSeries:
    if denominator.is_zero:
        raise GeneratingFunctionEvaluationError("Division by the zero series")
    if numerator.is_zero:
        return _constant_series(0)
    if denominator.is_constant:
        assert denominator.exact_constant is not None
        return _scale(numerator, 1 / denominator.exact_constant)

    numerator_valuation = numerator.valuation()
    denominator_valuation = denominator.valuation()
    quotient_valuation = numerator_valuation - denominator_valuation
    leading_coefficient = denominator.coefficient(denominator_valuation)

    quotient: _FormalSeries

    def coefficient(degree: int) -> Fraction:
        product_degree = degree + denominator_valuation
        known_terms = sum(
            (
                denominator.coefficient(index) * quotient.coefficient(product_degree - index)
                for index in range(
                    denominator_valuation + 1,
                    product_degree - quotient_valuation + 1,
                )
            ),
            Fraction(),
        )
        return (numerator.coefficient(product_degree) - known_terms) / leading_coefficient

    quotient = _FormalSeries(quotient_valuation, coefficient)
    return quotient


def _integer_power(series: _FormalSeries, exponent: int) -> _FormalSeries:
    if exponent < 0:
        return _divide(_constant_series(1), _integer_power(series, -exponent))

    result = _constant_series(1)
    factor = series
    while exponent:
        if exponent & 1:
            result = _multiply(result, factor)
        exponent //= 2
        if exponent:
            factor = _multiply(factor, factor)
    return result


def _compose(outer: _FormalSeries, inner: _FormalSeries) -> _FormalSeries:
    """Compose two formal power series when ``inner`` has zero constant term."""

    if outer.is_zero:
        return _constant_series(0)
    if inner.is_zero:
        return _constant_series(outer.coefficient(0))
    if inner.coefficient(0) != 0 or (inner.lower_bound < 0 and inner.valuation() < 1):
        raise GeneratingFunctionEvaluationError(
            "Named-series composition requires an argument with constant coefficient 0",
        )

    inner_valuation = inner.valuation()
    powers = [_constant_series(1), inner]

    def power(exponent: int) -> _FormalSeries:
        while len(powers) <= exponent:
            powers.append(_multiply(powers[-1], inner))
        return powers[exponent]

    outer_constant = outer.coefficient(0)
    lower_bound = 0 if outer_constant else outer.valuation() * inner_valuation
    return _FormalSeries(
        lower_bound,
        lambda degree: sum(
            (
                outer.coefficient(exponent) * power(exponent).coefficient(degree)
                for exponent in range(degree // inner_valuation + 1)
            ),
            Fraction(),
        ),
    )


def _rational_power(series: _FormalSeries, exponent: Fraction) -> _FormalSeries:
    if exponent.denominator == 1:
        return _integer_power(series, exponent.numerator)
    if series.coefficient(0) != 1 or (series.lower_bound < 0 and series.valuation() != 0):
        raise GeneratingFunctionEvaluationError(
            "A nonintegral power requires a series with constant coefficient 1",
        )

    result: _FormalSeries

    def coefficient(degree: int) -> Fraction:
        if degree == 0:
            return Fraction(1)
        return (
            sum(
                (
                    ((exponent + 1) * index - degree)
                    * series.coefficient(index)
                    * result.coefficient(degree - index)
                    for index in range(1, degree + 1)
                ),
                Fraction(),
            )
            / degree
        )

    result = _FormalSeries(0, coefficient)
    return result


def _exponential(series: _FormalSeries) -> _FormalSeries:
    if series.is_zero:
        return _constant_series(1)
    if series.coefficient(0) != 0 or (series.lower_bound < 1 and series.valuation() < 1):
        raise GeneratingFunctionEvaluationError(
            "exp requires an argument with constant coefficient 0",
        )

    result: _FormalSeries

    def coefficient(degree: int) -> Fraction:
        if degree == 0:
            return Fraction(1)
        return (
            sum(
                (
                    index * series.coefficient(index) * result.coefficient(degree - index)
                    for index in range(1, degree + 1)
                ),
                Fraction(),
            )
            / degree
        )

    result = _FormalSeries(0, coefficient)
    return result


def _derivative(series: _FormalSeries) -> _FormalSeries:
    if series.is_constant:
        return _constant_series(0)
    return _FormalSeries(
        series.lower_bound - 1,
        lambda degree: (degree + 1) * series.coefficient(degree + 1),
    )


def _logarithm(series: _FormalSeries) -> _FormalSeries:
    if series.is_constant and series.exact_constant == 1:
        return _constant_series(0)
    if series.coefficient(0) != 1 or (series.lower_bound < 0 and series.valuation() != 0):
        raise GeneratingFunctionEvaluationError(
            "ln requires an argument with constant coefficient 1",
        )

    logarithmic_derivative = _divide(_derivative(series), series)
    return _FormalSeries(
        0,
        lambda degree: (
            Fraction() if degree == 0 else logarithmic_derivative.coefficient(degree - 1) / degree
        ),
    )


def _lambert_w(series: _FormalSeries) -> _FormalSeries:
    """Return the principal formal Lambert W series composed with ``series``."""

    if series.is_zero:
        return _constant_series(0)
    valuation = series.valuation()
    if valuation < 1:
        raise GeneratingFunctionEvaluationError(
            "LambertW requires an argument with constant coefficient 0",
        )

    powers = [_constant_series(1), series]

    def power(exponent: int) -> _FormalSeries:
        while len(powers) <= exponent:
            powers.append(_multiply(powers[-1], series))
        return powers[exponent]

    def coefficient(degree: int) -> Fraction:
        return sum(
            (
                Fraction((-exponent) ** (exponent - 1), factorial(exponent))
                * power(exponent).coefficient(degree)
                for exponent in range(1, degree // valuation + 1)
            ),
            Fraction(),
        )

    return _FormalSeries(valuation, coefficient)


def _shifted_lambert_w(
    logarithmic_perturbation: _FormalSeries,
    center: Fraction,
) -> _FormalSeries:
    """Expand principal W around ``center * exp(center)`` exactly."""

    if center == -1:
        raise GeneratingFunctionEvaluationError(
            "Shifted LambertW expansion is singular at the branch point -1/e",
        )
    if center == 0:
        raise GeneratingFunctionEvaluationError(
            "A shifted LambertW center must be nonzero",
        )
    if logarithmic_perturbation.is_zero:
        return _constant_series(center)

    valuation = logarithmic_perturbation.valuation()
    if valuation < 1:
        raise GeneratingFunctionEvaluationError(
            "Shifted LambertW requires a logarithmic perturbation with constant coefficient 0",
        )

    linear_coefficient = 1 + 1 / center
    displacement: _FormalSeries
    powers: list[_FormalSeries]

    def power(exponent: int) -> _FormalSeries:
        while len(powers) <= exponent:
            powers.append(_multiply(powers[-1], displacement))
        return powers[exponent]

    def coefficient(degree: int) -> Fraction:
        nonlinear = sum(
            (
                Fraction((-1) ** (exponent + 1), exponent)
                * power(exponent).coefficient(degree)
                / center**exponent
                for exponent in range(2, degree // valuation + 1)
            ),
            Fraction(),
        )
        return (logarithmic_perturbation.coefficient(degree) - nonlinear) / linear_coefficient

    displacement = _FormalSeries(valuation, coefficient)
    powers = [_constant_series(1), displacement]
    return _add(_constant_series(center), displacement)


@cache
def _euler_totient(value: int) -> int:
    """Return Euler's totient for a positive summation-index value."""

    result = value
    remaining = value
    divisor = 2
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            while remaining % divisor == 0:
                remaining //= divisor
            result -= result // divisor
        divisor += 1
    if remaining > 1:
        result -= result // remaining
    return result


def _constant_expression_value(
    expression: GFExpression,
    index_values: dict[int, int],
) -> Fraction:
    if isinstance(expression, GFInteger):
        return Fraction(expression.value)
    if isinstance(expression, GFIndex):
        try:
            return Fraction(index_values[expression.level])
        except KeyError as error:
            raise GeneratingFunctionEvaluationError(
                f"Summation index j[{expression.level}] has no evaluation value",
            ) from error
    if isinstance(expression, GFTotient):
        return Fraction(
            _euler_totient(int(_constant_expression_value(expression.index, index_values)))
        )
    if isinstance(expression, GFIndexedCoefficient):
        raise GeneratingFunctionEvaluationError(
            f"Indexed coefficient {expression.name}_k requires an equation solver",
        )
    if isinstance(expression, GFUnary):
        value = _constant_expression_value(expression.operand, index_values)
        return value if expression.operator == "+" else -value
    if isinstance(expression, GFBinary):
        left = _constant_expression_value(expression.left, index_values)
        right = _constant_expression_value(expression.right, index_values)
        if expression.operator == "+":
            return left + right
        if expression.operator == "-":
            return left - right
        if expression.operator == "*":
            return left * right
        if expression.operator == "/":
            if right == 0:
                raise GeneratingFunctionEvaluationError("Division by zero in an exponent")
            return left / right
        if right.denominator == 1:
            return left**right.numerator
        if left == 1:
            return Fraction(1)
    raise GeneratingFunctionEvaluationError("A power exponent must be a rational constant")


def _try_constant_expression_value(
    expression: GFExpression,
    index_values: dict[int, int],
) -> Fraction | None:
    try:
        return _constant_expression_value(expression, index_values)
    except GeneratingFunctionEvaluationError:
        return None


def _constant_addend_and_remainder(
    expression: GFExpression,
    index_values: dict[int, int],
) -> tuple[Fraction, GFExpression] | None:
    constant = _try_constant_expression_value(expression, index_values)
    if constant is not None:
        return constant, GFInteger(0)
    if not isinstance(expression, GFBinary):
        return None
    if expression.operator == "+":
        left = _try_constant_expression_value(expression.left, index_values)
        if left is not None:
            return left, expression.right
        right = _try_constant_expression_value(expression.right, index_values)
        if right is not None:
            return right, expression.left
    if expression.operator == "-":
        right = _try_constant_expression_value(expression.right, index_values)
        if right is not None:
            return -right, expression.left
    return None


def _match_shifted_lambert_w(
    argument: GFExpression,
    index_values: dict[int, int],
) -> tuple[Fraction, GFExpression] | None:
    """Recognize ``c * exp(c + h)`` for a principal-branch center ``c``."""

    if not isinstance(argument, GFBinary) or argument.operator != "*":
        return None
    pairs = ((argument.left, argument.right), (argument.right, argument.left))
    for constant_expression, exponential_expression in pairs:
        center = _try_constant_expression_value(constant_expression, index_values)
        if (
            center is None
            or center == 0
            or center < -1
            or not isinstance(exponential_expression, GFFunction)
            or exponential_expression.name != "exp"
        ):
            continue
        decomposition = _constant_addend_and_remainder(
            exponential_expression.argument,
            index_values,
        )
        if decomposition is None:
            continue
        exponential_center, remainder = decomposition
        if exponential_center == center:
            return center, remainder
    return None


def _is_x_free(expression: GFExpression) -> bool:
    if isinstance(expression, GFInteger | GFIndex | GFTotient | GFIndexedCoefficient):
        return True
    if isinstance(expression, GFVariable):
        return expression.name != "_x"
    if isinstance(expression, GFUnary):
        return _is_x_free(expression.operand)
    if isinstance(expression, GFFunction):
        return _is_x_free(expression.argument)
    if isinstance(expression, GFSeriesCall):
        return False
    if isinstance(expression, GFRootOf):
        return _is_x_free(expression.equation)
    if isinstance(expression, GFComplex):
        return _is_x_free(expression.value)
    if isinstance(expression, GFInfiniteSum):
        return _is_x_free(expression.summand)
    if isinstance(expression, GFInfiniteProduct):
        return _is_x_free(expression.factor)
    return _is_x_free(expression.left) and _is_x_free(expression.right)


def _positive_exponent_index_factors(expression: GFExpression) -> frozenset[int] | None:
    """Return known index factors of a positive integer exponent expression."""

    if isinstance(expression, GFInteger):
        return frozenset() if expression.value > 0 else None
    if isinstance(expression, GFIndex):
        return frozenset({expression.level})
    if isinstance(expression, GFUnary) and expression.operator == "+":
        return _positive_exponent_index_factors(expression.operand)
    if isinstance(expression, GFBinary) and expression.operator == "*":
        left = _positive_exponent_index_factors(expression.left)
        right = _positive_exponent_index_factors(expression.right)
        if left is not None and right is not None:
            return left | right
    if isinstance(expression, GFBinary) and expression.operator == "^":
        base = _positive_exponent_index_factors(expression.left)
        exponent = _positive_exponent_index_factors(expression.right)
        if base is not None and exponent is not None:
            return base | exponent
    return None


def _x_monomial_index_factors(expression: GFExpression) -> frozenset[int] | None:
    """Return index factors known to divide the degree of an x monomial."""

    if isinstance(expression, GFVariable) and expression.name == "_x":
        return frozenset()
    if isinstance(expression, GFBinary) and expression.operator == "^":
        base = _x_monomial_index_factors(expression.left)
        exponent = _positive_exponent_index_factors(expression.right)
        if base is not None and exponent is not None:
            return base | exponent
    return None


def _is_index_scaled(expression: GFExpression, level: int) -> bool:
    """Prove syntactically that ``expression`` is a series in ``x^j[level]``."""

    if _is_x_free(expression):
        return True
    monomial_factors = _x_monomial_index_factors(expression)
    if monomial_factors is not None and level in monomial_factors:
        return True
    if isinstance(expression, GFSeriesCall):
        return _is_index_scaled(expression.argument, level)
    if isinstance(
        expression,
        GFVariable | GFInteger | GFIndex | GFTotient | GFIndexedCoefficient,
    ):
        return False
    if isinstance(expression, GFUnary):
        return _is_index_scaled(expression.operand, level)
    if isinstance(expression, GFFunction):
        return _is_index_scaled(expression.argument, level)
    if isinstance(expression, GFRootOf):
        return False
    if isinstance(expression, GFComplex):
        return _is_index_scaled(expression.value, level)
    if isinstance(expression, GFInfiniteSum):
        return _is_index_scaled(expression.summand, level)
    if isinstance(expression, GFInfiniteProduct):
        return _is_index_scaled(expression.factor, level)
    if expression.operator == "^":
        return _is_index_scaled(expression.left, level) and _is_x_free(expression.right)
    return _is_index_scaled(expression.left, level) and _is_index_scaled(
        expression.right,
        level,
    )


def _provably_positive(expression: GFExpression) -> bool:
    if isinstance(expression, GFInteger):
        return expression.value > 0
    if isinstance(expression, GFIndex | GFTotient):
        return True
    if isinstance(expression, GFUnary):
        return expression.operator == "+" and _provably_positive(expression.operand)
    if isinstance(expression, GFBinary) and expression.operator == "*":
        return _provably_positive(expression.left) and _provably_positive(expression.right)
    return False


def _constant_term(
    expression: GFExpression,
    series_constants: Mapping[str, Fraction] | None = None,
) -> Fraction | None:
    """Return a provable index-independent constant term, or ``None``."""

    if isinstance(expression, GFInteger):
        return Fraction(expression.value)
    if isinstance(expression, GFVariable):
        return Fraction() if expression.name == "_x" else None
    if isinstance(
        expression,
        GFIndex | GFTotient | GFIndexedCoefficient | GFInfiniteProduct | GFRootOf | GFComplex,
    ):
        return None
    if isinstance(expression, GFSeriesCall):
        argument_constant = _constant_term(expression.argument, series_constants)
        if argument_constant != 0 or series_constants is None:
            return None
        return series_constants.get(expression.name)
    if isinstance(expression, GFUnary):
        value = _constant_term(expression.operand, series_constants)
        if value is None:
            return None
        return value if expression.operator == "+" else -value
    if isinstance(expression, GFFunction):
        value = _constant_term(expression.argument, series_constants)
        if expression.name == "exp" and value == 0:
            return Fraction(1)
        if expression.name == "ln" and value == 1:
            return Fraction()
        if expression.name == "LambertW" and value == 0:
            return Fraction()
        return None
    if isinstance(expression, GFInfiniteSum):
        return Fraction() if _has_finite_sum_bound(expression, series_constants) else None

    left = _constant_term(expression.left, series_constants)
    right = _constant_term(expression.right, series_constants)
    if expression.operator == "+":
        return left + right if left is not None and right is not None else None
    if expression.operator == "-":
        if expression.left == expression.right:
            return Fraction()
        return left - right if left is not None and right is not None else None
    if expression.operator == "*":
        if left == 0 or right == 0:
            return Fraction()
        return left * right if left is not None and right is not None else None
    if expression.operator == "/":
        if left == 0 and _provably_nonzero_constant(expression.right):
            return Fraction()
        if left is not None and right not in {None, Fraction()}:
            return left / right
        return None
    if left == 1:
        return Fraction(1)
    if left == 0 and _provably_positive(expression.right):
        return Fraction()
    if left is not None and right is not None and right.denominator == 1:
        if left == 0 and right < 0:
            return None
        return left**right.numerator
    return None


def _provably_nonzero_constant(expression: GFExpression) -> bool:
    value = _constant_term(expression)
    if value is not None:
        return value != 0
    if isinstance(expression, GFIndex | GFTotient):
        return True
    if isinstance(expression, GFUnary):
        return _provably_nonzero_constant(expression.operand)
    if isinstance(expression, GFBinary) and expression.operator in {"*", "/"}:
        return _provably_nonzero_constant(
            expression.left,
        ) and _provably_nonzero_constant(expression.right)
    if isinstance(expression, GFBinary) and expression.operator == "^":
        return _provably_nonzero_constant(expression.left)
    return False


def _has_finite_sum_bound(
    expression: GFInfiniteSum,
    series_constants: Mapping[str, Fraction] | None = None,
) -> bool:
    """Prove that coefficient n only needs summation indices through n."""

    return (
        _is_index_scaled(expression.summand, expression.index.level)
        and _constant_term(expression.summand, series_constants) == 0
    )


@cache
def _positive_divisors(value: int) -> tuple[int, ...]:
    small: list[int] = []
    large: list[int] = []
    divisor = 1
    while divisor * divisor <= value:
        if value % divisor == 0:
            small.append(divisor)
            if divisor * divisor != value:
                large.append(value // divisor)
        divisor += 1
    return tuple(small + large[::-1])


def _infinite_sum(
    expression: GFInfiniteSum,
    index_values: dict[int, int],
    series_values: Mapping[str, _FormalSeries] | None = None,
) -> _FormalSeries:
    series_constants = (
        {name: series.coefficient(0) for name, series in series_values.items()}
        if series_values is not None
        else None
    )
    if not _has_finite_sum_bound(expression, series_constants):
        raise GeneratingFunctionEvaluationError(
            "Infinite Sum exact expansion requires a zero-constant summand whose "
            f"x degrees are all scaled by j[{expression.index.level}]",
        )

    outer_values = dict(index_values)
    outer_scale = prod(
        value
        for level, value in outer_values.items()
        if _is_index_scaled(expression.summand, level)
    )
    summands: dict[int, _FormalSeries] = {}

    def summand(index: int) -> _FormalSeries:
        if index not in summands:
            values = outer_values | {expression.index.level: index}
            summands[index] = _evaluate_series(
                expression.summand,
                values,
                series_values,
            )
        return summands[index]

    def coefficient(degree: int) -> Fraction:
        if degree % outer_scale:
            return Fraction()
        return sum(
            (
                summand(index).coefficient(degree)
                for index in _positive_divisors(degree // outer_scale)
                if index >= expression.lower_bound
            ),
            Fraction(),
        )

    return _FormalSeries(outer_scale, coefficient)


def _evaluate_series(
    expression: GFExpression,
    index_values: dict[int, int] | None = None,
    series_values: Mapping[str, _FormalSeries] | None = None,
) -> _FormalSeries:
    if index_values is None:
        index_values = {}
    if isinstance(expression, GFInteger):
        return _constant_series(expression.value)
    if isinstance(expression, GFIndex):
        return _constant_series(_constant_expression_value(expression, index_values))
    if isinstance(expression, GFTotient):
        return _constant_series(_constant_expression_value(expression, index_values))
    if isinstance(expression, GFVariable):
        if expression.name == "_Z":
            raise GeneratingFunctionEvaluationError(
                "Root variable '_Z' can only be evaluated through a selected RootOf branch",
            )
        return _FormalSeries(
            1,
            lambda degree: Fraction(1) if degree == 1 else Fraction(),
        )
    if isinstance(expression, GFUnary):
        operand = _evaluate_series(expression.operand, index_values, series_values)
        return operand if expression.operator == "+" else _negate(operand)
    if isinstance(expression, GFFunction):
        if expression.name == "LambertW":
            shifted = _match_shifted_lambert_w(expression.argument, index_values)
            if shifted is not None:
                center, remainder = shifted
                return _shifted_lambert_w(
                    _evaluate_series(remainder, index_values, series_values),
                    center,
                )
            return _lambert_w(
                _evaluate_series(expression.argument, index_values, series_values),
            )
        argument = _evaluate_series(expression.argument, index_values, series_values)
        if expression.name == "exp":
            return _exponential(argument)
        return _logarithm(argument)
    if isinstance(expression, GFRootOf):
        raise GeneratingFunctionEvaluationError(
            "RootOf has no branch selector; exact coefficient expansion requires "
            "an explicit formal-series branch",
        )
    if isinstance(expression, GFComplex):
        raise GeneratingFunctionEvaluationError(
            "Complex exact coefficient expansion requires complex formal-series support",
        )
    if isinstance(expression, GFIndexedCoefficient):
        raise GeneratingFunctionEvaluationError(
            f"Indexed coefficient {expression.name}_k requires an equation solver",
        )
    if isinstance(expression, GFInfiniteProduct):
        raise GeneratingFunctionEvaluationError(
            "Infinite Product exact expansion requires a symbolic-product solver",
        )
    if isinstance(expression, GFInfiniteSum):
        return _infinite_sum(expression, index_values, series_values)
    if isinstance(expression, GFSeriesCall):
        if series_values is None:
            raise GeneratingFunctionEvaluationError(
                f"Named series call {expression.name}(...) requires an implicit-equation solver",
            )
        if expression.name not in series_values:
            raise GeneratingFunctionEvaluationError(
                f"Named series call {expression.name}(...) has no defining equation",
            )
        return _compose(
            series_values[expression.name],
            _evaluate_series(expression.argument, index_values, series_values),
        )
    if expression.operator == "^":
        return _rational_power(
            _evaluate_series(expression.left, index_values, series_values),
            _constant_expression_value(expression.right, index_values),
        )
    if expression.operator == "-" and expression.left == expression.right:
        return _constant_series(0)

    left = _evaluate_series(expression.left, index_values, series_values)
    right = _evaluate_series(expression.right, index_values, series_values)
    if expression.operator == "+":
        return _add(left, right)
    if expression.operator == "-":
        return _add(left, right, right_sign=-1)
    if expression.operator == "*":
        return _multiply(left, right)
    return _divide(left, right)


def _require_supported_evaluation(
    expression: GFExpression,
    bound_indices: frozenset[int] = frozenset(),
    series_names: frozenset[str] | None = None,
    series_constants: Mapping[str, Fraction] | None = None,
) -> None:
    """Reject semantic boundaries before local series conditions obscure them."""

    if isinstance(expression, GFRootOf):
        raise GeneratingFunctionEvaluationError(
            "RootOf has no branch selector; exact coefficient expansion requires "
            "an explicit formal-series branch",
        )
    if isinstance(expression, GFComplex):
        raise GeneratingFunctionEvaluationError(
            "Complex exact coefficient expansion requires complex formal-series support",
        )
    if isinstance(expression, GFSeriesCall):
        if series_names is None:
            raise GeneratingFunctionEvaluationError(
                f"Named series call {expression.name}(...) requires an implicit-equation solver",
            )
        if expression.name not in series_names:
            raise GeneratingFunctionEvaluationError(
                f"Named series call {expression.name}(...) has no defining equation",
            )
        _require_supported_evaluation(
            expression.argument,
            bound_indices,
            series_names,
            series_constants,
        )
        return
    if isinstance(expression, GFIndexedCoefficient):
        raise GeneratingFunctionEvaluationError(
            f"Indexed coefficient {expression.name}_k requires an equation solver",
        )
    if isinstance(expression, GFInfiniteProduct):
        raise GeneratingFunctionEvaluationError(
            "Infinite Product exact expansion requires a symbolic-product solver",
        )
    if isinstance(expression, GFInfiniteSum):
        nested_bound_indices = bound_indices | {expression.index.level}
        _require_supported_evaluation(
            expression.summand,
            nested_bound_indices,
            series_names,
            series_constants,
        )
        if not _has_finite_sum_bound(expression, series_constants):
            raise GeneratingFunctionEvaluationError(
                "Infinite Sum exact expansion requires a zero-constant summand whose "
                f"x degrees are all scaled by j[{expression.index.level}]",
            )
        return
    if isinstance(expression, GFIndex):
        if expression.level not in bound_indices:
            raise GeneratingFunctionEvaluationError(
                "An index can only be evaluated inside a supported infinite aggregate",
            )
        return
    if isinstance(expression, GFTotient):
        _require_supported_evaluation(
            expression.index,
            bound_indices,
            series_names,
            series_constants,
        )
        return
    if isinstance(expression, (GFInteger, GFVariable)):
        return
    if isinstance(expression, GFUnary):
        _require_supported_evaluation(
            expression.operand,
            bound_indices,
            series_names,
            series_constants,
        )
        return
    if isinstance(expression, GFFunction):
        _require_supported_evaluation(
            expression.argument,
            bound_indices,
            series_names,
            series_constants,
        )
        return
    _require_supported_evaluation(
        expression.left,
        bound_indices,
        series_names,
        series_constants,
    )
    _require_supported_evaluation(
        expression.right,
        bound_indices,
        series_names,
        series_constants,
    )


def _truncated_series(coefficients: tuple[Fraction, ...]) -> _FormalSeries:
    nonzero_degrees = [degree for degree, coefficient in enumerate(coefficients) if coefficient]
    if not nonzero_degrees:
        return _constant_series(0)
    if nonzero_degrees == [0]:
        return _constant_series(coefficients[0])
    return _FormalSeries(
        nonzero_degrees[0],
        lambda degree: coefficients[degree] if 0 <= degree < len(coefficients) else Fraction(),
    )


def _assignment_expressions(
    equations: GFEquation | GFEquationSystem,
) -> dict[str, GFExpression]:
    members = equations.equations if isinstance(equations, GFEquationSystem) else (equations,)
    assignments: dict[str, GFExpression] = {}
    for equation in members:
        left = equation.left
        if not (isinstance(left, GFSeriesCall) and left.argument == GFVariable()):
            raise GeneratingFunctionEvaluationError(
                "Fixed-point equation solving requires each left side to be a named "
                "series evaluated at x",
            )
        if left.name in assignments:
            raise GeneratingFunctionEvaluationError(
                f"Named series {left.name!r} has more than one defining equation",
            )
        assignments[left.name] = equation.right
    return assignments


def _fixed_point_iteration(
    assignments: Mapping[str, GFExpression],
    initial_values: Mapping[str, tuple[Fraction, ...]],
    coefficient_count: int,
) -> dict[str, tuple[Fraction, ...]]:
    values = dict(initial_values)
    maximum_iterations = max(
        12,
        (coefficient_count + 1) * len(assignments) + 8,
    )
    for _ in range(maximum_iterations):
        series_values = {
            name: _truncated_series(coefficients) for name, coefficients in values.items()
        }
        updated = {}
        for name, expression in assignments.items():
            series = _evaluate_series(expression, series_values=series_values)
            updated[name] = tuple(series.coefficient(degree) for degree in range(coefficient_count))
        if updated == values:
            return updated
        values = updated
    raise GeneratingFunctionEvaluationError(
        "Named-series equations did not stabilize under exact fixed-point iteration; "
        "same-degree feedback requires a more general implicit-equation solver",
    )


def _fixed_point_coefficients(
    equations: GFEquation | GFEquationSystem,
    coefficient_count: int,
    symbol: str | None,
) -> tuple[Fraction, ...]:
    assignments = _assignment_expressions(equations)
    names = frozenset(assignments)
    if symbol is None:
        if len(assignments) != 1:
            raise GeneratingFunctionEvaluationError(
                "An equation system requires a symbol selecting the series to return",
            )
        selected = next(iter(assignments))
    elif symbol not in assignments:
        raise GeneratingFunctionEvaluationError(
            f"Equation system has no defining equation for series {symbol!r}",
        )
    else:
        selected = symbol

    probe_count = max(2, coefficient_count)
    constants = {name: Fraction() for name in names}
    for expression in assignments.values():
        _require_supported_evaluation(
            expression,
            series_names=names,
            series_constants=constants,
        )

    zero = (Fraction(),) * probe_count
    least = _fixed_point_iteration(
        assignments,
        {name: zero for name in names},
        probe_count,
    )
    positive_probe = (Fraction(),) + (Fraction(1),) * (probe_count - 1)
    checked = _fixed_point_iteration(
        assignments,
        {name: positive_probe for name in names},
        probe_count,
    )
    if checked != least:
        raise GeneratingFunctionEvaluationError(
            "Named-series equations are not contractive on zero-constant formal "
            "series; a more general implicit-equation solver is required",
        )
    return least[selected][:coefficient_count]


def generating_function_coefficients(
    source: str | GFParseResult,
    coefficient_count: int,
    *,
    symbol: str | None = None,
) -> tuple[Fraction, ...]:
    """Return exact coefficients from degree zero through ``count - 1``.

    ``source`` may be either stored ECS text or a result returned by
    :func:`parse_generating_function`. Contractive named-series assignments are
    solved by exact fixed-point iteration; ``symbol`` selects the returned
    member of an equation system. The coefficients are the raw formal series
    coefficients. Callers interpreting an exponential generating function must
    multiply coefficient ``n`` by ``n!`` to obtain its counting term.
    """

    if isinstance(coefficient_count, bool) or not isinstance(coefficient_count, int):
        raise TypeError("coefficient_count must be an integer")
    if coefficient_count < 0:
        raise ValueError("coefficient_count must be nonnegative")
    if symbol is not None and (not isinstance(symbol, str) or not symbol):
        raise TypeError("symbol must be a nonempty string or None")

    expression = parse_generating_function(source) if isinstance(source, str) else source
    if isinstance(expression, GFEquation | GFEquationSystem):
        return _fixed_point_coefficients(expression, coefficient_count, symbol)
    if not isinstance(
        expression,
        (
            GFInteger,
            GFVariable,
            GFUnary,
            GFBinary,
            GFFunction,
            GFSeriesCall,
            GFRootOf,
            GFComplex,
            GFIndex,
            GFTotient,
            GFIndexedCoefficient,
            GFInfiniteSum,
            GFInfiniteProduct,
        ),
    ):
        raise TypeError("source must be generating-function text or a GFParseResult")
    if symbol is not None:
        raise ValueError("symbol can only select a member of a generating-function equation")

    _require_supported_evaluation(expression)
    series = _evaluate_series(expression)
    if not series.is_zero and series.lower_bound < 0 and series.valuation() < 0:
        raise GeneratingFunctionEvaluationError(
            "The expression has negative powers and is not a formal power series",
        )
    return tuple(series.coefficient(degree) for degree in range(coefficient_count))


__all__ = [
    "GFBinary",
    "GFComplex",
    "GFEquation",
    "GFEquationSystem",
    "GFExpression",
    "GFFunction",
    "GFIndex",
    "GFIndexedCoefficient",
    "GFInfiniteProduct",
    "GFInfiniteSum",
    "GFInteger",
    "GFParseResult",
    "GFRootOf",
    "GFSeriesCall",
    "GFTotient",
    "GFUnary",
    "GFVariable",
    "GeneratingFunctionError",
    "GeneratingFunctionEvaluationError",
    "GeneratingFunctionParser",
    "UnsupportedGeneratingFunction",
    "generating_function_coefficients",
    "parse_generating_function",
]
