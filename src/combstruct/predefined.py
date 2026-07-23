"""Maple ``combstruct`` predefined finite structure families."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Hashable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from functools import cache
from itertools import combinations as choose_items
from itertools import permutations as permute_items
from random import Random
from typing import Literal, TypeGuard

type StructureSize = int | Literal["allsizes"] | None
type PredefinedObject = tuple[Hashable, ...] | tuple[int, ...]


def _item_key(item: Hashable) -> tuple[str, str, str]:
    item_type = type(item)
    return (item_type.__module__, item_type.__qualname__, repr(item))


def _elements(source: int | Iterable[Hashable], *, structure: str) -> tuple[Hashable, ...]:
    if isinstance(source, bool):
        raise TypeError(f"{structure} elements must be an integer, list, set, or iterable")
    if isinstance(source, int):
        if source < 0:
            raise ValueError(f"{structure} integer argument must be nonnegative")
        return tuple(range(1, source + 1))
    if isinstance(source, (str, bytes)):
        raise TypeError(f"{structure} elements must not be text")
    try:
        result = tuple(source)
    except TypeError as error:
        raise TypeError(
            f"{structure} elements must be an integer, list, set, or iterable"
        ) from error
    if not all(isinstance(item, Hashable) for item in result):
        raise TypeError(f"{structure} elements must be hashable")
    if isinstance(source, (set, frozenset)):
        return tuple(sorted(result, key=_item_key))
    return result


@dataclass(frozen=True, init=False)
class Combination:
    """Combinations/subsets drawn from a finite collection."""

    elements: tuple[Hashable, ...]

    def __init__(self, elements: int | Iterable[Hashable]):
        object.__setattr__(self, "elements", _elements(elements, structure="Combination"))


Subset = Combination


@dataclass(frozen=True, init=False)
class Permutation:
    """Partial or full permutations of a finite collection."""

    elements: tuple[Hashable, ...]

    def __init__(self, elements: int | Iterable[Hashable]):
        object.__setattr__(self, "elements", _elements(elements, structure="Permutation"))


def _positive_integer(value: int, *, structure: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{structure} argument must be a positive integer")
    if value <= 0:
        raise ValueError(f"{structure} argument must be a positive integer")
    return value


@dataclass(frozen=True)
class Partition:
    """Integer partitions of ``total`` classified by number of parts."""

    total: int

    def __post_init__(self) -> None:
        _positive_integer(self.total, structure="Partition")


@dataclass(frozen=True)
class Composition:
    """Integer compositions of ``total`` classified by number of parts."""

    total: int

    def __post_init__(self) -> None:
        _positive_integer(self.total, structure="Composition")


type PredefinedStructure = Combination | Permutation | Partition | Composition


def is_predefined(value: object) -> TypeGuard[PredefinedStructure]:
    """Return whether ``value`` is one of the predefined structure families."""

    return isinstance(value, (Combination, Permutation, Partition, Composition))


def _validate_size(size: StructureSize) -> None:
    if size is None or size == "allsizes":
        return
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be a nonnegative integer, 'allsizes', or None")
    if size < 0:
        raise ValueError("size must be nonnegative")


def structure_sizes(
    structure: PredefinedStructure,
    size: StructureSize,
) -> range | tuple[int]:
    """Resolve Maple's per-structure default and ``allsizes`` behavior."""

    _validate_size(size)
    maximum = (
        len(structure.elements)
        if isinstance(structure, (Combination, Permutation))
        else structure.total
    )
    if size is None and isinstance(structure, Permutation):
        return (maximum,)
    if size is None or size == "allsizes":
        start = 0 if isinstance(structure, (Combination, Permutation)) else 1
        return range(start, maximum + 1)
    return (size,)


def _multiplicities(elements: tuple[Hashable, ...]) -> tuple[int, ...]:
    return tuple(Counter(elements).values())


def _combination_count(elements: tuple[Hashable, ...], size: int) -> int:
    if size < 0 or size > len(elements):
        return 0
    counts = [0] * (size + 1)
    counts[0] = 1
    for available in _multiplicities(elements):
        updated = [0] * (size + 1)
        for old_size, old_count in enumerate(counts):
            for chosen in range(min(available, size - old_size) + 1):
                updated[old_size + chosen] += old_count
        counts = updated
    return counts[size]


