"""Tools for working with Encyclopedia of Combinatorial Structures data.

The public API parses Maple ``combstruct``-style specifications, computes exact
sequence terms, derives finite generating functions and selected quadratic
closed forms from specifications, and parses and exactly expands finite
elementary and supported principal ``LambertW`` generating functions in the ECS
catalogue, including faithful syntax trees for named implicit equations and
equation systems, exact fixed-point expansion for supported named-series
assignments, and unselected ``RootOf`` equations.
Indexed infinite sums are parsed with lexical summation-variable scope and
expanded when coefficientwise finiteness can be proved. The catalogue's
symbolic infinite product, indexed coefficients, and one-argument Maple
``Complex`` constructor are preserved explicitly.
"""

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _distribution_version

from .attributes import (
    AttributeBinary,
    AttributeCall,
    AttributeConstructor,
    AttributeEquationSystem,
    AttributeExpression,
    AttributeInteger,
    AttributeMomentSystem,
    AttributeParser,
    AttributeSeries,
    AttributeSpecification,
    AttributeSpecificationError,
    AttributeSymbol,
    SizeCall,
    agfeqns,
    agfmomentsolve,
    agfseries,
    parse_attribute_specification,
)
from .catalog import (
    Catalog,
    CatalogError,
    Structure,
    StructureNotFoundError,
    default_dataset,
    get_structure,
    iter_structures,
)
from .derivation import (
    UnsupportedGeneratingFunctionDerivation,
    derive_generating_function,
    gfeqns,
)
from .enumeration import (
    AtomObject,
    CombinatorialObject,
    ConstructionObject,
    EpsilonObject,
    StructureIterator,
    StructureValue,
    allstructs,
    finished,
    iterstructs,
    nextstruct,
)
from .generating_function import (
    GeneratingFunctionError,
    GeneratingFunctionEvaluationError,
    GeneratingFunctionParser,
    GFBinary,
    GFComplex,
    GFEquation,
    GFEquationSystem,
    GFExpression,
    GFFunction,
    GFIndex,
    GFIndexedCoefficient,
    GFInfiniteProduct,
    GFInfiniteSum,
    GFInteger,
    GFMultivariateSeriesCall,
    GFParseResult,
    GFRootOf,
    GFSeriesCall,
    GFTotient,
    GFUnary,
    GFVariable,
    UnsupportedGeneratingFunction,
    generating_function_coefficients,
    parse_generating_function,
)
from .operations import EmptyStructureClassError, count, draw, gfseries, gfsolve
from .predefined import (
    Combination,
    Composition,
    Partition,
    Permutation,
    PredefinedObject,
    PredefinedStructure,
    StructureSize,
    Subset,
)
from .sampling import (
    CountDirectedSampler,
    DrawAlgorithm,
    UnsupportedCountDirectedSampling,
)
from .specification import (
    Cardinality,
    Constructor,
    Expression,
    Parser,
    Reference,
    Specification,
    SpecificationError,
    expand_substitutions,
    parse_specification,
)
from .terms import (
    UnsupportedConstruction,
    compute_terms,
    load_record,
)

try:
    __version__ = _distribution_version("combstruct")
except _PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
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
    "ConstructionObject",
    "Constructor",
    "CountDirectedSampler",
    "DrawAlgorithm",
    "EmptyStructureClassError",
    "EpsilonObject",
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
    "generating_function_coefficients",
    "get_structure",
    "gfeqns",
    "gfseries",
    "gfsolve",
    "iter_structures",
    "iterstructs",
    "load_record",
    "nextstruct",
    "parse_attribute_specification",
    "parse_generating_function",
    "parse_specification",
]
