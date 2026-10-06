"""Tests for the results statistics: where the run starts and stops, the complement of the
design cut, the dropped setup subsections, the hand overrides, unit topics and themes, boxes in
paragraph and heading form, cross-references that are neither citations nor hidden from the
figtab marker, and the end-to-end row."""
import results_stats as rs

MD = """# 1 Introduction

We study saliency maps. RQ1 asks about the frontier.

# 2 Background

Definitions.

# 3 Approach

We propose a technique.

# 4 Experimental Setup

This section describes the datasets and metrics.

## 4.1 Datasets

We use ten datasets [\\[1\\]](#p) because they are public.

# 5 Results

In this section, we report the results of the four research questions.

## 5.1 RQ1: Effectiveness

Table [3](#page-5-0) shows the results. Method A outperforms B by 12% on all datasets, which suggests that context matters [\\[2\\]](#p).

**Finding 1:** Static context helps more than retrieved context.

## 5.2 RQ2: Efficiency

Figure [2](#page-6-0) plots the cost. Because indexing is offline, the online cost stays under one second.

# Answer to RQ2

Passive methods are cheaper than active ones.

## 5.3 Study Design

Not results: the design of a follow-up experiment.

# 6 Ablation Study

Removing the index halves the gain.

# 7 RQ3: Implications for Practice

Still results: titled by an RQ number.

# 8 Discussion

Not results.

# 9 New Approach

Not results either.

# References
"""

MD_INSIDE = """# 1 Introduction

Intro.

# 2 Approach

The technique.

# 3 Evaluation

We answer three RQs.

## 3.1 Experimental Setup

Models are trained on one GPU.

## 3.2 RQ1: Accuracy

The accuracy is 90%.

## 3.3 RQ2: Robustness

No significant difference is found.

# 4 Threats to Validity

Threats.

# References
"""


def _run(md, name="FSE2026_Fixture", ptype="method"):
    run, top, design_found, cut_of = rs.results_sections(rs.XREF.sub(r"\\1", md), ptype, name)
    return [(r[0], r[4]) for r in run], design_found


def test_run_starts_after_the_design_and_stops_at_discussion():
    # 5 Results, 6 Ablation Study and 7 RQ3 (an END word in an RQ title does not stop the run); 8 Discussion ends it before 9 New Approach
    assert _run(MD) == ([(5, "whole"), (6, "whole"), (7, "whole")], True)


def test_complement_of_the_design_cut():
    run, top, _, cut_of = rs.results_sections(MD_INSIDE, "method", "FSE2026_Fixture")
    assert [(r[0], r[4]) for r in run] == [(3, "complement")] and cut_of == {3: True}
    units = rs.results_units_of(*run[0][1:4], run[0][4])
    assert [u[0] for u in units] == ["RQ1: Accuracy", "RQ2: Robustness"]   # setup dropped, no preamble in complement mode


def test_setup_subsection_dropped_and_preamble_kept():
    run, *_ = rs.results_sections(MD, "method", "FSE2026_Fixture")
    units = rs.results_units_of(*run[0][1:4], run[0][4])
    assert [u[0] for u in units] == ["", "RQ1: Effectiveness", "RQ2: Efficiency"]   # 5.3 Study Design dropped


def test_hand_overrides():
    rs.HAND_RESULTS["FSE2026_Fixture"] = dict(start=6, end=7, why="test")   # end is exclusive
    try:
        assert _run(MD)[0] == [(6, "whole")]
    finally:
        del rs.HAND_RESULTS["FSE2026_Fixture"]


def test_topics_themes_and_boxes():
    assert [rs.topic_of(t) for t in ("RQ1: Effectiveness", "How Do Models Compare?", "Ablation Study", "Time Efficiency",
                                     "Case Study", "Symptom Taxonomy", "Experimental Setup", "Findings", "Answer to RQs")] == \
        ["rq", "question", "ablation", "efficiency", "qualitative", "other", "setup", "results", "summary"]
    assert [rs.theme_of(t) for t in ("RQ1: Effectiveness", "RQ2", "Attack Performance (RQ3)")] == ["comparison", "unnamed", "comparison"]
    keep, boxes = rs.boxes_in("Intro paragraph.\n\n**Finding 1:** Static context helps.\n\n# Answer to RQ2\n\nPassive methods are cheaper.\n\n"
                              "# Summary: the text on the heading line itself.\n\nFindings from the survey are mixed.\n\n"
                              "Result 1: quantized models are smaller.\n\nResults. Table 2 presents the numbers.")
    assert [(k, i) for i, k, _ in boxes] == [("finding", 1), ("answer", 2), ("summary", 3), ("result", 5)] and len(keep) == 7


def test_features_end_to_end(tmp_path):
    p = tmp_path / "FSE2026_Fixture_paper"
    p.mkdir()
    md = p / "FSE2026_Fixture_paper.md"
    md.write_text(MD, encoding="utf-8")
    row, units = rs.features("FSE2026_Fixture_paper", str(md))
    assert row["layout"] == "section" and row["sections"] == "5 6 7" and row["prev_kind"] == "design" and row["next_kind"] == "discussion"
    assert [u["topic"] for u in units] == ["preamble", "rq", "rq", "ablation", "rq"] and row["rq_level"] == "subsection" and row["rq_count"] == 3
    assert row["cite_groups"] == 1                       # the [3](#page-5-0) cross-reference is not a citation
    assert units[1]["opens_with_figtab"] and row["tables_ref"] == 1 and row["figures_ref"] == 1
    assert row["boxes"] == 2 and row["box_kinds"] == "answer finding" and units[1]["ends_with_box"] and units[2]["ends_with_box"]
    assert row["m_compare"] >= 1 and row["m_hedge"] >= 1 and row["m_explain"] >= 1 and row["m_magnitude"] >= 1
    assert row["opens_with_roadmap"] is True and "[" not in row["first_sentence"]
