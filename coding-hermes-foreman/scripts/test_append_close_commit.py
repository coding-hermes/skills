#!/usr/bin/env python3
"""DF-CRIER-510 acceptance: the board close path must STAGE the files it writes.

Defect being pinned: crier commit be35c5a7 (2026-11-19) closed DF-CRIER-509 in
.coding-hermes/board/tasks.jsonl while event id 1795041048590000012 sat UNCOMMITTED
in the working tree - every `git show main:<board>` reader saw a closed row with no
completion event. The close scripts wrote the files and left the commit to a human
instruction, so callers under-staged.

Run:  python3 coding-hermes-foreman/scripts/test_append_close_commit.py
      (also collectable by pytest / unittest discovery)

No live board is touched: every fixture is a throwaway git repo under TMPDIR.
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

BOARD = ".coding-hermes/board"
TS = "2026-11-20 00:00:00.000000"


def clean_env():
    """Ambient git plumbing (a live GIT_DIR/index) would hijack the fixtures."""
    env = dict(os.environ)
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE"):
        env.pop(var, None)
    return env


def git(repo, *args, check=True):
    res = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True,
                         text=True, stdin=subprocess.DEVNULL, env=clean_env())
    if check and res.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed ({res.returncode}): "
                             f"{res.stderr.strip() or res.stdout.strip()}")
    return res


def seed_board(repo):
    """Minimal board: one prior event, one pending row, one header object."""
    bdir = Path(repo) / BOARD
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "events.jsonl").write_text(json.dumps({
        "id": 1, "timestamp": TS, "event_type": "audit", "task_id": None,
        "actor": "foreman",
        "detail": json.dumps({"tick": 1, "summary": "fixture seed"}),
        "tick_number": 1,
    }) + "\n")
    (bdir / "tasks.jsonl").write_text(json.dumps({
        "id": "FIX-001", "title": "fixture task", "status": "pending",
        "worker_status": "idle", "attempts": 0,
    }) + "\n")
    (bdir / "board.jsonl").write_text(json.dumps({
        "project": "fixture", "ticks_total": 1, "ticks_idle": 0,
        "last_tick": TS, "last_commit": "", "updated_at": TS,
    }) + "\n")


def make_repo(committed=True):
    """Throwaway repo whose board sits at the git root."""
    repo = tempfile.mkdtemp(prefix="df-crier-510-")
    if committed:
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "fixture@board.test")
        git(repo, "config", "user.name", "Board Fixture")
        seed_board(repo)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "fixture: seed board")
    else:
        seed_board(repo)
    return repo


def make_nested_repo():
    """Board inside <root>/proj — repo root ABOVE the workdir (parent-repo case)."""
    root = tempfile.mkdtemp(prefix="df-crier-510-nested-")
    git(root, "init", "-q")
    git(root, "config", "user.email", "fixture@board.test")
    git(root, "config", "user.name", "Board Fixture")
    workdir = Path(root) / "proj"
    seed_board(workdir)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture: seed nested board")
    return root, str(workdir)


def run_script(*args):
    return subprocess.run([sys.executable] + [str(a) for a in args], capture_output=True,
                          text=True, stdin=subprocess.DEVNULL, env=clean_env())


def porcelain(repo, sub=BOARD):
    out = git(repo, "status", "--porcelain", "--", sub).stdout
    return [line for line in out.splitlines() if line.strip()]


def staged_paths(repo):
    out = git(repo, "diff", "--cached", "--name-only").stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def unstaged_paths(repo):
    out = git(repo, "diff", "--name-only").stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


class StageAfterWriteTests(unittest.TestCase):

    def assert_all_lines_staged(self, repo):
        """Every porcelain line must be index-side ('M ' / 'A '), never ' M'/'??'."""
        lines = porcelain(repo)
        self.assertTrue(lines, "expected staged board changes, git status was clean")
        for line in lines:
            self.assertNotIn(line[:2], (" M", " D", "??", " A"),
                             f"board file left UNSTAGED: {line!r}")
            self.assertIn(line[0], "MADRTC", f"unexpected porcelain line: {line!r}")
            self.assertEqual(line[1], " ", f"worktree-side change still pending: {line!r}")

    # ---- the reported defect: completion close -------------------------------------

    def test_completion_without_commit_flag_stages_all_three_board_files(self):
        repo = make_repo()
        res = run_script(COMPLETED, repo, "FIX-001", "2", "abc1234",
                         "--summary", "tick 2 - FIX-001 complete (abc1234, +10/-2).")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("OK: staged", res.stdout)

        self.assert_all_lines_staged(repo)
        staged = staged_paths(repo)
        for name in ("events.jsonl", "tasks.jsonl", "board.jsonl"):
            self.assertIn(f"{BOARD}/{name}", staged, f"{name} was not staged")

        # the STAGED blob must carry the completion event, not just the row flip
        staged_events = git(repo, "show", f":{BOARD}/events.jsonl").stdout
        staged_rows = [json.loads(l) for l in staged_events.splitlines() if l.strip()]
        self.assertEqual([e["id"] for e in staged_rows], [1, 2, 3])
        self.assertEqual(staged_rows[-2]["event_type"], "task_completed")
        self.assertEqual(staged_rows[-2]["task_id"], "FIX-001")
        self.assertEqual(staged_rows[-1]["event_type"], "audit")

        staged_tasks = [json.loads(l) for l in
                        git(repo, "show", f":{BOARD}/tasks.jsonl").stdout.splitlines() if l.strip()]
        self.assertEqual(staged_tasks[0]["status"], "complete")

        # nothing committed yet - the flag is opt-in
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").stdout.strip(), "1")

    def test_completion_with_commit_flag_commits_events_and_tasks_together(self):
        repo = make_repo()
        res = run_script(COMPLETED, repo, "FIX-001", "2", "abc1234",
                         "--summary", "tick 2 - FIX-001 complete (abc1234, +10/-2).",
                         "--commit", "test close")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("OK: committed", res.stdout)

        self.assertEqual(porcelain(repo), [], "board dir must be clean after --commit")
        self.assertEqual(git(repo, "rev-list", "--count", "HEAD").stdout.strip(), "2",
                         "exactly one board commit expected")

        log = git(repo, "log", "-1", "--name-only", "--format=%s").stdout.splitlines()
        self.assertEqual(log[0], "test close")
        committed = {l.strip() for l in log[1:] if l.strip()}
        for name in ("events.jsonl", "tasks.jsonl", "board.jsonl"):
            self.assertIn(f"{BOARD}/{name}", committed,
                          f"--commit did not include {name}: {sorted(committed)}")

        # the commit really carries the completion event (the be35c5a7 failure mode)
        committed_events = git(repo, "show", "HEAD:" + f"{BOARD}/events.jsonl").stdout
        ids = [json.loads(l)["id"] for l in committed_events.splitlines() if l.strip()]
        self.assertEqual(ids, [1, 2, 3])

    def test_non_git_dir_skips_staging_with_notice_and_exit_zero(self):
        repo = make_repo(committed=False)
        res = run_script(COMPLETED, repo, "FIX-001", "2", "abc1234",
                         "--summary", "tick 2 - FIX-001 complete (abc1234, +10/-2).",
                         "--commit", "test close")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("NOTICE:", res.stdout)
        self.assertIn("NOT staged", res.stdout)
        lines = (Path(repo) / BOARD / "events.jsonl").read_text().splitlines()
        self.assertEqual(len([l for l in lines if l.strip()]), 3, "writes must still land")

    # ---- same write-then-hope class: the sibling board writers ---------------------

    def test_dispatched_event_is_staged(self):
        repo = make_repo()
        res = run_script(DISPATCHED, repo, "FIX-001", "2", "glm-5.2", "zai-glm", "4242")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assert_all_lines_staged(repo)
        self.assertEqual(staged_paths(repo),
                         {f"{BOARD}/events.jsonl", f"{BOARD}/tasks.jsonl"})

    def test_board_append_event_is_staged(self):
        repo = make_repo()
        detail = Path(repo) / "detail.json"
        detail.write_text(json.dumps({"tick": 2, "summary": "fixture audit"}))
        res = run_script(BOARD_EVENT, repo, "2", str(detail), "--set", "ticks_idle=0")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assert_all_lines_staged(repo)
        self.assertEqual(staged_paths(repo),
                         {f"{BOARD}/events.jsonl", f"{BOARD}/board.jsonl"})

    def test_e2e_event_is_staged(self):
        repo = make_repo()
        detail = Path(repo) / "detail.json"
        detail.write_text(json.dumps({"tick": 2, "summary": "fixture e2e"}))
        res = run_script(E2E_EVENT, repo, "2", str(detail), "E2E-001")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assert_all_lines_staged(repo)
        self.assertEqual(staged_paths(repo), {f"{BOARD}/events.jsonl"})

    def test_task_notes_update_is_staged(self):
        repo = make_repo()
        res = run_script(TASK_NOTES, repo, "FIX-001", "foreman_note=fixture note")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assert_all_lines_staged(repo)
        self.assertEqual(staged_paths(repo), {f"{BOARD}/tasks.jsonl"})

    def test_created_tasks_and_their_events_are_staged_together(self):
        repo = make_repo()
        tasks = Path(repo) / "new_tasks.json"
        tasks.write_text(json.dumps([{"id": "FIX-002", "title": "second fixture task",
                                      "priority": 3, "complexity": "low"}]))
        res = run_script(CREATE_TASKS, repo, "2", str(tasks))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assert_all_lines_staged(repo)
        self.assertEqual(staged_paths(repo),
                         {f"{BOARD}/events.jsonl", f"{BOARD}/tasks.jsonl"},
                         "a created row without its task_created event is the be35c5a7 bug")
        ids = [json.loads(l)["id"] for l in
               git(repo, "show", f":{BOARD}/events.jsonl").stdout.splitlines() if l.strip()]
        self.assertEqual(ids, [1, 2])

    def test_task_notes_missing_row_writes_nothing(self):
        repo = make_repo()
        res = run_script(TASK_NOTES, repo, "NOPE-999", "foreman_note=x")
        self.assertEqual(res.returncode, 1)
        self.assertIn("not found", res.stdout)
        self.assertEqual(porcelain(repo), [])
        self.assertEqual(unstaged_paths(repo), set())

    # ---- board nested under a parent git root (cwd != toplevel) --------------------

    def test_commit_works_when_repo_root_is_above_the_workdir(self):
        root, workdir = make_nested_repo()
        rel = "proj/" + BOARD
        res = run_script(COMPLETED, workdir, "FIX-001", "2", "abc1234",
                         "--summary", "tick 2 - FIX-001 complete (abc1234, +10/-2).",
                         "--commit", "test close")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(porcelain(root, sub=rel), [], "board dir must be clean after --commit")
        committed = {l.strip() for l in
                     git(root, "log", "-1", "--name-only", "--format=").stdout.splitlines() if l.strip()}
        self.assertEqual(committed, {f"{rel}/events.jsonl", f"{rel}/tasks.jsonl",
                                     f"{rel}/board.jsonl"},
                         "pathspec must resolve relative to the board dir, not the git root")


if __name__ == "__main__":
    unittest.main(verbosity=2)
