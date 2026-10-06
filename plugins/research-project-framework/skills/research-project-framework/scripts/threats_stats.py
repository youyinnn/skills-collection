#!/usr/bin/env python3
"""Threats-to-validity statistics over a venue sample: heading and placement, length, how the section
is divided (validity categories, topic labels, ordinals, none), the validity category and topic of
each unit, and marker sentences (mitigation, disclaimer, residual risk, future work, released
material, ...). Papers the rules misread are set by hand in HAND_THREATS.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/threats_stats.py          # threats_features.csv, threats_units.csv, threats_report.md
  python scripts/threats_stats.py --dump   # prints the cut sections
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
from intro_stats import (HAND, LIST_ITEM, OUT, _plain, body_text, clean_paragraphs,  # noqa: E402
                             count_citations, paper_paths, word_count)
from methodology_stats import MARKERS as DESIGN_MARKERS, first_sentence, sentences  # noqa: E402
from relwork_stats import REFS, q, table  # noqa: E402
from results_stats import XREF, headings  # noqa: E402

# Assistant-set rules; tune them for a new venue.
TITLE = re.compile(r"threat|limitation", re.I)
NOT_TITLE = re.compile(r"threat model|^\(?RQ\s*-?\s*\d", re.I)
RUNIN_THREATS = re.compile(r"^(?:\*\*)?(?:\d+(?:\.\d+)*\s+)?Threats?\s+to\s+validity\s*[.:]", re.I)
LABEL = re.compile(r"^(?:\*\*)?(?:(\d+(?:\.\d+)*)\s+)?(?:\[([A-Z][A-Za-z ]{2,30})\]|([A-Z][A-Za-z0-9 &'\-/]{2,70}?)\s*[.:])(?:\*\*)?(?:\s|$)")
BOLD_PHRASE = re.compile(r"^\*\*([A-Z][^*\n]{2,70}?)\*\*(?:\s|$)")
LABEL_STOP = re.compile(r"\b(?:is|are|was|were|has|have|had|can|could|may|might|will|would|should|we|us|this|these|it|its"
                        r"|not|do|does|did|be|there|they|their)\b|^(?:Listing|Table|Figure|Fig|Algorithm|Eq)\b", re.I)
ORDINAL = re.compile(r"^(?:First(?:ly)?|Second(?:ly)?|Third(?:ly)?|Fourth(?:ly)?|Fifth|Finally|Lastly|Another|Additionally|Moreover"
                     r"|Furthermore|Regarding|In terms of|With respect to|As for|Concerning)\b"
                     r"|^(?:The|A|One|Other|Potential) (?:\w+ ){0,3}(?:threats?|limitations?|concerns?|risks?)\b|^Threats to\b|^There is also\b", re.I)
CATEGORIES = (
    ("internal", re.compile(r"\binternal|intrinsic", re.I)),
    ("external", re.compile(r"\bexternal|extrinsic", re.I)),
    ("construct", re.compile(r"\bconstruct\b", re.I)),
    ("conclusion", re.compile(r"conclusion validity|statistical conclusion|\bconclusion\b", re.I)),
    ("reliability", re.compile(r"reliab", re.I)),
)
TOPICS = (
    ("data", re.compile(r"\bdata(?:set)?s?\b|benchmark|corpus|subjects?\b|sample|projects?\b|repositor|seed inputs?|test cases?", re.I)),
    ("model", re.compile(r"\bmodels?\b|\bLLMs?\b|\bLCMs?\b|architecture|network|agents?\b|systems? (?:under|used)", re.I)),
    ("baseline", re.compile(r"baseline|compared approach|existing (?:methods|techniques|approaches|work)|state.of.the.art|competitor", re.I)),
    ("metric", re.compile(r"metrics?\b|measure|operationaliz|proxy|score|oracle|ground truth", re.I)),
    ("manual", re.compile(r"manual|label(?:l)?ing|annotat|subjectiv|human (?:judg|rater|evaluat)|raters?\b|kappa|agreement|taxonomy", re.I)),
    ("randomness", re.compile(r"random|determinis|\bseeds?\b|stochastic|variance|repeat|run-to-run|temperature", re.I)),
    ("hyperparameter", re.compile(r"hyper.?parameter|parameter (?:setting|selection|choice)|threshold|configuration|budget", re.I)),
    ("prompt", re.compile(r"prompt|instruction|wording|template", re.I)),
    ("leakage", re.compile(r"leak|contaminat|memoriz|training data|cutoff|cut-off", re.I)),
    ("implementation", re.compile(r"implement|\bcode\b|\bbugs?\b|\btools?\b|librar|script|framework|infrastructure|hardware|platform", re.I)),
    ("participants", re.compile(r"participant|user study|survey|respondent|interview|expertise", re.I)),
    ("generalization", re.compile(r"generali[sz]|representativ|other (?:languages|domains|tasks|settings)|beyond|real.world|in practice|deployment", re.I)),
    ("scope", re.compile(r"\bonly\b|\bsingle\b|limited to|scope|focus(?:es|ed)? (?:on|solely)|exclusively|coverage|completeness", re.I)),
)
MARKERS = {
    "category": re.compile(r"(?:internal|external|construct|conclusion|intrinsic|extrinsic) (?:validity|threats?)|threats? to (?:the )?(?:internal|external|construct|conclusion)", re.I),
    "define": re.compile(r"(?:validity|threats?) (?:concerns?|refers?|relates?|pertains?|(?:is|are) (?:concerned|about|related))\b"
                         r"|(?:concerns?|refers? to|relates? to|pertains? to) (?:the |whether |how )?(?:generaliz|extent|degree|ability|factors)", re.I),
    "mitigate": re.compile(r"mitigat|alleviat|to (?:address|reduce|limit|minimi[sz]e|counter|avoid|control|lessen) (?:this|these|the|such|that)|we (?:addressed|reduced|controlled)"
                           r"|to (?:ensure|guarantee)|to reduce (?:this|the) (?:threat|risk|bias)", re.I),
    "dismiss": re.compile(r"we believe|we argue|does not (?:significantly )?(?:affect|impact|threaten|compromise|invalidate)|limited impact|not a (?:severe|major|significant|serious) (?:threat|concern|issue)"
                          r"|unlikely to|negligible|minor|does not undermine|still hold|remain valid", re.I),
    "residual": re.compile(r"may not|might not|cannot|can not|could not|remains? (?:a |an )?(?:open|threat|limitation|unclear|possible)|not (?:fully |completely |perfectly )?(?:capture|cover|generaliz|represent|reflect|guarantee)"
                           r"|beyond (?:the scope|our control)|no (?:control|guarantee)|we (?:do not|did not|have not|could not)|(?:is|are) not (?:possible|feasible|available)", re.I),
    "future": re.compile(r"future work|in the future|we plan|we (?:leave|intend|aim|will)|further (?:study|research|investigation|work|experiments)|as (?:a )?future|remains? (?:for )?future", re.I),
    "standard": re.compile(r"widely.(?:used|adopted|recognized|accepted|studied)|well.(?:established|known|studied)|\bstandard\b|commonly (?:used|adopted|employed)|state.of.the.art|popular"
                           r"|(?:follow|following|consistent with|adhered? to|align(?:ed)? with|same as|as in) (?:prior|previous|existing|established|the literature|related|recent)", re.I),
    "replication": re.compile(r"replication package|publicly available|open.source|available (?:at|online)|artifact|\brelease|we (?:share|provide|publish)|zenodo|github", re.I),
    "refback": re.compile(r"\bSection\s*\d|as (?:described|mentioned|discussed|defined|introduced|explained|shown|noted|stated) (?:in|above|earlier)|described in|discussed in", re.I),
    "stats_test": DESIGN_MARKERS["stats_test"],
    "number": re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*%?|\b(?:two|three|four|five|six|seven|eight|nine|ten)\b", re.I),
    "cost": re.compile(r"\bcosts?\b|budget|computational (?:constraint|resource|cost)|expensive|time.consuming|effort|resource constraint|prohibitive|afford", re.I),
    "example": re.compile(r"for (?:example|instance)|e\.g\.|such as|an example", re.I),
    "hedge": re.compile(r"\bsuggest|\bmay\b|\bmight\b|\blikely\b|possibl|\bappear|\bseem|\btend|\bindicat|\bperhaps\b|\bcould\b|potential", re.I),
}
NEXT_KIND = (("related work", re.compile(r"related work", re.I)), ("conclusion", re.compile(r"conclu|future work", re.I)),
             ("discussion", re.compile(r"discussion|implication|lesson|recommendation", re.I)),
             ("results", re.compile(r"results?\b|evaluation|experiment|findings|\bRQ\s*-?\s*\d|study", re.I)),
             ("data", re.compile(r"data.availab|acknowledg|ethic", re.I)))
# Folder-name prefix -> dict(none=True, why="...") or other overrides for papers the rules misread.
HAND_THREATS = {}
# Folder-name prefix -> a caveat printed in the report.
NOTES = {}


def _hand(name):
    return next((v for k, v in HAND_THREATS.items() if name.startswith(k)), {})


def _note(name):
    return next((v for k, v in NOTES.items() if name.startswith(k)), "")


def kind_of(title):
    for k, rx in NEXT_KIND:
        if rx.search(title):
            return k
    return "other"


def category_of(text):
    for c, rx in CATEGORIES:
        if rx.search(text):
            return c
    return "none"


def topic_of(text):
    for t, rx in TOPICS:
        if rx.search(text):
            return t
    return "other"


def _norm(p):
    p = re.sub(r"^#+\s*", "", p.strip())
    return re.sub(r"<span[^>]*></span>", "", p).replace("**", "").strip()


def label_of(p):
    """(label, form) when the paragraph opens with a run-in label, else (None, None). Forms: bold,
    numbered, bracket, plain."""
    raw = re.sub(r"<span[^>]*></span>", "", p.strip())
    m = LABEL.match(raw)
    if not m:
        b = BOLD_PHRASE.match(raw)   # "**The internal threat** mainly arises ..." (bold phrase, no period)
        if b and word_count(b.group(1)) <= 8:
            return b.group(1).strip(" .:"), "bold"
        return None, None
    label = (m.group(2) or m.group(3)).strip()
    form = "bold" if raw.startswith("**") else "numbered" if m.group(1) else "bracket" if m.group(2) else "plain"
    n = word_count(label)
    if LABEL_STOP.match(label) or (form == "plain" and (n > 6 or LABEL_STOP.search(label))):
        return None, None
    if n > 8:
        return None, None
    return label, form


def split_labels(paras):
    """clean_paragraphs merges a paragraph ending with a colon into the next one, which hides a
    label line ("... acknowledged:\\n6.9.1 Internal Validity. ...", "... findings:\\nPolysemy in
    neurons. ..."); split such paragraphs again at every line that opens with a label."""
    out = []
    for p in paras:
        lines = p.splitlines()
        cur = [lines[0]]
        for line in lines[1:]:
            if label_of(line)[0]:
                out.append("\n".join(cur))
                cur = [line]
            else:
                cur.append(line)
        out.append("\n".join(cur))
    return out


def threats_heading(md, name):
    """The cut: (heading tuple, title, level, raw text, sub-headings, n_matching, layout) or None.
    hs are all numbered headings before References."""
    refs = REFS.search(md)
    limit = refs.start() if refs else len(md)
    hs = [h for h in headings(md) if h[0] < limit]
    hand = _hand(name)
    if hand.get("none"):
        return None, hs, limit
    matches = [h for h in hs if TITLE.search(h[3]) and not NOT_TITLE.search(h[3].strip("* "))]
    if hand.get("heading"):
        want = tuple(int(x) for x in hand["heading"].split("."))
        matches = [h for h in hs if h[2] == want] + matches
    if not matches:
        return None, hs, limit
    s, e, num, title = matches[0]
    level = len(num)
    nxt = next((h for h in hs if h[0] > s and len(h[2]) <= level), None)
    end = nxt[0] if nxt else limit
    subs = [(s2 - e, e2 - e, n2, t2.strip("* ")) for s2, e2, n2, t2 in hs if len(n2) == level + 1 and n2[:level] == num and e <= s2 < end]
    return (num, title.strip("* "), level, md[e:end], subs, len(matches)), hs, limit


def runin_fallback(md, hs, limit):
    """(text, parent title) of the paragraph run opening with a run-in 'Threats to validity.' label,
    inside the body, or None."""
    body = md[:limit]
    paras = [(m.start(), m.group(0)) for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*", body)]
    for i, (pos, p) in enumerate(paras):
        if RUNIN_THREATS.match(p.strip()) and not any(h[0] == pos for h in hs):
            out = [p]
            for pos2, p2 in paras[i + 1:]:
                if any(h[0] == pos2 for h in hs) or label_of(p2)[0] or re.match(r"^#+\s", p2.strip()) or LIST_ITEM.match(p2):
                    break
                out.append(p2)
            parent = next((h for h in reversed(hs) if h[0] < pos), None)
            return "\n\n".join(out), (parent[3].strip("* ") if parent else "")
    return None


def units_of(raw, subs, level):
    """[(label, form, text)], mode. Label '' marks a preamble."""
    if subs:
        out = []
        if clean_paragraphs(raw[:subs[0][0]]):
            out.append(("", "preamble", raw[:subs[0][0]]))
        for j, (s2, e2, n2, t2) in enumerate(subs):
            end2 = subs[j + 1][0] if j + 1 < len(subs) else len(raw)
            out.append((t2, "sub", raw[e2:end2]))
        return out, "sub3"
    paras = split_labels(clean_paragraphs(raw))
    if not paras:
        return [], "none"
    labels = [label_of(p) for p in paras]
    if sum(1 for l, _ in labels if l) >= 2 or (len(paras) == 1 and labels[0][0]):
        out = []
        for p, (l, f) in zip(paras, labels):
            if l:
                out.append((l, f, p))
            elif out:
                out[-1] = (out[-1][0], out[-1][1], out[-1][2] + "\n\n" + p)
            else:
                out.append(("", "preamble", p))
        return out, "runin"
    lists = [p for p in paras if sum(1 for l in p.splitlines() if LIST_ITEM.match(l)) >= 2]
    if lists:
        k = paras.index(lists[0])
        out = [("", "preamble", "\n\n".join(paras[:k]))] if k else []
        for line in lists[0].splitlines():
            if LIST_ITEM.match(line):
                item = LIST_ITEM.sub("", line, count=1).strip()
                l, f = label_of(item)
                out.append((l or first_sentence(item)[:60], f or "item", item))
            elif out:
                out[-1] = (out[-1][0], out[-1][1], out[-1][2] + "\n" + line)
        for p in paras[k + 1:]:   # text after the list attaches to the last item
            out[-1] = (out[-1][0], out[-1][1], out[-1][2] + "\n\n" + p)
        return out, "list"
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
    head = (label + ". " + " ".join(sents[:2]))[:300]   # the label and the first two sentences name the category and the threat
    return dict(paper=name, unit=idx, label=label, form=form,
                category="preamble" if form == "preamble" else category_of(head),
                topic="preamble" if form == "preamble" else topic_of(head),
                words=sum(word_count(p) for p in paras), paragraphs=len(paras), sentences=len(sents),
                sent_median=statistics.median(lens) if lens else None,
                cite_groups=count_citations(text)[0],
                m_mitigate=sum(1 for s in sents if MARKERS["mitigate"].search(s)),
                m_dismiss=sum(1 for s in sents if MARKERS["dismiss"].search(s)),
                m_residual=sum(1 for s in sents if MARKERS["residual"].search(s)),
                first_sentence=first_sentence(text))


def scheme_of(mode, units, text):
    labeled = [u for u in units if u["form"] != "preamble"]
    cats = [u["category"] for u in labeled if u["category"] != "none"]
    mentioned = {c for c, rx in CATEGORIES if rx.search(text) and c != "reliability"}
    if mode == "sub3" and len(labeled) >= 2:
        return "validity-subsections" if len(cats) >= max(2, len(labeled) // 2) else "topic-subsections"
    if mode in ("runin", "list") and len(labeled) >= 2:
        return "validity-labels" if len(cats) >= max(2, len(labeled) // 2) else "topic-labels"
    if len(set(cats)) >= 2 or len(mentioned) >= 2:
        return "validity-prose"
    return "enumerated" if mode == "ordinal" else "prose"


def features(name, md_path):
    with open(md_path, encoding="utf-8") as fh:
        md = XREF.sub(r"\1", fh.read())
    row = dict(paper=name, year=name[3:7], layout="none", title="", title_kind="", number="", level=None, n_matching=0,
               position=None, parent="", parent_kind="", parent_subs=0, sub_index=None, is_last_sub=None,
               prev="", prev_kind="", next="", next_kind="",
               mode="", scheme="", units=0, threats=0, preamble_words=0, categories="", category_order="",
               n_categories=0, mentioned="", topics="",
               words=0, share=None, paragraphs=0, sentences=0, sent_median=None, sent_max=0, long40=0,
               cite_groups=0, cites_per_100w=None, formulas=0, tables_ref=0, figures_ref=0, list_paras=0, runin_paras=0,
               first_sentence="", note=_note(name), hand=_hand(name).get("why", ""))
    for m in MARKERS:
        row["m_" + m] = 0
    cut, hs, limit = threats_heading(md, name)
    top = [h for h in hs if len(h[2]) == 1]

    def none_row():   # no section: numeric fields empty so that medians and fractions skip the paper
        for k, v in row.items():
            if v == 0 and k != "n_matching":
                row[k] = None
        row.update(mode="none", scheme="none")
        return row, []
    if cut:
        num, title, level, raw, subs, n_matching = cut
        row.update(title=title, number=".".join(map(str, num)), level=level, n_matching=n_matching,
                   layout="section" if level == 1 else "subsection" if level == 2 else "sub3",
                   title_kind="both" if re.search(r"threat", title, re.I) and re.search(r"limitation", title, re.I)
                   else "threats" if re.search(r"threat", title, re.I) else "limitations")
        nums = [t[2][0] for t in top]
        if num[0] in nums:
            i = nums.index(num[0])
            row["position"] = round((i + 1) / len(top), 2)
            if level == 1:
                row["prev"] = top[i - 1][3].strip("* ") if i else ""
                row["next"] = top[i + 1][3].strip("* ") if i + 1 < len(top) else ""
            else:
                parent = next((h for h in hs if h[2] == num[:-1]), None)
                row["parent"] = parent[3].strip("* ") if parent else top[i][3].strip("* ")
                sibs = [h for h in hs if len(h[2]) == level and h[2][:-1] == num[:-1]]
                row["parent_subs"] = len(sibs)
                row["sub_index"] = next((k + 1 for k, h in enumerate(sibs) if h[2] == num), None)
                row["is_last_sub"] = row["sub_index"] == len(sibs)
                row["next"] = next((h[3].strip("* ") for h in hs if h[0] > cut_end(hs, num, level, limit) - 1 and len(h[2]) <= level), "")
        row["prev_kind"] = kind_of(row["prev"]) if row["prev"] else ""
        row["next_kind"] = kind_of(row["next"]) if row["next"] else ""
        row["parent_kind"] = kind_of(row["parent"]) if row["parent"] else ""
        us, mode = units_of(raw, subs, level)
    else:
        fb = runin_fallback(md, hs, limit)
        if not fb:
            return none_row()
        raw, parent = fb
        row.update(layout="runin", parent=parent, parent_kind=kind_of(parent), title_kind="threats")
        l, f = label_of(raw)
        us, mode = [(l or "Threats to validity", f or "plain", "\n\n".join(clean_paragraphs(raw)))], "runin"
    units = [unit_row(name, k + 1, l, f, t) for k, (l, f, t) in enumerate(us)]
    if not units:
        return none_row()
    paras = clean_paragraphs(raw)
    sents = sentences(raw)
    lens = [word_count(s) for s in sents]
    labeled = [u for u in units if u["form"] != "preamble"]
    order = []
    for u in labeled:
        if u["category"] != "none" and u["category"] not in order:
            order.append(u["category"])
    row.update(mode=mode, scheme=scheme_of(mode, units, _plain(raw)), units=len(units), threats=len(labeled),
               preamble_words=sum(u["words"] for u in units if u["form"] == "preamble"),
               categories=" ".join(sorted(set(order))), category_order=" ".join(order), n_categories=len(order),
               mentioned=" ".join(c for c, rx in CATEGORIES if rx.search(_plain(raw))),
               topics=" ".join(u["topic"] for u in labeled),
               words=sum(u["words"] for u in units), paragraphs=len(paras), sentences=len(sents),
               sent_median=statistics.median(lens) if lens else None, sent_max=max(lens) if lens else 0,
               long40=sum(1 for n in lens if n >= 40), cite_groups=sum(u["cite_groups"] for u in units),
               formulas=len(FORMULA.findall(raw)),
               tables_ref=len(set(re.findall(r"\bTab(?:le|\.)s?\s*(\d+)", _plain(raw), re.I))),
               figures_ref=len(set(re.findall(r"\bFig(?:ure|s|\.)?\s*(\d+)", _plain(raw), re.I))),
               list_paras=sum(1 for p in paras if any(LIST_ITEM.match(l) for l in p.splitlines())),
               runin_paras=sum(1 for p in paras if label_of(p)[0]),
               first_sentence=units[0]["first_sentence"])
    body = word_count(body_text(md))
    row["share"] = round(row["words"] / body, 3) if body else None
    row["cites_per_100w"] = round(100 * row["cite_groups"] / row["words"], 1) if row["words"] else None
    for m, rx in MARKERS.items():
        row["m_" + m] = sum(1 for s in sents if rx.search(s))
    return row, units


def cut_end(hs, num, level, limit):
    s = next(h[0] for h in hs if h[2] == num)
    nxt = next((h for h in hs if h[0] > s and len(h[2]) <= level), None)
    return nxt[0] if nxt else limit


# ---------------------------------------------------------------- report

def _cnt(rows, key):
    return sum(1 for r in rows if r[key])


def _counter(rows, key):
    return ", ".join(f"{k} {v}" for k, v in Counter(r[key] for r in rows).most_common())


def report(rows, units):
    with_t = [r for r in rows if r["units"]]
    n = len(with_t)
    labeled = [u for u in units if u["form"] != "preamble"]
    cats = [c for c, _ in CATEGORIES] + ["none"]
    topics = [t for t, _ in TOPICS] + ["other"]
    L = [f"# Threats-to-validity sections of {len(rows)} {VENUE} papers", "",
         "Generated by `scripts/threats_stats.py`; do not edit. The title rule, the run-in fallback, the label and ordinal "
         "forms, the categories, the topics, the marker regexes and the scheme rule are assistant-set and printed "
         "at the top of the script. Numbers are over all papers; the per-type numbers are in `by_type_report.md`.", "",
         "## 1. Layout and position", "",
         table(["layout", "papers"], [[lay, sum(1 for r in rows if r["layout"] == lay)] for lay in ("section", "subsection", "sub3", "runin", "none")]),
         "section: a top-level section; subsection: a level-2 subsection (of a discussion, evaluation or conclusion section); "
         "sub3: a level-3 subsection; runin: a paragraph opening with a run-in 'Threats to validity.' label and no heading; "
         "none: no heading and no such paragraph.", "",
         f"- Papers with a threats section: {n} / {len(rows)}; papers whose section title carries 'threat' only: "
         f"{sum(1 for r in with_t if r['title_kind'] == 'threats')}, 'limitation' only: {sum(1 for r in with_t if r['title_kind'] == 'limitations')}, "
         f"both: {sum(1 for r in with_t if r['title_kind'] == 'both')}; papers with two or more matching headings: {sum(1 for r in with_t if r['n_matching'] >= 2)}.",
         "- Titles: " + ", ".join(f"{k} {v}" for k, v in Counter(re.sub(r'^\d+(\.\d+)*\s+', '', r['title']).title() for r in with_t if r['title']).most_common(8)) + ".",
         "- Top-level number of the section (or of the section holding it): " + ", ".join(f"{k} in {v}" for k, v in sorted(Counter(int(r['number'].split('.')[0]) for r in with_t if r['number']).items()))
         + f"; relative position in the body: {q([r['position'] for r in with_t])}.",
         "- Top-level sections, what precedes: " + _counter([r for r in with_t if r["layout"] == "section"], "prev_kind") + ".",
         "- Top-level sections, what follows: " + _counter([r for r in with_t if r["layout"] == "section"], "next_kind") + ".",
         "- Subsections and run-in paragraphs, the section they sit in: " + _counter([r for r in with_t if r["layout"] != "section"], "parent_kind")
         + f"; subsections that are the last of their section: {sum(1 for r in with_t if r['is_last_sub'])} / {sum(1 for r in with_t if r['is_last_sub'] is not None)}.",
         "- Hand overrides: " + ("; ".join(f"{r['paper'][:35]} ({r['hand']})" for r in rows if r["hand"]) or "none") + ".",
         "- Counted under a caveat: " + ("; ".join(f"{r['paper'][:35]} ({r['note']})" for r in rows if r["note"]) or "none") + ".", "",
         "## 2. Length", "",
         f"- Words: {q([r['words'] for r in with_t])}",
         f"- Share of the body: {q([r['share'] for r in with_t])}",
         f"- Paragraphs: {q([r['paragraphs'] for r in with_t])}; words per paragraph (paper medians): "
         f"{q([round(r['words'] / r['paragraphs']) for r in with_t if r['paragraphs']])}",
         f"- Threats (labeled units) per paper: {q([r['threats'] for r in with_t])}; words per threat unit: {q([u['words'] for u in labeled])}; "
         f"sentences per threat unit: {q([u['sentences'] for u in labeled])}",
         f"- Papers with a preamble before the first threat: {_cnt(with_t, 'preamble_words')} / {n}; preamble words: "
         f"{q([r['preamble_words'] for r in with_t if r['preamble_words']])}", "",
         "## 3. Organization", "",
         table(["mode", "papers"], [[m, sum(1 for r in with_t if r["mode"] == m)] for m in ("sub3", "runin", "list", "ordinal", "paragraphs", "whole")]),
         "sub3: level-3 subsections; runin: paragraphs opening with a run-in label; list: a list of items; ordinal: paragraphs "
         "opening with First, Second, Another, The main threat; paragraphs: plain paragraphs, one threat each; whole: one paragraph.", "",
         table(["scheme", "papers"], [[s, sum(1 for r in with_t if r["scheme"] == s)] for s in
                                      ("validity-subsections", "validity-labels", "topic-subsections", "topic-labels", "validity-prose", "enumerated", "prose")]),
         "validity-*: subsections or labels named by validity category (internal, external, construct, conclusion); topic-*: "
         "named by the threat itself (Selection of datasets, Data Quality); validity-prose: no labels, but two or more categories "
         "named in the text; enumerated: ordinal paragraphs without categories; prose: neither.", "",
         "- Run-in label forms (papers): " + ", ".join(f"{k} {v}" for k, v in Counter(f for r in with_t for f in {u['form'] for u in units if u['paper'] == r['paper']} if f in ('bold', 'plain', 'numbered', 'bracket')).most_common()) + ".",
         f"- Categories named by the units (papers with any): {sum(1 for r in with_t if r['n_categories'])} / {n}; categories per paper: {q([r['n_categories'] for r in with_t if r['n_categories']])}",
         "- Category, papers whose units name it: " + ", ".join(f"{c} {sum(1 for r in with_t if c in r['categories'].split())}" for c in cats[:-1]) + ".",
         "- Category, papers whose text mentions it anywhere: " + ", ".join(f"{c} {sum(1 for r in with_t if c in r['mentioned'].split())}" for c in cats[:-1]) + ".",
         "- Category order (papers with two or more): " + ", ".join(f"{k} {v}" for k, v in Counter(r["category_order"] for r in with_t if r["n_categories"] >= 2).most_common()) + ".", "",
         table(["category", "papers", "units", "words per unit", "sentences per unit"],
               [[c, sum(1 for r in with_t if any(u["category"] == c and u["paper"] == r["paper"] for u in labeled)),
                 sum(1 for u in labeled if u["category"] == c), q([u["words"] for u in labeled if u["category"] == c]),
                 q([u["sentences"] for u in labeled if u["category"] == c])] for c in cats]), "",
         "## 4. Threat topics (first match on the unit label and first sentence)", "",
         table(["topic", "papers", "units", "words per unit"],
               [[t, sum(1 for r in with_t if t in r["topics"].split()), sum(1 for u in labeled if u["topic"] == t),
                 q([u["words"] for u in labeled if u["topic"] == t])] for t in topics]), "",
         "Topic order per paper:", ""]
    L += [f"- {r['paper'][8:48]}: {r['topics']}" for r in with_t]
    L += ["", "## 5. Prose form", "",
          f"- Sentences: {q([r['sentences'] for r in with_t])}; median sentence length (paper medians): {q([r['sent_median'] for r in with_t])}; "
          f"longest sentence: {q([r['sent_max'] for r in with_t])}; sentences of 40 words or more: {q([r['long40'] for r in with_t])}",
          f"- Citation groups per 100 words: {q([r['cites_per_100w'] for r in with_t])}; papers with no citation at all: "
          f"{sum(1 for r in with_t if not r['cite_groups'])} / {n}; citation groups per paper: {q([r['cite_groups'] for r in with_t])}",
          f"- Papers with a formula: {_cnt(with_t, 'formulas')} / {n}; referencing a table: {_cnt(with_t, 'tables_ref')} / {n}; a figure: {_cnt(with_t, 'figures_ref')} / {n}",
          f"- Papers with a list paragraph: {_cnt(with_t, 'list_paras')} / {n}; with a run-in labeled paragraph: {_cnt(with_t, 'runin_paras')} / {n}; "
          f"run-in paragraphs per paper: {q([r['runin_paras'] for r in with_t])}", "",
          "## 6. Marker sentences (papers with at least one; median count per paper; median share of sentences)", "",
          table(["marker", "papers", "median per paper", "median share of sentences"],
                [[m, _cnt(with_t, "m_" + m), f"{statistics.median([r['m_' + m] for r in with_t]):g}",
                  f"{statistics.median([r['m_' + m] / r['sentences'] for r in with_t if r['sentences']]):.2f}"] for m in MARKERS]), "",
          "category: names a validity category; define: defines what the category concerns; mitigate: says how the threat is "
          "reduced; dismiss: says the threat does not affect the findings; residual: says what is not covered or guaranteed; "
          "future: defers to future work; standard: appeals to widely used or prior practice; replication: points to an "
          "artifact; refback: points to a section; stats_test: names a test or correction; number: carries a number; cost: names "
          "a cost or resource limit; example: gives an example; hedge: hedges.", "",
          f"- Threat units with a mitigation sentence: {sum(1 for u in labeled if u['m_mitigate'])} / {len(labeled)}; with a dismissal: "
          f"{sum(1 for u in labeled if u['m_dismiss'])} / {len(labeled)}; with a residual sentence: {sum(1 for u in labeled if u['m_residual'])} / {len(labeled)}; "
          f"with none of the three: {sum(1 for u in labeled if not (u['m_mitigate'] or u['m_dismiss'] or u['m_residual']))} / {len(labeled)}", "",
          "## 7. Every paper", "",
          table(["paper", "layout", "number", "title", "parent or next", "words", "mode", "scheme", "threats", "categories", "cites/100w", "mitigate", "dismiss", "residual"],
                [[r["paper"][8:50], r["layout"], r["number"], r["title"][:30], (r["parent"] or r["next"])[:25], r["words"], r["mode"], r["scheme"],
                  r["threats"], r["category_order"], "" if r["cites_per_100w"] is None else r["cites_per_100w"],
                  r["m_mitigate"], r["m_dismiss"], r["m_residual"]] for r in rows]), "",
          "## 8. Opening sentence", ""]
    L += [f"- {r['paper'][8:44]}: {r['first_sentence']}" for r in with_t]
    L += ["", "## 9. Unit labels per paper (label [category/topic, words])", ""]
    for r in with_t:
        us = [u for u in units if u["paper"] == r["paper"] and u["form"] != "preamble"]
        L.append(f"- {r['paper'][8:44]}: " + "; ".join(f"{u['label'][:45]} [{u['category']}/{u['topic']}, {u['words']}]" for u in us))
    L += ["", f"Units: {len(units)} (" + ", ".join(f"{k} {v}" for k, v in Counter(u['category'] for u in units).most_common()) + ")."]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="write the threats units of every paper to this directory and stop")
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
                         f"{r['words']} words; mode {r['mode']}; scheme {r['scheme']}; mentioned {r['mentioned']}\n\n")
                for u in us:
                    fh.write(f"{u['unit']}. [{u['form']}; {u['category']}/{u['topic']}, {u['words']} words, {u['sentences']} sents, "
                             f"mit {u['m_mitigate']} dis {u['m_dismiss']} res {u['m_residual']}] {u['label']}\n    {u['first_sentence']}\n\n")
    if args.dump:
        print(f"dumped {sum(1 for r in rows if r['units'])} papers to {args.dump}")
        return
    os.makedirs(OUT, exist_ok=True)
    for fn, data in (("threats_features.csv", rows), ("threats_units.csv", units)):
        with open(os.path.join(OUT, fn), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    with open(os.path.join(OUT, "threats_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(rows, units))
    print(f"{len(rows)} papers, {sum(1 for r in rows if r['units'])} with a threats section, {len(units)} units "
          f"-> {OUT}/threats_features.csv, threats_units.csv, threats_report.md")


if __name__ == "__main__":
    main()
