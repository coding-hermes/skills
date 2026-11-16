"""GitReins tier-1 enforcement: the writing rules are not optional.

Runs the style checker and the manifest drift gate as tests, so any GitReins
guard/test pass on this repo fails when a skill breaks the writing rules or the
manifest drifts. Baseline (pre-existing debt) is ratcheted in
scripts/style-baseline.json — new regressions FAIL, old debt WARNs until paid.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_style_check_no_new_failures():
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "style_check.py")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"style_check FAIL:\n{r.stdout}\n{r.stderr}"


def test_manifest_no_drift():
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "manifest_check.py")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"manifest drift:\n{r.stdout}\n{r.stderr}"


def test_baseline_exists():
    b = REPO / "scripts" / "style-baseline.json"
    assert b.exists(), "style-baseline.json missing — the ratchet has no floor"
