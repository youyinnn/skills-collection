#!/usr/bin/env python3
"""Methodology statistics over a venue sample: placement and position, length, subsection topics and
their order, sentence length, citation density, formulas and figures, marker sentences, and where
the research questions are stated. Papers whose design section the rules cannot find are set by
hand in HAND_DESIGN.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/methodology_stats.py          # methodology_features.csv, methodology_units.csv, methodology_report.md
  python scripts/methodology_stats.py --dump   # prints the cut sections
"""
import argparse
import csv
import os
import re
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from background_stats import FORMULA  # noqa: E402
from config import VENUE  # noqa: E402
from intro_stats import (HAND, LIST_ITEM, OUT, RUNIN, _plain, body_text, clean_paragraphs,  # noqa: E402
                             count_citations, extract_intro, paper_paths, rq_numbers, split_sentences, word_count)
from relwork_stats import REFS, headings, q, table  # noqa: E402

# Assistant-set rules; tune them for a new venue.
DESIGN = re.compile(r"study design|experiment|empirical study|methodology|research (?:method|question)"
                    r"|evaluation|\bdatasets?\b|implementation", re.I)
EMPIRICAL_EXTRA = re.compile(r"approach", re.I)
RESULTS = re.compile(r"\bRQ\s*-?\s*\d|\bresults?\b|\bfindings\b|case studies", re.I)
METHOD = re.compile(r"approach|technique|framework|algorithm|^design$|methodology|implementation", re.I)
METHOD_MIXED = re.compile(r"approach|technique|framework|algorithm|^design$", re.I)
EVAL = re.compile(r"evaluation|experiment", re.I)
NO_CUT = re.compile(r"methodology|study design|setup|settings?\b|experimental design|empirical study", re.I)
SETUP_SUB = re.compile(r"study design|experimental setup|evaluation setup|^setup", re.I)
PER_RQ = re.compile(r"^RQ\s*-?\s*\d", re.I)
# Folder-name prefix -> dict(exclude=(...), include=(...), why="...") for papers whose design section
# the rules misread (section numbers to drop or add).
HAND_DESIGN = {}
# Folder-name prefix -> a caveat printed in the report.
NOTES = {}
TOPICS = (
    ("rq", re.compile(r"research question", re.I)),
    ("threats", re.compile(r"threat", re.I)),
    ("notation", re.compile(r"notation|definition|formulation", re.I)),
    ("data", re.compile(r"dataset|benchmark|corpora|\bdata\b|subject|\btasks?\b|programs|scene|librar|systems"
                        r"|programming languages|\bmethods\b", re.I)),
    ("metric", re.compile(r"metric|measure", re.I)),
    ("baseline", re.compile(r"baseline|compared|comparison", re.I)),
    ("setting", re.compile(r"implementation|setting|setup|hyper.?parameter|details|configuration|hardware"
                           r"|environment|training|fine-tuning|inference|preprocessing|precondition|system|tool", re.I)),
    ("model", re.compile(r"\bmodels?\b|\bllms?\b|\blcms?\b|fuzzers|studied|selected", re.I)),
    ("procedure", re.compile(r"procedure|execution|protocol|process|pipeline|overview|design|experiment|construction"
                             r"|generation|label|evaluat|study|prompt|template|preliminary|manual|automatic", re.I)),
    ("statistics", re.compile(r"statistic|analysis", re.I)),
)
MARKERS = {
    "rq": re.compile(r"\bRQ\s*-?\s*\d"),
    "stats_test": re.compile(r"Wilcoxon|Mann.Whitney|t-test|Holm|Bonferroni|Cliff|Vargha|effect size|Spearman|Kendall"
                             r"|Pearson|bootstrap|ANOVA|Cohen|chi-square|Kruskal|Friedman|significan|confidence interval"
                             r"|p-value|\bp\s*[<>=]", re.I),
    "repeat": re.compile(r"\bseeds?\b|\brepeat|\b(?:three|five|ten|\d+) (?:times|runs|independent|repetitions|trials)\b"
                         r"|\btemperature\b|non-?determinis|\baverag\w* (?:over|across)\b|\brandomness\b", re.I),
    "hardware": re.compile(r"\bGPUs?\b|A100|H100|V100|RTX|NVIDIA|\bCPUs?\b|\bRAM\b|\d+\s?GB\b|\bTPU"),
    "hyper": re.compile(r"learning rate|\bepochs?\b|batch size|weight decay|optimi[sz]er|\bAdamW?\b|\bSGD\b|early stopping", re.I),
    "cost": re.compile(r"\bcosts?\b|\btokens?\b|\bAPI\b|\bprice|\$\d|\bbudget", re.I),
    "availability": re.compile(r"replication package|available at|artifact|open[- ]sourc|GitHub|Zenodo|supplement", re.I),
    "rationale": re.compile(r"\bbecause\b|so that|\bto (?:ensure|avoid|control|prevent|isolate|rule out|reduce)\b"
                            r"|for this reason|the reason|\bsince\b", re.I),
    "figtab": re.compile(r"\bTable\s*\d|\bFig(?:ure|\.)\s*\d", re.I),
    "roadmap": re.compile(r"\b(?:this|the) section\b|\bwe (?:describe|present|detail|introduce|now|first|then|next)\b", re.I),
}
PREV_KIND = (("background", re.compile(r"background|preliminar|motivat|problem|terminolog|definition|concordance|task definition", re.I)),
             ("related work", re.compile(r"related work", re.I)),
             ("approach", re.compile(r"approach|technique|framework|algorithm|design|methodology|insights|analysis of|taxonomy", re.I)))


