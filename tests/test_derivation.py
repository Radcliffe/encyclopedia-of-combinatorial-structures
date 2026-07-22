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
    def test_unlabelled_sequence_derives_a_rational_ogf(self):
        expression = derive_generating_function(
            "{S = Sequence(Z)}",
            labelled=False,
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

    def test_labelled_set_derives_an_exponential_egf(self):
        expression = derive_generating_function("{S = Set(Z)}", labelled=True)

        self.assertEqual(expression, GFFunction("exp", GFVariable()))
        self.assertEqual(
            generating_function_coefficients(expression, 6),
            tuple(Fraction(1, factorial(degree)) for degree in range(6)),
        )

    def test_labelled_cycle_respects_a_lower_cardinality_bound(self):
        expression = derive_generating_function(
            "{S = Cycle(Z,2 <= card)}",
            labelled=True,
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

    def test_bounded_unlabelled_set_uses_cycle_index_substitution(self):
        expression = derive_generating_function(
            "{S = Set(Sequence(Z),card = 2)}",
            labelled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 8),
            tuple(Fraction(value) for value in (1, 1, 2, 2, 3, 3, 4, 4)),
        )

    def test_bounded_unlabelled_cycle_uses_totient_weights(self):
        expression = derive_generating_function(
            "{S = Cycle(Sequence(Z,1 <= card),card = 3)}",
            labelled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 9),
            tuple(Fraction(value) for value in (0, 0, 0, 1, 1, 2, 4, 5, 7)),
        )

    def test_named_acyclic_equations_are_expanded(self):
        equations = parse_specification("{A = Sequence(Z), S = Prod(Z,A)}")
        expression = derive_generating_function(
            equations,
            labelled=False,
            symbol="S",
        )

        self.assertEqual(
            generating_function_coefficients(expression, 6),
            tuple(Fraction(value) for value in (0, 1, 1, 1, 1, 1)),
        )

    def test_linear_self_recursion_derives_a_rational_function(self):
        expression = derive_generating_function(
            "{S = Union(Z,Prod(Z,S))}",
            labelled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 7),
            tuple(Fraction(value) for value in (0, 1, 1, 1, 1, 1, 1)),
        )

    def test_quadratic_self_recursion_selects_the_formal_series_root(self):
        expression = derive_generating_function(
            "{S = Union(Z,Prod(S,S))}",
            labelled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 8),
            tuple(Fraction(value) for value in (0, 1, 1, 2, 5, 14, 42, 132)),
        )

    def test_quadratic_root_handles_a_removable_singularity(self):
        expression = derive_generating_function(
            "{S = Union(Epsilon,Prod(Z,S,S))}",
            labelled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 8),
            tuple(Fraction(value) for value in (1, 1, 2, 5, 14, 42, 132, 429)),
        )

    def test_named_quadratic_equation_is_available_through_an_alias(self):
        expression = derive_generating_function(
            "{A = Union(Z,Prod(A,A)), S = A}",
            labelled=False,
        )

        self.assertEqual(
            generating_function_coefficients(expression, 7),
            tuple(Fraction(value) for value in (0, 1, 1, 2, 5, 14, 42)),
        )

    def test_labelled_quadratic_self_recursion_yields_egf_coefficients(self):
        expression = derive_generating_function(
            "{S = Union(Z,Prod(S,S))}",
            labelled=True,
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
                derive_generating_function(specification, labelled=False)

        with self.assertRaisesRegex(
            UnsupportedGeneratingFunctionDerivation,
            "not well founded",
        ):
            derive_generating_function("{S = Union(Z,S)}", labelled=False)

    def test_recursive_system_reports_the_cycle(self):
        with self.assertRaisesRegex(
            UnsupportedGeneratingFunctionDerivation,
            "A -> B -> A",
        ):
            derive_generating_function(
                "{A = Prod(Z,B), B = Union(Z,A), S = A}",
                labelled=False,
            )

    def test_infinite_unlabelled_cycle_index_forms_are_explicitly_unsupported(self):
        for specification, message in (
            ("{S = Set(Z)}", "unrestricted unlabelled Set"),
            ("{S = Cycle(Z)}", "unrestricted unlabelled Cycle"),
            ("{S = PowerSet(Z)}", "PowerSet"),
        ):
            with (
                self.subTest(specification=specification),
                self.assertRaisesRegex(
                    UnsupportedGeneratingFunctionDerivation,
                    message,
                ),
            ):
                derive_generating_function(specification, labelled=False)

    def test_invalid_inputs_and_specifications_are_rejected(self):
        with self.assertRaises(TypeError):
            derive_generating_function(1, labelled=False)
        with self.assertRaises(TypeError):
            derive_generating_function("{S = Z}", labelled=0)
        with self.assertRaises(TypeError):
            derive_generating_function("{S = Z}", labelled=False, symbol=1)
        with self.assertRaises(ValueError):
            derive_generating_function("{S = Z}", labelled=False, symbol="")
        with self.assertRaisesRegex(SpecificationError, "does not define"):
            derive_generating_function("{A = Z}", labelled=False)
        with self.assertRaisesRegex(SpecificationError, "Undefined symbol"):
            derive_generating_function("{S = Missing}", labelled=False)
        with self.assertRaisesRegex(SpecificationError, "Union does not accept"):
            derive_generating_function("{S = Union(Z,card = 1)}", labelled=False)
        with self.assertRaisesRegex(SpecificationError, "requires exactly one"):
            derive_generating_function("{S = Sequence(Z,Z)}", labelled=False)

    def test_catalogue_derivation_partition_and_exact_terms(self):
        derived = []
        unsupported: Counter[str] = Counter()

        for structure in Catalog():
            try:
                expression = derive_generating_function(
                    structure.specification,
                    labelled=structure.labeled,
                    symbol=structure.symbol,
                )
            except UnsupportedGeneratingFunctionDerivation as error:
                message = str(error)
                if message.startswith("Recursive"):
                    unsupported["recursive"] += 1
                elif "unrestricted unlabelled Set" in message:
                    unsupported["unlabelled set"] += 1
                elif "unrestricted unlabelled Cycle" in message:
                    unsupported["unlabelled cycle"] += 1
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
                labelled=structure.labeled,
                term_count=len(structure.terms),
                symbol=structure.symbol,
            )

            self.assertEqual(terms, structure.terms, f"ECS {structure.id}")
            self.assertEqual(tuple(independently_computed), terms, f"ECS {structure.id}")
            derived.append(structure.id)

        self.assertEqual(len(derived), 845)
        self.assertEqual(
            unsupported,
            Counter(
                {
                    "recursive": 188,
                    "unlabelled set": 21,
                    "unlabelled cycle": 14,
                    "powerset": 7,
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()
