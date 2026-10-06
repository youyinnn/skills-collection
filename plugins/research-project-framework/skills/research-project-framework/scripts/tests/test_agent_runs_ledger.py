"""The ledger's numbers come only from the log: calls, requests (earlier attempts included), cost, tokens, wall time."""
import json

import agent_runs_ledger as a


def test_row_counts_earlier_attempts_as_requests_and_cost(tmp_path):
    log = tmp_path / "run1.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in [
        {"model": "m1", "at": "2026-01-01T10:00:00", "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.01}},
        {"model": "m1", "at": "2026-01-01T10:06:00", "usage": {"prompt_tokens": 50, "completion_tokens": 10, "cost": 0.005},
         "first_attempt": {"usage": {"prompt_tokens": 50, "completion_tokens": 5, "cost": 0.002}}},
    ]) + "\n")
    r = a.row(log)
    assert (r["calls"], r["requests"], r["tok_in"], r["tok_out"]) == (2, 3, 200, 35)
    assert abs(r["cost"] - 0.017) < 1e-9 and abs(r["wall_min"] - 6) < 1e-9
    assert r["purpose"] == "(未标注)"
