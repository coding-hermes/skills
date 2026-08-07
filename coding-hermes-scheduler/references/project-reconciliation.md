# Project Reconciliation Pattern

When verifying the scheduler fleet matches the expected project list.

## Audit script (Python — reads scheduler.db)

```python
import sqlite3
db = sqlite3.connect('~/.hermes/coding-hermes/scheduler.db')

expected = ['project-a', 'project-b', ...]  # your list

db_names = {r[0].lower().replace('-','').replace('_',''): r[0] 
            for r in db.execute('SELECT name FROM projects').fetchall()}

found, missing, disabled = 0, [], []
for name in expected:
    clean = name.lower().replace('-','').replace('_','')
    if clean in db_names:
        real_name = db_names[clean]
        enabled = db.execute("SELECT enabled FROM projects WHERE name=?", (real_name,)).fetchone()[0]
        if enabled:
            found += 1
        else:
            disabled.append(f"{name} → {real_name}")
    else:
        missing.append(name)
```

## Common issues found

1. **Duplicate projects with different case:** `<project>` and `<project>` point to same workdir.
   Disable the less-active variant.
2. **Project disabled:** Check `SELECT enabled FROM projects WHERE name='X'`. Enable with:
   `UPDATE projects SET enabled=1 WHERE name='X'`.
3. **Missing delivery target:** `SELECT name FROM projects WHERE enabled=1 AND (deliver IS NULL OR deliver='')`.
   Fix: `UPDATE projects SET deliver='telegram:-1003310984808:83996' WHERE name='X'`.
4. **Project not in DB at all:** Needs to be registered. Use the API or direct INSERT.
5. **Wrong workdir:** Two projects pointing to same directory (e.g., `hivemind-pulse` and 
   `<project>` both → `~/<project>`). Disable the duplicate.

## 2026-07-18 reconciliation results

- **39 enabled projects** after cleanup
- 3 fixes applied: `asce` (was disabled), <project> duplicate (disabled uppercase variant),
  `hivemind-pulse` (duplicate of `<project>`, disabled)
- 1 missing: `hilo` — never onboarded, no directory
- All 39 enabled projects have delivery targets set
