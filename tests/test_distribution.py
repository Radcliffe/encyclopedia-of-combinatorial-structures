import json
import unittest
from dataclasses import FrozenInstanceError
from fractions import Fraction
from importlib.metadata import PackageNotFoundError, distribution, version

import combstruct
import combstruct.terms
from combstruct import (
    Cardinality,
    Catalog,
    Constructor,
    GeneratingFunctionEvaluationError,
    GeneratingFunctionParser,
    GFBinary,
    GFComplex,
    GFEquation,
    GFEquationSystem,
    GFFunction,
    GFIndexedCoefficient,
    GFInfiniteProduct,
    GFInteger,
    GFRootOf,
    GFSeriesCall,
    GFVariable,
    Parser,
    Reference,
    SpecificationError,
    Structure,
    StructureNotFoundError,
    UnsupportedGeneratingFunctionDerivation,
    __version__,
    agfeqns,
    agfmomentsolve,
    agfseries,
    allstructs,
    compute_terms,
    count,
    default_dataset,
    derive_generating_function,
    draw,
    finished,
    generating_function_coefficients,
    get_structure,
    gfeqns,
    gfseries,
    gfsolve,
    iter_structures,
    iterstructs,
    load_record,
    nextstruct,
    parse_attribute_specification,
    parse_generating_function,
    parse_specification,
)
from combstruct.specification import Parser as SpecificationParser
from combstruct.terms import Parser as LegacyTermsParser


