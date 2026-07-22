"""Generate Maple inputs and validate Maple or OEIS sequence outputs."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from combstruct import Catalog, Structure

PROJECT_DIR = Path(__file__).resolve().parents[1]
MAPLE_SCRIPT_PATH = Path(__file__).with_name("maple_script.txt")
MAPLE_OUTPUT_PATH = Path(__file__).with_name("maple_output.txt")
OEIS_DATA_DIR = PROJECT_DIR / "oeisdata" / "seq"


def get_structures(dataset: str | Path | None = None) -> Iterator[Structure]:
    """Iterate over ECS structures through the public catalogue API."""

    return iter(Catalog(dataset))


def convert_data_to_maple_code(structure: Structure) -> str:
    """Return the historical Maple term-counting command for one structure."""

    labeled = ", labeled" if structure.labeled else ""
    max_size = len(structure.terms) - 1
    return (
        f"spec := [{structure.symbol}, {structure.specification}{labeled}]: "
        f"seq(combstruct[count](spec, size = n), n = 0 ..{max_size});\n"
    )


def convert_gf_to_maple_code(structure: Structure) -> str:
    """Return the historical Maple generating-function command."""

    universe = "labeled" if structure.labeled else "unlabeled"
    return f"lprint(rhs(gfsolve({structure.specification}, {universe}, z)[1]))"


def write_maple_scripts(
    output_path: str | Path = MAPLE_SCRIPT_PATH,
    *,
    dataset: str | Path | None = None,
) -> None:
    """Write term-counting commands for every structure and a final quit command."""

    with Path(output_path).open("w", encoding="utf-8", newline="\n") as output:
        for structure in get_structures(dataset):
            output.write(convert_data_to_maple_code(structure))
        output.write("quit;")


def get_maple_outputs(output_path: str | Path = MAPLE_OUTPUT_PATH) -> Iterator[list[int]]:
    """Yield comma-separated Maple result rows, including wrapped rows."""

    current = ""
    with Path(output_path).open(encoding="utf-8") as output:
        for line in output:
            line = line.strip()
            if not line:
                continue
            current += " " + line
            if not current.endswith(","):
                yield [int(term) for term in current.split(",")]
                current = ""


def validate_maple_output(
    output_path: str | Path = MAPLE_OUTPUT_PATH,
    *,
    dataset: str | Path | None = None,
) -> None:
    """Assert that Maple output matches stored terms in ECS identifier order."""

    for expected_id, (maple_terms, structure) in enumerate(
        zip(get_maple_outputs(output_path), get_structures(dataset), strict=False),
        1,
    ):
        assert expected_id == structure.id
        stored_terms = list(structure.terms)
        print(f"{expected_id}: {maple_terms} ")
        print(f"{expected_id}: {stored_terms}")
        assert maple_terms == stored_terms


def main() -> None:
    """Validate the checked-in Maple output against the default catalogue."""

    validate_maple_output()


def get_oeis_reference(structure: Structure) -> str | None:
    """Return the first historical EIS reference, if present."""

    for reference in structure.references:
        if reference.startswith("EIS "):
            return reference[len("EIS ") :]
    return None


def get_oeis_data(oeis_id: str, oeis_data_dir: str | Path = OEIS_DATA_DIR) -> list[int]:
    """Read sequence terms from a local OEIS internal-format file."""

    normalized_id = oeis_id.upper()
    prefix = normalized_id[:4]
    filename = Path(oeis_data_dir) / prefix / f"{normalized_id}.seq"
    serialized_terms = ""
    with filename.open(encoding="utf-8") as text_file:
        for line in text_file:
            row = line.split(" ", maxsplit=3)
            if len(row) == 3 and row[0] in ("%S", "%T", "%U"):
                serialized_terms += row[2]
    return [int(term) for term in serialized_terms.split(",")]


def match_sequences(oeis_sequence: Sequence[int], ecs_sequence: Sequence[int]) -> bool:
    """Compare equally long nonzero prefixes, ignoring the size-zero term."""

    length = min(len(oeis_sequence), len(ecs_sequence))
    return oeis_sequence[1:length] == ecs_sequence[1:length]


def remove_zeros(sequence: Iterable[int]) -> list[int]:
    """Return a copy of a sequence with all zero entries removed."""

    return [term for term in sequence if term != 0]


def fuzzy_match_sequences(
    oeis_sequence: Sequence[int],
    ecs_sequence: Sequence[int],
    ecs_id: int,
) -> bool:
    """Apply the historical sign, zero, and small-offset sequence comparison."""

    del ecs_id  # Retained for compatibility with the historical call signature.
    normalized_oeis = [abs(term) for term in remove_zeros(oeis_sequence)]
    normalized_ecs = remove_zeros(ecs_sequence)
    return (
        match_sequences(normalized_oeis, normalized_ecs)
        or match_sequences(normalized_oeis[1:], normalized_ecs)
        or match_sequences(normalized_oeis, normalized_ecs[1:])
        or match_sequences(normalized_oeis, normalized_ecs[2:])
        or match_sequences(normalized_oeis[2:], normalized_ecs)
        or match_sequences(normalized_oeis[1:], normalized_ecs[1:])
    )


def validate_sequences(
    *,
    dataset: str | Path | None = None,
    oeis_data_dir: str | Path = OEIS_DATA_DIR,
) -> None:
    """Report ECS records whose stored terms do not resemble their OEIS sequence."""

    bad_sequences = []
    for structure in get_structures(dataset):
        oeis_id = get_oeis_reference(structure)
        if oeis_id is None:
            print(f"ECS {structure.id} skipped")
            continue
        oeis_terms = get_oeis_data(oeis_id, oeis_data_dir)
        if not fuzzy_match_sequences(oeis_terms, structure.terms, structure.id):
            print(f"ECS {structure.id} does not match {oeis_id}")
            print(f"seq2={list(structure.terms)}")
            print("-" * 120)
            bad_sequences.append(structure.id)

    print(f"{len(bad_sequences)} sequences failed: {bad_sequences}")


if __name__ == "__main__":
    validate_sequences()
