"""Syntax tree and parser for ECS combinatorial specifications."""

from __future__ import annotations

import re
from collections.abc import Mapping
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


def _nullable_expressions(equations: Specification) -> dict[str, bool]:
    nullable = {name: False for name in equations}

    def expression_nullable(expression: Expression) -> bool:
        if isinstance(expression, Reference):
            if expression.name == "Epsilon":
                return True
            if expression.name in ("Atom", "Z") and expression.name not in equations:
                return False
            return nullable.get(expression.name, False)

        name = expression.name.lower()
        if name == "union":
            return any(expression_nullable(argument) for argument in expression.arguments)
        if name == "prod":
            return all(expression_nullable(argument) for argument in expression.arguments)
        if name == "subst":
            if len(expression.arguments) != 2:
                return False
            inner, outer = expression.arguments
            return expression_nullable(inner) or expression_nullable(outer)
        if len(expression.arguments) != 1:
            return False
        component_nullable = expression_nullable(expression.arguments[0])
        minimum = expression.cardinality.minimum if expression.cardinality is not None else 0
        if name == "cycle":
            minimum = max(1, minimum)
        if name in {"sequence", "set", "powerset", "cycle"}:
            return minimum == 0 or component_nullable
        return False

    for _ in range(max(1, len(equations) + 1)):
        changed = False
        for name, expression in equations.items():
            value = expression_nullable(expression)
            if value and not nullable[name]:
                nullable[name] = True
                changed = True
        if not changed:
            break
    return nullable


class _SubstitutionExpander:
    def __init__(self, equations: Specification):
        self.equations = dict(equations)
        self.nullable = _nullable_expressions(self.equations)
        self.output: Specification = {}
        self.counter = 0

    def expand(self) -> Specification:
        for name, expression in self.equations.items():
            self.output[name] = self._transform(expression)
        return self.output

    def _fresh_name(self, source_name: str) -> str:
        while True:
            candidate = f"_subst_{self.counter}_{source_name}"
            self.counter += 1
            if candidate not in self.equations and candidate not in self.output:
                return candidate

    def _expression_nullable(self, expression: Expression) -> bool:
        if isinstance(expression, Reference):
            if expression.name == "Epsilon":
                return True
            if expression.name in ("Atom", "Z") and expression.name not in self.equations:
                return False
            return self.nullable.get(expression.name, False)

        name = expression.name.lower()
        if name == "union":
            return any(self._expression_nullable(argument) for argument in expression.arguments)
        if name == "prod":
            return all(self._expression_nullable(argument) for argument in expression.arguments)
        if name == "subst":
            if len(expression.arguments) != 2:
                return False
            return any(self._expression_nullable(argument) for argument in expression.arguments)
        if len(expression.arguments) != 1:
            return False
        minimum = expression.cardinality.minimum if expression.cardinality is not None else 0
        if name == "cycle":
            minimum = max(1, minimum)
        return minimum == 0 or self._expression_nullable(expression.arguments[0])

    def _validate_substitution(self, expression: Constructor) -> tuple[Expression, Expression]:
        if expression.cardinality is not None:
            raise SpecificationError("Subst does not accept a cardinality constraint")
        if len(expression.arguments) != 2:
            raise SpecificationError("Subst requires exactly two arguments")
        inner, outer = expression.arguments
        if self._expression_nullable(inner):
            raise SpecificationError("The first argument of Subst cannot produce size-zero objects")
        if self._expression_nullable(outer):
            raise SpecificationError(
                "The second argument of Subst cannot produce size-zero objects"
            )
        return inner, outer

    def _transform(self, expression: Expression) -> Expression:
        if isinstance(expression, Reference):
            return expression
        if expression.name.lower() == "subst":
            inner, outer = self._validate_substitution(expression)
            replacement = self._transform(inner)
            return self._substitute(replacement, outer, {})
        return Constructor(
            expression.name,
            tuple(self._transform(argument) for argument in expression.arguments),
            expression.cardinality,
        )

    def _substitute(
        self,
        replacement: Expression,
        outer: Expression,
        clones: dict[str, str],
    ) -> Expression:
        if isinstance(outer, Reference):
            if outer.name in ("Atom", "Z") and outer.name not in self.equations:
                return replacement
            if outer.name == "Epsilon" or outer.name not in self.equations:
                return outer
            if outer.name in clones:
                return Reference(clones[outer.name])

            clone_name = self._fresh_name(outer.name)
            clones[outer.name] = clone_name
            self.output[clone_name] = Reference("Epsilon")
            self.output[clone_name] = self._substitute(
                replacement,
                self.equations[outer.name],
                clones,
            )
            return Reference(clone_name)

        if outer.name.lower() == "subst":
            inner, nested_outer = self._validate_substitution(outer)
            nested_replacement = self._substitute(replacement, inner, clones)
            return self._substitute(nested_replacement, nested_outer, {})
        return Constructor(
            outer.name,
            tuple(self._substitute(replacement, argument, clones) for argument in outer.arguments),
            outer.cardinality,
        )


def expand_substitutions(specification: Mapping[str, Expression]) -> Specification:
    """Replace every ``Subst(A,B)`` with an equivalent cloned grammar.

    Maple defines this constructor as B-objects whose atoms are replaced by
    A-objects. Cloning referenced B productions preserves their recursive
    constructor structure and therefore their unlabeled symmetries.
    """

    if not isinstance(specification, Mapping):
        raise TypeError("specification must be a mapping of equations")
    return _SubstitutionExpander(dict(specification)).expand()
