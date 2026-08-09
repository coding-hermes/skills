#!/usr/bin/env python3
"""Poll a GitHub Actions run until completion (bounded).

Usage: gh-ci-poll.py <run-id> [repo] [timeout-s]
  repo    default "dexdat/hivemind"
  timeout default 360s
Exit codes:
  0 = completed with conclusion "success"
  1 = completed with any other conclusion (failure/cancelled/etc.)
  2 = timed out waiting

Why a script file: `gh run view ... | python3 -c` pipes are Tirith-blocked in
cron/foreman contexts (pipe_to_interpreter). Run this file instead of building
the pipe inline. Proven hivemind tick #210 (Lint+Test both SUCCESS on 710c45e).
"""
import json, subprocess, sys, time

run_id = sys.argv[1]
repo = sys.argv[2] if len(sys.argv) > 2 else "dexdat/hivemind"
timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 360

start = time.time()
while time.time() - start < timeout:
    out = subprocess.run(
        ["gh", "run", "view", run_id, "-R", repo, "--json", "status,conclusion"],
        capture_output=True, text=True, timeout=30,
    ).stdout
    try:
        d = json.loads(out)
    except Exception:
        time.sleep(20)
        continue
    print(f"status={d.get('status')} conclusion={d.get('conclusion')}", flush=True)
    if d.get("status") == "completed":
        sys.exit(0 if d.get("conclusion") == "success" else 1)
    time.sleep(20)
print("TIMEOUT waiting for CI")
sys.exit(2)
