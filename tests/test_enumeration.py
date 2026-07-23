import unittest

from combstruct import (
    AtomObject,
    ConstructionObject,
    EpsilonObject,
    StructureIterator,
    UnsupportedConstruction,
    allstructs,
    count,
    finished,
    iterstructs,
    nextstruct,
    parse_specification,
)


class ExhaustiveGenerationTests(unittest.TestCase):
    def assert_enumeration_matches_count(
        self,
        specification: str,
        *,
        labelled: bool,
        sizes: range,
        symbol: str = "S",
    ):
        for size in sizes:
            with self.subTest(
                specification=specification,
                labelled=labelled,
                size=size,
            ):
                objects = allstructs(
                    specification,
                    labelled=labelled,
                    size=size,
                    symbol=symbol,
                )
                self.assertEqual(
                    len(objects),
                    count(
                        specification,
                        labelled=labelled,
                        size=size,
                        symbol=symbol,
                    ),
                )
                self.assertTrue(all(obj.size == size for obj in objects))
                self.assertEqual(len(objects), len(set(objects)))

    def test_elementary_objects_are_immutable_and_sized(self):
        self.assertEqual(AtomObject().size, 1)
        self.assertEqual(AtomObject(4).size, 1)
        self.assertEqual(EpsilonObject().size, 0)
        self.assertEqual(EpsilonObject("leaf").tag, "leaf")
        self.assertEqual(
            ConstructionObject("Prod", (AtomObject(), EpsilonObject())).size,
            1,
        )

    def test_named_epsilon_productions_preserve_derivation_tags(self):
        objects = allstructs(
            "{mark = Epsilon, S = Prod(mark,Z)}",
            labelled=False,
            size=1,
        )

        self.assertEqual(len(objects), 1)
        root = objects[0]
        self.assertIsInstance(root, ConstructionObject)
        assert isinstance(root, ConstructionObject)
        self.assertEqual(root.children[0], EpsilonObject("mark"))

    def test_unlabelled_recursive_binary_trees_match_catalan_counts(self):
        specification = "{S = Union(Epsilon,Prod(Z,S,S))}"

        self.assert_enumeration_matches_count(
            specification,
            labelled=False,
            sizes=range(7),
        )
        self.assertEqual(
            [len(allstructs(specification, labelled=False, size=size)) for size in range(6)],
            [1, 1, 2, 5, 14, 42],
        )

    def test_labelled_product_sequence_set_and_cycle_match_counts(self):
        for specification in (
            "{S = Prod(Z,Z)}",
            "{S = Sequence(Z)}",
            "{S = Set(Z)}",
            "{S = Cycle(Z)}",
        ):
            with self.subTest(specification=specification):
                self.assert_enumeration_matches_count(
                    specification,
                    labelled=True,
                    sizes=range(6),
                )

    def test_unlabelled_multisets_powersets_and_cycles_are_canonical(self):
        for specification in (
            "{A = Sequence(Z,1 <= card), S = Set(A)}",
            "{A = Sequence(Z,1 <= card), S = PowerSet(A)}",
            "{a = Atom, b = Atom, S = Cycle(Union(a,b))}",
        ):
            with self.subTest(specification=specification):
                self.assert_enumeration_matches_count(
                    specification,
                    labelled=False,
                    sizes=range(7),
                )

    def test_powerset_cardinality_constraints_are_counted_and_enumerated(self):
        specification = "{A = Union(Z,Prod(Z,Z)), S = PowerSet(A,card = 2)}"

        self.assert_enumeration_matches_count(
            specification,
            labelled=False,
            sizes=range(7),
        )
        self.assertEqual(
            [count(specification, labelled=False, size=size) for size in range(7)],
            [0, 0, 0, 1, 0, 0, 0],
        )

    def test_union_branches_remain_disjoint(self):
        objects = allstructs("{S = Union(Z,Z)}", labelled=False, size=1)

        self.assertEqual(len(objects), 2)
        self.assertEqual(
            {obj.branch for obj in objects if isinstance(obj, ConstructionObject)}, {0, 1}
        )

    def test_parsed_equations_and_nondefault_symbol_are_supported(self):
        equations = parse_specification("{A = Sequence(Z)}")

        objects = allstructs(
            equations,
            labelled=True,
            size=3,
            symbol="A",
        )

        self.assertEqual(len(objects), 6)
        self.assertEqual(
            {
                child.label
                for obj in objects
                if isinstance(obj, ConstructionObject)
                for child in obj.children
                if isinstance(child, AtomObject)
            },
            {1, 2, 3},
        )

    def test_size_zero_components_and_unsupported_constructors_are_rejected(self):
        for specification, message in (
            ("{S = Sequence(Epsilon)}", "size-zero"),
            ("{S = Set(Epsilon)}", "size-zero"),
            ("{S = Cycle(Epsilon)}", "size-zero"),
            ("{S = PowerSet(Epsilon)}", "size-zero"),
        ):
            with (
                self.subTest(specification=specification),
                self.assertRaisesRegex(UnsupportedConstruction, message),
            ):
                allstructs(specification, labelled=False, size=2)

        with self.assertRaisesRegex(UnsupportedConstruction, "only defined for unlabeled"):
            allstructs("{S = PowerSet(Z)}", labelled=True, size=2)

    def test_non_well_founded_generation_is_rejected(self):
        with self.assertRaisesRegex(UnsupportedConstruction, "finite fixed point"):
            allstructs("{S = Union(Z,S)}", labelled=False, size=1)

    def test_inputs_are_validated(self):
        for invalid in (-1, True, 1.5):
            with self.subTest(size=invalid), self.assertRaises((TypeError, ValueError)):
                allstructs("{S = Z}", labelled=False, size=invalid)

        with self.assertRaises(TypeError):
            allstructs("{S = Z}", labelled=0, size=1)
        with self.assertRaises(TypeError):
            allstructs(1, labelled=False, size=1)
        with self.assertRaises(TypeError):
            allstructs("{S = Z}", labelled=False, size=1, symbol=1)
        with self.assertRaises(ValueError):
            allstructs("{S = Z}", labelled=False, size=1, symbol="")


class StructureIteratorTests(unittest.TestCase):
    def test_iterator_command_family_tracks_consumption(self):
        expected = allstructs("{S = Union(Z,Z)}", labelled=False, size=1)
        iterator = iterstructs("{S = Union(Z,Z)}", labelled=False, size=1)

        self.assertIsInstance(iterator, StructureIterator)
        self.assertFalse(finished(iterator))
        self.assertEqual(nextstruct(iterator), expected[0])
        self.assertFalse(finished(iterator))
        self.assertEqual(nextstruct(iterator), expected[1])
        self.assertTrue(finished(iterator))
        with self.assertRaises(StopIteration):
            nextstruct(iterator)

    def test_structure_iterator_supports_python_iteration(self):
        iterator = iterstructs("{S = Sequence(Z)}", labelled=True, size=3)

        self.assertEqual(tuple(iterator), iterator.objects)
        self.assertTrue(finished(iterator))

    def test_iterator_commands_require_structure_iterator_state(self):
        with self.assertRaises(TypeError):
            nextstruct(iter(()))
        with self.assertRaises(TypeError):
            finished(iter(()))


if __name__ == "__main__":
    unittest.main()