def _hand(name):
    return next((v for k, v in HAND_DESIGN.items() if name.startswith(k)), {})


def topic_of(label):
    for t, rx in TOPICS:
        if rx.search(label):
            return t
    return "other"


def sentences(text):
    return [s for p in clean_paragraphs(text) for s in split_sentences(_plain(p))]


def first_sentence(text):
    for s in sentences(text):
        if word_count(s) >= 6:
            return re.sub(r"\s+", " ", re.sub(r"[\[\]]", "", s.replace("**", "")))[:220]   # no bracket remnants, which Obsidian reads as links
    return ""


def design_sections(md, ptype, name):
    """[(num, title, raw, subs)] of the taken top-level sections, plus (top, extra, per_rq) where
    extra are the design-titled subsections found inside sections that were not taken, as
    (parent num, label, text). ptype is the HAND paper type, used only for the cutting rules."""
    refs = REFS.search(md)
    limit = refs.start() if refs else len(md)
    hs = [h for h in headings(md) if h[0] < limit]
    top = [h for h in hs if len(h[2]) == 1]
    hand = _hand(name)
    taken, extra, per_rq, stopped = [], [], False, False
    for i, (s, e, num, title) in enumerate(top):
        t = title.strip("* ")
        end = top[i + 1][0] if i + 1 < len(top) else limit
        subs = [(s2 - e, e2 - e, n2, t2.strip("* ")) for s2, e2, n2, t2 in hs
                if len(n2) == 2 and n2[0] == num[0] and e <= s2 < end]
        per_rq = per_rq or bool(PER_RQ.match(t))
        if num[0] == 1:
            continue
        if not stopped and RESULTS.search(t) and num[0] not in hand.get("include", ()):
            stopped = True
        take = not stopped and num[0] not in hand.get("exclude", ())
        if take:
            if ptype == "method" and METHOD.search(t):
                take = False
            elif ptype == "mixed" and METHOD_MIXED.search(t):
                take = False
            elif not (DESIGN.search(t) or (ptype == "empirical" and EMPIRICAL_EXTRA.search(t))):
                take = False
        if num[0] in hand.get("include", ()):
            take = True
        if take:
            taken.append((num[0], t, md[e:end], subs))
        else:
            for j, (s2, e2, n2, t2) in enumerate(subs):
                if SETUP_SUB.search(t2):
                    end2 = subs[j + 1][0] if j + 1 < len(subs) else len(md[e:end])
                    extra.append((num[0], t2, md[e:end][e2:end2]))
    return taken, top, extra, per_rq


def units_of(num, title, raw, subs, force_cut=False):
    """[(label, text)], cut: the subsections, a preamble first when text precedes them, the cut
    applied for evaluation-like sections; cut is True on a section where subsections were dropped."""
    if not subs:
        return [(title, raw)], False
    out, cut = [], False
    if clean_paragraphs(raw[:subs[0][0]]):
        out.append(("", raw[:subs[0][0]]))
    stop_here = force_cut or (EVAL.search(title) and not NO_CUT.search(title))
    for j, (s2, e2, n2, t2) in enumerate(subs):
        if stop_here and RESULTS.search(t2):
            cut = True
            break
        end2 = subs[j + 1][0] if j + 1 < len(subs) else len(raw)
        out.append((t2, raw[e2:end2]))
    return out, cut


