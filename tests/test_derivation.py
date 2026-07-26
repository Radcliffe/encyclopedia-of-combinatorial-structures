import unittest
from collections import Counter
from fractions import Fraction
from math import factorial

from combstruct import (
    Catalog,
    GFBinary,
    GFFunction,
    GFInteger,
    GFVariable,
    SpecificationError,
    UnsupportedGeneratingFunctionDerivation,
    compute_terms,
    derive_generating_function,
    generating_function_coefficients,
    parse_specification,
)


class GeneratingFunctionDerivationTests(unittest.TestCase):
    def test_unlabeled_sequence_derives_a_rational_ogf(self):
        expression = derive_generating_function(
            "{S = Sequence(Z)}",
            labeled=False,
        )

        self.assertEqual(
            expression,
            GFBinary(
                "/",
                GFInteger(1),
                GFBinary("-", GFInteger(1), GFVariable()),
            ),
        )
        self.assertEqual(
            generating_function_coefficients(expression, 6),
            (Fraction(1),) * 6,
        )

    def test_labeled_set_derives_an_exponential_egf(self):
        expression = derive_generating_function("{S = Set(Z)}", labeled=True)

        self.assertEqual(expression, GFFunction("exp", GFVariable()))
        self.assertEqual(
            generating_function_coefficients(expression, 6),
            tuple(Fraction(1, factorial(degree)) for degree in range(6)),
        )

    def test_labeled_cycle_respects_a_lower_cardinality_bound(self):
        expression = derive_generating_function(
            "{S = Cycle(Z,2 <= card)}",
            labeled=True,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 6),
            (
                Fraction(0),
                Fraction(0),
                Fraction(1, 2),
                Fraction(1, 3),
                Fraction(1, 4),
                Fraction(1, 5),
            ),
        )

    def test_bounded_unlabeled_set_uses_cycle_index_substitution(self):
        expression = derive_generating_function(
            "{S = Set(Sequence(Z),card = 2)}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 8),
            tuple(Fraction(value) for value in (1, 1, 2, 2, 3, 3, 4, 4)),
        )

    def test_bounded_unlabeled_cycle_uses_totient_weights(self):
        expression = derive_generating_function(
            "{S = Cycle(Sequence(Z,1 <= card),card = 3)}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 9),
            tuple(Fraction(value) for value in (0, 0, 0, 1, 1, 2, 4, 5, 7)),
        )

    def test_named_acyclic_equations_are_expanded(self):
        equations = parse_specification("{A = Sequence(Z), S = Prod(Z,A)}")
        expression = derive_generating_function(
            equations,
            labeled=False,
            symbol="S",
        )

        self.assertEqual(
            generating_function_coefficients(expression, 6),
            tuple(Fraction(value) for value in (0, 1, 1, 1, 1, 1)),
        )

    def test_linear_self_recursion_derives_a_rational_function(self):
        expression = derive_generating_function(
            "{S = Union(Z,Prod(Z,S))}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 7),
            tuple(Fraction(value) for value in (0, 1, 1, 1, 1, 1, 1)),
        )

    def test_quadratic_self_recursion_selects_the_formal_series_root(self):
        expression = derive_generating_function(
            "{S = Union(Z,Prod(S,S))}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 8),
            tuple(Fraction(value) for value in (0, 1, 1, 2, 5, 14, 42, 132)),
        )

    def test_quadratic_root_handles_a_removable_singularity(self):
        expression = derive_generating_function(
            "{S = Union(Epsilon,Prod(Z,S,S))}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 8),
            tuple(Fraction(value) for value in (1, 1, 2, 5, 14, 42, 132, 429)),
        )

    def test_named_quadratic_equation_is_available_through_an_alias(self):
        expression = derive_generating_function(
            "{A = Union(Z,Prod(A,A)), S = A}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 7),
            tuple(Fraction(value) for value in (0, 1, 1, 2, 5, 14, 42)),
        )

    def test_labeled_quadratic_self_recursion_yields_egf_coefficients(self):
        expression = derive_generating_function(
            "{S = Union(Z,Prod(S,S))}",
            labeled=True,
        )

        coefficients = generating_function_coefficients(expression, 7)
        terms = tuple(
            coefficient * factorial(degree) for degree, coefficient in enumerate(coefficients)
        )
        self.assertEqual(terms, (0, 1, 2, 12, 120, 1680, 30240))

    def test_higher_degree_and_nested_recursion_remain_explicitly_unsupported(self):
        for specification, message in (
            ("{S = Union(Z,Prod(S,S,S))}", "degree greater than two"),
            ("{S = Sequence(S)}", "inside Sequence"),
        ):
            with (
                self.subTest(specification=specification),
                self.assertRaisesRegex(
                    UnsupportedGeneratingFunctionDerivation,
                    message,
                ),
            ):
                derive_generating_function(specification, labeled=False)

        with self.assertRaisesRegex(
            UnsupportedGeneratingFunctionDerivation,
            "not well founded",
        ):
            derive_generating_function("{S = Union(Z,S)}", labeled=False)

    def test_mutual_linear_system_is_eliminated(self):
        expression = derive_generating_function(
            "{A = Prod(Z,B), B = Union(Z,A), S = A}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 7),
            tuple(Fraction(value) for value in (0, 0, 1, 1, 1, 1, 1)),
        )

    def test_mutual_quadratic_system_is_eliminated(self):
        expression = derive_generating_function(
            "{A = Union(B,Z), B = Prod(A,A), S = A}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 8),
            tuple(Fraction(value) for value in (0, 1, 1, 2, 5, 14, 42, 132)),
        )

    def test_three_symbol_quadratic_component_is_eliminated(self):
        expression = derive_generating_function(
            "{B = Union(C,Z), C = Prod(S,S), S = Union(B,C)}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 6),
            tuple(Fraction(value) for value in (0, 1, 2, 8, 40, 224)),
        )

    def test_dependent_recursive_components_are_solved_in_order(self):
        expression = derive_generating_function(
            "{B = Union(C,Z), C = Prod(B,Z), E = Union(S,B), S = Prod(C,E)}",
            labeled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 10),
            tuple(Fraction(value) for value in (0, 0, 0, 1, 2, 4, 7, 12, 20, 33)),
        )

    def test_mutual_cubic_system_remains_explicitly_unsupported(self):
        with self.assertRaisesRegex(
            UnsupportedGeneratingFunctionDerivation,
            "degree greater than two",
        ):
            derive_generating_function(
                "{B = Prod(S,S), C = Prod(S,B), S = Union(B,C,Z)}",
                labeled=False,
            )

    def test_component_with_multiple_feedback_symbols_remains_unsupported(self):
        with self.assertRaisesRegex(
            UnsupportedGeneratingFunctionDerivation,
            "removing one feedback symbol",
        ):
            derive_generating_function(
                "{A = Union(Z,Prod(Z,B),Prod(Z,C)), "
                "B = Union(Z,Prod(Z,A),Prod(Z,C)), "
                "C = Union(Z,Prod(Z,A),Prod(Z,B)), S = A}",
                labeled=False,
            )

    def test_infinite_unlabeled_cycle_index_forms_are_explicitly_unsupported(self):
        for specification, message in (
            ("{S = Set(Z)}", "unrestricted unlabeled Set"),
            ("{S = Cycle(Z)}", "unrestricted unlabeled Cycle"),
            ("{S = PowerSet(Z)}", "PowerSet"),
        ):
            with (
                self.subTest(specification=specification),
                self.assertRaisesRegex(
                    UnsupportedGeneratingFunctionDerivation,
                    message,
                ),
            ):
                derive_generating_function(specification, labeled=False)

    def test_invalid_inputs_and_specifications_are_rejected(self):
        with self.assertRaises(TypeError):
            derive_generating_function(1, labeled=False)
        with self.assertRaises(TypeError):
            derive_generating_function("{S = Z}", labeled=0)
        with self.assertRaises(TypeError):
            derive_generating_function("{S = Z}", labeled=False, symbol=1)
        with self.assertRaises(ValueError):
            derive_generating_function("{S = Z}", labeled=False, symbol="")
        with self.assertRaisesRegex(SpecificationError, "does not define"):
            derive_generating_function("{A = Z}", labeled=False)
        with self.assertRaisesRegex(SpecificationError, "Undefined symbol"):
            derive_generating_function("{S = Missing}", labeled=False)
        with self.assertRaisesRegex(SpecificationError, "Union does not accept"):
            derive_generating_function("{S = Union(Z,card = 1)}", labeled=False)
        with self.assertRaisesRegex(SpecificationError, "requires exactly one"):
            derive_generating_function("{S = Sequence(Z,Z)}", labeled=False)

    def test_catalogue_derivation_partition_and_exact_terms(self):
        derived = []
        unsupported: Counter[str] = Counter()

        for structure in Catalog():
            try:
                expression = derive_generating_function(
                    structure.specification,
                    labeled=structure.labeled,
                    symbol=structure.symbol,
                )
            except UnsupportedGeneratingFunctionDerivation as error:
                message = str(error)
                if message.startswith("Recursive"):
                    unsupported["recursive"] += 1
                elif "unrestricted unlabeled Set" in message:
                    unsupported["unlabeled set"] += 1
                elif "unrestricted unlabeled Cycle" in message:
                    unsupported["unlabeled cycle"] += 1
                elif "PowerSet" in message:
                    unsupported["powerset"] += 1
                else:
                    self.fail(f"Unexpected derivation error for ECS {structure.id}: {error}")
                continue

            coefficients = generating_function_coefficients(
                expression,
                len(structure.terms),
            )
            terms = tuple(
                coefficient * factorial(degree) if structure.labeled else coefficient
                for degree, coefficient in enumerate(coefficients)
            )
            independently_computed = compute_terms(
                structure.specification,
                labeled=structure.labeled,
                term_count=len(structure.terms),
                symbol=structure.symbol,
            )

            self.assertEqual(terms, structure.terms, f"ECS {structure.id}")
            self.assertEqual(tuple(independently_computed), terms, f"ECS {structure.id}")
            derived.append(structure.id)

        self.assertEqual(len(derived), 888)
        self.assertEqual(
            unsupported,
            Counter(
                {
                    "recursive": 145,
                    "unlabeled set": 21,
                    "unlabeled cycle": 14,
                    "powerset": 7,
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()
