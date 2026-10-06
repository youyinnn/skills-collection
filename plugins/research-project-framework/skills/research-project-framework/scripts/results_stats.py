#!/usr/bin/env python3
"""Results-section statistics over a venue sample: where the results start and end, placement and
neighbouring sections, length, organisation by research question, unit topics, sentence length and
number density, citations, formulas, figures, summary boxes and marker sentences. Papers whose
results the rules cannot find are set by hand in HAND_RESULTS.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/results_stats.py          # results_features.csv, results_units.csv, results_report.md
  python scripts/results_stats.py --dump   # prints the cut sections
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
from intro_stats import (HAND, LIST_ITEM, OUT, RUNIN, _HEAD, _plain, body_text, clean_paragraphs,  # noqa: E402
                             count_citations, is_noise, paper_paths, word_count)
from methodology_stats import (DESIGN, MARKERS as DESIGN_MARKERS, PER_RQ, RESULTS, SETUP_SUB,  # noqa: E402
                                   _hand as design_hand, design_sections, first_sentence, sentences, units_of)
from relwork_stats import BOLD_HEAD, REFS, q, table  # noqa: E402

HASH_HEAD = re.compile(_HEAD + r"(\d+(?:\.\d+)*)\s+([A-Za-z(][^\n]*)", re.M)   # the shared parser wants a letter first and skips "4.1 (RQ1) Do ..."


def headings(md):
    """Every numbered heading as (start, end, number tuple, title), both forms, in order; unlike
    relwork_stats.headings a title may open with a parenthesis (Code Clones, Comment Traps)."""
    out = []
    for rx in (HASH_HEAD, BOLD_HEAD):
        for m in rx.finditer(md):
            out.append((m.start(), m.end(), tuple(int(x) for x in m.group(1).split(".")), m.group(2).strip()))
    return sorted(out)


# Assistant-set rules; tune them for a new venue.
START = re.compile(r"\bresults?\b|evaluation|experiment|empirical study|\bfindings\b|\bRQ\s*-?\s*\d", re.I)
NOT_START = re.compile(r"setup|settings?\b|design$|methodology|methods$|details|construction", re.I)
END = re.compile(r"threat|^discussion|related work|conclu|implication|recommendation|limitation|future work"
                 r"|data.availab|acknowledg|lessons", re.I)
PROPOSAL = re.compile(r"approach|technique|framework|algorithm|application|usage|mitigation|implementation|^design$", re.I)
XREF = re.compile(r"\[(\d+(?:\.\d+)?)\]\(#page-[^)]*\)")
RQ_TOKEN = re.compile(r"\(?\bRQ\s*-?\s*\d+\)?\s*[:.\-–]?\s*", re.I)
RQ_NUM = re.compile(r"\bRQ\s*-?\s*(\d+)")
# Folder-name prefix -> dict(start=N, end=M, why="...") (end exclusive) for papers whose results the
# rules misread.
HAND_RESULTS = {}
# Folder-name prefix -> a caveat printed in the report.
NOTES = {}
TOPICS = (
    ("setup", re.compile(r"study design|experimental setup|evaluation setup|^setup|\bsettings?\b|procedure|protocol"
                         r"|^datasets?\b|^subjects\b|^baselines\b|^metrics\b|implementation details", re.I)),
    ("rq", re.compile(r"\bRQ\s*-?\s*\d|research question", re.I)),
    ("question", re.compile(r"\?\s*$|^(?:how|what|which|does|do|can|is|are|why|when|to what extent|whether)\b", re.I)),
    ("results", re.compile(r"^(?:experimental |evaluation |analysis )?(?:results?|findings)$", re.I)),
    ("summary", re.compile(r"summar|takeaway|answer|overall|main results|key findings|overview", re.I)),
    ("ablation", re.compile(r"ablation|sensitivity|hyper.?parameter|\bparameters?\b|impact of|effect of|influence of|role of", re.I)),
    ("qualitative", re.compile(r"case stud|example|qualitative|error analysis|failure|manual|illustrat|user study", re.I)),
    ("efficiency", re.compile(r"efficien|\bcosts?\b|\btime\b|overhead|runtime|scalab|energy|speed|latency|resource", re.I)),
    ("generalization", re.compile(r"generali|transfer|robust|additional|extension|real.world|in.the.wild|practical|beyond|cross", re.I)),
    ("comparison", re.compile(r"compar|versus|\bvs\b|against|baseline|state.of.the.art|sota|effective|performance|accuracy|quality|correctness", re.I)),
    ("threats", re.compile(r"threat|limitation", re.I)),
    ("discussion", re.compile(r"discussion|implication|analysis|insight|lesson|why", re.I)),
)
BOX_KEY = re.compile(r"^(?:Key\s+)?(?:(Findings?|Summary|Answers?|Takeaways?|Observations?|Insights?|Implications?)\b"
                     r"(?:\s+to\s+RQ\s*-?\s*\d+)?(?:\s+\d+)?|(Results?)\s+\d+)\s*(?:[.:]|$)", re.I)   # Result only with a number: "Results." is a run-in label
MARKERS = {
    "rq": re.compile(r"\bRQ\s*-?\s*\d"),
    "figtab": re.compile(r"\bTab(?:le|\.)s?\s*\d|\bFig(?:ure|s|\.)?\s*\d|\bListing\s*\d", re.I),
    "stats_test": DESIGN_MARKERS["stats_test"],
    "compare": re.compile(r"outperform|surpass|exceed|\bbetter\b|\bworse\b|\bhigher\b|\blower\b|improv|degrad|\bdrops?\b"
                          r"|increas|decreas|\bgains?\b|comparable|on par|superior|inferior|\breduc", re.I),
    "magnitude": re.compile(r"\d+(?:\.\d+)?\s?%|percentage points|\bpp\b|\d+(?:\.\d+)?\s?[x×]\b|\b(?:two|three|four|five|ten|\d+)-?fold"
                            r"|\btimes\b", re.I),
    "hedge": re.compile(r"\bsuggest|\bmay\b|\bmight\b|\blikely\b|possibl|\bappear|\bseem|\btend|\bindicat|not necessarily|\bperhaps\b"
                        r"|\bcould\b", re.I),
    "explain": re.compile(r"\bbecause\b|due to|attribut|\breason|\bexplain|\bsince\b|owing to|we (?:hypothesi[sz]e|conjecture|speculate"
                          r"|believe|suspect)|\bcaus", re.I),
    "example": re.compile(r"for (?:example|instance)|e\.g\.|\bListing\s*\d|an example|as an illustration|\bconsider\b|such as", re.I),
    "negative": re.compile(r"no significant|not (?:statistically )?significant|insignificant|negligible|\bfails? to\b"
                           r"|does not (?:improve|help|hold|outperform|change|differ|affect|matter)"
                           r"|no (?:clear|notable|obvious|consistent|substantial|meaningful) (?:difference|effect|improvement|impact|change|correlation|gain)"
                           r"|none of the", re.I),
    "refback": re.compile(r"\bSection\s*\d|as (?:described|mentioned|discussed|defined|introduced|explained|shown) (?:in|above|earlier)"
                          r"|described in|introduced in|defined in", re.I),
    "implication": re.compile(r"\bimpl(?:y|ies|ication)|practitioners?|developers? (?:should|can|need)|recommend|\bshould\b|suggests? that", re.I),
    "roadmap": DESIGN_MARKERS["roadmap"],
}
NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*%?")
NEXT_KIND = (("discussion", re.compile(r"^discussion", re.I)), ("threats", re.compile(r"threat|limitation", re.I)),
             ("implications", re.compile(r"implication|recommendation|lessons", re.I)), ("related work", re.compile(r"related work", re.I)),
             ("conclusion", re.compile(r"conclu|future work", re.I)), ("proposal", PROPOSAL))


def _hand(name):
    return next((v for k, v in HAND_RESULTS.items() if name.startswith(k)), {})


def _note(name):
    return next((v for k, v in NOTES.items() if name.startswith(k)), "")


def topic_of(label):
    for t, rx in TOPICS:
        if rx.search(label):
            return t
    return "other"


def theme_of(label):
    """Topic of the title with the RQ token removed; 'unnamed' when nothing is left."""
    bare = RQ_TOKEN.sub("", label).strip(" :.-–")
    if not bare or re.fullmatch(r"research questions?", bare, re.I):
        return "unnamed"
    t = topic_of(bare)
    return "other" if t == "rq" else t


def _norm(p):
    p = re.sub(r"^#+\s*", "", p.strip())
    p = re.sub(r"<span[^>]*></span>", "", p).replace("**", "").strip()
    return p


def boxes_in(raw):
    """(non-noise paragraphs, [(index of the box text among them, keyword, words)]). A box line of
    at most eight words is a heading: its text is the next paragraph. Heading lines are dropped by
    is_noise, so the paragraph list is built here from the raw split."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    keep, boxes, pending = [], [], None
    for p in paras:
        norm = _norm(p)
        m = BOX_KEY.match(norm)
        if m:
            kind = (m.group(1) or m.group(2)).lower().rstrip("s")
            if not norm[m.end():].strip():      # heading form: the box text is the next paragraph
                pending = kind
                continue
            keep.append(norm if p.lstrip().startswith("#") else p)   # a hash line with the text inline is kept, hashes off
            boxes.append((len(keep) - 1, kind, word_count(norm)))
            pending = None
            continue
        if is_noise(p):
            continue
        keep.append(p)
        if pending:
            boxes.append((len(keep) - 1, pending, word_count(norm)))
        pending = None
    return keep, boxes