def unit_row(name, section, idx, label, text, source):
    paras = clean_paragraphs(text)
    return dict(paper=name, section=section, unit=idx, label=label,
                topic="preamble" if label == "" else topic_of(label), source=source,
                words=sum(word_count(p) for p in paras), paragraphs=len(paras),
                cite_groups=count_citations(text)[0], formulas=len(FORMULA.findall(text)),
                first_sentence=first_sentence(text))


def prev_kind(title):
    for k, rx in PREV_KIND:
        if rx.search(title):
            return k
    return "other"


def features(name, md_path):
    with open(md_path, encoding="utf-8") as fh:
        md = fh.read()
    ptype = HAND.get(name, {"type": "unlabelled"})["type"]
    taken, top, extra, per_rq = design_sections(md, ptype, name)
    try:
        intro = extract_intro(md)
    except ValueError:
        intro = ""
    row = dict(paper=name, year=name[3:7], layout="none", sections="", titles="",
               first_section=None, prev="", prev_kind="", next="", n_top=len(top), position=None,
               per_rq=per_rq, n_sections=len(taken), n_cut=0, units=0, preamble_units=0, sub_units=len(extra),
               all_subsectioned=bool(taken) and all(s[3] for s in taken),
               topics="", words=0, share=None, paragraphs=0, sentences=0, sent_median=None, sent_max=0,
               long40=0, cite_groups=0, cites_per_100w=None, formulas=0, tables=0, figures=0,
               list_paras=0, runin_paras=0, rq_in_intro=rq_numbers(intro), rq_in_design=0, rq_defining=0,
               opens_with_roadmap=False, first_sentence="",
               note=next((v for k, v in NOTES.items() if name.startswith(k)), ""),
               hand=_hand(name).get("why", ""))
    for m in MARKERS:
        row["m_" + m] = 0
    units, texts = [], []
    for num, title, raw, subs in taken:
        us, cut = units_of(num, title, raw, subs, force_cut=num in _hand(name).get("cut", ()))
        row["n_cut"] += int(cut)
        for label, text in us:
            units.append(unit_row(name, num, len(units) + 1, label, text, "section"))
            texts.append(text)
    for num, label, text in extra:
        units.append(unit_row(name, num, len(units) + 1, label, text, "subsection"))
        texts.append(text)
    if not units:
        row["layout"] = "per-RQ" if per_rq else "none"
        return row, units
    if taken:
        row["layout"] = "inside-evaluation" if all(units_of(*t, force_cut=t[0] in _hand(name).get("cut", ()))[1] for t in taken) else \
            "section+evaluation" if row["n_cut"] else "section"
        first = taken[0][0]
        nums = [t[2][0] for t in top]
        i = nums.index(first)
        row["prev"] = top[i - 1][3].strip("* ") if i else ""
        row["prev_kind"] = prev_kind(row["prev"])
        last = taken[-1][0]
        j = nums.index(last)
        row["next"] = top[j + 1][3].strip("* ") if j + 1 < len(top) else ""
        row["first_section"] = first
        row["position"] = round(first / len(top), 2)
        row["sections"] = " ".join(str(t[0]) for t in taken)
        row["titles"] = "; ".join(t[1][:40] for t in taken)
    else:
        row["layout"] = "subsections-only"
        row["sections"] = " ".join(str(u["section"]) for u in units)
        row["titles"] = "; ".join(u["label"][:40] for u in units)
    all_raw = "\n\n".join(texts)
    paras = [p for t in texts for p in clean_paragraphs(t)]
    sents = [s for t in texts for s in sentences(t)]
    lens = [word_count(s) for s in sents]
    row.update(units=len(units), preamble_units=sum(1 for u in units if u["label"] == ""),
               topics=" ".join(u["topic"] for u in units),
               words=sum(u["words"] for u in units), paragraphs=len(paras), sentences=len(sents),
               sent_median=statistics.median(lens) if lens else None, sent_max=max(lens) if lens else 0,
               long40=sum(1 for n in lens if n >= 40), cite_groups=sum(u["cite_groups"] for u in units),
               formulas=sum(u["formulas"] for u in units),
               tables=len(re.findall(r"^\s*(?:\*\*)?Table\s*\d+[.:]", all_raw, re.M | re.I)),
               figures=len(re.findall(r"!\[\]\(", all_raw)),
               list_paras=sum(1 for p in paras if any(LIST_ITEM.match(l) for l in p.splitlines())),
               runin_paras=sum(1 for p in paras if RUNIN.match(p)),
               rq_in_design=rq_numbers(all_raw),
               rq_defining=sum(1 for s in sents if re.match(r"\**\(?RQ\s*-?\s*\d", s)),
               first_sentence=first_sentence(texts[0]))
    body = word_count(body_text(md))
    row["share"] = round(row["words"] / body, 3) if body else None
    row["cites_per_100w"] = round(100 * row["cite_groups"] / row["words"], 1) if row["words"] else None
    for m, rx in MARKERS.items():
        row["m_" + m] = sum(1 for s in sents if rx.search(s))
    first_para = clean_paragraphs(texts[0])
    row["opens_with_roadmap"] = bool(first_para) and bool(MARKERS["roadmap"].search(_plain(first_para[0])))
    return row, units


