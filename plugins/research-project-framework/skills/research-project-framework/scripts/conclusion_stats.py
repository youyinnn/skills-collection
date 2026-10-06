#!/usr/bin/env python3
"""Conclusion statistics over a venue sample: heading, position and neighbours, length, paragraphs,
sentence length, citations, formulas, run-in labels, ten marker sentences (what was done, first
claim, findings, implications, future work, artifact, limitation, numbers, RQ numbers, pointers to
figures and tables), and whether the last sentence is future work. Per-group numbers use the label
file in config.py.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/conclusion_stats.py   # conclusion_features.csv, conclusion_report.md
"""
import csv
import os
import re
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from background_stats import FORMULA  # noqa: E402
from by_type import LABELS, group_of, match  # noqa: E402
from config import VENUE  # noqa: E402
from intro_stats import OUT, _plain, body_text, clean_paragraphs, count_citations, paper_paths, word_count  # noqa: E402
from methodology_stats import first_sentence, sentences  # noqa: E402
from relwork_stats import REFS, q, table  # noqa: E402
from results_stats import XREF, headings  # noqa: E402
from threats_stats import kind_of, label_of  # noqa: E402

# Assistant-set rules; tune them for a new venue.
TITLE = re.compile(r"conclu|final remarks|closing remarks|summary", re.I)
END = re.compile(r"^\s*(?:[-*]\s*)?\[1\]\s|^\s*#*\s*\**\s*(?:REFERENCES|References|ACKNOWLEDG|Acknowledg)|\b\d+\s+DATA AVAILABILITY\b|REFERENCES\s*\[1\]", re.M)
MARK = {   # sentence markers; a sentence can carry several
    "open_summary": re.compile(r"^(?:In this (?:paper|work|study|article)|This (?:paper|work|study|article)|We |Our |To (?:address|bridge|fill|answer))", re.I),
    "first_claim": re.compile(r"\b(?:the )?first\b(?! few)", re.I),
    "finding": re.compile(r"\bwe (?:find|found|show|showed|observe|observed|reveal|revealed|demonstrate|demonstrated|discover|discovered)\b|results? (?:show|indicate|reveal|demonstrate|confirm|suggest)|findings (?:show|indicate|reveal|suggest)", re.I),
    "implication": re.compile(r"implication|recommend|\bshould\b|practitioners|guideline|insights? for", re.I),
    "future": re.compile(r"future work|in the future|we plan|we (?:will|intend|aim to|hope to)\b|future (?:research|studies|directions?)", re.I),
    "artifact": re.compile(r"replication package|publicly (?:release|available)|available at|github\.com|zenodo|we (?:release|make) (?:all|our|the)", re.I),
    "limitation": re.compile(r"limitation|non-?significant|threat|caveat|although our", re.I),
    "number": re.compile(r"(?<![A-Za-z\[])\d+(?:[.,]\d+)*%?(?![\]\w])"),
    "rq": re.compile(r"\bRQ\s*-?\s*\d"),
    "figtab": re.compile(r"\bTab(?:le|\.)s?\s*\[?\d|\bFig(?:ure|s|\.)?\s*\[?\d", re.I),
}


def _clean_title(t):
    return re.sub(r"^\d+(?:\.\d+)*\s+", "", t.strip("* ")).strip()


def conclusion_cut(md):
    """(title, prev title, next title, raw text) of the conclusion, or None."""
    refs = REFS.search(md)
    limit = refs.start() if refs else len(md)
    top = [h for h in headings(md) if h[0] < limit and len(h[2]) == 1]
    cands = [h for h in top if TITLE.search(_clean_title(h[3]))]
    if not cands:
        return None
    pick = cands[-1]
    i = top.index(pick)
    end = top[i + 1][0] if i + 1 < len(top) else limit
    raw = md[pick[1]:end]
    m = END.search(raw)
    if m:
        raw = raw[:m.start()]
    prev = _clean_title(top[i - 1][3]) if i else ""
    nxt = _clean_title(top[i + 1][3]) if i + 1 < len(top) else ""
    return _clean_title(pick[3]), prev, nxt, raw


def conclusion_text(md, name=None):
    """The cut text, for voice_stats; None when there is no conclusion."""
    cut = conclusion_cut(XREF.sub(r"\1", md))
    return cut[3] if cut else None


