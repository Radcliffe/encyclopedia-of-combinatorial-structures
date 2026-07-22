import json
import tempfile
import unittest
from pathlib import Path

from compute_terms import default_dataset
from generate_bfiles import bfile_name, format_bfile, generate_bfiles


ROOT = Path(__file__).resolve().parents[1]
BFILE_DIRECTORY = ROOT / "react-app" / "public" / "b-files"


class BFileTests(unittest.TestCase):
    def test_name_and_format_follow_oeis_conventions(self):
        self.assertEqual(bfile_name(42), "b000042.txt")
        self.assertEqual(format_bfile([0, 1, 4, 9]), "0 0\n1 1\n2 4\n3 9\n")

    def test_generates_a_selected_record(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            results = generate_bfiles(
                default_dataset(),
                output,
                max_index=4,
                max_digits=1000,
                selected_ids={6},
            )

            self.assertEqual(results, [(6, 5, 21)])
            self.assertEqual(
                (output / "b000006.txt").read_text(encoding="ascii"),
                "0 1\n1 2\n2 4\n3 8\n4 16\n",
            )

    def test_checked_in_bfiles_cover_the_catalogue(self):
        with default_dataset().open(encoding="utf-8") as source:
            records = json.load(source)

        expected_names = {bfile_name(record["id"]) for record in records.values()}
        actual_names = {path.name for path in BFILE_DIRECTORY.glob("b*.txt")}
        self.assertEqual(actual_names, expected_names)

        for record in records.values():
            path = BFILE_DIRECTORY / bfile_name(record["id"])
            stored_terms = [str(term) for term in record["terms"]]
            bfile_terms = []
            with path.open(encoding="ascii") as source:
                for expected_index, line in enumerate(source):
                    index, term = line.rstrip("\n").split(" ", 1)
                    self.assertEqual(int(index), expected_index, path.name)
                    self.assertLessEqual(len(term.lstrip("-")), 1000, path.name)
                    bfile_terms.append(term)

            self.assertLessEqual(len(bfile_terms), 1001, path.name)
            self.assertEqual(bfile_terms[: len(stored_terms)], stored_terms, path.name)


if __name__ == "__main__":
    unittest.main()
