# Makefile-target smoke/e2e verification

Depth for Step 5 evidence checks in SKILL.md. Read when a row's premise is '<named target> fails' and the command is not given verbatim.

## Resolve the probe from the Makefile, not the row text

Rows say 'smoke-e2e fails' or 'e2e red' but the probe is rarely a file with that name (`scripts/smoke-e2e.sh` usually does not exist). The Makefile owns the target:

    grep -n "smoke" Makefile        # find the target and its recipe
    grep -rn smoke scripts/ tests/  # find the script the target actually invokes

Run `make <target>` itself (with a generous timeout — it rebuilds binaries first), not the guessed script.

## Run the probe unpiped, with a saved full output

`make <target> | tail` hides both the real exit code and the failure block (a FAILURES summary scrolls out of the tail window while the pipe masks the non-zero exit). Run it plainly; the tool saves the full output to a file. Then collect failures with a second pass over that output:

    make smoke-e2e 2>&1            # full run, saved output
    grep -nE 'FAIL|not ok' <saved> # the exact failing assertion lines

Quote the exact FAIL lines (the failing premise text, the mode being asserted) on the evidence refresh — they are what the foreman fixes, and 'fails' without the assertion text sends the next worker re-deriving the failure.

## Read the failure mode before stamping the refresh

A build step printing to stdout is not a failure; only FAIL/<error>/non-zero-exit lines count. Classify each failure as (a) assertion against a path/mode/contract the row already describes = evidence the premise holds, or (b) a NEW failure class = candidate row mint (after the G7 content-fingerprint check).
