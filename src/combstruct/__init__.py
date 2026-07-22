"""Tools for working with Encyclopedia of Combinatorial Structures data.

The public API parses Maple ``combstruct``-style specifications, computes exact
sequence terms, and parses the finite elementary generating-function syntax in
the ECS catalogue.
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
from .generating_function import (
    GeneratingFunctionError,
    GeneratingFunctionParser,
    GFBinary,
    GFExpression,
    GFFunction,
    GFInteger,
    GFUnary,
    GFVariable,
    UnsupportedGeneratingFunction,
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
    "GFInteger",
    "GFUnary",
    "GFVariable",
    "GeneratingFunctionError",
    "GeneratingFunctionParser",
    "Parser",
    "Reference",
    "Specification",
    "SpecificationError",
    "Structure",
    "StructureNotFoundError",
    "UnsupportedConstruction",
    "UnsupportedGeneratingFunction",
    "__version__",
    "compute_terms",
    "default_dataset",
    "get_structure",
    "iter_structures",
    "load_record",
    "parse_generating_function",
    "parse_specification",
]
