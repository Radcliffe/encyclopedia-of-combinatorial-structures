"""Normalize ECS structure names and descriptions without altering their meaning."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
STRUCTURES_DIR = PROJECT_DIR / "structures"
WEB_DATA_PATH = PROJECT_DIR / "react-app" / "public" / "ecs.json"

AMERICAN_SPELLINGS = {
    "labelled": "labeled",
    "unlabelled": "unlabeled",
    "colour": "color",
    "colours": "colors",
}

# Common nouns that occur title-cased in the historical data even when they
# appear in the middle of a sentence. Proper names, acronyms, and variables
# are intentionally absent.
COMMON_WORDS = {
    "Acyclic",
    "Balls",
    "Binary",
    "Connected",
    "Cycles",
    "Each",
    "Forest",
    "Functional",
    "General",
    "Generalized",
    "Labeled",
    "Non",
    "Numbers",
    "Permutations",
    "Plane",
    "Preferential",
    "Repeat",
    "Sequences",
    "Sets",
    "Sometimes",
    "Ternary",
    "This",
    "Trees",
    "Unlabeled",
    "Urns",
    "Ways",
}

UNAMBIGUOUS_REPLACEMENTS = {
    "parenthezing": "parenthesizing",
}


def _replace_word(text: str, old: str, new: str) -> str:
    pattern = re.compile(rf"\b{re.escape(old)}\b", flags=re.IGNORECASE)

    def replacement(match: re.Match[str]) -> str:
        value = match.group()
        if value.isupper():
            return new.upper()
        if value[:1].isupper():
            return new.capitalize()
        return new

    return pattern.sub(replacement, text)


def _is_sentence_start(text: str, start: int) -> bool:
    prefix = text[:start]
    return not prefix.strip() or re.search(r"[.!?]\s+\(?$", prefix) is not None


def _lowercase_historical_title_words(text: str) -> str:
    pattern = re.compile(r"\b(?:" + "|".join(sorted(COMMON_WORDS)) + r")\b")

    def replacement(match: re.Match[str]) -> str:
        if _is_sentence_start(text, match.start()):
            return match.group()
        return match.group().lower()

    return pattern.sub(replacement, text)


def _capitalize_initial_prose(text: str) -> str:
    # Mathematical expressions conventionally begin with a lowercase variable.
    if re.match(r"^[a-z]\s*(?:\([^)]*\)|[=^!])", text):
        return text
    match = re.match(r"""^["'(]*([a-z])""", text)
    if match is None:
        return text
    index = match.start(1)
    return text[:index] + text[index].upper() + text[index + 1 :]


def normalize_text(text: str) -> str:
    """Return normalized ECS prose while preserving formulas and proper names."""

    result = re.sub(r"\s+", " ", text.strip())

    for old, new in AMERICAN_SPELLINGS.items():
        result = _replace_word(result, old, new)
    for old, new in UNAMBIGUOUS_REPLACEMENTS.items():
        result = _replace_word(result, old, new)
    result = result.replace("Combstruct", "combstruct")

    result = re.sub(r"\be\.+g\.f\.", "EGF", result, flags=re.IGNORECASE)
    result = re.sub(r"\bo\.g\.f\.", "OGF", result, flags=re.IGNORECASE)
    result = re.sub(r"\bg\.f\.", "GF", result, flags=re.IGNORECASE)
    result = re.sub(r"\bnon[\s-]+plane\b", "non-plane", result, flags=re.IGNORECASE)
    result = re.sub(r"\bn thing\b", "n things", result, flags=re.IGNORECASE)

    result = re.sub(r"\s+([,;:!?])", r"\1", result)
    result = re.sub(r",(?=\S)", ", ", result)
    result = re.sub(r";(?=\S)", "; ", result)
    result = re.sub(r":(?=[A-Za-z])", ": ", result)
    result = re.sub(r"(?<=[A-Za-z)])\.(?=[A-Za-z(])", ". ", result)
    result = re.sub(r"\b(EGF|OGF|GF)(?!:)(?=\s+[A-Za-z0-9_[\](+\-])", r"\1:", result)
    result = re.sub(r"\b(EGF|OGF): (equals|is|satisfies)\b", r"\1 \2", result)

    result = _lowercase_historical_title_words(result)
    result = _capitalize_initial_prose(result)
    return result.rstrip(" ,;:").removesuffix(".").strip()


def normalize_structure_field(structure: dict[str, object], field: str) -> str:
    """Normalize one field and use the record's universe for GF abbreviations."""

    result = normalize_text(str(structure[field]))
    abbreviation = "EGF" if structure["labeled"] else "OGF"
    return re.sub(r"\b(?:EGF|OGF|GF)\b", abbreviation, result)


def structure_files() -> list[Path]:
    return sorted(STRUCTURES_DIR.glob("ecs*/*.json"))


def collect_changes() -> list[tuple[Path, int, str, str, str]]:
    changes = []
    for path in structure_files():
        with path.open(encoding="utf-8") as source:
            structure = json.load(source)
        for field in ("name", "description"):
            old_text = structure[field]
            new_text = normalize_structure_field(structure, field)
            if new_text != old_text:
                changes.append((path, structure["id"], field, old_text, new_text))
    return changes


def replace_field(path: Path, field: str, old_text: str, new_text: str) -> None:
    serialized = path.read_text(encoding="utf-8")
    old_field = f'"{field}": {json.dumps(old_text, ensure_ascii=False)}'
    new_field = f'"{field}": {json.dumps(new_text, ensure_ascii=False)}'
    if serialized.count(old_field) != 1:
        raise ValueError(f"Expected exactly one {field} field in {path}")
    path.write_text(serialized.replace(old_field, new_field, 1), encoding="utf-8")


def update_web_data(changes: list[tuple[Path, int, str, str, str]]) -> None:
    with WEB_DATA_PATH.open(encoding="utf-8") as source:
        web_data = json.load(source)
    for _, structure_id, field, old_text, new_text in changes:
        record = web_data[str(structure_id)]
        if record[field] != old_text:
            raise ValueError(
                f"Unexpected web {field} for ECS {structure_id}: {record[field]!r}",
            )
        record[field] = new_text
    with WEB_DATA_PATH.open("w", encoding="utf-8") as output:
        json.dump(web_data, output, indent=2)
        output.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize punctuation, capitalization, and American spelling in ECS prose.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Apply changes to canonical structure files and the web dataset.",
    )
    arguments = parser.parse_args()

    changes = collect_changes()
    for _, structure_id, field, old_text, new_text in changes:
        print(f"ECS {structure_id} {field}: {old_text} -> {new_text}")
    print(f"{len(changes)} fields would be changed.")

    if arguments.write:
        for path, _, field, old_text, new_text in changes:
            replace_field(path, field, old_text, new_text)
        update_web_data(changes)
        print("Changes written.")


if __name__ == "__main__":
    main()
