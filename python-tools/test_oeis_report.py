import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from main import get_oeis_ref, load_ecs_data, main, missing_gf

from combstruct import Structure

ROOT = Path(__file__).resolve().parents[1]
WEB_DATA = ROOT / "react-app" / "public" / "ecs.json"


def web_record(
    structure_id: int,
    *,
    name: str,
    description: str,
    references: list[str],
    gf: str | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "id": structure_id,
        "name": name,
        "description": description,
        "specification": "{S = Sequence(Z)}",
        "labeled": False,
        "symbol": "S",
        "terms": ["1", "1", "1"],
        "references": references,
    }
    if gf is not None:
        record["gf"] = gf
    return record


class OeisReportTests(unittest.TestCase):
    def test_web_catalogue_loads_as_typed_structures(self):
        structures = load_ecs_data(WEB_DATA)

        self.assertEqual(len(structures), 1075)
        self.assertIsInstance(structures["1"], Structure)
        self.assertEqual(structures["1"].terms[:4], (0, 1, 0, 0))

    def test_missing_gf_matches_historical_web_report(self):
        output = io.StringIO()
        with redirect_stdout(output):
            missing = missing_gf(WEB_DATA)

        self.assertEqual(len(missing), 58)
        self.assertEqual(
            missing[:5],
            [
                (1, "A000598"),
                (43, "A001190"),
                (44, "A000669"),
                (45, "A001190"),
                (56, "A004111"),
            ],
        )
        self.assertEqual(missing[-1], (869, "A052893"))
        self.assertEqual(output.getvalue().strip(), str(missing))

    def test_get_oeis_ref_uses_first_eis_reference(self):
        structure = Structure.from_record(
            web_record(
                1,
                name="Example",
                description="Example",
                references=["Book reference", "EIS A42", "EIS A99"],
            ),
        )

        self.assertEqual(get_oeis_ref(structure), "A42")

    def test_writes_historical_reports_from_typed_records(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            dataset = temporary / "ecs.json"
            names = temporary / "oeis-names.txt"
            csv_output = temporary / "ecs-oeis.csv"
            json_output = temporary / "augmented.json"
            dataset.write_text(
                json.dumps(
                    {
                        "1": web_record(
                            1,
                            name="FAIL",
                            description="FAIL",
                            references=["EIS A42"],
                        ),
                        "2": web_record(
                            2,
                            name="No reference",
                            description="No reference",
                            references=[],
                            gf="1/(1-x)",
                        ),
                    },
                ),
                encoding="utf-8",
            )
            names.write_text("A000042 The answer.\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                main(dataset, names, csv_output, json_output)

            self.assertIn("No EIS for 2: [1, 1, 1]", output.getvalue())
            self.assertIn("Wrote 2 rows to ecs-oeis.csv", output.getvalue())
            self.assertEqual(
                csv_output.read_text(encoding="utf-8").splitlines()[0],
                "ECS ID,OEIS ID,Description,Terms",
            )
            augmented = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(augmented["1"]["name"], "The answer")
            self.assertEqual(augmented["1"]["description"], "The answer")
            self.assertEqual(augmented["1"]["terms"], [1, 1, 1])


if __name__ == "__main__":
    unittest.main()
