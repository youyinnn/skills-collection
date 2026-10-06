"""A watched directory may be nested (work/proposals): files inside it are scanned, files beside it are not."""
import os

import humanizer_scan as h


def test_nested_watch_dir_is_matched(monkeypatch):
    monkeypatch.setattr(h, "WATCH_DIRS", ("work/proposals",))
    assert h.watched(os.path.join(h.ROOT, "work", "proposals", "p.md"))
    assert not h.watched(os.path.join(h.ROOT, "work", "drafts", "p.md"))
    assert not h.watched(os.path.join(h.ROOT, "work", "proposals", "p.txt"))


def test_watch_dirs_match_windows_paths(monkeypatch):
    import ntpath
    import types
    monkeypatch.setattr(h, "os", types.SimpleNamespace(path=ntpath, sep="\\"))
    monkeypatch.setattr(h, "ROOT", r"C:\proj")
    monkeypatch.setattr(h, "WATCH_DIRS", ("work/proposals",))
    assert h.watched(r"C:\proj\work\proposals\p.md")
    assert not h.watched(r"C:\proj\work\drafts\p.md")


def test_quoted_lines_are_skipped(tmp_path):
    f = tmp_path / "reply.md"
    f.write_text("> The authors delve into a pivotal question.\n\nWe delve into it.\n", encoding="utf-8")
    hits = h.scan(str(f))
    assert hits and all(" L3:" in h for h in hits)   # only the author's line is flagged
