#!/usr/bin/env python3
"""Abstract statistics over a venue sample: layout, length, paragraphs, sentence length, citations,
numbers (and numbers inside finding sentences), first person, first-of-its-kind claims, and the
function of every sentence (background, gap, this paper, approach, evaluation setup, finding,
implication, artifact) with the order in which each first appears. Numbers are also reported per
paper-type group read from the label file in config.py.

The cutting and cleaning rules were tuned on FSE 2023-2026 papers in ACM format
(Marker markdown). Check a few papers of a new venue with --dump before trusting the numbers.

  python scripts/abstract_stats.py          # abstract_features.csv, abstract_sentences.csv, abstract_report.md
  python scripts/abstract_stats.py --dump   # prints every sentence with its label for checking
"""
import argparse
import csv
import os
import re
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import VENUE  # noqa: E402
from intro_stats import OUT, _plain, clean_paragraphs, count_citations, paper_paths, split_sentences, word_count  # noqa: E402
from results_stats import NUMBER  # noqa: E402
from relwork_stats import q  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from config import GROUP_ORDER, LABELS  # noqa: E402

# Assistant-set rules; tune them for a new venue.
INTRO = re.compile(r"^#+\s*(?:\*\*)?\s*(?:<span[^>]*></span>\s*)*(?:1|I)\.?\s+Introduction", re.M | re.I)
ABS_HEAD = re.compile(r"^#+\s*\**ABSTRACT\**\s*$", re.M | re.I)
ABS_INLINE = re.compile(r"^(?:\*Abstract\*\s*[—–-]+|Abstract\.)\s*", re.M)
STOP = re.compile(r"^(?:<span[^>]*></span>\s*)*(?:#+\s*)?(?:\*\*)?(?:CCS Concepts|CCS CONCEPTS|Additional Key Words|KEYWORDS|Keywords"
                  r"|\*Index Terms\*|Index Terms|ACM Reference Format|Authors?['’]? (?:Contact|address)|Permission to make|\[?<?https?://doi)", re.I)
NOT_PROSE = re.compile(r"orcid\.org|@[a-z0-9-]+\.[a-z]|^\s*#|^\s*\[?This work is licensed|^\s*(?:©|Copyright)|^\s*!\[|^\s*<sup>|^\s*(?:[∗†‡§]|\*(?!\*))|corresponding author", re.I)

MOVES = "CGTDVFIR"
MOVE_NAMES = {"C": "context", "G": "gap (problem or limitation of prior work)", "T": "this paper (pivot)",
              "D": "design or approach", "V": "evaluation setup or scale", "F": "findings or results",
              "I": "implications", "R": "artifact"}
RX = {
    "R": re.compile(r"replication package|github\.com|zenodo|figshare|https?://|data and materials"
                    r"|\b(?:artifacts?|code|data|datasets?|tools?|benchmarks?|implementations?|materials)\b(?: \w+){0,3} (?:is|are) (?:\w+ )?(?:publicly )?(?:available|released)"
                    r"|we (?:release|open-source|make [^.]{0,60}available)|\bopen-sourced\b", re.I),
    "T": re.compile(r"\bIn this (?:paper|work|study|article)\b|^This (?:paper|work|study|article)\b|the (?:goal|aim|purpose) of this (?:paper|work|study)|^To (?:address|bridge|fill|tackle|overcome|mitigate|solve|this end|answer|close)"
                    r"|\bwe (?:propose|present|introduce|take the first|aim to|seek to|set out|conduct the first|perform the first)\b"
                    r"|\bwe (?:conduct|perform|carry out|present) (?:a|an|the first)\b[^.]{0,80}(?:study|analysis|investigation|evaluation|examination)", re.I),
    "I": re.compile(r"implications?\b|shed(?:s)? (?:new )?light|pave(?:s)? the way|we (?:hope|call|advocate|recommend|discuss|outline)|call for|guidance|lessons|underscore|insights? (?:into|for|on)"
                    r"|recommendations?|practitioners?|future (?:research|work|studies|directions)|highlight(?:s)? the (?:need|importance)|should (?:be|consider)", re.I),
    "F": re.compile(r"\bresults? (?:show|demonstrate|indicate|reveal|suggest|confirm)|\bwe (?:find|found|observe|show|reveal|demonstrate|identify|uncover|discover|note)\b"
                    r"|\bfindings?\b|outperform|\bachiev|surpass|improv(?:e|es|ed|ement|ing)s?\b[^.]*\d|\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)?\s?[x×]\b"
                    r"|reduc(?:e|es|ed|tion|ing)\b[^.]*\d|significant(?:ly)?|\b(?:show|shows|showed|reveal|reveals|indicate|indicates|demonstrate|demonstrates) that\b|\b(?:revealed|showed|found|demonstrated|indicated|uncovered)\b", re.I),
    "V": re.compile(r"\bwe (?:evaluate|conduct|perform|carry out|run|apply|compare|assess|test|collect|construct|build|curate|gather|manually)\b"
                    r"|\bexperiments?\b|\bevaluat|\bbenchmarks?\b|\b\d[\d,]*\s+(?:\w+[- ]){0,3}(?:projects|datasets|models|apps|applications|programs|repositories|bugs|subjects"
                    r"|systems|LLMs|tasks|developers|participants|papers|samples|commits|files|functions|images|instances|configurations|issues|posts|questions)\b", re.I),
    "G": re.compile(r"^(?:However|But|Yet|Unfortunately|Nevertheless|Nonetheless|Despite|Although|While)\b|remains? (?:unclear|unknown|underexplored|unexplored|open|challenging|limited|a challenge)"
                    r"|little (?:is known|attention|research|work)|\black|\blimited\b|\bfail|challeng|overlook|neglect|unexplored|under-?explored|few (?:studies|works|approaches)"
                    r"|no (?:existing|prior|systematic)|not (?:been|yet|well|fully)|suffer|difficult|hard to|struggle|costly|insufficient|inadequate|unknown"
                    r"|^(?:What|How|Which|Why|Whether|Is|Are|Can|Do|Does)\b", re.I),
}
F_LEAD = re.compile(r"^(?:We (?:find|found|observe|observed|show|reveal|discover|uncover|identify)\b"
                    r"|(?:Our|The|Experimental|Evaluation|Empirical)?\s*(?:\w+ ){0,2}(?:results|findings|evaluation|experiments|analysis|study|studies)\b[^.]{0,40}?"
                    r"\b(?:show|shows|showed|reveal|reveals|revealed|demonstrate|demonstrates|indicate|indicates|suggest|suggests|confirm|confirms)\b)", re.I)
