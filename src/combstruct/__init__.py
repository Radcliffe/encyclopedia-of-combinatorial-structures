"""Tools for working with Encyclopedia of Combinatorial Structures data.

The public API parses Maple ``combstruct``-style specifications, computes exact
sequence terms, derives finite generating functions and selected quadratic
closed forms from specifications, and parses and exactly expands finite
elementary and principal-at-zero ``LambertW`` generating functions in the ECS
catalogue, including faithful syntax trees for unselected ``RootOf`` equations.
Indexed infinite sums are parsed with lexical summation-variable scope.
"""

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _distribution_version

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
)
from .generating_function import (
    GeneratingFunctionError,
    GeneratingFunctionEvaluationError,
    GeneratingFunctionParser,
    GFBinary,
    GFExpression,
    GFFunction,
    GFIndex,
    GFInfiniteSum,
    GFInteger,
    GFRootOf,
    GFTotient,
    GFUnary,
    GFVariable,
    UnsupportedGeneratingFunction,
    generating_function_coefficients,
    parse_generating_function,
)
from .specification import (
    Cardinality,
    Constructor,
    Expression,
    Parser,
    Reference,
    Specification,
    SpecificationError,
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
    "Cardinality",
    "Catalog",
    "CatalogError",
    "Constructor",
    "Expression",
    "GFBinary",
    "GFExpression",
    "GFFunction",
    "GFIndex",
    "GFInfiniteSum",
    "GFInteger",
    "GFRootOf",
    "GFTotient",
    "GFUnary",
    "GFVariable",
    "GeneratingFunctionError",
    "GeneratingFunctionEvaluationError",
    "GeneratingFunctionParser",
    "Parser",
    "Reference",
    "Specification",
    "SpecificationError",
    "Structure",
    "StructureNotFoundError",
    "UnsupportedConstruction",
    "UnsupportedGeneratingFunction",
    "UnsupportedGeneratingFunctionDerivation",
    "__version__",
    "compute_terms",
    "default_dataset",
    "derive_generating_function",
    "generating_function_coefficients",
    "get_structure",
    "iter_structures",
    "load_record",
    "parse_generating_function",
    "parse_specification",
]