def results_sections(md, ptype, name):
    """[(num, title, raw, subs, mode)] of the run, mode 'complement' (the rest of a design-cut
    section) or 'whole'; plus the top-level headings, whether the design script found any design
    unit, and the design cut flags per taken section."""
    refs = REFS.search(md)
    limit = refs.start() if refs else len(md)
    hs = [h for h in headings(md) if h[0] < limit]
    top = [h for h in hs if len(h[2]) == 1]
    taken, _, extra, _ = design_sections(md, ptype, name)
    cut_of = {t[0]: units_of(*t, force_cut=t[0] in design_hand(name).get("cut", ()))[1] for t in taken}
    after = max([t[0] for t in taken], default=1)
    hand = _hand(name)
    start = hand.get("start")
    if start is None:
        for s, e, num, title in top:
            n, t = num[0], title.strip("* ")
            if n <= 1:
                continue
            if cut_of.get(n) or (n > after and START.search(t) and not NOT_START.search(t)):
                start = n
                break
    run = []
    if start is None:
        return run, top, bool(taken or extra), cut_of
    for i, (s, e, num, title) in enumerate(top):
        n, t = num[0], title.strip("* ")
        if n < start:
            continue
        if n == hand.get("end") or (n > start and not PER_RQ.match(t) and (END.search(t) or PROPOSAL.search(t))):
            break
        end = top[i + 1][0] if i + 1 < len(top) else limit
        subs = [(s2 - e, e2 - e, n2, t2.strip("* ")) for s2, e2, n2, t2 in hs
                if len(n2) == 2 and n2[0] == n and e <= s2 < end]
        if n in cut_of and not cut_of[n]:
            continue   # a design section taken whole
        run.append((n, t, md[e:end], subs, "complement" if cut_of.get(n) else "whole"))
    return run, top, bool(taken or extra), cut_of


