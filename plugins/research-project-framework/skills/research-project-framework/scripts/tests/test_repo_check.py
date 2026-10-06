"""Tests for the generated-state half of repo_check.

The dashboard reads derived/repo_state.md and prints whatever it finds there, so a
silent parse failure would show a wrong number rather than an error. These tests
pin the two parsers that can drift: the risk table (hand-written markdown) and the
proposal filenames (v10 must beat v9, which string comparison gets backwards).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import repo_check as rc

ROOT = rc.ROOT

OPEN_ROW = "| 2 | **时间表整体后移**:三项工作未开始 | 九月上旬顺延 | [[Timeline]] 已重排 | v7 时间表 |"
CLOSED_ROW = "| 1 | ~~**示例风险**~~ | ~~示例影响~~ | **关闭(2026-01-02)**:示例原因 | 示例出处 |"
DELETED_ROW = "| 3 | ~~(已删,2026-01-03)~~ | | 示例原因 | |"


def test_parse_risks_classifies_the_three_kinds():
    counts, bad = rc.parse_risks("\n".join([OPEN_ROW, CLOSED_ROW, DELETED_ROW]))
    assert counts == {"open": 1, "closed": 1, "deleted": 1, "total": 3}
    assert bad == []


def test_parse_risks_reports_a_row_it_cannot_split():
    counts, bad = rc.parse_risks("| 9 | 只有两栏 |")
    assert counts["total"] == 1
    assert bad == ["9"]


def test_parse_risks_ignores_the_header_and_separator():
    text = "| # | 风险 | 影响 | 状态 / 对策 | 出处 |\n|---|---|---|---|---|\n" + OPEN_ROW
    counts, bad = rc.parse_risks(text)
    assert counts["total"] == 1 and bad == []


def test_the_real_risk_table_still_parses():
    p = os.path.join(ROOT, "tracking/Risks.md")
    if not os.path.exists(p):
        pytest.skip("the project has no tracking/Risks.md yet")
    with open(p, encoding="utf-8") as f:
        counts, bad = rc.parse_risks(f.read())
    assert bad == []
    assert counts["total"] == counts["open"] + counts["closed"] + counts["deleted"]   # an empty table is fine


def test_latest_proposal_orders_by_number_not_by_string():
    names = ["Research_Proposal_EN_2026-01-01.md", "Research_Proposal_v9_2026-01-02.md",
             "Research_Proposal_v10_2026-01-03.md", "Research_Proposal_v2_2026-01-01.md"]
    assert rc.latest_proposal(names) == ("v10", "Research_Proposal_v10_2026-01-03.md")


def test_latest_proposal_skips_the_undated_english_copy():
    assert rc.latest_proposal(["Research_Proposal_EN_2026-01-01.md"]) == (None, None)


def test_state_page_is_frontmatter_only_and_quotes_values():
    text = rc.state_page({"last_commit": "aa45b6a: Part I: 前沿", "uncommitted": 3})
    assert text.startswith("---\n") and text.rstrip().endswith("---")
    assert '\nlast_commit: "aa45b6a: Part I: 前沿"\n' in text
    assert "\nuncommitted: 3\n" in text


def test_state_page_escapes_a_quote_inside_a_value():
    assert '\\"' in rc.state_page({"subject": 'he said "no"'})


def test_check_risks_flags_an_unparseable_row(tmp_path, monkeypatch):
    d = tmp_path / "tracking"
    d.mkdir()
    (d / "Risks.md").write_text("| 9 | 只有两栏 |\n", encoding="utf-8")
    monkeypatch.setattr(rc, "ROOT", str(tmp_path))
    issues = []
    rc.check_risks(issues)
    assert len(issues) == 1 and "9" in issues[0]


def test_write_state_leaves_the_file_alone_when_nothing_changed(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "ROOT", str(tmp_path))
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))   # a temp dir inside a repo must not see it
    (tmp_path / "derived").mkdir()
    p = tmp_path / "derived" / "repo_state.md"
    rc.write_state()
    first = p.stat().st_mtime_ns
    rc.write_state()
    assert p.stat().st_mtime_ns == first


def test_prose_lines_drops_fenced_code(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "ROOT", str(tmp_path))
    (tmp_path / "a.md").write_text(
        "prose\n```js\nconst x = 1;\n```\nafter\n", encoding="utf-8")
    assert [n for n, _ in rc.prose_lines("a.md")] == [1, 5]


def test_a_wikilink_inside_a_code_block_is_not_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "ROOT", str(tmp_path))
    (tmp_path / "Home.md").write_text(
        '```dataviewjs\nrow("[[" + id + "]]")\n```\n', encoding="utf-8")
    monkeypatch.setattr(rc, "live_files", lambda: ["Home.md"])
    issues = []
    rc.check_wikilinks(issues)
    rc.check_paths(issues)
    assert issues == []


def test_a_wikilink_in_prose_is_still_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "ROOT", str(tmp_path))
    (tmp_path / "Home.md").write_text("见 [[NoSuchCard]]\n", encoding="utf-8")
    monkeypatch.setattr(rc, "live_files", lambda: ["Home.md"])
    issues = []
    rc.check_wikilinks(issues)
    assert len(issues) == 1 and "NoSuchCard" in issues[0]


def test_parse_state_reads_back_what_state_page_wrote():
    fields = {"branch": "main", "last_commit": "abc123 first commit", "uncommitted": 3}
    assert rc.parse_state(rc.state_page(fields)) == {
        "branch": "main", "last_commit": "abc123 first commit", "uncommitted": "3"}


def test_parse_state_survives_a_missing_file():
    assert rc.parse_state("") == {}
