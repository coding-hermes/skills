# Zombie Tick Detection — Process-Liveness, Not Blind Timeout

## Problem

When the schedulerd process dies (kill, crash, systemctl stop), any running
ticks remain in 'running' state in the database. The new scheduler process
starts and sees these dangling ticks — they block concurrency slots until
cleared.

A naive fix (30-minute blind timeout) breaks legitimate long-running foreman
ticks that legitimately take >30 minutes.

## Solution: Three-Layer Defense

### Layer 1: Startup Cleanup (`cleanDanglingOnStartup()`)

On boot, marks ALL running ticks as 'timeout'. Rationale: a running tick from
a previous process has no OS process — it's a zombie.

```go
func (l *Loop) cleanDanglingOnStartup() {
    l.db.ExecContext(ctx, `UPDATE ticks SET status='timeout' WHERE status='running'`)
}
```

### Layer 2: Periodic Zombie Reaper (`reapZombies()`)

Runs every 60s. For each running tick with a PID, checks `/proc/<pid>/stat`:

- **Process exists** → tick is valid (leave alone, regardless of age)
- **Process doesn't exist** → zombie → mark as timeout

```go
func (l *Loop) reapZombies() {
    rows := l.db.Query(`SELECT id, pid FROM ticks WHERE status='running' AND pid > 0`)
    for rows.Next() {
        if _, err := os.Stat(fmt.Sprintf("/proc/%d/stat", pid)); os.IsNotExist(err) {
            l.db.Exec(`UPDATE ticks SET status='timeout', outcome='zombie_reaped' WHERE id=?`, id)
        }
    }
}
```

### Layer 3: Monitor Warning

Every 60s, logs if running count > max_concurrent (possible process leak):

```go
if running > l.maxConcur {
    log.Printf("ZOMBIE: %d ticks running (max=%d) — possible process leak", running, l.maxConcur)
}
```

## Why Not Blind Timeout?

A 30-minute hard cutoff kills legitimate work:
- Large builds (10+ minutes)
- Long test suites
- Complex code changes across many files
- E2E integration tests

Process-liveness is the only reliable signal: if the process is running,
the tick is valid regardless of age.

## PID Tracking

The scheduler stores the PID of each spawned `hermes chat` process in the
ticks table (`pid INTEGER DEFAULT 0`). Without this, the reaper can't check
process liveness.

```sql
-- In migrations.go: CREATE TABLE ticks
pid INTEGER DEFAULT 0

-- In spawn.go: UPDATE ticks SET status='running', spawned_at=?, pid=? WHERE id=?
```

## Proven

- **2026-07-18** — 15 dangling ticks from a scheduler restart blocked all 8
  concurrency slots. No new ticks spawned for 2+ hours. Root cause: no startup
  cleanup and no periodic reaper. Fixed by adding `cleanDanglingOnStartup()` +
  `reapZombies()` with `/proc/<pid>/stat` checks. The 30-minute blind timeout
  was rejected by Bane as "bad design — things can take longer than 30 minutes."
