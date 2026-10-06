"""Check every quoted example sentence in a writing-template file against the Marker markdown.

  python scripts/check_template_quotes.py records/findings/<template>.md

The template's paper table maps a short name to a folder under derived/papers_marker/<VENUE>/.
Every `short name ... "sentence"` cell is located, the sentence and the paper's markdown are both
normalised (span anchors, citation links, bracketed citations, bold markers and stray backslashes
removed, fi / fl / ff ligature letters dropped on both sides, whitespace collapsed) and the
sentence must occur as a substring. Prints each failure with the short name and the first 120
characters, then the tally.
"""
import os
import re
import sys

from config import MARKER_DIR as MARKER  # noqa: E402

TABLE_ROW = re.compile(r"^\| (\S+) \| ([^|]+?) \|", re.M)   # | <paper folder> | <short name> |
QUOTE_MIN = 15


def norm(s):
    s = re.sub(r'<span id="[^"]*"></span>', "", s)
    s = re.sub(r"\[[^\]]*?\\[\[\]][^\]]*?\]\(#[^)]*\)", "", s)   # [\[11,](#page-x) / [70\]](#page-x): citation links, dropped
    s = re.sub(r"\[([^\]]*?)\]\(#[^)]*\)", r"\1", s)            # [2,](#page-x): section or table refs keep the label
    s = re.sub(r"\[\s*\d+(?:\s*[,\u2013\-]\s*\d+)*\s*,?\s*\]", "", s)   # [11, 19] plain citations
    s = s.replace("\\_", "_").replace("\\[", "[").replace("\\]", "]").replace("\\*", "*")
    s = s.replace("**", "").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    for lig in ("ffi", "ffl", "ff", "fi", "fl"):                    # the 2023 ACM markdown drops these ligatures
        s = s.replace(lig, "")
    return re.sub(r"\s+", " ", s).strip()


def quotes(doc, names):
    """[(short name, quoted sentence)] for every `短称 ... "..."` occurrence in the template."""
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    out = []
    for line in doc.splitlines():
        if not line.startswith("|"):
            continue
        for cell in line.split("|"):
            for m in re.finditer(rf'({alt})\s[^"]*?"([^"]{{{QUOTE_MIN},}})"', cell):
                out.append((m.group(1), m.group(2)))
    return out


def check(path):
    doc = open(path, encoding="utf-8").read()
    short = {name.strip(): folder for folder, name in TABLE_ROW.findall(doc)
             if os.path.isdir(os.path.join(MARKER, folder))}   # header rows and other tables are not papers
    texts = {}
    for name, folder in short.items():
        md = os.path.join(MARKER, folder, folder + ".md")
        texts[name] = norm(open(md, encoding="utf-8").read()) if os.path.exists(md) else ""
    ok, fails = 0, []
    for name, q in quotes(doc, short):
        if norm(q) in texts[name]:
            ok += 1
        else:
            fails.append((name, q))
    return ok, fails


if __name__ == "__main__":
    total_ok, total_fail = 0, 0
    for p in sys.argv[1:]:
        ok, fails = check(p)
        for name, q in fails:
            print(f"FAIL {os.path.basename(p)} {name} | {q[:120]}")
        print(f"{os.path.basename(p)}: quotes {ok + len(fails)} ok {ok} fail {len(fails)}")
        total_ok += ok
        total_fail += len(fails)
    sys.exit(1 if total_fail else 0)
