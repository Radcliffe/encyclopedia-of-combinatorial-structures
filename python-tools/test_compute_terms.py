import json
import unittest
from pathlib import Path

from compute_terms import Cardinality, Constructor, Parser, Reference, compute_terms, decimal_digit_count


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "react-app" / "public" / "ecs.json"


class ParserTests(unittest.TestCase):
    def test_parses_indexed_symbols_and_cardinality(self):
        equations = Parser(
            "{S = Set(A[1],1 <= card), A[1] = Sequence(Z,card <= 2)}",
        ).parse()

        self.assertEqual(
            equations["S"],
            Constructor("Set", (Reference("A[1]"),), Cardinality(1, None)),
        )
        self.assertEqual(
            equations["A[1]"],
            Constructor("Sequence", (Reference("Z"),), Cardinality(0, 2)),
        )


class ComputationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with DATASET.open(encoding="utf-8") as source:
            cls.records = json.load(source)

    def assert_record_prefix(self, structure_id, term_count=12):
        record = self.records[str(structure_id)]
        actual = compute_terms(
            record["specification"],
            labelled=record["labeled"],
            term_count=term_count,
            symbol=record["symbol"],
        )
        expected = [int(term) for term in record["terms"][:term_count]]
        self.assertEqual(actual[: len(expected)], expected)

    def test_representative_ecs_records(self):
        for structure_id in (1, 2, 6, 15, 20, 56, 291):
            with self.subTest(structure_id=structure_id):
                self.assert_record_prefix(structure_id)

    def test_recursive_catalan_specification(self):
        terms = compute_terms(
            "{S = Union(Epsilon,Prod(Z,S,S))}",
            labelled=False,
            term_count=12,
        )
        self.assertEqual(
            terms,
            [1, 1, 2, 5, 14, 42, 132, 429, 1430, 4862, 16796, 58786],
        )

    def test_stops_before_digit_limit_is_exceeded(self):
        terms = compute_terms(
            "{S = Sequence(Union(a,b)), a = Atom, b = Atom}",
            labelled=False,
            term_count=1001,
            max_digits=3,
        )
        self.assertEqual(terms[-1], 512)
        self.assertEqual(len(terms), 10)
        self.assertEqual(decimal_digit_count(terms[-1]), 3)

    def test_every_ecs_record_matches_its_stored_prefix(self):
        for record in self.records.values():
            with self.subTest(structure_id=record["id"]):
                term_count = min(10, len(record["terms"]))
                actual = compute_terms(
                    record["specification"],
                    labelled=record["labeled"],
                    term_count=term_count,
                    symbol=record["symbol"],
                )
                self.assertEqual(actual, [int(term) for term in record["terms"][:term_count]])


if __name__ == "__main__":
    unittest.main()
