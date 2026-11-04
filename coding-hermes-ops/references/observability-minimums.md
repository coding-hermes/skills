# Observability minimums

The question an ops sweep answers is not "are there dashboards?" but **"if this broke at 3am,
what would tell us, and how long would it take?"** If the answer is "a user", the service is
unmonitored regardless of how many graphs exist.

## The four surfaces, in order of value

1. **Health** — a cheap endpoint that answers without touching a dependency. Split it:
   - *liveness*: "the process is alive and its loop is turning" (no database, no network),
   - *readiness*: "I can serve traffic right now" (dependencies checked, cached briefly).
   Conflating them turns a database blip into a restart storm.
2. **Metrics** — counters and gauges that let someone compute an error rate and a latency without
   reading logs. Minimum per service: requests (by status class), latency histogram, in-flight
   work, and one saturation signal (queue depth, pool usage, disk).
3. **Structured logs** — one line per event, machine-parseable, with a correlation id. A log
   nobody can grep by request id is a diary.
4. **Alerts** — a rule that fires on a symptom a human cares about (error rate, saturation,
   staleness), not on every counter crossing zero.

## The fleet-specific rule: liveness must be measured where the work happens

A lane can report healthy while doing nothing. Two real shapes of that:

- a scheduler whose `/health` answers 200 while its tick loop is stalled — health must include
  *last successful unit of work*, not only process liveness;
- a pipeline that exits 0 while producing nothing — a silent tripwire is not a pass. The
  end-to-end check is **destination coverage**: did the row land, did the message arrive, does the
  query return the new data. Never accept "the cron ran" as proof.

Corollary: any monitor whose failure mode is silence needs a **dead-man signal** (a heartbeat
that alerts when it *stops*), because the absence of an alert is indistinguishable from health.

## Minimum viable telemetry per project kind

| kind | floor |
|---|---|
| service | liveness + readiness, request/latency/error metrics, structured logs, one saturation signal, restart policy |
| batch / cron | last-success timestamp exported as a metric, failure counter, dead-man alert |
| cli | version stamped into the binary, non-zero exit on failure, `--version` answering from the build |
| library | release pipeline, semver, changelog |
| docs / spec | nothing — uptime is not a property of a corpus |

## Proving it live

A surface that exists in the source is not a surface that works. Verify in this order, and keep
the evidence:

```bash
curl -fsS localhost:PORT/health            # 200 and a body you can read
curl -fsS localhost:PORT/metrics | head    # a metric that MOVES when you make a request
journalctl -u <unit> -n 20                 # a log line for the request you just made
systemctl kill -s KILL <unit> && sleep 5 && systemctl is-active <unit>   # it came back
```

If any of those is missing, the finding is real even if the code "has" the feature.

## Failure taxonomy worth keeping straight

- **Unattributed failure** — a failure with no recorded reason. Keep it in any rate you compute
  (a failure nobody can explain is still a failure) but count it separately so the debt is
  visible. Excusing unreasoned failures is how a quality gate becomes decorative.
- **Self-inflicted failure** — a timeout or refusal the *system* produced (a wall-clock ceiling, an
  empty candidate set, a rating nothing could serve). These must not be charged to the component
  that never got to answer; charging them creates a feedback loop where the gate starves itself.
- **Silent success** — exit 0, nothing produced. The most expensive of the three, because it looks
  healthy on every dashboard.
