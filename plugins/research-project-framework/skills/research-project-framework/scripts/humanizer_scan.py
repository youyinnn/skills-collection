#!/usr/bin/env python3
"""PostToolUse hook: scan English project documents for the mechanical tells
listed in the humanizer skill and feed the hits back to Claude as context.

Reads the hook JSON on stdin. For Write/Edit it scans tool_input.file_path;
for Bash it scans every watched .md file modified in the last WINDOW seconds
(Claude often edits files through python heredocs in Bash).

Scope: .md files under the directories in WATCH_DIRS (config.py). Tracking files and
verbatim records of other people stay outside scope on purpose. "highlight" and
"landscape" are not flagged: both occur here in their literal/technical sense. Lines after a "References" heading, lines
inside fenced code blocks and quoted lines (starting with ">") are skipped. Title Case headings are NOT flagged:
many venues use them; drop this exception if the target venue does not.
"""
import json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from config import HUMANIZER_WATCH_DIRS as WATCH_DIRS  # noqa: E402
WINDOW = 90          # seconds; only for Bash-triggered scans
MAX_HITS = 40

AI_WORDS = r"\b(additionally|align(s|ed)? with|crucial|delve|emphasi[sz](e|es|ed|ing)|enduring|enhanc(e|es|ed|ing)|foster(s|ed|ing)?|garner(s|ed)?|interplay|intricate|intricacies|pivotal|showcas(e|es|ed|ing)|tapestry|testament|underscor(e|es|ed|ing)|vibrant|leverag(e|es|ed|ing)|robust|seamless(ly)?|holistic|notably|moreover|furthermore|comprehensive)\b"
RULES = [
    ("em/en dash",        re.compile(r"[—–]|(?<=\S) -- (?=\S)")),
    ("curly quote",       re.compile(r"[“”‘’]")),
    ("emoji",             re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")),
    ("bold",              re.compile(r"\*\*[^*]+\*\*")),
    ("rather than",       re.compile(r"\brather than\b", re.I)),
    ("negative contrast", re.compile(r"\b(not only|not just|not merely)\b|, not \w|,? and not \w|\bnot \w+ but\b", re.I)),
    ("-ing tail",         re.compile(r", (ensuring|reflecting|highlighting|underscoring|emphasizing|contributing|showcasing|fostering|encompassing|demonstrating|allowing|enabling|making|leaving|leading|resulting|providing|offering|creating|signal(l)?ing)\b")),
    ("AI vocabulary",     re.compile(AI_WORDS, re.I)),
    ("copula avoidance",  re.compile(r"\b(serves as|stands as|represents a|marks a|boasts)\b", re.I)),
    ("filler phrase",     re.compile(r"\b(in order to|due to the fact|it is important to note|at this point in time|has the ability to|the real question|at its core|fundamentally)\b", re.I)),
    ("inline-header list", re.compile(r"^\s*[-*] \*\*[^*]+:\*\*")),
    ("signposting",       re.compile(r"\b(let'?s (dive|explore|break)|here'?s what you need to know|without further ado)\b", re.I)),
]

def watched(path):
    if not path or not path.endswith(".md"):
        return False
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace(os.sep, "/")   # WATCH_DIRS use "/" on Windows too
    return not rel.startswith("..") and any(rel == d or rel.startswith(d + "/") for d in WATCH_DIRS)

def scan(path):
    hits = []
    in_code = False
    in_refs = False
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except OSError:
        return hits
    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if re.match(r"^#{1,6}\s.*\bReferences?\b", line):
            in_refs = True
        if in_refs or line.lstrip().startswith(">"):   # quoted text (a reviewer, a participant) is not ours
            continue
        # cited titles are italicized in these documents; do not judge other people's titles
        probe = re.sub(r"\*[^*\n]+\*", lambda m: " " * len(m.group(0)), line) if "**" not in line else line
        for name, rx in RULES:
            for m in rx.finditer(probe):
                s = max(0, m.start() - 40); e = min(len(line), m.end() + 40)
                hits.append(f"{name} L{i}: ...{line[s:e].strip()}...")
    return hits

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    tool = data.get("tool_name", "")
    files = []
    if tool in ("Write", "Edit"):
        p = data.get("tool_input", {}).get("file_path") or data.get("tool_response", {}).get("filePath")
        if watched(p):
            files.append(p)
    elif tool == "Bash":
        now = time.time()
        for d in WATCH_DIRS:
            dp = os.path.join(ROOT, d)
            if not os.path.isdir(dp):
                continue
            for fn in os.listdir(dp):
                fp = os.path.join(dp, fn)
                if fn.endswith(".md") and now - os.path.getmtime(fp) < WINDOW:
                    files.append(fp)
    if not files:
        return
    report = []
    total = 0
    for f in files:
        h = scan(f)
        total += len(h)
        if h:
            report.append(f"{os.path.relpath(f, ROOT)}: {len(h)} hit(s)")
            report.extend("  " + x for x in h[:MAX_HITS])
            if len(h) > MAX_HITS:
                report.append(f"  ... {len(h) - MAX_HITS} more")
    if total == 0:
        return
    ctx = ("humanizer_scan found AI-writing tells in English project documents. "
           "Fix them in the affected passages (report each change to the user with original and new text), "
           "or run the humanizer skill on the file. Title Case headings are intentional; do not change them.\n"
           + "\n".join(report))
    print(json.dumps({
        "systemMessage": f"humanizer_scan: {total} tell(s); see context",
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx},
    }))

if __name__ == "__main__":
    main()
