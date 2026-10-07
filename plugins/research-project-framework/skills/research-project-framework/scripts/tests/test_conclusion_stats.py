"""Tests for the conclusion statistics: the last Conclusion-like heading is cut, and a cut that
runs into an unheaded reference list stops there."""
import conclusion_stats as cs

MD = """# 1 Introduction

We study call graphs.

# 5 Summary of Findings

Not the conclusion: a later heading also matches.

# 6 Conclusion and Future Work

In this paper, we study model selection. We find that the rule recovers most of the difference. In future work, we will test more agents.

- [1] A. Author. 2020. A cited paper.
"""


def test_cut_takes_last_match_and_stops_at_reference_list():
    title, prev, nxt, raw = cs.conclusion_cut(MD)
    assert title == "Conclusion and Future Work"
    assert prev == "Summary of Findings" and nxt == ""
    assert "In future work" in raw and "A cited paper" not in raw


def test_no_conclusion():
    assert cs.conclusion_cut("# 1 Introduction\n\nText.\n") is None
