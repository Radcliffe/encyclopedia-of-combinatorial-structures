"""Exact count-directed sampling for combinatorial grammars."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from itertools import pairwise
from random import Random
from typing import Literal

from .enumeration import (
    AtomObject,
    CombinatorialObject,
    ConstructionObject,
    EpsilonObject,
    _canonical_children,
    _canonical_cycle,
)
from .specification import (
    Cardinality,
    Expression,
    Reference,
    SpecificationError,
    expand_substitutions,
)
from .terms import (
    CoefficientCompiler,
    UnsupportedConstruction,
    euler_totient,
    integer_value,
)

type DrawAlgorithm = Literal["auto", "counted", "enumerate"]


class UnsupportedCountDirectedSampling(UnsupportedConstruction):
    """A grammar cannot use the exact count-directed sampler."""


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


def _multinomial(total: int, parts: tuple[int, ...]) -> int:
    result = 1
    remaining = total
    for part in parts:
        result *= math.comb(remaining, part)
        remaining -= part
    return result


def _weighted_index(weights: list[int], rng: Random) -> int:
    total = sum(weights)
    if total <= 0:
        raise LookupError("No positive-weight choice exists")
    rank = rng.randrange(total)
    for index, weight in enumerate(weights):
        if rank < weight:
            return index
        rank -= weight
    raise AssertionError("weighted choice rank was not consumed")


class CountDirectedSampler:
    """Sample supported grammar objects using exact constructor counts."""

    def __init__(
        self,
        equations: Mapping[str, Expression],
        *,
        labelled: bool,
        size: int,
        rng: Random,
    ):
        self.equations = expand_substitutions(equations)
        self.labelled = labelled
        self.size = size
        self.rng = rng
        self.compiler = CoefficientCompiler(dict(self.equations), size, labelled)
        self.count_cache: dict[tuple[Expression, int], int] = {}
        self.selection_cache: dict[tuple[Expression, int, int, bool, int], int] = {}

    def sample(self, symbol: str) -> CombinatorialObject:
        if symbol not in self.equations:
            raise SpecificationError(f"Specification does not define {symbol!r}")
        self._require_supported_symbol(symbol, set())
        counts = self.compiler.compute(symbol)
        if integer_value(counts[self.size]) == 0:
            raise LookupError("No objects exist at the requested size")
        labels = tuple(range(1, self.size + 1)) if self.labelled else None
        return self._sample_symbol(symbol, self.size, labels)

    def _require_supported_symbol(self, symbol: str, active: set[str]) -> None:
        if symbol in active:
            return
        active.add(symbol)
        self._require_supported_expression(self.equations[symbol], active)
        active.remove(symbol)

    def _require_supported_expression(
        self,
        expression: Expression,
        active: set[str],
    ) -> None:
        if isinstance(expression, Reference):
            if expression.name in self.equations:
                self._require_supported_symbol(expression.name, active)
            return
        name = expression.name.lower()
        if name == "powerset" and self.labelled:
            raise UnsupportedCountDirectedSampling(
                "PowerSet is only defined for unlabeled structures",
            )
        for argument in expression.arguments:
            self._require_supported_expression(argument, active)

    def _count_expression(self, expression: Expression, size: int) -> int:
        key = (expression, size)
        if key in self.count_cache:
            return self.count_cache[key]
        result = self._uncached_count_expression(expression, size)
        self.count_cache[key] = result
        return result

    def _uncached_count_expression(self, expression: Expression, size: int) -> int:
        if isinstance(expression, Reference):
            if expression.name == "Epsilon":
                return int(size == 0)
            if expression.name in {"Atom", "Z"} and expression.name not in self.equations:
                return int(size == 1)
            try:
                value = self.compiler.roots[expression.name].coefficients[size]
            except KeyError as error:
                raise SpecificationError(f"Undefined symbol {expression.name!r}") from error
            return integer_value(value)

        name = expression.name.lower()
        if name == "union":
            return sum(self._count_expression(argument, size) for argument in expression.arguments)
        if name == "prod":
            return self._ordered_product_count(expression.arguments, size)
        if len(expression.arguments) != 1:
            raise SpecificationError(f"{expression.name} requires exactly one component argument")
        component = expression.arguments[0]
        weights = self._collection_weights(
            name,
            component,
            expression.cardinality,
            size,
        )
        return sum(weight for _, weight in weights)

    def _ordered_product_count(
        self,
        arguments: tuple[Expression, ...],
        size: int,
    ) -> int:
        total = 0
        for sizes in _weak_compositions(size, len(arguments)):
            weight = _multinomial(size, sizes) if self.labelled else 1
            for argument, child_size in zip(arguments, sizes, strict=True):
                weight *= self._count_expression(argument, child_size)
                if not weight:
                    break
            total += weight
        return total

    def _collection_weights(
        self,
        name: str,
        component: Expression,
        cardinality: Cardinality | None,
        size: int,
    ) -> list[tuple[int, int]]:
        if name not in {"sequence", "set", "cycle", "powerset"}:
            raise UnsupportedCountDirectedSampling(
                f"Count-directed {name} sampling is not implemented",
            )
        minimum = 1 if name == "cycle" else 0
        if cardinality is not None:
            minimum = max(minimum, cardinality.minimum)
        if cardinality is None or cardinality.maximum is None:
            if self._count_expression(component, 0):
                raise UnsupportedCountDirectedSampling(
                    f"Unrestricted {name} cannot be sampled with a size-zero component",
                )
            maximum = size
        else:
            maximum = cardinality.maximum
        if name in {"set", "cycle", "powerset"} and self._count_expression(component, 0):
            raise UnsupportedCountDirectedSampling(
                f"Count-directed {name} sampling requires positive-size components",
            )

        result: list[tuple[int, int]] = []
        for count in range(minimum, maximum + 1):
            if not self.labelled and name == "cycle":
                weight = self._unlabelled_cycle_fixed_count(
                    component,
                    size,
                    count,
                )
            elif not self.labelled and name in {"set", "powerset"}:
                weight = self._selection_exact_count(
                    component,
                    size,
                    count,
                    distinct=name == "powerset",
                )
            else:
                weight = self._ordered_product_count((component,) * count, size)
                if name == "set":
                    weight //= math.factorial(count)
                elif name == "cycle" and count:
                    weight //= count
            if weight:
                result.append((count, weight))
        return result

    def _unlabelled_cycle_fixed_count(
        self,
        component: Expression,
        total_size: int,
        count: int,
    ) -> int:
        if count <= 0:
            return 0
        numerator = 0
        for divisor in range(1, count + 1):
            if count % divisor or total_size % divisor:
                continue
            numerator += euler_totient(divisor) * self._ordered_product_count(
                (component,) * (count // divisor),
                total_size // divisor,
            )
        quotient, remainder = divmod(numerator, count)
        if remainder:
            raise AssertionError("cycle-index count is not integral")
        return quotient

    def _selection_exact_count(
        self,
        component: Expression,
        total_size: int,
        count: int,
        *,
        distinct: bool,
        component_size: int = 1,
    ) -> int:
        key = (component, total_size, count, distinct, component_size)
        if key in self.selection_cache:
            return self.selection_cache[key]
        if component_size > total_size:
            result = int(total_size == 0 and count == 0)
        else:
            type_count = self._count_expression(component, component_size)
            limit = min(count, total_size // component_size)
            if distinct:
                limit = min(limit, type_count)
            result = 0
            for chosen in range(limit + 1):
                group_ways = self._type_selection_count(
                    type_count,
                    chosen,
                    distinct=distinct,
                )
                if group_ways:
                    result += group_ways * self._selection_exact_count(
                        component,
                        total_size - chosen * component_size,
                        count - chosen,
                        distinct=distinct,
                        component_size=component_size + 1,
                    )
        self.selection_cache[key] = result
        return result

    def _sample_symbol(
        self,
        symbol: str,
        size: int,
        labels: tuple[int, ...] | None,
    ) -> CombinatorialObject:
        expression = self.equations[symbol]
        if expression == Reference("Epsilon") and size == 0:
            return EpsilonObject(symbol)
        return self._sample_expression(expression, size, labels)

    def _sample_expression(
        self,
        expression: Expression,
        size: int,
        labels: tuple[int, ...] | None,
    ) -> CombinatorialObject:
        if isinstance(expression, Reference):
            if expression.name == "Epsilon":
                if size != 0:
                    raise AssertionError("selected Epsilon at nonzero size")
                return EpsilonObject()
            if expression.name in {"Atom", "Z"} and expression.name not in self.equations:
                if size != 1:
                    raise AssertionError("selected atom at size other than one")
                label = labels[0] if labels is not None else None
                return AtomObject(label)
            return self._sample_symbol(expression.name, size, labels)

        name = expression.name.lower()
        if name == "union":
            weights = [self._count_expression(argument, size) for argument in expression.arguments]
            branch = _weighted_index(weights, self.rng)
            child = self._sample_expression(expression.arguments[branch], size, labels)
            return ConstructionObject("Union", (child,), branch=branch)
        if name == "prod":
            children = self._sample_ordered_product(expression.arguments, size, labels)
            return ConstructionObject("Prod", children)

        component = expression.arguments[0]
        if not self.labelled and name in {"set", "powerset"}:
            return self._sample_unlabelled_selection(
                component,
                expression.cardinality,
                size,
                distinct=name == "powerset",
            )
        choices = self._collection_weights(
            name,
            component,
            expression.cardinality,
            size,
        )
        choice = _weighted_index([weight for _, weight in choices], self.rng)
        count = choices[choice][0]
        if name == "cycle" and not self.labelled:
            return self._sample_unlabelled_cycle(component, count, size)
        children = self._sample_ordered_product((component,) * count, size, labels)
        if name == "sequence":
            return ConstructionObject("Sequence", children)
        if name == "set":
            return ConstructionObject("Set", _canonical_children(children))
        if name == "cycle":
            return ConstructionObject("Cycle", _canonical_cycle(children))
        raise AssertionError("unsupported collection passed validation")

    def _sample_unlabelled_cycle(
        self,
        component: Expression,
        count: int,
        size: int,
    ) -> ConstructionObject:
        while True:
            children = self._sample_ordered_product(
                (component,) * count,
                size,
                None,
            )
            rotations = {children[offset:] + children[:offset] for offset in range(count)}
            orbit_size = len(rotations)
            if self.rng.randrange(orbit_size) == 0:
                return ConstructionObject("Cycle", _canonical_cycle(children))

    def _sample_unlabelled_selection(
        self,
        component: Expression,
        cardinality: Cardinality | None,
        size: int,
        *,
        distinct: bool,
    ) -> CombinatorialObject:
        name = "powerset" if distinct else "set"
        cardinality_choices = self._collection_weights(
            name,
            component,
            cardinality,
            size,
        )
        selected_count = cardinality_choices[
            _weighted_index(
                [weight for _, weight in cardinality_choices],
                self.rng,
            )
        ][0]

        remaining_size = size
        remaining_count = selected_count
        component_size = 1
        children: list[CombinatorialObject] = []
        while remaining_size or remaining_count:
            type_count = self._count_expression(component, component_size)
            limit = min(remaining_count, remaining_size // component_size)
            if distinct:
                limit = min(limit, type_count)
            choices: list[tuple[int, int]] = []
            for chosen in range(limit + 1):
                group_ways = self._type_selection_count(
                    type_count,
                    chosen,
                    distinct=distinct,
                )
                suffix_ways = self._selection_exact_count(
                    component,
                    remaining_size - chosen * component_size,
                    remaining_count - chosen,
                    distinct=distinct,
                    component_size=component_size + 1,
                )
                if group_ways and suffix_ways:
                    choices.append((chosen, group_ways * suffix_ways))
            choice = _weighted_index(
                [weight for _, weight in choices],
                self.rng,
            )
            chosen = choices[choice][0]
            children.extend(
                self._sample_type_selection(
                    component,
                    component_size,
                    type_count,
                    chosen,
                    distinct=distinct,
                ),
            )
            remaining_size -= chosen * component_size
            remaining_count -= chosen
            component_size += 1

        constructor = "PowerSet" if distinct else "Set"
        return ConstructionObject(constructor, _canonical_children(tuple(children)))

    @staticmethod
    def _type_selection_count(
        type_count: int,
        chosen: int,
        *,
        distinct: bool,
    ) -> int:
        if distinct:
            return math.comb(type_count, chosen)
        if chosen == 0:
            return 1
        return math.comb(type_count + chosen - 1, chosen)

    def _sample_type_selection(
        self,
        component: Expression,
        component_size: int,
        type_count: int,
        chosen: int,
        *,
        distinct: bool,
    ) -> tuple[CombinatorialObject, ...]:
        if chosen == 0:
            return ()
        if distinct:
            return self._sample_distinct_component_types(
                component,
                component_size,
                chosen,
            )

        support_choices = [
            (
                support,
                math.comb(type_count, support) * math.comb(chosen - 1, support - 1),
            )
            for support in range(1, min(type_count, chosen) + 1)
        ]
        support = support_choices[
            _weighted_index(
                [weight for _, weight in support_choices],
                self.rng,
            )
        ][0]
        selected_types = self._sample_distinct_component_types(
            component,
            component_size,
            support,
        )
        separators = sorted(self.rng.sample(range(1, chosen), support - 1))
        boundaries = (0, *separators, chosen)
        multiplicities = tuple(right - left for left, right in pairwise(boundaries))
        return tuple(
            selected_type
            for selected_type, multiplicity in zip(
                selected_types,
                multiplicities,
                strict=True,
            )
            for _ in range(multiplicity)
        )

    def _sample_distinct_component_types(
        self,
        component: Expression,
        component_size: int,
        chosen: int,
    ) -> tuple[CombinatorialObject, ...]:
        selected: set[CombinatorialObject] = set()
        while len(selected) < chosen:
            selected.add(
                self._sample_expression(
                    component,
                    component_size,
                    None,
                ),
            )
        return _canonical_children(tuple(selected))

    def _sample_ordered_product(
        self,
        arguments: tuple[Expression, ...],
        size: int,
        labels: tuple[int, ...] | None,
    ) -> tuple[CombinatorialObject, ...]:
        compositions: list[tuple[int, ...]] = []
        weights: list[int] = []
        for sizes in _weak_compositions(size, len(arguments)):
            weight = _multinomial(size, sizes) if self.labelled else 1
            for argument, child_size in zip(arguments, sizes, strict=True):
                weight *= self._count_expression(argument, child_size)
                if not weight:
                    break
            if weight:
                compositions.append(sizes)
                weights.append(weight)
        selected = compositions[_weighted_index(weights, self.rng)]
        label_blocks = self._partition_labels(labels, selected)
        return tuple(
            self._sample_expression(argument, child_size, child_labels)
            for argument, child_size, child_labels in zip(
                arguments,
                selected,
                label_blocks,
                strict=True,
            )
        )

    def _partition_labels(
        self,
        labels: tuple[int, ...] | None,
        sizes: tuple[int, ...],
    ) -> tuple[tuple[int, ...] | None, ...]:
        if labels is None:
            return (None,) * len(sizes)
        remaining = list(labels)
        blocks: list[tuple[int, ...]] = []
        for size in sizes:
            selected = tuple(sorted(self.rng.sample(remaining, size)))
            selected_set = set(selected)
            remaining = [label for label in remaining if label not in selected_set]
            blocks.append(selected)
        return tuple(blocks)


__all__ = [
    "CountDirectedSampler",
    "DrawAlgorithm",
    "UnsupportedCountDirectedSampling",
]