def results_units_of(title, raw, subs, mode):
    """[(label, text)]: the subsections (from the first RQ- or Results-titled one in complement
    mode), study-design and setup subsections dropped, a preamble first when text precedes the
    subsections in whole mode; a section without subsections is one unit."""
    if not subs:
        return [(title, raw)]
    j0 = 0
    if mode == "complement":
        j0 = next((j for j, s in enumerate(subs) if RESULTS.search(s[3])), None)
        if j0 is None:
            return []
    out = []
    if mode == "whole" and clean_paragraphs(raw[:subs[0][0]]):
        out.append(("", raw[:subs[0][0]]))
    for j, (s2, e2, n2, t2) in enumerate(subs):
        if j < j0 or SETUP_SUB.search(t2):
            continue
        end2 = subs[j + 1][0] if j + 1 < len(subs) else len(raw)
        out.append((t2, raw[e2:end2]))
    return out


def _numbers(sent):
    return len(NUMBER.findall(MARKERS["figtab"].sub(" ", sent)))


def unit_row(name, section, idx, label, text):
    paras = clean_paragraphs(text)
    sents = sentences(text)
    lens = [word_count(s) for s in sents]
    keep, boxes = boxes_in(text)
    first = first_sentence(text)
    lead = sentences(paras[0])[0] if paras and sentences(paras[0]) else ""
    return dict(paper=name, section=section, unit=idx, label=label,
                topic="preamble" if label == "" else topic_of(label),
                theme="preamble" if label == "" else theme_of(label),
                level3=len(re.findall(r"^#+\s*(?:<span[^>]*></span>\s*)*(?:\*\*)?\s*\d+\.\d+\.\d+\s", text, re.M)),
                words=sum(word_count(p) for p in paras), paragraphs=len(paras), sentences=len(sents),
                sent_median=statistics.median(lens) if lens else None,
                cite_groups=count_citations(text)[0], formulas=len(FORMULA.findall(text)),
                tables_ref=len(set(re.findall(r"\bTab(?:le|\.)s?\s*(\d+)", _plain(text), re.I))),
                figures_ref=len(set(re.findall(r"\bFig(?:ure|s|\.)?\s*(\d+)", _plain(text), re.I))),
                boxes=len(boxes), box_kinds=" ".join(k for _, k, _ in boxes),
                box_words=statistics.median([w for _, _, w in boxes]) if boxes else None,
                ends_with_box=bool(boxes) and boxes[-1][0] == len(keep) - 1,
                opens_with_figtab=bool(MARKERS["figtab"].search(lead)),
                rq_numbers=len(set(RQ_NUM.findall(label + " " + text))),
                num_sent_share=round(sum(1 for s in sents if _numbers(s)) / len(sents), 2) if sents else None,
                list_paras=sum(1 for p in paras if any(LIST_ITEM.match(l) for l in p.splitlines())),
                runin_paras=sum(1 for p in paras if RUNIN.match(_norm(p)) and not BOX_KEY.match(_norm(p))),
                first_sentence=first)