class PublicApiTests(unittest.TestCase):
    def test_top_level_exports_are_an_explicit_public_surface(self):
        expected = {
            "AtomObject",
            "AttributeBinary",
            "AttributeCall",
            "AttributeConstructor",
            "AttributeEquationSystem",
            "AttributeExpression",
            "AttributeInteger",
            "AttributeMomentSystem",
            "AttributeParser",
            "AttributeSeries",
            "AttributeSpecification",
            "AttributeSpecificationError",
            "AttributeSymbol",
            "Cardinality",
            "Catalog",
            "CatalogError",
            "Combination",
            "CombinatorialObject",
            "Composition",
            "CountDirectedSampler",
            "Constructor",
            "ConstructionObject",
            "DrawAlgorithm",
            "EpsilonObject",
            "EmptyStructureClassError",
            "Expression",
            "GFBinary",
            "GFComplex",
            "GFEquation",
            "GFEquationSystem",
            "GFExpression",
            "GFFunction",
            "GFIndex",
            "GFIndexedCoefficient",
            "GFInfiniteProduct",
            "GFInfiniteSum",
            "GFInteger",
            "GFMultivariateSeriesCall",
            "GFParseResult",
            "GFRootOf",
            "GFSeriesCall",
            "GFTotient",
            "GFUnary",
            "GFVariable",
            "GeneratingFunctionError",
            "GeneratingFunctionEvaluationError",
            "GeneratingFunctionParser",
            "Parser",
            "Partition",
            "Permutation",
            "PredefinedObject",
            "PredefinedStructure",
            "Reference",
            "SizeCall",
            "Specification",
            "SpecificationError",
            "Structure",
            "StructureIterator",
            "StructureNotFoundError",
            "StructureSize",
            "StructureValue",
            "Subset",
            "UnsupportedConstruction",
            "UnsupportedCountDirectedSampling",
            "UnsupportedGeneratingFunction",
            "UnsupportedGeneratingFunctionDerivation",
            "__version__",
            "agfeqns",
            "agfmomentsolve",
            "agfseries",
            "allstructs",
            "compute_terms",
            "count",
            "default_dataset",
            "derive_generating_function",
            "draw",
            "expand_substitutions",
            "finished",
            "gfseries",
            "gfsolve",
            "gfeqns",
            "generating_function_coefficients",
            "get_structure",
            "iter_structures",
            "iterstructs",
            "load_record",
            "nextstruct",
            "parse_generating_function",
            "parse_attribute_specification",
            "parse_specification",
        }

        self.assertEqual(set(combstruct.__all__), expected)
        self.assertTrue(all(hasattr(combstruct, name) for name in expected))
        self.assertIs(combstruct.count, count)
        self.assertIs(combstruct.gfseries, gfseries)
        self.assertIs(combstruct.gfsolve, gfsolve)
        self.assertIs(combstruct.allstructs, allstructs)
        self.assertIs(combstruct.iterstructs, iterstructs)
        self.assertIs(combstruct.nextstruct, nextstruct)
        self.assertIs(combstruct.finished, finished)
        self.assertIs(combstruct.draw, draw)
        self.assertIs(combstruct.gfeqns, gfeqns)
        self.assertIs(combstruct.agfeqns, agfeqns)
        self.assertIs(combstruct.agfseries, agfseries)
        self.assertIs(combstruct.agfmomentsolve, agfmomentsolve)
        self.assertIs(combstruct.parse_attribute_specification, parse_attribute_specification)

    def test_generating_function_parser_is_available_from_package(self):
        expression = GeneratingFunctionParser("exp(_x)/(1-_x)^2").parse()

        self.assertEqual(expression, parse_generating_function("exp(_x)/(1-_x)^2"))
        self.assertEqual(
            expression,
            GFBinary(
                "/",
                GFFunction("exp", GFVariable()),
                GFBinary(
                    "^",
                    GFBinary("-", GFInteger(1), GFVariable()),
                    GFInteger(2),
                ),
            ),
        )

    def test_generating_function_coefficients_are_available_from_package(self):
        self.assertEqual(
            generating_function_coefficients("1/(1-_x)", 5),
            (1, 1, 1, 1, 1),
        )
        self.assertEqual(
            generating_function_coefficients(
                "Sum(_x^j[1]/j[1],j[1]=1..infinity)",
                5,
            ),
            (Fraction(0), Fraction(1), Fraction(1, 2), Fraction(1, 3), Fraction(1, 4)),
        )
        self.assertEqual(
            generating_function_coefficients(
                "-LambertW(-1/2*exp(-1/2+1/2*_x))-1/2+1/2*_x",
                5,
            ),
            (Fraction(0), Fraction(1), Fraction(1, 2), Fraction(2, 3), Fraction(13, 12)),
        )
        self.assertEqual(
            generating_function_coefficients(
                "A(x)=x+(A(x)^2+A(x^2))/2",
                8,
            ),
            (0, 1, 1, 1, 2, 3, 6, 11),
        )
        system = get_structure(118)
        self.assertIsNotNone(system.generating_function)
        self.assertEqual(
            generating_function_coefficients(
                system.generating_function,
                8,
                symbol=system.symbol,
            ),
            system.terms[:8],
        )
        self.assertTrue(issubclass(GeneratingFunctionEvaluationError, ValueError))

    def test_rootof_syntax_tree_is_available_from_package(self):
        expression = parse_generating_function("RootOf(_Z-_x)")

        self.assertEqual(
            expression,
            GFRootOf(GFBinary("-", GFVariable("_Z"), GFVariable())),
        )

    def test_complex_syntax_tree_is_available_from_package(self):
        expression = parse_generating_function("Complex(-1/2)")

        self.assertEqual(
            expression,
            GFComplex(
                GFBinary(
                    "/",
                    combstruct.GFUnary("-", GFInteger(1)),
                    GFInteger(2),
                ),
            ),
        )

    def test_implicit_equation_syntax_tree_is_available_from_package(self):
        equation = parse_generating_function("A(x)=x+A(x)^2")

        self.assertEqual(
            equation,
            GFEquation(
                GFSeriesCall("A", GFVariable()),
                GFBinary(
                    "+",
                    GFVariable(),
                    GFBinary("^", GFSeriesCall("A", GFVariable()), GFInteger(2)),
                ),
            ),
        )

    def test_equation_system_syntax_tree_is_available_from_package(self):
        system = parse_generating_function("A(x)=x,B(x)=A(x)")

        self.assertEqual(
            system,
            GFEquationSystem(
                (
                    GFEquation(GFSeriesCall("A", GFVariable()), GFVariable()),
                    GFEquation(
                        GFSeriesCall("B", GFVariable()),
                        GFSeriesCall("A", GFVariable()),
                    ),
                ),
            ),
        )

    def test_alternate_infinite_sum_syntax_is_available_from_package(self):
        expression = parse_generating_function("Sum_{j>2} x^j/j")

        self.assertIsInstance(expression, combstruct.GFInfiniteSum)
        assert isinstance(expression, combstruct.GFInfiniteSum)
        self.assertEqual(expression.index, combstruct.GFIndex(1))
        self.assertEqual(expression.lower_bound, 3)

    def test_patterned_ellipsis_is_available_from_package(self):
        source = get_structure(57).generating_function

        self.assertIsNotNone(source)
        assert source is not None
        equation = parse_generating_function(source)
        self.assertIsInstance(equation, GFEquation)
        assert isinstance(equation, GFEquation)
        self.assertIsInstance(equation.right, GFBinary)
        assert isinstance(equation.right, GFBinary)
        self.assertIsInstance(equation.right.right, GFFunction)
        assert isinstance(equation.right.right, GFFunction)
        self.assertIsInstance(equation.right.right.argument, combstruct.GFInfiniteSum)

    def test_symbolic_infinite_product_is_available_from_package(self):
        source = get_structure(44).generating_function

        self.assertIsNotNone(source)
        assert source is not None
        equation = parse_generating_function(source)
        self.assertIsInstance(equation, GFEquation)
        assert isinstance(equation, GFEquation)
        self.assertIsInstance(equation.left, GFInfiniteProduct)
        assert isinstance(equation.left, GFInfiniteProduct)
        self.assertIsInstance(equation.left.factor, GFBinary)
        assert isinstance(equation.left.factor, GFBinary)
        self.assertIsInstance(equation.left.factor.right, GFBinary)
        assert isinstance(equation.left.factor.right, GFBinary)
        self.assertIsInstance(equation.left.factor.right.right, GFIndexedCoefficient)

    def test_generating_function_derivation_is_available_from_package(self):
        expression = derive_generating_function("{S = Sequence(Z)}", labelled=False)

        self.assertEqual(
            generating_function_coefficients(expression, 5),
            (1, 1, 1, 1, 1),
        )
        self.assertTrue(issubclass(UnsupportedGeneratingFunctionDerivation, ValueError))

    def test_legacy_term_module_exports_the_original_script_surface(self):
        expected = {
            "Cardinality",
            "CoefficientCompiler",
            "CoefficientNode",
            "Constructor",
            "EulerSelectionNode",
            "Evaluator",
            "ExpNode",
            "FixedPowerSetNode",
            "Expression",
            "InverseOneMinusNode",
            "LiteralNode",
            "LogOneMinusNode",
            "Parser",
            "ProductNode",
            "Reference",
            "ReferenceNode",
            "ScaleNode",
            "Series",
            "SpecificationError",
            "SubstituteNode",
            "SumNode",
            "TOKEN_RE",
            "UnlabelledCycleNode",
            "UnsupportedConstruction",
            "add_series",
            "atom_series",
            "binomial_row",
            "build_argument_parser",
            "compact_number",
            "component_bounds",
            "compute_terms",
            "decimal_digit_count",
            "default_dataset",
            "divide_exact",
            "divisors",
            "euler_totient",
            "integer_value",
            "is_nonnegative_integer",
            "labelled_cycle_series",
            "labelled_set_series",
            "load_record",
            "main",
            "multiply_series",
            "one_series",
            "power_series",
            "product_series",
            "require_nonnegative_integers",
            "scale_series",
            "sequence_series",
            "substitute_power",
            "unlabelled_cycle_series",
            "unlabelled_selection_series",
            "zero_series",
        }

        self.assertEqual(set(combstruct.terms.__all__), expected)
        self.assertTrue(all(hasattr(combstruct.terms, name) for name in expected))

    def test_runtime_version_matches_installed_metadata(self):
        try:
            installed_version = version("combstruct")
        except PackageNotFoundError:
            installed_version = "0+unknown"

        self.assertEqual(__version__, installed_version)

    def test_installed_metadata_describes_both_component_licenses(self):
        try:
            installed = distribution("combstruct")
        except PackageNotFoundError:
            self.skipTest("distribution metadata is unavailable in an uninstalled checkout")

        installed_files = {str(path) for path in installed.files or ()}
        if not any(".dist-info/" in path for path in installed_files):
            self.skipTest("wheel metadata is unavailable in a source checkout")

        self.assertEqual(
            installed.metadata["License-Expression"],
            "LGPL-2.1-only AND CC-BY-SA-4.0",
        )
        self.assertTrue(any(path.endswith("licenses/LICENSE.md") for path in installed_files))
        self.assertTrue(
            any(
                ".dist-info/licenses/" in path and path.endswith("/CC-BY-SA-4.0.txt")
                for path in installed_files
            )
        )
        self.assertTrue(any(path.endswith("licenses/NOTICE.md") for path in installed_files))

    def test_parser_and_term_computation_are_available_from_package(self):
        equations = Parser("{S = Sequence(Z,card <= 2)}").parse()

        self.assertIn("S", equations)
        self.assertEqual(
            compute_terms(
                "{S = Union(Epsilon,Prod(Z,S,S))}",
                labelled=False,
                term_count=8,
            ),
            [1, 1, 2, 5, 14, 42, 132, 429],
        )

    def test_distribution_contains_the_complete_ecs_catalogue(self):
        dataset = default_dataset()
        if dataset.is_dir():
            record_count = len(list(dataset.glob("ecs*/*.json")))
        else:
            with dataset.open(encoding="utf-8") as source:
                record_count = len(json.load(source))

        self.assertEqual(record_count, 1075)
        self.assertEqual(load_record(dataset, 56)["name"], "Rooted identity trees")


