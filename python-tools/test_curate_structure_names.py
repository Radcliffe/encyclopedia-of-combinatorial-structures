import json
import unittest

from curate_structure_names import (
    WEB_DATA_PATH,
    collect_changes,
    proposed_name,
    structure_files,
)


class CurateStructureNamesTest(unittest.TestCase):
    def test_family_names_include_the_distinguishing_parameter(self):
        arithmetic = {
            'id': 935,
            'name': 'Arithmetic sequence',
            'description': '2 n + 1',
        }
        denumerant = {
            'id': 174,
            'name': 'Denumerant',
            'description': 'number of ways to make n cents with coins of 1 2 5 10 cents',
        }

        self.assertEqual(
            proposed_name(arithmetic),
            'Arithmetic sequence a(n) = 2n + 1',
        )
        self.assertEqual(
            proposed_name(denumerant),
            'Denumerant for coin values 1, 2, 5, 10',
        )

    def test_canonical_and_web_names_match(self):
        with open(WEB_DATA_PATH) as file:
            web_data = json.load(file)

        canonical_names = {}
        for path in structure_files():
            with open(path) as file:
                structure = json.load(file)
            canonical_names[str(structure['id'])] = structure['name']

        self.assertEqual(
            {key: structure['name'] for key, structure in web_data.items()},
            canonical_names,
        )

    def test_all_curated_changes_have_been_applied(self):
        self.assertEqual(collect_changes(), [])


if __name__ == '__main__':
    unittest.main()
