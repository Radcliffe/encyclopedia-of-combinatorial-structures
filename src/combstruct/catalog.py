"""Typed, read-only access to the Encyclopedia of Combinatorial Structures."""

from __future__ import annotations

import importlib.resources
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Literal, Self

GeneratingFunctionType = Literal["ordinary", "exponential"]


class CatalogError(ValueError):
    """The ECS catalogue or one of its records is invalid."""


class StructureNotFoundError(LookupError):
    """The requested ECS identifier is not present in the catalogue."""


@dataclass(frozen=True, slots=True)
class Structure:
    """One immutable record from the Encyclopedia of Combinatorial Structures.

    Symbolic results are stored as their original ECS strings. A missing
    generating function, recurrence, closed form, or asymptotic equivalent is
    represented by ``None``.
    """

    id: int
    name: str
    description: str
    specification: str
    labeled: bool
    symbol: str
    terms: tuple[int, ...]
    references: tuple[str, ...]
    generating_function: str | None = None
    recurrence: str | None = None
    closed_form: str | None = None
    asymptotic_equivalent: str | None = None
    generating_function_type: GeneratingFunctionType | None = None

    def __post_init__(self) -> None:
        if self.generating_function is None:
            if self.generating_function_type is not None:
                raise CatalogError("A generating function type requires a generating function")
            return

        expected: GeneratingFunctionType = "exponential" if self.labeled else "ordinary"
        if self.generating_function_type is None:
            object.__setattr__(self, "generating_function_type", expected)
        elif self.generating_function_type != expected:
            raise CatalogError(
                f"Generating function type must be {expected!r} when labeled is {self.labeled!r}",
            )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> Self:
        """Create a structure from a canonical or web-encoded ECS record."""

        structure_id = _integer(record, "id")
        if structure_id <= 0:
            raise CatalogError("ECS field 'id' must be positive")

        labeled = record.get("labeled")
        if not isinstance(labeled, bool):
            raise CatalogError("ECS field 'labeled' must be a boolean")

        generating_function = _optional_string(record, "gf")
        generating_function_type = _generating_function_type(
            record,
            generating_function=generating_function,
            labeled=labeled,
        )

        return cls(
            id=structure_id,
            name=_nonempty_string(record, "name"),
            description=_nonempty_string(record, "description"),
            specification=_nonempty_string(record, "specification"),
            labeled=labeled,
            symbol=_nonempty_string(record, "symbol"),
            terms=_terms(record),
            references=_references(record),
            generating_function=generating_function,
            generating_function_type=generating_function_type,
            recurrence=_optional_string(record, "rec"),
            closed_form=_optional_string(record, "closedform"),
            asymptotic_equivalent=_optional_string(record, "equiv"),
        )

    def as_record(self) -> dict[str, Any]:
        """Return a canonical mutable record using the ECS source field names."""

        record: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "specification": self.specification,
            "labeled": self.labeled,
            "symbol": self.symbol,
            "terms": list(self.terms),
            "references": list(self.references),
        }
        optional_fields = {
            "gf_type": self.generating_function_type,
            "gf": self.generating_function,
            "rec": self.recurrence,
            "closedform": self.closed_form,
            "equiv": self.asymptotic_equivalent,
        }
        record.update((name, value) for name, value in optional_fields.items() if value is not None)
        return record


class Catalog:
    """A lazy, read-only collection of ECS structures.

    ``dataset`` may be either the package's directory of canonical record files
    or the historical consolidated JSON mapping used by the web application.
    Omitting it selects the appropriate source for the current installation.
    """

    def __init__(self, dataset: str | Path | None = None):
        self.dataset = Path(dataset) if dataset is not None else _default_catalog_dataset()
        self._cache: dict[int, Structure] = {}

    @cached_property
    def ids(self) -> tuple[int, ...]:
        """All available ECS identifiers in increasing order."""

        if self.dataset.is_dir():
            identifiers = tuple(
                sorted(
                    int(path.stem.removeprefix("ecs_")) for path in self.dataset.glob("ecs*/*.json")
                ),
            )
        else:
            identifiers = tuple(sorted(int(key) for key in self._record_mapping))

        if len(identifiers) != len(set(identifiers)):
            raise CatalogError(f"Duplicate ECS identifiers in {self.dataset}")
        return identifiers

    @cached_property
    def _record_mapping(self) -> Mapping[str, Mapping[str, Any]]:
        if not self.dataset.is_file():
            raise CatalogError(f"ECS dataset does not exist: {self.dataset}")
        with self.dataset.open(encoding="utf-8") as source:
            records = json.load(source)
        if not isinstance(records, dict):
            raise CatalogError(f"Expected an ECS record mapping in {self.dataset}")
        return records

    def __len__(self) -> int:
        return len(self.ids)

    def __iter__(self) -> Iterator[Structure]:
        for structure_id in self.ids:
            yield self.get(structure_id)

    def __contains__(self, structure_id: object) -> bool:
        return (
            isinstance(structure_id, int)
            and not isinstance(structure_id, bool)
            and structure_id in self.ids
        )

    def get(self, structure_id: int) -> Structure:
        """Return one structure by ECS identifier."""

        if not isinstance(structure_id, int) or isinstance(structure_id, bool):
            raise TypeError("structure_id must be an integer")
        if structure_id in self._cache:
            return self._cache[structure_id]

        if self.dataset.is_dir():
            record = _load_record(self.dataset, structure_id)
        else:
            try:
                stored_record = self._record_mapping[str(structure_id)]
            except KeyError as error:
                raise StructureNotFoundError(
                    f"No ECS structure #{structure_id} in {self.dataset}",
                ) from error
            if not isinstance(stored_record, Mapping):
                raise CatalogError(f"ECS structure #{structure_id} is not a JSON object")
            record = dict(stored_record)

        structure = Structure.from_record(record)
        if structure.id != structure_id:
            raise CatalogError(
                f"ECS record #{structure_id} contains identifier {structure.id}",
            )
        self._cache[structure_id] = structure
        return structure