class CatalogTests(unittest.TestCase):
    def test_catalogue_ids_are_complete_and_ordered(self):
        catalog = Catalog()

        self.assertEqual(len(catalog), 1075)
        self.assertEqual(catalog.ids, tuple(range(1, 1076)))
        self.assertIn(56, catalog)
        self.assertNotIn(0, catalog)
        self.assertNotIn(True, catalog)

    def test_get_returns_an_immutable_typed_structure(self):
        catalog = Catalog()
        structure = catalog.get(56)

        self.assertIsInstance(structure, Structure)
        self.assertEqual(structure.name, "Rooted identity trees")
        self.assertEqual(structure.terms[:8], (0, 1, 1, 1, 2, 3, 6, 12))
        self.assertTrue(all(isinstance(term, int) for term in structure.terms))
        self.assertIs(catalog.get(56), structure)
        with self.assertRaises(FrozenInstanceError):
            structure.name = "changed"

    def test_ecs_79_matches_oeis_counted_class(self):
        structure = Catalog().get(79)

        self.assertEqual(structure.symbol, "B")
        self.assertEqual(structure.terms[:8], (0, 1, 1, 2, 5, 12, 36, 104))
        self.assertEqual(
            compute_terms(
                structure.specification,
                labelled=structure.labeled,
                term_count=len(structure.terms),
                symbol=structure.symbol,
            ),
            list(structure.terms),
        )
        self.assertEqual(
            generating_function_coefficients(
                structure.generating_function,
                len(structure.terms),
            ),
            tuple(Fraction(term) for term in structure.terms),
        )

    def test_optional_symbolic_fields_use_none(self):
        structure = get_structure(123)

        self.assertIsNone(structure.generating_function)
        self.assertIsNone(structure.generating_function_type)
        self.assertIsNone(structure.recurrence)
        self.assertIsNone(structure.closed_form)
        self.assertIsNone(structure.asymptotic_equivalent)

    def test_record_conversion_uses_canonical_ecs_field_names(self):
        structure = get_structure(6)
        record = structure.as_record()

        self.assertEqual(record["labeled"], structure.labeled)
        self.assertEqual(record["gf_type"], structure.generating_function_type)
        self.assertEqual(record["gf"], structure.generating_function)
        self.assertEqual(record["closedform"], structure.closed_form)
        self.assertEqual(Structure.from_record(record), structure)

    def test_default_iteration_is_in_identifier_order(self):
        iterator = iter_structures()

        self.assertEqual([next(iterator).id for _ in range(3)], [1, 2, 3])

    def test_every_canonical_record_has_a_valid_typed_model(self):
        structures = list(Catalog())

        self.assertEqual(sum(item.generating_function is not None for item in structures), 1028)
        self.assertEqual(
            sum(item.generating_function_type == "ordinary" for item in structures),
            577,
        )
        self.assertEqual(
            sum(item.generating_function_type == "exponential" for item in structures),
            451,
        )
        self.assertEqual(sum(item.recurrence is not None for item in structures), 867)
        self.assertEqual(sum(item.closed_form is not None for item in structures), 792)
        self.assertEqual(
            sum(item.asymptotic_equivalent is not None for item in structures),
            938,
        )
        for structure in structures:
            with self.subTest(structure_id=structure.id):
                self.assertEqual(Structure.from_record(structure.as_record()), structure)

    def test_missing_structure_has_a_specific_error(self):
        with self.assertRaisesRegex(StructureNotFoundError, "#0"):
            Catalog().get(0)


class SpecificationParserTests(unittest.TestCase):
    def test_function_api_builds_the_documented_syntax_tree(self):
        equations = parse_specification(
            "{S = Set(A[1],1 <= card), A[1] = Sequence(Z,card <= 2)}",
        )

        self.assertEqual(
            equations,
            {
                "S": Constructor(
                    "Set",
                    (Reference("A[1]"),),
                    Cardinality(1, None),
                ),
                "A[1]": Constructor(
                    "Sequence",
                    (Reference("Z"),),
                    Cardinality(0, 2),
                ),
            },
        )

    def test_public_and_legacy_parser_imports_are_identical(self):
        self.assertIs(Parser, SpecificationParser)
        self.assertIs(Parser, LegacyTermsParser)

    def test_every_canonical_ecs_specification_parses(self):
        for structure in Catalog():
            with self.subTest(structure_id=structure.id):
                equations = parse_specification(structure.specification)
                self.assertIn(structure.symbol, equations)

    def test_malformed_syntax_has_a_specific_exception(self):
        for specification in ("", "{S = Sequence(Z)", "{S = Sequence(@)}"):
            with self.subTest(specification=specification), self.assertRaises(SpecificationError):
                parse_specification(specification)


if __name__ == "__main__":
    unittest.main()
