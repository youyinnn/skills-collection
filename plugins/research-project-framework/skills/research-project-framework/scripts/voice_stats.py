#!/usr/bin/env python3
"""Ten voice features of one draft section against the same section of the venue sample.

First person, negation words, 'same', connectives and hedges per 100 words; the share of sentences
opening with 'The', of colon and semicolon sentences; the spread of sentence length; the share of
short sentences. The draft's value is printed next to the sample's median and quartiles, so the
draft can be rewritten where it falls outside. The sample side reuses the extraction of the
*_stats.py scripts; the draft side reuses measure_tex_section.py.

  python scripts/voice_stats.py --section intro path/to/section/introduction.tex
  (--section takes the section names listed in MIN_SENTS)
"""
import argparse
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intro_stats as F  # noqa: E402
import relwork_stats as R  # noqa: E402
import background_stats as B  # noqa: E402
import methodology_stats as D  # noqa: E402
import results_stats as RS  # noqa: E402
import measure_tex_section as M  # noqa: E402

WE = re.compile(r"\b(we|our|ours|us)\b", re.I)
NEG = re.compile(r"\b(no|none|nothing|never|neither|nor|not)\b", re.I)
SAME = re.compile(r"\bsame\b", re.I)
DISC = re.compile(r"\b(however|for example|for instance|e\.g\.|i\.e\.|in particular|in contrast|note that"
                  r"|that is|moreover|furthermore|thus|hence|therefore|indeed|also|first|second|third|finally"
                  r"|specifically|unfortunately|importantly|in addition|in practice|in this paper|in this work"
                  r"|in summary)\b", re.I)
HEDGE = re.compile(r"\b(may|might|can|could|would|should|likely|possibly|often|typically|generally|usually"
                   r"|tend|tends|suggest|suggests)\b", re.I)
OPENER = re.compile(r"^(The|This|These|Its|Each|Every)\b")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"(])")
RUNIN = re.compile(r"^\s*\\(?:textbf|subhead)\{[^}]*\}\s*$", re.M)   # a line that is only a run-in label (\subhead is a run-in macro some papers define)
KEYS = ["we100", "neg100", "same100", "disc100", "hedge100", "start_the", "colon", "semi", "cv", "short"]
MIN_SENTS = {"intro": 10, "relwork": 8, "background": 8, "methodology": 8, "results": 8, "abstract": 5, "discussion": 8, "conclusion": 4}


def sentences_from_prose(text):
    out = []
    for p in text.split("\n"):
        p = p.strip()
        if not p:
            continue
        out.extend(s for s in SENT_SPLIT.split(p) if F.word_count(s) >= 3)
    return out


def feats(sents):
    text = " ".join(sents)
    w = F.word_count(text)
    lens = [F.word_count(s) for s in sents]
    n = len(sents)
    per100 = lambda rx: round(100 * len(rx.findall(text)) / w, 2)  # noqa: E731
    return dict(
        words=w, sents=n,
        we100=per100(WE), neg100=per100(NEG), same100=per100(SAME), disc100=per100(DISC), hedge100=per100(HEDGE),
        start_the=round(100 * sum(1 for s in sents if OPENER.match(s.strip())) / n, 1),
        colon=round(100 * sum(1 for s in sents if ":" in s) / n, 1),
        semi=round(100 * sum(1 for s in sents if ";" in s) / n, 1),
        cv=round(statistics.pstdev(lens) / statistics.mean(lens), 2),
        short=round(100 * sum(1 for x in lens if x <= 12) / n, 1),
    )


def _extract(section, md, name):
    if section == "abstract":
        from abstract_stats import cut_abstract
        return "\n\n".join(cut_abstract(md)[1])
    if section == "conclusion":
        from conclusion_stats import conclusion_text   # the last top-level Conclusion-like section
        return conclusion_text(md, name)
    if section == "discussion":
        from discussion_stats import discussion_text   # standalone sections and subsections, not the merged layout
        return discussion_text(md, name)
    if section == "intro":
        return F.extract_intro(md)
    if section == "relwork":
        return R.extract_relwork(md)[2]
    if section == "methodology":
        ptype = D.HAND.get(name, {"type": "unlabelled"})["type"]
        taken, _top, extra, _per_rq = D.design_sections(md, ptype, name)
        parts = []
        for num, title, raw, subs in taken:
            units, _cut = D.units_of(num, title, raw, subs, force_cut=num in D._hand(name).get("cut", ()))
            parts.extend(text for _label, text in units)
        parts.extend(text for _num, _label, text in extra)
        return "\n\n".join(parts) if parts else None
    if section == "results":
        ptype = D.HAND.get(name, {"type": "unlabelled"})["type"]
        run, _top, _found, _cut = RS.results_sections(RS.XREF.sub(r"\1", md), ptype, name)
        parts = [text for _num, title, raw, subs, mode in run for _label, text in RS.results_units_of(title, raw, subs, mode)]
        return "\n\n".join(parts) if parts else None
    hit = B.background_section(md)
    return hit[2] if hit else None


def sample_rows(section):
    rows = []
    for name, path in F.paper_paths():
        with open(path, encoding="utf-8") as fh:
            md = fh.read()
        try:
            raw = _extract(section, md, name)
        except ValueError:
            continue
        if raw is None:
            continue
        raw = re.sub(r"^#+ .*$", "", raw, flags=re.M)
        paras = F.clean_paragraphs(raw)
        prose = "\n".join(F._plain(p) for p in paras if not F.LIST_ITEM.match(p.splitlines()[0]))
        sents = sentences_from_prose(re.sub(r"[*_`#>]", "", prose))
        if len(sents) >= MIN_SENTS[section]:
            rows.append(feats(sents))
    return rows


def draft_sentences(tex):
    lines, _f, _fl, _k = M.normalize(RUNIN.sub("", tex))
    return [l for l in lines if l and l != M.FORMULA_LINE and F.word_count(l) >= 3]


def quartiles(values):
    v = sorted(values)
    return statistics.median(v), v[len(v) // 4], v[3 * len(v) // 4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=sorted(MIN_SENTS), required=True)
    ap.add_argument("tex", nargs="+")
    a = ap.parse_args()
    rows = sample_rows(a.section)
    drafts = {}
    for p in a.tex:
        with open(p, encoding="utf-8") as fh:
            drafts[os.path.basename(p)] = feats(draft_sentences(fh.read()))
    names = list(drafts)
    print(f"sample: {a.section}, n = {len(rows)}")
    print("feature     " + "".join(f"{n[:14]:>15}" for n in names) + " | sample median (q1 to q3)")
    for k in KEYS:
        med, q1, q3 = quartiles([r[k] for r in rows])
        print(f"{k:12}" + "".join(f"{drafts[n][k]:>15}" for n in names) + f" | {med:>7} ({q1} to {q3})")
    for n in names:
        print(f"{n}: {drafts[n]['words']} words, {drafts[n]['sents']} sentences")


if __name__ == "__main__":
    main()
