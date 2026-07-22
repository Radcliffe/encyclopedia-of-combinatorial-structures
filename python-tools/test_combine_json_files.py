import json
import unittest

from combine_json_files import (
    STRUCTURES_DIR,
    WEB_DATA_PATH,
    decode_from_web,
    encode_for_web,
)


class EncodeForWebTest(unittest.TestCase):
    def test_terms_are_decimal_strings_without_mutating_source(self):
        large_term = 2363718092885120596738042023955660800000
        source = {'id': 693, 'terms': [0, large_term]}

        encoded = encode_for_web(source)

        self.assertEqual(encoded['terms'], ['0', str(large_term)])
        self.assertEqual(source['terms'], [0, large_term])

    def test_checked_in_web_terms_round_trip_exactly(self):
        with open(WEB_DATA_PATH) as file:
            web_data = json.load(file)

        canonical_terms = {}
        for path in STRUCTURES_DIR.glob('*/*.json'):
            with open(path) as file:
                structure = json.load(file)
            canonical_terms[str(structure['id'])] = structure['terms']

        self.assertEqual(web_data.keys(), canonical_terms.keys())
        for key, structure in web_data.items():
            self.assertTrue(all(isinstance(term, str) for term in structure['terms']))
            self.assertEqual(
                decode_from_web(structure)['terms'],
                canonical_terms[key],
            )


if __name__ == '__main__':
    unittest.main()
