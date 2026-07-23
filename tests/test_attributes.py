import unittest
from fractions import Fraction

from combstruct import (
    AttributeBinary,
    AttributeCall,
    AttributeConstructor,
    AttributeInteger,
    AttributeSpecificationError,
    AttributeSymbol,
    GFBinary,
    GFEquation,
    GFInfiniteSum,
    GFMultivariateSeriesCall,
    GFVariable,
    SizeCall,
    agfeqns,
    agfmomentsolve,
    agfseries,
    parse_attribute_specification,
)


class AttributeGrammarTests(unittest.TestCase):
    def test_parser_preserves_mirrored_constructors_and_linear_values(self):
        parsed = parse_attribute_specification(
            "{path(T)=Union(0,Prod(0,path(T)+size(T),2*path(T)+size(T)-1))}",
        )

        self.assertEqual(
            parsed[("path", "T")],
            AttributeConstructor(
                "Union",
                (
                    AttributeInteger(0),
                    AttributeConstructor(
                        "Prod",
                        (
                            AttributeInteger(0),
                            AttributeBinary(
                                "+",
                                AttributeCall("path", "T"),
                                SizeCall("T"),
                            ),
                            AttributeBinary(
                                "-",
                                AttributeBinary(
                                    "+",
                                    AttributeBinary(
                                        "*",
                                        AttributeInteger(2),
                                        AttributeCall("path", "T"),
                                    ),
                                    SizeCall("T"),
                                ),
                                AttributeInteger(1),
                            ),
                        ),
                    ),
                ),
            ),
        )

    def test_parser_preserves_atomic_symbolic_constants(self):
        parsed = parse_attribute_specification(
            "{cost(Bit)=Union(sq,sq+mul)}",
        )

        self.assertEqual(
            parsed[("cost", "Bit")],
            AttributeConstructor(
                "Union",
                (
                    AttributeSymbol("sq"),
                    AttributeBinary(
                        "+",
                        AttributeSymbol("sq"),
                        AttributeSymbol("mul"),
                    ),
                ),
            ),
        )

    def test_leaf_distribution_matches_maple_documented_binary_tree_example(self):
        series = agfseries(
            "{N=Atom,T=Union(N,Prod(N,T,T))}",
            "{leaf(T)=Union(1,Prod(0,leaf(T),leaf(T)))}",
            labelled=False,
            term_count=10,
            attributes={"u": "leaf"},
        )

        self.assertEqual(series["T"].variables, ("x", "u"))
        self.assertEqual(series["T"].coefficient(1, u=1), 1)
        self.assertEqual(series["T"].coefficient(3, u=2), 1)
        self.assertEqual(series["T"].coefficient(5, u=3), 2)
        self.assertEqual(series["T"].coefficient(7, u=4), 5)
        self.assertEqual(series["T"].coefficient(9, u=5), 14)
        self.assertEqual(series["T"].coefficient(7, u=3), 0)

    def test_agfeqns_marks_leaf_values_in_recursive_calls(self):
        system = agfeqns(
            "{T=Union(Z,Prod(Z,T,T))}",
            "{leaf(T)=Union(1,Prod(0,leaf(T),leaf(T)))}",
            labelled=False,
            attributes={"u": "leaf"},
        )

        x = GFVariable()
        u = GFVariable("u")
        call = GFMultivariateSeriesCall("T", (x, u))
        self.assertEqual(system.variables, ("_x", "u"))
        self.assertEqual(
            system.equations,
            (
                GFEquation(
                    GFMultivariateSeriesCall("T", (x, u)),
                    GFBinary(
                        "+",
                        GFBinary("*", x, u),
                        GFBinary(
                            "*",
                            GFBinary("*", x, call),
                            call,
                        ),
                    ),
                ),
            ),
        )

    def test_agfeqns_size_dependencies_shift_the_size_argument(self):
        system = agfeqns(
            "{T=Union(Z,Prod(Z,T,T))}",
            "{path(T)=Union(0,Prod(0,path(T)+size(T),path(T)+size(T)))}",
            labelled=False,
            attributes={"u": "path"},
        )

        right = system.equations[0].right
        shifted_call = GFMultivariateSeriesCall(
            "T",
            (GFBinary("*", GFVariable(), GFVariable("u")), GFVariable("u")),
        )
        self.assertEqual(
            right,
            GFBinary(
                "+",
                GFVariable(),
                GFBinary(
                    "*",
                    GFBinary("*", GFVariable(), shifted_call),
                    shifted_call,
                ),
            ),
        )

    def test_unlabelled_set_equations_power_size_and_attribute_variables(self):
        system = agfeqns(
            "{T=Set(Z)}",
            "{marks(T)=Set(1)}",
            labelled=False,
            attributes={"u": "marks"},
        )

        self.assertTrue(
            self._contains_type(system.equations[0].right, GFInfiniteSum),
        )

    def test_agfmomentsolve_returns_factorial_moment_series(self):
        equations = agfeqns(
            "{T=Union(Z,Prod(Z,T,T))}",
            "{leaf(T)=Union(1,Prod(0,leaf(T),leaf(T)))}",
            labelled=False,
            attributes={"u": "leaf"},
        )

        moments = agfmomentsolve(equations, 2, term_count=10)

        self.assertEqual(moments.series("T", 0)[7], 5)
        self.assertEqual(moments.series("T", 1)[7], 20)
        self.assertEqual(moments.series("T", 2)[7], 60)

    def test_agfmomentsolve_includes_mixed_moments(self):
        equations = agfeqns(
            "{bit=Union(zero,one),zero=Atom,one=Atom,S=Sequence(bit,card=2)}",
            "{ones(bit)=Union(0,1),ones(S)=Sequence(ones(bit)),"
            "weight(bit)=Union(2,3),weight(S)=Sequence(weight(bit))}",
            labelled=False,
            attributes={"u": "ones", "v": "weight"},
        )

        moments = agfmomentsolve(equations, 1, term_count=3)

        self.assertEqual(moments.series("S", 0, 0)[2], 4)
        self.assertEqual(moments.series("S", 1, 0)[2], 4)
        self.assertEqual(moments.series("S", 0, 1)[2], 20)
        self.assertEqual(moments.series("S", 1, 1)[2], 22)

    def test_symbolic_costs_remain_symbolic_in_equations_and_bind_for_series(self):
        grammar = "{Bit=Union(zero,one),zero=Atom,one=Atom,Chain=Sequence(Bit,card=2)}"
        attribute_grammar = "{cost(Bit)=Union(sq,sq+mul),cost(Chain)=Sequence(cost(Bit))}"
        equations = agfeqns(
            grammar,
            attribute_grammar,
            labelled=False,
            attributes={"u": "cost"},
        )

        self.assertEqual(equations.parameters, ("mul", "sq"))
        self.assertTrue(
            self._contains_value(equations.equations[0].right, GFVariable("sq")),
        )
        with self.assertRaisesRegex(AttributeSpecificationError, "Missing values"):
            agfseries(
                grammar,
                attribute_grammar,
                labelled=False,
                term_count=3,
                attributes={"u": "cost"},
            )
        with self.assertRaisesRegex(AttributeSpecificationError, "Unknown atomic"):
            agfseries(
                grammar,
                attribute_grammar,
                labelled=False,
                term_count=3,
                attributes={"u": "cost"},
                parameters={"sq": 1, "mul": 2, "other": 3},
            )
        with self.assertRaisesRegex(TypeError, "must be integers"):
            agfseries(
                grammar,
                attribute_grammar,
                labelled=False,
                term_count=3,
                attributes={"u": "cost"},
                parameters={"sq": 1, "mul": True},
            )

        series = agfseries(
            grammar,
            attribute_grammar,
            labelled=False,
            term_count=3,
            attributes={"u": "cost"},
            parameters={"sq": 1, "mul": 2},
        )
        moments = agfmomentsolve(
            equations,
            1,
            term_count=3,
            parameters={"sq": 1, "mul": 2},
        )

        self.assertEqual(series["Chain"].coefficient(2, u=2), 1)
        self.assertEqual(series["Chain"].coefficient(2, u=4), 2)
        self.assertEqual(series["Chain"].coefficient(2, u=6), 1)
        self.assertEqual(moments.series("Chain", 1)[2], 16)

    def test_atomic_values_can_be_linear_coefficients(self):
        grammar = "{T=Union(Z,Prod(Z,T))}"
        attribute_grammar = "{cost(T)=Union(sq,Prod(0,mul*cost(T)))}"

        equations = agfeqns(
            grammar,
            attribute_grammar,
            labelled=False,
            attributes={"u": "cost"},
        )
        series = agfseries(
            grammar,
            attribute_grammar,
            labelled=False,
            term_count=4,
            attributes={"u": "cost"},
            parameters={"sq": 2, "mul": 3},
        )

        transformed = GFMultivariateSeriesCall(
            "T",
            (
                GFVariable(),
                GFBinary("^", GFVariable("u"), GFVariable("mul")),
            ),
        )
        self.assertTrue(
            self._contains_value(equations.equations[0].right, transformed),
        )
        self.assertEqual(series["T"].coefficient(1, u=2), 1)
        self.assertEqual(series["T"].coefficient(2, u=6), 1)
        self.assertEqual(series["T"].coefficient(3, u=18), 1)

        with self.assertRaisesRegex(
            AttributeSpecificationError,
            "conflict with generating variables",
        ):
            agfeqns(
                grammar,
                "{cost(T)=Union(u,Prod(0,cost(T)))}",
                labelled=False,
                attributes={"u": "cost"},
            )

    def test_labeled_coefficients_use_egf_normalization(self):
        series = agfseries(
            "{T=Prod(Z,Z)}",
            "{marks(T)=Prod(1,1)}",
            labelled=True,
            term_count=4,
            attributes={"u": "marks"},
        )

        self.assertEqual(series["T"].coefficient(2, u=2), Fraction(1))
        self.assertEqual(
            sum(
                coefficient
                for exponent, coefficient in series["T"].coefficients.items()
                if exponent[0] == 2
            ),
            Fraction(1),
        )

    def test_iterative_attribute_constructors_sum_member_values(self):
        series = agfseries(
            "{bit=Union(zero,one),zero=Atom,one=Atom,S=Sequence(bit,card=2)}",
            "{ones(bit)=Union(0,1),ones(S)=Sequence(ones(bit))}",
            labelled=False,
            term_count=3,
            attributes={"u": "ones"},
        )

        self.assertEqual(series["S"].coefficient(2, u=0), 1)
        self.assertEqual(series["S"].coefficient(2, u=1), 2)
        self.assertEqual(series["S"].coefficient(2, u=2), 1)

    def test_multiple_attributes_produce_joint_coefficients(self):
        series = agfseries(
            "{bit=Union(zero,one),zero=Atom,one=Atom,S=Sequence(bit,card=2)}",
            "{ones(bit)=Union(0,1),ones(S)=Sequence(ones(bit)),"
            "weight(bit)=Union(2,3),weight(S)=Sequence(weight(bit))}",
            labelled=False,
            term_count=3,
            attributes={"u": "ones", "v": "weight"},
        )

        self.assertEqual(series["S"].coefficient(2, u=1, v=5), 2)

    def test_missing_rules_use_default_recursive_propagation(self):
        series = agfseries(
            "{bit=Union(zero,one),zero=Atom,one=Atom,S=Sequence(bit,card=2)}",
            "{ones(bit)=Union(0,1)}",
            labelled=False,
            term_count=3,
            attributes={"u": "ones"},
        )

        self.assertEqual(series["S"].coefficient(2, u=0), 1)
        self.assertEqual(series["S"].coefficient(2, u=1), 2)
        self.assertEqual(series["S"].coefficient(2, u=2), 1)

    def test_acyclic_attributes_can_depend_on_other_attributes(self):
        grammar = "{T=Union(Z,Prod(Z,T))}"
        attribute_grammar = "{a(T)=Union(1,Prod(0,a(T))),b(T)=Union(2,Prod(0,b(T)))+a(T)}"
        attributes = {"u": "a", "v": "b"}

        series = agfseries(
            grammar,
            attribute_grammar,
            labelled=False,
            term_count=4,
            attributes=attributes,
        )
        equations = agfeqns(
            grammar,
            attribute_grammar,
            labelled=False,
            attributes=attributes,
        )

        self.assertEqual(series["T"].coefficient(1, u=1, v=3), 1)
        self.assertEqual(series["T"].coefficient(2, u=1, v=4), 1)
        recursive_call = GFMultivariateSeriesCall(
            "T",
            (
                GFVariable(),
                GFBinary("*", GFVariable("u"), GFVariable("v")),
                GFVariable("v"),
            ),
        )
        self.assertTrue(
            self._contains_value(equations.equations[0].right, recursive_call),
        )

    def test_invalid_attribute_grammars_are_rejected(self):
        grammar = "{T=Union(Z,Prod(Z,T))}"
        cases = (
            (
                "{size(T)=0}",
                AttributeSpecificationError,
                "cannot be redefined",
            ),
            (
                "{cost(T)=Union(0,Prod(0,cost(T)*size(T)))}",
                AttributeSpecificationError,
                "must be linear",
            ),
            (
                "{cost(Missing)=0}",
                AttributeSpecificationError,
                "Undefined structure",
            ),
            (
                "{other(T)=0}",
                AttributeSpecificationError,
                "no marker",
            ),
            (
                "{cost(T)=Prod(0,cost(T))}",
                AttributeSpecificationError,
                "does not match",
            ),
        )
        for attribute_grammar, error, message in cases:
            with (
                self.subTest(attribute_grammar=attribute_grammar),
                self.assertRaisesRegex(error, message),
            ):
                agfseries(
                    grammar,
                    attribute_grammar,
                    labelled=False,
                    term_count=4,
                    attributes={"u": "cost"},
                )

        with self.assertRaisesRegex(AttributeSpecificationError, "circular"):
            agfseries(
                grammar,
                "{cost(T)=Union(0,Prod(0,cost(T)))+other(T),"
                "other(T)=Union(0,Prod(0,other(T)))+cost(T)}",
                labelled=False,
                term_count=4,
                attributes={"u": "cost", "v": "other"},
            )

    @staticmethod
    def _contains_type(expression, expected_type):
        if isinstance(expression, expected_type):
            return True
        if isinstance(expression, GFBinary):
            return AttributeGrammarTests._contains_type(
                expression.left,
                expected_type,
            ) or AttributeGrammarTests._contains_type(expression.right, expected_type)
        argument = getattr(expression, "argument", None)
        if argument is not None:
            return AttributeGrammarTests._contains_type(argument, expected_type)
        summand = getattr(expression, "summand", None)
        if summand is not None:
            return AttributeGrammarTests._contains_type(summand, expected_type)
        return False

    @staticmethod
    def _contains_value(expression, expected):
        if expression == expected:
            return True
        if isinstance(expression, GFBinary):
            return AttributeGrammarTests._contains_value(
                expression.left,
                expected,
            ) or AttributeGrammarTests._contains_value(expression.right, expected)
        argument = getattr(expression, "argument", None)
        if argument is not None:
            return AttributeGrammarTests._contains_value(argument, expected)
        return False


if __name__ == "__main__":
    unittest.main()
