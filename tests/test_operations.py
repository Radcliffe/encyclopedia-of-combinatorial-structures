import unittest
from collections import Counter
from fractions import Fraction
from random import Random
from unittest.mock import patch

from combstruct import (
    Combination,
    Composition,
    EmptyStructureClassError,
    GFBinary,
    GFInteger,
    GFVariable,
    Partition,
    Permutation,
    SpecificationError,
    allstructs,
    count,
    draw,
    gfseries,
    gfsolve,
    parse_specification,
)


class MapleCompatibleOperationTests(unittest.TestCase):
    def test_count_returns_one_requested_unlabeled_size(self):
        self.assertEqual(
            count(
                "{S = Union(Epsilon,Prod(Z,S,S))}",
                labeled=False,
                size=7,
            ),
            429,
        )

    def test_count_accepts_parsed_equations_and_labeled_semantics(self):
        equations = parse_specification("{S = Set(Z)}")

        self.assertEqual(count(equations, labeled=True, size=8), 1)

    def test_gfseries_returns_every_ogf(self):
        result = gfseries(
            "{A = Sequence(Z), S = Prod(Z,A)}",
            labeled=False,
            term_count=5,
        )

        self.assertEqual(
            result,
            {
                "A": (Fraction(1),) * 5,
                "S": tuple(Fraction(value) for value in (0, 1, 1, 1, 1)),
            },
        )

    def test_gfseries_distinguishes_egf_coefficients_from_counts(self):
        result = gfseries(
            "{S = Set(Z)}",
            labeled=True,
            term_count=6,
        )

        self.assertEqual(
            result["S"],
            tuple(Fraction(1, factorial) for factorial in (1, 1, 2, 6, 24, 120)),
        )
        self.assertEqual(count("{S = Set(Z)}", labeled=True, size=5), 1)

    def test_gfsolve_uses_the_existing_formal_series_branch_solver(self):
        self.assertEqual(
            gfsolve("{S = Union(Z,Prod(Z,S))}", labeled=False),
            GFBinary(
                "/",
                GFVariable(),
                GFBinary("-", GFInteger(1), GFVariable()),
            ),
        )

    def test_operation_inputs_are_validated(self):
        for invalid in (-1, True, 1.5):
            with self.subTest(size=invalid), self.assertRaises((TypeError, ValueError)):
                count("{S = Z}", labeled=False, size=invalid)

        for invalid in (0, -1, True, 1.5):
            with self.subTest(term_count=invalid), self.assertRaises((TypeError, ValueError)):
                gfseries("{S = Z}", labeled=False, term_count=invalid)

        with self.assertRaises(TypeError):
            count("{S = Z}", labeled=0, size=1)
        with self.assertRaises(TypeError):
            gfseries("{S = Z}", labeled="unlabeled", term_count=2)
        with self.assertRaises(TypeError):
            count(1, labeled=False, size=1)
        with self.assertRaisesRegex(SpecificationError, "does not define"):
            count("{A = Z}", labeled=False, size=1)

    def test_draw_is_uniform_by_exact_object_rank_and_reproducible(self):
        specification = "{S = Union(Z,Z)}"
        first_rng = Random(12345)
        first = [draw(specification, labeled=False, size=1, rng=first_rng) for _ in range(3)]
        second_rng = Random(12345)
        second = [draw(specification, labeled=False, size=1, rng=second_rng) for _ in range(3)]

        self.assertEqual(first, second)

        rng = Random(8675309)
        branches = [draw(specification, labeled=False, size=1, rng=rng).branch for _ in range(4000)]
        self.assertLess(abs(branches.count(0) - branches.count(1)), 200)

    def test_draw_supports_predefined_defaults(self):
        value = draw(Combination(5), rng=Random(7))

        self.assertIn(value, set(allstructs(Combination(5))))

    def test_counted_draw_samples_predefined_families_without_materializing(self):
        with patch(
            "combstruct.operations.allstructs",
            side_effect=AssertionError("exhaustive generation was called"),
        ):
            combination = draw(
                Combination(100),
                size=50,
                rng=Random(1),
                algorithm="counted",
            )
            permutation = draw(
                Permutation(["a", "a", "b", "c"]),
                size=3,
                rng=Random(2),
                algorithm="counted",
            )
            partition = draw(
                Partition(95),
                size=40,
                rng=Random(3),
                algorithm="counted",
            )
            composition = draw(
                Composition(95),
                size=40,
                rng=Random(4),
                algorithm="counted",
            )

        self.assertEqual(len(combination), 50)
        self.assertEqual(len(permutation), 3)
        self.assertLessEqual(Counter(permutation)["a"], 2)
        self.assertEqual(len(partition), 40)
        self.assertEqual(sum(partition), 95)
        self.assertEqual(tuple(sorted(partition, reverse=True)), partition)
        self.assertEqual(len(composition), 40)
        self.assertEqual(sum(composition), 95)

    def test_counted_predefined_draw_is_uniform_with_duplicate_elements(self):
        structure = Permutation(["a", "a", "b"])
        expected = set(allstructs(structure))
        rng = Random(908)
        samples = [draw(structure, rng=rng, algorithm="counted") for _ in range(3000)]

        self.assertEqual(set(samples), expected)
        for obj in expected:
            self.assertLess(abs(samples.count(obj) - 1000), 100)

    def test_counted_draw_does_not_materialize_recursive_tree_classes(self):
        specification = "{S=Union(Epsilon,Prod(Z,S,S))}"

        with patch(
            "combstruct.operations.allstructs",
            side_effect=AssertionError("exhaustive generation was called"),
        ):
            value = draw(
                specification,
                labeled=False,
                size=30,
                rng=Random(17),
                algorithm="counted",
            )

        self.assertEqual(value.size, 30)

    def test_counted_draw_distributes_labels_uniformly(self):
        specification = "{S=Prod(Z,Z)}"
        expected = set(allstructs(specification, labeled=True, size=2))
        rng = Random(2026)
        samples = [
            draw(
                specification,
                labeled=True,
                size=2,
                rng=rng,
                algorithm="counted",
            )
            for _ in range(2000)
        ]

        self.assertEqual(set(samples), expected)
        first_count = samples.count(next(iter(expected)))
        self.assertLess(abs(first_count - 1000), 100)

    def test_counted_draw_supports_labeled_set_and_cycle_symmetries(self):
        for specification, size in (
            ("{S=Set(Z,card=3)}", 3),
            ("{S=Cycle(Z,card=4)}", 4),
        ):
            with self.subTest(specification=specification):
                expected = set(
                    allstructs(
                        specification,
                        labeled=True,
                        size=size,
                    ),
                )
                actual = {
                    draw(
                        specification,
                        labeled=True,
                        size=size,
                        rng=Random(seed),
                        algorithm="counted",
                    )
                    for seed in range(200)
                }
                self.assertEqual(actual, expected)

    def test_counted_draw_handles_recursive_unlabeled_sets_without_materializing(self):
        specification = "{T=Prod(Z,Set(T))}"

        with patch(
            "combstruct.operations.allstructs",
            side_effect=AssertionError("exhaustive generation was called"),
        ):
            value = draw(
                specification,
                labeled=False,
                size=15,
                symbol="T",
                rng=Random(1),
                algorithm="counted",
            )

        self.assertEqual(value.size, 15)

    def test_counted_draw_handles_unlabeled_set_type_selection(self):
        for constructor in ("Set", "PowerSet"):
            with self.subTest(constructor=constructor):
                specification = (
                    "{color=Union(red,blue,green),red=Atom,blue=Atom,green=Atom,"
                    f"S={constructor}(color,card=2)}}"
                )
                expected = set(allstructs(specification, labeled=False, size=2))
                actual = {
                    draw(
                        specification,
                        labeled=False,
                        size=2,
                        rng=Random(seed),
                        algorithm="counted",
                    )
                    for seed in range(100)
                }

                self.assertEqual(actual, expected)

    def test_counted_draw_samples_unlabeled_cycles_without_materializing(self):
        specification = "{bead=Union(red,blue),red=Atom,blue=Atom,S=Cycle(bead,card=4)}"
        expected = set(allstructs(specification, labeled=False, size=4))

        rng = Random(20260723)
        with patch(
            "combstruct.operations.allstructs",
            side_effect=AssertionError("exhaustive generation was called"),
        ):
            samples = [
                draw(
                    specification,
                    labeled=False,
                    size=4,
                    rng=rng,
                    algorithm="counted",
                )
                for _ in range(6000)
            ]

        self.assertEqual(len(expected), 6)
        self.assertEqual(set(samples), expected)
        frequencies = Counter(samples)
        for obj in expected:
            self.assertLess(abs(frequencies[obj] - 1000), 150)

    def test_counted_draw_samples_nested_cycle_selections_without_materializing(self):
        for constructor, expected_count in (("Set", 10), ("PowerSet", 6)):
            with self.subTest(constructor=constructor):
                specification = (
                    "{bead=Union(red,blue),red=Atom,blue=Atom,"
                    "C=Cycle(bead,card=3),"
                    f"S={constructor}(C,card=2)}}"
                )
                expected = set(allstructs(specification, labeled=False, size=6))
                rng = Random(314159)
                with patch(
                    "combstruct.operations.allstructs",
                    side_effect=AssertionError("exhaustive generation was called"),
                ):
                    samples = [
                        draw(
                            specification,
                            labeled=False,
                            size=6,
                            rng=rng,
                            algorithm="counted",
                        )
                        for _ in range(6000)
                    ]

                self.assertEqual(len(expected), expected_count)
                self.assertEqual(set(samples), expected)
                frequencies = Counter(samples)
                target = len(samples) / expected_count
                for obj in expected:
                    self.assertLess(abs(frequencies[obj] - target), 125)

    def test_draw_rejects_empty_classes_and_invalid_random_sources(self):
        with self.assertRaises(EmptyStructureClassError):
            draw(Combination(2), size=3, rng=Random(1))
        with self.assertRaises(TypeError):
            draw(Combination(2), rng=object())
        with self.assertRaisesRegex(ValueError, "algorithm"):
            draw(Combination(2), rng=Random(1), algorithm="fast")


if __name__ == "__main__":
    unittest.main()
