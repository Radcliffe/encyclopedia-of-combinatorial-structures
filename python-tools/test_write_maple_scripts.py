import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path

from write_maple_scripts import (
    convert_data_to_maple_code,
    convert_gf_to_maple_code,
    fuzzy_match_sequences,
    get_maple_outputs,
    get_oeis_data,
    get_oeis_reference,
    get_structures,
    validate_maple_output,
    write_maple_scripts,
)

from combstruct import Structure

STRUCTURE = Structure(
    id=1,
    name="Sequences",
    description="A test sequence structure",
    specification="{S = Sequence(Z)}",
    labeled=False,
    symbol="S",
    terms=(1, 1, 1),
    references=("EIS A000012",),
    generating_function="1/(1-x)",
)


class MapleToolsTests(unittest.TestCase):
    def write_dataset(self, directory: str) -> Path:
        dataset = Path(directory) / "structures"
        record_path = dataset / "ecs00" / "ecs_0001.json"
        record_path.parent.mkdir(parents=True)
        with record_path.open("w", encoding="utf-8") as output:
            json.dump(STRUCTURE.as_record(), output)
        return dataset

    def test_generates_historical_maple_commands_from_typed_structures(self):
        self.assertEqual(
            convert_data_to_maple_code(STRUCTURE),
            "spec := [S, {S = Sequence(Z)}]: seq(combstruct[count](spec, size = n), n = 0 ..2);\n",
        )
        self.assertEqual(
            convert_data_to_maple_code(replace(STRUCTURE, labeled=True)),
            "spec := [S, {S = Sequence(Z)}, labeled]: "
            "seq(combstruct[count](spec, size = n), n = 0 ..2);\n",
        )
        self.assertEqual(
            convert_gf_to_maple_code(STRUCTURE),
            "lprint(rhs(gfsolve({S = Sequence(Z)}, unlabeled, z)[1]))",
        )
        self.assertEqual(
            convert_gf_to_maple_code(replace(STRUCTURE, labeled=True)),
            "lprint(rhs(gfsolve({S = Sequence(Z)}, labeled, z)[1]))",
        )

    def test_writes_a_catalogue_to_a_selected_output(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = self.write_dataset(directory)
            output = Path(directory) / "maple-script.txt"

            self.assertEqual(list(get_structures(dataset)), [STRUCTURE])
            write_maple_scripts(output, dataset=dataset)

            self.assertEqual(
                output.read_text(encoding="utf-8"),
                convert_data_to_maple_code(STRUCTURE) + "quit;",
            )

    def test_parses_wrapped_maple_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "maple-output.txt"
            output.write_text("1, 2,\n3\n\n4, 5\n", encoding="utf-8")

            self.assertEqual(list(get_maple_outputs(output)), [[1, 2, 3], [4, 5]])

    def test_validates_maple_terms_against_the_catalogue(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = self.write_dataset(directory)
            output = Path(directory) / "maple-output.txt"
            output.write_text("1, 1, 1\n", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                validate_maple_output(output, dataset=dataset)

            output.write_text("1, 2, 3\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()), self.assertRaises(AssertionError):
                validate_maple_output(output, dataset=dataset)

    def test_reads_the_historical_eis_reference(self):
        self.assertEqual(get_oeis_reference(STRUCTURE), "A000012")
        self.assertIsNone(get_oeis_reference(replace(STRUCTURE, references=())))

    def test_reads_and_normalizes_local_oeis_sequence_data(self):
        with tempfile.TemporaryDirectory() as directory:
            sequence_path = Path(directory) / "A000" / "A000012.seq"
            sequence_path.parent.mkdir()
            sequence_path.write_text(
                "%S A000012 0,1,\n%T A000012 2,3\n%N A000012 ignored\n",
                encoding="utf-8",
            )

            self.assertEqual(get_oeis_data("a000012", directory), [0, 1, 2, 3])
            self.assertTrue(fuzzy_match_sequences([0, -1, -2, -3], [0, 1, 2, 3], 1))


if __name__ == "__main__":
    unittest.main()
