"""Tests for the study-design statistics: which sections are taken per paper type, the cut
inside an evaluation section, the design-titled subsections under result sections, the hand
overrides, the unit topics and the marker sentences."""
import methodology_stats as ds

MD = """# 1 Introduction

We study call graphs. RQ1 asks about the frontier.

# 2 Background

Definitions.

# 3 Approach

We propose a technique.

## 3.1 Overview

The technique.

# 4 Experimental Setup

This section describes the datasets and metrics.

## 4.1 Datasets

We use ten datasets [\\[1\\]](#p) because they are public. Each run is repeated five times with a fixed seed.

## 4.2 Evaluation Metrics

Accuracy is the metric. Differences are tested with a Wilcoxon test.

# 5 Evaluation

Preamble of the evaluation.

## 5.1 Experimental Setup

Models are trained on one A100 GPU for 200 epochs.

## 5.2 RQ1: Effectiveness

Results here are not design.

# 6 RQ2: Stability

## 6.1 Study Design

Each pair is shown twice.

## 6.2 Results

Numbers.

# 7 Results

More numbers.

# 8 Implementation

Not taken: after the results.

# References
"""


def _sections(ptype, name="FSE2026_Fixture"):
    taken, top, extra, per_rq = ds.design_sections(MD, ptype, name)
    return [t[0] for t in taken], [(e[0], e[1]) for e in extra], per_rq


def test_sections_by_type_and_the_results_stop():
    # method papers drop 3 Approach, empirical papers keep it; 8 Implementation sits after 7 Results and is
    # never taken; the per-RQ flag is set because section 6 is titled by an RQ number
    assert _sections("method") == ([4, 5], [(6, "Study Design")], True)
    assert _sections("empirical") == ([3, 4, 5], [(6, "Study Design")], True)


def test_cut_inside_evaluation_but_not_inside_setup():
    taken, _, _, _ = ds.design_sections(MD, "method", "FSE2026_Fixture")
    setup, evaluation = taken
    units, cut = ds.units_of(*setup)
    assert [u[0] for u in units] == ["", "Datasets", "Evaluation Metrics"] and cut is False
    units, cut = ds.units_of(*evaluation)
    assert [u[0] for u in units] == ["", "Experimental Setup"] and cut is True


def test_hand_overrides():
    ds.HAND_DESIGN["FSE2026_Fixture"] = dict(exclude=(4,), include=(7,), why="test")
    try:
        assert _sections("method")[0] == [5, 7]
    finally:
        del ds.HAND_DESIGN["FSE2026_Fixture"]


def test_topics_and_markers():
    assert [ds.topic_of(t) for t in ("Research Questions", "Datasets and Evaluation Metrics", "Evaluation Metrics",
                                     "Implementation Details", "Selected LLMs", "Baselines", "Threats to Validity",
                                     "Experimental Procedure", "Taxonomy")] == \
        ["rq", "data", "metric", "setting", "model", "baseline", "threats", "procedure", "other"]
    text ="We use ten datasets because they are public. Each run is repeated five times with a fixed seed. " \
           "Differences are tested with a Wilcoxon test. Models are trained on one A100 GPU for 200 epochs."
    sents = ds.sentences(text)
    hits = {m: sum(1 for s in sents if rx.search(s)) for m, rx in ds.MARKERS.items()}
    assert (hits["rationale"], hits["repeat"], hits["stats_test"], hits["hardware"], hits["hyper"]) == (1, 1, 1, 1, 1)


def test_features_end_to_end(tmp_path):
    p = tmp_path / "FSE2026_Fixture_paper"
    p.mkdir()
    md = p / "FSE2026_Fixture_paper.md"
    md.write_text(MD, encoding="utf-8")
    row, units = ds.features("FSE2026_Fixture_paper", str(md))
    assert "type" not in row and row["layout"] == "section+evaluation" and row["sections"] == "4 5"
    assert row["all_subsectioned"] is True
    assert row["prev"] == "Approach" and row["prev_kind"] == "approach" and row["next"] == "RQ2: Stability"
    assert [u["topic"] for u in units] == ["preamble", "data", "metric", "preamble", "setting", "procedure"]
    assert row["units"] == 6 and row["sub_units"] == 1 and row["opens_with_roadmap"] is True
    assert row["cite_groups"] == 1 and row["m_stats_test"] == 1 and row["m_hardware"] == 1 and row["m_hyper"] == 1
    assert row["rq_in_intro"] == 1 and row["rq_in_design"] == 0
    assert "[" not in row["first_sentence"]
