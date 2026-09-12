---
name: paper-skeleton
description: Build and maintain a paper skeleton for a LaTeX manuscript, one load-bearing sentence per paragraph with its role in the argument, kept in an Obsidian vault as section files plus two generated canvases (reading order and argument map). Use when the user asks for a skeleton, reverse outline, or argument map of a paper, wants to see which claims a revision changed, or asks to sync the skeleton after editing the manuscript. Cards are tied to the tex by \label{sk|id}, so sync is exact.
license: MIT license
metadata:
    skill-author: Jun
---

# Paper skeleton

## What it is

A skeleton of a manuscript's main text: for every paragraph, the one sentence the paragraph exists to
deliver (its load-bearing sentence), the role that sentence plays in the argument, how the rest of the
paragraph hangs from it, and which other sentences depend on it. It lives in an Obsidian vault and is drawn
as two canvases. It serves three purposes: after a round of edits it reports which load-bearing sentences
changed and which paragraphs lost theirs; it gives one view of how the whole argument is built; and it is the
yardstick for cutting text (a sentence that nothing rests on can go).

The tool is `scripts/skeleton.py` (Python 3, standard library only). It is driven by one JSON config per vault
and never needs to be edited for a new paper.

## Three parts

1. **Identity, in the manuscript.** Each card's element carries `\label{sk|<id>}` in the tex, placed right
   after the sentence's period or after the run-in heading's closing brace. It produces no output (one line in
   the `.aux`); its only job is to let the tool find the element again after any edit. This is the only change
   the tool ever makes to the manuscript, and it makes it once, at bootstrap.
2. **Source, the section files.** `sections/00 Abstract.md` ... one file per section of the paper, one card
   per paragraph. A card is a heading (the card number), a header line (number, `file:line`, role, ★ for the
   section's load-bearing sentence), the sentence verbatim with a block id, a **What rests on it** paragraph,
   and optional **Relations** and **Left out** lines. These files are the only thing edited by hand. Grammar in
   `references/card-format.md`.
3. **Views, generated.** `Skeleton-graph.canvas` (reading order: one group per section, subsections as
   columns, arrows for the cross-references the text states), `Skeleton-argument.canvas` (argument map:
   contention on top, findings under the claims they support, judging rules along the bottom, boundaries on
   the right), and `Skeleton.md` (criterion, thesis, the numbered list of all sentences, cards left out of the
   map). Never edited by hand. Canvas cards are live embeds of the section files, so a text edit in a section
   file shows up on the canvas without a rebuild; a role, ★, card-list, or relation change needs `build`.

## Building one (new paper, once)

Announce each step to the user before running it; bootstrap edits their manuscript.

1. `python3 skeleton.py init <path/to/main.tex> --vault <vault dir>`. The tool follows the `\input` chain,
   keeps the files that hold prose, names the sections, detects box environments (`\newtcolorbox` and the like)
   and macros, finds the `.aux` for `\ref` numbers, and writes `skeleton.json`. Show the user the report it
   prints (sections in order with paragraph counts, environments with their classification, macro count) and
   fix anything wrong in `skeleton.json`: section order or titles, an environment that should be skipped or
   treated as a box, a macro whose rendering should be overridden (`"macros": {"symfoo": "Foo-X"}`).
2. `python3 skeleton.py bootstrap --vault <vault dir>` prints, per paragraph, where a label would go; with
   `--write` it writes `sections/` (one card per paragraph, sentence = the paragraph opener, role `unset`,
   What rests on it = TODO) and inserts the labels into the tex. Get an explicit go before `--write`. Afterwards
   the manuscript should compile to an identical PDF (same page count, same extracted text); offer that check.
3. The editorial pass, by hand, card by card: replace the opener with the load-bearing sentence when it is not
   the opener (move the label in the tex accordingly), set the role, mark one ★ per section, write What rests
   on it, add Relations where the text states a dependency. Criterion and roles in `references/criterion.md`.
   This is the only real time investment (one to two hours for an 80-paragraph paper). Do it in batches and
   let the user rule on the sentences you are unsure of.
4. `python3 skeleton.py build --vault <vault dir>`, then open the vault folder in Obsidian (no community
   plugins needed).

## Using one (every editing round)

- While editing the manuscript, ignore the skeleton.
- After the round (typically after the compile), run `python3 skeleton.py sync --vault <vault dir>` and read
  the three counts. `moved` needs no attention. `updated` prints a diff per card; a card tagged
  `(rewrite, re-judge the card)` needs its role and What rests on it re-read. `missing` means the element and
  its label are gone; handle each card by hand.
- Then read the census. `PROBLEM` lines are the four structural cases: a paragraph with no card (a new
  paragraph: add a label in the tex and a card in the section file, or leave it if it deserves none), a card
  whose paragraph is gone (delete the card), a paragraph holding two labels (a merge: keep one), a card with no
  label (the label was deleted: restore it or delete the card). A relation naming a card that does not exist
  is also reported.
- Report to the user in one line: the three counts and the census result; list `updated` rewrites and
  `missing` cards item by item. Never re-judge a card on your own.
- Editing a card means editing its section file only. A role or ★ change needs `build`; a text change does
  not.

## The criterion, short form

The load-bearing sentence is the sentence the paragraph exists to deliver: remove it and the paragraph has no
claim; the other sentences lead up to it or hang from it. When two qualify, the one later text depends on wins
(the antecedent of a back-reference, the opener of a parallel structure, the anchor of a box, abstract, or
conclusion sentence). In a procedure or definition block whose sentences are parallel details that no later
text cites, the run-in heading is the load-bearing element and the label sits after its brace. Boxes
(research questions, hypotheses, summaries) contribute the sentence other sections cite. One ★ per section.
Roles: claim, question, method, finding, boundary, nav. Full text with worked examples in
`references/criterion.md`.

## Rules that keep it cheap

- No line numbers in card prose (no `L14`, no `abs:12`): they drift and nothing checks them. Name another card
  by its number; name any other sentence by a description or a few quoted words.
- A new card needs both its label in the tex and its heading in the section file; a deleted card is removed in
  both. The census catches a half-done change either way.
- Do not give non-load-bearing sentences labels; do not draw on the canvases by hand; do not use Mermaid.
- `bootstrap` refuses to run on a vault that already has section files. To start over, delete `sections/`.
- `python3 skeleton.py check` runs the tool against a synthetic manuscript in a temp directory and is the one
  regression test; run it after changing the script.

## What it does not do

It does not judge whether a sentence that restates a card still holds after the card changed; it names the
cards joined by a Relations line and leaves the reading to the user. A change to a non-load-bearing sentence
inside a paragraph is not detected; the card's prose may then be stale until the card is next re-judged. The
sentence splitter protects common abbreviations (e.g., et al., Fig.) but not every one; a mis-split shows up as
a truncated `updated` diff, never silently.
