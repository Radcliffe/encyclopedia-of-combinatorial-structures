import unittest

from combstruct import (
    Combination,
    Composition,
    Partition,
    Permutation,
    Subset,
    allstructs,
    count,
    finished,
    iterstructs,
    nextstruct,
)


class PredefinedStructureTests(unittest.TestCase):
    def test_integer_arguments_expand_to_one_through_n(self):
        self.assertEqual(Combination(4).elements, (1, 2, 3, 4))
        self.assertEqual(Permutation(3).elements, (1, 2, 3))
        self.assertIs(Subset, Combination)

    def test_combination_counts_sizes_and_default_allsizes(self):
        structure = Combination(["a", "b", "c", "d"])

        self.assertEqual(
            [count(structure, size=size) for size in range(5)],
            [1, 4, 6, 4, 1],
        )
        self.assertEqual(count(structure), 16)
        self.assertEqual(count(structure, size="allsizes"), 16)
        self.assertEqual(len(allstructs(structure)), 16)
        self.assertEqual(
            allstructs(structure, size=2),
            (
                ("a", "b"),
                ("a", "c"),
                ("a", "d"),
                ("b", "c"),
                ("b", "d"),
                ("c", "d"),
            ),
        )

    def test_duplicate_elements_form_multiset_combinations(self):
        structure = Combination(["a", "a", "b"])

        self.assertEqual(count(structure, size=2), 2)
        self.assertEqual(
            set(allstructs(structure, size=2)),
            {("a", "a"), ("a", "b")},
        )

    def test_permutation_default_is_full_length_and_allsizes_is_explicit(self):
        structure = Permutation(3)

        self.assertEqual(count(structure), 6)
        self.assertEqual(len(allstructs(structure)), 6)
        self.assertEqual(count(structure, size=2), 6)
        self.assertEqual(count(structure, size="allsizes"), 16)
        self.assertEqual(
            [len(obj) for obj in allstructs(structure, size="allsizes")],
            [0, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3],
        )

    def test_duplicate_elements_form_distinct_multiset_permutations(self):
        structure = Permutation(["a", "a", "b"])

        self.assertEqual(count(structure), 3)
        self.assertEqual(
            set(allstructs(structure)),
            {("a", "a", "b"), ("a", "b", "a"), ("b", "a", "a")},
        )
        self.assertEqual(count(structure, size=2), 3)

    def test_partition_size_is_number_of_parts(self):
        structure = Partition(5)

        self.assertEqual(count(structure), 7)
        self.assertEqual(count(structure, size=2), 2)
        self.assertEqual(allstructs(structure, size=2), ((4, 1), (3, 2)))
        self.assertEqual(
            set(allstructs(structure)),
            {
                (5,),
                (4, 1),
                (3, 2),
                (3, 1, 1),
                (2, 2, 1),
                (2, 1, 1, 1),
                (1, 1, 1, 1, 1),
            },
        )
        self.assertEqual(count(Partition(95), size=40), 450768)

    def test_composition_size_is_number_of_parts(self):
        structure = Composition(5)

        self.assertEqual(count(structure), 16)
        self.assertEqual(count(structure, size=2), 4)
        self.assertEqual(
            allstructs(structure, size=2),
            ((1, 4), (2, 3), (3, 2), (4, 1)),
        )
        self.assertEqual(len(allstructs(structure)), 16)

    def test_out_of_range_sizes_are_empty(self):
        for structure in (
            Combination(3),
            Permutation(3),
            Partition(3),
            Composition(3),
        ):
            with self.subTest(structure=structure):
                self.assertEqual(count(structure, size=4), 0)
                self.assertEqual(allstructs(structure, size=4), ())

    def test_predefined_iterator_uses_the_shared_command_family(self):
        expected = allstructs(Combination(3), size=2)
        iterator = iterstructs(Combination(3), size=2)
        actual = []

        while not finished(iterator):
            actual.append(nextstruct(iterator))

        self.assertEqual(tuple(actual), expected)

    def test_predefined_structures_do_not_accept_grammar_options(self):
        with self.assertRaisesRegex(TypeError, "labelled does not apply"):
            count(Combination(3), size=2, labelled=False)
        with self.assertRaisesRegex(TypeError, "labelled does not apply"):
            allstructs(Combination(3), size=2, labelled=False)
        with self.assertRaisesRegex(ValueError, "symbol does not apply"):
            count(Combination(3), size=2, symbol="A")

    def test_invalid_structure_arguments_and_sizes_are_rejected(self):
        for constructor in (Combination, Permutation):
            with self.subTest(constructor=constructor):
                with self.assertRaises(ValueError):
                    constructor(-1)
                with self.assertRaises(TypeError):
                    constructor("abc")
                with self.assertRaises(TypeError):
                    constructor([[1], [2]])

        for constructor in (Partition, Composition):
            with self.subTest(constructor=constructor):
                with self.assertRaises((TypeError, ValueError)):
                    constructor(0)
                with self.assertRaises(TypeError):
                    constructor(True)

        with self.assertRaises(ValueError):
            count(Combination(3), size=-1)
        with self.assertRaises(TypeError):
            count(Combination(3), size="some")


if __name__ == "__main__":
    unittest.main()
