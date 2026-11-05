# Coverage — `_coverage.md`

Two tables that no checker can infer. Both are mandatory before quorum.

## Surface → flow (from the live system, not memory)

| surface | declared at | flow | or out-of-scope reason |
|---|---|---|---|
| `CLI verb --x` | `cmd/x.go` | FLOW-01 | |
| `GET /v1/...` | router table | FLOW-02 | |
| `<cron/timer unit>` | unit list | FLOW-03 | |

## Requirement → module → assertion

| R | module | flow | assertion | evidence |
|---|---|---|---|---|
| R-001 | MOD-01 | FLOW-01 | test: TestExpiredRejects | FACT-01 |

## Open questions carried

| question | owner | resolution path | blocking? |
|---|---|---|---|
| <from the Rumsfeld known-unknowns> | <...> | <...> | yes/no |