def next_kind(title):
    for k, rx in NEXT_KIND:
        if rx.search(title):
            return k
    return "other"


def features(name, md_path):
    with open(md_path, encoding="utf-8") as fh:
        md = XREF.sub(r"\1", fh.read())
    ptype = HAND.get(name, {"type": "unlabelled"})["type"]
    run, top, design_found, cut_of = results_sections(md, ptype, name)
    row = dict(paper=name, year=name[3:7], layout="none", sections="", titles="", first_section=None, n_top=len(top),
               position=None, prev="", prev_kind="", next="", next_kind="", design_found=design_found,
               n_sections=len(run), flat_sections=0, units=0, preamble_units=0, level3=0,
               rq_level="none", rq_count=0, units_per_rq=None, topics="", themes="",
               words=0, share=None, paragraphs=0, sentences=0, sent_median=None, sent_max=0, long40=0,
               cite_groups=0, cites_per_100w=None, formulas=0, tables_in=0, tables_ref=0, figures_in=0, figures_ref=0,
               boxes=0, box_kinds="", box_words=None, units_ending_with_box=0, opens_with_figtab_units=0,
               num_sent_share=None, numbers_per_100w=None, list_paras=0, runin_paras=0,
               opens_with_roadmap=False, first_sentence="", note=_note(name), hand=_hand(name).get("why", ""))
    for m in MARKERS:
        row["m_" + m] = 0
    units, texts = [], []
    for num, title, raw, subs, mode in run:
        us = results_units_of(title, raw, subs, mode)
        row["flat_sections"] += int(not subs)
        for label, text in us:
            units.append(unit_row(name, num, len(units) + 1, label, text))
            texts.append(text)
    if not units:
        return row, units
    nums = [t[2][0] for t in top]
    first, last = run[0][0], run[-1][0]
    i, j = nums.index(first), nums.index(last)
    row["prev"] = top[i - 1][3].strip("* ") if i else ""
    row["prev_kind"] = "" if not i else "design" if (top[i - 1][2][0] in cut_of or (DESIGN.search(row["prev"]) and not PROPOSAL.search(row["prev"]))) \
        else "approach" if PROPOSAL.search(row["prev"]) else "other"
    row["next"] = top[j + 1][3].strip("* ") if j + 1 < len(top) else ""
    row["next_kind"] = next_kind(row["next"]) if row["next"] else ""
    rq_sections = sum(1 for r in run if PER_RQ.match(r[1]))
    modes = {r[4] for r in run}
    row["layout"] = "per-RQ-sections" if rq_sections >= 2 else \
        "undivided" if not design_found and row["flat_sections"] == len(run) else \
        "inside-evaluation" if modes == {"complement"} else "section+inside" if "complement" in modes else "section"
    row.update(first_section=first, position=round(first / len(top), 2),
               sections=" ".join(str(r[0]) for r in run), titles="; ".join(r[1][:40] for r in run))
    all_raw = "\n\n".join(texts)
    paras = [p for t in texts for p in clean_paragraphs(t)]
    sents = [s for t in texts for s in sentences(t)]
    lens = [word_count(s) for s in sents]
    rq_units = sum(1 for u in units if u["topic"] == "rq")
    rq_count = len(set(RQ_NUM.findall(all_raw + " " + " ".join(u["label"] for u in units) + " " + " ".join(r[1] for r in run))))
    row["rq_level"] = "section" if rq_sections >= 2 else "subsection" if rq_units >= 2 else \
        "sub3" if re.search(r"^#+\s*(?:<span[^>]*></span>\s*)*(?:\*\*)?\s*\d+\.\d+\.\d+\s+\(?RQ\s*-?\s*\d", all_raw, re.M) else \
        "prose" if rq_count else "none"
    row.update(units=len(units), preamble_units=sum(1 for u in units if u["label"] == ""),
               level3=sum(u["level3"] for u in units),
               rq_count=rq_count, units_per_rq=round(len(units) / rq_count, 1) if rq_count else None,
               topics=" ".join(u["topic"] for u in units), themes=" ".join(u["theme"] for u in units),
               words=sum(u["words"] for u in units), paragraphs=len(paras), sentences=len(sents),
               sent_median=statistics.median(lens) if lens else None, sent_max=max(lens) if lens else 0,
               long40=sum(1 for n in lens if n >= 40), cite_groups=sum(u["cite_groups"] for u in units),
               formulas=sum(u["formulas"] for u in units),
               tables_in=len(re.findall(r"^\s*(?:<span[^>]*></span>\s*)*(?:\*\*)?Table\s*\d+[.:]", all_raw, re.M | re.I)),
               tables_ref=len(set(re.findall(r"\bTab(?:le|\.)s?\s*(\d+)", _plain(all_raw), re.I))),
               figures_in=len(re.findall(r"!\[\]\(", all_raw)),
               figures_ref=len(set(re.findall(r"\bFig(?:ure|s|\.)?\s*(\d+)", _plain(all_raw), re.I))),
               boxes=sum(u["boxes"] for u in units),
               box_kinds=" ".join(sorted(Counter(k for u in units for k in u["box_kinds"].split()))),
               units_ending_with_box=sum(1 for u in units if u["ends_with_box"]),
               opens_with_figtab_units=sum(1 for u in units if u["opens_with_figtab"]),
               num_sent_share=round(sum(1 for s in sents if _numbers(s)) / len(sents), 2) if sents else None,
               list_paras=sum(u["list_paras"] for u in units), runin_paras=sum(u["runin_paras"] for u in units),
               first_sentence=units[0]["first_sentence"])
    bw = [u["box_words"] for u in units if u["box_words"] is not None]
    row["box_words"] = statistics.median(bw) if bw else None
    body = word_count(body_text(md))
    row["share"] = round(row["words"] / body, 3) if body else None
    row["cites_per_100w"] = round(100 * row["cite_groups"] / row["words"], 1) if row["words"] else None
    row["numbers_per_100w"] = round(100 * sum(_numbers(s) for s in sents) / row["words"], 1) if row["words"] else None
    for m, rx in MARKERS.items():
        row["m_" + m] = sum(1 for s in sents if rx.search(s))
    first_para = clean_paragraphs(texts[0])
    row["opens_with_roadmap"] = bool(first_para) and bool(MARKERS["roadmap"].search(_plain(first_para[0])))
    return row, units


