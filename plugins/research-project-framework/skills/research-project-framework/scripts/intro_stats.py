#!/usr/bin/env python3
"""Introduction statistics over a venue sample.

Reads the Marker markdown of every sample paper under derived/papers_marker/<VENUE>/ (config.py),
cuts the introduction, strips the front-matter noise Marker leaves in it, merges paragraphs split at
page breaks, and measures length, paragraphs, sentence length, citation groups per 100 words,
sentence patterns and contribution lists. Paragraph moves (context, problem, gap, this paper,
design, findings, contributions, ...) come from HAND, labelled by hand per paper after --dump.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/intro_stats.py          # intro_features.csv, intro_moves.csv, intro_report.md
  python scripts/intro_stats.py --dump   # prints the cleaned paragraphs for hand labelling

Output goes to the patterns folder set in config.py. Several other *_stats.py scripts reuse the
cutting, cleaning and counting functions defined here.
"""
import argparse
import sys
import csv
from functools import partial
import os
import re
import statistics
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from config import MARKER_DIR, PATTERNS_OUT as OUT, VENUE, need  # noqa: E402

TYPES = ("method", "empirical", "mixed")
# "importance" was added while reading the fourth paper (Calibration): an opener that states why the
# object matters ("Code summaries help maintainers understand code") is neither a trend nor a definition.
OPENERS = ("trend", "problem", "definition", "fact", "question", "importance")
CONTRIB_FIRST = ("propose", "study", "find", "release", "none")
# Move labels, fixed before labelling. X marks a non-prose paragraph the cleaner
# missed (figure content, caption remnant); it is excluded from every count.
MOVES = "CPLETDFKIRX"
MOVE_NAMES = {
    "C": "context", "P": "problem", "L": "limitation of prior work", "E": "example",
    "T": "this paper", "D": "design", "F": "findings", "K": "contributions",
    "I": "implications", "R": "roadmap or artifact", "X": "noise",
}

# Hand labels per sample paper, set after reading the --dump output. Key: the paper's folder name
# under derived/papers_marker/<VENUE>/. Example:
#   "<folder>": dict(type="empirical", opener="trend", moves="CPLTDFK", contrib_first="study"),
# moves has one letter per cleaned paragraph, in order (letters in MOVES above).
HAND = {}

# ---------------------------------------------------------------- cutting and cleaning

_HEAD = r"^#+\s*(?:\*\*)?\s*(?:<span[^>]*></span>\s*)*(?:\*\*)?\s*"
INTRO_HEAD = re.compile(_HEAD + r"1\s+Introduction[^\n]*", re.M | re.I)
SEC2_HEAD = re.compile(_HEAD + r"2\s+\S", re.M)
REFS_HEAD = re.compile(_HEAD + r"(?:\d+\s+)?References", re.M | re.I)

_SPANS = r"^(?:<span[^>]*></span>\s*)*"
NOISE = [
    re.compile(_SPANS + r"Authors?['’]?\s*(Contact Information|address(es)?)", re.I),
    re.compile(_SPANS + r"!\[\]\("),
    re.compile(r"licensed under a Creative Commons", re.I),
    re.compile(_SPANS + r"(?:©|\(c\)|Copyright\b)", re.I),
    re.compile(_SPANS + r"ACM \d{4}-\d{3}[\dX]/"),
    re.compile(_SPANS + r"<sup>"),
    re.compile(_SPANS + r"[∗*†‡]\s*Corresponding author", re.I),
    re.compile(_SPANS + r"(?:Fig\.|Figure|Table)\s*\d+[.:]", re.I),
    re.compile(_SPANS + r"Permission to make digital or hard copies", re.I),
    re.compile(_SPANS + r"(?:ESEC/)?FSE ['’]\d\d,"),        # running header of the ACM version (ESEC/FSE '23 for 2023)
    re.compile(_SPANS + r"#+\s"),                            # stray heading inside the cut (figure text)
    re.compile(_SPANS + r"\([a-z]\)\s+\S+(?:\s+\S+){0,8}$"),   # sub-caption such as (a) Non-coding task alignment
    re.compile(_SPANS + r"\|"),                                # markdown table rows (a table inside the cut)
]
LEAD_IN = re.compile(r"contribution|as follows|following", re.I)
LIST_ITEM = re.compile(r"^\s*(?:[-•]\s?|\*\s|\(\d+\)\s|\d+[.)]\s|[IVX]{1,4}\)\s|\*\*\(?\d+\)?\.?\*\*|(?:\*\*)?RQ\s*\d+)")
# [IVX]{1,4}\) covers contributions written as paragraphs "I) ... IV) ..."
SENT_END = re.compile(r"[.!?:;\"”’']\s*$")


