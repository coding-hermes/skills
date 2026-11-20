"""DF-CRIER-513: next event id comes from NUMERIC ids only, across the skill's tooling.

The fleet's boards carry MIXED event-id shapes — plain ints next to legacy
"evt-..." string ids, null ids, and rows with no id at all. Any `max()` (or a
`> max_id` comparison) over every row raises TypeError / KeyError before a single
event is written, so every append path in this skill computes the next id from the
numeric candidates only (ints + pure ASCII digit strings; default 0).

Targets covered:
  scripts/close_tick_jsonl_board.py          next_event_id(events)      (worker + audit modes)
  scripts/docwriter_inject_rows.py           audit event id             (end-to-end run)
  templates/manual_append_no_duckdb.py       next_event_id(lines)       (ast-extracted)
  templates/append_event_no_header.py        numeric_event_ids(events)  (ast-extracted)
  templates/append_event_with_header.py      numeric_event_ids(events)  (ast-extracted)

Run:  python3 coding-hermes-jsonl-board-append/scripts/test_board_event_id_shapes.py
      (also collectable by pytest)

No live board is touched: every fixture is a throwaway dir under TMPDIR.
"""
import ast
import json
import os
import py_compile
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import close_tick_jsonl_board as close_tick  # noqa: E402

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
CLOSE = HERE / "close_tick_jsonl_board.py"
DOCWRITER = HERE / "docwriter_inject_rows.py"
MANUAL = TEMPLATES / "manual_append_no_duckdb.py"
NO_HEADER = TEMPLATES / "append_event_no_header.py"
WITH_HEADER = TEMPLATES / "append_event_with_header.py"

TS = "2026-11-20 06:00:00.000000"

# The shape mix the crier events.jsonl actually carries: int, non-numeric string,
# null, pure-digit string. max numeric = 9 -> next id 10.
MIXED_IDS = [4, "evt-3", None, "9"]


def event_rows(ids):
    """Event dicts carrying those exact id shapes, in board order."""
    return [{
        "id": eid, "timestamp": TS, "event_type": "audit", "task_id": None,
        "actor": "foreman",
        "detail": json.dumps({"tick": idx + 1, "summary": f"fixture seed id={eid!r}"}),
        "tick_number": idx + 1,
    } for idx, eid in enumerate(ids)]


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in rows))


def make_board(ids=None, with_header=True):
    """Throwaway repo with a JSONL board; returns (repo, board_dir)."""
    repo = tempfile.mkdtemp(prefix="df-crier-513-")
    bdir = Path(repo) / ".coding-hermes" / "board"
    bdir.mkdir(parents=True)
    write_jsonl(bdir / "events.jsonl", event_rows(ids if ids is not None else [1]))
    write_jsonl(bdir / "tasks.jsonl", [{
        "id": "FIX-001", "title": "fixture task", "status": "pending",
        "worker_status": "idle", "attempts": 0, "priority": 2, "complexity": 2,
    }])
    if with_header:
        Path(bdir / "board.jsonl").write_text(json.dumps({
            "project": "fixture", "namespace": "fixture", "ticks_total": 1,
            "ticks_idle": 0, "last_commit": "deadbee", "last_tick": TS,
            "updated_at": TS,
        }) + "\n")
    return repo, bdir


def run_script(script, args):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return subprocess.run([sys.executable, str(script), *args], capture_output=True,
                          text=True, env=env, timeout=120)


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def load_template_functions(path, names):
    """Exec only the named top-level helpers out of a template's real source.

    Templates are copy/paste artifacts (module-level CONFIG + file I/O against a
    live board), so a test cannot import them. Instead the named FunctionDef nodes
    are extracted with ast and executed — the code under test is the template file
    itself, byte for byte, not a copy of it.
    """
    src = Path(path).read_text()
    tree = ast.parse(src)
    wanted = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert [n.name for n in wanted] == list(names), \
        f"{Path(path).name}: expected top-level {names}, found {[n.name for n in wanted]}"
    ns = {"json": json}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(path), "exec"), ns)
    return ns


class HelpersUnitTests(unittest.TestCase):
    """The no-crash contract itself, on every shape a fleet board holds."""

    def test_mixed_shapes_skip_non_numeric_and_bound_on_digit_strings(self):
        ns = load_template_functions(NO_HEADER, ["numeric_event_ids"])
        events = event_rows(MIXED_IDS) + [
            {"timestamp": TS},                      # no id at all
            "not-a-dict",                           # garbage row
            {"id": True},                           # bool is an int in python
            {"id": 7.5},                            # float is not an event id
        ]
        self.assertEqual(max(ns["numeric_event_ids"](events)), 9)
        self.assertEqual(max(close_tick.numeric_event_ids(events)), 9)

    def test_no_numeric_ids_starts_at_one(self):
        events = event_rows(["evt-3", None])
        self.assertEqual(close_tick.next_event_id(events), 1)
        for path, fn in ((NO_HEADER, "numeric_event_ids"), (WITH_HEADER, "numeric_event_ids")):
            ns = load_template_functions(path, [fn])
            self.assertEqual(max(ns[fn](events), default=0) + 1, 1, path.name)

    def test_templates_no_longer_compare_raw_ids(self):
        """The two pre-fix shapes must be gone: they TypeError on str/None rows."""
        manual = MANUAL.read_text()
        self.assertNotIn('max(int(json.loads(l)["id"])', manual)
        self.assertIn("next_event_id", manual)
        for path in (NO_HEADER, WITH_HEADER):
            src = path.read_text()
            self.assertNotIn('e.get("id", 0) > max_id', src, path.name)
            self.assertIn("numeric_event_ids", src, path.name)


