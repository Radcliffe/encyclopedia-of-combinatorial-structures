"""Parse and expand finite ECS generating functions exactly.

The parser recognizes the finite elementary grammar, principal ``LambertW``
calls, unselected ``RootOf`` equations, indexed infinite sums, and the
one-argument ``Complex`` constructor used by 1,017 stored ECS generating
functions. Heterogeneous equation fields are rejected clearly for a later
parser milestone. The series evaluator uses exact rational arithmetic and
expands ``LambertW`` compositions whose argument has constant term zero.
Unselected roots, infinite sums, and complex series remain explicit evaluation
boundaries; the evaluator never guesses a branch or truncation.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from math import factorial
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
class GFRootOf:
    """An unselected Maple ``RootOf`` equation in its local ``_Z`` variable."""

    equation: GFExpression


@dataclass(frozen=True, slots=True)
class GFComplex:
    """A one-argument Maple ``Complex`` constructor representing ``I * value``."""

    value: GFExpression


@dataclass(frozen=True, slots=True)
class GFIndex:
    """A Maple indexed summation variable such as ``j[1]``."""

    level: int


@dataclass(frozen=True, slots=True)
class GFTotient:
    """Euler's totient applied to an indexed summation variable."""

    index: GFIndex


@dataclass(frozen=True, slots=True)
class GFInfiniteSum:
    """A sum over one indexed variable from one through infinity."""

    summand: GFExpression
    index: GFIndex


type GFExpression = (
    GFInteger
    | GFVariable
    | GFUnary
    | GFBinary
    | GFFunction
    | GFRootOf
    | GFComplex
    | GFIndex
    | GFTotient
    | GFInfiniteSum
)


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


