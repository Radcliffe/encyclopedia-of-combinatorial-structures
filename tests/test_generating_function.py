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
    GFComplex,
    GFEquation,
    GFEquationSystem,
    GFFunction,
    GFIndex,
    GFInfiniteSum,
    GFInteger,
    GFRootOf,
    GFSeriesCall,
    GFTotient,
    GFUnary,
    GFVariable,
    UnsupportedGeneratingFunction,
    generating_function_coefficients,
    parse_generating_function,
)


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

    def test_rootof_equation_and_local_variable(self):
        self.assertEqual(
            parse_generating_function("RootOf(_Z^3*_x-_Z+1)"),
            GFRootOf(
                GFBinary(
                    "+",
                    GFBinary(
                        "-",
                        GFBinary(
                            "*",
                            GFBinary("^", GFVariable("_Z"), GFInteger(3)),
                            GFVariable(),
                        ),
                        GFVariable("_Z"),
                    ),
                    GFInteger(1),
                ),
            ),
        )
        with self.assertRaisesRegex(GeneratingFunctionError, "only valid inside RootOf"):
            parse_generating_function("_Z+_x")

    def test_indexed_infinite_sum_and_totient(self):
        expression = parse_generating_function(
            "Sum(numtheory:-phi(j[1])*_x^j[1]/j[1],j[1]=1..infinity)",
        )

        self.assertEqual(
            expression,
            GFInfiniteSum(
                GFBinary(
                    "/",
                    GFBinary(
                        "*",
                        GFTotient(GFIndex(1)),
                        GFBinary("^", GFVariable(), GFIndex(1)),
                    ),
                    GFIndex(1),
                ),
                GFIndex(1),
            ),
        )

    def test_one_argument_complex_constructor(self):
        self.assertEqual(
            parse_generating_function("Complex(-1/2)"),
            GFComplex(
                GFBinary("/", GFUnary("-", GFInteger(1)), GFInteger(2)),
            ),
        )

    def test_implicit_equation_and_named_series_calls(self):
        equation = parse_generating_function("A(x)=x+(1/2)*(A(x)^2+A(x^2))")

        self.assertIsInstance(equation, GFEquation)
        assert isinstance(equation, GFEquation)
        self.assertEqual(equation.left, GFSeriesCall("A", GFVariable()))
        self.assertIsInstance(equation.right, GFBinary)

        call = GFSeriesCall("A", GFVariable())
        self.assertEqual(
            parse_generating_function("log(1-A(x))+2*A(x)-x=0"),
            GFEquation(
                GFBinary(
                    "-",
                    GFBinary(
                        "+",
                        GFFunction("ln", GFBinary("-", GFInteger(1), call)),
                        GFBinary("*", GFInteger(2), call),
                    ),
                    GFVariable(),
                ),
                GFInteger(0),
            ),
        )

    def test_implicit_equation_system(self):
        source = Catalog().get(118).generating_function

        self.assertIsNotNone(source)
        assert source is not None
        system = parse_generating_function(source)

        self.assertIsInstance(system, GFEquationSystem)
        assert isinstance(system, GFEquationSystem)
        self.assertEqual(len(system.equations), 3)
        self.assertEqual(
            tuple(equation.left for equation in system.equations),
            (
                GFSeriesCall("B", GFVariable()),
                GFSeriesCall("C", GFVariable()),
                GFSeriesCall("S", GFVariable()),
            ),
        )
        self.assertIsInstance(system.equations[1].right, GFFunction)
        self.assertIsInstance(system.equations[2].right, GFInfiniteSum)

    def test_summation_indices_are_lexically_scoped(self):
        cases = {
            "j[1]": "not bound",
            "Sum(_x^j[1],j[2]=1..infinity)": "j\\[1\\].*not bound",
            "Sum(Sum(_x^j[1],j[1]=1..infinity),j[1]=1..infinity)": "rebind",
            "Sum(_x^j[1],j[1]=2..infinity)": "Expected '1'",
        }
        for source, message in cases.items():
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(GeneratingFunctionError, message),
            ):
                parse_generating_function(source)

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
        for source in ("A(x),B(x)=x", "A(x)=x,B(x)"):
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(GeneratingFunctionError, "must contain equations"),
            ):
                parse_generating_function(source)

    def test_special_ecs_forms_are_explicitly_unsupported(self):
        for source in (
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
        equations = []
        systems = []
        unsupported = []

        for structure in Catalog():
            source = structure.generating_function
            if source is None:
                continue
            try:
                result = parse_generating_function(source)
            except UnsupportedGeneratingFunction:
                unsupported.append(structure.id)
            else:
                supported.append(structure.id)
                if isinstance(result, GFEquation):
                    equations.append(structure.id)
                elif isinstance(result, GFEquationSystem):
                    systems.append(structure.id)

        self.assertEqual(len(supported), 1023)
        self.assertEqual(equations, [1, 43, 45, 89, 91])
        self.assertEqual(systems, [118])
        self.assertEqual(unsupported, [44, 56, 57, 79, 95])
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

    def test_shifted_principal_lambert_w(self):
        source = "-LambertW(-1/2*exp(-1/2+1/2*_x))-1/2+1/2*_x"
        expression = parse_generating_function(source)

        for value in (source, expression):
            with self.subTest(value=value):
                self.assertEqual(
                    generating_function_coefficients(value, 8),
                    (
                        Fraction(0),
                        Fraction(1),
                        Fraction(1, 2),
                        Fraction(2, 3),
                        Fraction(13, 12),
                        Fraction(59, 30),
                        Fraction(172, 45),
                        Fraction(4901, 630),
                    ),
                )
        self.assertEqual(
            generating_function_coefficients("LambertW(exp(1+_x^2)*1)", 5),
            (Fraction(1), Fraction(0), Fraction(1, 2), Fraction(0), Fraction(1, 16)),
        )
        self.assertEqual(
            generating_function_coefficients("LambertW(2*exp(2))", 3),
            (Fraction(2), Fraction(0), Fraction(0)),
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
            "LambertW(-1*exp(-1+_x))": "branch point",
            "LambertW(-2*exp(-2+_x))": "constant coefficient 0",
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

    def test_unselected_rootof_requires_a_formal_series_branch(self):
        source = "RootOf(_Z^3*_x-_Z+1)"
        expression = parse_generating_function(source)

        for value in (source, expression):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "no branch selector",
                ),
            ):
                generating_function_coefficients(value, 6)

    def test_implicit_equation_requires_a_named_series_solver(self):
        source = "A(x)=x+(1/2)*(A(x)^2+A(x^2))"
        equation = parse_generating_function(source)

        for value in (source, equation):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "Implicit generating-function equations.*solver",
                ),
            ):
                generating_function_coefficients(value, 6)

        with self.assertRaisesRegex(
            GeneratingFunctionEvaluationError,
            "Named series call A.*solver",
        ):
            generating_function_coefficients("A(x)", 6)

    def test_implicit_equation_system_requires_a_named_series_solver(self):
        source = Catalog().get(118).generating_function

        self.assertIsNotNone(source)
        assert source is not None
        system = parse_generating_function(source)
        for value in (source, system):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "Implicit generating-function equations.*solver",
                ),
            ):
                generating_function_coefficients(value, 6)

    def test_coefficientwise_finite_infinite_sum(self):
        source = "Sum(_x^j[1]/j[1],j[1]=1..infinity)"
        expression = parse_generating_function(source)

        for value in (source, expression):
            with self.subTest(value=value):
                self.assertEqual(
                    generating_function_coefficients(value, 6),
                    tuple(Fraction(1, degree) if degree else Fraction() for degree in range(6)),
                )

    def test_totient_and_nested_infinite_sums(self):
        self.assertEqual(
            generating_function_coefficients(
                "Sum(numtheory:-phi(j[1])*_x^j[1],j[1]=1..infinity)",
                7,
            ),
            tuple(Fraction(value) for value in (0, 1, 1, 2, 2, 4, 2)),
        )
        self.assertEqual(
            generating_function_coefficients(
                "Sum(Sum((_x^j[1])^j[2]/(j[1]*j[2]),j[2]=1..infinity),j[1]=1..infinity)",
                7,
            ),
            (
                Fraction(0),
                Fraction(1),
                Fraction(1),
                Fraction(2, 3),
                Fraction(3, 4),
                Fraction(2, 5),
                Fraction(2, 3),
            ),
        )

    def test_infinite_sum_requires_a_provable_coefficient_bound(self):
        cases = (
            "Sum(_x/j[1],j[1]=1..infinity)",
            "Sum(1+_x^j[1],j[1]=1..infinity)",
            "Sum(j[1]-1+_x^j[1],j[1]=1..infinity)",
        )
        for source in cases:
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "zero-constant summand.*scaled",
                ),
            ):
                generating_function_coefficients(source, 6)

    def test_complex_requires_complex_formal_series(self):
        source = "Complex(-1/2)*_x"
        expression = parse_generating_function(source)

        for value in (source, expression):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "complex formal-series support",
                ),
            ):
                generating_function_coefficients(value, 6)

    def test_every_parsed_catalogue_function_matches_its_stored_terms(self):
        ordinary = []
        exponential = []
        complex_forms = []
        infinite_sums = []
        implicit_equations = []
        implicit_systems = []
        unselected_roots = []

        for structure in Catalog():
            source = structure.generating_function
            if source is None:
                continue
            try:
                expression = parse_generating_function(source)
            except UnsupportedGeneratingFunction:
                continue

            if isinstance(expression, GFEquation):
                with self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "Implicit generating-function equations.*solver",
                ):
                    generating_function_coefficients(expression, len(structure.terms))
                implicit_equations.append(structure.id)
                continue

            if isinstance(expression, GFEquationSystem):
                with self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "Implicit generating-function equations.*solver",
                ):
                    generating_function_coefficients(expression, len(structure.terms))
                implicit_systems.append(structure.id)
                continue

            if "RootOf(" in source:
                with self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "no branch selector",
                ):
                    generating_function_coefficients(expression, len(structure.terms))
                unselected_roots.append(structure.id)
                continue

            if "Complex(" in source:
                with self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "complex formal-series support",
                ):
                    generating_function_coefficients(expression, len(structure.terms))
                complex_forms.append(structure.id)
                continue

            coefficients = generating_function_coefficients(expression, len(structure.terms))
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
            if "Sum(" in source:
                infinite_sums.append(structure.id)
            (exponential if exponential_match else ordinary).append(structure.id)

        self.assertEqual(len(ordinary), 548)
        self.assertEqual(len(exponential), 429)
        self.assertEqual(len(ordinary) + len(exponential), 977)
        self.assertEqual(complex_forms, [47])
        self.assertEqual(implicit_equations, [1, 43, 45, 89, 91])
        self.assertEqual(implicit_systems, [118])
        self.assertEqual(len(infinite_sums), 45)
        self.assertEqual(len(unselected_roots), 39)


if __name__ == "__main__":
    unittest.main()
