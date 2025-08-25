# Encyclopedia of Combinatorial Structures

# Overview

This repository is a modern re-implementation of the Encyclopedia of Combinatorial Structures, a database of combinatorial 
structures and their associated integer sequences, with an emphasis on sequences
that arise in the context of decomposable combinatorial structures. 

The database can be searched by the first terms in the sequence, keywords, generating functions, or closed forms.

# Getting Started (Developer Installation)

## Prerequisites
- [Node.js](https://nodejs.org/) (version 18 or higher recommended)
- [npm](https://www.npmjs.com/) (comes with Node.js) or [yarn](https://yarnpkg.com/)

## Installation

1. Clone this repository:
   ```sh
   git clone https://github.com/jlumbroso/encyclopedia-of-combinatorial-structures.git
   cd encyclopedia-of-combinatorial-structures/react-app
   ```
2. Install dependencies:
   ```sh
   npm install
   # or
   yarn install
   ```

## Running the Development Server

Start the app in development mode:
```sh
npm run dev
# or
yarn dev
```

The app will be available at the URL printed in your terminal (usually http://localhost:5173/).

## Building for Production

To build the app for production:
```sh
npm run build
# or
yarn build
```

The output will be in the `dist/` directory.

# Result format

The result of a successful search is a list of combinatorial structures with, 
for each of them:

  * Its [combstruct](https://www.maplesoft.com/support/help/Maple/view.aspx?path=combstruct) 
   [grammar specification](https://maplesoft.com/support/help/maple/view.aspx?path=combstruct%2fspecification); 
  * A sequence of integers: the $(n+1)$st term of this sequence is the number of objects 
    of size $n$ defined by the specification. 
    This sequence is computed by the [Maple](https://www.maplesoft.com/products/Maple/) 
    function combstruct[count] which you can use to compute more terms; 
  * The generating function of this sequence. 
    When the objects are labelled, exponential generating functions are produced. 
    In the unlabelled universe, ordinary generating functions are used. 
    This generating function is obtained with combstruct[gfsolve];
  * A linear recurrence for $f(n)$, the number of objects of size $n$. 
    In order to obtain this recurrence, it is necessary that the generating function 
    be [holonomic](https://en.wikipedia.org/wiki/Holonomic_function). This recurrence is computed by 
    gfun[holexprtodiffeq] and gfun[diffeqtorec];
  * The closed form for these numbers $f(n)$ (computed either by Maple's [rsolve](https://www.maplesoft.com/support/help/Maple/view.aspx?path=rsolve) or 
    by [gfun](https://www.maplesoft.com/support/help/Maple/view.aspx?path=gfun)[ratpolytocoeff]);
  * The first term of the asymptotic expansion of $f(n)$ or $f(n)/n!$ as $n$ tends to infinity. 
    If the objects are unlabelled (ordinary generating functions), 
    these coefficients are the number of objects, 
    otherwise, in the labelled case (exponential generating functions), 
    they are the number of objects divided by $n!$. This asymptotic behaviour is computed by 
    [gdev](https://dl.acm.org/doi/10.1145/122520.122521)[equivalent] which you can use to 
    compute more terms of the expansion;
  * A description of the combinatorial structure;
  * Some references. When the sequence $(f(n))$ is in 
    [Sloane's Encyclopedia of Integer Sequences](https://oeis.org), 
    the references contain "EIS nb" with nb the sequence number in the EIS. 
    A reference can also contain the address (URL) of a Web page. 
    Most of the entries in this list are generated automatically. 
    In some cases, not all the entries could be found by programs 
    and some of there are missing.

# Credits
The original ECS was created in 1998 by Stéphanie Petit at INRIA in Rocquencourt, France.
Unfortunately, it has been offline for several years. 

The underlying data is from Jérémie Lumbroso's Github repository
[jlumbroso/encyclopedia-of-combinatorial-structures-data](https://github.com/jlumbroso/encyclopedia-of-combinatorial-structures-data).
