import unittest
from dataclasses import FrozenInstanceError
from fractions import Fraction
from math import factorial

from combstruct import Catalog
from combstruct.generating_function import (
    GeneratingFunctionError,
    GeneratingFunctionEvaluationError,
    GeneratingFunctionParser,
    GFBinary,
    GFFunction,
    GFInteger,
    GFUnary,
    GFVariable,
    UnsupportedGeneratingFunction,
    generating_function_coefficients,
    parse_generating_function,
)

UNSUPPORTED_FORMS = ("Sum(", "RootOf(", "Complex(", "infinity", "...")


def is_supported_expression(source: str) -> bool:
    return "=" not in source and not any(token in source for token in UNSUPPORTED_FORMS)


class GeneratingFunctionParserTests(unittest.TestCase):
    def test_operator_precedence_and_unary_minus(self):
        expression = parse_generating_function("-1 + 2*_x^3")

        self.assertEqual(
            expression,
            GFBinary(
                "+",
                GFUnary("-", GFInteger(1)),
                GFBinary(
                    "*",
                    GFInteger(2),
                    GFBinary("^", GFVariable(), GFInteger(3)),
                ),
            ),
        )

    def test_power_is_right_associative(self):
        expression = GeneratingFunctionParser("_x^2^3").parse()

        self.assertEqual(
            expression,
            GFBinary(
                "^",
                GFVariable(),
                GFBinary("^", GFInteger(2), GFInteger(3)),
            ),
        )

    def test_elementary_functions_and_rational_power(self):
        expression = parse_generating_function("exp(_x)-ln(1-_x)^(1/2)")

        self.assertEqual(
            expression,
            GFBinary(
                "-",
                GFFunction("exp", GFVariable()),
                GFBinary(
                    "^",
                    GFFunction(
                        "ln",
                        GFBinary("-", GFInteger(1), GFVariable()),
                    ),
                    GFBinary("/", GFInteger(1), GFInteger(2)),
                ),
            ),
        )

    def test_lambert_w_function(self):
        self.assertEqual(
            parse_generating_function("LambertW(-_x)"),
            GFFunction("LambertW", GFUnary("-", GFVariable())),
        )

    def test_ast_is_immutable(self):
        expression = GFInteger(1)

        with self.assertRaises(FrozenInstanceError):
            expression.value = 2

    def test_malformed_expression_reports_context(self):
        with self.assertRaisesRegex(GeneratingFunctionError, "Unexpected end"):
            parse_generating_function("1+(")
        with self.assertRaisesRegex(GeneratingFunctionError, "Unexpected token"):
            parse_generating_function("1 2")
        with self.assertRaisesRegex(GeneratingFunctionError, "must not be empty"):
            parse_generating_function("  ")

    def test_special_ecs_forms_are_explicitly_unsupported(self):
        for source in (
            "S(_x) = _x+S(_x)^2",
            "Sum(_x^j,j=1..infinity)",
            "RootOf(_Z^2+_x)",
            "Complex(0,1)*_x",
            "exp(_x+...)",
        ):
            with (
                self.subTest(source=source),
                self.assertRaises(
                    UnsupportedGeneratingFunction,
                ),
            ):
                parse_generating_function(source)

    def test_catalogue_coverage_matches_audited_grammar(self):
        supported = []
        unsupported = []

        for structure in Catalog():
            source = structure.generating_function
            if source is None:
                continue
            if is_supported_expression(source):
                parse_generating_function(source)
                supported.append(structure.id)
            else:
                with self.assertRaises(UnsupportedGeneratingFunction):
                    parse_generating_function(source)
                unsupported.append(structure.id)

        self.assertEqual(len(supported), 932)
        self.assertEqual(len(unsupported), 96)
        self.assertEqual(len(supported) + len(unsupported), 1028)


