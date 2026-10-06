#!/usr/bin/env python3
"""Check the facts about the project that the repository can compute for itself.

Every check targets a hand-written restatement that goes stale: a backticked path to a file that
no longer exists, a [[wikilink]] with no target, a kanban card in a lane its status does not match,
an Obsidian setting that points nowhere, a risk-table row the dashboard cannot read, a file-count
block that no longer matches the disk.

Read-only on hand-written files, so it is safe inside a PostToolUse hook: --fix rewrites the
generated counts block in tracking/File-map.md and nothing else. The one file it always rewrites
is derived/repo_state.md (generated, gitignored), the only way an Obsidian dashboard can see the
git state, the latest proposal and the size of the draft. Project settings live in config.py.

  python scripts/repo_check.py          # prints what does not match; exit 1 if anything
  python scripts/repo_check.py --fix    # also regenerates the counts block
  python scripts/repo_check.py --hook   # hook mode: findings go back as context, exit 0
"""
import json, os, re, subprocess, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Facts the dashboard prints that Obsidian cannot see for itself: git state, the latest
# proposal, the size of the draft.
STATE = "derived/repo_state.md"
from config import (COUNTED, LANES, PAPER_SECTION_DIR, PROPOSAL_DIR, PROPOSAL_PATTERN,  # noqa: E402
                    RISK_CLOSED, RISK_DELETED, TOPDIRS)


def live_files():
    out = ["CLAUDE.md", "Home.md"]
    for pat in ("tracking/**/*.md", "scripts/**/*.py", "derived/**/*.md"):
        out += [os.path.relpath(p, ROOT).replace(os.sep, "/") for p in   # "/" on Windows too
                glob.glob(os.path.join(ROOT, pat), recursive=True)]
    return sorted(set(p for p in out if os.path.exists(os.path.join(ROOT, p))))


def prose_lines(rel):
    """Lines of a file with fenced code blocks left out.

    A path or a wikilink inside a fence is code the dashboard's JS builds, not a
    claim about the repository, and checking it reports the code as a defect.
    """
    fence = False
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if rel.endswith(".md") and line.lstrip().startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            yield n, line


def check_paths(issues):
    """Backticked repo paths in live files must exist on disk."""
    for rel in live_files():
        skip = False
        for n, line in prose_lines(rel):
            if "repo_check:skip-paths" in line:
                skip = "/repo_check" not in line
                continue
            if skip:
                continue
            for m in re.finditer(r"`([A-Za-z0-9_.\-]+/[A-Za-z0-9_./\-]*)`", line):
                path = m.group(1)
                if path.split("/")[0] not in TOPDIRS or "*" in path:
                    continue
                if not os.path.exists(os.path.join(ROOT, path.rstrip("/"))):
                    issues.append(f"{rel}:{n} 引用了不存在的路径 `{path}`")


def check_wikilinks(issues):
    """[[X]] must resolve to some X.md in the vault."""
    names = {os.path.splitext(os.path.basename(p))[0]
             for p in glob.glob(os.path.join(ROOT, "**/*.md"), recursive=True)}
    for rel in live_files():
        if not rel.endswith(".md"):
            continue
        # Converted papers are raw text, not vault prose: a search string such
        # as [[Abstract: "safe"]] inside a paper is content, not a link.
        if rel.startswith("derived/papers_marker/"):
            continue
        for n, line in prose_lines(rel):
            for m in re.finditer(r"\[\[([^\]|#]+)", line):
                target = os.path.basename(m.group(1).strip())
                if target and target not in names:
                    issues.append(f"{rel}:{n} 链接 [[{m.group(1).strip()}]] 找不到对应文件")



def card_status():
    out = {}
    for p in glob.glob(os.path.join(ROOT, "tracking/tasks/*.md")):
        with open(p, encoding="utf-8") as f:
            m = re.search(r"^status:\s*(\S+)", f.read(), re.M)
        out[os.path.splitext(os.path.basename(p))[0]] = m.group(1) if m else None
    return out


