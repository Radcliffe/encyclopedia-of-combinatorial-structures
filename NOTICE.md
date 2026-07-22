# Notices and data provenance

## License scope

The `combstruct` distribution contains components under two licenses:

- the Python source code and the underlying ECS catalogue are distributed
  under the GNU Lesser General Public License version 2.1 only, whose text is
  in `LICENSE.md`; and
- the OEIS-derived names, descriptions, and later adaptations of that text are
  distributed under the Creative Commons Attribution-ShareAlike 4.0
  International license, whose text is in
  `LICENSES/CC-BY-SA-4.0.txt`.

The package metadata therefore uses the SPDX expression
`LGPL-2.1-only AND CC-BY-SA-4.0`. The two licenses apply to their respective
components; this expression does not claim that every file is offered under
both licenses.

## Encyclopedia of Combinatorial Structures

The bundled catalogue is derived from Jérémie Lumbroso's
[`encyclopedia-of-combinatorial-structures-data`](https://github.com/jlumbroso/encyclopedia-of-combinatorial-structures-data)
repository, which extracted the ECS subset of the INRIA Algorithms Project's
`algolib` version 17 distribution. That repository is distributed under the
GNU Lesser General Public License version 2.1 and contains the same
`LICENSE.md` text as this project.

The Encyclopedia of Combinatorial Structures was started in 1998 by
Stéphanie Petit-Halajda while visiting the Algorithms Project at INRIA
Rocquencourt. It built on work by many Algorithms Project contributors,
including contributors to `combstruct` and `gdev`. The upstream dataset README
contains additional history and credits.

## OEIS-derived text

This project's history records an OEIS enrichment in commit `aa28cd1`: 696
structure names and 703 descriptions were replaced with the exact titles of
their corresponding entries in
[The On-Line Encyclopedia of Integer Sequences](https://oeis.org/) (OEIS).
All 703 prior descriptions were missing; 158 prior names were missing and the
others were generic ECS labels. Names were curated further in later commits.
ECS records retain their OEIS references where available.

OEIS states that its content is available under the
[Creative Commons Attribution Share-Alike 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/)
and requests attribution to The Online Encyclopedia of Integer Sequences with
a link to OEIS or the applicable sequence entry. This project incorporated
OEIS entry titles into ECS `name` and `description` fields and subsequently
modified some names to make generic structure families distinguishable. Those
OEIS-derived fields and adaptations remain under CC BY-SA 4.0. The retained
`EIS` references identify applicable sequence entries.

This notice records provenance, attribution, and modifications; it does not
replace the applicable license texts or legal terms.
