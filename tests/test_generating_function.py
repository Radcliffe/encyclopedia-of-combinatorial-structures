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
    GFIndexedCoefficient,
    GFInfiniteProduct,
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

    def test_alternate_indexed_sum_notation(self):
        index = GFIndex(1)
        first = GFInfiniteSum(
            GFBinary(
                "/",
                GFBinary(
                    "*",
                    GFTotient(index),
                    GFBinary("^", GFVariable(), index),
                ),
                index,
            ),
            index,
        )
        later = GFInfiniteSum(
            GFBinary("/", GFBinary("^", GFVariable(), index), index),
            index,
            3,
        )

        self.assertEqual(
            parse_generating_function("Sum_{j=1..inf} phi(j)*x^j/j"),
            first,
        )
        self.assertEqual(parse_generating_function("Sum_{j>2} x^j/j"), later)
        self.assertEqual(
            parse_generating_function("Sum_{j>2} x^j/j + 1"),
            GFBinary("+", later, GFInteger(1)),
        )

    def test_symbolic_infinite_product_and_indexed_coefficients(self):
        source = Catalog().get(44).generating_function
        index = GFIndex(1)
        coefficient = GFIndexedCoefficient("a", index)

        self.assertIsNotNone(source)
        assert source is not None
        self.assertEqual(
            parse_generating_function(source),
            GFEquation(
                GFInfiniteProduct(
                    GFBinary(
                        "/",
                        GFInteger(1),
                        GFBinary(
                            "^",
                            GFBinary(
                                "-",
                                GFInteger(1),
                                GFBinary("^", GFVariable(), index),
                            ),
                            coefficient,
                        ),
                    ),
                    index,
                ),
                GFBinary(
                    "+",
                    GFBinary("+", GFInteger(1), GFVariable()),
                    GFBinary(
                        "*",
                        GFInteger(2),
                        GFInfiniteSum(
                            GFBinary(
                                "*",
                                coefficient,
                                GFBinary("^", GFVariable(), index),
                            ),
                            index,
                            2,
                        ),
                    ),
                ),
            ),
        )

    def test_patterned_ellipsis_normalizes_to_an_infinite_sum(self):
        index = GFIndex(1)
        call = GFSeriesCall("A", GFBinary("^", GFVariable(), index))
        positive_sum = GFInfiniteSum(GFBinary("/", call, index), index)
        alternating_sum = GFInfiniteSum(
            GFBinary(
                "/",
                GFBinary(
                    "*",
                    GFBinary(
                        "^",
                        GFUnary("-", GFInteger(1)),
                        GFBinary("+", index, GFInteger(1)),
                    ),
                    call,
                ),
                index,
            ),
            index,
        )

        for structure_id, infinite_sum in ((56, alternating_sum), (57, positive_sum)):
            source = Catalog().get(structure_id).generating_function
            self.assertIsNotNone(source)
            assert source is not None
            with self.subTest(structure_id=structure_id):
                self.assertEqual(
                    parse_generating_function(source),
                    GFEquation(
                        GFSeriesCall("A", GFVariable()),
                        GFBinary("*", GFVariable(), GFFunction("exp", infinite_sum)),
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
            "j": "not bound",
            "phi(j)": "not bound",
            "Sum(_x^j[1],j[2]=1..infinity)": "j\\[1\\].*not bound",
            "Sum(Sum(_x^j[1],j[1]=1..infinity),j[1]=1..infinity)": "rebind",
            "Sum(_x^j[1],j[1]=2..infinity)": "Expected '1'",
            "Sum_{j=0..inf} x^j": "lower bound must be positive",
            "a_k": "not supported",
        }
        for source, message in cases.items():
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(GeneratingFunctionError, message),
            ):
                parse_generating_function(source)

        mixed = parse_generating_function(
            "Sum(Product_{k>0} x^(j[1]*k),j[1]=1..infinity)",
        )
        self.assertIsInstance(mixed, GFInfiniteSum)
        assert isinstance(mixed, GFInfiniteSum)
        self.assertIsInstance(mixed.summand, GFInfiniteProduct)
        assert isinstance(mixed.summand, GFInfiniteProduct)
        self.assertEqual(mixed.index, GFIndex(1))
        self.assertEqual(mixed.summand.index, GFIndex(2))

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
            "A(x)=x*exp(A(x)+A(x^2)/2-A(x^3)/3+...)",
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

        self.assertEqual(len(supported), 1028)
        self.assertEqual(equations, [1, 43, 44, 45, 56, 57, 79, 89, 91, 95])
        self.assertEqual(systems, [118])
        self.assertEqual(unsupported, [])
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
        self.assertEqual(
            generating_function_coefficients("LambertW(1*exp(1-_x))", 5),
            (
                Fraction(1),
                Fraction(-1, 2),
                Fraction(1, 16),
                Fraction(1, 192),
                Fraction(-1, 3072),
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

    def test_contractive_named_series_equation(self):
        source = "A(x)=x+(1/2)*(A(x)^2+A(x^2))"
        equation = parse_generating_function(source)

        for value in (source, equation):
            with self.subTest(value=value):
                self.assertEqual(
                    generating_function_coefficients(value, 10),
                    tuple(Fraction(term) for term in (0, 1, 1, 1, 2, 3, 6, 11, 23, 46)),
                )

        with self.assertRaisesRegex(
            GeneratingFunctionEvaluationError,
            "Named series call A.*solver",
        ):
            generating_function_coefficients("A(x)", 6)

    def test_contractive_named_series_equations_match_the_catalogue(self):
        for identifier in (1, 43, 45, 56, 57):
            structure = Catalog().get(identifier)
            with self.subTest(identifier=identifier):
                self.assertEqual(
                    generating_function_coefficients(
                        structure.generating_function,
                        len(structure.terms),
                    ),
                    tuple(Fraction(term) for term in structure.terms),
                )

    def test_contractive_equation_system_and_symbol_selection(self):
        source = Catalog().get(118).generating_function

        self.assertIsNotNone(source)
        assert source is not None
        system = parse_generating_function(source)
        expected = tuple(Fraction(term) for term in Catalog().get(118).terms)
        self.assertEqual(
            generating_function_coefficients(source, len(expected), symbol="S"),
            expected,
        )
        expected_prefixes = {
            "B": (0, 1, 1, 2, 4, 9, 20, 48),
            "C": (1, 1, 2, 4, 9, 20, 48, 115),
            "S": (0, 1, 2, 4, 9, 20, 51, 125),
        }
        for symbol, prefix in expected_prefixes.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    generating_function_coefficients(system, len(prefix), symbol=symbol),
                    tuple(Fraction(term) for term in prefix),
                )

        with self.assertRaisesRegex(
            GeneratingFunctionEvaluationError,
            "requires a symbol",
        ):
            generating_function_coefficients(system, 6)
        with self.assertRaisesRegex(
            GeneratingFunctionEvaluationError,
            "no defining equation.*'A'",
        ):
            generating_function_coefficients(system, 6, symbol="A")

    def test_acyclic_zero_delay_dependencies_are_contractive(self):
        source = "A(x)=B(x), B(x)=x+x*A(x)"

        self.assertEqual(
            generating_function_coefficients(source, 8, symbol="A"),
            tuple(Fraction(term) for term in (0, 1, 1, 1, 1, 1, 1, 1)),
        )

    def test_coefficient_recursive_and_implicit_equations(self):
        self.assertEqual(
            generating_function_coefficients("A(x)=x/2+A(x)/2", 6),
            tuple(Fraction(term) for term in (0, 1, 0, 0, 0, 0)),
        )
        self.assertEqual(
            generating_function_coefficients("A(x)+A(x)^2=x", 7),
            tuple(Fraction(term) for term in (0, 1, -1, 2, -5, 14, -42)),
        )
        self.assertEqual(
            generating_function_coefficients(
                "A(x)=LambertW(1*exp(1+(x+A(x))))-1",
                7,
            ),
            (Fraction(0), *(Fraction(1, factorial(degree)) for degree in range(1, 7))),
        )
        system = "A(x)=x+B(x)/2, B(x)=A(x)/3"
        self.assertEqual(
            generating_function_coefficients(system, 5, symbol="A"),
            (Fraction(0), Fraction(6, 5), Fraction(0), Fraction(0), Fraction(0)),
        )
        self.assertEqual(
            generating_function_coefficients(system, 5, symbol="B"),
            (Fraction(0), Fraction(2, 5), Fraction(0), Fraction(0), Fraction(0)),
        )

    def test_coefficient_recursive_catalogue_equations(self):
        expected_prefixes = {
            79: (0, 2, 6, 29, 186, 1314, 10181, 82344, 690711, 5941864),
            91: (
                Fraction(0),
                Fraction(1),
                Fraction(0),
                Fraction(1, 3),
                Fraction(1, 4),
                Fraction(8, 15),
                Fraction(3, 4),
                Fraction(1727, 1260),
                Fraction(93, 40),
                Fraction(192827, 45360),
            ),
        }
        for identifier, prefix in expected_prefixes.items():
            with self.subTest(identifier=identifier):
                self.assertEqual(
                    generating_function_coefficients(
                        Catalog().get(identifier).generating_function,
                        len(prefix),
                    ),
                    tuple(Fraction(term) for term in prefix),
                )

        structure = Catalog().get(89)
        coefficients = generating_function_coefficients(
            structure.generating_function,
            len(structure.terms),
        )
        self.assertEqual(
            tuple(
                coefficient * factorial(degree) for degree, coefficient in enumerate(coefficients)
            ),
            structure.terms,
        )

    def test_remaining_implicit_equation_boundaries_are_rejected(self):
        cases = {
            44: "symbolic-product solver",
            95: "zero-constant summand.*scaled",
        }
        for identifier, message in cases.items():
            structure = Catalog().get(identifier)
            with (
                self.subTest(identifier=identifier),
                self.assertRaisesRegex(GeneratingFunctionEvaluationError, message),
            ):
                generating_function_coefficients(structure.generating_function, 8)

    def test_fixed_point_solver_rejects_ambiguous_and_malformed_systems(self):
        cases = {
            "A(x)=A(x)": "singular at degree 1",
            "A(x)=B(x), B(x)=A(x)": "singular at degree 1",
            "A(x)=B(x)": "B.*no defining equation",
            "A(x)=x, A(x)=x^2": "more than one defining equation",
            "A(x+1)=x": "named-series left side.*evaluated at x",
            "A(x)=A(x+1)": "constant coefficient 0",
            "A(x)+B(x)=x": "square system",
            "A(x)=x+A(A(x))": "arguments independent.*A",
            "A(x)=1/_x": "negative powers",
            "A(x)=x, B(x)=1/_x": "negative powers",
            (
                "A(x)=(_x/(1-_x))*(A(x)/(_x/(1-_x)))*(A(x)/(_x/(1-_x))-1)^2"
            ): "division by a formal power series with nonzero constant term",
        }
        for source, message in cases.items():
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(GeneratingFunctionEvaluationError, message),
            ):
                generating_function_coefficients(source, 5, symbol="A")

    def test_fixed_point_argument_validation_and_empty_prefix(self):
        source = "A(x)=1+x*A(x)"
        self.assertEqual(generating_function_coefficients(source, 0), ())
        self.assertEqual(
            generating_function_coefficients(source, 6),
            (Fraction(1),) * 6,
        )
        for symbol in (True, 1, ""):
            with self.subTest(symbol=symbol), self.assertRaises(TypeError):
                generating_function_coefficients(source, 3, symbol=symbol)
        with self.assertRaisesRegex(ValueError, "only select.*equation"):
            generating_function_coefficients("1+x", 3, symbol="A")

    def test_symbolic_infinite_product_requires_an_equation_solver(self):
        source = "Product_{k>0} 1/(1-x^k)^a_k"
        expression = parse_generating_function(source)

        self.assertIsInstance(expression, GFInfiniteProduct)
        for value in (source, expression):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "symbolic-product solver",
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

    def test_power_exponents_do_not_supply_index_divisibility(self):
        with self.assertRaisesRegex(
            GeneratingFunctionEvaluationError,
            "x degrees are all scaled by j\\[1\\]",
        ):
            generating_function_coefficients(
                "Sum(_x^(2^j[1])*_x^j[1],j[1]=1..infinity)",
                12,
            )

    def test_alternate_infinite_sum_bounds(self):
        self.assertEqual(
            generating_function_coefficients("Sum_{j>2} x^j/j", 8),
            tuple(Fraction(1, degree) if degree >= 3 else Fraction() for degree in range(8)),
        )
        self.assertEqual(
            generating_function_coefficients("Sum_{j=1..inf} phi(j)*x^j/j", 8),
            (
                Fraction(0),
                Fraction(1),
                Fraction(1, 2),
                Fraction(2, 3),
                Fraction(1, 2),
                Fraction(4, 5),
                Fraction(1, 3),
                Fraction(6, 7),
            ),
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
        catalogue_mismatches = []
        solved_systems = []
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
                try:
                    generating_function_coefficients(
                        expression,
                        min(4, len(structure.terms)),
                    )
                except GeneratingFunctionEvaluationError:
                    implicit_equations.append(structure.id)
                    continue
                coefficients = generating_function_coefficients(
                    expression,
                    len(structure.terms),
                )

            elif isinstance(expression, GFEquationSystem):
                coefficients = generating_function_coefficients(
                    expression,
                    len(structure.terms),
                    symbol=structure.symbol,
                )
                solved_systems.append(structure.id)

            elif "RootOf(" in source:
                with self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "no branch selector",
                ):
                    generating_function_coefficients(expression, len(structure.terms))
                unselected_roots.append(structure.id)
                continue

            elif "Complex(" in source:
                with self.assertRaisesRegex(
                    GeneratingFunctionEvaluationError,
                    "complex formal-series support",
                ):
                    generating_function_coefficients(expression, len(structure.terms))
                complex_forms.append(structure.id)
                continue
            else:
                coefficients = generating_function_coefficients(
                    expression,
                    len(structure.terms),
                )
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

            if not ordinary_match and not exponential_match:
                catalogue_mismatches.append(structure.id)
                continue

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

        self.assertEqual(len(ordinary), 554)
        self.assertEqual(len(exponential), 430)
        self.assertEqual(len(ordinary) + len(exponential), 984)
        self.assertEqual(complex_forms, [47])
        self.assertEqual(implicit_equations, [44, 95])
        self.assertEqual(catalogue_mismatches, [79, 91])
        self.assertEqual(solved_systems, [118])
        self.assertEqual(len(infinite_sums), 46)
        self.assertEqual(len(unselected_roots), 39)


if __name__ == "__main__":
    unittest.main()
