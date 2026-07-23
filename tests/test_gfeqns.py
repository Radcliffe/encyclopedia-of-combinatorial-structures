import unittest
from fractions import Fraction
from math import factorial

from combstruct import (
    Catalog,
    GeneratingFunctionEvaluationError,
    GFBinary,
    GFEquation,
    GFEquationSystem,
    GFFunction,
    GFInfiniteSum,
    GFInteger,
    GFSeriesCall,
    GFTotient,
    GFVariable,
    SpecificationError,
    UnsupportedGeneratingFunctionDerivation,
    compute_terms,
    generating_function_coefficients,
    gfeqns,
    parse_specification,
)


def equation_counts(
    system: GFEquationSystem,
    *,
    symbol: str,
    labelled: bool,
    term_count: int,
) -> list[int]:
    coefficients = generating_function_coefficients(
        system,
        term_count,
        symbol=symbol,
    )
    return [
        int(coefficient * factorial(size)) if labelled else int(coefficient)
        for size, coefficient in enumerate(coefficients)
    ]


class GeneratingFunctionEquationTests(unittest.TestCase):
    def assert_equations_match_terms(
        self,
        specification: str,
        *,
        labelled: bool,
        symbol: str = "S",
        term_count: int = 9,
    ):
        system = gfeqns(specification, labelled=labelled)
        self.assertEqual(
            equation_counts(
                system,
                symbol=symbol,
                labelled=labelled,
                term_count=term_count,
            ),
            compute_terms(
                specification,
                labelled=labelled,
                symbol=symbol,
                term_count=term_count,
            ),
        )

    def test_named_equations_remain_unsolved_series_calls(self):
        system = gfeqns(
            "{A = Sequence(Z), S = Prod(Z,A)}",
            labelled=False,
        )

        self.assertEqual(
            system,
            GFEquationSystem(
                (
                    GFEquation(
                        GFSeriesCall("A", GFVariable()),
                        GFBinary(
                            "/",
                            GFInteger(1),
                            GFBinary("-", GFInteger(1), GFVariable()),
                        ),
                    ),
                    GFEquation(
                        GFSeriesCall("S", GFVariable()),
                        GFBinary(
                            "*",
                            GFVariable(),
                            GFSeriesCall("A", GFVariable()),
                        ),
                    ),
                )
            ),
        )
        self.assert_equations_match_terms(
            "{A = Sequence(Z), S = Prod(Z,A)}",
            labelled=False,
        )

    def test_labeled_and_unlabeled_set_equations_are_distinct(self):
        labeled = gfeqns("{S = Set(Z)}", labelled=True)
        unlabeled = gfeqns("{S = Set(Z)}", labelled=False)

        self.assertEqual(
            labeled.equations[0].right,
            GFFunction("exp", GFVariable()),
        )
        unlabeled_right = unlabeled.equations[0].right
        self.assertIsInstance(unlabeled_right, GFFunction)
        assert isinstance(unlabeled_right, GFFunction)
        self.assertIsInstance(unlabeled_right.argument, GFInfiniteSum)

        self.assert_equations_match_terms("{S = Set(Z)}", labelled=True)
        self.assert_equations_match_terms("{S = Set(Z)}", labelled=False)

    def test_unrestricted_unlabeled_cycle_uses_totient_sum(self):
        system = gfeqns(
            "{a = Atom, b = Atom, S = Cycle(Union(a,b))}",
            labelled=False,
        )
        right = system.equations[-1].right

        self.assertIsInstance(right, GFInfiniteSum)
        assert isinstance(right, GFInfiniteSum)
        self.assertIsInstance(right.summand.left.left, GFTotient)
        self.assert_equations_match_terms(
            "{a = Atom, b = Atom, S = Cycle(Union(a,b))}",
            labelled=False,
            term_count=8,
        )

    def test_unrestricted_unlabeled_powerset_uses_alternating_cycle_index(self):
        specification = "{A = Sequence(Z,1 <= card), S = PowerSet(A)}"
        system = gfeqns(specification, labelled=False)
        right = system.equations[-1].right

        self.assertIsInstance(right, GFFunction)
        assert isinstance(right, GFFunction)
        self.assertIsInstance(right.argument, GFInfiniteSum)
        self.assert_equations_match_terms(
            specification,
            labelled=False,
            term_count=9,
        )

    def test_bounded_unlabeled_cycle_index_equations_match_terms(self):
        for specification in (
            "{A = Sequence(Z,1 <= card), S = Set(A,card <= 3)}",
            "{A = Sequence(Z,1 <= card), S = Cycle(A,card <= 3)}",
            "{A = Sequence(Z,1 <= card), S = PowerSet(A,card <= 3)}",
        ):
            with self.subTest(specification=specification):
                self.assert_equations_match_terms(
                    specification,
                    labelled=False,
                    term_count=9,
                )

    def test_substitution_is_preserved_as_function_composition(self):
        specification = "{A = Prod(Z,Z), B = Sequence(Z,1 <= card), S = Subst(A,B)}"
        system = gfeqns(specification, labelled=False)

        self.assertEqual(
            system.equations[-1],
            GFEquation(
                GFSeriesCall("S", GFVariable()),
                GFSeriesCall(
                    "B",
                    GFSeriesCall("A", GFVariable()),
                ),
            ),
        )
        self.assertEqual(
            compute_terms(
                specification,
                labelled=False,
                term_count=9,
            ),
            [0, 0, 1, 0, 1, 0, 1, 0, 1],
        )

    def test_recursive_equations_expand_by_formal_fixed_point(self):
        specification = "{S = Union(Epsilon,Prod(Z,S,S))}"

        self.assert_equations_match_terms(
            specification,
            labelled=False,
            term_count=10,
        )
        self.assert_equations_match_terms(
            specification,
            labelled=True,
            term_count=8,
        )

    def test_parsed_mappings_and_invalid_inputs(self):
        equations = parse_specification("{S = Sequence(Z)}")
        self.assertEqual(
            gfeqns(equations, labelled=False),
            gfeqns("{S = Sequence(Z)}", labelled=False),
        )

        with self.assertRaises(TypeError):
            gfeqns(1, labelled=False)
        with self.assertRaises(TypeError):
            gfeqns("{S = Z}", labelled=0)
        with self.assertRaisesRegex(SpecificationError, "Undefined symbol"):
            gfeqns("{S = Missing}", labelled=False)
        with self.assertRaises(UnsupportedGeneratingFunctionDerivation):
            gfeqns("{S = PowerSet(Z)}", labelled=True)

    def test_equation_coefficients_are_exact_fractions(self):
        system = gfeqns("{S = Set(Z)}", labelled=True)

        self.assertEqual(
            generating_function_coefficients(system, 6, symbol="S"),
            tuple(Fraction(1, factorial(size)) for size in range(6)),
        )

    def test_epsilon_marker_tags_become_independent_variables(self):
        system = gfeqns(
            "{leaf = Epsilon, internal = Epsilon, S = Union(Prod(leaf,Z),Prod(internal,Z,Z))}",
            labelled=False,
            tags={"u": "leaf", "v": ("internal",)},
        )

        self.assertEqual(system.equations[0].right, GFVariable("u"))
        self.assertEqual(system.equations[1].right, GFVariable("v"))
        self.assertEqual(
            system.equations[2].right,
            GFBinary(
                "+",
                GFBinary("*", GFVariable("u"), GFVariable()),
                GFBinary(
                    "*",
                    GFBinary("*", GFVariable("v"), GFVariable()),
                    GFVariable(),
                ),
            ),
        )
        with self.assertRaisesRegex(
            GeneratingFunctionEvaluationError,
            "multivariate evaluation",
        ):
            generating_function_coefficients(system, 3, symbol="S")

    def test_one_epsilon_marker_can_contribute_to_multiple_variables(self):
        system = gfeqns(
            "{node2=Epsilon,node3=Epsilon,T=Union(Prod(node2,Z,Z),Prod(node3,Z,Z,Z))}",
            labelled=False,
            tags={"u": "node2", "v": ("node2", "node3")},
        )

        self.assertEqual(
            system.equations[0].right,
            GFBinary("*", GFVariable("u"), GFVariable("v")),
        )
        self.assertEqual(system.equations[1].right, GFVariable("v"))

    def test_marker_tags_are_validated(self):
        specification = "{mark = Epsilon, A = Z, S = Prod(mark,A)}"

        for tags, error, message in (
            ({"_x": "mark"}, ValueError, "reserved"),
            ({"u": "missing"}, SpecificationError, "undefined"),
            ({"u": "A"}, SpecificationError, "directly as Epsilon"),
            ({1: "mark"}, TypeError, "nonempty strings"),
        ):
            with (
                self.subTest(tags=tags),
                self.assertRaisesRegex(error, message),
            ):
                gfeqns(specification, labelled=False, tags=tags)

    def test_every_catalogue_grammar_has_an_equation_system(self):
        built = 0
        for structure in Catalog():
            system = gfeqns(
                structure.specification,
                labelled=structure.labeled,
            )
            left_names = {
                equation.left.name
                for equation in system.equations
                if isinstance(equation.left, GFSeriesCall)
            }
            self.assertIn(structure.symbol, left_names, f"ECS {structure.id}")
            built += 1

        self.assertEqual(built, 1075)


if __name__ == "__main__":
    unittest.main()
