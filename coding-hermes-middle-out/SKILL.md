---
name: coding-hermes-middle-out
description: Middle-out development — build from the engine outward. Every package must be wired to CLI/HTTP/gRPC before "done." Catches the "all tests pass, nothing usable" failure mode.
version: 1.0.0
category: software-development
---

# Coding Hermes Middle-Out

**The problem:** Foremen build engines that pass tests but aren't wired to the world. 12 packages with green tests and zero entry points. No CLI. No HTTP handlers. No `cmd/`. No `main.go`. "Done" means nothing.

**The principle:** Build from the MIDDLE (engine internals) OUT to both ends (user interface AND infrastructure). Every line of engine code must have a corresponding outward path.

## The Middle-Out Pyramid

```
         CLI flags              HTTP routes          gRPC handlers
         --port 8080           GET /api/v1/...      RegisterServer()
              \                    |                    /
               \                   |                   /
                ---- config.go ← main.go ← cmd/ ------
                           |           |
                    ┌──────┴───────────┴──────┐
                    │     ENGINE (packages)    │
                    │  services, repos, models │
                    │  All tests green ✓       │
                    └──────────────────────────┘
```

The engine is the middle. It works. Now build OUT:
1. **Out-left:** Config struct → env vars → CLI flags
2. **Out-right:** Handlers → routes → main.go wiring
3. **Out-up:** cmd/ directory → serve command → Dockerfile
4. **Out-down:** DB migrations → connection pool → health check

## The 8 Wiring Questions

Before marking any implementation phase complete, answer ALL 8:

| # | Question | Check |
|---|----------|-------|
| 1 | Does `cmd/` exist with a `main.go`? | `ls cmd/*/main.go` |
| 2 | Does `main.go` import every service package? | `grep import cmd/*/main.go` |
| 3 | Is every API handler registered on a route? | `grep -r 'HandleFunc\|mux.Handle' .` |
| 4 | Is every gRPC service registered? | `grep -r 'Register.*Server' .` |
| 5 | Does config load from env vars + CLI flags? | `grep 'viper\|flag\|os.Getenv' main.go` |
| 6 | Does `serve` command start and stay alive? | `go build && timeout 5 ./bin serve` |
| 7 | Does health endpoint return 200? | `curl localhost:<port>/health` |
| 8 | Do DB migrations run before serve? | `ls migrations/ && grep migrate main.go` |

If ANY answer is "no," the phase is NOT complete. Create WIRING tasks.

## The Wiring Task Template

```
## [ ] WIRING — <component> not connected to <entry point>

**Engine:** <package> — all tests green, ready for wiring
**Missing:** <CLI flag | HTTP route | gRPC registration | main.go import>
**To wire:**
1. Create handler in <file>
2. Register route in <router file>
3. Wire into main.go
4. Add config flag/env var if needed
5. End-to-end test: curl/grpcurl/cli invocation
```

## Proven Failure Pattern

**Dagger/Crier 2026-07:** 12 packages with green tests. Foreman marked "done." No `cmd/`, no `main.go`, no HTTP listener. Engine running in a vacuum — completely unusable.

**Imhotep after wiring:** Same foreman, 1 tick later. 12 packages → wired to `dagger serve`. Works, tests, health endpoint responds. All 8 wiring questions answered.

## Integration with never-done Audit

The `never-done` skill's Step 11 (Middle-Out Wiring) loads this skill and runs the 8-question check on every empty-board tick. If any project has engine code without wiring, it creates WIRING tasks.

## When to Wire vs When to Defer

| Scenario | Action |
|----------|--------|
| Package has tests + no entry point | WIRE NOW |
| Package is a library (no server) | Skip wiring — verify importable |
| Package is infrastructure-only (migrations, config) | Wire into main.go startup |
| CLI tool (single binary) | Wire into cmd/ with cobra/urfave |
| HTTP service | Wire into cmd/ with router + handlers |
| gRPC service | Wire into cmd/ with server registration |
