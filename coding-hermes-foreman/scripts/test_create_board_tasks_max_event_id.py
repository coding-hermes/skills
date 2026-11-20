#!/usr/bin/env python3
"""DF-CRIER-514: create_board_tasks.py takes its next event id from the NUMERIC ids only.

Defect being pinned: the real crier events.jsonl mixes INTEGER ids
(e.g. 1795041048590000042) with legacy STRING ids, so

    if e.get("id", 0) > mid:        # max_event_id()

raised `TypeError: '>' not supported between instances of 'str' and 'int'` on
every run. Live crash 2026-11-20 (crier board): the task rows were appended but
their task_created events never landed and staging never ran, because the crash
precedes stage_board_files(). Same crash class as DF-CRIER-511/512/513.

The sanctioned shape is the replicated numeric_event_ids helper used by
append_board_task_completed.py (DF-CRIER-511) and
append_board_task_dispatched.py (DF-CRIER-512): ints count (bools excluded - True
is an int in Python), pure ASCII digit strings count (so a legacy "9" still
bounds the sequence), and nulls / id-less rows / non-numeric string ids / non-dict
rows are ignored. max_event_id(path) keeps its signature and returns an int.

Run:  python3 coding-hermes-foreman/scripts/test_create_board_tasks_max_event_id.py
      (also collectable by pytest)

No live board is touched: every fixture is a throwaway dir under TMPDIR.
"""
import importlib.util
import json
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
CREATE_TASKS = SCRIPTS / "create_board_tasks.py"

BOARD = ".coding-hermes/board"
TS = "2026-11-20 00:00:00.000000"

# The id shapes the crier events.jsonl actually carries, plus the large-int
# second-precision form the coder writes today.
REAL_INT_IDS = [1795041048590000001, 1795041048590000002, 1795041048590000042]


def load_script_module():
    """Import create_board_tasks.py by path (it is an entry point, not a package)."""
    spec = importlib.util.spec_from_file_location("df_crier_514_create_tasks",
                                                  str(CREATE_TASKS))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def event_rows(ids):
    """Event dicts carrying those exact id shapes, in board order."""
    return [{
        "id": eid, "timestamp": TS, "event_type": "audit", "task_id": None,
        "actor": "foreman",
        "detail": json.dumps({"tick": idx + 1, "summary": f"fixture seed id={eid!r}"}),
        "tick_number": idx + 1,
    } for idx, eid in enumerate(ids)]


def write_events(path, rows, blank_lines=False):
    body = "".join(json.dumps(r) + "\n" for r in rows)
    if blank_lines:
        body = "\n" + body.replace("\n", "\n\n", 1) + "   \n"
    Path(path).write_text(body)


def make_events_file(rows, blank_lines=False):
    """Throwaway events.jsonl holding those rows; returns its path."""
    tmp = tempfile.mkdtemp(prefix="df-crier-514-")
    path = Path(tmp) / "events.jsonl"
    write_events(path, rows, blank_lines=blank_lines)
    return str(path)


class MaxEventIdUnitTests(unittest.TestCase):
    """The no-crash contract of max_event_id() on every shape a fleet board holds."""

    def setUp(self):
        self.mod = load_script_module()

    def max_of(self, rows, blank_lines=False):
        return self.mod.max_event_id(make_events_file(rows, blank_lines=blank_lines))

    # ---- required cases --------------------------------------------------------

    def test_all_int_ids_return_the_int_max(self):
        self.assertEqual(self.max_of(event_rows([11, 3, 42])), 42)

    def test_int_ids_beside_one_digit_string_id_still_bound_on_the_number(self):
        # "9" is a legacy string id: it must bound the sequence, not crash
        self.assertEqual(self.max_of(event_rows([4, "9"])), 9)
        self.assertEqual(self.max_of(event_rows(["9", 4])), 9)

    def test_non_numeric_string_ids_are_ignored(self):
        self.assertEqual(self.max_of(event_rows([3, "evt-3", "abc"])), 3)

    def test_null_missing_and_bool_ids_are_ignored(self):
        rows = event_rows([7])
        rows.append({"timestamp": TS, "id": None, "event_type": "audit"})
        rows.append({"timestamp": TS, "event_type": "audit"})   # no id key at all
        rows.append({"id": True, "timestamp": TS})               # True is an int in Python
        rows.append({"id": False, "timestamp": TS})
        self.assertEqual(self.max_of(rows), 7)

    def test_empty_file_returns_zero(self):
        self.assertEqual(self.max_of([]), 0)

    def test_blank_lines_are_skipped(self):
        self.assertEqual(self.max_of(event_rows([5]), blank_lines=True), 5)

    def test_real_mixed_board_returns_the_int_max_not_a_string(self):
        # the live crier shape: several large ints + one legacy string id + junk
        rows = event_rows(REAL_INT_IDS)
        rows.append({"id": "evt-101", "timestamp": TS, "event_type": "audit"})
        rows.append({"id": None, "timestamp": TS, "event_type": "audit"})
        got = self.max_of(rows)
        self.assertEqual(got, 1795041048590000042)
        self.assertIsInstance(got, int)
        self.assertNotIsInstance(got, bool)
        # the bug's second half: a propagated STRING max would break next_id += 1
        self.assertEqual(got + 1, 1795041048590000043)

    # ---- helper contract kept in step with DF-CRIER-511/512 ---------------------

    def test_numeric_event_ids_helper_matches_the_511_512_domain(self):
        rows = event_rows([4, "evt-3", None, "9"]) + [
            {"timestamp": TS},          # no id
            "not-a-dict",               # garbage row
            {"id": True},               # bool
            {"id": 7.5},                # float is not an event id
        ]
        self.assertEqual(list(self.mod.numeric_event_ids(rows)), [4, 9])
        self.assertEqual(max(self.mod.numeric_event_ids(rows), default=0), 9)

    def test_unicode_digit_strings_are_not_event_ids(self):
        # isascii() guard: int("٩") would otherwise be accepted by isdigit()
        self.assertEqual(self.max_of(event_rows([3, "\u0669"])), 3)


