"""Tests for the introduction statistics.

The introduction is cut out of Marker markdown whose headings are not uniform (one to four
hashes, optional bold, optional span anchor, optional upper case), and the cut text carries
front-matter noise (author block, licence, copyright, ISSN, images, footnotes, captions) plus
paragraphs split at page breaks. These tests pin the cut, the cleaning, and the mechanical
features so that the hand-coded move sequences line up with what the script counts.
"""
import pytest

import intro_stats as fis


SAMPLE = """# Some Title

Abstract text.

#### <span id="page-1-0"></span>1 Introduction

Transformer models [\\[53\\]](#page-21-1) are everywhere. They matter [\\[1\\]](#p), [\\[2\\]](#p).

Authors' Contact Information: [A. Person,](https://orcid.org/0) Some University.

![](_page_0_Picture_14.jpeg)

[This work is licensed under a Creative Commons Attribution 4.0 International License.](https://creativecommons.org/licenses/by/4.0)

© 2025 Copyright held by the owner/author(s).

ACM 2994-970X/2025/7-ARTFSE054

However, fine-tuning them requires significant compute, and prior work leaves this

<span id="page-1-0"></span><sup>1</sup>Footnote text here.

unaddressed in practice. See Figure 1.

<span id="page-2-0"></span>![](_page_2_Figure_2.jpeg)

Fig. 1. A motivating example.

To address this, we present Tool, a technique for pruning. We evaluate it on two tasks.

In summary, this paper makes the following contributions:

- We conduct an analysis of compute. This finds 40% of the cost in attention.
- We design a pruning method.
- We release a replication package [\\[45\\]](#page-20-7).

The rest of this paper is organized as follows.

## 2 Background

Background text.

# References

[1] A reference.
"""


def test_extract_intro_finds_span_and_hash_variants():
    intro = fis.extract_intro(SAMPLE)
    assert intro.lstrip().startswith("Transformer models")
    assert "Background text" not in intro
    assert "organized as follows" in intro


@pytest.mark.parametrize("heading", [
    "# 1 Introduction", "## 1 Introduction", "#### 1 INTRODUCTION", "# **1 Introduction**",
    "#### <span id=\"page-1-0\"></span>1 Introduction",
])
def test_extract_intro_accepts_every_heading_form(heading):
    md = f"{heading}\n\nBody para.\n\n# **2 Background and Related Work**\n\nOther."
    assert fis.extract_intro(md).strip() == "Body para."


def test_extract_intro_raises_when_missing():
    with pytest.raises(ValueError):
        fis.extract_intro("# 3 Something\n\ntext")


def test_clean_paragraphs_strips_noise_and_merges_page_break():
    paras = fis.clean_paragraphs(fis.extract_intro(SAMPLE))
    joined = "\n".join(paras)
    for noise in ("Contact Information", "licensed under", "Copyright held", "2994-970X",
                  "![](", "<sup>1</sup>", "Fig. 1."):
        assert noise not in joined
    # page-break split merged back into one paragraph
    assert any(p.startswith("However, fine-tuning") and "unaddressed in practice" in p for p in paras)
    # lead-in ending with a colon is merged into the list that follows
    assert any(p.startswith("In summary") and "- We design" in p for p in paras)
    assert paras == [
        "Transformer models [\\[53\\]](#page-21-1) are everywhere. They matter [\\[1\\]](#p), [\\[2\\]](#p).",
        "However, fine-tuning them requires significant compute, and prior work leaves this unaddressed in practice. See Figure 1.",
        "To address this, we present Tool, a technique for pruning. We evaluate it on two tasks.",
        "In summary, this paper makes the following contributions:\n- We conduct an analysis of compute. This finds 40% of the cost in attention.\n- We design a pruning method.\n- We release a replication package [\\[45\\]](#page-20-7).",
        "The rest of this paper is organized as follows.",
    ]


def test_clean_paragraphs_merges_consecutive_list_items_split_by_blank_lines():
    text = "Lead in:\n\n- one\n\n- two\n\n- three\n\nAfter."
    assert fis.clean_paragraphs(text) == ["Lead in:\n- one\n- two\n- three", "After."]


def test_word_count_ignores_link_targets_and_citation_brackets():
    p = "Transformer models [\\[53\\]](#page-21-1) are everywhere."
    assert fis.word_count(p) == 4


def test_count_citations_numeric_groups_and_refs():
    text = "A [\\[53\\]](#p). B [\\[1\\]](#p), [\\[2\\]](#p). C [\\[3,](#p) [4\\]](#p) and [\\[7\\]\\[8\\]](#p)."
    groups, refs = fis.count_citations(text)
    assert refs == 7
    assert groups >= 4


def test_count_citations_author_year():
    text = "Studies [Smith et al. 2020; Doe 2021] show this [Lee and Kim 2019]."
    groups, refs = fis.count_citations(text)
    assert (groups, refs) == (2, 3)


def test_pivot_and_lists_and_flags():
    paras = fis.clean_paragraphs(fis.extract_intro(SAMPLE))
    assert fis.pivot_index(paras) == 3
    c = fis.contribution_list(paras)
    assert c == dict(has=True, items=3, index=4, labelled=True)
    assert fis.rq_numbers("RQ1 and RQ2, then RQ 2 again") == 2
    raw = fis.extract_intro(SAMPLE)
    assert fis.has_figure(raw) is True
    assert fis.has_table(raw) is False
    assert fis.has_roadmap(paras[-1]) is True
    assert fis.has_artifact("\n".join(paras)) is True
    assert fis.tail_has_numbers(paras) is True


