#!/usr/bin/env python3
"""DF-CRIER-510 acceptance: the board close path must STAGE the files it writes.

Defect being pinned: crier commit be35c5a7 (2026-11-19) closed DF-CRIER-509 in
.coding-hermes/board/tasks.jsonl while event id 1795041048590000012 sat UNCOMMITTED
in the working tree - every `git show main:<board>` reader saw a closed row with no
completion event. The close scripts wrote the files and left the commit to a human
instruction, so callers under-staged.

DF-CRIER-511 adds the second half: the real crier events.jsonl carries MIXED id
shapes (ints, string ids, null ids), and the close script's bare
`max(e["id"] for e in events)` raised TypeError before writing a single event, so
every fleet closeout died. The next id must come from the numeric candidates only.

DF-CRIER-512 is the same defect in the DISPATCH writer
(append_board_task_dispatched.py): every dispatch append died on the mixed crier
board before its event line was written.

Run:  python3 coding-hermes-foreman/scripts/test_append_close_commit.py
      (also collectable by pytest / unittest discovery)

No live board is touched: every fixture is a throwaway git repo under TMPDIR.
"""
import json
import os
import py_compile
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


def seed_board(repo, events=None):
    """Minimal board: prior events (default one audit event), one pending row, one header."""
    bdir = Path(repo) / BOARD
    bdir.mkdir(parents=True, exist_ok=True)
    if events is None:
        events = [{
            "id": 1, "timestamp": TS, "event_type": "audit", "task_id": None,
            "actor": "foreman",
            "detail": json.dumps({"tick": 1, "summary": "fixture seed"}),
            "tick_number": 1,
        }]
    (bdir / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    (bdir / "tasks.jsonl").write_text(json.dumps({
        "id": "FIX-001", "title": "fixture task", "status": "pending",
        "worker_status": "idle", "attempts": 0,
    }) + "\n")
    (bdir / "board.jsonl").write_text(json.dumps({
        "project": "fixture", "ticks_total": 1, "ticks_idle": 0,
        "last_tick": TS, "last_commit": "", "updated_at": TS,
    }) + "\n")


def mixed_events(event_ids):
    """Event rows carrying those exact id shapes, in board order (DF-CRIER-511)."""
    return [{
        "id": eid, "timestamp": TS, "event_type": "audit", "task_id": None,
        "actor": "foreman",
        "detail": json.dumps({"tick": idx + 1, "summary": f"fixture seed id={eid!r}"}),
        "tick_number": idx + 1,
    } for idx, eid in enumerate(event_ids)]


def make_repo(committed=True, events=None):
    """Throwaway repo whose board sits at the git root."""
    repo = tempfile.mkdtemp(prefix="df-crier-510-")
    if committed:
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "fixture@board.test")
        git(repo, "config", "user.name", "Board Fixture")
        seed_board(repo, events)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "fixture: seed board")
    else:
        seed_board(repo, events)
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


