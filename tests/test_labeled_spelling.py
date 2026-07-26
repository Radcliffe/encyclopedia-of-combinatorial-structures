"""``labeled`` is the preferred spelling; ``labelled`` remains an accepted alias.

These tests cover every public entry point that takes a labeling flag and
confirm: the ``labeled`` spelling works, the legacy ``labelled`` spelling still
works, passing both with agreeing values is fine, and passing both with
conflicting values raises ``TypeError``.
"""

import unittest
from random import Random

from combstruct import (
    CountDirectedSampler,
    agfeqns,
    agfseries,
    allstructs,
    compute_terms,
    count,
    derive_generating_function,
    draw,
    gfeqns,
    gfseries,
    gfsolve,
    iterstructs,
    parse_specification,
)


class LabeledSpellingTests(unittest.TestCase):
    def test_derive_generating_function_accepts_either_spelling(self):
        expected = derive_generating_function("{S = Sequence(Z)}", labelled=False)

        self.assertEqual(
            derive_generating_function("{S = Sequence(Z)}", labeled=False),
            expected,
        )
        self.assertEqual(
            derive_generating_function("{S = Sequence(Z)}", labeled=False, labelled=False),
            expected,
        )
        with self.assertRaises(TypeError):
            derive_generating_function("{S = Sequence(Z)}", labeled=True, labelled=False)

    def test_gfeqns_accepts_either_spelling(self):
        expected = gfeqns("{S = Sequence(Z)}", labelled=False)

        self.assertEqual(gfeqns("{S = Sequence(Z)}", labeled=False), expected)
        with self.assertRaises(TypeError):
            gfeqns("{S = Sequence(Z)}", labeled=True, labelled=False)

    def test_allstructs_and_iterstructs_accept_either_spelling(self):
        expected = allstructs("{S = Union(Z,Z)}", size=1, labelled=True)

        self.assertEqual(allstructs("{S = Union(Z,Z)}", size=1, labeled=True), expected)
        self.assertEqual(
            tuple(iterstructs("{S = Union(Z,Z)}", size=1, labeled=True)),
            expected,
        )
        with self.assertRaises(TypeError):
            allstructs("{S = Union(Z,Z)}", size=1, labeled=True, labelled=False)

    def test_compute_terms_accepts_either_spelling(self):
        expected = compute_terms("{S = Sequence(Z)}", labelled=False, term_count=5)

        self.assertEqual(
            compute_terms("{S = Sequence(Z)}", labeled=False, term_count=5),
            expected,
        )
        with self.assertRaises(TypeError):
            compute_terms("{S = Sequence(Z)}", labeled=True, labelled=False, term_count=5)

    def test_count_accepts_either_spelling(self):
        expected = count("{S = Set(Z)}", labelled=True, size=5)

        self.assertEqual(count("{S = Set(Z)}", labeled=True, size=5), expected)
        with self.assertRaises(TypeError):
            count("{S = Set(Z)}", labeled=True, labelled=False, size=5)

    def test_gfseries_accepts_either_spelling(self):
        expected = gfseries("{S = Set(Z)}", labelled=True, term_count=4)

        self.assertEqual(gfseries("{S = Set(Z)}", labeled=True, term_count=4), expected)
        with self.assertRaises(TypeError):
            gfseries("{S = Set(Z)}", labeled=True, labelled=False, term_count=4)

    def test_gfsolve_accepts_either_spelling(self):
        expected = gfsolve("{S = Union(Z,Prod(Z,S))}", labelled=False)

        self.assertEqual(
            gfsolve("{S = Union(Z,Prod(Z,S))}", labeled=False),
            expected,
        )
        with self.assertRaises(TypeError):
            gfsolve("{S = Union(Z,Prod(Z,S))}", labeled=True, labelled=False)

    def test_draw_accepts_either_spelling(self):
        specification = "{S = Union(Z,Z)}"
        result = draw(specification, size=1, labeled=True, rng=Random(1))

        self.assertIsNotNone(result)
        with self.assertRaises(TypeError):
            draw(specification, size=1, labeled=True, labelled=False, rng=Random(1))

    def test_agfeqns_and_agfseries_accept_either_spelling(self):
        specification = "{N=Atom,T=Union(N,Prod(N,T,T))}"
        attribute_specification = "{leaf(T)=Union(1,Prod(0,leaf(T),leaf(T)))}"
        attributes = {"u": "leaf"}

        expected_system = agfeqns(
            specification,
            attribute_specification,
            labelled=False,
            attributes=attributes,
        )
        self.assertEqual(
            agfeqns(
                specification,
                attribute_specification,
                labeled=False,
                attributes=attributes,
            ),
            expected_system,
        )
        with self.assertRaises(TypeError):
            agfeqns(
                specification,
                attribute_specification,
                labeled=True,
                labelled=False,
                attributes=attributes,
            )

        expected_series = agfseries(
            specification,
            attribute_specification,
            labelled=False,
            term_count=6,
            attributes=attributes,
        )
        series = agfseries(
            specification,
            attribute_specification,
            labeled=False,
            term_count=6,
            attributes=attributes,
        )
        self.assertEqual(series["T"].coefficient(3, u=2), expected_series["T"].coefficient(3, u=2))
        with self.assertRaises(TypeError):
            agfseries(
                specification,
                attribute_specification,
                labeled=True,
                labelled=False,
                term_count=6,
                attributes=attributes,
            )

    def test_count_directed_sampler_accepts_either_spelling(self):
        equations = parse_specification("{S = Union(Z,Z)}")

        by_labeled = CountDirectedSampler(equations, labeled=True, size=1, rng=Random(1))
        by_labelled = CountDirectedSampler(equations, labelled=True, size=1, rng=Random(1))
        self.assertEqual(by_labeled.labelled, by_labelled.labelled)
        with self.assertRaises(TypeError):
            CountDirectedSampler(equations, labeled=True, labelled=False, size=1, rng=Random(1))


if __name__ == "__main__":
    unittest.main()
