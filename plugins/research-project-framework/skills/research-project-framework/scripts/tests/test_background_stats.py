"""Tests for the background statistics: the cut, the unit split and classes, the relation to
the related-work section and the three-beat rules."""
import background_stats as bg

MD = """# 1 Introduction

We study call graphs and selection. Findings follow.

# 2 Background

Background opens here with a framing sentence about graphs.

## 2.1 Call Graphs

A call graph is defined as a directed graph [\\[1\\]](#p). Formally $s_{i} = f(x)$ holds.

## 2.2 Motivating Example

An example of the problem.

## 2.3 Related Work

Prior work [\\[2\\]](#p). Unlike them, we measure selection.

# 3 Study Design

Design.

# References
"""


def test_cut_units_and_classes():
    num, title, raw, subs = bg.background_section(MD)
    assert (num, title) == (2, "Background")
    units = bg.units_of(raw, subs, title)
    assert [(l, k) for l, k, in [(u[0], u[2]) for u in units]] == [
        ("", "preamble"), ("Call Graphs", "definitional"), ("Motivating Example", "motivation"),
        ("Related Work", "related-work")]
    u = bg.unit_row("p", "empirical", 2, 2, *units[1], intro="we study call graphs and selection")
    assert (u["named_in_intro"], u["def_sentences"], u["formulas"], u["cite_groups"]) == (True, 2, 1, 1)


def test_whole_section_unit_keeps_its_label_class():
    raw = "Just prose, no subsections and no run-in labels.\n"
    assert bg.units_of(raw, [], "Motivating Example")[0][2] == "motivation"
    assert bg.units_of(raw, [], "Preliminaries")[0][2] == "definitional"


def test_relation():
    assert bg.relation(2, "Background and Related Work", dict(section="2", placement="front-combined")) == "merged"
    assert bg.relation(2, "Preliminaries", dict(section="2.3", placement="subsection")) == "rw-subsection"
    assert bg.relation(2, "Background", dict(section="3", placement="front")) == "before-adjacent"
    assert bg.relation(2, "Background", dict(section="7", placement="back")) == "before"
    assert bg.relation(3, "Background", dict(section="2", placement="front")) == "after-adjacent"


def test_beats():
    row = dict(has_background=True, relation="before", units=2, def_units=2, def_units_named_in_intro=2,
               motiv_units=0, rw_units=0)
    rw = dict(section="7", position_sents=2, last_para_positions=True)
    b = bg.beats("CPLTFK", row, rw)
    assert (b["beat1"], b["beat2"], b["beat2_strict"], b["beat3"], b["order"], b["fit"]) == (True,) * 6
    b = bg.beats("CPLTK", row, rw)
    assert (b["beat1"], b["beat1_lenient"], b["fit"], b["first_fail"]) == (False, True, False, "beat1")
    b = bg.beats("CPLTFK", dict(row, relation="after-adjacent"), rw)
    assert (b["order"], b["first_fail"]) == (False, "order")


def test_section_kinds_and_label_words():
    # whole-section class: a motivation word alone is motivation, next to a background word it is not
    assert bg.kind_of_section("Motivating Example") == "motivation"
    assert bg.kind_of_section("Background and Motivation") == "definitional"
    # label words match whole words in the introduction, singular or plural
    assert bg.named_in({"rust"}, "we trust the compiler") is False
    assert bg.named_in({"rust"}, "rust programs") and bg.named_in({"graphs"}, "a call graph") and bg.named_in({"graph"}, "the graphs")
    # a paper without a related-work heading gets a row instead of aborting
    assert bg.relation(2, "Background", None) == "no-rw"
    row = dict(has_background=True, relation="no-rw", units=1, def_units=1, def_units_named_in_intro=1, motiv_units=0, rw_units=0)
    b = bg.beats("CPLTFK", row, None)
    assert (b["beat3"], b["order"], b["fit"], b["first_fail"]) == (False, False, False, "beat3")