def extract_intro(md):
    """Text between the '1 Introduction' heading and the '2 ...' heading."""
    m = INTRO_HEAD.search(md)
    if not m:
        raise ValueError("no '1 Introduction' heading")
    e = SEC2_HEAD.search(md, m.end())
    if not e:
        raise ValueError("no section 2 heading after the introduction")
    return md[m.end():e.start()]


def body_text(md):
    """From the introduction heading to the References heading (the numbered body)."""
    m = INTRO_HEAD.search(md)
    r = REFS_HEAD.search(md, m.end()) if m else None
    return md[m.end():r.start()] if (m and r) else md[m.end():] if m else md


def is_noise(p):
    return not _plain(p).strip() or any(n.search(p) for n in NOISE)


def clean_paragraphs(text):
    """Paragraphs of the cut text: noise dropped, page-break splits merged, a lead-in (ending
    with a colon, or a short sentence announcing contributions or a list) merged into the
    list that follows, consecutive list items merged into one block."""
    raw = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    raw = [p for p in raw if not is_noise(p)]
    out = []
    for p in raw:
        if out:
            prev = out[-1]
            prev_last = prev.splitlines()[-1]
            short_lead = len(prev.splitlines()) == 1 and word_count(prev) <= 20 and LEAD_IN.search(prev)
            if prev.endswith(":") or (LIST_ITEM.match(p) and (LIST_ITEM.match(prev_last) or short_lead)):
                out[-1] = prev + "\n" + p
                continue
            if not SENT_END.search(_plain(prev_last).rstrip()) and (p[0].islower() or p[0] in "[0123456789"):
                out[-1] = prev + " " + p
                continue
        out.append(p)
    return out


# ---------------------------------------------------------------- features

def _plain(text):
    """Text with markdown link targets, citation brackets and span anchors removed."""
    t = re.sub(r"</?[a-z][^<>\n]{0,80}>", "", text)   # html tags only, never across lines
    t = re.sub(r"\]\([^)]*\)", "]", t)          # [label](target) -> [label]
    t = t.replace("\\[", "[").replace("\\]", "]")
    t = re.sub(r"\[\s*\d+(?:\s*[,–\-]\s*\d+)*\s*\]", " ", t)
    return t


WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*")


def word_count(text):
    return len(WORD.findall(_plain(text)))


NUM_GROUP = re.compile(r"\[\s*(\d+(?:\s*[,–\-]\s*\d+)*)\s*,?\s*\]")
AUTHOR_YEAR = re.compile(r"\[([A-Z][^\[\]]*?\b(?:19|20)\d{2}[a-z]?(?:\s*;\s*[^\[\]]*?\b(?:19|20)\d{2}[a-z]?)*)\]")


def count_citations(text):
    """(bracket groups, references cited). Numeric groups count every number inside; ranges
    such as 3-5 count both ends only (the middle is unknowable from the text). Author-year
    groups count one reference per semicolon-separated entry."""
    t = re.sub(r"</?[a-z][^<>\n]{0,80}>", "", text)   # html tags only, never across lines
    t = re.sub(r"\]\([^)]*\)", "]", t)
    t = t.replace("\\[", "[").replace("\\]", "]")
    t = re.sub(r"\]\s*\[", ", ", t)             # [7][8] -> [7, 8]
    t = re.sub(r",\s*,", ",", t)                # [3,] [4] -> [3, 4] after the line above
    groups = refs = 0
    for m in NUM_GROUP.finditer(t):
        groups += 1
        refs += len(re.findall(r"\d+", m.group(1)))
    for m in AUTHOR_YEAR.finditer(t):
        groups += 1
        refs += len(m.group(1).split(";"))
    return groups, refs


PIVOT = re.compile(r"\b(?:In this (?:paper|work|study|article)|This (?:paper|work|study|article)\b"
                   r"|we (?:present|propose|introduce|conduct|perform|investigate|study|report)"
                   r"|To (?:this end|address|fill|bridge|answer|tackle|overcome))", re.I)
CONTRIB_LEAD = re.compile(r"contribution|we make the following|as follows", re.I)
RQ = re.compile(r"\bRQ\s*(\d+)")
ROADMAP = re.compile(r"(?:rest|remainder) of (?:this|the) (?:paper|article) is (?:organi[sz]ed|structured)"
                     r"|is organi[sz]ed as follows|paper is structured as", re.I)
ARTIFACT = re.compile(r"replication package|artifact|publicly available|available at|open[- ]sourced?"
                      r"|we release|are available|is available", re.I)
NUMBERS = re.compile(r"\d+(?:\.\d+)?\s?%|\b\d+ (?:of|out of) \d+\b|\b\d+(?:\.\d+)?[x×]\b"
                     r"|\b\d+(?:\.\d+)? (?:percentage points|pp)\b")


