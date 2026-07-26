import json
import unittest

from combine_json_files import (
    STRUCTURES_DIR,
    WEB_DATA_PATH,
    decode_from_web,
    encode_for_web,
    validate_json,
)


class EncodeForWebTest(unittest.TestCase):
    def test_generating_function_type_is_explicit_and_matches_labeled_semantics(self):
        validate_json(
            {
                "id": 1,
                "name": "Example",
                "description": "Example structure",
                "specification": "{S = Z}",
                "labeled": True,
                "symbol": "S",
                "terms": [0, 1],
                "references": [],
                "gf_type": "exponential",
                "gf": "_x",
            }
        )

        with self.assertRaisesRegex(ValueError, "GF type"):
            validate_json(
                {
                    "id": 1,
                    "name": "Example",
                    "description": "Example structure",
                    "specification": "{S = Z}",
                    "labeled": True,
                    "symbol": "S",
                    "terms": [0, 1],
                    "references": [],
                    "gf_type": "ordinary",
                    "gf": "_x",
                }
            )

    def test_terms_are_decimal_strings_without_mutating_source(self):
        large_term = 2363718092885120596738042023955660800000
        source = {"id": 693, "terms": [0, large_term]}

        encoded = encode_for_web(source)

        self.assertEqual(encoded["terms"], ["0", str(large_term)])
        self.assertEqual(source["terms"], [0, large_term])

    def test_checked_in_web_terms_round_trip_exactly(self):
        with open(WEB_DATA_PATH) as file:
            web_data = json.load(file)

        canonical_records = {}
        for path in STRUCTURES_DIR.glob("*/*.json"):
            with open(path) as file:
                structure = json.load(file)
            canonical_records[str(structure["id"])] = structure

        self.assertEqual(web_data.keys(), canonical_records.keys())
        for key, structure in web_data.items():
            canonical = canonical_records[key]
            self.assertTrue(all(isinstance(term, str) for term in structure["terms"]))
            self.assertEqual(
                decode_from_web(structure)["terms"],
                canonical["terms"],
            )
            self.assertEqual("gf" in canonical, "gf_type" in canonical)
            self.assertEqual(structure.get("gf_type"), canonical.get("gf_type"))
            if "gf" in canonical:
                expected = "exponential" if canonical["labeled"] else "ordinary"
                self.assertEqual(canonical["gf_type"], expected)


if __name__ == "__main__":
    unittest.main()