def _multiplicity_vectors(
    multiplicities: tuple[int, ...],
    size: int,
    index: int = 0,
) -> Iterator[tuple[int, ...]]:
    if index == len(multiplicities):
        if size == 0:
            yield ()
        return
    for chosen in range(min(multiplicities[index], size) + 1):
        for rest in _multiplicity_vectors(multiplicities, size - chosen, index + 1):
            yield (chosen, *rest)


def _permutation_count(elements: tuple[Hashable, ...], size: int) -> int:
    if size < 0 or size > len(elements):
        return 0
    result = 0
    factorial = math.factorial(size)
    for counts in _multiplicity_vectors(_multiplicities(elements), size):
        denominator = math.prod(math.factorial(count) for count in counts)
        result += factorial // denominator
    return result


def _partition_count(total: int, parts: int) -> int:
    if parts <= 0 or parts > total:
        return 0
    table = [[0] * (parts + 1) for _ in range(total + 1)]
    table[0][0] = 1
    for summand in range(1, total + 1):
        for subtotal in range(summand, total + 1):
            for count in range(1, parts + 1):
                table[subtotal][count] += table[subtotal - summand][count - 1]
    return table[total][parts]


def count_predefined(
    structure: PredefinedStructure,
    *,
    size: StructureSize = None,
) -> int:
    """Count one predefined family using Maple's size conventions."""

    sizes = structure_sizes(structure, size)
    if isinstance(structure, Combination):
        return sum(_combination_count(structure.elements, part_count) for part_count in sizes)
    if isinstance(structure, Permutation):
        return sum(_permutation_count(structure.elements, part_count) for part_count in sizes)
    if isinstance(structure, Partition):
        return sum(_partition_count(structure.total, part_count) for part_count in sizes)
    if isinstance(structure, Composition):
        return sum(
            math.comb(structure.total - 1, part_count - 1)
            for part_count in sizes
            if 1 <= part_count <= structure.total
        )
    raise TypeError("structure must be a predefined structure")


def _partitions(
    total: int,
    parts: int,
    maximum: int | None = None,
) -> Iterator[tuple[int, ...]]:
    if parts == 0:
        if total == 0:
            yield ()
        return
    limit = min(total - parts + 1, total if maximum is None else maximum)
    for first in range(limit, 0, -1):
        for rest in _partitions(total - first, parts - 1, first):
            yield (first, *rest)


def _compositions(total: int, parts: int) -> Iterator[tuple[int, ...]]:
    if parts == 0:
        if total == 0:
            yield ()
        return
    if parts == 1:
        if total >= 1:
            yield (total,)
        return
    for first in range(1, total - parts + 2):
        for rest in _compositions(total - first, parts - 1):
            yield (first, *rest)


def enumerate_predefined(
    structure: PredefinedStructure,
    *,
    size: StructureSize = None,
) -> tuple[PredefinedObject, ...]:
    """Return all objects in one predefined structure family."""

    result: list[PredefinedObject] = []
    for object_size in structure_sizes(structure, size):
        if isinstance(structure, Combination):
            result.extend(sorted(set(choose_items(structure.elements, object_size)), key=repr))
        elif isinstance(structure, Permutation):
            result.extend(sorted(set(permute_items(structure.elements, object_size)), key=repr))
        elif isinstance(structure, Partition):
            result.extend(_partitions(structure.total, object_size))
        elif isinstance(structure, Composition):
            result.extend(_compositions(structure.total, object_size))
        else:
            raise TypeError("structure must be a predefined structure")
    return tuple(result)


def _weighted_choice[T](values: Sequence[tuple[T, int]], rng: Random) -> T:
    total = sum(weight for _, weight in values)
    if total <= 0:
        raise LookupError("No objects exist for the requested predefined size")
    rank = rng.randrange(total)
    for value, weight in values:
        if rank < weight:
            return value
        rank -= weight
    raise AssertionError("weighted choice rank was not consumed")


def _distinct_groups(
    elements: tuple[Hashable, ...],
) -> tuple[tuple[Hashable, int], ...]:
    counts = Counter(elements)
    return tuple(counts.items())