def pivot_index(paras):
    """1-based index of the first paragraph that says what this paper does, or None."""
    for i, p in enumerate(paras, 1):
        if PIVOT.search(_plain(p)):
            return i
    return None


def _items(block):
    return [l for l in block.splitlines() if LIST_ITEM.match(l) and not RQ.match(l.strip())]


def contribution_list(paras):
    """The contribution list: has it, how many items, which paragraph (1-based), and whether a
    lead-in names it (the word 'contribution' or a 'we make the following' phrase)."""
    for i, p in enumerate(paras, 1):
        items = _items(p)
        first = p.splitlines()[0]
        if items and CONTRIB_LEAD.search(first):
            return dict(has=True, items=len(items), index=i, labelled=bool(re.search("contribution", first, re.I)))
        if items and LIST_ITEM.match(first) and i > 1:
            prev_tail = _plain(paras[i - 2]).strip()[-160:]
            if re.search("contribution", prev_tail, re.I):     # lead-in sits at the end of the previous paragraph
                return dict(has=True, items=len(items), index=i, labelled=True)
    for i, p in enumerate(paras, 1):
        if re.search("contribution", p, re.I):
            inline = len(re.findall(r"\(\d+\)|\b(?:First|Second|Third|Fourth)\b", p))
            items = _items(p)
            return dict(has=True, items=len(items) or inline or 1, index=i, labelled=True)
    return dict(has=False, items=0, index=None, labelled=False)


RUNIN = re.compile(r"^(?:\*\*)?[A-Z][A-Za-z &\-]{2,40}(?<!et al)[.:](?:\*\*)?\s")
TITLED_ITEM = re.compile(r"^\s*(?:[-•]\s?|\*\s|\(\d+\)\s|\d+[.)]\s)(?:\*\*)?[A-Z][A-Za-z &\-]{2,45}[.:]")


def runin_labels(paras):
    """Paragraphs opened by a run-in label such as 'Our work.' or '**Contributions.**'."""
    return sum(1 for p in paras if RUNIN.match(p) and not RQ.match(p))


def rq_numbers(text):
    return len(set(RQ.findall(text)))


def has_figure(raw):
    return bool(re.search(r"!\[\]\(|^(?:Fig\.|Figure)\s*\d+[.:]", raw, re.M | re.I))


def has_table(raw):
    return bool(re.search(r"^Table\s*\d+[.:]|^\|.*\|\s*$", raw, re.M | re.I))


def has_roadmap(text):
    return bool(ROADMAP.search(text))


def has_artifact(text):
    return bool(ARTIFACT.search(_plain(text)))