def load_script_module(name, path):
    """Import a sibling script by path (they are entry points, not packages)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


class MixedEventIdTests(unittest.TestCase):
    """DF-CRIER-511: the next event id comes from the NUMERIC ids only.

    The real crier events.jsonl mixes int ids with string ids and null ids, so the
    bare `max(e["id"] ...)` died with TypeError before any event was written.
    """

    def assert_compiles(self, script):
        """py_compile clean, emitted into TMPDIR so the repo tree stays clean."""
        with tempfile.TemporaryDirectory(prefix="df-crier-511-pyc-") as tmp:
            try:
                py_compile.compile(str(script), cfile=os.path.join(tmp, "out.pyc"),
                                   doraise=True)
            except py_compile.PyCompileError as exc:
                self.fail(f"{script.name} does not compile: {exc}")

    def close(self, repo):
        return run_script(COMPLETED, repo, "FIX-001", "2", "abc1234",
                          "--summary", "tick 2 - FIX-001 complete (abc1234, +10/-2).")

    def test_mixed_int_str_null_ids_are_skipped_and_appended_ids_are_ints(self):
        # 4 (int) / "evt-3" (non-numeric str) / None / "9" (pure-digit str)
        repo = make_repo(events=mixed_events([4, "evt-3", None, "9"]))
        bdir = Path(repo) / BOARD
        seeded = (bdir / "events.jsonl").read_text()

        res = self.close(repo)
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertNotIn("TypeError", res.stderr)
        self.assertIn("OK: events [10,11]", res.stdout, "max numeric is 9 -> 10, 11")

        text = (bdir / "events.jsonl").read_text()
        self.assertTrue(text.startswith(seeded), "existing event bytes must be preserved")
        rows = [json.loads(l) for l in text.splitlines() if l.strip()]
        self.assertEqual(len(rows), 6, "four seeded events + two appended")

        appended = rows[-2:]
        for row, expected in zip(appended, (10, 11)):
            self.assertIsInstance(row["id"], int)
            self.assertNotIsInstance(row["id"], bool)
            self.assertEqual(row["id"], expected)
        self.assertEqual([r["event_type"] for r in appended], ["task_completed", "audit"])
        self.assertEqual(appended[0]["task_id"], "FIX-001")

        # untouched neighbours keep their exact original shapes
        self.assertEqual([r["id"] for r in rows[:4]], [4, "evt-3", None, "9"])

        tasks = [json.loads(l) for l in (bdir / "tasks.jsonl").read_text().splitlines() if l.strip()]
        self.assertEqual(tasks[0]["status"], "complete")
        self.assertEqual(tasks[0]["worker_status"], "complete")
        self.assertEqual(tasks[0]["commit_hash"], "abc1234")

        self.assert_compiles(COMPLETED)

    def test_board_without_any_numeric_id_starts_at_one(self):
        repo = make_repo(events=mixed_events(["evt-3", None]))
        res = self.close(repo)
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertIn("OK: events [1,2]", res.stdout)
        rows = [json.loads(l) for l in
                (Path(repo) / BOARD / "events.jsonl").read_text().splitlines() if l.strip()]
        self.assertEqual([r["id"] for r in rows], ["evt-3", None, 1, 2])


class DispatchedMixedEventIdTests(unittest.TestCase):
    """DF-CRIER-512: the DISPATCH writer takes the same numeric-only next id.

    append_board_task_dispatched.py carried the identical bare
    `max(e["id"] for e in events) + 1`, so on the real crier board (ints + "evt-..."
    + nulls) every dispatch append raised TypeError before writing its event.
    """

    def dispatch(self, repo):
        return run_script(DISPATCHED, repo, "FIX-001", "2", "glm-5.2", "zai-glm", "4242")

    def events_of(self, repo):
        text = (Path(repo) / BOARD / "events.jsonl").read_text()
        return text, [json.loads(l) for l in text.splitlines() if l.strip()]

    def test_mixed_ids_append_next_numeric_id_and_stage(self):
        # the exact shapes from the ticket: 41 (int), "evt-7" (str), None, 42 (int)
        repo = make_repo(events=mixed_events([41, "evt-7", None, 42]))
        seeded = (Path(repo) / BOARD / "events.jsonl").read_text()

        res = self.dispatch(repo)
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertNotIn("TypeError", res.stderr)
        self.assertIn("event id=43 appended", res.stdout, "max numeric is 42 -> 43")

        text, rows = self.events_of(repo)
        self.assertTrue(text.startswith(seeded), "existing event bytes must be preserved")
        self.assertEqual(len(rows), 5, "four seeded events + one appended")
        self.assertEqual([r["id"] for r in rows[:4]], [41, "evt-7", None, 42],
                         "neighbouring ids keep their exact original shapes")

        dispatched = rows[-1]
        self.assertIsInstance(dispatched["id"], int)
        self.assertNotIsInstance(dispatched["id"], bool)
        self.assertEqual(dispatched["id"], 43)
        self.assertEqual(dispatched["event_type"], "task_dispatched")
        self.assertEqual(dispatched["task_id"], "FIX-001")
        self.assertEqual(dispatched["tick_number"], 2)
        # detail stays a JSON-encoded STRING (readers json.loads it)
        detail = dispatched["detail"]
        self.assertIsInstance(detail, str)
        self.assertEqual(json.loads(detail),
                         {"model": "glm-5.2", "provider": "zai-glm", "pid": 4242,
                          "task": "FIX-001", "tick": 2})

        tasks = [json.loads(l) for l in
                 (Path(repo) / BOARD / "tasks.jsonl").read_text().splitlines() if l.strip()]
        self.assertEqual(tasks[0]["worker_status"], "dispatched")
        self.assertEqual(tasks[0]["attempts"], 1)

        # the dispatch write is staged, not left in the worktree (DF-CRIER-510)
        lines = porcelain(repo)
        self.assertTrue(lines, "expected staged board changes, git status was clean")
        for line in lines:
            self.assertEqual(line[1], " ", f"worktree-side change still pending: {line!r}")
        self.assertEqual(unstaged_paths(repo), set())
        self.assertEqual(staged_paths(repo),
                         {f"{BOARD}/events.jsonl", f"{BOARD}/tasks.jsonl"})

        self.assert_compiles(DISPATCHED)

    def test_all_numeric_board_next_id_is_still_max_plus_one(self):
        repo = make_repo(events=mixed_events([41, 42]))
        res = self.dispatch(repo)
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertIn("event id=43 appended", res.stdout)
        self.assertEqual([r["id"] for r in self.events_of(repo)[1]], [41, 42, 43])

    def test_board_without_any_numeric_id_starts_at_one(self):
        repo = make_repo(events=mixed_events(["evt-9", None]))
        res = self.dispatch(repo)
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertIn("event id=1 appended", res.stdout)
        self.assertEqual([r["id"] for r in self.events_of(repo)[1]], ["evt-9", None, 1])

    def test_pure_digit_string_bounds_the_sequence_and_bools_do_not(self):
        """Unit-level contract of the replicated helper (kept in step with 511)."""
        mod = load_script_module("df_crier_512_dispatched", DISPATCHED)
        self.assertEqual(mod.next_event_id([]), 1)
        self.assertEqual(mod.next_event_id([{"id": 7}, {"id": "8"}, {"id": "evt-9"},
                                            {"id": None}, {}]), 9)
        # True is an int in Python but must not bound a sequence
        self.assertEqual(mod.next_event_id([{"id": 3}, {"id": True}]), 4)
        self.assertEqual(mod.next_event_id([{"id": "0041"}]), 42)
        self.assertEqual(list(mod.numeric_event_ids([{"id": 5}, {"id": "6"}, {"id": "x"}])),
                         [5, 6])

    def assert_compiles(self, script):
        with tempfile.TemporaryDirectory(prefix="df-crier-512-pyc-") as tmp:
            try:
                py_compile.compile(str(script), cfile=os.path.join(tmp, "out.pyc"),
                                   doraise=True)
            except py_compile.PyCompileError as exc:
                self.fail(f"{script.name} does not compile: {exc}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