def check_board(issues):
    board = os.path.join(ROOT, "tracking/Board.md")
    if not os.path.exists(board):
        return
    cards, seen, lane = card_status(), set(), None
    with open(board, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.startswith("## "):
                lane = line[3:].strip()
            m = re.search(r"\[\[([A-Z]\d+)\]\]", line)
            if not m or lane not in LANES:
                continue
            cid = m.group(1)
            seen.add(cid)
            if cid in cards and cards[cid] not in LANES[lane]:
                issues.append(f"tracking/Board.md:{n} {cid} 在「{lane}」栏,卡片写的是 status: {cards[cid]}")
    for cid in sorted(set(cards) - seen):
        issues.append(f"tracking/Board.md 没有 {cid},卡片存在(status: {cards[cid]})")


def check_obsidian(issues):
    p = os.path.join(ROOT, ".obsidian/daily-notes.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        for key, suffix in (("folder", ""), ("template", ".md")):
            val = cfg.get(key)
            if val and not os.path.exists(os.path.join(ROOT, val + suffix)):
                issues.append(f".obsidian/daily-notes.json 的 {key} 指向不存在的 {val}")
    # A rename silently voids an exclusion: the folder is indexed again with no error.
    p = os.path.join(ROOT, ".obsidian/app.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        for val in cfg.get("userIgnoreFilters", []):
            if not os.path.exists(os.path.join(ROOT, val.rstrip("/"))):
                issues.append(f".obsidian/app.json 的 userIgnoreFilters 排除了不存在的 {val}")


def parse_risks(text):
    """Tally tracking/Risks.md into open / closed / deleted.

    A row is deleted if its risk cell is struck through and says so, closed if the
    countermeasure cell says RISK_CLOSED (config.py), open otherwise. Rows that do not split into the
    table's five cells are returned by number instead of being guessed at.
    """
    counts = {"open": 0, "closed": 0, "deleted": 0, "total": 0}
    bad = []
    for line in text.splitlines():
        line = line.strip()
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        counts["total"] += 1
        if len(cells) != 5:
            bad.append(cells[0])
            continue
        num, risk, _impact, action, _src = cells
        if risk.startswith("~~") and RISK_DELETED in risk:
            counts["deleted"] += 1
        elif RISK_CLOSED in action:
            counts["closed"] += 1
        else:
            counts["open"] += 1
    return counts, bad


def check_risks(issues):
    p = os.path.join(ROOT, "tracking/Risks.md")
    if not os.path.exists(p):
        return
    with open(p, encoding="utf-8") as f:
        _counts, bad = parse_risks(f.read())
    for num in bad:
        issues.append(f"tracking/Risks.md 第 {num} 行不是五栏,dashboard 数不出这条是开是关")


def latest_proposal(names):
    """Highest proposal version by number (PROPOSAL_PATTERN). String order puts v9 above v10."""
    best = (None, None, -1)
    for n in names:
        m = re.search(PROPOSAL_PATTERN, n)
        if m and int(m.group(1)) > best[2]:
            best = (f"v{m.group(1)}", n, int(m.group(1)))
    return best[0], best[1]


def state_page(fields):
    out = ["---"]
    for k, v in fields.items():
        if isinstance(v, int):
            out.append(f"{k}: {v}")
        else:
            out.append('{}: "{}"'.format(k, str(v).replace("\\", "\\\\").replace('"', '\\"')))
    out += ["---", ""]
    return "\n".join(out)


def git(*args):
    try:
        return subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def chars(paths):
    """Non-whitespace characters. Word counts mean nothing for the Chinese half."""
    n = 0
    for p in paths:
        with open(p, encoding="utf-8") as f:
            n += len(re.sub(r"\s", "", f.read()))
    return n


def parse_state(text):
    """Read back the frontmatter this script itself wrote. Values stay strings."""
    out = {}
    for line in text.splitlines():
        m = re.match(r'^([a-z_]+): (?:"(.*)"|(.*))$', line)
        if m:
            out[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    return out


def state_fields():
    f = {}
    porcelain = git("status", "--porcelain", "--untracked-files=all")   # one line per file, not per untracked folder
    # symbolic-ref names the branch even before the first commit; a detached HEAD gets its short hash
    f["branch"] = git("symbolic-ref", "--short", "-q", "HEAD") or git("rev-parse", "--short", "HEAD")
    f["last_commit"] = git("log", "-1", "--format=%h %s")
    f["last_commit_date"] = git("log", "-1", "--format=%ad", "--date=short")
    f["uncommitted"] = len([l for l in porcelain.splitlines() if l.strip()])

    prop_dir = os.path.join(ROOT, PROPOSAL_DIR)
    names = sorted(os.listdir(prop_dir)) if os.path.isdir(prop_dir) else []
    ver, fname = latest_proposal(names)
    f["proposal_version"] = ver or ""
    if fname:
        full = os.path.join(prop_dir, fname)
        f["proposal_file"] = os.path.splitext(fname)[0]
        # the date the version carries, not the last commit that touched the path:
        # a reorganisation that renames the files would otherwise report itself as the date
        m = re.search(r"(\d{4}-\d{2}-\d{2})", fname)
        f["proposal_date"] = m.group(1) if m else ""
        f["proposal_chars"] = chars([full])
    f["draft_chars"] = (chars(sorted(glob.glob(os.path.join(PAPER_SECTION_DIR, "**/*.tex"), recursive=True)))
                        if PAPER_SECTION_DIR else 0)
    f["analysis_files"] = len([p for p in glob.glob(
        os.path.join(ROOT, "derived/analysis/**/*"), recursive=True) if os.path.isfile(p)])

    rp = os.path.join(ROOT, "tracking/Risks.md")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as fh:
            counts, _bad = parse_risks(fh.read())
        for k, v in counts.items():
            f["risks_" + k] = v
    return f


def write_state():
    """Rewrite derived/repo_state.md unless it already says the same thing.

    The narrow exception to this script being read-only: the file is fully derived,
    it lives in the folder where hand edits are declared void, and it is gitignored,
    so rewriting it can neither lose work nor dirty the tree. Every hand-written
    file still waits for --fix.
    """
    want = state_page(state_fields())
    p = os.path.join(ROOT, STATE)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            if f.read() == want:
                return False
    with open(p, "w", encoding="utf-8") as f:
        f.write(want)
    return True


def counts_block():
    lines = ["| 目录 | 文件数 |", "|---|---|"]
    for d in COUNTED:
        full = os.path.join(ROOT, d)
        n = (sum(1 for _, _, fs in os.walk(full) for f in fs
                 if not f.startswith(".") and not f.lower().endswith((".jpeg", ".jpg", ".png")))
             if os.path.isdir(full) else 0)
        lines.append(f"| `{d}/` | {n} |")
    return "\n".join(lines)


def check_counts(issues, fix):
    p = os.path.join(ROOT, "tracking/File-map.md")
    if not os.path.exists(p):
        return
    with open(p, encoding="utf-8") as f:
        t = f.read()
    m = re.search(r"(<!-- repo_check:counts -->\n)(.*?)(<!-- /repo_check:counts -->)", t, re.S)
    if not m:
        issues.append("tracking/File-map.md 里没有 <!-- repo_check:counts --> 标记块")
        return
    want = counts_block() + "\n"
    if m.group(2) == want:
        return
    if fix:
        with open(p, "w", encoding="utf-8") as f:
            f.write(t[:m.start(2)] + want + t[m.end(2):])
        print("已重新生成 tracking/File-map.md 的数量块")
    else:
        issues.append("tracking/File-map.md 的数量块与磁盘不符,跑 `python3 scripts/repo_check.py --fix`")


def main():
    fix = "--fix" in sys.argv
    hook = "--hook" in sys.argv
    issues = []
    try:
        write_state()
    except Exception as e:
        issues.append(f"{STATE} 没能生成:{e}")
    check_paths(issues)
    check_wikilinks(issues)
    check_board(issues)
    check_obsidian(issues)
    check_risks(issues)
    check_counts(issues, fix and not hook)
    if not issues:
        return 0
    if hook:
        # Same convention as humanizer_scan.py: hand the findings back as context
        # and exit 0, so a stale record never reads as a tool failure.
        ctx = ("repo_check 发现记录与磁盘对不上。逐条修好再继续;数量块用 "
               "`python3 scripts/repo_check.py --fix` 重新生成。\n" + "\n".join(issues))
        print(json.dumps({
            "systemMessage": f"repo_check: {len(issues)} 处对不上",
            "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx},
        }, ensure_ascii=False))
        return 0
    print(f"repo_check: {len(issues)} 处对不上")
    for i in issues:
        print("  " + i)
    return 1


if __name__ == "__main__":
    sys.exit(main())
