# ECS Python maintenance tools

These repository scripts curate ECS data and generate assets for the website.
They are not part of the public `combstruct` distribution.

## Environment

The tools require Python 3.12 or newer. From the repository root, create an
environment and install both the package and the maintenance-tools project:

```console
python3.12 -m venv python-tools/.venv
python-tools/.venv/bin/python -m pip install -e . -e python-tools
```

`combstruct` is also declared as a dependency of this tools project. Installing
from PyPI therefore uses the released package when a repository checkout is not
being developed at the same time.

## Generating b-files

`generate_bfiles.py` uses the public `combstruct` catalogue and exact term
evaluator APIs. With no dataset argument it reads the canonical catalogue from
the installed package (or the repository's `structures` directory during
editable development):

```console
python-tools/.venv/bin/python python-tools/generate_bfiles.py
```

Use `--dataset PATH` to read another canonical record directory or a historical
consolidated JSON mapping. `--id` may be repeated to generate only selected ECS
records; `--output`, `--max-index`, `--max-digits`, and `--jobs` control the
generation run.

The evaluator regression suite imports the documented top-level `combstruct`
API and reads records through `Catalog`. The historical `compute_terms.py`
entry point remains a compatibility wrapper and has a dedicated command-line
smoke test.

## Maple and OEIS validation

`write_maple_scripts.py` uses the same public catalogue API to create the
historical Maple `combstruct[count]` input and to compare Maple or locally
stored OEIS output with ECS terms. Its default input is the bundled catalogue;
its default text files remain `maple_script.txt` and `maple_output.txt` beside
the script.

The module functions also accept explicit catalogue, output, and OEIS-data
paths. This keeps maintenance runs independent of the current working
directory and allows validation against a selected catalogue without changing
checked-in artifacts.
