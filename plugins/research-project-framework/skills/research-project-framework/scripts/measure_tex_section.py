#!/usr/bin/env python3
"""Measure one or more .tex sections of the draft with the same counting functions as the sample
scripts: words, blocks, sentences, median and longest sentence, sentences over 40 words, citation
groups per 100 words, formulas, figures and tables.

  python scripts/measure_tex_section.py path/to/section/background.tex [more .tex] [--long]
  (--long also prints every sentence over 40 words)
"""
import argparse
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intro_stats import count_citations, word_count  # noqa: E402

DISPLAY_MATH = re.compile(r"\\begin\{(equation\*?|align\*?|gather\*?|displaymath)\}.*?\\end\{\1\}"
                          r"|(?<!\\)\\\[.*?(?<!\\)\\\]", re.S)
FLOAT = re.compile(r"\\begin\{(figure\*?|table\*?|tabular\*?|wrapfigure|algorithm)\}.*?\\end\{\1\}", re.S)
CITE = re.compile(r"~?\\cite[a-zA-Z]*\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")
KEEP_ARG = re.compile(r"\\(?:textbf|emph|textit|textsc|texttt|mbox)\{([^{}]*)\}")
DROP_LINE = re.compile(r"^\s*\\(?:section|subsection|label|input|begin|end)\b")
TWO_SENTENCES = re.compile(r"[.!?][\"')]?\s+[A-Z]")
ABBREV = ("e.g.", "i.e.", "et al.", "vs.", "cf.", "Fig.", "Eq.", "Sec.", "No.")
FORMULA_LINE = "<<=>>"   # no letters or digits, so it never counts as a word when it sits inside a line


def normalize(tex):
    """(lines, formulas, floats, keys): cleaned lines, blank where the file has a blank line, the
    number of display formulas and of floats removed, and the citation keys in order of first
    appearance."""
    formulas = len(DISPLAY_MATH.findall(tex))
    floats = len(FLOAT.findall(tex))
    tex = FLOAT.sub(FORMULA_LINE, DISPLAY_MATH.sub(FORMULA_LINE, tex))
    keys = []

    def cite(m):
        ks = [k.strip() for k in m.group(1).split(",") if k.strip()]
        if not ks:
            return " "
        for k in ks:
            if k not in keys:
                keys.append(k)
        return " [" + ", ".join(str(keys.index(k) + 1) for k in ks) + "]"

    lines = []
    for line in tex.split("\n"):
        if line.strip().startswith("%") or DROP_LINE.match(line):
            continue
        line = re.sub(r"(?<!\\)%.*$", "", line)
        line = CITE.sub(cite, line)
        line = re.sub(r"\\ref\{[^}]*\}", "1", line)
        line = re.sub(r"\$[^$]*\$", " X ", line)
        line = re.sub(r"\\\\(?:\[[^\]]*\])?", " ", line)   # line breaks such as \\ and \\[4pt]
        line = re.sub(r"^\s*\\item\s*", "", line)
        for _ in range(3):
            line = KEEP_ARG.sub(r"\1", line)
        line = re.sub(r"\\[a-zA-Z]+\*?", " ", line)
        line = line.replace("~", " ").replace("\\%", "%").replace("``", '"').replace("''", '"')
        lines.append(line.replace("{", "").replace("}", "").strip())
    return lines, formulas, floats, keys


def measure(tex):
    lines, formulas, floats, keys = normalize(tex)
    blocks, cur = [], []
    for line in lines + [""]:
        if line:
            if line != FORMULA_LINE:
                cur.append(line)
        elif cur:
            blocks.append(cur)
            cur = []
    sents = [s for b in blocks for s in b]
    lens = [word_count(s) for s in sents]
    words = sum(lens)
    groups, refs = count_citations("\n".join(sents))
    two = []
    for s in sents:
        t = s
        for a in ABBREV:
            t = t.replace(a, a.replace(".", "_"))
        if TWO_SENTENCES.search(t):
            two.append(s)
    return dict(words=words, blocks=[sum(word_count(s) for s in b) for b in blocks], sentences=len(sents),
                median=statistics.median(lens) if lens else 0, mean=round(statistics.mean(lens), 1) if lens else 0,
                max=max(lens) if lens else 0, long40=sum(1 for n in lens if n >= 40), long50=sum(1 for n in lens if n >= 50),
                cite_groups=groups, cite_refs=refs, keys=len(keys),
                per100w=round(100 * groups / words, 2) if words else 0, formulas=formulas, floats=floats,
                two_sentence_lines=two, long_sentences=[(n, s) for n, s in zip(lens, sents) if n >= 40])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--long", action="store_true", help="list the sentences of 40 words or more")
    args = ap.parse_args()
    for path in args.files:
        with open(path, encoding="utf-8") as fh:
            m = measure(fh.read())
        print(f"{os.path.basename(path)}: {m['words']} words, {len(m['blocks'])} blocks {m['blocks']}, "
              f"{m['sentences']} sentences (median {m['median']:g}, mean {m['mean']}, max {m['max']}, "
              f"40+ {m['long40']}, 50+ {m['long50']}), {m['cite_groups']} citation groups from {m['keys']} keys, "
              f"{m['per100w']} per 100 words, {m['formulas']} formulas, {m['floats']} floats removed")
        for s in m["two_sentence_lines"]:
            print(f"  two sentences on one line: {s[:100]}")
        if args.long:
            for n, s in m["long_sentences"]:
                print(f"  {n} words: {s[:120]}")


if __name__ == "__main__":
    main()
