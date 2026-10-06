"""Tests for the template quote checker: the normaliser must drop citation links but keep
section-reference labels, and tolerate the ligature letters the 2023 ACM markdown lost."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import check_template_quotes as ctq


def test_norm_drops_citation_links_keeps_section_refs():
    md = 'Prior research [\\[11,](#page-11-0) [70\\]](#page-12-1) shows X. In Section [2,](#page-2-0) we discuss it.'
    assert ctq.norm(md) == "Prior research shows X. In Section 2, we discuss it."


def test_norm_drops_plain_citations_and_bold():
    assert ctq.norm("As shown [11, 19] in **bold** text") == "As shown in bold text"


def test_norm_ligature_tolerance_matches_both_sides():
    assert ctq.norm("we are the first to find differences") == ctq.norm("we are the rst to nd dierences")


def test_quotes_extracts_short_name_and_sentence_from_table_cells():
    doc = '| 槽 | 例句 |\n|---|---|\n| C | Foo 第 1 段:"This is a quoted example sentence"。Bar 2.1:"Another quoted example here" |\n'
    assert ctq.quotes(doc, ["Foo", "Bar"]) == [("Foo", "This is a quoted example sentence"), ("Bar", "Another quoted example here")]
