import unittest
from dataclasses import FrozenInstanceError

from combstruct import Catalog
from combstruct.generating_function import (
    GeneratingFunctionError,
    GeneratingFunctionParser,
    GFBinary,
    GFFunction,
    GFInteger,
    GFUnary,
    GFVariable,
    UnsupportedGeneratingFunction,
    parse_generating_function,
)

SPECIAL_FORMS = ("Sum(", "RootOf(", "LambertW(", "Complex(", "infinity", "...")


def is_finite_elementary_expression(source: str) -> bool:
    return "=" not in source and not any(token in source for token in SPECIAL_FORMS)


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
            "LambertW(-_x)",
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
            if is_finite_elementary_expression(source):
                parse_generating_function(source)
                supported.append(structure.id)
            else:
                with self.assertRaises(UnsupportedGeneratingFunction):
                    parse_generating_function(source)
                unsupported.append(structure.id)

        self.assertEqual(len(supported), 913)
        self.assertEqual(len(unsupported), 115)
        self.assertEqual(len(supported) + len(unsupported), 1028)


if __name__ == "__main__":
    unittest.main()