class GeneratingFunctionCoefficientTests(unittest.TestCase):
    def test_rational_expression(self):
        self.assertEqual(
            generating_function_coefficients("1/(1-_x)^2", 6),
            tuple(Fraction(value) for value in (1, 2, 3, 4, 5, 6)),
        )

    def test_exponential_and_logarithm(self):
        self.assertEqual(
            generating_function_coefficients("exp(_x)", 6),
            tuple(Fraction(1, factorial(degree)) for degree in range(6)),
        )

    def test_lambert_w_and_composition(self):
        self.assertEqual(
            generating_function_coefficients("LambertW(_x)", 6),
            (
                Fraction(0),
                Fraction(1),
                Fraction(-1),
                Fraction(3, 2),
                Fraction(-8, 3),
                Fraction(125, 24),
            ),
        )
        self.assertEqual(
            generating_function_coefficients("-LambertW(-_x)/_x", 6),
            (
                Fraction(1),
                Fraction(1),
                Fraction(3, 2),
                Fraction(8, 3),
                Fraction(125, 24),
                Fraction(54, 5),
            ),
        )
        self.assertEqual(
            generating_function_coefficients("ln(1/(1-_x))", 6),
            (
                Fraction(0),
                Fraction(1),
                Fraction(1, 2),
                Fraction(1, 3),
                Fraction(1, 4),
                Fraction(1, 5),
            ),
        )

    def test_square_root_and_removable_singularity(self):
        self.assertEqual(
            generating_function_coefficients(
                "-1/2*(-1+(1-4*_x)^(1/2))/_x",
                8,
            ),
            tuple(Fraction(value) for value in (1, 1, 2, 5, 14, 42, 132, 429)),
        )

    def test_parsed_expression_is_accepted(self):
        expression = parse_generating_function("(1+_x)^3")

        self.assertEqual(
            generating_function_coefficients(expression, 5),
            tuple(Fraction(value) for value in (1, 3, 3, 1, 0)),
        )

    def test_exact_zero_after_cancellation(self):
        self.assertEqual(
            generating_function_coefficients("(_x-_x)/_x", 4),
            (Fraction(0),) * 4,
        )

    def test_invalid_coefficient_count(self):
        for value in (True, 1.5, "2"):
            with self.subTest(value=value), self.assertRaises(TypeError):
                generating_function_coefficients("1", value)
        with self.assertRaises(ValueError):
            generating_function_coefficients("1", -1)

    def test_invalid_source_object(self):
        with self.assertRaises(TypeError):
            generating_function_coefficients(object(), 4)

    def test_non_formal_or_nonexact_expressions_are_rejected(self):
        cases = {
            "1/0": "zero series",
            "exp(1+_x)": "constant coefficient 0",
            "ln(2+_x)": "constant coefficient 1",
            "LambertW(1+_x)": "constant coefficient 0",
            "_x^_x": "rational constant",
            "(2+_x)^(1/2)": "constant coefficient 1",
            "_x^(-1)": "negative powers",
        }
        for source, message in cases.items():
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(GeneratingFunctionEvaluationError, message),
            ):
                generating_function_coefficients(source, 4)

    def test_every_parsed_catalogue_function_matches_its_stored_terms(self):
        ordinary = []
        exponential = []

        for structure in Catalog():
            source = structure.generating_function
            if source is None or not is_supported_expression(source):
                continue

            if structure.id == 69:
                with self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "constant coefficient 0",
                ):
                    generating_function_coefficients(source, len(structure.terms))
                continue

            coefficients = generating_function_coefficients(source, len(structure.terms))
            ordinary_match = all(
                coefficient == term
                for coefficient, term in zip(coefficients, structure.terms, strict=True)
            )
            exponential_match = all(
                coefficient * factorial(degree) == term
                for degree, (coefficient, term) in enumerate(
                    zip(coefficients, structure.terms, strict=True),
                )
            )

            self.assertNotEqual(
                ordinary_match,
                exponential_match,
                f"ECS {structure.id} must match exactly one interpretation",
            )
            self.assertEqual(
                exponential_match,
                structure.labeled,
                f"ECS {structure.id} disagrees with its labeled field",
            )
            (exponential if exponential_match else ordinary).append(structure.id)

        self.assertEqual(len(ordinary), 503)
        self.assertEqual(len(exponential), 428)
        self.assertEqual(len(ordinary) + len(exponential), 931)


if __name__ == "__main__":
    unittest.main()