class GeneratingFunctionParser:
    """Parse the supported finite expression syntax used by the ECS."""

    def __init__(self, source: str):
        self.source = source
        self.tokens = self._tokenize(source)
        self.position = 0
        self.root_depth = 0

    @staticmethod
    def _tokenize(source: str) -> list[str]:
        if source.strip() == "":
            raise GeneratingFunctionError("Generating-function source must not be empty")
        if "..." in source:
            raise UnsupportedGeneratingFunction(
                "Infinite or ellipsis-based generating functions are not supported",
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

    def parse(self) -> GFExpression:
        """Parse and return one immutable generating-function expression."""

        expression = self._parse_expression()
        if self.position != len(self.tokens):
            raise self._error(f"Unexpected token {self._peek()!r} after expression")
        self._validate_indices(expression, frozenset())
        return expression

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
        if token == "_x":
            return GFVariable()
        if token == "_Z":
            if self.root_depth == 0:
                raise self._error("Root variable '_Z' is only valid inside RootOf")
            return GFVariable("_Z")
        if token == "j":
            return self._parse_index_suffix()
        if token in {"+", "-"}:
            return GFUnary(
                cast(UnaryOperator, token),
                self._parse_expression(UNARY_BINDING_POWER),
            )
        if token == "(":
            expression = self._parse_expression()
            self._expect(")")
            return expression
        if token in {"exp", "ln", "LambertW"}:
            self._expect("(")
            argument = self._parse_expression()
            self._expect(")")
            return GFFunction(cast(FunctionName, token), argument)
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
            index = self._parse_index_suffix()
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
        if IDENTIFIER_RE.fullmatch(token):
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
                    f"Summation index j[{expression.level}] is not bound by a Sum",
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
        if isinstance(expression, GFRootOf):
            self._validate_indices(expression.equation, bound)
            return
        if isinstance(expression, GFComplex):
            self._validate_indices(expression.value, bound)
            return
        if isinstance(expression, GFTotient):
            self._validate_indices(expression.index, bound)
            return
        if expression.index.level in bound:
            raise GeneratingFunctionError(
                f"Nested Sum cannot rebind j[{expression.index.level}]",
            )
        self._validate_indices(expression.summand, bound | {expression.index.level})

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


def parse_generating_function(source: str) -> GFExpression:
    """Parse a supported finite ECS generating-function expression."""

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


def _rational_power(series: _FormalSeries, exponent: Fraction) -> _FormalSeries:
    if exponent.denominator == 1:
        return _integer_power(series, exponent.numerator)
    if series.valuation() != 0 or series.coefficient(0) != 1:
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
    if series.valuation() < 1:
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
    if series.valuation() != 0 or series.coefficient(0) != 1:
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


def _constant_expression_value(expression: GFExpression) -> Fraction:
    if isinstance(expression, GFInteger):
        return Fraction(expression.value)
    if isinstance(expression, GFUnary):
        value = _constant_expression_value(expression.operand)
        return value if expression.operator == "+" else -value
    if isinstance(expression, GFBinary):
        left = _constant_expression_value(expression.left)
        right = _constant_expression_value(expression.right)
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


def _evaluate_series(expression: GFExpression) -> _FormalSeries:
    if isinstance(expression, GFInteger):
        return _constant_series(expression.value)
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
        operand = _evaluate_series(expression.operand)
        return operand if expression.operator == "+" else _negate(operand)
    if isinstance(expression, GFFunction):
        argument = _evaluate_series(expression.argument)
        if expression.name == "exp":
            return _exponential(argument)
        if expression.name == "ln":
            return _logarithm(argument)
        return _lambert_w(argument)
    if isinstance(expression, GFRootOf):
        raise GeneratingFunctionEvaluationError(
            "RootOf has no branch selector; exact coefficient expansion requires "
            "an explicit formal-series branch",
        )
    if isinstance(expression, GFComplex):
        raise GeneratingFunctionEvaluationError(
            "Complex exact coefficient expansion requires complex formal-series support",
        )
    if isinstance(expression, GFInfiniteSum):
        raise GeneratingFunctionEvaluationError(
            "Infinite Sum exact expansion requires a proven finite truncation bound",
        )
    if isinstance(expression, (GFIndex, GFTotient)):
        raise GeneratingFunctionEvaluationError(
            "A summation index can only be evaluated inside a supported infinite Sum",
        )
    if expression.operator == "^":
        return _rational_power(
            _evaluate_series(expression.left),
            _constant_expression_value(expression.right),
        )
    if expression.operator == "-" and expression.left == expression.right:
        return _constant_series(0)

    left = _evaluate_series(expression.left)
    right = _evaluate_series(expression.right)
    if expression.operator == "+":
        return _add(left, right)
    if expression.operator == "-":
        return _add(left, right, right_sign=-1)
    if expression.operator == "*":
        return _multiply(left, right)
    return _divide(left, right)


def _require_supported_evaluation(expression: GFExpression) -> None:
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
    if isinstance(expression, GFInfiniteSum):
        raise GeneratingFunctionEvaluationError(
            "Infinite Sum exact expansion requires a proven finite truncation bound",
        )
    if isinstance(expression, (GFIndex, GFTotient)):
        raise GeneratingFunctionEvaluationError(
            "A summation index can only be evaluated inside a supported infinite Sum",
        )
    if isinstance(expression, (GFInteger, GFVariable)):
        return
    if isinstance(expression, GFUnary):
        _require_supported_evaluation(expression.operand)
        return
    if isinstance(expression, GFFunction):
        _require_supported_evaluation(expression.argument)
        return
    _require_supported_evaluation(expression.left)
    _require_supported_evaluation(expression.right)


def generating_function_coefficients(
    source: str | GFExpression,
    coefficient_count: int,
) -> tuple[Fraction, ...]:
    """Return exact coefficients from degree zero through ``count - 1``.

    ``source`` may be either stored ECS text or an expression returned by
    :func:`parse_generating_function`. The coefficients are the raw formal
    series coefficients. Callers interpreting an exponential generating
    function must multiply coefficient ``n`` by ``n!`` to obtain its counting
    term.
    """

    if isinstance(coefficient_count, bool) or not isinstance(coefficient_count, int):
        raise TypeError("coefficient_count must be an integer")
    if coefficient_count < 0:
        raise ValueError("coefficient_count must be nonnegative")

    expression = parse_generating_function(source) if isinstance(source, str) else source
    if not isinstance(
        expression,
        (
            GFInteger,
            GFVariable,
            GFUnary,
            GFBinary,
            GFFunction,
            GFRootOf,
            GFComplex,
            GFIndex,
            GFTotient,
            GFInfiniteSum,
        ),
    ):
        raise TypeError("source must be generating-function text or a GFExpression")

    _require_supported_evaluation(expression)
    series = _evaluate_series(expression)
    if not series.is_zero and series.valuation() < 0:
        raise GeneratingFunctionEvaluationError(
            "The expression has negative powers and is not a formal power series",
        )
    return tuple(series.coefficient(degree) for degree in range(coefficient_count))


__all__ = [
    "GFBinary",
    "GFComplex",
    "GFExpression",
    "GFFunction",
    "GFIndex",
    "GFInfiniteSum",
    "GFInteger",
    "GFRootOf",
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
