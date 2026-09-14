#!/usr/bin/env python3
"""
Supporting script for docs/resilience-testing-runbook.md (Phase 4).

Never changes cluster state -- only observes it, via kubectl/psql
subprocess calls. Two subcommands:

    snapshot <name>   capture current state to docs/logs/resilience-<name>.json
    diff <name>       re-check current state against that snapshot

Snapshots live under docs/logs/, gitignored same as the other session
logs -- nothing here is meant to be committed.

A dedicated Python script rather than inline python3 -c blocks in a
bash wrapper: this data (tick counts, pod lists) round-trips through
JSON several times, and building JSON by interpolating one shell
variable into another script's string literal is exactly the kind of
thing that silently breaks the moment a value contains a quote.
Subprocess + json module handles that correctly by construction.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

NAMESPACE = "quantpulse"
SNAPSHOT_DIR = Path("docs/logs")


def pg_scalar(query: str):
    """One psql query against postgres-0, returned as a bare string, or
    None if the query itself failed. -t (tuples only) -A (unaligned)
    strips all of psql's formatting.

    Returning None (not '') on failure matters: a failed query and a
    query that legitimately succeeded with an empty/zero result used to
    both read back as the same falsy value, which is exactly what caused
    a missing FROM clause to silently read back as "no ticks yet"
    instead of a SQL error (found live testing this script the first
    time), and separately caused cmd_diff to print a false "tick count
    went DOWN" alarm whenever psql failed transiently mid-scenario --
    ironically hitting hardest during Scenario 1 (kill Postgres), the
    primary reason this script exists (found live via code review).
    Prints the real error to stderr so a broken query stays visible, but
    still returns None rather than raising -- a resilience check that
    itself crashes on Postgres being briefly unreachable would defeat
    the point of it."""
    result = subprocess.run(
        [
            "kubectl", "exec", "postgres-0", "-n", NAMESPACE, "--",
            "psql", "-U", "quantpulse", "-d", "quantpulse", "-t", "-A", "-c", query,
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"WARNING: query failed ({query!r}): {result.stderr.strip()}", file=sys.stderr)
        return None
    return result.stdout.strip()


def _as_int(value):
    """value is a pg_scalar() result already known to hold a plain
    integer on success (every caller below uses count(*) or
    COALESCE(..., 0), so a successful query is never an empty string) --
    None propagates through as None ("couldn't determine"), never
    silently coerced to 0."""
    return int(value) if value is not None else None


def capture_state() -> dict:
    tick_count = pg_scalar("SELECT count(*) FROM ticks;")
    max_tick_id = pg_scalar("SELECT COALESCE(max(id), 0) FROM ticks;")
    latest_traded_at = pg_scalar("SELECT COALESCE(max(traded_at)::text, '') FROM ticks;")
    alert_count = pg_scalar("SELECT count(*) FROM alerts;")

    pods_raw = subprocess.run(
        ["kubectl", "get", "pods", "-n", NAMESPACE, "-o", "json"],
        capture_output=True, text=True,
    )

    # A transient kubectl/API-server hiccup here used to crash the whole
    # diff with a JSONDecodeError instead of the intended pass/fail
    # summary -- found live via code review, the same class of bug
    # pg_scalar's own docstring above already exists to prevent, just
    # not yet applied to this second subprocess call.
    if pods_raw.returncode != 0:
        print(f"WARNING: kubectl get pods failed: {pods_raw.stderr.strip()}", file=sys.stderr)
        pods = None
    else:
        pods_data = json.loads(pods_raw.stdout)
        pods = []
        for p in pods_data["items"]:
            statuses = p["status"].get("containerStatuses", [])
            ready = all(c["ready"] for c in statuses) if statuses else False
            restarts = sum(c["restartCount"] for c in statuses)
            pods.append({
                "name": p["metadata"]["name"],
                "ready": ready,
                "restarts": restarts,
                "phase": p["status"].get("phase"),
            })

    return {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tick_count": _as_int(tick_count),
        "max_tick_id": _as_int(max_tick_id),
        "latest_traded_at": latest_traded_at,
        "alert_count": _as_int(alert_count),
        "pods": pods,
    }


def cmd_snapshot(name: str):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = SNAPSHOT_DIR / f"resilience-{name}.json"

    print("Capturing current state...")
    state = capture_state()
    outfile.write_text(json.dumps(state, indent=2))

    print(f"Saved to {outfile}")
    print()
    print(json.dumps(state, indent=2))


def cmd_diff(name: str):
    infile = SNAPSHOT_DIR / f"resilience-{name}.json"
    if not infile.exists():
        print(f"No snapshot found at {infile} -- run 'snapshot {name}' first.")
        sys.exit(1)

    before = json.loads(infile.read_text())

    print("Capturing current state for comparison...")
    current = capture_state()

    print()
    print("=== Ticks ===")
    if before["tick_count"] is None or current["tick_count"] is None:
        print("  -> Could not determine tick count on one side (kubectl/psql issue) -- skipping this check rather than risk a false reading.")
    else:
        delta = current["tick_count"] - before["tick_count"]
        print(f"  before: {before['tick_count']} (max id {before['max_tick_id']}, latest {before['latest_traded_at'] or 'none'})")
        print(f"  now:    {current['tick_count']} (max id {current['max_tick_id']}, latest {current['latest_traded_at'] or 'none'})")
        if delta > 0:
            print(f"  -> +{delta} ticks since snapshot -- ingestion is producing data again.")
        elif delta == 0:
            print("  -> NO new ticks since snapshot -- ingestion may still be down, or the market is genuinely quiet (check asset types/hours before assuming failure).")
        else:
            print("  -> WARNING: tick count went DOWN. This should never happen (ticks are never deleted) -- investigate before trusting anything else here.")

    print()
    print("=== Alerts ===")
    before_alerts = before["alert_count"] if before["alert_count"] is not None else "unknown"
    current_alerts = current["alert_count"] if current["alert_count"] is not None else "unknown"
    print(f"  before: {before_alerts}  now: {current_alerts}")

    print()
    print("=== Pods ===")
    if before["pods"] is None or current["pods"] is None:
        print("  -> Could not list pods on one side (kubectl issue) -- skipping this check.")
        return

    before_pods = {p["name"]: p for p in before["pods"]}
    current_pods = {p["name"]: p for p in current["pods"]}

    not_ready = [p for p in current["pods"] if not p["ready"] and p["phase"] != "Succeeded"]
    if not_ready:
        print("  NOT READY (excluding completed Jobs):")
        for p in not_ready:
            print(f"    {p['name']}: phase={p['phase']} restarts={p['restarts']}")
    else:
        print("  All non-Job pods Ready.")

    new_restarts = []
    for name_, cur in current_pods.items():
        prev = before_pods.get(name_)
        if prev and cur["restarts"] > prev["restarts"]:
            new_restarts.append((name_, prev["restarts"], cur["restarts"]))
    if new_restarts:
        print("  Restart count increased since snapshot:")
        for name_, old, new in new_restarts:
            print(f"    {name_}: {old} -> {new}")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("snapshot", "diff"):
        print("Usage:")
        print("  resilience_check.py snapshot <name>   -- capture current state")
        print("  resilience_check.py diff <name>       -- compare current state against a saved snapshot")
        sys.exit(1)

    action, name = sys.argv[1], sys.argv[2]
    if action == "snapshot":
        cmd_snapshot(name)
    else:
        cmd_diff(name)


if __name__ == "__main__":
    main()
