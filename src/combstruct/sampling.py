"""Exact count-directed sampling for combinatorial grammars."""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
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
    """A grammar requires a symmetry-aware sampler not implemented here."""


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
        if (
            not self.labelled
            and name in {"set", "powerset"}
            and self._contains_unrankable_cycle(expression.arguments[0], set())
        ):
            raise UnsupportedCountDirectedSampling(
                f"Count-directed {expression.name} sampling cannot yet unrank "
                "component types containing an unlabeled Cycle",
            )
        for argument in expression.arguments:
            self._require_supported_expression(argument, active)

    def _contains_unrankable_cycle(
        self,
        expression: Expression,
        active: set[str],
    ) -> bool:
        if isinstance(expression, Reference):
            if expression.name not in self.equations or expression.name in active:
                return False
            active.add(expression.name)
            result = self._contains_unrankable_cycle(
                self.equations[expression.name],
                active,
            )
            active.remove(expression.name)
            return result
        if expression.name.lower() == "cycle":
            return True
        return any(
            self._contains_unrankable_cycle(argument, active)
            for argument in expression.arguments
        )

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
                group_ways = (
                    math.comb(type_count, chosen)
                    if distinct
                    else (
                        1
                        if chosen == 0
                        else math.comb(type_count + chosen - 1, chosen)
                    )
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
            weights = [
                self._count_expression(argument, size)
                for argument in expression.arguments
            ]
            branch = _weighted_index(weights, self.rng)
            child = self._sample_expression(expression.arguments[branch], size, labels)
            return ConstructionObject("Union", (child,), branch=branch)
        if name == "prod":
            children = self._sample_ordered_product(expression.arguments, size, labels)
            return ConstructionObject("Prod", children)

        component = expression.arguments[0]
        if not self.labelled and name in {"set", "powerset"}:
            total = self._count_expression(expression, size)
            return self._unrank_expression(
                expression,
                size,
                self.rng.randrange(total),
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
            rotations = {
                children[offset:] + children[:offset]
                for offset in range(count)
            }
            orbit_size = len(rotations)
            if self.rng.randrange(orbit_size) == 0:
                return ConstructionObject("Cycle", _canonical_cycle(children))

    def _unrank_symbol(
        self,
        symbol: str,
        size: int,
        rank: int,
    ) -> CombinatorialObject:
        expression = self.equations[symbol]
        if expression == Reference("Epsilon") and size == 0:
            if rank:
                raise IndexError("object rank is out of range")
            return EpsilonObject(symbol)
        return self._unrank_expression(expression, size, rank)

    def _unrank_expression(
        self,
        expression: Expression,
        size: int,
        rank: int,
    ) -> CombinatorialObject:
        total = self._count_expression(expression, size)
        if rank < 0 or rank >= total:
            raise IndexError("object rank is out of range")
        if isinstance(expression, Reference):
            if expression.name == "Epsilon":
                return EpsilonObject()
            if expression.name in {"Atom", "Z"} and expression.name not in self.equations:
                return AtomObject()
            return self._unrank_symbol(expression.name, size, rank)

        name = expression.name.lower()
        if name == "union":
            for branch, argument in enumerate(expression.arguments):
                branch_count = self._count_expression(argument, size)
                if rank < branch_count:
                    return ConstructionObject(
                        "Union",
                        (self._unrank_expression(argument, size, rank),),
                        branch=branch,
                    )
                rank -= branch_count
            raise AssertionError("union rank was not consumed")
        if name == "prod":
            children = self._unrank_ordered_product(
                expression.arguments,
                size,
                rank,
            )
            return ConstructionObject("Prod", children)
        if name == "sequence":
            component = expression.arguments[0]
            for count, weight in self._collection_weights(
                name,
                component,
                expression.cardinality,
                size,
            ):
                if rank < weight:
                    return ConstructionObject(
                        "Sequence",
                        self._unrank_ordered_product(
                            (component,) * count,
                            size,
                            rank,
                        ),
                    )
                rank -= weight
            raise AssertionError("sequence rank was not consumed")
        if name in {"set", "powerset"} and not self.labelled:
            return self._unrank_selection(
                expression.arguments[0],
                expression.cardinality,
                size,
                rank,
                distinct=name == "powerset",
            )
        raise UnsupportedCountDirectedSampling(
            f"Unranking {expression.name} is not implemented",
        )

    def _unrank_ordered_product(
        self,
        arguments: tuple[Expression, ...],
        size: int,
        rank: int,
    ) -> tuple[CombinatorialObject, ...]:
        for sizes in _weak_compositions(size, len(arguments)):
            counts = tuple(
                self._count_expression(argument, child_size)
                for argument, child_size in zip(arguments, sizes, strict=True)
            )
            weight = math.prod(counts)
            if rank >= weight:
                rank -= weight
                continue
            child_ranks: list[int] = []
            for count in reversed(counts):
                child_ranks.append(rank % count)
                rank //= count
            child_ranks.reverse()
            return tuple(
                self._unrank_expression(argument, child_size, child_rank)
                for argument, child_size, child_rank in zip(
                    arguments,
                    sizes,
                    child_ranks,
                    strict=True,
                )
            )
        raise AssertionError("product rank was not consumed")

    def _unrank_selection(
        self,
        component: Expression,
        cardinality: Cardinality | None,
        size: int,
        rank: int,
        *,
        distinct: bool,
    ) -> ConstructionObject:
        minimum = cardinality.minimum if cardinality is not None else 0
        maximum = (
            cardinality.maximum
            if cardinality is not None and cardinality.maximum is not None
            else size
        )
        selected_count: int | None = None
        for count in range(minimum, maximum + 1):
            ways = self._selection_exact_count(
                component,
                size,
                count,
                distinct=distinct,
            )
            if rank < ways:
                selected_count = count
                break
            rank -= ways
        if selected_count is None:
            raise AssertionError("selection cardinality rank was not consumed")

        remaining_size = size
        remaining_count = selected_count
        component_size = 1
        ranked_groups: list[tuple[int, tuple[int, ...]]] = []
        while remaining_size or remaining_count:
            type_count = self._count_expression(component, component_size)
            limit = min(remaining_count, remaining_size // component_size)
            if distinct:
                limit = min(limit, type_count)
            selected = False
            for chosen in range(limit + 1):
                group_ways = (
                    math.comb(type_count, chosen)
                    if distinct
                    else (
                        1
                        if chosen == 0
                        else math.comb(type_count + chosen - 1, chosen)
                    )
                )
                suffix_ways = self._selection_exact_count(
                    component,
                    remaining_size - chosen * component_size,
                    remaining_count - chosen,
                    distinct=distinct,
                    component_size=component_size + 1,
                )
                block = group_ways * suffix_ways
                if rank < block:
                    group_rank, rank = divmod(rank, suffix_ways)
                    type_ranks = self._unrank_type_selection(
                        type_count,
                        chosen,
                        group_rank,
                        distinct=distinct,
                    )
                    ranked_groups.append((component_size, type_ranks))
                    remaining_size -= chosen * component_size
                    remaining_count -= chosen
                    selected = True
                    break
                rank -= block
            if not selected:
                raise AssertionError("selection multiplicity rank was not consumed")
            component_size += 1

        children = tuple(
            self._unrank_expression(component, child_size, child_rank)
            for child_size, type_ranks in ranked_groups
            for child_rank in type_ranks
        )
        constructor = "PowerSet" if distinct else "Set"
        return ConstructionObject(constructor, _canonical_children(children))

    @staticmethod
    def _unrank_type_selection(
        type_count: int,
        chosen: int,
        rank: int,
        *,
        distinct: bool,
    ) -> tuple[int, ...]:
        if not distinct:
            shifted = CountDirectedSampler._unrank_combination(
                type_count + chosen - 1,
                chosen,
                rank,
            )
            return tuple(value - index for index, value in enumerate(shifted))
        return CountDirectedSampler._unrank_combination(type_count, chosen, rank)

    @staticmethod
    def _unrank_combination(
        population: int,
        chosen: int,
        rank: int,
    ) -> tuple[int, ...]:
        if chosen == 0:
            if rank:
                raise IndexError("combination rank is out of range")
            return ()
        result: list[int] = []
        start = 0
        for remaining in range(chosen, 0, -1):
            for value in range(start, population - remaining + 1):
                suffixes = math.comb(population - value - 1, remaining - 1)
                if rank < suffixes:
                    result.append(value)
                    start = value + 1
                    break
                rank -= suffixes
            else:
                raise IndexError("combination rank is out of range")
        return tuple(result)

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
