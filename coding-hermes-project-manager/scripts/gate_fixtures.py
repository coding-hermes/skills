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
# REPO pinned to a barren suite-created temp dir by default (2026-11-22 PM tick,
# measured): the expectations encode a repo whose tracked files mention NONE of
# the fixture tokens — the invented-flag cases reject only when the grep misses.
# A real checkout can never satisfy that (the skills repo itself contains this
# fixtures file, boardctl's docs quote --insecure), so REPO=caller-cwd made
# ALL-GREEN cwd-dependent: from boardctl, insecure-prohibition-on-other-tool-
# fails PASSed (suite read FAILURES); from a non-git dir, all 12 matched. The
# temp dir reproduces that barren context deterministically; the argv override
# is kept for a deliberate cross-repo run.
REPO = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix='gate-fx-repo-')

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
    # Repo-root escape guard (MY-GAP-067 closeout re-grade, tier-2 derived FAIL):
    # a ../../../ token normalized above the repo root must NOT pass by host-disk
    # existence, even when the host file happens to exist — the relative-link
    # helper's repo-boundary guard makes the path-resolution arm irrelevant here
    # and the token stays 'path not in repo'.
    ("relative-link-escape-still-fails", "REJECT",
     "PASS: Open docs/getting-started/troubleshooting.md and follow its relative link ../../../Invented-Gone.md; expect a 200 page that grep finds the heading Invented-Gone in."),
    # curl --insecure scoping (voice-mode VOICE-8): a PROHIBITION of the real curl
    # bypass flag passes inside a curl criterion, while the same token on another
    # tool and an invented curl-ish flag both still FAIL.
    ("curl-insecure-prohibition-passes", "PASS",
     "PASS: `curl -sS -o /dev/null -w '%{http_code}' https://192.168.123.147:7860/client/` with verification ENABLED (no -k, no --insecure) prints 200."),
    ("insecure-prohibition-on-other-tool-fails", "REJECT",
     "PASS: `go test ./...` with verification ENABLED (no --insecure) exits 0 and prints ok, so the arm is clean."),
    ("invented-curl-flag-still-fails", "REJECT",
     "PASS: `curl -sS --insecure-tls https://192.168.123.147:7860/client/` exits 0 and prints 200."),
    ("unexpanded-placeholder-still-fails", "REJECT",
     "PASS: `make version-check VERSION_TAG=<current release>` exits 0 on the edited tree."),
    # git ls-files --exclude-standard scoping (QA-DEXDAT-CORE-28): the real
    # tracked-but-ignored inventory flag passes inside a `git ls-files` criterion,
    # while the same token on another tool and an invented ls-files flag both
    # still FAIL.
    ("git-ls-files-exclude-standard-passes", "PASS",
     "PASS: `git ls-files -i -c --exclude-standard` exits 0 and prints nothing; no tracked path is matched by .gitignore."),
    ("exclude-standard-on-other-tool-fails", "REJECT",
     "PASS: `go test ./... --exclude-standard` exits 0 and prints ok, so the arm is clean."),
    ("invented-ls-files-flag-still-fails", "REJECT",
     "PASS: `git ls-files -i -c --exclude-symlink-standard` exits 0 and prints nothing, so the arm is clean."),
    # bunker list --status / bunker destroy --purge scoping (QA-HERMES-CANOPY-50):
    # real flags of the host-installed bunker CLI pass inside criteria that invoke
    # the owning subcommand, while an invented bunker flag and the same flag on
    # another tool both still FAIL.
    ("bunker-list-status-flag-passes", "PASS",
     "PASS: `bunker list --status all` exits 0 and prints the agent table, so the slot census is real."),
    ("bunker-destroy-purge-flag-passes", "PASS",
     "PASS: `bunker destroy $AGENT_ID --purge` terminates within the printed deadline and exits 0; the follow-up `bunker list --status all` no longer lists the agent."),
    ("invented-bunker-flag-still-fails", "REJECT",
     "PASS: `bunker list --status all --frobnicate` exits 0 and prints the table, so the census is clean."),
    ("purge-on-other-tool-still-fails", "REJECT",
     "PASS: `go vet ./... --purge` exits 0 and prints no output, so the arm is clean."),
    # Absence-shape extension (QA-HERMES-CANOPY-060): a "contains no <token>"
    # anti-latch arm and a `grep -c '<token>'` arm whose expectation is zero are
    # sanctioned absence assertions, while a zero-shaped token does not exempt a
    # DIFFERENT path cited as must-exist, and a grep -c expecting a NONZERO count
    # stays an existence arm and still FAILs on an absent path.
    ("contains-no-absence-passes", "PASS",
     "PASS: run `cat /var/lib/qa/state-snapshot-text.txt` after the fix; the snapshot contains no ./qa-evidence.jsonl and the probe exits 0, so the chaos cell grades a repo surface."),
    ("zero-count-grep-passes", "PASS",
     "PASS: run `grep -c './qa-evidence.jsonl' /var/lib/qa/state-snapshot-text.txt`; expect the next battery's snapshot to return 0 for that token and the probe to exit 0."),
    ("zero-grep-nonzero-expect-still-fails", "REJECT",
     "PASS: run `grep -c './Other-Invented.jsonl' /var/lib/qa/snap.txt`; expect the count to be 1 and the probe to exit 0."),
    ("absence-shape-does-not-leak", "REJECT",
     "PASS: the snapshot contains no ./qa-evidence.jsonl and the probe exits 0; the shipped ./Third-Invented.jsonl parses against the spec."),
    # doc_inbound_census.py --root scoping (digest DOC-028, 2026-11-25 PM tick):
    # the REQUIRED --root flag of the coding-hermes-docs inbound census passes
    # inside a criterion invoking the script, while an invented neighbor flag
    # beside the script and the same flag on another tool both still FAIL.
    ("doc-census-root-flag-passes", "PASS",
     "PASS: `python3 doc_inbound_census.py --root /srv/probe-repo` exits 0 and prints the orphan-page census; the three named docs no longer appear among zero-inbound pages."),
    ("invented-doc-census-flag-still-fails", "REJECT",
     "PASS: `python3 doc_inbound_census.py --rootz /srv/probe-repo` exits 0 and prints the orphan-page census."),
    ("root-flag-on-other-tool-still-fails", "REJECT",
     "PASS: `go test ./... --root ./` exits 0 and prints ok, so the arm is clean."),
    # auditctl -k scoping (hermes-canopy CAN-OPS-006, 2026-11-25 PM tick): auditctl
    # is not a test runner — its `-k <key>` is an operator-invented AUDIT-RULE key,
    # so the named-symbol arm must NOT repo-grep it, while an invented pytest `-k`
    # token on any other command still FAILs with the same message.
    ("auditctl-operator-key-passes", "PASS",
     "PASS: `sudo auditctl -a always,exit -F arch=b64 -S pidfd_send_signal -F a2=9 -k canopykill_fx` adds the pidfd audit rule (consent-block recorded on unattended surfaces). Expected outcome: auditctl -l lists the rule with key canopykill_fx."),
    ("invented-pytest-k-token-still-fails", "REJECT",
     "PASS: run `pytest -k canopytest_fx`; expect exit 0 and the invented suite as the only match."),
    # hermes CLI --provider seat-binding pair (warpfs INT-CI-025, 2026-11-28): the
    # real dispatch-law flag passes inside a criterion that invokes hermes, while
    # the same token on another tool and an invented hermes flag both still FAIL.
    ("hermes-provider-dispatch-pair-passes", "PASS",
     "PASS: `hermes -z 'seat probe' -m glm-5.3-flash --provider opencode-go-2` records model=glm-5.3-flash and the ocg billing_base_url in state.db sessions and never deepseek-foreman."),
    ("provider-flag-on-other-tool-still-fails", "REJECT",
     "PASS: `go vet ./... --provider opencode-go-2` exits 0 and prints no output, so the arm is clean."),
    ("invented-flag-beside-hermes-still-fails", "REJECT",
     "PASS: `hermes -z 'seat probe' --seat-pin-lane opencode-go-2` refuses loudly when the lane cannot bind."),
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