T_SUBJECT = re.compile(r"\b(?:we|our|us)\b|\bthis (?:paper|work|study|article)\b", re.I)   # a pivot names the paper or its authors
NOVELTY = re.compile(r"to the best of our knowledge|\bthe first\b", re.I)
RQ = re.compile(r"\bRQ\s*\d|research questions?", re.I)
FIRST_PERSON = re.compile(r"\b(?:we|our|us)\b", re.I)


def front_matter(md):
    m = INTRO.search(md)
    if not m:
        raise ValueError("no Introduction heading")
    return md[:m.start()]


def cut_abstract(md):
    """(layout, [paragraphs])."""
    fm = front_matter(md)
    h = ABS_HEAD.search(fm)
    if h:
        layout, rest = "heading", fm[h.end():]
    else:
        i = ABS_INLINE.search(fm)
        if i:
            layout, rest = "inline", fm[i.end():]
        else:
            t = re.search(r"^# .*$", fm, re.M)       # skip the title line
            layout, rest = "pacmse", fm[t.end():] if t else fm
    paras, started = [], False
    for p in (x.strip() for x in re.split(r"\n\s*\n", rest)):
        if not p:
            continue
        if STOP.match(p) or (layout == "heading" and p.startswith("#")):
            break
        prose = word_count(_plain(p)) >= 30 and not NOT_PROSE.search(p)
        if started and RX["R"].search(p) and word_count(_plain(p)) < 30:   # "Replication Package: <url>" line under the abstract
            paras.append(p)
            continue
        if layout == "pacmse" and not prose:
            if started:
                break
            continue
        if layout != "pacmse" and NOT_PROSE.search(p):
            continue
        paras.append(p)
        started = True
    return layout, clean_paragraphs("\n\n".join(paras))


def sentences_of(paras):
    return [s for p in paras for s in split_sentences(_plain(p)) if word_count(s) >= 3]


LIGATURES = ("ffi", "ffl", "ff", "fi", "fl")
_VOCAB = None


def vocab():
    """Word frequencies over the whole sample, for repairing dropped ligatures."""
    global _VOCAB
    if _VOCAB is None:
        _VOCAB = Counter()
        for _, md in paper_paths():
            _VOCAB.update(w.lower() for w in re.findall(r"[A-Za-z]+", open(md, encoding="utf-8").read()))
    return _VOCAB


def repair_ligatures(text):
    """The 2023 ACM PDFs lose fi, fl and ff ligatures in Marker ("rst" for first, "ll" for fill).
    A word is repaired when exactly one ligature insertion turns it into a word seen at least 20 times
    in the sample and at least five times as often as the word itself ("dierent" 153, "different" 1429). Applied only to papers where "rst" or "dierent" occurs, so that clean text is untouched."""
    if not re.search(r"\b(?:rst|dierent|ndings)\b", text):
        return text
    v = vocab()

    def fix(m):
        w = m.group(0)
        lw = w.lower()
        cands = {lw[:i] + lig + lw[i:] for i in range(len(lw) + 1) for lig in LIGATURES}
        cands = [c for c in cands if v[c] >= 20 and v[c] >= 5 * v[lw]]
        if len(cands) != 1:
            return w
        c = cands[0]
        return c.capitalize() if w[0].isupper() else c
    return re.sub(r"[A-Za-z]+", fix, text)