def test_skeleton_compresses_runs_and_drops_noise():
    assert fis.skeleton("CCPLLTKR") == "C P L T K R"
    assert fis.skeleton("CXPXX") == "C P"


def test_hand_labels_are_well_formed():
    for key, h in fis.HAND.items():
        assert h["type"] in fis.TYPES, key
        assert h["opener"] in fis.OPENERS, key
        assert h["contrib_first"] in fis.CONTRIB_FIRST, key
        assert set(h["moves"]) <= set(fis.MOVES), key
        assert len(h["moves"]) >= 3, key


def test_coarse_skeleton_maps_blocks_and_collapses():
    assert fis.coarse_skeleton("CPLTDFKIR") == "O L T F K"
    assert fis.coarse_skeleton("CXLTTK") == "O L T K"


def test_order_stats_counts_every_a_before_first_b():
    rows = [dict(paper="a"), dict(paper="b"), dict(paper="c")]
    moves = {"a": "CLTFK", "b": "CLCTK", "c": "PTFK"}
    out = dict(fis.order_stats(rows, moves, pairs=(("C", "L"), ("L", "T"), ("C", "T"))))
    assert out["C context entirely before L limitation of prior work"] == "1/2"
    assert out["L limitation of prior work entirely before T this paper"] == "2/2"
    assert out["C context entirely before T this paper"] == "2/2"


# ---- wording, scope, two-study shape, contribution items

def test_first_sentence_stops_at_first_period_not_et_al_or_number():
    assert fis.first_sentence("Shi et al. [3] proposed foo. Then bar.") == "Shi et al. proposed foo."
    assert fis.first_sentence("Only 0.5 seconds matter. Next.") == "Only 0.5 seconds matter."
    assert fis.first_sentence("**Our Approach.** We propose Z. More.") == "Our Approach."


@pytest.mark.parametrize("sent,form", [
    ("In this paper, we conduct a study.", "in_this_paper"),
    ("In this work, we aim to investigate X.", "in_this_paper"),
    ("To address these shortcomings, we conduct a study.", "to_address_we"),
    ("To effectively address these challenges, we propose Foo.", "to_address_we"),
    ("This paper presents the first study.", "this_paper"),
    ("Our work.", "other"),
])
def test_pivot_form(sent, form):
    assert fis.pivot_form(sent) == form


@pytest.mark.parametrize("sent,form", [
    ("However, we find that existing frameworks do not cover it.", "however"),
    ("Existing methods are guided by reward signals.", "existing_prior"),
    ("Previous work has explored alignment, but there is a gap.", "existing_prior"),
    ("Despite the widespread usage, contributions have never been evaluated.", "despite"),
    ("Shi et al. proposed X.", "other"),
])
def test_gap_form(sent, form):
    assert fis.gap_form(sent) == form


@pytest.mark.parametrize("sent,form", [
    ("We evaluate our method on two tasks.", "we_do"),
    ("To validate these hypotheses, we construct six tasks.", "we_do"),
    ("Our findings reveal distinct patterns.", "results_show"),
    ("Our analysis shows that current models are weak.", "results_show"),
    ("Unlike previous findings, our study reveals a zero-sum trade-off.", "results_show"),
    ("Results.", "other"),
])
def test_findings_form(sent, form):
    assert fis.findings_form(sent) == form


def test_leadin_formula():
    assert fis.LEADIN_FORMULA.search("In summary, this paper makes the following contributions:")
    assert fis.LEADIN_FORMULA.search("Our main contributions are summarized as follows:")
    assert fis.LEADIN_FORMULA.search("The contributions of this paper are summarized below.")
    assert fis.LEADIN_FORMULA.search("Our study reveals significant disparities.") is None


def test_scope_and_practitioner_regexes():
    assert fis.GAP_TURN.search("Regression errors have been widely investigated") is None
    assert fis.GAP_TURN.search("but there is a gap in research")
    assert fis.SCOPE.search("In this paper, we focus on the oracle problem.")
    assert fis.SCOPE.search("a complete account is out of scope")
    assert not fis.SCOPE.search("focusing on the impact of model updates")
    assert fis.PRACTITIONER.search("A survey of 53% of developers")
    assert fis.PRACTITIONER.search("practitioners report")
    assert fis.PRACTITIONER.search("we surveyed the literature") is None   # 'surveyed' is not counted


def test_monotone_blocks():
    assert fis.monotone_blocks("O L T F K") is True
    assert fis.monotone_blocks("L T K") is True
    assert fis.monotone_blocks("O L O T F K") is False
    assert fis.monotone_blocks("O L T F K T K") is False


@pytest.mark.parametrize("item,cat", [
    ("- We propose a failure-based method, PRT.", "propose"),
    ("- **An empirical study.** We conducted a large-scale empirical study.", "study"),
    ("- Novelty: To the best of our knowledge, we present the first large-scale study.", "propose"),
    ("- We reveal that trajectory reduction is promising.", "find"),
    ("- We release our code and data at https://x.", "release"),
    ("- Our replication package is publicly available.", "release"),
    ("- Something without a verb we know.", "other"),
])
def test_item_category(item, cat):
    assert fis.item_category(item) == cat


def test_novelty_claim():
    assert fis.NOVELTY.search(fis._item_text("- To the best of our knowledge, this is the first study."))
    assert fis.NOVELTY.search(fis._item_text("- We present the first systematic study."))
    assert fis.NOVELTY.search(fis._item_text("- We evaluate ten models.")) is None
