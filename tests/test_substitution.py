import unittest
from fractions import Fraction
from math import factorial
from random import Random

from combstruct import (
    Constructor,
    GFBinary,
    GFFunction,
    GFInteger,
    GFVariable,
    SpecificationError,
    allstructs,
    count,
    draw,
    expand_substitutions,
    generating_function_coefficients,
    gfsolve,
    parse_specification,
)


def contains_subst(expression) -> bool:
    if not isinstance(expression, Constructor):
        return False
    return expression.name.lower() == "subst" or any(
        contains_subst(argument) for argument in expression.arguments
    )


class SubstitutionConstructorTests(unittest.TestCase):
    def test_parser_preserves_and_expander_desugars_subst(self):
        equations = parse_specification("{A = Prod(Z,Z), B = Union(Z,Prod(Z,B)), S = Subst(A,B)}")

        self.assertEqual(equations["S"].name, "Subst")
        expanded = expand_substitutions(equations)

        self.assertTrue(any(name.startswith("_subst_") for name in expanded))
        self.assertFalse(any(contains_subst(expression) for expression in expanded.values()))

    def test_unlabelled_substitution_preserves_outer_symmetries(self):
        specification = "{A = Sequence(Z,1 <= card), S = Subst(A,Set(Z,1 <= card))}"

        expected = [0, 1, 2, 3, 5, 7, 11, 15]
        self.assertEqual(
            [count(specification, labelled=False, size=size) for size in range(8)],
            expected,
        )
        self.assertEqual(
            [len(allstructs(specification, labelled=False, size=size)) for size in range(8)],
            expected,
        )

    def test_labelled_substitution_uses_partitional_label_distribution(self):
        specification = "{S = Subst(Set(Z,card = 2),Set(Z,1 <= card))}"

        expected = [0, 0, 1, 0, 3, 0, 15, 0, 105]
        self.assertEqual(
            [count(specification, labelled=True, size=size) for size in range(9)],
            expected,
        )
        self.assertEqual(
            [len(allstructs(specification, labelled=True, size=size)) for size in range(7)],
            expected[:7],
        )

    def test_named_recursive_outer_grammar_is_cloned(self):
        specification = "{A = Prod(Z,Z), B = Union(Z,Prod(Z,B)), S = Subst(A,B)}"

        expected = [0, 0, 1, 0, 1, 0, 1, 0, 1]
        self.assertEqual(
            [count(specification, labelled=False, size=size) for size in range(9)],
            expected,
        )
        self.assertEqual(
            [len(allstructs(specification, labelled=False, size=size)) for size in range(9)],
            expected,
        )

    def test_nested_substitution_is_associative(self):
        nested = "{S = Subst(Prod(Z,Z),Subst(Sequence(Z,card = 2),Sequence(Z,1 <= card)))}"
        flattened = "{S = Subst(Subst(Prod(Z,Z),Sequence(Z,card = 2)),Sequence(Z,1 <= card))}"

        self.assertEqual(
            [count(nested, labelled=False, size=size) for size in range(13)],
            [count(flattened, labelled=False, size=size) for size in range(13)],
        )

    def test_gfsolve_derives_the_substituted_generating_function(self):
        specification = "{S = Subst(Prod(Z,Z),Sequence(Z,1 <= card))}"
        expression = gfsolve(specification, labelled=False)

        self.assertEqual(
            expression,
            GFBinary(
                "/",
                GFBinary("*", GFVariable(), GFVariable()),
                GFBinary(
                    "-",
                    GFInteger(1),
                    GFBinary("*", GFVariable(), GFVariable()),
                ),
            ),
        )
        self.assertEqual(
            generating_function_coefficients(expression, 8),
            tuple(Fraction(value) for value in (0, 0, 1, 0, 1, 0, 1, 0)),
        )

        matchings = "{S = Subst(Set(Z,card = 2),Set(Z,1 <= card))}"
        labeled_expression = gfsolve(matchings, labelled=True)
        self.assertEqual(
            labeled_expression,
            GFBinary(
                "-",
                GFFunction(
                    "exp",
                    GFBinary(
                        "/",
                        GFBinary("^", GFVariable(), GFInteger(2)),
                        GFInteger(2),
                    ),
                ),
                GFInteger(1),
            ),
        )
        coefficients = generating_function_coefficients(labeled_expression, 9)
        self.assertEqual(
            [int(coefficient * factorial(size)) for size, coefficient in enumerate(coefficients)],
            [0, 0, 1, 0, 3, 0, 15, 0, 105],
        )

    def test_draw_uses_the_same_substitution_class(self):
        specification = "{S = Subst(Prod(Z,Z),Sequence(Z,1 <= card))}"
        objects = allstructs(specification, labelled=False, size=6)

        self.assertEqual(
            draw(specification, labelled=False, size=6, rng=Random(42)),
            objects[0],
        )

    def test_substitution_rejects_nullable_or_malformed_arguments(self):
        for specification, message in (
            ("{S = Subst(Epsilon,Z)}", "first argument"),
            ("{S = Subst(Z,Sequence(Z))}", "second argument"),
            ("{S = Subst(Z)}", "exactly two"),
            ("{S = Subst(Z,Z,Z)}", "exactly two"),
            ("{S = Subst(Z,Z,card = 2)}", "does not accept"),
        ):
            with (
                self.subTest(specification=specification),
                self.assertRaisesRegex(SpecificationError, message),
            ):
                count(specification, labelled=False, size=3)


if __name__ == "__main__":
    unittest.main()