# ---------------------------------------------------------------- report

def _cnt(rows, key):
    return sum(1 for r in rows if r[key])


def report(rows, units):
    with_r = [r for r in rows if r["units"]]
    n = len(with_r)
    layouts = ["section", "section+inside", "inside-evaluation", "per-RQ-sections", "undivided", "none"]
    topics = [t for t, _ in TOPICS] + ["preamble", "other"]
    themes = [t for t, _ in TOPICS if t != "rq"] + ["other", "unnamed"]
    rq_units = [u for u in units if u["topic"] == "rq"]
    L = [f"# Results sections of {len(rows)} {VENUE} papers", "",
         "Generated by `scripts/results_stats.py`; do not edit. The start, stop and complement rules, the unit topics, "
         "the box keywords, the marker regexes and the hand overrides are assistant-set and printed at the top "
         "of the script. Numbers are over all papers; the per-type numbers are in `by_type_report.md`.", "",
         "## 1. Layout and position", "",
         table(["layout", "papers"], [[lay, sum(1 for r in rows if r["layout"] == lay)] for lay in layouts]),
         "section: one or more results-titled top-level sections taken whole; section+inside: such a section plus the rest "
         "of an evaluation section shared with the setup; inside-evaluation: only the rest of an evaluation section shared "
         "with the setup; per-RQ-sections: two or more top-level sections titled by an RQ number; undivided: no design "
         "unit anywhere and the results section has no subsections (setup and results in one block).", "",
         f"- Papers with a results unit: {n} / {len(rows)}; sections per paper: {q([r['n_sections'] for r in with_r])}; "
         f"papers with a results section that has no numbered subsections: {_cnt(with_r, 'flat_sections')}.",
         "- First results section number: " + ", ".join(f"{k} in {v}" for k, v in sorted(Counter(r['first_section'] for r in with_r).items()))
         + f"; relative position in the body: {q([r['position'] for r in with_r])}.",
         "- What precedes the first results section: " + ", ".join(f"{k} {v}" for k, v in Counter(r["prev_kind"] for r in with_r).most_common()) + ".",
         "- What follows the last results section: " + ", ".join(f"{k} {v}" for k, v in Counter(r["next_kind"] for r in with_r).most_common()) + ".",
         "- Hand overrides: " + "; ".join(f"{r['paper'][:35]} ({r['hand']})" for r in rows if r["hand"]) + ".",
         "- Counted under a caveat: " + "; ".join(f"{r['paper'][:35]} ({r['note']})" for r in rows if r["note"]) + ".", "",
         "## 2. Length", "",
         f"- Results words: {q([r['words'] for r in with_r])}",
         f"- Share of the body: {q([r['share'] for r in with_r])}",
         f"- Units per paper: {q([r['units'] for r in with_r])}; papers with a preamble unit: {_cnt(with_r, 'preamble_units')} / {n}; "
         f"papers with level-3 subsections inside the results: {_cnt(with_r, 'level3')} / {n}",
         f"- Words per unit (subsection): {q([u['words'] for u in units if u['label']])}; preamble words: {q([u['words'] for u in units if not u['label']])}",
         f"- Paragraphs: {q([r['paragraphs'] for r in with_r])}; words per paragraph (paper medians): "
         f"{q([round(r['words'] / r['paragraphs']) for r in with_r if r['paragraphs']])}", "",
         "## 3. Organization by research question", "",
         table(["RQ level", "papers"], [[k, sum(1 for r in with_r if r["rq_level"] == k)] for k in ("section", "subsection", "sub3", "prose", "none")]),
         "section: top-level sections titled by RQ; subsection: two or more level-2 units titled by RQ; sub3: RQ titles only "
         "at level 3; prose: RQ numbers appear only in the text or boxes; none: no RQ number in the results.", "",
         f"- Distinct RQ numbers in the results: {q([r['rq_count'] for r in with_r if r['rq_count']])} (papers with any: {_cnt(with_r, 'rq_count')} / {n})",
         f"- Units per RQ (papers with RQs): {q([r['units_per_rq'] for r in with_r])}",
         f"- Words per RQ unit: {q([u['words'] for u in rq_units])}; paragraphs per RQ unit: {q([u['paragraphs'] for u in rq_units])}; "
         f"RQ units with a box: {sum(1 for u in rq_units if u['boxes'])} / {len(rq_units)}; RQ units ending with a box: "
         f"{sum(1 for u in rq_units if u['ends_with_box'])} / {len(rq_units)}; RQ units opening on a table or figure: "
         f"{sum(1 for u in rq_units if u['opens_with_figtab'])} / {len(rq_units)}", "",
         "## 4. Unit topics and themes", "",
         "Topic is the first match on the unit title; theme is the topic of the title with the RQ token removed.", "",
         table(["topic", "papers", "units", "words per unit"],
               [[t, sum(1 for r in with_r if t in r["topics"].split()), sum(1 for u in units if u["topic"] == t),
                 q([u["words"] for u in units if u["topic"] == t])] for t in topics]), "",
         table(["theme", "papers", "units", "of which RQ units"],
               [[t, sum(1 for r in with_r if t in r["themes"].split()), sum(1 for u in units if u["theme"] == t),
                 sum(1 for u in rq_units if u["theme"] == t)] for t in themes]), "",
         "Theme order per paper:", ""]
    L += [f"- {r['paper'][8:48]}: {r['themes']}" for r in with_r]
    L += ["", "## 5. Prose form", "",
          f"- Sentences: {q([r['sentences'] for r in with_r])}; median sentence length (paper medians): {q([r['sent_median'] for r in with_r])}; "
          f"longest sentence: {q([r['sent_max'] for r in with_r])}; sentences of 40 words or more: {q([r['long40'] for r in with_r])}",
          f"- Share of sentences carrying a number: {q([r['num_sent_share'] for r in with_r])}; numbers per 100 words: {q([r['numbers_per_100w'] for r in with_r])}",
          f"- Citation groups per 100 words: {q([r['cites_per_100w'] for r in with_r])}; papers with no citation at all: "
          f"{sum(1 for r in with_r if not r['cite_groups'])} / {n}",
          f"- Papers with a formula: {_cnt(with_r, 'formulas')} / {n}",
          f"- Tables referenced (distinct numbers): {q([r['tables_ref'] for r in with_r])}; table captions inside the results: {q([r['tables_in'] for r in with_r])}",
          f"- Figures referenced (distinct numbers): {q([r['figures_ref'] for r in with_r])}; figures inside the results: {q([r['figures_in'] for r in with_r])}",
          f"- Papers with a list paragraph: {_cnt(with_r, 'list_paras')} / {n}; with a run-in labeled paragraph: {_cnt(with_r, 'runin_paras')} / {n}; "
          f"run-in paragraphs per paper: {q([r['runin_paras'] for r in with_r])}",
          f"- First results unit opens with a roadmap or 'we describe' sentence: {_cnt(with_r, 'opens_with_roadmap')} / {n}; "
          f"units opening on a table or figure: {sum(u['opens_with_figtab'] for u in units)} / {len(units)}", "",
          "## 6. Boxes (Finding, Summary, Answer to RQn, Takeaway, Observation, Insight, Implication)", "",
          f"- Papers with a box: {_cnt(with_r, 'boxes')} / {n}; boxes per paper (papers with any): {q([r['boxes'] for r in with_r if r['boxes']])}; "
          f"box length in words (paper medians): {q([r['box_words'] for r in with_r])}",
          "- Keyword, papers: " + ", ".join(f"{k} {v}" for k, v in Counter(k for r in with_r for k in r["box_kinds"].split()).most_common()) + ".",
          f"- Units ending with a box, papers with boxes: {q([round(r['units_ending_with_box'] / r['units'], 2) for r in with_r if r['boxes']])} "
          f"(share of the paper's units)", "",
          "## 7. Marker sentences (papers with at least one; median count per paper)", "",
          table(["marker", "papers", "median per paper", "median share of sentences"],
                [[m, _cnt(with_r, "m_" + m), f"{statistics.median([r['m_' + m] for r in with_r]):g}",
                  f"{statistics.median([r['m_' + m] / r['sentences'] for r in with_r if r['sentences']]):.2f}"] for m in MARKERS]), "",
          "## 8. Every paper", "",
          table(["paper", "layout", "sections", "next", "words", "units", "RQ level", "RQs", "cites/100w", "num share", "tables", "figures", "boxes", "stats"],
                [[r["paper"][8:50], r["layout"], r["sections"], r["next_kind"], r["words"], r["units"], r["rq_level"], r["rq_count"],
                  "" if r["cites_per_100w"] is None else r["cites_per_100w"], "" if r["num_sent_share"] is None else r["num_sent_share"],
                  r["tables_ref"], r["figures_ref"], r["boxes"], r["m_stats_test"]] for r in rows]), "",
          "## 9. Opening sentence of the first results unit", ""]
    L += [f"- {r['paper'][8:44]}: {r['first_sentence']}" for r in with_r]
    L += ["", f"Units: {len(units)} (" + ", ".join(f"{k} {v}" for k, v in Counter(u['topic'] for u in units).most_common()) + ")."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="write the results units of every paper to this directory and stop")
    args = ap.parse_args()
    rows, units = [], []
    for name, md in paper_paths():
        r, us = features(name, md)
        rows.append(r)
        units += us
        if args.dump:
            os.makedirs(args.dump, exist_ok=True)
            with open(os.path.join(args.dump, name + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(f"{r['layout']}; sections {r['sections']} ({r['titles']}); prev: {r['prev']} | next: {r['next']}; "
                         f"{r['words']} words; RQ level {r['rq_level']}; boxes {r['boxes']}\n\n")
                for u in us:
                    fh.write(f"{u['unit']}. [{u['topic']}/{u['theme']}, {u['words']} words, {u['paragraphs']} paras, boxes {u['boxes']}] "
                             f"{u['section']} {u['label']}\n    {u['first_sentence']}\n\n")
    if args.dump:
        print(f"dumped {sum(1 for r in rows if r['units'])} papers to {args.dump}")
        return
    os.makedirs(OUT, exist_ok=True)
    for fn, data in (("results_features.csv", rows), ("results_units.csv", units)):
        with open(os.path.join(OUT, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    with open(os.path.join(OUT, "results_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(rows, units))
    print(f"{len(rows)} papers, {sum(1 for r in rows if r['units'])} with results units, {len(units)} units "
          f"-> {OUT}/results_features.csv, results_units.csv, results_report.md")


if __name__ == "__main__":
    main()
