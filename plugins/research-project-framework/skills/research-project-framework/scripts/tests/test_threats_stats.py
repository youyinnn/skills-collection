"""Tests for the threats statistics: which heading is cut and where its text ends, the run-in
fallback when no heading matches, the label forms and the sentence that is not a label, the unit
modes, categories, topics and the scheme, and the end-to-end row."""
import threats_stats as ts

MD = """# 1 Introduction

We study saliency maps.

# 2 Threat Model

Not a threats section.

# 3 Results

## 3.1 RQ1: Validity of the findings

Not a threats section either.

# 4 Discussion

Discussion text.

## 4.1 Threats to Validity

We identify three threats to our study.

Internal validity: Parameter settings such as the number of iterations can lead to different results. To mitigate this, we ran each setting five times [\\[3\\]](#p).

**External validity.** Our datasets may not represent other domains. We leave other domains to future work.

Listing 1. A code snippet.

Construct Validity. The metric is standard and widely used, as described in Section [3](#page-4-0). We believe this threat does not affect our findings.

## 4.2 Implications

Not threats.

# 5 Related Work

# References
"""

MD_RUNIN = """# 1 Introduction

Intro.

# 5 Discussion

Some discussion.

Threats to Validity. In terms of construct validity, we use one metric. In terms of external validity, our results may not generalize to other systems. To mitigate this threat, we chose three systems.

Implications. Practitioners should tune.

# 6 Conclusion

# References
"""


def test_cut_skips_threat_model_and_rq_titles_and_ends_at_the_next_subsection():
    cut, hs, limit = ts.threats_heading(MD, "FSE2026_Fixture")
    num, title, level, raw, subs, n_matching = cut
    assert num == (4, 1) and level == 2 and n_matching == 1 and subs == []
    assert "Construct Validity" in raw and "Implications" not in raw


def test_labels_and_the_sentence_that_is_not_a_label():
    assert ts.label_of("Internal validity: Parameter settings can differ.") == ("Internal validity", "plain")
    assert ts.label_of("**External validity.** Our datasets may not represent other domains.") == ("External validity", "bold")
    assert ts.label_of("**The internal threat** mainly arises from the implementation.") == ("The internal threat", "bold")
    assert ts.label_of("6.2.1 Internal Threats. The selection of metrics.") == ("Internal Threats", "numbered")
    assert ts.label_of("[Internal] Inherited from prior work.") == ("Internal", "bracket")
    assert ts.label_of("Selection of datasets and networks. We used three datasets.") == ("Selection of datasets and networks", "plain")
    assert ts.label_of("Our study has two main threats. Internally, expertise varies.") == (None, None)   # a verb and a pronoun
    assert ts.label_of("Listing 1. The code snippet shown in (a).") == (None, None)                       # a caption
    assert ts.label_of("The validity of this work may be subject to some threats. First, ...") == (None, None)


def test_units_categories_topics_and_scheme():
    cut, *_ = ts.threats_heading(MD, "FSE2026_Fixture")
    units, mode = ts.units_of(cut[3], cut[4], cut[2])
    assert mode == "runin" and [u[0] for u in units] == ["", "Internal validity", "External validity", "Construct Validity"]
    assert "Listing 1" in units[2][2]                                     # the caption attaches to the unit before it
    rows = [ts.unit_row("p", i + 1, *u) for i, u in enumerate(units)]
    assert [r["category"] for r in rows] == ["preamble", "internal", "external", "construct"]
    assert [r["topic"] for r in rows] == ["preamble", "hyperparameter", "data", "metric"]
    assert ts.scheme_of(mode, rows, cut[3]) == "validity-labels"
    assert ts.label_of("Polysemy in neurons. This study investigates.")[0] and \
        ts.split_labels(["Limitations follow:\nPolysemy in neurons. This study investigates."]) == ["Limitations follow:", "Polysemy in neurons. This study investigates."]


def test_runin_fallback(tmp_path):
    p = tmp_path / "FSE2026_Fixture_runin"
    p.mkdir()
    md = p / "FSE2026_Fixture_runin.md"
    md.write_text(MD_RUNIN, encoding="utf-8")
    row, units = ts.features("FSE2026_Fixture_runin", str(md))
    assert row["layout"] == "runin" and row["parent_kind"] == "discussion" and row["threats"] == 1
    assert "Implications" not in units[0]["first_sentence"] and row["words"] < 45
    assert row["scheme"] == "validity-prose" and row["mentioned"] == "external construct"


def test_features_end_to_end(tmp_path):
    p = tmp_path / "FSE2026_Fixture_paper"
    p.mkdir()
    md = p / "FSE2026_Fixture_paper.md"
    md.write_text(MD, encoding="utf-8")
    row, units = ts.features("FSE2026_Fixture_paper", str(md))
    assert row["layout"] == "subsection" and row["number"] == "4.1" and row["parent_kind"] == "discussion" and row["is_last_sub"] is False
    assert row["title_kind"] == "threats" and row["mode"] == "runin" and row["scheme"] == "validity-labels"
    assert row["threats"] == 3 and row["category_order"] == "internal external construct" and row["preamble_words"] == 7
    assert row["cite_groups"] == 1                       # [3](#page-4-0) is a cross-reference, not a citation
    assert row["m_mitigate"] >= 1 and row["m_future"] >= 1 and row["m_dismiss"] >= 1 and row["m_refback"] >= 1 and row["m_standard"] >= 1
    assert units[1]["m_mitigate"] == 1 and units[3]["m_dismiss"] == 1


def test_hand_none():
    ts.HAND_THREATS["FSE2026_Fixture"] = dict(none=True, why="test")
    try:
        assert ts.threats_heading(MD, "FSE2026_Fixture")[0] is None
    finally:
        del ts.HAND_THREATS["FSE2026_Fixture"]