def tail_has_numbers(paras):
    tail = paras[-max(1, -(-len(paras) // 3)):]   # ceil(n/3)
    return bool(NUMBERS.search(_plain("\n".join(tail))))


COARSE = {"C": "O", "P": "O", "E": "O", "L": "L", "T": "T", "D": "T", "F": "F", "K": "K", "I": "K", "R": "K"}


def coarse_skeleton(moves):
    """Five blocks: O opening (context, problem, example), L limitation, T this paper and design,
    F findings, K closing (contributions, implications, roadmap); runs collapsed, noise dropped."""
    return skeleton("".join(COARSE.get(ch, "X") for ch in moves))


def order_stats(rows, moves_by_paper, pairs=(("C", "L"), ("L", "T"), ("T", "F"), ("F", "K"), ("P", "L"), ("P", "T"))):
    """For each pair (a, b): among papers with both, how many have every a before the first b."""
    out = []
    for a, b in pairs:
        both = before = 0
        for r in rows:
            seq = moves_by_paper[r["paper"]]
            if a in seq and b in seq:
                both += 1
                if max(i for i, m in enumerate(seq) if m == a) < seq.index(b):
                    before += 1
        out.append((f"{a} {MOVE_NAMES[a]} entirely before {b} {MOVE_NAMES[b]}", f"{before}/{both}" if both else "0/0"))
    return out


def skeleton(moves):
    """Consecutive duplicates collapsed, noise dropped: CCPLLTKR -> 'C P L T K R'."""
    out = []
    for ch in moves:
        if ch == "X":
            continue
        if not out or out[-1] != ch:
            out.append(ch)
    return " ".join(out)


# ---------------------------------------------------------------- wording
# Sentence-level forms per slot, scope sentences, practitioner evidence, the two-study shape and
# the verb of each contribution item. All regex on the cleaned text; categories are the
# assistant's, chosen after reading the 40 pivot / gap / findings / lead-in sentences once.

# Sentence breaks, shared by every *_stats.py. No break after "et al", a single capital or these
# abbreviations (before, "vs." "e.g." "Fig." and the rest split sentences). A period after a digit breaks only
# before whitespace and a capital ("at line 11. If"), never inside 3.5 or 4.3 (before, it never broke).
ABBREVIATIONS = ("vs", r"e\.g", r"i\.e", "cf", "Fig", "Figs", "Eq", "Eqs", "No", "approx", "resp",
                 "Sec", "Tab", "Tabs", "Alg", "Algo", "Def", r"w\.r\.t")
NO_BREAK = r"(?<!\bet al)(?<!\b[A-Z])" + "".join(rf"(?<!\b{a})" for a in ABBREVIATIONS)
AFTER_DIGIT = r"(?<=\d)\.(?=\s+[A-Z])"
SENT = re.compile(NO_BREAK + r"(?:(?<!\d)[.!?](?!\d)(?=\s|$)|" + AFTER_DIGIT + ")")
_SENT_SPLIT = re.compile(NO_BREAK + r"(?:(?<!\d)\.(?!\d)(?=\s|$)|" + AFTER_DIGIT + ")")


def _breaks(t, rx):
    """(start, end) of each break rx finds in t, except one after a numbered label or list number ("Rule 1.",
    "RQ1.1.", "Finding-3.", "1."): at most three words since the last break, ending in a digit."""
    start = 0
    for m in rx.finditer(t):
        if m.start() and t[m.start() - 1].isdigit() and len(WORD.findall(t[start:m.start()])) <= 3:
            continue
        yield m.start(), m.end()
        start = m.end()


def split_sentences(text):
    """Stripped non-empty sentences of text, the break character dropped."""
    out, pos = [], 0
    for s, e in _breaks(text, SENT):
        out.append(text[pos:s])
        pos = e
    out.append(text[pos:])
    return [x.strip() for x in out if x.strip()]


def first_sentence(text):
    t = re.sub(r"\s+", " ", _plain(text).replace("**", "")).strip()
    b = next(_breaks(t, _SENT_SPLIT), None)
    return t[:b[1]].strip() if b else t


PIVOT_FORMS = (
    ("in_this_paper", re.compile(r"^In this (?:paper|work|study|article)\b", re.I)),
    ("to_address_we", re.compile(r"^To \w+(?: \w+){0,12}?,\s*(?:we|this paper|in this paper)\b", re.I)),
    ("this_paper", re.compile(r"^This (?:paper|work|study|article)\b", re.I)),
)
GAP_FORMS = (
    ("however", re.compile(r"^(?:However|But|Yet|Unfortunately|Nevertheless|Nonetheless)\b", re.I)),
    ("despite", re.compile(r"^(?:Despite|Although|While|Even though)\b", re.I)),
    ("existing_prior", re.compile(r"^(?:The )?(?:existing|previous|prior|current|recent|most|several|some|limited|traditional)\b", re.I)),
)
FINDINGS_FORMS = (
    ("we_do", re.compile(r"^(?:We|(?:To|Using|Through|Based on|In order to) [^.]{0,80}?, we)\s+(?:first |then |further |thoroughly |empirically |comprehensively |also |have )?"
                         r"(?:evaluat|conduct|compar|perform|validat|instantiat|analy[sz]|construct|appl|test|assess|measur|examin|investigat|stud|replicat)", re.I)),
    ("results_show", re.compile(r"^(?:Our|The|Through|Based on|Unlike|In (?:sharp )?contrast|Overall|Surprisingly|Interestingly|We (?:only )?find|We observe|We show)\b[^.]*?"
                                r"\b(?:show|shows|reveal|reveals|find|finds|found|indicate|indicates|demonstrate|demonstrates|suggest|suggests|observe|make the following|summarize|highlight)", re.I)),
)
LEADIN_FORMULA = re.compile(r"(?:make|makes|made) (?:the following|(?:two|three|four|five) (?:main |primary |principal )?)?(?:\w+ )*contributions"
                            r"|contributions (?:of (?:this|our) (?:paper|work) )?(?:are|can be) (?:summari[sz]ed )?(?:as follows|below)"
                            r"|contributions (?:are )?as follows|following (?:\w+ )?contributions", re.I)
SCOPE = re.compile(r"\b(?:we (?:focus|limit|restrict|confine) |our (?:focus|scope)\b|out of (?:the )?scope|beyond the scope|in scope\b)", re.I)
GAP_TURN = re.compile(r"\b(?:however|but|yet|unfortunately|nevertheless|despite|although|while|limited|lack|lacks|lacking|fail|fails|overlook|overlooks|ignore|ignores|neglect|neglects|remain|remains|unclear|unexplored|little|few|none|not|no|cannot|without|gap)\b", re.I)
PRACTITIONER = re.compile(r"\b(?:surveys?|practitioners?|interviews?|questionnaires?)\b", re.I)
NOVELTY = re.compile(r"to the best of our knowledge|\bthe first\b|\bfirst (?:large-scale|systematic|empirical|in-depth|comprehensive)\b", re.I)

ITEM_CATS = (
    ("release", re.compile(r"\b(?:release|open[- ]sourc|publicly|make [^.]{0,40}available|available at|replication package|artifact)", re.I)),
    ("propose", re.compile(r"\b(?:propose|present|introduce|design|develop|build|implement|define|formulate|derive|extend|create|construct)\b", re.I)),
    ("study", re.compile(r"\b(?:conduct|study|investigate|evaluate|perform|analy[sz]e|compare|characteri[sz]e|explore|replicate|assess|examine|measure|benchmark)\b", re.I)),
    ("find", re.compile(r"\b(?:find|reveal|show|identify|observe|demonstrate|report|summari[sz]e|highlight|uncover|discuss|provide (?:insights|evidence|findings|implications|guidance|recommendations))\b", re.I)),
)


def _classify(sent, forms):
    for name, rx in forms:
        if rx.search(sent):
            return name
    return "other"


pivot_form = partial(_classify, forms=PIVOT_FORMS)
gap_form = partial(_classify, forms=GAP_FORMS)
findings_form = partial(_classify, forms=FINDINGS_FORMS)


def _item_text(line):
    t = _plain(line).replace("**", "").replace("*", "")
    t = re.sub(r"^\s*(?:[-•]\s?|\(\d+\)\s|\d+[.)]\s)", "", t)
    t = re.sub(r"^[A-Z][A-Za-z &\-]{2,45}[.:]\s+(?=[A-Z])", "", t)     # run-in title: 'Novelty: ' / 'Approach. '
    return t.strip()


def item_category(line):
    """First matching category in the first 20 words of a contribution item; release is checked
    first (an item that 'presents ... and releases ...' still counts as propose because the
    release phrase usually sits later than 20 words)."""
    head = " ".join(_item_text(line).split()[:20])
    return _classify(head, ITEM_CATS)


def contribution_items_text(k_paras):
    """Item texts of the contribution paragraphs: bullet lines, else inline (1) ... (2) ... splits."""
    lines = [l for p in k_paras for l in _items(p)]
    if lines:
        return lines
    for p in k_paras:
        parts = re.split(r"\(\d+\)\s", _plain(p))
        if len(parts) > 2:
            return ["- " + x.strip() for x in parts[1:]]
    return []


_BLOCK_RANK = {"O": 0, "L": 1, "T": 2, "F": 3, "K": 4}


def monotone_blocks(coarse):
    ranks = [_BLOCK_RANK[b] for b in coarse.split()]
    return all(a <= b for a, b in zip(ranks, ranks[1:]))


def wording(paras, moves):
    """Per-paper wording features from the hand-labelled moves."""
    t, l, f = (next((p for p, m in zip(paras, moves) if m == ch), None) for ch in "TLF")
    l_first = first_sentence(l) if l else ""
    k_paras = [p for p, m in zip(paras, moves) if m == "K"]
    lead = None
    if k_paras:
        head = k_paras[0].splitlines()[0]
        lead = head if not LIST_ITEM.match(head) else None
        if lead is None:
            i = moves.index("K")
            lead = paras[i - 1].splitlines()[-1] if i else ""
    items = contribution_items_text(k_paras)
    cats = [item_category(x) for x in items]
    cp = [p for p, m in zip(paras, moves) if m in "CP"]
    return dict(
        pivot_form=pivot_form(first_sentence(t)) if t else None,
        gap_form=gap_form(first_sentence(l)) if l else None,
        gap_turn_in_first_sentence=bool(GAP_TURN.search(l_first)) if l else None,
        gap_turn_later=bool(GAP_TURN.search(_plain(l))) and not GAP_TURN.search(l_first) if l else None,
        findings_form=findings_form(first_sentence(f)) if f else None,
        leadin_formula=bool(LEADIN_FORMULA.search(_plain(lead))) if lead else None,
        scope_sentences=sum(len(SCOPE.findall(_plain(p))) for p in paras),
        scope_moves="".join(sorted({m for p, m in zip(paras, moves) if SCOPE.search(_plain(p))})),
        practitioner_in_opening=any(PRACTITIONER.search(_plain(p)) for p in cp),
        t_runs=skeleton(moves).split().count("T"), tf_alternation=bool(re.search(r"T.*F.*T.*F", skeleton(moves))),
        monotone=monotone_blocks(coarse_skeleton(moves)),
        item_cats=" ".join(cats), item1_novelty=bool(NOVELTY.search(_item_text(items[0]))) if items else None,
    )


# ---------------------------------------------------------------- per paper

# Folder names of sample papers whose markdown the section scripts cannot cut (for example a
# different heading numbering); they are left out of every section measure.
SKIP = set()


def paper_paths():
    for name in sorted(os.listdir(need(VENUE, "VENUE") and MARKER_DIR)):
        d = os.path.join(MARKER_DIR, name)
        md = os.path.join(d, name + ".md")
        if os.path.isdir(d) and os.path.exists(md) and name not in SKIP:
            yield name, md


def features(name, md):
    with open(md, encoding="utf-8") as fh:
        text = fh.read()
    raw = extract_intro(text)
    paras = clean_paragraphs(raw)
    words = [word_count(p) for p in paras]
    total = sum(words)
    body = word_count(body_text(text))
    groups, refs = count_citations(raw)
    c = contribution_list(paras)
    piv = pivot_index(paras)
    n = len(paras)
    return dict(
        paper=name, year=name[3:7], paragraphs=n, words=total, body_words=body,
        intro_share=round(total / body, 3) if body else None,
        cite_groups=groups, cite_refs=refs, cites_per_100w=round(100 * groups / total, 1) if total else None,
        pivot_para=piv, pivot_pos=round(piv / n, 2) if piv else None,
        contrib_list=c["has"], contrib_items=c["items"], contrib_para=c["index"],
        contrib_pos=round(c["index"] / n, 2) if c["index"] else None, contrib_labelled=c["labelled"],
        rq_in_intro=rq_numbers(raw), figure=has_figure(raw), table=has_table(raw),
        runin_labels=runin_labels(paras),
        roadmap=has_roadmap("\n".join(paras)), artifact=has_artifact("\n".join(paras)),
        tail_numbers=tail_has_numbers(paras),
    ), paras, words


# ---------------------------------------------------------------- report

def summarize(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {"n": len(vals), "mean": round(statistics.mean(vals), 2),
            "median": float(statistics.median(vals)), "min": min(vals), "max": max(vals)}


def _md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _num_block(rows, key, label):
    return (label,) + tuple(summarize(r[key] for r in rows)[k] for k in ("n", "mean", "median", "min", "max"))


def _count(rows, key):
    return sum(1 for r in rows if r[key])


def move_stats(rows, moves_by_paper):
    """Per move: papers that have it, mean number of paragraphs, mean relative position."""
    stats = []
    for ch in MOVES:
        if ch == "X":
            continue
        have, paras, pos, words = 0, [], [], []
        for r in rows:
            seq = moves_by_paper[r["paper"]]
            idx = [i for i, m in enumerate(seq) if m == ch]
            if idx:
                have += 1
                paras.append(len(idx))
                live = [i for i, m in enumerate(seq) if m != "X"]
                pos.append(statistics.mean(live.index(i) / max(1, len(live) - 1) for i in idx))
                words.append(sum(r["_words"][i] for i in idx))
        stats.append((f"{ch} {MOVE_NAMES[ch]}", f"{have}/{len(rows)}",
                      round(statistics.mean(paras), 1) if paras else None,
                      round(statistics.mean(words)) if words else None,
                      round(statistics.mean(pos), 2) if pos else None))
    return stats


def item_position_table(rows):
    """Rows: item 1, item 2, item 3, last item; cells: papers whose item at that position falls in the category."""
    cats = [c for c, _ in ITEM_CATS] + ["other"]
    pos = (("item 1", 0), ("item 2", 1), ("item 3", 2), ("last item", -1))
    cnt = Counter((label, c[i]) for r in rows for c in [r["item_cats"].split()]
                  for label, i in pos if -len(c) <= i < len(c))
    return [(label,) + tuple(cnt[label, x] for x in cats) for label, _ in pos]


def report(rows, moves_by_paper):
    groups = {f"all {len(rows)}": rows}   # per-type numbers come from by_type.py
    out = [f"# Introductions of the {len(rows)} {VENUE} papers", "",
           "Generated by `scripts/intro_stats.py`; hand labels in its HAND table.", ""]
    for gname, g in groups.items():
        out += [f"## {gname} (n={len(g)})", "", "### Length and density", "",
                _md_table(("measure", "n", "mean", "median", "min", "max"), [
                    _num_block(g, "words", "words"),
                    _num_block(g, "paragraphs", "paragraphs (cleaned, noise excluded)"),
                    _num_block(g, "intro_share", "share of body words"),
                    _num_block(g, "cite_groups", "citation groups"),
                    _num_block(g, "cite_refs", "references cited"),
                    _num_block(g, "cites_per_100w", "citation groups per 100 words"),
                    _num_block(g, "pivot_pos", "pivot position (fraction of paragraphs)"),
                    _num_block([r for r in g if r["contrib_list"]], "contrib_items", "contribution items (papers with a list)"),
                    _num_block(g, "contrib_pos", "contribution list position"),
                ]), "", "### Presence", "",
                _md_table(("feature", "papers"), [
                    ("pivot sentence found", f"{_count(g, 'pivot_para')}/{len(g)}"),
                    ("contribution list", f"{_count(g, 'contrib_list')}/{len(g)}"),
                    ("contribution list with 'contribution' lead-in", f"{_count(g, 'contrib_labelled')}/{len(g)}"),
                    ("RQs numbered in the introduction", f"{_count(g, 'rq_in_intro')}/{len(g)}"),
                    ("figure in the introduction", f"{_count(g, 'figure')}/{len(g)}"),
                    ("table in the introduction", f"{_count(g, 'table')}/{len(g)}"),
                    ("roadmap paragraph", f"{_count(g, 'roadmap')}/{len(g)}"),
                    ("artifact or availability statement", f"{_count(g, 'artifact')}/{len(g)}"),
                    ("numbers in the closing third", f"{_count(g, 'tail_numbers')}/{len(g)}"),
                    ("two or more run-in labels (Our work. / Results.)", f"{sum(1 for r in g if r['runin_labels'] >= 2)}/{len(g)}"),
                    ("contribution items with a run-in title (Approach. / Evaluation.)", f"{_count(g, 'contrib_titled')}/{len(g)}"),
                    ("artifact statement in the last contribution item", f"{_count(g, 'artifact_in_last_item')}/{len(g)}"),
                ]), "", "### Hand labels", "",
                _md_table(("opener", "papers"), sorted(Counter(r["opener"] for r in g).items(), key=lambda x: -x[1])), "",
                _md_table(("first contribution verb", "papers"), sorted(Counter(r["contrib_first"] for r in g).items(), key=lambda x: -x[1])), "",
                "### Moves", "",
                _md_table(("move", "papers with it", "mean paragraphs", "mean words", "mean position 0..1"),
                          move_stats(g, moves_by_paper)), "",
                "### Order", "",
                _md_table(("first move", "papers"), sorted(Counter(skeleton(r["moves"])[0] for r in g).items(), key=lambda x: -x[1])), "",
                _md_table(("last move", "papers"), sorted(Counter(skeleton(r["moves"])[-1] for r in g).items(), key=lambda x: -x[1])), "",
                _md_table(("pair", "papers"), order_stats(g, moves_by_paper)), "",
                "### Wording (first sentence of the first paragraph of each slot; regex forms)", "",
                _md_table(("pivot sentence form", "papers"), sorted(Counter(r["pivot_form"] for r in g if r["pivot_form"]).items(), key=lambda x: -x[1])), "",
                _md_table(("gap paragraph opener", "papers"), sorted(Counter(r["gap_form"] for r in g if r["gap_form"]).items(), key=lambda x: -x[1])), "",
                _md_table(("findings paragraph opener", "papers"), sorted(Counter(r["findings_form"] for r in g if r["findings_form"]).items(), key=lambda x: -x[1])), "",
                _md_table(("feature", "papers"), [
                    ("contribution lead-in is the 'makes the following contributions' formula", f"{_count(g, 'leadin_formula')}/{sum(1 for r in g if r['leadin_formula'] is not None)} with a lead-in"),
                    ("gap paragraph: contrast or lack word in its first sentence", f"{_count(g, 'gap_turn_in_first_sentence')}/{sum(1 for r in g if r['gap_form'])} with a gap paragraph"),
                    ("gap paragraph: first sentence neutral, contrast or lack word later in the paragraph", f"{_count(g, 'gap_turn_later')}/{sum(1 for r in g if r['gap_form'])} with a gap paragraph"),
                    ("scope sentence (we focus on / out of scope) anywhere in the introduction", f"{_count(g, 'scope_sentences')}/{len(g)}"),
                    ("survey, practitioner, interview or questionnaire named in a context or problem paragraph", f"{_count(g, 'practitioner_in_opening')}/{len(g)}"),
                    ("two or more 'this paper' runs (two studies in one introduction)", f"{sum(1 for r in g if r['t_runs'] >= 2)}/{len(g)}"),
                    ("this paper -> findings -> this paper -> findings alternation", f"{_count(g, 'tf_alternation')}/{len(g)}"),
                    ("block order monotone (O L T F K never returns)", f"{_count(g, 'monotone')}/{len(g)}"),
                    ("first contribution item claims novelty (the first / to the best of our knowledge)", f"{_count(g, 'item1_novelty')}/{sum(1 for r in g if r['item1_novelty'] is not None)} with a list"),
                ]), "",
                _md_table(("scope sentence sits in slot", "papers"), sorted(Counter(r["scope_moves"] for r in g if r["scope_moves"]).items(), key=lambda x: -x[1])), "",
                "### Contribution items by position (category of the first verb in the first 20 words)", "",
                _md_table(("position",) + tuple(c for c, _ in ITEM_CATS) + ("other",), item_position_table(g)), "",
                _md_table(("papers with two or more 'this paper' runs", "skeleton"), [(r["paper"], r["skeleton"]) for r in g if r["t_runs"] >= 2]), "",
                _md_table(("block order returns", "coarse skeleton"), [(r["paper"], r["coarse"]) for r in g if not r["monotone"]]), "",
                "### Coarse skeletons (O opening, L limitation, T this paper, F findings, K closing)", "",
                _md_table(("coarse skeleton", "papers"), sorted(Counter(r["coarse"] for r in g).items(), key=lambda x: (-x[1], x[0]))), "",
                "### Skeletons (runs collapsed, noise dropped)", "",
                _md_table(("skeleton", "papers"), sorted(Counter(r["skeleton"] for r in g).items(), key=lambda x: (-x[1], x[0]))), ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", help="write cleaned, numbered paragraphs per paper to this directory and stop")
    args = ap.parse_args()

    rows, moves_by_paper, move_rows, unread = [], {}, [], []
    for name, md in paper_paths():
        try:
            f, paras, words = features(name, md)
        except ValueError as e:      # no heading the rules can read (e.g. unnumbered or Roman-numeral headings)
            unread.append(f"{name}: {e}")
            continue
        if args.dump:
            os.makedirs(args.dump, exist_ok=True)
            with open(os.path.join(args.dump, name + ".txt"), "w", encoding="utf-8") as fh:
                for i, (p, w) in enumerate(zip(paras, words), 1):
                    fh.write(f"[{i}] ({w} words)\n{p}\n\n")
            continue
        h = HAND.get(name)
        if h is None:
            raise SystemExit(f"no hand labels for {name}: run `python scripts/intro_stats.py --dump <dir>`, "
                             "label every paragraph of each paper with the letters in MOVES, and add the paper to HAND")
        if len(h["moves"]) != len(paras):
            raise SystemExit(f"{name}: moves has {len(h['moves'])} letters, cleaned text has {len(paras)} paragraphs")
        f.update(opener=h["opener"], contrib_first=h["contrib_first"],
                 moves=h["moves"], skeleton=skeleton(h["moves"]), coarse=coarse_skeleton(h["moves"]))
        # Item count over every paragraph hand-labelled K (a list split by a page break spans two
        # paragraphs); a HAND override wins when a bullet lost its marker in the conversion.
        k_paras = [p for p, m in zip(paras, h["moves"]) if m == "K"]
        k_items = sum(len(_items(p)) for p in k_paras) \
            or sum(len(re.findall(r"\(\d+\)", _plain(p))) for p in k_paras)      # inline (1) ... (2) ...
        if "contrib_items" in h:
            f["contrib_items"] = h["contrib_items"]
        elif k_items:
            f["contrib_items"] = k_items
        if k_paras:
            f["contrib_list"] = True
            f["contrib_para"] = 1 + h["moves"].index("K")
            f["contrib_pos"] = round(f["contrib_para"] / len(paras), 2)
        k_lines = [l for p in k_paras for l in p.splitlines() if LIST_ITEM.match(l)]
        f["contrib_titled"] = sum(1 for l in k_lines if TITLED_ITEM.match(l)) >= 2
        f["artifact_in_last_item"] = bool(k_lines) and bool(ARTIFACT.search(_plain(k_lines[-1])))
        live = [p for p, m in zip(paras, h["moves"]) if m != "X"]
        f["runin_labels"] = runin_labels(live)
        f.update(wording(paras, h["moves"]))
        f["_words"] = words
        rows.append(f)
        moves_by_paper[name] = h["moves"]
        for i, (m, w) in enumerate(zip(h["moves"], words), 1):
            move_rows.append(dict(paper=name, para=i, move=m, move_name=MOVE_NAMES[m], words=w))
    if unread:
        print(f"{len(unread)} paper(s) skipped, no introduction the rules can cut; add them to SKIP or extend "
              f"INTRO_HEAD:\n  " + "\n  ".join(unread), file=sys.stderr)
    if args.dump:
        print(f"dumped {sum(1 for _ in paper_paths()) - len(unread)} papers to {args.dump}")
        return
    if len(rows) != len(HAND):
        raise SystemExit(f"HAND has {len(HAND)} entries, {len(rows)} papers found")

    os.makedirs(OUT, exist_ok=True)
    cols = [k for k in rows[0] if not k.startswith("_")]
    with open(os.path.join(OUT, "intro_features.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in cols})
    with open(os.path.join(OUT, "intro_moves.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(move_rows[0]))
        w.writeheader()
        w.writerows(move_rows)
    with open(os.path.join(OUT, "intro_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(rows, moves_by_paper))
    print(f"{len(rows)} papers -> {OUT}/intro_features.csv, intro_moves.csv, intro_report.md")


if __name__ == "__main__":
    main()
