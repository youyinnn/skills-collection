"""Tests for the discussion statistics: which heading is cut (ranking, RQ exclusion, merged and
subsection layouts, hand overrides), the units and their topics and audiences, the scheme, and the
end-to-end row."""
import discussion_stats as ds

MD = """# 1 Introduction

We study saliency maps.

# 3 Results

## 3.1 RQ1: Implications of the first result

Not a discussion section (an RQ title).

# 4 Discussion

We discuss what the findings mean.

## 4.1 Implications

For practitioners: developers should select on both metrics [\\[3\\]](#p).

For researchers: the relation deserves a larger study.

## 4.2 Why the Agents Fall Short

The agents weigh the other columns because the prompt names them.

## 4.3 Threats to Validity

Our datasets may not represent other domains.

# 5 Related Work

# References
"""

MD_MERGED = """# 1 Introduction

Intro.

# 4 Results and Discussion

## 4.1 RQ1

Results. Numbers.

Discussion. Meaning.

# 5 Conclusion

# References
"""

MD_SUB = """# 1 Introduction

Intro.

# 5 Results

## 5.1 RQ1

Numbers.

## 5.2 Implications for Developers and Researchers

First, developers should tune. Second, researchers should replicate.

# 6 Threats to Validity

# References
"""


def test_cut_skips_the_rq_title_and_takes_the_top_level_discussion():
    cut, hs, limit = ds.discussion_heading(MD, "FSE2026_Fixture")
    num, title, level, raw, subs, n_matching, layout = cut
    assert num == (4,) and title == "Discussion" and level == 1 and layout == "section" and n_matching == 1
    assert [s[3] for s in subs] == ["Implications", "Why the Agents Fall Short", "Threats to Validity"]
    assert "Related Work" not in raw


def test_units_topics_audiences_and_scheme():
    row, units = ds.features("FSE2026_Fixture", _write(MD))
    assert row["layout"] == "section" and row["mode"] == "sub" and row["labeled"] == 4   # the Implications subsection splits at its two run-in labels
    assert [u["topic"] for u in units] == ["preamble", "implications", "implications", "explanation", "threats"]
    assert units[1]["label"] == "Implications: For practitioners" and "practitioner" in units[1]["audiences"] and "researcher" in units[2]["audiences"]
    assert row["threats_inside"] is True and row["future_inside"] is False
    assert row["scheme"] == "audience-labels" and row["prev_kind"] == "results" and row["next_kind"] == "related work"
    assert row["m_implication"] >= 1 and row["m_explain"] >= 1


def test_merged_layout_is_flagged():
    row, units = ds.features("FSE2026_Merged", _write(MD_MERGED))
    assert row["layout"] == "merged" and row["title"] == "Results and Discussion"
    assert ds.discussion_text(MD_MERGED, "FSE2026_Merged") is None


def test_subsection_layout_and_ordinal_units():
    row, units = ds.features("FSE2026_Sub", _write(MD_SUB))
    assert row["layout"] == "subsection" and row["parent_kind"] == "results" and row["level"] == 2
    assert row["mode"] in ("ordinal", "whole", "paragraphs")
    assert units[0]["topic"] == "implications" and "developer" not in units[0]["audiences"] and "practitioner" in units[0]["audiences"]


def test_hand_override_picks_the_named_heading():
    md = MD.replace("# 4 Discussion", "# 4 Insights\n\nEarly analysis.\n\n# 6 Discussion")
    ds.HAND["FSE2026_Hand"] = dict(title=r"^Discussion$", why="test")
    try:
        cut, _hs, _limit = ds.discussion_heading(md, "FSE2026_Hand")
        assert cut[0] == (6,) and cut[1] == "Discussion"
    finally:
        del ds.HAND["FSE2026_Hand"]


_TMP = __import__("tempfile").TemporaryDirectory()   # removed when the test run ends


def _write(text, _n=[0]):
    import os
    _n[0] += 1
    path = os.path.join(_TMP.name, f"discussion_fixture_{_n[0]}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path
