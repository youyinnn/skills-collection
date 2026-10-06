#!/usr/bin/env python3
"""Background-section statistics over a venue sample: whether a background section exists, how it is
placed against related work, length, units and their topics, citation density, formulas.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/background_stats.py          # background_features.csv, background_units.csv, background_report.md
  python scripts/background_stats.py --dump   # prints the cut sections
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import relwork_stats as frs  # noqa: E402
from config import VENUE  # noqa: E402
from intro_stats import (HAND, OUT, RUNIN, _plain, clean_paragraphs, count_citations,  # noqa: E402
                             extract_intro, paper_paths, split_sentences, word_count)
from relwork_stats import REFS, RW, headings, q, table  # noqa: E402

# Assistant-set rules; tune them for a new venue.
BG = re.compile(r"background|preliminar|motivat|problem (?:formulation|definition|statement|setting|analysis)"
                r"|terminolog|definitions?\b|primer|nutshell|foundation|basic concept|concepts|overview of"
                r"|technical background|task definition|concordance", re.I)
RWSUB = re.compile(r"related work|research gap|prior work|existing (?:work|studies)|empirical stud", re.I)
MOTIV = re.compile(r"motivat|preliminary (?:study|experiment)|example|feasibility|observation|key idea|why ", re.I)
DEF = re.compile(r"\b(?:is defined as|are defined as|we define|refers to|denotes?|let \$|let [A-Z]|formally"
                 r"|is the process of|is a (?:practice|technique|measure|metric|set|type|class)\b|consists of)", re.I)
FORMULA = re.compile(r"\$\$|\\begin\{equation|\\frac|\\sum|\\arg|= *\\|\$[^$]{3,80}=[^$]{1,80}\$")
STOP = set("the a an of and or for in on to with via by from as at into vs versus its their our this that based "
           "using use large language model models llm llms code software study section overview approach "
           "approaches introduction".split())
# Folder-name prefix -> a caveat printed in the report.
NOTES = {}


def _label_words(text):
    return [w for w in re.findall(r"[a-z][a-z\-]{3,}", text.lower()) if w not in STOP]


def named_in(words, intro):
    """True when one of the label words occurs in the introduction as a whole word, singular or
    plural (a label word ending in s also matches its singular)."""
    for w in words:
        stem = w[:-1] if w.endswith("s") else w
        if re.search(r"\b" + re.escape(stem) + r"(?:s|es)?\b", intro):
            return True
    return False


def first_sentence(text):
    for p in clean_paragraphs(text):
        s = split_sentences(_plain(p))
        if s and word_count(s[0]) >= 6:
            return s[0][:200]
    return ""


def background_section(md):
    """(number, title, raw text, nested headings with positions relative to raw) of the first
    background-like top-level section after section 1, or None."""
    refs = REFS.search(md)
    limit = refs.start() if refs else len(md)
    hs = [h for h in headings(md) if h[0] < limit]
    top = [h for h in hs if len(h[2]) == 1]
    for i, (s, e, num, title) in enumerate(top):
        t = title.strip("* ")
        if num[0] != 1 and BG.search(t):
            end = top[i + 1][0] if i + 1 < len(top) else limit
            subs = [(s2 - e, e2 - e, n2, t2) for s2, e2, n2, t2 in hs
                    if len(n2) == 2 and n2[0] == num[0] and e <= s2 < end]
            return num[0], t, md[e:end], subs
    return None


def kind_of(label):
    if RWSUB.search(label):
        return "related-work"
    if MOTIV.search(label):
        return "motivation"
    return "definitional"


def kind_of_section(title):
    """Class of a whole section used as one unit: motivation only when nothing else in the title
    is a background word ("Motivating Example" is motivation, "Background and Motivation" is not)."""
    k = kind_of(title)
    if k == "motivation" and BG.search(MOTIV.sub("", title)):
        return "definitional"
    return k


def units_of(raw, subs, title):
    """[(label, text, kind)]: the subsections; else the run-in labelled blocks; else the whole
    section. Text before the first subsection or label is a preamble unit."""
    if subs:
        out = []
        if clean_paragraphs(raw[:subs[0][0]]):
            out.append(("", raw[:subs[0][0]], "preamble"))
        for j, (s2, e2, n2, t2) in enumerate(subs):
            end2 = subs[j + 1][0] if j + 1 < len(subs) else len(raw)
            label = t2.strip("* ")
            out.append((label, raw[e2:end2], kind_of(label)))
        return out
    paras = clean_paragraphs(raw)
    labels = [RUNIN.match(_plain(p)) for p in paras]
    if any(labels):
        out, cur, buf = [], None, []
        for p, m in zip(paras, labels):
            if m:
                if buf:
                    out.append((cur or "", "\n\n".join(buf), kind_of(cur) if cur else "preamble"))
                cur, buf = m.group(0).strip(" .:*"), [p]
            else:
                buf.append(p)
        if buf:
            out.append((cur or "", "\n\n".join(buf), kind_of(cur) if cur else "preamble"))
        return out
    return [(title, raw, kind_of_section(title))]


def unit_row(name, ptype, section, idx, label, text, kind, intro):
    paras = clean_paragraphs(text)
    plain = " ".join(_plain(p) for p in paras)
    ws = set(_label_words(label))
    return dict(paper=name, section=section, unit=idx, label=label, kind=kind,   # ptype kept in the signature, retired from the output
                words=sum(word_count(p) for p in paras),
                named_in_intro=named_in(ws, intro),
                def_sentences=len(DEF.findall(plain)), formulas=len(FORMULA.findall(text)),
                cite_groups=count_citations(text)[0], first_sentence=first_sentence(text))


def relation(bg_num, bg_title, rw):
    """Where the background-like section sits relative to the related-work section (rw is a
    relwork_stats.features row)."""
    if rw is None:
        return "no-rw"
    if RW.match(bg_title):
        return "merged"
    rw_top = int(rw["section"].split(".")[0])
    if rw["placement"] == "subsection" and rw_top == bg_num:
        return "rw-subsection"
    if bg_num < rw_top:
        return "before-adjacent" if rw_top == bg_num + 1 else "before"
    return "after-adjacent" if bg_num == rw_top + 1 else "after"


def beats(moves, row, rw):
    """Three-beat rules (assistant-set). beat 1: the introduction opens with
    context, problem or example (moves C, P, E) and previews findings (F); lenient: F or a
    contributions list K. beat 2: a background-like section with at least one definitional
    unit whose label words occur in the introduction; strict: every definitional unit is
    named there and the motivation units are not all of it. beat 3: the related-work section
    has a positioning sentence. order: background precedes related work (section number, or
    the related-work part is the last unit of a merged section, or related work is a
    subsection of the background section, read as last in both such papers)."""
    b1 = any(m in "CPE" for m in moves) and "F" in moves
    b1_len = any(m in "CPE" for m in moves) and ("F" in moves or "K" in moves)
    d, named, mot, n = row["def_units"], row["def_units_named_in_intro"], row["motiv_units"], row["units"]
    b2 = d >= 1 and named >= 1
    b2_strict = d >= 1 and named == d and mot < n
    b3 = rw is not None and rw["position_sents"] >= 1
    rel = row["relation"]
    if not row["has_background"] or rel == "no-rw":
        order = False
    elif rel == "merged":
        order = row["rw_units"] >= 1 or bool(rw["last_para_positions"])
    elif rel == "rw-subsection":
        order = True
    else:
        order = rel.startswith("before")
    fit = b1 and b2 and b3 and order
    first_fail = "" if fit else "beat1" if not b1 else "beat2" if not b2 else "beat3" if not b3 else "order"
    return dict(beat1=b1, beat1_lenient=b1_len, beat2=b2, beat2_strict=b2_strict, beat3=b3, order=order,
                fit=fit, first_fail=first_fail)


def features(name, md_path):
    with open(md_path, encoding="utf-8") as fh:
        md = fh.read()
    hand = HAND.get(name, {"type": "unlabelled", "moves": ""})
    ptype, moves = hand["type"], hand["moves"]
    try:
        rw = frs.features(name, md_path)[0]
    except (ValueError, KeyError):   # no related-work heading, or the paper is not in HAND
        rw = None
    try:
        intro = " ".join(clean_paragraphs(extract_intro(md))).lower()
    except ValueError:
        intro = ""
    row = dict(paper=name, year=name[3:7], has_background=False, section="", title="",
               relation="none", rw_section=rw["section"] if rw else "", rw_placement=rw["placement"] if rw else "",
               units=0, def_units=0, def_units_named_in_intro=0, rw_units=0, motiv_units=0,
               preamble_words=0, bg_words=0, dens_words=0, def_words=0, rw_part_words=0,
               formulas=0, def_sentences=0, cite_groups=0, def_cite_groups=0,
               cites_per_100w=None, cites_per_100w_def=None,
               note=next((v for k, v in NOTES.items() if name.startswith(k)), ""))
    units = []
    cut = background_section(md)
    if cut:
        num, title, raw, subs = cut
        row.update(has_background=True, section=num, title=title, relation=relation(num, title, rw))
        for i, (label, text, kind) in enumerate(units_of(raw, subs, title), 1):
            u = unit_row(name, ptype, num, i, label, text, kind, intro)
            units.append(u)
            if kind == "related-work":
                row["units"] += 1
                row["rw_units"] += 1
                row["rw_part_words"] += u["words"]
                continue
            row["bg_words"] += u["words"]
            if kind == "motivation":
                row["units"] += 1
                row["motiv_units"] += 1
                continue
            if kind == "preamble":
                row["preamble_words"] += u["words"]
            else:
                row["units"] += 1
                row["def_units"] += 1
                row["def_units_named_in_intro"] += int(u["named_in_intro"])
                row["def_words"] += u["words"]
                row["def_cite_groups"] += u["cite_groups"]
            row["dens_words"] += u["words"]
            row["formulas"] += u["formulas"]
            row["def_sentences"] += u["def_sentences"]
            row["cite_groups"] += u["cite_groups"]
        if row["dens_words"]:
            row["cites_per_100w"] = round(100 * row["cite_groups"] / row["dens_words"], 1)
        if row["def_words"]:
            row["cites_per_100w_def"] = round(100 * row["def_cite_groups"] / row["def_words"], 1)
    row.update(beats(moves, row, rw))
    return row, units


# ---------------------------------------------------------------- report

def _cnt(rows, key):
    return sum(1 for r in rows if r[key])


def report(rows, units):
    with_bg = [r for r in rows if r["has_background"]]
    merged = [r for r in with_bg if r["relation"] == "merged"]
    indep = [r for r in with_bg if r["relation"] != "merged"]
    dens = [r for r in with_bg if r["dens_words"]]
    rels = ["merged", "rw-subsection", "before-adjacent", "before", "after-adjacent", "after", "no-rw", "none"]
    L = [f"# Background sections of {len(rows)} {VENUE} papers", "",
         "Generated by `scripts/background_stats.py`; do not edit. The title regex, the unit "
         "classes, the definitional-sentence and formula regexes and the three-beat rules are "
         "assistant-set and printed at the top of the script. Numbers are over all "
         "papers; the per-type numbers are in `by_type_report.md`.", "",
         "## 1. Presence, and relation to the related-work section", "",
         table(["relation", "papers"], [[rel, sum(1 for r in rows if r["relation"] == rel)] for rel in rels]),
         f"Papers with a background-like top-level section: {len(with_bg)} / {len(rows)}. "
         "Papers with no such section whose background material was found by reading: "
         + "; ".join(f"{r['paper'][:40]} ({r['note']})" for r in rows if r["note"] and not r["has_background"]) + ".", "",
         "## 2. Length", "",
         f"- Background words, non-merged sections: {q([r['bg_words'] for r in indep])}",
         f"- Merged sections, background part: {q([r['bg_words'] for r in merged])}; "
         f"related-work part: {q([r['rw_part_words'] for r in merged])}", "",
         table(["merged section", "background words", "related-work words"],
               [[r["paper"][:50], r["bg_words"], r["rw_part_words"]] for r in merged]),
         f"- Words per definitional unit: {q([u['words'] for u in units if u['kind'] == 'definitional'])}",
         f"- Sections with a motivation unit: {_cnt(with_bg, 'motiv_units')} / {len(with_bg)}",
         f"- Sections with a related-work unit inside: {_cnt(with_bg, 'rw_units')} / {len(with_bg)}", "",
         "## 3. Preamble and definitional units: citation density, formulas, definitional sentences", "",
         f"- Citation groups per 100 words: {q([r['cites_per_100w'] for r in dens])}"]
    defonly = [r for r in with_bg if r["def_words"]]
    L += [f"- Same, on the definitional units alone, "
          f"{q([r['cites_per_100w_def'] for r in defonly])}"]
    low = sorted(dens, key=lambda r: r["cites_per_100w"])[:3]
    L += [f"- Lowest: " + ", ".join(f"{r['paper'][:40]} {r['cites_per_100w']}" for r in low),
          f"- Papers with a formula: {_cnt(dens, 'formulas')} / {len(dens)}",
          f"- Papers with a definitional sentence: {_cnt(dens, 'def_sentences')} / {len(dens)}", "",
          "## 4. Definitional units whose label words occur in the introduction", "",
          f"- units {sum(r['def_units_named_in_intro'] for r in with_bg)} / {sum(r['def_units'] for r in with_bg)}; "
          f"papers with every unit named {sum(1 for r in with_bg if r['def_units'] and r['def_units_named_in_intro'] == r['def_units'])}, "
          f"with none named {sum(1 for r in with_bg if r['def_units'] and r['def_units_named_in_intro'] == 0)}",
          "", "## 5. Three-beat fit", "",
          table(["n", "beat 1", "beat 1 lenient", "beat 2", "beat 2 strict", "beat 3", "order",
                 "all four", "all four with lenient beat 1"],
                [[len(rows), _cnt(rows, "beat1"), _cnt(rows, "beat1_lenient"), _cnt(rows, "beat2"),
                  _cnt(rows, "beat2_strict"), _cnt(rows, "beat3"), _cnt(rows, "order"), _cnt(rows, "fit"),
                  sum(1 for r in rows if r["beat1_lenient"] and r["beat2"] and r["beat3"] and r["order"])]]),
          "Papers that miss the rhythm, by the first beat they miss:", ""]
    L += [f"- {r['paper'][:60]}: {r['first_fail']}" for r in rows if not r["fit"]]
    L += ["", "## 6. Every paper", "",
          table(["paper", "section", "relation", "bg words", "cites/100w", "formulas", "fit"],
                [[r["paper"][:55], f"{r['section']} {r['title'][:32]}" if r["has_background"] else "",
                  r["relation"], r["bg_words"], "" if r["cites_per_100w"] is None else r["cites_per_100w"],
                  r["formulas"], "yes" if r["fit"] else ""] for r in rows]),
          f"Units: {len(units)} (" + ", ".join(f"{k} {sum(1 for u in units if u['kind'] == k)}"
                                              for k in ("preamble", "definitional", "motivation", "related-work")) + ")."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="write the units of every background-like section to this directory and stop")
    args = ap.parse_args()
    rows, units = [], []
    for name, md in paper_paths():
        r, us = features(name, md)
        rows.append(r)
        units += us
        if args.dump and us:
            os.makedirs(args.dump, exist_ok=True)
            with open(os.path.join(args.dump, name + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(f"[{r['type']}] {r['section']} {r['title']}  ({r['relation']}; background words {r['bg_words']})\n\n")
                for u in us:
                    fh.write(f"{u['unit']}. [{u['kind']}, {u['words']} words, named in intro: {u['named_in_intro']}] "
                             f"{u['label']}\n    {u['first_sentence']}\n\n")
    if args.dump:
        print(f"dumped {sum(1 for r in rows if r['has_background'])} papers to {args.dump}")
        return
    os.makedirs(OUT, exist_ok=True)
    for fn, data in (("background_features.csv", rows), ("background_units.csv", units)):
        with open(os.path.join(OUT, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    with open(os.path.join(OUT, "background_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(rows, units))
    print(f"{len(rows)} papers, {sum(1 for r in rows if r['has_background'])} with a background-like section, "
          f"{len(units)} units -> {OUT}/background_features.csv, background_units.csv, background_report.md")


if __name__ == "__main__":
    main()
