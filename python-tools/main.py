"""Build OEIS reports from the ECS web catalogue.

This historical script keeps its original filename and default behavior while
using the public :mod:`combstruct` catalogue API for record loading.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from combstruct import Catalog, Structure

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
WEB_DATA_PATH = PROJECT_DIR / "react-app" / "public" / "ecs.json"
OEIS_NAMES_PATH = SCRIPT_DIR / "oeis-names.txt"
OEIS_CSV_PATH = SCRIPT_DIR / "ecs-oeis.csv"
AUGMENTED_DATA_PATH = SCRIPT_DIR / "ecs-augmented-with-oeis-names.json"


def load_ecs_data(dataset: str | Path = WEB_DATA_PATH) -> dict[str, Structure]:
    """Load the web catalogue as typed structures keyed by ECS identifier."""

    return {str(structure.id): structure for structure in Catalog(dataset)}


def load_oeis_names(path: str | Path = OEIS_NAMES_PATH) -> dict[str, str]:
    """Load the local OEIS identifier-to-name mapping."""

    with Path(path).open(encoding="utf-8") as names_file:
        return dict(line.strip().rstrip(".").split(" ", 1) for line in names_file)


def test_load_oeis_names(path: str | Path = OEIS_NAMES_PATH) -> None:
    """Print one historical spot check retained for interactive use."""

    oeis_names = load_oeis_names(path)
    print(oeis_names["A000217"])


def get_oeis_ref(structure: Structure) -> str:
    """Return the first legacy EIS reference, or ``MISSING``."""

    for reference in structure.references:
        if reference.startswith("EIS "):
            return reference[4:]
    return "MISSING"


def missing_gf(dataset: str | Path = WEB_DATA_PATH) -> list[tuple[int, str]]:
    """Print and return ECS identifiers whose web records lack a GF."""

    missing = [
        (structure.id, get_oeis_ref(structure))
        for structure in load_ecs_data(dataset).values()
        if structure.generating_function is None
    ]
    print(missing)
    return missing


def main(
    dataset: str | Path = WEB_DATA_PATH,
    oeis_names_path: str | Path = OEIS_NAMES_PATH,
    csv_path: str | Path = OEIS_CSV_PATH,
    augmented_data_path: str | Path = AUGMENTED_DATA_PATH,
) -> None:
    """Write the historical OEIS CSV and name-augmented JSON reports."""

    structures = load_ecs_data(dataset)
    oeis_names = load_oeis_names(oeis_names_path)
    rows: list[tuple[int, str | None, str, str]] = []
    augmented_data: dict[str, dict[str, object]] = {}

    for key, structure in structures.items():
        record = structure.as_record()
        oeis_id = None
        for reference in structure.references:
            if reference.startswith("EIS "):
                oeis_id = reference.removeprefix("EIS ")
                full_oeis_id = "A" + oeis_id[1:].zfill(6)
                oeis_name = oeis_names[full_oeis_id]
                if structure.name == "FAIL":
                    record["name"] = oeis_name
                if structure.description == "FAIL":
                    record["description"] = oeis_name
                break
        else:
            print(f"No EIS for {structure.id}: {list(structure.terms)}")

        rows.append(
            (
                structure.id,
                oeis_id,
                structure.description,
                str(list(structure.terms))[1:-1],
            ),
        )
        augmented_data[key] = record

    if rows:
        with Path(csv_path).open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(("ECS ID", "OEIS ID", "Description", "Terms"))
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {Path(csv_path).name}")

    with Path(augmented_data_path).open("w", encoding="utf-8") as output:
        json.dump(augmented_data, output, indent=2)


if __name__ == "__main__":
    missing_gf()
