r"""Settings that change from project to project. Every script in this folder reads them from here.

Fill this file once when the framework is copied into a new project. Apart from this file, the scripts
need edits only when the target venue changes: the venue-specific cutting rules of the sample
measurement (*_stats.py, see the writing workflow, section 1 step 2). Paths are relative to the
project root (the folder above scripts/) unless absolute. On Windows write absolute paths with forward
slashes ("C:/Users/...") or as raw strings (r"C:\Users\..."); a plain "C:\Users" is a syntax error.
"""
import os
import sys

# Windows: print UTF-8 even when the output goes to a pipe (the default code page cannot encode Chinese).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- venue sample (the *_stats.py scripts, by_type.py, voice_stats.py, check_template_quotes.py)
VENUE = ""   # folder name of the sample under inputs/papers/ and derived/papers_marker/, e.g. "ICSE"
MARKER_DIR = os.path.join(ROOT, "derived/papers_marker", VENUE)
PATTERNS_OUT = os.path.join(ROOT, "derived/analysis/writing_patterns")
# One row per sample paper: column `paper` (folder name, or a unique prefix of the title part after
# the first underscore) and column `group` (the paper-type group from the codebook).
LABELS = os.path.join(ROOT, "records/protocols/paper_type_labels.csv")
GROUP_ORDER = []   # column order of the groups in the reports; empty = order of first appearance in LABELS

# ---- repo_check.py (runs after every edit through the hook in .claude/settings.json)
TOPDIRS = {"records", "inputs", "work", "derived", "tracking", "archive", "scripts"}
COUNTED = ["records/log", "records/protocols", "records/findings", "records/plans",
           "work/proposals", "inputs/papers", "derived/papers_marker", "tracking/tasks"]
PAPER_SECTION_DIR = ""   # absolute path of the paper repo's section/ folder; counts the draft size
PROPOSAL_DIR = "work/proposals"
PROPOSAL_PATTERN = r"Proposal_v(\d+)_"   # file names carry the version number and a YYYY-MM-DD date

# Fixed words the checks match in hand-written files; the same lane names must be used in
# tracking/Board.md and in the LANE table of Home.md (see references/glossary-zh-en.md of skill research-project-framework for the English set).
LANES = {"待办": {"todo"}, "进行中": {"doing"}, "阻塞 / 暂缓": {"blocked", "paused"},
         "取消": {"cancelled"}, "完成": {"done"}}   # kanban lane title -> card statuses it may hold
RISK_CLOSED = "关闭"    # a risk row whose countermeasure cell contains this word counts as closed
RISK_DELETED = "已删"   # a struck-through risk cell containing this word counts as deleted

# ---- humanizer_scan.py (same hook)
HUMANIZER_WATCH_DIRS = ("work/proposals",)   # never put verbatim records of other people here

# ---- agent_runs_ledger.py
AGENT_RUNS_DIR = ""   # absolute path of the folder holding one JSONL log per LLM-call run


def need(value, name):
    """Stop with a plain message when a setting a script depends on is still empty."""
    if not value:
        raise SystemExit(f"fill {name} in scripts/config.py first")
    return value
