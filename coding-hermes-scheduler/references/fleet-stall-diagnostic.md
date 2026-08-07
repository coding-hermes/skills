# Fleet Stall Rapid Diagnostic (2026-07-19)

When multiple projects haven't fired in hours, run these in order.

## 1. How many enabled?

```bash
python3 -c "import sqlite3;db=sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
print(db.execute('SELECT COUNT(*) FROM projects WHERE enabled=1').fetchone()[0])"
```

Expected: 38 active. Less = some disabled since last check.

## 2. Any disabled that shouldn't be?

```bash
python3 -c "import sqlite3;db=sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
for r in db.execute('SELECT name,cooldown_s FROM projects WHERE enabled=0 AND name NOT LIKE \"sim-%\" AND name NOT LIKE \"ch-%\" AND name NOT LIKE \"mon-%\" AND name NOT LIKE \"dc-%\" AND name NOT LIKE \"global-%\"').fetchall():
    print(f'DISABLED: {r[0]} cd={r[1]}s')"
```

Real projects should never be disabled. Test/sim projects are intentionally off.

## 3. Inflated cooldowns? (>30min)

```bash
python3 -c "import sqlite3;db=sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
for r in db.execute('SELECT name,cooldown_s,priority FROM projects WHERE enabled=1 AND cooldown_s>1800 ORDER BY cooldown_s DESC').fetchall():
    print(f'{r[0]:30s} {r[1]//3600}h{r[1]%3600//60}m prio={r[2]}')"
```

If any show >1h, auto-slowdown may have escalated. Reset: `UPDATE projects SET cooldown_s=900`.

## 4. Stale last_tick? (>90min)

```bash
python3 -c "
import sqlite3, datetime
db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
now = datetime.datetime.now(datetime.timezone.utc)
for r in db.execute('SELECT name,last_tick_completed FROM projects WHERE enabled=1').fetchall():
    if r[1]:
        ts = datetime.datetime.fromisoformat(r[1].replace('Z','+00:00'))
        age = (now - ts).total_seconds() / 60
        if age > 90:
            print(f'{r[0]:30s} {age:.0f}m ago')"
```

## 5. Duplicate processes?

```bash
ps aux | grep -c '[r]ethinkdb'
# If > expected, suspect timeout→re-spawn→duplicate cascade
```

## 6. Case-variant duplicates?

```bash
python3 -c "import sqlite3;db=sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')
names=db.execute('SELECT LOWER(name), COUNT(*) FROM projects GROUP BY LOWER(name) HAVING COUNT(*)>1').fetchall()
for n in names: print(f'DUPLICATE: {n[0]} ({n[1]} copies)')"
```

SQLite is case-sensitive on WHERE name=?. "<project>" and "<project>" are separate projects.

## Quick Fixes

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| en=0 | Fleet TOML `Enabled=false` | Remove from TOML or set `Enabled=true` |
| cd>1h | Auto-slowdown escalation | `UPDATE projects SET cooldown_s=900` |
| Duplicate processes | Timeout freed slot, re-spawned | Dedup guard (v3.8) prevents this |
| Stale >2h | Packed but never spawned | Force eval: `curl -X POST /api/v1/evaluate` |
| NULL namespace | `--namespace-mode` skips it | `UPDATE projects SET namespace_id='coding-hermes'` |
| Case duplicate | Two entries, different case | Disable/merge one, use single name |
