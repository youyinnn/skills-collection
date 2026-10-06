"""Tests for the related-work statistics: the cut (own section, combined section, 2.x
subsection, hash and bold headings), the subsection split and the sentence classes."""
import relwork_stats as frs

OWN = """# 1 Introduction

Intro text.

# 7 Related Work

## 7.1 Topic A

Prior work A [\\[1\\]](#p). Unlike them, we measure cost.

**7.2 Topic B**

Prior work B [\\[2,](#p) [3\\]](#p). To the best of our knowledge no prior work does this.

# 8 Conclusion

Done.

# References
"""

SUB = """# 1 Introduction

Intro.

# 2 Preliminaries

## 2.1 Setting

Setting text.

## 2.3 Related Work

Closest is X [\\[4\\]](#p). Our work differs in the object.

# 3 Experimental Setup

Setup.

# References
"""


def test_own_section_cut_and_split():
    num, title, raw, nxt, prev, n_top = frs.extract_relwork(OWN)
    assert (num, title, nxt, prev, n_top) == ((7,), "Related Work", "Conclusion", "Introduction", 3)
    parts = frs.split_subsections(raw, num)
    assert [t for t, _ in parts] == ["Topic A", "Topic B"]


def test_subsection_cut_ends_at_next_top_level():
    num, title, raw, nxt, prev, n_top = frs.extract_relwork(SUB)
    assert (num, title, nxt, prev) == ((2, 3), "Related Work", "Experimental Setup", "Setting")
    assert "Closest is X" in raw and "Setup." not in raw


def test_combined_heading_matches():
    assert frs.RW.match("Background and Related Work")
    assert frs.RW.match("BACKGROUND & RELATED WORKS")
    assert not frs.RW.match("Background and Motivation")


def test_sentence_classes():
    assert frs.POSITION.search("Unlike them, we measure cost.")
    assert frs.NOVELTY.search("To the best of our knowledge no prior work does this.")
    assert frs.SEARCH.search("We searched Google Scholar and DBLP.")
    assert not frs.SEARCH.search("Code search tools are popular.")
    assert frs.count_sentences(["Prior work A. Unlike them, we measure cost."], frs.POSITION) == 1
