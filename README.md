# Encyclopedia of Combinatorial Structures

This is a modern re-implementation of the Encyclopedia of Combinatorial Structures, a database of combinatorial 
structures and their associated integer sequences, with an emphasis on sequences
that arise in the context of decomposable combinatorial structures. 

The database can be searched by the first terms in the sequence, keywords, generating functions, or closed forms.

The ECS is currently deployed at http://combstruct.netlify.app.
## Getting Started (Developer Installation)

### Prerequisites
- [Node.js](https://nodejs.org/) (version 18 or higher recommended)
- [npm](https://www.npmjs.com/) (comes with Node.js) or [yarn](https://yarnpkg.com/)

### Installation

1. Clone this repository:
   ```sh
   git clone https://codeberg.org/Radcliffe/encyclopedia-of-combinatorial-structures.git
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
If you are making changes to the data, please make edits in the `/structure` directory.

## Credits
The original ECS was created in 1998 by Stéphanie Petit at INRIA in Rocquencourt, France.
Unfortunately, it has been offline for several years. 

The underlying data is from Jérémie Lumbroso's Github repository
[jlumbroso/encyclopedia-of-combinatorial-structures-data](https://github.com/jlumbroso/encyclopedia-of-combinatorial-structures-data).

The site logo is adapted from a logo created by
<a href="//commons.wikimedia.org/wiki/User_talk:Tmigler" title="User talk:Tmigler">Tmigler</a>, 
<a href="https://creativecommons.org/licenses/by-sa/4.0" title="Creative Commons Attribution-Share Alike 4.0">CC BY-SA 4.0</a>, 
<a href="https://commons.wikimedia.org/w/index.php?curid=65928645">Link</a>.

Where names and descriptions of combinatorial structures were missing,
they were added from the corresponding [OEIS](https://oeis.org) entries.

The initial prototype was created using OpenAI ChatGPT, so it incorporates
the uncredited contributions of countless developers, on whose work the
model was trained without their consent. Please contact me if you believe 
any of your work has been used without proper attribution.

All other work is by David Radcliffe.