def _sample_combination(
    elements: tuple[Hashable, ...],
    size: int,
    rng: Random,
) -> PredefinedObject:
    groups = _distinct_groups(elements)

    @cache
    def suffix_count(index: int, remaining: int) -> int:
        if index == len(groups):
            return int(remaining == 0)
        return sum(
            suffix_count(index + 1, remaining - chosen)
            for chosen in range(min(groups[index][1], remaining) + 1)
        )

    chosen_counts: list[int] = []
    remaining = size
    for index, (_, available) in enumerate(groups):
        options = [
            (chosen, suffix_count(index + 1, remaining - chosen))
            for chosen in range(min(available, remaining) + 1)
        ]
        chosen = _weighted_choice(options, rng)
        assert isinstance(chosen, int)
        chosen_counts.append(chosen)
        remaining -= chosen
    if remaining:
        raise LookupError("No combination exists at the requested size")
    return tuple(
        item
        for (item, _), chosen in zip(groups, chosen_counts, strict=True)
        for _ in range(chosen)
    )


def _sample_permutation(
    elements: tuple[Hashable, ...],
    size: int,
    rng: Random,
) -> PredefinedObject:
    groups = _distinct_groups(elements)
    vectors = [
        (
            counts,
            math.factorial(size)
            // math.prod(math.factorial(count) for count in counts),
        )
        for counts in _multiplicity_vectors(
            tuple(available for _, available in groups),
            size,
        )
    ]
    selected = _weighted_choice(vectors, rng)
    assert isinstance(selected, tuple)
    remaining = list(selected)
    result: list[Hashable] = []
    for _ in range(size):
        index = _weighted_choice(
            [
                (index, count)
                for index, count in enumerate(remaining)
                if count
            ],
            rng,
        )
        assert isinstance(index, int)
        result.append(groups[index][0])
        remaining[index] -= 1
    return tuple(result)


def _sample_partition(
    total: int,
    parts: int,
    rng: Random,
) -> tuple[int, ...]:
    @cache
    def completions(remaining: int, count: int, maximum: int) -> int:
        if count == 0:
            return int(remaining == 0)
        limit = min(maximum, remaining - count + 1)
        return sum(
            completions(remaining - first, count - 1, first)
            for first in range(1, limit + 1)
        )

    remaining = total
    maximum = total
    result: list[int] = []
    for remaining_parts in range(parts, 0, -1):
        limit = min(maximum, remaining - remaining_parts + 1)
        first = _weighted_choice(
            [
                (
                    candidate,
                    completions(
                        remaining - candidate,
                        remaining_parts - 1,
                        candidate,
                    ),
                )
                for candidate in range(1, limit + 1)
            ],
            rng,
        )
        assert isinstance(first, int)
        result.append(first)
        remaining -= first
        maximum = first
    return tuple(result)


def _sample_composition(
    total: int,
    parts: int,
    rng: Random,
) -> tuple[int, ...]:
    if parts <= 0 or parts > total:
        raise LookupError("No composition exists at the requested size")
    separators = sorted(rng.sample(range(1, total), parts - 1))
    boundaries = (0, *separators, total)
    return tuple(
        boundaries[index + 1] - boundaries[index]
        for index in range(parts)
    )


def sample_predefined(
    structure: PredefinedStructure,
    *,
    size: StructureSize,
    rng: Random,
) -> PredefinedObject:
    """Sample one predefined object without exhaustive materialization."""

    sizes = tuple(structure_sizes(structure, size))
    object_size = _weighted_choice(
        [
            (
                candidate,
                count_predefined(structure, size=candidate),
            )
            for candidate in sizes
        ],
        rng,
    )
    assert isinstance(object_size, int)
    if isinstance(structure, Combination):
        return _sample_combination(structure.elements, object_size, rng)
    if isinstance(structure, Permutation):
        return _sample_permutation(structure.elements, object_size, rng)
    if isinstance(structure, Partition):
        return _sample_partition(structure.total, object_size, rng)
    if isinstance(structure, Composition):
        return _sample_composition(structure.total, object_size, rng)
    raise TypeError("structure must be a predefined structure")


__all__ = [
    "Combination",
    "Composition",
    "Partition",
    "Permutation",
    "PredefinedObject",
    "PredefinedStructure",
    "StructureSize",
    "Subset",
    "count_predefined",
    "enumerate_predefined",
    "is_predefined",
    "sample_predefined",
    "structure_sizes",
]