def features(name, md_path):
    with open(md_path, encoding="utf-8") as fh:
        md = XREF.sub(r"\1", fh.read())
    row = dict(paper=name, year=name[3:7], title="", prev="", prev_kind="", next="", words=0)
    cut = conclusion_cut(md)
    if not cut:
        return row
    title, prev, nxt, raw = cut
    paras = clean_paragraphs(raw)
    text = "\n\n".join(paras)
    sents = [_plain(s).strip() for s in sentences(text) if word_count(s) >= 3]
    lens = [word_count(s) for s in sents]
    words = sum(word_count(p) for p in paras)
    body = word_count(body_text(md))
    row.update(title=title, prev=prev, prev_kind=kind_of(prev) if prev else "", next=nxt, words=words,
               share=round(words / body, 3) if body else None, paragraphs=len(paras), sentences=len(sents),
               sent_median=statistics.median(lens) if lens else None, sent_max=max(lens) if lens else 0,
               long40=sum(1 for n in lens if n >= 40), cite_groups=count_citations(text)[0],
               formulas=len(FORMULA.findall(raw)), runin_paras=sum(1 for p in paras if label_of(p)[0]),
               title_future=bool(re.search(r"future", title, re.I)),
               first_sentence=first_sentence(text)[:240], last_sentence=sents[-1][:240] if sents else "")
    row["cites_per_100w"] = round(100 * row["cite_groups"] / words, 2) if words else None
    for k, rx in MARK.items():
        if k == "open_summary":
            row["m_" + k] = int(bool(sents and rx.match(sents[0])))
        else:
            row["m_" + k] = sum(1 for s in sents if rx.search(s))
    row["last_future"] = int(bool(sents and MARK["future"].search(sents[-1])))
    return row


def types(rows):
    with open(LABELS, encoding="utf-8") as fh:
        labels = list(csv.DictReader(fh))
    longs = [r["paper"] for r in rows]
    out = {}
    for lab in labels:
        try:
            out[match(lab["paper"], longs)] = group_of(lab)
        except KeyError:
            pass
    return out


def block(rs, tag):
    have = [r for r in rs if r["words"]]
    n = len(have)
    L = [f"## {tag} ({n} / {len(rs)} with a conclusion)", "",
         "- Titles: " + ", ".join(f"{k} {v}" for k, v in Counter(r["title"].title() for r in have).most_common()) + ".",
         f"- Last top-level section of the body: {sum(1 for r in have if not r['next'] or re.search(r'data|availab|declar|acknowl', r['next'], re.I))} / {n}; "
         "what follows: " + ", ".join(f"{k} {v}" for k, v in Counter((r['next'] or '(nothing)').title()[:30] for r in have).most_common()) + ".",
         "- What precedes: " + ", ".join(f"{k} {v}" for k, v in Counter(r["prev"].title()[:30] for r in have).most_common()) + ".",
         f"- Words: {q([r['words'] for r in have])}",
         f"- Share of the body: {q([r['share'] for r in have])}",
         f"- Paragraphs: {q([r['paragraphs'] for r in have])}; sentences: {q([r['sentences'] for r in have])}",
         f"- Median sentence length: {q([r['sent_median'] for r in have])}; longest: {q([r['sent_max'] for r in have])}; 40 words or more: {q([r['long40'] for r in have])}",
         f"- Citation groups per 100 words: {q([r['cites_per_100w'] for r in have])}; papers with a citation: {sum(1 for r in have if r['cite_groups'])} / {n}",
         f"- Papers with a formula {sum(1 for r in have if r['formulas'])}, a run-in label {sum(1 for r in have if r['runin_paras'])}, "
         f"Future in the title {sum(1 for r in have if r['title_future'])} (of {n}).", "",
         table(["marker", "papers", "sentences per paper (papers with it)"],
               [[k, sum(1 for r in have if r['m_' + k]), q([r['m_' + k] for r in have if r['m_' + k]])] for k in MARK]
               + [["last sentence is future work", sum(r["last_future"] for r in have), ""]]), ""]
    return L


def report(rows):
    L = [f"# Conclusion sections of {VENUE} papers", "",
         "Generated by `scripts/conclusion_stats.py`; do not edit. The title rule, the cut and the sentence markers are "
         "assistant-set and printed at the top of the script. open_summary is the first sentence only; "
         "the other markers count sentences.", ""]
    L += block(rows, "All papers")
    for g in sorted({r["type"] for r in rows}):
        L += block([r for r in rows if r["type"] == g], g)
    L += ["## Every paper", "",
          table(["paper", "type", "title", "prev", "words", "sents", "cites", "summary", "finding", "impl", "future", "artifact", "first"],
                [[r["paper"][8:50], r["type"], r["title"][:28], r["prev"][:22], r["words"], r.get("sentences", ""), r.get("cite_groups", ""),
                  r.get("m_open_summary", ""), r.get("m_finding", ""), r.get("m_implication", ""), r.get("m_future", ""),
                  r.get("m_artifact", ""), r.get("m_first_claim", "")] for r in rows]), ""]
    return "\n".join(L) + "\n"


def main():
    rows = [features(name, md) for name, md in paper_paths()]
    ty = types(rows)
    for r in rows:
        r["type"] = ty.get(r["paper"], "?")
    os.makedirs(OUT, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(OUT, "conclusion_features.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(OUT, "conclusion_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(rows))
    print(f"{len(rows)} papers, {sum(1 for r in rows if r['words'])} with a conclusion -> {OUT}/conclusion_features.csv, conclusion_report.md")


if __name__ == "__main__":
    main()
