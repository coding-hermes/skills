"""Regression fixtures for the acceptance gate's repo-scoped arms (TRBL-141).

Both directions are proven:
  PASS cases  — a criterion legitimately naming a token outside this repo
                (negative existence assertion, documented gitreins guard flag)
                must NOT be flagged.
  REJECT cases — a mistyped in-repo path, an invented flag on the same verb, an
                invented flag on another tool, and an invented flag on another
                gitreins verb must still FAIL.

Run: python3 scripts/gate_fixtures.py <repo>
Exit 0 only when every case matches its expectation.
"""
import json, os, subprocess, sys, tempfile

GATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'acceptance_gate.py')
REPO = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

CASES = [
    ("absence-assertion-passes", "PASS",
     "PASS: `test ! -e docs/Invented-Gone.md` exits 0 and prints no output; the forbidden file is absent from the tree."),
    ("negative-log-arm-passes", "PASS",
     "PASS: `git log --all -- docs/Invented-Gone.md` exits 0 and prints no commits."),
    ("mistyped-in-repo-path-still-fails", "REJECT",
     "PASS: `test -f docs/Invented-Gone.md` exits 0 and the file is byte-identical to the spec."),
    ("exemption-does-not-leak-across-arms", "REJECT",
     "PASS: `test ! -e ~/elsewhere/docs/Invented-Gone.md` exits 0; the shipped docs/Invented-Gone.md parses and matches the spec."),
    ("invented-token-not-exempt", "REJECT",
     "PASS: `test ! -e docs/Other-Invented.md` and `test -f docs/Second-Invented.md` both behave; the shipped docs/Second-Invented.md parses."),
    ("gitreins-guard-flag-passes", "PASS",
     "PASS: `gitreins guard --quality-async` exits 0 and prints the producer pid it spawned, with no fallback activated."),
    ("invented-flag-on-same-verb-fails", "REJECT",
     "PASS: `gitreins guard --bogus-async-flag` exits 0 and prints the queued job id, no fallback activated."),
    ("invented-flag-on-other-tool-fails", "REJECT",
     "PASS: `go vet ./... --quality-async` exits 0 and prints no output, so the arm is clean."),
    ("invented-flag-on-other-gitreins-verb-fails", "REJECT",
     "PASS: `gitreins task complete TRBL-999 --quality-async` exits 0 and the row reads complete."),
]


def main():
    ok = True
    for name, expect, acceptance in CASES:
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
            json.dump({'acceptance': acceptance}, fh)
            path = fh.name
        try:
            r = subprocess.run([sys.executable, GATE, 'validate', REPO, path],
                               capture_output=True, text=True)
        finally:
            os.unlink(path)
        got = 'PASS' if r.returncode == 0 else 'REJECT'
        good = got == expect
        ok = ok and good
        print(f"{'ok  ' if good else 'FAIL'} {name}: expect={expect} got={got}")
    print('RESULT:', 'ALL-GREEN' if ok else 'FAILURES')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
