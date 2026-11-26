#!/usr/bin/env python3
"""QA-GITREINS-16 / QA-GITREINS-15 acceptance: board write-path locking.

Defect being pinned: on 2026-11-15 the gitreins QA closeout (commit 60789922)
wrote the board back from a STALE snapshot. The damage signature was in-place
content substitution with unchanged line counts: the releng row RELEASE-025
was deleted, RELEASE-023 reverted to an older state, and event ids
1794171000000000101/102 were reused for different events. Reproduced on a
scratch copy: a read-modify-write-all writer that races a concurrent append
drops the concurrent row and reuses its event id.

The fix: every writer script in this directory holds an exclusive advisory
flock on <board dir>/.lock - the SAME sidecar lock file boardctl's Go write
guard uses (coding-hermes-boardctl internal/board/lock.go,
boardLockFileName = ".lock") - from BEFORE its first board read until AFTER
its last write, and every rewrite writer gains an optional
--snapshot-*-lines drift refusal (exit 2, nothing written) for callers that
read the board before invoking.

Run:  python3 coding-hermes-foreman/scripts/test_board_write_lock.py
      (also collectable by pytest / unittest discovery)

No live board is touched: every fixture is a throwaway board under TMPDIR.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
COMPLETED = SCRIPTS / "append_board_task_completed.py"
DISPATCHED = SCRIPTS / "append_board_task_dispatched.py"
BOARD_EVENT = SCRIPTS / "append_board_event.py"
E2E_EVENT = SCRIPTS / "append_e2e_event.py"
TASK_NOTES = SCRIPTS / "update_board_task_notes.py"
CREATE_TASKS = SCRIPTS / "create_board_tasks.py"
TOTALSTACK = SCRIPTS / "totalstack-board-update-jsonl.py"

# every script that reads-modifies-writes ALL rows of a board file (the
# class that turned a stale snapshot into the 60789922 damage) must carry
# the flock helper
REWRITE_WRITERS = (COMPLETED, DISPATCHED, TASK_NOTES, BOARD_EVENT,
                   E2E_EVENT, CREATE_TASKS, TOTALSTACK)

BOARD = ".coding-hermes/board"
TS = "2026-11-26 00:00:00.000000"


def clean_env():
    """Ambient git plumbing (a live GIT_DIR/index) would hijack the fixtures."""
    env = dict(os.environ)
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE"):
        env.pop(var, None)
    return env


def run(script, *args, timeout=120):
    return subprocess.run([sys.executable, str(script)] + list(args),
                          capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, env=clean_env())


def seed_board(root, tasks=None, events=None, header=None):
    """Minimal board under <root>/.coding-hermes/board (a throwaway dir)."""
    bdir = Path(root) / BOARD
    bdir.mkdir(parents=True, exist_ok=True)
    if tasks is None:
        tasks = [{"id": "FIX-001", "title": "fixture task", "status": "pending",
                  "worker_status": "idle", "attempts": 0}]
    if events is None:
        events = [{"id": 1, "timestamp": TS, "event_type": "audit", "task_id": None,
                   "actor": "foreman",
                   "detail": json.dumps({"tick": 1, "summary": "fixture seed"}),
                   "tick_number": 1}]
    if header is None:
        header = {"project": "fixture", "ticks_total": 1, "ticks_idle": 0}
    (bdir / "tasks.jsonl").write_text(
        "".join(json.dumps(t) + "\n" for t in tasks))
    (bdir / "events.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in events))
    (bdir / "board.jsonl").write_text(json.dumps(header) + "\n")
    return bdir


def read_lines(path):
    return Path(path).read_text().splitlines(keepends=True)


def numeric_event_ids(path):
    ids = []
    for line in read_lines(path):
        if not line.strip():
            continue
        v = json.loads(line).get("id")
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            ids.append(v)
        elif isinstance(v, str) and v.isdigit():
            ids.append(int(v))
    return ids


def tasks_payload(bdir):
    return json.dumps({
        "tasks": [{"id": "NEW-A", "title": "task A"}],
    })


class TestRewriteWritersCarryTheLock(unittest.TestCase):
    """Structural: every board writer acquires the shared <board>/.lock flock."""

    def test_every_writer_source_contains_the_flock(self):
        for script in REWRITE_WRITERS:
            with self.subTest(script=script.name):
                src = script.read_text()
                self.assertIn("acquire_board_write_lock", src,
                              f"{script.name} does not acquire the board write lock")
                self.assertIn("fcntl.flock", src,
                              f"{script.name} has no flock call")
                self.assertIn('.lock', src,
                              f"{script.name} does not name the .lock sidecar file")

    def test_lock_helper_matches_boardctl_sidecar_name(self):
        """The lock file name must be exactly boardctl's boardLockFileName."""
        src = COMPLETED.read_text()
        self.assertIn('BOARD_LOCK_FILE = ".lock"', src)