# ---------------------------------------------------------------- report

def _cnt(rows, key):
    return sum(1 for r in rows if r[key])


def report(rows, units):
    with_d = [r for r in rows if r["units"]]
    layouts = ["section", "section+evaluation", "inside-evaluation", "subsections-only", "per-RQ", "none"]
    topics = [t for t, _ in TOPICS] + ["preamble", "other"]
    L = [f"# Study-design sections of {len(rows)} {VENUE} papers", "",
         "Generated by `scripts/methodology_stats.py`; do not edit. The title rules, the unit topics, the "
         "marker regexes and the hand overrides are assistant-set and printed at the top "
         "of the script. Numbers are over all papers; the per-type numbers are in `by_type_report.md`.", "",
         "## 1. Layout and position", "",
         table(["layout", "papers"], [[lay, sum(1 for r in rows if r["layout"] == lay)] for lay in layouts]),
         "section: one or more top-level sections taken whole; section+evaluation: a whole section plus the "
         "setup part of an evaluation section; inside-evaluation: only the setup part of an evaluation "
         "section; subsections-only: design-titled subsections under result sections; per-RQ: no design "
         "unit and the paper is organised by RQ sections.", "",
         f"- Papers with a design unit: {len(with_d)} / {len(rows)}; taken sections per paper: "
         f"{q([r['n_sections'] for r in with_d])}; sections where the cut dropped result subsections: "
         f"{_cnt(with_d, 'n_cut')}.",
         f"- First design section number: " + ", ".join(f"{k} in {v}" for k, v in sorted(Counter(r['first_section'] for r in with_d if r['first_section']).items()))
         + f"; relative position in the body: {q([r['position'] for r in with_d])}.",
         "- What precedes the first design section: " + ", ".join(f"{k} {v}" for k, v in Counter(r["prev_kind"] for r in with_d if r["prev"]).most_common()) + ".",
         "- What follows the last design section: " + ", ".join(f"{k[:40]} {v}" for k, v in Counter(r["next"] for r in with_d if r["next"]).most_common(8)) + ".",
         "- Hand overrides: " + "; ".join(f"{r['paper'][:35]} ({r['hand']})" for r in rows if r["hand"]) + ".",
         "- Read but not counted: " + "; ".join(f"{r['paper'][:35]} ({r['note']})" for r in rows if r["note"]) + ".", "",
         "## 2. Length", "",
         f"- Design words: {q([r['words'] for r in with_d])}",
         f"- Share of the body: {q([r['share'] for r in with_d])}",
         f"- Units per paper: {q([r['units'] for r in with_d])}; papers with a preamble unit: {_cnt(with_d, 'preamble_units')} / {len(with_d)}",
         f"- Words per unit (subsection): {q([u['words'] for u in units if u['label']])}; preamble words: {q([u['words'] for u in units if not u['label']])}",
         f"- Paragraphs: {q([r['paragraphs'] for r in with_d])}; words per paragraph (paper medians): "
         f"{q([round(r['words'] / r['paragraphs']) for r in with_d if r['paragraphs']])}", "",
         "## 3. Unit topics", "",
         table(["topic", "papers", "units", "words per unit"],
               [[t, sum(1 for r in with_d if t in r["topics"].split()),
                 sum(1 for u in units if u["topic"] == t), q([u["words"] for u in units if u["topic"] == t])]
                for t in topics]),
         "Topic order per paper:", ""]
    L += [f"- {r['paper'][8:48]}: {r['topics']}" for r in with_d]
    L += ["", "## 4. Prose form", "",
          f"- Sentences: {q([r['sentences'] for r in with_d])}; median sentence length (paper medians): "
          f"{q([r['sent_median'] for r in with_d])}; longest sentence: {q([r['sent_max'] for r in with_d])}; "
          f"sentences of 40 words or more: {q([r['long40'] for r in with_d])}",
          f"- Citation groups per 100 words: {q([r['cites_per_100w'] for r in with_d])}",
          f"- Papers with a formula: {_cnt(with_d, 'formulas')} / {len(with_d)}",
          f"- Papers with a table caption inside the design: {_cnt(with_d, 'tables')} / {len(with_d)}; "
          f"tables per paper: {q([r['tables'] for r in with_d])}",
          f"- Papers with a figure inside the design: {_cnt(with_d, 'figures')} / {len(with_d)}",
          f"- Papers with a list paragraph: {_cnt(with_d, 'list_paras')} / {len(with_d)}; with a run-in labelled paragraph: {_cnt(with_d, 'runin_paras')} / {len(with_d)}",
          f"- Papers whose every taken section has numbered subsections: {_cnt(with_d, 'all_subsectioned')} / {len(with_d)}",
          f"- First design section opens with a roadmap or 'we describe' sentence: {_cnt(with_d, 'opens_with_roadmap')} / {len(with_d)}", "",
          "## 5. Marker sentences (papers with at least one; median count per paper)", "",
          table(["marker", "papers", "median per paper"],
                [[m, _cnt(with_d, "m_" + m), f"{statistics.median([r['m_' + m] for r in with_d]):g}"] for m in MARKERS]), "",
          "## 6. Research questions", "",
          f"- Papers whose introduction numbers RQs: {sum(1 for r in rows if r['rq_in_intro'])} / {len(rows)}; "
          f"whose design numbers RQs: {sum(1 for r in with_d if r['rq_in_design'])} / {len(with_d)}; "
          f"both: {sum(1 for r in with_d if r['rq_in_intro'] and r['rq_in_design'])}; "
          f"design only: {sum(1 for r in with_d if r['rq_in_design'] and not r['rq_in_intro'])}; "
          f"intro only: {sum(1 for r in with_d if r['rq_in_intro'] and not r['rq_in_design'])}",
          f"- Papers with an rq unit (a subsection titled Research Questions): {sum(1 for r in with_d if 'rq' in r['topics'].split())} / {len(with_d)}",
          f"- Sentences opening with an RQ number inside the design: {q([r['rq_defining'] for r in with_d])}", "",
          "## 7. Every paper", "",
          table(["paper", "layout", "sections", "prev", "words", "units", "cites/100w", "formulas", "tables", "stats", "repeat", "hyper"],
                [[r["paper"][8:50], r["layout"], r["sections"], r["prev"][:22], r["words"], r["units"],
                  "" if r["cites_per_100w"] is None else r["cites_per_100w"], r["formulas"], r["tables"],
                  r["m_stats_test"], r["m_repeat"], r["m_hyper"]] for r in rows]), "",
          "## 8. Opening sentence of the first design unit", ""]
    L += [f"- {r['paper'][8:44]}: {r['first_sentence']}" for r in with_d]
    L += ["", f"Units: {len(units)} (" + ", ".join(f"{k} {v}" for k, v in Counter(u['topic'] for u in units).most_common()) + ")."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="write the design units of every paper to this directory and stop")
    args = ap.parse_args()
    rows, units = [], []
    for name, md in paper_paths():
        r, us = features(name, md)
        rows.append(r)
        units += us
        if args.dump and us:
            os.makedirs(args.dump, exist_ok=True)
            with open(os.path.join(args.dump, name + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(f"{r['layout']}; sections {r['sections']} ({r['titles']}); prev: {r['prev']} | next: {r['next']}; "
                         f"{r['words']} words\n\n")
                for u in us:
                    fh.write(f"{u['unit']}. [{u['topic']}, {u['words']} words, {u['source']}] {u['section']} {u['label']}\n    {u['first_sentence']}\n\n")
    if args.dump:
        print(f"dumped {sum(1 for r in rows if r['units'])} papers to {args.dump}")
        return
    os.makedirs(OUT, exist_ok=True)
    for fn, data in (("methodology_features.csv", rows), ("methodology_units.csv", units)):
        with open(os.path.join(OUT, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    with open(os.path.join(OUT, "methodology_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(rows, units))
    print(f"{len(rows)} papers, {sum(1 for r in rows if r['units'])} with design units, {len(units)} units "
          f"-> {OUT}/methodology_features.csv, methodology_units.csv, methodology_report.md")


if __name__ == "__main__":
    main()
