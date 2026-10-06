#!/usr/bin/env python3
"""Related-work statistics over a venue sample: position of the section, length, subsections,
positioning sentences, first-of-its-kind claims and search sentences. Reuses the cutting and
cleaning of intro_stats.py.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/relwork_stats.py          # relwork_features.csv, relwork_subsections.csv, relwork_report.md
  python scripts/relwork_stats.py --dump   # prints the cut sections
"""
import argparse
import csv
import os
import re
import statistics
from collections import Counter

from config import VENUE  # noqa: E402
from intro_stats import (OUT, RUNIN, _HEAD, _plain, body_text, clean_paragraphs,
                             count_citations, paper_paths, split_sentences, word_count)

RW_TITLE = r"(?:Background\s*(?:and|&)\s*)?Related\s+Works?\b[^\n]*"
HASH_HEAD = re.compile(_HEAD + r"(\d+(?:\.\d+)*)\s+([A-Za-z][^\n]*)", re.M)
BOLD_HEAD = re.compile(r"^\*\*(\d+(?:\.\d+)*)\s+([A-Za-z][^\n*]*)\*\*\s*$", re.M)
REFS = re.compile(_HEAD + r"(?:\d+\s+)?References", re.M | re.I)
RW = re.compile(RW_TITLE, re.I)

# Assistant-set sentence classes; tune them for a new venue.
POSITION = re.compile(r"\b(?:unlike|in contrast|differs?|different from|orthogonal|complementary|whereas"
                      r"|our (?:work|study|approach|paper|method|framework|analysis|benchmark|focus)"
                      r"|this (?:work|paper|study)\b|in this paper|we (?:instead|differ|focus|extend|complement"
                      r"|build on|go beyond|are the first))\b", re.I)
NOVELTY = re.compile(r"to (?:the best of )?our knowledge|\bthe first\b|\bnone of (?:these|them|the|which)"
                     r"|\bno (?:prior|existing|previous|other) (?:work|study|studies|research|approach|effort)", re.I)
SEARCH = re.compile(r"\b(?:we searched|literature search|search strings?|search terms?|Google Scholar|DBLP|Scopus"
                    r"|IEEE Xplore|ACM Digital Library|snowball|systematic (?:literature )?(?:review|mapping)"
                    r"|we (?:reviewed|surveyed) (?:the )?(?:literature|papers|studies|prior work))\b", re.I)
OWN_PRIOR = re.compile(r"\bour (?:prior|previous|earlier|recent) (?:work|study|paper)\b|\bin our (?:prior|previous|earlier)\b", re.I)
NUM_RUNIN = re.compile(r"^\d+\.\d+\.\d+\s+[A-Z]")


def headings(md):
    """Every numbered heading as (start, end, number tuple, title), both forms, in order."""
    out = []
    for rx in (HASH_HEAD, BOLD_HEAD):
        for m in rx.finditer(md):
            out.append((m.start(), m.end(), tuple(int(x) for x in m.group(1).split(".")), m.group(2).strip()))
    return sorted(out)


def extract_relwork(md):
    """(number tuple, title, raw text, next heading title, previous heading title, top-level count)."""
    hs = headings(md)
    refs = REFS.search(md)
    limit = refs.start() if refs else len(md)
    hs = [h for h in hs if h[0] < limit]
    top = [h for h in hs if len(h[2]) == 1]
    hit = next((i for i, h in enumerate(hs) if RW.match(h[3])), None)
    if hit is None:
        raise ValueError("no related-work heading")
    s, e, num, title = hs[hit]
    end = next((h[0] for h in hs[hit + 1:] if h[2][:len(num)] != num), limit)
    prev = next((h[3] for h in reversed(hs[:hit]) if len(h[2]) == len(num)), "")
    nxt = next((h[3] for h in hs[hit + 1:] if len(h[2]) <= len(num)), "")
    return num, title, md[e:end], nxt, prev, len(top)


def split_subsections(raw, num):
    """[(title or '', text)] of the cut: text before the first nested heading, then each nested heading."""
    hs = [h for h in headings(raw) if len(h[2]) == len(num) + 1]
    parts, pos, title = [], 0, ""
    for s, e, _, t in hs:
        parts.append((title, raw[pos:s]))
        pos, title = e, t
    parts.append((title, raw[pos:]))
    return [(t, x) for t, x in parts if x.strip()]


