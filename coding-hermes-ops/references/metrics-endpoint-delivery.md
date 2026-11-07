# Delivering an ops `metrics` P1 (a service that exports nothing)

Load when the census reports `check=metrics` for a `service` family and the tick (or a dispatched
worker) has to land the endpoint — not when refuting the finding.

## Shape that works

- **Stdlib-only Prometheus TEXT exposition (0.0.4)** in one new module: `Counter`, `Histogram` with
  fixed buckets, and a labelled error counter. Render `# HELP` / `# TYPE` per family, cumulative
  `_bucket{le="…"}` lines ending in `+Inf`, `_sum`, `_count`, escaped label values (backslash, quote,
  newline), trailing newline. A module-level default registry plus `reset()` keeps tests independent.
- **Enforce structure at registration**: a required name prefix, a declared label set, and a CLOSED
  reason vocabulary. A sample whose labels do not match the family's declaration must be refused, or a
  typo silently invents a series the scrape never shows.
- **Do not add a dependency** (prometheus_client, OTel, statsd) unless the repo already ships one: a
  new pin widens the release surface, breaks offline installs and drags a formatter/lint change with it.
- **Mount on the EXISTING surface** when there is one: an opt-in config field per listener, default
  false, answered AFTER auth and BEFORE namespace/path policy. Off means the path falls through to the
  previous behaviour exactly — that is the fail-closed arm, not a missing feature.
- **Instrument ONE choke point** (the response/send helper) so counters, durations and error reasons
  come from real traffic without restructuring the auth/namespace logic. This is instrumentation, not a
  refactor; a diff that reshapes decisions cannot be judged on a metrics criterion.

## Acceptance arms that make the close falsifiable

1. Opted-in listener → 200, `text/plain; version=0.0.4; charset=utf-8`, and all three families present.
2. **Negative control**: the same listener WITHOUT the opt-in → non-200 and no metric family in the
   body. This arm is what proves it is opt-in rather than a silently public endpoint.
3. Auth still applies to the scrape path on a bearer listener (401, then 200 with the token).
4. A refusal / handler-error path moves the right reason label and the status counter.
5. **Red proofs by mutation**, on copies outside the repo: delete the opt-in gate → arm 2 fails; delete
   the instrumentation → the family lines and reason samples disappear. Never commit a mutant, and
   quote the failures, so the green run means "fixed" rather than "tautological".

## Gates to run and quote (foreman runs them, not the worker)

- Full suite with the pre-change baseline count recorded beside the new count; the delta should equal
  the tests the change adds.
- The formatter/linter the CI or commit guard ACTUALLY invokes — it often lives outside the repo venv,
  so resolve the real binary path first rather than reporting a gate you never ran.
- Any artifact-reproducibility gate (regenerate committed docs, require empty porcelain).
- GitReins lifecycle, commit-time guard log, and the CI run for the pushed sha.
- Family-scoped census re-run: `fleet_ops_check.py --project <family> --json` shows the metrics gap
  gone while the family's untouched checks (`deploy-doc`, `container`) are still reported.

## Always-on exposure on an existing HTTP listener (no opt-in flag)

When the service already serves its own API listener and auth is unchanged, mount `GET /metrics`
there with no flag and no second port: a monitor then needs only the credential it already uses for
`/v1/health`. The shape that survives review:

- **Bound the label cardinality or the scrape surface becomes its own outage.** Label by the matched
  route TEMPLATE (`/v1/deliberate`), never the raw request path, and collapse an unmatched request to a
  single `<unmatched>` series. A scanner walking `/wp-admin-<random>` otherwise mints one time series
  per hit.
- **A pure-ASGI wrapper, not `BaseHTTPMiddleware`.** Base HTTP middleware re-frames the response body,
  which corrupts SSE streams (any live DAG/chat view); the ASGI wrapper only reads
  `http.response.start` and passes every message through. Count an unhandled exception under its own
  `exception` reason so a crash is distinguishable from a deliberate 5xx.
- **Exclude the scrape path from its own counters** by early-returning when the matched route is the
  metrics path, and assert that exclusion in a test (three scrapes, no `route="/metrics"` series).
- **Unit-level negative control, no mutant tree needed.** Copy `src/` to scratch, delete the route
  registration block from the copy, run the new test file against it with `PYTHONPATH` pointing at the
  copy (`--override-ini="pythonpath="` so the repo's ini does not shadow it), and require the SPECIFIC
  failing test names plus a ratio (e.g. 3 of 5). Restore, re-run, require all green. Quote both numbers.
- **A repo with a docs-index test wants the new doc LINKED, not merely written.** Adding `docs/<x>.md`
  fails a tracked-docs-reachability test until it is linked from the root README or the docs index;
  satisfy it through whichever surface is clean — if the root README stages a pre-existing placeholder
  secret that trips the commit scanner, add the line to `docs/README.md` instead of editing or
  bypassing the scanner. Verify with the index test alone before committing.

## Pitfalls

- The census clears on a source hit for `prometheus|otel|statsd|datadog` plus a `/metrics` route; a real
  endpoint and its doc satisfy it honestly. Never rename a file to satisfy the matcher.
- Clearing `metrics` does not clear `deploy-doc`/`container`: say the family's remaining gaps out loud
  instead of implying a clean census.
- A metrics endpoint that counts itself pollutes the duration histogram on every scrape; either exclude
  the scrape path from the observation or state that it is counted, in the doc and the test.
- Document the scrape path, the opt-in snippet and the fail-closed rule in the repo's own ops doc name,
  so the next `deploy-doc` audit finds it where the matcher looks.
