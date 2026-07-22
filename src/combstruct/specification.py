"""Syntax tree and parser for ECS combinatorial specifications."""

from __future__ import annotations

import re
from dataclasses import dataclass


class SpecificationError(ValueError):
    """A combinatorial specification is malformed or incomplete."""


@dataclass(frozen=True)
class Cardinality:
    """Inclusive lower and optional upper bounds on constructor cardinality."""

    minimum: int = 0
    maximum: int | None = None

    def includes(self, value: int) -> bool:
        """Return whether ``value`` satisfies this cardinality constraint."""

        return value >= self.minimum and (self.maximum is None or value <= self.maximum)


@dataclass(frozen=True)
class Reference:
    """A reference to a named species or one of the ECS terminal symbols."""

    name: str


@dataclass(frozen=True)
class Constructor:
    """An ECS constructor call with zero or more component expressions."""

    name: str
    arguments: tuple[Reference | Constructor, ...]
    cardinality: Cardinality | None = None


Expression = Reference | Constructor
Specification = dict[str, Expression]


TOKEN_RE = re.compile(
    r"\s*(<=|[A-Za-z_][A-Za-z0-9_]*(?:\[\d+\])?|\d+|[{}(),=<])",
)


class Parser:
    """Parse the Maple ``combstruct``-style syntax used by the ECS."""

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

    def parse(self) -> Specification:
        """Parse and return the specification's named equations."""

        self._expect("{")
        equations: Specification = {}
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


def parse_specification(specification: str) -> Specification:
    """Parse an ECS specification into named immutable expression trees."""

    return Parser(specification).parse()
