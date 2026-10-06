"""Recompute the medians and counts of the *_features.csv tables per paper-type group.

The groups come from the label file in config.py (one row per sample paper: folder name and
group), produced by coding the sample with a paper-type codebook. The measuring scripts are not
changed; this script only joins their tables.

  python scripts/by_type.py   # by_type_report.md, by_type_slots.md
"""
import csv, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from config import GROUP_ORDER, LABELS as _LABELS, MARKER_DIR, PATTERNS_OUT, VENUE, need  # noqa: E402
PAT = Path(PATTERNS_OUT)
LABELS = Path(_LABELS)
OUT = PAT / "by_type_report.md"
OUT_SLOTS = PAT / "by_type_slots.md"

def group_of(r):
    """The paper-type group of one label row (column `group` of the label file)."""
    return r["group"]

def match(short, longs):
    toks = short.split("_")
    for n in range(len(toks), 0, -1):
        hits = [l for l in longs if l.split("_", 1)[-1].startswith("_".join(toks[:n]) + "_") or l.split("_", 1)[-1] == "_".join(toks[:n])]   # [-1]: a name without "_" is its own title part
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1 and n == 1:
            break
    raise KeyError(short)

def load(name):
    p = PAT / f"{name}_features.csv"
    if not p.exists():
        raise SystemExit(f"{p} is missing: run scripts/{name}_stats.py first")
    return {r["paper"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}

def as_num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def as_bool(v):
    if v in ("True", "False"):
        return v == "True"
    n = as_num(v)  # count columns (rq_in_intro, m_*): nonzero means present
    return None if n is None else n > 0

# (table, column, kind, label); kind: med, frac, cat, has ("col:token": token in the space-separated / letter string)
FEATS = [
    ("intro", "words", "med", "引言词数"),
    ("intro", "paragraphs", "med", "引言段数"),
    ("intro", "contrib_items", "med", "贡献条数"),
    ("intro", "cites_per_100w", "med", "引言引用/百词"),
    ("intro", "rq_in_intro", "frac", "RQ 在引言"),
    ("intro", "contrib_list", "frac", "有贡献列表"),
    ("intro", "figure", "frac", "引言有图"),
    ("intro", "tail_numbers", "frac", "引言结尾带数字"),
    ("intro", "monotone", "frac", "引言块顺序单调"),
    ("intro", "moves:D", "has", "引言有设计段 D"),
    ("intro", "moves:F", "has", "引言有发现段 F"),
    ("intro", "contrib_first", "cat", "贡献第一条"),
    ("intro", "opener", "cat", "开头句"),
    ("relwork", "placement", "cat", "相关工作位置"),
    ("relwork", "words", "med", "相关工作词数"),
    ("relwork", "subsections", "med", "相关工作小节数"),
    ("relwork", "cites_per_100w", "med", "相关工作引用/百词"),
    ("background", "has_background", "frac", "有背景节"),
    ("background", "relation", "cat", "背景节与相关工作的排法"),
    ("background", "fit", "frac", "背景节三拍契合(有的篇)"),
    ("background", "bg_words", "med", "背景节词数(有的篇)"),
    ("background", "formulas", "med", "背景节公式数(有的篇)"),
    ("background", "cites_per_100w", "med", "背景节引用/百词(有的篇)"),
    ("methodology", "layout", "cat", "方法节排法"),
    ("methodology", "words", "med", "方法节词数"),
    ("methodology", "units", "med", "方法节单元数"),
    ("methodology", "topics:rq", "has", "方法节有 RQ 小节"),
    ("methodology", "topics:data", "has", "方法节有数据小节"),
    ("methodology", "topics:metric", "has", "方法节有度量小节"),
    ("methodology", "topics:baseline", "has", "方法节有基线小节"),
    ("methodology", "topics:procedure", "has", "方法节有流程小节"),
    ("methodology", "topics:model", "has", "方法节有模型小节"),
    ("methodology", "per_rq", "frac", "结果按 RQ 分节"),
    ("methodology", "cites_per_100w", "med", "方法节引用/百词"),
    ("methodology", "formulas", "med", "方法节公式数"),
    ("methodology", "tables", "med", "方法节表数"),
    ("methodology", "figures", "med", "方法节图数"),
    ("methodology", "sent_median", "med", "方法节句长中位"),
    ("methodology", "rq_in_design", "frac", "RQ 在方法节"),
    ("methodology", "m_stats_test", "frac", "方法节提统计检验"),
    ("methodology", "m_repeat", "frac", "方法节提重复次数"),
    ("results", "layout", "cat", "结果节排法"),
    ("results", "words", "med", "结果节词数"),
    ("results", "share", "med", "结果节占正文"),
    ("results", "units", "med", "结果节单元数"),
    ("results", "rq_level", "cat", "结果节 RQ 层级"),
    ("results", "rq_count", "med", "结果节 RQ 个数"),
    ("results", "units_per_rq", "med", "每个 RQ 的单元数"),
    ("results", "paragraphs", "med", "结果节段数"),
    ("results", "sent_median", "med", "结果节句长中位"),
    ("results", "num_sent_share", "med", "带数字的句子占比"),
    ("results", "numbers_per_100w", "med", "结果节数字/百词"),
    ("results", "cites_per_100w", "med", "结果节引用/百词"),
    ("results", "formulas", "frac", "结果节有公式"),
    ("results", "tables_ref", "med", "结果节引用的表数"),
    ("results", "figures_ref", "med", "结果节引用的图数"),
    ("results", "boxes", "frac", "结果节有总结框"),
    ("results", "boxes", "med", "总结框数"),
    ("results", "runin_paras", "frac", "结果节有行内小标题段"),
    ("results", "m_stats_test", "frac", "结果节提统计检验"),
    ("results", "m_explain", "frac", "结果节有解释句"),
    ("results", "m_negative", "frac", "结果节有零结果句"),
    ("results", "m_implication", "frac", "结果节有含义句"),
    ("results", "opens_with_roadmap", "frac", "结果节首段路标句"),
    ("threats", "layout", "cat", "威胁节排法"),
    ("threats", "words", "med", "威胁节词数"),
    ("threats", "share", "med", "威胁节占正文"),
    ("threats", "paragraphs", "med", "威胁节段数"),
    ("threats", "threats", "med", "威胁条数"),
    ("threats", "mode", "cat", "威胁节分块方式"),
    ("threats", "scheme", "cat", "威胁节组织"),
    ("threats", "n_categories", "med", "威胁节命名的效度类别数"),
    ("threats", "preamble_words", "frac", "威胁节有引言段"),
    ("threats", "sent_median", "med", "威胁节句长中位"),
    ("threats", "cites_per_100w", "med", "威胁节引用/百词"),
    ("threats", "m_mitigate", "frac", "威胁节有缓解句"),
    ("threats", "m_dismiss", "frac", "威胁节有免责句"),
    ("threats", "m_residual", "frac", "威胁节有余留句"),
    ("threats", "m_future", "frac", "威胁节有未来工作句"),
    ("threats", "m_standard", "frac", "威胁节有惯例句"),
    ("threats", "m_define", "frac", "威胁节有定义句"),
    ("threats", "m_number", "frac", "威胁节有数字句"),
    ("discussion", "layout", "cat", "讨论节排法"),
    ("discussion", "words", "med", "讨论节词数(独立与小节)"),
    ("discussion", "share", "med", "讨论节占正文"),
    ("discussion", "paragraphs", "med", "讨论节段数"),
    ("discussion", "labeled", "med", "讨论节单元数"),
    ("discussion", "mode", "cat", "讨论节分块方式"),
    ("discussion", "scheme", "cat", "讨论节组织"),
    ("discussion", "topics:implications", "has", "讨论节有启示单元"),
    ("discussion", "topics:explanation", "has", "讨论节有解释单元"),
    ("discussion", "topics:comparison", "has", "讨论节有对照先前工作单元"),
    ("discussion", "topics:future", "has", "讨论节有未来工作单元"),
    ("discussion", "topics:case", "has", "讨论节有案例单元"),
    ("discussion", "threats_inside", "frac", "威胁在讨论节内"),
    ("discussion", "audiences", "cat", "讨论节点名的对象"),
    ("discussion", "sent_median", "med", "讨论节句长中位"),
    ("discussion", "cites_per_100w", "med", "讨论节引用/百词"),
    ("discussion", "m_implication", "frac", "讨论节有启示句"),
    ("discussion", "m_audience", "frac", "讨论节有点名对象句"),
    ("discussion", "m_explain", "frac", "讨论节有解释句"),
    ("discussion", "m_compare_prior", "frac", "讨论节有对照先前工作句"),
    ("discussion", "m_number", "frac", "讨论节有数字句"),
    ("discussion", "m_hedge", "frac", "讨论节有缓和句"),
    ("discussion", "m_question", "frac", "讨论节有问句"),
]


# ---- per-group slot tables from the four unit files -------------------------
MOVES = [("C", "context"), ("P", "problem"), ("E", "example"), ("L", "limitation of prior work"),
         ("T", "this paper"), ("D", "design"), ("F", "findings"), ("K", "contributions"),
         ("I", "implications"), ("R", "roadmap or artifact")]
BG_KINDS = ["preamble", "definitional", "motivation", "related-work"]
DESIGN_TOPICS = ["preamble", "rq", "data", "model", "metric", "baseline", "setting", "procedure", "other"]
RESULT_THEMES = ["preamble", "setup", "results", "question", "summary", "ablation", "qualitative", "efficiency",
                 "generalization", "comparison", "threats", "discussion", "other", "unnamed"]
THREAT_CATS = ["preamble", "internal", "external", "construct", "conclusion", "reliability", "none"]
DISC_TOPICS = ["preamble", "implications", "explanation", "comparison", "generalization", "case", "validation", "cost",
               "summary", "future", "threats", "other"]

def q(vals):
    vals = sorted(vals)
    if not vals:
        return "-"
    n = len(vals)
    med = statistics.median(vals)
    lo, hi = vals[n // 4], vals[(3 * n) // 4 if (3 * n) // 4 < n else n - 1]
    return f"{med:g} ({lo:g}–{hi:g})"

def slot_rows(unit_rows, key, vocab, papers, order_key):
    """For each vocab value: papers having it / n, median position (1-based unit index) and words (median, quartiles)."""
    by_paper = {}
    for r in unit_rows:
        if r["paper"] in papers:
            by_paper.setdefault(r["paper"], []).append(r)
    out = []
    for v in vocab:
        have, pos, words = [], [], []
        for pp, rs in by_paper.items():
            rs = sorted(rs, key=lambda r: int(r[order_key]))
            hits = [i for i, r in enumerate(rs, 1) if r[key] == v]
            if hits:
                have.append(pp); pos.append(hits[0])
                words.append(sum(float(r["words"]) for r in rs if r[key] == v))
        out.append((v, f"{len(have)} / {len(papers)}", q(pos), q(words)))
    return out

def slots_report(members, order):
    units = {n: list(csv.DictReader(open(PAT / f"{n}.csv", encoding="utf-8"))) for n in ("intro_moves", "relwork_subsections", "background_units", "methodology_units", "results_units", "threats_units", "discussion_units")}
    tables_discussion = list(csv.DictReader(open(PAT / "discussion_features.csv", encoding="utf-8")))
    out = [f"# {VENUE} {sum(len(v) for g, v in members.items() if g != '全部')} 篇按论文类型分组的槽位统计", "",
           "由 `scripts/by_type.py` 生成,与 `by_type_report.md` 同一套分组。",
           "每个槽位报:该组里有这个槽的篇数 / 组篇数;它第一次出现的位置(第几段或第几个单元,中位与四分位);这个槽在一篇里的合计词数(中位与四分位,只算有它的篇)。",
           "引言的槽是 `intro_stats.py` 的段落功能标签(HAND 表,单人手标);背景、研究设计与结果的槽是各自脚本按标题归的单元类别(结果节用去掉 RQ 编号后的主题);相关工作只有小节,没有槽。", ""]
    for g in order:
        papers = {r["paper"] for r in members[g]}
        n = len(papers)
        out += [f"## {g}({n})", ""]
        if n < 5:
            out += ["篇数不足 5,只列篇目:" + ",".join(r["short"] for r in members[g]), ""]; continue
        out += ["### 引言:段落功能", "", "| 功能 | 有的篇数 | 首次出现在第几段 | 合计词数 |", "|---|---|---|---|"]
        for v, name in MOVES:
            for row in slot_rows(units["intro_moves"], "move", [v], papers, "para"):
                out.append(f"| {v} {name} | {row[1]} | {row[2]} | {row[3]} |")
        # coarse order: most common sequence of distinct moves in order of first appearance
        seqs = {}
        for pp in papers:
            rs = sorted([r for r in units["intro_moves"] if r["paper"] == pp], key=lambda r: int(r["para"]))
            seen = []
            for r in rs:
                if r["move"] not in seen and r["move"] not in ("X",):
                    seen.append(r["move"])
            seqs[" ".join(seen)] = seqs.get(" ".join(seen), 0) + 1
        top = sorted(seqs.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
        out += ["", "首次出现顺序(去掉重复与噪声段,最常见的几种):" + ";".join(f"{k} {v}" for k, v in top), ""]
        out += ["### 相关工作:小节", ""]
        subs = [r for r in units["relwork_subsections"] if r["paper"] in papers]
        per = {}
        for r in subs:
            per.setdefault(r["paper"], []).append(r)
        nsub = [len(v) for v in per.values()] + [0] * (n - len(per))
        out.append(f"有小节的篇数 {len(per)} / {n};小节数中位 {q(nsub)};小节词数中位 {q([float(r['words']) for r in subs])};小节末段带定位句的小节 {sum(r['last_para_positions']=='True' for r in subs)} / {len(subs)}。")
        out += ["", "### 背景节:单元类别", "", "| 类别 | 有的篇数 | 首次出现在第几个单元 | 合计词数 |", "|---|---|---|---|"]
        bg_papers = {r["paper"] for r in units["background_units"]} & papers
        for row in slot_rows(units["background_units"], "kind", BG_KINDS, bg_papers, "unit"):
            out.append(f"| {row[0]} | {row[1]}(有背景节的篇) | {row[2]} | {row[3]} |")
        out += ["", "### 方法节:单元主题", "", "| 主题 | 有的篇数 | 首次出现在第几个单元 | 合计词数 |", "|---|---|---|---|"]
        for row in slot_rows(units["methodology_units"], "topic", DESIGN_TOPICS, papers, "unit"):
            out.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
        seqs = {}
        for pp in papers:
            rs = sorted([r for r in units["methodology_units"] if r["paper"] == pp], key=lambda r: int(r["unit"]))
            seen = []
            for r in rs:
                if r["topic"] not in seen:
                    seen.append(r["topic"])
            seqs[" ".join(seen)] = seqs.get(" ".join(seen), 0) + 1
        top = sorted(seqs.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
        out += ["", "主题首次出现顺序(最常见的几种):" + ";".join(f"{k} {v}" for k, v in top), ""]
        out += ["### 结果节:单元主题", "", "| 主题 | 有的篇数 | 首次出现在第几个单元 | 合计词数 |", "|---|---|---|---|"]
        for row in slot_rows(units["results_units"], "theme", RESULT_THEMES, papers, "unit"):
            out.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
        seqs = {}
        for pp in papers:
            rs = sorted([r for r in units["results_units"] if r["paper"] == pp], key=lambda r: int(r["unit"]))
            seen = []
            for r in rs:
                if r["theme"] not in seen:
                    seen.append(r["theme"])
            seqs[" ".join(seen)] = seqs.get(" ".join(seen), 0) + 1
        top = sorted(seqs.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
        rq = [r for r in units["results_units"] if r["paper"] in papers and r["topic"] == "rq"]
        out += ["", "主题首次出现顺序(最常见的几种):" + ";".join(f"{k} {v}" for k, v in top),
                f"RQ 单元 {len(rq)} 个:词数中位 {q([float(r['words']) for r in rq])};以总结框收尾的 {sum(r['ends_with_box']=='True' for r in rq)} / {len(rq)};首句指向图表的 {sum(r['opens_with_figtab']=='True' for r in rq)} / {len(rq)}。", ""]
        out += ["### 威胁节:单元的效度类别", "", "| 类别 | 有的篇数 | 首次出现在第几个单元 | 合计词数 |", "|---|---|---|---|"]
        th_papers = {r["paper"] for r in units["threats_units"]} & papers
        for row in slot_rows(units["threats_units"], "category", THREAT_CATS, th_papers, "unit"):
            out.append(f"| {row[0]} | {row[1]}(有威胁节的篇) | {row[2]} | {row[3]} |")
        seqs = {}
        for pp in th_papers:
            rs = sorted([r for r in units["threats_units"] if r["paper"] == pp], key=lambda r: int(r["unit"]))
            seen = [r["category"] for r in rs if r["category"] not in ("preamble", "none")]
            seen = [c for i, c in enumerate(seen) if c not in seen[:i]]
            seqs[" ".join(seen) or "(无)"] = seqs.get(" ".join(seen) or "(无)", 0) + 1
        top = sorted(seqs.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
        out += ["", "类别首次出现顺序(最常见的几种):" + ";".join(f"{k} {v}" for k, v in top), ""]
        out += ["### 讨论节:单元主题(独立一节与小节,不含并进结果节的)", "", "| 主题 | 有的篇数 | 首次出现在第几个单元 | 合计词数 |", "|---|---|---|---|"]
        merged = {r["paper"] for r in tables_discussion if r["layout"] == "merged"}
        di_papers = ({r["paper"] for r in units["discussion_units"]} & papers) - merged
        for row in slot_rows(units["discussion_units"], "topic", DISC_TOPICS, di_papers, "unit"):
            out.append(f"| {row[0]} | {row[1]}(有讨论节的篇) | {row[2]} | {row[3]} |")
        seqs = {}
        for pp in di_papers:
            rs = sorted([r for r in units["discussion_units"] if r["paper"] == pp], key=lambda r: int(r["unit"]))
            seen = [r["topic"] for r in rs if r["topic"] != "preamble"]
            seen = [c for i, c in enumerate(seen) if c not in seen[:i]]
            seqs[" ".join(seen) or "(无)"] = seqs.get(" ".join(seen) or "(无)", 0) + 1
        top = sorted(seqs.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
        out += ["", "主题首次出现顺序(最常见的几种):" + ";".join(f"{k} {v}" for k, v in top), ""]
    OUT_SLOTS.write_text("\n".join(out) + "\n", encoding="utf-8")

def main():
    need(VENUE, "VENUE")
    if not LABELS.exists():
        raise SystemExit(f"no label file {LABELS}: code the sample papers by type first (column paper, column group)")
    labels = list(csv.DictReader(open(LABELS, encoding="utf-8")))
    tables = {t: load(t) for t in ("intro", "relwork", "background", "methodology", "results", "threats", "discussion")}
    longs = sorted(d.name for d in Path(need(VENUE, "VENUE") and MARKER_DIR).iterdir() if d.is_dir())
    rows, unmeasured = [], []
    for r in labels:
        long = match(r["paper"], longs)
        if not any(long in tables[t] for t in tables):      # in intro_stats.SKIP: labeled, not measured
            unmeasured.append(r["paper"]); continue
        rows.append({"paper": long, "short": r["paper"], "group": group_of(r)})
    seen = list(dict.fromkeys(r["group"] for r in rows))
    groups = [g for g in GROUP_ORDER if g in seen] + [g for g in seen if g not in GROUP_ORDER]
    members = {g: [r for r in rows if r["group"] == g] for g in groups}
    members["全部"] = rows
    order = groups + ["全部"]
    out = [f"# {VENUE} {len(rows)} 篇按论文类型分组的形式特征", "",
           f"由 `scripts/by_type.py` 生成;标签来自 `{LABELS.relative_to(ROOT)}` 的 group 列({len(labels)} 篇)。"
           + (f"有标签但六份特征表都没有的 {len(unmeasured)} 篇不计:{'、'.join(unmeasured)}(见 `intro_stats.py` 的 SKIP)。" if unmeasured else ""),
           "分组按标签文件的 group 列,组名与组数由编码本定。",
           "数值列报中位数;是/否列报「是的篇数 / 该组篇数」;类别列报各值篇数。篇数不足 5 的组只列篇目、不报数字。", "",
           "## 分组篇目", ""]
    for g in groups:
        out.append(f"- **{g}({len(members[g])})**:" + ",".join(r["short"] for r in members[g]))
    out += ["", "## 特征表", "", "| 特征 | " + " | ".join(f"{g}({len(members[g])})" for g in order) + " |", "|---|" + "---|" * len(order)]
    for table, col, kind, label in FEATS:
        cells = []
        for g in order:
            recs = [tables[table][r["paper"]] for r in members[g] if r["paper"] in tables[table]]
            if table == "background" and col != "has_background":
                recs = [x for x in recs if x["has_background"] == "True"]
            if len(members[g]) < 5:
                cells.append("篇数不足"); continue
            if kind == "med":
                vals = [v for v in (as_num(x[col]) for x in recs) if v is not None]
                cells.append(f"{statistics.median(vals):g} (n={len(vals)})" if vals else "-")
            elif kind == "has":
                c, tok = col.split(":")
                vals = [tok in (x[c].split() if " " in x[c] or c == "topics" else x[c]) for x in recs]
                cells.append(f"{sum(vals)} / {len(vals)}")
            elif kind == "frac":
                vals = [as_bool(x[col]) for x in recs]
                vals = [v for v in vals if v is not None]
                cells.append(f"{sum(vals)} / {len(vals)}")
            else:
                cnt = {}
                for x in recs:
                    cnt[x[col]] = cnt.get(x[col], 0) + 1
                cells.append(", ".join(f"{k} {v}" for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])))
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(OUT)
    slots_report(members, order)
    print(OUT_SLOTS)

if __name__ == "__main__":
    main()
