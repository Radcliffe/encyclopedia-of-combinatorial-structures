"""Exact-size exhaustive generation for combinatorial specifications."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from itertools import combinations, product

from .predefined import (
    PredefinedObject,
    PredefinedStructure,
    StructureSize,
    enumerate_predefined,
    is_predefined,
)
from .specification import (
    Cardinality,
    Expression,
    Reference,
    SpecificationError,
    expand_substitutions,
    parse_specification,
    resolve_labelled,
)
from .terms import UnsupportedConstruction


@dataclass(frozen=True)
class AtomObject:
    """One atom, optionally carrying its label in a labeled class."""

    label: int | None = None

    @property
    def size(self) -> int:
        """Return the number of atoms in this object."""

        return 1


@dataclass(frozen=True)
class EpsilonObject:
    """A size-zero elementary object, optionally preserving its grammar tag."""

    tag: str | None = None

    @property
    def size(self) -> int:
        """Return the number of atoms in this object."""

        return 0


@dataclass(frozen=True)
class ConstructionObject:
    """An object built by a grammar constructor.

    ``branch`` identifies a ``Union`` alternative so equal-looking alternatives
    remain disjoint. It is ``None`` for every other constructor.
    """

    constructor: str
    children: tuple[CombinatorialObject, ...]
    branch: int | None = None

    @property
    def size(self) -> int:
        """Return the total number of atoms in the children."""

        return sum(child.size for child in self.children)


type CombinatorialObject = AtomObject | EpsilonObject | ConstructionObject
type StructureValue = CombinatorialObject | PredefinedObject
type _SizeKey = int | tuple[int, ...]


def _object_key(obj: CombinatorialObject) -> tuple[object, ...]:
    if isinstance(obj, AtomObject):
        return ("Atom", -1 if obj.label is None else obj.label)
    if isinstance(obj, EpsilonObject):
        return ("Epsilon", "" if obj.tag is None else obj.tag)
    return (
        obj.constructor,
        -1 if obj.branch is None else obj.branch,
        tuple(_object_key(child) for child in obj.children),
    )


def _canonical_children(
    children: tuple[CombinatorialObject, ...],
) -> tuple[CombinatorialObject, ...]:
    return tuple(sorted(children, key=_object_key))


def _canonical_cycle(
    children: tuple[CombinatorialObject, ...],
) -> tuple[CombinatorialObject, ...]:
    if not children:
        return children
    rotations = tuple(children[offset:] + children[:offset] for offset in range(len(children)))
    return min(rotations, key=lambda rotation: tuple(_object_key(child) for child in rotation))


def _weak_compositions(total: int, parts: int) -> Iterator[tuple[int, ...]]:
    if parts == 0:
        if total == 0:
            yield ()
        return
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in _weak_compositions(total - first, parts - 1):
            yield (first, *rest)


def _label_partitions(
    labels: tuple[int, ...],
    parts: int,
) -> Iterator[tuple[tuple[int, ...], ...]]:
    if parts == 0:
        if not labels:
            yield ()
        return
    for assignments in product(range(parts), repeat=len(labels)):
        blocks = tuple(
            tuple(
                label
                for label, assignment in zip(labels, assignments, strict=True)
                if assignment == part
            )
            for part in range(parts)
        )
        yield blocks


@dataclass
class StructureIterator(Iterator[StructureValue]):
    """Mutable iterator state corresponding to Maple's ``iterstructs`` table."""

    objects: tuple[StructureValue, ...]
    _position: int = field(default=0, init=False, repr=False)

    def __iter__(self) -> StructureIterator:
        return self

    def __next__(self) -> StructureValue:
        if self._position >= len(self.objects):
            raise StopIteration
        result = self.objects[self._position]
        self._position += 1
        return result

    @property
    def is_finished(self) -> bool:
        """Return whether all objects have been consumed."""

        return self._position >= len(self.objects)