def label(sents, force_t=None):
    """force_t: index of the sentence to take as the pivot when no sentence matches T (the abstract
    has no "In this paper" or "we propose"); it is the first sentence with we, our or us."""
    out, seen_t, seen_f, seen_v = [], False, False, False
    for i, s in enumerate(sents):
        m = None
        if i == force_t:
            m = "T"
        elif RX["R"].search(s):
            m = "R"
        elif RX["T"].search(s) and T_SUBJECT.search(s) and not F_LEAD.search(s):
            m = "T"
        elif seen_t and F_LEAD.search(s):
            m = "F"
        elif seen_t:
            for k in "IFV":
                if RX[k].search(s):
                    m = k
                    break
        elif RX["G"].search(s):
            m = "G"
        if m is None:
            m = "F" if (seen_f or seen_v) else "D" if seen_t else "C"
        seen_t |= m == "T"
        seen_f |= m == "F"
        seen_v |= m == "V"
        out.append(m)
    return out


def features(name, md):
    with open(md, encoding="utf-8") as fh:
        text = fh.read()
    layout, paras = cut_abstract(text)
    paras = [repair_ligatures(p) for p in paras]
    sents = sentences_of(paras)
    moves = label(sents)
    forced = "T" not in moves
    if forced:
        moves = label(sents, force_t=next((i for i, x in enumerate(sents) if FIRST_PERSON.search(x)), None))
    lens = [word_count(s) for s in sents]
    words = sum(word_count(_plain(p)) for p in paras)
    joined = " ".join(sents)
    groups, _ = count_citations("\n\n".join(paras))
    num_sents = sum(bool(NUMBER.search(s)) for s in sents)
    f_num = sum(bool(NUMBER.search(s)) for s, m in zip(sents, moves) if m == "F")   # a quantitative result, not a scale
    piv = moves.index("T") + 1 if "T" in moves else None
    fwords = sum(n for n, m in zip(lens, moves) if m == "F")
    row = dict(
        paper=name, year=name[3:7], layout=layout, words=words, paragraphs=len(paras), sentences=len(sents),
        sent_median=statistics.median(lens) if lens else None, sent_max=max(lens) if lens else None,
        cite_groups=groups, numbers=len(NUMBER.findall(joined)), num_sentences=num_sents, f_num_sentences=f_num,
        first_person_per_100w=round(100 * len(FIRST_PERSON.findall(joined)) / words, 1) if words else None,
        pivot_sent=piv, pivot_pos=round(piv / len(sents), 2) if piv else None,
        findings_share=round(fwords / sum(lens), 2) if lens else None,
        novelty=bool(NOVELTY.search(joined)), rq=bool(RQ.search(joined)), pivot_forced=forced, moves="".join(moves),
    )
    for k in MOVES:
        row["n_" + k] = moves.count(k)
    return row, list(zip(sents, moves, lens))


def groups_of(names):
    """paper folder name -> codebook group, by the matching rule of by_type.py."""
    from by_type import group_of, match
    out = {}
    for r in csv.DictReader(open(LABELS, encoding="utf-8")):
        try:
            out[match(r["paper"], names)] = group_of(r)
        except KeyError:
            pass
    return out


def first_order(moves):
    seen = []
    for m in moves:
        if m not in seen:
            seen.append(m)
    return " ".join(seen)