class CloseTickBoardTests(unittest.TestCase):
    """close_tick_jsonl_board.py end-to-end on a mixed-shape board."""

    def close_worker_tick(self, repo):
        return run_script(CLOSE, [
            "--repo", repo, "--tick", "2", "--task", "FIX-001",
            "--commit", "abc1234", "--judge", "7dde3f10",
            "--worker", "fixture@lane", "--note", "gates PASS",
        ])

    def test_worker_tick_uses_max_numeric_id_and_preserves_neighbours(self):
        repo, bdir = make_board(MIXED_IDS)
        seeded = (bdir / "events.jsonl").read_text()

        res = self.close_worker_tick(repo)
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertNotIn("TypeError", res.stderr)
        self.assertIn("event id 10 appended", res.stdout, "max numeric is 9 -> next 10")

        text = (bdir / "events.jsonl").read_text()
        self.assertTrue(text.startswith(seeded), "existing event bytes must be preserved")
        rows = read_jsonl(bdir / "events.jsonl")
        self.assertEqual(len(rows), len(MIXED_IDS) + 1)

        new = rows[-1]
        self.assertIsInstance(new["id"], int)
        self.assertNotIsInstance(new["id"], bool)
        self.assertEqual(new["id"], 10)
        self.assertEqual(new["event_type"], "worker_tick")
        self.assertEqual(new["task_id"], "FIX-001")
        # untouched neighbours keep their exact original shapes
        self.assertEqual([r["id"] for r in rows[:-1]], MIXED_IDS)

        tasks = read_jsonl(bdir / "tasks.jsonl")
        self.assertEqual(tasks[0]["status"], "complete")
        self.assertEqual(tasks[0]["commit_hash"], "abc1234")

    def test_audit_tick_on_board_without_numeric_ids_starts_at_one(self):
        repo, bdir = make_board(["evt-3", None])
        res = run_script(CLOSE, [
            "--repo", repo, "--tick", "3", "--audit",
            "--verdict", "IDLE", "--type", "light-audit", "--note", "gates 9/9",
        ])
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertIn("event id 1 appended", res.stdout)
        self.assertEqual([r["id"] for r in read_jsonl(bdir / "events.jsonl")],
                         ["evt-3", None, 1])


class DocWriterTests(unittest.TestCase):
    """docwriter_inject_rows.py writes its audit event with a numeric-only id."""

    def test_docwriter_audit_event_id_skips_mixed_shapes(self):
        repo, bdir = make_board(MIXED_IDS)
        specs = json.dumps([["Doc gap one", "why it matters"]])

        res = run_script(DOCWRITER, [str(bdir), "2026-11-20", specs])
        self.assertEqual(res.returncode, 0, f"stdout={res.stdout!r} stderr={res.stderr!r}")
        self.assertIn("EVENT_APPENDED id=10", res.stdout)

        rows = read_jsonl(bdir / "events.jsonl")
        new = rows[-1]
        self.assertEqual(new["id"], 10)
        self.assertIsInstance(new["id"], int)
        self.assertEqual(new["actor"], "doc-writer")
        self.assertEqual([r["id"] for r in rows[:-1]], MIXED_IDS)
        # the DOC row itself must have landed too
        self.assertTrue(any(r["id"] == "DOC-1" for r in read_jsonl(bdir / "tasks.jsonl")))


class TemplateTests(unittest.TestCase):
    """The copy/paste templates must not reintroduce the bare max()."""

    def test_manual_append_next_event_id_tolerates_mixed_and_malformed_lines(self):
        ns = load_template_functions(MANUAL, ["next_event_id"])
        lines = [json.dumps(r) for r in event_rows(MIXED_IDS)]
        lines.insert(0, "{ this is not json")   # malformed line: skipped, not fatal
        lines.append("")                        # blank line
        self.assertEqual(ns["next_event_id"](lines), 10)

    def test_manual_append_bool_id_is_not_numeric(self):
        ns = load_template_functions(MANUAL, ["next_event_id"])
        self.assertEqual(ns["next_event_id"]([json.dumps({"id": True})]), 1)

    def test_with_header_helper_matches_close_script_domain(self):
        ns = load_template_functions(WITH_HEADER, ["numeric_event_ids"])
        events = event_rows(MIXED_IDS)
        self.assertEqual(sorted(ns["numeric_event_ids"](events)),
                         sorted(close_tick.numeric_event_ids(events)))


class CompileTests(unittest.TestCase):
    """Every touched file must compile (pyc emitted outside the repo tree)."""

    def test_touched_files_compile(self):
        for path in (CLOSE, DOCWRITER, MANUAL, NO_HEADER, WITH_HEADER):
            with tempfile.TemporaryDirectory(prefix="df-crier-513-pyc-") as tmp:
                try:
                    py_compile.compile(str(path), cfile=os.path.join(tmp, "out.pyc"),
                                       doraise=True)
                except py_compile.PyCompileError as exc:
                    self.fail(f"{path.name} does not compile: {exc}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