def _integer(record: Mapping[str, Any], field: str) -> int:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise CatalogError(f"ECS field {field!r} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise CatalogError(f"ECS field {field!r} must be an integer") from error
    if isinstance(value, float) and not value.is_integer():
        raise CatalogError(f"ECS field {field!r} must be an integer")
    return result


def _nonempty_string(record: Mapping[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise CatalogError(f"ECS field {field!r} must be a nonempty string")
    return value


def _optional_string(record: Mapping[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise CatalogError(f"ECS field {field!r} must be a nonempty string when present")
    return value


def _generating_function_type(
    record: Mapping[str, Any],
    *,
    generating_function: str | None,
    labeled: bool,
) -> GeneratingFunctionType | None:
    value = record.get("gf_type")
    if generating_function is None:
        if value is not None:
            raise CatalogError("ECS field 'gf_type' requires field 'gf'")
        return None

    expected: GeneratingFunctionType = "exponential" if labeled else "ordinary"
    # Historical consolidated datasets did not carry gf_type. Keep them
    # readable while ensuring all newly serialized records are explicit.
    if value is None:
        return expected
    if value == "ordinary":
        result: GeneratingFunctionType = "ordinary"
    elif value == "exponential":
        result = "exponential"
    else:
        raise CatalogError("ECS field 'gf_type' must be 'ordinary' or 'exponential'")
    if result != expected:
        raise CatalogError(
            f"ECS field 'gf_type' must be {expected!r} when 'labeled' is {labeled!r}",
        )
    return result


def _terms(record: Mapping[str, Any]) -> tuple[int, ...]:
    values = record.get("terms")
    if not isinstance(values, list):
        raise CatalogError("ECS field 'terms' must be a list")
    terms = tuple(_integer({"term": value}, "term") for value in values)
    if any(term < 0 for term in terms):
        raise CatalogError("ECS terms must be nonnegative")
    return terms


def _references(record: Mapping[str, Any]) -> tuple[str, ...]:
    values = record.get("references")
    if not isinstance(values, list) or not all(
        isinstance(value, str) and value for value in values
    ):
        raise CatalogError("ECS field 'references' must be a list of nonempty strings")
    return tuple(values)


def default_dataset() -> Path:
    """Return the legacy repository or installed-package ECS data location."""

    repository_dataset = Path(__file__).resolve().parents[2] / "react-app" / "public" / "ecs.json"
    if repository_dataset.is_file():
        return repository_dataset

    packaged_dataset = importlib.resources.files("combstruct").joinpath("data")
    return Path(str(packaged_dataset))


def _default_catalog_dataset() -> Path:
    """Return canonical per-record data for the typed catalogue API."""

    repository_dataset = Path(__file__).resolve().parents[2] / "structures"
    if repository_dataset.is_dir():
        return repository_dataset

    packaged_dataset = importlib.resources.files("combstruct").joinpath("data")
    return Path(str(packaged_dataset))


def _load_record(dataset: Path, structure_id: int) -> dict[str, Any]:
    """Load one raw ECS record from a directory or consolidated JSON file."""

    if not isinstance(structure_id, int) or isinstance(structure_id, bool):
        raise TypeError("structure_id must be an integer")

    if dataset.is_dir():
        record_path = dataset / f"ecs{structure_id // 100:02d}" / f"ecs_{structure_id:04d}.json"
        try:
            with record_path.open(encoding="utf-8") as source:
                record = json.load(source)
        except FileNotFoundError as error:
            raise StructureNotFoundError(
                f"No ECS structure #{structure_id} in {dataset}",
            ) from error
    else:
        if not dataset.is_file():
            raise CatalogError(f"ECS dataset does not exist: {dataset}")
        with dataset.open(encoding="utf-8") as source:
            records = json.load(source)
        if not isinstance(records, dict):
            raise CatalogError(f"Expected an ECS record mapping in {dataset}")
        try:
            record = records[str(structure_id)]
        except KeyError as error:
            raise StructureNotFoundError(
                f"No ECS structure #{structure_id} in {dataset}",
            ) from error

    if not isinstance(record, dict):
        raise CatalogError(f"ECS structure #{structure_id} is not a JSON object")
    return record


_DEFAULT_CATALOG = Catalog()


def get_structure(structure_id: int) -> Structure:
    """Return one structure from the bundled ECS catalogue."""

    return _DEFAULT_CATALOG.get(structure_id)


def iter_structures() -> Iterator[Structure]:
    """Iterate over the bundled ECS catalogue in identifier order."""

    return iter(_DEFAULT_CATALOG)