class CreateTasksEndToEndTests(unittest.TestCase):
    """The live failure was script-level: rows landed, task_created events did not."""

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="df-crier-514-repo-")
        self.addCleanup(shutil.rmtree, self.repo, True)
        bdir = Path(self.repo) / BOARD
        bdir.mkdir(parents=True, exist_ok=True)
        write_events(bdir / "events.jsonl", event_rows(REAL_INT_IDS[:2]) + [
            {"id": "evt-9", "timestamp": TS, "event_type": "audit", "task_id": None},
            {"id": None, "timestamp": TS, "event_type": "audit", "task_id": None},
        ])
        (bdir / "tasks.jsonl").write_text(json.dumps({
            "id": "FIX-001", "title": "fixture task", "status": "pending",
            "worker_status": "idle", "attempts": 0,
        }) + "\n")
        self.bdir = bdir

    def clean_env(self):
        """Ambient git plumbing would hijack the fixture (it is intentionally not a repo)."""
        env = dict(os.environ)
        for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE"):
            env.pop(var, None)
        return env

    def run_create(self, tasks):
        tasks_json = Path(self.repo) / "new_tasks.json"
        tasks_json.write_text(json.dumps(tasks))
        return subprocess.run([sys.executable, str(CREATE_TASKS), self.repo, "514",
                               str(tasks_json)],
                              capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, env=self.clean_env(), timeout=120)

    def read_jsonl(self, name):
        return [json.loads(l) for l in
                (self.bdir / name).read_text().splitlines() if l.strip()]

    def test_mixed_board_appends_numeric_events_and_reaches_staging(self):
        seeded = (self.bdir / "events.jsonl").read_text()

        res = self.run_create([{"id": "FIX-514", "title": "second fixture task",
                                "priority": 2, "complexity": "small"}])
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertNotIn("TypeError", res.stderr)
        self.assertIn("events.jsonl: appended 1 task_created events", res.stdout)
        # the crash used to precede staging; the staging step must now be reached
        self.assertIn("NOTICE:", res.stdout)
        self.assertIn("NOT staged", res.stdout)

        text = (self.bdir / "events.jsonl").read_text()
        self.assertTrue(text.startswith(seeded), "existing event bytes must be preserved")
        rows = self.read_jsonl("events.jsonl")
        self.assertEqual(len(rows), 5, "four seeded events + one task_created")

        new = rows[-1]
        self.assertIsInstance(new["id"], int)
        self.assertNotIsInstance(new["id"], bool)
        self.assertEqual(new["id"], 1795041048590000003,
                         "max numeric is the large int -> +1, never a string")
        self.assertEqual(new["event_type"], "task_created")
        self.assertEqual(new["task_id"], "FIX-514")
        self.assertEqual(new["tick_number"], 514)
        # untouched neighbours keep their exact original shapes
        self.assertEqual([r["id"] for r in rows[:4]],
                         [*REAL_INT_IDS[:2], "evt-9", None])
        self.assertTrue(any(r["id"] == "FIX-514" for r in self.read_jsonl("tasks.jsonl")))

    def test_two_created_tasks_get_consecutive_numeric_ids(self):
        res = self.run_create([
            {"id": "FIX-514-A", "title": "a", "priority": 2, "complexity": "small"},
            {"id": "FIX-514-B", "title": "b", "priority": 2, "complexity": "small"},
        ])
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        appended = [r["id"] for r in self.read_jsonl("events.jsonl")[4:]]
        self.assertEqual(appended, [1795041048590000003, 1795041048590000004])


class CompileTests(unittest.TestCase):

    def test_script_compiles(self):
        """py_compile clean, emitted into TMPDIR so the repo tree stays clean."""
        with tempfile.TemporaryDirectory(prefix="df-crier-514-pyc-") as tmp:
            try:
                py_compile.compile(str(CREATE_TASKS), cfile=os.path.join(tmp, "out.pyc"),
                                   doraise=True)
            except py_compile.PyCompileError as exc:
                self.fail(f"{CREATE_TASKS.name} does not compile: {exc}")

    def test_pre_fix_comparison_shape_is_gone(self):
        """The bare `e.get(\"id\", 0) > mid` comparison is the crash; it must not return."""
        src = CREATE_TASKS.read_text()
        self.assertNotIn('e.get("id", 0) > mid', src)
        self.assertIn("numeric_event_ids", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