class _Enumerator:
    def __init__(
        self,
        equations: Mapping[str, Expression],
        *,
        labeled: bool,
        size: int,
    ):
        self.equations = expand_substitutions(equations)
        self.labeled = labeled
        self.size = size
        self.keys = self._keys()
        self.values: dict[str, dict[_SizeKey, set[CombinatorialObject]]] = {
            name: {key: set() for key in self.keys} for name in self.equations
        }

    def _keys(self) -> tuple[_SizeKey, ...]:
        if not self.labeled:
            return tuple(range(self.size + 1))
        labels = tuple(range(1, self.size + 1))
        return tuple(
            subset
            for subset_size in range(self.size + 1)
            for subset in combinations(labels, subset_size)
        )

    def enumerate(self, symbol: str) -> tuple[CombinatorialObject, ...]:
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a string")
        if not symbol:
            raise ValueError("symbol must not be empty")
        if symbol not in self.equations:
            raise SpecificationError(f"Specification does not define {symbol!r}")

        iteration_limit = max(100, (self.size + 1) * max(1, len(self.equations)) * 8)
        for _ in range(iteration_limit):
            changed = False
            for name, expression in self.equations.items():
                for key in self.keys:
                    candidates: set[CombinatorialObject]
                    if (
                        isinstance(expression, Reference)
                        and expression.name == "Epsilon"
                        and self._key_size(key) == 0
                    ):
                        candidates = {EpsilonObject(name)}
                    else:
                        candidates = self._evaluate(expression, key)
                    before = len(self.values[name][key])
                    self.values[name][key].update(candidates)
                    changed = changed or len(self.values[name][key]) != before
            if not changed:
                target: _SizeKey = tuple(range(1, self.size + 1)) if self.labeled else self.size
                return tuple(sorted(self.values[symbol][target], key=_object_key))

        raise UnsupportedConstruction(
            "Exhaustive generation did not reach a finite fixed point; "
            "the specification may not be well founded",
        )

    def _evaluate(
        self,
        expression: Expression,
        key: _SizeKey,
    ) -> set[CombinatorialObject]:
        if isinstance(expression, Reference):
            return self._reference(expression.name, key)

        name = expression.name.lower()
        if name == "union":
            if expression.cardinality is not None:
                raise SpecificationError("Union does not accept a cardinality constraint")
            return {
                ConstructionObject("Union", (obj,), branch=branch)
                for branch, argument in enumerate(expression.arguments)
                for obj in self._evaluate(argument, key)
            }
        if name == "prod":
            if expression.cardinality is not None:
                raise SpecificationError("Prod does not accept a cardinality constraint")
            return self._fixed_arity("Prod", expression.arguments, key)
        if name not in {"sequence", "set", "cycle", "powerset"}:
            raise UnsupportedConstruction(
                f"Exhaustive generation does not support constructor {expression.name!r}",
            )
        if len(expression.arguments) != 1:
            raise SpecificationError(f"{expression.name} requires exactly one component argument")
        if name == "sequence":
            return self._collection(
                "Sequence", expression.arguments[0], expression.cardinality, key
            )
        if name == "set":
            return self._collection("Set", expression.arguments[0], expression.cardinality, key)
        if name == "cycle":
            supplied = expression.cardinality or Cardinality()
            constraint = Cardinality(max(1, supplied.minimum), supplied.maximum)
            return self._collection("Cycle", expression.arguments[0], constraint, key)
        if name == "powerset":
            if self.labeled:
                raise UnsupportedConstruction("PowerSet is only defined for unlabeled structures")
            return self._collection(
                "PowerSet",
                expression.arguments[0],
                expression.cardinality,
                key,
            )
        raise AssertionError("unreachable")

    def _reference(self, name: str, key: _SizeKey) -> set[CombinatorialObject]:
        key_size = self._key_size(key)
        if name in ("Atom", "Z") and name not in self.equations:
            if key_size != 1:
                return set()
            label = key[0] if isinstance(key, tuple) else None
            return {AtomObject(label)}
        if name == "Epsilon":
            return {EpsilonObject()} if key_size == 0 else set()
        try:
            return self.values[name][key]
        except KeyError as error:
            raise SpecificationError(f"Undefined symbol {name!r}") from error

    @staticmethod
    def _key_size(key: _SizeKey) -> int:
        return len(key) if isinstance(key, tuple) else key

    def _partitions(
        self,
        key: _SizeKey,
        parts: int,
    ) -> Iterator[tuple[_SizeKey, ...]]:
        if isinstance(key, tuple):
            yield from _label_partitions(key, parts)
        else:
            yield from _weak_compositions(key, parts)

    def _fixed_arity(
        self,
        constructor: str,
        arguments: tuple[Expression, ...],
        key: _SizeKey,
    ) -> set[CombinatorialObject]:
        if not arguments:
            return {ConstructionObject(constructor, ())} if self._key_size(key) == 0 else set()
        result: set[CombinatorialObject] = set()
        for partition in self._partitions(key, len(arguments)):
            choices = [
                tuple(self._evaluate(argument, child_key))
                for argument, child_key in zip(arguments, partition, strict=True)
            ]
            if any(not choice for choice in choices):
                continue
            result.update(
                ConstructionObject(constructor, tuple(children)) for children in product(*choices)
            )
        return result

    def _collection(
        self,
        constructor: str,
        component: Expression,
        cardinality: Cardinality | None,
        key: _SizeKey,
    ) -> set[CombinatorialObject]:
        empty_key: _SizeKey = () if self.labeled else 0
        if self._evaluate(component, empty_key):
            raise UnsupportedConstruction(
                f"{constructor} cannot contain size-zero objects",
            )

        constraint = cardinality or Cardinality()
        maximum = self._key_size(key)
        if constraint.maximum is not None:
            maximum = min(maximum, constraint.maximum)
        minimum = constraint.minimum
        if minimum > maximum:
            return set()

        result: set[CombinatorialObject] = set()
        for count in range(minimum, maximum + 1):
            repeated = (component,) * count
            for obj in self._fixed_arity(constructor, repeated, key):
                if not isinstance(obj, ConstructionObject):
                    raise AssertionError("fixed-arity generation returned an elementary object")
                children = obj.children
                if constructor in ("Set", "PowerSet"):
                    children = _canonical_children(children)
                    if constructor == "PowerSet" and len(set(children)) != len(children):
                        continue
                elif constructor == "Cycle":
                    children = _canonical_cycle(children)
                result.add(ConstructionObject(constructor, children))
        return result


