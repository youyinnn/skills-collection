# Vault layout and card grammar

```
<vault>/
  skeleton.json              config written by init, edited by hand when the report is wrong
  sections/
    00 Abs Abstract.md       one file per section of the paper, in reading order (two-digit prefix)
    01 I Introduction.md
    ...
  Skeleton-graph.canvas      generated
  Skeleton-argument.canvas   generated
  Skeleton.md                generated
```

## skeleton.json

```json
{
  "main_tex": "/abs/path/to/main.tex",
  "aux": "output/main.aux",                 // relative to main.tex's directory; null if none was found
  "sections": [
    {"tex": "sections/intro.tex", "file": "01 I Introduction", "title": "Introduction", "num": "I", "short": "intro"}
  ],
  "boxes": ["rqbox", "sumbox"],             // environments whose whole body is one card
  "skip_envs": [],                          // environments to ignore, added to the built-in list (figure, table, equation, ...)
  "macros": {"symrcapvnl": "RCAP-VNL"}      // rendering overrides, macro name without the backslash
}
```

`tex` is relative to the directory of `main_tex`. `file` is the section file's name without `.md`. `num` is the
prefix of the card numbers in that file. `short` is the file's name inside `file:line` references.

## A section file

```
---
section: V
title: Overall Impacts of Factors
tex: sections/exp/rq1.tex
source_commit: 68da0ac (clean)
updated: 2026-09-12
---

# Overall Impacts of Factors

<one intro sentence, free text>

### V.1
**V.1** · `rq1:9` · method
To answer RQ-1, 12 hypotheses are derived on both the majority and minority class groups based on a hypothesis pattern. ^v1

**What rests on it.** Twelve hypotheses from one pattern; the sentence after it splits them by factor.

## V-A Interaction Between Factors

### V-A.3
**★ V-A.3** · `rq1:32` · boundary
The RCAP effects reported in Sections V-B and VI establish whether a factor affects RCAP and are averaged over the factor not under test. ^va3

**What rests on it.** The averaging caveat: RCAP effects describe no single level of the other factor.
**Relations.** qualifies: VI-C.1; cited in: Summary-1
**Left out.** restates III.0
```

Rules the parser enforces:

- `### <num>` starts a card; the next line is `**<num>**` (or `**★ <num>**`), ` · `, the location in backticks,
  ` · `, the role. The location is `<short>:<line>` or `<short>:<first>-<last>` for an element broken over
  lines. Location and sentence are rewritten by `sync`; do not maintain them by hand.
- The sentence is one line ending in ` ^<block id>`. The block id is the identity of the card: it must equal the
  `<id>` in the tex label `\label{sk|<id>}`, lowercase letters, digits, and hyphens only, unique across the
  vault. Keep it stable; rename the heading freely.
- A blank line, then `**What rests on it.** ` and one paragraph of prose on the same line.
- Optionally, on the next lines, `**Relations.** verb: target, target; verb: target` and `**Left out.** reason`.
  Targets are card numbers as they appear in headings.
- `## <title>` between cards opens a subsection (a column on the reading-order canvas).
- Roles: claim, question, method, finding, boundary, nav, unset.

## The label in the tex

`\label{sk|<block id>}` immediately after the element it marks: after the sentence's terminal punctuation
(`... on average.\label{sk|vic4}`), even mid-line when the line holds two sentences; after the closing brace of
a run-in heading (`\textbf{Data Preprocessing.}\label{sk|iva2}`); at the end of the last line when the sentence
runs over several lines. `\label` has no typesetting effect there (LaTeX's `\@bsphack`/`\@esphack` keep the
spacing) and produces one `\newlabel{sk|...}` line in the `.aux`. Duplicated labels are reported both by LaTeX
("multiply defined") and by the census.