def sentences(text):
    return split_sentences(_plain(text))


def count_sentences(paras, rx):
    return sum(1 for p in paras for s in sentences(p) if rx.search(s))


def features(name, md):
    with open(md, encoding="utf-8") as fh:
        text = fh.read()
    num, title, raw, nxt, prev, n_top = extract_relwork(text)
    parts = split_subsections(raw, num)
    sub_rows, paras = [], []
    for i, (t, x) in enumerate(parts, 1):
        ps = clean_paragraphs(x)
        paras += ps
        if t:
            sub_rows.append(dict(paper=name, sub=i, title=t, paragraphs=len(ps), words=sum(word_count(p) for p in ps),
                                 last_para_positions=bool(ps) and bool(POSITION.search(_plain(ps[-1])))))
    words = sum(word_count(p) for p in paras)
    body = word_count(body_text(text))
    groups, refs = count_citations(raw)
    combined = title.lower().startswith("background")
    placement = "subsection" if len(num) > 1 else ("front" if num[0] <= 3 else "back")
    if placement == "front" and combined:
        placement = "front-combined"
    return dict(
        paper=name, year=name[3:7], section=".".join(map(str, num)), title=title,
        placement=placement, sections_total=n_top, position=round(num[0] / n_top, 2), prev=prev, next=nxt,
        paragraphs=len(paras), words=words, body_words=body, share=round(words / body, 3) if body else None,
        subsections=len(sub_rows), words_per_sub=round(words / len(sub_rows)) if sub_rows else None,
        cite_groups=groups, cite_refs=refs, cites_per_100w=round(100 * groups / words, 1) if words else None,
        runin_paras=sum(1 for p in paras if RUNIN.match(p) or NUM_RUNIN.match(p)),
        table=bool(re.search(r"^\|", raw, re.M)),
        position_sents=count_sentences(paras, POSITION),
        position_paras=sum(1 for p in paras if POSITION.search(_plain(p))),
        last_para_positions=bool(paras) and bool(POSITION.search(_plain(paras[-1]))),
        subs_ending_positioned=sum(1 for r in sub_rows if r["last_para_positions"]),
        novelty_sents=count_sentences(paras, NOVELTY),
        search_sents=count_sentences(paras, SEARCH),
        own_prior_sents=count_sentences(paras, OWN_PRIOR),
    ), sub_rows, parts


# ---------------------------------------------------------------- report

