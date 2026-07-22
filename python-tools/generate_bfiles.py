#!/usr/bin/env python3
"""Generate OEIS-style b-files for ECS records."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
from typing import Iterable

from compute_terms import compute_terms, default_dataset


def bfile_name(structure_id: int) -> str:
    return f"b{structure_id:06d}.txt"


def format_bfile(terms: Iterable[int]) -> str:
    return "".join(f"{index} {term}\n" for index, term in enumerate(terms))


def generate_record(task: tuple[dict, str, int, int]) -> tuple[int, int, int]:
    record, output_directory, max_index, max_digits = task
    terms = compute_terms(
        record["specification"],
        labelled=bool(record["labeled"]),
        term_count=max_index + 1,
        symbol=record.get("symbol") or "S",
        max_digits=max_digits,
    )

    destination = Path(output_directory) / bfile_name(record["id"])
    temporary = destination.with_suffix(".tmp")
    text = format_bfile(terms)
    temporary.write_text(text, encoding="ascii")
    temporary.replace(destination)
    return record["id"], len(terms), len(text)


def load_records(dataset: Path, selected_ids: set[int] | None = None) -> list[dict]:
    with dataset.open(encoding="utf-8") as source:
        records = json.load(source)
    selected = [
        record
        for record in records.values()
        if selected_ids is None or record["id"] in selected_ids
    ]
    return sorted(selected, key=lambda record: record["id"])


def generate_bfiles(
    dataset: Path,
    output_directory: Path,
    *,
    max_index: int = 1000,
    max_digits: int = 1000,
    jobs: int = 1,
    selected_ids: set[int] | None = None,
) -> list[tuple[int, int, int]]:
    output_directory.mkdir(parents=True, exist_ok=True)
    records = load_records(dataset, selected_ids)
    tasks = [
        (record, str(output_directory), max_index, max_digits)
        for record in records
    ]

    if jobs == 1:
        results = [generate_record(task) for task in tasks]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(generate_record, tasks, chunksize=1))
    return sorted(results)


def default_output_directory() -> Path:
    return Path(__file__).resolve().parents[1] / "react-app" / "public" / "b-files"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=default_dataset())
    parser.add_argument("--output", type=Path, default=default_output_directory())
    parser.add_argument("--max-index", type=int, default=1000)
    parser.add_argument("--max-digits", type=int, default=1000)
    parser.add_argument(
        "--jobs",
        type=int,
        default=min(4, os.cpu_count() or 1),
        help="worker processes (default: up to 4)",
    )
    parser.add_argument("--id", type=int, action="append", dest="ids", help="generate only this ECS id")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)
    if arguments.max_index < 0:
        raise SystemExit("error: --max-index must be nonnegative")
    if arguments.max_digits <= 0:
        raise SystemExit("error: --max-digits must be positive")
    if arguments.jobs <= 0:
        raise SystemExit("error: --jobs must be positive")

    results = generate_bfiles(
        arguments.dataset,
        arguments.output,
        max_index=arguments.max_index,
        max_digits=arguments.max_digits,
        jobs=arguments.jobs,
        selected_ids=set(arguments.ids) if arguments.ids else None,
    )
    total_bytes = sum(size for _, _, size in results)
    shortest = min((term_count for _, term_count, _ in results), default=0)
    longest = max((term_count for _, term_count, _ in results), default=0)
    print(
        f"Generated {len(results)} b-files in {arguments.output} "
        f"({total_bytes:,} bytes; {shortest}-{longest} terms per file).",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
