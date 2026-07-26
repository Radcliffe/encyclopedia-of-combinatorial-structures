"""Attribute grammars and exact multivariate series.

Maple attribute specifications mirror a combinatorial specification while
replacing each structural component by an additive attribute value.  This
module parses that syntax and evaluates the resulting attributes on the exact
objects produced by :mod:`combstruct.enumeration`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import cast

from .derivation import (
    UnsupportedGeneratingFunctionDerivation,
    _divide,
    _GeneratingFunctionDeriver,
    _integer,
    _power,
    _product,
    _scale,
    _subtract,
    _sum,
)
from .enumeration import (
    CombinatorialObject,
    ConstructionObject,
    allstructs,
)
from .generating_function import (
    GFBinary,
    GFEquation,
    GFExpression,
    GFFunction,
    GFIndex,
    GFInfiniteSum,
    GFInteger,
    GFMultivariateSeriesCall,
    GFTotient,
    GFUnary,
    GFVariable,
)
from .specification import (
    Expression,
    Reference,
    SpecificationError,
    parse_specification,
    resolve_labelled,
)


class AttributeSpecificationError(SpecificationError):
    """An attribute grammar is malformed or incompatible with its grammar."""


@dataclass(frozen=True)
class AttributeInteger:
    """An integer constant in an attribute rule."""

    value: int


@dataclass(frozen=True)
class AttributeSymbol:
    """An atomic symbolic constant or coefficient in an attribute rule."""

    name: str


@dataclass(frozen=True)
class AttributeCall:
    """The value of one attribute on a named substructure."""

    attribute: str
    symbol: str


@dataclass(frozen=True)
class SizeCall:
    """The predefined size attribute on a named substructure."""

    symbol: str


@dataclass(frozen=True)
class AttributeBinary:
    """Addition, subtraction, or multiplication in an attribute rule."""

    operator: str
    left: AttributeExpression
    right: AttributeExpression


@dataclass(frozen=True)
class AttributeConstructor:
    """An attribute rule mirroring one combinatorial constructor."""

    name: str
    arguments: tuple[AttributeExpression, ...]


type AttributeExpression = (
    AttributeInteger
    | AttributeSymbol
    | AttributeCall
    | SizeCall
    | AttributeBinary
    | AttributeConstructor
)
type AttributeSpecification = dict[tuple[str, str], AttributeExpression]


@dataclass(frozen=True)
class AttributeSeries:
    """A finite exact multivariate OGF or EGF expansion.

    Exponent tuples follow ``variables`` and always put the size variable
    first.  Labeled coefficients are divided by ``size!``.
    """

    variables: tuple[str, ...]
    coefficients: Mapping[tuple[int, ...], Fraction]
    labeled: bool

    def coefficient(self, size: int, /, **attribute_values: int) -> Fraction:
        """Return one coefficient, using zero for no absent monomial."""

        expected = set(self.variables[1:])
        if set(attribute_values) != expected:
            raise ValueError(
                f"attribute values must name exactly {sorted(expected)!r}",
            )
        exponent = (size, *(attribute_values[name] for name in self.variables[1:]))
        return self.coefficients.get(exponent, Fraction())


@dataclass(frozen=True)
class AttributeEquationSystem:
    """Symbolic multivariate equations plus their source attribute grammar."""

    equations: tuple[GFEquation, ...]
    variables: tuple[str, ...]
    labeled: bool
    structure_specification: Mapping[str, Expression]
    attribute_specification: Mapping[tuple[str, str], AttributeExpression]
    attributes: Mapping[str, str]
    parameters: tuple[str, ...]


@dataclass(frozen=True)
class AttributeMomentSystem:
    """Truncated factorial-moment series derived from attribute equations."""

    variables: tuple[str, ...]
    term_count: int
    labeled: bool
    moments: Mapping[tuple[str, tuple[int, ...]], tuple[Fraction, ...]]

    def series(self, symbol: str, /, *orders: int) -> tuple[Fraction, ...]:
        """Return the size series for one mixed factorial moment."""

        key = (symbol, orders)
        if key not in self.moments:
            raise KeyError(f"No moment series for {symbol!r} and orders {orders!r}")
        return self.moments[key]


_ATTRIBUTE_TOKEN_RE = re.compile(
    r"\s*([A-Za-z_][A-Za-z0-9_]*|\d+|[{}(),=+*^-])",
)
_ATTRIBUTE_CONSTRUCTORS = {
    "union",
    "prod",
    "set",
    "powerset",
    "sequence",
    "cycle",
}


class AttributeParser:
    """Parse Maple-style attribute grammar equations."""

    def __init__(self, specification: str):
        self.source = specification
        self.tokens = self._tokenize(specification)
        self.position = 0

    @staticmethod
    def _tokenize(specification: str) -> list[str]:
        tokens: list[str] = []
        position = 0
        while position < len(specification):
            match = _ATTRIBUTE_TOKEN_RE.match(specification, position)
            if not match:
                if specification[position:].strip() == "":
                    break
                excerpt = specification[position : position + 20]
                raise AttributeSpecificationError(f"Unexpected input near {excerpt!r}")
            tokens.append(match.group(1))
            position = match.end()
        return tokens

    def parse(self) -> AttributeSpecification:
        """Return equations keyed by ``(attribute, structure symbol)``."""

        self._expect("{")
        equations: AttributeSpecification = {}
        while self._peek() != "}":
            attribute = self._expect_identifier()
            if attribute == "size":
                raise AttributeSpecificationError(
                    "The predefined size attribute cannot be redefined"
                )
            self._expect("(")
            symbol = self._expect_identifier()
            self._expect(")")
            self._expect("=")
            key = (attribute, symbol)
            if key in equations:
                raise AttributeSpecificationError(
                    f"Duplicate attribute equation {attribute}({symbol})",
                )
            equations[key] = self._parse_sum()
            if self._peek() == ",":
                self.position += 1
            elif self._peek() != "}":
                raise self._error("Expected ',' or '}' after attribute equation")
        self._expect("}")
        if self.position != len(self.tokens):
            raise self._error("Unexpected tokens after attribute specification")
        return equations

    def _parse_sum(self) -> AttributeExpression:
        expression = self._parse_product()
        while self._peek() in {"+", "-"}:
            operator = self._take()
            expression = AttributeBinary(operator, expression, self._parse_product())
        return expression

    def _parse_product(self) -> AttributeExpression:
        expression = self._parse_primary()
        while self._peek() == "*":
            self.position += 1
            expression = AttributeBinary("*", expression, self._parse_primary())
        if self._peek() == "^":
            raise self._error("Attribute values must be linear; exponentiation is unsupported")
        return expression

    def _parse_primary(self) -> AttributeExpression:
        token = self._take()
        if token == "-":
            operand = self._parse_primary()
            if isinstance(operand, AttributeInteger):
                return AttributeInteger(-operand.value)
            return AttributeBinary("*", AttributeInteger(-1), operand)
        if token == "(":
            expression = self._parse_sum()
            self._expect(")")
            return expression
        if token.isdigit():
            return AttributeInteger(int(token))
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            raise self._error(f"Expected an attribute value, found {token!r}")
        name = token
        if self._peek() != "(":
            return AttributeSymbol(name)
        self._expect("(")
        if name.lower() in _ATTRIBUTE_CONSTRUCTORS:
            arguments: list[AttributeExpression] = []
            while self._peek() != ")":
                arguments.append(self._parse_sum())
                if self._peek() == ",":
                    self.position += 1
                elif self._peek() != ")":
                    raise self._error("Expected ',' or ')' in attribute constructor")
            self._expect(")")
            return AttributeConstructor(name, tuple(arguments))
        symbol = self._expect_identifier()
        self._expect(")")
        return SizeCall(symbol) if name == "size" else AttributeCall(name, symbol)

    def _expect_identifier(self) -> str:
        token = self._take()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            raise self._error(f"Expected identifier, found {token!r}")
        return token

    def _expect(self, expected: str) -> None:
        token = self._take()
        if token != expected:
            raise self._error(f"Expected {expected!r}, found {token!r}")

    def _take(self) -> str:
        if self.position >= len(self.tokens):
            raise self._error("Unexpected end of attribute specification")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def _peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _error(self, message: str) -> AttributeSpecificationError:
        nearby = " ".join(self.tokens[max(0, self.position - 2) : self.position + 3])
        return AttributeSpecificationError(f"{message} near {nearby!r}")


def parse_attribute_specification(specification: str) -> AttributeSpecification:
    """Parse a Maple-style attribute grammar."""

    if not isinstance(specification, str):
        raise TypeError("attribute specification must be text")
    return AttributeParser(specification).parse()


def _attribute_equations(
    specification: str | Mapping[tuple[str, str], AttributeExpression],
) -> AttributeSpecification:
    if isinstance(specification, str):
        return parse_attribute_specification(specification)
    if not isinstance(specification, Mapping):
        raise TypeError("attribute specification must be text or an equation mapping")
    result = dict(specification)
    if not all(
        isinstance(key, tuple)
        and len(key) == 2
        and all(isinstance(part, str) and part for part in key)
        for key in result
    ):
        raise TypeError("attribute equation keys must be (attribute, symbol) string pairs")
    return result


def _structure_equations(
    specification: str | Mapping[str, Expression],
) -> dict[str, Expression]:
    if isinstance(specification, str):
        return parse_specification(specification)
    if not isinstance(specification, Mapping):
        raise TypeError("specification must be text or a mapping of equations")
    return dict(specification)


def _contains_attribute_value(expression: AttributeExpression) -> bool:
    if isinstance(expression, AttributeCall | SizeCall):
        return True
    if isinstance(expression, AttributeBinary):
        return _contains_attribute_value(expression.left) or _contains_attribute_value(
            expression.right,
        )
    if isinstance(expression, AttributeConstructor):
        return any(_contains_attribute_value(argument) for argument in expression.arguments)
    return False


def _validate_linearity(expression: AttributeExpression) -> None:
    if isinstance(expression, AttributeBinary):
        _validate_linearity(expression.left)
        _validate_linearity(expression.right)
        if (
            expression.operator == "*"
            and _contains_attribute_value(expression.left)
            and _contains_attribute_value(expression.right)
        ):
            raise AttributeSpecificationError(
                "Attribute values must be linear in substructure attributes and size",
            )
    elif isinstance(expression, AttributeConstructor):
        for argument in expression.arguments:
            _validate_linearity(argument)


def _walk_calls(expression: AttributeExpression) -> tuple[AttributeCall | SizeCall, ...]:
    if isinstance(expression, AttributeCall | SizeCall):
        return (expression,)
    if isinstance(expression, AttributeBinary):
        return _walk_calls(expression.left) + _walk_calls(expression.right)
    if isinstance(expression, AttributeConstructor):
        return tuple(call for argument in expression.arguments for call in _walk_calls(argument))
    return ()


def _walk_symbols(expression: AttributeExpression) -> tuple[str, ...]:
    if isinstance(expression, AttributeSymbol):
        return (expression.name,)
    if isinstance(expression, AttributeBinary):
        return _walk_symbols(expression.left) + _walk_symbols(expression.right)
    if isinstance(expression, AttributeConstructor):
        return tuple(
            symbol for argument in expression.arguments for symbol in _walk_symbols(argument)
        )
    return ()


def _validate_attribute_grammar(
    equations: Mapping[str, Expression],
    attributes: Mapping[tuple[str, str], AttributeExpression],
    requested: Mapping[str, str],
) -> None:
    if not requested:
        raise ValueError("at least one attribute marker is required")
    if any(not isinstance(variable, str) or not variable for variable in requested):
        raise TypeError("attribute variable names must be nonempty strings")
    if any(variable in {"x", "_x", "_Z"} for variable in requested):
        raise ValueError("attribute variables must differ from the size variable")
    if any(not isinstance(attribute, str) or not attribute for attribute in requested.values()):
        raise TypeError("attribute names must be nonempty strings")
    if len(set(requested.values())) != len(requested):
        raise ValueError("each attribute must be marked by one unique variable")

    requested_names = set(requested.values())
    parameter_names = {
        parameter for expression in attributes.values() for parameter in _walk_symbols(expression)
    }
    conflicts = parameter_names & (set(requested) | {"x", "_x", "_Z"})
    if conflicts:
        raise AttributeSpecificationError(
            f"Atomic parameters conflict with generating variables: {sorted(conflicts)!r}",
        )
    for (attribute, symbol), expression in attributes.items():
        if attribute not in requested_names:
            raise AttributeSpecificationError(
                f"Attribute {attribute!r} has no marker variable",
            )
        if symbol not in equations:
            raise AttributeSpecificationError(f"Undefined structure symbol {symbol!r}")
        _validate_linearity(expression)
        for call in _walk_calls(expression):
            if call.symbol not in equations:
                raise AttributeSpecificationError(
                    f"Undefined structure symbol {call.symbol!r} in attribute rule",
                )
            if isinstance(call, AttributeCall) and call.attribute not in requested_names:
                raise AttributeSpecificationError(
                    f"Attribute {call.attribute!r} has no marker variable",
                )
        _validate_rule_shape(
            equations[symbol],
            expression,
            current_symbol=symbol,
        )
    _validate_outer_dependency_graphs(equations, attributes, requested_names)


def _validate_parameters(
    attributes: Mapping[tuple[str, str], AttributeExpression],
    parameters: Mapping[str, int] | None,
) -> dict[str, int]:
    if parameters is None:
        supplied: dict[str, int] = {}
    elif not isinstance(parameters, Mapping):
        raise TypeError("parameters must map atomic names to integer values")
    else:
        supplied = dict(parameters)
    if any(not isinstance(name, str) or not name for name in supplied):
        raise TypeError("parameter names must be nonempty strings")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in supplied.values()):
        raise TypeError("parameter values must be integers")

    required = {
        parameter for expression in attributes.values() for parameter in _walk_symbols(expression)
    }
    missing = required - set(supplied)
    extra = set(supplied) - required
    if missing:
        raise AttributeSpecificationError(
            f"Missing values for atomic parameters: {sorted(missing)!r}",
        )
    if extra:
        raise AttributeSpecificationError(
            f"Unknown atomic parameters: {sorted(extra)!r}",
        )
    return supplied


def _default_attribute_expression(
    expression: Expression,
    attribute: str,
) -> AttributeExpression:
    if isinstance(expression, Reference):
        if expression.name in {"Atom", "Z", "Epsilon"}:
            return AttributeInteger(0)
        return AttributeCall(attribute, expression.name)
    return AttributeConstructor(
        expression.name,
        tuple(
            _default_attribute_expression(argument, attribute) for argument in expression.arguments
        ),
    )


def _affine_value(
    expression: AttributeExpression,
    *,
    symbol: str,
) -> tuple[GFExpression, GFExpression, dict[str, GFExpression]]:
    """Return ``constant, size coefficient, attribute coefficients``."""

    if isinstance(expression, AttributeInteger):
        return _integer(expression.value), GFInteger(0), {}
    if isinstance(expression, AttributeSymbol):
        return GFVariable(expression.name), GFInteger(0), {}
    if isinstance(expression, SizeCall):
        if expression.symbol != symbol:
            raise AttributeSpecificationError(
                f"size({expression.symbol}) does not describe component {symbol}",
            )
        return GFInteger(0), GFInteger(1), {}
    if isinstance(expression, AttributeCall):
        if expression.symbol != symbol:
            raise AttributeSpecificationError(
                f"{expression.attribute}({expression.symbol}) does not describe component {symbol}",
            )
        return GFInteger(0), GFInteger(0), {expression.attribute: GFInteger(1)}
    if isinstance(expression, AttributeConstructor):
        raise AttributeSpecificationError(
            f"Unexpected {expression.name} inside a scalar attribute value",
        )
    if expression.operator in {"+", "-"}:
        left = _affine_value(expression.left, symbol=symbol)
        right = _affine_value(expression.right, symbol=symbol)
        sign = GFInteger(1) if expression.operator == "+" else _integer(-1)
        coefficients = dict(left[2])
        for name, value in right[2].items():
            coefficients[name] = _sum(
                (
                    coefficients.get(name, GFInteger(0)),
                    _product((sign, value)),
                ),
            )
        return (
            _sum((left[0], _product((sign, right[0])))),
            _sum((left[1], _product((sign, right[1])))),
            coefficients,
        )

    left = _affine_value(expression.left, symbol=symbol)
    right = _affine_value(expression.right, symbol=symbol)
    left_has_value = not _gf_is_zero(left[1]) or any(
        not _gf_is_zero(value) for value in left[2].values()
    )
    right_has_value = not _gf_is_zero(right[1]) or any(
        not _gf_is_zero(value) for value in right[2].values()
    )
    if left_has_value and right_has_value:
        raise AttributeSpecificationError(
            "Attribute values must be linear in substructure attributes and size",
        )
    scalar = right[0] if left_has_value else left[0]
    affine_result = left if left_has_value else right
    return (
        _product((scalar, affine_result[0])),
        _product((scalar, affine_result[1])),
        {name: _product((scalar, coefficient)) for name, coefficient in affine_result[2].items()},
    )


def _gf_is_zero(expression: GFExpression) -> bool:
    return isinstance(expression, GFInteger) and expression.value == 0


def _attribute_power(
    base: GFExpression,
    exponent: GFExpression,
) -> GFExpression:
    if isinstance(exponent, GFInteger):
        return _power(base, exponent.value)
    return _power(base, exponent)


def _constructor_and_adjustment(
    expression: AttributeExpression,
    *,
    constructor: str,
    symbol: str,
) -> tuple[
    AttributeConstructor,
    GFExpression,
    GFExpression,
    dict[str, GFExpression],
]:
    terms: list[tuple[int, AttributeExpression]] = []

    def collect(value: AttributeExpression, sign: int = 1) -> None:
        if isinstance(value, AttributeBinary) and value.operator in {"+", "-"}:
            collect(value.left, sign)
            collect(value.right, sign if value.operator == "+" else -sign)
        else:
            terms.append((sign, value))

    collect(expression)
    constructors = [
        (sign, value) for sign, value in terms if isinstance(value, AttributeConstructor)
    ]
    if len(constructors) != 1 or constructors[0][0] != 1:
        raise AttributeSpecificationError(
            f"Attribute rule for {symbol} must mirror constructor {constructor}",
        )
    mirrored = constructors[0][1]
    if mirrored.name.lower() != constructor.lower():
        raise AttributeSpecificationError(
            f"Attribute constructor {mirrored.name} does not match {constructor}",
        )

    constant: GFExpression = GFInteger(0)
    size_coefficient: GFExpression = GFInteger(0)
    attribute_coefficients: dict[str, GFExpression] = {}
    removed = False
    for sign, value in terms:
        if value is mirrored and not removed:
            removed = True
            continue
        value_constant, value_size, value_attributes = _affine_value(value, symbol=symbol)
        sign_expression = GFInteger(1) if sign == 1 else _integer(-1)
        constant = _sum(
            (constant, _product((sign_expression, value_constant))),
        )
        size_coefficient = _sum(
            (size_coefficient, _product((sign_expression, value_size))),
        )
        for name, coefficient in value_attributes.items():
            attribute_coefficients[name] = _sum(
                (
                    attribute_coefficients.get(name, GFInteger(0)),
                    _product((sign_expression, coefficient)),
                ),
            )
    return mirrored, constant, size_coefficient, attribute_coefficients


def _validate_rule_shape(
    structure: Expression,
    attribute_value: AttributeExpression,
    *,
    current_symbol: str,
) -> None:
    if isinstance(structure, Reference):
        _affine_value(attribute_value, symbol=structure.name)
        return
    if structure.name.lower() == "subst":
        raise UnsupportedGeneratingFunctionDerivation(
            "Attribute rules for Subst require attribute-rule expansion",
        )
    mirrored, _, _, _ = _constructor_and_adjustment(
        attribute_value,
        constructor=structure.name,
        symbol=current_symbol,
    )
    if len(mirrored.arguments) != len(structure.arguments):
        raise AttributeSpecificationError(
            f"{structure.name} attribute rule has incompatible arity",
        )
    for structure_argument, attribute_argument in zip(
        structure.arguments,
        mirrored.arguments,
        strict=True,
    ):
        _validate_rule_shape(
            structure_argument,
            attribute_argument,
            current_symbol=current_symbol,
        )


def _validate_outer_dependency_graphs(
    equations: Mapping[str, Expression],
    attributes: Mapping[tuple[str, str], AttributeExpression],
    attribute_names: set[str],
) -> None:
    for symbol, structure in equations.items():
        if isinstance(structure, Reference):
            continue
        dependencies: dict[str, set[str]] = {}
        for attribute in attribute_names:
            value = attributes.get(
                (attribute, symbol),
                _default_attribute_expression(structure, attribute),
            )
            _, _, _, coefficients = _constructor_and_adjustment(
                value,
                constructor=structure.name,
                symbol=symbol,
            )
            dependencies[attribute] = {
                dependency
                for dependency, coefficient in coefficients.items()
                if not _gf_is_zero(coefficient)
            }
        _require_acyclic_dependencies(dependencies)


def _require_acyclic_dependencies(dependencies: Mapping[str, set[str]]) -> None:
    active: set[str] = set()
    visited: set[str] = set()

    def visit(attribute: str) -> None:
        if attribute in visited:
            return
        if attribute in active:
            raise AttributeSpecificationError(
                "Attributes of one structure may not have circular dependencies",
            )
        active.add(attribute)
        for dependency in dependencies[attribute]:
            if dependency not in dependencies:
                raise AttributeSpecificationError(
                    f"Attribute {dependency!r} has no marker variable",
                )
            visit(dependency)
        active.remove(attribute)
        visited.add(attribute)

    for attribute in dependencies:
        visit(attribute)


def _replace_variables(
    expression: GFExpression,
    replacements: Mapping[str, GFExpression],
) -> GFExpression:
    if isinstance(expression, GFVariable):
        return replacements.get(expression.name, expression)
    if isinstance(expression, GFInteger | GFIndex | GFTotient):
        return expression
    if isinstance(expression, GFUnary):
        return GFUnary(expression.operator, _replace_variables(expression.operand, replacements))
    if isinstance(expression, GFBinary):
        return GFBinary(
            expression.operator,
            _replace_variables(expression.left, replacements),
            _replace_variables(expression.right, replacements),
        )
    if isinstance(expression, GFFunction):
        return GFFunction(
            expression.name,
            _replace_variables(expression.argument, replacements),
        )
    if isinstance(expression, GFMultivariateSeriesCall):
        return GFMultivariateSeriesCall(
            expression.name,
            tuple(_replace_variables(argument, replacements) for argument in expression.arguments),
        )
    if isinstance(expression, GFInfiniteSum):
        return GFInfiniteSum(
            _replace_variables(expression.summand, replacements),
            expression.index,
            expression.lower_bound,
        )
    raise UnsupportedGeneratingFunctionDerivation(
        f"Cannot substitute variables in {type(expression).__name__}",
    )


def _raise_all_variables(
    expression: GFExpression,
    exponent: GFExpression,
    variables: tuple[GFVariable, ...],
) -> GFExpression:
    return _replace_variables(
        expression,
        {variable.name: _power(variable, exponent) for variable in variables},
    )


def _divisors(value: int) -> tuple[int, ...]:
    return tuple(candidate for candidate in range(1, value + 1) if value % candidate == 0)


def _totient(value: int) -> int:
    return sum(1 for candidate in range(1, value + 1) if math.gcd(candidate, value) == 1)


class _AttributeEquationBuilder:
    def __init__(
        self,
        equations: Mapping[str, Expression],
        attribute_equations: Mapping[tuple[str, str], AttributeExpression],
        *,
        labeled: bool,
        attributes: Mapping[str, str],
    ):
        self.equations = equations
        self.attribute_equations = attribute_equations
        self.labeled = labeled
        self.attributes = attributes
        self.variables = (
            GFVariable("_x"),
            *(GFVariable(name) for name in attributes),
        )
        self.attribute_names = tuple(attributes.values())
        self.next_index = 1

    def build(self) -> AttributeEquationSystem:
        equations = tuple(
            GFEquation(
                cast(GFExpression, GFMultivariateSeriesCall(name, self.variables)),
                self._pair(
                    expression,
                    tuple(
                        self.attribute_equations.get(
                            (attribute, name),
                            _default_attribute_expression(expression, attribute),
                        )
                        for attribute in self.attribute_names
                    ),
                    current_symbol=name,
                ),
            )
            for name, expression in self.equations.items()
        )
        return AttributeEquationSystem(
            equations,
            tuple(variable.name for variable in self.variables),
            self.labeled,
            dict(self.equations),
            dict(self.attribute_equations),
            dict(self.attributes),
            tuple(
                sorted(
                    {
                        parameter
                        for expression in self.attribute_equations.values()
                        for parameter in _walk_symbols(expression)
                    },
                ),
            ),
        )

    def _pair(
        self,
        structure: Expression,
        attribute_values: tuple[AttributeExpression, ...],
        *,
        current_symbol: str,
    ) -> GFExpression:
        if isinstance(structure, Reference):
            return self._reference(structure.name, attribute_values)

        if structure.name.lower() == "subst":
            raise UnsupportedGeneratingFunctionDerivation(
                "Attribute equations for Subst require attribute-rule expansion",
            )

        mirrored: list[AttributeConstructor] = []
        constants: list[GFExpression] = []
        size_coefficients: list[GFExpression] = []
        outer_dependencies: list[dict[str, GFExpression]] = []
        for value in attribute_values:
            (
                constructor,
                constant,
                size_coefficient,
                dependencies,
            ) = _constructor_and_adjustment(
                value,
                constructor=structure.name,
                symbol=current_symbol,
            )
            mirrored.append(constructor)
            constants.append(constant)
            size_coefficients.append(size_coefficient)
            outer_dependencies.append(dependencies)

        name = structure.name.lower()
        if any(len(rule.arguments) != len(structure.arguments) for rule in mirrored):
            raise AttributeSpecificationError(
                f"{structure.name} attribute rule has incompatible arity",
            )
        if name == "union":
            result = _sum(
                self._pair(
                    argument,
                    tuple(rule.arguments[index] for rule in mirrored),
                    current_symbol=current_symbol,
                )
                for index, argument in enumerate(structure.arguments)
            )
        elif name == "prod":
            result = _product(
                self._pair(
                    argument,
                    tuple(rule.arguments[index] for rule in mirrored),
                    current_symbol=current_symbol,
                )
                for index, argument in enumerate(structure.arguments)
            )
        elif name in {"sequence", "set", "cycle", "powerset"}:
            if len(structure.arguments) != 1:
                raise AttributeSpecificationError(
                    f"{structure.name} requires one component argument",
                )
            component = self._pair(
                structure.arguments[0],
                tuple(rule.arguments[0] for rule in mirrored),
                current_symbol=current_symbol,
            )
            minimum, maximum = _GeneratingFunctionDeriver._bounds(
                structure.cardinality,
                default_minimum=1 if name == "cycle" else 0,
            )
            result = self._iterative(name, component, minimum, maximum)
        else:
            raise UnsupportedGeneratingFunctionDerivation(
                f"Unsupported constructor {structure.name!r}",
            )

        resolved = self._resolve_outer_adjustments(
            constants,
            size_coefficients,
            outer_dependencies,
        )
        replacements: dict[str, GFExpression] = {"_x": self.variables[0]}
        factor_terms: list[GFExpression] = []
        for output_variable, (constant, size_coefficient, base_coefficients) in zip(
            self.variables[1:],
            resolved,
            strict=True,
        ):
            if not _gf_is_zero(constant):
                factor_terms.append(_attribute_power(output_variable, constant))
            if not _gf_is_zero(size_coefficient):
                replacements["_x"] = _product(
                    (
                        replacements["_x"],
                        _attribute_power(output_variable, size_coefficient),
                    ),
                )
            for index, coefficient in enumerate(base_coefficients):
                if not _gf_is_zero(coefficient):
                    input_variable = self.variables[index + 1]
                    replacements[input_variable.name] = _product(
                        (
                            replacements.get(input_variable.name, GFInteger(1)),
                            _attribute_power(output_variable, coefficient),
                        ),
                    )
        adjusted = _replace_variables(result, replacements)
        return _product((*factor_terms, adjusted))

    def _resolve_outer_adjustments(
        self,
        constants: list[GFExpression],
        size_coefficients: list[GFExpression],
        dependencies: list[dict[str, GFExpression]],
    ) -> tuple[
        tuple[GFExpression, GFExpression, tuple[GFExpression, ...]],
        ...,
    ]:
        count = len(self.attribute_names)
        indices = {name: index for index, name in enumerate(self.attribute_names)}
        resolved: dict[
            int,
            tuple[GFExpression, GFExpression, tuple[GFExpression, ...]],
        ] = {}
        active: set[int] = set()

        def resolve(
            index: int,
        ) -> tuple[GFExpression, GFExpression, tuple[GFExpression, ...]]:
            if index in resolved:
                return resolved[index]
            if index in active:
                raise AttributeSpecificationError(
                    "Attributes of one structure may not have circular dependencies",
                )
            active.add(index)
            constant = constants[index]
            size_coefficient = size_coefficients[index]
            base: list[GFExpression] = [GFInteger(0) for _ in range(count)]
            base[index] = GFInteger(1)
            for attribute, coefficient in dependencies[index].items():
                if attribute not in indices:
                    raise AttributeSpecificationError(
                        f"Attribute {attribute!r} has no marker variable",
                    )
                dependency_constant, dependency_size, dependency_base = resolve(
                    indices[attribute],
                )
                constant = _sum(
                    (constant, _product((coefficient, dependency_constant))),
                )
                size_coefficient = _sum(
                    (
                        size_coefficient,
                        _product((coefficient, dependency_size)),
                    ),
                )
                for base_index, base_coefficient in enumerate(dependency_base):
                    base[base_index] = _sum(
                        (
                            base[base_index],
                            _product((coefficient, base_coefficient)),
                        ),
                    )
            active.remove(index)
            value = (constant, size_coefficient, tuple(base))
            resolved[index] = value
            return value

        return tuple(resolve(index) for index in range(count))

    def _reference(
        self,
        name: str,
        attribute_values: tuple[AttributeExpression, ...],
    ) -> GFExpression:
        affine = tuple(_affine_value(value, symbol=name) for value in attribute_values)
        if name in {"Atom", "Z", "Epsilon"} and name not in self.equations:
            size = 0 if name == "Epsilon" else 1
            factors: list[GFExpression] = [] if size == 0 else [self.variables[0]]
            for variable, (constant, size_coefficient, coefficients) in zip(
                self.variables[1:],
                affine,
                strict=True,
            ):
                if coefficients:
                    raise AttributeSpecificationError(
                        f"Elementary symbol {name} has no recursive attributes",
                    )
                exponent = _sum(
                    (
                        constant,
                        _product((GFInteger(size), size_coefficient)),
                    ),
                )
                if not _gf_is_zero(exponent):
                    factors.append(_attribute_power(variable, exponent))
            return _product(factors)
        if name not in self.equations:
            raise AttributeSpecificationError(f"Undefined structure symbol {name!r}")

        arguments: list[GFExpression] = [self.variables[0]]
        constant_factors: list[GFExpression] = []
        for output_variable, (constant, size_coefficient, _) in zip(
            self.variables[1:],
            affine,
            strict=True,
        ):
            if not _gf_is_zero(constant):
                constant_factors.append(_attribute_power(output_variable, constant))
            if not _gf_is_zero(size_coefficient):
                arguments[0] = _product(
                    (
                        arguments[0],
                        _attribute_power(output_variable, size_coefficient),
                    ),
                )
        for input_attribute in self.attribute_names:
            argument_factors = [
                _attribute_power(
                    output_variable,
                    coefficients.get(input_attribute, GFInteger(0)),
                )
                for output_variable, (_, _, coefficients) in zip(
                    self.variables[1:],
                    affine,
                    strict=True,
                )
                if not _gf_is_zero(
                    coefficients.get(input_attribute, GFInteger(0)),
                )
            ]
            arguments.append(_product(argument_factors))
        call = cast(
            GFExpression,
            GFMultivariateSeriesCall(name, tuple(arguments)),
        )
        return _product((*constant_factors, call))

    def _iterative(
        self,
        name: str,
        component: GFExpression,
        minimum: int,
        maximum: int | None,
    ) -> GFExpression:
        if name == "sequence":
            return _GeneratingFunctionDeriver._sequence(component, minimum, maximum)
        if name == "set" and self.labeled:
            return _GeneratingFunctionDeriver._labeled_set(component, minimum, maximum)
        if name == "cycle" and self.labeled:
            return _GeneratingFunctionDeriver._labeled_cycle(component, minimum, maximum)
        if name == "powerset" and self.labeled:
            raise UnsupportedGeneratingFunctionDerivation(
                "PowerSet is only defined for unlabeled structures",
            )
        if name == "cycle":
            return self._unlabeled_cycle(component, minimum, maximum)
        return self._unlabeled_selection(
            component,
            minimum,
            maximum,
            distinct=name == "powerset",
        )

    def _unlabeled_selection(
        self,
        component: GFExpression,
        minimum: int,
        maximum: int | None,
        *,
        distinct: bool,
    ) -> GFExpression:
        fixed_values: dict[int, GFExpression] = {0: GFInteger(1)}

        def fixed(count: int) -> GFExpression:
            if count not in fixed_values:
                terms: list[GFExpression] = []
                for part in range(1, count + 1):
                    substituted = _raise_all_variables(
                        component,
                        GFInteger(part),
                        self.variables,
                    )
                    term = _product((substituted, fixed(count - part)))
                    if distinct and part % 2 == 0:
                        term = GFUnary("-", term)
                    terms.append(term)
                fixed_values[count] = _scale(_sum(terms), Fraction(1, count))
            return fixed_values[count]

        if maximum is not None:
            return _sum(fixed(count) for count in range(minimum, maximum + 1))
        index = GFIndex(self.next_index)
        self.next_index += 1
        substituted = _raise_all_variables(component, index, self.variables)
        summand: GFExpression = _divide(substituted, index)
        if distinct:
            sign = _power(
                GFInteger(-1),
                GFBinary("-", index, GFInteger(1)),
            )
            summand = _product((sign, summand))
        unrestricted = GFFunction("exp", GFInfiniteSum(summand, index))
        return _subtract(
            unrestricted,
            _sum(fixed(count) for count in range(minimum)),
        )

    def _unlabeled_cycle(
        self,
        component: GFExpression,
        minimum: int,
        maximum: int | None,
    ) -> GFExpression:
        def fixed(count: int) -> GFExpression:
            return _sum(
                _scale(
                    _power(
                        _raise_all_variables(
                            component,
                            GFInteger(divisor),
                            self.variables,
                        ),
                        count // divisor,
                    ),
                    Fraction(_totient(divisor), count),
                )
                for divisor in _divisors(count)
            )

        if maximum is not None:
            return _sum(fixed(count) for count in range(minimum, maximum + 1))
        index = GFIndex(self.next_index)
        self.next_index += 1
        substituted = _raise_all_variables(component, index, self.variables)
        logarithm = GFFunction(
            "ln",
            _divide(GFInteger(1), _subtract(GFInteger(1), substituted)),
        )
        unrestricted = GFInfiniteSum(
            _product((_divide(GFTotient(index), index), logarithm)),
            index,
        )
        return _subtract(
            unrestricted,
            _sum(fixed(count) for count in range(1, minimum)),
        )


def agfeqns(
    specification: str | Mapping[str, Expression],
    attribute_specification: str | Mapping[tuple[str, str], AttributeExpression],
    *,
    labeled: bool | None = None,
    labelled: bool | None = None,
    attributes: Mapping[str, str],
) -> AttributeEquationSystem:
    """Return symbolic multivariate equations for an attribute grammar.

    ``labeled`` is the preferred spelling for the labeling flag; ``labelled``
    is accepted for backward compatibility.
    """

    labeled = resolve_labelled(labeled=labeled, labelled=labelled)
    if not isinstance(labeled, bool):
        raise TypeError("labeled must be a boolean")
    if not isinstance(attributes, Mapping):
        raise TypeError("attributes must map marker-variable names to attribute names")
    equations = _structure_equations(specification)
    attribute_equations = _attribute_equations(attribute_specification)
    _validate_attribute_grammar(equations, attribute_equations, attributes)
    return _AttributeEquationBuilder(
        equations,
        attribute_equations,
        labeled=labeled,
        attributes=attributes,
    ).build()


def _falling_factorial(value: int, order: int) -> int:
    result = 1
    for offset in range(order):
        result *= value - offset
    return result


def agfmomentsolve(
    equations: AttributeEquationSystem,
    num: int,
    *,
    term_count: int,
    parameters: Mapping[str, int] | None = None,
) -> AttributeMomentSystem:
    """Return exact factorial-moment series through derivative order ``num``.

    Each marker variable is differentiated from zero through ``num`` times and
    then set to one.  Mixed orders are included, so ordinary averages and
    variances as well as cross moments are available from one result.
    """

    if not isinstance(equations, AttributeEquationSystem):
        raise TypeError("equations must be returned by agfeqns")
    if isinstance(num, bool) or not isinstance(num, int):
        raise TypeError("num must be an integer")
    if num < 0:
        raise ValueError("num must be nonnegative")
    if isinstance(term_count, bool) or not isinstance(term_count, int):
        raise TypeError("term_count must be an integer")
    if term_count <= 0:
        raise ValueError("term_count must be positive")

    joint = agfseries(
        equations.structure_specification,
        equations.attribute_specification,
        labeled=equations.labeled,
        term_count=term_count,
        attributes=equations.attributes,
        parameters=parameters,
    )
    attribute_count = len(equations.attributes)
    result: dict[tuple[str, tuple[int, ...]], tuple[Fraction, ...]] = {}
    for symbol, series in joint.items():
        for orders in product(range(num + 1), repeat=attribute_count):
            coefficients = [Fraction() for _ in range(term_count)]
            for exponent, coefficient in series.coefficients.items():
                multiplier = math.prod(
                    _falling_factorial(value, order)
                    for value, order in zip(exponent[1:], orders, strict=True)
                )
                coefficients[exponent[0]] += coefficient * multiplier
            result[(symbol, orders)] = tuple(coefficients)
    return AttributeMomentSystem(
        equations.variables,
        term_count,
        equations.labeled,
        result,
    )


class _AttributeEvaluator:
    def __init__(
        self,
        equations: Mapping[str, Expression],
        attributes: Mapping[tuple[str, str], AttributeExpression],
        parameters: Mapping[str, int],
    ):
        self.equations = equations
        self.attributes = attributes
        self.parameters = parameters
        self.active: set[tuple[str, str, CombinatorialObject]] = set()

    def evaluate(
        self,
        attribute: str,
        symbol: str,
        obj: CombinatorialObject,
    ) -> int:
        key = (attribute, symbol, obj)
        if key in self.active:
            raise AttributeSpecificationError(
                f"Circular attribute dependency while evaluating {attribute}({symbol})",
            )
        self.active.add(key)
        try:
            expression = self.attributes.get((attribute, symbol))
            if expression is None:
                return self._default(attribute, symbol, obj)
            return self._value(expression, obj)
        finally:
            self.active.remove(key)

    def _default(self, attribute: str, symbol: str, obj: CombinatorialObject) -> int:
        return self._value(
            _default_attribute_expression(self.equations[symbol], attribute),
            obj,
        )

    def _value(self, expression: AttributeExpression, obj: CombinatorialObject) -> int:
        if isinstance(expression, AttributeInteger):
            return expression.value
        if isinstance(expression, AttributeSymbol):
            return self.parameters[expression.name]
        if isinstance(expression, SizeCall):
            return obj.size
        if isinstance(expression, AttributeCall):
            return self.evaluate(expression.attribute, expression.symbol, obj)
        if isinstance(expression, AttributeBinary):
            left = self._value(expression.left, obj)
            right = self._value(expression.right, obj)
            if expression.operator == "+":
                return left + right
            if expression.operator == "-":
                return left - right
            return left * right

        if not isinstance(obj, ConstructionObject):
            raise AttributeSpecificationError(
                f"Attribute constructor {expression.name} does not match an elementary object",
            )
        name = expression.name.lower()
        if name != obj.constructor.lower():
            raise AttributeSpecificationError(
                f"Attribute constructor {expression.name} does not match {obj.constructor}",
            )
        if name == "union":
            if obj.branch is None or not 0 <= obj.branch < len(expression.arguments):
                raise AttributeSpecificationError("Union attribute rule has incompatible arity")
            return self._value(expression.arguments[obj.branch], obj.children[0])
        if name == "prod":
            if len(expression.arguments) != len(obj.children):
                raise AttributeSpecificationError("Prod attribute rule has incompatible arity")
            return sum(
                self._value(argument, child)
                for argument, child in zip(expression.arguments, obj.children, strict=True)
            )
        if len(expression.arguments) != 1:
            raise AttributeSpecificationError(
                f"{expression.name} attribute rule requires exactly one argument",
            )
        return sum(self._value(expression.arguments[0], child) for child in obj.children)


def agfseries(
    specification: str | Mapping[str, Expression],
    attribute_specification: str | Mapping[tuple[str, str], AttributeExpression],
    *,
    labeled: bool | None = None,
    labelled: bool | None = None,
    term_count: int,
    attributes: Mapping[str, str],
    parameters: Mapping[str, int] | None = None,
) -> dict[str, AttributeSeries]:
    """Return exact truncated multivariate series for an attribute grammar.

    ``attributes`` maps marker-variable names to attribute names.  Exponents
    are returned in ``(size, *attribute_values)`` order. ``labeled`` is the
    preferred spelling for the labeling flag; ``labelled`` is accepted for
    backward compatibility.
    """

    labeled = resolve_labelled(labeled=labeled, labelled=labelled)
    if not isinstance(labeled, bool):
        raise TypeError("labeled must be a boolean")
    if isinstance(term_count, bool) or not isinstance(term_count, int):
        raise TypeError("term_count must be an integer")
    if term_count <= 0:
        raise ValueError("term_count must be positive")
    if not isinstance(attributes, Mapping):
        raise TypeError("attributes must map marker-variable names to attribute names")

    equations = _structure_equations(specification)
    attribute_equations = _attribute_equations(attribute_specification)
    _validate_attribute_grammar(equations, attribute_equations, attributes)
    parameter_values = _validate_parameters(attribute_equations, parameters)
    variables = ("x", *attributes.keys())
    evaluator = _AttributeEvaluator(equations, attribute_equations, parameter_values)
    result: dict[str, AttributeSeries] = {}
    for symbol in equations:
        coefficients: dict[tuple[int, ...], Fraction] = {}
        for size in range(term_count):
            denominator = math.factorial(size) if labeled else 1
            for obj in allstructs(
                equations,
                size=size,
                labeled=labeled,
                symbol=symbol,
            ):
                combinatorial_object = cast(CombinatorialObject, obj)
                exponent = (
                    size,
                    *(
                        evaluator.evaluate(attribute, symbol, combinatorial_object)
                        for attribute in attributes.values()
                    ),
                )
                coefficients[exponent] = coefficients.get(exponent, Fraction()) + Fraction(
                    1,
                    denominator,
                )
        result[symbol] = AttributeSeries(variables, coefficients, labeled)
    return result


__all__ = [
    "AttributeBinary",
    "AttributeCall",
    "AttributeConstructor",
    "AttributeEquationSystem",
    "AttributeExpression",
    "AttributeInteger",
    "AttributeMomentSystem",
    "AttributeParser",
    "AttributeSeries",
    "AttributeSpecification",
    "AttributeSpecificationError",
    "AttributeSymbol",
    "SizeCall",
    "agfeqns",
    "agfmomentsolve",
    "agfseries",
    "parse_attribute_specification",
]