def section(rows, sents_by, title):
    n = len(rows)
    out = [f"## {title}({n})", ""]
    if n < 5:
        return out + ["篇数不足 5,只列篇目:" + ",".join(r["paper"] for r in rows), ""]
    num = lambda c: q([r[c] for r in rows if r[c] is not None])
    frac = lambda c: f"{sum(bool(r[c]) for r in rows)} / {n}"
    out += ["| 特征 | 中位 (四分位) 或篇数 |", "|---|---|",
            f"| 词数 | {num('words')} |", f"| 段数 | {num('paragraphs')} |", f"| 句数 | {num('sentences')} |",
            f"| 句长中位 | {num('sent_median')} |", f"| 最长句 | {num('sent_max')} |",
            f"| 引用组 | 有引用的 {sum(r['cite_groups'] > 0 for r in rows)} / {n} |",
            f"| 数字个数 | {num('numbers')} |", f"| 带数字的句子数 | {num('num_sentences')} |",
            f"| 有数字的篇 | {sum(r['numbers'] > 0 for r in rows)} / {n} |",
            f"| 有带数字的发现句的篇 | {sum(r['f_num_sentences'] > 0 for r in rows)} / {n} |",
            f"| 第一人称 / 百词 | {num('first_person_per_100w')} |",
            f"| 转折到本文(T)在第几句 | {num('pivot_sent')} |", f"| T 的相对位置 | {num('pivot_pos')} |",
            f"| 发现句(F)占词数 | {num('findings_share')} |",
            f"| 写 the first 或 to the best of our knowledge | {frac('novelty')} |", f"| 提 RQ 或 research question | {frac('rq')} |", "",
            "| 功能 | 有的篇数 | 句数(有的篇,中位与四分位) | 首次出现在第几句 |", "|---|---|---|---|"]
    for k in MOVES:
        have = [r for r in rows if r["n_" + k]]
        pos = [r["moves"].index(k) + 1 for r in have]
        out.append(f"| {k} {MOVE_NAMES[k]} | {len(have)} / {n} | {q([r['n_' + k] for r in have])} | {q(pos)} |")
    seqs = Counter(first_order(r["moves"]) for r in rows)
    out += ["", "首次出现顺序(最常见的几种):" + ";".join(f"{k} {v}" for k, v in seqs.most_common(5)),
            "", "逐篇句序(每个字母一句):", ""]
    out += [f"- {r['moves']}  {r['paper'][:60]}" for r in rows]
    return out + [""]


def _check():
    """Sentences taken from the sample; fails when a rule edit breaks a case already settled."""
    got = label(["Large language models are widely used for code generation.",
                 "However, it remains unclear whether this effect applies to tabular data.",
                 "To this end, researchers have proposed a wide range of test selection metrics.",
                 "In this paper, we empirically analyze the differences in coding style.",
                 "Specifically, we first summarize the types of coding style inconsistencies.",
                 "Our experiments involved three LLMs and 88 open-source software projects.",
                 "The results reveal that LLMs and developers exhibit differences in coding style.",
                 "These findings underscore the need for improved robustness."])
    assert "".join(got) == "CGCTDVFI", got
    assert label(["What are the root causes of such issues?"])[0] == "G"
    v = vocab()
    if v["first"] >= 20 and v["different"] >= 20:   # the repair needs a sample large enough to know these words
        assert repair_ligatures("we conduct the rst study on dierent data") == "we conduct the first study on different data"
    assert len(sentences_of(["It gains 3.7% (vs. EffiCoder), e.g. on Fig. 2, i.e. overall. Smith et al. agree.",
                             "It stops at line 11. Rule 1. It reads 4.3 then stops."])) == 4


def main():
    _check()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump")
    a = ap.parse_args()
    rows, sents_by, unread = [], {}, []
    for name, md in paper_paths():
        try:
            row, s = features(name, md)
        except ValueError as e:      # no heading the rules can read
            unread.append(f"{name}: {e}")
            continue
        rows.append(row)
        sents_by[name] = s
    if unread:
        print(f"{len(unread)} paper(s) skipped, no abstract the rules can cut:\n  " + "\n  ".join(unread), file=sys.stderr)
    if a.dump:
        os.makedirs(a.dump, exist_ok=True)
        for name, s in sents_by.items():
            with open(os.path.join(a.dump, name + ".txt"), "w", encoding="utf-8") as fh:
                fh.writelines(f"{i:2d} {m} ({n}w) {t}\n" for i, (t, m, n) in enumerate(s, 1))
        return
    bad = [r["paper"] for r in rows if r["sentences"] < 3 or r["words"] < 80]
    if bad:
        sys.exit("abstract cut too short: " + ", ".join(bad))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "abstract_features.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(OUT, "abstract_sentences.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["paper", "sentence", "move", "words", "text"])
        for name, s in sents_by.items():
            w.writerows([name, i, m, n, t] for i, (t, m, n) in enumerate(s, 1))
    grp = groups_of([r["paper"] for r in rows])
    seen = list(dict.fromkeys(grp.values()))
    order = [g for g in GROUP_ORDER if g in seen] + [g for g in seen if g not in GROUP_ORDER]
    out = [f"# {VENUE} {len(rows)} 篇的摘要", "",
           "由 `scripts/abstract_stats.py` 生成,切法与句子功能标签是机械规则(见脚本文件头)。",
           "版式:" + ",".join(f"{k} {v}" for k, v in Counter(r["layout"] for r in rows).most_common()) + "。",
           f"分组按 `{os.path.relpath(LABELS, ROOT)}` 的 group 列,与 `by_type_report.md` 同一套。", ""]
    out += section(rows, sents_by, "全部")
    for g in order:
        out += section([r for r in rows if grp.get(r["paper"]) == g], sents_by, g)
    with open(os.path.join(OUT, "abstract_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(os.path.join(OUT, "abstract_report.md"))


if __name__ == "__main__":
    main()
