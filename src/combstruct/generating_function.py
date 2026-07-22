"""Syntax tree and parser for finite elementary ECS generating functions.

The first parser milestone recognizes the exact finite-expression grammar used
by 913 stored ECS generating functions. Equations, infinite sums, algebraic
``RootOf`` values, ``LambertW``, and explicit complex values are rejected
clearly for later parser milestones. Parsing does not decide whether an
expression is an ordinary or exponential generating function and does not
evaluate its coefficients.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, cast

type UnaryOperator = Literal["+", "-"]
type BinaryOperator = Literal["+", "-", "*", "/", "^"]
type FunctionName = Literal["exp", "ln"]


class GeneratingFunctionError(ValueError):
    """A stored generating-function expression is malformed."""


class UnsupportedGeneratingFunction(GeneratingFunctionError):
    """A valid ECS generating-function form is outside the current grammar."""


@dataclass(frozen=True, slots=True)
class GFInteger:
    """An integer literal in a generating-function expression."""

    value: int


@dataclass(frozen=True, slots=True)
class GFVariable:
    """The Maple variable used by finite ECS generating functions."""

    name: Literal["_x"] = "_x"


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
    """An elementary function call recognized in the finite ECS corpus."""

    name: FunctionName
    argument: GFExpression


type GFExpression = GFInteger | GFVariable | GFUnary | GFBinary | GFFunction


TOKEN_RE = re.compile(r"\s*(\d+|[A-Za-z_][A-Za-z0-9_]*|[()+\-*/^]|\S)")
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
    """Parse the finite elementary expression syntax used by the ECS."""

    def __init__(self, source: str):
        self.source = source
        self.tokens = self._tokenize(source)
        self.position = 0

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
        if token in {"+", "-"}:
            return GFUnary(
                cast(UnaryOperator, token),
                self._parse_expression(UNARY_BINDING_POWER),
            )
        if token == "(":
            expression = self._parse_expression()
            self._expect(")")
            return expression
        if token in {"exp", "ln"}:
            self._expect("(")
            argument = self._parse_expression()
            self._expect(")")
            return GFFunction(cast(FunctionName, token), argument)
        if IDENTIFIER_RE.fullmatch(token):
            raise UnsupportedGeneratingFunction(
                f"Generating-function identifier {token!r} is not supported",
            )
        raise self._error(f"Expected an expression, found {token!r}")

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
    """Parse a finite elementary ECS generating-function expression."""

    return GeneratingFunctionParser(source).parse()


__all__ = [
    "GFBinary",
    "GFExpression",
    "GFFunction",
    "GFInteger",
    "GFUnary",
    "GFVariable",
    "GeneratingFunctionError",
    "GeneratingFunctionParser",
    "UnsupportedGeneratingFunction",
    "parse_generating_function",
]