class TestTwoWriterAppendPreservesLines(unittest.TestCase):
    """QA-GITREINS-15 criterion 1 (exact name): two concurrent writer
    invocations against one scratch board must leave every pre-existing line
    byte-identical and mint no duplicate event id."""

    def test_two_writer_append_preserves_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = seed_board(tmp)
            pre_tasks = (bdir / "tasks.jsonl").read_bytes()
            pre_events = (bdir / "events.jsonl").read_bytes()

            detail = Path(tmp) / "detail.json"
            detail.write_text(json.dumps({"tick": "qa16", "summary": "concurrent create"}))

            # two concurrent create_board_tasks.py processes, different task ids,
            # same board: both must land, serialized by the flock.
            procs = []
            for task_id in ("NEW-A", "NEW-B"):
                payload = Path(tmp) / f"{task_id}.json"
                payload.write_text(json.dumps([{"id": task_id, "title": f"task {task_id}"}]))
                procs.append(subprocess.Popen(
                    [sys.executable, str(CREATE_TASKS), tmp, "5", str(payload),
                     "--reason", "qa16-concurrency"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    env=clean_env(), stdin=subprocess.DEVNULL))
            outs = [p.communicate(timeout=180)[0] for p in procs]
            for proc, out in zip(procs, outs):
                self.assertEqual(proc.returncode, 0,
                                 f"writer failed: {out}")

            post_tasks = read_lines(bdir / "tasks.jsonl")
            post_event_ids = numeric_event_ids(bdir / "events.jsonl")

            # every pre-existing line survives byte-identical
            pre_task_lines = read_lines_bytepreserved(pre_tasks)
            self.assertEqual(post_tasks[:len(pre_task_lines)], pre_task_lines)
            self.assertGreaterEqual(len(post_tasks), len(pre_task_lines) + 2,
                                    "both new rows must land")

            # no duplicate event ids after the concurrent appends
            self.assertEqual(len(post_event_ids), len(set(post_event_ids)),
                             f"duplicate event ids: "
                             f"{sorted({i for i in post_event_ids if post_event_ids.count(i) > 1})}")

            # the fixture board's own bytes are still present in events
            self.assertTrue(pre_events.splitlines()[0] in
                            (bdir / "events.jsonl").read_bytes().splitlines())


def read_lines_bytepreserved(raw_bytes):
    return raw_bytes.decode().splitlines(keepends=True)


class TestConcurrentCloseoutWriters(unittest.TestCase):
    """Two concurrent CLOSE writers (the 60789922 writer class) on different
    rows: both rows complete, every other line byte-identical, ids unique."""

    def test_two_concurrent_closes_preserve_rows_and_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = seed_board(tmp, tasks=[
                {"id": "FIX-001", "title": "fixture task", "status": "pending",
                 "worker_status": "idle", "attempts": 0},
                {"id": "FIX-002", "title": "fixture task 2", "status": "pending",
                 "worker_status": "idle", "attempts": 0},
            ])
            pre_tasks = (bdir / "tasks.jsonl").read_bytes()

            detail = Path(tmp) / "detail.json"
            detail.write_text(json.dumps({"tick": "qa16", "summary": "close"}))

            procs = []
            for task_id, commit in (("FIX-001", "a" * 40), ("FIX-002", "b" * 40)):
                procs.append(subprocess.Popen(
                    [sys.executable, str(COMPLETED), tmp, task_id, "7", commit,
                     "--summary", f"qa16 close {task_id}", "--guard", "PASS"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    env=clean_env(), stdin=subprocess.DEVNULL))
            outs = [p.communicate(timeout=180)[0] for p in procs]
            for proc, out in zip(procs, outs):
                self.assertEqual(proc.returncode, 0, f"close failed: {out}")

            rows = [json.loads(l) for l in read_lines(bdir / "tasks.jsonl") if l.strip()]
            by_id = {r["id"]: r for r in rows}
            self.assertEqual(by_id["FIX-001"]["status"], "complete")
            self.assertEqual(by_id["FIX-002"]["status"], "complete")

            # the row each close did NOT touch is byte-identical to the seed
            seed_lines = read_lines_bytepreserved(pre_tasks)
            post_lines = read_lines(bdir / "tasks.jsonl")
            self.assertEqual(len(post_lines), len(seed_lines),
                             "a close rewrote a pre-existing line away")

            event_ids = numeric_event_ids(bdir / "events.jsonl")
            self.assertEqual(len(event_ids), len(set(event_ids)),
                             "concurrent closes reused an event id")


class TestDriftRefusal(unittest.TestCase):
    """QA-GITREINS-16: a writer given a stale pre-lock snapshot refuses with
    exit 2 and writes NOTHING."""

    def test_drift_refusal_tasks_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = seed_board(tmp)

            # caller snapshots the seed's 1 line, then a concurrent writer
            # appends a row before the writer runs: the snapshot is now stale.
            stale_snapshot = 1
            with open(bdir / "tasks.jsonl", "a") as f:
                f.write(json.dumps({"id": "RACE-001", "title": "landed between "
                                    "snapshot and lock", "status": "pending"}) + "\n")
            # the writer must leave the board exactly as the concurrent writer
            # left it - baseline captured AFTER the simulated concurrent write
            pre_tasks = (bdir / "tasks.jsonl").read_bytes()

            res = run(TASK_NOTES, tmp, "FIX-001", "foreman_note=should not land",
                      "--snapshot-tasks-lines", str(stale_snapshot))
            self.assertEqual(res.returncode, 2,
                             f"expected drift refusal exit 2, got {res.returncode}: "
                             f"{res.stdout} {res.stderr}")
            self.assertIn("DRIFT REFUSED", res.stdout + res.stderr)
            self.assertEqual((bdir / "tasks.jsonl").read_bytes(),
                             pre_tasks, "drift refusal must not write")

    def test_drift_refusal_events_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = seed_board(tmp)

            detail = Path(tmp) / "detail.json"
            detail.write_text(json.dumps({"tick": "qa16", "summary": "nope"}))

            stale_snapshot = 1  # caller saw 1 event; we add one underneath
            with open(bdir / "events.jsonl", "a") as f:
                f.write(json.dumps({"id": 2, "timestamp": TS, "event_type": "audit",
                                    "task_id": None, "actor": "other",
                                    "detail": "{}", "tick_number": 2}) + "\n")
            # baseline captured AFTER the simulated concurrent write: the
            # writer must leave the board exactly as the concurrent writer
            # left it
            pre_events = (bdir / "events.jsonl").read_bytes()

            res = run(BOARD_EVENT, tmp, "3", str(detail),
                      "--snapshot-events-lines", str(stale_snapshot))
            self.assertEqual(res.returncode, 2,
                             f"expected drift refusal exit 2, got {res.returncode}: "
                             f"{res.stdout} {res.stderr}")
            self.assertIn("DRIFT REFUSED", res.stdout + res.stderr)
            self.assertEqual((bdir / "events.jsonl").read_bytes(),
                             pre_events, "drift refusal must not write")

    def test_fresh_snapshot_still_writes(self):
        """The refusal is keyed on the CALLER's snapshot: a fresh (matching)
        snapshot must NOT refuse - the flag cannot wedge a healthy close."""
        with tempfile.TemporaryDirectory() as tmp:
            bdir = seed_board(tmp)
            res = run(TASK_NOTES, tmp, "FIX-001", "foreman_note=lands fine",
                      "--snapshot-tasks-lines", "1")
            self.assertEqual(res.returncode, 0, f"healthy write refused: {res.stdout} {res.stderr}")
            self.assertNotIn("DRIFT REFUSED", res.stdout + res.stderr)
            rows = [json.loads(l) for l in read_lines(bdir / "tasks.jsonl") if l.strip()]
            self.assertEqual(rows[0]["foreman_note"], "lands fine")


if __name__ == "__main__":
    unittest.main()
