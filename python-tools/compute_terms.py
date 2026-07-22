#!/usr/bin/env python3
"""Compute ECS sequence terms from a Maple combstruct-style specification.

The evaluator uses truncated ordinary generating functions for unlabelled
structures and exponential generating functions for labelled structures.
All arithmetic is exact.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence


class SpecificationError(ValueError):
    """The specification is malformed or does not define the requested symbol."""


class UnsupportedConstruction(SpecificationError):
    """The specification is valid but cannot be expanded safely by this evaluator."""


@dataclass(frozen=True)
class Cardinality:
    minimum: int = 0
    maximum: int | None = None

    def includes(self, value: int) -> bool:
        return value >= self.minimum and (self.maximum is None or value <= self.maximum)


@dataclass(frozen=True)
class Reference:
    name: str


@dataclass(frozen=True)
class Constructor:
    name: str
    arguments: tuple[Reference | "Constructor", ...]
    cardinality: Cardinality | None = None


Expression = Reference | Constructor
Series = list[Fraction]


TOKEN_RE = re.compile(r"\s*(<=|[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?|\d+|[{}(),=<])")


class Parser:
    def __init__(self, specification: str):
        self.specification = specification
        self.tokens = self._tokenize(specification)
        self.position = 0

    @staticmethod
    def _tokenize(specification: str) -> list[str]:
        tokens: list[str] = []
        position = 0
        while position < len(specification):
            match = TOKEN_RE.match(specification, position)
            if not match:
                if specification[position:].strip() == "":
                    break
                excerpt = specification[position : position + 20]
                raise SpecificationError(f"Unexpected input near {excerpt!r}")
            tokens.append(match.group(1))
            position = match.end()
        return tokens

    def parse(self) -> dict[str, Expression]:
        self._expect("{")
        equations: dict[str, Expression] = {}
        while self._peek() != "}":
            name = self._expect_identifier()
            self._expect("=")
            equations[name] = self._parse_expression()
            if self._peek() == ",":
                self.position += 1
            elif self._peek() != "}":
                raise self._error("Expected ',' or '}' after equation")
        self._expect("}")
        if self.position != len(self.tokens):
            raise self._error("Unexpected tokens after specification")
        return equations

    def _parse_expression(self) -> Expression:
        name = self._expect_identifier()
        if self._peek() != "(":
            return Reference(name)

        self.position += 1
        arguments: list[Expression] = []
        cardinality: Cardinality | None = None
        while self._peek() != ")":
            if self._starts_cardinality():
                if cardinality is not None:
                    raise self._error("A constructor may have only one cardinality constraint")
                cardinality = self._parse_cardinality()
            else:
                arguments.append(self._parse_expression())

            if self._peek() == ",":
                self.position += 1
            elif self._peek() != ")":
                raise self._error("Expected ',' or ')' in constructor")
        self._expect(")")
        return Constructor(name, tuple(arguments), cardinality)

    def _starts_cardinality(self) -> bool:
        token = self._peek()
        if token == "card":
            return True
        return bool(token and token.isdigit() and self._peek(2) == "card")

    def _parse_cardinality(self) -> Cardinality:
        first = self._peek()
        if first == "card":
            self.position += 1
            operator = self._take()
            value = self._expect_number()
            if operator == "=":
                return Cardinality(value, value)
            if operator == "<=":
                return Cardinality(0, value)
            if operator == "<":
                return Cardinality(0, value - 1)
            raise self._error(f"Unsupported cardinality operator {operator!r}")

        value = self._expect_number()
        operator = self._take()
        self._expect("card")
        if operator == "<=":
            return Cardinality(value, None)
        if operator == "<":
            return Cardinality(value + 1, None)
        raise self._error(f"Unsupported cardinality operator {operator!r}")

    def _expect_identifier(self) -> str:
        token = self._take()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?", token):
            raise self._error(f"Expected identifier, found {token!r}")
        return token

    def _expect_number(self) -> int:
        token = self._take()
        if not token.isdigit():
            raise self._error(f"Expected nonnegative integer, found {token!r}")
        return int(token)

    def _expect(self, expected: str) -> None:
        token = self._take()
        if token != expected:
            raise self._error(f"Expected {expected!r}, found {token!r}")

    def _take(self) -> str:
        if self.position >= len(self.tokens):
            raise self._error("Unexpected end of specification")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def _peek(self, offset: int = 0) -> str | None:
        index = self.position + offset
        return self.tokens[index] if index < len(self.tokens) else None

    def _error(self, message: str) -> SpecificationError:
        nearby = " ".join(self.tokens[max(0, self.position - 2) : self.position + 3])
        return SpecificationError(f"{message} near {nearby!r}")


def zero_series(degree: int) -> Series:
    return [Fraction(0) for _ in range(degree + 1)]


def one_series(degree: int) -> Series:
    result = zero_series(degree)
    result[0] = Fraction(1)
    return result


def atom_series(degree: int) -> Series:
    result = zero_series(degree)
    if degree >= 1:
        result[1] = Fraction(1)
    return result


def add_series(*series: Series) -> Series:
    if not series:
        raise SpecificationError("Union requires at least one argument")
    return [sum((value[index] for value in series), Fraction(0)) for index in range(len(series[0]))]


def multiply_series(left: Series, right: Series) -> Series:
    degree = len(left) - 1
    result = zero_series(degree)
    for left_degree, left_coefficient in enumerate(left):
        if not left_coefficient:
            continue
        for right_degree in range(degree - left_degree + 1):
            right_coefficient = right[right_degree]
            if right_coefficient:
                result[left_degree + right_degree] += left_coefficient * right_coefficient
    return result


def product_series(series: Sequence[Series], degree: int) -> Series:
    result = one_series(degree)
    for factor in series:
        result = multiply_series(result, factor)
    return result


def power_series(series: Series, exponent: int) -> Series:
    degree = len(series) - 1
    result = one_series(degree)
    factor = series
    remaining = exponent
    while remaining:
        if remaining & 1:
            result = multiply_series(result, factor)
        remaining //= 2
        if remaining:
            factor = multiply_series(factor, factor)
    return result


def scale_series(series: Series, scalar: Fraction) -> Series:
    return [scalar * coefficient for coefficient in series]


def substitute_power(series: Series, exponent: int) -> Series:
    degree = len(series) - 1
    result = zero_series(degree)
    for index in range(degree // exponent + 1):
        result[index * exponent] = series[index]
    return result


def component_bounds(cardinality: Cardinality | None, degree: int) -> tuple[int, int]:
    constraint = cardinality or Cardinality()
    maximum = degree if constraint.maximum is None else constraint.maximum
    return constraint.minimum, maximum


def sequence_series(component: Series, cardinality: Cardinality | None) -> Series:
    degree = len(component) - 1
    minimum, maximum = component_bounds(cardinality, degree)
    if component[0] and (cardinality is None or cardinality.maximum is None):
        raise UnsupportedConstruction("An unrestricted Sequence cannot contain size-zero objects")

    result = zero_series(degree)
    current = one_series(degree)
    for count in range(maximum + 1):
        if count >= minimum:
            result = add_series(result, current)
        current = multiply_series(current, component)
    return result


def labelled_set_series(component: Series, cardinality: Cardinality | None) -> Series:
    degree = len(component) - 1
    minimum, maximum = component_bounds(cardinality, degree)
    if component[0] and (cardinality is None or cardinality.maximum is None):
        raise UnsupportedConstruction("An unrestricted labelled Set cannot contain size-zero objects")

    result = zero_series(degree)
    current = one_series(degree)
    factorial = 1
    for count in range(maximum + 1):
        if count:
            factorial *= count
        if count >= minimum:
            result = add_series(result, scale_series(current, Fraction(1, factorial)))
        current = multiply_series(current, component)
    return result


def require_nonnegative_integers(component: Series, construction: str) -> list[int]:
    coefficients: list[int] = []
    for coefficient in component:
        if coefficient.denominator != 1 or coefficient < 0:
            raise UnsupportedConstruction(
                f"Unlabelled {construction} requires nonnegative integer component coefficients",
            )
        coefficients.append(coefficient.numerator)
    return coefficients


def unlabelled_selection_series(
    component: Series,
    cardinality: Cardinality | None,
    *,
    distinct: bool,
) -> Series:
    """Evaluate an unlabelled multiset (Set) or distinct selection (PowerSet)."""

    degree = len(component) - 1
    coefficients = require_nonnegative_integers(component, "PowerSet" if distinct else "Set")
    if coefficients[0]:
        if not distinct:
            raise UnsupportedConstruction("An unlabelled Set cannot contain size-zero objects")
        if cardinality is not None:
            raise UnsupportedConstruction("Cardinality constraints on PowerSet are not supported")

    minimum, maximum = component_bounds(cardinality, degree)
    table = [zero_series(degree) for _ in range(maximum + 1)]
    table[0][0] = Fraction(2 ** coefficients[0] if distinct else 1)

    for size, type_count in enumerate(coefficients[1:], 1):
        if not type_count:
            continue
        updated = [zero_series(degree) for _ in range(maximum + 1)]
        for old_count in range(maximum + 1):
            for old_size, old_value in enumerate(table[old_count]):
                if not old_value:
                    continue
                limit = min(maximum - old_count, (degree - old_size) // size)
                if distinct:
                    limit = min(limit, type_count)
                for chosen in range(limit + 1):
                    ways = (
                        math.comb(type_count, chosen)
                        if distinct
                        else math.comb(type_count + chosen - 1, chosen)
                    )
                    updated[old_count + chosen][old_size + chosen * size] += old_value * ways
        table = updated

    result = zero_series(degree)
    for count in range(minimum, maximum + 1):
        result = add_series(result, table[count])
    return result


def euler_totient(value: int) -> int:
    result = value
    factor = 2
    remaining = value
    while factor * factor <= remaining:
        if remaining % factor == 0:
            while remaining % factor == 0:
                remaining //= factor
            result -= result // factor
        factor += 1
    if remaining > 1:
        result -= result // remaining
    return result


def labelled_cycle_series(component: Series, cardinality: Cardinality | None) -> Series:
    degree = len(component) - 1
    minimum, maximum = component_bounds(cardinality or Cardinality(1), degree)
    minimum = max(1, minimum)
    if component[0] and (cardinality is None or cardinality.maximum is None):
        raise UnsupportedConstruction("An unrestricted labelled Cycle cannot contain size-zero objects")

    result = zero_series(degree)
    current = one_series(degree)
    for count in range(1, maximum + 1):
        current = multiply_series(current, component)
        if count >= minimum:
            result = add_series(result, scale_series(current, Fraction(1, count)))
    return result


def unlabelled_cycle_series(component: Series, cardinality: Cardinality | None) -> Series:
    degree = len(component) - 1
    if component[0]:
        raise UnsupportedConstruction("An unlabelled Cycle cannot contain size-zero objects")
    minimum, maximum = component_bounds(cardinality or Cardinality(1), degree)
    minimum = max(1, minimum)
    result = zero_series(degree)

    for count in range(minimum, maximum + 1):
        fixed_count = zero_series(degree)
        for divisor in range(1, count + 1):
            if count % divisor:
                continue
            substituted = substitute_power(component, divisor)
            contribution = power_series(substituted, count // divisor)
            fixed_count = add_series(
                fixed_count,
                scale_series(contribution, Fraction(euler_totient(divisor), count)),
            )
        result = add_series(result, fixed_count)
    return result


class Evaluator:
    def __init__(self, equations: dict[str, Expression], degree: int, labelled: bool):
        self.equations = equations
        self.degree = degree
        self.labelled = labelled

    def compute(self, symbol: str) -> Series:
        if symbol not in self.equations:
            raise SpecificationError(f"Specification does not define {symbol!r}")

        values = {name: zero_series(self.degree) for name in self.equations}
        iteration_limit = max(100, (self.degree + 1) * max(1, len(values)) * 4)
        for _ in range(iteration_limit):
            updated = {
                name: self._evaluate(expression, values)
                for name, expression in self.equations.items()
            }
            if updated == values:
                return updated[symbol]
            values = updated
        raise UnsupportedConstruction(
            f"The recursive system did not stabilize through degree {self.degree}; "
            "it may not be well founded",
        )

    def _evaluate(self, expression: Expression, values: dict[str, Series]) -> Series:
        if isinstance(expression, Reference):
            if expression.name in ("Atom", "Z") and expression.name not in self.equations:
                return atom_series(self.degree)
            if expression.name == "Epsilon":
                return one_series(self.degree)
            if expression.name not in values:
                raise SpecificationError(f"Undefined symbol {expression.name!r}")
            return values[expression.name]

        arguments = [self._evaluate(argument, values) for argument in expression.arguments]
        name = expression.name.lower()
        if name == "union":
            if expression.cardinality is not None:
                raise SpecificationError("Union does not accept a cardinality constraint")
            return add_series(*arguments)
        if name == "prod":
            if expression.cardinality is not None:
                raise SpecificationError("Prod does not accept a cardinality constraint")
            return product_series(arguments, self.degree)
        if len(arguments) != 1:
            raise SpecificationError(f"{expression.name} requires exactly one component argument")

        component = arguments[0]
        if name == "sequence":
            return sequence_series(component, expression.cardinality)
        if name == "set":
            if self.labelled:
                return labelled_set_series(component, expression.cardinality)
            return unlabelled_selection_series(
                component,
                expression.cardinality,
                distinct=False,
            )
        if name == "cycle":
            if self.labelled:
                return labelled_cycle_series(component, expression.cardinality)
            return unlabelled_cycle_series(component, expression.cardinality)
        if name == "powerset":
            if self.labelled:
                raise UnsupportedConstruction("PowerSet is only defined for unlabelled structures")
            if expression.cardinality is not None:
                raise UnsupportedConstruction("PowerSet cardinality constraints are not supported")
            return unlabelled_selection_series(component, None, distinct=True)
        raise UnsupportedConstruction(f"Unsupported constructor {expression.name!r}")


class CoefficientNode:
    def __init__(self, compiler: "CoefficientCompiler"):
        self.compiler = compiler
        self.coefficients: list[int | Fraction] = [0 for _ in range(compiler.degree + 1)]
        compiler.nodes.append(self)

    def value(self, degree: int) -> Fraction:
        raise NotImplementedError

    def update(self, degree: int) -> bool:
        value = compact_number(self.value(degree))
        if value == self.coefficients[degree]:
            return False
        self.coefficients[degree] = value
        return True


def compact_number(value: int | Fraction) -> int | Fraction:
    if isinstance(value, Fraction) and value.denominator == 1:
        return value.numerator
    return value


def divide_exact(value: int | Fraction, divisor: int) -> int | Fraction:
    if isinstance(value, int):
        quotient, remainder = divmod(value, divisor)
        return quotient if remainder == 0 else Fraction(value, divisor)
    return compact_number(value / divisor)


def is_nonnegative_integer(value: int | Fraction) -> bool:
    return value >= 0 and (isinstance(value, int) or value.denominator == 1)


def integer_value(value: int | Fraction) -> int:
    return value if isinstance(value, int) else value.numerator


@lru_cache(maxsize=None)
def binomial_row(degree: int) -> tuple[int, ...]:
    row = [1]
    for index in range(1, degree + 1):
        row.append(row[-1] * (degree - index + 1) // index)
    return tuple(row)


def decimal_digit_count(value: int) -> int:
    value = abs(value)
    if value == 0:
        return 1
    digits = int((value.bit_length() - 1) * math.log10(2)) + 1
    if value >= 10**digits:
        return digits + 1
    if value < 10 ** (digits - 1):
        return digits - 1
    return digits


class LiteralNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", nonzero_degree: int | None):
        self.nonzero_degree = nonzero_degree
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        return int(degree == self.nonzero_degree)


class ReferenceNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", name: str):
        self.name = name
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        try:
            return self.compiler.roots[self.name].coefficients[degree]
        except KeyError as error:
            raise SpecificationError(f"Undefined symbol {self.name!r}") from error


class SumNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", children: Sequence[CoefficientNode]):
        self.children = tuple(children)
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        return sum(child.coefficients[degree] for child in self.children)


class ProductNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", left: CoefficientNode, right: CoefficientNode):
        self.left = left
        self.right = right
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        weights = binomial_row(degree) if self.compiler.labelled else None
        return sum(
            (
                (weights[index] if weights else 1)
                * self.left.coefficients[index]
                * self.right.coefficients[degree - index]
                for index in range(degree + 1)
            ),
            0,
        )


class ScaleNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", child: CoefficientNode, scalar: Fraction):
        self.child = child
        self.scalar = scalar
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        return self.scalar * self.child.coefficients[degree]


class SubstituteNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", child: CoefficientNode, exponent: int):
        self.child = child
        self.exponent = exponent
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        if degree % self.exponent:
            return 0
        return self.child.coefficients[degree // self.exponent]


class InverseOneMinusNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", child: CoefficientNode):
        self.child = child
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        if self.child.coefficients[0]:
            raise UnsupportedConstruction("An unrestricted Sequence cannot contain size-zero objects")
        if degree == 0:
            return 1
        weights = binomial_row(degree) if self.compiler.labelled else None
        return sum(
            (
                (weights[index] if weights else 1)
                * self.child.coefficients[index]
                * self.coefficients[degree - index]
                for index in range(1, degree + 1)
            ),
            0,
        )


class ExpNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", child: CoefficientNode):
        self.child = child
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        if self.child.coefficients[0]:
            raise UnsupportedConstruction("An exponential construction cannot contain size-zero objects")
        if degree == 0:
            return 1
        if self.compiler.labelled:
            weights = binomial_row(degree - 1)
            return sum(
                (
                    weights[index - 1]
                    * self.child.coefficients[index]
                    * self.coefficients[degree - index]
                    for index in range(1, degree + 1)
                ),
                0,
            )
        total = sum(
            (
                index
                * self.child.coefficients[index]
                * self.coefficients[degree - index]
                for index in range(1, degree + 1)
            ),
            0,
        )
        return divide_exact(total, degree)


class LogOneMinusNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", child: CoefficientNode):
        self.child = child
        self.inverse = InverseOneMinusNode(compiler, child)
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        if degree == 0:
            return 0
        if self.compiler.labelled:
            weights = binomial_row(degree - 1)
            return sum(
                (
                    weights[index - 1]
                    * self.child.coefficients[index]
                    * self.inverse.coefficients[degree - index]
                    for index in range(1, degree + 1)
                ),
                0,
            )
        total = sum(
            (
                index
                * self.child.coefficients[index]
                * self.inverse.coefficients[degree - index]
                for index in range(1, degree + 1)
            ),
            0,
        )
        return divide_exact(total, degree)


def divisors(value: int) -> list[int]:
    small: list[int] = []
    large: list[int] = []
    candidate = 1
    while candidate * candidate <= value:
        if value % candidate == 0:
            small.append(candidate)
            if candidate * candidate != value:
                large.append(value // candidate)
        candidate += 1
    return small + list(reversed(large))


class EulerSelectionNode(CoefficientNode):
    """Unrestricted unlabelled Set or PowerSet via its logarithm."""

    def __init__(self, compiler: "CoefficientCompiler", child: CoefficientNode, distinct: bool):
        self.child = child
        self.distinct = distinct
        self.log_coefficients: list[int | Fraction] = [0 for _ in range(compiler.degree + 1)]
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        constant = self.child.coefficients[0]
        if not is_nonnegative_integer(constant):
            raise UnsupportedConstruction("Unlabelled selections require nonnegative integer coefficients")
        if constant and not self.distinct:
            raise UnsupportedConstruction("An unlabelled Set cannot contain size-zero objects")
        if degree == 0:
            return 2 ** integer_value(constant) if self.distinct else 1

        logarithm: int | Fraction = 0
        for divisor in divisors(degree):
            coefficient = self.child.coefficients[degree // divisor]
            if not is_nonnegative_integer(coefficient):
                raise UnsupportedConstruction(
                    "Unlabelled selections require nonnegative integer component coefficients",
                )
            sign = -1 if self.distinct and divisor % 2 == 0 else 1
            logarithm += sign * Fraction(integer_value(coefficient), divisor)
        self.log_coefficients[degree] = compact_number(logarithm)
        total = sum(
            (
                index * self.log_coefficients[index] * self.coefficients[degree - index]
                for index in range(1, degree + 1)
            ),
            0,
        )
        return divide_exact(total, degree)


class UnlabelledCycleNode(CoefficientNode):
    def __init__(self, compiler: "CoefficientCompiler", child: CoefficientNode):
        self.logarithm = LogOneMinusNode(compiler, child)
        super().__init__(compiler)

    def value(self, degree: int) -> Fraction:
        if degree == 0:
            return Fraction(0)
        return sum(
            (
                Fraction(euler_totient(divisor), divisor)
                * self.logarithm.coefficients[degree // divisor]
                for divisor in divisors(degree)
            ),
            Fraction(0),
        )


class CoefficientCompiler:
    def __init__(self, equations: dict[str, Expression], degree: int, labelled: bool):
        self.equations = equations
        self.degree = degree
        self.labelled = labelled
        self.nodes: list[CoefficientNode] = []
        self.roots: dict[str, CoefficientNode] = {}
        self._powers: dict[tuple[int, int], CoefficientNode] = {}
        self._fixed_msets: dict[tuple[int, int], CoefficientNode] = {}
        self.zero = LiteralNode(self, None)
        self.one = LiteralNode(self, 0)
        self.atom = LiteralNode(self, 1)

    def compute(self, symbol: str, max_digits: int | None = None) -> Series:
        if symbol not in self.equations:
            raise SpecificationError(f"Specification does not define {symbol!r}")
        equation_order, recursive = self.equation_order()
        for name in equation_order:
            self.roots[name] = self.compile(self.equations[name])

        for degree in range(self.degree + 1):
            if not recursive:
                for node in self.nodes:
                    node.update(degree)
            else:
                iteration_limit = max(100, len(self.nodes) * 4)
                for _ in range(iteration_limit):
                    changed = False
                    for node in self.nodes:
                        changed = node.update(degree) or changed
                    if not changed:
                        break
                else:
                    raise UnsupportedConstruction(
                        f"The recursive system did not stabilize at degree {degree}; "
                        "it may not be well founded",
                    )

            if max_digits is not None:
                value = self.roots[symbol].coefficients[degree]
                if isinstance(value, Fraction) and value.denominator != 1:
                    raise UnsupportedConstruction(
                        f"Coefficient of size {degree} does not yield an integer count: {value}",
                    )
                if decimal_digit_count(integer_value(value)) > max_digits:
                    return self.roots[symbol].coefficients[:degree]
        return self.roots[symbol].coefficients

    def equation_order(self) -> tuple[list[str], bool]:
        dependencies = {
            name: self.expression_references(expression) & self.equations.keys()
            for name, expression in self.equations.items()
        }
        order: list[str] = []
        temporary: set[str] = set()
        permanent: set[str] = set()
        recursive = False

        def visit(name: str) -> None:
            nonlocal recursive
            if name in permanent:
                return
            if name in temporary:
                recursive = True
                return
            temporary.add(name)
            for dependency in dependencies[name]:
                visit(dependency)
            temporary.remove(name)
            permanent.add(name)
            order.append(name)

        for name in self.equations:
            visit(name)
        return order, recursive

    @classmethod
    def expression_references(cls, expression: Expression) -> set[str]:
        if isinstance(expression, Reference):
            return {expression.name}
        references: set[str] = set()
        for argument in expression.arguments:
            references.update(cls.expression_references(argument))
        return references

    def compile(self, expression: Expression) -> CoefficientNode:
        if isinstance(expression, Reference):
            if expression.name == "Epsilon":
                return self.one
            if expression.name in ("Atom", "Z") and expression.name not in self.equations:
                return self.atom
            return ReferenceNode(self, expression.name)

        children = [self.compile(argument) for argument in expression.arguments]
        name = expression.name.lower()
        if name == "union":
            if expression.cardinality is not None:
                raise SpecificationError("Union does not accept a cardinality constraint")
            return self.sum(children)
        if name == "prod":
            if expression.cardinality is not None:
                raise SpecificationError("Prod does not accept a cardinality constraint")
            return self.product(children)
        if len(children) != 1:
            raise SpecificationError(f"{expression.name} requires exactly one component argument")

        child = children[0]
        if name == "sequence":
            return self.sequence(child, expression.cardinality)
        if name == "set":
            return self.labelled_set(child, expression.cardinality) if self.labelled else self.mset(
                child,
                expression.cardinality,
            )
        if name == "cycle":
            return self.cycle(child, expression.cardinality)
        if name == "powerset":
            if self.labelled:
                raise UnsupportedConstruction("PowerSet is only defined for unlabelled structures")
            if expression.cardinality is not None:
                raise UnsupportedConstruction("PowerSet cardinality constraints are not supported")
            return EulerSelectionNode(self, child, distinct=True)
        raise UnsupportedConstruction(f"Unsupported constructor {expression.name!r}")

    def sum(self, children: Sequence[CoefficientNode]) -> CoefficientNode:
        if not children:
            return self.zero
        if len(children) == 1:
            return children[0]
        return SumNode(self, children)

    def product(self, children: Sequence[CoefficientNode]) -> CoefficientNode:
        if not children:
            return self.one
        result = children[0]
        for child in children[1:]:
            result = ProductNode(self, result, child)
        return result

    def scale(self, child: CoefficientNode, scalar: Fraction) -> CoefficientNode:
        return child if scalar == 1 else ScaleNode(self, child, scalar)

    def power(self, child: CoefficientNode, exponent: int) -> CoefficientNode:
        key = (id(child), exponent)
        if key in self._powers:
            return self._powers[key]
        if exponent == 0:
            result = self.one
        else:
            result = self.one
            for _ in range(exponent):
                result = ProductNode(self, result, child)
        self._powers[key] = result
        return result

    @staticmethod
    def bounds(cardinality: Cardinality | None, default_minimum: int = 0) -> tuple[int, int | None]:
        if cardinality is None:
            return default_minimum, None
        return max(default_minimum, cardinality.minimum), cardinality.maximum

    def sequence(self, child: CoefficientNode, cardinality: Cardinality | None) -> CoefficientNode:
        minimum, maximum = self.bounds(cardinality)
        if maximum is not None:
            return self.sum([self.power(child, count) for count in range(minimum, maximum + 1)])
        inverse = InverseOneMinusNode(self, child)
        return self.product([self.power(child, minimum), inverse])

    def labelled_set(self, child: CoefficientNode, cardinality: Cardinality | None) -> CoefficientNode:
        minimum, maximum = self.bounds(cardinality)
        if maximum is not None:
            return self.sum(
                [
                    self.scale(self.power(child, count), Fraction(1, math.factorial(count)))
                    for count in range(minimum, maximum + 1)
                ],
            )
        unrestricted = ExpNode(self, child)
        excluded = self.sum(
            [
                self.scale(self.power(child, count), Fraction(1, math.factorial(count)))
                for count in range(minimum)
            ],
        )
        return self.sum([unrestricted, self.scale(excluded, Fraction(-1))])

    def fixed_mset(self, child: CoefficientNode, count: int) -> CoefficientNode:
        key = (id(child), count)
        if key in self._fixed_msets:
            return self._fixed_msets[key]
        if count == 0:
            result = self.one
        else:
            terms = []
            for part in range(1, count + 1):
                substituted = SubstituteNode(self, child, part)
                terms.append(ProductNode(self, substituted, self.fixed_mset(child, count - part)))
            result = self.scale(self.sum(terms), Fraction(1, count))
        self._fixed_msets[key] = result
        return result

    def mset(self, child: CoefficientNode, cardinality: Cardinality | None) -> CoefficientNode:
        minimum, maximum = self.bounds(cardinality)
        if maximum is not None:
            return self.sum([self.fixed_mset(child, count) for count in range(minimum, maximum + 1)])
        unrestricted = EulerSelectionNode(self, child, distinct=False)
        excluded = self.sum([self.fixed_mset(child, count) for count in range(minimum)])
        return self.sum([unrestricted, self.scale(excluded, Fraction(-1))])

    def fixed_cycle(self, child: CoefficientNode, count: int) -> CoefficientNode:
        if self.labelled:
            return self.scale(self.power(child, count), Fraction(1, count))
        terms = []
        for divisor in divisors(count):
            substituted = SubstituteNode(self, child, divisor)
            term = self.power(substituted, count // divisor)
            terms.append(self.scale(term, Fraction(euler_totient(divisor), count)))
        return self.sum(terms)

    def cycle(self, child: CoefficientNode, cardinality: Cardinality | None) -> CoefficientNode:
        minimum, maximum = self.bounds(cardinality, default_minimum=1)
        if maximum is not None:
            return self.sum([self.fixed_cycle(child, count) for count in range(minimum, maximum + 1)])
        unrestricted = LogOneMinusNode(self, child) if self.labelled else UnlabelledCycleNode(self, child)
        excluded = self.sum([self.fixed_cycle(child, count) for count in range(1, minimum)])
        return self.sum([unrestricted, self.scale(excluded, Fraction(-1))])


def compute_terms(
    specification: str,
    *,
    labelled: bool,
    term_count: int,
    symbol: str = "S",
    max_digits: int | None = None,
) -> list[int]:
    """Return counts a(0) through a(term_count - 1) for a specification."""

    if term_count <= 0:
        raise ValueError("term_count must be positive")
    equations = Parser(specification).parse()
    coefficients = CoefficientCompiler(equations, term_count - 1, labelled).compute(
        symbol,
        max_digits=max_digits,
    )

    terms: list[int] = []
    for degree, coefficient in enumerate(coefficients):
        count = coefficient
        if isinstance(count, Fraction) and count.denominator != 1:
            raise UnsupportedConstruction(
                f"Coefficient of size {degree} does not yield an integer count: {count}",
            )
        terms.append(integer_value(count))
    return terms


def load_record(dataset: Path, structure_id: int) -> dict:
    with dataset.open(encoding="utf-8") as source:
        records = json.load(source)
    try:
        return records[str(structure_id)]
    except KeyError as error:
        raise SpecificationError(f"No ECS structure #{structure_id} in {dataset}") from error


def default_dataset() -> Path:
    return Path(__file__).resolve().parents[1] / "react-app" / "public" / "ecs.json"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--id", type=int, help="ECS structure number to load from the dataset")
    source.add_argument("--spec", help="Specification text, for example '{S = Sequence(Z)}'")
    parser.add_argument("--dataset", type=Path, default=default_dataset())
    parser.add_argument("--terms", type=int, default=20, help="number of terms, beginning with a(0)")
    parser.add_argument("--symbol", default="S", help="root symbol to enumerate (default: S)")
    parser.add_argument("--max-digits", type=int, help="stop before a term exceeds this many digits")
    universe = parser.add_mutually_exclusive_group()
    universe.add_argument("--labelled", action="store_true", help="use labelled/EGF semantics")
    universe.add_argument("--unlabelled", action="store_true", help="use unlabelled/OGF semantics")
    parser.add_argument("--plain", action="store_true", help="print comma-separated integers instead of JSON")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)

    record = None
    if arguments.id is not None:
        record = load_record(arguments.dataset, arguments.id)
        specification = record["specification"]
        labelled = bool(record["labeled"])
        symbol = record.get("symbol") or arguments.symbol
    else:
        if not arguments.labelled and not arguments.unlabelled:
            parser.error("--spec requires either --labelled or --unlabelled")
        specification = arguments.spec
        labelled = arguments.labelled
        symbol = arguments.symbol

    try:
        terms = compute_terms(
            specification,
            labelled=labelled,
            term_count=arguments.terms,
            symbol=symbol,
            max_digits=arguments.max_digits,
        )
    except (SpecificationError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")

    if arguments.plain:
        print(", ".join(map(str, terms)))
        return 0

    output = {
        "id": arguments.id,
        "symbol": symbol,
        "labelled": labelled,
        "terms": [str(term) for term in terms],
    }
    if record is not None:
        stored = [str(term) for term in record.get("terms", [])]
        overlap = min(len(stored), len(terms))
        output["matches_stored_prefix"] = stored[:overlap] == output["terms"][:overlap]
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