def q(values):
    v = sorted(x for x in values if x is not None)
    if not v:
        return "n=0"
    med = statistics.median(v)
    lo, hi = v[len(v) // 4], v[(3 * len(v)) // 4]
    return f"n={len(v)}, median {med:g}, quartiles {lo:g} to {hi:g}, range {v[0]:g} to {v[-1]:g}"


def table(header, rows):
    return "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n" + \
        "".join("| " + " | ".join(str(c) for c in r) + " |\n" for r in rows)


def report(rows, subs, missing=()):
    by = lambda k: Counter(r[k] for r in rows)
    out = [f"# Related-work sections of {len(rows)} {VENUE} papers\n",
           "Generated by scripts/relwork_stats.py; regexes for the sentence classes are in the script.\n",
           ("Papers without a related-work heading, not counted: " + ", ".join(missing) + "\n") if missing else "",
           "## 1. Placement\n",
           table(["placement", "papers"],
                 [[p, by("placement")[p]] for p in ("front", "front-combined", "back", "subsection")]),
           "\nfront: own section numbered 2 or 3; front-combined: 'Background and Related Work'; back: own section "
           "numbered 4 or later; subsection: a 2.x subsection of Background or Preliminaries.\n",
           "\nWhat the back-placed sections sit between (previous | next heading):\n",
           table(["previous", "next", "papers"],
                 [[p, n, c] for (p, n), c in Counter((r["prev"], r["next"]) for r in rows if r["placement"] == "back").most_common()]),
           "\n## 2. Length\n"]
    for label, sel in (("all", rows), ("back", [r for r in rows if r["placement"] == "back"]),
                       ("front or front-combined", [r for r in rows if r["placement"].startswith("front")])):
        out.append(f"- words, {label}: {q([r['words'] for r in sel])}")
    out += [f"- share of the body: {q([r['share'] for r in rows])}",
            f"- paragraphs: {q([r['paragraphs'] for r in rows])}",
            f"- words per paragraph (paper medians): {q([round(r['words'] / r['paragraphs']) for r in rows if r['paragraphs']])}",
            "\n## 3. Structure\n",
            f"- subsections: {q([r['subsections'] for r in rows])}; papers with none: {sum(1 for r in rows if not r['subsections'])}",
            f"- words per subsection, papers that have them: {q([r['words_per_sub'] for r in rows])}",
            f"- paragraphs per subsection: {q([s['paragraphs'] for s in subs])}",
            f"- run-in labelled paragraphs (bold or numbered lead-in): papers with any: {sum(1 for r in rows if r['runin_paras'])}",
            f"- a table inside the section: {sum(1 for r in rows if r['table'])}",
            "\n## 4. Citations\n",
            f"- reference count cited: {q([r['cite_refs'] for r in rows])}",
            f"- citation groups per 100 words: {q([r['cites_per_100w'] for r in rows])}",
            "\n## 5. Positioning sentences (regex POSITION: unlike, in contrast, differs, our work, this paper, ...)\n",
            f"- papers with at least one: {sum(1 for r in rows if r['position_sents'])} / {len(rows)}",
            f"- positioning sentences per paper: {q([r['position_sents'] for r in rows])}",
            f"- paragraphs containing one, share of paragraphs: {q([round(r['position_paras'] / r['paragraphs'], 2) for r in rows if r['paragraphs']])}",
            f"- last paragraph of the section contains one: {sum(1 for r in rows if r['last_para_positions'])} / {len(rows)}",
            f"- subsections whose last paragraph contains one: {sum(1 for s in subs if s['last_para_positions'])} / {len(subs)}",
            "\n## 6. Novelty, search and own prior work\n",
            f"- papers with a novelty sentence (to our knowledge, the first, none of, no prior work): {sum(1 for r in rows if r['novelty_sents'])} / {len(rows)}",
            f"- papers describing a literature search (we searched, Google Scholar, snowball, ...): {sum(1 for r in rows if r['search_sents'])} / {len(rows)}",
            f"- papers citing their own prior work explicitly: {sum(1 for r in rows if r['own_prior_sents'])} / {len(rows)}",
            "\n## 7. Per paper\n",
            table(["paper", "sec", "placement", "words", "paras", "subs", "refs", "position", "last positions", "novelty", "search"],
                  [[r["paper"][8:48], r["section"], r["placement"], r["words"], r["paragraphs"], r["subsections"],
                    r["cite_refs"], r["position_sents"], r["last_para_positions"], r["novelty_sents"], r["search_sents"]]
                   for r in rows])]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="write cleaned paragraphs per paper with subsection titles to this directory and stop")
    args = ap.parse_args()
    rows, subs, missing = [], [], []
    for name, md in paper_paths():
        try:
            f, s, parts = features(name, md)
        except ValueError as e:      # a paper can have a background section and no related-work section
            missing.append(name)
            print(f"{name}: {e}, skipped")
            continue
        rows.append(f)
        subs += s
        if args.dump:
            os.makedirs(args.dump, exist_ok=True)
            with open(os.path.join(args.dump, name + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(f"{f['section']} {f['title']}  [{f['placement']}, {f['words']} words, prev: {f['prev']} | next: {f['next']}]\n\n")
                for t, x in parts:
                    if t:
                        fh.write(f"### {t}\n\n")
                    for p in clean_paragraphs(x):
                        fh.write(f"({word_count(p)} words) {p}\n\n")
    if args.dump:
        print(f"dumped {len(rows)} papers to {args.dump}")
        return
    os.makedirs(OUT, exist_ok=True)
    for fn, data in (("relwork_features.csv", rows), ("relwork_subsections.csv", subs)):
        with open(os.path.join(OUT, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    with open(os.path.join(OUT, "relwork_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(rows, subs, missing))
    print(f"{len(rows)} papers, {len(subs)} subsections -> {OUT}/relwork_features.csv, relwork_subsections.csv, relwork_report.md")


if __name__ == "__main__":
    main()
