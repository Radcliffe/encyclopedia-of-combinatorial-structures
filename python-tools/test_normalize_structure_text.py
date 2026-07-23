import json
import unittest

from normalize_structure_text import (
    WEB_DATA_PATH,
    collect_changes,
    normalize_structure_field,
    normalize_text,
    structure_files,
)


class NormalizeStructureTextTest(unittest.TestCase):
    def test_normalizes_spelling_capitalization_and_punctuation(self):
        self.assertEqual(
            normalize_text("Labelled Non Plane Binary Trees"),
            "Labeled non-plane binary trees",
        )
        self.assertEqual(
            normalize_text("necklaces of 2 colours;Ways to count them."),
            "Necklaces of 2 colors; ways to count them",
        )
        self.assertEqual(normalize_text("Maple Combstruct grammar"), "Maple combstruct grammar")

    def test_standardizes_generating_function_abbreviations(self):
        self.assertEqual(
            normalize_text("Expansion of e.g.f. x/(1-x)"),
            "Expansion of EGF: x/(1-x)",
        )

    def test_preserves_initial_formula_variables(self):
        self.assertEqual(normalize_text("a(n) = 2^n - 2"), "a(n) = 2^n - 2")

    def test_uses_the_structure_universe_for_gf_abbreviations(self):
        structure = {
            "name": "Expansion of e.g.f. 1/(1-x)",
            "labeled": False,
        }

        self.assertEqual(
            normalize_structure_field(structure, "name"),
            "Expansion of OGF: 1/(1-x)",
        )

    def test_canonical_and_web_text_match(self):
        with WEB_DATA_PATH.open(encoding="utf-8") as source:
            web_data = json.load(source)

        canonical_text = {}
        for path in structure_files():
            with path.open(encoding="utf-8") as source:
                structure = json.load(source)
            canonical_text[str(structure["id"])] = (
                structure["name"],
                structure["description"],
            )

        self.assertEqual(
            {
                key: (structure["name"], structure["description"])
                for key, structure in web_data.items()
            },
            canonical_text,
        )

    def test_all_normalizations_have_been_applied(self):
        self.assertEqual(collect_changes(), [])


if __name__ == "__main__":
    unittest.main()
