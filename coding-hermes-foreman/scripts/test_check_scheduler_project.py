#!/usr/bin/env python3
"""GAP-111 board-acceptance tests for late-sorting scheduler project lookup.

No live scheduler is required for these regressions.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock
import urllib.error

SCRIPT = Path(__file__).with_name("check_scheduler_project.py")
SPEC = importlib.util.spec_from_file_location("check_scheduler_project", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


class JSONResponse(io.StringIO):
    def __init__(self, value):
        super().__init__(json.dumps(value))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class CheckSchedulerProjectTests(unittest.TestCase):
    def run_main(self, name, responses):
        output = io.StringIO()
        with mock.patch.object(checker.urllib.request, "urlopen", side_effect=responses) as urlopen:
            with mock.patch.object(sys, "argv", [str(SCRIPT), name]):
                with contextlib.redirect_stdout(output):
                    checker.main()
        return output.getvalue().splitlines(), [call.args[0] for call in urlopen.call_args_list]

    def test_nested_single_project_success_skips_truncated_list(self):
        name = "zzzz late/target"
        nested_project = {
            "name": name,
            "enabled": True,
            "cooldown_s": 21600,
            "decay_rate": 1,
            "priority": 5,
            "weight": 10,
            "updated_at": "2026-10-29T20:14:22Z",
            "last_tick_started": "2026-10-29T20:14:21Z",
        }

        lines, urls = self.run_main(name, [JSONResponse({"project": nested_project})])

        self.assertEqual([checker.API + "/zzzz%20late%2Ftarget"], urls)
        self.assertEqual([{
            "Name": name,
            "Enabled": True,
            "CooldownS": 21600,
            "DecayRate": 1,
            "Priority": 5,
            "Weight": 10,
            "UpdatedAt": "2026-10-29T20:14:22Z",
            "LastTickStarted": "2026-10-29T20:14:21Z",
        }], [json.loads(line) for line in lines])

    def test_single_project_404_falls_back_to_list(self):
        name = "late-project"
        list_project = {
            "name": name,
            "enabled": False,
            "cooldown_s": 0,
            "decay_rate": 2,
            "priority": 3,
            "weight": 4,
            "updated_at": "updated",
            "last_tick_started": "started",
        }
        missing = urllib.error.HTTPError(checker.API + "/" + name, 404, "Not Found", None, None)

        lines, urls = self.run_main(name, [missing, JSONResponse({"projects": [list_project]})])

        self.assertEqual([checker.API + "/" + name, checker.API], urls)
        self.assertEqual([{
            "Name": name,
            "Enabled": False,
            "CooldownS": 0,
            "DecayRate": 2,
            "Priority": 3,
            "Weight": 4,
            "UpdatedAt": "updated",
            "LastTickStarted": "started",
        }], [json.loads(line) for line in lines])

    def test_legacy_camel_case_list_normalization(self):
        name = "legacy-project"
        legacy_project = {
            "Name": name,
            "Enabled": False,
            "CooldownS": 0,
            "DecayRate": 0,
            "Priority": 0,
            "Weight": 0,
            "UpdatedAt": "legacy-updated",
            "LastTickStarted": "legacy-started",
        }
        missing = urllib.error.HTTPError(checker.API + "/" + name, 404, "Not Found", None, None)

        lines, _ = self.run_main(name, [missing, JSONResponse([legacy_project])])

        self.assertEqual([legacy_project], [json.loads(line) for line in lines])

    def test_no_name_keeps_all_project_list_dump(self):
        projects = [
            {"name": "snake", "enabled": True},
            {"Name": "camel", "Enabled": False},
        ]
        output = io.StringIO()
        with mock.patch.object(checker.urllib.request, "urlopen", return_value=JSONResponse({"projects": projects})) as urlopen:
            with mock.patch.object(sys, "argv", [str(SCRIPT)]):
                with contextlib.redirect_stdout(output):
                    checker.main()

        self.assertEqual([mock.call(checker.API, timeout=10)], urlopen.call_args_list)
        self.assertEqual([
            {"Name": "snake", "Enabled": True, "CooldownS": None, "DecayRate": None,
             "Priority": None, "Weight": None, "UpdatedAt": None, "LastTickStarted": None},
            {"Name": "camel", "Enabled": False, "CooldownS": None, "DecayRate": None,
             "Priority": None, "Weight": None, "UpdatedAt": None, "LastTickStarted": None},
        ], [json.loads(line) for line in output.getvalue().splitlines()])


if __name__ == "__main__":
    unittest.main()
