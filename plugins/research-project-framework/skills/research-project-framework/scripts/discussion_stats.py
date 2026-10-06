#!/usr/bin/env python3
"""Discussion-section statistics over a venue sample: heading and layout (own section, folded into the
results, subsection, none), position and neighbours, length, how it is divided, the theme of each
unit (implications, explanation, comparison with prior work, generalisation, case, verification,
cost, summary, future work, threats) and the audiences it names, and marker sentences. Papers the
rules misread are set by hand in HAND.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/discussion_stats.py          # discussion_features.csv, discussion_units.csv, discussion_report.md
  python scripts/discussion_stats.py --dump   # prints every unit for reading
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
from intro_stats import (LIST_ITEM, OUT, _plain, body_text, clean_paragraphs,  # noqa: E402
                             count_citations, paper_paths, word_count)
from methodology_stats import first_sentence, sentences  # noqa: E402
from relwork_stats import REFS, q, table  # noqa: E402
from results_stats import XREF, headings  # noqa: E402
from threats_stats import ORDINAL, kind_of, label_of, split_labels  # noqa: E402

# Assistant-set rules; tune them for a new venue.
WORDS = r"discussion|implication|lesson|recommendation|takeaway|reflection|insight|opportunit"
TITLE = re.compile(WORDS, re.I)
OPENS = re.compile(r"^(?:" + WORDS + r")", re.I)
NOT_TITLE = re.compile(r"threat model|^\(?RQ\s*-?\s*\d", re.I)
MERGED = re.compile(r"(?:results?|evaluation|experiments?|findings|analysis|case stud)", re.I)
THREAT = re.compile(r"threat|limitation", re.I)
TOPICS = (   # first match on the unit label and its first two sentences
    ("threats", re.compile(r"threat|limitation|validity", re.I)),
    ("future", re.compile(r"future|opportunit|open (?:problem|question|challenge)|next steps?|road ?map|outlook|directions?\b", re.I)),
    ("summary", re.compile(r"summar|key findings|overview|recap|in short|main findings", re.I)),
    ("case", re.compile(r"case stud|\bexample|qualitative|error analysis|illustrat|anecdot|walk.?through", re.I)),
    ("validation", re.compile(r"validation|human (?:study|evaluation)|user study|expert|practitioner (?:study|validation|feedback)|survey|interview", re.I)),
    ("cost", re.compile(r"\bcosts?\b|efficien|overhead|latency|token|budget|scal(?:e|ing|ability)|resource", re.I)),
    ("comparison", re.compile(r"compar|prior (?:work|studies|findings|research)|previous (?:work|studies|findings)|existing (?:work|studies)|alignment with|consistent with|contrast|literature|versus|\bvs\b", re.I)),
    ("explanation", re.compile(r"\bwhy\b|rationale|reason|explain|explanation|hypothes|\bcause|interpret|understand|mechanism|account for", re.I)),
    ("generalization", re.compile(r"generali[sz]|applicab|beyond|other (?:languages?|domains?|tasks?|compilers?|models?|settings?|systems?)|extension|transfer|broader", re.I)),
    ("implications", re.compile(r"implication|recommend|suggest|lesson|takeaway|advice|guideline|practical|actionable|for (?:practitioners|developers|researchers|engineers|users|tool)|should\b|call for", re.I)),
)
AUDIENCES = (   # every match on the unit text
    ("practitioner", re.compile(r"practitioners?|developers?|engineers?|programmers?|maintainers?|teams?\b|industry|industrial", re.I)),
    ("researcher", re.compile(r"researchers?|research community|future (?:work|research|studies)|academi", re.I)),
    ("tool", re.compile(r"tool (?:builders?|designers?|developers?|vendors?|makers?)|(?:library|framework|platform|model) (?:vendors?|providers?|developers?|maintainers?)|tool ?smiths?|designers? of", re.I)),
    ("policy", re.compile(r"policy ?makers?|regulators?|standard(?:ization)? bod|educators?|instructors?|organizations?\b|managers?", re.I)),
    ("user", re.compile(r"\busers?\b|end.users?|customers?", re.I)),
)
MARKERS = {
    "implication": re.compile(r"\bshould\b|\bought\b|recommend|we (?:advise|encourage|call|urge|suggest)|suggests? that|need(?:s)? to\b|it is (?:advisable|important|essential|necessary)"
                              r"|practitioners?|developers? (?:can|should|may|need)|tool (?:builders|designers|vendors)|for (?:practitioners|researchers|developers|engineers)", re.I),
    "audience": re.compile(r"\bfor (?:practitioners|researchers|developers|engineers|tool (?:builders|designers|vendors)|policy ?makers|educators|users|the (?:research|SE) community)\b"
                           r"|implications? (?:for|to)\b|(?:practitioners|researchers|developers|engineers) (?:can|should|may|need|could|might|are advised)", re.I),
    "explain": re.compile(r"\bbecause\b|due to|attribut|\breasons?\b|\bexplain|\bsince\b|owing to|we (?:hypothesi[sz]e|conjecture|speculate|believe|suspect|posit)|this (?:suggests|indicates|implies) that|likely (?:because|due|caused)", re.I),
    "compare_prior": re.compile(r"prior (?:work|studies|study|findings|research|results)|previous (?:work|studies|study|findings|research|results)|existing (?:work|studies|literature)|consistent with|in line with|(?:in )?contrast (?:to|with)|contrary to"
                                r"|corroborat|confirms? (?:the|prior|previous|earlier)|aligns? with|unlike\b|differs? from|similar to|reported (?:by|in)|(?:has|have) (?:been )?(?:shown|reported|observed|found) (?:by|in|that)|\bliterature\b", re.I),
    "generalize": re.compile(r"generali[sz]|applicab|other (?:languages?|domains?|tasks?|compilers?|models?|settings?|systems?|datasets?)|beyond (?:the|our|this)|transfer(?:able|s)? to|extend(?:s|ed)? to|broader", re.I),
    "question": re.compile(r"\?\s*$"),
    "rq": re.compile(r"\bRQ\s*-?\s*\d"),
    "figtab": re.compile(r"\bTab(?:le|\.)s?\s*\d|\bFig(?:ure|s|\.)?\s*\d|\bListing\s*\d", re.I),
    "refback": re.compile(r"\bSection\s*\d|as (?:described|mentioned|discussed|defined|introduced|explained|shown|noted|stated|reported) (?:in|above|earlier)|described in|discussed in|reported in", re.I),
    "number": re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*%?|\b(?:two|three|four|five|six|seven|eight|nine|ten)\b", re.I),
    "hedge": re.compile(r"\bsuggest|\bmay\b|\bmight\b|\blikely\b|possibl|\bappear|\bseem|\btend|\bindicat|\bperhaps\b|\bcould\b|potential", re.I),
    "future": re.compile(r"future work|in the future|we plan|we (?:leave|intend|aim|will)|further (?:study|research|investigation|work|experiments)|as (?:a )?future|remains? (?:for )?future|open (?:problem|question|challenge)|opportunit", re.I),
    "cost": re.compile(r"\bcosts?\b|budget|computational (?:constraint|resource|cost)|expensive|time.consuming|effort|overhead|latency|\btokens?\b", re.I),
    "example": re.compile(r"for (?:example|instance)|e\.g\.|such as|an example|consider\b", re.I),
    "we": re.compile(r"\b(?:we|our|ours|us)\b", re.I),
}
# Folder-name prefix -> dict(heading="7") or dict(title=r"^Discussion$") or dict(none=True), plus why="...",
# for papers whose discussion the rules misread.
HAND = {}
# Folder-name prefix -> a caveat printed in the report for papers counted under a caveat.
NOTES = {}


def _hand(name):
    return next((v for k, v in HAND.items() if name.startswith(k)), {})


def _note(name):
    return next((v for k, v in NOTES.items() if name.startswith(k)), "")


def _clean_title(t):
    return re.sub(r"^\d+(?:\.\d+)*\s+", "", t.strip("* ")).strip()


def topic_of(text, label=""):
    """First TOPICS match on the label alone when there is one, else on the text (label plus the
    first two sentences), so that a subsection titled Implications is not turned into an
    explanation unit by a "reason" in its first sentence."""
    for t, rx in TOPICS:
        if label and rx.search(label):
            return t
    for t, rx in TOPICS:
        if rx.search(text):
            return t
    return "other"


def audiences_of(text):
    return [a for a, rx in AUDIENCES if rx.search(text)]


def discussion_heading(md, name):
    """The cut: (num, title, level, raw text, sub-headings, n_matching, layout) or None, plus the
    headings before References and that limit."""
    refs = REFS.search(md)
    limit = refs.start() if refs else len(md)
    hs = [h for h in headings(md) if h[0] < limit]
    hand = _hand(name)
    if hand.get("none"):
        return None, hs, limit
    top = [h for h in hs if len(h[2]) == 1]
    cands = [h for h in top if TITLE.search(h[3]) and not NOT_TITLE.search(_clean_title(h[3]))]
    pick = None
    if hand.get("heading"):
        pick = next((h for h in top if h[2] == (int(hand["heading"]),)), None)
    if hand.get("title"):
        pick = next((h for h in top if re.search(hand["title"], _clean_title(h[3]), re.I)), None)
    if pick is None and cands:
        pick = (next((h for h in cands if OPENS.match(_clean_title(h[3]))), None)
                or next((h for h in cands if re.search(r"discussion", h[3], re.I)), None)
                or cands[0])
    level = 1
    if pick is None:
        subs_c = [h for h in hs if len(h[2]) >= 2 and TITLE.search(h[3]) and not NOT_TITLE.search(_clean_title(h[3]))]
        if not subs_c:
            return None, hs, limit
        pick, level = subs_c[0], len(subs_c[0][2])
    s, e, num, title = pick
    nxt = next((h for h in hs if h[0] > s and len(h[2]) <= level), None)
    end = nxt[0] if nxt else limit
    subs = [(s2 - e, e2 - e, n2, _clean_title(t2)) for s2, e2, n2, t2 in hs if len(n2) == level + 1 and n2[:level] == num and e <= s2 < end]
    ct = _clean_title(title)
    layout = "merged" if (MERGED.search(ct) and re.search(r"discussion", ct, re.I)) else "subsection" if level > 1 else "section"
    return (num, ct, level, md[e:end], subs, len(cands), layout), hs, limit


def units_of(raw, subs):
    """[(label, form, text)], mode. Label '' marks a preamble."""
    if subs:
        out = []
        if clean_paragraphs(raw[:subs[0][0]]):
            out.append(("", "preamble", raw[:subs[0][0]]))
        for j, (s2, e2, n2, t2) in enumerate(subs):
            end2 = subs[j + 1][0] if j + 1 < len(subs) else len(raw)
            text = raw[e2:end2]
            paras = split_labels(clean_paragraphs(text))
            labels = [label_of(p) for p in paras]
            if sum(1 for l, _ in labels if l) >= 2:   # run-in labels inside the subsection are its units
                for p, (l, f) in zip(paras, labels):
                    if l:
                        out.append((t2 + ": " + l, "runin", p))
                    elif out and out[-1][1] == "runin" and out[-1][0].startswith(t2 + ": "):
                        out[-1] = (out[-1][0], out[-1][1], out[-1][2] + "\n\n" + p)
                    else:
                        out.append((t2, "sub", p))
            else:
                out.append((t2, "sub", text))
        return out, "sub"
    paras = split_labels(clean_paragraphs(raw))
    if not paras:
        return [], "none"
    labels = [label_of(p) for p in paras]
    if sum(1 for l, _ in labels if l) >= 2:
        out = []
        for p, (l, f) in zip(paras, labels):
            if l:
                out.append((l, f, p))
            elif out:
                out[-1] = (out[-1][0], out[-1][1], out[-1][2] + "\n\n" + p)
            else:
                out.append(("", "preamble", p))
        return out, "runin"
    ords = [bool(ORDINAL.match(_plain(p).strip())) for p in paras]
    if sum(ords) >= 2:
        out = []
        for p, o in zip(paras, ords):
            if o:
                out.append((first_sentence(p)[:60], "ordinal", p))
            elif out:
                out[-1] = (out[-1][0], out[-1][1], out[-1][2] + "\n\n" + p)
            else:
                out.append(("", "preamble", p))
        return out, "ordinal"
    if len(paras) >= 2:
        return [(first_sentence(p)[:60], "paragraph", p) for p in paras], "paragraphs"
    return [(first_sentence(paras[0])[:60], "whole", paras[0])], "whole"


def unit_row(name, idx, label, form, text):
    paras = clean_paragraphs(text)
    sents = sentences(text)
    lens = [word_count(s) for s in sents]
    head = (label + ". " + " ".join(sents[:2]))[:300]
    plain = _plain(text)
    return dict(paper=name, unit=idx, label=label, form=form,
                topic="preamble" if form == "preamble" else topic_of(head, label if form in ("sub", "runin", "bold", "plain", "numbered", "bracket") else ""),
                audiences=" ".join(audiences_of(plain)),
                words=sum(word_count(p) for p in paras), paragraphs=len(paras), sentences=len(sents),
                sent_median=statistics.median(lens) if lens else None,
                cite_groups=count_citations(text)[0],
                m_implication=sum(1 for s in sents if MARKERS["implication"].search(s)),
                m_explain=sum(1 for s in sents if MARKERS["explain"].search(s)),
                m_compare_prior=sum(1 for s in sents if MARKERS["compare_prior"].search(s)),
                first_sentence=first_sentence(text))


def scheme_of(mode, units):
    labeled = [u for u in units if u["form"] != "preamble"]
    if len(labeled) >= 2:
        if sum(1 for u in labeled if MARKERS["audience"].search(u["label"])) >= 2:
            return "audience-labels"
        if mode == "sub":
            return "question-subsections" if sum(1 for u in labeled if u["label"].rstrip().endswith("?")) >= 2 else "topic-subsections"
        if mode == "runin":
            return "topic-labels"
    return "enumerated" if mode == "ordinal" else "prose"


def features(name, md_path):
    with open(md_path, encoding="utf-8") as fh:
        md = XREF.sub(r"\1", fh.read())
    row = dict(paper=name, year=name[3:7], layout="none", title="", number="", level=None, n_matching=0,
               position=None, parent="", parent_kind="", prev="", prev_kind="", next="", next_kind="",
               mode="", scheme="", units=0, labeled=0, preamble_words=0, topics="", audiences="",
               threats_inside=None, future_inside=None,
               words=0, share=None, paragraphs=0, sentences=0, sent_median=None, sent_max=0, long40=0,
               cite_groups=0, cites_per_100w=None, formulas=0, tables_ref=0, figures_ref=0, list_paras=0, runin_paras=0,
               first_sentence="", note=_note(name), hand=_hand(name).get("why", ""))
    for m in MARKERS:
        row["m_" + m] = 0
    cut, hs, limit = discussion_heading(md, name)
    top = [h for h in hs if len(h[2]) == 1]

    def none_row():
        for k, v in row.items():
            if v == 0 and k != "n_matching":
                row[k] = None
        row.update(mode="none", scheme="none")
        return row, []
    if not cut:
        return none_row()
    num, title, level, raw, subs, n_matching, layout = cut
    row.update(title=title, number=".".join(map(str, num)), level=level, n_matching=n_matching, layout=layout)
    nums = [t[2][0] for t in top]
    if num[0] in nums:
        i = nums.index(num[0])
        row["position"] = round((i + 1) / len(top), 2)
        if level == 1:
            row["prev"] = _clean_title(top[i - 1][3]) if i else ""
            row["next"] = _clean_title(top[i + 1][3]) if i + 1 < len(top) else ""
        else:
            row["parent"] = _clean_title(top[i][3])
            s = next(h[0] for h in hs if h[2] == num)
            nxt = next((h for h in hs if h[0] > s and len(h[2]) <= level), None)
            row["next"] = _clean_title(nxt[3]) if nxt else ""
    row["prev_kind"] = kind_of(row["prev"]) if row["prev"] else ""
    row["next_kind"] = kind_of(row["next"]) if row["next"] else ""
    row["parent_kind"] = kind_of(row["parent"]) if row["parent"] else ""
    us, mode = units_of(raw, subs)
    units = [unit_row(name, k + 1, l, f, t) for k, (l, f, t) in enumerate(us)]
    if not units:
        return none_row()
    paras = clean_paragraphs(raw)
    sents = sentences(raw)
    lens = [word_count(s) for s in sents]
    labeled = [u for u in units if u["form"] != "preamble"]
    plain = _plain(raw)
    row.update(mode=mode, scheme=scheme_of(mode, units), units=len(units), labeled=len(labeled),
               preamble_words=sum(u["words"] for u in units if u["form"] == "preamble"),
               topics=" ".join(u["topic"] for u in labeled),
               audiences=" ".join(sorted({a for u in units for a in u["audiences"].split()})),
               threats_inside=any(u["topic"] == "threats" for u in labeled) or bool(THREAT.search(" ".join(u["label"] for u in labeled))),
               future_inside=any(u["topic"] == "future" for u in labeled),
               words=sum(u["words"] for u in units), paragraphs=len(paras), sentences=len(sents),
               sent_median=statistics.median(lens) if lens else None, sent_max=max(lens) if lens else 0,
               long40=sum(1 for n in lens if n >= 40), cite_groups=sum(u["cite_groups"] for u in units),
               formulas=len(FORMULA.findall(raw)),
               tables_ref=len(set(re.findall(r"\bTab(?:le|\.)s?\s*(\d+)", plain, re.I))),
               figures_ref=len(set(re.findall(r"\bFig(?:ure|s|\.)?\s*(\d+)", plain, re.I))),
               list_paras=sum(1 for p in paras if any(LIST_ITEM.match(l) for l in p.splitlines())),
               runin_paras=sum(1 for p in paras if label_of(p)[0]),
               first_sentence=units[0]["first_sentence"])
    body = word_count(body_text(md))
    row["share"] = round(row["words"] / body, 3) if body else None
    row["cites_per_100w"] = round(100 * row["cite_groups"] / row["words"], 1) if row["words"] else None
    for m, rx in MARKERS.items():
        row["m_" + m] = sum(1 for s in sents if rx.search(s))
    return row, units


def discussion_text(md, name):
    """The cut text of a standalone or subsection discussion (not merged), for voice_stats; None otherwise."""
    cut, _hs, _limit = discussion_heading(XREF.sub(r"\1", md), name)
    if not cut or cut[6] == "merged":
        return None
    return cut[3]


# ---------------------------------------------------------------- report

def _cnt(rows, key):
    return sum(1 for r in rows if r[key])


def _counter(rows, key):
    return ", ".join(f"{k} {v}" for k, v in Counter(r[key] for r in rows).most_common())


def report(rows, units):
    have = [r for r in rows if r["units"]]
    stand = [r for r in have if r["layout"] != "merged"]
    n = len(stand)
    labeled = [u for u in units if u["form"] != "preamble" and any(r["paper"] == u["paper"] and r["layout"] != "merged" for r in stand)]
    topics = [t for t, _ in TOPICS] + ["other"]
    L = [f"# Discussion sections of {len(rows)} {VENUE} papers", "",
         "Generated by `scripts/discussion_stats.py`; do not edit. The title rule, the candidate ranking, the merged rule, the "
         "unit modes, the topics, the audiences, the marker regexes, the scheme rule and the hand overrides are assistant-set "
         "and printed at the top of the script. Numbers are over all papers; the per-type numbers are in "
         "`by_type_report.md`. Unless a line says otherwise, the length and prose numbers leave out the merged layout.", "",
         "## 1. Layout and position", "",
         table(["layout", "papers"], [[lay, sum(1 for r in rows if r["layout"] == lay)] for lay in ("section", "merged", "subsection", "none")]),
         "section: a top-level discussion-like section; merged: a top-level section whose title joins results or evaluation with "
         "discussion; subsection: a second-level discussion-like heading inside another section; none: no such heading.", "",
         f"- Papers with a standalone discussion-like section or subsection: {n} / {len(rows)}; with two or more matching top-level headings: "
         f"{sum(1 for r in have if r['n_matching'] >= 2)}.",
         "- Titles (standalone): " + ", ".join(f"{k} {v}" for k, v in Counter(r["title"].title() for r in stand).most_common(10)) + ".",
         "- Top-level number: " + ", ".join(f"{k} in {v}" for k, v in sorted(Counter(int(r["number"].split(".")[0]) for r in stand if r["number"]).items()))
         + f"; relative position in the body: {q([r['position'] for r in stand if r['position'] is not None])}.",
         "- Standalone sections, what precedes: " + _counter([r for r in stand if r["layout"] == "section"], "prev_kind") + ".",
         "- Standalone sections, what follows: " + _counter([r for r in stand if r["layout"] == "section"], "next_kind") + ".",
         "- Subsections, the section they sit in: " + (_counter([r for r in stand if r["layout"] == "subsection"], "parent_kind") or "none") + ".",
         f"- Sections holding a threats unit: {sum(1 for r in stand if r['threats_inside'])} / {n}; holding a future-work unit: {sum(1 for r in stand if r['future_inside'])} / {n}.",
         "- Hand overrides: " + ("; ".join(f"{r['paper'][:35]} ({r['hand']})" for r in rows if r["hand"]) or "none") + ".",
         "- Counted under a caveat: " + ("; ".join(f"{r['paper'][:35]} ({r['note']})" for r in rows if r["note"]) or "none") + ".", "",
         "## 2. Length (standalone only)", "",
         f"- Words: {q([r['words'] for r in stand])}",
         f"- Share of the body: {q([r['share'] for r in stand])}",
         f"- Paragraphs: {q([r['paragraphs'] for r in stand])}; words per paragraph (paper medians): "
         f"{q([round(r['words'] / r['paragraphs']) for r in stand if r['paragraphs']])}",
         f"- Labeled units per paper: {q([r['labeled'] for r in stand])}; words per unit: {q([u['words'] for u in labeled])}; "
         f"sentences per unit: {q([u['sentences'] for u in labeled])}",
         f"- Papers with a preamble before the first unit: {_cnt(stand, 'preamble_words')} / {n}; preamble words: "
         f"{q([r['preamble_words'] for r in stand if r['preamble_words']])}",
         f"- Merged layout, words of the whole section: {q([r['words'] for r in have if r['layout'] == 'merged'])}", "",
         "## 3. Organization (standalone only)", "",
         table(["mode", "papers"], [[m, sum(1 for r in stand if r["mode"] == m)] for m in ("sub", "runin", "ordinal", "paragraphs", "whole")]),
         "sub: level-2 subsections; runin: paragraphs opening with a run-in label; ordinal: paragraphs opening with First, "
         "Second, Another; paragraphs: plain paragraphs, one unit each; whole: one paragraph.", "",
         table(["scheme", "papers"], [[s, sum(1 for r in stand if r["scheme"] == s)] for s in
                                      ("audience-labels", "question-subsections", "topic-subsections", "topic-labels", "enumerated", "prose")]),
         "audience-labels: two or more units named by audience (For practitioners:); question-subsections: subsection titles "
         "phrased as questions; topic-*: subsections or labels named by what they discuss; enumerated: ordinal paragraphs; "
         "prose: undivided.", "",
         table(["topic", "papers", "units", "words per unit", "first at unit"],
               [[t, sum(1 for r in stand if t in r["topics"].split()), sum(1 for u in labeled if u["topic"] == t),
                 q([u["words"] for u in labeled if u["topic"] == t]),
                 q([next(k + 1 for k, x in enumerate([v for v in units if v["paper"] == r["paper"] and v["form"] != "preamble"]) if x["topic"] == t)
                    for r in stand if t in r["topics"].split()])] for t in topics]), "",
         "Topic order per paper:", ""]
    L += [f"- {r['paper'][8:48]}: {r['topics']}" for r in stand]
    L += ["", "- Audiences named anywhere in the section (papers): " + ", ".join(f"{a} {sum(1 for r in stand if a in r['audiences'].split())}" for a, _ in AUDIENCES) + ".",
          "- Papers whose units are labeled by audience: " + ", ".join(r["paper"][8:40] for r in stand if r["scheme"] == "audience-labels") + ".", "",
          "## 4. Prose form (standalone only)", "",
          f"- Sentences: {q([r['sentences'] for r in stand])}; median sentence length (paper medians): {q([r['sent_median'] for r in stand])}; "
          f"longest sentence: {q([r['sent_max'] for r in stand])}; sentences of 40 words or more: {q([r['long40'] for r in stand])}",
          f"- Citation groups per 100 words: {q([r['cites_per_100w'] for r in stand])}; papers with no citation at all: "
          f"{sum(1 for r in stand if not r['cite_groups'])} / {n}; citation groups per paper: {q([r['cite_groups'] for r in stand])}",
          f"- Papers with a formula: {_cnt(stand, 'formulas')} / {n}; referencing a table: {_cnt(stand, 'tables_ref')} / {n}; a figure: {_cnt(stand, 'figures_ref')} / {n}",
          f"- Papers with a list paragraph: {_cnt(stand, 'list_paras')} / {n}; with a run-in labeled paragraph: {_cnt(stand, 'runin_paras')} / {n}; "
          f"run-in paragraphs per paper: {q([r['runin_paras'] for r in stand])}", "",
          "## 5. Marker sentences (standalone; papers with at least one; median count per paper; median share of sentences)", "",
          table(["marker", "papers", "median per paper", "median share of sentences"],
                [[m, _cnt(stand, "m_" + m), f"{statistics.median([r['m_' + m] for r in stand]):g}",
                  f"{statistics.median([r['m_' + m] / r['sentences'] for r in stand if r['sentences']]):.2f}"] for m in MARKERS]), "",
          "implication: a should, a recommendation or a named audience; audience: names who the implication is for; explain: gives a "
          "reason for a finding; compare_prior: sets the finding beside prior work; generalize: speaks of other settings; question: "
          "ends with a question mark; rq: names an RQ; figtab: points to a table or figure; refback: points to a section; number: carries "
          "a number; hedge: hedges; future: defers to future work; cost: names a cost; example: gives an example; we: first person.", "",
          f"- Units with an implication sentence: {sum(1 for u in labeled if u['m_implication'])} / {len(labeled)}; with an explanation: "
          f"{sum(1 for u in labeled if u['m_explain'])} / {len(labeled)}; with a comparison to prior work: {sum(1 for u in labeled if u['m_compare_prior'])} / {len(labeled)}", "",
          "## 6. Every paper", "",
          table(["paper", "layout", "number", "title", "prev", "next", "words", "mode", "scheme", "units", "topics", "cites/100w", "implication", "explain", "compare"],
                [[r["paper"][8:50], r["layout"], r["number"], r["title"][:30], (r["prev"] or r["parent"])[:22], r["next"][:22], r["words"], r["mode"], r["scheme"],
                  r["labeled"], r["topics"], "" if r["cites_per_100w"] is None else r["cites_per_100w"],
                  r["m_implication"], r["m_explain"], r["m_compare_prior"]] for r in rows]), "",
          "## 7. Opening sentence (standalone)", ""]
    L += [f"- {r['paper'][8:44]}: {r['first_sentence']}" for r in stand]
    L += ["", "## 8. Unit labels per paper (label [topic; audiences, words])", ""]
    for r in stand:
        us = [u for u in units if u["paper"] == r["paper"] and u["form"] != "preamble"]
        L.append(f"- {r['paper'][8:44]}: " + "; ".join(f"{u['label'][:45]} [{u['topic']}; {u['audiences'] or '-'}, {u['words']}]" for u in us))
    L += ["", f"Units: {len(units)} (" + ", ".join(f"{k} {v}" for k, v in Counter(u['topic'] for u in units).most_common()) + ")."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="write the discussion units of every paper to this directory and stop")
    args = ap.parse_args()
    rows, units = [], []
    for name, md in paper_paths():
        r, us = features(name, md)
        rows.append(r)
        units += us
        if args.dump:
            os.makedirs(args.dump, exist_ok=True)
            with open(os.path.join(args.dump, name + ".txt"), "w", encoding="utf-8") as fh:
                fh.write(f"{r['layout']} {r['number']} {r['title']}; parent: {r['parent']} | prev: {r['prev']} | next: {r['next']}; "
                         f"{r['words']} words; mode {r['mode']}; scheme {r['scheme']}; audiences {r['audiences']}\n\n")
                for u in us:
                    fh.write(f"{u['unit']}. [{u['form']}; {u['topic']}; {u['audiences'] or '-'}, {u['words']} words, {u['sentences']} sents, "
                             f"impl {u['m_implication']} expl {u['m_explain']} cmp {u['m_compare_prior']}] {u['label']}\n    {u['first_sentence']}\n\n")
    if args.dump:
        print(f"dumped {sum(1 for r in rows if r['units'])} papers to {args.dump}")
        return
    os.makedirs(OUT, exist_ok=True)
    for fn, data in (("discussion_features.csv", rows), ("discussion_units.csv", units)):
        with open(os.path.join(OUT, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    with open(os.path.join(OUT, "discussion_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(rows, units))
    print(f"{len(rows)} papers, {sum(1 for r in rows if r['units'])} with a discussion-like section ({sum(1 for r in rows if r['layout'] == 'merged')} merged), "
          f"{len(units)} units -> {OUT}/discussion_features.csv, discussion_units.csv, discussion_report.md")


if __name__ == "__main__":
    main()
