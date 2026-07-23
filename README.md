# Encyclopedia of Combinatorial Structures

This is a modern re-implementation of the Encyclopedia of Combinatorial Structures, a database of combinatorial 
structures and their associated integer sequences, with an emphasis on sequences
that arise in the context of decomposable combinatorial structures. 

The database can be searched by the first terms in the sequence, keywords, generating functions, or closed forms.
Every stored generating function has an explicit `gf_type`: `ordinary` (OGF)
for an unlabelled structure or `exponential` (EGF) for a labelled structure.

The ECS is currently deployed at http://combstruct.netlify.app.
## Getting Started (Developer Installation)

### Prerequisites
- [Node.js](https://nodejs.org/) (version 18 or higher recommended)
- [npm](https://www.npmjs.com/) (comes with Node.js) or [yarn](https://yarnpkg.com/)

### Installation

1. Clone this repository:
   ```sh
   git clone https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures.git
   cd encyclopedia-of-combinatorial-structures/react-app
   ```
2. Install dependencies:
   ```sh
   npm install
   # or
   yarn install
   ```

### Running the Development Server

Start the app in development mode:
```sh
npm run dev
# or
yarn dev
```

The app will be available at the URL printed in your terminal (usually http://localhost:5173/).

### Computing terms from a specification

The reusable evaluator is available as the pre-alpha
[`combstruct` Python package](https://pypi.org/project/combstruct/0.1.0a1/):

```sh
python -m pip install "combstruct==0.1.0a1"
```

See [`PYTHON_PACKAGE.md`](PYTHON_PACKAGE.md) for its installation,
Python API, command-line interface, current scope, and roadmap.
The detailed API reference is in [`docs/api.md`](docs/api.md).
Contributor setup and package quality checks are in
[`docs/development.md`](docs/development.md).

`python-tools/compute_terms.py` evaluates the Maple `combstruct`-style specifications stored in the ECS using exact arithmetic. It uses ordinary generating functions for unlabelled structures and exponential generating functions for labelled structures.

Compute 30 terms for an existing ECS record:

```sh
python3 python-tools/compute_terms.py --id 56 --terms 30
```

Evaluate a specification directly:

```sh
python3 python-tools/compute_terms.py \
  --spec '{S = Union(Epsilon,Prod(Z,S,S))}' \
  --unlabelled \
  --terms 12 \
  --plain
```

The supported constructors are `Union`, `Prod`, `Sequence`, `Set`, `Cycle`, and `PowerSet`, including ECS cardinality constraints such as `card = 2`, `card <= 3`, and `1 <= card`. Specifications may contain multiple mutually recursive equations.

Generate the public OEIS-style b-files:

```sh
python3 python-tools/generate_bfiles.py
```

This creates `react-app/public/b-files/bNNNNNN.txt` for every ECS record. Each file includes terms through `a(1000)` unless a term first exceeds 1,000 decimal digits, in which case that term and all subsequent terms are omitted.

### Building for Production

To build the app for production:
```sh
npm run build
# or
yarn build
```

The output will be in the `dist/` directory.

### Deployment

This is a static website and can be deployed to any static hosting service, such as GitHub Pages, Netlify, or Vercel.

### Changelog

Production changes are recorded in [`CHANGELOG.md`](CHANGELOG.md). Every change intended
for the `prod` branch should add an entry under **Unreleased**. When `prod` is deployed,
move those entries into a dated section and retain the empty **Unreleased** section for
future changes.

## Result format

*Adapted from the [original ECS documentation](https://web.archive.org/web/19991010004232/http://algo.inria.fr/encyclopedia/).*

The result of a successful search is a list of combinatorial structures with, 
for each of them:

  * Its [combstruct](https://www.maplesoft.com/support/help/Maple/view.aspx?path=combstruct) 
   [grammar specification](https://maplesoft.com/support/help/maple/view.aspx?path=combstruct%2fspecification); 
  * A sequence of integers: the $n$-th term (counting from 0) is the number of objects 
    of size $n$ defined by the specification. 
    This sequence is computed by the [Maple](https://www.maplesoft.com/products/Maple/) 
    function combstruct\[count\] which you can use to compute more terms; 
  * The generating function of this sequence. 
    When the objects are labeled, exponential generating functions are produced. 
    In the unlabeled universe, ordinary generating functions are used. 
    This generating function is obtained with combstruct\[gfsolve\];
  * A linear recurrence for $f(n)$, the number of objects of size $n$. 
    To obtain this recurrence, it is necessary that the generating function 
    be [holonomic](https://en.wikipedia.org/wiki/Holonomic_function). This recurrence is computed by 
    gfun\[holexprtodiffeq\] and gfun\[diffeqtorec\];
  * The closed form for these numbers $f(n)$ (computed either by Maple's [rsolve](https://www.maplesoft.com/support/help/Maple/view.aspx?path=rsolve) or 
    by [gfun](https://www.maplesoft.com/support/help/Maple/view.aspx?path=gfun)[ratpolytocoeff]);
  * The first term of the asymptotic expansion of $f(n)$ or $f(n)/n!$ as $n$ tends to infinity. 
    If the objects are unlabeled (ordinary generating functions), 
    these coefficients are the number of objects, 
    otherwise, in the labeled case (exponential generating functions), 
    they are the number of objects divided by $n!$. This asymptotic behaviour is computed by 
    [gdev](https://dl.acm.org/doi/10.1145/122520.122521)\[equivalent\] which you can use to 
    compute more terms of the expansion;
  * A description of the combinatorial structure;
  * Some references. When the sequence $(f(n))$ is in 
    [Sloane's Encyclopedia of Integer Sequences](https://oeis.org), 
    the references contain "EIS nb" with nb the sequence number in the EIS. 
    A reference can also contain the address (URL) of a Web page. 
    Most of the entries in this list are generated automatically. 
    In some cases, not all the entries could be found by programs, 
    and some of them are missing.

## Contributions

Contributions are welcome! Please fork the repository and submit a pull request with your changes.
If you are making changes to the data, please make edits in the `/structures` directory.

## Credits
The original ECS was created in 1998 by Stéphanie Petit at INRIA in Rocquencourt, France.
Unfortunately, it has been offline for several years. 

The underlying data is from Jérémie Lumbroso's Github repository
[jlumbroso/encyclopedia-of-combinatorial-structures-data](https://github.com/jlumbroso/encyclopedia-of-combinatorial-structures-data).

Names and descriptions were enriched from corresponding
[OEIS](https://oeis.org) entries. See [`NOTICE.md`](NOTICE.md) for exact
historical provenance, contributor credits, attribution, and licensing
information.

The initial prototype was created using OpenAI ChatGPT, so it incorporates
the uncredited contributions of countless developers, on whose work the
model was trained without their consent. Please contact me if you believe 
any of your work has been used without proper attribution.

All other work is by David Radcliffe.
