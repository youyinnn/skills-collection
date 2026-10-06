"""Ledger of LLM-call runs: one row per JSONL log, numbers computed from the log, purpose and status
from the NOTES table below (the only hand-kept part).

Each line of a log is the record of one call, with at least
  model        the model id
  at           ISO timestamp of the call
  usage        the provider's usage object (prompt_tokens, completion_tokens, cost, and optionally
               completion_tokens_details.reasoning_tokens)
and optionally
  answered_provider   the host that answered
  first_attempt       the record of an earlier attempt of the same call (truncated, malformed), which
                      counts as a request and as cost
A <log>.batches.json next to a log (batch API) supplies the cost when the records carry none.

  python scripts/agent_runs_ledger.py   # writes tracking/Agent-runs.md
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

from config import AGENT_RUNS_DIR, ROOT, need

OUT = Path(ROOT) / "tracking" / "Agent-runs.md"

# file stem -> (purpose, status). Add a line in the same turn a new log appears; numbers are never typed here.
NOTES = {}


def row(path):
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    att = rows + [r["first_attempt"] for r in rows if r.get("first_attempt")]
    u = lambda a, k: ((a.get("usage") or {}).get(k) or 0)
    batches = path.with_suffix(".batches.json")
    batch_cost = (sum(((b.get("usage") or {}).get("cost") or 0) for b in json.loads(batches.read_text(encoding="utf-8"))["batches"])
                  if batches.exists() else 0)
    t = sorted(r["at"] for r in rows if r.get("at"))
    wall = (datetime.fromisoformat(t[-1]) - datetime.fromisoformat(t[0])).total_seconds() / 60 if t else 0
    tracked = subprocess.run(["git", "-C", str(path.parent), "ls-files", "--error-unmatch", path.name],
                             capture_output=True).returncode == 0
    purpose, status = NOTES.get(path.stem, ("(未标注)", "(未标注)"))
    return {"file": path.name, "model": rows[0].get("model") if rows else "",
            "provider": ",".join(sorted({str(r.get("answered_provider")) for r in rows})),
            "calls": len(rows), "requests": len(att), "cost": sum(u(a, "cost") for a in att) or batch_cost,
            "tok_in": sum(u(a, "prompt_tokens") for a in att), "tok_out": sum(u(a, "completion_tokens") for a in att),
            "reasoning_tok": sum((((a.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
                                 for a in att),
            "start": t[0][5:16].replace("T", " ") if t else "", "wall_min": wall, "first": t[0] if t else "",
            "tracked": "是" if tracked else "否", "purpose": purpose, "status": status}


def main():
    runs = Path(need(AGENT_RUNS_DIR, "AGENT_RUNS_DIR"))
    rows = sorted((row(p) for p in runs.glob("*.jsonl")), key=lambda r: r["first"])
    L = [f"# LLM 调用跑过什么(由 `scripts/agent_runs_ledger.py` 从 `{runs}` 生成,不要手改)\n",
         f"生成时间 {datetime.now():%Y-%m-%d %H:%M}。每行一份日志;调用数、请求数(含重发的第一次)、费用、token、时段都从日志算;"
         f"用途与状态是脚本里 NOTES 表的手写标注。合计 {sum(r['requests'] for r in rows)} 次请求、{sum(r['cost'] for r in rows):.2f} 美元。\n",
         "| 开始 | 用途 | 状态 | 模型 | 提供方 | 调用 | 请求 | 费用 $ | 输入 tok | 输出 tok(推理) | 墙钟 min | 入库 | 日志 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['start']} | {r['purpose']} | {r['status']} | {r['model']} | {r['provider']} | {r['calls']} | {r['requests']} | "
                 f"{r['cost']:.4f} | {r['tok_in']:,} | {r['tok_out']:,} ({r['reasoning_tok']:,}) | {r['wall_min']:.1f} | {r['tracked']} | `{r['file']}` |")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(rows)} runs")


if __name__ == "__main__":
    main()