def _validate_size(size: int) -> None:
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be an integer")
    if size < 0:
        raise ValueError("size must be nonnegative")


def _validate_universe(labeled: bool) -> None:
    if not isinstance(labeled, bool):
        raise TypeError("labeled must be a boolean")


def allstructs(
    specification: str | Mapping[str, Expression] | PredefinedStructure,
    *,
    size: StructureSize = None,
    labeled: bool | None = None,
    labelled: bool | None = None,
    symbol: str = "S",
) -> tuple[StructureValue, ...]:
    """Return objects from a grammar-defined or predefined finite class.

    ``labeled`` is the preferred spelling for the labeling flag; ``labelled``
    is accepted for backward compatibility.
    """

    labeled = resolve_labelled(labeled=labeled, labelled=labelled)
    if is_predefined(specification):
        if labeled is not None:
            raise TypeError("labeled does not apply to predefined structures")
        if symbol != "S":
            raise ValueError("symbol does not apply to predefined structures")
        return enumerate_predefined(specification, size=size)
    if size is None or isinstance(size, str):
        raise TypeError("grammar-defined structures require an integer size")
    _validate_size(size)
    if labeled is None:
        raise TypeError("grammar-defined structures require labeled=True or labeled=False")
    _validate_universe(labeled)
    if isinstance(specification, str):
        equations = parse_specification(specification)
    elif isinstance(specification, Mapping):
        equations = dict(specification)
    else:
        raise TypeError("specification must be text or a mapping of equations")
    return _Enumerator(equations, labeled=labeled, size=size).enumerate(symbol)


def iterstructs(
    specification: str | Mapping[str, Expression] | PredefinedStructure,
    *,
    size: StructureSize = None,
    labeled: bool | None = None,
    labelled: bool | None = None,
    symbol: str = "S",
) -> StructureIterator:
    """Return mutable iterator state over ``allstructs`` results."""

    return StructureIterator(
        allstructs(
            specification,
            size=size,
            labeled=resolve_labelled(labeled=labeled, labelled=labelled),
            symbol=symbol,
        ),
    )


def _require_iterator(iterator: StructureIterator) -> None:
    if not isinstance(iterator, StructureIterator):
        raise TypeError("iterator must be a StructureIterator")


def nextstruct(iterator: StructureIterator) -> StructureValue:
    """Return and consume the next object from ``iterstructs``."""

    _require_iterator(iterator)
    return next(iterator)


def finished(iterator: StructureIterator) -> bool:
    """Return whether an ``iterstructs`` iterator has been exhausted."""

    _require_iterator(iterator)
    return iterator.is_finished


__all__ = [
    "AtomObject",
    "CombinatorialObject",
    "ConstructionObject",
    "EpsilonObject",
    "StructureIterator",
    "StructureValue",
    "allstructs",
    "finished",
    "iterstructs",
    "nextstruct",
]
