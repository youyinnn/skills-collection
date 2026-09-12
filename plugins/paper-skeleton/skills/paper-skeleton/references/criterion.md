# The load-bearing sentence, the roles, and the judgment calls

## Criterion

A paragraph's load-bearing sentence is the sentence the paragraph exists to deliver: remove it and the
paragraph has no claim; the other sentences either lead up to it (background, evidence, numbers) or hang from it
(refer back to it, parallel it, point to it).

When two sentences qualify, the one later text depends on wins:

- the antecedent of a back-reference ("that band" three sentences later needs its "the negligible band");
- the opener of a parallel structure (the first of "Neither ... / Both ..." carries the pair);
- the anchor of a summary box, abstract, or conclusion sentence (the sentence the box restates, not the
  restatement).

For a procedure or definition block whose sentences are parallel details that no later text cites (a data
preprocessing block listing the split of each dataset, a factor definition listing what an algorithm decides),
the run-in heading (`\textbf{Data Preprocessing.}`) is the load-bearing element: the card's sentence is the
heading text and the label sits after the heading's closing brace. A sentence stays the card only when it
states a claim, finding, rule, or design decision that later text depends on.

Boxes (research question boxes, hypothesis boxes, summary boxes) contribute the sentence other sections cite.
In a multi-item summary box that is usually the item the abstract or conclusion restates.

One sentence per section is the section's load-bearing sentence (★), the one its other paragraphs serve. The
paper's thesis is the ★ of the conclusion (and the ★ of the abstract, which should be the same claim).

## Roles

| role | color | what it marks |
|---|---|---|
| claim | `#D55E00` | what the article proposes, contributes, or establishes |
| question | `#E69F00` | the need, the research questions, the positioning against prior work |
| method | `#0072B2` | how the study is built and the rules it judges by |
| finding | `#009E73` | what the results show |
| boundary | `#CC79A7` | what limits or scopes the findings |
| nav | `#999999` | roadmap and pointers |
| unset | none | bootstrapped, not yet judged |

Colors are Okabe-Ito (colorblind-safe). A caveat that averages or scopes a finding is a boundary, not a
finding. A design sentence that a finding is judged by (a practical-relevance rule, a generalizability
criterion) is method and belongs on the argument map as a warrant (`licenses`).

## What rests on it

One paragraph per card, prose. It records two things: how the rest of the paragraph hangs from the sentence
(which sentences lead up to it, which elaborate it, which qualify it) and what elsewhere depends on it (which
box, abstract sentence, conclusion sentence, or later section restates or cites it). Name another card by its
number ("Feeds Summary-2 item III", "Anchors IX.1"); name any other sentence by a description or a few quoted
words ("the two 'Selecting by' sentences price it"). Never by line number.

## Relations

An optional line per card, `**Relations.** verb: target, target; verb: target`, targets being card numbers.
The verbs the canvases color: `delivered by` / `delivers` (blue, a promise and where it is kept), `anchors`
(green, evidence restated in the abstract or conclusion), `supports` (green, on the argument map: this finding
holds up that claim), `licenses` (blue, on the argument map: this rule is what that finding is judged by),
`qualifies` (purple, on the argument map: this boundary scopes that claim), `same claim as` (gray, one claim
at two ends of the paper). Any other verb (`cited in`, `restated in`, `premise of`, ...) is drawn gray on the
reading-order canvas. Only relations the text itself states are drawn.

A card that is neither a question, a method, nor navigation and has no `supports` / `licenses` / `qualifies` /
`same claim as` relation is listed in Skeleton.md as "no reason recorded"; give it a relation or a
`**Left out.** reason` line.

## Judgment calls worth remembering (from the first paper this was built on)

- Abstract: the sentence that proposes the framework beat the sentence that states the headline finding,
  because every other abstract sentence hangs from the proposal and the conclusion's ★ makes the same claim.
- Results verdict paragraph: the verdict sentence ("No cell reaches practical relevance") beat the sentence
  with the numbers, because the summary box restates the verdict; the numbers sentence is its evidence and the
  antecedent of a later "that band", which the card's prose records.
- A specificity section: the sentence drawing the inference ("the explanation-side advantage is thus specific
  to mix-based augmentation") beat the design sentence, by the author's ruling that the inference is what the
  conclusion cites.
- A three-line sentence (an enumeration broken over lines) is one element; the label goes at the end of its
  last line and the card's `file:line` is a range.
- A two-sentence line: the label goes right after the load-bearing sentence's period, mid-line.
